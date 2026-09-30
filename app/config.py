import os
from datetime import timedelta


class Config:

    SECRET_KEY = os.getenv("SECRET_KEY", "library-dev-secret")

    PERMANENT_SESSION_LIFETIME = timedelta(
        days=int(os.getenv("SESSION_LIFETIME_DAYS", "7"))
    )

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SUPABASE_URL = os.getenv("SUPABASE_URL")

    SUPABASE_SERVICE_ROLE_KEY = os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY"
    )

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@library.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin12345")
    SECURITY_EMAIL = os.getenv("SECURITY_EMAIL", "security@library.local")
    SECURITY_PASSWORD = os.getenv("SECURITY_PASSWORD", "Security12345")

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    PASSWORD_RESET_MAX_AGE_SECONDS = int(
        os.getenv("PASSWORD_RESET_MAX_AGE_SECONDS", str(30 * 60))
    )