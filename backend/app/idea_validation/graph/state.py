"""
LangGraph state definition for the Idea Validation pipeline.

The state flows through:
    START → extract_lofa → [vc, buyer, competitor] (parallel) → synthesis → scoring → END
"""

from __future__ import annotations
from typing import TypedDict


class ValidationState(TypedDict, total=False):
    """
    Shared state passed through the LangGraph validation pipeline.

    Fields are populated progressively by each node.
    """

    # ---- Inputs (set before graph invocation) ----
    workspace_data: dict          # {problem, solution, target_market, industry, stage, name, tagline}
    startup_id: int

    # ---- LOFA node output ----
    lofa: str                     # Leap-of-Faith Assumption

    # ---- Red-Team agent outputs ----
    vc_critique: dict             # Skeptical VC Partner analysis
    buyer_critique: dict          # Cynical Buyer / ICP analysis
    competitor_critique: dict     # Competitor & Moat Strategist analysis

    # ---- Synthesis node outputs ----
    dimension_scores: dict        # {problem, buyer, market, moat, feasibility} each 0-100
    overall_assessment: str
    strengths: list
    key_risks: list
    recommended_next_steps: list
    mom_test_questions: list      # 3 Mom Test questions
    kill_threshold: str           # Falsification criterion

    # ---- Scoring node outputs (deterministic) ----
    score_tiers: dict
    weighted_base_score: float
    final_validation_score: float
    vetoes: dict
    penalty_multiplier: float
    triggered_vetoes: list

    # ---- Error tracking ----
    error: str | None
