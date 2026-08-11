"""
Startup database model.

Schema:

TABLE startups
    id, founder_id, name, tagline, problem, solution, industry,
    target_market, stage, status, created_at, updated_at

Relationship: One User (Founder) has one Startup.
"""

import enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class StartupStage(str, enum.Enum):
    """Controlled startup maturity stages."""
    IDEA = "Idea"
    PROTOTYPE = "Prototype"
    MVP = "MVP"
    EARLY_TRACTION = "Early Traction"
    GROWTH = "Growth"


class StartupStatus(str, enum.Enum):
    """Workspace state — separate from stage."""
    ACTIVE = "Active"
    ARCHIVED = "Archived"


class Startup(Base):
    __tablename__ = "startups"
    __table_args__ = (
        UniqueConstraint("founder_id", name="uq_startups_founder_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    founder_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(150), nullable=False)
    tagline = Column(String(300), nullable=True)
    problem = Column(Text, nullable=False)
    solution = Column(Text, nullable=False)
    industry = Column(String(100), nullable=True)
    target_market = Column(String(200), nullable=True)
    stage = Column(
        Enum(StartupStage, name="startupstage"),
        default=StartupStage.IDEA,
        nullable=False,
    )
    status = Column(
        Enum(StartupStatus, name="startupstatus"),
        default=StartupStatus.ACTIVE,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    founder = relationship("User", back_populates="startup")
