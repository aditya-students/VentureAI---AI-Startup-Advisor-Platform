"""
Reusable FastAPI dependencies for authentication + authorization.

- get_current_user : reads the access token cookie, validates it, loads the user
- require_role(...) : dependency factory for RBAC — protects a route to specific roles
"""

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.auth.jwt import decode_token

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Reads the `access_token` HttpOnly cookie, verifies it, and loads the
    corresponding user from the DB. Raises 401 if missing/invalid/expired,
    or if the user no longer exists (e.g. deleted after the token was issued).
    """
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
        )

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
        )
    return user


def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.get("/admin/dashboard")
        def admin_dashboard(user: User = Depends(require_role("Admin"))):
            ...

    A Founder hitting an Admin-only route gets a 403, matching the spec.
    """

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return user

    return _checker
