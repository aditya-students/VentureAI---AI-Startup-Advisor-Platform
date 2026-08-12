"""
Context Builder Service for AI Business Model Canvas.

Loads Startup Workspace data and existing AI Idea Validation report details
directly from database models.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.startup.models import Startup
from app.idea_validation.models import IdeaValidation


def build_bmc_context(db: Session, startup_id: int) -> Dict[str, Any]:
    """
    Load startup information and latest idea validation report for BMC engine.

    Returns a context dictionary containing startup_data, validation_data,
    has_validation flag, and validation_score.
    """
    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not startup:
        raise ValueError(f"Startup with ID {startup_id} not found.")

    startup_data = {
        "id": startup.id,
        "name": startup.name,
        "tagline": startup.tagline,
        "problem": startup.problem,
        "solution": startup.solution,
        "industry": startup.industry,
        "target_market": startup.target_market,
        "stage": startup.stage.value if hasattr(startup.stage, "value") else str(startup.stage),
    }

    # Fetch latest validation report for this startup
    latest_val = (
        db.query(IdeaValidation)
        .filter(IdeaValidation.startup_id == startup_id)
        .order_by(IdeaValidation.version.desc())
        .first()
    )

    if not latest_val:
        return {
            "startup_data": startup_data,
            "validation_data": None,
            "has_validation": False,
            "validation_score": None,
        }

    validation_data = {
        "id": latest_val.id,
        "version": latest_val.version,
        "final_validation_score": latest_val.final_validation_score,
        "dimension_scores": {
            "problem": latest_val.problem_score,
            "buyer": latest_val.buyer_score,
            "market": latest_val.market_score,
            "moat": latest_val.moat_score,
            "feasibility": latest_val.feasibility_score,
        },
        "lofa": latest_val.lofa,
        "overall_assessment": latest_val.overall_assessment,
        "strengths": latest_val.strengths,
        "key_risks": latest_val.key_risks,
        "recommended_next_steps": latest_val.recommended_next_steps,
        "agent_vc": latest_val.agent_vc,
        "agent_buyer": latest_val.agent_buyer,
        "agent_competitor": latest_val.agent_competitor,
    }

    return {
        "startup_data": startup_data,
        "validation_data": validation_data,
        "has_validation": True,
        "validation_score": latest_val.final_validation_score,
    }
