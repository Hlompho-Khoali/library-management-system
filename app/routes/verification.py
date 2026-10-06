from collections import defaultdict
from datetime import datetime
from io import BytesIO

from flask import (
    Blueprint,
    render_template,
    session,
    request,
    redirect,
    url_for,
    flash,
    send_file,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.extensions import db
from app.models import Member, Verification, Library
from app.models import LibraryVisit
from app.services.loan_service import (
    OVERDUE_BLOCK,
    can_lift_block,
    enforce_overdue_blocks,
    total_outstanding_fees,
)
from app.services.card_service import generate_virtual_card, format_member_number
from app.services.approval_service import create_member_from_verification
from app.services.rejection_reasons import REJECTION_REASONS
from app.services.supabase_storage import get_document_url


verification_bp = Blueprint(
    "verification",
    __name__,
    url_prefix="/verification"
)


def require_security_access():
    member_id = session.get("member_id")
    member = db.session.get(Member, member_id) if member_id else None

    if member is None:
        return redirect(url_for("auth.login"))

    if member.role not in {"security_officer", "admin"} or not member.is_active:
        session.clear()
        return redirect(url_for("auth.login"))

    session["role"] = member.role


def require_staff_access():
    member_id = session.get("member_id")
    member = db.session.get(Member, member_id) if member_id else None

    if member is None:
        return redirect(url_for("auth.login"))

    if member.role not in {"security_officer", "admin"} or not member.is_active:
        session.clear()
        return redirect(url_for("auth.login"))

    session["role"] = member.role


@verification_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    access_redirect = require_staff_access()
    if access_redirect:
        return access_redirect

    enforce_overdue_blocks()

    pending = Verification.query.filter_by(status="pending").order_by(
        Verification.created_at.desc()
    ).all()

    for application in pending:
        application.id_document_url = get_document_url(application.id_document_path)
        library = db.session.get(Library, application.library_id)
        application.library_name = library.name if library else "Unknown library"

    member = None
    status = None

    if request.method == "POST":
        lookup = request.form.get("member_lookup", "").strip()

        if lookup:
            member = Member.query.filter(
                (Member.id_number == lookup)
                | (Member.email == lookup)
                | (Member.id == lookup)
            ).first()

            if member is None:
                status = "Member not found."
            elif member.is_active and member.id_verified:
                status = "Eligible to access the library."
            else:
                status = "Not eligible to access the library."

    active_members = Member.query.filter_by(
        is_active=True,
        id_verified=True,
        role="member"
    ).order_by(Member.first_name).all()

    members = Member.query.filter_by(
        role="member"
    ).order_by(Member.first_name).all()

    return render_template(
        "verification/dashboard.html",
        pending=pending,
        member=member,
        status=status,
        active_members=active_members,
        members=members,
        format_member_number=format_member_number,
        rejection_reason_choices=REJECTION_REASONS,
    )


@verification_bp.route("/security", methods=["GET", "POST"])
def security_dashboard():
    access_redirect = require_security_access()
    if access_redirect:
        return access_redirect

    enforce_overdue_blocks()

    result = None
    if request.method == "POST":
        return scan_member()

    return _render_security_dashboard(result)


def _render_security_dashboard(result):
    current_visits = LibraryVisit.query.filter_by(exit_at=None).order_by(
        LibraryVisit.entry_at.desc()
    ).all()
    overdue_blocked = Member.query.filter_by(
        is_active=False, block_reason=OVERDUE_BLOCK, role="member"
    ).order_by(Member.first_name).all()

    return render_template(
        "verification/security_dashboard.html",
        current_visits=current_visits,
        overdue_blocked=overdue_blocked,
        format_member_number=format_member_number,
        total_outstanding_fees=total_outstanding_fees,
        result=result,
    )


@verification_bp.route("/security/stats.pdf")
def visit_statistics_pdf():
    access_redirect = require_security_access()
    if access_redirect:
        return access_redirect

    daily_entries = defaultdict(int)
    daily_exits = defaultdict(int)

    entry_rows = db.session.query(
        db.func.date(LibraryVisit.entry_at),
        db.func.count(LibraryVisit.id),
    ).group_by(db.func.date(LibraryVisit.entry_at)).all()
    exit_rows = db.session.query(
        db.func.date(LibraryVisit.exit_at),
        db.func.count(LibraryVisit.id),
    ).filter(LibraryVisit.exit_at.isnot(None)).group_by(
        db.func.date(LibraryVisit.exit_at)
    ).all()

    for visit_date, count in entry_rows:
        daily_entries[visit_date] = count
    for visit_date, count in exit_rows:
        daily_exits[visit_date] = count

    total_entries = sum(daily_entries.values())
    total_exits = sum(daily_exits.values())
    currently_inside = LibraryVisit.query.filter_by(exit_at=None).count()
    unique_members = db.session.query(
        db.func.count(db.distinct(LibraryVisit.member_id))
    ).scalar() or 0

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Library Visit Statistics",
    )
    styles = getSampleStyleSheet()
    report = [
        Paragraph("Library Visit Statistics", styles["Title"]),
        Paragraph(
            f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}",
            styles["Normal"],
        ),
        Spacer(1, 18),
        Paragraph("All-time summary", styles["Heading2"]),
    ]

    summary_table = Table([
        ["Recorded entries", "Recorded exits", "Currently inside", "Unique members"],
        [total_entries, total_exits, currently_inside, unique_members],
    ], colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#214e34")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#edf4ef")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd9cf")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd9cf")),
    ]))
    report.extend([summary_table, Spacer(1, 18), Paragraph("Daily entry and exit log", styles["Heading2"])])

    visits = LibraryVisit.query.order_by(LibraryVisit.entry_at.desc()).all()
    daily_data = [["Date", "Entries", "Exits", "Name", "Entry Time", "Exit Time"]]
    for visit in visits:
        daily_data.append([
            visit.entry_at.strftime("%d %b %Y"),
            1,
            1 if visit.exit_at else 0,
            f"{visit.member.first_name} {visit.member.last_name}",
            visit.entry_at.strftime("%H:%M"),
            visit.exit_at.strftime("%H:%M") if visit.exit_at else "-",
        ])
    if not visits:
        daily_data.append(["No visit activity recorded", "-", "-", "-", "-", "-"])

    daily_table = Table(
        daily_data,
        colWidths=[1.2 * inch, 0.7 * inch, 0.7 * inch, 2.0 * inch, 1.3 * inch, 1.3 * inch],
        repeatRows=1,
    )
    daily_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#214e34")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7f4")]),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd9cf")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd9cf")),
    ]))
    report.append(daily_table)
    document.build(report)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="library-visit-statistics.pdf",
    )


def _monthly_statistics_pdf(title, column_label, rows, total, download_name):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=title,
    )
    styles = getSampleStyleSheet()
    report = [
        Paragraph(title, styles["Title"]),
        Paragraph(
            f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}",
            styles["Normal"],
        ),
        Spacer(1, 18),
        Paragraph("Monthly summary", styles["Heading2"]),
    ]

    data = [["Month", column_label]]
    data.extend(rows or [["No activity recorded", 0]])
    table = Table(data, colWidths=[4.6 * inch, 2.6 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#214e34")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7f4")]),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd9cf")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd9cf")),
    ]))
    report.extend([
        table,
        Spacer(1, 18),
        Paragraph(f"All-time total: {total}", styles["Heading2"]),
    ])
    document.build(report)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


@verification_bp.route("/admin/monthly-members.pdf")
def monthly_member_statistics_pdf():
    access_redirect = require_admin()
    if access_redirect:
        return access_redirect

    monthly_members = defaultdict(int)
    members = Member.query.filter_by(role="member").all()
    for member in members:
        monthly_members[member.created_at.strftime("%Y-%m")] += 1

    rows = [[month, monthly_members[month]] for month in sorted(monthly_members)]
    return _monthly_statistics_pdf(
        "Monthly Member Account Statistics",
        "Accounts created",
        rows,
        len(members),
        "monthly-member-account-statistics.pdf",
    )


@verification_bp.route("/admin/monthly-entries.pdf")
def monthly_entry_statistics_pdf():
    access_redirect = require_admin()
    if access_redirect:
        return access_redirect

    monthly_entries = defaultdict(int)
    visits = LibraryVisit.query.all()
    for visit in visits:
        monthly_entries[visit.entry_at.strftime("%Y-%m")] += 1

    rows = [[month, monthly_entries[month]] for month in sorted(monthly_entries)]
    return _monthly_statistics_pdf(
        "Monthly Library Entry Statistics",
        "Entries recorded",
        rows,
        len(visits),
        "monthly-library-entry-statistics.pdf",
    )


@verification_bp.route("/security/scan", methods=["GET", "POST"])
def scan_member():
    access_redirect = require_security_access()
    if access_redirect:
        return access_redirect

    if request.method == "GET":
        return redirect(url_for("verification.security_dashboard"))

    enforce_overdue_blocks()

    raw_barcode = request.form.get("barcode", "").strip()
    member = None

    if len(raw_barcode) == 8 and raw_barcode.isdigit():
        member_id = int(raw_barcode)
        member = Member.query.filter_by(id=member_id).first()

    if member is None:
        result = {
            "approved": False,
            "heading": "Access denied",
            "name": "Unknown member",
            "message": "This barcode is not linked to a member account.",
        }
    elif member.block_reason == OVERDUE_BLOCK and not member.is_active:
        result = {
            "approved": False,
            "heading": "Access denied - membership blocked",
            "name": f"{member.first_name} {member.last_name}",
            "message": "This member has outstanding book(s). Ask them to report to the admin desk to return the book(s) and pay any outstanding fees.",
            "member": member,
            "member_number": format_member_number(member.id),
        }
    elif not member.is_active or not member.id_verified or member.role != "member":
        result = {
            "approved": False,
            "heading": "Access denied",
            "name": f"{member.first_name} {member.last_name}",
            "message": "This membership is not active or verified.",
            "member": member,
            "member_number": format_member_number(member.id),
        }
    else:
        open_visit = LibraryVisit.query.filter_by(
            member_id=member.id,
            exit_at=None,
        ).order_by(LibraryVisit.entry_at.desc()).first()

        if open_visit is None:
            visit = LibraryVisit(member_id=member.id)
            db.session.add(visit)
            action = "Entry recorded"
            message = "The member is eligible to enter the library."
        else:
            open_visit.exit_at = db.func.now()
            action = "Exit recorded"
            message = "The member has been checked out of the library."

        db.session.commit()
        result = {
            "approved": True,
            "heading": action,
            "name": f"{member.first_name} {member.last_name}",
            "message": message,
            "member": member,
            "member_number": format_member_number(member.id),
        }

    return _render_security_dashboard(result)


@verification_bp.route("/pending-applications")
def pending_applications():
    access_redirect = require_staff_access()
    if access_redirect:
        return access_redirect

    enforce_overdue_blocks()

    pending = Verification.query.filter_by(status="pending").order_by(
        Verification.created_at.desc()
    ).all()

    for application in pending:
        application.id_document_url = get_document_url(application.id_document_path)
        library = db.session.get(Library, application.library_id)
        application.library_name = library.name if library else "Unknown library"

    return render_template(
        "verification/_pending_applications.html",
        pending=pending,
        rejection_reason_choices=REJECTION_REASONS,
    )


@verification_bp.route("/approve/<int:verification_id>", methods=["POST"])
def approve(verification_id):
    access_redirect = require_staff_access()
    if access_redirect:
        return access_redirect

    verification = Verification.query.get_or_404(verification_id)
    verification.status = "approved"
    verification.reviewed_at = db.func.now()
    verification.rejection_reasons = None
    verification.rejection_comment = None
    db.session.commit()

    member = create_member_from_verification(verification, approved=True)

    library = Library.query.get(verification.library_id)
    card = generate_virtual_card(
        member_number=format_member_number(member.id),
        full_name=f"{member.first_name} {member.last_name}",
        library_name=library.name if library else "Library",
    )

    flash("Application approved.", "success")
    return redirect(url_for("verification.dashboard"))


@verification_bp.route("/decline/<int:verification_id>", methods=["POST"])
def decline(verification_id):
    access_redirect = require_staff_access()
    if access_redirect:
        return access_redirect

    verification = Verification.query.get_or_404(verification_id)

    selected_reasons = [
        code for code in request.form.getlist("reasons")
        if code in REJECTION_REASONS
    ]
    comment = request.form.get("comment", "").strip()

    if not selected_reasons and not comment:
        flash("Please select at least one reason or add a comment for the decline.", "error")
        return redirect(url_for("verification.dashboard"))

    verification.status = "declined"
    verification.reviewed_at = db.func.now()
    verification.rejection_reasons = ",".join(selected_reasons)
    verification.rejection_comment = comment or None
    db.session.commit()

    create_member_from_verification(verification, approved=False)

    flash("Application declined. The applicant can log in to see the reason and resubmit their ID.", "info")
    return redirect(url_for("verification.dashboard"))


def require_admin():
    if session.get("role") is None:
        return redirect(url_for("auth.login"))

    if session.get("role") != "admin":
        flash("Only administrators can manage member accounts.", "error")
        return redirect(url_for("verification.dashboard"))


def _after_member_action():
    if request.form.get("return_to") == "books":
        return redirect(url_for("books.books"))
    return redirect(url_for("verification.dashboard"))


@verification_bp.route("/members/<int:member_id>/block", methods=["POST"])
def block_member(member_id):
    access_redirect = require_admin()
    if access_redirect:
        return access_redirect

    member = Member.query.filter_by(id=member_id, role="member").first_or_404()
    member.is_active = False
    if any(loan.closed_at is None and loan.is_overdue() for loan in member.loans):
        member.block_reason = OVERDUE_BLOCK
    db.session.commit()

    flash(f"{member.first_name} {member.last_name} has been blocked.", "info")
    return _after_member_action()


@verification_bp.route("/members/<int:member_id>/reactivate", methods=["POST"])
def reactivate_member(member_id):
    access_redirect = require_admin()
    if access_redirect:
        return access_redirect

    member = Member.query.filter_by(id=member_id, role="member").first_or_404()
    if not can_lift_block(member):
        flash(
            f"{member.first_name} {member.last_name} still has overdue or lost books, or unpaid fees. "
            "Return the books and record payment before lifting the block.",
            "error",
        )
        return _after_member_action()

    member.is_active = True
    member.block_reason = None
    db.session.commit()

    flash(f"{member.first_name} {member.last_name} has been reactivated.", "success")
    return _after_member_action()


@verification_bp.route("/members/<int:member_id>/delete", methods=["POST"])
def delete_member(member_id):
    access_redirect = require_admin()
    if access_redirect:
        return access_redirect

    member = Member.query.filter_by(id=member_id, role="member").first_or_404()
    member_name = f"{member.first_name} {member.last_name}"
    db.session.delete(member)
    db.session.commit()

    flash(f"{member_name} has been permanently deleted.", "info")
    return redirect(url_for("verification.dashboard"))

