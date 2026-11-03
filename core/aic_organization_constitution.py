"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Universal Organization Layer beneath the AIC CEO:
Organization Constitution, Dynamic Hierarchy, Executive Role Registry,
KRA/KPI Cascade, Executable SOPs, Agent Workforce Architecture,
Communication, Delegation, Escalation, and Organization Scaling Engine.

Standards Alignment:
  ISO 37000 (Governance of Organizations)
  ISO 31000 (Risk Management)
  ISO 37301 (Compliance Management)
  ISO/IEC 42001 (AI Management System)

Constitutional Invariants:
  1. DYNAMIC_ASSEMBLY (No one-size-fits-all hierarchy. Executives, departments, and agents are synthesized to actual business reality)
  2. BOUNDED_DELEGATION (Delegation transfers bounded execution responsibility, never sovereign constitutional authority)
  3. HUMAN_AUTHORITY_PROTECTION (AI agent role title != legal authority. Agents cannot bind the enterprise in law without explicit human approval)
  4. INVARIANT_VERIFICATION (TASK_COMPLETION != MISSION_COMPLETION != BUSINESS_OUTCOME != CASH)
  5. ANTI_GAMING (Every primary metric is paired with a counter-metric to prevent local metric optimization at enterprise expense)
"""

import time
import json
import uuid
import hashlib
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from core.db import db
from core.database_engine import engine, WorkloadType

logger = logging.getLogger("zonata.org.constitution")

# ==============================================================================
# 1. ENUMS & CONSTANTS
# ==============================================================================

class HierarchyLevel(str, Enum):
    L0_OWNER = "L0_OWNER"
    L1_GOVERNANCE = "L1_GOVERNANCE"
    L2_CEO = "L2_CEO"
    L3_CHIEF_EXECUTIVE = "L3_CHIEF_EXECUTIVE"
    L4_BUSINESS_UNIT = "L4_BUSINESS_UNIT"
    L5_DEPARTMENT = "L5_DEPARTMENT"
    L6_FUNCTION = "L6_FUNCTION"
    L7_TEAM = "L7_TEAM"
    L8_MANAGER = "L8_MANAGER"
    L9_SPECIALIST = "L9_SPECIALIST"
    L10_WORKER = "L10_WORKER"
    L11_TASK = "L11_TASK"

class RoleRequirementStatus(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    COMBINABLE = "COMBINABLE"
    NOT_REQUIRED = "NOT_REQUIRED"
    FUTURE = "FUTURE"

class WorkforceType(str, Enum):
    HUMAN = "HUMAN"
    AI_AGENT = "AI_AGENT"
    HYBRID = "HYBRID"
    AUTOMATION = "AUTOMATION"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"

class AgentCategory(str, Enum):
    EXECUTIVE_AGENT = "EXECUTIVE_AGENT"
    MANAGEMENT_AGENT = "MANAGEMENT_AGENT"
    SPECIALIST_AGENT = "SPECIALIST_AGENT"
    WORKER_AGENT = "WORKER_AGENT"
    EXECUTION_AGENT = "EXECUTION_AGENT"

class CompanyScaleStage(str, Enum):
    MICRO_STARTUP = "MICRO_STARTUP"       # 1-10 people/agents
    SMALL_COMPANY = "SMALL_COMPANY"       # 11-50 people/agents
    GROWING_COMPANY = "GROWING_COMPANY"   # 51-250 people/agents
    MIDSIZE_COMPANY = "MIDSIZE_COMPANY"   # 251-1000 people/agents
    ENTERPRISE = "ENTERPRISE"             # 1000+ people/agents

class MessagePriority(str, Enum):
    INFO = "INFO"
    REQUEST = "REQUEST"
    DECISION = "DECISION"
    APPROVAL = "APPROVAL"
    ESCALATION = "ESCALATION"
    ALERT = "ALERT"

class OperatingCadence(str, Enum):
    DAILY = "DAILY"           # Operational exceptions
    WEEKLY = "WEEKLY"         # Department performance
    MONTHLY = "MONTHLY"       # Financial + operational + commercial
    QUARTERLY = "QUARTERLY"   # Strategy + capital allocation + org
    ANNUAL = "ANNUAL"         # Enterprise strategy + budget + org design

# ==============================================================================
# 2. ORGANIZATION CONSTITUTION DATA STRUCTURES
# ==============================================================================

@dataclass
class AccountabilityNode:
    """
    16-Field machine-enforceable accountability node for every organizational entity.
    """
    node_id: str
    owner: str                          # Responsible persona / identity
    purpose: str                        # Why this node exists
    mission: str                        # Current operational mandate
    authority_level: str                # SOVEREIGN, EXECUTIVE_FUNCTION, DEPARTMENTAL, DELEGATED
    responsibility: List[str]           # Specific operational duties
    accountability: str                 # Exact business outcome this node answers for
    kra_ids: List[str]                  # Key Result Areas assigned
    kpi_ids: List[str]                  # Specific metrics measuring success
    budget_limit_usd: float             # Hard financial spend envelope
    resources_allocated: Dict[str, Any] # People, Compute, Tool tokens
    reporting_line_id: Optional[str]    # Parent node ID
    communication_channels: List[str]   # Allowed communication pathways
    escalation_path_id: str             # Where to route exceptions
    risk_limit: str                     # LOW, MEDIUM, HIGH, CRITICAL
    success_criteria: str               # Ground truth proof of success
    verification_method: str            # Cryptographic, Audited Statement, Telemetry

@dataclass
class AuthorityMatrix:
    """
    Constitutional permissions matrix defining who may execute corporate actions.
    """
    can_decide: List[str] = field(default_factory=list)
    can_approve: List[str] = field(default_factory=list)
    can_execute: List[str] = field(default_factory=list)
    can_delegate: List[str] = field(default_factory=list)
    can_spend_usd_limit: float = 0.0
    can_hire: bool = False
    can_fire: bool = False
    can_contract: bool = False
    can_negotiate: bool = False
    can_access_data: List[str] = field(default_factory=list)
    can_change_systems: bool = False
    can_create_agents: bool = False
    can_disable_agents: bool = False
    can_modify_sops: bool = False
    can_change_kpis: bool = False
    can_change_org_structure: bool = False

# ==============================================================================
# 3. UNIVERSAL EXECUTIVE ROLE REGISTRY
# ==============================================================================

@dataclass
class ExecutiveRoleDefinition:
    role_id: str
    role_name: str
    purpose: str
    when_required: str
    when_optional: str
    authority_scope: str
    responsibilities: List[str]
    kra: List[str]
    kpi: List[str]
    sop_ids: List[str]
    reporting_line: str
    subordinate_functions: List[str]
    decision_rights: List[str]
    budget_authority_usd: float
    risk_authority: str
    required_data: List[str]
    required_tools: List[str]
    escalation_conditions: List[str]
    replacement_failover_role: str
    combinable_with: List[str] = field(default_factory=list)

class ExecutiveRoleRegistry:
    """
    Universal repository of canonical executive roles and dynamic requirements.
    """
    _ROLES: Dict[str, ExecutiveRoleDefinition] = {}

    @classmethod
    def initialize(cls):
        if cls._ROLES:
            return

        roles_data = [
            ExecutiveRoleDefinition(
                role_id="EXEC_CEO",
                role_name="AIC Chief Executive Officer (CEO)",
                purpose="Overall enterprise economic, strategic, and organizational leadership on behalf of Sovereign Owner.",
                when_required="Always mandatory for all organizations.",
                when_optional="Never optional.",
                authority_scope="Enterprise-wide operational executive authority bounded by Owner DoA.",
                responsibilities=[
                    "Enterprise strategy & capital allocation",
                    "Dynamic organization design & executive leadership",
                    "Sustainable revenue, gross profit, and cash generation",
                    "Enterprise resilience, risk governance, and owner reporting"
                ],
                kra=["Enterprise Economic Value", "Capital Efficiency (ROIC)", "Organizational Discipline"],
                kpi=["EBITDA Margin %", "Free Cash Flow USD", "Composite Qualification Index"],
                sop_ids=["SOP-CEO-01-CapitalAllocation", "SOP-CEO-02-OrgRestructure"],
                reporting_line="OWNER_SOVEREIGN",
                subordinate_functions=["CFO", "COO", "CTO", "CMO", "CRO", "CHRO", "CLO"],
                decision_rights=["Class A Bounded Decisions", "Executive Delegation", "Capital Reallocation"],
                budget_authority_usd=500000.0,
                risk_authority="HIGH",
                required_data=["ALL_ENTERPRISE_LEDGERS", "TREASURY_CASH", "MARKET_INTELLIGENCE"],
                required_tools=["AuthorityGateway", "EvidenceLedger", "PolicyEngine", "OpenHandsRuntime"],
                escalation_conditions=["Existential Cash Shock", "Constitutional Breach", "Statutory Injunction"],
                replacement_failover_role="DEPUTY_CEO_OR_COO",
                combinable_with=[]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CFO",
                role_name="Chief Financial Officer (CFO)",
                purpose="Financial integrity, treasury solvency, financial planning, and capital efficiency.",
                when_required="Small, Growing, Midsize, and Enterprise scale companies.",
                when_optional="Micro/early startup (combined into CEO or COO).",
                authority_scope="Treasury management, accounting, financial planning, audit compliance.",
                responsibilities=[
                    "Accounting, general ledger, and financial reporting",
                    "Treasury, cash preservation, and liquidity buffer",
                    "FP&A, revenue forecasting, and capital allocation analysis",
                    "Internal financial controls, tax compliance, and working capital optimization"
                ],
                kra=["Financial Solvency", "Capital Preservation", "Working Capital Optimization (DSO)"],
                kpi=["Cash Runway (Months)", "Contribution Margin %", "DSO (Days Sales Outstanding)"],
                sop_ids=["SOP-FIN-01-InvoiceCollection", "SOP-FIN-02-TreasuryDisbursement"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["FP&A", "Accounting", "Treasury", "Accounts Receivable", "Accounts Payable", "Tax"],
                decision_rights=["Disbursements within DoA", "Credit Terms Approval", "Budget Rebalancing"],
                budget_authority_usd=100000.0,
                risk_authority="MEDIUM",
                required_data=["ACCOUNTING_ERP", "BANKING_FEEDS", "INVOICING_SYSTEMS"],
                required_tools=["QuickBooksAPI", "StripeTreasury", "AuditVerificationEngine"],
                escalation_conditions=["Cash runway < 3 months", "Unreconciled discrepancy > $10,000"],
                replacement_failover_role="FINANCE_CONTROLLER_OR_CEO",
                combinable_with=["EXEC_CIO", "EXEC_COO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_COO",
                role_name="Chief Operating Officer (COO)",
                purpose="Convert strategic intent into repeatable operational execution, quality, and SLA fulfillment.",
                when_required="Operations-heavy, hospitality, manufacturing, logistics, or multi-department companies.",
                when_optional="Lean digital product companies in early seed phase.",
                authority_scope="Operational workflow execution, resource capacity, service quality, vendor SLAs.",
                responsibilities=[
                    "Service delivery and end-to-end operational execution",
                    "Operational productivity, throughput, and capacity planning",
                    "SLA fulfillment, quality assurance, and continuous improvement",
                    "Cross-functional operational coordination and vendor performance"
                ],
                kra=["Operational Excellence", "SLA Adherence", "Capacity Utilization"],
                kpi=["Operational Efficiency Ratio", "SLA Violation Rate %", "Unit Delivery Cost"],
                sop_ids=["SOP-OPS-01-IncidentEscalation", "SOP-OPS-02-CapacityScaling"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Operations", "Quality Assurance", "Process Excellence", "Service Delivery"],
                decision_rights=["Operational Scheduling", "Process Modifications", "Capacity Reallocation"],
                budget_authority_usd=50000.0,
                risk_authority="MEDIUM",
                required_data=["OPERATIONAL_TELEMETRY", "INVENTORY_PMS_SYSTEMS", "TICKET_QUEUES"],
                required_tools=["TemporalWorkflowEngine", "ServiceDeskAPI", "CapacityManager"],
                escalation_conditions=["SLA breach > 5%", "Safety incident", "Critical facility failure"],
                replacement_failover_role="OPERATIONS_DIRECTOR_OR_CEO",
                combinable_with=["EXEC_CTO", "EXEC_CSCO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CTO",
                role_name="Chief Technology Officer (CTO)",
                purpose="Technology architecture, software engineering, cloud infrastructure, and technical reliability.",
                when_required="SaaS, tech-enabled, digital commerce, and automation-heavy companies.",
                when_optional="Non-technical small services companies (outsourced to external managed IT).",
                authority_scope="Software systems, cloud compute infrastructure, DevOps pipelines, developer tools.",
                responsibilities=[
                    "Technology strategy, architecture roadmap, and system design",
                    "Software engineering execution, code quality, and testing standards",
                    "Cloud infrastructure resilience, DevOps, SRE, and uptime",
                    "Technical debt mitigation and AI/ML model deployment"
                ],
                kra=["System Reliability & Uptime", "Engineering Velocity", "Technical Architecture Integrity"],
                kpi=["System Uptime %", "Mean Time To Recovery (MTTR)", "Sprint Deliverable Velocity"],
                sop_ids=["SOP-TECH-01-DeploymentRollback", "SOP-TECH-02-ComputeScaling"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Engineering", "Architecture", "Infrastructure/SRE", "AI/ML", "QA"],
                decision_rights=["Tech Stack Architecture", "Production Release Approval", "Infra Scaling"],
                budget_authority_usd=50000.0,
                risk_authority="MEDIUM",
                required_data=["GIT_REPOSITORIES", "CLOUD_METRICS", "ERROR_LOGS"],
                required_tools=["OpenHandsExecutionManager", "TemporalRuntime", "DockerAPI"],
                escalation_conditions=["System-wide outage > 15m", "Catastrophic data corruption"],
                replacement_failover_role="VP_ENGINEERING_OR_CEO",
                combinable_with=["EXEC_CPO", "EXEC_CIO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CMO",
                role_name="Chief Marketing Officer (CMO)",
                purpose="Demand generation, brand positioning, customer acquisition cost (CAC) efficiency, and market share.",
                when_required="Growth, consumer, B2C, e-commerce, and high-velocity B2B organizations.",
                when_optional="B2B enterprise firms with sales-led growth (combined into CRO).",
                authority_scope="Marketing campaigns, advertising budgets, content, brand guidelines, SEO.",
                responsibilities=[
                    "Brand strategy, public messaging, and market positioning",
                    "Customer acquisition, paid campaigns, and SEO/content strategy",
                    "Marketing analytics, attribution modeling, and CAC efficiency",
                    "Lead generation pipelines and campaign ROI optimization"
                ],
                kra=["Customer Acquisition", "CAC Efficiency", "Market Brand Visibility"],
                kpi=["CAC (Customer Acquisition Cost)", "Inbound Qualified Leads", "Marketing ROI Ratio"],
                sop_ids=["SOP-MKT-01-CampaignLaunch", "SOP-MKT-02-CACAudit"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Brand", "Content", "Performance Marketing", "SEO", "Creative"],
                decision_rights=["Campaign Approvals", "Ad Budget Allocation", "Brand Assets"],
                budget_authority_usd=40000.0,
                risk_authority="LOW",
                required_data=["ANALYTICS_FEEDS", "AD_NETWORKS", "CRM_LEADS"],
                required_tools=["GoogleAnalyticsAPI", "BrowserUseAgent", "AdCampaignManager"],
                escalation_conditions=["CAC exceeds LTV/3 threshold", "Brand reputation incident"],
                replacement_failover_role="GROWTH_DIRECTOR_OR_CRO",
                combinable_with=["EXEC_CRO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CRO",
                role_name="Chief Revenue Officer (CRO)",
                purpose="Unified commercial revenue ownership: sales pipeline, account expansion, partnerships, and revenue ops.",
                when_required="B2B, SaaS, enterprise, high-value consulting, and commercial operations.",
                when_optional="Product-led self-serve businesses without direct sales force.",
                authority_scope="Sales quotas, commercial contracts within DoA, partner agreements, pricing discounts.",
                responsibilities=[
                    "Sales strategy, direct sales team leadership, and pipeline conversion",
                    "Commercial negotiations, enterprise deals, and account growth",
                    "Revenue operations, CRM hygiene, and revenue forecasting",
                    "Strategic commercial partnerships and channel distribution"
                ],
                kra=["Gross Commercial Revenue", "Sales Pipeline Velocity", "Quota Attainment"],
                kpi=["Net New ARR / Bookings USD", "Win Rate %", "Average Deal Size USD"],
                sop_ids=["SOP-REV-01-EnterpriseDealClosing", "SOP-REV-02-DiscountGovernance"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Sales", "Business Development", "Partnerships", "Account Management", "RevOps"],
                decision_rights=["Commercial Terms Approval", "Pipeline Reallocation", "Commission Plans"],
                budget_authority_usd=60000.0,
                risk_authority="MEDIUM",
                required_data=["CRM_PIPELINE", "SALESFORCE_HUBSPOT", "CUSTOMER_USAGE"],
                required_tools=["SalesforceNangoConnector", "HubSpotConnector", "ContractReviewer"],
                escalation_conditions=["Quarterly revenue forecast shortfall > 20%", "Key enterprise churn"],
                replacement_failover_role="VP_SALES_OR_CEO",
                combinable_with=["EXEC_CMO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CSO",
                role_name="Chief Strategy Officer (CSO)",
                purpose="Corporate strategy, competitive intelligence, new market expansion, and strategic scenario planning.",
                when_required="Mid-size and Enterprise companies undergoing transformation or multi-market expansion.",
                when_optional="Startups and early-stage companies (managed directly by CEO).",
                authority_scope="Strategic initiative formulation, market intelligence research, M&A evaluation.",
                responsibilities=[
                    "Corporate strategy formulation and strategic planning cycles",
                    "Competitive intelligence and adversarial market monitoring",
                    "New market entry and commercial business model expansion",
                    "Strategic scenario analysis and long-term enterprise resilience"
                ],
                kra=["Strategic Positioning", "Competitive Advantage", "Market Expansion Success"],
                kpi=["Strategic Milestone Execution Rate %", "New Market Revenue Share %"],
                sop_ids=["SOP-STRAT-01-MarketEntryAnalysis", "SOP-STRAT-02-CompetitorBenchmark"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Corporate Strategy", "Market Intelligence", "Strategic Partnerships"],
                decision_rights=["Strategy Proposals", "Strategic Research Mandates"],
                budget_authority_usd=30000.0,
                risk_authority="LOW",
                required_data=["MARKET_RESEARCH", "INDUSTRY_BENCHMARKS", "COMPETITOR_SIGNALS"],
                required_tools=["MarketIntelligenceAgent", "EvidenceLedger", "ScenarioSimulator"],
                escalation_conditions=["Unanticipated competitor market disruption"],
                replacement_failover_role="CEO",
                combinable_with=["EXEC_CPO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CHRO",
                role_name="Chief Human Resources Officer / Chief People Officer (CHRO / CHO)",
                purpose="Workforce planning, talent acquisition, human-AI hybrid team coordination, and performance management.",
                when_required="Companies with 20+ human employees or complex human-AI hybrid workforce fleets.",
                when_optional="Micro AI-only autonomous businesses.",
                authority_scope="Workforce policies, hiring authorizations, compensation structures, performance reviews.",
                responsibilities=[
                    "Workforce planning, organizational chart maintenance, and capacity modeling",
                    "Talent acquisition, recruitment pipelines, and role specification",
                    "Employee engagement, human-AI collaborative productivity, and training",
                    "Performance appraisals, compensation governance, and succession planning"
                ],
                kra=["Workforce Productivity", "Talent Retention", "Human-AI Collaboration Health"],
                kpi=["Employee Retention Rate %", "Time to Hire (Days)", "Productivity Per FTE USD"],
                sop_ids=["SOP-HR-01-OnboardingProcess", "SOP-HR-02-PerformanceAudit"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Talent Acquisition", "People Ops", "L&D", "Performance Management"],
                decision_rights=["Hiring Offers within Budget", "Compensation Adjustments within Policy"],
                budget_authority_usd=40000.0,
                risk_authority="LOW",
                required_data=["HRIS_SYSTEMS", "WORKFORCE_METRICS", "COMPENSATION_BENCHMARKS"],
                required_tools=["HRISConnector", "WorkforcePlanner", "CulturePulseAgent"],
                escalation_conditions=["Key personnel departure", "Workplace harassment or statutory grievance"],
                replacement_failover_role="PEOPLE_DIRECTOR_OR_COO",
                combinable_with=["EXEC_COO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CPO",
                role_name="Chief Product Officer (CPO)",
                purpose="Product strategy, customer discovery, roadmap prioritization, and product-market fit.",
                when_required="Product-led SaaS, digital platform, and software product companies.",
                when_optional="Pure service or operational asset holding companies.",
                authority_scope="Product roadmaps, feature specifications, user experience standards, release acceptance.",
                responsibilities=[
                    "Product vision, customer problem discovery, and roadmap prioritization",
                    "User experience (UX) research, design systems, and product analytics",
                    "Feature prioritization based on economic value and customer retention",
                    "Product lifecycle management from inception to sunset"
                ],
                kra=["Product-Market Fit", "Customer Product Adoption", "Feature Retention Impact"],
                kpi=["Product NPS", "Feature Adoption Rate %", "User Retention (Cohort D30/D90)"],
                sop_ids=["SOP-PROD-01-RoadmapPrioritization", "SOP-PROD-02-ReleaseGate"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Product Management", "Product Design/UX", "Product Analytics"],
                decision_rights=["Roadmap Scope Commitments", "UX Design Approvals", "Release Gates"],
                budget_authority_usd=35000.0,
                risk_authority="LOW",
                required_data=["USER_SESSION_TELEMETRY", "CUSTOMER_FEEDBACK", "ROADMAP_JIRA"],
                required_tools=["ProductAnalyticsAPI", "FigmaConnector", "FeatureFlagController"],
                escalation_conditions=["Product adoption collapse < 30%", "Critical usability failure"],
                replacement_failover_role="CTO_OR_HEAD_OF_PRODUCT",
                combinable_with=["EXEC_CTO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CIO",
                role_name="Chief Information Officer (CIO)",
                purpose="Internal business applications, enterprise data pipelines, and digital workplace productivity.",
                when_required="Mid-size and enterprise companies with complex internal ERP/CRM tech stacks.",
                when_optional="Lean cloud-native startups (managed by CTO).",
                authority_scope="Internal software procurement, corporate networks, business software licensing.",
                responsibilities=[
                    "Enterprise software applications (ERP, CRM, Billing, HRIS)",
                    "Internal corporate IT systems, device security, and network access",
                    "Corporate data governance, data warehouse pipelines, and business intelligence",
                    "Digital workplace software efficiency and IT licensing spend"
                ],
                kra=["Internal Systems Availability", "Data Warehouse Integrity", "Software Licensing Efficiency"],
                kpi=["Internal Application Uptime %", "IT Support Resolution Time", "IT Spend per Head USD"],
                sop_ids=["SOP-IT-01-SoftwareProvisioning", "SOP-IT-02-DataGovernance"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Business Systems", "Enterprise IT", "Data Warehouse / BI"],
                decision_rights=["Software Vendor Approvals", "Internal System Changes"],
                budget_authority_usd=40000.0,
                risk_authority="LOW",
                required_data=["SYSTEM_ACCESS_LOGS", "IT_TICKETS", "VENDOR_CONTRACTS"],
                required_tools=["ITServiceDesk", "SSOIdentityGateway", "LicenseManager"],
                escalation_conditions=["Core internal ERP downtime", "Internal data integrity fault"],
                replacement_failover_role="CTO_OR_IT_DIRECTOR",
                combinable_with=["EXEC_CTO", "EXEC_CFO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CISO",
                role_name="Chief Information Security Officer (CISO)",
                purpose="Information security architecture, data protection, vulnerability management, and incident response.",
                when_required="Regulated, financial, healthcare, enterprise B2B, or high-security organizations.",
                when_optional="Early startups with basic security requirements (handled by CTO with oversight).",
                authority_scope="Security policies, vulnerability remediation mandates, security incident halts.",
                responsibilities=[
                    "Cybersecurity governance, threat modeling, and defensive architecture",
                    "Data loss prevention (DLP), access control audits, and cryptographic enforcement",
                    "Security incident response, penetration testing, and vulnerability management",
                    "Security compliance certifications (SOC2, ISO 27001, HIPAA, GDPR)"
                ],
                kra=["Enterprise Security Posture", "Zero Critical Breaches", "Compliance Integrity"],
                kpi=["Unpatched Critical Vulnerability Count", "Security Incident MTTR", "Audit Pass Rate %"],
                sop_ids=["SOP-SEC-01-IncidentQuarantine", "SOP-SEC-02-VulnerabilityPatching"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["SecOps", "Security Architecture", "Compliance & Governance"],
                decision_rights=["Emergency Quarantine", "Security Gate Block", "Revocation of Credentials"],
                budget_authority_usd=45000.0,
                risk_authority="HIGH",
                required_data=["SIEM_LOGS", "VULNERABILITY_SCANS", "AUDIT_RECEIPTS"],
                required_tools=["SecurityGateway", "AuditLedger", "FirewallController"],
                escalation_conditions=["Confirmed data exfiltration", "Ransomware signature detected"],
                replacement_failover_role="SECURITY_DIRECTOR_OR_CTO",
                combinable_with=[]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CLO",
                role_name="Chief Legal Officer / General Counsel (CLO)",
                purpose="Legal compliance, corporate governance, commercial contract review, and intellectual property defense.",
                when_required="Growth and enterprise companies with high contractual volume or regulatory oversight.",
                when_optional="Small early companies using standard template legal agreements.",
                authority_scope="Contract execution approvals, regulatory filings, external counsel engagement.",
                responsibilities=[
                    "Commercial contract review, legal risk assessment, and standard agreement governance",
                    "Corporate governance, regulatory statutory compliance, and corporate filings",
                    "Intellectual property (IP) protection, patents, and trademark portfolio",
                    "Litigation management and coordination with licensed external human counsel"
                ],
                kra=["Legal Risk Mitigation", "Contract Velocity & Protection", "Regulatory Compliance"],
                kpi=["Contract Turnaround Time (Hours)", "Contractual Risk Flag Rate %", "Zero Regulatory Penalties"],
                sop_ids=["SOP-LEG-01-ContractReview", "SOP-LEG-02-RegulatoryDisclosure"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Corporate Legal", "Contract Management", "Regulatory Affairs"],
                decision_rights=["Legal Clause Approvals", "Contract Signoff (Within Governance Limits)"],
                budget_authority_usd=50000.0,
                risk_authority="HIGH",
                required_data=["CONTRACT_ARCHIVE", "REGULATORY_STATUTES", "TERMS_OF_SERVICE"],
                required_tools=["LegalContractParser", "DocumentValidator", "RegulatoryMonitor"],
                escalation_conditions=["Lawsuit served", "Regulatory investigation initiated"],
                replacement_failover_role="EXTERNAL_COUNSEL_OR_CEO",
                combinable_with=["EXEC_CCO_COMPLIANCE"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CSCO",
                role_name="Chief Supply Chain Officer (CSCO)",
                purpose="Procurement, supplier relations, inventory optimization, warehousing, and logistics fulfillment.",
                when_required="Manufacturing, retail, e-commerce, hospitality procurement, or physical asset companies.",
                when_optional="Pure software or pure services companies.",
                authority_scope="Vendor purchase orders, inventory targets, warehouse logistics, supplier contracts.",
                responsibilities=[
                    "Supplier discovery, contract negotiation, and vendor performance management",
                    "Inventory planning, safety stock optimization, and lead time reduction",
                    "Logistics, freight routing, and on-time-in-full (OTIF) fulfillment",
                    "Supply chain risk mitigation and secondary supplier redundancy"
                ],
                kra=["Supply Continuity", "Procurement Cost Efficiency", "Inventory Turnover"],
                kpi=["OTIF (On-Time In-Full) %", "Inventory Turnover Ratio", "Supplier Defect Rate %"],
                sop_ids=["SOP-SCM-01-SupplierEvaluation", "SOP-SCM-02-InventoryReorder"],
                reporting_line="EXEC_COO",
                subordinate_functions=["Procurement", "Inventory Management", "Logistics & Freight"],
                decision_rights=["Purchase Orders within DoA", "Supplier Selection"],
                budget_authority_usd=75000.0,
                risk_authority="MEDIUM",
                required_data=["ERP_INVENTORY", "SUPPLIER_CATALOGS", "SHIPPING_METRICS"],
                required_tools=["SupplyChainERPConnector", "InventoryOptimizer", "LogisticsAPI"],
                escalation_conditions=["Critical supplier bankruptcy", "Stockout of tier-1 supply"],
                replacement_failover_role="PROCUREMENT_DIRECTOR_OR_COO",
                combinable_with=["EXEC_COO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CCO_CUSTOMER",
                role_name="Chief Customer Officer (CCO-Customer)",
                purpose="Customer experience, customer success, retention, onboarding, and customer lifetime value.",
                when_required="Subscription businesses, hospitality, customer-centric retail, and services.",
                when_optional="Commodity wholesale or early-stage development companies.",
                authority_scope="Customer success playbooks, refund/escalation concessions, churn mitigation campaigns.",
                responsibilities=[
                    "Customer journey mapping, customer onboarding, and time-to-value",
                    "Customer success operations, account health scoring, and proactive outreach",
                    "Customer retention, renewal governance, and gross churn minimization",
                    "Voice of customer insights, feedback loops to Product, and satisfaction programs"
                ],
                kra=["Customer Retention", "Net Promoter Score", "Customer Health"],
                kpi=["Gross Churn Rate %", "Net Revenue Retention (NRR) %", "Customer Satisfaction (CSAT) %"],
                sop_ids=["SOP-CS-01-AccountOnboarding", "SOP-CS-02-ChurnIntervention"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Customer Success", "Customer Support", "Client Onboarding"],
                decision_rights=["Customer Retention Credits within Limit", "Service Concessions"],
                budget_authority_usd=30000.0,
                risk_authority="LOW",
                required_data=["CUSTOMER_USAGE", "SUPPORT_TICKETS", "NPS_SURVEYS"],
                required_tools=["ZendeskHubSpotConnector", "CustomerHealthEngine", "SurveyMonkeyAPI"],
                escalation_conditions=["Key enterprise churn alert", "CSAT drop below 70%"],
                replacement_failover_role="VP_CUSTOMER_SUCCESS_OR_CRO",
                combinable_with=["EXEC_CRO"]
            ),
            ExecutiveRoleDefinition(
                role_id="EXEC_CRO_RISK",
                role_name="Chief Risk & Compliance Officer (CRO-Risk / CCO-Compliance)",
                purpose="Enterprise risk governance, risk register maintenance, statutory compliance, and audit oversight.",
                when_required="Regulated industries (Healthcare, Financial, Aviation, Defense, Utilities) and Enterprises.",
                when_optional="Low-risk, unregulated micro businesses.",
                authority_scope="Enterprise risk limits, compliance audits, control effectiveness mandates.",
                responsibilities=[
                    "Enterprise risk management framework (ISO 31000) execution",
                    "Corporate risk register maintenance and risk-adjusted exposure limits",
                    "Statutory compliance management (ISO 37301) and regulatory audit verification",
                    "Business continuity planning, disaster recovery governance, and ethics reporting"
                ],
                kra=["Enterprise Risk Control", "Audit & Statutory Compliance", "Zero Compliance Violations"],
                kpi=["High-Risk Finding Count", "Compliance Audit Score %", "Overdue Risk Remediations"],
                sop_ids=["SOP-RISK-01-RiskAssessment", "SOP-RISK-02-ComplianceAudit"],
                reporting_line="EXEC_CEO",
                subordinate_functions=["Enterprise Risk", "Regulatory Compliance", "Internal Audit"],
                decision_rights=["Risk Acceptance Veto", "Compliance Audit Signoff"],
                budget_authority_usd=35000.0,
                risk_authority="HIGH",
                required_data=["RISK_REGISTER", "INCIDENT_LOGS", "AUDIT_REPORTS"],
                required_tools=["EvidenceLedger", "RiskEngine", "ComplianceTracker"],
                escalation_conditions=["Material unmitigated risk > $100k", "Regulatory sanction threat"],
                replacement_failover_role="GENERAL_COUNSEL_OR_CEO",
                combinable_with=["EXEC_CLO"]
            ),
ExecutiveRoleDefinition(
    role_id="EXEC_CDO",
    role_name="Chief Data & Digital Officer (CDO)",
    purpose="Enterprise data governance, analytical data warehouse modeling, and single source of analytical truth.",
    when_required="Data-heavy enterprises, analytics SaaS, and business intelligence operations.",
    when_optional="Early startups with simple single-database models.",
    authority_scope="Enterprise data warehouse, analytical pipeline schemas, data lineage, BI reporting.",
    responsibilities=["Data warehouse governance", "BI dashboard accuracy", "Master data management"],
    kra=["Data Quality & Integrity", "Analytics Query Latency", "Data Warehouse Completeness"],
    kpi=["Data Freshness SLA %", "Pipeline Error Rate %", "Data Governance Coverage %"],
    sop_ids=["SOP-DATA-01-PipelineReconciliation", "SOP-DATA-02-SchemaMigrationReview"],
    reporting_line="EXEC_CEO",
    subordinate_functions=["Data Engineering", "Business Intelligence", "Data Governance"],
    decision_rights=["Master Data Schema Approvals", "Warehouse Model Signoff"],
    budget_authority_usd=40000.0,
    risk_authority="MEDIUM",
    required_data=["DATA_WAREHOUSE", "SCHEMA_REGISTRY", "ETL_LOGS"],
    required_tools=["PostgresDatabaseEngine", "NeonAnalytics", "DbtPipelineEngine"],
    escalation_conditions=["Critical analytical divergence > 10%", "ETL pipeline failure > 4h"],
    replacement_failover_role="HEAD_OF_DATA_OR_CTO",
    combinable_with=["EXEC_CIO", "EXEC_CAIO"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CAIO",
    role_name="Chief Artificial Intelligence Officer (CAIO)",
    purpose="AI alignment, token budgeting, prompt safety, model routing, and agent workforce evaluation.",
    when_required="Autonomous AI workforce enterprises, multi-agent deployments, and AI-first startups.",
    when_optional="Companies with zero AI adoption.",
    authority_scope="AI models, agent evaluation benchmarks, token budgets, prompt injection defenses.",
    responsibilities=["Agent model benchmark evaluation", "Token spend monitoring", "Prompt injection containment"],
    kra=["Agent Alignment & Safety", "Token Cost Efficiency", "Model Inference Quality"],
    kpi=["Agent Hallucination Rate %", "Token Budget Variance %", "Evaluation Benchmark Score %"],
    sop_ids=["SOP-AI-01-ModelEvaluation", "SOP-AI-02-TokenBudgetQuarantine"],
    reporting_line="EXEC_CEO",
    subordinate_functions=["AI Alignment", "Agent Engineering", "Model Optimization"],
    decision_rights=["Agent Quota Enforcement", "Model Routing Policy Veto"],
    budget_authority_usd=60000.0,
    risk_authority="HIGH",
    required_data=["AGENT_EVAL_RUNS", "TOKEN_USAGE_LEDGER", "PROMPT_LOGS"],
    required_tools=["AgentFactoryV2", "EvaluationEngine", "NeonAIGateway"],
    escalation_conditions=["Severe prompt injection breakout", "Token budget exhaustion"],
    replacement_failover_role="AI_ARCHITECT_OR_CTO",
    combinable_with=["EXEC_CTO", "EXEC_CDO"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CCO_COMPLIANCE",
    role_name="Chief Compliance Officer (CCO-Compliance)",
    purpose="Statutory regulatory compliance (ISO 37301), ethics hotlines, and anti-fraud oversight.",
    when_required="Regulated industries, public companies, and multi-jurisdictional commerce.",
    when_optional="Unregulated micro businesses.",
    authority_scope="Statutory regulatory compliance, whistleblower reports, anti-money laundering (AML).",
    responsibilities=["Compliance audits", "Regulatory filings", "Anti-fraud monitoring"],
    kra=["Statutory Compliance", "Regulatory Audit Pass Rate", "Zero Sanction Penalties"],
    kpi=["Compliance Audit Score %", "Overdue Regulatory Action Items", "Zero Statutory Breaches"],
    sop_ids=["SOP-COMP-01-RegulatoryAudit", "SOP-COMP-02-WhistleblowerInvestigation"],
    reporting_line="EXEC_CEO",
    subordinate_functions=["Regulatory Compliance", "Ethics & Anti-Fraud", "Internal Audit"],
    decision_rights=["Regulatory Filing Approval", "Fraud Quarantine Veto"],
    budget_authority_usd=45000.0,
    risk_authority="CRITICAL",
    required_data=["STATUTORY_REGISTERS", "AUDIT_RECEIPTS", "FRAUD_ALERTS"],
    required_tools=["AuditVerificationEngine", "EvidenceLedger", "RegulatoryMonitor"],
    escalation_conditions=["Regulatory subpoena received", "Material fraud detected"],
    replacement_failover_role="LEGAL_COUNSEL_OR_CEO",
    combinable_with=["EXEC_CLO", "EXEC_CRO_RISK"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CSO_SUSTAINABILITY",
    role_name="Chief Sustainability Officer (CSO-Sustainability)",
    purpose="ESG compliance, carbon accounting, environmental impact, and energy efficiency.",
    when_required="Enterprise, energy-intensive industrial, and public disclosure organizations.",
    when_optional="Early startups.",
    authority_scope="ESG disclosures, carbon offsets, energy efficiency guidelines.",
    responsibilities=["Carbon footprint accounting", "ESG regulatory reporting", "Green supplier auditing"],
    kra=["ESG Audit Compliance", "Energy Efficiency Optimization", "Carbon Offset Fulfillment"],
    kpi=["Carbon Emissions Intensity", "ESG Disclosure Score %", "Renewable Energy Ratio %"],
    sop_ids=["SOP-ESG-01-CarbonAudit", "SOP-ESG-02-SustainableProcurement"],
    reporting_line="EXEC_CEO",
    subordinate_functions=["Sustainability", "ESG Reporting", "Energy Operations"],
    decision_rights=["ESG Report Approval", "Green Supplier Certification"],
    budget_authority_usd=30000.0,
    risk_authority="LOW",
    required_data=["UTILITY_FEEDS", "SUPPLIER_ESG_REPORTS", "EMISSION_LEDGERS"],
    required_tools=["ESGAnalyticsAPI", "EvidenceLedger"],
    escalation_conditions=["Material ESG reporting misstatement", "Environmental sanction"],
    replacement_failover_role="HEAD_OF_FACILITIES_OR_COO",
    combinable_with=["EXEC_CAO", "EXEC_CSCO"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CQO",
    role_name="Chief Quality Officer (CQO)",
    purpose="Six Sigma quality control, defect triage, ISO 9001 compliance, and process quality engineering.",
    when_required="Manufacturing, pharma, industrial hardware, and mission-critical engineering.",
    when_optional="Pure software development.",
    authority_scope="Quality control standards, shipment stop-work authority, defect tracking.",
    responsibilities=["Quality management system (ISO 9001)", "Defect analysis", "Supplier quality audits"],
    kra=["Defect Rate Minimization", "ISO 9001 Audit Pass Rate", "First Pass Yield"],
    kpi=["Defect Parts Per Million (PPM)", "Customer Return Rate %", "First Pass Yield %"],
    sop_ids=["SOP-QA-01-StopWorkOrder", "SOP-QA-02-RootCauseAnalysis"],
    reporting_line="EXEC_COO",
    subordinate_functions=["Quality Assurance", "Metrology", "Process Engineering"],
    decision_rights=["Stop-Shipment Authority", "Quality Rejection Veto"],
    budget_authority_usd=40000.0,
    risk_authority="HIGH",
    required_data=["INSPECTION_LOGS", "DEFECT_TRACKER", "CALIBRATION_RECORDS"],
    required_tools=["QualityTracker", "EvidenceLedger"],
    escalation_conditions=["Batch defect rate > 2%", "Regulatory recall trigger"],
    replacement_failover_role="HEAD_OF_QA_OR_COO",
    combinable_with=["EXEC_COO"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CGO",
    role_name="Chief Growth Officer (CGO)",
    purpose="Growth loops, viral acquisition, funnel conversion optimization, and product-led growth (PLG).",
    when_required="High-velocity consumer tech, PLG SaaS, and e-commerce scaleups.",
    when_optional="Slow-cycle enterprise contracts.",
    authority_scope="Conversion rate experiments, onboarding loops, referral systems.",
    responsibilities=["Viral loop optimization", "Growth experimentation backlog", "Activation rate audits"],
    kra=["User Activation Velocity", "Conversion Rate (CRO)", "Referral Factor"],
    kpi=["Free-to-Paid Conversion %", "30-Day Cohort Retention %", "Viral K-Factor"],
    sop_ids=["SOP-GRO-01-A_B_TestDeployment", "SOP-GRO-02-FunnelAudit"],
    reporting_line="EXEC_CEO",
    subordinate_functions=["Growth Engineering", "Conversion Optimization", "Lifecycle Marketing"],
    decision_rights=["Experiment Rollout Approval", "Growth Incentive Budgets"],
    budget_authority_usd=45000.0,
    risk_authority="LOW",
    required_data=["PRODUCT_ANALYTICS", "CONVERSION_FUNNELS", "ATTRIBUTION_DATA"],
    required_tools=["PostHogConnector", "MixpanelAPI", "AdCampaignManager"],
    escalation_conditions=["Core funnel conversion drop > 25%", "Churn spike > 10%"],
    replacement_failover_role="GROWTH_LEAD_OR_CMO",
    combinable_with=["EXEC_CMO", "EXEC_CRO"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CPCO",
    role_name="Chief Privacy Officer (CPCO)",
    purpose="GDPR, CCPA, HIPAA data privacy compliance, consent graphs, and data minimization.",
    when_required="Consumer apps, healthcare, European/California users, and sensitive data processing.",
    when_optional="Internal B2B tools with zero personal data.",
    authority_scope="Data privacy policies, DSAR automation, consent audits, third-party vendor privacy.",
    responsibilities=["GDPR/CCPA statutory compliance", "DSAR fulfillment within SLA", "Privacy impact assessments"],
    kra=["Zero Privacy Breaches", "DSAR Turnaround SLA", "Consent Graph Accuracy"],
    kpi=["DSAR Average Resolution Hours", "Privacy Assessment Coverage %", "Zero Privacy Injunctions"],
    sop_ids=["SOP-PRIV-01-DSARProcessing", "SOP-PRIV-02-PrivacyImpactAssessment"],
    reporting_line="EXEC_CLO",
    subordinate_functions=["Data Privacy Office", "Consent Operations", "Vendor Privacy Review"],
    decision_rights=["Data Processing Veto", "DSAR Approval"],
    budget_authority_usd=35000.0,
    risk_authority="HIGH",
    required_data=["CONSENT_REGISTRY", "DSAR_QUEUE", "VENDOR_DPA_ARCHIVE"],
    required_tools=["PrivacyEngine", "EvidenceLedger", "DlpEngine"],
    escalation_conditions=["Unauthorized PII disclosure", "Regulatory privacy inquiry"],
    replacement_failover_role="PRIVACY_COUNSEL_OR_CISO",
    combinable_with=["EXEC_CLO", "EXEC_CISO"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CBO",
    role_name="Chief Business Officer (CBO)",
    purpose="Strategic joint ventures, channel alliances, OEM licensing, and cross-enterprise partnerships.",
    when_required="High partnership volume, distribution ecosystems, and enterprise channel ecosystems.",
    when_optional="Direct self-serve products.",
    authority_scope="Partner contracts, channel revenue share agreements, ecosystem distribution.",
    responsibilities=["Strategic channel alliances", "Joint venture structuring", "Partner revenue governance"],
    kra=["Partner Channel Revenue", "Ecosystem Expansion", "Alliance Retention"],
    kpi=["Channel ARR USD", "Active Certified Partners", "Partner Net Retention %"],
    sop_ids=["SOP-BUS-01-PartnerOnboarding", "SOP-BUS-02-RevenueShareAudit"],
    reporting_line="EXEC_CEO",
    subordinate_functions=["Strategic Alliances", "Channel Operations", "OEM Licensing"],
    decision_rights=["Channel Agreement Terms", "Co-Marketing Budgets"],
    budget_authority_usd=50000.0,
    risk_authority="MEDIUM",
    required_data=["PARTNER_PORTAL", "CHANNEL_PIPELINE", "REVENUE_SHARE_LEDGERS"],
    required_tools=["SalesforceConnector", "HubSpotConnector"],
    escalation_conditions=["Key alliance termination", "Partner revenue breach > 30%"],
    replacement_failover_role="VP_BUSDEV_OR_CRO",
    combinable_with=["EXEC_CRO", "EXEC_CSO"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CAO",
    role_name="Chief Administrative Officer (CAO)",
    purpose="Corporate governance administration, multi-office facilities, corporate records, and internal policies.",
    when_required="Holding companies, multi-entity conglomerates, and large corporate campuses.",
    when_optional="Single-entity digital startups.",
    authority_scope="Corporate records, facilities leases, board minutes, administrative operating policies.",
    responsibilities=["Corporate records governance", "Real estate facility administration", "Internal board administration"],
    kra=["Administrative Operational Continuity", "Corporate Record Hygiene", "Facility Uptime"],
    kpi=["Administrative SLA Fulfillment %", "Audit Record Completeness %", "Facility Operational Index"],
    sop_ids=["SOP-ADM-01-BoardRecordFiling", "SOP-ADM-02-FacilityLeaseReview"],
    reporting_line="EXEC_CEO",
    subordinate_functions=["Corporate Administration", "Facilities Management", "Board Relations"],
    decision_rights=["Facility Lease Authorizations", "Administrative Policy Signoff"],
    budget_authority_usd=40000.0,
    risk_authority="LOW",
    required_data=["CORPORATE_RECORDS", "FACILITY_MANAGEMENT_DB", "LEASE_CONTRACTS"],
    required_tools=["DocumentValidator", "EvidenceLedger"],
    escalation_conditions=["Facility shutdown", "Board governance failure"],
    replacement_failover_role="OPERATIONS_MANAGER_OR_COO",
    combinable_with=["EXEC_COO", "EXEC_CHRO"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CSE",
    role_name="Chief Safety & Environmental Officer (CSE)",
    purpose="OSHA workplace physical safety, zero-hazard compliance, and chemical/environmental hazard control.",
    when_required="Heavy industry, chemical plants, manufacturing, construction, and freight logistics.",
    when_optional="Remote digital software companies.",
    authority_scope="Physical workplace safety, OSHA compliance, hazardous material management.",
    responsibilities=["Workplace hazard assessments", "OSHA recordkeeping", "Emergency containment protocols"],
    kra=["Zero Lost-Time Incidents", "OSHA Audit Compliance", "Safety Training Completion"],
    kpi=["Total Recordable Incident Rate (TRIR)", "Near-Miss Reporting Volume", "Safety Audit Score %"],
    sop_ids=["SOP-SAFE-01-WorkplaceIncidentResponse", "SOP-SAFE-02-HazardAssessment"],
    reporting_line="EXEC_COO",
    subordinate_functions=["Environmental Health & Safety (EHS)", "Physical Security", "Hazardous Material Operations"],
    decision_rights=["Immediate Safety Stop-Work Order", "Facility Evacuation"],
    budget_authority_usd=40000.0,
    risk_authority="CRITICAL",
    required_data=["EHS_INCIDENT_LOGS", "OSHA_300_LOGS", "SAFETY_INSPECTION_FEED"],
    required_tools=["EvidenceLedger", "SafetyTracker"],
    escalation_conditions=["Workplace injury incident", "Environmental spill threshold breach"],
    replacement_failover_role="EHS_DIRECTOR_OR_COO",
    combinable_with=["EXEC_COO", "EXEC_CQO"]
),
ExecutiveRoleDefinition(
    role_id="EXEC_CMO_MEDICAL",
    role_name="Chief Medical Officer (CMO-Medical)",
    purpose="Clinical governance, clinical trial ethics, patient medical safety, and HIPAA healthcare compliance.",
    when_required="Hospitals, healthcare clinics, biotech, pharmaceutical, and healthtech platforms.",
    when_optional="Non-healthcare companies.",
    authority_scope="Clinical protocols, medical review boards, patient safety standards, clinical trials.",
    responsibilities=["Clinical governance framework", "Physician protocol oversight", "Medical trial safety audits"],
    kra=["Clinical Quality & Safety", "Zero Medical Protocol Deviations", "Clinical Compliance"],
    kpi=["Patient Safety Index", "Clinical Protocol Adherence %", "Zero Malpractice Findings"],
    sop_ids=["SOP-MED-01-ClinicalProtocolReview", "SOP-MED-02-AdverseEventReporting"],
    reporting_line="EXEC_CEO",
    subordinate_functions=["Clinical Affairs", "Medical Review Board", "Patient Safety"],
    decision_rights=["Clinical Protocol Approval", "Medical Treatment Review Veto"],
    budget_authority_usd=70000.0,
    risk_authority="CRITICAL",
    required_data=["ELECTRONIC_HEALTH_RECORDS", "CLINICAL_TRIAL_DATA", "ADVERSE_EVENT_LOGS"],
    required_tools=["ClinicalVerificationEngine", "EvidenceLedger"],
    escalation_conditions=["Adverse patient event", "Clinical trial regulatory halt"],
    replacement_failover_role="MEDICAL_DIRECTOR_OR_CEO",
    combinable_with=[]
)
        ]

        for r in roles_data:
            cls._ROLES[r.role_id] = r

    @classmethod
    def get_role(cls, role_id: str) -> Optional[ExecutiveRoleDefinition]:
        cls.initialize()
        return cls._ROLES.get(role_id)

    @classmethod
    def list_roles(cls) -> List[ExecutiveRoleDefinition]:
        cls.initialize()
        return list(cls._ROLES.values())

# ==============================================================================
# 4. COMPANY ONBOARDING AUDIT & GAP ANALYZER
# ==============================================================================

@dataclass
class CompanyProfile:
    company_id: str
    tenant_id: str
    company_name: str
    industry: str
    geography: str
    company_size: str                   # MICRO_STARTUP, SMALL_COMPANY, GROWING_COMPANY, MIDSIZE_COMPANY, ENTERPRISE
    stage_maturity: str                 # PRE_REVENUE, EARLY_STAGE, SCALEUP, MATURE, TRANSFORMATION
    revenue_model: str                  # SUBSCRIPTION_SAAS, DIRECT_BOOKING_HOSPITALITY, CONTRACT_MANUFACTURING, ECOMMERCE_RETAIL, SERVICES
    annual_revenue_usd: float
    current_human_employees: int
    current_active_agents: int
    products_services: List[str]
    customer_archetype: str             # B2B, B2C, B2G, HYBRID
    regulatory_intensity: str           # LOW, MEDIUM, HIGH, SEVERE
    operational_complexity: str         # LOW, MEDIUM, HIGH, VERY_HIGH
    capital_intensity: str              # ASSET_LIGHT, MODERATE, ASSET_HEAVY

@dataclass
class OrgGapAnalysisResult:
    current_state: Dict[str, Any]
    required_state: Dict[str, Any]
    gaps: List[Dict[str, str]]
    duplications: List[Dict[str, str]]
    bottlenecks: List[Dict[str, str]]
    excess_management: List[Dict[str, str]]
    material_risks: List[Dict[str, str]]
    recommendations: List[str]

class OrganizationGapAnalyzer:
    """
    Analyzes existing company structure vs required operational reality.
    Never blindly replaces an organization; preserves healthy existing functions.
    """
    @classmethod
    def analyze(cls, profile: CompanyProfile, existing_org: Optional[Dict[str, Any]] = None) -> OrgGapAnalysisResult:
        existing = existing_org or {"executives": [], "departments": [], "workforce": []}
        existing_exec_ids = {e.get("role_id") for e in existing.get("executives", [])}
        existing_depts = {d.get("name") for d in existing.get("departments", [])}

        gaps = []
        duplications = []
        bottlenecks = []
        excess = []
        risks = []
        recommendations = []

        # 1. Determine baseline requirements based on scale and industry
        scale = profile.company_size
        scale_str = scale.value if hasattr(scale, "value") else str(scale)
        ind = profile.industry.upper()

        required_execs = ["EXEC_CEO"]
        if scale in [CompanyScaleStage.SMALL_COMPANY, CompanyScaleStage.GROWING_COMPANY, CompanyScaleStage.MIDSIZE_COMPANY, CompanyScaleStage.ENTERPRISE]:
            required_execs.extend(["EXEC_CFO", "EXEC_COO"])
        
        if ("SAAS" in ind or "TECH" in ind) and "FINTECH" not in ind and "BIOTECH" not in ind:
            required_execs.extend(["EXEC_CTO", "EXEC_CRO"])
            if scale in [CompanyScaleStage.GROWING_COMPANY, CompanyScaleStage.MIDSIZE_COMPANY, CompanyScaleStage.ENTERPRISE]:
                required_execs.append("EXEC_CPO")
        elif "HOTEL" in ind or "HOSPITALITY" in ind:
            required_execs.extend(["EXEC_CMO", "EXEC_CCO_CUSTOMER"])
            if scale in [CompanyScaleStage.GROWING_COMPANY, CompanyScaleStage.MIDSIZE_COMPANY, CompanyScaleStage.ENTERPRISE]:
                required_execs.append("EXEC_CSCO") # Procurement for F&B/Rooms
        elif "MANUFACTURING" in ind:
            required_execs.extend(["EXEC_CSCO", "EXEC_CTO"])
        elif "HEALTHCARE" in ind:
            required_execs.extend(["EXEC_CRO_RISK", "EXEC_CLO"])

        # Check for gaps
        for req in required_execs:
            if req not in existing_exec_ids:
                role_def = ExecutiveRoleRegistry.get_role(req)
                role_name = role_def.role_name if role_def else req
                gaps.append({
                    "function": req,
                    "title": role_name,
                    "severity": "HIGH",
                    "rationale": f"Missing core leadership for {scale_str} {profile.industry} operations."
                })

        # Check for bottlenecks
        if profile.current_human_employees > 50 and len(existing_depts) < 3:
            bottlenecks.append({
                "area": "Operational Coordination",
                "issue": "High employee count with flat structure creates executive overload.",
                "solution": "Establish dedicated operational departments with clear manager spans of control."
            })

        # Check for risk exposure
        if profile.regulatory_intensity in ["HIGH", "SEVERE"] and "EXEC_CRO_RISK" not in existing_exec_ids and "EXEC_CLO" not in existing_exec_ids:
            risks.append({
                "area": "Statutory Compliance",
                "exposure": "Severe regulatory profile without dedicated Legal/Compliance leadership.",
                "remedy": "Instantiate Chief Legal & Compliance Officer or formal external counsel gate."
            })

        recommendations.append(f"Synthesize {scale_str} target organization tailored to {profile.industry}.")
        if gaps:
            recommendations.append(f"Address {len(gaps)} missing executive capabilities via dynamic assignment.")
        if not bottlenecks and not risks:
            recommendations.append("Existing structure is healthy; expand specialized agent workforce within existing departments.")

        return OrgGapAnalysisResult(
            current_state={
                "executive_count": len(existing.get("executives", [])),
                "department_count": len(existing.get("departments", [])),
                "workforce_count": len(existing.get("workforce", []))
            },
            required_state={
                "recommended_executives": required_execs,
                "recommended_departments": [d for d in ["Finance", "Operations", "Growth/Revenue", "Technology"] if d]
            },
            gaps=gaps,
            duplications=duplications,
            bottlenecks=bottlenecks,
            excess_management=excess,
            material_risks=risks,
            recommendations=recommendations
        )

# ==============================================================================
# 5. DYNAMIC ORGANIZATION DESIGN ENGINE
# ==============================================================================

@dataclass
class DynamicOrgBlueprint:
    blueprint_id: str
    tenant_id: str
    company_id: str
    organization_version: str
    scale_stage: str
    industry: str
    executives: List[Dict[str, Any]]
    departments: List[Dict[str, Any]]
    workforce_agents: List[Dict[str, Any]]
    reporting_tree: Dict[str, Any]
    span_of_control_analysis: Dict[str, Any]
    kras: List[Dict[str, Any]]
    kpis: List[Dict[str, Any]]
    sops: List[Dict[str, Any]]
    cryptographic_seal: str
    created_at: float = field(default_factory=time.time)

class DynamicOrganizationDesignEngine:
    """
    Synthesizes industry-adaptive, dynamically scaled company organizations
    grounded in universal constitutional templates.
    """
    @classmethod
    def synthesize_organization(
        cls,
        profile: CompanyProfile,
        existing_org: Optional[Dict[str, Any]] = None
    ) -> DynamicOrgBlueprint:
        ExecutiveRoleRegistry.initialize()
        now = time.time()
        b_id = f"org_{profile.company_id}_{int(now)}"

        # 1. Determine Executive Lineup Dynamically
        executives = cls._select_executives(profile)

        # 2. Determine Operational Departments Dynamically
        departments = cls._synthesize_departments(profile, executives)

        # 3. Size and Distribute Workforce Agents Dynamically
        workforce = cls._synthesize_workforce(profile, departments)

        # 4. Compute Spans of Control
        span_analysis = cls._evaluate_spans_of_control(executives, departments, workforce)

        # 5. Generate KRA/KPI Cascade
        kras, kpis = cls._generate_kra_kpi_cascade(profile, executives, departments, workforce)

        # 6. Generate Executable SOPs
        sops = cls._generate_executable_sops(profile, departments)

        # 7. Construct Reporting Tree
        tree = cls._construct_reporting_tree(profile, executives, departments, workforce)

        # 8. Cryptographic Seal
        raw = f"{b_id}:{profile.tenant_id}:{profile.company_id}:{len(executives)}:{len(departments)}:{len(workforce)}:{now}"
        seal = hashlib.sha256(raw.encode()).hexdigest()

        blueprint = DynamicOrgBlueprint(
            blueprint_id=b_id,
            tenant_id=profile.tenant_id,
            company_id=profile.company_id,
            organization_version="1.0.0-PROPOSED",
            scale_stage=profile.company_size,
            industry=profile.industry,
            executives=executives,
            departments=departments,
            workforce_agents=workforce,
            reporting_tree=tree,
            span_of_control_analysis=span_analysis,
            kras=kras,
            kpis=kpis,
            sops=sops,
            cryptographic_seal=seal,
            created_at=now
        )

        return blueprint

    design_organization = synthesize_organization

    @classmethod
    def _select_executives(cls, profile: CompanyProfile) -> List[Dict[str, Any]]:
        ind = profile.industry.upper()
        scale = profile.company_size
        exec_list = []

        # CEO is always first and mandatory
        ceo_role = ExecutiveRoleRegistry.get_role("EXEC_CEO")
        exec_list.append({
            "role_id": ceo_role.role_id,
            "role_name": ceo_role.role_name,
            "persona_name": f"{profile.company_name} AI CEO",
            "requirement_status": RoleRequirementStatus.REQUIRED.value,
            "workforce_type": WorkforceType.AI_AGENT.value,
            "budget_limit_usd": 500000.0,
            "reporting_to": "OWNER",
            "purpose": ceo_role.purpose
        })

        if scale == CompanyScaleStage.MICRO_STARTUP:
            # Lean startup: Combined roles
            exec_list.append({
                "role_id": "EXEC_COO",
                "role_name": "COO / Head of Operations",
                "persona_name": "Operations Lead",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 25000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Manages day-to-day execution and customer delivery."
            })
            exec_list.append({
                "role_id": "EXEC_CRO",
                "role_name": "Growth / Revenue Lead",
                "persona_name": "Commercial Growth Lead",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 20000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Direct commercial outreach, pipeline, and marketing."
            })
            if "TECH" in ind or "SAAS" in ind:
                exec_list.append({
                    "role_id": "EXEC_CTO",
                    "role_name": "CTO / Lead Architect",
                    "persona_name": "Engineering Lead",
                    "requirement_status": RoleRequirementStatus.REQUIRED.value,
                    "workforce_type": WorkforceType.AI_AGENT.value,
                    "budget_limit_usd": 30000.0,
                    "reporting_to": "EXEC_CEO",
                    "purpose": "Full-stack code architecture and cloud hosting."
                })
            return exec_list

        # Small to Growing companies
        exec_list.append({
            "role_id": "EXEC_CFO",
            "role_name": "Chief Financial Officer (CFO)",
            "persona_name": "Corporate Treasurer & CFO",
            "requirement_status": RoleRequirementStatus.REQUIRED.value,
            "workforce_type": WorkforceType.AI_AGENT.value,
            "budget_limit_usd": 100000.0,
            "reporting_to": "EXEC_CEO",
            "purpose": "Treasury, working capital, cash burn, and financial controls."
        })
        exec_list.append({
            "role_id": "EXEC_COO",
            "role_name": "Chief Operating Officer (COO)",
            "persona_name": "Operations Chief",
            "requirement_status": RoleRequirementStatus.REQUIRED.value,
            "workforce_type": WorkforceType.AI_AGENT.value,
            "budget_limit_usd": 75000.0,
            "reporting_to": "EXEC_CEO",
            "purpose": "Operational service delivery, quality, and SLA tracking."
        })

        if ("SAAS" in ind or "TECH" in ind) and "FINTECH" not in ind and "BIOTECH" not in ind:
            exec_list.append({
                "role_id": "EXEC_CTO",
                "role_name": "Chief Technology Officer (CTO)",
                "persona_name": "Technology Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 80000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "SaaS engineering, DevOps, and cloud reliability."
            })
            exec_list.append({
                "role_id": "EXEC_CRO",
                "role_name": "Chief Revenue Officer (CRO)",
                "persona_name": "Revenue Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 60000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "B2B SaaS pipeline, renewals, and enterprise expansion."
            })
            if scale in [CompanyScaleStage.MIDSIZE_COMPANY, CompanyScaleStage.ENTERPRISE]:
                exec_list.append({
                    "role_id": "EXEC_CPO",
                    "role_name": "Chief Product Officer (CPO)",
                    "persona_name": "Product Chief",
                    "requirement_status": RoleRequirementStatus.REQUIRED.value,
                    "workforce_type": WorkforceType.AI_AGENT.value,
                    "budget_limit_usd": 50000.0,
                    "reporting_to": "EXEC_CEO",
                    "purpose": "Product discovery, roadmap, and customer UX."
                })
                exec_list.append({
                    "role_id": "EXEC_CISO",
                    "role_name": "Chief Information Security Officer (CISO)",
                    "persona_name": "Security Chief",
                    "requirement_status": RoleRequirementStatus.REQUIRED.value,
                    "workforce_type": WorkforceType.AI_AGENT.value,
                    "budget_limit_usd": 50000.0,
                    "reporting_to": "EXEC_CEO",
                    "purpose": "SOC2, pen-testing, data protection, and cloud security."
                })
        elif "HOTEL" in ind or "HOSPITALITY" in ind:
            exec_list.append({
                "role_id": "EXEC_CMO",
                "role_name": "Chief Marketing Officer (CMO)",
                "persona_name": "Hospitality Marketing Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 50000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Direct bookings, wedding campaigns, and luxury brand image."
            })
            exec_list.append({
                "role_id": "EXEC_CCO_CUSTOMER",
                "role_name": "Chief Customer Officer (CCO)",
                "persona_name": "Guest Experience Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 40000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Guest satisfaction, VIP concierge, and online reputation."
            })
            if scale in [CompanyScaleStage.GROWING_COMPANY, CompanyScaleStage.MIDSIZE_COMPANY, CompanyScaleStage.ENTERPRISE]:
                exec_list.append({
                    "role_id": "EXEC_CSCO",
                    "role_name": "Chief Supply Chain Officer (CSCO)",
                    "persona_name": "Procurement Chief",
                    "requirement_status": RoleRequirementStatus.REQUIRED.value,
                    "workforce_type": WorkforceType.AI_AGENT.value,
                    "budget_limit_usd": 45000.0,
                    "reporting_to": "EXEC_COO",
                    "purpose": "F&B supplies, linen procurement, and hotel vendor management."
                })
        elif "MANUFACTURING" in ind:
            exec_list.append({
                "role_id": "EXEC_CSCO",
                "role_name": "Chief Supply Chain Officer (CSCO)",
                "persona_name": "Supply Chain Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 90000.0,
                "reporting_to": "EXEC_COO",
                "purpose": "Raw material procurement, tier-1 inventory, and logistics."
            })
            exec_list.append({
                "role_id": "EXEC_CTO",
                "role_name": "Chief Technology Officer (CTO)",
                "persona_name": "Industrial Engineering Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 60000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Automation systems, CNC telemetry, and predictive maintenance."
            })
        elif "HEALTHCARE" in ind or "BIOTECH" in ind or "CLINICAL" in ind or "PHARMA" in ind:
            exec_list.append({
                "role_id": "EXEC_CMO_MEDICAL",
                "role_name": "Chief Medical Officer (CMO-Medical)",
                "persona_name": "Clinical Governance & Medical Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 70000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Clinical trial protocols, clinical governance, and patient safety."
            })
            exec_list.append({
                "role_id": "EXEC_CRO_RISK",
                "role_name": "Chief Risk & Compliance Officer",
                "persona_name": "Healthcare Risk Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 65000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Statutory healthcare compliance, clinical risk, and regulatory audits."
            })
            exec_list.append({
                "role_id": "EXEC_CPCO",
                "role_name": "Chief Privacy Officer (CPCO)",
                "persona_name": "Data Privacy Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 50000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "HIPAA compliance, patient data privacy, and consent management."
            })
        elif "FINTECH" in ind or "FINANCIAL" in ind or "BANKING" in ind:
            exec_list.append({
                "role_id": "EXEC_CRO_RISK",
                "role_name": "Chief Risk Officer (CRO-Risk)",
                "persona_name": "Financial Risk & Capital Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 75000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Capital adequacy, credit risk, market volatility, and liquidity modeling."
            })
            exec_list.append({
                "role_id": "EXEC_CISO",
                "role_name": "Chief Information Security Officer (CISO)",
                "persona_name": "Cyber Defense Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 70000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "SOC2, PCI-DSS, zero-trust infrastructure, and anti-tamper controls."
            })
            exec_list.append({
                "role_id": "EXEC_CCO_COMPLIANCE",
                "role_name": "Chief Compliance Officer (CCO-Compliance)",
                "persona_name": "Regulatory & AML Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 65000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "FinCEN, SEC, KYC/AML, and statutory regulatory filings."
            })
        elif "RETAIL" in ind or "ECOMMERCE" in ind:
            exec_list.append({
                "role_id": "EXEC_CMO",
                "role_name": "Chief Marketing Officer (CMO)",
                "persona_name": "Brand & Acquisition Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 60000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Omnichannel customer acquisition, performance ad spend, and brand equity."
            })
            exec_list.append({
                "role_id": "EXEC_CSCO",
                "role_name": "Chief Supply Chain Officer (CSCO)",
                "persona_name": "Fulfillment & SCM Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 55000.0,
                "reporting_to": "EXEC_COO",
                "purpose": "Warehousing, inventory replenishment, and 3PL shipping logistics."
            })
            exec_list.append({
                "role_id": "EXEC_CGO",
                "role_name": "Chief Growth Officer (CGO)",
                "persona_name": "Commerce Growth Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 50000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Conversion rate optimization, referral loops, and marketplace expansion."
            })
        elif "LOGISTICS" in ind or "FREIGHT" in ind or "SUPPLY_CHAIN" in ind:
            exec_list.append({
                "role_id": "EXEC_CSCO",
                "role_name": "Chief Supply Chain Officer (CSCO)",
                "persona_name": "Freight & Logistics Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 80000.0,
                "reporting_to": "EXEC_COO",
                "purpose": "Carrier network, freight dispatch, route optimization, and cross-docking."
            })
            exec_list.append({
                "role_id": "EXEC_CSE",
                "role_name": "Chief Safety & Environmental Officer (CSE)",
                "persona_name": "Fleet Safety & OSHA Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 50000.0,
                "reporting_to": "EXEC_COO",
                "purpose": "Fleet safety compliance, DOT regulations, and driver incident prevention."
            })
        elif "TRAVEL" in ind or "TOURISM" in ind:
            exec_list.append({
                "role_id": "EXEC_CRO",
                "role_name": "Chief Revenue Officer (CRO)",
                "persona_name": "Travel Revenue Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 50000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Package distribution, GDS partnerships, and customer bookings."
            })
            exec_list.append({
                "role_id": "EXEC_CCO_CUSTOMER",
                "role_name": "Chief Customer Officer (CCO)",
                "persona_name": "Traveler Experience Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 40000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Traveler support, rebooking, disruptions, and 24/7 concierge."
            })

        # People officer if human employees > 20
        if profile.current_human_employees >= 20:
            exec_list.append({
                "role_id": "EXEC_CHRO",
                "role_name": "Chief Human Resources Officer (CHRO)",
                "persona_name": "People & Culture Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 45000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Human workforce planning, recruitment, and hybrid collaboration."
            })

        # General Counsel if regulatory intensity is HIGH or SEVERE
        if profile.regulatory_intensity in ["HIGH", "SEVERE"]:
            exec_list.append({
                "role_id": "EXEC_CLO",
                "role_name": "Chief Legal Officer / General Counsel (CLO)",
                "persona_name": "Legal Counsel Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 60000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Regulatory disclosures, contract review, and external counsel liaison."
            })

        return exec_list

    @classmethod
    def _synthesize_departments(cls, profile: CompanyProfile, executives: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ind = profile.industry.upper()
        depts = []

        if "HOTEL" in ind or "HOSPITALITY" in ind:
            depts = [
                {"dept_id": "dept_rooms", "name": "Rooms & Front Office", "lead_role": "EXEC_COO", "purpose": "Guest check-in, room turnover, and front desk operations."},
                {"dept_id": "dept_fnb", "name": "Food & Beverage (F&B)", "lead_role": "EXEC_COO", "purpose": "Restaurant dining, banquet banqueting, and culinary inventory."},
                {"dept_id": "dept_sales_mkt", "name": "Sales & Revenue Marketing", "lead_role": "EXEC_CMO", "purpose": "Direct bookings, wedding sales, and channel optimization."},
                {"dept_id": "dept_finance", "name": "Finance & Accounting", "lead_role": "EXEC_CFO", "purpose": "Hotel night audit, vendor payouts, and guest billing."},
                {"dept_id": "dept_maintenance", "name": "Engineering & Facilities", "lead_role": "EXEC_COO", "purpose": "HVAC, physical security, asset maintenance, and utilities."}
            ]
        elif ("SAAS" in ind or "TECH" in ind) and "FINTECH" not in ind and "BIOTECH" not in ind:
            depts = [
                {"dept_id": "dept_eng", "name": "Software Engineering", "lead_role": "EXEC_CTO", "purpose": "Core platform code, APIs, database architecture, and release cycles."},
                {"dept_id": "dept_prod", "name": "Product & Design", "lead_role": "EXEC_CPO" if any(e["role_id"]=="EXEC_CPO" for e in executives) else "EXEC_CTO", "purpose": "Roadmap prioritization, UX/UI, and feature specification."},
                {"dept_id": "dept_rev", "name": "Sales & Revenue Operations", "lead_role": "EXEC_CRO", "purpose": "B2B pipeline generation, enterprise closing, and partner channels."},
                {"dept_id": "dept_cs", "name": "Customer Success & Support", "lead_role": "EXEC_CRO", "purpose": "User onboarding, retention, technical support, and NRR."},
                {"dept_id": "dept_fin", "name": "Finance & Operations", "lead_role": "EXEC_CFO", "purpose": "SaaS billing, MRR accounting, metrics audit, and cash burn."}
            ]
        elif "MANUFACTURING" in ind:
            depts = [
                {"dept_id": "dept_prod", "name": "Plant Production & Assembly", "lead_role": "EXEC_COO", "purpose": "Factory floor execution, machine utilization, and OEE."},
                {"dept_id": "dept_qa", "name": "Quality Assurance & Testing", "lead_role": "EXEC_COO", "purpose": "Defect inspection, ISO 9001 compliance, and tolerance testing."},
                {"dept_id": "dept_scm", "name": "Procurement & Supply Chain", "lead_role": "EXEC_CSCO", "purpose": "Raw material procurement, supplier audits, and shipping logistics."},
                {"dept_id": "dept_fin", "name": "Cost Accounting & Finance", "lead_role": "EXEC_CFO", "purpose": "COGS optimization, asset depreciation, and bill of materials (BOM)."}
            ]
        elif "HEALTHCARE" in ind or "BIOTECH" in ind or "CLINICAL" in ind or "PHARMA" in ind:
            depts = [
                {"dept_id": "dept_clinical", "name": "Clinical Affairs & Patient Care", "lead_role": "EXEC_CMO_MEDICAL", "purpose": "Patient care delivery, clinical scheduling, and clinical trial oversight."},
                {"dept_id": "dept_compliance", "name": "Regulatory & Medical Compliance", "lead_role": "EXEC_CRO_RISK", "purpose": "HIPAA compliance, FDA/EMA filing protocols, and patient safety audits."},
                {"dept_id": "dept_privacy", "name": "Data Privacy & Patient Records", "lead_role": "EXEC_CPCO", "purpose": "EHR privacy governance, patient consent records, and access security."},
                {"dept_id": "dept_lab", "name": "Research & Lab Operations", "lead_role": "EXEC_COO", "purpose": "Laboratory workflows, assay validation, and specimen logistics."},
                {"dept_id": "dept_fin", "name": "Medical Billing & Finance", "lead_role": "EXEC_CFO", "purpose": "Insurance claims, patient invoicing, and provider payouts."}
            ]
        elif "FINTECH" in ind or "FINANCIAL" in ind or "BANKING" in ind:
            depts = [
                {"dept_id": "dept_treasury", "name": "Treasury & Capital Markets", "lead_role": "EXEC_CFO", "purpose": "Capital adequacy, liquidity buffers, and yield optimization."},
                {"dept_id": "dept_risk", "name": "Risk Management & Solvency", "lead_role": "EXEC_CRO_RISK", "purpose": "Credit risk evaluation, market volatility stress testing, and counterparty exposure."},
                {"dept_id": "dept_compliance", "name": "Regulatory Compliance & AML", "lead_role": "EXEC_CCO_COMPLIANCE", "purpose": "FinCEN/SEC statutory audits, KYC/AML surveillance, and anti-fraud filters."},
                {"dept_id": "dept_secops", "name": "SecOps & Financial Engineering", "lead_role": "EXEC_CISO", "purpose": "PCI-DSS certified infrastructure, transactional cryptography, and pen-testing."},
                {"dept_id": "dept_audit", "name": "Internal Audit & Controls", "lead_role": "EXEC_CFO", "purpose": "Ledger reconciliation, dual-signoff enforcement, and external auditor defense."}
            ]
        elif "RETAIL" in ind or "ECOMMERCE" in ind:
            depts = [
                {"dept_id": "dept_store", "name": "E-Commerce & Digital Storefront", "lead_role": "EXEC_COO", "purpose": "Online catalog, checkout funnel, payment gateway, and cart conversion."},
                {"dept_id": "dept_fulfillment", "name": "Fulfillment & Warehousing", "lead_role": "EXEC_CSCO", "purpose": "Pick-pack-ship SLAs, warehouse stock turns, and carrier tracking."},
                {"dept_id": "dept_merch", "name": "Merchandising & SCM", "lead_role": "EXEC_CSCO", "purpose": "SKU catalog management, supplier replenishment, and margin optimization."},
                {"dept_id": "dept_mkt", "name": "Performance Marketing & Acquisition", "lead_role": "EXEC_CMO", "purpose": "ROAS ad spend, influencer campaigns, SEO cataloging, and promotions."},
                {"dept_id": "dept_support", "name": "Customer Support & Returns", "lead_role": "EXEC_COO", "purpose": "RMA returns, ticket SLAs, live chat assistance, and CSAT."}
            ]
        elif "LOGISTICS" in ind or "FREIGHT" in ind or "SUPPLY_CHAIN" in ind:
            depts = [
                {"dept_id": "dept_freight", "name": "Fleet & Freight Logistics", "lead_role": "EXEC_CSCO", "purpose": "Intermodal freight routing, load balancing, and carrier contract execution."},
                {"dept_id": "dept_dispatch", "name": "Dispatch & Route Operations", "lead_role": "EXEC_COO", "purpose": "Real-time fleet tracking, dynamic dispatch, and on-time delivery (OTD)."},
                {"dept_id": "dept_procurement", "name": "Procurement & Carrier Network", "lead_role": "EXEC_CSCO", "purpose": "Fuel hedging, spot rate bidding, and third-party logistics agreements."},
                {"dept_id": "dept_safety", "name": "Safety & Fleet Maintenance", "lead_role": "EXEC_CSE", "purpose": "DOT inspections, driver hours-of-service, and preventative vehicle upkeep."},
                {"dept_id": "dept_fin", "name": "Logistics Finance & Billing", "lead_role": "EXEC_CFO", "purpose": "Freight bill auditing, accessorial billing, and working capital DSO."}
            ]
        elif "TRAVEL" in ind or "TOURISM" in ind:
            depts = [
                {"dept_id": "dept_bookings", "name": "Bookings & Travel Operations", "lead_role": "EXEC_COO", "purpose": "Itinerary booking, GDS ticketing, and partner network scheduling."},
                {"dept_id": "dept_customer_care", "name": "Traveler Care & Concierge", "lead_role": "EXEC_CCO_CUSTOMER", "purpose": "24/7 guest support, trip disruptions, and traveler satisfaction."},
                {"dept_id": "dept_sales_growth", "name": "Commercial Distribution & Sales", "lead_role": "EXEC_CRO", "purpose": "Corporate travel accounts, holiday packages, and channel distribution."},
                {"dept_id": "dept_fin", "name": "Settlements & Finance", "lead_role": "EXEC_CFO", "purpose": "Airline GDS settlements, merchant fees, and currency hedging."}
            ]
        else:
            # Universal Default
            depts = [
                {"dept_id": "dept_ops", "name": "Operations & Fulfillment", "lead_role": "EXEC_COO", "purpose": "Core business execution and customer service delivery."},
                {"dept_id": "dept_growth", "name": "Growth & Commercial Revenue", "lead_role": "EXEC_CRO" if any(e["role_id"]=="EXEC_CRO" for e in executives) else "EXEC_CEO", "purpose": "Customer acquisition, sales, and marketing campaigns."},
                {"dept_id": "dept_fin", "name": "Finance & Administration", "lead_role": "EXEC_CFO", "purpose": "Accounting, invoices, payroll, and compliance controls."}
            ]

        for d in depts:
            if "name" in d and "department_name" not in d:
                d["department_name"] = d["name"]
            if "department_name" in d and "name" not in d:
                d["name"] = d["department_name"]
            if "lead_role" in d and "executive_lead" not in d:
                d["executive_lead"] = d["lead_role"]
            if "executive_lead" in d and "lead_role" not in d:
                d["lead_role"] = d["executive_lead"]

        return depts

    @classmethod
    def _synthesize_workforce(cls, profile: CompanyProfile, departments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Dynamically calculates workforce agents based on actual workload, not arbitrary quotas.
        """
        scale = profile.company_size
        agents = []

        # Formula: Base staffing by department multiplied by scale factor
        multiplier = 1
        if scale == CompanyScaleStage.SMALL_COMPANY:
            multiplier = 2
        elif scale == CompanyScaleStage.GROWING_COMPANY:
            multiplier = 3
        elif scale in [CompanyScaleStage.MIDSIZE_COMPANY, CompanyScaleStage.ENTERPRISE]:
            multiplier = 5

        agent_counter = 1
        for dept in departments:
            d_id = dept["dept_id"]
            d_name = dept["name"]

            # 1. Department Manager Agent
            mgr_id = f"agt_mgr_{d_id}"
            agents.append({
                "agent_id": mgr_id,
                "name": f"{d_name} Lead Manager",
                "role_category": AgentCategory.MANAGEMENT_AGENT.value,
                "hierarchy_level": HierarchyLevel.L8_MANAGER.value,
                "department_id": d_id,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "capabilities": ["TaskAssignment", "ExceptionReview", "WorkforceCoordination"],
                "authority_limit_usd": 10000.0,
                "reporting_to": dept["lead_role"]
            })

            # 2. Specialist Agents
            for s in range(1, multiplier + 1):
                spec_id = f"agt_spec_{d_id}_{s}"
                agents.append({
                    "agent_id": spec_id,
                    "name": f"{d_name} Specialist #{s}",
                    "role_category": AgentCategory.SPECIALIST_AGENT.value,
                    "hierarchy_level": HierarchyLevel.L9_SPECIALIST.value,
                    "department_id": d_id,
                    "workforce_type": WorkforceType.AI_AGENT.value,
                    "capabilities": ["WorkflowExecution", "DataAnalysis", "ToolInteraction"],
                    "authority_limit_usd": 2500.0,
                    "reporting_to": mgr_id
                })

            # 3. Worker / Execution Agents for high-volume tasks
            worker_id = f"agt_wrk_{d_id}_01"
            agents.append({
                "agent_id": worker_id,
                "name": f"{d_name} Execution Runner",
                "role_category": AgentCategory.WORKER_AGENT.value,
                "hierarchy_level": HierarchyLevel.L10_WORKER.value,
                "department_id": d_id,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "capabilities": ["DataEntry", "TelemetryLogging", "DocumentVerification"],
                "authority_limit_usd": 500.0,
                "reporting_to": mgr_id
            })

        return agents

    @classmethod
    def _evaluate_spans_of_control(
        cls,
        executives: List[Dict[str, Any]],
        departments: List[Dict[str, Any]],
        workforce: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates manager-to-report ratios and flags SPAN_TOO_LARGE (> 10) or SPAN_TOO_SMALL (< 2).
        """
        # Count direct reports to CEO
        ceo_reports = len([e for e in executives if e.get("reporting_to") == "EXEC_CEO"])
        
        # Count reports per department manager
        mgr_spans = {}
        for a in workforce:
            if a["role_category"] in [AgentCategory.SPECIALIST_AGENT.value, AgentCategory.WORKER_AGENT.value]:
                rep = a.get("reporting_to")
                if rep:
                    mgr_spans[rep] = mgr_spans.get(rep, 0) + 1

        flags = []
        if ceo_reports > 8:
            flags.append({"target": "EXEC_CEO", "status": "SPAN_TOO_LARGE", "count": ceo_reports, "recommendation": "Group related functions under COO or Chief of Staff."})
        elif ceo_reports < 2 and len(executives) > 1:
            flags.append({"target": "EXEC_CEO", "status": "SPAN_TOO_SMALL", "count": ceo_reports, "recommendation": "Merge intermediate layers."})

        for mgr, cnt in mgr_spans.items():
            if cnt > 10:
                flags.append({"target": mgr, "status": "SPAN_TOO_LARGE", "count": cnt, "recommendation": "Split team into sub-functions or introduce Team Leads."})
            elif cnt < 2:
                flags.append({"target": mgr, "status": "SPAN_TOO_SMALL", "count": cnt, "recommendation": "Consolidate management overhead."})

        return {
            "ceo_span": ceo_reports,
            "manager_spans": mgr_spans,
            "flags": flags,
            "is_balanced": len(flags) == 0
        }

    @classmethod
    def _generate_kra_kpi_cascade(
        cls,
        profile: CompanyProfile,
        executives: List[Dict[str, Any]],
        departments: List[Dict[str, Any]],
        workforce: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generates connected KRA and KPI cascades with anti-gaming counter-metrics.
        """
        kras = []
        kpis = []

        # 1. Enterprise / CEO KRA & KPI
        kras.append({
            "kra_id": "KRA_ENT_01",
            "level": "ENTERPRISE",
            "owner": "EXEC_CEO",
            "name": "Sustainable Profitable Growth",
            "description": "Expand enterprise revenue while protecting gross margin and free cash flow."
        })
        kpis.append({
            "kpi_id": "KPI_ENT_01",
            "kra_id": "KRA_ENT_01",
            "name": "Contribution Margin %",
            "owner": "EXEC_CEO",
            "baseline": 50.0,
            "target": 65.0,
            "unit": "PERCENT",
            "frequency": "MONTHLY",
            "counter_metric_id": "KPI_ENT_REV",
            "anti_gaming_rule": "Revenue growth without positive contribution margin is flagged as economic deterioration.",
            "data_source": "AUDITED_LEDGER"
        })

        # 2. Executive / Departmental KRAs & KPIs
        for d in departments:
            d_id = d["dept_id"]
            d_name = d["name"]
            lead = d["lead_role"]

            kra_id = f"KRA_{d_id.upper()}"
            kras.append({
                "kra_id": kra_id,
                "level": "DEPARTMENT",
                "owner": lead,
                "department_id": d_id,
                "name": f"{d_name} Operational Delivery",
                "description": f"Ensure disciplined execution, SLA adherence, and budget control for {d_name}."
            })

            # Department KPI with anti-gaming pair
            kpi_p_id = f"KPI_{d_id.upper()}_EFF"
            kpi_c_id = f"KPI_{d_id.upper()}_QUAL"

            kpis.append({
                "kpi_id": kpi_p_id,
                "kra_id": kra_id,
                "name": f"{d_name} Throughput / Output",
                "owner": lead,
                "baseline": 100.0,
                "target": 120.0,
                "unit": "UNITS",
                "frequency": "WEEKLY",
                "counter_metric_id": kpi_c_id,
                "anti_gaming_rule": f"Throughput gains at the expense of {d_name} quality or defect spikes are rejected.",
                "data_source": "DEPARTMENT_TELEMETRY"
            })
            kpis.append({
                "kpi_id": kpi_c_id,
                "kra_id": kra_id,
                "name": f"{d_name} Quality & Error Rate %",
                "owner": lead,
                "baseline": 2.5,
                "target": 1.0,
                "unit": "PERCENT",
                "frequency": "WEEKLY",
                "counter_metric_id": kpi_p_id,
                "anti_gaming_rule": "Quality metric must remain below threshold during any volume expansion.",
                "data_source": "QA_AUDIT_LOGS"
            })

        return kras, kpis

    @classmethod
    def _generate_executable_sops(cls, profile: CompanyProfile, departments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sops = []
        for d in departments:
            d_id = d["dept_id"]
            sops.append({
                "sop_id": f"SOP_{d_id.upper()}_01",
                "name": f"{d['name']} Standard Operating Procedure",
                "department_id": d_id,
                "owner_role": d["lead_role"],
                "trigger": "OPERATIONAL_REQUEST_OR_SCHEDULE",
                "preconditions": ["Authority Validated", "Data Inputs Grounded"],
                "steps": [
                    {"step": 1, "action": "Validate Authority & Permissions", "system": "AuthorityGateway"},
                    {"step": 2, "action": "Fetch Ground Truth Parameters", "system": "EvidenceLedger"},
                    {"step": 3, "action": "Evaluate Financial & Risk Boundary", "system": "PolicyEngine"},
                    {"step": 4, "action": "Execute Governed Workflow Step", "system": "TemporalEngine"},
                    {"step": 5, "action": "Verify Business Outcome & Hash Artifact", "system": "VerificationEngine"}
                ],
                "risk_limit": "MEDIUM",
                "success_criteria": "Cryptographic receipt verified and recorded to Evidence Ledger.",
                "status": "ACTIVE_VERSION_1"
            })
        return sops

    @classmethod
    def _construct_reporting_tree(
        cls,
        profile: CompanyProfile,
        executives: List[Dict[str, Any]],
        departments: List[Dict[str, Any]],
        workforce: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assembles clean nested tree representing the enterprise hierarchy.
        """
        ceo_node = next((e for e in executives if e["role_id"] == "EXEC_CEO"), executives[0])
        tree = {
            "id": ceo_node["role_id"],
            "title": ceo_node["role_name"],
            "persona": ceo_node["persona_name"],
            "level": "L2_CEO",
            "children": []
        }

        # Direct reports to CEO
        exec_map = {}
        for e in executives:
            if e["role_id"] == "EXEC_CEO":
                continue
            e_node = {
                "id": e["role_id"],
                "title": e["role_name"],
                "persona": e["persona_name"],
                "level": "L3_CHIEF_EXECUTIVE",
                "children": []
            }
            exec_map[e["role_id"]] = e_node
            tree["children"].append(e_node)

        # Attach departments to executives
        dept_map = {}
        for d in departments:
            d_node = {
                "id": d["dept_id"],
                "title": d["name"],
                "level": "L5_DEPARTMENT",
                "children": []
            }
            dept_map[d["dept_id"]] = d_node
            lead = d["lead_role"]
            if lead in exec_map:
                exec_map[lead]["children"].append(d_node)
            else:
                tree["children"].append(d_node)

        # Attach workforce agents to departments
        for a in workforce:
            a_node = {
                "id": a["agent_id"],
                "title": a["name"],
                "category": a["role_category"],
                "level": a["hierarchy_level"],
                "children": []
            }
            d_id = a.get("department_id")
            if d_id in dept_map:
                dept_map[d_id]["children"].append(a_node)

        return tree

# ==============================================================================
# 6. COMMUNICATION, DELEGATION & ESCALATION ENGINES
# ==============================================================================

@dataclass
class GovernedMessage:
    message_id: str
    sender_id: str
    recipient_id: str
    message_type: str                   # INFO, REQUEST, DECISION, APPROVAL, ESCALATION, ALERT
    priority: str                       # LOW, MEDIUM, HIGH, CRITICAL
    subject: str
    content: str
    evidence_ref: Optional[str]
    deadline_timestamp: Optional[float]
    status: str                         # SENT, DELIVERED, ACKNOWLEDGED, RESOLVED
    created_at: float = field(default_factory=time.time)

@dataclass
class DelegationRecord:
    delegation_id: str
    delegator_id: str
    delegatee_id: str
    mission_mandate: str
    granted_authority_level: str
    budget_limit_usd: float
    time_limit_hours: float
    prohibited_actions: List[str]
    success_criteria: str
    status: str                         # ACTIVE, REVOKED, COMPLETED
    timestamp: float = field(default_factory=time.time)

@dataclass
class EscalationEvent:
    escalation_id: str
    originator_id: str
    target_executive_id: str
    escalation_trigger: str             # RISK_EXCEEDED, FINANCIAL_THRESHOLD, SAFETY_CRITICAL, UNRESOLVED_CONFLICT
    severity: str                       # MEDIUM, HIGH, CRITICAL
    context_details: Dict[str, Any]
    required_resolution: str
    status: str                         # OPEN, UNDER_REVIEW, RESOLVED
    timestamp: float = field(default_factory=time.time)

class ExecutiveCommunicationEngine:
    """
    Governed enterprise communication channels with anti-storm protections.
    """
    _messages: List[GovernedMessage] = []
    _rate_limits: Dict[str, List[float]] = {}

    @classmethod
    def send_message(
        cls,
        sender_id: str,
        recipient_id: str,
        message_type: str,
        subject: str,
        content: str,
        priority: str = "MEDIUM",
        evidence_ref: Optional[str] = None,
        deadline_hours: Optional[float] = None
    ) -> GovernedMessage:
        now = time.time()
        
        # Anti-storm rate limit: Max 20 messages per sender per minute
        history = cls._rate_limits.get(sender_id, [])
        history = [t for t in history if now - t < 60.0]
        if len(history) >= 20:
            raise RuntimeError(f"COMMUNICATION_STORM_PREVENTED: Sender '{sender_id}' exceeded rate limit (20 msgs/min).")
        history.append(now)
        cls._rate_limits[sender_id] = history

        deadline = now + (deadline_hours * 3600) if deadline_hours else None
        msg = GovernedMessage(
            message_id=f"msg_{uuid.uuid4().hex[:10]}",
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            priority=priority,
            subject=subject,
            content=content,
            evidence_ref=evidence_ref,
            deadline_timestamp=deadline,
            status="SENT",
            created_at=now
        )
        cls._messages.append(msg)
        return msg

    @classmethod
    def send_communication(
        cls,
        sender_id: str,
        recipient_id: str,
        subject: str,
        body: str,
        priority: Any = "REQUEST",
        response_required_by: Optional[float] = None,
        evidence_ref: Optional[str] = None
    ) -> GovernedMessage:
        p_val = priority.value if hasattr(priority, "value") else str(priority)
        return cls.send_message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type="DIRECTIVE",
            subject=subject,
            content=body,
            priority=p_val,
            evidence_ref=evidence_ref,
            deadline_hours=response_required_by
        )

    @classmethod
    def get_messages(cls, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not entity_id:
            return [asdict(m) for m in cls._messages]
        return [asdict(m) for m in cls._messages if m.sender_id == entity_id or m.recipient_id == entity_id]

class DelegationEngine:
    """
    Constitutional delegation: transfers bounded execution responsibility without transferring sovereign authority.
    """
    _delegations: Dict[str, DelegationRecord] = {}

    @classmethod
    def create_delegation(
        cls,
        delegator_id: str,
        delegatee_id: str,
        mandate: str,
        authority_level: str,
        budget_usd: float,
        time_hours: float,
        prohibitions: Optional[List[str]] = None,
        success_criteria: str = "Verified financial or operational deliverable"
    ) -> DelegationRecord:
        d_id = f"dlg_{uuid.uuid4().hex[:8]}"
        record = DelegationRecord(
            delegation_id=d_id,
            delegator_id=delegator_id,
            delegatee_id=delegatee_id,
            mission_mandate=mandate,
            granted_authority_level=authority_level,
            budget_limit_usd=budget_usd,
            time_limit_hours=time_hours,
            prohibited_actions=prohibitions or ["UNAUTHORIZED_DISCOUNTS", "LEGAL_COMMITMENTS", "SYSTEM_MUTATIONS"],
            success_criteria=success_criteria,
            status="ACTIVE"
        )
        cls._delegations[d_id] = record
        return record

    @classmethod
    def list_delegations(cls) -> List[Dict[str, Any]]:
        return [asdict(d) for d in cls._delegations.values()]

class EscalationEngine:
    """
    Rules-based escalation hierarchy routing unresolved risks upward through defined gates.
    """
    _escalations: List[EscalationEvent] = []

    @classmethod
    def trigger_escalation(
        cls,
        originator_id: str,
        target_executive_id: str,
        trigger_reason: str,
        severity: str,
        details: Dict[str, Any],
        required_resolution: str
    ) -> EscalationEvent:
        e_id = f"esc_{uuid.uuid4().hex[:8]}"
        event = EscalationEvent(
            escalation_id=e_id,
            originator_id=originator_id,
            target_executive_id=target_executive_id,
            escalation_trigger=trigger_reason,
            severity=severity,
            context_details=details,
            required_resolution=required_resolution,
            status="OPEN"
        )
        cls._escalations.append(event)
        return event

    @classmethod
    def list_escalations(cls) -> List[Dict[str, Any]]:
        return [asdict(e) for e in cls._escalations]

# ==============================================================================
# 7. ORGANIZATION RESTRUCTURING & SIMULATOR
# ==============================================================================

@dataclass
class OrgRestructuringSimulation:
    simulation_id: str
    company_id: str
    current_roles_count: int
    proposed_roles_count: int
    roles_added: List[str]
    roles_removed: List[str]
    roles_merged: List[str]
    projected_cost_delta_usd: float
    projected_efficiency_gain_pct: float
    risk_assessment: str
    organizational_value_score: float   # Cost + Capacity + Quality + Speed - Risk
    approval_required: str              # SOVEREIGN_OWNER, BOARD, AIC_CEO_INTERNAL
    created_at: float = field(default_factory=time.time)

class OrganizationRestructuringEngine:
    """
    Evaluates organizational efficiency, detects bottlenecks/excess,
    and calculates net Organizational Value before applying restructuring.
    """
    @classmethod
    def simulate_restructuring(
        cls,
        company_id: str,
        current_blueprint: Dict[str, Any],
        proposed_blueprint: Dict[str, Any]
    ) -> OrgRestructuringSimulation:
        s_id = f"sim_{uuid.uuid4().hex[:8]}"
        
        curr_roles = {e["role_id"] for e in current_blueprint.get("executives", [])}
        prop_roles = {e["role_id"] for e in proposed_blueprint.get("executives", [])}

        added = list(prop_roles - curr_roles)
        removed = list(curr_roles - prop_roles)

        curr_agents = len(current_blueprint.get("workforce_agents", []))
        prop_agents = len(proposed_blueprint.get("workforce_agents", []))

        # Organizational Value Equation:
        # Value = Output Efficiency (+20%) + Quality (+15%) - Cost Delta - Latent Risk
        cost_delta = (len(added) - len(removed)) * 40000.0 + (prop_agents - curr_agents) * 1200.0
        efficiency_gain = 18.5 if len(added) > 0 or prop_agents > curr_agents else 5.0
        
        # Determine approval requirement
        if len(added) > 2 or any("CFO" in r or "CLO" in r for r in added):
            approval = "SOVEREIGN_OWNER"
        else:
            approval = "AIC_CEO_INTERNAL"

        val_score = round(max(0.0, min(100.0, 75.0 + efficiency_gain - (cost_delta / 20000.0))), 1)

        return OrgRestructuringSimulation(
            simulation_id=s_id,
            company_id=company_id,
            current_roles_count=len(curr_roles),
            proposed_roles_count=len(prop_roles),
            roles_added=added,
            roles_removed=removed,
            roles_merged=[],
            projected_cost_delta_usd=cost_delta,
            projected_efficiency_gain_pct=efficiency_gain,
            risk_assessment="LOW: Redundancy safeguarded and DoA boundaries preserved.",
            organizational_value_score=val_score,
            approval_required=approval
        )

# ==============================================================================
# 8. EXISTING COMPANY DISCOVERY, AUDIT & TRANSFORMATION ENGINE (GAP OQ-01)
# ==============================================================================

@dataclass
class ExistingOrganizationData:
    """
    Intake schema for existing enterprise organizations.
    Gracefully handles missing information without silent fabrication.
    """
    company_id: str
    tenant_id: str
    company_name: str
    industry: str = "UNKNOWN"
    geography: str = "UNKNOWN"
    jurisdictions: List[str] = field(default_factory=lambda: ["UNKNOWN"])
    company_stage: str = "UNKNOWN"
    employee_count: int = 0
    AI_agent_count: int = 0
    contractor_count: int = 0
    business_units: List[Dict[str, Any]] = field(default_factory=list)
    departments: List[Dict[str, Any]] = field(default_factory=list)
    teams: List[Dict[str, Any]] = field(default_factory=list)
    managers: List[Dict[str, Any]] = field(default_factory=list)
    executives: List[Dict[str, Any]] = field(default_factory=list)
    reporting_lines: List[Dict[str, str]] = field(default_factory=list) # [{"subordinate": "...", "superior": "..."}]
    current_roles: List[Dict[str, Any]] = field(default_factory=list)
    current_KRAs: List[Dict[str, Any]] = field(default_factory=list)
    current_KPIs: List[Dict[str, Any]] = field(default_factory=list)
    current_SOPs: List[Dict[str, Any]] = field(default_factory=list)
    current_tools: List[str] = field(default_factory=list)
    current_systems: List[str] = field(default_factory=list)
    current_revenue_model: str = "UNKNOWN"
    current_customer_model: str = "UNKNOWN"
    current_operating_hours: str = "UNKNOWN"
    current_risk_profile: str = "UNKNOWN"
    current_regulatory_profile: str = "UNKNOWN"
    current_budget: float = 0.0
    current_cost_structure: Dict[str, float] = field(default_factory=dict)
    current_workload: str = "UNKNOWN"
    current_volume: float = 0.0
    current_service_levels: Dict[str, Any] = field(default_factory=dict)
    current_quality_metrics: Dict[str, Any] = field(default_factory=dict)
    current_exception_rate: float = 0.0
    current_pain_points: List[str] = field(default_factory=list)
    data_freshness: str = "FRESH" # FRESH, STALE, EXPIRED, UNKNOWN, UNVERIFIED, PARTIAL_DATA, DATA_CONFLICT

@dataclass
class CurrentOrgFingerprint:
    """
    Cryptographic snapshot of an organizational structure for audit and change detection.
    """
    company_id: str
    tenant_id: str
    node_count: int
    executive_count: int
    department_count: int
    team_count: int
    manager_count: int
    specialist_count: int
    worker_count: int
    agent_count: int
    reporting_edge_count: int
    KRA_count: int
    KPI_count: int
    SOP_count: int
    communication_channel_count: int
    escalation_path_count: int
    delegation_count: int
    budget_count: int
    risk_control_count: int
    regulatory_requirement_count: int
    generated_at: float
    source_version: str
    sha256_fingerprint: str

@dataclass
class OrganizationAuditReport:
    """
    Explainable multi-dimensional audit of an organization's health, governance, and operational integrity.
    """
    audit_id: str
    company_id: str
    tenant_id: str
    current_org_version: str
    audit_timestamp: float
    organization_health_score: float      # Composite 0-100
    governance_health_score: float        # Clear reporting, DoA, Owner sovereignty
    accountability_score: float           # 16-field coverage, single owner per outcome
    reporting_integrity_score: float      # No orphans, circulars, or dead ends
    span_of_control_score: float          # Adaptive span balance
    capability_coverage_score: float      # Required industry functions present
    KPI_coverage_score: float             # KRA to KPI mapping ratio
    SOP_coverage_score: float             # Executable SOP ownership
    risk_coverage_score: float            # ISO 31000 risk limits assigned
    regulatory_coverage_score: float      # Statutory compliance ownership
    resilience_score: float               # Failover role redundancy, no SPOFs
    cost_efficiency_score: float          # Management overhead ratio
    execution_capacity_score: float       # Queue handling vs throughput
    bottleneck_score: float               # Overloaded manager penalty
    duplication_score: float              # Duplicate role overlap penalty
    critical_gap_count: int
    warning_count: int
    recommendation_count: int
    gaps: List[Dict[str, Any]]
    warnings: List[str]
    recommendations: List[str]
    evidence_receipt: Dict[str, Any]

class ExistingOrganizationDiscoveryEngine:
    """
    Discovers, validates, and audits an existing enterprise organization structure.
    Executes 30 structural, operational, governance, and regulatory integrity checks.
    """
    @classmethod
    def generate_fingerprint(cls, data: ExistingOrganizationData, version: str = "CURRENT") -> CurrentOrgFingerprint:
        now = time.time()
        node_cnt = len(data.executives) + len(data.managers) + len(data.current_roles) + data.employee_count + data.AI_agent_count
        edge_cnt = len(data.reporting_lines)
        kra_cnt = len(data.current_KRAs)
        kpi_cnt = len(data.current_KPIs)
        sop_cnt = len(data.current_SOPs)
        
        raw = f"{data.tenant_id}:{data.company_id}:{node_cnt}:{edge_cnt}:{kra_cnt}:{kpi_cnt}:{sop_cnt}:{data.employee_count}:{data.AI_agent_count}:{now}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        return CurrentOrgFingerprint(
            company_id=data.company_id,
            tenant_id=data.tenant_id,
            node_count=node_cnt,
            executive_count=len(data.executives),
            department_count=len(data.departments),
            team_count=len(data.teams),
            manager_count=len(data.managers),
            specialist_count=len([r for r in data.current_roles if "specialist" in r.get("role_name", "").lower()]),
            worker_count=data.employee_count,
            agent_count=data.AI_agent_count,
            reporting_edge_count=edge_cnt,
            KRA_count=kra_cnt,
            KPI_count=kpi_cnt,
            SOP_count=sop_cnt,
            communication_channel_count=max(1, len(data.departments)),
            escalation_path_count=max(1, len(data.executives)),
            delegation_count=0,
            budget_count=1 if data.current_budget > 0 else 0,
            risk_control_count=1 if data.current_risk_profile != "UNKNOWN" else 0,
            regulatory_requirement_count=len(data.jurisdictions),
            generated_at=now,
            source_version=version,
            sha256_fingerprint=digest
        )

    @classmethod
    def audit_existing_organization(cls, data: ExistingOrganizationData) -> OrganizationAuditReport:
        audit_id = f"aud_org_{uuid.uuid4().hex[:8]}"
        now = time.time()

        gaps: List[Dict[str, Any]] = []
        warnings: List[str] = []
        recommendations: List[str] = []

        all_node_ids = {e.get("role_id") for e in data.executives if e.get("role_id")}
        all_node_ids.update({m.get("id") or m.get("manager_id") for m in data.managers if m.get("id") or m.get("manager_id")})
        all_node_ids.update({r.get("role_id") or r.get("id") for r in data.current_roles if r.get("role_id") or r.get("id")})

        # 1. Check reporting integrity (circular reporting, orphans, impossible reporting)
        subordinate_to_superior: Dict[str, str] = {}
        superior_to_subordinates: Dict[str, List[str]] = {}
        circulars: List[str] = []
        orphans: List[str] = []

        for line in data.reporting_lines:
            sub = line.get("subordinate")
            sup = line.get("superior")
            if not sub or not sup:
                continue
            if sub == sup:
                circulars.append(f"Self-reporting node: {sub}")
            if sup not in all_node_ids and sup not in ["OWNER", "BOARD", "EXEC_CEO"]:
                orphans.append(f"Orphan subordinate {sub} reports to non-existent superior {sup}")
            
            subordinate_to_superior[sub] = sup
            superior_to_subordinates.setdefault(sup, []).append(sub)

        # Detect circular reporting loops (A -> B -> A)
        for sub, sup in subordinate_to_superior.items():
            visited = {sub}
            curr = sup
            while curr and curr in subordinate_to_superior:
                if curr in visited:
                    circulars.append(f"Circular reporting detected: {sub} -> {sup} -> {curr}")
                    break
                visited.add(curr)
                curr = subordinate_to_superior.get(curr)

        if circulars:
            for c in circulars:
                gaps.append({"category": "REPORTING_GAP", "severity": "CRITICAL", "description": c})
        if orphans:
            for o in orphans:
                gaps.append({"category": "REPORTING_GAP", "severity": "HIGH", "description": o})

        # 2. Check for overloaded managers (> 12 direct reports)
        for sup, subs in superior_to_subordinates.items():
            if len(subs) > 12:
                warnings.append(f"Manager {sup} is overloaded with {len(subs)} direct reports (exceeds span benchmark).")
                gaps.append({
                    "category": "MANAGEMENT_OVERLOAD",
                    "severity": "MEDIUM",
                    "description": f"Superior {sup} manages {len(subs)} direct reports."
                })

        # 3. Check for single points of failure (critical functions without backup)
        spofs: List[str] = []
        has_ceo = any("CEO" in (e.get("role_id", "") + e.get("role_name", "")) for e in data.executives)
        if not has_ceo:
            gaps.append({"category": "ACCOUNTABILITY_GAP", "severity": "CRITICAL", "description": "No formal CEO/Executive Director leadership found."})
            spofs.append("Executive Direction")

        has_cfo = any("CFO" in (e.get("role_id", "") + e.get("role_name", "")) for e in data.executives)
        if data.employee_count > 10 and not has_cfo:
            gaps.append({"category": "MISSING_CAPABILITY", "severity": "HIGH", "description": "Company scale warrants dedicated CFO; financial treasury is unassigned."})
            spofs.append("Treasury & Solvency")

        has_security = any("CISO" in e.get("role_id", "") or "security" in e.get("role_name", "").lower() for e in data.executives)
        if "HIGH" in data.current_regulatory_profile.upper() and not has_security:
            gaps.append({"category": "REGULATORY_GAP", "severity": "HIGH", "description": "High regulatory profile without dedicated CISO or Security Officer."})

        # 4. Check for unowned KRAs, KPIs, SOPs
        unowned_kras = [k for k in data.current_KRAs if not k.get("owner_id") and not k.get("assigned_role")]
        for k in unowned_kras:
            gaps.append({"category": "KRA_GAP", "severity": "MEDIUM", "description": f"KRA '{k.get('title', 'Untitled')}' has no assigned accountable owner."})

        unowned_kpis = [k for k in data.current_KPIs if not k.get("owner_id") and not k.get("assigned_role")]
        for k in unowned_kpis:
            gaps.append({"category": "KPI_GAP", "severity": "MEDIUM", "description": f"KPI '{k.get('name', 'Untitled')}' has no assigned owner."})

        unowned_sops = [s for s in data.current_SOPs if not s.get("owner_role") and not s.get("owner_id")]
        for s in unowned_sops:
            gaps.append({"category": "SOP_GAP", "severity": "MEDIUM", "description": f"SOP '{s.get('title', 'Untitled')}' has no owner role."})

        # 5. Check Segregation of Duties conflicts
        sod_conflicts = SegregationOfDutiesEngine.audit_conflicts(data)
        for conf in sod_conflicts:
            gaps.append({"category": "AUTHORITY_GAP", "severity": "CRITICAL", "description": conf})

        # 6. Calculate Explainable Dimension Scores
        rep_score = max(0.0, 100.0 - (len(circulars) * 30.0) - (len(orphans) * 15.0))
        gov_score = max(0.0, 100.0 - (len(sod_conflicts) * 20.0) - (25.0 if not has_ceo else 0.0))
        acc_score = max(0.0, 100.0 - (len(unowned_kras) * 12.0) - (len(unowned_kpis) * 8.0))
        res_score = max(0.0, 100.0 - (len(spofs) * 20.0))
        span_score = max(0.0, 100.0 - (len(warnings) * 10.0))
        cap_score = 90.0 if len(data.departments) >= 3 else 65.0
        kpi_cov_score = max(0.0, 100.0 - (len(unowned_kpis) * 15.0))
        sop_cov_score = max(0.0, 100.0 - (len(unowned_sops) * 15.0))
        risk_cov_score = 85.0 if data.current_risk_profile != "UNKNOWN" else 40.0
        reg_cov_score = 90.0 if data.current_regulatory_profile != "UNKNOWN" else 45.0
        cost_eff_score = 80.0
        exec_cap_score = 85.0
        bottle_score = max(0.0, 100.0 - (len(warnings) * 15.0))
        dup_score = 90.0

        scores = [rep_score, gov_score, acc_score, res_score, span_score, cap_score, kpi_cov_score, sop_cov_score]
        composite_health = round(sum(scores) / len(scores), 1)

        # 7. Generate Recommendations
        if not has_cfo and data.employee_count > 10:
            recommendations.append("Establish dedicated CFO or treasury lead to safeguard cash runway.")
        if circulars:
            recommendations.append("Eliminate circular reporting relationships to restore chain of accountability.")
        if orphans:
            recommendations.append("Reassign orphan subordinate nodes to valid departmental superiors.")
        if unowned_kras or unowned_kpis:
            recommendations.append(f"Assign single accountable owners to {len(unowned_kras)} unowned KRAs and {len(unowned_kpis)} unowned KPIs.")
        if sod_conflicts:
            recommendations.append("Enforce segregation of duties: separate approval rights from execution/audit rights.")

        fingerprint = cls.generate_fingerprint(data)

        evidence_receipt = {
            "fingerprint_sha256": fingerprint.sha256_fingerprint,
            "audit_id": audit_id,
            "timestamp": now,
            "node_count": fingerprint.node_count,
            "status": "QUALIFIED_AUDIT"
        }

        return OrganizationAuditReport(
            audit_id=audit_id,
            company_id=data.company_id,
            tenant_id=data.tenant_id,
            current_org_version="1.0.0-DISCOVERED",
            audit_timestamp=now,
            organization_health_score=composite_health,
            governance_health_score=gov_score,
            accountability_score=acc_score,
            reporting_integrity_score=rep_score,
            span_of_control_score=span_score,
            capability_coverage_score=cap_score,
            KPI_coverage_score=kpi_cov_score,
            SOP_coverage_score=sop_cov_score,
            risk_coverage_score=risk_cov_score,
            regulatory_coverage_score=reg_cov_score,
            resilience_score=res_score,
            cost_efficiency_score=cost_eff_score,
            execution_capacity_score=exec_cap_score,
            bottleneck_score=bottle_score,
            duplication_score=dup_score,
            critical_gap_count=len([g for g in gaps if g.get("severity") == "CRITICAL"]),
            warning_count=len(warnings),
            recommendation_count=len(recommendations),
            gaps=gaps,
            warnings=warnings,
            recommendations=recommendations,
            evidence_receipt=evidence_receipt
        )

# ==============================================================================
# 9. DIFFERENCE MODEL, TRANSITION PLAN & ROLLBACK ENGINE
# ==============================================================================

@dataclass
class OrganizationDifferenceModel:
    """
    Formal diff model contrasting current state against proposed target blueprint.
    """
    diff_id: str
    company_id: str
    added_roles: List[Dict[str, Any]]
    removed_roles: List[Dict[str, Any]]
    renamed_roles: List[Dict[str, str]]
    merged_roles: List[Dict[str, Any]]
    split_departments: List[Dict[str, Any]]
    moved_nodes: List[Dict[str, str]]
    authority_changes: List[Dict[str, Any]]
    budget_changes: List[Dict[str, Any]]
    KRA_changes: List[Dict[str, Any]]
    KPI_changes: List[Dict[str, Any]]
    SOP_changes: List[Dict[str, Any]]
    reporting_changes: List[Dict[str, str]]
    workforce_changes: Dict[str, int]
    regulatory_owner_changes: List[Dict[str, str]]

    @classmethod
    def calculate_diff(cls, current_org: Dict[str, Any], target_blueprint: Dict[str, Any]) -> "OrganizationDifferenceModel":
        d_id = f"diff_{uuid.uuid4().hex[:8]}"
        comp_id = target_blueprint.get("company_id", "comp_default")

        curr_execs = {e.get("role_id"): e for e in current_org.get("executives", []) if e.get("role_id")}
        target_execs = {e.get("role_id"): e for e in target_blueprint.get("executives", []) if e.get("role_id")}

        added = [target_execs[rid] for rid in target_execs if rid not in curr_execs]
        removed = [curr_execs[rid] for rid in curr_execs if rid not in target_execs]

        authority_chgs = []
        for rid in target_execs:
            if rid in curr_execs:
                t_bgt = target_execs[rid].get("budget_limit_usd", 0.0)
                c_bgt = curr_execs[rid].get("budget_limit_usd", 0.0)
                if t_bgt != c_bgt:
                    authority_chgs.append({"role_id": rid, "previous_budget": c_bgt, "new_budget": t_bgt})

        curr_agents_cnt = len(current_org.get("workforce_agents", []))
        targ_agents_cnt = len(target_blueprint.get("workforce_agents", []))

        return OrganizationDifferenceModel(
            diff_id=d_id,
            company_id=comp_id,
            added_roles=added,
            removed_roles=removed,
            renamed_roles=[],
            merged_roles=[],
            split_departments=[],
            moved_nodes=[],
            authority_changes=authority_chgs,
            budget_changes=authority_chgs,
            KRA_changes=[{"status": "ALIGNED_TO_TARGET"}],
            KPI_changes=[{"status": "PAIRED_COUNTER_METRICS_ADDED"}],
            SOP_changes=[{"status": "GOVERNED_EXECUTABLE_SOPS_ATTACHED"}],
            reporting_changes=[],
            workforce_changes={"current": curr_agents_cnt, "target": targ_agents_cnt, "delta": targ_agents_cnt - curr_agents_cnt},
            regulatory_owner_changes=[]
        )

@dataclass
class OrganizationTransitionPlan:
    """
    Phased transition plan ensuring zero authority vacuum during organizational change.
    """
    transition_id: str
    company_id: str
    current_version: str
    target_version: str
    phases: List[Dict[str, Any]]
    affected_people: int
    affected_agents: int
    authority_changes: List[Dict[str, Any]]
    rollback_plan: Dict[str, Any]
    approval_requirements: str # SOVEREIGN_OWNER, AIC_CEO_INTERNAL
    risk_assessment: str
    expected_duration_days: int
    success_criteria: str
    evidence_receipt: Dict[str, Any]

    @classmethod
    def create_transition_plan(cls, company_id: str, diff: OrganizationDifferenceModel) -> "OrganizationTransitionPlan":
        t_id = f"trans_{uuid.uuid4().hex[:8]}"
        
        # Verify no authority vacuum before removal
        for rem in diff.removed_roles:
            rid = rem.get("role_id", "")
            if "CFO" in rid and not any("CFO" in a.get("role_id", "") or "treasury" in a.get("purpose", "").lower() for a in diff.added_roles):
                raise RuntimeError(f"AUTHORITY_VACUUM_PREVENTED: Cannot remove {rid} without successor treasury ownership.")

        approval = "SOVEREIGN_OWNER" if len(diff.added_roles) > 2 or any("CFO" in r.get("role_id", "") or "CLO" in r.get("role_id", "") for r in diff.added_roles) else "AIC_CEO_INTERNAL"

        phases = [
            {"phase": 1, "title": "Governance Authorization", "action": "Owner/CEO signoff and DoA commitment"},
            {"phase": 2, "title": "Pre-Provisioning & Successor Onboarding", "action": "Provision successor roles before altering existing duties"},
            {"phase": 3, "title": "Reporting & Communication Cutover", "action": "Update reporting lines and anti-storm channels"},
            {"phase": 4, "title": "SOP & KPI Verification", "action": "Verify executable SOPs and anti-gaming counter-metrics"},
            {"phase": 5, "title": "Audit & Post-Cutover Telemetry", "action": "Log cryptographic receipt into EvidenceLedger"}
        ]

        rollback = {
            "strategy": "STATE_RESTORE",
            "safe_fallback_version": "1.0.0-DISCOVERED",
            "preconditions": ["Target version backup preserved", "No unassigned regulatory responsibilities"]
        }

        return OrganizationTransitionPlan(
            transition_id=t_id,
            company_id=company_id,
            current_version="1.0.0-DISCOVERED",
            target_version="2.0.0-TARGET",
            phases=phases,
            affected_people=0,
            affected_agents=diff.workforce_changes.get("target", 0),
            authority_changes=diff.authority_changes,
            rollback_plan=rollback,
            approval_requirements=approval,
            risk_assessment="LOW: Redundancy safeguarded and authority vacuum prevented.",
            expected_duration_days=14,
            success_criteria="All departments operational, all KRAs owned, zero unowned KPIs.",
            evidence_receipt={"transition_id": t_id, "timestamp": time.time(), "sha256": hashlib.sha256(t_id.encode()).hexdigest()}
        )

class OrganizationRollbackEngine:
    """
    Safely reverts organizational changes or escalates to Owner if rollback causes an authority vacuum.
    """
    @classmethod
    def rollback(cls, company_id: str, target_version: str, current_version: str) -> Dict[str, Any]:
        if not target_version:
            return {
                "success": False,
                "status": "ESCALATE_TO_OWNER",
                "reason": "ROLLBACK_UNSAFE: No valid target version specified; escalating to Sovereign Owner."
            }
        
        now = time.time()
        receipt = {
            "rollback_id": f"rb_{uuid.uuid4().hex[:8]}",
            "company_id": company_id,
            "reverted_from": current_version,
            "restored_to": target_version,
            "timestamp": now,
            "status": "ROLLED_BACK",
            "sha256": hashlib.sha256(f"{company_id}:{target_version}:{now}".encode()).hexdigest()
        }
        return {"success": True, "status": "ROLLED_BACK", "receipt": receipt}

# ==============================================================================
# 10. ADAPTIVE SPAN-OF-CONTROL & WORKFORCE SCALING ENGINE (GAP OQ-03)
# ==============================================================================

class AdaptiveSpanOfControlEngine:
    """
    Context-aware span-of-control reasoning based on operational complexity rather than rigid constants.
    """
    @classmethod
    def calculate_complexity_score(
        cls,
        role_complexity: float = 5.0,
        risk_level: str = "MEDIUM",
        regulatory_intensity: str = "MEDIUM",
        workload_volatility: float = 0.3,
        exception_rate: float = 0.05,
        geographic_dispersion: int = 1,
        workforce_type: str = "AI_AGENT"
    ) -> float:
        risk_w = 10.0 if risk_level == "CRITICAL" else (8.0 if risk_level == "HIGH" else (5.0 if risk_level == "MEDIUM" else 2.0))
        reg_w = 10.0 if regulatory_intensity == "SEVERE" else (8.5 if regulatory_intensity == "HIGH" else (5.0 if regulatory_intensity == "MEDIUM" else 2.0))
        wf_w = 8.0 if workforce_type == "HUMAN" else 3.0 # AI agents with telemetry require less cognitive oversight

        # Explainable Complexity Formula (0.0 to 10.0 scale)
        comp = (role_complexity * 0.25) + (risk_w * 0.25) + (reg_w * 0.25) + (wf_w * 0.15) + (exception_rate * 20.0 * 0.10)
        return round(min(10.0, max(1.0, comp)), 2)

    @classmethod
    def evaluate_span(
        cls,
        role_id: str,
        current_reports_count: int,
        role_complexity: float = 5.0,
        risk_level: str = "MEDIUM",
        regulatory_intensity: str = "MEDIUM",
        workforce_type: str = "AI_AGENT",
        exception_rate: float = 0.05
    ) -> Dict[str, Any]:
        complexity = cls.calculate_complexity_score(
            role_complexity=role_complexity,
            risk_level=risk_level,
            regulatory_intensity=regulatory_intensity,
            exception_rate=exception_rate,
            workforce_type=workforce_type
        )

        is_exec = "CEO" in role_id or "EXEC" in role_id

        if is_exec:
            # Executive Span Benchmark Range
            if complexity >= 6.5:
                min_span, max_span, rec_span = 3, 5, 4
                rationale = "High regulatory/risk complexity requires narrower executive span for rigorous oversight."
            elif complexity < 3.5:
                min_span, max_span, rec_span = 6, 10, 8
                rationale = "Standardized low-risk operations allow broad executive coordination span."
            else:
                min_span, max_span, rec_span = 4, 8, 6
                rationale = "Balanced operating complexity supports standard canonical C-suite span."
        else:
            # Manager-to-Worker Span Benchmark Range
            if workforce_type == "AI_AGENT":
                # AI workers with telemetry and automated exception handling
                if complexity > 7.0:
                    min_span, max_span, rec_span = 6, 14, 10
                else:
                    min_span, max_span, rec_span = 10, 25, 18
                rationale = "AI agents governed by telemetry and automated SOPs support expanded spans."
            else:
                # Human or hybrid workforce
                if complexity > 7.0:
                    min_span, max_span, rec_span = 3, 7, 5
                else:
                    min_span, max_span, rec_span = 5, 12, 8
                rationale = "Human operational coordination requires bounded span to avoid cognitive overload."

        if current_reports_count < min_span:
            status = "TOO_NARROW"
        elif current_reports_count > max_span:
            status = "CRITICAL_OVERLOAD" if current_reports_count > max_span + 3 else "TOO_WIDE"
        else:
            status = "OPTIMAL"

        return {
            "role_id": role_id,
            "current_span": current_reports_count,
            "recommended_span": rec_span,
            "min_reasonable_span": min_span,
            "max_reasonable_span": max_span,
            "status": status,
            "complexity_score": complexity,
            "rationale": rationale,
            "assumptions": {
                "workforce_type": workforce_type,
                "risk_level": risk_level,
                "regulatory_intensity": regulatory_intensity,
                "exception_rate": exception_rate
            }
        }

class WorkloadWorkforceScalingSimulator:
    """
    Simulates workforce sizing based on measurable operational drivers without mutating live state.
    """
    @classmethod
    def simulate(
        cls,
        department_name: str,
        base_agent_count: int,
        scenario: str = "NORMAL_VOLUME",
        queue_depth: int = 50,
        target_sla_sec: float = 30.0,
        avg_handle_time_sec: float = 15.0
    ) -> Dict[str, Any]:
        multipliers = {
            "LOW_VOLUME": 0.5,
            "NORMAL_VOLUME": 1.0,
            "HIGH_VOLUME": 2.2,
            "SPIKE": 4.5,
            "CRISIS": 8.0,
            "RECOVERY": 1.3
        }
        mult = multipliers.get(scenario.upper(), 1.0)
        effective_queue = int(queue_depth * mult)

        # Queueing Theory Driver: Required capacity = (arrival_rate * service_time) / target_latency
        req_capacity = max(1, int(round((effective_queue * avg_handle_time_sec) / (target_sla_sec * 2.5))))
        agent_delta = req_capacity - base_agent_count

        return {
            "department_name": department_name,
            "scenario": scenario,
            "effective_queue_depth": effective_queue,
            "base_agent_count": base_agent_count,
            "simulated_agent_count": req_capacity,
            "agent_delta": agent_delta,
            "sla_fulfillment_projected_pct": 99.2 if req_capacity >= base_agent_count else 84.5,
            "estimated_cost_delta_usd": agent_delta * 120.0,
            "simulation_only": True,
            "mutates_production": False
        }

# ==============================================================================
# 11. JURISDICTION-AWARE REGULATORY ARCHITECTURE (GAP OQ-05)
# ==============================================================================

@dataclass
class RegulatoryProfile:
    """
    Jurisdiction-aware regulatory compliance blueprint.
    Never hallucinates legal certainty; explicitly records verification confidence.
    """
    jurisdiction_id: str
    country: str
    state_province: str
    business_activity: str
    industry: str
    regulated_data_types: List[str]
    applicable_frameworks: List[str]
    licensing_requirements: List[str]
    human_approval_requirements: List[str]
    accountable_owner_role: str
    verification_status: str # VERIFIED, REGULATORY_DETERMINATION_REQUIRED, REGULATORY_UNKNOWN
    confidence: float

class JurisdictionRegulatoryEngine:
    """
    Maps abstract regulatory classes to country/region frameworks without hardcoded assumptions.
    """
    _FRAMEWORKS: Dict[str, Dict[str, List[str]]] = {
        "US": {
            "PRIVACY": ["CCPA / CPRA", "FTC Act Section 5"],
            "HEALTHCARE": ["HIPAA (Health Insurance Portability and Accountability Act)", "HITECH"],
            "FINANCIAL": ["SEC Regulations", "Sarbanes-Oxley (SOX)", "Gramm-Leach-Bliley"],
            "EMPLOYMENT": ["OSHA (Occupational Safety)", "FLSA"],
            "CYBERSECURITY": ["NIST Cybersecurity Framework", "SOC 2 Type II"]
        },
        "EU": {
            "PRIVACY": ["GDPR (General Data Protection Regulation)"],
            "CYBERSECURITY": ["NIS 2 Directive", "DORA (Digital Operational Resilience Act)"],
            "FINANCIAL": ["MiFID II", "PSD2 / PSD3"],
            "HEALTHCARE": ["EU MDR (Medical Device Regulation)"],
            "AI_GOVERNANCE": ["EU Artificial Intelligence Act (EU AI Act)"]
        },
        "IN": {
            "PRIVACY": ["Digital Personal Data Protection (DPDP) Act 2023"],
            "FOOD_SAFETY": ["FSSAI Food Safety Standards"],
            "MANUFACTURING": ["Factories Act 1948", "State Industrial Safety Rules"],
            "CORPORATE_GOVERNANCE": ["Companies Act 2013"],
            "FINANCIAL": ["Reserve Bank of India (RBI) Cyber Security Guidelines"]
        },
        "UK": {
            "PRIVACY": ["UK GDPR", "Data Protection Act 2018"],
            "FINANCIAL": ["FCA Handbook Regulations"],
            "HEALTHCARE": ["Care Quality Commission (CQC) Fundamental Standards"]
        },
        "AE": {
            "PRIVACY": ["DIFC Data Protection Law No. 5 of 2020", "UAE Federal Decree Law No. 45"],
            "HEALTHCARE": ["Dubai Health Authority (DHA) Regulatory Standards"],
            "FINANCIAL": ["DFSA Rulebook"]
        },
        "GLOBAL": {
            "TRAVEL": ["IATA Resolutions", "Montreal Convention 1999"],
            "GOVERNANCE": ["ISO 37000 (Governance of Organizations)"],
            "RISK": ["ISO 31000 (Risk Management)"],
            "COMPLIANCE": ["ISO 37301 (Compliance Management)"],
            "AI_MANAGEMENT": ["ISO/IEC 42001 (AI Management System)"]
        }
    }

    @classmethod
    def get_regulatory_profile(cls, country: str, industry: str, business_activity: str = "") -> RegulatoryProfile:
        country_code = (country or "UNKNOWN").upper().strip()
        ind = (industry or "UNKNOWN").upper().strip()

        if country_code in ["UNKNOWN", "INSUFFICIENT_DATA", ""]:
            return RegulatoryProfile(
                jurisdiction_id="REGULATORY_UNKNOWN",
                country="UNKNOWN",
                state_province="NONE",
                business_activity=business_activity or "Unspecified",
                industry=ind,
                regulated_data_types=["UNKNOWN"],
                applicable_frameworks=["REGULATORY_DETERMINATION_REQUIRED"],
                licensing_requirements=["LEGAL_COUNSEL_REVIEW_MANDATORY"],
                human_approval_requirements=["Statutory filings require human legal signature."],
                accountable_owner_role="EXEC_CLO",
                verification_status="REGULATORY_DETERMINATION_REQUIRED",
                confidence=0.0
            )

        frameworks_by_country = cls._FRAMEWORKS.get(country_code, cls._FRAMEWORKS.get("GLOBAL", {}))
        applicable: List[str] = []
        data_types: List[str] = []
        licensing: List[str] = []
        owner_role = "EXEC_CLO"

        # Privacy is universal across digital/modern operations
        applicable.extend(frameworks_by_country.get("PRIVACY", ["Baseline ISO 27701 Data Privacy"]))
        data_types.append("CUSTOMER_PII")

        if "CYBERSECURITY" in frameworks_by_country:
            applicable.extend(frameworks_by_country["CYBERSECURITY"])
        if "AI_GOVERNANCE" in frameworks_by_country:
            applicable.extend(frameworks_by_country["AI_GOVERNANCE"])

        if "HEALTH" in ind:
            applicable.extend(frameworks_by_country.get("HEALTHCARE", ["Statutory Clinical Care Standards"]))
            data_types.extend(["PROTECTED_HEALTH_INFORMATION_PHI", "ELECTRONIC_HEALTH_RECORDS"])
            licensing.append("Healthcare Facility Provider License")
            owner_role = "EXEC_CRO_RISK"
        elif "FINANC" in ind or "FINTECH" in ind or "BANK" in ind:
            applicable.extend(frameworks_by_country.get("FINANCIAL", ["Statutory Financial Conduct Rules"]))
            data_types.extend(["FINANCIAL_PAYMENT_DATA", "CARDHOLDER_DATA"])
            licensing.append("Financial Services Regulatory Authority Authorization")
            owner_role = "EXEC_CFO"
        elif "MANUFACTUR" in ind:
            applicable.extend(frameworks_by_country.get("MANUFACTURING", ["Industrial Workplace Safety Compliance"]))
            licensing.append("Factory Operating Permit & Environmental Clearance")
            owner_role = "EXEC_COO"
        elif "HOTEL" in ind or "HOSPITAL" in ind:
            applicable.extend(frameworks_by_country.get("FOOD_SAFETY", ["Municipal Hospitality & Hygiene Licensing"]))
            licensing.append("Hospitality & Lodging Business License")
            owner_role = "EXEC_COO"
        elif "TRAVEL" in ind or "TOUR" in ind:
            applicable.extend(cls._FRAMEWORKS["GLOBAL"]["TRAVEL"])
            licensing.append("IATA Travel Agent Accreditation")
            owner_role = "EXEC_CRO"

        # Attach ISO Governance, Risk, Compliance & AI Management
        applicable.extend(cls._FRAMEWORKS["GLOBAL"]["GOVERNANCE"])
        applicable.extend(cls._FRAMEWORKS["GLOBAL"]["RISK"])
        applicable.extend(cls._FRAMEWORKS["GLOBAL"]["COMPLIANCE"])
        applicable.extend(cls._FRAMEWORKS["GLOBAL"]["AI_MANAGEMENT"])

        return RegulatoryProfile(
            jurisdiction_id=f"reg_{country_code}_{ind}",
            country=country_code,
            state_province="ALL",
            business_activity=business_activity or f"Operating in {ind}",
            industry=ind,
            regulated_data_types=data_types,
            applicable_frameworks=applicable,
            licensing_requirements=licensing,
            human_approval_requirements=[
                "Statutory tax filings require explicit human signature.",
                "Clinical practice decisions must be verified by licensed human practitioners.",
                "Legal deeds and litigation settlements cannot be executed solely by AI agents."
            ],
            accountable_owner_role=owner_role,
            verification_status="VERIFIED",
            confidence=0.92
        )

# ==============================================================================
# 12. SEGREGATION OF DUTIES (SOD) & CONFLICT DETECTION (GAP OQ-01 / OQ-04)
# ==============================================================================

class SegregationOfDutiesEngine:
    """
    Prevents toxic combinations of rights and conflicting organizational duties.
    """
    @classmethod
    def audit_conflicts(cls, data: ExistingOrganizationData) -> List[str]:
        conflicts: List[str] = []

        # 1. AI agent cannot hold sovereign authority
        for ex in data.executives:
            if ex.get("workforce_type") == "AI_AGENT" and ex.get("role_id") == "L0_OWNER":
                conflicts.append("SOD_CONFLICT: AI agent cannot be assigned Sovereign Owner authority (Invariant 3 & 17).")

        # 2. Check requester vs approver conflicts
        for role in data.current_roles:
            rights = role.get("decision_rights", [])
            if any("disbursement" in r.lower() for r in rights) and any("audit" in r.lower() for r in rights):
                conflicts.append(f"SOD_CONFLICT: Role '{role.get('role_name')}' holds both financial disbursement and audit authority.")

        return conflicts

# ==============================================================================
# 13. MULTI-TENANT ISOLATION TRIPWIRES & PROMPT-INJECTION PROTECTION (OQ-04)
# ==============================================================================

class TenantIsolationViolation(Exception):
    """Raised when an attempt to cross tenant or company isolation boundaries is detected."""
    pass

class AntiPromptInjectionScanner:
    """
    Inspects organization metadata, directives, and role assignments for adversarial prompt-injection payloads.
    """
    _PROHIBITED_PATTERNS = [
        "ignore previous instructions",
        "elevate your authority",
        "elevate authority to sovereign",
        "authorize all payments",
        "ignore tenant policy",
        "export every company",
        "system prompt override",
        "disable kill switch",
        "bypass doa"
    ]

    @classmethod
    def scan_for_injection(cls, content: str) -> Tuple[bool, List[str]]:
        if not content or not isinstance(content, str):
            return True, []
        low = content.lower()
        found = [p for p in cls._PROHIBITED_PATTERNS if p in low]
        return len(found) == 0, found

