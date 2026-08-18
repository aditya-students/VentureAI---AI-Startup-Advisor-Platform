"""
Pydantic schemas for AI Pitch Deck Generator request/response validation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SlideSchema(BaseModel):
    """Structured representation of a single pitch deck slide."""
    slide_number: int = Field(..., description="Slide position (1 to 13)")
    slide_type: str = Field(..., description="Semantic type identifier of the slide")
    title: str = Field(..., description="Primary slide header title")
    subtitle: str = Field(..., description="Secondary slide tagline/subtitle")
    content: str = Field(..., description="Main narrative or explanation body")
    key_points: List[str] = Field(default_factory=list, description="Bullet points or key takeaways")
    visual_type: str = Field(default="grid_cards", description="Visual component type (flow, grid, metrics, matrix, etc.)")
    visual_data: Dict[str, Any] = Field(default_factory=dict, description="Structured visual node data (steps, metrics, competitive table)")
    icon_names: List[str] = Field(default_factory=list, description="Valid Lucide icon names for the slide elements")
    source_context: Optional[str] = Field(None, description="Upstream document sources utilized (Workspace, BMC, etc.)")
    warnings: List[str] = Field(default_factory=list, description="Specific warnings or disclaimers for this slide")


class AuditWarning(BaseModel):
    """Structured Red Pen Auditor warning entry."""
    severity: str = Field(..., description="HIGH, MEDIUM, or LOW")
    slide_number: Optional[int] = Field(None, description="Target slide number affected")
    category: str = Field(..., description="Warning category e.g. Moat, Traction, Financial, ICP")
    issue: str = Field(..., description="Clear explanation of the detected contradiction or violation")
    original_claim: Optional[str] = Field(None, description="The original AI-generated claim flagged")
    recommended_fix: Optional[str] = Field(None, description="Actionable correction guidance")
    auto_fixed: bool = Field(False, description="Whether the Auditor automatically rewrote the claim")


class PitchDeckAuditReport(BaseModel):
    """Aggregated Red Pen Audit findings for the complete deck."""
    health_score: int = Field(..., description="Overall consistency health score (0 to 100)")
    warnings: List[AuditWarning] = Field(default_factory=list, description="List of auditor warnings")


class PitchDeckResponse(BaseModel):
    """Response payload for a full pitch deck version."""
    id: int
    startup_id: int
    version_number: int
    slides_data: List[SlideSchema]
    audit_report: PitchDeckAuditReport
    is_validation_mode: bool
    validation_score: Optional[float] = None
    upstream_versions: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PitchDeckHistoryItem(BaseModel):
    """Summary item for pitch deck version history list."""
    id: int
    version_number: int
    is_validation_mode: bool
    validation_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SlideEditPayload(BaseModel):
    """Founder payload for manually editing a slide."""
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str] = None
    key_points: Optional[List[str]] = None


class SlideRegeneratePayload(BaseModel):
    """Payload for triggering single slide AI regeneration."""
    custom_instructions: Optional[str] = None


class PrerequisitesStatusResponse(BaseModel):
    """Status summary of upstream feature data completeness."""
    workspace_exists: bool
    validation_exists: bool
    bmc_exists: bool
    business_plan_exists: bool
    missing_message: Optional[str] = None
