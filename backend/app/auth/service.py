"""
Auth business logic — kept separate from the router so route handlers
stay thin (just request/response wiring) and this logic is unit-testable
without spinning up FastAPI.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.users.models import User, Role, RoleName
from app.auth.schemas import RegisterRequest
from app.auth.jwt import hash_password, verify_password
from app.founder.service import create_founder_profile


def get_role_by_name(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        # Only happens if the `roles` table wasn't seeded — a setup error, not a user error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Role '{role_name}' is not configured. Run the role seed script.",
        )
    return role


def register_user(db: Session, payload: RegisterRequest) -> User:
    """
    Create a new user account.
    1. Reject duplicate emails
    2. Hash the password (never store plaintext)
    3. Look up the role row (Founder/Mentor only — enforced in the schema validator)
    4. Persist and return the new user
    5. If the role is Founder, create an empty FounderProfile in the same transaction
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    role = get_role_by_name(db, payload.role)

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=role.id,
    )
    db.add(user)
    db.flush()  # assigns user.id so the FK is available for FounderProfile

    # Founders get an empty profile record at registration.
    if payload.role == RoleName.FOUNDER.value:
        create_founder_profile(db, user.id)

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Verify credentials for login.
    Raises 401 for both "no such user" and "wrong password" — deliberately
    identical errors so the API doesn't leak which emails are registered.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    return user
