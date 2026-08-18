"""
Service layer for AI Business Model Canvas.

Implements database CRUD, founder ownership enforcement, versioning,
smart block updates, single-block regeneration, and audit execution.
"""

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.startup.models import Startup
from app.bmc.models import BMCVersion
from app.bmc.context import build_bmc_context
from app.bmc.graph.graph import run_bmc_pipeline
from app.bmc.graph.nodes import red_pen_audit_node, regenerate_single_block_node

VALID_BLOCK_NAMES = {
    "customer_segments",
    "value_propositions",
    "channels",
    "customer_relationships",
    "revenue_streams",
    "key_resources",
    "key_activities",
    "key_partnerships",
    "cost_structure",
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


async def generate_bmc(db: Session, startup_id: int, user_id: int) -> BMCVersion:
    """Generate a new Business Model Canvas version using workspace and validation data."""
    _verify_startup_ownership(db, startup_id, user_id)

    # 1. Build Context
    context = build_bmc_context(db, startup_id)

    # 2. Run Pipeline
    pipeline_result = await run_bmc_pipeline(context)

    # 3. Determine next version number
    latest = (
        db.query(BMCVersion)
        .filter(BMCVersion.startup_id == startup_id)
        .order_by(BMCVersion.version.desc())
        .first()
    )
    next_version = (latest.version + 1) if latest else 1

    # 4. Save Version
    bmc_version = BMCVersion(
        startup_id=startup_id,
        version=next_version,
        canvas_data=pipeline_result["canvas_data"],
        audit_data=pipeline_result["audit_data"],
        validation_score=pipeline_result["validation_score"],
        generation_mode=pipeline_result["generation_mode"],
    )
    db.add(bmc_version)
    db.commit()
    db.refresh(bmc_version)
    return bmc_version


def get_latest_bmc(db: Session, startup_id: int, user_id: int) -> BMCVersion:
    """Fetch the latest BMC version for the founder's startup."""
    _verify_startup_ownership(db, startup_id, user_id)

    latest = (
        db.query(BMCVersion)
        .filter(BMCVersion.startup_id == startup_id)
        .order_by(BMCVersion.version.desc())
        .first()
    )
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Business Model Canvas has been generated yet for this startup.",
        )
    return latest


def get_bmc_history(db: Session, startup_id: int, user_id: int) -> List[BMCVersion]:
    """Fetch all BMC versions for the startup."""
    _verify_startup_ownership(db, startup_id, user_id)

    return (
        db.query(BMCVersion)
        .filter(BMCVersion.startup_id == startup_id)
        .order_by(BMCVersion.version.desc())
        .all()
    )


def get_bmc_version_by_id(
    db: Session, startup_id: int, version_id: int, user_id: int
) -> BMCVersion:
    """Fetch a specific BMC version by ID or version number."""
    _verify_startup_ownership(db, startup_id, user_id)

    bmc = (
        db.query(BMCVersion)
        .filter(
            BMCVersion.startup_id == startup_id,
            (BMCVersion.id == version_id) | (BMCVersion.version == version_id)
        )
        .first()
    )
    if not bmc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BMC version {version_id} not found.",
        )
    return bmc


async def update_block(
    db: Session,
    startup_id: int,
    block_name: str,
    items: List[str],
    user_id: int,
) -> BMCVersion:
    """
    Update items in a single block and persist as a new version.
    Never silently overwrites existing versions.
    """
    if block_name not in VALID_BLOCK_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid block name '{block_name}'. Must be one of {sorted(list(VALID_BLOCK_NAMES))}",
        )

    _verify_startup_ownership(db, startup_id, user_id)
    latest = get_latest_bmc(db, startup_id, user_id)

    new_canvas = deepcopy(latest.canvas_data)
    now_iso = datetime.now(timezone.utc).isoformat()

    existing_block = new_canvas.get(block_name)
    existing_risk = existing_block.get("risk_notes") if isinstance(existing_block, dict) else None

    new_canvas[block_name] = {
        "items": items,
        "generated_by_ai": False,
        "modified_by_founder": True,
        "last_updated": now_iso,
        "risk_notes": existing_risk,
    }

    # Re-run Red Pen audit pass
    context = build_bmc_context(db, startup_id)
    audit_data = await asyncio.to_thread(red_pen_audit_node, new_canvas, context)

    new_version = BMCVersion(
        startup_id=startup_id,
        version=latest.version + 1,
        canvas_data=new_canvas,
        audit_data=audit_data,
        validation_score=latest.validation_score,
        generation_mode=latest.generation_mode,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


async def regenerate_block(
    db: Session,
    startup_id: int,
    block_name: str,
    custom_instructions: Optional[str],
    user_id: int,
) -> BMCVersion:
    """
    Regenerate a single block with AI while keeping remaining blocks consistent.
    Saves as a new canvas version.
    """
    if block_name not in VALID_BLOCK_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid block name '{block_name}'. Must be one of {sorted(list(VALID_BLOCK_NAMES))}",
        )

    _verify_startup_ownership(db, startup_id, user_id)
    latest = get_latest_bmc(db, startup_id, user_id)

    context = build_bmc_context(db, startup_id)
    new_items = await asyncio.to_thread(
        regenerate_single_block_node,
        block_name,
        latest.canvas_data,
        context,
        custom_instructions,
    )

    new_canvas = deepcopy(latest.canvas_data)
    now_iso = datetime.now(timezone.utc).isoformat()

    existing_block = new_canvas.get(block_name)
    existing_risk = existing_block.get("risk_notes") if isinstance(existing_block, dict) else None

    new_canvas[block_name] = {
        "items": new_items,
        "generated_by_ai": True,
        "modified_by_founder": False,
        "last_updated": now_iso,
        "risk_notes": existing_risk,
    }

    audit_data = await asyncio.to_thread(red_pen_audit_node, new_canvas, context)

    new_version = BMCVersion(
        startup_id=startup_id,
        version=latest.version + 1,
        canvas_data=new_canvas,
        audit_data=audit_data,
        validation_score=latest.validation_score,
        generation_mode=latest.generation_mode,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


def run_audit(db: Session, startup_id: int, user_id: int) -> Dict[str, Any]:
    """Run an on-demand Red Pen audit pass on the latest BMC version."""
    _verify_startup_ownership(db, startup_id, user_id)
    latest = get_latest_bmc(db, startup_id, user_id)

    context = build_bmc_context(db, startup_id)
    audit_data = red_pen_audit_node(latest.canvas_data, context)

    latest.audit_data = audit_data
    db.commit()
    db.refresh(latest)
    return audit_data
