"""
IdeaValidation database model.

Schema:

TABLE idea_validations
    id, startup_id, version, input_snapshot, lofa,
    agent_vc, agent_buyer, agent_competitor,
    problem_score, buyer_score, market_score, moat_score, feasibility_score,
    weighted_base_score, final_validation_score,
    vetoes, penalty_multiplier, score_tiers,
    overall_assessment, strengths, key_risks, recommended_next_steps,
    mom_test_questions, kill_threshold,
    created_at

Relationship: One Startup has many IdeaValidations (versioned).
"""

from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class IdeaValidation(Base):
    """
    Stores a single versioned idea-validation report for a startup.

    Every time the Founder clicks "Validate My Idea" (or "Re-analyze"),
    a new row is inserted with an incremented version number.
    Previous versions are never overwritten.
    """
    __tablename__ = "idea_validations"
    __table_args__ = (
        UniqueConstraint("startup_id", "version", name="uq_validation_startup_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    startup_id = Column(
        Integer,
        ForeignKey("startups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False, default=1)

    # ---- Input snapshot (frozen at validation time) ----
    input_snapshot = Column(JSONB, nullable=False)

    # ---- LOFA ----
    lofa = Column(Text, nullable=False)

    # ---- Agent outputs (structured AI output) ----
    agent_vc = Column(JSONB, nullable=False)
    agent_buyer = Column(JSONB, nullable=False)
    agent_competitor = Column(JSONB, nullable=False)

    # ---- Dimension scores (0-100) ----
    problem_score = Column(Integer, nullable=False)
    buyer_score = Column(Integer, nullable=False)
    market_score = Column(Integer, nullable=False)
    moat_score = Column(Integer, nullable=False)
    feasibility_score = Column(Integer, nullable=False)

    # ---- Calculated scores ----
    weighted_base_score = Column(Float, nullable=False)
    final_validation_score = Column(Float, nullable=False)

    # ---- Veto information ----
    vetoes = Column(JSONB, nullable=False)
    penalty_multiplier = Column(Float, nullable=False, default=1.0)

    # ---- Score tiers ----
    score_tiers = Column(JSONB, nullable=False)

    # ---- Synthesis outputs ----
    overall_assessment = Column(Text, nullable=False)
    strengths = Column(JSONB, nullable=False)
    key_risks = Column(JSONB, nullable=False)
    recommended_next_steps = Column(JSONB, nullable=False)

    # ---- Falsification blueprint ----
    mom_test_questions = Column(JSONB, nullable=False)
    kill_threshold = Column(Text, nullable=False)

    # ---- Timestamps ----
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ---- Relationships ----
    startup = relationship("Startup", backref="validations")
