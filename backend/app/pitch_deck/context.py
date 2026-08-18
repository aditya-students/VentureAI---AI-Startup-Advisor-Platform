"""
Context Aggregation helper for AI Pitch Deck Generator.

Retrieves and merges data from:
1. Startup Workspace
2. AI Idea Validation Report
3. AI Business Model Canvas (BMC)
4. AI Business Plan

Handles missing upstream features gracefully without crashing.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.startup.models import Startup
from app.idea_validation.models import IdeaValidation
from app.bmc.models import BMCVersion
from app.business_plan.models import BusinessPlan


def get_prerequisites_status(db: Session, startup_id: int) -> Dict[str, Any]:
    """Inspects which upstream documents exist for the startup workspace."""
    startup = db.query(Startup).filter(Startup.id == startup_id).first()

    val = (
        db.query(IdeaValidation)
        .filter(IdeaValidation.startup_id == startup_id)
        .order_by(IdeaValidation.version.desc())
        .first()
    )
    bmc = (
        db.query(BMCVersion)
        .filter(BMCVersion.startup_id == startup_id)
        .order_by(BMCVersion.version.desc())
        .first()
    )
    bp = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.startup_id == startup_id)
        .order_by(BusinessPlan.version.desc())
        .first()
    )

    missing_parts = []
    if not val:
        missing_parts.append("Idea Validation")
    if not bmc:
        missing_parts.append("Business Model Canvas")
    if not bp:
        missing_parts.append("Business Plan")

    if missing_parts:
        missing_msg = f"Your {', '.join(missing_parts)} has not been generated yet. Generate all upstream features for the most complete pitch deck."
    else:
        missing_msg = None

    return {
        "workspace_exists": startup is not None,
        "validation_exists": val is not None,
        "bmc_exists": bmc is not None,
        "business_plan_exists": bp is not None,
        "missing_message": missing_msg,
    }


def build_pitch_deck_context(db: Session, startup_id: int) -> Dict[str, Any]:
    """
    Builds a unified context dictionary from all available upstream models.
    Tolerates missing validation, BMC, or Business Plan records.
    """
    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not startup:
        raise ValueError(f"Startup workspace with ID {startup_id} not found.")

    founder = startup.founder
    founder_info = {
        "id": founder.id if founder else None,
        "name": founder.name if founder else "Founder",
        "email": founder.email if founder else "",
    }

    startup_data = {
        "id": startup.id,
        "name": startup.name,
        "tagline": startup.tagline or "",
        "problem": startup.problem,
        "solution": startup.solution,
        "industry": startup.industry or "Technology",
        "target_market": startup.target_market or "Target Audience",
        "stage": startup.stage.value if hasattr(startup.stage, "value") else str(startup.stage),
        "status": startup.status.value if hasattr(startup.status, "value") else str(startup.status),
        "founder": founder_info,
    }

    # Latest Idea Validation
    val_record = (
        db.query(IdeaValidation)
        .filter(IdeaValidation.startup_id == startup_id)
        .order_by(IdeaValidation.version.desc())
        .first()
    )
    if val_record:
        validation_data = {
            "id": val_record.id,
            "version": val_record.version,
            "final_validation_score": val_record.final_validation_score,
            "dimension_scores": {
                "problem": val_record.problem_score,
                "buyer": val_record.buyer_score,
                "market": val_record.market_score,
                "moat": val_record.moat_score,
                "feasibility": val_record.feasibility_score,
            },
            "lofa": val_record.lofa,
            "agent_vc": val_record.agent_vc,
            "agent_buyer": val_record.agent_buyer,
            "agent_competitor": val_record.agent_competitor,
            "overall_assessment": val_record.overall_assessment,
            "strengths": val_record.strengths,
            "key_risks": val_record.key_risks,
            "recommended_next_steps": val_record.recommended_next_steps,
            "mom_test_questions": val_record.mom_test_questions,
            "kill_threshold": val_record.kill_threshold,
        }
        val_score = val_record.final_validation_score
    else:
        validation_data = {}
        val_score = 50.0  # Default neutral context baseline if unvalidated

    # Latest Business Model Canvas
    bmc_record = (
        db.query(BMCVersion)
        .filter(BMCVersion.startup_id == startup_id)
        .order_by(BMCVersion.version.desc())
        .first()
    )
    if bmc_record:
        bmc_data = {
            "id": bmc_record.id,
            "version": bmc_record.version,
            "canvas_blocks": bmc_record.canvas_data.get("canvas_blocks", bmc_record.canvas_data)
            if isinstance(bmc_record.canvas_data, dict)
            else {},
            "audit_data": bmc_record.audit_data,
        }
    else:
        bmc_data = {}

    # Latest Business Plan
    bp_record = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.startup_id == startup_id)
        .order_by(BusinessPlan.version.desc())
        .first()
    )
    if bp_record:
        bp_data = {
            "id": bp_record.id,
            "version": bp_record.version,
            "executive_summary": bp_record.executive_summary,
            "domains_data": bp_record.domains_data,
            "audit_report": bp_record.audit_report,
            "is_pivot_mode": bp_record.is_pivot_mode,
        }
    else:
        bp_data = {}

    # Flag for Low Validation Mode
    is_validation_mode = val_score < 50.0

    prereq_status = get_prerequisites_status(db, startup_id)

    return {
        "startup_data": startup_data,
        "validation_data": validation_data,
        "bmc_data": bmc_data,
        "business_plan_data": bp_data,
        "validation_score": val_score,
        "is_validation_mode": is_validation_mode,
        "prerequisites_status": prereq_status,
    }
