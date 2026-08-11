"""
Pydantic schemas for the Idea Validation feature.

Response models for the validation report, history, and delta.
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Agent critique schemas
# ---------------------------------------------------------------------------

class VCCritique(BaseModel):
    tam_assessment: str = ""
    platform_risk: str = ""
    venture_verdict: str = ""
    market_assessment: str = ""
    feasibility_assessment: str = ""


class BuyerCritique(BaseModel):
    buying_objection: str = ""
    status_quo_trap: str = ""
    buyer_verdict: str = ""
    problem_assessment: str = ""
    buyer_assessment: str = ""


class CompetitorCritique(BaseModel):
    primary_incumbent_threat: str = ""
    moat_vulnerability: str = ""
    competitor_verdict: str = ""
    defensibility_assessment: str = ""


# ---------------------------------------------------------------------------
# Veto detail
# ---------------------------------------------------------------------------

class VetoDetail(BaseModel):
    no_urgent_pain: bool = False
    capped_market: bool = False
    high_incumbent_risk: bool = False


class TriggeredVeto(BaseModel):
    key: str
    label: str
    penalty: float


# ---------------------------------------------------------------------------
# Score breakdown
# ---------------------------------------------------------------------------

class ScoreBreakdown(BaseModel):
    problem_score: int
    buyer_score: int
    market_score: int
    moat_score: int
    feasibility_score: int
    weighted_base_score: float
    final_validation_score: float


class ScoreTiers(BaseModel):
    problem: str = ""
    buyer: str = ""
    market: str = ""
    moat: str = ""
    feasibility: str = ""


# ---------------------------------------------------------------------------
# Falsification blueprint
# ---------------------------------------------------------------------------

class FalsificationBlueprint(BaseModel):
    mom_test_questions: list[str] = []
    kill_threshold: str = ""


# ---------------------------------------------------------------------------
# Agent analysis (grouped)
# ---------------------------------------------------------------------------

class AgentAnalysis(BaseModel):
    vc: dict = {}
    buyer: dict = {}
    competitor: dict = {}


# ---------------------------------------------------------------------------
# Delta comparison
# ---------------------------------------------------------------------------

class DimensionDelta(BaseModel):
    dimension: str
    previous: int
    current: int
    change: int


class ValidationDelta(BaseModel):
    previous_version: int
    current_version: int
    score_change: float
    dimension_deltas: list[DimensionDelta] = []


# ---------------------------------------------------------------------------
# Full validation report response
# ---------------------------------------------------------------------------

class ValidationReportResponse(BaseModel):
    """Full validation report returned by the API."""
    validation_id: int
    startup_id: int
    version: int

    lofa: str

    scores: ScoreBreakdown
    score_tiers: ScoreTiers

    vetoes: VetoDetail
    penalty_multiplier: float
    triggered_vetoes: list[TriggeredVeto] = []

    agent_analysis: AgentAnalysis

    overall_assessment: str
    strengths: list[str] = []
    key_risks: list[str] = []
    recommended_next_steps: list[str] = []

    falsification_blueprint: FalsificationBlueprint

    created_at: datetime

    # Optional delta (included when a previous version exists)
    delta: Optional[ValidationDelta] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# History list item (lightweight)
# ---------------------------------------------------------------------------

class ValidationHistoryItem(BaseModel):
    """Lightweight history item for version listing."""
    validation_id: int
    version: int
    final_validation_score: float
    created_at: datetime

    class Config:
        from_attributes = True
