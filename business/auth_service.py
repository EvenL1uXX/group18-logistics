from werkzeug.security import check_password_hash, generate_password_hash

from data.models import Role, User


class AuthError(ValueError):
    """Raised for invalid credentials or registration input."""


def _role(db, name: str) -> Role:
    role = db.query(Role).filter_by(name=name).first()
    if role is None:
        raise AuthError(f"Unknown role: {name}")
    return role


def register(
    db,
    email: str,
    password: str,
    full_name: str,
    phone: str | None = None,
    role_name: str = "Customer",
) -> User:
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()
    if not email or "@" not in email:
        raise AuthError("A valid email address is required.")
    if len(password or "") < 6:
        raise AuthError("Password must be at least 6 characters.")
    if not full_name:
        raise AuthError("Full name is required.")
    if db.query(User).filter_by(email=email).first() is not None:
        raise AuthError("That email is already registered.")

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        full_name=full_name,
        phone=(phone or "").strip() or None,
        role=_role(db, role_name),
    )
    db.add(user)
    db.commit()
    return user


def authenticate(db, email: str, password: str) -> User | None:
    email = (email or "").strip().lower()
    user = db.query(User).filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password or ""):
        return None
    return user
