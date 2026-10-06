from datetime import datetime

from app.extensions import db
from app.models import Loan, Member
from app.models.loan import LOAN_LIMIT

OVERDUE_BLOCK = "overdue"


def enforce_overdue_blocks():
    """Temporarily block every member holding a book past its due date."""
    now = datetime.utcnow()
    overdue_members = (
        Member.query.join(Loan, Loan.member_id == Member.id)
        .filter(
            Loan.closed_at.is_(None),
            Loan.due_at < now,
            Member.is_active.is_(True),
        )
        .distinct()
        .all()
    )
    for member in overdue_members:
        member.is_active = False
        member.block_reason = OVERDUE_BLOCK
    if overdue_members:
        db.session.commit()


def open_loans(member):
    return [loan for loan in member.loans if loan.closed_at is None]


def total_outstanding_fees(member, now=None):
    return sum(loan.fee_outstanding(now) for loan in member.loans)


def has_overdue_loans(member, now=None):
    return any(loan.is_overdue(now) for loan in member.loans)


def checkout_denial_reason(member):
    """Return why a member may not borrow right now, or None if they may."""
    if member.role != "member" or not member.id_verified:
        return "This membership is not verified."
    if not member.is_active:
        return "This membership is blocked."
    if has_overdue_loans(member):
        return "The member has overdue books."
    if total_outstanding_fees(member) > 0:
        return "The member has outstanding fees to pay first."
    if len(open_loans(member)) >= LOAN_LIMIT:
        return f"The member has reached the limit of {LOAN_LIMIT} books."
    return None


def can_lift_block(member):
    """A block may be lifted once books are returned and fees are paid."""
    unresolved = any(
        loan.closed_at is None and (loan.status == "lost" or loan.is_overdue())
        for loan in member.loans
    )
    return not unresolved and total_outstanding_fees(member) == 0

