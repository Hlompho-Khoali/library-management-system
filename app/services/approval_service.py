from datetime import datetime, UTC

from flask import has_app_context
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Member


def create_member_from_verification(verification, approved=True):
    """Create or update the member linked to a verification submission.

    Runs on both approval and decline so that declined applicants still get
    a login-capable account, and again whenever a declined applicant is
    re-reviewed after resubmitting their ID document.
    """

    if not has_app_context():
        raise RuntimeError("Approval service requires an active Flask application context.")

    return _create_member_from_verification(verification, approved)


def _create_member_from_verification(verification, approved):
    member = Member.query.filter_by(email=verification.email).first()

    if member is None:
        member = Member(
            title=verification.title,
            first_name=verification.first_name,
            middle_name=verification.middle_name,
            last_name=verification.last_name,
            id_number=verification.id_number,
            date_of_birth=verification.date_of_birth,
            phone_number=verification.phone_number,
            street_address=verification.street_address,
            suburb=verification.suburb,
            city=verification.city,
            postal_code=verification.postal_code,
            library_id=verification.library_id,
            email=verification.email,
            password_hash=verification.password_hash,
            is_active=True,
            role="member",
        )
        db.session.add(member)

    member.verification_id = verification.id
    member.id_document_front_path = verification.id_document_path
    member.id_document_back_path = verification.id_document_path

    if approved:
        member.id_verified = True
        member.id_verified_at = datetime.now(UTC)
        member.id_review_status = "approved"
        member.id_rejection_reasons = None
        member.id_rejection_comment = None
    else:
        member.id_verified = False
        member.id_verified_at = None
        member.id_review_status = "declined"
        member.id_rejection_reasons = verification.rejection_reasons
        member.id_rejection_comment = verification.rejection_comment

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

        member = Member.query.filter_by(email=verification.email).first()

        if member is None:
            raise

    return member
