"""
Pydantic schemas for the Startup Workspace feature.

StartupCreate    — accepted by POST /startups
StartupUpdate    — accepted by PUT  /startups/me
StartupStatusUpdate — accepted by PATCH /startups/me/status
StartupResponse  — returned by all startup endpoints
"""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.startup.models import StartupStage, StartupStatus


class StartupCreate(BaseModel):
    """Fields accepted when creating a startup."""
    name: str
    tagline: Optional[str] = None
    problem: str
    solution: str
    industry: Optional[str] = None
    target_market: Optional[str] = None
    stage: Optional[StartupStage] = StartupStage.IDEA

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Startup name cannot be empty.")
        if len(v.strip()) > 150:
            raise ValueError("Startup name must be 150 characters or fewer.")
        return v.strip()

    @field_validator("problem")
    @classmethod
    def problem_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Problem cannot be empty.")
        if len(v.strip()) > 2000:
            raise ValueError("Problem must be 2000 characters or fewer.")
        return v.strip()

    @field_validator("solution")
    @classmethod
    def solution_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Solution cannot be empty.")
        if len(v.strip()) > 2000:
            raise ValueError("Solution must be 2000 characters or fewer.")
        return v.strip()

    @field_validator("tagline")
    @classmethod
    def tagline_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 300:
            raise ValueError("Tagline must be 300 characters or fewer.")
        return v

    @field_validator("industry")
    @classmethod
    def industry_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 100:
            raise ValueError("Industry must be 100 characters or fewer.")
        return v

    @field_validator("target_market")
    @classmethod
    def target_market_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 200:
            raise ValueError("Target market must be 200 characters or fewer.")
        return v


class StartupUpdate(BaseModel):
    """Editable startup fields (everything except status)."""
    name: Optional[str] = None
    tagline: Optional[str] = None
    problem: Optional[str] = None
    solution: Optional[str] = None
    industry: Optional[str] = None
    target_market: Optional[str] = None
    stage: Optional[StartupStage] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Startup name cannot be empty.")
        if len(v.strip()) > 150:
            raise ValueError("Startup name must be 150 characters or fewer.")
        return v.strip()

    @field_validator("problem")
    @classmethod
    def problem_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Problem cannot be empty.")
        if len(v.strip()) > 2000:
            raise ValueError("Problem must be 2000 characters or fewer.")
        return v.strip()

    @field_validator("solution")
    @classmethod
    def solution_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Solution cannot be empty.")
        if len(v.strip()) > 2000:
            raise ValueError("Solution must be 2000 characters or fewer.")
        return v.strip()

    @field_validator("tagline")
    @classmethod
    def tagline_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 300:
            raise ValueError("Tagline must be 300 characters or fewer.")
        return v

    @field_validator("industry")
    @classmethod
    def industry_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 100:
            raise ValueError("Industry must be 100 characters or fewer.")
        return v

    @field_validator("target_market")
    @classmethod
    def target_market_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 200:
            raise ValueError("Target market must be 200 characters or fewer.")
        return v


class StartupStatusUpdate(BaseModel):
    """Used to archive or restore a startup."""
    status: StartupStatus


class StartupResponse(BaseModel):
    """Full startup view returned by all endpoints."""
    id: int
    founder_id: int
    name: str
    tagline: Optional[str] = None
    problem: str
    solution: str
    industry: Optional[str] = None
    target_market: Optional[str] = None
    stage: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
