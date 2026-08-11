"""
Founder Profile API routes.

  GET  /founder/profile  -> return the current founder's profile
  PUT  /founder/profile  -> update editable profile fields
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.auth.dependencies import require_role
from app.founder.schemas import FounderProfileResponse, FounderProfileUpdate
from app.founder import service

router = APIRouter(prefix="/founder", tags=["Founder Profile"])


@router.get("/profile", response_model=FounderProfileResponse)
def get_profile(
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Return the authenticated founder's profile.
    Name and email come from the User relationship — never from the profile table.
    """
    profile = service.get_founder_profile(db, current_user.id)
    return FounderProfileResponse(
        id=profile.id,
        name=current_user.name,
        email=current_user.email,
        bio=profile.bio,
        skills=profile.skills or [],
        education=profile.education,
        experience=profile.experience,
        linkedin_url=profile.linkedin_url,
    )


@router.put("/profile", response_model=FounderProfileResponse)
def update_profile(
    payload: FounderProfileUpdate,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Update editable profile fields (bio, skills, education, experience, linkedin_url).
    Name, email, and role remain on the User model and cannot be changed here.
    """
    profile = service.update_founder_profile(db, current_user.id, payload)
    return FounderProfileResponse(
        id=profile.id,
        name=current_user.name,
        email=current_user.email,
        bio=profile.bio,
        skills=profile.skills or [],
        education=profile.education,
        experience=profile.experience,
        linkedin_url=profile.linkedin_url,
    )
