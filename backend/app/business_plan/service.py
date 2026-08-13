"""
Service layer for AI Business Plan Generator.

Handles:
- Founder workspace ownership verification
- Upstream prerequisite validation
- Full business plan generation pipeline
- Version management (incrementing versions, preserving previous runs)
- Granular section regeneration with Executive Summary & Audit re-synthesis
- Report retrieval & version history
- PDF HTML layout builder
"""

import asyncio
from copy import deepcopy
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.startup.models import Startup
from app.business_plan.models import BusinessPlan
from app.business_plan.context import get_prerequisites_status, build_business_plan_context
from app.business_plan.graph.graph import run_business_plan_pipeline
from app.business_plan.graph.nodes import (
    regenerate_single_section_node,
    synthesize_executive_summary,
    run_cross_document_audit,
)

VALID_SECTIONS = {
    "market_customer",
    "business_model_unit_economics",
    "gtm_operations",
    "financial_structure",
    "risk_validation_legal",
    "executive_summary",
}


def _verify_startup_ownership(db: Session, startup_id: int, user_id: int) -> Startup:
    """Ensure startup exists and belongs to the authenticated founder."""
    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Startup with ID {startup_id} not found.",
        )
    if startup.founder_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this startup workspace.",
        )
    return startup


def check_prerequisites(db: Session, startup_id: int, user_id: int) -> Dict[str, Any]:
    """Check if upstream prerequisites (Idea Validation + BMC) are completed."""
    _verify_startup_ownership(db, startup_id, user_id)
    return get_prerequisites_status(db, startup_id)


async def generate_business_plan(db: Session, startup_id: int, user_id: int) -> BusinessPlan:
    """Generate a complete new Business Plan version using workspace, validation, and BMC data."""
    _verify_startup_ownership(db, startup_id, user_id)

    # 1. Build Context (validates prerequisites)
    try:
        context = build_business_plan_context(db, startup_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 2. Run Pipeline
    pipeline_result = await run_business_plan_pipeline(context)

    # 3. Determine next version number
    latest = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.startup_id == startup_id)
        .order_by(BusinessPlan.version.desc())
        .first()
    )
    next_version = (latest.version + 1) if latest else 1

    # 4. Save Version in DB
    bp_record = BusinessPlan(
        startup_id=startup_id,
        bmc_version_id=context["bmc_data"]["id"],
        validation_report_id=context["validation_data"]["id"],
        version=next_version,
        executive_summary=pipeline_result["executive_summary"],
        domains_data=pipeline_result["domains_data"],
        audit_report=pipeline_result["audit_report"],
        validation_score=pipeline_result["validation_score"],
        is_pivot_mode=pipeline_result["is_pivot_mode"],
    )
    db.add(bp_record)
    db.commit()
    db.refresh(bp_record)
    return bp_record


def get_latest_business_plan(db: Session, startup_id: int, user_id: int) -> BusinessPlan:
    """Fetch the latest Business Plan version for the founder's startup."""
    _verify_startup_ownership(db, startup_id, user_id)

    latest = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.startup_id == startup_id)
        .order_by(BusinessPlan.version.desc())
        .first()
    )
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Business Plan has been generated yet for this startup workspace.",
        )
    return latest


def get_business_plan_history(db: Session, startup_id: int, user_id: int) -> List[BusinessPlan]:
    """Fetch all Business Plan versions for the startup."""
    _verify_startup_ownership(db, startup_id, user_id)

    return (
        db.query(BusinessPlan)
        .filter(BusinessPlan.startup_id == startup_id)
        .order_by(BusinessPlan.version.desc())
        .all()
    )


def get_business_plan_by_id(db: Session, plan_id: int, user_id: int) -> BusinessPlan:
    """Fetch a specific Business Plan by ID after owner verification."""
    bp = db.query(BusinessPlan).filter(BusinessPlan.id == plan_id).first()
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business Plan with ID {plan_id} not found.",
        )
    _verify_startup_ownership(db, bp.startup_id, user_id)
    return bp


async def regenerate_section(
    db: Session,
    plan_id: int,
    section_name: str,
    custom_instructions: Optional[str],
    user_id: int
) -> BusinessPlan:
    """
    Regenerates a single domain section (or Executive Summary).
    Re-synthesizes Executive Summary and re-runs Cross-Document Audit.
    Saves as a new Business Plan version.
    """
    if section_name not in VALID_SECTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid section name '{section_name}'. Must be one of {sorted(list(VALID_SECTIONS))}",
        )

    current_bp = get_business_plan_by_id(db, plan_id, user_id)
    startup_id = current_bp.startup_id

    # Load context
    context = build_business_plan_context(db, startup_id)

    new_domains = deepcopy(current_bp.domains_data)

    if section_name in new_domains:
        # Regenerate target domain
        updated_domain = await asyncio.to_thread(
            regenerate_single_section_node,
            section_name, context, new_domains, custom_instructions
        )
        new_domains[section_name] = updated_domain

        # Re-synthesize Executive Summary since a domain changed
        new_exec_summary = await asyncio.to_thread(
            synthesize_executive_summary, context, new_domains, custom_instructions
        )
    else:
        # User requested Executive Summary direct regeneration
        new_exec_summary = await asyncio.to_thread(
            synthesize_executive_summary, context, new_domains, custom_instructions
        )

    # Re-run Red Pen audit pass
    new_audit = await asyncio.to_thread(
        run_cross_document_audit, context, new_domains, new_exec_summary
    )

    # Determine next version
    latest = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.startup_id == startup_id)
        .order_by(BusinessPlan.version.desc())
        .first()
    )
    next_version = (latest.version + 1) if latest else (current_bp.version + 1)

    new_version = BusinessPlan(
        startup_id=startup_id,
        bmc_version_id=current_bp.bmc_version_id,
        validation_report_id=current_bp.validation_report_id,
        version=next_version,
        executive_summary=new_exec_summary,
        domains_data=new_domains,
        audit_report=new_audit,
        validation_score=current_bp.validation_score,
        is_pivot_mode=current_bp.is_pivot_mode,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


def get_audit_report(db: Session, plan_id: int, user_id: int) -> Dict[str, Any]:
    """Fetch the cross-document Red Pen Audit report for a plan."""
    bp = get_business_plan_by_id(db, plan_id, user_id)
    return bp.audit_report
