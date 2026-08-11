"""
LangGraph StateGraph for the Idea Validation pipeline.

Graph structure:

    START
      ↓
    extract_lofa
      ↓
    ┌───────────┬──────────────┬────────────────────┐
    ↓           ↓              ↓
  vc_agent  buyer_agent  competitor_agent
    ↓           ↓              ↓
    └───────────┴──────────────┘
                ↓
          synthesis_node
                ↓
          scoring_node
                ↓
               END

The three Red-Team agents execute in parallel after LOFA extraction.
"""

from __future__ import annotations

import asyncio
import logging

from app.idea_validation.graph.state import ValidationState
from app.idea_validation.graph.nodes import (
    extract_lofa,
    skeptical_vc_agent,
    cynical_buyer_agent,
    competitor_strategist_agent,
    synthesis_node,
    scoring_node,
)

logger = logging.getLogger(__name__)


async def run_validation_pipeline(workspace_data: dict, startup_id: int) -> ValidationState:
    """
    Execute the full validation pipeline.

    Uses asyncio.to_thread for the synchronous Gemini calls and
    asyncio.gather for parallel agent execution.

    Returns the completed ValidationState.
    """
    state: ValidationState = {
        "workspace_data": workspace_data,
        "startup_id": startup_id,
    }

    # ---- Step 1: LOFA Extraction ----
    logger.info("Starting LOFA extraction for startup %s", startup_id)
    lofa_result = await asyncio.to_thread(extract_lofa, state)
    state.update(lofa_result)
    logger.info("LOFA extracted: %s", state["lofa"][:80])

    # ---- Step 2: Three Red-Team agents in parallel ----
    logger.info("Starting parallel Red-Team analysis")

    async def run_vc():
        return await asyncio.to_thread(skeptical_vc_agent, state)

    async def run_buyer():
        return await asyncio.to_thread(cynical_buyer_agent, state)

    async def run_competitor():
        return await asyncio.to_thread(competitor_strategist_agent, state)

    vc_result, buyer_result, competitor_result = await asyncio.gather(
        run_vc(),
        run_buyer(),
        run_competitor(),
    )

    state.update(vc_result)
    state.update(buyer_result)
    state.update(competitor_result)
    logger.info("All three Red-Team agents completed")

    # ---- Step 3: Synthesis ----
    logger.info("Starting synthesis")
    synthesis_result = await asyncio.to_thread(synthesis_node, state)
    state.update(synthesis_result)
    logger.info("Synthesis completed — dimension scores: %s", state["dimension_scores"])

    # ---- Step 4: Deterministic Scoring ----
    logger.info("Applying deterministic scoring")
    scoring_result = scoring_node(state)  # Pure Python, no IO
    state.update(scoring_result)
    logger.info(
        "Final score: %.1f (base: %.1f, penalty: %.4f)",
        state["final_validation_score"],
        state["weighted_base_score"],
        state["penalty_multiplier"],
    )

    return state
