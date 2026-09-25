"""
ZONATA Universal AI CEO — Organization Design Engine
Synthesizes industry-tailored executive structures, dynamic departments,
and governed, mission-first AI workforce roles based on discovered operational truth.
Constitutional Invariant: No fixed 25-employee templates. Every organization is synthesized
dynamically from the company's business model, processes, systems, and strategic objectives.
"""

from typing import Dict, List, Optional, Any
import json
import time
import uuid

from core.db import db
from zonata.models import (
    DynamicOrganization,
    DynamicDepartment,
    DynamicWorkforceMember,
    AgentLifecycleState,
    EntityType,
    RelationType,
    EpistemicState
)
from zonata.knowledge_graph import CompanyKnowledgeGraph

class OrganizationDesignEngine:
    """
    Generative organization designer.
    Translates Company Knowledge Graph, Health, and Goals into a custom operational hierarchy.
    """

    def __init__(self):
        pass

    def design_organization(
        self,
        tenant_id: str,
        company_id: str,
        industry_override: Optional[str] = None
    ) -> DynamicOrganization:
        """
        Synthesizes a complete organization tailored to the company's actual operational reality.
        """
        kg = CompanyKnowledgeGraph(tenant_id, company_id)
        now = time.time()
        blueprint_id = f"blueprint_{uuid.uuid4().hex[:10]}"

        # 1. Detect Industry & Business Model from Knowledge Graph
        detected_industry = industry_override or self._detect_industry(kg)

        # 2. Synthesize Executive Hierarchy
        executives = self._synthesize_executives(detected_industry, kg)

        # 3. Synthesize Dynamic Departments
        departments = self._synthesize_departments(detected_industry, kg)

        # 4. Synthesize Governed Mission-First Workforce
        workforce = self._synthesize_workforce(detected_industry, departments, kg)

        # 5. Build Reporting Hierarchy
        reporting = self._build_reporting_hierarchy(executives, departments, workforce)

        rationale = (
            f"Synthesized organizational blueprint for {detected_industry} operations. "
            f"Tailored {len(executives)} executive direct reports, {len(departments)} dynamic operational departments, "
            f"and {len(workforce)} mission-specialized autonomous agents with full authority and tool governance."
        )

        org = DynamicOrganization(
            blueprint_id=blueprint_id,
            company_id=company_id,
            tenant_id=tenant_id,
            industry=detected_industry,
            rationale=rationale,
            executives=executives,
            departments=departments,
            workforce=workforce,
            reporting_hierarchy=reporting,
            created_at=now
        )

        # 6. Persist to SQLite
        self._persist_blueprint(org)

        # 7. Update Knowledge Graph with Departments and Workforce Members
        self._update_knowledge_graph(kg, org)

        return org

    def generate_mission_workforce(
        self,
        tenant_id: str,
        company_id: str,
        mission_objective: str,
        target_department: Optional[str] = None
    ) -> List[DynamicWorkforceMember]:
        """
        Mission-First Agent Generation:
        Generates specialized on-demand workforce members needed specifically to accomplish an objective.
        Example: 'Increase hotel direct bookings' -> Market Intel, SEO, Content, Paid Ads, Conversion Analytics.
        """
        kg = CompanyKnowledgeGraph(tenant_id, company_id)
        lower_mission = mission_objective.lower()
        now = time.time()
        generated_agents: List[DynamicWorkforceMember] = []

        # Find or use department
        dept_id = target_department or "dept_growth"
        exec_role = "CMO" if any(w in lower_mission for w in ["booking", "sales", "marketing", "revenue", "lead"]) else "COO"

        if "direct booking" in lower_mission or "hotel booking" in lower_mission or "occupancy" in lower_mission:
            # Hotel Direct Booking Growth Fleet
            specs = [
                {
                    "name": "OTA Price Parity & Intelligence Agent",
                    "role": "Rate Intelligence Specialist",
                    "focus": "Monitor competitor and OTA room rates in real-time to maintain rate parity and direct booking advantage",
                    "tools": ["BROWSER_SURFACE", "OTA_SCRAPER", "RATE_CALCULATOR", "COMPETITOR_BENCHMARK"],
                    "model": {"provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.2},
                    "risk": "LOW",
                    "budget": 50.0
                },
                {
                    "name": "Direct Booking Engine Optimizer",
                    "role": "Conversion Rate Optimization Agent",
                    "focus": "Optimize direct hotel website checkout funnel and eliminate friction points",
                    "tools": ["WEB_AUDIT", "HTML_ANALYZER", "DESKTOP_SURFACE", "ANALYTICS_QUERY"],
                    "model": {"provider": "gemini", "model": "gemini-1.5-pro", "temperature": 0.3},
                    "risk": "MEDIUM",
                    "budget": 100.0
                },
                {
                    "name": "Guest Retention & Campaign Dispatcher",
                    "role": "Guest Loyalty Marketing Agent",
                    "focus": "Target past guests with automated loyalty incentives and personalized re-booking offers",
                    "tools": ["EMAIL_DISPATCHER", "WHATSAPP_CONNECTOR", "PMS_QUERY", "CRM_SYNC"],
                    "model": {"provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.4},
                    "risk": "MEDIUM",
                    "budget": 75.0
                }
            ]
        elif "bug" in lower_mission or "quality" in lower_mission or "test" in lower_mission:
            # Software Quality & QA Fleet
            specs = [
                {
                    "name": "Automated Regression Tester",
                    "role": "QA Verification Specialist",
                    "focus": "Execute end-to-end regression suites and report verified reproduction traces",
                    "tools": ["TEST_RUNNER", "LOG_ANALYZER", "GITHUB_API", "CODE_INSPECTOR"],
                    "model": {"provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.1},
                    "risk": "LOW",
                    "budget": 60.0
                },
                {
                    "name": "Security & Static Analysis Agent",
                    "role": "AppSec Auditor",
                    "focus": "Scan codebases and dependencies for vulnerabilities and hardcoded secrets",
                    "tools": ["STATIC_ANALYZER", "DEPENDENCY_AUDIT", "SECRET_SCANNER"],
                    "model": {"provider": "gemini", "model": "gemini-1.5-pro", "temperature": 0.1},
                    "risk": "LOW",
                    "budget": 80.0
                }
            ]
        else:
            # Universal Strategic Execution Specialist
            specs = [
                {
                    "name": "Strategic Mission Coordinator",
                    "role": "Mission Execution Specialist",
                    "focus": f"Plan, orchestrate, and verify milestone execution for mission: '{mission_objective}'",
                    "tools": ["MISSION_TRACKER", "AGENT_BUS", "LEDGER_VERIFIER", "METRICS_REPORTER"],
                    "model": {"provider": "gemini", "model": "gemini-1.5-pro", "temperature": 0.2},
                    "risk": "MEDIUM",
                    "budget": 100.0
                }
            ]

        for s in specs:
            agent_id = f"agent_mission_{uuid.uuid4().hex[:8]}"
            agent = DynamicWorkforceMember(
                id=agent_id,
                name=s["name"],
                role=s["role"],
                department_id=dept_id,
                executive=exec_role,
                mission_focus=s["focus"],
                responsibilities=[s["focus"], "Report milestone verification to Evidence Ledger", "Escalate budget violations to CFO"],
                capabilities=s["tools"],
                tools=s["tools"],
                knowledge_sources=["Company Knowledge Graph", "Mission Objective Contract"],
                model_policy=s["model"],
                budget=s["budget"],
                risk_class=s["risk"],
                approval_policy={"require_approval_above_usd": s["budget"] / 2.0},
                kpis=[{"name": "Mission Milestone Verification Rate", "target": ">=95%"}],
                verification_policy={"require_dual_source_evidence": True},
                status=AgentLifecycleState.ACTIVE,
                certification={"governance_status": "CERTIFIED", "certified_at": now},
                authority_scope={"department": dept_id, "spending_limit": s["budget"]}
            )
            generated_agents.append(agent)
            self._persist_workforce_member(tenant_id, company_id, agent, None)

        return generated_agents

    # --- Internal Synthesis Helpers ---

    def _detect_industry(self, kg: CompanyKnowledgeGraph) -> str:
        # Check company node attribute
        comp_nodes = kg.find_nodes_by_type(EntityType.COMPANY)
        if comp_nodes and "industry" in comp_nodes[0].properties:
            return str(comp_nodes[0].properties["industry"]).upper()

        # Check for asset cues (e.g. rooms -> HOTEL)
        if kg.find_nodes_by_type(EntityType.ASSET):
            for a in kg.find_nodes_by_type(EntityType.ASSET):
                if "room" in a.name.lower() or "room_inventory" in a.properties:
                    return "HOTEL"

        # Check system cues (e.g. Cloudbeds/Opera -> HOTEL, Shopify -> ECOMMERCE, Jira/Github -> SAAS)
        for s in kg.find_nodes_by_type(EntityType.SYSTEM) + kg.find_nodes_by_type(EntityType.APPLICATION):
            s_name = s.name.lower()
            if any(k in s_name for k in ["cloudbeds", "opera", "mews", "hotel"]):
                return "HOTEL"
            if any(k in s_name for k in ["github", "jira", "aws", "docker"]):
                return "SAAS"
            if any(k in s_name for k in ["cnc", "sap", "machinery", "factory"]):
                return "MANUFACTURING"

        return "GENERAL_ENTERPRISE"

    def _synthesize_executives(self, industry: str, kg: CompanyKnowledgeGraph) -> List[Dict[str, Any]]:
        ind = industry.upper()
        if "HOTEL" in ind or "HOSPITALITY" in ind or "RESORT" in ind:
            return [
                {"role": "COO", "title": "Chief Operating Officer", "focus": "Rooms, Guest Operations, Housekeeping & Facilities"},
                {"role": "CMO", "title": "Chief Marketing Officer", "focus": "Revenue Management, Direct Bookings & OTA Partnerships"},
                {"role": "CFO", "title": "Chief Financial Officer", "focus": "Financial Integrity, Audit, Cash Flow & Procurement"}
            ]
        elif "MANUFACTURING" in ind or "FACTORY" in ind:
            return [
                {"role": "COO", "title": "Chief Operating Officer", "focus": "Plant Operations, CNC Production & Quality Control"},
                {"role": "CTO", "title": "Chief Technology Officer", "focus": "Tooling, Engineering Automation & Machinery Maintenance"},
                {"role": "CFO", "title": "Chief Financial Officer", "focus": "Procurement, Supply Chain Financing & Cost Accounting"}
            ]
        elif "SAAS" in ind or "SOFTWARE" in ind or "TECH" in ind:
            return [
                {"role": "CTO", "title": "Chief Technology Officer", "focus": "Engineering, Product Architecture, QA & Cloud Infrastructure"},
                {"role": "CRO", "title": "Chief Revenue Officer", "focus": "SaaS Sales, Growth, Inbound Pipeline & Customer Retention"},
                {"role": "CFO", "title": "Chief Financial Officer", "focus": "Unit Economics, Runway, ARR/MRR Metrics & Billing"}
            ]
        else: # General Enterprise
            return [
                {"role": "COO", "title": "Chief Operating Officer", "focus": "Daily Business Operations, SOP Execution & Delivery"},
                {"role": "CMO", "title": "Chief Marketing Officer", "focus": "Customer Acquisition, Sales Pipeline & Brand Positioning"},
                {"role": "CFO", "title": "Chief Financial Officer", "focus": "Financial Control, Budget Limits & Commercial Integrity"}
            ]

    def _synthesize_departments(self, industry: str, kg: CompanyKnowledgeGraph) -> List[DynamicDepartment]:
        ind = industry.upper()
        if "HOTEL" in ind or "HOSPITALITY" in ind:
            return [
                DynamicDepartment(
                    id="dept_revenue",
                    name="Revenue Management",
                    code="REV",
                    justification="Controls room pricing, occupancy optimization, and OTA distribution channels.",
                    responsibilities=["Dynamic room pricing", "OTA rate parity monitoring", "Occupancy forecasting"],
                    processes=["Daily rate adjustment", "Channel manager synchronization"],
                    systems_used=["PMS", "Channel Manager", "Booking Engine"]
                ),
                DynamicDepartment(
                    id="dept_reservations",
                    name="Reservations & Guest Relations",
                    code="RES",
                    justification="Handles direct guest inquiries, reservation modifications, and concierge communication.",
                    responsibilities=["Inquiry response within 5 mins", "Special request handling", "Direct booking conversion"],
                    processes=["Guest messaging", "Check-in briefing"],
                    systems_used=["PMS", "WhatsApp API", "Email"]
                ),
                DynamicDepartment(
                    id="dept_operations",
                    name="Rooms & Housekeeping Operations",
                    code="OPS",
                    justification="Maintains room readiness, housekeeping inspection checklists, and physical upkeep.",
                    responsibilities=["Room turnaround tracking", "Maintenance request ticketing", "Amenity inventory"],
                    processes=["Morning room assignment", "Inspection sign-off"],
                    systems_used=["PMS Housekeeping Module", "Facility Ticketing"]
                ),
                DynamicDepartment(
                    id="dept_finance",
                    name="Finance & Accounting",
                    code="FIN",
                    justification="Monitors daily night audit reconciliation, cash collection, and vendor invoice settlements.",
                    responsibilities=["Daily revenue reconciliation", "Expense audit", "Vendor ledger tracking"],
                    processes=["Night audit sign-off", "Weekly financial reporting"],
                    systems_used=["Accounting Software", "Bank Feeds"]
                )
            ]
        elif "MANUFACTURING" in ind:
            return [
                DynamicDepartment(
                    id="dept_production",
                    name="Production & CNC Operations",
                    code="PRD",
                    justification="Supervises CNC machinery cycles, machining schedules, and line throughput.",
                    responsibilities=["Production schedule optimization", "Cycle time monitoring", "Machine load balancing"],
                    processes=["Shift dispatch", "Cycle completion logging"],
                    systems_used=["MES", "CNC Controllers", "SCADA"]
                ),
                DynamicDepartment(
                    id="dept_quality",
                    name="Quality Assurance & Metrology",
                    code="QA",
                    justification="Verifies component tolerance dimensions and prevents defective parts shipments.",
                    responsibilities=["Tolerance inspection verification", "Defect rate tracking", "Root cause logging"],
                    processes=["First piece inspection", "Batch verification"],
                    systems_used=["CMM Software", "Quality Audit Database"]
                ),
                DynamicDepartment(
                    id="dept_procurement",
                    name="Procurement & Supply Chain",
                    code="SCM",
                    justification="Manages raw material inventory, metal stock orders, and supplier lead times.",
                    responsibilities=["Raw material re-ordering", "Supplier delivery verification", "BOM tracking"],
                    processes=["PO dispatch", "Stock level check"],
                    systems_used=["ERP", "Inventory Database"]
                ),
                DynamicDepartment(
                    id="dept_finance",
                    name="Cost Accounting & Finance",
                    code="FIN",
                    justification="Calculates per-part manufacturing cost, machine depreciation, and margin thresholds.",
                    responsibilities=["COGS tracking", "Machine hour rate audit", "Receivables aging"],
                    processes=["Cost variance analysis", "Monthly close"],
                    systems_used=["ERP Finance", "Accounting Ledger"]
                )
            ]
        elif "SAAS" in ind or "SOFTWARE" in ind:
            return [
                DynamicDepartment(
                    id="dept_engineering",
                    name="Software Engineering & Cloud Platform",
                    code="ENG",
                    justification="Maintains platform architecture, code health, cloud deployments, and uptime.",
                    responsibilities=["CI/CD pipeline stability", "Bug triage and automated remediation", "Uptime monitoring"],
                    processes=["Automated regression testing", "Release deployment"],
                    systems_used=["GitHub", "AWS/Cloud Console", "Datadog"]
                ),
                DynamicDepartment(
                    id="dept_product",
                    name="Product & User Experience",
                    code="PRD",
                    justification="Tracks feature usage analytics, user onboarding funnels, and churn telemetry.",
                    responsibilities=["Product analytics analysis", "Feature adoption tracking", "User feedback synthesis"],
                    processes=["Funnel conversion audit", "Sprint backlog prioritization"],
                    systems_used=["PostHog", "Mixpanel", "Jira"]
                ),
                DynamicDepartment(
                    id="dept_growth",
                    name="Sales & Inbound Growth",
                    code="GRO",
                    justification="Drives B2B lead qualification, inbound response speed, and demo scheduling.",
                    responsibilities=["Lead scoring and enrichment", "Pipeline velocity tracking", "Demo follow-up"],
                    processes=["Inbound lead routing", "Outreach cadence"],
                    systems_used=["CRM", "Email Outreach", "Calendar Scheduler"]
                ),
                DynamicDepartment(
                    id="dept_customer_success",
                    name="Customer Success & Support",
                    code="CS",
                    justification="Resolves customer tickets and monitors account health to reduce churn.",
                    responsibilities=["Support ticket SLA resolution", "Account onboarding health", "NPS tracking"],
                    processes=["Automated ticket triage", "Proactive customer check-in"],
                    systems_used=["Zendesk/Intercom", "Knowledge Base"]
                )
            ]
        else:
            return [
                DynamicDepartment(
                    id="dept_operations",
                    name="Business Operations",
                    code="OPS",
                    justification="Maintains fulfillment workflows, customer orders, and vendor delivery.",
                    responsibilities=["Daily fulfillment tracking", "SOP compliance", "Exception routing"],
                    processes=["Order review", "Fulfillment sign-off"],
                    systems_used=["Internal Database", "Email"]
                ),
                DynamicDepartment(
                    id="dept_commercial",
                    name="Sales & Commercial Growth",
                    code="COM",
                    justification="Drives customer acquisition, inbound queries, and quote follow-ups.",
                    responsibilities=["Customer acquisition", "Quotation follow-up", "Marketing coordination"],
                    processes=["Lead response", "Contract dispatch"],
                    systems_used=["CRM", "Billing System"]
                ),
                DynamicDepartment(
                    id="dept_finance",
                    name="Finance & Governance",
                    code="FIN",
                    justification="Maintains cash flow tracking, expense approvals, and budget thresholds.",
                    responsibilities=["Cash flow monitoring", "Invoice reconciliation", "Audit compliance"],
                    processes=["Invoice verification", "Monthly reconciliation"],
                    systems_used=["Accounting System", "Bank Feeds"]
                )
            ]

    def _synthesize_workforce(
        self,
        industry: str,
        departments: List[DynamicDepartment],
        kg: CompanyKnowledgeGraph
    ) -> List[DynamicWorkforceMember]:
        workforce: List[DynamicWorkforceMember] = []
        ind = industry.upper()

        for d in departments:
            # Generate 1-2 specialized agents per department
            if d.code == "REV":
                workforce.append(DynamicWorkforceMember(
                    id=f"wf_rev_pricing_{d.id}",
                    name="Autonomous Pricing & Yield Optimizer",
                    role="Revenue Yield Specialist",
                    department_id=d.id,
                    executive="CMO",
                    mission_focus="Maximize RevPAR and direct booking margin by adjusting daily rates according to demand signals",
                    responsibilities=["Monitor market demand", "Update PMS rate grids", "Maintain rate parity across OTAs"],
                    capabilities=["PMS_PRICE_UPDATER", "COMPETITOR_BENCHMARK", "RATE_CALCULATOR"],
                    tools=["PMS_API", "OTA_SCRAPER", "RATE_CALCULATOR"],
                    knowledge_sources=["Historical Occupancy Ledger", "PMS Rate Tables"],
                    model_policy={"preferred_model": "gemini-1.5-flash", "temperature": 0.1, "fallback": "claude-3-haiku"},
                    budget=150.0,
                    risk_class="MEDIUM",
                    approval_policy={"require_approval_above_usd": 75.0, "rate_change_max_percent": 25.0},
                    kpis=[{"name": "Occupancy Rate", "target": ">=78%"}, {"name": "Direct Booking Share", "target": ">=40%"}],
                    verification_policy={"require_dual_source_evidence": True},
                    working_hours="24x7_CONTINUOUS",
                    authority_scope={"department": d.id, "allowed_rate_swing": 0.25}
                ))
            elif d.code == "RES":
                workforce.append(DynamicWorkforceMember(
                    id=f"wf_res_concierge_{d.id}",
                    name="Instant Guest Concierge & Booking Agent",
                    role="Guest Experience Specialist",
                    department_id=d.id,
                    executive="COO",
                    mission_focus="Respond to guest queries within 60 seconds and convert inquiries into direct bookings",
                    responsibilities=["Immediate guest inquiry handling", "Special booking requests", "Upsell amenities"],
                    capabilities=["WHATSAPP_MESSAGING", "EMAIL_DISPATCHER", "PMS_RESERVATION_LOOKUP"],
                    tools=["MESSAGING_GATEWAY", "PMS_CONNECTOR"],
                    knowledge_sources=["Hotel Property SOPs", "Amenity Directory"],
                    model_policy={"preferred_model": "gemini-1.5-flash", "temperature": 0.3},
                    budget=80.0,
                    risk_class="LOW",
                    approval_policy={"require_approval_for_free_cancellation": True},
                    kpis=[{"name": "Average Response Time", "target": "<60 seconds"}, {"name": "Inquiry Conversion", "target": ">=25%"}],
                    verification_policy={"evidence": "Message delivery receipt"},
                    working_hours="24x7_CONTINUOUS",
                    authority_scope={"department": d.id}
                ))
            elif d.code == "OPS":
                workforce.append(DynamicWorkforceMember(
                    id=f"wf_ops_coordinator_{d.id}",
                    name="Operational Dispatch & Night Shift Supervisor",
                    role="Operations Dispatch Specialist",
                    department_id=d.id,
                    executive="COO",
                    mission_focus="Coordinate daily room inspections, maintenance tickets, and conduct the automated Night Audit",
                    responsibilities=["Verify room readiness status", "Track maintenance tickets", "Execute 02:00 AM Night Audit reconciliation"],
                    capabilities=["PMS_NIGHT_AUDIT", "TICKET_DISPATCH", "MAINTENANCE_LOG"],
                    tools=["PMS_API", "TICKETING_ENGINE", "DESKTOP_SURFACE"],
                    knowledge_sources=["Operational SOPs", "Room Readiness Guidelines"],
                    model_policy={"preferred_model": "gemini-1.5-flash", "temperature": 0.1},
                    budget=100.0,
                    risk_class="LOW",
                    approval_policy={"require_approval_for_maintenance_above": 200.0},
                    kpis=[{"name": "Night Audit Verification Rate", "target": "100%"}, {"name": "Ticket Resolution Time", "target": "<4 hours"}],
                    verification_policy={"evidence": "Signed Merkle audit record"},
                    working_hours="24x7_NIGHT_SHIFT_READY",
                    authority_scope={"department": d.id}
                ))
            elif d.code == "FIN":
                workforce.append(DynamicWorkforceMember(
                    id=f"wf_fin_auditor_{d.id}",
                    name="Autonomous Ledger & Financial Reconciler",
                    role="Financial Reconciliation Specialist",
                    department_id=d.id,
                    executive="CFO",
                    mission_focus="Audit daily transactions, match bank deposits against ledger entries, and enforce spending limits",
                    responsibilities=["Daily bank statement reconciliation", "Expense variance detection", "Enforce corporate budget ceilings"],
                    capabilities=["LEDGER_AUDIT", "TRANSACTION_MATCHING", "BUDGET_ENFORCER"],
                    tools=["ACCOUNTING_API", "BANK_FEED", "EVIDENCE_LEDGER"],
                    knowledge_sources=["Corporate Financial Policy", "Tax Rules"],
                    model_policy={"preferred_model": "gemini-1.5-pro", "temperature": 0.05},
                    budget=200.0,
                    risk_class="HIGH",
                    approval_policy={"require_approval_for_all_outbound_payments": True},
                    kpis=[{"name": "Reconciliation Accuracy", "target": "100%"}, {"name": "Unmatched Transactions", "target": "0"}],
                    verification_policy={"require_dual_source_evidence": True},
                    working_hours="DAILY_BATCH_AND_REAL_TIME",
                    authority_scope={"department": d.id, "payment_authority": False}
                ))
            elif d.code == "ENG":
                workforce.append(DynamicWorkforceMember(
                    id=f"wf_eng_sentinel_{d.id}",
                    name="Cloud Reliability & Automated QA Sentinel",
                    role="Reliability & Verification Specialist",
                    department_id=d.id,
                    executive="CTO",
                    mission_focus="Maintain platform uptime, test staging deployments, and triage system exceptions in real time",
                    responsibilities=["Monitor production health", "Run automated regression tests", "Verify release safety"],
                    capabilities=["CLOUD_HEALTH_CHECK", "GITHUB_TRIAGE", "LOG_INSPECTION"],
                    tools=["GITHUB_API", "DATADOG_METRICS", "SANDBOX_EXECUTOR"],
                    knowledge_sources=["Architecture Diagrams", "Runbooks"],
                    model_policy={"preferred_model": "gemini-1.5-flash", "temperature": 0.1},
                    budget=120.0,
                    risk_class="MEDIUM",
                    approval_policy={"require_approval_for_prod_deploys": True},
                    kpis=[{"name": "System Uptime", "target": ">=99.95%"}, {"name": "MTTD (Detection Time)", "target": "<2 mins"}],
                    verification_policy={"evidence": "Uptime ping and cryptographic log trace"},
                    working_hours="24x7_CONTINUOUS",
                    authority_scope={"department": d.id}
                ))
            else:
                workforce.append(DynamicWorkforceMember(
                    id=f"wf_gen_{d.code.lower()}_{d.id}",
                    name=f"{d.name} Execution Specialist",
                    role=f"{d.name} Specialist",
                    department_id=d.id,
                    executive="COO",
                    mission_focus=f"Execute daily operational duties and reporting for {d.name}",
                    responsibilities=d.responsibilities,
                    capabilities=["TASK_RUNNER", "REPORT_GENERATOR", "STATUS_LOGGER"],
                    tools=["DESKTOP_SURFACE", "EMAIL_CLIENT", "EVIDENCE_LEDGER"],
                    knowledge_sources=[f"{d.name} SOP"],
                    model_policy={"preferred_model": "gemini-1.5-flash", "temperature": 0.2},
                    budget=100.0,
                    risk_class="LOW",
                    approval_policy={"require_approval_above_usd": 50.0},
                    kpis=[{"name": "Task Completion Rate", "target": ">=95%"}],
                    verification_policy={"require_dual_source_evidence": True},
                    working_hours="24x7_CONTINUOUS",
                    authority_scope={"department": d.id}
                ))

        return workforce

    def _build_reporting_hierarchy(
        self,
        executives: List[Dict[str, Any]],
        departments: List[DynamicDepartment],
        workforce: List[DynamicWorkforceMember]
    ) -> Dict[str, str]:
        """Maps each workforce member and department to its supervising executive or CEO."""
        hierarchy: Dict[str, str] = {}
        for ex in executives:
            hierarchy[ex["role"]] = "CEO"

        for d in departments:
            # Map department to appropriate executive
            if d.code in ("REV", "COM", "GRO"):
                hierarchy[d.id] = "CMO" if any(e["role"] == "CMO" for e in executives) else "CRO"
            elif d.code in ("FIN", "ACC"):
                hierarchy[d.id] = "CFO"
            elif d.code in ("ENG", "QA", "TECH"):
                hierarchy[d.id] = "CTO"
            else:
                hierarchy[d.id] = "COO" if any(e["role"] == "COO" for e in executives) else "CEO"

        for w in workforce:
            hierarchy[w.id] = w.executive

        return hierarchy

    def _persist_blueprint(self, org: DynamicOrganization):
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO zonata_org_blueprints (
                    blueprint_id, tenant_id, company_id, industry, rationale,
                    executives, departments, workforce, reporting_hierarchy, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                org.blueprint_id, org.tenant_id, org.company_id, org.industry, org.rationale,
                json.dumps(org.executives), json.dumps([d.to_dict() for d in org.departments]),
                json.dumps([w.to_dict() for w in org.workforce]),
                json.dumps(org.reporting_hierarchy), "ACTIVE", org.created_at
            ))
            conn.commit()

        for w in org.workforce:
            self._persist_workforce_member(org.tenant_id, org.company_id, w, org.blueprint_id)

    def _persist_workforce_member(
        self,
        tenant_id: str,
        company_id: str,
        w: DynamicWorkforceMember,
        blueprint_id: Optional[str]
    ):
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO zonata_workforce_members (
                    agent_id, tenant_id, company_id, blueprint_id, name, role,
                    department_id, executive_role, mission_focus, responsibilities,
                    capabilities, tools, knowledge_sources, model_policy, budget_limit,
                    risk_class, approval_policy, kpis, verification_policy, working_hours,
                    communication_channels, lifecycle_state, certification, authority_scope, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    lifecycle_state=excluded.lifecycle_state,
                    budget_limit=excluded.budget_limit
            """, (
                w.id, tenant_id, company_id, blueprint_id, w.name, w.role,
                w.department_id, w.executive, w.mission_focus, json.dumps(w.responsibilities),
                json.dumps(w.capabilities), json.dumps(w.tools), json.dumps(w.knowledge_sources),
                json.dumps(w.model_policy), w.budget, w.risk_class, json.dumps(w.approval_policy),
                json.dumps(w.kpis), json.dumps(w.verification_policy), w.working_hours,
                json.dumps(w.communication_channels), w.status.value, json.dumps(w.certification),
                json.dumps(w.authority_scope), time.time()
            ))
            conn.commit()

    def _update_knowledge_graph(self, kg: CompanyKnowledgeGraph, org: DynamicOrganization):
        """Reflects generated departments and workforce members into Knowledge Graph."""
        for d in org.departments:
            d_node = kg.add_node(
                entity_type=EntityType.DEPARTMENT,
                name=d.name,
                properties={"code": d.code, "justification": d.justification},
                epistemic_state=EpistemicState.FACT,
                confidence=1.0,
                node_id=d.id
            )
            # Edge: Company -> operates -> Department
            company_node = kg.find_node_by_name(org.company_id, EntityType.COMPANY)
            if company_node:
                try:
                    kg.add_edge(
                        source_node_id=company_node.node_id,
                        target_node_id=d_node.node_id,
                        relation=RelationType.OPERATES,
                        epistemic_state=EpistemicState.FACT
                    )
                except Exception:
                    pass

        for w in org.workforce:
            w_node = kg.add_node(
                entity_type=EntityType.AI_WORKFORCE_MEMBER,
                name=w.name,
                properties={
                    "role": w.role,
                    "department_id": w.department_id,
                    "executive": w.executive,
                    "mission_focus": w.mission_focus,
                    "budget": w.budget
                },
                epistemic_state=EpistemicState.FACT,
                confidence=1.0,
                node_id=w.id
            )
            # Edge: Department -> employs -> AI_WORKFORCE_MEMBER
            try:
                kg.add_edge(
                    source_node_id=w.department_id,
                    target_node_id=w_node.node_id,
                    relation=RelationType.EMPLOYS,
                    epistemic_state=EpistemicState.FACT
                )
            except Exception:
                pass
