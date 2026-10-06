from app.routes.auth import auth_bp
from app.routes.verification import verification_bp
from app.routes.books import books_bp


__all__ = [
    "auth_bp",
    "verification_bp",
]