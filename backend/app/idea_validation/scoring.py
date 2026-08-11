"""
Deterministic scoring engine for AI Idea Validation.

This module is pure Python — no AI involvement.  Gemini provides the
qualitative dimension scores (0-100); this module calculates the weighted
base score, applies veto penalties, determines score tiers, and produces
the final validation score.

The separation ensures scoring is reproducible and explainable.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------
WEIGHTS: dict[str, float] = {
    "problem":     0.30,
    "buyer":       0.25,
    "market":      0.20,
    "moat":        0.15,
    "feasibility": 0.10,
}

# ---------------------------------------------------------------------------
# Score-tier bands (min, max, label)
# ---------------------------------------------------------------------------
SCORE_TIERS: dict[str, list[tuple[int, int, str]]] = {
    "problem": [
        (0,  20, "Latent Wish / Nice-to-Have"),
        (21, 50, "Workflow Friction"),
        (51, 75, "Significant Bottleneck"),
        (76, 100, "Urgent Pain / Hair-on-Fire"),
    ],
    "buyer": [
        (0,  20, "High Resistance / Vague Buyer"),
        (21, 50, "Moderate Friction"),
        (51, 75, "Clear ICP / Moderate Cycle"),
        (76, 100, "High Velocity / High Intent"),
    ],
    "market": [
        (0,  20, "Capped / Niche Market"),
        (21, 50, "Moderate Market"),
        (51, 75, "Large Scalable Market"),
        (76, 100, "Venture Scale ($1B+)"),
    ],
    "moat": [
        (0,  20, "Zero Moat / Feature Risk"),
        (21, 50, "Weak Moat"),
        (51, 75, "Moderate Moat"),
        (76, 100, "Structural Moat"),
    ],
    "feasibility": [
        (0,  20, "Extreme Risk / Unproven"),
        (21, 50, "High Complexity"),
        (51, 75, "Standard Engineering"),
        (76, 100, "High Feasibility / Off-the-Shelf"),
    ],
}

# ---------------------------------------------------------------------------
# Veto rules
# ---------------------------------------------------------------------------
VETO_RULES: list[dict] = [
    {
        "key":       "no_urgent_pain",
        "dimension": "problem",
        "threshold": 20,
        "penalty":   0.60,
        "label":     "No Urgent Pain — Problem score critically low",
    },
    {
        "key":       "capped_market",
        "dimension": "market",
        "threshold": 20,
        "penalty":   0.50,
        "label":     "Capped Market — Market score critically low",
    },
    {
        "key":       "high_incumbent_risk",
        "dimension": "moat",
        "threshold": 20,
        "penalty":   0.80,
        "label":     "High Incumbent Risk — Moat score critically low",
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    """Clamp an integer to [lo, hi]."""
    return max(lo, min(hi, int(value)))


def _get_tier(dimension: str, score: int) -> str:
    """Return the human-readable tier label for a dimension score."""
    bands = SCORE_TIERS.get(dimension, [])
    for lo, hi, label in bands:
        if lo <= score <= hi:
            return label
    return "Unknown"


def calculate_validation_score(
    problem_score: int,
    buyer_score: int,
    market_score: int,
    moat_score: int,
    feasibility_score: int,
) -> dict:
    """
    Deterministic scoring calculation.

    Parameters
    ----------
    problem_score, buyer_score, market_score, moat_score, feasibility_score
        Raw dimension scores (0-100) produced by the AI synthesis node.

    Returns
    -------
    dict with keys:
        - problem_score … feasibility_score  (clamped 0-100)
        - weighted_base_score   (float)
        - final_validation_score (float, 0-100)
        - vetoes                (dict[str, bool])
        - penalty_multiplier    (float)
        - score_tiers           (dict[str, str])
        - triggered_vetoes      (list[dict]) — details of any active vetoes
    """
    # 1. Clamp all dimension scores
    scores = {
        "problem":     _clamp(problem_score),
        "buyer":       _clamp(buyer_score),
        "market":      _clamp(market_score),
        "moat":        _clamp(moat_score),
        "feasibility": _clamp(feasibility_score),
    }

    # 2. Weighted base score
    base = sum(scores[dim] * weight for dim, weight in WEIGHTS.items())

    # 3. Veto / penalty detection
    vetoes: dict[str, bool] = {}
    penalty_multiplier = 1.0
    triggered_vetoes: list[dict] = []

    for rule in VETO_RULES:
        triggered = scores[rule["dimension"]] <= rule["threshold"]
        vetoes[rule["key"]] = triggered
        if triggered:
            penalty_multiplier *= rule["penalty"]
            triggered_vetoes.append({
                "key":   rule["key"],
                "label": rule["label"],
                "penalty": rule["penalty"],
            })

    # 4. Final score (apply penalties multiplicatively)
    final = base * penalty_multiplier

    # 5. Clamp final to [0, 100] and round
    final = round(max(0.0, min(100.0, final)), 1)

    # 6. Tier labels
    tiers = {dim: _get_tier(dim, s) for dim, s in scores.items()}

    return {
        "problem_score":          scores["problem"],
        "buyer_score":            scores["buyer"],
        "market_score":           scores["market"],
        "moat_score":             scores["moat"],
        "feasibility_score":      scores["feasibility"],
        "weighted_base_score":    round(base, 1),
        "final_validation_score": final,
        "vetoes":                 vetoes,
        "penalty_multiplier":     round(penalty_multiplier, 4),
        "score_tiers":            tiers,
        "triggered_vetoes":       triggered_vetoes,
    }
