"""
Pydantic schemas for the Mentor Profile feature.

MentorProfileResponse — returned by GET /mentor/profile
MentorProfileUpdate  — accepted by PUT /mentor/profile

MentorPublicCard       — public card view for Mentor Discovery
MentorPublicProfile    — public detail view for Mentor Discovery
MentorDiscoveryResponse — paginated list wrapper
"""

from typing import Optional, List

from pydantic import BaseModel, field_validator


# --- Allowed values for structured multi-select fields ---
# Extensible: simply add new entries to these lists.

ALLOWED_INDUSTRIES = [
    "SaaS", "FinTech", "HealthTech", "EdTech", "E-commerce",
    "AI/ML", "Cybersecurity", "Logistics", "CleanTech", "Consumer Tech", "Other",
]

ALLOWED_AREAS_OF_EXPERTISE = [
    "Product Strategy", "Business Strategy", "Go-To-Market", "Marketing",
    "Sales", "Fundraising", "Finance", "Operations", "Technology", "AI/ML",
    "Product-Market Fit", "Customer Discovery", "Business Model", "Legal/Compliance",
]

ALLOWED_STARTUP_STAGES = [
    "Idea Stage", "Pre-MVP", "MVP", "Early Revenue", "Growth Stage", "Scaling",
]

ALLOWED_MENTORSHIP_AREAS = [
    "Idea Validation", "Product Development", "Business Model", "Go-To-Market",
    "Fundraising", "Pitching", "Operations", "Technology", "Scaling",
]

ALLOWED_AVAILABILITY = [
    "Available", "Limited Availability", "Currently Unavailable",
]


class MentorProfileResponse(BaseModel):
    """Full profile view — includes name/email from User + profile fields."""
    id: int
    name: str
    email: str
    profile_image: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    current_role: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    years_of_experience: Optional[int] = None
    startup_experience: Optional[int] = None
    mentoring_experience: Optional[int] = None
    industries: Optional[List[str]] = None
    areas_of_expertise: Optional[List[str]] = None
    startup_stages: Optional[List[str]] = None
    mentorship_areas: Optional[List[str]] = None
    availability: Optional[str] = None
    is_discoverable: bool = True
    profile_completion: int = 0

    class Config:
        from_attributes = True


class MentorPublicCard(BaseModel):
    """Public-facing mentor card for the Founder Discovery directory.
    Explicitly excludes email, password, internal IDs, and private metadata."""
    id: int
    name: str
    profile_image: Optional[str] = None
    headline: Optional[str] = None
    current_role: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    years_of_experience: Optional[int] = None
    startup_experience: Optional[int] = None
    mentoring_experience: Optional[int] = None
    industries: Optional[List[str]] = None
    areas_of_expertise: Optional[List[str]] = None
    startup_stages: Optional[List[str]] = None
    mentorship_areas: Optional[List[str]] = None
    availability: Optional[str] = None

    class Config:
        from_attributes = True


class MentorPublicProfile(MentorPublicCard):
    """Extended public profile for the detail view — adds bio."""
    bio: Optional[str] = None


class MentorDiscoveryResponse(BaseModel):
    """Paginated response for the Mentor Discovery endpoint."""
    mentors: List[MentorPublicCard]
    total: int
    page: int
    limit: int
    total_pages: int


class MentorProfileUpdate(BaseModel):
    """Editable profile fields only. Name/email/role remain on the User model."""
    headline: Optional[str] = None
    bio: Optional[str] = None
    current_role: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    years_of_experience: Optional[int] = None
    startup_experience: Optional[int] = None
    mentoring_experience: Optional[int] = None
    industries: Optional[List[str]] = None
    areas_of_expertise: Optional[List[str]] = None
    startup_stages: Optional[List[str]] = None
    mentorship_areas: Optional[List[str]] = None
    availability: Optional[str] = None
    is_discoverable: Optional[bool] = None

    # --- Validators ---

    @field_validator("headline")
    @classmethod
    def headline_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 200:
            raise ValueError("Headline must be 200 characters or fewer.")
        return v

    @field_validator("bio")
    @classmethod
    def bio_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 2000:
            raise ValueError("Bio must be 2000 characters or fewer.")
        return v

    @field_validator("current_role")
    @classmethod
    def current_role_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 150:
            raise ValueError("Current role must be 150 characters or fewer.")
        return v

    @field_validator("company")
    @classmethod
    def company_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 200:
            raise ValueError("Company must be 200 characters or fewer.")
        return v

    @field_validator("location")
    @classmethod
    def location_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 200:
            raise ValueError("Location must be 200 characters or fewer.")
        return v

    @field_validator("years_of_experience", "startup_experience", "mentoring_experience")
    @classmethod
    def experience_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Experience cannot be negative.")
        if v is not None and v > 100:
            raise ValueError("Experience value seems unreasonably high.")
        return v

    @field_validator("industries")
    @classmethod
    def validate_industries(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        for item in v:
            if item not in ALLOWED_INDUSTRIES:
                raise ValueError(f"Invalid industry: '{item}'.")
        return v

    @field_validator("areas_of_expertise")
    @classmethod
    def validate_areas_of_expertise(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        for item in v:
            if item not in ALLOWED_AREAS_OF_EXPERTISE:
                raise ValueError(f"Invalid area of expertise: '{item}'.")
        return v

    @field_validator("startup_stages")
    @classmethod
    def validate_startup_stages(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        for item in v:
            if item not in ALLOWED_STARTUP_STAGES:
                raise ValueError(f"Invalid startup stage: '{item}'.")
        return v

    @field_validator("mentorship_areas")
    @classmethod
    def validate_mentorship_areas(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        for item in v:
            if item not in ALLOWED_MENTORSHIP_AREAS:
                raise ValueError(f"Invalid mentorship area: '{item}'.")
        return v

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_AVAILABILITY:
            raise ValueError(
                f"Availability must be one of: {', '.join(ALLOWED_AVAILABILITY)}."
            )
        return v
