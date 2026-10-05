"""
ZONATA / URA UNIVERSAL AIC CEO KRA & KPI ENGINE
Comprehensive 15-KRA Universal Framework (with mandatory 18-attribute schema),
Tier 0-5 Hierarchical KPI System, 10-point KPI Quality Test,
Anti-Gaming Detection Engine, and Non-Universal Adaptive Industry Benchmarking Engine.

Standards Alignment:
  - ISO 37000: Governance & Performance Oversight
  - ISO 31000: Risk-adjusted KPIs and Guardrails
  - ISO/IEC 42001: Continual AI Performance & Quality Assurance
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("zonata.aic_ceo.kra_kpi")

# ==============================================================================
# 1. KRA ENUMS & SCHEMA
# ==============================================================================

class KPITier(str, Enum):
    TIER_0_ENTERPRISE_VALUE = "TIER_0_ENTERPRISE_VALUE"
    TIER_1_FINANCIAL = "TIER_1_FINANCIAL"
    TIER_2_CUSTOMER_MARKET = "TIER_2_CUSTOMER_MARKET"
    TIER_3_OPERATIONAL = "TIER_3_OPERATIONAL"
    TIER_4_ORGANIZATIONAL = "TIER_4_ORGANIZATIONAL"
    TIER_5_AGENT_TECHNOLOGY = "TIER_5_AGENT_TECHNOLOGY"

class KPIClassification(str, Enum):
    NORTH_STAR = "NORTH_STAR"
    LAGGING = "LAGGING"
    LEADING = "LEADING"
    DIAGNOSTIC = "DIAGNOSTIC"
    GUARDRAIL = "GUARDRAIL"
    RISK = "RISK"
    EFFICIENCY = "EFFICIENCY"
    QUALITY = "QUALITY"
    FINANCIAL = "FINANCIAL"
    STRATEGIC = "STRATEGIC"

class IndustryArchetype(str, Enum):
    SAAS_SOFTWARE = "SAAS_SOFTWARE"
    HOSPITALITY_TOURISM = "HOSPITALITY_TOURISM"
    HEALTHCARE_CLINICAL = "HEALTHCARE_CLINICAL"
    MANUFACTURING_INDUSTRIAL = "MANUFACTURING_INDUSTRIAL"
    ECOMMERCE_RETAIL = "ECOMMERCE_RETAIL"
    LOGISTICS_SUPPLY_CHAIN = "LOGISTICS_SUPPLY_CHAIN"
    PROFESSIONAL_SERVICES = "PROFESSIONAL_SERVICES"
    FINANCIAL_SERVICES = "FINANCIAL_SERVICES"
    UNKNOWN = "UNKNOWN"

class CompanyMaturity(str, Enum):
    SEED = "SEED"
    EARLY_GROWTH = "EARLY_GROWTH"
    SCALEUP = "SCALEUP"
    MATURE_ENTERPRISE = "MATURE_ENTERPRISE"
    DISTRESSED = "DISTRESSED"

@dataclass
class UniversalKRA:
    """
    Mandatory 18-attribute schema defined by AIC CEO Master Constitution.
    """
    kra_id: str
    kra_name: str
    purpose: str
    executive_responsibility: str
    desired_outcome: str
    leading_indicators: List[str]
    lagging_indicators: List[str]
    financial_impact: str
    strategic_impact: str
    risk_factors: List[str]
    benchmark_method: str
    measurement_frequency: str           # CONTINUOUS, DAILY, WEEKLY, MONTHLY, QUARTERLY
    target_method: str                   # ADAPTIVE_INDUSTRY_CALIBRATION, BASELINE_TREND, STRATEGIC_TARGET
    escalation_threshold: str
    failure_condition: str
    corrective_action: str
    evidence_source: str
    accountable_executive: str
    dependencies: List[str]

@dataclass
class HierarchicalKPI:
    kpi_id: str
    tier: KPITier
    classification: KPIClassification
    name: str
    definition: str
    unit: str                            # USD, PERCENTAGE, RATIO, DAYS, COUNT, SCORE
    formula: str
    data_source: str
    accountable_owner: str
    frequency: str
    baseline: float
    target: float
    stretch: float
    minimum_acceptable: float
    warning_threshold: float
    critical_threshold: float
    time_horizon_days: int
    benchmark_source: str                # e.g., "INDUSTRY_PEER_GROUP", "BENCHMARK UNKNOWN"
    confidence_level: str = "HIGH"       # HIGH, MEDIUM, LOW, UNKNOWN
    gaming_risk_guardrail: Optional[str] = None

# ==============================================================================
# 2. THE 15 UNIVERSAL KRAs (CANONICAL CATALOG)
# ==============================================================================

CANONICAL_UNIVERSAL_KRAS: List[UniversalKRA] = [
    UniversalKRA(
        kra_id="KRA-01",
        kra_name="Enterprise Value Creation",
        purpose="Steward long-term risk-adjusted enterprise value and owner equity.",
        executive_responsibility="AIC CEO & Chief Capital Allocator",
        desired_outcome="Sustained increase in risk-adjusted enterprise value and DCF trajectory.",
        leading_indicators=["Pipeline Growth Quality", "Net Revenue Retention Trajectory", "Gross Margin Expansion"],
        lagging_indicators=["Enterprise Valuation Multiple", "Return on Invested Capital (ROIC)", "Free Cash Flow Yield"],
        financial_impact="Direct expansion of enterprise capitalization and exit/holding value.",
        strategic_impact="Protects enterprise sovereignty, solvency, and market dominance.",
        risk_factors=["Capital Misallocation", "Uncontrolled Cash Burn", "Market Multiple Compression"],
        benchmark_method="Peer valuation multiples and discounted cash flow models.",
        measurement_frequency="QUARTERLY",
        target_method="ADAPTIVE_INDUSTRY_CALIBRATION",
        escalation_threshold="Value erosion >10% over two consecutive evaluation cycles.",
        failure_condition="Enterprise insolvency or severe equity impairment.",
        corrective_action="Halt non-essential capital projects; execute immediate cash conservation and restructuring.",
        evidence_source="Audited Financial Ledger & Cap Table Valuation Records",
        accountable_executive="AIC_CEO",
        dependencies=["KRA-02", "KRA-03", "KRA-04", "KRA-05"]
    ),
    UniversalKRA(
        kra_id="KRA-02",
        kra_name="Revenue Growth",
        purpose="Drive sustainable, economically viable top-line revenue expansion.",
        executive_responsibility="Chief Commercial Officer / AIC CEO",
        desired_outcome="High-quality recurring or repeat revenue expansion aligned with target margins.",
        leading_indicators=["Sales Qualified Pipeline", "Lead Velocity Rate", "Bookings Momentum"],
        lagging_indicators=["Recognized GAAP Revenue", "ARR / MRR", "Revenue Growth Rate YoY"],
        financial_impact="Top-line scale enabling operating leverage.",
        strategic_impact="Market share capture and competitive deterrence.",
        risk_factors=["Discount Gaming", "High Churn Inflow", "Channel Partner Disruption"],
        benchmark_method="Industry peer growth rates for maturity and geography class.",
        measurement_frequency="MONTHLY",
        target_method="ADAPTIVE_INDUSTRY_CALIBRATION",
        escalation_threshold="Revenue shortfall >15% against calibrated baseline.",
        failure_condition="Sustained revenue contraction threatening unit viability.",
        corrective_action="Recalibrate ICP, pricing tiers, and commercial conversion funnel.",
        evidence_source="Stripe Invoicing / ERP Billing Transaction Log",
        accountable_executive="CRO_SALES_AGENT",
        dependencies=["KRA-03", "KRA-06", "KRA-07"]
    ),
    UniversalKRA(
        kra_id="KRA-03",
        kra_name="Profitability & Unit Economics",
        purpose="Ensure every unit of revenue contributes positive economic margin.",
        executive_responsibility="Chief Financial Officer / AIC CEO",
        desired_outcome="Healthy contribution margins and EBITDA progression without sacrificing product quality.",
        leading_indicators=["COGS per unit", "Gross Margin Trend", "Variable Cost Efficiency"],
        lagging_indicators=["Operating Margin", "Contribution Margin %", "EBITDA"],
        financial_impact="Generates bottom-line cash and eliminates unprofitable subsidization.",
        strategic_impact="Enables self-funding operations independent of dilutive external capital.",
        risk_factors=["Input Cost Inflation", "Hidden Operational Waste", "Underpricing"],
        benchmark_method="Industry quartile benchmarks for gross and net margin.",
        measurement_frequency="MONTHLY",
        target_method="ADAPTIVE_INDUSTRY_CALIBRATION",
        escalation_threshold="Contribution margin drops below industry floor.",
        failure_condition="Persistent negative unit economics at steady-state scale.",
        corrective_action="Mandatory margin floor enforcement; repricing or exiting unprofitable segments.",
        evidence_source="General Ledger Accounting Journal & Bank Reconciliation",
        accountable_executive="CFO_FINANCE_AGENT",
        dependencies=["KRA-02", "KRA-04", "KRA-08"]
    ),
    UniversalKRA(
        kra_id="KRA-04",
        kra_name="Cash Flow & Liquidity Preservation",
        purpose="Guarantee enterprise solvency, cash runway, and working capital health.",
        executive_responsibility="Chief Financial Officer / AIC CEO",
        desired_outcome="Positive operating cash flow and minimum required liquidity reserve intact.",
        leading_indicators=["DSO (Days Sales Outstanding)", "DPO", "Billing Cycle Velocity"],
        lagging_indicators=["Operating Cash Flow", "Free Cash Flow", "Cash Runway Months"],
        financial_impact="Prevents cash crises, default, or distressed liquidation.",
        strategic_impact="Provides resilience through macroeconomic downturns.",
        risk_factors=["Delayed Collections", "Lumpy Capital Expenditures", "Credit Facility Freezes"],
        benchmark_method="Minimum 6 to 12 months runway benchmark adjusted for burn rate.",
        measurement_frequency="WEEKLY",
        target_method="BASELINE_TREND",
        escalation_threshold="Runway drops below 90 days; immediate Level 2 emergency.",
        failure_condition="Liquidity breach; unable to meet payroll or mandatory obligations.",
        corrective_action="Activate emergency cash conservation SOP; delay non-critical AP; enforce cash collection.",
        evidence_source="Bank API Statements & Treasury Reconciliation Ledger",
        accountable_executive="CFO_FINANCE_AGENT",
        dependencies=["KRA-03", "KRA-05"]
    ),
    UniversalKRA(
        kra_id="KRA-05",
        kra_name="Capital Allocation & ROI",
        purpose="Deploy capital into highest risk-adjusted economic return opportunities.",
        executive_responsibility="AIC CEO & Executive Council",
        desired_outcome="Capital allocations beat hurdle rate with audited payback periods.",
        leading_indicators=["Project Pipeline IRR", "Payback Period Modeling", "Discounted Opportunity Cost"],
        lagging_indicators=["Realized ROIC", "Capital Payback Realization", "NPV Delivery"],
        financial_impact="Maximizes return on equity and avoids capital destruction.",
        strategic_impact="Builds durable competitive advantages and technological moats.",
        risk_factors=["Sunk Cost Fallacy", "Optimism Bias in Projections", "Cost Overruns"],
        benchmark_method="Enterprise cost of capital (WACC) + risk hurdle premium.",
        measurement_frequency="QUARTERLY",
        target_method="STRATEGIC_TARGET",
        escalation_threshold="Project ROI underperforms hurdle rate by >25% at 6-month review.",
        failure_condition="Persistent capital destruction in non-performing initiatives.",
        corrective_action="Trigger Termination / Kill SOP; reallocate remaining capital.",
        evidence_source="Executive Decision Records & Project Accounting Audits",
        accountable_executive="AIC_CEO",
        dependencies=["KRA-01", "KRA-04", "KRA-13"]
    ),
    UniversalKRA(
        kra_id="KRA-06",
        kra_name="Customer Value & Retention",
        purpose="Cultivate deep customer relationships, high retention, and long-term lifetime value.",
        executive_responsibility="Chief Customer Officer / Head of Customer Success",
        desired_outcome="High customer satisfaction, low churn, and robust lifetime value to CAC ratio.",
        leading_indicators=["Customer Health Score", "Product Adoption Depth", "Support Ticket Escalation Rate"],
        lagging_indicators=["Gross Revenue Retention (GRR)", "Net Revenue Retention (NRR)", "LTV / CAC"],
        financial_impact="Minimizes cost of customer replacement; compounding recurring revenue.",
        strategic_impact="Strengthens switching barriers and market reputation.",
        risk_factors=["Service Degradation", "Competitor Poaching", "Silent Churn"],
        benchmark_method="Industry peer NRR/GRR benchmarks matched to customer scale.",
        measurement_frequency="MONTHLY",
        target_method="ADAPTIVE_INDUSTRY_CALIBRATION",
        escalation_threshold="Monthly logo churn exceeds warning threshold by >20%.",
        failure_condition="Mass customer exodus or structural destruction of customer trust.",
        corrective_action="Deploy immediate customer rescue swat team; conduct churn forensic analysis.",
        evidence_source="CRM Database & Customer Contract Management System",
        accountable_executive="CCO_CUSTOMER_AGENT",
        dependencies=["KRA-02", "KRA-08", "KRA-14"]
    ),
    UniversalKRA(
        kra_id="KRA-07",
        kra_name="Market Position & Differentiation",
        purpose="Build and protect competitive moats, pricing power, and strategic positioning.",
        executive_responsibility="Chief Strategy Officer / CMO",
        desired_outcome="Defensible market leadership, strong organic inbound demand, and pricing power.",
        leading_indicators=["Share of Voice", "Competitive Win/Loss Ratio", "Inbound Referral Velocity"],
        lagging_indicators=["Market Share %", "Gross Margin Pricing Premium", "Brand Equity Score"],
        financial_impact="Preserves pricing power and shields margins against commoditization.",
        strategic_impact="Long-term enterprise survivability against disruptive competitors.",
        risk_factors=["Technological Disruption", "Aggressive Competitor Subsidies", "Category Commoditization"],
        benchmark_method="Competitive win rate (>50%) and analyst/industry benchmark positioning.",
        measurement_frequency="QUARTERLY",
        target_method="ADAPTIVE_INDUSTRY_CALIBRATION",
        escalation_threshold="Win/loss ratio drops below 1.0 against primary competitors.",
        failure_condition="Total commoditization resulting in inability to command gross margins.",
        corrective_action="Execute strategic positioning review; differentiate core capability stack.",
        evidence_source="Competitive Intelligence Hub & Win/Loss CRM Audits",
        accountable_executive="CSO_STRATEGY_AGENT",
        dependencies=["KRA-02", "KRA-13"]
    ),
    UniversalKRA(
        kra_id="KRA-08",
        kra_name="Operational Excellence & Quality",
        purpose="Eliminate waste, defects, bottlenecks, and latency in operational execution.",
        executive_responsibility="Chief Operating Officer / Operations Director",
        desired_outcome="Zero-defect operations, high throughput, and strict SLA fulfillment.",
        leading_indicators=["Process Cycle Time", "Work-in-Progress (WIP) Levels", "First-Pass Yield"],
        lagging_indicators=["SLA Compliance Rate", "Defect / Error Rate", "Cost per Process Output"],
        financial_impact="Lowers operating expenses and prevents costly rework or refund liabilities.",
        strategic_impact="Enables frictionless scaling without exponential headcount or resource bloat.",
        risk_factors=["Process Brittleness", "Single Points of Failure", "Unobserved Quality Drift"],
        benchmark_method="Six Sigma / Lean operational benchmarks calibrated to industry process.",
        measurement_frequency="WEEKLY",
        target_method="ADAPTIVE_INDUSTRY_CALIBRATION",
        escalation_threshold="Process defect rate crosses critical threshold; SLA breach >5%.",
        failure_condition="Systemic operational failure causing delivery collapse.",
        corrective_action="Deploy operational constraint analysis; automate or refactor process bottlenecks.",
        evidence_source="Operational Telemetry & Workflow Execution Database",
        accountable_executive="COO_OPERATIONS_AGENT",
        dependencies=["KRA-03", "KRA-06", "KRA-11"]
    ),
    UniversalKRA(
        kra_id="KRA-09",
        kra_name="Enterprise Risk Management & Resilience",
        purpose="Identify, evaluate, treat, and monitor all material enterprise risks.",
        executive_responsibility="Chief Risk Officer / AIC CEO",
        desired_outcome="Zero catastrophic unmitigated risks; rapid business continuity recovery.",
        leading_indicators=["Risk Register Movement", "Near-Miss Incident Reports", "Control Effectiveness Testing"],
        lagging_indicators=["Annualized Loss Expectancy (ALE)", "Incident Recovery Time (MTTR)", "Insurability Rating"],
        financial_impact="Prevents asymmetric catastrophic financial ruin and claims exposure.",
        strategic_impact="Ensures business continuity through black-swan shocks.",
        risk_factors=["Unidentified Risks", "Inadequate Contingency Reserves", "Risk Appetite Creep"],
        benchmark_method="ISO 31000 risk management maturity standards.",
        measurement_frequency="CONTINUOUS",
        target_method="STRATEGIC_TARGET",
        escalation_threshold="Any Critical Tier-1 risk unmitigated for >48 hours.",
        failure_condition="Unmitigated risk materializes into existential enterprise distress.",
        corrective_action="Activate Business Continuity & Crisis Response Protocol immediately.",
        evidence_source="Enterprise Risk Register & Audit Incident Logs",
        accountable_executive="CRO_RISK_AGENT",
        dependencies=["KRA-04", "KRA-10"]
    ),
    UniversalKRA(
        kra_id="KRA-10",
        kra_name="Governance, Compliance & Ethics",
        purpose="Enforce lawful, ethical, auditable operations conforming to all laws and regulations.",
        executive_responsibility="General Counsel & Compliance Director",
        desired_outcome="100% compliance with applicable laws, zero regulatory fines or ethical breaches.",
        leading_indicators=["Compliance Audit Coverage", "Whistleblower / Issue Log Latency", "Regulatory Horizon Tracking"],
        lagging_indicators=["Regulatory Fines ($0 Target)", "Legal Disputes Settled", "Audit Finding Resolution Rate"],
        financial_impact="Avoids criminal/civil penalties, sanctions, and reputational destruction.",
        strategic_impact="Maintains social license to operate and investor confidence.",
        risk_factors=["Regulatory Blindspots", "Jurisdictional Rule Divergence", "Employee Malfeasance"],
        benchmark_method="ISO 37000 / ISO 37301 compliance management frameworks.",
        measurement_frequency="MONTHLY",
        target_method="STRATEGIC_TARGET",
        escalation_threshold="Any material statutory or regulatory breach identified.",
        failure_condition="Criminal indictment, regulatory revocation of operating license, or systemic fraud.",
        corrective_action="Halt non-compliant operations immediately; self-report if required; remediate root cause.",
        evidence_source="Legal Compliance Register & Independent Audit Evidence",
        accountable_executive="LEGAL_COMPLIANCE_AGENT",
        dependencies=["KRA-01", "KRA-09"]
    ),
    UniversalKRA(
        kra_id="KRA-11",
        kra_name="Technology, AI Transformation & Security",
        purpose="Govern modern, secure, cost-effective technology and governed AI capabilities.",
        executive_responsibility="Chief Technology Officer / Chief Information Officer",
        desired_outcome="High system uptime, low technical debt, secure data infrastructure, and cost-effective AI.",
        leading_indicators=["AI Cost per Verified Outcome", "Vulnerability Remediated Latency", "Deployment Velocity"],
        lagging_indicators=["System Availability (99.9%+)", "Cybersecurity Incidents", "Compute Capital Efficiency"],
        financial_impact="Drives operational automation while bounding compute and licensing costs.",
        strategic_impact="Technological agility and defensible automation capability.",
        risk_factors=["Model Hallucinations", "Cyber Exploits", "Runaway Cloud / API Costs"],
        benchmark_method="ISO/IEC 42001 and ISO/IEC 27001 management standards.",
        measurement_frequency="WEEKLY",
        target_method="STRATEGIC_TARGET",
        escalation_threshold="Cyber security breach or monthly AI spend exceeding budget by >25%.",
        failure_condition="Complete infrastructure compromise or uncontrollable compute burn.",
        corrective_action="Enforce spend governor; route models to deterministic fallbacks; isolate compromised hosts.",
        evidence_source="DevOps / Cloud Billing Telemetry & SIEM Security Logs",
        accountable_executive="CTO_TECH_AGENT",
        dependencies=["KRA-08", "KRA-09"]
    ),
    UniversalKRA(
        kra_id="KRA-12",
        kra_name="Organization, Workforce & Leadership",
        purpose="Architect high-performance digital and human workforce capacity.",
        executive_responsibility="Chief Human Resources Officer / Workforce Architect",
        desired_outcome="Optimally sized, highly productive, specialized workforce without excess overhead.",
        leading_indicators=["Agent Task Verification Rate", "Role Capability Coverage", "Decision Latency"],
        lagging_indicators=["Revenue per Workforce Unit", "Workforce Turnover / Replacement Rate", "Employee NPS"],
        financial_impact="Maximizes human/AI workforce ROI and controls fixed overhead costs.",
        strategic_impact="Ensures enterprise execution capability scales without friction.",
        risk_factors=["Organizational Bloat", "Agent Hallucination Cascade", "Key Personnel Attrition"],
        benchmark_method="Revenue per employee / agent quartile benchmarks for industry archetype.",
        measurement_frequency="MONTHLY",
        target_method="ADAPTIVE_INDUSTRY_CALIBRATION",
        escalation_threshold="Workforce productivity drops below 80% of calibrated baseline.",
        failure_condition="Organizational gridlock, widespread capability collapse, or high key-talent attrition.",
        corrective_action="Restructure team workflows; de-duplicate roles; reassign or retrain agents.",
        evidence_source="Workforce Directory & Organizational Productivity Ledger",
        accountable_executive="CHRO_WORKFORCE_AGENT",
        dependencies=["KRA-08", "KRA-11"]
    ),
    UniversalKRA(
        kra_id="KRA-13",
        kra_name="Innovation & Strategic Optionality",
        purpose="Incubate breakthrough offerings, business models, and new market opportunities.",
        executive_responsibility="Chief Innovation Officer / AIC CEO",
        desired_outcome="Structured pipeline of validated new offerings driving future growth.",
        leading_indicators=["Hypotheses Tested per Month", "Customer Problem Validation Speed", "Pilot Conversion Rate"],
        lagging_indicators=["Revenue from Offerings <2 Years Old", "Patent / IP Assets Created", "Innovation ROI"],
        financial_impact="Compounds future revenue curves and avoids obsolescence.",
        strategic_impact="Creates long-term optionality and strategic adaptability.",
        risk_factors=["Uncontrolled Experimentation Burn", "Failure to Kill Losing Bets", "Distraction from Core"],
        benchmark_method="Innovation portfolio balance (70% Core, 20% Adjacent, 10% Transformational).",
        measurement_frequency="QUARTERLY",
        target_method="STRATEGIC_TARGET",
        escalation_threshold="Three consecutive failed pilot phases with zero customer validation.",
        failure_condition="Complete strategic stagnation leading to market irrelevance.",
        corrective_action="Apply strict Stage-Gate Killing Protocol; pivot or prune experimental budget.",
        evidence_source="R&D Experimentation Ledger & Product Analytics",
        accountable_executive="HEAD_OF_INNOVATION_AGENT",
        dependencies=["KRA-01", "KRA-05", "KRA-07"]
    ),
    UniversalKRA(
        kra_id="KRA-14",
        kra_name="Reputation & Stakeholder Trust",
        purpose="Safeguard brand equity, customer trust, and credibility across all stakeholder groups.",
        executive_responsibility="Head of Communications / AIC CEO",
        desired_outcome="Consistently high stakeholder confidence, positive sentiment, and brand defensibility.",
        leading_indicators=["Social / Media Sentiment Trend", "Public Review Ratings", "Customer Trust Index"],
        lagging_indicators=["Net Promoter Score (NPS)", "Stakeholder Retention Rate", "Brand Valuation Index"],
        financial_impact="Lowers customer acquisition costs and builds durable organic pricing power.",
        strategic_impact="Insulates enterprise against reputational crises and adverse publicity.",
        risk_factors=["PR Crisis", "Social Media Misinformation", "Unaddressed Service Failures"],
        benchmark_method="Industry customer NPS and stakeholder trust index.",
        measurement_frequency="MONTHLY",
        target_method="ADAPTIVE_INDUSTRY_CALIBRATION",
        escalation_threshold="Public NPS drops by >15 points in a single evaluation cycle.",
        failure_condition="Catastrophic brand destruction resulting in mass cancellation/boycott.",
        corrective_action="Activate Reputational Crisis SOP; communicate transparent facts; fix underlying defect.",
        evidence_source="Reputation Monitoring Telemetry & Review Aggregator APIs",
        accountable_executive="COMMS_REPUTATION_AGENT",
        dependencies=["KRA-06", "KRA-10"]
    ),
    UniversalKRA(
        kra_id="KRA-15",
        kra_name="Long-Term Viability & Sustainability",
        purpose="Ensure multi-year enterprise endurance, ESG compliance, and generational viability.",
        executive_responsibility="AIC CEO & Sovereign Governing Body",
        desired_outcome="Zero existential vulnerabilities; resilient adaptation to energy, climate, and macro shifts.",
        leading_indicators=["Energy Efficiency Metrics", "Supply Chain Diversification Index", "Macro Shock Stress Score"],
        lagging_indicators=["Enterprise Viability Rating", "ESG Compliance Score", "Multi-Year Survival Probability"],
        financial_impact="Protects long-term asset valuations and prevents stranded asset write-offs.",
        strategic_impact="Guarantees enterprise longevity across changing technological and societal landscapes.",
        risk_factors=["Single Supplier / Single Region Dependency", "Regulatory Sunset Provisions", "Climate Liabilities"],
        benchmark_method="Multi-scenario macro resilience stress test models.",
        measurement_frequency="ANNUALLY",
        target_method="STRATEGIC_TARGET",
        escalation_threshold="Stress-test reveals unhedged existential vulnerability to 24-month horizon shock.",
        failure_condition="Enterprise failure due to unmitigated macro, environmental, or regulatory obsolescence.",
        corrective_action="Execute strategic diversification; hedge catastrophic exposures; redesign core dependencies.",
        evidence_source="Annual Executive Sustainability & Viability Audit Report",
        accountable_executive="AIC_CEO",
        dependencies=["KRA-01", "KRA-09", "KRA-10"]
    )
]

# ==============================================================================
# 3. ANTI-GAMING DETECTION ENGINE
# ==============================================================================

@dataclass
class MetricPairEvaluation:
    primary_metric_name: str
    primary_metric_change_pct: float
    counter_metric_name: str
    counter_metric_change_pct: float
    is_gaming_detected: bool
    diagnosis: str
    recommended_intervention: str

class AntiGamingEngine:
    """
    Detects gaming of vanity or local metrics at the expense of true business outcomes.
    Examples:
      - Revenue increased (+20%), but Contribution Margin fell (-30%)
      - Bookings increased (+40%), but Cancellations spiked (+80%)
      - Leads increased (+50%), but Qualified Conversion plummeted (-60%)
      - Support tickets closed fast (-50% time), but Churn increased (+25%)
      - Output throughput increased (+30%), but Defect rate jumped (+100%)
      - Agent tasks completed (+100%), but Business Revenue / Cash remained 0
    """
    def __init__(self):
        self._rules = [
            {
                "primary": "revenue",
                "counter": "contribution_margin",
                "condition": lambda p, c: p > 5.0 and c < -5.0,
                "diagnosis": "Revenue growth is being achieved through unprofitable discounts or negative contribution margin.",
                "intervention": "Enforce strict margin floor policy; prohibit below-cost sales without sovereign waiver."
            },
            {
                "primary": "bookings",
                "counter": "cancellations",
                "condition": lambda p, c: p > 10.0 and c > 20.0,
                "diagnosis": "Booking volume is being artificially inflated through deceptive terms or unqualified demand, driving cancellation spikes.",
                "intervention": "Audit booking qualification criteria and customer intent verification."
            },
            {
                "primary": "leads",
                "counter": "qualified_conversions",
                "condition": lambda p, c: p > 20.0 and c < -15.0,
                "diagnosis": "Marketing agent is optimizing vanity lead volume with poor ICP alignment, increasing SDR waste.",
                "intervention": "Tie marketing agent performance directly to Sales Qualified Pipeline (SQP) rather than raw leads."
            },
            {
                "primary": "support_resolution_speed",
                "counter": "resolution_quality",
                "condition": lambda p, c: p > 20.0 and c < -10.0,
                "diagnosis": "Support agents are rushing ticket closures without solving root causes, damaging customer trust.",
                "intervention": "Prioritize First-Contact Resolution (FCR) and Customer Satisfaction (CSAT) over speed-to-close."
            },
            {
                "primary": "throughput",
                "counter": "defect_rate",
                "condition": lambda p, c: p > 10.0 and c > 15.0,
                "diagnosis": "Manufacturing/production is forcing speed at the expense of quality, creating warranty/scrap liabilities.",
                "intervention": "Halt throughput acceleration; recalibrate quality inspection gates."
            },
            {
                "primary": "agent_task_completions",
                "counter": "verified_revenue_cash",
                "condition": lambda p, c: p > 50.0 and c <= 0.0,
                "diagnosis": "Agent activity explosion without corresponding business economic realization (Activity != Achievement).",
                "intervention": "Terminate unaligned agent swarms; demand verified business causality before task reactivation."
            }
        ]

    def evaluate_pair(
        self,
        primary_name: str,
        primary_delta_pct: float,
        counter_name: str,
        counter_delta_pct: float
    ) -> MetricPairEvaluation:
        norm_p = primary_name.lower().replace(" ", "_")
        norm_c = counter_name.lower().replace(" ", "_")

        for r in self._rules:
            if r["primary"] in norm_p and r["counter"] in norm_c:
                if r["condition"](primary_delta_pct, counter_delta_pct):
                    return MetricPairEvaluation(
                        primary_metric_name=primary_name,
                        primary_metric_change_pct=primary_delta_pct,
                        counter_metric_name=counter_name,
                        counter_metric_change_pct=counter_delta_pct,
                        is_gaming_detected=True,
                        diagnosis=r["diagnosis"],
                        recommended_intervention=r["intervention"]
                    )

        # Default healthy / no gaming detected
        return MetricPairEvaluation(
            primary_metric_name=primary_name,
            primary_metric_change_pct=primary_delta_pct,
            counter_metric_name=counter_name,
            counter_metric_change_pct=counter_delta_pct,
            is_gaming_detected=False,
            diagnosis="Metrics show aligned healthy movement without adversarial gaming.",
            recommended_intervention="Maintain current operational monitoring."
        )

# ==============================================================================
# 4. ADAPTIVE INDUSTRY BENCHMARKING ENGINE (NO UNIVERSAL HARDCODING)
# ==============================================================================

@dataclass
class CalibratedBenchmarkResult:
    industry: IndustryArchetype
    maturity: CompanyMaturity
    metric_name: str
    calibrated_baseline: float
    calibrated_target: float
    calibrated_stretch: float
    calibrated_minimum_acceptable: float
    benchmark_status: str                # CALIBRATED_FROM_PEERS, BENCHMARK UNKNOWN
    rationale: str

class AdaptiveIndustryBenchmarkingEngine:
    """
    Prevents blind application of universal KPI targets (e.g. 120% NRR or 85% OEE across all companies).
    Calibrates targets against:
      - Industry archetype (SaaS, Hospitality, Healthcare, Manufacturing, E-Commerce, etc.)
      - Company maturity (Seed, Early Growth, Scaleup, Mature Enterprise, Distressed)
      - Business model, geography, scale, and capital structure.
    If no reliable benchmark data exists, returns 'BENCHMARK UNKNOWN' rather than fabricating numbers.
    """
    # Industry reference models based on empirically documented standard reference classes
    _ARCHETYPE_BENCHMARKS = {
        IndustryArchetype.SAAS_SOFTWARE: {
            "NRR_PERCENT": {
                CompanyMaturity.SEED: (85.0, 100.0, 110.0, 75.0),
                CompanyMaturity.EARLY_GROWTH: (95.0, 110.0, 120.0, 85.0),
                CompanyMaturity.SCALEUP: (105.0, 120.0, 130.0, 95.0),
                CompanyMaturity.MATURE_ENTERPRISE: (100.0, 112.0, 120.0, 90.0),
                CompanyMaturity.DISTRESSED: (70.0, 85.0, 95.0, 60.0),
            },
            "GROSS_MARGIN_PERCENT": {
                CompanyMaturity.EARLY_GROWTH: (65.0, 75.0, 82.0, 55.0),
                CompanyMaturity.MATURE_ENTERPRISE: (72.0, 80.0, 85.0, 65.0),
            },
            "CAC_PAYBACK_MONTHS": {
                CompanyMaturity.EARLY_GROWTH: (18.0, 12.0, 8.0, 24.0),
                CompanyMaturity.MATURE_ENTERPRISE: (15.0, 10.0, 6.0, 18.0),
            }
        },
        IndustryArchetype.HOSPITALITY_TOURISM: {
            "OCCUPANCY_PERCENT": {
                CompanyMaturity.EARLY_GROWTH: (55.0, 68.0, 78.0, 45.0),
                CompanyMaturity.MATURE_ENTERPRISE: (65.0, 75.0, 85.0, 55.0),
                CompanyMaturity.DISTRESSED: (35.0, 50.0, 60.0, 25.0)
            },
            "GOP_MARGIN_PERCENT": {
                CompanyMaturity.MATURE_ENTERPRISE: (25.0, 35.0, 42.0, 18.0),
            },
            "DIRECT_BOOKING_SHARE_PERCENT": {
                CompanyMaturity.MATURE_ENTERPRISE: (20.0, 35.0, 50.0, 12.0),
            }
        },
        IndustryArchetype.MANUFACTURING_INDUSTRIAL: {
            "OEE_PERCENT": {
                CompanyMaturity.EARLY_GROWTH: (60.0, 72.0, 80.0, 50.0),
                CompanyMaturity.MATURE_ENTERPRISE: (70.0, 82.0, 88.0, 62.0),
            },
            "FIRST_PASS_YIELD_PERCENT": {
                CompanyMaturity.MATURE_ENTERPRISE: (90.0, 96.0, 99.0, 85.0),
            }
        },
        IndustryArchetype.HEALTHCARE_CLINICAL: {
            "CLINICAL_COMPLIANCE_PERCENT": {
                CompanyMaturity.MATURE_ENTERPRISE: (98.0, 100.0, 100.0, 95.0),
            },
            "OPERATING_MARGIN_PERCENT": {
                CompanyMaturity.MATURE_ENTERPRISE: (5.0, 9.0, 14.0, 2.0),
            }
        }
    }

    def calibrate(
        self,
        industry: IndustryArchetype,
        maturity: CompanyMaturity,
        metric_name: str,
        historical_baseline: Optional[float] = None
    ) -> CalibratedBenchmarkResult:
        """
        Calibrates targets specifically for industry and maturity, or flags BENCHMARK UNKNOWN.
        """
        norm_metric = metric_name.upper().replace(" ", "_")
        ind_data = self._ARCHETYPE_BENCHMARKS.get(industry)

        if not ind_data or norm_metric not in ind_data:
            # Explicitly mark BENCHMARK UNKNOWN rather than fabricating numbers
            base = historical_baseline if historical_baseline is not None else 0.0
            return CalibratedBenchmarkResult(
                industry=industry,
                maturity=maturity,
                metric_name=metric_name,
                calibrated_baseline=base,
                calibrated_target=base * 1.1 if base else 0.0,
                calibrated_stretch=base * 1.25 if base else 0.0,
                calibrated_minimum_acceptable=base * 0.9 if base else 0.0,
                benchmark_status="BENCHMARK UNKNOWN",
                rationale=f"No verified empirical benchmark exists for metric '{metric_name}' in {industry.value}; explicit BENCHMARK UNKNOWN status assigned."
            )

        metric_maturity_data = ind_data[norm_metric]
        data_tuple = metric_maturity_data.get(maturity)

        if not data_tuple:
            # Fallback to MATURE_ENTERPRISE reference or first available with adjustment
            data_tuple = next(iter(metric_maturity_data.values()))
            status = "CALIBRATED_FROM_ADJACENT_MATURITY"
        else:
            status = "CALIBRATED_FROM_PEERS"

        base, target, stretch, min_acc = data_tuple

        # Blend with historical company baseline if provided
        if historical_baseline is not None:
            cal_base = round(historical_baseline, 2)
            cal_target = round((historical_baseline * 0.4) + (target * 0.6), 2)
            cal_stretch = round((historical_baseline * 0.3) + (stretch * 0.7), 2)
            cal_min = round(min(historical_baseline * 0.95, min_acc), 2)
            rationale = f"Blended historical baseline ({historical_baseline}) with calibrated peer benchmark ({target}) for {industry.value} ({maturity.value})."
        else:
            cal_base, cal_target, cal_stretch, cal_min = base, target, stretch, min_acc
            rationale = f"Calibrated strictly from verified peer class: {industry.value} under {maturity.value} lifecycle."

        return CalibratedBenchmarkResult(
            industry=industry,
            maturity=maturity,
            metric_name=metric_name,
            calibrated_baseline=cal_base,
            calibrated_target=cal_target,
            calibrated_stretch=cal_stretch,
            calibrated_minimum_acceptable=cal_min,
            benchmark_status=status,
            rationale=rationale
        )

# ==============================================================================
# 5. 10-POINT KPI QUALITY TESTER
# ==============================================================================

@dataclass
class KPIQualityCheckResult:
    kpi_id: str
    kpi_name: str
    passes_all_tests: bool
    quality_score: float                # 0 - 100
    criteria_evaluations: Dict[str, bool]
    failure_reasons: List[str]

class KPIQualityTester:
    """
    Enforces the constitutional 10-point test before any KPI can be adopted into the executive scorecard:
      1. Is it measurable?
      2. Is the data trustworthy?
      3. Does it influence the desired outcome?
      4. Can it be gamed?
      5. What happens if it is optimized?
      6. Can it create harmful side effects?
      7. Is it comparable?
      8. Is it timely?
      9. Is it economically relevant?
      10. Does it have an accountable owner?
    """
    @classmethod
    def test_kpi(cls, kpi: HierarchicalKPI) -> KPIQualityCheckResult:
        evals = {}
        failures = []

        # 1. Measurable
        evals["is_measurable"] = bool(kpi.unit and kpi.formula)
        if not evals["is_measurable"]:
            failures.append("KPI lacks precise formula or measurable unit.")

        # 2. Data trustworthy
        evals["is_data_trustworthy"] = bool(kpi.data_source and kpi.confidence_level != "UNKNOWN")
        if not evals["is_data_trustworthy"]:
            failures.append("Data source is unverified or confidence is UNKNOWN.")

        # 3. Influences outcome
        evals["influences_outcome"] = kpi.tier in (KPITier.TIER_0_ENTERPRISE_VALUE, KPITier.TIER_1_FINANCIAL, KPITier.TIER_2_CUSTOMER_MARKET, KPITier.TIER_3_OPERATIONAL)
        if not evals["influences_outcome"]:
            failures.append("KPI resides in low-tier activity without demonstrable causal link to enterprise outcome.")

        # 4. Gaming resistance
        evals["gaming_guarded"] = bool(kpi.gaming_risk_guardrail)
        if not evals["gaming_guarded"]:
            failures.append("KPI has no paired guardrail metric to prevent local gaming.")

        # 5 & 6. Side effects assessed
        evals["side_effects_controlled"] = bool(kpi.minimum_acceptable is not None and kpi.warning_threshold is not None)
        if not evals["side_effects_controlled"]:
            failures.append("Missing minimum acceptable floor or warning thresholds.")

        # 7. Comparable
        evals["is_comparable"] = bool(kpi.benchmark_source)
        if not evals["is_comparable"]:
            failures.append("No benchmark reference class or comparative historical method assigned.")

        # 8. Timely
        evals["is_timely"] = bool(kpi.frequency in ("CONTINUOUS", "DAILY", "WEEKLY", "MONTHLY"))
        if not evals["is_timely"]:
            failures.append(f"Measurement frequency '{kpi.frequency}' is too slow for active operational steering.")

        # 9. Economically relevant
        evals["is_economically_relevant"] = kpi.classification in (KPIClassification.NORTH_STAR, KPIClassification.FINANCIAL, KPIClassification.GUARDRAIL, KPIClassification.STRATEGIC, KPIClassification.EFFICIENCY)
        if not evals["is_economically_relevant"]:
            failures.append("Metric appears to be a vanity metric lacking direct economic relevance.")

        # 10. Accountable owner
        evals["has_accountable_owner"] = bool(kpi.accountable_owner)
        if not evals["has_accountable_owner"]:
            failures.append("KPI lacks an assigned, attributable executive owner.")

        passed_count = sum(1 for v in evals.values() if v)
        score = round((passed_count / len(evals)) * 100.0, 1)
        all_passed = (passed_count == len(evals))

        return KPIQualityCheckResult(
            kpi_id=kpi.kpi_id,
            kpi_name=kpi.name,
            passes_all_tests=all_passed,
            quality_score=score,
            criteria_evaluations=evals,
            failure_reasons=failures
        )
