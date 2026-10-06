from datetime import datetime

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.extensions import db
from app.models import Book, Loan, Member
from app.models.loan import FEE_PER_DAY, LOAN_DAYS, LOAN_LIMIT
from app.services.card_service import format_member_number
from app.services.loan_service import (
    checkout_denial_reason,
    enforce_overdue_blocks,
    open_loans,
    total_outstanding_fees,
)

books_bp = Blueprint("books", __name__, url_prefix="/verification/books")


def require_admin_access():
    member_id = session.get("member_id")
    member = db.session.get(Member, member_id) if member_id else None

    if member is None:
        return redirect(url_for("auth.login"))

    if member.role != "admin" or not member.is_active:
        flash("Only administrators can manage books.", "error")
        return redirect(url_for("auth.login"))

    session["role"] = member.role


def _find_member(raw_number):
    raw_number = (raw_number or "").strip()
    if not raw_number.isdigit():
        return None
    return Member.query.filter_by(id=int(raw_number), role="member").first()


def _back(member=None):
    if member is not None:
        return redirect(
            url_for("books.books", member_number=format_member_number(member.id))
        )
    return redirect(url_for("books.books"))


@books_bp.route("")
def books():
    access_redirect = require_admin_access()
    if access_redirect:
        return access_redirect

    enforce_overdue_blocks()

    member = None
    lookup = request.args.get("member_number", "").strip()
    if lookup:
        member = _find_member(lookup)
        if member is None:
            flash("No member is linked to that membership number.", "error")

    all_books = Book.query.order_by(Book.title, Book.item_id).all()

    owing_members = [
        m for m in Member.query.filter_by(role="member").all()
        if any(loan.closed_at is None and loan.is_overdue() for loan in m.loans)
        or total_outstanding_fees(m) > 0
        or any(loan.closed_at is None and loan.status == "lost" for loan in m.loans)
    ]

    return render_template(
        "verification/books.html",
        books=all_books,
        member=member,
        member_number=format_member_number(member.id) if member else None,
        member_loans=open_loans(member) if member else [],
        member_fees=total_outstanding_fees(member) if member else 0,
        denial_reason=checkout_denial_reason(member) if member else None,
        owing_members=owing_members,
        format_member_number=format_member_number,
        total_outstanding_fees=total_outstanding_fees,
        open_loans=open_loans,
        loan_limit=LOAN_LIMIT,
        loan_days=LOAN_DAYS,
        fee_per_day=FEE_PER_DAY,
        now=datetime.utcnow(),
    )


@books_bp.route("/add", methods=["POST"])
def add_book():
    access_redirect = require_admin_access()
    if access_redirect:
        return access_redirect

    item_id = request.form.get("item_id", "").strip()
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()

    if not item_id or not title or not author:
        flash("Item ID, title and author are all required.", "error")
    elif Book.query.filter_by(item_id=item_id).first():
        flash(f"Item ID {item_id} is already registered.", "error")
    else:
        db.session.add(Book(item_id=item_id, title=title, author=author))
        db.session.commit()
        flash(f"Added “{title}” (item {item_id}).", "success")

    return _back()


@books_bp.route("/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id):
    access_redirect = require_admin_access()
    if access_redirect:
        return access_redirect

    book = Book.query.get_or_404(book_id)
    if book.loans:
        flash("Books with a borrowing history cannot be deleted.", "error")
    else:
        db.session.delete(book)
        db.session.commit()
        flash("Book removed from the catalogue.", "info")

    return _back()


@books_bp.route("/checkout", methods=["POST"])
def checkout():
    access_redirect = require_admin_access()
    if access_redirect:
        return access_redirect

    enforce_overdue_blocks()

    member = _find_member(request.form.get("member_number"))
    if member is None:
        flash("Scan a valid membership number first.", "error")
        return _back()

    item_id = request.form.get("item_id", "").strip()
    book = Book.query.filter_by(item_id=item_id).first()

    reason = checkout_denial_reason(member)
    if reason is None and book is None:
        reason = "That item ID is not in the catalogue."
    elif reason is None and book.status != "available":
        reason = "That book is not available to borrow."

    if reason:
        flash(reason, "error")
        return _back(member)

    now = datetime.utcnow()
    db.session.add(
        Loan(
            book_id=book.id,
            member_id=member.id,
            checked_out_at=now,
            due_at=Loan.new_due_date(now),
        )
    )
    db.session.commit()

    flash(
        f"“{book.title}” checked out to {member.first_name} {member.last_name}. "
        f"Due back in {LOAN_DAYS} days.",
        "success",
    )
    return _back(member)


@books_bp.route("/return", methods=["POST"])
def return_book():
    access_redirect = require_admin_access()
    if access_redirect:
        return access_redirect

    item_id = request.form.get("item_id", "").strip()
    book = Book.query.filter_by(item_id=item_id).first()
    loan = book.current_loan if book else None

    if loan is None:
        flash("That item is not currently on loan.", "error")
        return _back()

    return _close_loan(loan, "returned")


@books_bp.route("/loans/<int:loan_id>/return", methods=["POST"])
def return_loan(loan_id):
    access_redirect = require_admin_access()
    if access_redirect:
        return access_redirect

    loan = Loan.query.get_or_404(loan_id)
    if loan.closed_at is not None:
        flash("This loan is already closed.", "error")
        return _back(loan.member)
    return _close_loan(loan, "returned")


@books_bp.route("/loans/<int:loan_id>/replaced", methods=["POST"])
def replace_lost(loan_id):
    access_redirect = require_admin_access()
    if access_redirect:
        return access_redirect

    loan = Loan.query.get_or_404(loan_id)
    if loan.status != "lost" or loan.closed_at is not None:
        flash("Only lost books can be marked as replaced.", "error")
        return _back(loan.member)
    return _close_loan(loan, "replaced")


def _close_loan(loan, status):
    loan.status = status
    loan.closed_at = datetime.utcnow()
    db.session.commit()

    owed = loan.fee_outstanding()
    message = f"“{loan.book.title}” marked as {status}."
    if owed:
        message += f" Outstanding fee: R{owed}."
    flash(message, "success")
    return _back(loan.member)


@books_bp.route("/loans/<int:loan_id>/lost", methods=["POST"])
def mark_lost(loan_id):
    access_redirect = require_admin_access()
    if access_redirect:
        return access_redirect

    loan = Loan.query.get_or_404(loan_id)
    if loan.closed_at is not None or loan.status == "lost":
        flash("This loan cannot be marked as lost.", "error")
    else:
        loan.status = "lost"
        db.session.commit()
        flash(
            "Book marked as lost. The member must replace the exact same book.",
            "info",
        )
    return _back(loan.member)


@books_bp.route("/loans/<int:loan_id>/pay", methods=["POST"])
def pay_fee(loan_id):
    access_redirect = require_admin_access()
    if access_redirect:
        return access_redirect

    loan = Loan.query.get_or_404(loan_id)
    owed = loan.fee_outstanding()
    if owed:
        loan.fee_paid = loan.fee_total()
        db.session.commit()
        flash(f"Payment of R{owed} recorded.", "success")
    return _back(loan.member)
