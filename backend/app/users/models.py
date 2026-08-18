"""
Database models: Role and User.

Schema (matches the spec):

TABLE roles
    id, name, description
    Seed data: 1=Founder, 2=Mentor, 3=Admin

TABLE users
    id, name, email, password_hash, role_id, profile_image, status,
    created_at, updated_at

Relationship: One Role has many Users.
"""

import enum

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class RoleName(str, enum.Enum):
    """Fixed set of role names. Kept as an enum so application code
    (RBAC checks, registration validation) can't typo a role string."""
    FOUNDER = "Founder"
    MENTOR = "Mentor"
    ADMIN = "Admin"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    # One Role -> many Users
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash, never plaintext
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    profile_image = Column(String(500), nullable=True)
    status = Column(
        Enum(UserStatus, name="user_status"),
        default=UserStatus.ACTIVE,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    role = relationship("Role", back_populates="users")
    founder_profile = relationship("FounderProfile", back_populates="user", uselist=False)
    mentor_profile = relationship("MentorProfile", back_populates="user", uselist=False)
    startup = relationship("Startup", back_populates="founder", uselist=False)


class FounderProfile(Base):
    """
    Professional profile for users with the Founder role.

    One-to-one with User. Created automatically during Founder registration.
    Name and email are read from the related User — never duplicated here.
    """
    __tablename__ = "founder_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_founder_profiles_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bio = Column(Text, nullable=True)
    skills = Column(ARRAY(String), nullable=True, default=[])
    education = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="founder_profile")


class MentorProfile(Base):
    """
    Professional profile for users with the Mentor role.

    One-to-one with User. Created automatically during Mentor registration.
    Name and email are read from the related User — never duplicated here.

    Structured fields (industries, areas_of_expertise, startup_stages,
    mentorship_areas) are stored as PostgreSQL ARRAY columns for efficient
    querying by the future AI Mentor Matching engine.
    """
    __tablename__ = "mentor_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_mentor_profiles_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # --- Basic professional information ---
    headline = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    current_role = Column(String(150), nullable=True)
    company = Column(String(200), nullable=True)
    location = Column(String(200), nullable=True)

    # --- Experience (numeric, for AI matching) ---
    years_of_experience = Column(Integer, nullable=True)
    startup_experience = Column(Integer, nullable=True)
    mentoring_experience = Column(Integer, nullable=True)

    # --- Structured multi-select fields (AI matching) ---
    industries = Column(ARRAY(String), nullable=True, default=[])
    areas_of_expertise = Column(ARRAY(String), nullable=True, default=[])
    startup_stages = Column(ARRAY(String), nullable=True, default=[])
    mentorship_areas = Column(ARRAY(String), nullable=True, default=[])

    # --- Availability ---
    availability = Column(String(50), nullable=True, default="Available")

    # --- Discoverability (controls visibility in Founder Mentor Directory) ---
    is_discoverable = Column(Boolean, nullable=False, default=True, server_default='true')

    # --- Profile completeness (computed on save) ---
    profile_completion = Column(Integer, nullable=False, default=0)

    # --- Timestamps ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="mentor_profile")
