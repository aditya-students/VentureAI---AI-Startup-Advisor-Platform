"""
JWT + password hashing utilities.

Two token types are issued on login:
  - access token  (short-lived, 15 min)  -> sent as HttpOnly cookie, used on every request
  - refresh token (long-lived, 7 days)   -> sent as HttpOnly cookie, used only to mint new access tokens

Both are signed with the same secret here for simplicity; in a larger system
you'd typically use separate secrets/keys per token type.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

# --- Password hashing (bcrypt) ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt before storing it."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Compare a plaintext password against the stored bcrypt hash."""
    return pwd_context.verify(plain_password, password_hash)


# --- JWT creation ---
def create_access_token(subject: str, role: str) -> str:
    """
    Create a short-lived access token.
    `subject` is the user id (as a string, per JWT `sub` convention).
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a long-lived refresh token. Carries no role claim on purpose —
    role is re-fetched from the DB when the refresh token is used, so a
    stale/rotated role can't linger for 7 days."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode + verify a token's signature and expiry. Returns None if invalid/expired."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
