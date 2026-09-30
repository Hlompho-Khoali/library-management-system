from datetime import datetime

from werkzeug.security import generate_password_hash

from app.config import Config
from app.extensions import db
from app.models import Member, Library, Region


def ensure_default_admin():
    email = Config.ADMIN_EMAIL
    admin = Member.query.filter_by(email=email).first()

    if admin is not None:
        return admin

    region = Region.query.filter_by(name="Head Office").first()
    if region is None:
        region = Region(name="Head Office")
        db.session.add(region)
        db.session.flush()

    library = Library.query.filter_by(name="Administration Library").first()
    if library is None:
        library = Library(name="Administration Library", region_id=region.id)
        db.session.add(library)
        db.session.flush()

    admin = Member(
        title="Mr",
        first_name="System",
        middle_name="",
        last_name="Administrator",
        id_number="0000000000000",
        date_of_birth=datetime.strptime("2000-01-01", "%Y-%m-%d").date(),
        phone_number="0000000000",
        street_address="Administration Office",
        suburb="Head Office",
        city="Pretoria",
        postal_code="0000",
        library_id=library.id,
        email=email,
        password_hash=generate_password_hash(Config.ADMIN_PASSWORD),
        is_active=True,
        role="admin",
        id_verified=True,
    )

    db.session.add(admin)
    db.session.commit()

    return admin


def ensure_default_security_officer():
    email = Config.SECURITY_EMAIL
    officer = Member.query.filter_by(email=email).first()

    if officer is not None:
        return officer

    region = Region.query.filter_by(name="Head Office").first()
    if region is None:
        region = Region(name="Head Office")
        db.session.add(region)
        db.session.flush()

    library = Library.query.filter_by(name="Administration Library").first()
    if library is None:
        library = Library(name="Administration Library", region_id=region.id)
        db.session.add(library)
        db.session.flush()

    officer = Member(
        title="Mr",
        first_name="Security",
        middle_name="",
        last_name="Officer",
        id_number="0000000000001",
        date_of_birth=datetime.strptime("2000-01-01", "%Y-%m-%d").date(),
        phone_number="0000000001",
        street_address="Administration Office",
        suburb="Head Office",
        city="Pretoria",
        postal_code="0000",
        library_id=library.id,
        email=email,
        password_hash=generate_password_hash(Config.SECURITY_PASSWORD),
        is_active=True,
        role="security_officer",
        id_verified=True,
    )

    db.session.add(officer)
    db.session.commit()
    return officer
