"""
Pydantic schemas for AI Business Plan Generator.

Includes domain models, executive summary, audit findings, request/response models,
and prerequisite status checks.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ===================================================================
# 1. DOMAIN AI OUTPUT SCHEMAS
# ===================================================================

class MarketCustomerDomain(BaseModel):
    """Domain 1: Market & Customer Analysis."""
    problem_analysis: str = Field(description="Problem analysis and severity description")
    problem_severity_note: str = Field(description="Context note respecting problem score from validation")
    icp_definition: str = Field(description="Ideal Customer Profile definition")
    target_customer_characteristics: List[str] = Field(default_factory=list)
    buyer_persona: str = Field(description="Detailed buyer persona description")
    customer_pain_points: List[str] = Field(default_factory=list)
    market_opportunity: str = Field(description="Overview of market opportunity")
    tam_sam_som_drivers: List[str] = Field(default_factory=list, description="Qualitative drivers for TAM/SAM/SOM")
    market_growth_drivers: List[str] = Field(default_factory=list)
    market_limitations: List[str] = Field(default_factory=list)
    direct_competitors: List[str] = Field(default_factory=list)
    indirect_competitors: List[str] = Field(default_factory=list)
    existing_alternatives: List[str] = Field(default_factory=list)
    competitive_positioning: str = Field(description="Competitive positioning narrative")
    defensibility_moat: str = Field(description="Defensibility and moat analysis respecting Moat score")


class BusinessModelDomain(BaseModel):
    """Domain 2: Business Model & Unit Economics."""
    revenue_model: str = Field(description="Primary revenue model definition")
    monetization_strategy: str = Field(description="Monetization strategy narrative")
    pricing_logic: str = Field(description="Pricing strategy and logic")
    payment_mechanism: str = Field(description="Customer payment mechanism")
    cac_framework: str = Field(description="Customer Acquisition Cost (CAC) framework explanation")
    ltv_framework: str = Field(description="Lifetime Value (LTV) framework explanation")
    cac_ltv_relationship: str = Field(description="Target CAC/LTV relationship logic")
    revenue_drivers: List[str] = Field(default_factory=list)
    pricing_considerations: List[str] = Field(default_factory=list)
    unit_economics_assumptions: List[str] = Field(default_factory=list)
    key_metrics_to_track: List[str] = Field(default_factory=list)


class GtmOperationsDomain(BaseModel):
    """Domain 3: Go-To-Market & Operations."""
    customer_acquisition_strategy: str = Field(description="Customer acquisition strategy narrative")
    sales_strategy: str = Field(description="Sales strategy matching buyer viability")
    marketing_channels: List[str] = Field(default_factory=list)
    distribution_strategy: str = Field(description="Distribution strategy narrative")
    customer_onboarding: str = Field(description="Customer onboarding workflow")
    customer_retention_approach: str = Field(description="Customer retention approach")
    operational_workflow: List[str] = Field(default_factory=list)
    technology_infrastructure_requirements: List[str] = Field(default_factory=list)
    operational_dependencies: List[str] = Field(default_factory=list)
    partnership_requirements: List[str] = Field(default_factory=list)


class FinancialStructureDomain(BaseModel):
    """Domain 4: Financial Structure."""
    startup_cost_categories: List[str] = Field(default_factory=list)
    operating_cost_categories: List[str] = Field(default_factory=list)
    infrastructure_costs: List[str] = Field(default_factory=list)
    payroll_considerations: List[str] = Field(default_factory=list)
    sales_marketing_costs: List[str] = Field(default_factory=list)
    compliance_legal_costs: List[str] = Field(default_factory=list)
    major_cost_drivers: List[str] = Field(default_factory=list)
    burn_rate_explanation: str = Field(description="Burn-rate explanation and management strategy")
    break_even_logic: str = Field(description="Break-even economics logic and formula")
    break_even_volume_requirements: str = Field(description="Operational volume required to reach break-even")


class RiskValidationLegalDomain(BaseModel):
    """Domain 5: Risk, Validation & Legal."""
    major_business_risks: List[str] = Field(default_factory=list)
    technical_risks: List[str] = Field(default_factory=list)
    market_risks: List[str] = Field(default_factory=list)
    buyer_adoption_risks: List[str] = Field(default_factory=list)
    competitive_risks: List[str] = Field(default_factory=list)
    financial_risks: List[str] = Field(default_factory=list)
    risk_mitigation_strategies: List[str] = Field(default_factory=list)
    plan_b_fallback_strategy: str = Field(description="Fallback / pivot strategy")
    lofa: str = Field(description="Leap-of-Faith Assumption")
    mom_test_questions: List[str] = Field(default_factory=list)
    kill_threshold: str = Field(description="Kill threshold / falsification criteria")
    validation_roadmap: List[str] = Field(default_factory=list)
    general_legal_considerations: List[str] = Field(default_factory=list)
    ip_considerations: List[str] = Field(default_factory=list)
    compliance_considerations: List[str] = Field(default_factory=list)


class ExecutiveSummarySchema(BaseModel):
    """Executive Summary synthesized LAST from the 5 domains."""
    startup_overview: str = Field(description="High-level startup overview")
    problem_statement: str = Field(description="Concise problem summary")
    solution_overview: str = Field(description="Concise solution summary")
    target_customer: str = Field(description="Target customer segment summary")
    business_model_summary: str = Field(description="Core monetization and business model summary")
    market_opportunity_summary: str = Field(description="Market opportunity highlights")
    competitive_positioning_summary: str = Field(description="Positioning & defensibility summary")
    gtm_direction: str = Field(description="Primary Go-To-Market direction")
    major_risks_summary: str = Field(description="Summary of critical risks")
    validation_readiness: str = Field(description="Validation status and readiness summary")
    overall_validation_score: float = Field(description="Overall validation score context")
    key_next_steps: List[str] = Field(default_factory=list, description="Top 3-5 immediate founder action items")


# ===================================================================
# 2. AUDIT SCHEMAS
# ===================================================================

class AuditWarning(BaseModel):
    """Single consistency warning item from Red Pen Audit."""
    severity: str = Field(description="'HIGH' | 'MEDIUM' | 'LOW' | 'WARNING' | 'ERROR'")
    section: str = Field(description="Domain section or canvas block where contradiction occurs")
    issue: str = Field(description="Clear explanation of contradiction")
    source_context: str = Field(description="Original workspace / validation / BMC data context")
    recommended_correction: str = Field(description="Suggested correction for founder")


class BusinessPlanAuditReport(BaseModel):
    """Cross-document Red Pen Audit Report."""
    health_score: int = Field(default=100, ge=0, le=100)
    warnings: List[AuditWarning] = Field(default_factory=list)


# ===================================================================
# 3. REQUEST / RESPONSE PAYLOADS
# ===================================================================

class SectionRegeneratePayload(BaseModel):
    """Payload to regenerate a single domain section."""
    section_name: str = Field(
        description="One of: 'market_customer', 'business_model_unit_economics', 'gtm_operations', 'financial_structure', 'risk_validation_legal', 'executive_summary'"
    )
    custom_instructions: Optional[str] = Field(default=None, description="Optional founder notes/instructions")


class PrerequisitesStatusResponse(BaseModel):
    """Status check for Business Plan generation prerequisites."""
    startup_id: int
    has_workspace: bool
    has_validation: bool
    has_bmc: bool
    can_generate: bool
    missing_prerequisite_message: Optional[str] = None
    validation_score: Optional[float] = None
    is_pivot_mode: bool = False


class BusinessPlanHistoryItem(BaseModel):
    """Version list item summary."""
    id: int
    version: int
    validation_score: Optional[float] = None
    is_pivot_mode: bool = False
    audit_health_score: int = 100
    warning_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class BusinessPlanResponse(BaseModel):
    """Full Business Plan API Response."""
    id: int
    startup_id: int
    bmc_version_id: Optional[int] = None
    validation_report_id: Optional[int] = None
    version: int
    executive_summary: Dict[str, Any]
    domains_data: Dict[str, Any]
    audit_report: Dict[str, Any]
    validation_score: Optional[float] = None
    is_pivot_mode: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
