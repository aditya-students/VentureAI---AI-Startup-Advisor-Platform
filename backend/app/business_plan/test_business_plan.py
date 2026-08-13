"""
Unit tests for AI Business Plan Generator.

Tests:
1. Prerequisite status checker (detecting missing Validation or missing BMC)
2. Pivot-aware mode detection (validation score < 50)
3. Cross-document Red Pen Audit contradiction engine
4. Domain fallback generators & schema validation
"""

import unittest
from unittest.mock import MagicMock

from app.business_plan.context import get_prerequisites_status
from app.business_plan.graph.nodes import (
    run_cross_document_audit,
    _fallback_domain1,
    _fallback_domain2,
    _fallback_domain3,
    _fallback_domain4,
    _fallback_domain5,
    _fallback_executive_summary,
)
from app.business_plan.schemas import (
    MarketCustomerDomain,
    BusinessModelDomain,
    GtmOperationsDomain,
    FinancialStructureDomain,
    RiskValidationLegalDomain,
    ExecutiveSummarySchema,
    BusinessPlanAuditReport,
)


class TestBusinessPlanContextAndPrerequisites(unittest.TestCase):
    def test_prerequisites_missing_workspace(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        res = get_prerequisites_status(db, 999)
        self.assertFalse(res["can_generate"])
        self.assertFalse(res["has_workspace"])

    def test_prerequisites_missing_validation(self):
        db = MagicMock()

        startup_mock = MagicMock()
        startup_mock.id = 1

        # Query returns startup, but None for validation and BMC
        def mock_query(model):
            q = MagicMock()
            if model.__name__ == "Startup":
                q.filter().first.return_value = startup_mock
            else:
                q.filter().order_by().first.return_value = None
            return q

        db.query.side_effect = mock_query

        res = get_prerequisites_status(db, 1)
        self.assertFalse(res["can_generate"])
        self.assertTrue(res["has_workspace"])
        self.assertFalse(res["has_validation"])
        self.assertIn("Complete AI Idea Validation", res["missing_prerequisite_message"])

    def test_pivot_mode_trigger(self):
        db = MagicMock()
        startup_mock = MagicMock()
        startup_mock.id = 1

        val_mock = MagicMock()
        val_mock.final_validation_score = 42.0

        bmc_mock = MagicMock()

        def mock_query(model):
            q = MagicMock()
            if model.__name__ == "Startup":
                q.filter().first.return_value = startup_mock
            elif model.__name__ == "IdeaValidation":
                q.filter().order_by().first.return_value = val_mock
            elif model.__name__ == "BMCVersion":
                q.filter().order_by().first.return_value = bmc_mock
            return q

        db.query.side_effect = mock_query

        res = get_prerequisites_status(db, 1)
        self.assertTrue(res["can_generate"])
        self.assertTrue(res["is_pivot_mode"])
        self.assertEqual(res["validation_score"], 42.0)


class TestRedPenAuditEngine(unittest.TestCase):
    def test_moat_score_contradiction(self):
        context = {
            "startup_data": {
                "name": "TechCorp",
                "problem": "Manual testing is slow",
                "solution": "AI testing",
                "target_market": "Local Businesses",
            },
            "validation_data": {
                "final_validation_score": 45,
                "dimension_scores": {"moat": 20},
            },
            "bmc_data": {"canvas_blocks": {}},
        }

        domains_data = {
            "market_customer": {
                "problem_analysis": "Problem is moderate",
                "icp_definition": "Local Businesses",
                "defensibility_moat": "We have a strong proprietary technology moat and patented moat.",
            },
            "business_model_unit_economics": {},
            "gtm_operations": {},
            "financial_structure": {},
            "risk_validation_legal": {},
        }

        exec_summary = {}

        audit_res = run_cross_document_audit(context, domains_data, exec_summary)
        self.assertIn("warnings", audit_res)
        self.assertTrue(any(w["severity"] == "HIGH" and "moat" in w["issue"].lower() for w in audit_res["warnings"]))

    def test_target_market_mismatch(self):
        context = {
            "startup_data": {
                "name": "LocalBizAI",
                "problem": "Inventory management",
                "solution": "App for local shops",
                "target_market": "Small Business owners",
            },
            "validation_data": {"dimension_scores": {"moat": 70}},
            "bmc_data": {"canvas_blocks": {}},
        }

        domains_data = {
            "market_customer": {
                "icp_definition": "Fortune 500 Enterprise CEOs and global conglomerates",
                "defensibility_moat": "Speed to market",
            },
            "business_model_unit_economics": {},
            "gtm_operations": {},
            "financial_structure": {},
            "risk_validation_legal": {},
        }

        exec_summary = {}

        audit_res = run_cross_document_audit(context, domains_data, exec_summary)
        self.assertTrue(any("mismatch" in w["issue"].lower() for w in audit_res["warnings"]))


class TestFallbackGeneratorsAndSchemas(unittest.TestCase):
    def test_fallbacks_produce_valid_schemas(self):
        startup = {
            "name": "DemoApp",
            "problem": "Slow workflow",
            "solution": "Automation bot",
            "target_market": "Freelancers",
            "industry": "Software",
        }
        val = {"lofa": "Users will install bot", "kill_threshold": "Fewer than 5 signups"}
        bmc = {"canvas_blocks": {}}

        d1 = _fallback_domain1(startup, val, False)
        MarketCustomerDomain(**d1)

        d2 = _fallback_domain2(startup, bmc, False)
        BusinessModelDomain(**d2)

        d3 = _fallback_domain3(startup, bmc, False)
        GtmOperationsDomain(**d3)

        d4 = _fallback_domain4(startup, bmc, False)
        FinancialStructureDomain(**d4)

        d5 = _fallback_domain5(startup, val, False)
        RiskValidationLegalDomain(**d5)

        exec_sum = _fallback_executive_summary(startup, val, 75.0, {})
        ExecutiveSummarySchema(**exec_sum)


if __name__ == "__main__":
    unittest.main()
