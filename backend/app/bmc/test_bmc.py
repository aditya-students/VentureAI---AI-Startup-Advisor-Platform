"""
Unit and logic tests for the AI Business Model Canvas engine.
Run with: python -m app.bmc.test_bmc
"""

from app.bmc.constraints import evaluate_bmc_constraints
from app.bmc.graph.nodes import generate_bmc_canvas_node, red_pen_audit_node
from app.bmc.schemas import BMCBlocksRaw, BMCAuditReport


def test_constraint_engine():
    print("Testing Constraint Engine...")
    
    # 1. Test Low Moat
    ctx_moat = {
        "startup_data": {"id": 1, "name": "TestStartup"},
        "validation_data": {
            "final_validation_score": 75.0,
            "dimension_scores": {"moat": 20, "buyer": 70, "problem": 80}
        }
    }
    constraints, mode = evaluate_bmc_constraints(ctx_moat)
    assert mode == "STANDARD"
    assert any("LOW MOAT" in c for c in constraints)
    print("  [PASS] Low Moat constraint trigger passed.")

    # 2. Test Low Buyer & Low Problem & Pivot-Aware score
    ctx_pivot = {
        "startup_data": {"id": 1, "name": "TestStartup"},
        "validation_data": {
            "final_validation_score": 42.0,
            "dimension_scores": {"moat": 50, "buyer": 35, "problem": 15}
        }
    }
    constraints, mode = evaluate_bmc_constraints(ctx_pivot)
    assert mode == "PIVOT_AWARE"
    assert any("LOW BUYER" in c for c in constraints)
    assert any("LOW PROBLEM PAIN" in c for c in constraints)
    assert any("PIVOT-AWARE MODE" in c for c in constraints)
    print("  [PASS] Low Buyer, Low Problem, and Pivot-Aware mode triggers passed.")


def test_fallback_canvas_generation():
    print("\nTesting Fallback Canvas Generation...")
    ctx = {
        "startup_data": {
            "id": 1,
            "name": "EduTech AI",
            "solution": "AI math tutor",
            "target_market": "High school students"
        },
        "validation_data": None
    }
    formatted_canvas = generate_bmc_canvas_node(ctx, [], "STANDARD")
    
    block_keys = [
        "customer_segments", "value_propositions", "channels",
        "customer_relationships", "revenue_streams", "key_resources",
        "key_activities", "key_partnerships", "cost_structure"
    ]
    for k in block_keys:
        assert k in formatted_canvas
        assert "items" in formatted_canvas[k]
        assert len(formatted_canvas[k]["items"]) >= 1
    
    print("  [PASS] All 9 blocks generated with proper structure.")


def test_red_pen_audit_node():
    print("\nTesting Red Pen Audit Node...")
    ctx = {
        "startup_data": {"id": 1, "name": "TestStartup"},
        "validation_data": {
            "dimension_scores": {"moat": 15, "buyer": 50, "problem": 50}
        }
    }
    canvas = {
        "customer_segments": {"items": ["Enterprise corporate accounts"]},
        "value_propositions": {"items": ["AI platform"]},
        "channels": {"items": ["Paid outbound ad campaigns"]},
        "customer_relationships": {"items": ["Self-serve"]},
        "revenue_streams": {"items": ["SaaS subscription"]},
        "key_resources": {"items": ["Patented proprietary tech & custom GPU cloud"]},
        "key_activities": {"items": ["Software dev"]},
        "key_partnerships": {"items": ["Cloud providers"]},
        "cost_structure": {"items": ["Office rent"]} # Missing cloud & ad cost!
    }

    audit_res = red_pen_audit_node(canvas, ctx)
    assert "health_score" in audit_res
    assert "conflicts" in audit_res
    conflicts = audit_res["conflicts"]
    
    titles = [c["title"] for c in conflicts]
    print(f"  Audit Health Score: {audit_res['health_score']}")
    print(f"  Detected Conflict Titles: {titles}")
    assert any("Cost Coverage" in t or "Moat" in t for t in titles)
    print("  [PASS] Red Pen Audit detected expected logical contradictions.")


if __name__ == "__main__":
    print("==================================================")
    print("RUNNING BMC UNIT & LOGIC TESTS")
    print("==================================================")
    test_constraint_engine()
    test_fallback_canvas_generation()
    test_red_pen_audit_node()
    print("\n==================================================")
    print("ALL BMC LOGIC TESTS PASSED [PASS]")
    print("==================================================")
