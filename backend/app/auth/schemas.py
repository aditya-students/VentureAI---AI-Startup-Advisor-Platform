"""
Pydantic schemas for the auth module — request validation and response shapes.
"""

import re

from pydantic import BaseModel, EmailStr, field_validator

from app.users.models import RoleName

# Public registration may only create Founder or Mentor accounts.
# Admin accounts are provisioned separately (DB seed / internal tooling).
PUBLIC_ROLES = {RoleName.FOUNDER.value, RoleName.MENTOR.value}

PASSWORD_RULES = (
    r"(?=.*[a-z])"      # at least one lowercase
    r"(?=.*[A-Z])"      # at least one uppercase
    r"(?=.*\d)"         # at least one digit
    r"(?=.*[^\w\s])"    # at least one special character
)


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty.")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(PASSWORD_RULES, v):
            raise ValueError(
                "Password must include an uppercase letter, a lowercase letter, "
                "a number, and a special character."
            )
        return v

    @field_validator("role")
    @classmethod
    def role_must_be_public(cls, v: str) -> str:
        # Blocks anyone from registering as Admin through the public API,
        # regardless of what the frontend sends.
        if v not in PUBLIC_ROLES:
            raise ValueError("Role must be either 'Founder' or 'Mentor'.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    message: str
    user: UserOut


class LoginResponse(BaseModel):
    """
    Note: the actual JWT is set as an HttpOnly cookie, not returned in the
    body. The body still echoes back token metadata + user info so the
    frontend can update UI state immediately without decoding the cookie.
    """
    access_token: str
    token_type: str = "bearer"
    user: UserOut
