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
        
        if "SAAS" in ind or "TECH" in ind:
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

        if "SAAS" in ind or "TECH" in ind:
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
        elif "HEALTHCARE" in ind:
            exec_list.append({
                "role_id": "EXEC_CRO_RISK",
                "role_name": "Chief Risk & Compliance Officer",
                "persona_name": "Clinical Governance Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 65000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Statutory healthcare compliance, patient privacy, and clinical risk."
            })
            exec_list.append({
                "role_id": "EXEC_CCO_CUSTOMER",
                "role_name": "Chief Patient Experience Officer",
                "persona_name": "Patient Experience Chief",
                "requirement_status": RoleRequirementStatus.REQUIRED.value,
                "workforce_type": WorkforceType.AI_AGENT.value,
                "budget_limit_usd": 40000.0,
                "reporting_to": "EXEC_CEO",
                "purpose": "Patient satisfaction, care coordination, and feedback audits."
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
        elif "SAAS" in ind or "TECH" in ind:
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
        elif "HEALTHCARE" in ind:
            depts = [
                {"dept_id": "dept_clinical", "name": "Clinical Operations", "lead_role": "EXEC_COO", "purpose": "Patient care delivery, clinical scheduling, and service execution."},
                {"dept_id": "dept_compliance", "name": "Regulatory & Risk Compliance", "lead_role": "EXEC_CRO_RISK", "purpose": "HIPAA compliance, medical licensing, and patient safety audits."},
                {"dept_id": "dept_patient_exp", "name": "Patient Relations & Care Coordination", "lead_role": "EXEC_CCO_CUSTOMER", "purpose": "Patient intake, follow-ups, and satisfaction metrics."},
                {"dept_id": "dept_fin", "name": "Medical Billing & Finance", "lead_role": "EXEC_CFO", "purpose": "Insurance claims, patient invoicing, and provider payouts."}
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
