"""
Mentor Profile + Mentor Discovery API routes.

  GET  /mentor/profile              -> return the current mentor's profile  (Mentor only)
  PUT  /mentor/profile              -> update editable profile fields       (Mentor only)
  GET  /mentor/discover             -> paginated mentor discovery directory (Founder only)
  GET  /mentor/discover/{mentor_id} -> single mentor public profile        (Founder only)
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.auth.dependencies import require_role
from app.mentor.schemas import (
    MentorProfileResponse,
    MentorProfileUpdate,
    MentorDiscoveryResponse,
    MentorPublicProfile,
)
from app.mentor import service

router = APIRouter(prefix="/mentor", tags=["Mentor"])


# -----------------------------------------------------------------------
# Mentor-only profile management
# -----------------------------------------------------------------------

@router.get("/profile", response_model=MentorProfileResponse)
def get_profile(
    current_user: User = Depends(require_role("Mentor")),
    db: Session = Depends(get_db),
):
    """
    Return the authenticated mentor's profile.
    Name and email come from the User relationship — never from the profile table.
    Auto-creates the profile if it doesn't exist (backward compat).
    """
    profile = service.get_or_create_mentor_profile(db, current_user.id)
    return MentorProfileResponse(
        id=profile.id,
        name=current_user.name,
        email=current_user.email,
        profile_image=current_user.profile_image,
        headline=profile.headline,
        bio=profile.bio,
        current_role=profile.current_role,
        company=profile.company,
        location=profile.location,
        years_of_experience=profile.years_of_experience,
        startup_experience=profile.startup_experience,
        mentoring_experience=profile.mentoring_experience,
        industries=profile.industries or [],
        areas_of_expertise=profile.areas_of_expertise or [],
        startup_stages=profile.startup_stages or [],
        mentorship_areas=profile.mentorship_areas or [],
        availability=profile.availability,
        is_discoverable=profile.is_discoverable,
        profile_completion=profile.profile_completion,
    )


@router.put("/profile", response_model=MentorProfileResponse)
def update_profile(
    payload: MentorProfileUpdate,
    current_user: User = Depends(require_role("Mentor")),
    db: Session = Depends(get_db),
):
    """
    Update editable profile fields.
    Name, email, and role remain on the User model and cannot be changed here.
    user_id is taken from the authenticated session, never from the request body.
    """
    profile = service.update_mentor_profile(db, current_user.id, payload)
    return MentorProfileResponse(
        id=profile.id,
        name=current_user.name,
        email=current_user.email,
        profile_image=current_user.profile_image,
        headline=profile.headline,
        bio=profile.bio,
        current_role=profile.current_role,
        company=profile.company,
        location=profile.location,
        years_of_experience=profile.years_of_experience,
        startup_experience=profile.startup_experience,
        mentoring_experience=profile.mentoring_experience,
        industries=profile.industries or [],
        areas_of_expertise=profile.areas_of_expertise or [],
        startup_stages=profile.startup_stages or [],
        mentorship_areas=profile.mentorship_areas or [],
        availability=profile.availability,
        is_discoverable=profile.is_discoverable,
        profile_completion=profile.profile_completion,
    )


# -----------------------------------------------------------------------
# Founder-facing Mentor Discovery
# -----------------------------------------------------------------------

@router.get("/discover", response_model=MentorDiscoveryResponse)
def discover_mentors(
    search: Optional[str] = Query(None, description="Search by name, headline, role, industry, expertise"),
    industry: Optional[List[str]] = Query(None, description="Filter by industries"),
    expertise: Optional[List[str]] = Query(None, description="Filter by areas of expertise"),
    startup_stage: Optional[List[str]] = Query(None, description="Filter by startup stages"),
    availability: Optional[List[str]] = Query(None, description="Filter by availability"),
    sort: str = Query("relevance", description="Sort by: relevance, experience, availability"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(12, ge=1, le=50, description="Results per page"),
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Paginated mentor directory for founders.
    Returns only discoverable mentors with public-safe fields.
    """
    return service.discover_mentors(
        db=db,
        search=search,
        industry=industry,
        expertise=expertise,
        startup_stage=startup_stage,
        availability=availability,
        sort=sort,
        page=page,
        limit=limit,
    )


@router.get("/discover/{mentor_id}", response_model=MentorPublicProfile)
def get_mentor_public_profile(
    mentor_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Return a single mentor's public profile for a founder to view.
    Only returns discoverable, active-user mentors.
    No email, password, or internal fields are exposed.
    """
    return service.get_public_mentor_by_id(db, mentor_id)

