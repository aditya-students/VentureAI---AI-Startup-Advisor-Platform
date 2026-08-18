"""
Pydantic schemas for the Mentorship Request feature.

Reuses ALLOWED_MENTORSHIP_AREAS and ALLOWED_STARTUP_STAGES from the
mentor module — no duplicate constant definitions.
"""

from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.mentor.schemas import ALLOWED_MENTORSHIP_AREAS, ALLOWED_STARTUP_STAGES


# ---------------------------------------------------------------------------
# Request creation (Founder submits)
# ---------------------------------------------------------------------------

class MentorshipRequestCreate(BaseModel):
    """Fields accepted when a founder creates a mentorship request."""
    mentor_id: int
    mentorship_area: str
    startup_stage: str
    challenge: str
    message: Optional[str] = None

    @field_validator("mentorship_area")
    @classmethod
    def validate_mentorship_area(cls, v: str) -> str:
        if v not in ALLOWED_MENTORSHIP_AREAS:
            raise ValueError(
                f"Invalid mentorship area: '{v}'. "
                f"Must be one of: {', '.join(ALLOWED_MENTORSHIP_AREAS)}."
            )
        return v

    @field_validator("startup_stage")
    @classmethod
    def validate_startup_stage(cls, v: str) -> str:
        if v not in ALLOWED_STARTUP_STAGES:
            raise ValueError(
                f"Invalid startup stage: '{v}'. "
                f"Must be one of: {', '.join(ALLOWED_STARTUP_STAGES)}."
            )
        return v

    @field_validator("challenge")
    @classmethod
    def validate_challenge(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 20:
            raise ValueError("Challenge must be at least 20 characters.")
        if len(stripped) > 1000:
            raise ValueError("Challenge must be 1000 characters or fewer.")
        return stripped

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            return None
        if len(stripped) > 1000:
            raise ValueError("Message must be 1000 characters or fewer.")
        return stripped


# ---------------------------------------------------------------------------
# Rejection payload
# ---------------------------------------------------------------------------

class MentorshipRequestReject(BaseModel):
    """Optional rejection reason when a mentor rejects a request."""
    rejection_reason: Optional[str] = None

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            return None
        if len(stripped) > 500:
            raise ValueError("Rejection reason must be 500 characters or fewer.")
        return stripped


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class MentorBrief(BaseModel):
    """Minimal mentor info for embedding in request cards."""
    id: int
    name: str
    profile_image: Optional[str] = None
    headline: Optional[str] = None
    company: Optional[str] = None
    availability: Optional[str] = None


class FounderBrief(BaseModel):
    """Minimal founder info for embedding in request cards (mentor view)."""
    id: int
    name: str
    profile_image: Optional[str] = None


class StartupBrief(BaseModel):
    """Minimal startup info for embedding in request cards."""
    id: int
    name: str
    industry: Optional[str] = None
    stage: str


class MentorshipRequestResponse(BaseModel):
    """Full request view returned by detail endpoint."""
    id: int
    founder: FounderBrief
    mentor: MentorBrief
    startup: Optional[StartupBrief] = None
    mentorship_area: str
    startup_stage: str
    challenge: str
    message: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    responded_at: Optional[datetime] = None


class MentorshipRequestFounderCard(BaseModel):
    """Card view for the founder's 'My Requests' list."""
    id: int
    mentor: MentorBrief
    mentorship_area: str
    startup_stage: str
    status: str
    created_at: datetime
    responded_at: Optional[datetime] = None


class MentorshipRequestMentorCard(BaseModel):
    """Card view for the mentor's incoming requests list."""
    id: int
    founder: FounderBrief
    startup: Optional[StartupBrief] = None
    mentorship_area: str
    startup_stage: str
    status: str
    created_at: datetime


class MentorshipRequestListResponse(BaseModel):
    """Paginated list wrapper."""
    requests: list
    total: int
    page: int
    limit: int
    total_pages: int


class MentorshipCheckResponse(BaseModel):
    """Quick status check for a founder/mentor pair."""
    has_pending_request: bool = False
    has_active_mentorship: bool = False
    pending_request_id: Optional[int] = None
    mentorship_id: Optional[int] = None
