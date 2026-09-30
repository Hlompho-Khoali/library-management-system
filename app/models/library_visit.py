from datetime import datetime

from app.extensions import db


class LibraryVisit(db.Model):
    __tablename__ = "library_visits"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(
        db.Integer,
        db.ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    exit_at = db.Column(db.DateTime, nullable=True)

    member = db.relationship("Member", back_populates="library_visits")
