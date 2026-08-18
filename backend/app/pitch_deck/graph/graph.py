"""
Pitch Deck Pipeline Orchestrator.

Pipeline Flow:
Context Aggregation
        ↓
      Router
 ┌──────┼────────┐
 ▼      ▼        ▼
Group A Group B  Group C
Slides  Slides   Slides
1-5     6-10     11-13
 └──────┼────────┘
        ↓
 Slide Schema Validation
        ↓
 Visual Asset Processing
        ↓
 Red Pen Auditor Pass
        ↓
 Final Pitch Deck Persistence
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from app.pitch_deck.graph.nodes import (
    generate_group_a_slides,
    generate_group_b_slides,
    generate_group_c_slides,
    run_pitch_deck_audit,
)

logger = logging.getLogger(__name__)


async def run_pitch_deck_pipeline(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the complete multi-stage Pitch Deck generation pipeline.

    Returns dict with slides_data, audit_report, is_validation_mode, validation_score.
    """
    startup_id = context["startup_data"]["id"]
    logger.info("Starting Pitch Deck generation pipeline for startup ID %s", startup_id)

    # Step 1: Run Groups A, B, and C concurrently in parallel
    logger.info("Executing Pitch Deck Slide Groups A, B, and C concurrently...")

    async def run_group_a():
        return await asyncio.to_thread(generate_group_a_slides, context)

    async def run_group_b():
        return await asyncio.to_thread(generate_group_b_slides, context)

    async def run_group_c():
        return await asyncio.to_thread(generate_group_c_slides, context)

    slides_a, slides_b, slides_c = await asyncio.gather(
        run_group_a(), run_group_b(), run_group_c()
    )

    all_slides = slides_a + slides_b + slides_c
    all_slides.sort(key=lambda s: s.get("slide_number", 0))

    logger.info("Generated %d pitch deck slides across Groups A, B, and C.", len(all_slides))

    # Step 2: Run Red Pen Auditor Pass
    logger.info("Running Pitch Deck Red Pen Auditor pass...")
    audit_report = await asyncio.to_thread(
        run_pitch_deck_audit, context, all_slides
    )
    logger.info(
        "Red Pen Audit completed — health_score=%s, warnings=%d",
        audit_report.get("health_score"),
        len(audit_report.get("warnings", [])),
    )

    return {
        "slides_data": all_slides,
        "audit_report": audit_report,
        "is_validation_mode": context.get("is_validation_mode", False),
        "validation_score": context.get("validation_score"),
    }
