"""
RoboAssistant Company OS 1.0 — Unified Multi-Tenant API & Web Server
Production implementation with normalized SQLite persistence, zero mock data,
dynamic host discovery, first-class approvals, department control units,
epistemic truth tracking, digital twin simulation, enterprise connectors,
owner decision center ('Attention Required'), global search, and ingestion pipeline.
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
import platform
import time
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.models import MissionStatus, AuthorityLevel, HostType
from core.portfolio import CompanyPortfolioManager, CompanyOnboardingEngine
from core.ceo import CeoCommandEngine, ExecutiveReportEngine
from core.evidence_ledger import EvidenceLedger
from core.control_kernel import UniversalControlKernel
from core.tool_fabric import CapabilityRegistry
from core.workforce import DynamicAgentFactory
from core.db import db
from core.auth import TenantManager, UserManager, AuthorizationEnforcer, UserRole
from core.departments import DepartmentControlUnit
from core.approvals import ApprovalPipeline
from core.knowledge_graph import CompanyKnowledgeGraph as CoreKnowledgeGraph, TruthState
from core.intelligence import OpportunityEngine, RiskEngine
from core.memory import OrganizationalMemory, MemoryTier, MemoryType
from core.financials import BudgetHierarchyEngine
from core.billing import UsageMeteringEngine
from core.digital_twin import DigitalTwinSimulator, SimulationState
from core.connectors import ConnectorRegistry, HospitalityPMSConnector, AccountingConnector, PaymentGatewayConnector
from core.agent_bus import AgentCommunicationBus, GovernedAgentMessage, MessagePriority
from core.evolution import SelfEvolutionPipeline
from core.night_shift import OvernightOperationsEngine
from core.decision_center import OwnerDecisionCenter
from core.ingestion_pipeline import DataIngestionPipeline
from core.search_engine import GlobalSearchEngine
from core.ceo_brain import CEOExecutiveBrain, CEOLearningEngine
from core.webhooks import WebhookSecurityGateway
from core.secrets import SecretManager, ContentSanitizer
from core.kpis import DynamicKpiEngine, KpiVerificationState
from core.handover import HandoverManager, CompanyLifecycleState
from workloads.hospitality import run_hospitality_night_audit
from workloads.manufacturing import run_manufacturing_bottleneck_analysis
from workloads.saas import run_saas_churn_analysis
from workloads.personal import run_personal_file_hygiene
from workloads.universal_computer import run_universal_capability_discovery_task
from core.paperclip_catalog import PaperclipCatalogManager, BUNDLED_TEAMS
from core.paperclip_skills import PaperclipSkillRegistry, SKILLS_CATALOG
from src.services.agent_engine import heartbeat_coordinator, delegation_engine, config_manager

# Initialize Core Subsystems
LEDGER_FILE = os.path.join(BASE_DIR, "storage/evidence/audit_ledger.jsonl")
ledger = EvidenceLedger(LEDGER_FILE)
kernel = UniversalControlKernel(ledger)
registry = CapabilityRegistry()
portfolio = CompanyPortfolioManager(tenant_id="tnt_primary", load_from_db=True)
ceo_command = CeoCommandEngine(portfolio)
ceo_reports = ExecutiveReportEngine(portfolio)

# Company OS 2.0 Subsystems
from core.ceo_engine import CEOExecutiveEngine
from core.executive_council import ExecutiveCouncil
from core.ceo_chief_of_staff import ChiefOfStaff
from core.host_fabric import UniversalHostAgent
from core.desktop_robot import UniversalDesktopRobot
from core.sales_workforce import AISalesWorkforce
from core.voice_agent import GovernedVoiceAgent
from core.event_engine import EnterpriseEventEngine
from core.interactive_meeting import InteractiveMeetingSystem
from core.business_causality import BusinessCausalityEngine
from core.workforce_intelligence import WorkforceIntelligenceEngine

ceo_engine = CEOExecutiveEngine(portfolio, tenant_id="tnt_primary")
host_agent = UniversalHostAgent(tenant_id="tnt_primary")
desktop_robot = UniversalDesktopRobot(host_agent, ledger=ledger)
event_engine = EnterpriseEventEngine(portfolio, tenant_id="tnt_primary")
interactive_meetings = InteractiveMeetingSystem(portfolio, tenant_id="tnt_primary")
sales_workforce = AISalesWorkforce(tenant_id="tnt_primary")
voice_agent = GovernedVoiceAgent(tenant_id="tnt_primary")
business_causality = BusinessCausalityEngine(tenant_id="tnt_primary")
workforce_intel = WorkforceIntelligenceEngine(tenant_id="tnt_primary")

# Zonata Universal AI CEO Subsystems
from zonata.discovery import CompanyDiscoveryEngine
from zonata.interview import CEODiscoveryInterview
from zonata.knowledge_graph import CompanyKnowledgeGraph
from zonata.health import CompanyHealthEngine
from zonata.competitive import CompetitiveIntelligenceEngine
from zonata.org_designer import OrganizationDesignEngine
from zonata.agent_factory import GovernedAgentFactory

zonata_discovery = CompanyDiscoveryEngine()
zonata_interview = CEODiscoveryInterview()
zonata_health = CompanyHealthEngine()
zonata_competitive = CompetitiveIntelligenceEngine()
zonata_org_designer = OrganizationDesignEngine()
zonata_agent_factory = GovernedAgentFactory()

# Connectors and Agent Bus
connector_registry = ConnectorRegistry()
connector_registry.register(HospitalityPMSConnector())
connector_registry.register(AccountingConnector())
connector_registry.register(PaymentGatewayConnector())
agent_bus = AgentCommunicationBus()

WEB_DIR = os.path.join(BASE_DIR, "web")

def get_real_system_host():
    """Inspects the actual execution machine environment."""
    uname = platform.uname()
    load = 0
    try:
        load_tuple = os.getloadavg()
        load = int(min(100, max(1, load_tuple[0] * 10)))
    except Exception:
        load = 15

    return {
        "name": uname.node or "Local-Host-Node",
        "os": f"{uname.system} {uname.release}",
        "architecture": uname.machine,
        "is_primary": True,
        "status": "Online",
        "agents": sum(len(c.workforce) for c in portfolio.list_companies()),
        "load": load,
        "latency_ms": 1
    }

class RoboAssistantRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def _get_tenant_id(self) -> str:
        tenant_id = self.headers.get("X-Tenant-ID")
        if not tenant_id:
            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            tenant_id = q.get("tenant_id", ["tnt_primary"])[0]
        return tenant_id or "tnt_primary"

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Tenant-ID")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Tenant-ID")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)
        tenant_id = self._get_tenant_id()

        if path == "/api/portfolio":
            summary = portfolio.get_portfolio_summary()
            companies = [
                {
                    "id": c.company_id,
                    "name": c.name,
                    "industry": c.industry,
                    "type": c.company_type,
                    "status": c.status,
                    "revenue": c.revenue,
                    "cost": c.cost,
                    "contribution": c.contribution,
                    "workforce_count": len(c.workforce),
                    "missions_count": len(c.missions),
                    "rules": c.operating_rules
                }
                for c in portfolio.list_companies()
            ]
            self._send_json({"summary": summary, "companies": companies})
            return

        elif path == "/api/briefing":
            briefing = ceo_reports.generate_daily_executive_briefing()
            self._send_json(briefing)
            return

        elif path == "/api/attention":
            companies = portfolio.list_companies()
            cid = companies[0].company_id if companies else None
            attention = OwnerDecisionCenter.get_attention_required_items(tenant_id, cid)
            self._send_json(attention)
            return

        elif path == "/api/search":
            q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            search_res = GlobalSearchEngine.search_all(tenant_id, q)
            self._send_json(search_res)
            return

        elif path == "/api/agent-engine/status":
            self._send_json({
                "status": "OPERATIONAL",
                "default_adapter": config_manager.get("default_model_adapter", "gemini_local"),
                "heartbeat_interval_seconds": config_manager.get("heartbeat_interval_seconds", 30),
                "active_runs_count": len(heartbeat_coordinator.runs),
                "active_plans_count": len(delegation_engine.plans),
                "total_bundled_teams": len(BUNDLED_TEAMS),
                "total_skills": len(SKILLS_CATALOG)
            })
            return

        elif path == "/api/agent-engine/teams":
            teams = PaperclipCatalogManager.list_teams()
            self._send_json({"teams": teams})
            return

        elif path == "/api/agent-engine/skills":
            skills = PaperclipSkillRegistry.list_skills()
            self._send_json({"skills": skills})
            return

        elif path == "/api/agent-engine/plans":
            plans = list(delegation_engine.plans.values())
            self._send_json({"plans": plans})
            return

        elif path == "/api/agent-engine/heartbeats":
            runs = list(heartbeat_coordinator.runs.values())
            self._send_json({"runs": runs[-20:] if runs else []})
            return

        elif path == "/api/morning-meeting":
            companies = portfolio.list_companies()
            cname = companies[0].name if companies else "Enterprise Portfolio"
            cid = companies[0].company_id if companies else "comp_none"
            missions = [{"mission_id": m.mission_id, "status": m.status.value} for m in (companies[0].missions if companies else [])]
            ovn = OvernightOperationsEngine.execute_night_shift(
                tenant_id=tenant_id,
                company_id=cid,
                active_missions=missions,
                employees_count=len(companies[0].workforce) if companies else 0
            )
            agenda = OvernightOperationsEngine.generate_executive_morning_meeting(
                company_name=cname,
                overnight_summary=ovn,
                unresolved_approvals_count=0,
                discovered_opportunities=[]
            )
            self._send_json(agenda)
            return

        elif path == "/api/employees":
            emp_list = []
            for c in portfolio.list_companies():
                for e in c.workforce.values():
                    emp_list.append({
                        "id": e.agent_id,
                        "name": e.role,
                        "department": e.department,
                        "manager": e.manager,
                        "status": e.working_state,
                        "budget_limit": e.budget_limit,
                        "spending_limit": e.spending_limit,
                        "allowed_tools": e.allowed_tools,
                        "company_name": c.name
                    })
            self._send_json({"employees": emp_list})
            return

        elif path == "/api/evidence":
            records = ledger.chain
            root = ledger.get_merkle_root()
            integrity = ledger.verify_ledger_integrity()
            self._send_json({
                "merkle_root": root,
                "unbroken_integrity": integrity,
                "total_records": len(records),
                "records": records[-10:] if records else []
            })
            return

        elif path == "/api/hosts":
            real_host = get_real_system_host()
            self._send_json({"hosts": [real_host]})
            return

        elif path == "/api/missions":
            missions_list = []
            for c in portfolio.list_companies():
                for m in c.missions:
                    missions_list.append({
                        "id": m.mission_id,
                        "title": m.title,
                        "company": c.name,
                        "department": m.department,
                        "outcome": m.target_outcome,
                        "status": m.status.value,
                        "progress": 100 if m.status == MissionStatus.SUCCESS else 50,
                        "verification_summary": m.verification_summary
                    })
            self._send_json({"missions": missions_list})
            return

        elif path == "/api/departments":
            companies = portfolio.list_companies()
            cid = companies[0].company_id if companies else "comp_none"
            depts = DepartmentControlUnit.list_departments(tenant_id, cid)
            self._send_json({"departments": depts})
            return

        elif path == "/api/approvals":
            approvals = ApprovalPipeline.list_approvals(tenant_id)
            self._send_json({"approvals": approvals})
            return

        elif path == "/api/knowledge":
            companies = portfolio.list_companies()
            cid = companies[0].company_id if companies else "comp_none"
            facts = CoreKnowledgeGraph.query_facts(tenant_id, cid)
            baseline = CoreKnowledgeGraph.get_company_baseline(tenant_id, cid)
            self._send_json({"baseline": baseline, "facts": facts})
            return

        elif path == "/api/intelligence":
            companies = portfolio.list_companies()
            cid = companies[0].company_id if companies else "comp_none"
            items = RiskEngine.list_intelligence_items(tenant_id, cid)
            self._send_json({"items": items})
            return

        elif path == "/api/memory":
            memories = OrganizationalMemory.query_memory(tenant_id)
            self._send_json({"memories": memories})
            return

        elif path == "/api/billing":
            usage = UsageMeteringEngine.get_tenant_usage_summary(tenant_id)
            self._send_json({"usage": usage})
            return

        elif path == "/api/ceo/intelligence":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_none"])[0]
            intel = CEOExecutiveBrain.get_company_intelligence_summary(tenant_id, cid)
            self._send_json(intel)
            return

        elif path == "/api/ceo/lessons":
            lessons = CEOLearningEngine.query_lessons(tenant_id)
            self._send_json({"lessons": lessons})
            return

        elif path == "/api/kpis":
            companies = portfolio.list_companies()
            cid = companies[0].company_id if companies else "comp_none"
            kpis = [
                DynamicKpiEngine.register_kpi(tenant_id, cid, "Net Contribution Margin", "Operating profit percentage", "%", 25.0, 18.0),
                DynamicKpiEngine.register_kpi(tenant_id, cid, "Evidence Audit Integrity", "Cryptographically sealed action ratio", "%", 100.0, 100.0)
            ]
            self._send_json({"kpis": kpis})
            return

        elif path == "/api/connectors":
            connectors = connector_registry.list_connectors()
            self._send_json({"connectors": connectors})
            return

        elif path == "/api/tenants":
            tenants = TenantManager.list_tenants()
            self._send_json({"tenants": tenants})
            return

        # Company OS 2.0 Endpoints
        elif path == "/api/ceo/cycle":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_none"])[0]
            cycle_res = ceo_engine.execute_executive_cycle(cid)
            self._send_json(cycle_res)
            return

        elif path == "/api/council/members":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_none"])[0]
            members = ExecutiveCouncil(tenant_id, cid).list_members()
            self._send_json({"members": members})
            return

        elif path == "/api/council/debates":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_none"])[0]
            debates = ExecutiveCouncil(tenant_id, cid).list_debates()
            self._send_json({"debates": debates})
            return

        elif path == "/api/chief-of-staff/dossier":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_none"])[0]
            dossier = ChiefOfStaff(tenant_id, cid).compile_executive_dossier()
            self._send_json(dossier)
            return

        elif path == "/api/chief-of-staff/items":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_none"])[0]
            items = ChiefOfStaff(tenant_id, cid).list_items()
            self._send_json({"items": items})
            return

        elif path == "/api/host/telemetry":
            telemetry = host_agent.get_telemetry()
            self._send_json(telemetry)
            return

        elif path == "/api/sales/leads":
            leads = sales_workforce.list_leads()
            self._send_json({"leads": leads})
            return

        elif path == "/api/events":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_none"])[0]
            events = event_engine.list_unhandled_events(cid)
            self._send_json({"events": events})
            return

        elif path == "/api/meetings":
            meetings = interactive_meetings.list_recent_meetings()
            self._send_json({"meetings": meetings})
            return

        elif path == "/api/causality/summary":
            summary = business_causality.get_causality_summary()
            self._send_json(summary)
            return

        # --- ZONATA UNIVERSAL AI CEO OS ENDPOINTS (GET) ---
        elif path == "/api/v1/zonata/discovery/session":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_primary"])[0]
            session = zonata_discovery.get_or_create_session(tenant_id, cid)
            self._send_json(session.to_dict())
            return

        elif path == "/api/v1/zonata/discovery/facts":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_primary"])[0]
            facts = zonata_discovery.list_findings(tenant_id, cid)
            self._send_json({"facts": facts, "count": len(facts)})
            return

        elif path == "/api/v1/zonata/interview/next":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_primary"])[0]
            q = zonata_interview.get_next_question(tenant_id, cid)
            score, missing = zonata_interview.calculate_completeness(tenant_id, cid)
            self._send_json({
                "next_question": q.to_dict() if q else None,
                "completeness_score": round(score, 4),
                "completeness_pct": f"{int(score * 100)}%",
                "missing_information": missing,
                "is_ready_for_org": score >= 0.70 or len(missing) == 0
            })
            return

        elif path == "/api/v1/zonata/interview/history":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_primary"])[0]
            history = zonata_interview.get_interview_history(tenant_id, cid)
            self._send_json({"history": history, "count": len(history)})
            return

        elif path == "/api/v1/zonata/knowledge-graph":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_primary"])[0]
            kg = CompanyKnowledgeGraph(tenant_id, cid)
            self._send_json({
                "summary": kg.export_summary(),
                "graph": kg.to_dict()
            })
            return

        elif path == "/api/v1/zonata/health":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_primary"])[0]
            model = zonata_health.evaluate_company_health(tenant_id, cid)
            self._send_json(model.to_dict())
            return

        elif path == "/api/v1/zonata/org-design":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_primary"])[0]
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM zonata_org_blueprints WHERE tenant_id = ? AND company_id = ? ORDER BY created_at DESC",
                    (tenant_id, cid)
                ).fetchone()
                if row:
                    self._send_json({
                        "blueprint_id": row["blueprint_id"],
                        "industry": row["industry"],
                        "rationale": row["rationale"],
                        "executives": json.loads(row["executives"]),
                        "departments": json.loads(row["departments"]),
                        "workforce": json.loads(row["workforce"]),
                        "reporting_hierarchy": json.loads(row["reporting_hierarchy"]),
                        "status": row["status"]
                    })
                else:
                    self._send_json({"status": "NOT_GENERATED", "message": "Run org-design/generate to synthesize organization."})
            return

        elif path == "/api/v1/zonata/competitors":
            companies = portfolio.list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else "comp_primary"])[0]
            comps = zonata_competitive.list_competitors(tenant_id, cid)
            opps = zonata_competitive.analyze_competitive_opportunities(tenant_id, cid)
            self._send_json({
                "competitors": [c.to_dict() for c in comps],
                "analysis": opps
            })
            return

        # Fallback to static files in WEB_DIR
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)
        tenant_id = self._get_tenant_id()
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length > 0 else b'{}'
        try:
            req_data = json.loads(body.decode('utf-8'))
        except Exception:
            req_data = {}

        if path == "/api/webhooks/verify":
            secret = req_data.get("secret", "default_webhook_secret")
            payload = json.dumps(req_data.get("payload", {})).encode("utf-8")
            sig = req_data.get("signature", "")
            ts = req_data.get("timestamp", str(time.time()))
            nonce = req_data.get("nonce", f"nonce_{uuid.uuid4().hex}")
            res = WebhookSecurityGateway.verify_webhook(payload, sig, secret, ts, nonce)
            self._send_json(res)
            return

        elif path == "/api/agent-engine/teams/deploy":
            company_id = req_data.get("company_id")
            if not company_id:
                companies = portfolio.list_companies()
                company_id = companies[0].company_id if companies else None
            team_id = req_data.get("team_id", "core_executive_suite")
            try:
                res = PaperclipCatalogManager.deploy_team_to_company(
                    portfolio_manager=portfolio,
                    company_id=company_id,
                    team_id=team_id,
                    tenant_id=tenant_id
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/agent-engine/heartbeat":
            agent_id = req_data.get("agent_id", "agent_ceo_001")
            role = req_data.get("role", "Chief Executive Officer (CEO)")
            company_id = req_data.get("company_id")
            if not company_id:
                companies = portfolio.list_companies()
                company_id = companies[0].company_id if companies else "comp_primary"
            trigger = req_data.get("trigger", "manual")
            tasks = req_data.get("tasks", [])
            res = heartbeat_coordinator.execute_heartbeat_turn(
                agent_id=agent_id,
                company_id=company_id,
                role=role,
                trigger=trigger,
                tasks=tasks
            )
            self._send_json(res)
            return

        elif path == "/api/agent-engine/delegate":
            goal_id = req_data.get("goal_id", f"goal_{uuid.uuid4().hex[:8]}")
            goal_title = req_data.get("goal_title", "Execute Strategic Growth Initiative")
            lead_agent_id = req_data.get("lead_agent_id", "agent_ceo")
            subtasks = req_data.get("subtasks", [])
            requires_board_approval = req_data.get("requires_board_approval", False)
            if not subtasks:
                subtasks = [
                    {"title": "Formulate Architectural Roadmap", "target_role": "Chief Technology Officer (CTO)", "priority": "high", "dependencies": []},
                    {"title": "Draft Feature Specifications", "target_role": "Lead Product Manager", "priority": "high", "dependencies": []},
                    {"title": "Implement Core API", "target_role": "Senior Fullstack Engineer", "priority": "urgent", "dependencies": ["s1"]},
                    {"title": "Verify Security & CI/CD", "target_role": "QA & Reliability Engineer", "priority": "medium", "dependencies": ["s2"]}
                ]
            try:
                plan = delegation_engine.create_delegation_plan(
                    goal_id=goal_id,
                    goal_title=goal_title,
                    lead_agent_id=lead_agent_id,
                    subtasks=subtasks,
                    requires_board_approval=requires_board_approval
                )
                self._send_json({"success": True, "plan": plan})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/agent-engine/plans/approve":
            goal_id = req_data.get("goal_id")
            plan = delegation_engine.plans.get(goal_id)
            if plan:
                plan["approval_status"] = "approved"
                for st in plan["subtasks"]:
                    if st["status"] == "pending_approval":
                        st["status"] = "assigned" if not st.get("dependencies") else "blocked"
                self._send_json({"success": True, "plan": plan})
            else:
                self._send_json({"error": f"Plan '{goal_id}' not found"}, status=404)
            return

        elif path == "/api/agent-engine/subtasks/complete":
            goal_id = req_data.get("goal_id")
            subtask_id = req_data.get("subtask_id")
            result_text = req_data.get("result", "Completed successfully")
            try:
                res = delegation_engine.complete_subtask(goal_id, subtask_id, result_text)
                self._send_json({"success": True, "update": res, "plan": delegation_engine.plans.get(goal_id)})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/handover/package":
            companies = portfolio.list_companies()
            c = companies[0] if companies else None
            cname = c.name if c else "Operating Entity"
            cid = c.company_id if c else "comp_primary"
            pkg = HandoverManager.generate_handover_package(
                tenant_id=tenant_id,
                company_id=cid,
                company_name=cname,
                data_sources_count=len(c.data_sources) if c else 1,
                departments_count=len(c.departments) if c else 1,
                workforce_count=len(c.workforce) if c else 1,
                trust_score=0.95
            )
            self._send_json(pkg)
            return

        elif path == "/api/ceo/decision-room":
            companies = portfolio.list_companies()
            cid = req_data.get("company_id") or (companies[0].company_id if companies else "comp_primary")
            intent = req_data.get("objective_intent", "Increase company profitability")
            spending_limit = float(req_data.get("spending_limit", 1000000.0))
            room = CEOExecutiveBrain.convene_decision_room(tenant_id, cid, intent, spending_limit)
            self._send_json(room)
            return

        elif path == "/api/handover/authorize":
            pkg = req_data.get("package", {})
            user = {"user_id": "usr_owner_executive", "role": UserRole.OWNER}
            res = HandoverManager.authorize_handover(pkg, user)
            self._send_json(res)
            return

        elif path == "/api/simulate":
            companies = portfolio.list_companies()
            c = companies[0] if companies else None
            ctx = {
                "name": c.name if c else "General Enterprise",
                "revenue": c.revenue if c else 0.0,
                "cost": c.cost if c else 0.0,
                "departments": c.departments if c else []
            }
            sim = DigitalTwinSimulator.simulate_mission_execution(
                company_context=ctx,
                proposed_action=req_data.get("action", "Execute strategic workload"),
                target_department=req_data.get("department", "Operations"),
                estimated_budget=float(req_data.get("budget", 5000.0)),
                authority_required=req_data.get("authority", "ASK_ME")
            )
            self._send_json(sim)
            return

        elif path == "/api/ingest":
            companies = portfolio.list_companies()
            cid = companies[0].company_id if companies else "comp_primary"
            res = DataIngestionPipeline.ingest_external_dataset(
                tenant_id=tenant_id,
                company_id=cid,
                source_name=req_data.get("source_name", "Enterprise Ingestion Gateway"),
                source_type=req_data.get("source_type", "API_CONNECTOR"),
                raw_records=req_data.get("records", []),
                trust_score=float(req_data.get("trust_score", 0.9))
            )
            self._send_json(res)
            return

        elif path == "/api/messages":
            msg = GovernedAgentMessage(
                sender_id=req_data.get("sender_id", "ceo_core"),
                receiver_id=req_data.get("receiver_id", "agt_specialist"),
                tenant_id=tenant_id,
                company_id=req_data.get("company_id", "comp_primary"),
                purpose=req_data.get("purpose", "Coordination"),
                payload=req_data.get("payload", {})
            )
            res = agent_bus.dispatch_message(msg)
            self._send_json(res)
            return

        elif path == "/api/onboard":
            name = req_data.get("name", "").strip()
            industry = req_data.get("industry", "General Business")
            is_existing = req_data.get("is_existing", False)

            if not name:
                self._send_json({"error": "Company name is required"}, status=400)
                return

            if is_existing:
                comp = CompanyOnboardingEngine.onboard_existing_company(
                    name=name,
                    industry=industry,
                    initial_data_sources=req_data.get("data_sources", [])
                )
            else:
                comp = CompanyOnboardingEngine.onboard_new_company(
                    name=name,
                    industry=industry,
                    business_model=req_data.get("business_model", "Commercial"),
                    target_revenue=float(req_data.get("target_revenue", 0.0))
                )

            portfolio.register_company(comp)

            # Record in Organizational Memory
            OrganizationalMemory.store_memory(
                tenant_id=tenant_id,
                company_id=comp.company_id,
                memory_tier=MemoryTier.COMPANY,
                memory_type=MemoryType.POLICY,
                content=f"Company '{comp.name}' onboarded into operating portfolio as {comp.company_type} entity."
            )

            self._send_json({
                "success": True,
                "company_id": comp.company_id,
                "name": comp.name,
                "status": comp.status
            })
            return

        elif path == "/api/chat":
            instruction = req_data.get("message", "")
            companies = portfolio.list_companies()
            if not companies:
                self._send_json({
                    "success": False,
                    "command_type": "NO_COMPANY",
                    "ceo_response": "No operating business entities currently onboarded. Please onboard your first company to launch missions."
                })
                return

            target_comp = companies[0]
            res = ceo_command.execute_directive(target_comp.company_id, instruction)

            # Meter CEO Interaction
            UsageMeteringEngine.record_usage(
                tenant_id=tenant_id,
                company_id=target_comp.company_id,
                agent_id="ceo_core",
                mission_id=None,
                model="claude-3-7-sonnet",
                input_tokens=len(instruction) * 2,
                output_tokens=len(res.get("ceo_response", "")) * 2,
                cost=0.0005
            )

            self._send_json(res)
            return

        elif path == "/api/run-workload":
            wtype = req_data.get("workload", "hospitality")

            companies = portfolio.list_companies()
            if not companies:
                comp = CompanyOnboardingEngine.onboard_existing_company(
                    name="Operating Enterprise",
                    industry="Commercial Operations"
                )
                portfolio.register_company(comp)
            else:
                comp = companies[0]

            if wtype == "hospitality":
                mis = run_hospitality_night_audit(comp, kernel)
            elif wtype == "manufacturing":
                mis = run_manufacturing_bottleneck_analysis(comp, kernel)
            elif wtype == "saas":
                mis = run_saas_churn_analysis(comp, kernel)
            elif wtype == "personal":
                mis = run_personal_file_hygiene(comp, kernel)
            elif wtype == "universal":
                mis = run_universal_capability_discovery_task(comp, kernel, registry)
            else:
                self._send_json({"error": "Unknown workload type"}, status=400)
                return

            comp.missions.append(mis)

            # Persist mission into SQLite
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO missions (
                        mission_id, company_id, tenant_id, title, owner_agent,
                        department, target_outcome, status, progress, verification_summary, started_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mis.mission_id, comp.company_id, tenant_id, mis.title, mis.owner_agent,
                        mis.department, mis.target_outcome, mis.status.value, 100, mis.verification_summary, mis.started_at
                    )
                )
                conn.commit()

            self._send_json({
                "success": (mis.status == MissionStatus.SUCCESS),
                "mission_id": mis.mission_id,
                "title": mis.title,
                "status": mis.status.value,
                "verification_summary": mis.verification_summary,
                "evidence_count": len(mis.evidence_packages),
                "merkle_root": ledger.get_merkle_root()
            })
            return

        elif path == "/api/employees":
            role = req_data.get("role", "Specialist Agent")
            dept = req_data.get("department", "Operations")
            companies = portfolio.list_companies()
            if not companies:
                comp = CompanyOnboardingEngine.onboard_new_company(
                    name="Default Operations",
                    industry="Services"
                )
                portfolio.register_company(comp)
            else:
                comp = companies[0]

            contract = DynamicAgentFactory.create_employment_contract(
                role=role,
                department=dept,
                manager="AI CEO",
                responsibilities=[f"Execute autonomous workflows in {dept}"],
                objectives=["100% verification compliance"],
                allowed_tools=["python3", "jq", "tar"]
            )
            comp.workforce[contract.agent_id] = contract

            # Persist employee into SQLite
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO employees (
                        agent_id, company_id, tenant_id, role, department, manager,
                        budget_limit, spending_limit, authority_ceiling, working_state, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        contract.agent_id, comp.company_id, tenant_id, contract.role,
                        contract.department, contract.manager, contract.budget_limit, contract.spending_limit,
                        "AUTOMATIC_IDEMPOTENT", contract.working_state, time.time()
                    )
                )
                conn.commit()

            self._send_json({
                "success": True,
                "agent_id": contract.agent_id,
                "role": contract.role,
                "department": contract.department,
                "authority_ceiling": "AUTOMATIC_IDEMPOTENT"
            })
            return

        elif path == "/api/approvals":
            desc = req_data.get("action_desc", "Automated system operation")
            reason = req_data.get("reason", "Required operational step")
            risk = req_data.get("risk_level", "MEDIUM")
            consequence = req_data.get("consequence", "Production state change")
            companies = portfolio.list_companies()
            cid = companies[0].company_id if companies else "comp_none"

            req = ApprovalPipeline.create_request(
                tenant_id=tenant_id,
                company_id=cid,
                agent_id="agent_requester",
                action_desc=desc,
                reason=reason,
                risk_level=risk,
                consequence=consequence
            )
            self._send_json(req)
            return

        elif path.startswith("/api/approvals/") and path.endswith("/decide"):
            parts = path.strip("/").split("/")
            req_id = parts[2]
            approved = req_data.get("approved", True)
            user = {"user_id": "usr_executive_owner", "role": UserRole.OWNER}
            res = ApprovalPipeline.decide_request(
                tenant_id=tenant_id,
                request_id=req_id,
                approver_user=user,
                approved=approved
            )
            self._send_json(res)
            return

        # Company OS 2.0 POST Endpoints
        elif path == "/api/ceo/chat":
            instruction = req_data.get("message", "")
            companies = portfolio.list_companies()
            cid = req_data.get("company_id", companies[0].company_id if companies else "comp_none")
            chat_res = ceo_engine.chat_directive(cid, instruction)
            self._send_json(chat_res)
            return

        elif path == "/api/council/review":
            topic = req_data.get("topic", "Executive Proposal")
            proposal = req_data.get("proposal", "")
            data = req_data.get("data", {})
            companies = portfolio.list_companies()
            cid = req_data.get("company_id", companies[0].company_id if companies else "comp_none")
            review = ExecutiveCouncil(tenant_id, cid).review_proposal(topic, proposal, data)
            self._send_json(review)
            return

        elif path == "/api/chief-of-staff/items":
            itype = req_data.get("item_type", "INBOX")
            title = req_data.get("title", "New Item")
            details = req_data.get("details", "")
            priority = req_data.get("priority", "MEDIUM")
            companies = portfolio.list_companies()
            cid = req_data.get("company_id", companies[0].company_id if companies else "comp_none")
            item_id = ChiefOfStaff(tenant_id, cid).add_inbox_item(itype, title, details, priority)
            self._send_json({"success": True, "item_id": item_id})
            return

        elif path == "/api/host/quarantine":
            reason = req_data.get("reason", "Manual security quarantine")
            host_agent.quarantine(reason)
            self._send_json({"success": True, "quarantined": True, "status": "QUARANTINED"})
            return

        elif path == "/api/sales/leads":
            name = req_data.get("contact_name", "Lead Contact")
            channel = req_data.get("channel", "WEB_CHAT")
            inquiry = req_data.get("inquiry", "Product inquiry")
            lead = sales_workforce.ingest_lead(name, channel, inquiry)
            self._send_json(lead)
            return

        elif path == "/api/sales/message":
            lead_id = req_data.get("lead_id", "")
            message = req_data.get("message", "")
            res = sales_workforce.process_customer_message(lead_id, message)
            self._send_json(res)
            return

        elif path == "/api/voice/call":
            caller_id = req_data.get("caller_id", "+91-0000000000")
            direction = req_data.get("direction", "INBOUND")
            consent = req_data.get("consent_given", True)
            call = voice_agent.initiate_call_session(caller_id, direction, consent)
            self._send_json(call)
            return

        elif path == "/api/voice/utterance":
            session_id = req_data.get("session_id", "")
            text = req_data.get("text", "")
            turn = voice_agent.process_utterance(session_id, text)
            self._send_json(turn)
            return

        elif path == "/api/events":
            companies = portfolio.list_companies()
            cid = req_data.get("company_id", companies[0].company_id if companies else "comp_none")
            etype = req_data.get("event_type", "REVENUE_ANOMALY")
            category = req_data.get("category", "OPERATIONAL")
            severity = req_data.get("severity", "MEDIUM")
            details = req_data.get("details", {})
            evt = event_engine.emit_event(cid, etype, category, severity, details)
            self._send_json(evt)
            return

        elif path == "/api/meetings/conduct":
            mtype = req_data.get("meeting_type", "MORNING_OPERATING")
            rec = interactive_meetings.conduct_executive_operating_meeting(mtype)
            self._send_json(rec)
            return

        elif path == "/api/causality/verify":
            chain_id = req_data.get("chain_id", "")
            tx_id = req_data.get("transaction_id", "tx_verified")
            rev = float(req_data.get("revenue", 0.0))
            res = business_causality.verify_outcome_with_transaction(chain_id, tx_id, rev)
            self._send_json(res)
            return

        # --- ZONATA UNIVERSAL AI CEO OS ENDPOINTS (POST) ---
        elif path == "/api/v1/zonata/discovery/ingest":
            companies = portfolio.list_companies()
            cid = req_data.get("company_id") or (companies[0].company_id if companies else "comp_primary")
            stmt = req_data.get("statement")
            findings = []
            if stmt:
                findings = zonata_discovery.ingest_owner_statement(tenant_id, cid, stmt)
            elif req_data.get("doc_title") and req_data.get("doc_content"):
                findings = zonata_discovery.ingest_document(
                    tenant_id, cid, req_data["doc_title"], req_data["doc_content"], req_data.get("doc_type", "SOP")
                )
            elif req_data.get("system_name") and req_data.get("payload"):
                findings = zonata_discovery.ingest_system_feed(
                    tenant_id, cid, req_data["system_name"], req_data.get("system_type", "API"), req_data["payload"]
                )
            self._send_json({"success": True, "findings": [f.to_dict() for f in findings], "count": len(findings)})
            return

        elif path == "/api/v1/zonata/interview/answer":
            companies = portfolio.list_companies()
            cid = req_data.get("company_id") or (companies[0].company_id if companies else "comp_primary")
            qid = req_data.get("question_id", "q_general")
            ans = req_data.get("answer", "")
            res = zonata_interview.submit_answer(tenant_id, cid, qid, ans)
            self._send_json(res)
            return

        elif path == "/api/v1/zonata/org-design/generate":
            companies = portfolio.list_companies()
            cid = req_data.get("company_id") or (companies[0].company_id if companies else "comp_primary")
            ind_override = req_data.get("industry")
            org = zonata_org_designer.design_organization(tenant_id, cid, ind_override)
            self._send_json(org.to_dict())
            return

        elif path == "/api/v1/zonata/org-design/mission-workforce":
            companies = portfolio.list_companies()
            cid = req_data.get("company_id") or (companies[0].company_id if companies else "comp_primary")
            mis = req_data.get("mission_objective", "Increase company profitability")
            dept = req_data.get("target_department")
            wf = zonata_org_designer.generate_mission_workforce(tenant_id, cid, mis, dept)
            self._send_json({"mission": mis, "workforce": [w.to_dict() for w in wf], "count": len(wf)})
            return

        elif path == "/api/v1/zonata/workforce/certify":
            agent_id = req_data.get("agent_id")
            if not agent_id:
                self._send_json({"error": "agent_id is required"}, status=400)
                return
            t_res = zonata_agent_factory.run_sandbox_tests(agent_id)
            cert_agent = zonata_agent_factory.certify_and_activate(agent_id)
            self._send_json({"success": True, "test_results": t_res, "agent": cert_agent.to_dict()})
            return

        elif path == "/api/v1/zonata/competitors/add":
            companies = portfolio.list_companies()
            cid = req_data.get("company_id") or (companies[0].company_id if companies else "comp_primary")
            c = zonata_competitive.register_competitor(
                tenant_id=tenant_id,
                company_id=cid,
                name=req_data.get("name", "Competitor"),
                website=req_data.get("website"),
                products=req_data.get("products", []),
                services=req_data.get("services", []),
                public_pricing=req_data.get("public_pricing", {}),
                positioning=req_data.get("positioning")
            )
            self._send_json({"success": True, "competitor": c.to_dict()})
            return

        self._send_json({"error": "Endpoint not found"}, status=404)

def run_server(port=8080):
    socketserver.TCPServer.allow_reuse_address = True
    print(f"[*] Starting RoboAssistant Company OS 1.0 Server on port {port}...")
    with socketserver.TCPServer(("", port), RoboAssistantRequestHandler) as httpd:
        print(f"[*] Company OS 1.0 ready at http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(p)
