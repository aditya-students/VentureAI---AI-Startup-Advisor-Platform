"""
BMC database model.

Schema:

TABLE bmc_versions
    id, startup_id, version, canvas_data, audit_data,
    validation_score, generation_mode, created_at, updated_at

Relationship: One Startup has many BMC versions.
"""

from sqlalchemy import (
    Column, Integer, Float, String, DateTime, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class BMCVersion(Base):
    """
    Stores a versioned Business Model Canvas for a startup.

    Every full generation or single-block regeneration creates a new version.
    Previous versions are preserved for historical review.
    """
    __tablename__ = "bmc_versions"
    __table_args__ = (
        UniqueConstraint("startup_id", "version", name="uq_bmc_startup_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    startup_id = Column(
        Integer,
        ForeignKey("startups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False, default=1)

    # ---- Canvas 9-block data (JSONB) ----
    canvas_data = Column(JSONB, nullable=False)

    # ---- Audit findings (JSONB) ----
    audit_data = Column(JSONB, nullable=False)

    # ---- Validation score context ----
    validation_score = Column(Float, nullable=True)

    # ---- Generation Mode ("STANDARD" | "PIVOT_AWARE") ----
    generation_mode = Column(String(50), nullable=False, default="STANDARD")

    # ---- Timestamps ----
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ---- Relationships ----
    startup = relationship("Startup", backref="bmc_versions")
