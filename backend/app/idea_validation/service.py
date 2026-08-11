"""
Idea Validation business logic — orchestrates the validation pipeline,
persists results, and retrieves reports.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.startup.models import Startup
from app.idea_validation.models import IdeaValidation
from app.idea_validation.graph.graph import run_validation_pipeline
from app.idea_validation.schemas import (
    ValidationReportResponse,
    ValidationHistoryItem,
    ValidationDelta,
    DimensionDelta,
    ScoreBreakdown,
    ScoreTiers,
    VetoDetail,
    TriggeredVeto,
    AgentAnalysis,
    FalsificationBlueprint,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_startup_or_404(db: Session, startup_id: int, founder_id: int) -> Startup:
    """
    Load a startup by ID and verify ownership.
    Raises 404 if not found, 403 if not owned by the requesting founder.
    """
    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Startup not found.",
        )
    if startup.founder_id != founder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this startup.",
        )
    return startup


def _build_workspace_data(startup: Startup) -> dict:
    """Extract workspace data from the Startup ORM object."""
    return {
        "name":          startup.name,
        "tagline":       startup.tagline or "",
        "problem":       startup.problem,
        "solution":      startup.solution,
        "industry":      startup.industry or "",
        "target_market": startup.target_market or "",
        "stage":         startup.stage.value if startup.stage else "Idea",
    }


def _next_version(db: Session, startup_id: int) -> int:
    """Calculate the next version number for a startup's validation."""
    latest = (
        db.query(IdeaValidation.version)
        .filter(IdeaValidation.startup_id == startup_id)
        .order_by(IdeaValidation.version.desc())
        .first()
    )
    return (latest[0] + 1) if latest else 1


def _validation_to_response(
    v: IdeaValidation,
    delta: Optional[ValidationDelta] = None,
) -> ValidationReportResponse:
    """Convert an IdeaValidation ORM instance to a response schema."""
    # Extract agent analysis — handle both nested and flat structures
    vc_data = v.agent_vc or {}
    buyer_data = v.agent_buyer or {}
    competitor_data = v.agent_competitor or {}

    # Ensure triggered_vetoes is always a list
    triggered = []
    vetoes_dict = v.vetoes or {}
    if isinstance(vetoes_dict, dict):
        for key, triggered_flag in vetoes_dict.items():
            if triggered_flag:
                triggered.append(TriggeredVeto(
                    key=key,
                    label=_veto_label(key),
                    penalty=_veto_penalty(key),
                ))

    return ValidationReportResponse(
        validation_id=v.id,
        startup_id=v.startup_id,
        version=v.version,
        lofa=v.lofa,
        scores=ScoreBreakdown(
            problem_score=v.problem_score,
            buyer_score=v.buyer_score,
            market_score=v.market_score,
            moat_score=v.moat_score,
            feasibility_score=v.feasibility_score,
            weighted_base_score=v.weighted_base_score,
            final_validation_score=v.final_validation_score,
        ),
        score_tiers=ScoreTiers(**(v.score_tiers or {})),
        vetoes=VetoDetail(**(v.vetoes or {})),
        penalty_multiplier=v.penalty_multiplier,
        triggered_vetoes=triggered,
        agent_analysis=AgentAnalysis(
            vc=vc_data,
            buyer=buyer_data,
            competitor=competitor_data,
        ),
        overall_assessment=v.overall_assessment,
        strengths=v.strengths or [],
        key_risks=v.key_risks or [],
        recommended_next_steps=v.recommended_next_steps or [],
        falsification_blueprint=FalsificationBlueprint(
            mom_test_questions=v.mom_test_questions or [],
            kill_threshold=v.kill_threshold or "",
        ),
        created_at=v.created_at,
        delta=delta,
    )


def _veto_label(key: str) -> str:
    labels = {
        "no_urgent_pain": "No Urgent Pain — Problem score critically low",
        "capped_market": "Capped Market — Market score critically low",
        "high_incumbent_risk": "High Incumbent Risk — Moat score critically low",
    }
    return labels.get(key, key)


def _veto_penalty(key: str) -> float:
    penalties = {
        "no_urgent_pain": 0.60,
        "capped_market": 0.50,
        "high_incumbent_risk": 0.80,
    }
    return penalties.get(key, 1.0)


def _compute_delta(
    current: IdeaValidation,
    previous: IdeaValidation,
) -> ValidationDelta:
    """Compute delta between two validation versions."""
    dims = [
        ("Problem Severity", "problem_score"),
        ("Buyer Viability", "buyer_score"),
        ("Market Potential", "market_score"),
        ("Defensibility & Moat", "moat_score"),
        ("Technical Feasibility", "feasibility_score"),
    ]
    dimension_deltas = []
    for label, attr in dims:
        prev_val = getattr(previous, attr)
        curr_val = getattr(current, attr)
        dimension_deltas.append(DimensionDelta(
            dimension=label,
            previous=prev_val,
            current=curr_val,
            change=curr_val - prev_val,
        ))

    return ValidationDelta(
        previous_version=previous.version,
        current_version=current.version,
        score_change=round(current.final_validation_score - previous.final_validation_score, 1),
        dimension_deltas=dimension_deltas,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_validation(db: Session, startup_id: int, founder_id: int) -> ValidationReportResponse:
    """
    Run the full AI Idea Validation pipeline for a startup.

    1. Verify ownership + completeness
    2. Run LangGraph pipeline (async, with parallel agents)
    3. Persist versioned report
    4. Compute delta if previous version exists
    5. Return the complete report
    """
    # 1. Verify startup
    startup = _get_startup_or_404(db, startup_id, founder_id)

    # Check required fields
    missing = []
    if not startup.problem or not startup.problem.strip():
        missing.append("problem")
    if not startup.solution or not startup.solution.strip():
        missing.append("solution")
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Your startup workspace is missing required information: {', '.join(missing)}. "
                   f"Please complete your startup information before running Idea Validation.",
        )

    # 2. Build workspace data snapshot
    workspace_data = _build_workspace_data(startup)
    version = _next_version(db, startup_id)

    # 3. Run the validation pipeline
    try:
        result = await run_validation_pipeline(workspace_data, startup_id)
    except RuntimeError as e:
        logger.error("Validation pipeline failed for startup %s: %s", startup_id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI validation pipeline failed: {e}",
        )
    except Exception as e:
        logger.error("Unexpected error in validation pipeline: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during validation. Please try again.",
        )

    # 4. Persist to database
    dim = result["dimension_scores"]
    validation = IdeaValidation(
        startup_id=startup_id,
        version=version,
        input_snapshot=workspace_data,
        lofa=result["lofa"],
        agent_vc=result["vc_critique"],
        agent_buyer=result["buyer_critique"],
        agent_competitor=result["competitor_critique"],
        problem_score=dim["problem"],
        buyer_score=dim["buyer"],
        market_score=dim["market"],
        moat_score=dim["moat"],
        feasibility_score=dim["feasibility"],
        weighted_base_score=result["weighted_base_score"],
        final_validation_score=result["final_validation_score"],
        vetoes=result["vetoes"],
        penalty_multiplier=result["penalty_multiplier"],
        score_tiers=result["score_tiers"],
        overall_assessment=result["overall_assessment"],
        strengths=result["strengths"],
        key_risks=result["key_risks"],
        recommended_next_steps=result["recommended_next_steps"],
        mom_test_questions=result["mom_test_questions"],
        kill_threshold=result["kill_threshold"],
    )

    db.add(validation)
    db.commit()
    db.refresh(validation)

    # 5. Compute delta with previous version
    delta = None
    if version > 1:
        previous = (
            db.query(IdeaValidation)
            .filter(
                IdeaValidation.startup_id == startup_id,
                IdeaValidation.version == version - 1,
            )
            .first()
        )
        if previous:
            delta = _compute_delta(validation, previous)

    return _validation_to_response(validation, delta)


def get_latest_validation(
    db: Session, startup_id: int, founder_id: int
) -> ValidationReportResponse:
    """Get the latest validation report for a startup."""
    _get_startup_or_404(db, startup_id, founder_id)

    validation = (
        db.query(IdeaValidation)
        .filter(IdeaValidation.startup_id == startup_id)
        .order_by(IdeaValidation.version.desc())
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No validation report found. Run 'Validate My Idea' first.",
        )

    # Compute delta
    delta = None
    if validation.version > 1:
        previous = (
            db.query(IdeaValidation)
            .filter(
                IdeaValidation.startup_id == startup_id,
                IdeaValidation.version == validation.version - 1,
            )
            .first()
        )
        if previous:
            delta = _compute_delta(validation, previous)

    return _validation_to_response(validation, delta)


def get_validation_history(
    db: Session, startup_id: int, founder_id: int
) -> list[ValidationHistoryItem]:
    """Get all validation versions (lightweight) for a startup."""
    _get_startup_or_404(db, startup_id, founder_id)

    validations = (
        db.query(IdeaValidation)
        .filter(IdeaValidation.startup_id == startup_id)
        .order_by(IdeaValidation.version.desc())
        .all()
    )

    return [
        ValidationHistoryItem(
            validation_id=v.id,
            version=v.version,
            final_validation_score=v.final_validation_score,
            created_at=v.created_at,
        )
        for v in validations
    ]


def get_validation_by_id(
    db: Session, startup_id: int, validation_id: int, founder_id: int
) -> ValidationReportResponse:
    """Get a specific validation report by ID."""
    _get_startup_or_404(db, startup_id, founder_id)

    validation = (
        db.query(IdeaValidation)
        .filter(
            IdeaValidation.id == validation_id,
            IdeaValidation.startup_id == startup_id,
        )
        .first()
    )
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation report not found.",
        )

    # Compute delta with previous version
    delta = None
    if validation.version > 1:
        previous = (
            db.query(IdeaValidation)
            .filter(
                IdeaValidation.startup_id == startup_id,
                IdeaValidation.version == validation.version - 1,
            )
            .first()
        )
        if previous:
            delta = _compute_delta(validation, previous)

    return _validation_to_response(validation, delta)
