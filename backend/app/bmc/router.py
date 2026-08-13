"""
FastAPI router for AI Business Model Canvas endpoints.

Endpoints:
  POST /startups/{startup_id}/bmc/generate         -> generate complete BMC
  GET  /startups/{startup_id}/bmc/latest           -> get latest BMC canvas
  GET  /startups/{startup_id}/bmc/history          -> list version history
  GET  /startups/{startup_id}/bmc/history/{version_id} -> get specific BMC version
  PUT  /startups/{startup_id}/bmc/blocks/{block_name} -> manual block edit
  POST /startups/{startup_id}/bmc/regenerate-block -> single block AI regeneration
  POST /startups/{startup_id}/bmc/audit            -> trigger Red Pen audit
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.auth.dependencies import require_role
from app.bmc.schemas import (
    BMCVersionResponse,
    BMCVersionHistoryItem,
    BlockUpdatePayload,
    BlockRegeneratePayload,
    BMCAuditReport,
)
from app.bmc import service

router = APIRouter(prefix="/startups", tags=["Business Model Canvas"])


@router.post(
    "/{startup_id}/bmc/generate",
    response_model=BMCVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_bmc(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Generate a complete 9-block Business Model Canvas using Startup Workspace data
    and AI Idea Validation report insights.
    """
    return await service.generate_bmc(db, startup_id, current_user.id)


@router.get(
    "/{startup_id}/bmc/latest",
    response_model=BMCVersionResponse,
)
def get_latest_bmc(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return the latest generated Business Model Canvas for the founder's startup."""
    return service.get_latest_bmc(db, startup_id, current_user.id)


@router.get(
    "/{startup_id}/bmc/history",
    response_model=List[BMCVersionHistoryItem],
)
def get_bmc_history(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return version history items for the founder's Business Model Canvas."""
    return service.get_bmc_history(db, startup_id, current_user.id)


@router.get(
    "/{startup_id}/bmc/history/{version_id}",
    response_model=BMCVersionResponse,
)
def get_bmc_version_by_id(
    startup_id: int,
    version_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return a specific Business Model Canvas version by ID."""
    return service.get_bmc_version_by_id(db, startup_id, version_id, current_user.id)


@router.put(
    "/{startup_id}/bmc/blocks/{block_name}",
    response_model=BMCVersionResponse,
)
async def update_bmc_block(
    startup_id: int,
    block_name: str,
    payload: BlockUpdatePayload,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Update bullet points in a single block manually and persist as a new version."""
    return await service.update_block(
        db, startup_id, block_name, payload.items, current_user.id
    )


@router.post(
    "/{startup_id}/bmc/regenerate-block",
    response_model=BMCVersionResponse,
)
async def regenerate_bmc_block(
    startup_id: int,
    payload: BlockRegeneratePayload,
    block_name: Optional[str] = None,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Regenerate a single block with AI while keeping remaining blocks consistent."""
    target_block = payload.block_name or block_name
    if not target_block:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="block_name is required either in payload or query parameter.",
        )
    return await service.regenerate_block(
        db, startup_id, target_block, payload.custom_instructions, current_user.id
    )


@router.post(
    "/{startup_id}/bmc/audit",
    response_model=BMCAuditReport,
)
def audit_bmc(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Run an on-demand Red Pen Audit pass on the latest canvas."""
    return service.run_audit(db, startup_id, current_user.id)
