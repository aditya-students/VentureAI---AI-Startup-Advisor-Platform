"""
Mentor Profile business logic — kept separate from the router so route
handlers stay thin and this logic is independently testable.
"""

import math
from typing import Optional, List

from sqlalchemy import or_, case, func as sa_func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.users.models import MentorProfile, User, UserStatus
from app.mentor.schemas import MentorProfileUpdate, MentorPublicCard


def create_mentor_profile(db: Session, user_id: int) -> MentorProfile:
    """Create an empty mentor profile. Called during Mentor registration."""
    profile = MentorProfile(user_id=user_id)
    db.add(profile)
    return profile


def get_mentor_profile(db: Session, user_id: int) -> MentorProfile:
    """Load the mentor profile for a given user. Raises 404 if not found."""
    profile = db.query(MentorProfile).filter(MentorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentor profile not found.",
        )
    return profile


def get_or_create_mentor_profile(db: Session, user_id: int) -> MentorProfile:
    """
    Load the mentor profile, creating one if it doesn't exist yet.
    Handles edge cases where a Mentor was registered before this feature
    shipped and therefore has no profile row.
    """
    profile = db.query(MentorProfile).filter(MentorProfile.user_id == user_id).first()
    if not profile:
        profile = MentorProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def calculate_profile_completion(profile: MentorProfile) -> int:
    """
    Deterministic profile completion percentage based on 9 weighted fields.

    Each field has a fixed weight. The total always sums to 100%.
    This is stored on the model so it can be queried/sorted without
    recomputing on every read.

    Weights:
      headline           15%
      bio                15%
      current_role       10%
      industries         12%
      areas_of_expertise 12%
      startup_stages     10%
      mentorship_areas   10%
      experience          8%  (any of the three experience fields)
      availability        8%
    """
    score = 0

    if profile.headline and profile.headline.strip():
        score += 15
    if profile.bio and profile.bio.strip():
        score += 15
    if profile.current_role and profile.current_role.strip():
        score += 10
    if profile.industries and len(profile.industries) > 0:
        score += 12
    if profile.areas_of_expertise and len(profile.areas_of_expertise) > 0:
        score += 12
    if profile.startup_stages and len(profile.startup_stages) > 0:
        score += 10
    if profile.mentorship_areas and len(profile.mentorship_areas) > 0:
        score += 10
    if any([
        profile.years_of_experience is not None,
        profile.startup_experience is not None,
        profile.mentoring_experience is not None,
    ]):
        score += 8
    if profile.availability and profile.availability.strip():
        score += 8

    return score


def update_mentor_profile(
    db: Session, user_id: int, data: MentorProfileUpdate
) -> MentorProfile:
    """Update a mentor's profile fields, recalculate completion, and persist."""
    profile = get_or_create_mentor_profile(db, user_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    # Recalculate completion after applying updates
    profile.profile_completion = calculate_profile_completion(profile)

    db.commit()
    db.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# Mentor Discovery — Founder-facing directory
# ---------------------------------------------------------------------------

def discover_mentors(
    db: Session,
    search: Optional[str] = None,
    industry: Optional[List[str]] = None,
    expertise: Optional[List[str]] = None,
    startup_stage: Optional[List[str]] = None,
    availability: Optional[List[str]] = None,
    sort: str = "relevance",
    page: int = 1,
    limit: int = 12,
) -> dict:
    """
    Server-side search, filter, sort, and paginate discoverable mentors.

    Returns a dict matching MentorDiscoveryResponse fields.
    """
    query = (
        db.query(MentorProfile, User)
        .join(User, MentorProfile.user_id == User.id)
        .filter(
            MentorProfile.is_discoverable == True,  # noqa: E712
            User.status == UserStatus.ACTIVE,
        )
    )

    # --- Search ---
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(term),
                MentorProfile.headline.ilike(term),
                MentorProfile.current_role.ilike(term),
                MentorProfile.company.ilike(term),
                MentorProfile.industries.any(search.strip()),
                MentorProfile.areas_of_expertise.any(search.strip()),
                MentorProfile.mentorship_areas.any(search.strip()),
            )
        )

    # --- Filters ---
    if industry:
        query = query.filter(MentorProfile.industries.overlap(industry))

    if expertise:
        query = query.filter(MentorProfile.areas_of_expertise.overlap(expertise))

    if startup_stage:
        query = query.filter(MentorProfile.startup_stages.overlap(startup_stage))

    if availability:
        query = query.filter(MentorProfile.availability.in_(availability))
    else:
        # Default: exclude "Currently Unavailable" unless explicitly included
        query = query.filter(
            or_(
                MentorProfile.availability != "Currently Unavailable",
                MentorProfile.availability == None,  # noqa: E711
            )
        )

    # --- Total count (before pagination) ---
    total = query.count()

    # --- Sorting ---
    if sort == "experience":
        query = query.order_by(
            MentorProfile.years_of_experience.desc().nullslast(),
            MentorProfile.profile_completion.desc(),
        )
    elif sort == "availability":
        avail_order = case(
            (MentorProfile.availability == "Available", 1),
            (MentorProfile.availability == "Limited Availability", 2),
            else_=3,
        )
        query = query.order_by(
            avail_order,
            MentorProfile.profile_completion.desc(),
        )
    else:
        # "relevance" — profile completeness then experience
        query = query.order_by(
            MentorProfile.profile_completion.desc(),
            MentorProfile.years_of_experience.desc().nullslast(),
        )

    # --- Pagination ---
    offset = (page - 1) * limit
    results = query.offset(offset).limit(limit).all()
    total_pages = math.ceil(total / limit) if limit > 0 else 0

    # --- Build public card data ---
    mentors = []
    for profile, user in results:
        mentors.append(MentorPublicCard(
            id=profile.id,
            name=user.name,
            profile_image=user.profile_image,
            headline=profile.headline,
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
        ))

    return {
        "mentors": mentors,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


def get_public_mentor_by_id(db: Session, mentor_profile_id: int) -> dict:
    """
    Load a single mentor's public profile by profile ID.
    Only returns discoverable, active-user mentors. Raises 404 otherwise.
    """
    result = (
        db.query(MentorProfile, User)
        .join(User, MentorProfile.user_id == User.id)
        .filter(
            MentorProfile.id == mentor_profile_id,
            MentorProfile.is_discoverable == True,  # noqa: E712
            User.status == UserStatus.ACTIVE,
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentor not found.",
        )

    profile, user = result
    return {
        "id": profile.id,
        "name": user.name,
        "profile_image": user.profile_image,
        "headline": profile.headline,
        "bio": profile.bio,
        "current_role": profile.current_role,
        "company": profile.company,
        "location": profile.location,
        "years_of_experience": profile.years_of_experience,
        "startup_experience": profile.startup_experience,
        "mentoring_experience": profile.mentoring_experience,
        "industries": profile.industries or [],
        "areas_of_expertise": profile.areas_of_expertise or [],
        "startup_stages": profile.startup_stages or [],
        "mentorship_areas": profile.mentorship_areas or [],
        "availability": profile.availability,
    }

