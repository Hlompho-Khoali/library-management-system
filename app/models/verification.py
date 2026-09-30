from datetime import datetime

from app.extensions import db


class Verification(db.Model):
    __tablename__ = "verifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Registration information
    title = db.Column(
        db.String(20),
        nullable=False
    )

    first_name = db.Column(
        db.String(100),
        nullable=False
    )

    middle_name = db.Column(
        db.String(100),
        nullable=True
    )

    last_name = db.Column(
        db.String(100),
        nullable=False
    )

    id_number = db.Column(
        db.String(13),
        nullable=False
    )

    date_of_birth = db.Column(
        db.Date,
        nullable=False
    )

    phone_number = db.Column(
        db.String(20),
        nullable=False
    )

    # Address
    street_address = db.Column(
        db.String(255),
        nullable=False
    )

    suburb = db.Column(
        db.String(100),
        nullable=False
    )

    city = db.Column(
        db.String(100),
        nullable=False
    )

    postal_code = db.Column(
        db.String(10),
        nullable=False
    )

    # Library
    library_id = db.Column(
        db.Integer,
        db.ForeignKey("libraries.id"),
        nullable=False
    )

    # Account
    email = db.Column(
        db.String(255),
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # ID document
    id_document_path = db.Column(
        db.String(500),
        nullable=False
    )

    privacy_consent_at = db.Column(
        db.DateTime,
        nullable=True
    )

    privacy_notice_version = db.Column(
        db.String(20),
        nullable=True
    )

    # Verification status
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
    )

    rejection_reason = db.Column(
        db.String(500),
        nullable=True
    )

    # Comma-separated reason codes chosen by the admin when declining
    rejection_reasons = db.Column(
        db.String(255),
        nullable=True
    )

    rejection_comment = db.Column(
        db.Text,
        nullable=True
    )

    # Timestamps
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    reviewed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    def __repr__(self):
        return f"<Verification {self.first_name} {self.last_name} - {self.status}>"