"""
BMC Generation Orchestrator Pipeline.

Coordinates Context -> Constraint Engine -> Gemini Canvas Generation -> Red Pen Audit.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from app.bmc.constraints import evaluate_bmc_constraints
from app.bmc.graph.nodes import (
    generate_bmc_canvas_node,
    red_pen_audit_node,
)

logger = logging.getLogger(__name__)


async def run_bmc_pipeline(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the complete BMC generation and audit pipeline.

    Returns:
        Dict with canvas_data, audit_data, generation_mode, and validation_score.
    """
    startup_id = context["startup_data"]["id"]
    logger.info("Starting BMC pipeline for startup ID %s", startup_id)

    # Step 1: Constraint Engine Evaluation
    constraints, generation_mode = evaluate_bmc_constraints(context)
    logger.info("Constraints generated: %d rules, mode=%s", len(constraints), generation_mode)

    # Step 2: Gemini Canvas Generation
    canvas_data = await asyncio.to_thread(
        generate_bmc_canvas_node,
        context,
        constraints,
        generation_mode,
    )
    logger.info("Canvas generation completed for startup ID %s", startup_id)

    # Step 3: Red Pen Consistency Audit
    audit_data = await asyncio.to_thread(
        red_pen_audit_node,
        canvas_data,
        context,
    )
    logger.info("Red Pen Audit completed — health_score=%s", audit_data.get("health_score"))

    return {
        "canvas_data": canvas_data,
        "audit_data": audit_data,
        "generation_mode": generation_mode,
        "validation_score": context.get("validation_score"),
    }
