"""
Founder Profile business logic — kept separate from the router so route
handlers stay thin and this logic is independently testable.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.users.models import FounderProfile
from app.founder.schemas import FounderProfileUpdate


def create_founder_profile(db: Session, user_id: int) -> FounderProfile:
    """Create an empty founder profile. Called during Founder registration."""
    profile = FounderProfile(user_id=user_id)
    db.add(profile)
    return profile


def get_founder_profile(db: Session, user_id: int) -> FounderProfile:
    """Load the founder profile for a given user. Raises 404 if not found."""
    profile = db.query(FounderProfile).filter(FounderProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Founder profile not found.",
        )
    return profile


def update_founder_profile(
    db: Session, user_id: int, data: FounderProfileUpdate
) -> FounderProfile:
    """Update a founder's profile fields and persist the changes."""
    profile = get_founder_profile(db, user_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile
