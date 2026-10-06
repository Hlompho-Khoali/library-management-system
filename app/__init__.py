from flask import Flask
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

from app.config import Config
from app.extensions import db, migrate, mail
from app.models import Region, Library, Member, Verification
from app.routes import auth_bp, verification_bp, books_bp
from app.services.admin_service import ensure_default_admin, ensure_default_security_officer


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    }

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    with app.app_context():
        # Skip seeding if the schema is mid-migration (e.g. running `flask db upgrade`)
        if not app.config.get("TESTING"):
            try:
                ensure_default_admin()
                ensure_default_security_officer()
            except SQLAlchemyError:
                db.session.rollback()

    app.register_blueprint(auth_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(books_bp)

    return app