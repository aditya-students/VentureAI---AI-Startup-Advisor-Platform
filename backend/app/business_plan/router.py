"""
FastAPI router for AI Business Plan Generator endpoints.

Supports:
- POST /startups/{startup_id}/business-plan/generate -> generate complete business plan
- GET  /startups/{startup_id}/business-plan/latest   -> get latest business plan
- GET  /startups/{startup_id}/business-plan/versions -> list version history
- GET  /startups/{startup_id}/business-plan/check-prerequisites -> check upstream data
- GET  /business-plan/{business_plan_id} -> fetch specific plan by ID
- POST /business-plan/{business_plan_id}/regenerate-section -> regenerate single section
- GET  /business-plan/{business_plan_id}/audit -> fetch Red Pen audit findings
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.auth.dependencies import require_role
from app.business_plan.schemas import (
    BusinessPlanResponse,
    BusinessPlanHistoryItem,
    PrerequisitesStatusResponse,
    SectionRegeneratePayload,
    BusinessPlanAuditReport,
)
from app.business_plan import service

router = APIRouter(tags=["AI Business Plan Generator"])


# ===================================================================
# 1. STARTUP WORKSPACE SCOPED ENDPOINTS
# ===================================================================

@router.get(
    "/startups/{startup_id}/business-plan/check-prerequisites",
    response_model=PrerequisitesStatusResponse,
)
def check_prerequisites(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Check whether Idea Validation and BMC prerequisites are complete before generation."""
    return service.check_prerequisites(db, startup_id, current_user.id)


@router.post(
    "/startups/{startup_id}/business-plan/generate",
    response_model=BusinessPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_business_plan(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Generate a complete AI Business Plan using Startup Workspace, AI Idea Validation,
    and AI Business Model Canvas data.
    """
    return await service.generate_business_plan(db, startup_id, current_user.id)


@router.get(
    "/startups/{startup_id}/business-plan/latest",
    response_model=BusinessPlanResponse,
)
def get_latest_business_plan(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return the latest generated Business Plan for the founder's startup workspace."""
    return service.get_latest_business_plan(db, startup_id, current_user.id)


@router.get(
    "/startups/{startup_id}/business-plan/versions",
    response_model=List[BusinessPlanHistoryItem],
)
def get_business_plan_versions(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return version history for the startup's Business Plan."""
    return service.get_business_plan_history(db, startup_id, current_user.id)


# ===================================================================
# 2. BUSINESS PLAN ENTITY SCOPED ENDPOINTS
# ===================================================================

@router.get(
    "/business-plan/{business_plan_id}",
    response_model=BusinessPlanResponse,
)
def get_business_plan_by_id(
    business_plan_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return a specific Business Plan by its unique ID."""
    return service.get_business_plan_by_id(db, business_plan_id, current_user.id)


@router.post(
    "/business-plan/{business_plan_id}/regenerate-section",
    response_model=BusinessPlanResponse,
)
async def regenerate_section(
    business_plan_id: int,
    payload: SectionRegeneratePayload,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Regenerate a single Business Plan section (e.g. market_customer, gtm_operations).
    Preserves other domains, re-synthesizes Executive Summary & Red Pen Audit,
    and saves as a new Business Plan version.
    """
    return await service.regenerate_section(
        db,
        business_plan_id,
        payload.section_name,
        payload.custom_instructions,
        current_user.id,
    )


@router.get(
    "/business-plan/{business_plan_id}/audit",
    response_model=Dict[str, Any],
)
def get_business_plan_audit(
    business_plan_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return the cross-document Red Pen Audit report for a business plan."""
    return service.get_audit_report(db, business_plan_id, current_user.id)


# Direct /api/ prefix aliases specified in Section 14
@router.post(
    "/api/business-plan/generate",
    response_model=BusinessPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def api_generate_business_plan(
    startup_id: int = Query(..., description="Startup Workspace ID"),
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for POST /startups/{startup_id}/business-plan/generate."""
    return await service.generate_business_plan(db, startup_id, current_user.id)


@router.get(
    "/api/business-plan/{workspace_id}/latest",
    response_model=BusinessPlanResponse,
)
def api_get_latest_business_plan(
    workspace_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for GET /startups/{startup_id}/business-plan/latest."""
    return service.get_latest_business_plan(db, workspace_id, current_user.id)


@router.get(
    "/api/business-plan/{workspace_id}/versions",
    response_model=List[BusinessPlanHistoryItem],
)
def api_get_business_plan_versions(
    workspace_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for GET /startups/{startup_id}/business-plan/versions."""
    return service.get_business_plan_history(db, workspace_id, current_user.id)
