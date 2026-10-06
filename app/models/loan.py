import math
from datetime import datetime, timedelta

from app.extensions import db

LOAN_LIMIT = 6
LOAN_DAYS = 14
FEE_PER_DAY = 2


class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(
        db.Integer, db.ForeignKey("books.id"), nullable=False, index=True
    )
    member_id = db.Column(
        db.Integer, db.ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    checked_out_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_at = db.Column(db.DateTime, nullable=False)

    # "borrowed" or "lost" while open; "returned" or "replaced" once closed
    status = db.Column(db.String(20), nullable=False, default="borrowed")
    closed_at = db.Column(db.DateTime, nullable=True)
    fee_paid = db.Column(db.Integer, nullable=False, default=0)

    book = db.relationship("Book", back_populates="loans")
    member = db.relationship("Member", back_populates="loans")

    @staticmethod
    def new_due_date(start=None):
        return (start or datetime.utcnow()) + timedelta(days=LOAN_DAYS)

    def days_overdue(self, now=None):
        end = self.closed_at or now or datetime.utcnow()
        if end <= self.due_at:
            return 0
        return math.ceil((end - self.due_at).total_seconds() / 86400)

    def fee_total(self, now=None):
        return self.days_overdue(now) * FEE_PER_DAY

    def fee_outstanding(self, now=None):
        return max(0, self.fee_total(now) - self.fee_paid)

    def is_overdue(self, now=None):
        return self.closed_at is None and (now or datetime.utcnow()) > self.due_at
