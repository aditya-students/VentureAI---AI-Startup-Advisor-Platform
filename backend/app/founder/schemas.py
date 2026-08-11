"""
Pydantic schemas for the Founder Profile feature.

FounderProfileResponse — returned by GET /founder/profile
FounderProfileUpdate  — accepted by PUT /founder/profile
"""

import re
from typing import Optional, List

from pydantic import BaseModel, field_validator


class FounderProfileResponse(BaseModel):
    """Full profile view — includes name/email from User + profile fields."""
    id: int
    name: str
    email: str
    bio: Optional[str] = None
    skills: Optional[List[str]] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    linkedin_url: Optional[str] = None

    class Config:
        from_attributes = True


class FounderProfileUpdate(BaseModel):
    """Editable profile fields only. Name/email/role remain on the User model."""
    bio: Optional[str] = None
    skills: Optional[List[str]] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    linkedin_url: Optional[str] = None

    @field_validator("bio")
    @classmethod
    def bio_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 1000:
            raise ValueError("Bio must be 1000 characters or fewer.")
        return v

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("You can add up to 20 skills.")
        cleaned = []
        seen = set()
        for skill in v:
            s = skill.strip()
            if not s:
                raise ValueError("Skill cannot be empty.")
            if len(s) > 50:
                raise ValueError(f"Skill '{s[:20]}…' is too long (max 50 characters).")
            lower = s.lower()
            if lower in seen:
                raise ValueError(f"Duplicate skill: '{s}'.")
            seen.add(lower)
            cleaned.append(s)
        return cleaned

    @field_validator("education")
    @classmethod
    def education_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 500:
            raise ValueError("Education must be 500 characters or fewer.")
        return v

    @field_validator("experience")
    @classmethod
    def experience_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 500:
            raise ValueError("Experience must be 500 characters or fewer.")
        return v

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        v = v.strip()
        # Accept common LinkedIn profile URL patterns.
        pattern = r"^https?://(www\.)?linkedin\.com/.*$"
        if not re.match(pattern, v, re.IGNORECASE):
            raise ValueError("Please enter a valid LinkedIn URL (e.g. https://linkedin.com/in/yourname).")
        if len(v) > 500:
            raise ValueError("LinkedIn URL is too long.")
        return v
