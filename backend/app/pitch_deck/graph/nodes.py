"""
Gemini and deterministic nodes for Pitch Deck generation, Red Pen Auditor engine, and slide regeneration.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config import settings
from app.pitch_deck.schemas import (
    SlideSchema,
    PitchDeckAuditReport,
    AuditWarning,
)

logger = logging.getLogger(__name__)

MODEL_CANDIDATES = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-pro",
    "gemini-pro-latest",
]


def _configure_genai() -> None:
    """Ensure Gemini client is configured."""
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Call Gemini API with model candidate fallbacks."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

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


def _extract_json(text: str) -> Any:
    """Extract JSON array or object from markdown fences or raw text."""
    fence_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
    if fence_match:
        text = fence_match.group(1)

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        bracket_match = re.search(r"\[[\s\S]*\]", text)
        if bracket_match:
            return json.loads(bracket_match.group(0))
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            return json.loads(brace_match.group(0))
        raise ValueError(f"Could not extract JSON from Gemini response:\n{text[:500]}")


# ===================================================================
# GROUP A: NARRATIVE + MARKET (SLIDES 1 to 5)
# ===================================================================

GROUP_A_SYSTEM = """You are a top-tier Venture Capital pitch deck designer creating Slides 1 to 5 of an investor pitch deck.

STRICT ANTI-HALLUCINATION & CONSISTENCY RULES:
1. Ground every claim in provided context. Do NOT invent fake customers, fake market statistics, or fake revenue figures.
2. Slide 2 (Problem): If Problem Score < 50, frame problem as workflow friction/inconvenience. If >= 50, frame as operational/financial pain.
3. Slide 4 (Why Now?): Do NOT invent market numbers. If statistics are absent, explicitly state that trend evidence requires further validation.
4. Slide 5 (Market Opportunity): Use Business Plan TAM/SAM/SOM if present. If no numeric market data exists, output "Market sizing requires further validation."
5. Output ONLY a valid JSON array of 5 Slide objects matching the requested schema.
"""


def generate_group_a_slides(context: Dict[str, Any], custom_instructions: Optional[str] = None) -> List[Dict[str, Any]]:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bp = context.get("business_plan_data", {})
    val_score = context.get("validation_score", 50.0)
    is_validation_mode = context.get("is_validation_mode", False)

    prompt = f"""Generate Slides 1 to 5 for pitch deck of startup '{startup.get('name')}'.

CONTEXT DATA:
- Startup Name: {startup.get('name')}
- Tagline: {startup.get('tagline')}
- Industry: {startup.get('industry')}
- Problem: {startup.get('problem')}
- Solution: {startup.get('solution')}
- Target Market: {startup.get('target_market')}
- Validation Score: {val_score}/100
- Problem Score: {val.get('dimension_scores', {}).get('problem', 50)}/100
- Buyer Score: {val.get('dimension_scores', {}).get('buyer', 50)}/100
- Buyer Critique: {json.dumps(val.get('agent_buyer', {}))}
- Business Plan Market Domain: {json.dumps(bp.get('domains_data', {}).get('market_customer', {}))}
- Is Validation Mode Active (<50 score): {is_validation_mode}
- Custom Instructions: {custom_instructions or 'None'}

Return ONLY a JSON array with EXACTLY 5 objects corresponding to Slide 1, Slide 2, Slide 3, Slide 4, and Slide 5.
Each object schema:
{{
  "slide_number": 1,
  "slide_type": "cover",
  "title": "...",
  "subtitle": "...",
  "content": "...",
  "key_points": ["...", "..."],
  "visual_type": "hero_badge",
  "visual_data": {{...}},
  "icon_names": ["rocket", "target"],
  "source_context": "Startup Workspace",
  "warnings": []
}}"""

    try:
        raw_text = _call_gemini(GROUP_A_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        if isinstance(parsed, list) and len(parsed) == 5:
            slides = [SlideSchema(**item).model_dump() for item in parsed]
            return slides
    except Exception as e:
        logger.warning("Group A AI slide generation failed (%s), using fallbacks.", e)

    return _fallback_group_a(startup, val, bp, val_score, is_validation_mode)


# ===================================================================
# GROUP B: PRODUCT + BUSINESS + GTM + COMPETITION + MOAT (SLIDES 6 to 10)
# ===================================================================

GROUP_B_SYSTEM = """You are a venture strategist creating Slides 6 to 10 of an investor pitch deck.

STRICT ANTI-HALLUCINATION & MOAT RULES:
1. Slide 6 (Product Workflow): Create a clean 3-step workflow (Input -> Processing -> Outcome) based on BMC Key Activities.
2. Slide 7 (Business Model): Use BMC Revenue Streams. Do NOT invent pricing if founder has not provided it.
3. Slide 8 (Go-To-Market): Align GTM with Buyer Viability Score and BMC Channels (Acquisition -> Conversion -> Onboarding -> Retention).
4. Slide 9 (Competition): Use Validation Competitor Agent. Do NOT invent fake competitors. Include status quo & manual workarounds.
5. Slide 10 (Defensive Moat): STRICT RULE: If Moat Score < 30, strictly block claims of "proprietary technology", "unbeatable AI", or "patented moat". Emphasize speed, niche focus, workflow integration, or customer relationships.
6. Output ONLY a valid JSON array of 5 Slide objects matching the requested schema.
"""


def generate_group_b_slides(context: Dict[str, Any], custom_instructions: Optional[str] = None) -> List[Dict[str, Any]]:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bmc = context.get("bmc_data", {})
    bp = context.get("business_plan_data", {})
    moat_score = val.get("dimension_scores", {}).get("moat", 50)

    prompt = f"""Generate Slides 6 to 10 for pitch deck of startup '{startup.get('name')}'.

CONTEXT DATA:
- Solution: {startup.get('solution')}
- BMC Channels: {json.dumps(bmc.get('canvas_blocks', {}).get('channels', []))}
- BMC Revenue Streams: {json.dumps(bmc.get('canvas_blocks', {}).get('revenue_streams', []))}
- BMC Key Activities: {json.dumps(bmc.get('canvas_blocks', {}).get('key_activities', []))}
- BMC Key Resources: {json.dumps(bmc.get('canvas_blocks', {}).get('key_resources', []))}
- Validation Moat Score: {moat_score}/100
- Validation Competitor Agent: {json.dumps(val.get('agent_competitor', {}))}
- Business Plan GTM & Ops Domain: {json.dumps(bp.get('domains_data', {}).get('gtm_operations', {}))}
- Custom Instructions: {custom_instructions or 'None'}

Return ONLY a JSON array with EXACTLY 5 objects corresponding to Slide 6, Slide 7, Slide 8, Slide 9, and Slide 10.
"""

    try:
        raw_text = _call_gemini(GROUP_B_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        if isinstance(parsed, list) and len(parsed) == 5:
            slides = [SlideSchema(**item).model_dump() for item in parsed]
            # Post-validate moat score rule
            if moat_score < 30:
                s10 = slides[4]  # Slide 10
                moat_str = (s10.get("content", "") + " " + " ".join(s10.get("key_points", []))).lower()
                if any(kw in moat_str for kw in ["proprietary", "unbeatable", "patented", "insurmountable"]):
                    s10["content"] = "Defensibility is driven by rapid execution, tailored customer onboarding, and deep workflow integration."
                    s10["key_points"] = [
                        "Execution Speed & Agile Product Iteration",
                        "Niche Specialization for Target Workflows",
                        "Customer Relationship & Workflow Lock-in"
                    ]
                    s10["warnings"] = ["Moat score <30: Avoided unsupported proprietary IP claims."]
            return slides
    except Exception as e:
        logger.warning("Group B AI slide generation failed (%s), using fallbacks.", e)

    return _fallback_group_b(startup, val, bmc, bp, moat_score)


# ===================================================================
# GROUP C: VALIDATION + ECONOMICS + TEAM/ASK (SLIDES 11 to 13)
# ===================================================================

GROUP_C_SYSTEM = """You are a venture capital advisor creating Slides 11 to 13 of an investor pitch deck.

STRICT ANTI-HALLUCINATION RULES:
1. Slide 11 (Validation / Traction): STRICT RULE — Do NOT invent fake users, fake MRR, fake growth %, or fake customer numbers. If pre-revenue/pre-traction, show Validation Status, LOFA, Mom Test Questions, and Kill Threshold. Wording MUST state: "Pre-revenue — customer validation in progress."
2. Slide 12 (Unit Economics): Show CAC/LTV logic, margin assumptions, and break-even mechanics. Do NOT generate fake 5-year financial projections (Year 1 Revenue = $X, Year 5 = $Y).
3. Slide 13 (Team & Ask): Use actual founder/team info. Do NOT invent a funding amount if unstated ("Ask: Not specified"). IF Validation Score < 50, change slide purpose to "Validation & Early Prototyping Ask".
4. Output ONLY a valid JSON array of 3 Slide objects matching the requested schema.
"""


def generate_group_c_slides(context: Dict[str, Any], custom_instructions: Optional[str] = None) -> List[Dict[str, Any]]:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bmc = context.get("bmc_data", {})
    bp = context.get("business_plan_data", {})
    val_score = context.get("validation_score", 50.0)
    is_validation_mode = context.get("is_validation_mode", False)

    prompt = f"""Generate Slides 11 to 13 for pitch deck of startup '{startup.get('name')}'.

CONTEXT DATA:
- Founder Info: {json.dumps(startup.get('founder', {}))}
- Startup Stage: {startup.get('stage')}
- Validation Score: {val_score}/100
- Is Validation Mode Active (<50 score): {is_validation_mode}
- LOFA: {val.get('lofa', 'N/A')}
- Mom Test Questions: {json.dumps(val.get('mom_test_questions', []))}
- Kill Threshold: {val.get('kill_threshold', 'N/A')}
- BMC Cost Structure: {json.dumps(bmc.get('canvas_blocks', {}).get('cost_structure', []))}
- Business Plan Financial Domain: {json.dumps(bp.get('domains_data', {}).get('financial_structure', {}))}
- Custom Instructions: {custom_instructions or 'None'}

Return ONLY a JSON array with EXACTLY 3 objects corresponding to Slide 11, Slide 12, and Slide 13.
"""

    try:
        raw_text = _call_gemini(GROUP_C_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        if isinstance(parsed, list) and len(parsed) == 3:
            slides = [SlideSchema(**item).model_dump() for item in parsed]
            return slides
    except Exception as e:
        logger.warning("Group C AI slide generation failed (%s), using fallbacks.", e)

    return _fallback_group_c(startup, val, bmc, bp, val_score, is_validation_mode)


# ===================================================================
# RED PEN AUDITOR PASS
# ===================================================================

AUDITOR_SYSTEM = """You are an uncompromising startup pitch deck auditor called the "Red Pen Auditor".

Your task is to audit a 13-slide pitch deck against upstream Workspace, Validation Report, BMC, and Business Plan context to flag CONTRADICTIONS, MISALIGNMENTS, and FABRICATIONS.

CHECK LIST:
1. Moat Exaggeration: Validation Moat Score < 30 but deck claims "unbeatable proprietary tech / patent moat" -> HIGH severity.
2. Target Customer Mismatch: Workspace says SMBs but deck claims Fortune 500 enterprise -> HIGH severity.
3. GTM / Cost Mismatch: Deck claims enterprise sales team but BMC omits sales payroll/costs -> MEDIUM severity.
4. Fake Traction: Deck claims 10k users / MRR without source -> HIGH severity.
5. Fake Financial Forecasts: Deck invents 5-year revenue forecasts -> HIGH severity.

Return structured JSON object matching health_score and warnings list.
"""


def run_pitch_deck_audit(
    context: Dict[str, Any],
    slides: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Inspects all 13 slides for contradictions and anti-hallucination compliance."""
    warnings: List[AuditWarning] = []
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bmc = context.get("bmc_data", {})
    val_score = context.get("validation_score", 50.0)

    # 1. Deterministic Rule 1: Moat contradiction check
    moat_score = val.get("dimension_scores", {}).get("moat", 50)
    slide10 = next((s for s in slides if s.get("slide_number") == 10), None)
    if slide10 and moat_score < 30:
        text10 = (slide10.get("content", "") + " " + " ".join(slide10.get("key_points", []))).lower()
        if any(kw in text10 for kw in ["proprietary", "unbeatable", "patented", "insurmountable"]):
            warnings.append(AuditWarning(
                severity="HIGH",
                slide_number=10,
                category="Moat Contradiction",
                issue="Slide 10 claims proprietary IP or unbeatable technology despite a low validation moat score (<30).",
                original_claim=slide10.get("content", "")[:120],
                recommended_fix="Reframe defensibility around execution speed, workflow integration, and customer relationships.",
                auto_fixed=True
            ))
            # Auto-rewrite Slide 10 content
            slide10["content"] = "Defensibility is grounded in execution speed, specialized workflow integration, and customer feedback velocity."
            slide10["key_points"] = [
                "Agile Development & Rapid Feature Delivery",
                "Deep Integration with Target Customer Workflows",
                "Strong Early Customer Relationships & Direct Support"
            ]

    # 2. Deterministic Rule 2: Customer segment mismatch check
    workspace_target = str(startup.get("target_market", "")).lower()
    slide2 = next((s for s in slides if s.get("slide_number") == 2), None)
    if slide2 and any(smb in workspace_target for smb in ["small business", "smb", "student", "individual"]):
        text2 = (slide2.get("content", "") + " " + " ".join(slide2.get("key_points", []))).lower()
        if any(ent in text2 for ent in ["fortune 500", "large enterprise", "global conglomerate"]):
            warnings.append(AuditWarning(
                severity="HIGH",
                slide_number=2,
                category="Customer Mismatch",
                issue="Slide 2 claims target customer is Fortune 500 enterprises, conflicting with SMB workspace target.",
                original_claim=slide2.get("content", "")[:120],
                recommended_fix="Align ICP strictly with the validated target market in the workspace.",
                auto_fixed=True
            ))
            slide2["content"] = slide2["content"].replace("Fortune 500 enterprises", "target SMB decision makers")

    # 3. Deterministic Rule 3: Traction hallucination check
    slide11 = next((s for s in slides if s.get("slide_number") == 11), None)
    if slide11:
        text11 = (slide11.get("content", "") + " " + " ".join(slide11.get("key_points", []))).lower()
        if any(fake in text11 for fake in ["10,000 active users", "$100k mrr", "50 enterprise pilots", "$1m arr"]):
            warnings.append(AuditWarning(
                severity="HIGH",
                slide_number=11,
                category="Fake Traction",
                issue="Slide 11 claims fabricated metrics (MRR/users) not present in verified startup context.",
                original_claim=slide11.get("content", "")[:120],
                recommended_fix="Replace manufactured metrics with current validation progress and Mom Test milestones.",
                auto_fixed=True
            ))
            slide11["content"] = "Pre-revenue — customer discovery and validation in active progress."
            slide11["key_points"] = [
                f"Validation Score: {val_score:.0f}/100",
                f"LOFA: {val.get('lofa', 'Key assumption under discovery')}",
                "Active Mom Test customer discovery interviews underway"
            ]

    # Calculate overall health score
    high_count = sum(1 for w in warnings if w.severity == "HIGH")
    med_count = sum(1 for w in warnings if w.severity == "MEDIUM")
    health_score = max(0, 100 - (high_count * 20 + med_count * 10))

    return {
        "health_score": health_score,
        "warnings": [w.model_dump() for w in warnings]
    }


# ===================================================================
# REGENERATE SINGLE SLIDE NODE
# ===================================================================

def regenerate_single_slide_node(
    slide_number: int,
    context: Dict[str, Any],
    existing_slides: List[Dict[str, Any]],
    custom_instructions: Optional[str] = None
) -> Dict[str, Any]:
    """Regenerates a single specific slide while preserving the other 12 slides."""
    if slide_number < 1 or slide_number > 13:
        raise ValueError("Slide number must be between 1 and 13.")

    # Determine which group the slide belongs to
    if 1 <= slide_number <= 5:
        group = generate_group_a_slides(context, custom_instructions)
        target = next((s for s in group if s["slide_number"] == slide_number), None)
    elif 6 <= slide_number <= 10:
        group = generate_group_b_slides(context, custom_instructions)
        target = next((s for s in group if s["slide_number"] == slide_number), None)
    else:
        group = generate_group_c_slides(context, custom_instructions)
        target = next((s for s in group if s["slide_number"] == slide_number), None)

    if not target:
        # Fallback to single slide deterministic generator
        target = _fallback_single_slide(slide_number, context, custom_instructions)

    return target


# ===================================================================
# FALLBACK GENERATORS (WHEN GEMINI API IS UNAVAILABLE)
# ===================================================================

def _fallback_group_a(startup: dict, val: dict, bp: dict, val_score: float, is_val_mode: bool) -> List[dict]:
    prob_score = val.get("dimension_scores", {}).get("problem", 50)
    prob_severity = "significant operational friction and costs" if prob_score >= 50 else "workflow inconvenience and inefficiency"

    s1 = {
        "slide_number": 1,
        "slide_type": "cover",
        "title": startup.get("name", "Venture AI Startup"),
        "subtitle": startup.get("tagline") or f"Transforming {startup.get('industry', 'the industry')} with innovative solutions.",
        "content": f"{startup.get('name')} provides an automated solution tailored for {startup.get('target_market', 'target customers')}.",
        "key_points": [
            f"Industry: {startup.get('industry', 'Technology')}",
            f"Stage: {startup.get('stage', 'Idea')}",
            f"Target Market: {startup.get('target_market', 'Target Audience')}"
        ],
        "visual_type": "hero_badge",
        "visual_data": {
            "badge": startup.get("stage", "Idea"),
            "category": startup.get("industry", "SaaS"),
            "tagline": startup.get("tagline", "Innovative Startup Platform")
        },
        "icon_names": ["rocket", "sparkles", "target"],
        "source_context": "Startup Workspace",
        "warnings": []
    }

    s2 = {
        "slide_number": 2,
        "slide_type": "problem",
        "title": "The Problem",
        "subtitle": f"Target customers experience {prob_severity}.",
        "content": startup.get("problem", "Current workflows are manual, fragmented, and inefficient."),
        "key_points": [
            f"Problem Severity Score: {prob_score}/100",
            "High time lost on repetitive manual execution",
            "Lack of specialized automated tools"
        ],
        "visual_type": "stat_callout",
        "visual_data": {
            "metric_value": f"{prob_score}/100",
            "metric_label": "Problem Score",
            "description": "Validation assessment of pain point severity."
        },
        "icon_names": ["alert-triangle", "clock", "frown"],
        "source_context": "Workspace + Validation Report",
        "warnings": []
    }

    s3 = {
        "slide_number": 3,
        "slide_type": "solution",
        "title": "The Solution",
        "subtitle": "Streamlined, outcome-focused intelligent automation.",
        "content": startup.get("solution", "An intuitive platform designed to automate core workflows."),
        "key_points": [
            "Dramatically reduces operational time",
            "Provides intelligent automated guidance",
            "Seamless onboarding for early adopters"
        ],
        "visual_type": "grid_cards",
        "visual_data": {
            "cards": [
                {"title": "Automated Processing", "desc": "Eliminates repetitive manual steps."},
                {"title": "Instant Insights", "desc": "Delivers real-time strategic recommendations."},
                {"title": "Seamless Workflow", "desc": "Integrates directly into existing routines."}
            ]
        },
        "icon_names": ["check-circle", "zap", "shield-check"],
        "source_context": "Workspace + BMC Value Proposition",
        "warnings": []
    }

    s4 = {
        "slide_number": 4,
        "slide_type": "why_now",
        "title": "Why Now?",
        "subtitle": "Convergence of tech shifts and changing customer expectations.",
        "content": "Rapid advancements in modern technology and cloud adoption make workflow automation faster and cheaper than ever.",
        "key_points": [
            "Accelerating adoption of digital workflow solutions",
            "Growing demand for cost-efficient SaaS tooling",
            "Trend evidence requires ongoing market validation"
        ],
        "visual_type": "list_badges",
        "visual_data": {
            "items": [
                "Technological Shift: Rapid AI API accessibility",
                "Customer Behavior: Shift toward self-serve tools",
                "Market Need: Focus on operational efficiency"
            ]
        },
        "icon_names": ["trending-up", "cpu", "calendar"],
        "source_context": "Business Plan Market Analysis",
        "warnings": ["No fabricated stats included."]
    }

    s5 = {
        "slide_number": 5,
        "slide_type": "market",
        "title": "Market Opportunity",
        "subtitle": "Addressable market driven by workflow digital transformation.",
        "content": "Targeting early adopter segments seeking rapid software deployment.",
        "key_points": [
            "Target Segment: " + (startup.get("target_market") or "Specialized Industry Professionals"),
            "Market sizing requires further empirical validation",
            "Initial focus on high-intent niche customers"
        ],
        "visual_type": "tam_sam_som",
        "visual_data": {
            "tam": "Broader Industry Market",
            "sam": "Serviceable Segment",
            "som": "Initial Early Adopter Target",
            "note": "Market sizing requires further validation."
        },
        "icon_names": ["globe", "pie-chart", "users"],
        "source_context": "Business Plan Market Domain",
        "warnings": ["Numeric market stats require empirical validation."]
    }

    return [s1, s2, s3, s4, s5]


def _fallback_group_b(startup: dict, val: dict, bmc: dict, bp: dict, moat_score: float) -> List[dict]:
    s6 = {
        "slide_number": 6,
        "slide_type": "product_workflow",
        "title": "Product Workflow",
        "subtitle": "Simple 3-step operational process.",
        "content": "A seamless end-to-end user experience transforming raw inputs into strategic outcomes.",
        "key_points": [
            "Step 1: Input startup parameters and goals",
            "Step 2: Intelligent processing engine runs analysis",
            "Step 3: Actionable output and structured recommendations delivered"
        ],
        "visual_type": "three_step_flow",
        "visual_data": {
            "steps": [
                {"step": "1", "title": "Input", "desc": "Founder enters core workspace information."},
                {"step": "2", "title": "VentureAI Processing", "desc": "Multi-agent evaluation & synthesis."},
                {"step": "3", "title": "Outcome", "desc": "Investor-ready structured artifact delivered."}
            ]
        },
        "icon_names": ["input", "cpu", "award"],
        "source_context": "BMC Key Activities & Solution",
        "warnings": []
    }

    rev_streams = bmc.get("canvas_blocks", {}).get("revenue_streams", ["Subscription SaaS"])
    if isinstance(rev_streams, list):
        rev_str = ", ".join(rev_streams[:2])
    else:
        rev_str = str(rev_streams)

    s7 = {
        "slide_number": 7,
        "slide_type": "business_model",
        "title": "Business Model",
        "subtitle": f"Monetization model: {rev_str}.",
        "content": "Value-driven subscription pricing tailored for target customer ROI.",
        "key_points": [
            f"Primary Revenue Stream: {rev_str}",
            "Scalable tier structure based on feature access",
            "Pricing structure grounded in validated customer willingness to pay"
        ],
        "visual_type": "grid_cards",
        "visual_data": {
            "cards": [
                {"title": "Monetization", "desc": rev_str},
                {"title": "Billing Mechanism", "desc": "Recurring SaaS subscription"},
                {"title": "Value Metric", "desc": "Usage & seat-based tiers"}
            ]
        },
        "icon_names": ["dollar-sign", "credit-card", "repeat"],
        "source_context": "BMC Revenue Streams",
        "warnings": []
    }

    channels = bmc.get("canvas_blocks", {}).get("channels", ["Digital Ads", "Organic Content"])
    if isinstance(channels, list):
        chan_str = ", ".join(channels[:2])
    else:
        chan_str = str(channels)

    s8 = {
        "slide_number": 8,
        "slide_type": "gtm",
        "title": "Go-To-Market",
        "subtitle": f"Acquisition channels: {chan_str}.",
        "content": "Targeted customer acquisition pipeline aligned with buyer persona.",
        "key_points": [
            f"Primary Acquisition: {chan_str}",
            "Onboarding: Self-guided digital experience",
            "Retention: Proactive customer success and feature updates"
        ],
        "visual_type": "funnel_steps",
        "visual_data": {
            "stages": [
                {"stage": "Acquisition", "desc": chan_str},
                {"stage": "Conversion", "desc": "Free tier / trial demo"},
                {"stage": "Onboarding", "desc": "Interactive walk-through"},
                {"stage": "Retention", "desc": "Value reinforcement"}
            ]
        },
        "icon_names": ["share-2", "user-plus", "heart"],
        "source_context": "BMC Channels & GTM Domain",
        "warnings": []
    }

    s9 = {
        "slide_number": 9,
        "slide_type": "competition",
        "title": "Competition",
        "subtitle": "Positioned against legacy options and status quo.",
        "content": "Differentiating through speed, specialized focus, and lower total cost of ownership.",
        "key_points": [
            "Direct: Legacy domain software tools",
            "Indirect: General-purpose spreadsheets and manual workarounds",
            "Advantage: Built-in intelligence and tailored workflow focus"
        ],
        "visual_type": "matrix",
        "visual_data": {
            "categories": [
                {"name": "Status Quo", "weakness": "Time-consuming manual effort"},
                {"name": "Legacy Tools", "weakness": "High cost & complex setup"},
                {"name": "VentureAI Solution", "weakness": "Agile, automated & affordable"}
            ]
        },
        "icon_names": ["shield", "crosshair", "layers"],
        "source_context": "Validation Competitor Agent",
        "warnings": []
    }

    moat_claim = "Defensibility built on execution velocity, niche specialization, and deep customer workflow integration." if moat_score < 30 else "Defensibility supported by specialized workflow integration and data feedback loops."
    s10 = {
        "slide_number": 10,
        "slide_type": "defensive_moat",
        "title": "Defensive Moat",
        "subtitle": f"Validation Moat Score: {moat_score:.0f}/100",
        "content": moat_claim,
        "key_points": [
            "Rapid execution and customer feedback loops",
            "Specialized niche workflow integration",
            "First-mover advantage in targeted sub-segment"
        ],
        "visual_type": "grid_cards",
        "visual_data": {
            "moat_score": f"{moat_score:.0f}/100",
            "pillars": ["Execution Speed", "Workflow Lock-in", "Niche Focus"]
        },
        "icon_names": ["lock", "zap", "check-square"],
        "source_context": "Validation Moat Score",
        "warnings": ["Moat score <30: Focused on execution speed rather than IP."] if moat_score < 30 else []
    }

    return [s6, s7, s8, s9, s10]


def _fallback_group_c(startup: dict, val: dict, bmc: dict, bp: dict, val_score: float, is_val_mode: bool) -> List[dict]:
    lofa = val.get("lofa", "Target customers are willing to adopt automated platform.")

    s11 = {
        "slide_number": 11,
        "slide_type": "validation_traction",
        "title": "Validation & Traction",
        "subtitle": "Pre-revenue — customer validation in progress.",
        "content": "Current focus is on falsifying leap-of-faith assumptions via structured discovery.",
        "key_points": [
            f"Overall Validation Score: {val_score:.0f}/100",
            f"Leap-of-Faith Assumption: {lofa}",
            "Active Mom Test customer discovery interviews in progress"
        ],
        "visual_type": "blueprint_list",
        "visual_data": {
            "status": "Pre-revenue — customer validation in progress",
            "score": f"{val_score:.0f}/100",
            "lofa": lofa,
            "questions": val.get("mom_test_questions", ["How do you solve this currently?", "What is your main pain point?"])
        },
        "icon_names": ["check-square", "search", "help-circle"],
        "source_context": "Idea Validation Report",
        "warnings": ["Pre-revenue status enforced — no fake traction."]
    }

    s12 = {
        "slide_number": 12,
        "slide_type": "unit_economics",
        "title": "Unit Economics",
        "subtitle": "Lean cost structure focused on positive contribution margins.",
        "content": "Unit economics framework prioritizing low fixed overhead and efficient CAC payback.",
        "key_points": [
            "Gross Margin Goal: 75%+ for SaaS tier",
            "Target LTV/CAC Ratio: 3.0x upon scaling",
            "Break-even logic based on fixed hosting & acquisition cost coverage"
        ],
        "visual_type": "grid_cards",
        "visual_data": {
            "metrics": [
                {"label": "Target LTV/CAC", "value": "3.0x"},
                {"label": "Estimated Gross Margin", "value": "75%+"},
                {"label": "Break-even Logic", "value": "Cover fixed costs"}
            ]
        },
        "icon_names": ["bar-chart-2", "trending-up", "calculator"],
        "source_context": "BMC Cost Structure & BP Financials",
        "warnings": ["No manufactured 5-year revenue forecasts."]
    }

    ask_title = "Validation & Early Prototyping Ask" if is_val_mode else "Team & The Ask"
    s13 = {
        "slide_number": 13,
        "slide_type": "team_ask",
        "title": ask_title,
        "subtitle": f"Founder: {startup.get('founder', {}).get('name', 'Founder')} · Stage: {startup.get('stage', 'Idea')}",
        "content": "Seeking validation partners, early pilot cohort users, and strategic feedback." if is_val_mode else "Resource allocation directed toward customer discovery and product iteration.",
        "key_points": [
            f"Founder: {startup.get('founder', {}).get('name', 'Founder')}",
            f"Current Stage: {startup.get('stage', 'Idea')}",
            "Funding Requirement: Ask: Not specified"
        ],
        "visual_type": "hero_badge",
        "visual_data": {
            "founder_name": startup.get("founder", {}).get("name", "Founder"),
            "stage": startup.get("stage", "Idea"),
            "ask_amount": "Not specified",
            "next_milestone": "Complete pilot cohort onboarding"
        },
        "icon_names": ["user", "flag", "compass"],
        "source_context": "Workspace Founder Info",
        "warnings": ["Funding requirement unstated — Ask set to Not Specified."]
    }

    return [s11, s12, s13]


def _fallback_single_slide(slide_number: int, context: Dict[str, Any], custom_instructions: Optional[str] = None) -> dict:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bmc = context.get("bmc_data", {})
    bp = context.get("business_plan_data", {})
    val_score = context.get("validation_score", 50.0)
    is_val_mode = context.get("is_validation_mode", False)
    moat_score = val.get("dimension_scores", {}).get("moat", 50)

    if 1 <= slide_number <= 5:
        slides = _fallback_group_a(startup, val, bp, val_score, is_val_mode)
    elif 6 <= slide_number <= 10:
        slides = _fallback_group_b(startup, val, bmc, bp, moat_score)
    else:
        slides = _fallback_group_c(startup, val, bmc, bp, val_score, is_val_mode)

    slide = next((s for s in slides if s["slide_number"] == slide_number), slides[0])
    if custom_instructions:
        slide["content"] += f" (Custom note: {custom_instructions[:60]})"
    return slide
