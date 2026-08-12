"""
Validation-Driven Constraint Engine for AI Business Model Canvas.

Converts validation score dimensions into strict deterministic constraints
for Gemini prompt generation.
"""

from typing import Dict, Any, List, Tuple


def evaluate_bmc_constraints(context: Dict[str, Any]) -> Tuple[List[str], str]:
    """
    Evaluates validation scores and generates deterministic constraint rules.

    Returns:
        (constraints_list, generation_mode)
    """
    constraints: List[str] = []
    val_data = context.get("validation_data")

    # Default to STANDARD if no validation report is available
    if not val_data:
        return constraints, "STANDARD"

    scores = val_data.get("dimension_scores", {})
    final_score = val_data.get("final_validation_score", 100.0)

    moat_score = scores.get("moat", 50)
    buyer_score = scores.get("buyer", 50)
    problem_score = scores.get("problem", 50)

    # --- Constraint 1: Moat ---
    if moat_score < 30:
        constraints.append(
            "CONSTRAINT (LOW MOAT < 30): PROHIBIT claiming proprietary IP, patented technology, "
            "or strong technical defensibility unless explicitly present in workspace data. "
            "Instead, emphasize execution-based advantages such as first-mover speed, niche community focus, "
            "manual concierge onboarding, workflow specialization, or distribution advantage."
        )

    # --- Constraint 2: Buyer ---
    if buyer_score < 40:
        constraints.append(
            "CONSTRAINT (LOW BUYER < 40): PROHIBIT assuming instant self-serve viral adoption. "
            "Account for high sales friction, procurement complexity, multiple decision-maker approvals, "
            "compliance/security requirements, and extended sales cycles."
        )

    # --- Constraint 3: Problem ---
    if problem_score <= 20:
        constraints.append(
            "CONSTRAINT (LOW PROBLEM PAIN <= 20): PROHIBIT positioning product as an urgent emergency / "
            "'hair-on-fire' solution. Emphasize realistic cost avoidance, incremental time savings, "
            "workflow friction reduction, and administrative efficiency."
        )

    # --- Generation Mode ---
    generation_mode = "PIVOT_AWARE" if (final_score is not None and final_score < 50.0) else "STANDARD"

    if generation_mode == "PIVOT_AWARE":
        constraints.append(
            "CONSTRAINT (PIVOT-AWARE MODE SCORE < 50): Highlight validation risks directly within relevant "
            "canvas blocks (e.g. noting defensibility or buyer adoption risks under Key Resources or Channels)."
        )

    return constraints, generation_mode
