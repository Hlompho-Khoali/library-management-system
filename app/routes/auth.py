from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    session,
    redirect,
    url_for
)

from app.models import Library, Member, Verification
from app.services.loan_service import (
    OVERDUE_BLOCK,
    enforce_overdue_blocks,
    total_outstanding_fees,
)
from app.extensions import db
from app.services.approval_service import create_member_from_verification
from app.services.card_service import generate_virtual_card, format_member_number
from app.services.ocr_service import date_from_sa_id, validate_sa_id
from app.services.password_reset_service import (
    generate_reset_token,
    decode_reset_token,
    is_token_valid_for_member,
    send_password_reset_email,
)
from app.services.rejection_reasons import describe_rejection_reasons
from app.services.supabase_storage import supabase
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from datetime import datetime

import base64
import secrets
import uuid


auth_bp = Blueprint("auth", __name__)
POPIA_NOTICE_VERSION = "1.0"

@auth_bp.route("/")
def home():
    return render_template("home.html")


@auth_bp.route("/about")
def about():

    return render_template("about.html")


@auth_bp.route("/faq")
def faq():
    return render_template("faq.html")


@auth_bp.route("/privacy-consent")
def privacy_consent():
    return render_template(
        "auth/privacy_consent.html",
        notice_version=POPIA_NOTICE_VERSION,
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    libraries = Library.query.order_by(Library.name).all()

    if request.method == "POST":
        if request.form.get("privacy_consent") != "accepted":
            flash("Please read and accept the POPIA privacy notice to continue.", "error")
            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        # Personal information
        title = request.form.get("title", "").strip()
        first_name = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        id_number = request.form.get("id_number", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()
        phone_number = request.form.get("phone_number", "").strip()

        # Address
        street_address = request.form.get("street_address", "").strip()
        suburb = request.form.get("suburb", "").strip()
        city = request.form.get("city", "").strip()
        postal_code = request.form.get("postal_code", "").strip()

        # Library
        library_id = request.form.get("library_id", "").strip()

        # Account
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # -------------------------
        # Validation
        # -------------------------

        if not all([
            title,
            first_name,
            last_name,
            id_number,
            date_of_birth,
            phone_number,
            street_address,
            suburb,
            city,
            postal_code,
            library_id,
            email,
            password,
            confirm_password
        ]):
            flash("Please complete all required fields.", "error")

            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        if len(phone_number) != 10 or not phone_number.isdigit():
            flash("Phone number must contain exactly 10 digits.", "error")

            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        if password != confirm_password:
            flash("Passwords do not match.", "error")

            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        if not validate_sa_id(id_number):
            flash("Please enter a valid South African ID number.", "error")

            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        id_date_of_birth = date_from_sa_id(id_number)

        if not id_date_of_birth:
            flash("The date of birth could not be read from the ID number.", "error")

            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        if date_of_birth != id_date_of_birth:
            flash("Date of birth must match the date encoded in the ID number.", "error")

            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        existing_id = Member.query.filter_by(
            id_number=id_number
        ).first()

        if existing_id:
            flash("A member with this ID number already exists.", "error")

            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        existing_email = Member.query.filter_by(
            email=email
        ).first()

        if existing_email:
            flash("An account with this email already exists.", "error")

            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")

            return render_template(
                "auth/register.html",
                libraries=libraries
            )

        # -------------------------
        # Prepare registration data
        # -------------------------

        password_hash = generate_password_hash(password)
        session["privacy_consent_at"] = datetime.utcnow().isoformat()
        session["privacy_notice_version"] = POPIA_NOTICE_VERSION

        session["pending_registration"] = {
            "title": title,
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "id_number": id_number,
            "date_of_birth": date_of_birth,
            "phone_number": phone_number,
            "street_address": street_address,
            "suburb": suburb,
            "city": city,
            "postal_code": postal_code,
            "library_id": library_id,
            "email": email,
            "password_hash": password_hash,
        }

        return redirect(url_for("auth.verify_id"))

    # -------------------------
    # GET request
    # -------------------------

    return render_template(
        "auth/register.html",
        libraries=libraries
    )

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        enforce_overdue_blocks()

        # Find the account
        member = Member.query.filter_by(email=email).first()

        if not member:
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html")

        # Check password
        if not check_password_hash(member.password_hash, password):
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html")

        # Check whether account is active
        if not member.is_active and member.block_reason == OVERDUE_BLOCK:
            flash(
                "Your membership is blocked because you have outstanding book(s). "
                "Please report to the admin desk to return the book(s) and pay any outstanding fees.",
                "error",
            )
            return render_template("auth/login.html")

        if not member.is_active:
            flash("Your account is inactive. Please contact the library.", "error")
            return render_template("auth/login.html")

        # Store login information in the session
        session.permanent = True
        session["member_id"] = member.id
        session["role"] = member.role

        # Admin / security officer access
        if member.role == "admin":
            return redirect(url_for("verification.dashboard"))

        if member.role == "security_officer":
            return redirect(url_for("verification.security_dashboard"))

        # Normal member
        return redirect(url_for("auth.member_dashboard"))

    return render_template("auth/login.html")

@auth_bp.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "info")

    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        member = Member.query.filter_by(email=email).first()

        if member is not None:
            token = generate_reset_token(member)
            reset_url = url_for("auth.reset_password", token=token, _external=True)

            try:
                send_password_reset_email(member, reset_url)
            except Exception as e:
                print("Password reset email error:", e)

        # Always show the same message so we never reveal whether an email exists.
        flash(
            "If that email address is registered, a password reset link has been sent.",
            "info"
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    payload = decode_reset_token(token)
    member = Member.query.get(payload["member_id"]) if payload else None

    if not is_token_valid_for_member(payload, member):
        flash("This password reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(new_password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("auth/reset_password.html", token=token)

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/reset_password.html", token=token)

        member.password_hash = generate_password_hash(new_password)
        db.session.commit()

        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/member/dashboard")
def member_dashboard():
    if session.get("role") != "member" or not session.get("member_id"):
        return redirect(url_for("auth.login"))

    member = Member.query.get_or_404(session["member_id"])
    library = Library.query.get(member.library_id)
    member_number = format_member_number(member.id)

    card_filename = None
    child_cards = []

    if member.id_review_status == "approved":
        generate_virtual_card(
            member_number=member_number,
            full_name=f"{member.first_name} {member.last_name}",
            library_name=library.name if library else "Library",
        )
        card_filename = f"{member_number}.png"

    for child in member.children:
        child_number = format_member_number(child.id)
        generate_virtual_card(
            member_number=child_number,
            full_name=f"{child.first_name} {child.last_name}",
            library_name=library.name if library else "Library",
            status_label="CHILD MEMBER",
            status_fill=(18, 64, 48),
            status_text_color="white",
            child_card=True,
        )
        child_cards.append({
            "member": child,
            "member_number": child_number,
            "card_filename": f"{child_number}.png",
            "card_version": f"child-feet-v1-{child.updated_at.timestamp() if child.updated_at else child.id}",
        })

    return render_template(
        "auth/member_dashboard.html",
        member=member,
        library=library,
        member_number=member_number,
        card_filename=card_filename,
        child_cards=child_cards,
        loans=[loan for loan in member.loans if loan.closed_at is None],
        outstanding_fees=total_outstanding_fees(member),
        fee_loans=[loan for loan in member.loans if loan.fee_outstanding() > 0],
        rejection_reasons=describe_rejection_reasons(member.id_rejection_reasons),
    )


@auth_bp.route("/member/reupload-id", methods=["POST"])
def reupload_id():
    if session.get("role") != "member" or not session.get("member_id"):
        return {"success": False, "message": "Please log in again."}, 401

    member = Member.query.get_or_404(session["member_id"])

    if member.id_review_status != "declined":
        return {
            "success": False,
            "message": "No ID resubmission is required at this time."
        }, 400

    data = request.get_json()

    if not data or "image" not in data:
        return {"success": False, "message": "No ID image was received."}, 400

    try:
        image_data = data["image"]

        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        image_bytes = base64.b64decode(image_data)

        max_size = 5 * 1024 * 1024  # 5 MB

        if len(image_bytes) > max_size:
            return {
                "success": False,
                "message": "The ID image is too large. Please choose a smaller image."
            }, 400

        file_path = f"pending/{uuid.uuid4()}.jpg"

        supabase.storage.from_("id-documents").upload(
            file_path,
            image_bytes,
            {
                "content-type": "image/jpeg",
                "upsert": False
            }
        )

        member.id_document_front_path = file_path
        member.id_document_back_path = file_path
        member.id_review_status = "pending"
        member.id_rejection_reasons = None
        member.id_rejection_comment = None

        verification = (
            db.session.get(Verification, member.verification_id)
            if member.verification_id else None
        )

        if verification is not None:
            verification.id_document_path = file_path
            verification.status = "pending"
            verification.rejection_reasons = None
            verification.rejection_comment = None
            verification.reviewed_at = None

        db.session.commit()

        return {
            "success": True,
            "message": "Your ID has been resubmitted. Please wait for the administrator to review it again.",
        }

    except Exception as e:

        db.session.rollback()

        print("ID resubmission error:", e)

        return {
            "success": False,
            "message": "The ID image could not be resubmitted."
        }, 500


@auth_bp.route("/member/settings", methods=["GET", "POST"])
def member_settings():
    if session.get("role") != "member" or not session.get("member_id"):
        return redirect(url_for("auth.login"))

    member = Member.query.get_or_404(session["member_id"])

    if request.method == "POST":

        phone_number = request.form.get("phone_number", "").strip()
        street_address = request.form.get("street_address", "").strip()
        suburb = request.form.get("suburb", "").strip()
        city = request.form.get("city", "").strip()
        postal_code = request.form.get("postal_code", "").strip()

        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([phone_number, street_address, suburb, city, postal_code]):
            flash("Please complete all contact detail fields.", "error")
            return render_template("auth/member_settings.html", member=member)

        if len(phone_number) != 10 or not phone_number.isdigit():
            flash("Phone number must contain exactly 10 digits.", "error")
            return render_template("auth/member_settings.html", member=member)

        wants_password_change = any([current_password, new_password, confirm_password])

        if wants_password_change:
            if not check_password_hash(member.password_hash, current_password):
                flash("Your current password is incorrect.", "error")
                return render_template("auth/member_settings.html", member=member)

            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "error")
                return render_template("auth/member_settings.html", member=member)

            if new_password != confirm_password:
                flash("New password and confirmation do not match.", "error")
                return render_template("auth/member_settings.html", member=member)

            member.password_hash = generate_password_hash(new_password)

        member.phone_number = phone_number
        member.street_address = street_address
        member.suburb = suburb
        member.city = city
        member.postal_code = postal_code

        db.session.commit()

        flash("Your account settings have been updated.", "success")
        return redirect(url_for("auth.member_settings"))

    return render_template("auth/member_settings.html", member=member)


@auth_bp.route("/member/add-child", methods=["POST"])
def add_child():
    if session.get("role") != "member" or not session.get("member_id"):
        return redirect(url_for("auth.login"))

    parent = Member.query.get_or_404(session["member_id"])
    first_name = request.form.get("first_name", "").strip()
    middle_name = request.form.get("middle_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    date_of_birth_text = request.form.get("date_of_birth", "").strip()

    if not first_name or not last_name or not date_of_birth_text:
        flash("Please complete the child's name and date of birth.", "error")
        return redirect(url_for("auth.member_settings"))

    try:
        date_of_birth = datetime.strptime(date_of_birth_text, "%Y-%m-%d").date()
    except ValueError:
        flash("Please enter a valid date of birth.", "error")
        return redirect(url_for("auth.member_settings"))

    today = datetime.utcnow().date()
    age = today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )
    if date_of_birth > today or age >= 18:
        flash("A child membership is for members under 18 years old.", "error")
        return redirect(url_for("auth.member_settings"))

    child = Member(
        parent=parent,
        is_child=True,
        title="Child",
        first_name=first_name,
        middle_name=middle_name or None,
        last_name=last_name,
        date_of_birth=date_of_birth,
        phone_number=parent.phone_number,
        street_address=parent.street_address,
        suburb=parent.suburb,
        city=parent.city,
        postal_code=parent.postal_code,
        library_id=parent.library_id,
        email=f"child-{secrets.token_hex(8)}@library.local",
        password_hash=generate_password_hash(secrets.token_urlsafe(24)),
        is_active=True,
        role="member",
        id_verified=True,
        id_verified_at=datetime.utcnow(),
        id_review_status="approved",
        id_number=f"C{secrets.token_hex(6).upper()}",
    )
    db.session.add(child)
    db.session.commit()

    flash(f"{first_name} {last_name}'s child membership was created.", "success")
    return redirect(url_for("auth.member_settings"))


@auth_bp.route("/member/child/<int:child_id>/edit", methods=["POST"])
def edit_child(child_id):
    if session.get("role") != "member" or not session.get("member_id"):
        return redirect(url_for("auth.login"))

    parent = Member.query.get_or_404(session["member_id"])
    child = Member.query.filter_by(
        id=child_id,
        parent_id=parent.id,
        is_child=True,
    ).first_or_404()

    first_name = request.form.get("first_name", "").strip()
    middle_name = request.form.get("middle_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    date_of_birth_text = request.form.get("date_of_birth", "").strip()

    if not first_name or not last_name or not date_of_birth_text:
        flash("Please complete the child's name and date of birth.", "error")
        return redirect(url_for("auth.member_settings"))

    try:
        date_of_birth = datetime.strptime(date_of_birth_text, "%Y-%m-%d").date()
    except ValueError:
        flash("Please enter a valid date of birth.", "error")
        return redirect(url_for("auth.member_settings"))

    today = datetime.utcnow().date()
    age = today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )
    if date_of_birth > today or age >= 18:
        flash("A child membership is for members under 18 years old.", "error")
        return redirect(url_for("auth.member_settings"))

    child.first_name = first_name
    child.middle_name = middle_name or None
    child.last_name = last_name
    child.date_of_birth = date_of_birth
    db.session.commit()

    flash(f"{first_name} {last_name}'s information was updated.", "success")
    return redirect(url_for("auth.member_settings"))


@auth_bp.route("/member/child/<int:child_id>/delete", methods=["POST"])
def delete_child(child_id):
    if session.get("role") != "member" or not session.get("member_id"):
        return redirect(url_for("auth.login"))

    child = Member.query.filter_by(
        id=child_id,
        parent_id=session["member_id"],
        is_child=True,
    ).first_or_404()
    child_name = f"{child.first_name} {child.last_name}"
    db.session.delete(child)
    db.session.commit()

    flash(f"{child_name}'s child membership was deleted.", "info")
    return redirect(url_for("auth.member_settings"))

@auth_bp.route("/verify-id")
def verify_id():

    if "pending_registration" not in session:
        flash(
            "Please complete the registration form first.",
            "error"
        )

        return redirect(url_for("auth.register"))

    return render_template("auth/verify_id.html")

@auth_bp.route("/upload-id", methods=["POST"])
def upload_id():

    if (
        "pending_registration" not in session
        or "privacy_consent_at" not in session
        or session.get("privacy_notice_version") != POPIA_NOTICE_VERSION
    ):
        return {
            "success": False,
            "message": "Please complete registration and accept the current privacy notice first."
        }, 400

    data = request.get_json()

    if not data or "image" not in data:
        return {
            "success": False,
            "message": "No ID image was received."
        }, 400

    try:
        registration = session["pending_registration"]

        image_data = data["image"]

        # Remove the data URL prefix
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        image_bytes = base64.b64decode(image_data)

        # Prevent excessively large uploads
        max_size = 5 * 1024 * 1024  # 5 MB

        if len(image_bytes) > max_size:
            return {
                "success": False,
                "message": "The ID image is too large. Please capture a smaller image."
            }, 400

        # Generate a random file path.
        # Never use the member's ID number in the filename.
        file_path = f"pending/{uuid.uuid4()}.jpg"

        # Upload ID document to private Supabase Storage
        supabase.storage.from_("id-documents").upload(
            file_path,
            image_bytes,
            {
                "content-type": "image/jpeg",
                "upsert": False
            }
        )

        # Store submission as a pending registration for administrator review.
        date_of_birth = datetime.strptime(
            registration["date_of_birth"],
            "%Y-%m-%d"
        ).date()

        verification = Verification(
            title=registration["title"],
            first_name=registration["first_name"],
            middle_name=registration["middle_name"],
            last_name=registration["last_name"],
            id_number=registration["id_number"],
            date_of_birth=date_of_birth,
            phone_number=registration["phone_number"],
            street_address=registration["street_address"],
            suburb=registration["suburb"],
            city=registration["city"],
            postal_code=registration["postal_code"],
            library_id=int(registration["library_id"]),
            email=registration["email"],
            password_hash=registration["password_hash"],
            id_document_path=file_path,
            privacy_consent_at=datetime.fromisoformat(session["privacy_consent_at"]),
            privacy_notice_version=session["privacy_notice_version"],
            status="pending"
        )

        db.session.add(verification)
        db.session.commit()

        session["pending_registration"] = registration
        session["verification_id"] = verification.id
        session["id_document_path"] = file_path
        session["verification_status"] = "pending"

        return {
            "success": True,
            "message": "ID image uploaded and registration submitted for admin approval.",
            "redirect": url_for("auth.verification")
        }

    except Exception as e:

        db.session.rollback()

        print("ID verification error:", e)

        return {
            "success": False,
            "message": "The ID verification could not be submitted."
        }, 500

@auth_bp.route("/verification")
def verification():

    if "pending_registration" not in session and "verification_id" not in session:
        flash(
            "Your registration session has expired. Please register again.",
            "error"
        )
        return redirect(url_for("auth.register"))

    if "id_document_path" not in session and "verification_id" not in session:
        flash(
            "Please upload your ID document first.",
            "error"
        )
        return redirect(url_for("auth.verify_id"))

    return render_template(
        "auth/verification.html",
        registration=session.get("pending_registration")
    )


@auth_bp.route("/registration-status")
def registration_status():
    verification_id = session.get("verification_id")

    if not verification_id:
        return {"status": "expired"}, 400

    verification = db.session.get(Verification, verification_id)

    if verification is None:
        return {"status": "expired"}, 404

    if verification.status == "approved":
        member = Member.query.filter_by(email=verification.email).first()

        if member is None:
            member = create_member_from_verification(verification)
            library = Library.query.get(verification.library_id)
            generate_virtual_card(
                member_number=format_member_number(member.id),
                full_name=f"{member.first_name} {member.last_name}",
                library_name=library.name if library else "Library",
            )

        session["member_id"] = member.id
        session["role"] = member.role
        session.pop("pending_registration", None)
        session.pop("verification_id", None)
        session.pop("id_document_path", None)
        session.pop("verification_status", None)

        return {
            "status": "approved",
            "redirect": url_for("auth.member_dashboard"),
        }

    if verification.status == "declined":
        session.pop("pending_registration", None)
        session.pop("verification_id", None)
        session.pop("id_document_path", None)
        session.pop("verification_status", None)

        flash(
            "Your ID verification was declined. Log in to see the reason and resubmit your ID.",
            "error"
        )

        return {
            "status": "declined",
            "redirect": url_for("auth.login"),
        }

    return {"status": verification.status}