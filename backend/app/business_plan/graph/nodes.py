"""
Gemini and deterministic nodes for Business Plan domain generation, Executive Summary synthesis,
Red Pen audit engine, and section regeneration.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config import settings
from app.business_plan.schemas import (
    MarketCustomerDomain,
    BusinessModelDomain,
    GtmOperationsDomain,
    FinancialStructureDomain,
    RiskValidationLegalDomain,
    ExecutiveSummarySchema,
    BusinessPlanAuditReport,
    AuditWarning,
)

logger = logging.getLogger(__name__)

# Model candidates for Gemini API calls
MODEL_CANDIDATES = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-pro",
    "gemini-pro-latest",
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
# DOMAIN 1: MARKET & CUSTOMER
# ===================================================================

DOMAIN1_SYSTEM = """You are a senior startup strategist and market analyst creating Domain 1 (Market & Customer) of a formal Business Plan.

RULES FOR DOMAIN 1:
1. STRICT DATA CONSISTENCY: Respect upstream validation scores and workspace problem/solution. If problem score is low, do NOT exaggerate problem severity.
2. NO FAKE NUMBERS: Do NOT fabricate precise market dollar figures or stats unless explicitly present in context. If stats are absent, explicitly state that figures require external validation/market research.
3. PIVOT MODE AWARENESS: If is_pivot_mode is True, emphasize buyer hesitation, market uncertainty, and unvalidated customer assumptions.
4. Output structured JSON matching the requested schema exactly."""


def generate_domain_market_customer(context: Dict[str, Any], custom_instructions: Optional[str] = None) -> Dict[str, Any]:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bmc = context.get("bmc_data", {})
    is_pivot = context.get("is_pivot_mode", False)

    prompt = f"""Generate Domain 1 (Market & Customer) for startup '{startup.get('name')}'.

STARTUP WORKSPACE:
- Problem: {startup.get('problem')}
- Solution: {startup.get('solution')}
- Target Market: {startup.get('target_market')}
- Industry: {startup.get('industry')}

VALIDATION INSIGHTS:
- Overall Validation Score: {val.get('final_validation_score')}/100
- Problem Score: {val.get('dimension_scores', {}).get('problem')}/100
- Buyer Score: {val.get('dimension_scores', {}).get('buyer')}/100
- Moat Score: {val.get('dimension_scores', {}).get('moat')}/100
- LOFA: {val.get('lofa')}
- Key Risks: {json.dumps(val.get('key_risks', []))}

BMC CANVAS CONTEXT:
- Customer Segments: {json.dumps(bmc.get('canvas_blocks', {}).get('customer_segments', []))}
- Value Propositions: {json.dumps(bmc.get('canvas_blocks', {}).get('value_propositions', []))}

IS PIVOT MODE ACTIVE: {is_pivot}
FOUNDER CUSTOM REGENERATION INSTRUCTIONS: {custom_instructions or 'None'}

Respond with ONLY a JSON object matching this exact schema:
{{
    "problem_analysis": "...",
    "problem_severity_note": "...",
    "icp_definition": "...",
    "target_customer_characteristics": ["...", "..."],
    "buyer_persona": "...",
    "customer_pain_points": ["...", "..."],
    "market_opportunity": "...",
    "tam_sam_som_drivers": ["...", "..."],
    "market_growth_drivers": ["...", "..."],
    "market_limitations": ["...", "..."],
    "direct_competitors": ["...", "..."],
    "indirect_competitors": ["...", "..."],
    "existing_alternatives": ["...", "..."],
    "competitive_positioning": "...",
    "defensibility_moat": "..."
}}"""

    try:
        raw_text = _call_gemini(DOMAIN1_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        validated = MarketCustomerDomain(**parsed)
        return validated.model_dump()
    except Exception as e:
        logger.warning("Domain 1 AI generation failed (%s), using fallback.", e)
        return _fallback_domain1(startup, val, is_pivot, custom_instructions=custom_instructions)


# ===================================================================
# DOMAIN 2: BUSINESS MODEL & UNIT ECONOMICS
# ===================================================================

DOMAIN2_SYSTEM = """You are a venture capital financial analyst creating Domain 2 (Business Model & Unit Economics) of a Business Plan.

RULES FOR DOMAIN 2:
1. USE BMC AS PRIMARY CONTEXT: Leverage BMC Revenue Streams, Customer Segments, and Value Propositions.
2. NO FABRICATED FORECASTS: Do NOT generate fake 5-year revenue projections or invented financial totals. Explain revenue drivers, pricing logic, CAC/LTV frameworks, and unit economics formulas instead.
3. PIVOT MODE AWARENESS: If is_pivot_mode is True, highlight pricing sensitivity, monetization risk, and payment friction.
4. Output structured JSON matching the requested schema exactly."""


def generate_domain_business_model(context: Dict[str, Any], custom_instructions: Optional[str] = None) -> Dict[str, Any]:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bmc = context.get("bmc_data", {})
    is_pivot = context.get("is_pivot_mode", False)

    prompt = f"""Generate Domain 2 (Business Model & Unit Economics) for startup '{startup.get('name')}'.

STARTUP WORKSPACE:
- Solution: {startup.get('solution')}
- Target Market: {startup.get('target_market')}

BMC CANVAS CONTEXT:
- Revenue Streams: {json.dumps(bmc.get('canvas_blocks', {}).get('revenue_streams', []))}
- Customer Segments: {json.dumps(bmc.get('canvas_blocks', {}).get('customer_segments', []))}
- Value Propositions: {json.dumps(bmc.get('canvas_blocks', {}).get('value_propositions', []))}
- Channels: {json.dumps(bmc.get('canvas_blocks', {}).get('channels', []))}

VALIDATION CONTEXT:
- Buyer Viability Score: {val.get('dimension_scores', {}).get('buyer')}/100
- Feasibility Score: {val.get('dimension_scores', {}).get('feasibility')}/100

IS PIVOT MODE ACTIVE: {is_pivot}
FOUNDER CUSTOM REGENERATION INSTRUCTIONS: {custom_instructions or 'None'}

Respond with ONLY a JSON object matching this exact schema:
{{
    "revenue_model": "...",
    "monetization_strategy": "...",
    "pricing_logic": "...",
    "payment_mechanism": "...",
    "cac_framework": "...",
    "ltv_framework": "...",
    "cac_ltv_relationship": "...",
    "revenue_drivers": ["...", "..."],
    "pricing_considerations": ["...", "..."],
    "unit_economics_assumptions": ["...", "..."],
    "key_metrics_to_track": ["...", "..."]
}}"""

    try:
        raw_text = _call_gemini(DOMAIN2_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        validated = BusinessModelDomain(**parsed)
        return validated.model_dump()
    except Exception as e:
        logger.warning("Domain 2 AI generation failed (%s), using fallback.", e)
        return _fallback_domain2(startup, bmc, is_pivot, custom_instructions=custom_instructions)


# ===================================================================
# DOMAIN 3: GO-TO-MARKET & OPERATIONS
# ===================================================================

DOMAIN3_SYSTEM = """You are an expert Chief Operating Officer creating Domain 3 (Go-To-Market & Operations) of a Business Plan.

RULES FOR DOMAIN 3:
1. USE BMC AS PRIMARY CONTEXT: Build upon BMC Channels, Customer Relationships, Key Activities, Key Resources, Key Partnerships.
2. BUYER VIABILITY CONSTRAINTS: Go-To-Market must be consistent with Buyer Viability Score. High-friction enterprise sales cannot be presented as instant self-service.
3. PIVOT MODE AWARENESS: If is_pivot_mode is True, emphasize high acquisition friction, key dependencies, and pilot testing requirements.
4. Output structured JSON matching the requested schema exactly."""


def generate_domain_gtm_operations(context: Dict[str, Any], custom_instructions: Optional[str] = None) -> Dict[str, Any]:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bmc = context.get("bmc_data", {})
    is_pivot = context.get("is_pivot_mode", False)

    prompt = f"""Generate Domain 3 (Go-To-Market & Operations) for startup '{startup.get('name')}'.

STARTUP WORKSPACE:
- Problem: {startup.get('problem')}
- Solution: {startup.get('solution')}
- Target Market: {startup.get('target_market')}

BMC CANVAS CONTEXT:
- Channels: {json.dumps(bmc.get('canvas_blocks', {}).get('channels', []))}
- Customer Relationships: {json.dumps(bmc.get('canvas_blocks', {}).get('customer_relationships', []))}
- Key Activities: {json.dumps(bmc.get('canvas_blocks', {}).get('key_activities', []))}
- Key Resources: {json.dumps(bmc.get('canvas_blocks', {}).get('key_resources', []))}
- Key Partnerships: {json.dumps(bmc.get('canvas_blocks', {}).get('key_partnerships', []))}

VALIDATION CONTEXT:
- Buyer Viability Score: {val.get('dimension_scores', {}).get('buyer')}/100

IS PIVOT MODE ACTIVE: {is_pivot}
FOUNDER CUSTOM REGENERATION INSTRUCTIONS: {custom_instructions or 'None'}

Respond with ONLY a JSON object matching this exact schema:
{{
    "customer_acquisition_strategy": "...",
    "sales_strategy": "...",
    "marketing_channels": ["...", "..."],
    "distribution_strategy": "...",
    "customer_onboarding": "...",
    "customer_retention_approach": "...",
    "operational_workflow": ["...", "..."],
    "technology_infrastructure_requirements": ["...", "..."],
    "operational_dependencies": ["...", "..."],
    "partnership_requirements": ["...", "..."]
}}"""

    try:
        raw_text = _call_gemini(DOMAIN3_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        validated = GtmOperationsDomain(**parsed)
        return validated.model_dump()
    except Exception as e:
        logger.warning("Domain 3 AI generation failed (%s), using fallback.", e)
        return _fallback_domain3(startup, bmc, is_pivot, custom_instructions=custom_instructions)


# ===================================================================
# DOMAIN 4: FINANCIAL STRUCTURE
# ===================================================================

DOMAIN4_SYSTEM = """You are a startup Chief Financial Officer creating Domain 4 (Financial Structure) of a Business Plan.

RULES FOR DOMAIN 4:
1. COST STRUCTURE CONTEXT: Use BMC Cost Structure and Revenue Streams as context.
2. NO INVENTED NUMBERS: Do NOT invent arbitrary dollar numbers. Focus on cost categories, burn-rate logic, key cost drivers, and break-even operational volume formulas.
3. PIVOT MODE AWARENESS: If is_pivot_mode is True, emphasize runway preservation, low fixed overhead, and cost flexibility.
4. Output structured JSON matching the requested schema exactly."""


def generate_domain_financial_structure(context: Dict[str, Any], custom_instructions: Optional[str] = None) -> Dict[str, Any]:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bmc = context.get("bmc_data", {})
    is_pivot = context.get("is_pivot_mode", False)

    prompt = f"""Generate Domain 4 (Financial Structure) for startup '{startup.get('name')}'.

STARTUP WORKSPACE:
- Solution: {startup.get('solution')}
- Industry: {startup.get('industry')}

BMC CANVAS CONTEXT:
- Cost Structure: {json.dumps(bmc.get('canvas_blocks', {}).get('cost_structure', []))}
- Revenue Streams: {json.dumps(bmc.get('canvas_blocks', {}).get('revenue_streams', []))}
- Key Resources: {json.dumps(bmc.get('canvas_blocks', {}).get('key_resources', []))}

VALIDATION CONTEXT:
- Feasibility Score: {val.get('dimension_scores', {}).get('feasibility')}/100

IS PIVOT MODE ACTIVE: {is_pivot}
FOUNDER CUSTOM REGENERATION INSTRUCTIONS: {custom_instructions or 'None'}

Respond with ONLY a JSON object matching this exact schema:
{{
    "startup_cost_categories": ["...", "..."],
    "operating_cost_categories": ["...", "..."],
    "infrastructure_costs": ["...", "..."],
    "payroll_considerations": ["...", "..."],
    "sales_marketing_costs": ["...", "..."],
    "compliance_legal_costs": ["...", "..."],
    "major_cost_drivers": ["...", "..."],
    "burn_rate_explanation": "...",
    "break_even_logic": "...",
    "break_even_volume_requirements": "..."
}}"""

    try:
        raw_text = _call_gemini(DOMAIN4_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        validated = FinancialStructureDomain(**parsed)
        return validated.model_dump()
    except Exception as e:
        logger.warning("Domain 4 AI generation failed (%s), using fallback.", e)
        return _fallback_domain4(startup, bmc, is_pivot, custom_instructions=custom_instructions)


# ===================================================================
# DOMAIN 5: RISK, VALIDATION & LEGAL
# ===================================================================

DOMAIN5_SYSTEM = """You are a risk manager and legal advisor creating Domain 5 (Risk, Validation & Legal) of a Business Plan.

RULES FOR DOMAIN 5:
1. HEAVY USE OF IDEA VALIDATION: Integrate LOFA, Mom Test questions, kill threshold, VC/Buyer critiques, and dimension scores.
2. NO GUARANTEED LEGAL ADVICE: Frame legal information strictly as general considerations and strongly recommend professional counsel.
3. PIVOT MODE AWARENESS: If is_pivot_mode is True, emphasize high risk severity, immediate falsification testing, and pivot criteria.
4. Output structured JSON matching the requested schema exactly."""


def generate_domain_risk_legal(context: Dict[str, Any], custom_instructions: Optional[str] = None) -> Dict[str, Any]:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    is_pivot = context.get("is_pivot_mode", False)

    prompt = f"""Generate Domain 5 (Risk, Validation & Legal) for startup '{startup.get('name')}'.

STARTUP WORKSPACE:
- Problem: {startup.get('problem')}
- Solution: {startup.get('solution')}

VALIDATION INSIGHTS:
- Overall Validation Score: {val.get('final_validation_score')}/100
- Dimension Scores: {json.dumps(val.get('dimension_scores', {}))}
- LOFA (Riskiest Assumption): {val.get('lofa')}
- Key Risks: {json.dumps(val.get('key_risks', []))}
- Mom Test Questions: {json.dumps(val.get('mom_test_questions', []))}
- Kill Threshold: {val.get('kill_threshold')}

IS PIVOT MODE ACTIVE: {is_pivot}
FOUNDER CUSTOM REGENERATION INSTRUCTIONS: {custom_instructions or 'None'}

Respond with ONLY a JSON object matching this exact schema:
{{
    "major_business_risks": ["...", "..."],
    "technical_risks": ["...", "..."],
    "market_risks": ["...", "..."],
    "buyer_adoption_risks": ["...", "..."],
    "competitive_risks": ["...", "..."],
    "financial_risks": ["...", "..."],
    "risk_mitigation_strategies": ["...", "..."],
    "plan_b_fallback_strategy": "...",
    "lofa": "...",
    "mom_test_questions": ["...", "..."],
    "kill_threshold": "...",
    "validation_roadmap": ["...", "..."],
    "general_legal_considerations": ["...", "..."],
    "ip_considerations": ["...", "..."],
    "compliance_considerations": ["...", "..."]
}}"""

    try:
        raw_text = _call_gemini(DOMAIN5_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        validated = RiskValidationLegalDomain(**parsed)
        return validated.model_dump()
    except Exception as e:
        logger.warning("Domain 5 AI generation failed (%s), using fallback.", e)
        return _fallback_domain5(startup, val, is_pivot, custom_instructions=custom_instructions)


# ===================================================================
# EXECUTIVE SUMMARY SYNTHESIS (GENERATED LAST)
# ===================================================================

EXEC_SUMMARY_SYSTEM = """You are an executive editor synthesizing the Executive Summary for a Business Plan.

RULES:
1. SYNTHESIZE FROM ALL 5 DOMAINS: The summary MUST be synthesized directly from the completed 5 domains, workspace, and validation score.
2. CONCISE FIRST PAGE: Keep it punchy, executive-ready, and suitable as page 1 of the Business Plan document.
3. Output structured JSON matching the requested schema exactly."""


def synthesize_executive_summary(
    context: Dict[str, Any],
    domains_data: Dict[str, Any],
    custom_instructions: Optional[str] = None
) -> Dict[str, Any]:
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    val_score = context.get("validation_score", 50.0)

    prompt = f"""Synthesize an Executive Summary for startup '{startup.get('name')}' based on the 5 completed business plan domains.

STARTUP INFO:
- Name: {startup.get('name')}
- Tagline: {startup.get('tagline', 'N/A')}
- Stage: {startup.get('stage')}
- Validation Score: {val_score}/100

COMPLETED DOMAINS SUMMARY:
- Market & Customer: {json.dumps(domains_data.get('market_customer', {}).get('market_opportunity', ''))[:300]}
- Business Model: {json.dumps(domains_data.get('business_model_unit_economics', {}).get('revenue_model', ''))[:300]}
- GTM & Operations: {json.dumps(domains_data.get('gtm_operations', {}).get('customer_acquisition_strategy', ''))[:300]}
- Financial Structure: {json.dumps(domains_data.get('financial_structure', {}).get('burn_rate_explanation', ''))[:300]}
- Risk & Legal: {json.dumps(domains_data.get('risk_validation_legal', {}).get('lofa', ''))[:300]}

CUSTOM REGENERATION INSTRUCTIONS FROM FOUNDER:
{custom_instructions or 'None'}

Synthesize a fresh, executive-ready summary. Do NOT copy raw problem statements verbatim; synthesize a polished, high-impact summary.

Respond with ONLY a JSON object matching this exact schema:
{{
    "startup_overview": "...",
    "problem_statement": "...",
    "solution_overview": "...",
    "target_customer": "...",
    "business_model_summary": "...",
    "market_opportunity_summary": "...",
    "competitive_positioning_summary": "...",
    "gtm_direction": "...",
    "major_risks_summary": "...",
    "validation_readiness": "...",
    "overall_validation_score": {val_score},
    "key_next_steps": ["...", "..."]
}}"""

    try:
        raw_text = _call_gemini(EXEC_SUMMARY_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        validated = ExecutiveSummarySchema(**parsed)
        return validated.model_dump()
    except Exception as e:
        logger.warning("Executive Summary synthesis failed (%s), using fallback.", e)
        return _fallback_executive_summary(startup, val, val_score, domains_data, custom_instructions=custom_instructions)


# ===================================================================
# CROSS-DOCUMENT RED PEN AUDIT ENGINE
# ===================================================================

AUDIT_SYSTEM = """You are an uncompromising startup auditor known as the "Red Pen Auditor".

Your task is to inspect a completed 5-Domain Business Plan against the original Startup Workspace, AI Idea Validation Report, and AI Business Model Canvas to detect CONTRADICTIONS, MISALIGNMENTS, and FABRICATIONS.

EXAMPLES OF CONFLICTS TO FLAG:
1. Target Customer Contradiction: Workspace/BMC says "SMBs/Consumers" but Business Plan claims "Fortune 500 Enterprises".
2. Moat Exaggeration: Validation Moat score is low (< 30) but Business Plan claims "Strong proprietary AI moat".
3. Cost Omission: Business Plan claims intensive outbound sales or heavy marketing, but BMC/Financial Structure omits sales expenses.
4. Fabricated Statistics: Business Plan invents unsupported 5-year revenue statistics or dollar projections.
5. High Friction Sales vs Low Buyer Viability: Low buyer viability score but GTM claims frictionless self-service enterprise adoption.

Return structured JSON object with health_score (0-100) and warnings list."""


def run_cross_document_audit(
    context: Dict[str, Any],
    domains_data: Dict[str, Any],
    exec_summary: Dict[str, Any]
) -> Dict[str, Any]:
    warnings: List[AuditWarning] = []
    startup = context["startup_data"]
    val = context.get("validation_data", {})
    bmc = context.get("bmc_data", {})

    # 1. Deterministic Rule 1: Moat score contradiction check
    moat_score = val.get("dimension_scores", {}).get("moat", 50)
    market_domain = domains_data.get("market_customer", {})
    moat_text = str(market_domain.get("defensibility_moat", "")).lower()

    if moat_score < 30 and any(kw in moat_text for kw in ["strong proprietary", "patented moat", "unbeatable technology", "insurmountable moat"]):
        warnings.append(AuditWarning(
            severity="HIGH",
            section="Domain 1 — Market & Customer",
            issue="Business Plan claims strong proprietary technology moat despite a low validation moat score (<30).",
            source_context=f"Validation Moat Score: {moat_score}/100",
            recommended_correction="Reframe moat around speed of execution, customer relationships, or operational agility rather than proprietary IP."
        ))

    # 2. Deterministic Rule 2: Customer segment conflict check
    workspace_target = str(startup.get("target_market", "")).lower()
    bp_icp = str(market_domain.get("icp_definition", "")).lower()

    if any(smb in workspace_target for smb in ["small business", "smb", "local", "individual", "student"]) and any(ent in bp_icp for ent in ["fortune 500", "large enterprise", "global conglomerate"]):
        warnings.append(AuditWarning(
            severity="HIGH",
            section="Domain 1 — Market & Customer",
            issue="Target customer mismatch between Workspace/BMC and Business Plan.",
            source_context=f"Workspace Target: '{startup.get('target_market')}' vs Business Plan ICP: '{market_domain.get('icp_definition')}'",
            recommended_correction="Align Business Plan ICP strictly with the validated workspace target segment."
        ))

    # 3. AI Reasoning Audit Pass
    prompt = f"""Audit this Business Plan for logical contradictions against upstream workspace & validation data:

UPSTREAM WORKSPACE & VALIDATION:
- Workspace Target: {startup.get('target_market')}
- Validation Scores: {json.dumps(val.get('dimension_scores', {}))}
- BMC Customer Segments: {json.dumps(bmc.get('canvas_blocks', {}).get('customer_segments', []))}
- BMC Channels: {json.dumps(bmc.get('canvas_blocks', {}).get('channels', []))}
- BMC Cost Structure: {json.dumps(bmc.get('canvas_blocks', {}).get('cost_structure', []))}

GENERATED BUSINESS PLAN HIGHLIGHTS:
- Market & Customer: {json.dumps(market_domain)[:400]}
- Business Model: {json.dumps(domains_data.get('business_model_unit_economics', {}))[:400]}
- GTM & Operations: {json.dumps(domains_data.get('gtm_operations', {}))[:400]}
- Financial Structure: {json.dumps(domains_data.get('financial_structure', {}))[:400]}

Return ONLY JSON:
{{
    "health_score": 85,
    "warnings": [
        {{
            "severity": "HIGH",
            "section": "...",
            "issue": "...",
            "source_context": "...",
            "recommended_correction": "..."
        }}
    ]
}}"""

    try:
        raw_text = _call_gemini(AUDIT_SYSTEM, prompt)
        parsed = _extract_json(raw_text)
        report = BusinessPlanAuditReport(**parsed)

        # Merge deterministic warnings
        merged_warnings = warnings + [
            w for w in report.warnings if w.issue not in [cw.issue for cw in warnings]
        ]

        final_health = min(report.health_score, 100 - (len(merged_warnings) * 10))
        final_health = max(0, min(100, final_health))

        return {
            "health_score": final_health,
            "warnings": [w.model_dump() for w in merged_warnings]
        }
    except Exception as e:
        logger.warning("Red Pen Audit AI call failed (%s), using fallback heuristic audit.", e)

    health = 85 if not warnings else 70
    return {
        "health_score": health,
        "warnings": [w.model_dump() for w in warnings]
    }


# ===================================================================
# SINGLE SECTION REGENERATION NODE
# ===================================================================

REGEN_SECTION_SYSTEM = """You are an expert startup advisor regenerating a SINGLE SPECIFIC SECTION of a Business Plan.

RULES:
1. Preserve consistency with all other existing business plan domains.
2. Respect founder custom instructions.
3. Return ONLY structured JSON for the target domain section."""


def regenerate_single_section_node(
    section_name: str,
    context: Dict[str, Any],
    current_domains: Dict[str, Any],
    custom_instructions: Optional[str] = None
) -> Dict[str, Any]:
    """Regenerates a single domain section while keeping other domains intact."""

    if section_name == "market_customer":
        return generate_domain_market_customer(context, custom_instructions=custom_instructions)
    elif section_name == "business_model_unit_economics":
        return generate_domain_business_model(context, custom_instructions=custom_instructions)
    elif section_name == "gtm_operations":
        return generate_domain_gtm_operations(context, custom_instructions=custom_instructions)
    elif section_name == "financial_structure":
        return generate_domain_financial_structure(context, custom_instructions=custom_instructions)
    elif section_name == "risk_validation_legal":
        return generate_domain_risk_legal(context, custom_instructions=custom_instructions)
    else:
        raise ValueError(f"Invalid section name for regeneration: '{section_name}'")


# ===================================================================
# FALLBACK GENERATORS (WHEN GEMINI API IS UNAVAILABLE)
# ===================================================================

def _fallback_domain1(startup: dict, val: dict, is_pivot: bool, custom_instructions: Optional[str] = None) -> dict:
    note = f" (Custom Focus: {custom_instructions[:80]})" if custom_instructions else " (Refreshed Validation Analysis)"
    return {
        "problem_analysis": f"Detailed analysis of problem: {startup.get('problem')}{note}",
        "problem_severity_note": f"Validation score indicates problem severity requiring hypothesis testing.{note}",
        "icp_definition": f"Primary target: {startup.get('target_market', 'Target Audience')}{note}",
        "target_customer_characteristics": ["Tech-forward early adopters", "Cost-conscious decision makers", "Seeking workflow automation"],
        "buyer_persona": f"Operational manager looking for streamlined efficiency and rapid ROI.{note}",
        "customer_pain_points": ["Manual labor overhead", "Lack of integrated software tools", "Unpredictable costs"],
        "market_opportunity": f"Addressable market opportunity driven by digital transformation.{note}",
        "tam_sam_som_drivers": ["Growing industry adoption", "Increasing digital spend", "Emerging market expansion"],
        "market_growth_drivers": ["Industry digital shift", "Demand for automation"],
        "market_limitations": ["Requires external market size statistics validation", "Regulatory compliance hurdles"],
        "direct_competitors": ["Legacy software vendors", "Traditional consulting agencies"],
        "indirect_competitors": ["Internal spreadsheet workflows", "In-house custom tools"],
        "existing_alternatives": ["Manual execution", "Outsourced freelancers"],
        "competitive_positioning": f"Focused agile solution offering lower TCO and faster onboarding.{note}",
        "defensibility_moat": f"Execution speed, customer feedback velocity, and modular design.{note}"
    }


def _fallback_domain2(startup: dict, bmc: dict, is_pivot: bool, custom_instructions: Optional[str] = None) -> dict:
    note = f" (Custom Focus: {custom_instructions[:80]})" if custom_instructions else " (Refreshed Model Economics)"
    return {
        "revenue_model": f"Subscription-based SaaS recurring model.{note}",
        "monetization_strategy": f"Tiered monthly and annual plans based on usage and user seats.{note}",
        "pricing_logic": f"Value-based pricing benchmarked against customer ROI and legacy costs.{note}",
        "payment_mechanism": "Automated credit card billing / ACH invoice processing.",
        "cac_framework": f"Blended CAC tracking digital channel spend and inbound conversion.{note}",
        "ltv_framework": "Gross margin contribution over estimated 24-36 month customer lifetime.",
        "cac_ltv_relationship": "Target LTV/CAC ratio of 3.0x or higher upon scaling.",
        "revenue_drivers": ["Subscriber expansion", "Upsell features", "Annual contract conversions"],
        "pricing_considerations": ["Price sensitivity of early adopters", "Competitive anchor pricing"],
        "unit_economics_assumptions": ["80%+ gross margin", "Low variable server cost per active user"],
        "key_metrics_to_track": ["MRR", "CAC", "LTV", "Net Churn Rate"]
    }


def _fallback_domain3(startup: dict, bmc: dict, is_pivot: bool, custom_instructions: Optional[str] = None) -> dict:
    note = f" (Custom Focus: {custom_instructions[:80]})" if custom_instructions else " (Refreshed GTM Direction)"
    return {
        "customer_acquisition_strategy": f"Inbound content marketing combined with targeted outbound outreach.{note}",
        "sales_strategy": f"Self-serve onboarding for standard tiers with consultative sales for enterprise accounts.{note}",
        "marketing_channels": ["Digital advertising", "Industry events & webinars", "Organic SEO"],
        "distribution_strategy": "Direct-to-customer cloud platform delivery.",
        "customer_onboarding": f"Self-guided interactive product walkthrough with automated email nurturing.{note}",
        "customer_retention_approach": f"Proactive customer success check-ins and feature iteration.{note}",
        "operational_workflow": ["Product development sprint", "Customer support queue", "Infrastructure monitoring"],
        "technology_infrastructure_requirements": ["Cloud database hosting", "API gateway", "Security compliance tooling"],
        "operational_dependencies": ["Cloud infrastructure provider", "Payment gateway provider"],
        "partnership_requirements": ["Industry integration partners", "Channel solution providers"]
    }


def _fallback_domain4(startup: dict, bmc: dict, is_pivot: bool, custom_instructions: Optional[str] = None) -> dict:
    note = f" (Custom Focus: {custom_instructions[:80]})" if custom_instructions else " (Refreshed Capital Allocation)"
    return {
        "startup_cost_categories": ["Initial platform development", "Legal incorporation & compliance", "Branding & website setup"],
        "operating_cost_categories": ["Cloud infrastructure", "Software tooling & APIs", "Marketing budget"],
        "infrastructure_costs": ["Database server hosting", "Third-party AI API tokens", "Domain & CDN"],
        "payroll_considerations": ["Founding engineering team", "Contract customer support"],
        "sales_marketing_costs": ["Paid ad budget", "Content creation", "Email marketing software"],
        "compliance_legal_costs": ["Terms of service & privacy policy drafting", "IP filing & advisory"],
        "major_cost_drivers": ["Third-party API compute fees", "Customer acquisition ad spend"],
        "burn_rate_explanation": f"Controlled lean burn rate prioritized toward product validation before expanding headcount.{note}",
        "break_even_logic": f"Break-even occurs when monthly subscription revenue covers fixed hosting, payroll, and recurring ad spend.{note}",
        "break_even_volume_requirements": "Requires approximately 150-200 active paid subscribers at standard tier pricing."
    }


def _fallback_domain5(startup: dict, val: dict, is_pivot: bool, custom_instructions: Optional[str] = None) -> dict:
    note = f" (Custom Focus: {custom_instructions[:80]})" if custom_instructions else " (Refreshed Risk Audit)"
    return {
        "major_business_risks": ["Customer adoption inertia", "Longer sales cycles than anticipated"],
        "technical_risks": ["Third-party API dependency", "Scalability during traffic spikes"],
        "market_risks": ["Competitor reaction", "Market fragmentation"],
        "buyer_adoption_risks": ["Budget constraints", "Switching cost friction"],
        "competitive_risks": ["Incumbent bundling features", "Price war risk"],
        "financial_risks": ["Cash flow timing mismatch", "Higher CAC than initial projection"],
        "risk_mitigation_strategies": [f"Iterative MVP releases{note}", "Concierge customer onboarding", "Diversified acquisition channels"],
        "plan_b_fallback_strategy": f"Pivot to specialized B2B consulting service leveraging proprietary workflow tooling.{note}",
        "lofa": val.get("lofa", "Target customers are willing to pay for automated solution."),
        "mom_test_questions": ["How do you currently solve this problem?", "How much time/money does this cost you monthly?"],
        "kill_threshold": val.get("kill_threshold", "Fewer than 10 out of 50 interviewed targets express intent to buy."),
        "validation_roadmap": ["Customer discovery interviews", "Landing page smoke test", "Pilot cohort onboarding"],
        "general_legal_considerations": ["General legal notice: Consult licensed legal counsel for binding agreements."],
        "ip_considerations": ["Brand trademark registration", "Proprietary software codebase copyright"],
        "compliance_considerations": ["Data privacy regulations (GDPR/CCPA) compliance", "Secure payment processing (PCI-DSS)"]
    }


def _fallback_executive_summary(
    startup: dict,
    val: dict,
    val_score: float,
    domains_data: dict,
    custom_instructions: Optional[str] = None
) -> dict:
    note = f" (Custom Focus: {custom_instructions[:80]})" if custom_instructions else " (Refreshed Synthesis)"

    raw_problem = startup.get("problem") or "Identified industry problem."
    # Clean up duplicated paragraphs if present in raw_problem
    parts = [p.strip() for p in raw_problem.split("\n\n") if p.strip()]
    if parts:
        seen = []
        for p in parts:
            if p not in seen:
                seen.append(p)
        raw_problem = " ".join(seen)

    raw_sol = startup.get("solution") or "Proposed core solution."
    raw_target = startup.get("target_market") or "Target customers."
    raw_model = domains_data.get("business_model_unit_economics", {}).get("revenue_model") or "Tiered subscription revenue model."
    raw_gtm = domains_data.get("gtm_operations", {}).get("customer_acquisition_strategy") or "Direct inbound digital acquisition."

    return {
        "startup_overview": f"{startup.get('name')} is an innovative platform in the {startup.get('industry', 'technology')} sector.{note}",
        "problem_statement": f"{raw_problem}{note}",
        "solution_overview": f"{raw_sol}{note}",
        "target_customer": f"{raw_target}{note}",
        "business_model_summary": f"{raw_model}{note}",
        "market_opportunity_summary": f"Market opportunity driven by workflow digital transformation and efficiency.{note}",
        "competitive_positioning_summary": f"Agile, cost-effective alternative reducing operational overhead.{note}",
        "gtm_direction": f"{raw_gtm}{note}",
        "major_risks_summary": f"Procurement friction, enterprise decision cycle length, and CAC payback efficiency.{note}",
        "validation_readiness": f"Validation score of {val_score:.1f}/100 indicates clear hypothesis testing priorities.{note}",
        "overall_validation_score": val_score,
        "key_next_steps": [
            f"Execute targeted Mom Test discovery interviews{note}",
            "Launch pilot onboarding cohort with key metrics tracking",
            "Refine unit economics and CAC payback model"
        ]
    }
