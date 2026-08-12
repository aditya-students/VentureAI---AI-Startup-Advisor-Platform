"""
Gemini and deterministic nodes for BMC generation, Red Pen Audit, and block regeneration.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import google.generativeai as genai

from app.config import settings
from app.bmc.schemas import BMCBlocksRaw, BMCAuditReport, AuditConflict

logger = logging.getLogger(__name__)

# Model candidates for Gemini API calls
MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
]


def _configure_genai() -> None:
    """Ensure Gemini client is configured."""
    genai.configure(api_key=settings.GEMINI_API_KEY)


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Call Gemini API with model candidate fallbacks."""
    _configure_genai()
    last_error = None

    for model_name in MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(
                model_name,
                system_instruction=system_prompt,
            )
            response = model.generate_content(user_prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            logger.warning("Gemini API call to model '%s' failed: %s", model_name, e)
            last_error = e

    raise last_error or RuntimeError("All Gemini API model calls failed.")


def _extract_json(text: str) -> dict:
    """Extract JSON object from markdown fences or raw text."""
    fence_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
    if fence_match:
        text = fence_match.group(1)

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            return json.loads(brace_match.group(0))
        raise ValueError(f"Could not extract JSON from Gemini response:\n{text[:500]}")


# ===================================================================
# NODE 1: BMC Generation Prompt & Node
# ===================================================================

BMC_GEN_SYSTEM = """You are a master startup advisor building a validation-aware Business Model Canvas (BMC).

You must generate all 9 blocks of the Business Model Canvas:
1. customer_segments
2. value_propositions
3. channels
4. customer_relationships
5. revenue_streams
6. key_resources
7. key_activities
8. key_partnerships
9. cost_structure

RULES FOR GENERATION:
- CONCISE BULLETS: Each block MUST contain 3 to 5 clear, concise, actionable bullet points (short phrases, NOT huge paragraphs).
- VALIDATION-AWARE: Incorporate the startup's LOFA, risk areas, and validation scores into the model.
- INTER-BLOCK DEPENDENCIES:
  * COST FLOOR RULE: Every major activity, resource, or channel listed MUST have a corresponding cost implication in cost_structure.
  * REVENUE ORIGIN RULE: Every revenue stream MUST explicitly tie to a specific customer segment and value proposition.
  * VALUE ALIGNMENT: Value propositions MUST solve the identified customer problem.
- DETERMINISTIC CONSTRAINTS: Strictly honor any provided business constraints (e.g. do not invent proprietary tech if Moat score is low; do not assume instant self-serve adoption if Buyer score is low).

Respond with ONLY a JSON object matching this structure:
{
    "customer_segments": ["...", "..."],
    "value_propositions": ["...", "..."],
    "channels": ["...", "..."],
    "customer_relationships": ["...", "..."],
    "revenue_streams": ["...", "..."],
    "key_resources": ["...", "..."],
    "key_activities": ["...", "..."],
    "key_partnerships": ["...", "..."],
    "cost_structure": ["...", "..."]
}"""


def generate_bmc_canvas_node(context: Dict[str, Any], constraints: List[str], generation_mode: str) -> Dict[str, Any]:
    """Generates a complete 9-block BMC JSON and formats block metadata."""
    startup = context["startup_data"]
    val = context.get("validation_data")

    prompt = f"""Generate a Business Model Canvas for the following startup:

STARTUP INFORMATION:
- Name: {startup.get('name')}
- Tagline: {startup.get('tagline', 'N/A')}
- Problem: {startup.get('problem')}
- Solution: {startup.get('solution')}
- Industry: {startup.get('industry', 'N/A')}
- Target Market: {startup.get('target_market', 'N/A')}
- Stage: {startup.get('stage', 'N/A')}
"""

    if val:
        prompt += f"""
VALIDATION CONTEXT:
- Final Score: {val.get('final_validation_score')}/100
- Dimension Scores: {json.dumps(val.get('dimension_scores', {}))}
- LOFA (Riskiest Assumption): {val.get('lofa')}
- Key Risks: {json.dumps(val.get('key_risks', []))}
"""
    else:
        prompt += "\nVALIDATION CONTEXT: None available (generating canvas from workspace data only).\n"

    if constraints:
        prompt += "\nBUSINESS & VALIDATION CONSTRAINTS (STRICT ENFORCE):\n" + "\n".join(f"- {c}" for c in constraints) + "\n"

    prompt += "\nRespond with ONLY the 9-block JSON object."

    raw_blocks: Dict[str, List[str]] = {}
    try:
        raw_text = _call_gemini(BMC_GEN_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        validated = BMCBlocksRaw(**parsed)
        raw_blocks = validated.model_dump()
    except Exception as e:
        logger.warning("BMC generation AI call failed (%s), using fallback context canvas.", e)
        raw_blocks = _get_fallback_bmc_blocks(startup, val)

    # Format into block objects with metadata
    now_iso = datetime.now(timezone.utc).isoformat()
    formatted_canvas: Dict[str, Any] = {}
    block_keys = [
        "customer_segments", "value_propositions", "channels",
        "customer_relationships", "revenue_streams", "key_resources",
        "key_activities", "key_partnerships", "cost_structure"
    ]

    for key in block_keys:
        items = raw_blocks.get(key, ["Standard industry default"])
        formatted_canvas[key] = {
            "items": items,
            "generated_by_ai": True,
            "modified_by_founder": False,
            "last_updated": now_iso,
            "risk_notes": "Low validation score area" if generation_mode == "PIVOT_AWARE" and key in ["key_resources", "channels"] else None
        }

    return formatted_canvas


def _get_fallback_bmc_blocks(startup: dict, val: dict | None) -> dict:
    """Fallback block generator when Gemini API is unavailable."""
    name = startup.get("name", "Startup")
    target = startup.get("target_market") or "Target Customers"
    sol = startup.get("solution", "Core Solution")

    return {
        "customer_segments": [
            f"Primary: {target}",
            "Early Adopters & Power Users",
            "Niche market pioneers"
        ],
        "value_propositions": [
            f"Automated solution for {sol[:60]}",
            "Cost & time reduction over legacy methods",
            "Streamlined workflow integration"
        ],
        "channels": [
            "Direct digital outreach & content inbound",
            "Targeted professional social channels",
            "Referral & word-of-mouth networks"
        ],
        "customer_relationships": [
            "Self-serve onboarding with guided tutorials",
            "Dedicated email & chat support",
            "Community feedback loop"
        ],
        "revenue_streams": [
            "Tiered monthly subscription plans",
            "Enterprise annual licenses",
            "Usage-based add-ons"
        ],
        "key_resources": [
            "Core technology platform & database",
            "Founding engineering & domain expertise",
            "User community & proprietary insights"
        ],
        "key_activities": [
            "Product development & iterative releases",
            "Customer acquisition & onboarding",
            "Infrastructure upkeep & security monitoring"
        ],
        "key_partnerships": [
            "Cloud infrastructure & API service providers",
            "Industry advisory mentors",
            "Distribution channel partners"
        ],
        "cost_structure": [
            "Cloud hosting & API infrastructure costs",
            "Sales & digital marketing expenses",
            "Product development & operational overhead"
        ]
    }


# ===================================================================
# NODE 2: Red Pen Audit Engine
# ===================================================================

AUDIT_SYSTEM = """You are an uncompromising, expert startup auditor known as the "Red Pen Auditor".

Your task is to inspect all 9 blocks of a Business Model Canvas and detect LOGICAL CONTRADICTIONS, OMISSION FLUTTERS, and MISALIGNMENTS.

Examples of issues to flag:
1. Enterprise target segment + TikTok or purely self-serve channels without justification.
2. High-touch white-glove enterprise service + sub-$10/month pricing.
3. Proprietary AI infrastructure listed as Key Resource + zero infrastructure or GPU costs in Cost Structure.
4. Revenue Stream not linked to any listed Customer Segment or Value Proposition.
5. Key Activities do not support the promised Value Proposition.
6. Moat claims that contradict a low defensibility score.

Calculate a health_score (0-100) based on severity and count of issues.
Return structured findings.

Respond with ONLY a JSON object:
{
    "health_score": 85,
    "conflicts": [
        {
            "severity": "warning",
            "blocks": ["channels", "customer_segments"],
            "title": "Channel/Segment Misalignment",
            "description": "...",
            "recommendation": "..."
        }
    ]
}"""


def red_pen_audit_node(canvas_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Runs deterministic + AI audit pass on the complete BMC canvas."""
    conflicts: List[AuditConflict] = []
    
    # Extract raw items per block
    block_items = {k: canvas_data.get(k, {}).get("items", []) for k in canvas_data}

    # 1. Deterministic Rule: Cost Floor Check
    # Ensure channels, key activities, key resources have cost mentions
    costs_str = " ".join(block_items.get("cost_structure", [])).lower()
    resources_str = " ".join(block_items.get("key_resources", [])).lower()
    channels_str = " ".join(block_items.get("channels", [])).lower()

    if any(term in resources_str or term in channels_str for term in ["cloud", "ml", "gpu", "paid ads", "outbound sales"]):
        if not any(cost_term in costs_str for cost_term in ["cloud", "server", "ad", "marketing", "sales", "infra", "hosting", "tooling"]):
            conflicts.append(AuditConflict(
                severity="warning",
                blocks=["key_resources", "channels", "cost_structure"],
                title="Missing Resource/Channel Cost Coverage",
                description="Resource or Channel items (e.g., infrastructure/paid outreach) lack corresponding cost line items in Cost Structure.",
                recommendation="Add explicit hosting, infrastructure, or marketing tooling line items to Cost Structure."
            ))

    # 2. Deterministic Rule: Moat Contradiction Check
    val_data = context.get("validation_data")
    if val_data:
        moat_score = val_data.get("dimension_scores", {}).get("moat", 50)
        res_str = " ".join(block_items.get("key_resources", [])).lower()
        if moat_score < 30 and any(m in res_str for m in ["patent", "proprietary ip", "unbeatable moat", "defensible tech"]):
            conflicts.append(AuditConflict(
                severity="error",
                blocks=["key_resources"],
                title="Low Moat Score Contradiction",
                description="Key Resources claims proprietary IP/patented moat despite low defensibility score (<30) from validation.",
                recommendation="Replace proprietary IP claims with execution-based advantages like speed-to-market or concierge onboarding."
            ))

    # 3. AI Reasoning Audit Pass
    prompt = f"""Audit this 9-block Business Model Canvas for logical contradictions and misalignments:

CANVAS DATA:
{json.dumps(block_items, indent=2)}

VALIDATION SCORES:
{json.dumps(val_data.get('dimension_scores', {}) if val_data else {})}

Analyze inter-block consistency and return ONLY the JSON result."""

    try:
        raw_text = _call_gemini(AUDIT_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        report = BMCAuditReport(**parsed)

        # Merge deterministic conflicts into report
        merged_conflicts = list(report.conflicts) + conflicts
        # Deduplicate conflicts by title
        seen_titles = set()
        final_conflicts = []
        for c in merged_conflicts:
            if c.title not in seen_titles:
                seen_titles.add(c.title)
                final_conflicts.append(c)

        # Adjust health score if deterministic error triggered
        final_health = min(report.health_score, 100 - (len(final_conflicts) * 8))
        final_health = max(0, min(100, final_health))

        return {
            "health_score": final_health,
            "conflicts": [c.model_dump() for c in final_conflicts]
        }
    except Exception as e:
        logger.warning("Red Pen Audit AI call failed (%s), using fallback heuristic audit.", e)

    base_health = 85 if not conflicts else 72
    return {
        "health_score": base_health,
        "conflicts": [c.model_dump() for c in conflicts]
    }


# ===================================================================
# NODE 3: Single Block Regeneration
# ===================================================================

REGEN_SYSTEM = """You are a business model expert. Your task is to REGENERATE A SINGLE BLOCK of a Business Model Canvas.

You are provided with:
1. The target block to regenerate.
2. The current content of all other 8 blocks.
3. The startup context and validation insights.
4. Optional custom instructions from the founder.

RULES:
- Return 3 to 5 concise bullet points ONLY for the target block.
- Keep the new items strictly aligned with the other 8 blocks.
- Respect inter-block dependency rules (Cost Floor Rule, Revenue Origin Rule, Value Alignment).

Respond with ONLY a JSON object:
{
    "items": ["...", "...", "..."]
}"""


def regenerate_single_block_node(
    block_name: str,
    canvas_data: Dict[str, Any],
    context: Dict[str, Any],
    custom_instructions: str | None = None
) -> List[str]:
    """Regenerates bullet points for a single block while keeping remaining canvas consistent."""
    startup = context["startup_data"]
    val = context.get("validation_data")

    current_blocks = {k: canvas_data.get(k, {}).get("items", []) for k in canvas_data if k != block_name}

    prompt = f"""Regenerate the block '{block_name}' for this Business Model Canvas.

STARTUP: {startup.get('name')} — {startup.get('solution')}
TARGET MARKET: {startup.get('target_market')}

OTHER 8 CANVAS BLOCKS FOR CONTEXT:
{json.dumps(current_blocks, indent=2)}

CUSTOM INSTRUCTIONS FROM FOUNDER:
{custom_instructions or 'None'}

Generate 3-5 concise bullet points for '{block_name}'. Respond with ONLY JSON: {{"items": [...]}}"""

    try:
        raw_text = _call_gemini(REGEN_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        items = parsed.get("items", [])
        if isinstance(items, list) and len(items) >= 1:
            return [str(it).strip() for it in items]
    except Exception as e:
        logger.warning("Single block regen AI call failed (%s), using fallback items.", e)

    # Fallback default items
    return canvas_data.get(block_name, {}).get("items", ["Updated industry standard point"])
