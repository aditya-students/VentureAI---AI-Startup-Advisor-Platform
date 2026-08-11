"""
LangGraph node functions for the Idea Validation pipeline.

Each node receives the shared ValidationState and returns a dict of
state updates.  Gemini calls use google-generativeai directly for
maximum control over prompts and JSON parsing.
"""

from __future__ import annotations

import json
import logging
import re

import google.generativeai as genai

from app.config import settings
from app.idea_validation.scoring import calculate_validation_score

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini helper
# ---------------------------------------------------------------------------

def _configure_genai() -> None:
    """Ensure the Gemini client is configured (idempotent)."""
    genai.configure(api_key=settings.GEMINI_API_KEY)


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Call Gemini and return the text response.

    Uses gemini-2.0-flash for speed (three agents run in parallel).
    """
    _configure_genai()
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=system_prompt,
    )
    response = model.generate_content(user_prompt)
    return response.text


def _extract_json(text: str) -> dict:
    """
    Extract a JSON object from Gemini's response text.

    Handles cases where the model wraps JSON in markdown code fences.
    """
    # Try to find JSON within code fences first
    fence_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
    if fence_match:
        text = fence_match.group(1)

    # Strip leading/trailing whitespace
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last-resort: find the first { ... } block
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            return json.loads(brace_match.group(0))
        raise ValueError(f"Could not extract JSON from Gemini response:\n{text[:500]}")


def _format_workspace(data: dict) -> str:
    """Format workspace data into a readable prompt block."""
    return (
        f"Startup Name: {data.get('name', 'N/A')}\n"
        f"Tagline: {data.get('tagline', 'N/A')}\n"
        f"Problem: {data.get('problem', 'N/A')}\n"
        f"Solution: {data.get('solution', 'N/A')}\n"
        f"Industry: {data.get('industry', 'N/A')}\n"
        f"Target Market: {data.get('target_market', 'N/A')}\n"
        f"Stage: {data.get('stage', 'N/A')}"
    )


# ===================================================================
# NODE 1: LOFA Extraction
# ===================================================================

LOFA_SYSTEM = """You are a startup validation expert specializing in identifying the single most critical assumption — the Leap-of-Faith Assumption (LOFA) — that must be true for a startup to succeed.

You must identify the ONE assumption that, if proven false, would invalidate the entire business model.

Rules:
- Be concise and specific (1-2 sentences).
- Do NOT simply summarize the startup.
- Focus on the critical assumption about customer behavior, willingness to pay, market size, or technical feasibility.
- Frame it as a testable hypothesis.

Respond with ONLY a JSON object:
{"lofa": "The specific assumption..."}"""


def extract_lofa(state: dict) -> dict:
    """Extract the Leap-of-Faith Assumption from workspace data."""
    workspace = state["workspace_data"]

    prompt = f"""Analyze this startup and identify the single Leap-of-Faith Assumption (LOFA) — the riskiest assumption that must be true for this business to work.

{_format_workspace(workspace)}

Respond with ONLY a JSON object: {{"lofa": "..."}}"""

    try:
        raw = _call_gemini(LOFA_SYSTEM, prompt)
        parsed = _extract_json(raw)
        lofa = parsed.get("lofa", "").strip()
        if not lofa:
            raise ValueError("Empty LOFA returned by Gemini")
        return {"lofa": lofa}
    except Exception as e:
        logger.error("LOFA extraction failed: %s", e)
        raise RuntimeError(f"LOFA extraction failed: {e}") from e


# ===================================================================
# NODE 2A: Skeptical VC Partner
# ===================================================================

VC_SYSTEM = """You are a skeptical venture capital partner evaluating a startup pitch. You are NOT a supportive coach — you are adversarial and looking for reasons to PASS on this deal.

Your job:
1. Evaluate TAM/SAM ceiling (but DO NOT invent precise figures — mark as estimates if no evidence exists).
2. Evaluate market growth and scalability.
3. Evaluate venture-scale potential vs lifestyle business.
4. Evaluate platform dependency and incumbent risk.
5. Evaluate preliminary technical and operational feasibility.
6. Identify major reasons an investor would reject this idea.

Be brutally honest. Do NOT be encouraging.

Respond with ONLY a JSON object matching this exact structure:
{
    "agent_id": "skeptical_vc",
    "critique": {
        "tam_assessment": "Your assessment of the total addressable market...",
        "platform_risk": "Platform dependencies and incumbent threats...",
        "venture_verdict": "Is this venture-scale or a lifestyle business? Why?",
        "market_assessment": "Market growth, scalability, adjacent expansion potential...",
        "feasibility_assessment": "Technical complexity, capital requirements, regulatory hurdles..."
    }
}"""


def skeptical_vc_agent(state: dict) -> dict:
    """Run the Skeptical VC Partner analysis."""
    workspace = state["workspace_data"]
    lofa = state["lofa"]

    prompt = f"""Evaluate this startup from the perspective of a skeptical VC partner deciding whether to invest.

STARTUP INFORMATION:
{_format_workspace(workspace)}

RISKIEST ASSUMPTION (LOFA):
{lofa}

Be adversarial. Identify why you would PASS on this deal. Do not invent precise TAM figures — mark estimates clearly.

Respond with ONLY the JSON object."""

    try:
        raw = _call_gemini(VC_SYSTEM, prompt)
        parsed = _extract_json(raw)
        return {"vc_critique": parsed}
    except Exception as e:
        logger.error("VC agent failed: %s", e)
        raise RuntimeError(f"Skeptical VC agent failed: {e}") from e


# ===================================================================
# NODE 2B: Cynical Buyer / ICP
# ===================================================================

BUYER_SYSTEM = """You are roleplaying as a cynical, skeptical target customer for this startup. You are NOT easily impressed and you resist changing your current workflow.

Your job:
1. Evaluate whether the problem is painful enough to motivate action.
2. Evaluate frequency — how often does this problem occur?
3. Evaluate switching friction — what would it take to abandon current tools/processes?
4. Evaluate implementation overhead — is adoption burdensome?
5. Identify current status-quo workarounds (spreadsheets, manual processes, existing tools).
6. Evaluate willingness to pay — would you actually spend money on this?
7. Identify the budget owner and procurement friction.
8. Explain why you, as the target customer, might refuse to buy.

Do NOT ask hypothetical questions like "Would you use this?"
Focus on actual behavior and existing alternatives.

Respond with ONLY a JSON object:
{
    "agent_id": "cynical_buyer",
    "critique": {
        "buying_objection": "The main reason you would NOT buy this...",
        "status_quo_trap": "What you currently do instead and why it's good enough...",
        "buyer_verdict": "Your verdict as a skeptical buyer — written in first person...",
        "problem_assessment": "How painful is this problem really? Frequency and urgency...",
        "buyer_assessment": "Decision-maker clarity, sales cycle, willingness to pay..."
    }
}"""


def cynical_buyer_agent(state: dict) -> dict:
    """Run the Cynical Buyer / ICP analysis."""
    workspace = state["workspace_data"]
    lofa = state["lofa"]

    prompt = f"""You are the target customer described below. Evaluate whether you would actually buy this product.

STARTUP INFORMATION:
{_format_workspace(workspace)}

TARGET MARKET: {workspace.get('target_market', 'Not specified')}

RISKIEST ASSUMPTION (LOFA):
{lofa}

Be skeptical. Explain why you might NOT buy. Focus on your actual current behavior, not hypotheticals.

Respond with ONLY the JSON object."""

    try:
        raw = _call_gemini(BUYER_SYSTEM, prompt)
        parsed = _extract_json(raw)
        return {"buyer_critique": parsed}
    except Exception as e:
        logger.error("Buyer agent failed: %s", e)
        raise RuntimeError(f"Cynical Buyer agent failed: {e}") from e


# ===================================================================
# NODE 2C: Competitor & Moat Strategist
# ===================================================================

COMPETITOR_SYSTEM = """You are a competitive intelligence and moat strategist. You analyze whether a startup can defend its market position against competitors.

Your job:
1. Identify likely direct competitors (existing companies solving the same problem).
2. Identify indirect competitors and status-quo alternatives.
3. Identify incumbent threats (large companies that could add this feature).
4. Analyze platform risk (dependency on third-party platforms).
5. Evaluate network effects, proprietary data advantages, switching costs.
6. Evaluate workflow lock-in and distribution advantage.
7. Evaluate fast-follower risk — how easily could this be duplicated?

IMPORTANT: Clearly distinguish between:
- Known/obvious alternatives
- Likely alternatives
- AI-generated hypotheses requiring further research

Do NOT claim competitors definitely exist unless the evidence supports it.

Respond with ONLY a JSON object:
{
    "agent_id": "competitor_strategist",
    "critique": {
        "primary_incumbent_threat": "The biggest existing threat to this startup...",
        "moat_vulnerability": "Why the startup's competitive advantage is weak or non-existent...",
        "competitor_verdict": "Overall competitive landscape assessment...",
        "defensibility_assessment": "Network effects, switching costs, data moats, fast-follower risk..."
    }
}"""


def competitor_strategist_agent(state: dict) -> dict:
    """Run the Competitor & Moat Strategist analysis."""
    workspace = state["workspace_data"]
    lofa = state["lofa"]

    prompt = f"""Analyze the competitive landscape and defensibility of this startup.

STARTUP INFORMATION:
{_format_workspace(workspace)}

RISKIEST ASSUMPTION (LOFA):
{lofa}

Identify real threats. Distinguish between known competitors and hypotheses. Assess moat strength.

Respond with ONLY the JSON object."""

    try:
        raw = _call_gemini(COMPETITOR_SYSTEM, prompt)
        parsed = _extract_json(raw)
        return {"competitor_critique": parsed}
    except Exception as e:
        logger.error("Competitor agent failed: %s", e)
        raise RuntimeError(f"Competitor Strategist agent failed: {e}") from e


# ===================================================================
# NODE 3: Synthesis
# ===================================================================

SYNTHESIS_SYSTEM = """You are a startup validation synthesis engine. You have received three independent adversarial assessments of a startup from:
1. A Skeptical VC Partner
2. A Cynical Target Customer (Buyer)
3. A Competitor & Moat Strategist

Your job is to synthesize their critiques into a structured validation report.

You MUST produce scores for exactly five dimensions (each 0-100):
- problem (0-100): Pain depth, urgency, frequency, financial/operational friction
- buyer (0-100): Decision-maker clarity, sales cycle, willingness to pay, switching friction
- market (0-100): TAM/SAM, growth, scalability, adjacent expansion
- moat (0-100): Network effects, proprietary data, switching costs, workflow lock-in, platform risk
- feasibility (0-100): Technical complexity, capital requirements, dependencies, regulatory hurdles

IMPORTANT SCORING GUIDELINES:
- Be calibrated and honest. Do NOT inflate scores.
- A score of 50 means "average/uncertain". Scores above 75 require strong evidence.
- If information is missing or vague, score conservatively (40-55 range).
- The dimension scores must reflect the adversarial analysis, not an optimistic reading.

You must also provide:
- An overall qualitative assessment (2-3 paragraphs)
- 2-4 key strengths
- 3-5 key risks
- 3-5 recommended next steps
- 3 Mom Test interview questions (non-leading, focused on past behavior, testing the LOFA)
- 1 kill threshold (specific measurable condition to reconsider the assumption)

BAD Mom Test questions (do NOT use these patterns):
- "Would you pay for X?" (hypothetical)
- "Do you think X is a good idea?" (leading)
- "Would you use X?" (hypothetical)

GOOD Mom Test questions:
- "Tell me about the last time you experienced [problem]. How did you handle it?"
- "What solutions have you tried? How much did you spend?"
- "Walk me through your current workflow for [task]."

Respond with ONLY a JSON object:
{
    "dimension_scores": {
        "problem": 0,
        "buyer": 0,
        "market": 0,
        "moat": 0,
        "feasibility": 0
    },
    "overall_assessment": "...",
    "strengths": ["...", "..."],
    "key_risks": ["...", "..."],
    "recommended_next_steps": ["...", "..."],
    "mom_test_questions": ["...", "...", "..."],
    "kill_threshold": "If fewer than X of Y target customers report..."
}"""


def synthesis_node(state: dict) -> dict:
    """Synthesize all three agent critiques into a unified assessment."""
    workspace = state["workspace_data"]
    lofa = state["lofa"]
    vc = state["vc_critique"]
    buyer = state["buyer_critique"]
    competitor = state["competitor_critique"]

    prompt = f"""Synthesize the following three independent adversarial assessments into a unified validation report.

STARTUP INFORMATION:
{_format_workspace(workspace)}

LEAP-OF-FAITH ASSUMPTION (LOFA):
{lofa}

--- SKEPTICAL VC PARTNER ASSESSMENT ---
{json.dumps(vc, indent=2)}

--- CYNICAL BUYER ASSESSMENT ---
{json.dumps(buyer, indent=2)}

--- COMPETITOR & MOAT STRATEGIST ASSESSMENT ---
{json.dumps(competitor, indent=2)}

Produce calibrated scores (0-100) for each dimension based on the evidence above.
Generate Mom Test questions that specifically test the LOFA.
Generate a kill threshold specific to this startup's riskiest assumption.

Respond with ONLY the JSON object."""

    try:
        raw = _call_gemini(SYNTHESIS_SYSTEM, prompt)
        parsed = _extract_json(raw)

        # Validate required fields
        dim_scores = parsed.get("dimension_scores", {})
        required_dims = ["problem", "buyer", "market", "moat", "feasibility"]
        for dim in required_dims:
            if dim not in dim_scores:
                raise ValueError(f"Missing dimension score: {dim}")
            score = int(dim_scores[dim])
            if not (0 <= score <= 100):
                raise ValueError(f"Score out of range for {dim}: {score}")
            dim_scores[dim] = score

        mom_questions = parsed.get("mom_test_questions", [])
        if not isinstance(mom_questions, list) or len(mom_questions) < 1:
            raise ValueError("Must provide at least 1 Mom Test question")
        # Ensure exactly 3
        mom_questions = mom_questions[:3]
        while len(mom_questions) < 3:
            mom_questions.append("Tell me about the last time you encountered this problem. What did you do?")

        return {
            "dimension_scores":     dim_scores,
            "overall_assessment":   parsed.get("overall_assessment", "Assessment not available."),
            "strengths":            parsed.get("strengths", []),
            "key_risks":            parsed.get("key_risks", []),
            "recommended_next_steps": parsed.get("recommended_next_steps", []),
            "mom_test_questions":   mom_questions,
            "kill_threshold":       parsed.get("kill_threshold", "Not specified."),
        }
    except Exception as e:
        logger.error("Synthesis node failed: %s", e)
        raise RuntimeError(f"Synthesis node failed: {e}") from e


# ===================================================================
# NODE 4: Deterministic Scoring
# ===================================================================

def scoring_node(state: dict) -> dict:
    """
    Apply the deterministic scoring engine.

    This node does NOT call Gemini — it uses pure Python to calculate
    the weighted base score, apply veto penalties, and determine tiers.
    """
    dim = state["dimension_scores"]

    result = calculate_validation_score(
        problem_score=dim["problem"],
        buyer_score=dim["buyer"],
        market_score=dim["market"],
        moat_score=dim["moat"],
        feasibility_score=dim["feasibility"],
    )

    return {
        "score_tiers":            result["score_tiers"],
        "weighted_base_score":    result["weighted_base_score"],
        "final_validation_score": result["final_validation_score"],
        "vetoes":                 result["vetoes"],
        "penalty_multiplier":     result["penalty_multiplier"],
        "triggered_vetoes":       result["triggered_vetoes"],
    }
