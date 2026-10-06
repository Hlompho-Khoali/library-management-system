from datetime import datetime

from app.extensions import db


class Book(db.Model):
    """A single physical copy, identified by the item id on its barcode."""

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    loans = db.relationship(
        "Loan",
        back_populates="book",
        order_by="Loan.checked_out_at.desc()",
    )

    @property
    def current_loan(self):
        return next((loan for loan in self.loans if loan.closed_at is None), None)

    @property
    def status(self):
        loan = self.current_loan
        if loan is None:
            return "available"
        return "lost" if loan.status == "lost" else "borrowed"
