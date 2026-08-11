"""
Quick scoring engine test — verifies deterministic calculations.
Run: python -m app.idea_validation.test_scoring
"""
from app.idea_validation.scoring import calculate_validation_score


def test_basic_calculation():
    """Test with known inputs from the spec."""
    result = calculate_validation_score(
        problem_score=80,
        buyer_score=70,
        market_score=60,
        moat_score=50,
        feasibility_score=90,
    )

    # Manual calculation:
    # base = 80*0.30 + 70*0.25 + 60*0.20 + 50*0.15 + 90*0.10
    #      = 24 + 17.5 + 12 + 7.5 + 9 = 70.0
    expected_base = 70.0

    print(f"Problem=80, Buyer=70, Market=60, Moat=50, Feasibility=90")
    print(f"Expected base: {expected_base}")
    print(f"Got base:      {result['weighted_base_score']}")
    assert result["weighted_base_score"] == expected_base, f"Base mismatch: {result['weighted_base_score']}"

    # No vetoes (all > 20)
    assert result["vetoes"]["no_urgent_pain"] == False
    assert result["vetoes"]["capped_market"] == False
    assert result["vetoes"]["high_incumbent_risk"] == False
    assert result["penalty_multiplier"] == 1.0
    assert result["final_validation_score"] == 70.0
    print(f"Final score:   {result['final_validation_score']}")
    print(f"Vetoes:        {result['vetoes']}")
    print(f"Tiers:         {result['score_tiers']}")
    print("✓ Basic calculation PASSED\n")


def test_single_veto():
    """Test with problem_score <= 20 (no_urgent_pain veto)."""
    result = calculate_validation_score(
        problem_score=15,
        buyer_score=70,
        market_score=60,
        moat_score=50,
        feasibility_score=90,
    )

    # base = 15*0.30 + 70*0.25 + 60*0.20 + 50*0.15 + 90*0.10
    #      = 4.5 + 17.5 + 12 + 7.5 + 9 = 50.5
    expected_base = 50.5
    # With no_urgent_pain veto: 50.5 * 0.60 = 30.3
    expected_final = 30.3

    print(f"Problem=15 (veto trigger), Buyer=70, Market=60, Moat=50, Feasibility=90")
    print(f"Expected base:  {expected_base}")
    print(f"Got base:       {result['weighted_base_score']}")
    assert result["weighted_base_score"] == expected_base
    assert result["vetoes"]["no_urgent_pain"] == True
    assert result["vetoes"]["capped_market"] == False
    assert result["vetoes"]["high_incumbent_risk"] == False
    assert result["penalty_multiplier"] == 0.60
    print(f"Expected final: {expected_final}")
    print(f"Got final:      {result['final_validation_score']}")
    assert result["final_validation_score"] == expected_final
    print("✓ Single veto (no_urgent_pain) PASSED\n")


def test_double_veto():
    """Test with problem AND market both <= 20."""
    result = calculate_validation_score(
        problem_score=10,
        buyer_score=70,
        market_score=18,
        moat_score=50,
        feasibility_score=90,
    )

    # base = 10*0.30 + 70*0.25 + 18*0.20 + 50*0.15 + 90*0.10
    #      = 3 + 17.5 + 3.6 + 7.5 + 9 = 40.6
    expected_base = 40.6
    # Penalties: 0.60 * 0.50 = 0.30
    expected_penalty = 0.30
    # Final: 40.6 * 0.30 = 12.18 → rounds to 12.2
    expected_final = 12.2

    print(f"Problem=10, Market=18 (two vetoes), Buyer=70, Moat=50, Feasibility=90")
    print(f"Expected base:    {expected_base}")
    print(f"Got base:         {result['weighted_base_score']}")
    assert result["weighted_base_score"] == expected_base
    assert result["vetoes"]["no_urgent_pain"] == True
    assert result["vetoes"]["capped_market"] == True
    assert result["vetoes"]["high_incumbent_risk"] == False
    print(f"Expected penalty: {expected_penalty}")
    print(f"Got penalty:      {result['penalty_multiplier']}")
    assert result["penalty_multiplier"] == expected_penalty
    print(f"Expected final:   {expected_final}")
    print(f"Got final:        {result['final_validation_score']}")
    assert result["final_validation_score"] == expected_final
    print("✓ Double veto (pain + market) PASSED\n")


def test_triple_veto():
    """Test with all three vetoes triggered."""
    result = calculate_validation_score(
        problem_score=5,
        buyer_score=70,
        market_score=10,
        moat_score=15,
        feasibility_score=90,
    )

    # base = 5*0.30 + 70*0.25 + 10*0.20 + 15*0.15 + 90*0.10
    #      = 1.5 + 17.5 + 2 + 2.25 + 9 = 32.25
    expected_base = 32.2  # rounds to 32.2
    # Penalties: 0.60 * 0.50 * 0.80 = 0.24
    expected_penalty = 0.24
    # Final: 32.25 * 0.24 = 7.74 → rounds to 7.7
    expected_final = 7.7

    print(f"Problem=5, Market=10, Moat=15 (triple veto), Buyer=70, Feasibility=90")
    print(f"Expected base:    {expected_base}")
    print(f"Got base:         {result['weighted_base_score']}")
    assert result["weighted_base_score"] == expected_base
    assert result["vetoes"]["no_urgent_pain"] == True
    assert result["vetoes"]["capped_market"] == True
    assert result["vetoes"]["high_incumbent_risk"] == True
    print(f"Expected penalty: {expected_penalty}")
    print(f"Got penalty:      {result['penalty_multiplier']}")
    assert result["penalty_multiplier"] == expected_penalty
    print(f"Expected final:   {expected_final}")
    print(f"Got final:        {result['final_validation_score']}")
    assert result["final_validation_score"] == expected_final
    print("✓ Triple veto PASSED\n")


def test_clamping():
    """Test that scores are clamped to 0-100."""
    result = calculate_validation_score(
        problem_score=150,
        buyer_score=-10,
        market_score=50,
        moat_score=50,
        feasibility_score=50,
    )

    assert result["problem_score"] == 100
    assert result["buyer_score"] == 0
    print("✓ Clamping PASSED\n")


def test_score_tiers():
    """Test tier labeling."""
    result = calculate_validation_score(
        problem_score=80,
        buyer_score=30,
        market_score=15,
        moat_score=60,
        feasibility_score=50,
    )

    assert result["score_tiers"]["problem"] == "Urgent Pain / Hair-on-Fire"
    assert result["score_tiers"]["buyer"] == "Moderate Friction"
    assert result["score_tiers"]["market"] == "Capped / Niche Market"
    assert result["score_tiers"]["moat"] == "Moderate Moat"
    assert result["score_tiers"]["feasibility"] == "High Complexity"
    print("Tiers:", result["score_tiers"])
    print("✓ Score tiers PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("SCORING ENGINE TESTS")
    print("=" * 60 + "\n")

    test_basic_calculation()
    test_single_veto()
    test_double_veto()
    test_triple_veto()
    test_clamping()
    test_score_tiers()

    print("=" * 60)
    print("ALL SCORING TESTS PASSED ✓")
    print("=" * 60)
