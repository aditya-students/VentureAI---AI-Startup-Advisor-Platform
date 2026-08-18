"""
PitchDeck database model.

Schema:

TABLE pitch_decks
    id, startup_id, validation_report_id, bmc_version_id, business_plan_id,
    version_number, slides_data, audit_report, is_validation_mode,
    validation_score, created_at, updated_at

Relationship: One Startup has many PitchDeck versions.
"""

from sqlalchemy import (
    Column, Integer, Float, Boolean, String, DateTime, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class PitchDeck(Base):
    """
    Stores a versioned 13-slide Pitch Deck for a startup.

    Every full generation or single slide regeneration saves a versioned record.
    Previous versions are preserved for historical review and rollback.
    """
    __tablename__ = "pitch_decks"
    __table_args__ = (
        UniqueConstraint("startup_id", "version_number", name="uq_pitch_deck_startup_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    startup_id = Column(
        Integer,
        ForeignKey("startups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    validation_report_id = Column(
        Integer,
        ForeignKey("idea_validations.id", ondelete="SET NULL"),
        nullable=True,
    )
    bmc_version_id = Column(
        Integer,
        ForeignKey("bmc_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    business_plan_id = Column(
        Integer,
        ForeignKey("business_plans.id", ondelete="SET NULL"),
        nullable=True,
    )

    version_number = Column(Integer, nullable=False, default=1)

    # ---- Structured 13 Slides Data (JSONB) ----
    slides_data = Column(JSONB, nullable=False)

    # ---- Red Pen Auditor Report (JSONB) ----
    audit_report = Column(JSONB, nullable=False)

    # ---- Validation Context Flags ----
    is_validation_mode = Column(Boolean, nullable=False, default=False)
    validation_score = Column(Float, nullable=True)

    # ---- Timestamps ----
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ---- Relationships ----
    startup = relationship("Startup", backref="pitch_decks")
    validation_report = relationship("IdeaValidation", backref="pitch_decks")
    bmc_version = relationship("BMCVersion", backref="pitch_decks")
    business_plan = relationship("BusinessPlan", backref="pitch_decks")
