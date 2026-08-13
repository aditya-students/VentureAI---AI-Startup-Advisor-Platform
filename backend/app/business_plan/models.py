"""
BusinessPlan database model.

Schema:

TABLE business_plans
    id, startup_id, bmc_version_id, validation_report_id, version,
    executive_summary, domains_data, audit_report,
    validation_score, is_pivot_mode, created_at, updated_at

Relationship: One Startup has many BusinessPlan versions.
"""

from sqlalchemy import (
    Column, Integer, Float, Boolean, String, DateTime, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class BusinessPlan(Base):
    """
    Stores a versioned Business Plan for a startup.

    Every full generation or section regeneration creates a new version.
    Previous versions are preserved for historical review.
    """
    __tablename__ = "business_plans"
    __table_args__ = (
        UniqueConstraint("startup_id", "version", name="uq_business_plan_startup_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    startup_id = Column(
        Integer,
        ForeignKey("startups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bmc_version_id = Column(
        Integer,
        ForeignKey("bmc_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    validation_report_id = Column(
        Integer,
        ForeignKey("idea_validations.id", ondelete="SET NULL"),
        nullable=True,
    )
    version = Column(Integer, nullable=False, default=1)

    # ---- Executive Summary (JSONB) ----
    executive_summary = Column(JSONB, nullable=False)

    # ---- Five Domains Data (JSONB) ----
    # Contains:
    # - market_customer
    # - business_model_unit_economics
    # - gtm_operations
    # - financial_structure
    # - risk_validation_legal
    domains_data = Column(JSONB, nullable=False)

    # ---- Cross-Document Audit Findings (JSONB) ----
    audit_report = Column(JSONB, nullable=False)

    # ---- Validation Context ----
    validation_score = Column(Float, nullable=True)
    is_pivot_mode = Column(Boolean, nullable=False, default=False)

    # ---- Timestamps ----
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ---- Relationships ----
    startup = relationship("Startup", backref="business_plans")
    bmc_version = relationship("BMCVersion", backref="business_plans")
    validation_report = relationship("IdeaValidation", backref="business_plans")
