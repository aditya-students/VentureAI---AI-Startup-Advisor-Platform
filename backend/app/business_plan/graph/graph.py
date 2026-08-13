"""
Business Plan Pipeline Orchestrator.

Pipeline Flow:
Context Aggregation
        ↓
5 Domain Workers (Concurrent / Parallel via asyncio.gather)
        ↓
Executive Summary Synthesis (Runs LAST after 5 domains)
        ↓
Cross-Document Red Pen Audit
        ↓
Persistence & Output
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from app.business_plan.graph.nodes import (
    generate_domain_market_customer,
    generate_domain_business_model,
    generate_domain_gtm_operations,
    generate_domain_financial_structure,
    generate_domain_risk_legal,
    synthesize_executive_summary,
    run_cross_document_audit,
)

logger = logging.getLogger(__name__)


async def run_business_plan_pipeline(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the complete multi-stage Business Plan generation pipeline.

    Returns dict with executive_summary, domains_data, audit_report, validation_score, is_pivot_mode.
    """
    startup_id = context["startup_data"]["id"]
    logger.info("Starting Business Plan generation pipeline for startup ID %s", startup_id)

    # Step 1: Run 5 Domain Workers concurrently in parallel
    logger.info("Executing 5 Business Plan Domain Workers concurrently...")

    async def run_d1():
        return await asyncio.to_thread(generate_domain_market_customer, context)

    async def run_d2():
        return await asyncio.to_thread(generate_domain_business_model, context)

    async def run_d3():
        return await asyncio.to_thread(generate_domain_gtm_operations, context)

    async def run_d4():
        return await asyncio.to_thread(generate_domain_financial_structure, context)

    async def run_d5():
        return await asyncio.to_thread(generate_domain_risk_legal, context)

    d1_res, d2_res, d3_res, d4_res, d5_res = await asyncio.gather(
        run_d1(), run_d2(), run_d3(), run_d4(), run_d5()
    )

    domains_data = {
        "market_customer": d1_res,
        "business_model_unit_economics": d2_res,
        "gtm_operations": d3_res,
        "financial_structure": d4_res,
        "risk_validation_legal": d5_res,
    }
    logger.info("All 5 Business Plan Domains generated successfully.")

    # Step 2: Synthesize Executive Summary LAST
    logger.info("Synthesizing Executive Summary from 5 completed domains...")
    exec_summary = await asyncio.to_thread(
        synthesize_executive_summary, context, domains_data
    )
    logger.info("Executive Summary synthesized successfully.")

    # Step 3: Run Cross-Document Red Pen Audit
    logger.info("Running Cross-Document Red Pen Audit...")
    audit_report = await asyncio.to_thread(
        run_cross_document_audit, context, domains_data, exec_summary
    )
    logger.info(
        "Cross-Document Audit completed — health_score=%s, warnings=%d",
        audit_report.get("health_score"),
        len(audit_report.get("warnings", [])),
    )

    return {
        "executive_summary": exec_summary,
        "domains_data": domains_data,
        "audit_report": audit_report,
        "validation_score": context.get("validation_score"),
        "is_pivot_mode": context.get("is_pivot_mode", False),
    }
