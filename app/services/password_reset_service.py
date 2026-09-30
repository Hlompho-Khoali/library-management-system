from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app
from flask_mail import Message

from app.extensions import mail


RESET_SALT = "password-reset"


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_reset_token(member):
    """Sign a token tied to the member's ID and current password hash.

    Including the password hash means the token stops working as soon as
    the password is changed, so a used or leaked token cannot be replayed.
    """

    payload = {"member_id": member.id, "password_hash": member.password_hash}
    return _serializer().dumps(payload, salt=RESET_SALT)


def decode_reset_token(token):
    """Return the token payload, or None if it is invalid or expired."""

    max_age = current_app.config["PASSWORD_RESET_MAX_AGE_SECONDS"]

    try:
        return _serializer().loads(token, salt=RESET_SALT, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def is_token_valid_for_member(payload, member):
    return (
        payload is not None
        and member is not None
        and payload.get("member_id") == member.id
        and payload.get("password_hash") == member.password_hash
    )


def send_password_reset_email(member, reset_url):
    message = Message(
        subject="Reset your library account password",
        recipients=[member.email],
        body=(
            f"Hello {member.first_name},\n\n"
            "A password reset was requested for your library account.\n"
            f"Use the link below to choose a new password. This link expires shortly and can only be used once.\n\n"
            f"{reset_url}\n\n"
            "If you did not request this, you can safely ignore this email."
        ),
    )
    mail.send(message)
