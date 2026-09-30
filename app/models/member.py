from datetime import datetime

from app.extensions import db


class Member(db.Model):
    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("members.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    is_child = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    parent = db.relationship(
        "Member",
        back_populates="children",
        remote_side=[id],
        foreign_keys=[parent_id],
    )

    children = db.relationship(
        "Member",
        back_populates="parent",
        foreign_keys=[parent_id],
        passive_deletes=True,
    )

    # Personal information
    title = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=False)
    id_number = db.Column(db.String(13), nullable=False, unique=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)

    # Address
    street_address = db.Column(db.String(255), nullable=False)
    suburb = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(10), nullable=False)

    # Registration library
    library_id = db.Column(
        db.Integer,
        db.ForeignKey("libraries.id"),
        nullable=False
    )

    library = db.relationship(
        "Library",
        back_populates="members"
    )

    library_visits = db.relationship(
        "LibraryVisit",
        back_populates="member",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Account information
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    role = db.Column(
        db.String(30),
        nullable=False,
        default="member"
    )

    # ID verification
    id_verified = db.Column(db.Boolean, nullable=False, default=False)
    id_verified_at = db.Column(db.DateTime, nullable=True)

    # Tracks the outcome of the most recent ID review:
    # "approved", "declined", or "pending" (resubmitted, awaiting re-review)
    id_review_status = db.Column(
        db.String(20),
        nullable=False,
        default="approved"
    )

    id_rejection_reasons = db.Column(
        db.String(255),
        nullable=True
    )

    id_rejection_comment = db.Column(
        db.Text,
        nullable=True
    )

    # Links back to the originating verification submission so that
    # resubmitted ID documents can be re-reviewed by an admin
    verification_id = db.Column(
        db.Integer,
        db.ForeignKey("verifications.id"),
        nullable=True
    )

    # ID document information
    id_document_front_path = db.Column(
        db.String(500),
        nullable=True
    )

    id_document_back_path = db.Column(
        db.String(500),
        nullable=True
    )

    # System timestamps
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Member {self.first_name} {self.last_name}>"