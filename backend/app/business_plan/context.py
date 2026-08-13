"""
Context Aggregator Service for AI Business Plan Generator.

Aggregates:
1. Startup Workspace data (Name, Problem, Solution, Target Market, Industry, Stage)
2. AI Idea Validation report (Scores, LOFA, VC/Buyer/Competitor critiques, Mom Test, Kill Threshold)
3. AI Business Model Canvas (9 blocks, audit findings, version ID)

Strictly enforces prerequisite completion before allowing Business Plan generation.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.startup.models import Startup
from app.idea_validation.models import IdeaValidation
from app.bmc.models import BMCVersion


def get_prerequisites_status(db: Session, startup_id: int) -> Dict[str, Any]:
    """
    Check if required upstream data exists for Business Plan generation.

    Prerequisites:
    - Active Startup Workspace
    - Latest AI Idea Validation report
    - Latest AI Business Model Canvas (BMC)
    """
    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not startup:
        return {
            "startup_id": startup_id,
            "has_workspace": False,
            "has_validation": False,
            "has_bmc": False,
            "can_generate": False,
            "missing_prerequisite_message": f"Startup workspace with ID {startup_id} not found.",
            "validation_score": None,
            "is_pivot_mode": False,
        }

    latest_val = (
        db.query(IdeaValidation)
        .filter(IdeaValidation.startup_id == startup_id)
        .order_by(IdeaValidation.version.desc())
        .first()
    )

    latest_bmc = (
        db.query(BMCVersion)
        .filter(BMCVersion.startup_id == startup_id)
        .order_by(BMCVersion.version.desc())
        .first()
    )

    has_val = latest_val is not None
    has_bmc = latest_bmc is not None
    can_gen = has_val and has_bmc

    msg: Optional[str] = None
    if not has_val and not has_bmc:
        msg = "Complete AI Idea Validation and generate a Business Model Canvas before creating your Business Plan."
    elif not has_val:
        msg = "Complete AI Idea Validation before generating your Business Plan."
    elif not has_bmc:
        msg = "Generate a Business Model Canvas before creating your Business Plan."

    val_score = latest_val.final_validation_score if latest_val else None
    is_pivot = (val_score is not None and val_score < 50.0)

    return {
        "startup_id": startup_id,
        "has_workspace": True,
        "has_validation": has_val,
        "has_bmc": has_bmc,
        "can_generate": can_gen,
        "missing_prerequisite_message": msg,
        "validation_score": val_score,
        "is_pivot_mode": is_pivot,
    }


def build_business_plan_context(db: Session, startup_id: int) -> Dict[str, Any]:
    """
    Load startup information, latest idea validation report, and latest BMC version.

    Raises ValueError if required upstream data is missing.
    """
    status_info = get_prerequisites_status(db, startup_id)

    if not status_info["has_workspace"]:
        raise ValueError(f"Startup workspace with ID {startup_id} not found.")

    if not status_info["can_generate"]:
        raise ValueError(status_info["missing_prerequisite_message"])

    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    latest_val = (
        db.query(IdeaValidation)
        .filter(IdeaValidation.startup_id == startup_id)
        .order_by(IdeaValidation.version.desc())
        .first()
    )
    latest_bmc = (
        db.query(BMCVersion)
        .filter(BMCVersion.startup_id == startup_id)
        .order_by(BMCVersion.version.desc())
        .first()
    )

    startup_data = {
        "id": startup.id,
        "name": startup.name,
        "tagline": startup.tagline,
        "problem": startup.problem,
        "solution": startup.solution,
        "industry": startup.industry,
        "target_market": startup.target_market,
        "stage": startup.stage.value if hasattr(startup.stage, "value") else str(startup.stage),
        "status": startup.status.value if hasattr(startup.status, "value") else str(startup.status),
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
        "mom_test_questions": latest_val.mom_test_questions,
        "kill_threshold": latest_val.kill_threshold,
        "agent_vc": latest_val.agent_vc,
        "agent_buyer": latest_val.agent_buyer,
        "agent_competitor": latest_val.agent_competitor,
    }

    # Extract 9 raw block item lists from BMC canvas_data
    raw_bmc_blocks = {}
    if isinstance(latest_bmc.canvas_data, dict):
        for block_name, block_info in latest_bmc.canvas_data.items():
            if isinstance(block_info, dict) and "items" in block_info:
                raw_bmc_blocks[block_name] = block_info["items"]
            elif isinstance(block_info, list):
                raw_bmc_blocks[block_name] = block_info

    bmc_data = {
        "id": latest_bmc.id,
        "version": latest_bmc.version,
        "canvas_blocks": raw_bmc_blocks,
        "canvas_raw": latest_bmc.canvas_data,
        "audit_data": latest_bmc.audit_data,
        "generation_mode": latest_bmc.generation_mode,
    }

    val_score = latest_val.final_validation_score
    is_pivot = (val_score < 50.0)

    return {
        "startup_data": startup_data,
        "validation_data": validation_data,
        "bmc_data": bmc_data,
        "validation_score": val_score,
        "is_pivot_mode": is_pivot,
    }
