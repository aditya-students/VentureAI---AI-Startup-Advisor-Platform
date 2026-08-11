"""
Auth API routes.

  POST /auth/register  -> create a Founder or Mentor account
  POST /auth/login      -> verify credentials, issue JWT cookies
  GET  /auth/me         -> return the currently logged-in user
  POST /auth/logout     -> clear auth cookies
  POST /auth/refresh    -> exchange a valid refresh token for a new access token
"""

from fastapi import APIRouter, Depends, Response, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.auth.schemas import RegisterRequest, LoginRequest, RegisterResponse, LoginResponse, UserOut
from app.auth import service
from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.dependencies import get_current_user, ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookies(response: Response, user: User) -> str:
    """
    Issue access + refresh tokens and attach them as HttpOnly cookies.
    Returns the access token so it can also be echoed in the JSON body
    (useful for clients that want it in memory too, e.g. for Authorization
    headers on non-cookie-aware requests).
    """
    access_token = create_access_token(subject=str(user.id), role=user.role.name)
    refresh_token = create_refresh_token(subject=str(user.id))

    cookie_kwargs = dict(
        httponly=True,
        secure=settings.COOKIE_SECURE,  # True in production (HTTPS only)
        samesite="lax",
        path="/",
    )

    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_kwargs,
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **cookie_kwargs,
    )
    return access_token


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = service.register_user(db, payload)
    return RegisterResponse(
        message="Account created successfully. You can now log in.",
        user=UserOut(id=user.id, name=user.name, email=user.email, role=user.role.name),
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = service.authenticate_user(db, payload.email, payload.password)
    access_token = _set_auth_cookies(response, user)
    return LoginResponse(
        access_token=access_token,
        user=UserOut(id=user.id, name=user.name, email=user.email, role=user.role.name),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role.name,
    )


@router.post("/logout")
def logout(response: Response):
    # Clearing both cookies logs the user out of the current session entirely.
    # path / samesite / httponly / secure must match the values used when the
    # cookies were originally set, otherwise the browser will not remove them.
    delete_kwargs = dict(
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(ACCESS_COOKIE_NAME, **delete_kwargs)
    response.delete_cookie(REFRESH_COOKIE_NAME, **delete_kwargs)
    return {"message": "Logged out successfully."}


@router.post("/refresh", response_model=LoginResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Uses the long-lived refresh cookie to silently issue a new access token
    once the 15-minute access token has expired, without forcing re-login.
    """
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token found.")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")

    access_token = _set_auth_cookies(response, user)
    return LoginResponse(
        access_token=access_token,
        user=UserOut(id=user.id, name=user.name, email=user.email, role=user.role.name),
    )
