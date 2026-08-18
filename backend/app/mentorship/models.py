"""
Database models for the Mentorship Request system.

TABLE mentorship_requests
    id, founder_id, mentor_id, workspace_id, mentorship_area, startup_stage,
    challenge, message, status, rejection_reason, created_at, updated_at,
    responded_at

TABLE mentorships
    id, founder_id, mentor_id, request_id, workspace_id, status,
    started_at, created_at, updated_at

Relationships:
    MentorshipRequest  ->  User (founder), MentorProfile (mentor), Startup (workspace)
    Mentorship         ->  User (founder), MentorProfile (mentor), MentorshipRequest
"""

import enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class RequestStatus(str, enum.Enum):
    """Allowed statuses for a mentorship request."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class MentorshipStatus(str, enum.Enum):
    """Allowed statuses for an active mentorship relationship."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MentorshipRequest(Base):
    """
    A founder's request for mentorship from a specific mentor.

    State machine:
        PENDING  ->  ACCEPTED  (by mentor)
        PENDING  ->  REJECTED  (by mentor)
        PENDING  ->  CANCELLED (by founder)
    No other transitions are allowed.
    """
    __tablename__ = "mentorship_requests"
    __table_args__ = (
        # Performance index for duplicate-request checks
        Index(
            "ix_mentorship_requests_founder_mentor_status",
            "founder_id", "mentor_id", "status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    founder_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    mentor_id = Column(
        Integer,
        ForeignKey("mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id = Column(
        Integer,
        ForeignKey("startups.id", ondelete="SET NULL"),
        nullable=True,
    )

    mentorship_area = Column(String(100), nullable=False)
    startup_stage = Column(String(100), nullable=False)
    challenge = Column(Text, nullable=False)
    message = Column(Text, nullable=True)

    status = Column(
        Enum(RequestStatus, name="requeststatus"),
        default=RequestStatus.PENDING,
        nullable=False,
    )
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    responded_at = Column(DateTime(timezone=True), nullable=True)

    # --- Relationships ---
    founder = relationship("User", foreign_keys=[founder_id])
    mentor_profile = relationship("MentorProfile", foreign_keys=[mentor_id])
    workspace = relationship("Startup", foreign_keys=[workspace_id])


class Mentorship(Base):
    """
    An active mentorship relationship created when a request is ACCEPTED.

    The original MentorshipRequest is kept for historical evidence.
    """
    __tablename__ = "mentorships"
    __table_args__ = (
        Index(
            "ix_mentorships_founder_mentor_status",
            "founder_id", "mentor_id", "status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    founder_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    mentor_id = Column(
        Integer,
        ForeignKey("mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_id = Column(
        Integer,
        ForeignKey("mentorship_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    workspace_id = Column(
        Integer,
        ForeignKey("startups.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        Enum(MentorshipStatus, name="mentorshipstatus"),
        default=MentorshipStatus.ACTIVE,
        nullable=False,
    )
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---
    founder = relationship("User", foreign_keys=[founder_id])
    mentor_profile = relationship("MentorProfile", foreign_keys=[mentor_id])
    request = relationship("MentorshipRequest", foreign_keys=[request_id])
    workspace = relationship("Startup", foreign_keys=[workspace_id])
