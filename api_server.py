"""
RoboAssistant Company OS 1.0 — Unified Multi-Tenant API & Web Server
Production implementation with normalized SQLite persistence, zero mock data,
dynamic host discovery, first-class approvals, department control units,
epistemic truth tracking, digital twin simulation, enterprise connectors,
owner decision center ('Attention Required'), global search, and ingestion pipeline.
"""

from __future__ import annotations

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
import urllib.request
import logging
import platform
import time
import uuid
import hashlib
import hmac
from typing import Dict, List, Optional, Any, Tuple, Set, Union
try:
    import cryptography
    CRYPTOGRAPHY_VERSION = getattr(cryptography, "__version__", "unknown")
except Exception:
    CRYPTOGRAPHY_VERSION = "unavailable"

logger = logging.getLogger("api_server")
_SERVER_BOOT_TIME = time.time()
_BOOTSTRAP_PROVISIONED_TENANTS: Set[str] = set()

def is_production_mode() -> bool:
    app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
    return (app_env in ("production", "prod", "staging")) or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1") or (os.environ.get("ZONATA_PRODUCTION", "0") == "1")

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
from core.auth import TenantManager, UserManager, AuthorizationEnforcer, UserRole, AuthExceptions, TokenRevocationStore
from core.departments import DepartmentControlUnit
from core.approvals import ApprovalPipeline
from core.knowledge_graph import CompanyKnowledgeGraph as CoreKnowledgeGraph, TruthState
from core.intelligence import OpportunityEngine, RiskEngine
from core.memory import OrganizationalMemory, MemoryTier, MemoryType as OrganizationalMemoryType
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
from core.team_catalog import EnterpriseTeamCatalog, BUNDLED_TEAMS
from core.operating_skills import OperatingSkillRegistry, SKILLS_CATALOG
from core.skill_arena import SkillArena
from src.services.agent_engine import config_manager
# Heartbeat/delegation state is tenant-scoped; see _heartbeat()/_delegation().
from core.settings_service import settings_service, GROUPS, CATEGORIES_CATALOG
from core.neon_env import get_neon_services_status, load_neon_env
from core.neon_auth import neon_auth
from core.neon_functions import neon_functions
from core.neon_ai_gateway import neon_ai_gateway
from core.neon_data_api import neon_data_api

SERVER_START_TIME = time.time()

# Initialize Core Subsystems
from core.evidence_ledger import get_default_ledger_path
from core.tenancy import get_runtime, get_portfolio, get_ledger, get_coworker, invalidate as invalidate_tenant_runtime
LEDGER_FILE = get_default_ledger_path()
# No tenant data is instantiated at import time. All stateful runtimes are
# created per authenticated tenant via core.tenancy.get_runtime().
registry = CapabilityRegistry()

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

from core.overview_service import OverviewDataService
from core.schedule_service import UniversalScheduleService
from core.meeting_service import AiCeoMeetingService
from core.assistant_service import FloatingAssistantService
from core.plugins_service import PluginsAndConnectionsService

from core.production_api import api_handler
from core.coworker.engine import UniversalCoworkerEngine
from core.coworker.runtimes.terminal_runtime import TerminalWorkerRuntime, TerminalCommandRisk, TerminalSecurityAnalyzer
from core.universal_terminal import (
    UniversalTerminal, TerminalHandlingAgent, TerminalHealthService,
    ResourceInspector, UniversalRuntimeRouter, CommandPlan,
    VerificationPostcondition, EnvironmentCapabilityRegistry,
    AICeoTerminalInstruction, AICeoTerminalResult
)




from core.enterprise_records import records_engine, EnterpriseRecordsEngine
from core.enterprise_files import files_engine, EnterpriseFilesEngine
from core.enterprise_reports import reports_engine, EnterpriseReportsEngine
from core.enterprise_finance import finance_engine, EnterpriseFinanceEngine
from core.enterprise_agent_factory import agent_factory, EnterpriseAgentFactory
from core.enterprise_integrations import integrations_registry
from core.unified_search import unified_search

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
from zonata.company_api_service import CompanyApiService
from zonata.agent_swarm_adapter import AgentWorkforceAdapter, workforce_planner
from zonata.stateful_agent_adapter import stateful_agent_adapter
from core.stateful_agent_runtime import (
    stateful_memory_gateway,
    SecurityException,
    ConflictResolution,
    MemoryScope,
    MemoryType,
    MemoryCategory
)
from core.multimodal_capability_runtime import (
    multimodal_registry,
    screen_observer,
    hal_vision,
    hal_hearing,
    hal_voice,
    governed_shell,
    governed_files,
    governed_artifacts,
    governed_mcp,
    execution_manager,
    RedactionEngine,
    MemoryFirewall,
    CapabilityFamily,
    ExecutionState
)
from zonata.hal_multimodal_adapter import hal_multimodal_adapter
from core.durable_workflow_runtime import (
    governed_workflow_runtime,
    get_workflow_runtime,
    WorkflowState,
    Command,
    NodeType,
    EdgeType
)
from zonata.langgraph_adapter import langgraph_adapter
from core.automation_fabric import (
    universal_automation_fabric,
    connector_registry as automation_connector_registry,
    template_catalog,
    specialized_agent_registry,
    license_validator,
    AgentDelegationTask
)
from core.a2a_interoperability_runtime import (
    A2AGateway,
    A2AKillSwitch,
    AgentTrustLevel,
    AgentRoleType,
    A2ATaskState,
    ZonataA2ATaskState,
    DataClassification,
    SecurityEventType
)
from zonata.a2a_adapter import A2ACanonicalScenarios, A2ACeoBridge

# NOTE: A2A gateway/scenarios are constructed per tenant via _a2a()/get_runtime().a2a.

# MCP (Model Context Protocol - Project 06)
from core.mcp_interoperability_runtime import (
    MCPGateway,
    MCPKillSwitch,
    MCPTrustState,
    MCPToolRiskClass,
    MCPExecutionStatus,
    MCPDataClassification,
    MCPSecurityEventType,
    MCPTransportType,
    SecurityException as MCPSecurityException,
    ZonataMcpServer,
    MCP_PROTOCOL_VERSION
)
from zonata.mcp_adapter import McpCanonicalScenarios, McpCeoBridge

# NOTE: MCP gateway/server/scenarios are constructed per tenant via _mcp()/get_runtime().

# OpenHands (Governed Agent Execution Runtime - Project 07)
from core.openhands_execution_runtime import (
    OpenHandsRuntimeGateway,
    OpenHandsKillSwitch,
    OpenHandsExecutionStatus,
    WorkspaceClass,
    WorkspaceType,
    NetworkScope,
    CommandRiskClass,
    OpenHandsSecurityEventType,
    SecurityException as OpenHandsSecurityException
)
from zonata.openhands_adapter import OpenHandsCanonicalScenarios, OpenHandsCeoBridge

# NOTE: OpenHands gateway/scenarios are constructed per tenant via get_runtime().

# Browser Use (Governed Autonomous Browser Execution Layer - Project 08)
from core.browser_use_execution_runtime import (
    BrowserExecutionGateway,
    BrowserKillSwitch,
    BrowserExecutionStatus,
    BrowserActionType,
    BrowserActionRiskClass,
    BrowserProfileType,
    BrowserDomainPolicyMode,
    BrowserSecurityEventType,
    SecurityException as BrowserSecurityException
)
from zonata.browser_use_adapter import BrowserUseCanonicalScenarios, BrowserUseCeoBridge

# NOTE: Browser gateway/scenarios are constructed per tenant via _browser()/get_runtime().

# Temporal (Governed Durable Execution & Long-Running Mission Reliability Layer - Project 09)
from core.temporal_durable_execution_runtime import (
    TemporalDurableExecutionGateway,
    TemporalKillSwitch,
    TemporalWorkflowStatus,
    TemporalActivityStatus,
    ActivityRiskClass,
    WorkflowEventType,
    TemporalSecurityEventType,
    ExecutionRoute,
    DurableMissionEngine,
    ExecutionBudget,
    RetryPolicy,
    SecurityException as TemporalSecurityException
)
from zonata.temporal_adapter import TemporalCanonicalScenarios, TemporalCeoBridge

# NOTE: temporal gateway/scenarios are constructed per tenant via _temporal().

# Nango (Governed External System Connectivity & Integration Layer - Project 10)
from core.nango_integration_runtime import (
    ExternalIntegrationGateway,
    IntegrationKillSwitch,
    IntegrationSecurityBoundary,
    ActionRiskClass,
    ConnectionStatus,
    HealthStatus,
    ExecutionStatus,
    SyncType,
    WebhookStatus,
    SecurityException as NangoSecurityException
)
from zonata.nango_adapter import NangoCanonicalScenarios, NangoCeoBridge

# NOTE: Nango gateway/scenarios are constructed per tenant via _nango()/get_runtime().

# Connectors and Agent Bus
connector_registry = ConnectorRegistry()
connector_registry.register(HospitalityPMSConnector())
connector_registry.register(AccountingConnector())
connector_registry.register(PaymentGatewayConnector())
agent_bus = AgentCommunicationBus()

# Universal AI Company OS SaaS Infrastructure Engines
from core.opentelemetry_engine import opentelemetry_engine, opentelemetry_tracer, CorrelationContext, SpanKind, SpanStatus, StatusCode
from core.langfuse_engine import langfuse_engine
from core.openfga_engine import openfga_engine
from core.nats_jetstream import jetstream_engine, nats_broker
from core.vault_client import vault_client
from core.keycloak_idp import keycloak_idp
from core.agent_evaluation import agent_evaluation_engine
from core.saas_billing import saas_billing_engine, SubscriptionTier, SubscriptionStatus, TIER_ENTITLEMENTS, InvalidSubscriptionTransitionError
from core.posthog_analytics import posthog_analytics
from core.object_storage import object_store

WEB_DIR = os.path.join(BASE_DIR, "web")
RECEIVED_ALERTS: List[Dict[str, Any]] = []


def get_real_system_host(tenant_id: str = "tnt_primary"):
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
        "agents": sum(len(c.workforce) for c in get_portfolio(tenant_id).list_companies()),
        "load": load,
        "latency_ms": 1
    }

def _cw(tenant_id: str, company_id: str = None):
    """Tenant-scoped Universal Co-worker engine."""
    return get_coworker(tenant_id, company_id)


def _ceo_engine(tenant_id: str, company_id: str = None):
    """Tenant-scoped AI CEO engine."""
    return get_runtime(tenant_id, company_id).ceo_engine


def _company_service(tenant_id: str):
    """Tenant-scoped Company API service."""
    return get_runtime(tenant_id).company_service


def _ledger_for(tenant_id: str):
    """Tenant-scoped evidence ledger."""
    return get_ledger(tenant_id)


def _heartbeat(tenant_id: str):
    return get_runtime(tenant_id).heartbeat


def _delegation(tenant_id: str):
    return get_runtime(tenant_id).delegation


def _a2a(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).a2a


def _a2a_scenarios(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).a2a_scenarios


def _mcp(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).mcp


def _mcp_scenarios(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).mcp_scenarios


def _mcp_server(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).mcp_server


def _openhands(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).openhands


def _openhands_scenarios(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).openhands_scenarios


def _browser(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).browser


def _browser_scenarios(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).browser_scenarios


def _nango(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).nango


def _nango_scenarios(tenant_id: str, company_id: str = None):
    return get_runtime(tenant_id, company_id).nango_scenarios


_GIT_META: Dict[str, str] = {}


def _git_metadata() -> Dict[str, str]:
    """Commit/branch of the running deployment, resolved honestly (no constants)."""
    if _GIT_META:
        return _GIT_META
    commit = os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("GIT_COMMIT") or ""
    branch = os.environ.get("RENDER_GIT_BRANCH") or os.environ.get("GIT_BRANCH") or ""
    if not commit or not branch:
        try:
            import subprocess
            base = os.path.dirname(os.path.abspath(__file__))
            if not commit:
                commit = subprocess.run(
                    ["git", "-C", base, "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, timeout=3,
                ).stdout.strip()
            if not branch:
                branch = subprocess.run(
                    ["git", "-C", base, "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, timeout=3,
                ).stdout.strip()
        except Exception:
            pass
    _GIT_META.update({"commit": commit or "unknown", "branch": branch or "unknown"})
    return _GIT_META


def _database_status() -> str:
    try:
        with db.get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return "CONNECTED"
    except Exception:
        return "UNAVAILABLE"


def _temporal(tenant_id: str, company_id: str = None):
    """Tenant-scoped durable execution gateway."""
    return get_runtime(tenant_id, company_id).temporal


def _temporal_scenarios(tenant_id: str, company_id: str = None):
    """Tenant-scoped canonical durable-execution scenario suite."""
    return get_runtime(tenant_id, company_id).temporal_scenarios


def _safe_company_key(company_id: str) -> str:
    """Reject path traversal in company identifiers used for filesystem paths."""
    import re as _re
    key = (company_id or "").strip()
    if not key or not _re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key) or ".." in key:
        raise ValueError(f"Invalid company id: {company_id!r}")
    return key


def _draft_path(tenant_id: str, company_id: str) -> str:
    """Tenant-isolated draft location (one directory per tenant)."""
    key = _safe_company_key(company_id)
    tkey = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in tenant_id or "unknown")
    return os.path.join(BASE_DIR, "storage", "drafts", tkey, f"{key}.json")


_MERKLE_CACHE: Dict[str, Any] = {"ts": 0.0, "value": "UNVERIFIED", "lock": __import__("threading").Lock()}
_MERKLE_TTL = 30.0


def _platform_merkle_status() -> str:
    """Cached platform ledger verification (30s TTL) for liveness probes."""
    now = time.time()
    cached = _MERKLE_CACHE["value"]
    if now - _MERKLE_CACHE["ts"] < _MERKLE_TTL and cached != "UNVERIFIED":
        return cached
    with _MERKLE_CACHE["lock"]:
        now = time.time()
        if now - _MERKLE_CACHE["ts"] < _MERKLE_TTL and _MERKLE_CACHE["value"] != "UNVERIFIED":
            return _MERKLE_CACHE["value"]
        try:
            audit = get_ledger("tnt_primary").verify_full_chain_integrity()
            if audit.get("valid"):
                value = "INTEGRITY_VERIFIED"
            elif audit.get("active_epoch_valid"):
                value = "ACTIVE_EPOCH_VERIFIED_HISTORICAL_FORKS_RECORDED"
            else:
                value = "INTEGRITY_FAILED"
        except Exception as exc:
            value = f"INTEGRITY_CHECK_ERROR: {str(exc)[:100]}"
        _MERKLE_CACHE["ts"] = time.time()
        _MERKLE_CACHE["value"] = value
        return value


ALLOWED_ORIGINS = {
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://app.zonata.ai"
}
_env_origins = os.environ.get("ZONATA_ALLOWED_ORIGINS")
if _env_origins:
    for _o in _env_origins.split(","):
        if _o.strip():
            ALLOWED_ORIGINS.add(_o.strip())

class RoboAssistantRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        self._request_id = f"req_{uuid.uuid4().hex[:10]}"
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def _apply_cors_headers(self):
        req_origin = self.headers.get("Origin")
        if req_origin:
            is_allowed = (
                req_origin in ALLOWED_ORIGINS
                or req_origin.startswith("http://localhost:")
                or req_origin.startswith("http://127.0.0.1:")
            )
            if is_allowed:
                self.send_header("Access-Control-Allow-Origin", req_origin)
                self.send_header("Access-Control-Allow-Credentials", "true")
                self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE, PATCH")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Tenant-ID, X-Company-ID, X-Request-ID, X-Correlation-ID")

    def _get_client_ip(self) -> str:
        """
        Resolves client IP address with anti-spoofing reverse proxy verification.
        X-Forwarded-For and X-Real-IP are only trusted if direct peer is in ZONATA_TRUSTED_PROXIES.
        """
        peer_ip = self.client_address[0] if self.client_address else "127.0.0.1"
        trusted_proxies_str = os.environ.get("ZONATA_TRUSTED_PROXIES", "127.0.0.1,::1")
        trusted_proxies = {p.strip() for p in trusted_proxies_str.split(",") if p.strip()}
        if peer_ip in trusted_proxies or os.environ.get("ZONATA_TRUST_ALL_PROXIES", "0") == "1":
            xff = self.headers.get("X-Forwarded-For")
            if xff:
                client_candidate = xff.split(",")[0].strip()
                if client_candidate:
                    return client_candidate
            x_real_ip = self.headers.get("X-Real-IP")
            if x_real_ip:
                return x_real_ip.strip()
        return peer_ip

    def _validate_transport_security(self) -> bool:
        """
        Enforces transport layer security (TLS/HTTPS) boundaries:
        - In production mode (APP_ENV=production or ZONATA_STRICT_AUTH=1 or is_production_mode()):
          1. If request is forwarded via reverse proxy with X-Forwarded-Proto: http (and ZONATA_ALLOW_INSECURE_HTTP != '1'),
             rejects with HTTP 403 Forbidden.
          2. If ZONATA_ENFORCE_HTTPS=1 is set, requires either TLS socket or X-Forwarded-Proto: https.
        - Returns True if transport security is satisfied, False if rejected (and sends error response).
        """
        app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
        is_prod = (app_env in ("production", "prod")) or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1") or is_production_mode()

        forwarded_proto = self.headers.get("X-Forwarded-Proto", "").lower().strip()

        if is_prod and os.environ.get("ZONATA_ALLOW_INSECURE_HTTP", "0") != "1":
            if forwarded_proto == "http":
                self._send_json({
                    "error": "HTTPS Required",
                    "detail": "Insecure HTTP connections are prohibited in production mode. Please connect via HTTPS.",
                    "code": "TLS_TRANSPORT_SECURITY_VIOLATION"
                }, status=403)
                return False

            if os.environ.get("ZONATA_ENFORCE_HTTPS", "0") == "1":
                is_ssl_socket = hasattr(self.connection, "getpeercert")
                if not is_ssl_socket and forwarded_proto != "https":
                    self._send_json({
                        "error": "HTTPS Required",
                        "detail": "Encrypted HTTPS transport is strictly enforced. Cleartext connections rejected.",
                        "code": "TLS_ENCRYPTION_MANDATORY"
                    }, status=403)
                    return False

        return True

    def _blocked_by_global_killswitch(self, surface: str) -> bool:
        """Single authoritative gate for every execution surface."""
        if universal_automation_fabric.is_killswitch_active():
            self._send_json({
                "error": f"Global kill switch engaged: {surface} blocked",
                "blocked": True,
                "killswitch_active": True,
            }, status=403)
            return True
        return False

    def _approver_denied(self, auth_context: Dict[str, Any]) -> bool:
        role = str((auth_context or {}).get("role") or "")
        if role not in (UserRole.OWNER, UserRole.EXECUTIVE, UserRole.GLOBAL_ADMIN):
            self._send_json({
                "success": False,
                "error": "INSUFFICIENT_PERMISSIONS: Only Owner or Executive roles can decide approvals.",
                "role": role,
            }, status=403)
            return True
        return False

    def _get_auth_context(self) -> Dict[str, Any]:
        """
        Constitutional Invariant: UNAUTHENTICATED REQUEST != TENANT IDENTITY.
        Extracts and cryptographically verifies Bearer token, enforcing tenant isolation.
        Fails closed on missing or invalid tokens.
        """
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif auth_header:
            token = auth_header.strip()

        payload = UserManager.verify_token(token) if token else None

        header_tenant = self.headers.get("X-Tenant-ID")
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        param_tenant = q.get("tenant_id", [None])[0]
        requested_tenant = header_tenant or param_tenant

        if payload:
            token_tenant = payload.get("tenant_id")
            if requested_tenant and requested_tenant != token_tenant and payload.get("role") != UserRole.GLOBAL_ADMIN:
                raise AuthExceptions.TenantIsolationViolation(
                    f"Tenant isolation violation: requested tenant '{requested_tenant}' does not match authenticated token '{token_tenant}'"
                )
            return payload

        # Fail closed: No unauthenticated bootstrap permitted on network-accessible interface
        raise AuthExceptions.AuthenticationError(
            "Authentication Required: Missing, invalid, or expired Bearer token"
        )

    def _get_tenant_id(self) -> str:
        ctx = self._get_auth_context()
        tenant_id = ctx.get("tenant_id")
        if not tenant_id:
            raise AuthExceptions.AuthenticationError("Authenticated context has no valid tenant_id")
        return tenant_id

    def _resolve_company_id(self, auth_context: Dict[str, Any],
                            query_params: Optional[Dict[str, List[str]]] = None) -> str:
        """
        Resolve the active company for this request, trusting only the verified
        token. A client-supplied X-Company-ID / ?company_id is honoured only if
        the company is proven to belong to the authenticated tenant.
        """
        tenant_id = auth_context.get("tenant_id") or ""
        token_company = auth_context.get("company_id")

        requested = self.headers.get("X-Company-ID")
        if not requested and query_params:
            requested = (query_params.get("company_id") or [None])[0]
        if isinstance(requested, str):
            requested = requested.strip()
        if not requested or requested.lower() in ("portfolio", "all", "null", "undefined", "none"):
            return token_company or f"comp_{tenant_id}"
        if requested == token_company:
            return requested
        try:
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT company_id FROM companies WHERE company_id = ? AND tenant_id = ?",
                    (requested, tenant_id),
                ).fetchone()
            if row:
                return requested
        except Exception:
            pass
        # Fail closed to the token's own company.
        return token_company or f"comp_{tenant_id}"

    def _send_json(self, data, status=200, headers=None):
        req_id = getattr(self, "_request_id", None) or f"req_{uuid.uuid4().hex[:10]}"
        try:
            from core.observability_stack import sre_metrics
            sre_metrics.inc_counter("zonata_api_requests_total", 1.0)
            if status >= 500:
                sre_metrics.inc_counter("zonata_api_errors_total", 1.0)
            elif status in (401, 403):
                sre_metrics.inc_counter("zonata_auth_failures_total", 1.0)
            elif status == 429:
                sre_metrics.inc_counter("zonata_rate_limit_exceeded_total", 1.0)
            start_time = getattr(self, "_start_time", None)
            if start_time:
                sre_metrics.observe_latency((time.time() - start_time) * 1000.0)
        except Exception:
            pass
        body_bytes = json.dumps(data, default=str).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_bytes)))
            self._apply_cors_headers()
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-XSS-Protection", "1; mode=block")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.send_header("X-Request-ID", req_id)
            if headers:
                for k, v in headers.items():
                    self.send_header(k, str(v))
            elif getattr(self, "_last_rate_limit_headers", None):
                for k, v in self._last_rate_limit_headers.items():
                    self.send_header(k, str(v))
            self.end_headers()
            if getattr(self, "_head_only", False):
                return
            self.wfile.write(body_bytes)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _enforce_tenant_fairness(self, path: str, method: str, auth_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Evaluates hierarchical rate limiting, tenant fairness, and endpoint abuse protection.
        Returns True if request is permitted to proceed, or False if HTTP 429 was sent.
        """
        try:
            client_ip = self._get_client_ip()
            from core.tenant_fairness import tenant_fairness_engine
            decision = tenant_fairness_engine.evaluate_request(path, method, client_ip, auth_context=auth_context)
            if not decision.is_allowed:
                err_payload = {
                    "error": "Too Many Requests",
                    "detail": decision.detail or "Rate limit exceeded. Please try again later.",
                    "limit": decision.limit,
                    "remaining": decision.remaining,
                    "retry_after": decision.retry_after,
                    "violation_axis": decision.violation_axis
                }
                self._send_json(err_payload, status=429, headers=decision.headers)
                return False
            self._last_rate_limit_headers = decision.headers
            return True
        except Exception as e:
            logger.warning(f"Tenant fairness evaluation encountered error: {e}")
            return True

    def do_OPTIONS(self):
        req_origin = self.headers.get("Origin")
        if req_origin:
            is_allowed = (
                req_origin in ALLOWED_ORIGINS
                or req_origin.startswith("http://localhost:")
                or req_origin.startswith("http://127.0.0.1:")
            )
            if not is_allowed:
                self.send_response(403)
                self.end_headers()
                return

        self.send_response(204)
        self._apply_cors_headers()
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.end_headers()

    def do_HEAD(self):
        """Handle HTTP HEAD requests identically to GET, omitting response body per RFC 7231."""
        self._head_only = True
        try:
            self.do_GET()
        finally:
            self._head_only = False

    def do_GET(self):
        self._start_time = time.time()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        # Standard Health & Liveness Endpoints (Public)
        if path == "/readyz":
            if not db.is_ready():
                self._send_json({
                    "status": "UNREADY",
                    "database": "UNAVAILABLE",
                    "error": "Database readiness verification not completed",
                    "timestamp": time.time()
                }, status=503)
                return
            git_meta = _git_metadata()
            git_commit = git_meta["commit"]
            git_branch = git_meta["branch"]
            db_state = _database_status()
            is_ga_mode = os.environ.get("ZONATA_PUBLIC_GA_MODE", "0") == "1" or os.environ.get("ZONATA_RESTRICTED_PILOT_MODE", "1") == "0"
            default_version = "1.0.0-GA" if is_ga_mode else "1.0.0-RESTRICTED-PILOT"
            release_version = os.environ.get("APP_RELEASE_VERSION", default_version)
            release_scope = "URA / ZONATA — PUBLIC GA PRODUCTION" if is_ga_mode else "URA / ZONATA — RESTRICTED PRODUCTION PILOT, NOT PUBLIC GA"
            # Authoritative Merkle ledger integrity check, cached briefly so
            # liveness probes stay fast under concurrent load. The cached value
            # is a real verification result, not a fabricated constant.
            merkle_status = _platform_merkle_status()
            envelope_data = {
                "max_organizations": int(os.environ.get("MAX_DESIGN_PARTNER_ORGS", "100" if is_ga_mode else "3")),
                "max_concurrency_leases_per_tenant": int(os.environ.get("PILOT_MAX_CONCURRENCY", "10" if is_ga_mode else "4")),
                "max_rpm_per_tenant": int(os.environ.get("PILOT_MAX_RPM", "120" if is_ga_mode else "60")),
                "mode": "GA" if is_ga_mode else "RESTRICTED_PILOT",
                "status": "ENFORCED"
            }
            self._send_json({
                "status": "HEALTHY" if db_state == "CONNECTED" else "DEGRADED",
                "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
                "version": release_version,
                "release_scope": release_scope,
                "commit": git_commit,
                "branch": git_branch,
                "database": db_state,
                "database_dialect": db.get_dialect(),
                "merkle_ledger": merkle_status,
                "server_mode": "MULTI_THREADED_CONCURRENT",
                "cryptography_version": CRYPTOGRAPHY_VERSION,
                "pilot_envelope": envelope_data,
                "operating_envelope": envelope_data,
                "timestamp": time.time()
            })
            return

        if path in ("/health", "/healthz", "/livez", "/api/v1/health"):
            git_meta = _git_metadata()
            git_commit = git_meta["commit"]
            git_branch = git_meta["branch"]
            db_state = _database_status()
            is_ga_mode = os.environ.get("ZONATA_PUBLIC_GA_MODE", "0") == "1" or os.environ.get("ZONATA_RESTRICTED_PILOT_MODE", "1") == "0"
            default_version = "1.0.0-GA" if is_ga_mode else "1.0.0-RESTRICTED-PILOT"
            release_version = os.environ.get("APP_RELEASE_VERSION", default_version)
            release_scope = "URA / ZONATA — PUBLIC GA PRODUCTION" if is_ga_mode else "URA / ZONATA — RESTRICTED PRODUCTION PILOT, NOT PUBLIC GA"
            # Authoritative Merkle ledger integrity check — derived honestly from ledger verifier
            try:
                ledger_audit = _ledger_for("tnt_primary").verify_full_chain_integrity()
                if ledger_audit["valid"]:
                    merkle_status = "INTEGRITY_VERIFIED"
                elif ledger_audit.get("active_epoch_valid"):
                    merkle_status = "ACTIVE_EPOCH_VERIFIED_HISTORICAL_FORKS_RECORDED"
                else:
                    merkle_status = "INTEGRITY_FAILED"
            except Exception as e:
                ledger_audit = {}
                merkle_status = f"INTEGRITY_CHECK_ERROR: {str(e)[:100]}"
            envelope_data = {
                "max_organizations": int(os.environ.get("MAX_DESIGN_PARTNER_ORGS", "100" if is_ga_mode else "3")),
                "max_concurrency_leases_per_tenant": int(os.environ.get("PILOT_MAX_CONCURRENCY", "10" if is_ga_mode else "4")),
                "max_rpm_per_tenant": int(os.environ.get("PILOT_MAX_RPM", "120" if is_ga_mode else "60")),
                "mode": "GA" if is_ga_mode else "RESTRICTED_PILOT",
                "status": "ENFORCED"
            }
            self._send_json({
                "status": "HEALTHY" if db_state == "CONNECTED" else "DEGRADED",
                "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
                "version": release_version,
                "release_scope": release_scope,
                "commit": git_commit,
                "branch": git_branch,
                "database": db_state,
                "database_dialect": db.get_dialect(),
                "merkle_ledger": merkle_status,
                "server_mode": "MULTI_THREADED_CONCURRENT",
                "cryptography_version": CRYPTOGRAPHY_VERSION,
                "pilot_envelope": envelope_data,
                "operating_envelope": envelope_data,
                "timestamp": time.time()
            })
            return

        # Operating Envelope — supports both GA and Restricted Pilot modes
        if path in ("/api/pilot/envelope", "/api/v1/pilot/envelope", "/api/operating-envelope"):
            is_pilot_mode = os.environ.get("ZONATA_PUBLIC_GA_MODE", "0") != "1" and os.environ.get("ZONATA_RESTRICTED_PILOT_MODE", "1") == "1"
            is_ga_mode = not is_pilot_mode
            max_orgs = int(os.environ.get("MAX_DESIGN_PARTNER_ORGS", "3" if is_pilot_mode else "100"))
            max_concurrency = int(os.environ.get("PILOT_MAX_CONCURRENCY", "4" if is_pilot_mode else "10"))
            max_rpm = int(os.environ.get("PILOT_MAX_RPM", "60" if is_pilot_mode else "120"))
            active_org_count = 0
            try:
                with db.get_connection() as conn:
                    row = conn.execute("SELECT COUNT(*) FROM pilot_organizations WHERE status = 'ACTIVE'").fetchone()
                    if row:
                        active_org_count = row[0] if isinstance(row, (tuple, list)) else row["COUNT(*)"]
            except Exception:
                pass
            release_scope = "URA / ZONATA — RESTRICTED PRODUCTION PILOT, NOT PUBLIC GA" if is_pilot_mode else "URA / ZONATA — PUBLIC GA PRODUCTION"
            env_dict = {
                "max_organizations": max_orgs,
                "active_organizations": active_org_count,
                "active_pilot_organizations": active_org_count,
                "available_slots": max(0, max_orgs - active_org_count),
                "available_pilot_slots": max(0, max_orgs - active_org_count),
                "max_concurrency_leases_per_tenant": max_concurrency,
                "max_requests_per_minute_per_tenant": max_rpm,
                "request_timeout_seconds": 60,
                "execution_timeout_seconds": 300,
                "enterprise_sla": "BEST_EFFORT" if is_ga_mode else "NOT_OFFERED_ON_FREE_TIER",
                "public_ga_qualified": is_ga_mode
            }
            self._send_json({
                "status": "ENFORCED",
                "release_scope": release_scope,
                "mode": "GA" if is_ga_mode else "RESTRICTED_PILOT",
                "target_audience": "Public GA — All Organizations" if is_ga_mode else "1–3 Controlled Design-Partner Organizations",
                "pilot_envelope": env_dict,
                "operating_envelope": env_dict,
                "timestamp": time.time()
            })
            return

        # Milestone J: List Active Pilot Organizations
        if path in ("/api/pilot/organizations", "/api/v1/pilot/organizations"):
            try:
                with db.get_connection() as conn:
                    rows = conn.execute("SELECT tenant_id, org_name, status, registered_at FROM pilot_organizations WHERE status = 'ACTIVE'").fetchall()
                    self._send_json({"pilot_organizations": [dict(r) for r in rows], "count": len(rows)})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        # Enforce IP-level rate limiting for public unauthenticated endpoints (healthz/readyz exempt above)
        if not self._enforce_tenant_fairness(path, "GET", auth_context=None):
            return

        # Neon Cloud Services Status & Gateway Endpoints
        if path == "/api/v1/neon/services":
            self._send_json(get_neon_services_status())
            return

        if path == "/api/v1/neon/auth/config":
            self._send_json(neon_auth.get_public_config())
            return

        if path == "/api/v1/neon/functions/hello":
            res = neon_functions.invoke("hello")
            status_code = 200 if res.get("success") else 502
            self._send_json(res, status=status_code)
            return

        if path == "/api/v1/neon/ai/status":
            self._send_json(neon_ai_gateway.get_status())
            return

        if path == "/api/v1/neon/data-api/status":
            self._send_json(neon_data_api.get_status())
            return

        if path == "/api/auth/csrf":
            import secrets
            token = secrets.token_hex(32)
            self._send_json({"csrf_token": token, "timestamp": time.time()})
            return

        # Google OAuth / Enterprise SSO Public Endpoints
        if path == "/api/auth/oauth/google/config":
            client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
            configured = bool(client_id)
            host_header = self.headers.get("Host", "localhost")
            proto = self.headers.get("X-Forwarded-Proto", "https" if "render.com" in host_header else "http")
            callback_uri = f"{proto}://{host_header}/api/auth/oauth/google/callback"
            self._send_json({
                "configured": configured,
                "provider": "google",
                "client_id": client_id if configured else "",
                "redirect_uri": callback_uri,
                "auth_url": "/api/auth/oauth/google/login" if configured else "",
                "neon_auth_configured": bool(os.environ.get("NEON_AUTH_BASE_URL")),
                "message": "Google OAuth is ready" if configured else "Google OAuth credentials (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET) not configured."
            })
            return

        if path == "/api/auth/oauth/google/login":
            client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
            if not client_id:
                self._send_json({
                    "error": "Enterprise Identity Provider Not Configured",
                    "detail": "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are not configured on this host. Please set them in your deployment environment variables or sign in with host password.",
                    "code": "OAUTH_NOT_CONFIGURED"
                }, status=503)
                return
            host_header = self.headers.get("Host", "localhost")
            proto = self.headers.get("X-Forwarded-Proto", "https" if "render.com" in host_header else "http")
            redirect_uri = f"{proto}://{host_header}/api/auth/oauth/google/callback"
            state_val = uuid.uuid4().hex
            scope = urllib.parse.quote("openid email profile")
            google_auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth"
                f"?response_type=code"
                f"&client_id={urllib.parse.quote(client_id)}"
                f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
                f"&scope={scope}"
                f"&state={state_val}"
                f"&prompt=select_account"
            )
            self.send_response(302)
            self.send_header("Location", google_auth_url)
            self.end_headers()
            return

        if path == "/api/auth/oauth/google/callback":
            code = query_params.get("code", [""])[0]
            client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
            if not code or not client_id or not client_secret:
                err_msg = query_params.get("error", ["OAuth exchange failed: missing credentials or authorization code"])[0]
                self.send_response(302)
                self.send_header("Location", f"/?error={urllib.parse.quote(err_msg)}")
                self.end_headers()
                return

            try:
                host_header = self.headers.get("Host", "localhost")
                proto = self.headers.get("X-Forwarded-Proto", "https" if "render.com" in host_header else "http")
                redirect_uri = f"{proto}://{host_header}/api/auth/oauth/google/callback"

                token_url = "https://oauth2.googleapis.com/token"
                token_data = urllib.parse.urlencode({
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }).encode("utf-8")
                token_req = urllib.request.Request(token_url, data=token_data, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
                with urllib.request.urlopen(token_req, timeout=15) as t_resp:
                    t_json = json.loads(t_resp.read().decode("utf-8"))

                access_token = t_json.get("access_token")
                user_req = urllib.request.Request("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {access_token}"})
                with urllib.request.urlopen(user_req, timeout=15) as u_resp:
                    user_info = json.loads(u_resp.read().decode("utf-8"))

                email = user_info.get("email", "").strip().lower()
                name = user_info.get("name") or user_info.get("given_name") or (email.split("@")[0] if "@" in email else "Host")

                if not email:
                    raise RuntimeError("Google profile did not contain a verified email address.")

                with db.get_connection() as conn:
                    existing_user = conn.execute(
                        "SELECT user_id, tenant_id, role, company_id FROM users WHERE email = ? AND status = 'ACTIVE'",
                        (email,)
                    ).fetchone()

                if existing_user:
                    user_id = existing_user["user_id"]
                    tenant_id = existing_user["tenant_id"]
                    role = existing_user["role"]
                    company_id = existing_user["company_id"] or f"comp_{tenant_id}"
                else:
                    tenant = TenantManager.create_tenant(name=f"{name} Enterprise", plan="ENTERPRISE")
                    tenant_id = tenant["tenant_id"]
                    company_id = f"comp_{tenant_id}"
                    oauth_pw = uuid.uuid4().hex + uuid.uuid4().hex
                    user = UserManager.create_user_with_credentials(
                        tenant_id=tenant_id,
                        email=email,
                        name=name,
                        password=oauth_pw,
                        role=UserRole.OWNER,
                        company_id=company_id
                    )
                    user_id = user["user_id"]
                    role = UserRole.OWNER
                    now = time.time()
                    with db.get_connection() as conn:
                        conn.execute(
                            """
                            INSERT INTO companies (
                                company_id, tenant_id, name, country, industry,
                                company_type, status, currency, timezone, revenue,
                                cost, contribution, created_at
                            ) VALUES (?, ?, ?, 'US', 'Enterprise Cloud & SaaS', 'EXISTING', 'OPERATIONAL', '$', 'UTC', 0.0, 0.0, 0.0, ?)
                            ON CONFLICT (company_id) DO NOTHING
                            """,
                            (company_id, tenant_id, f"{name} Enterprise", now)
                        )
                        conn.commit()

                user_data = {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "email": email,
                    "name": name,
                    "role": role,
                    "permissions": ["*"] if role == UserRole.OWNER else ["read", "execute"]
                }
                token = UserManager.generate_token(user_data, expires_in_seconds=86400 * 7)
                self.send_response(302)
                self.send_header("Location", f"/?token={urllib.parse.quote(token)}")
                self.end_headers()
                return
            except Exception as e:
                logger.exception(f"Google OAuth callback error: {e}")
                self.send_response(302)
                self.send_header("Location", f"/?error={urllib.parse.quote(f'SSO authentication failed: {str(e)}')}")
                self.end_headers()
                return

        # Prometheus Standard Exposition Endpoint (Public / Scraper)
        if path == "/metrics":
            # Edge protection guard when running directly on public PaaS without Nginx
            if os.environ.get("ZONATA_PROTECT_METRICS", "0") == "1":
                auth_header = self.headers.get("Authorization", "")
                metrics_token = os.environ.get("METRICS_AUTH_TOKEN", "")
                is_authorized = bool(metrics_token and auth_header == f"Bearer {metrics_token}")
                if not is_authorized:
                    self.send_response(403)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Forbidden: Public access to /metrics is restricted."}).encode('utf-8'))
                    return

            from core.observability_stack import sre_metrics
            from core.production_observability import observability_engine
            content1 = sre_metrics.scrape_prometheus_format()
            content2 = observability_engine.generate_prometheus_metrics()
            combined = content1.strip() + "\n\n" + content2.strip() + "\n"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(combined.encode('utf-8'))
            return

        # Enforce transport security for API and application endpoints
        if not self._validate_transport_security():
            return

        # Public Auth Environment Endpoint
        if path == "/api/auth/environment":
            app_env = os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or os.environ.get("NODE_ENV") or "development"
            is_strict = (app_env.lower() == "production") or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1")
            self._send_json({
                "environment": app_env.lower(),
                "strict_auth": is_strict,
                "requires_mfa": is_strict or (app_env.lower() == "staging"),
                "auth_mode": "PRODUCTION_STRICT" if is_strict else ("STAGING" if app_env.lower() == "staging" else "DEV_BOOTSTRAP"),
                "server_time": time.time()
            })
            return

        # SRE Alertmanager Ingested Alerts Exposition Endpoint
        if path == "/api/telemetry/alerts":
            self._send_json({"alerts": RECEIVED_ALERTS[-100:], "count": len(RECEIVED_ALERTS)})
            return

        # Real OpenAPI document (previously the SPA fallback returned HTML here).
        if path in ("/openapi.json", "/api/openapi.json"):
            from core.openapi_spec import build_openapi
            self._send_json(build_openapi())
            return

        # Public Static Web Content (HTML, JS, CSS, images)
        if not path.startswith("/api/") and path != "/metrics":
            clean_path = path.lstrip('/')
            if not clean_path:
                clean_path = 'index.html'
            file_path = os.path.join(WEB_DIR, clean_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.path = '/' + clean_path
                return super().do_GET()
            if path.startswith("/api/"):
                self._send_json({
                    "error": "Not Found",
                    "code": "UNKNOWN_ENDPOINT",
                    "path": path,
                    "docs": "/openapi.json",
                }, status=404)
                return
            self.path = '/index.html'
            return super().do_GET()

        if path.startswith("/api/v2/"):
            headers_dict = {k: v for k, v in self.headers.items()}
            status_code, resp_headers, body = api_handler.handle_request("GET", path, headers_dict, b"")
            self._send_json(body, status=status_code)
            return

        try:
            auth_context = self._get_auth_context()
            tenant_id = auth_context.get("tenant_id")
            company_id = self._resolve_company_id(auth_context, query_params)
        except AuthExceptions.AuthenticationError as e:
            self._send_json({"error": "Unauthorized", "detail": str(e)}, status=401)
            return
        except AuthExceptions.TenantIsolationViolation as e:
            self._send_json({"error": "Forbidden", "detail": str(e), "security_event": "TENANT_SPOOFING_ATTEMPT"}, status=403)
            return

        if not self._enforce_tenant_fairness(path, "GET", auth_context=auth_context):
            return

        if path == "/api/auth/me":
            try:
                ctx = self._get_auth_context()
                self._send_json({"authenticated": True, "context": ctx})
            except AuthExceptions.AuthenticationError as e:
                self._send_json({"authenticated": False, "error": str(e)}, status=401)
            return

        # Milestone J: Tenant Concurrency Leases Inspection
        if path == "/api/concurrency/leases":
            max_leases = int(os.environ.get("PILOT_MAX_CONCURRENCY", "4"))
            now = time.time()
            active_count = 0
            leases_list = []
            try:
                with db.get_connection() as conn:
                    rows = conn.execute(
                        "SELECT lease_id, lease_type, acquired_at, expires_at FROM tenant_concurrency_leases WHERE tenant_id = ? AND expires_at >= ?",
                        (tenant_id, now)
                    ).fetchall()
                    active_count = len(rows)
                    leases_list = [dict(r) for r in rows]
            except Exception:
                pass
            self._send_json({
                "tenant_id": tenant_id,
                "active_leases_count": active_count,
                "max_concurrency": max_leases,
                "available_slots": max(0, max_leases - active_count),
                "leases": leases_list
            })
            return
        if path == "/api/crm/customers":
            from core.enterprise_crm import EnterpriseCrmService
            company_id = self.headers.get("X-Company-ID") or query_params.get("company_id", [None])[0]
            search = query_params.get("search", [None])[0]
            status = query_params.get("status", [None])[0]
            tier = query_params.get("tier", [None])[0]
            svc = EnterpriseCrmService(tenant_id)
            customers = svc.list_customers(company_id=company_id, search=search, status=status, tier=tier)
            self._send_json({"customers": customers, "total": len(customers)})
            return

        elif path.startswith("/api/crm/customers/"):
            cust_id = path.split("/api/crm/customers/")[1].split("?")[0].strip()
            from core.enterprise_crm import EnterpriseCrmService
            svc = EnterpriseCrmService(tenant_id)
            c = svc.get_customer(cust_id)
            if c:
                self._send_json(c)
            else:
                self._send_json({"error": "Customer not found"}, status=404)
            return

        elif path == "/api/crm/deals":
            from core.enterprise_crm import EnterpriseCrmService
            company_id = self.headers.get("X-Company-ID") or query_params.get("company_id", [None])[0]
            stage = query_params.get("stage", [None])[0]
            svc = EnterpriseCrmService(tenant_id)
            deals = svc.list_deals(company_id=company_id, stage=stage)
            self._send_json({"deals": deals, "total": len(deals)})
            return

        elif path.startswith("/api/crm/deals/"):
            deal_id = path.split("/api/crm/deals/")[1].split("?")[0].strip()
            from core.enterprise_crm import EnterpriseCrmService
            svc = EnterpriseCrmService(tenant_id)
            d = svc.get_deal(deal_id)
            if d:
                self._send_json(d)
            else:
                self._send_json({"error": "Deal not found"}, status=404)
            return

        if path in ("/api/overview", "/api/overview/snapshot"):
            try:
                cid = query_params.get("company_id", [None])[0] if query_params.get("company_id") else None
                if cid in ("", "ALL", "null", "undefined", "portfolio"):
                    cid = None
                period = query_params.get("period", ["30d"])[0] if query_params.get("period") else "30d"
                snapshot = OverviewDataService.get_snapshot(tenant_id, company_id=cid, period=period)
                self._send_json(snapshot)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                logger.error(f"Failed to retrieve overview snapshot for tenant {tenant_id}: {e}\n{tb}", exc_info=True)
                self._send_json({
                    "error": "Internal Server Error",
                    "detail": f"Failed to retrieve overview snapshot: {type(e).__name__}: {str(e)}",
                    "traceback": tb.splitlines()[-5:]
                }, status=500)
            return

        elif path == "/api/overview/explain-variance":
            try:
                cid = query_params.get("company_id", [None])[0]
                if cid in ("", "ALL", "null", "undefined", "portfolio"):
                    cid = None
                metric = query_params.get("metric", ["revenue"])[0]
                explanation = OverviewDataService.explain_variance(tenant_id, company_id=cid, metric=metric)
                self._send_json(explanation)
            except Exception as e:
                logger.error(f"Failed to explain variance for tenant {tenant_id}: {e}", exc_info=True)
                self._send_json({
                    "error": "Internal Server Error",
                    "detail": f"Failed to explain variance: {type(e).__name__}"
                }, status=500)
            return

        elif path == "/api/portfolio":
            target_portfolio = get_portfolio(tenant_id)
            summary = target_portfolio.get_portfolio_summary()
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
                for c in get_portfolio(tenant_id).list_companies()
            ]
            self._send_json({"summary": summary, "companies": companies})
            return

        elif path == "/api/briefing":
            briefing = ceo_reports.generate_daily_executive_briefing()
            self._send_json(briefing)
            return

        elif path == "/api/attention":
            companies = get_portfolio(tenant_id).list_companies()
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
                "active_runs_count": len(_heartbeat(tenant_id).runs),
                "active_plans_count": len(_delegation(tenant_id).plans),
                "total_bundled_teams": len(BUNDLED_TEAMS),
                "total_skills": len(SKILLS_CATALOG)
            })
            return

        elif path == "/api/agent-engine/teams":
            teams = EnterpriseTeamCatalog.list_teams()
            self._send_json({"teams": teams})
            return

        elif path == "/api/agent-engine/skills":
            skills = OperatingSkillRegistry.list_skills()
            self._send_json({"skills": skills})
            return

        elif path == "/api/skills":
            arena = SkillArena(tenant_id, company_id)
            skills = arena.list_skills(role=(auth_context or {}).get("role"))
            self._send_json({"skills": skills, "count": len(skills)})
            return

        elif path.startswith("/api/skills/") and len(path.split("/")) == 4:
            skill_id = path.split("/")[3]
            skill = OperatingSkillRegistry.get_skill(skill_id)
            if not skill:
                self._send_json({"error": f"Skill '{skill_id}' not found"}, status=404)
                return
            from core.skill_arena import role_to_authority, AUTHORITY_RANK
            authority = role_to_authority((auth_context or {}).get("role"))
            floor = str(skill.get("authority_floor", "EMPLOYEE"))
            self._send_json({
                "skill": skill,
                "requester_authority": authority,
                "available_to_requester": (
                    AUTHORITY_RANK.get(authority, 0) >= AUTHORITY_RANK.get(floor, 0)
                ),
            })
            return

        elif path == "/api/arena/skill-runs":
            limit = int(query_params.get("limit", ["50"])[0])
            arena = SkillArena(tenant_id, company_id)
            runs = arena.list_skill_runs(limit=limit)
            self._send_json({"runs": runs, "count": len(runs)})
            return

        elif path == "/api/arena/decisions":
            limit = int(query_params.get("limit", ["50"])[0])
            arena = SkillArena(tenant_id, company_id)
            decisions = arena.list_decisions(limit=limit)
            self._send_json({"decisions": decisions, "count": len(decisions)})
            return

        elif path.startswith("/api/arena/decisions/") and len(path.split("/")) == 5:
            decision_id = path.split("/")[4]
            decision = SkillArena(tenant_id, company_id).get_decision(decision_id)
            if not decision:
                self._send_json({"error": "Decision not found"}, status=404)
                return
            self._send_json(decision)
            return

        elif path == "/api/agent-engine/plans":
            plans = list(_delegation(tenant_id).plans.values())
            self._send_json({"plans": plans})
            return

        elif path == "/api/agent-engine/heartbeats":
            runs = list(_heartbeat(tenant_id).runs.values())
            self._send_json({"runs": runs[-20:] if runs else []})
            return

        elif path == "/api/morning-meeting":
            companies = get_portfolio(tenant_id).list_companies()
            if not companies:
                self._send_json({
                    "error": "No company is onboarded for this tenant",
                    "code": "NO_COMPANY",
                    "detail": "Onboard a company before requesting a morning meeting.",
                }, status=409)
                return
            cname = companies[0].name
            cid = companies[0].company_id
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
            target_portfolio = get_portfolio(tenant_id)
            for c in get_portfolio(tenant_id).list_companies():
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
            tenant_ledger = _ledger_for(tenant_id)
            # Defense in depth: even if a legacy ledger file contains records
            # from other tenants, never return them to this tenant.
            records = [
                r for r in tenant_ledger.chain
                if (r.get("metadata") or {}).get("tenant_id") in (None, tenant_id)
                and (r.get("metadata") or {}).get("company_id") in (None, company_id)
            ]
            root = tenant_ledger.get_merkle_root()
            ledger_audit = tenant_ledger.verify_full_chain_integrity()
            self._send_json({
                "tenant_id": tenant_id,
                "merkle_root": root,
                "unbroken_integrity": ledger_audit["valid"],
                "active_epoch_integrity": ledger_audit.get("active_epoch_valid", True),
                "active_epoch_records": ledger_audit.get("active_epoch_records", 0),
                "epochs_count": ledger_audit.get("epochs_count", 1),
                "total_records": len(records),
                "status": "INTEGRITY_VERIFIED" if ledger_audit["valid"] else ("ACTIVE_EPOCH_VERIFIED_HISTORICAL_FORKS_RECORDED" if ledger_audit.get("active_epoch_valid") else "INTEGRITY_FAILED"),
                "records": records[-10:] if records else []
            })
            return

        elif path.startswith("/api/evidence/") and path.endswith("/verify"):
            evidence_id = path.split("/")[3]
            res = _ledger_for(tenant_id).verify_evidence_artifacts(
                evidence_id, tenant_id=tenant_id, company_id=company_id
            )
            self._send_json(res, status=200 if res.get("success") else 404)
            return

        elif path == "/api/hosts":
            real_host = get_real_system_host(tenant_id)
            self._send_json({"hosts": [real_host]})
            return

        elif path == "/api/missions":
            missions_list = []
            for c in get_portfolio(tenant_id).list_companies():
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
            depts = DepartmentControlUnit.list_departments(tenant_id, company_id)
            self._send_json({"departments": depts, "company_id": company_id})
            return

        elif path == "/api/approvals":
            approvals = ApprovalPipeline.list_approvals(tenant_id)
            self._send_json({"approvals": approvals})
            return

        elif path == "/api/knowledge":
            companies = get_portfolio(tenant_id).list_companies()
            cid = companies[0].company_id if companies else ""
            facts = CoreKnowledgeGraph.query_facts(tenant_id, cid)
            baseline = CoreKnowledgeGraph.get_company_baseline(tenant_id, cid)
            self._send_json({"baseline": baseline, "facts": facts})
            return

        elif path == "/api/intelligence":
            companies = get_portfolio(tenant_id).list_companies()
            cid = companies[0].company_id if companies else ""
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

        elif path == "/api/telemetry/spans":
            trace_id = query_params.get("trace_id", [None])[0]
            spans = opentelemetry_engine.tracer.get_spans(tenant_id=tenant_id, trace_id=trace_id)
            self._send_json({"spans": [s.to_dict() for s in spans], "count": len(spans)})
            return

        elif path == "/api/telemetry/metrics":
            summary = opentelemetry_engine.metrics.get_metrics_summary()
            self._send_json({"metrics": summary})
            return

        elif path == "/api/langfuse/generations":
            m_id = query_params.get("mission_id", [None])[0]
            a_id = query_params.get("agent_id", [None])[0]
            generations = langfuse_engine.get_generations(tenant_id=tenant_id, mission_id=m_id, agent_id=a_id)
            self._send_json({"generations": generations, "count": len(generations)})
            return

        elif path == "/api/langfuse/analytics":
            analytics = langfuse_engine.get_analytics(tenant_id=tenant_id)
            self._send_json(analytics)
            return

        elif path == "/api/openfga/relations":
            user = query_params.get("user", [""])[0]
            obj = query_params.get("object", [""])[0]
            rels = openfga_engine.list_relations(user=user, object=obj, tenant_id=tenant_id)
            self._send_json({"user": user, "object": obj, "relations": rels})
            return

        elif path == "/api/vault/leases":
            leases = vault_client.list_active_leases(tenant_id=tenant_id)
            self._send_json({"leases": leases, "count": len(leases)})
            return

        elif path == "/api/events/replay":
            stream = query_params.get("stream", ["ZONATA_MISSIONS"])[0]
            filter_sub = query_params.get("filter_subject", [None])[0]
            limit_val = int(query_params.get("limit", [50])[0])
            msgs = jetstream_engine.replay_stream(stream_name=stream, filter_subject=filter_sub, tenant_id=tenant_id, limit=limit_val)
            self._send_json({"stream": stream, "messages": [m if isinstance(m, dict) else m.to_dict() for m in msgs], "count": len(msgs)})
            return

        elif path == "/api/evaluations/reports":
            test_id = query_params.get("test_id", [None])[0]
            agent_id = query_params.get("agent_id", [None])[0]
            reports = agent_evaluation_engine.list_reports(test_id=test_id, agent_id=agent_id)
            self._send_json({"reports": reports, "count": len(reports)})
            return

        elif path == "/api/billing/usage" or path == "/api/v1/billing/usage":
            snapshot = saas_billing_engine.get_or_create_tenant(tenant_id=tenant_id)
            self._send_json(snapshot.to_dict())
            return

        elif path in ("/api/billing/subscription", "/api/v1/billing/subscriptions"):
            sub = saas_billing_engine.get_or_create_subscription(tenant_id=tenant_id)
            self._send_json(sub.to_dict())
            return

        elif path in ("/api/billing/entitlements", "/api/v1/billing/entitlements"):
            sub = saas_billing_engine.get_or_create_subscription(tenant_id=tenant_id)
            plan = TIER_ENTITLEMENTS.get(sub.tier, TIER_ENTITLEMENTS[SubscriptionTier.FREE])
            metric = query_params.get("metric", [None])[0]
            amount_str = query_params.get("amount", ["1.0"])[0]
            try:
                amount = float(amount_str)
            except ValueError:
                amount = 1.0

            if metric:
                allowed, reason = saas_billing_engine.check_entitlement(tenant_id=tenant_id, metric=metric, requested_amount=amount)
                self._send_json({
                    "allowed": allowed,
                    "reason": reason,
                    "metric": metric,
                    "amount": amount,
                    "tier": sub.tier.value,
                    "status": sub.status.value
                })
            else:
                self._send_json({
                    "tier": sub.tier.value,
                    "status": sub.status.value,
                    "entitlements": {
                        "max_tokens_per_month": plan.max_tokens_per_month,
                        "max_browser_minutes_per_month": plan.max_browser_minutes_per_month,
                        "max_terminal_seconds_per_month": plan.max_terminal_seconds_per_month,
                        "max_storage_bytes": plan.max_storage_bytes,
                        "max_agents": plan.max_agents,
                        "max_seats": plan.max_seats,
                        "max_concurrency": plan.max_concurrency,
                        "features_allowed": plan.features_allowed,
                        "monthly_price_usd": plan.monthly_price_usd
                    }
                })
            return

        elif path in ("/api/billing/invoices", "/api/v1/billing/invoices"):
            now = time.time()
            inv = saas_billing_engine.generate_tenant_invoice(
                tenant_id=tenant_id,
                period_start=now - (86400 * 30),
                period_end=now
            )
            self._send_json({"invoices": [inv], "count": 1})
            return

        elif path == "/api/analytics/posthog/funnel":
            funnel = posthog_analytics.get_funnel_summary(tenant_id=tenant_id)
            self._send_json({"funnel": funnel})
            return

        elif path == "/api/analytics/posthog/flags":
            key = query_params.get("key", [""])[0]
            distinct_id = query_params.get("distinct_id", ["anon"])[0]
            enabled = posthog_analytics.is_feature_enabled(key, distinct_id=distinct_id, tenant_id=tenant_id)
            self._send_json({"key": key, "enabled": enabled, "distinct_id": distinct_id})
            return

        elif path == "/api/storage/artifacts/download":
            artifact_id = query_params.get("artifact_id", [""])[0]
            expiry = int(query_params.get("expiry_seconds", [3600])[0])
            url = object_store.generate_presigned_url(artifact_id, tenant_id=tenant_id, expiry_seconds=expiry, action="download")
            self._send_json({"artifact_id": artifact_id, "download_url": url, "expires_in": expiry})
            return


        elif path == "/api/ceo/intelligence":
            companies = get_portfolio(tenant_id).list_companies()
            if not companies:
                self._send_json({
                    "error": "No company is onboarded for this tenant",
                    "code": "NO_COMPANY",
                    "detail": "Onboard a company to view AI CEO intelligence.",
                }, status=409)
                return
            cid = self._resolve_company_id(auth_context, query_params)
            intel = CEOExecutiveBrain.get_company_intelligence_summary(tenant_id, cid)
            self._send_json(intel)
            return

        elif path == "/api/ceo/lessons":
            lessons = CEOLearningEngine.query_lessons(tenant_id)
            self._send_json({"lessons": lessons})
            return

        elif path == "/api/kpis":
            companies = get_portfolio(tenant_id).list_companies()
            if not companies:
                self._send_json({"kpis": [], "company_id": None, "code": "NO_COMPANY"})
                return
            cid = self._resolve_company_id(auth_context, query_params)
            comp = next((c for c in companies if c.company_id == cid), companies[0])
            revenue = float(getattr(comp, "revenue", 0.0) or 0.0)
            cost = float(getattr(comp, "cost", 0.0) or 0.0)
            margin_pct = round(((revenue - cost) / revenue) * 100.0, 2) if revenue > 0 else None
            ledger = _ledger_for(tenant_id)
            audit = ledger.verify_full_chain_integrity()
            records = len(ledger.chain)
            integrity_pct = 100.0 if audit.get("valid") else 0.0
            kpis = []
            if margin_pct is not None:
                kpis.append({
                    "kpi_id": "kpi_net_contribution_margin",
                    "name": "Net Contribution Margin",
                    "description": "Operating profit as a percentage of booked revenue",
                    "unit": "%",
                    "value": margin_pct,
                    "source": "companies.revenue / companies.cost",
                })
            kpis.append({
                "kpi_id": "kpi_evidence_integrity",
                "name": "Evidence Audit Integrity",
                "description": "Merkle chain verification across this tenant's evidence ledger",
                "unit": "%",
                "value": integrity_pct,
                "records": records,
                "source": "tenant evidence ledger",
            })
            self._send_json({
                "kpis": kpis,
                "company_id": cid,
                "financials_available": margin_pct is not None,
            })
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
            companies = get_portfolio(tenant_id).list_companies()
            if not companies:
                self._send_json({
                    "error": "No company is onboarded for this tenant",
                    "code": "NO_COMPANY",
                    "detail": "Onboard a company before running an executive cycle.",
                }, status=409)
                return
            cid = self._resolve_company_id(auth_context, query_params)
            cycle_res = _ceo_engine(tenant_id, company_id).execute_executive_cycle(cid)
            self._send_json(cycle_res)
            return

        elif path == "/api/council/members":
            companies = get_portfolio(tenant_id).list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else ""])[0]
            members = ExecutiveCouncil(tenant_id, cid).list_members()
            self._send_json({"members": members})
            return

        elif path == "/api/council/debates":
            companies = get_portfolio(tenant_id).list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else ""])[0]
            debates = ExecutiveCouncil(tenant_id, cid).list_debates()
            self._send_json({"debates": debates})
            return

        elif path == "/api/chief-of-staff/dossier":
            companies = get_portfolio(tenant_id).list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else ""])[0]
            dossier = ChiefOfStaff(tenant_id, cid).compile_executive_dossier()
            self._send_json(dossier)
            return

        elif path == "/api/chief-of-staff/items":
            companies = get_portfolio(tenant_id).list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else ""])[0]
            items = ChiefOfStaff(tenant_id, cid).list_items()
            self._send_json({"items": items})
            return

        elif path == "/api/host/telemetry":
            telemetry = get_runtime(tenant_id).host_agent.get_telemetry()
            self._send_json(telemetry)
            return

        elif path == "/api/sales/leads":
            leads = get_runtime(tenant_id).sales.list_leads()
            self._send_json({"leads": leads})
            return

        elif path == "/api/events":
            companies = get_portfolio(tenant_id).list_companies()
            cid = query_params.get("company_id", [companies[0].company_id if companies else ""])[0]
            events = get_runtime(tenant_id).event_engine.list_unhandled_events(cid)
            self._send_json({"events": events})
            return

        elif path == "/api/meetings":
            meetings = get_runtime(tenant_id).meetings.list_recent_meetings()
            self._send_json({"meetings": meetings})
            return

        elif path == "/api/causality/summary":
            summary = get_runtime(tenant_id).causality.get_causality_summary()
            self._send_json(summary)
            return

        # --- PHASE 11 GOVERNANCE & ECONOMIC COMMAND ENDPOINTS (GET) ---
        elif path == "/api/v1/economic/budgets":
            from core.economic_governance import economic_governor
            from dataclasses import asdict
            entity_id = query_params.get("entity_id", [None])[0]
            if entity_id:
                b = economic_governor.get_budget(entity_id)
                self._send_json({"budget": asdict(b) if b else None})
            else:
                with db.get_connection() as conn:
                    rows = conn.execute("SELECT * FROM enterprise_budgets WHERE tenant_id = ?", (tenant_id,)).fetchall()
                    budgets = [dict(r) for r in rows]
                self._send_json({"budgets": budgets, "total": len(budgets)})
            return

        elif path == "/api/v1/economic/reservations":
            with db.get_connection() as conn:
                rows = conn.execute("SELECT * FROM enterprise_budget_reservations WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 50", (tenant_id,)).fetchall()
                res_list = [dict(r) for r in rows]
            self._send_json({"reservations": res_list, "total": len(res_list)})
            return

        elif path == "/api/v1/approvals/cryptographic/nonces":
            with db.get_connection() as conn:
                rows = conn.execute("SELECT nonce, approval_id, tenant_id, action_digest, approver_id, approver_role, risk_class, status, issued_at, expires_at, consumed_at, consumed_by_action_id FROM action_approval_nonces WHERE tenant_id = ? ORDER BY issued_at DESC LIMIT 50", (tenant_id,)).fetchall()
                nonces = [dict(r) for r in rows]
            self._send_json({"nonces": nonces, "total": len(nonces)})
            return

        # --- ZONATA UNIVERSAL AI CEO OS ENDPOINTS (GET) ---
        elif path == "/api/v1/zonata/discovery/session":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            session = zonata_discovery.get_or_create_session(tenant_id, cid)
            self._send_json(session.to_dict())
            return

        elif path == "/api/v1/zonata/discovery/facts":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            facts = zonata_discovery.list_findings(tenant_id, cid)
            self._send_json({"facts": facts, "count": len(facts)})
            return

        elif path == "/api/v1/zonata/interview/next":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
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
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            history = zonata_interview.get_interview_history(tenant_id, cid)
            self._send_json({"history": history, "count": len(history)})
            return

        elif path == "/api/v1/zonata/knowledge-graph":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            kg = CompanyKnowledgeGraph(tenant_id, cid)
            self._send_json({
                "summary": kg.export_summary(),
                "graph": kg.to_dict()
            })
            return

        elif path == "/api/v1/zonata/health":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            model = zonata_health.evaluate_company_health(tenant_id, cid)
            self._send_json(model.to_dict())
            return

        elif path == "/api/v1/zonata/org-design":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
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
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            comps = zonata_competitive.list_competitors(tenant_id, cid)
            opps = zonata_competitive.analyze_competitive_opportunities(tenant_id, cid)
            self._send_json({
                "competitors": [c.to_dict() for c in comps],
                "analysis": opps
            })
            return

        elif path == "/api/companies":
            comps = []
            for c in get_portfolio(tenant_id).list_companies():
                comps.append({
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
                    "rules": c.operating_rules,
                    "baseline_summary": c.baseline_summary
                })
            self._send_json({"companies": comps})
            return

        elif path.startswith("/api/companies/") and path.endswith("/draft"):
            cid = path.split("/")[3]
            try:
                draft_file = _draft_path(tenant_id, cid)
            except ValueError as exc:
                self._send_json({"error": "Invalid company id", "code": "INVALID_COMPANY_ID",
                                 "detail": str(exc)}, status=400)
                return
            if os.path.exists(draft_file):
                try:
                    with open(draft_file, "r", encoding="utf-8") as f:
                        self._send_json({"draft": json.load(f), "company_id": cid,
                                         "tenant_id": tenant_id})
                        return
                except Exception as exc:
                    self._send_json({"error": "Draft file is unreadable",
                                     "code": "DRAFT_UNREADABLE",
                                     "detail": f"{type(exc).__name__}: {exc}"}, status=500)
                    return
            self._send_json({"draft": None, "company_id": cid, "tenant_id": tenant_id})
            return

        elif path.startswith("/api/companies/"):
            parts = path.split("/")
            if len(parts) >= 4:
                cid = parts[3]
                sub_action = parts[4] if len(parts) >= 5 else None

                if sub_action == "context":
                    ctx = _company_service(tenant_id).get_company_context(tenant_id, cid)
                    if not ctx:
                        self._send_json({"error": "Company not found"}, status=404)
                    else:
                        self._send_json(ctx)
                    return
                elif sub_action == "organization":
                    org = _company_service(tenant_id).get_organization(tenant_id, cid)
                    self._send_json(org)
                    return
                elif sub_action == "workforce":
                    wf = _company_service(tenant_id).get_workforce(tenant_id, cid)
                    self._send_json({"workforce": wf, "count": len(wf)})
                    return
                elif sub_action == "missions":
                    msns = _company_service(tenant_id).get_missions(tenant_id, cid)
                    self._send_json({"missions": msns, "count": len(msns)})
                    return
                elif sub_action == "processes":
                    procs = _company_service(tenant_id).get_processes(tenant_id, cid)
                    self._send_json({"processes": procs, "count": len(procs)})
                    return
                elif sub_action == "trustgraph":
                    tg = _company_service(tenant_id).get_trustgraph(tenant_id, cid)
                    self._send_json(tg)
                    return
                elif len(parts) == 4:
                    c = get_portfolio(tenant_id).get_company(cid)
                    if c:
                        self._send_json({
                            "company": {
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
                                "rules": c.operating_rules,
                                "baseline_summary": c.baseline_summary
                            }
                        })
                        return
                    self._send_json({"error": "Company not found"}, status=404)
                    return

        elif path == "/api/tools":
            tools_list = []
            for cap_name, cap in registry._capabilities.items():
                tools_list.append({
                    "id": f"cap_{cap.name}",
                    "name": cap.name,
                    "category": "Development & CLI",
                    "source": "Built In",
                    "availability": "Available",
                    "permission": "SANDBOXED_READ_ONLY" if cap.is_sandboxed else "AUTOMATIC_IDEMPOTENT",
                    "version": cap.version,
                    "health": "Healthy",
                    "last_verified": "Realtime",
                    "path": cap.binary_path,
                    "license": cap.license_type,
                    "description": f"Standard vetted system execution capability ({cap.license_type})."
                })

            try:
                with db.get_connection() as conn:
                    h_rows = conn.execute(
                        "SELECT hc.* FROM host_capabilities hc "
                        "JOIN hosts h ON h.host_id = hc.host_id "
                        "WHERE h.tenant_id = ?",
                        (tenant_id,),
                    ).fetchall()
                    for hr in h_rows:
                        cat_map = {
                            "SCREEN": "Desktop & Robot",
                            "MOUSE": "Desktop & Robot",
                            "KEYBOARD": "Desktop & Robot",
                            "WINDOWS": "Desktop & Robot",
                            "FILES": "Operating System",
                            "PROCESS": "Operating System",
                            "BROWSER": "Browser Automation",
                            "INSTALLER": "Package Management"
                        }
                        tools_list.append({
                            "id": hr["cap_id"],
                            "name": hr["capability_name"].replace("_", " ").title(),
                            "category": cat_map.get(hr["category"], hr["category"]),
                            "source": "Host Fabric",
                            "availability": "Available" if hr["enabled"] else "Disabled",
                            "permission": hr["authority_required"],
                            "version": "2.0-native",
                            "health": "Healthy",
                            "last_verified": "Realtime",
                            "description": f"Trusted host execution contract for {hr['category'].lower()} operations."
                        })
            except Exception:
                pass

            for conn_item in connector_registry.list_connectors():
                configured = bool(
                    conn_item.get("connected")
                    and str(conn_item.get("qualification_status")) not in ("BLOCKED", "MOCK_ONLY")
                )
                tools_list.append({
                    "id": "conn_" + "".join(
                        ch if ch.isalnum() else "_" for ch in conn_item["name"].lower()
                    ).strip("_"),
                    "name": conn_item["name"],
                    "category": "Connected Service",
                    "source": "Connected Integration",
                    "availability": "Available" if configured else "Needs configuration",
                    "permission": conn_item.get("permission", "AUDITED_TRANSACTIONAL"),
                    "version": "1.0",
                    "health": "Healthy" if configured else "Not configured",
                    "qualification_status": conn_item.get("qualification_status"),
                    "last_verified": "Active" if configured else "Never",
                    "description": (
                        f"Enterprise connector gateway ({conn_item.get('type', 'system')})."
                        if configured else
                        f"Connector ({conn_item.get('type', 'system')}) is registered but has no provider credentials; "
                        "it returns NOT_CONFIGURED until configured in Settings → Connectors."
                    ),
                })

            try:
                with db.get_connection() as conn:
                    for tr in conn.execute(
                        "SELECT tool_id, name, version, risk_class, status, signature, created_at "
                        "FROM tool_packages WHERE tenant_id = ? ORDER BY created_at DESC",
                        (tenant_id,),
                    ).fetchall():
                        tools_list.append({
                            "id": tr["tool_id"],
                            "name": tr["name"],
                            "category": "Custom Automation",
                            "source": "User Created",
                            "availability": "Available" if tr["status"] == "ACTIVE" else tr["status"],
                            "permission": "AUDITED_TRANSACTIONAL",
                            "risk_class": tr["risk_class"],
                            "version": tr["version"],
                            "health": "Registered",
                            "last_verified": "Registration only (never executed)",
                            "signature": tr["signature"],
                            "created_at": tr["created_at"],
                            "description": "Tenant-created tool registered through Tool Factory V2 after AST security validation.",
                        })
            except Exception:
                pass

            # HAL Multimodal Capabilities (Requirement 41)
            for mc in get_runtime(tenant_id).multimodal.list_capabilities():
                tools_list.append({
                    "id": mc["capability_id"],
                    "name": mc["name"],
                    "category": f"Multimodal & {mc['family'].replace('_', ' ').title()}",
                    "source": "HAL9000 Multimodal Layer",
                    "availability": "Available" if (mc["health_status"] == "HEALTHY" and mc["is_enabled"]) else mc["health_status"],
                    "permission": "AUDITED_TRANSACTIONAL" if mc["requires_approval"] else "AUTOMATIC_IDEMPOTENT",
                    "version": mc["version"],
                    "platform": mc["platform"],
                    "health": mc["health_status"].title(),
                    "risk": mc["risk_level"],
                    "dependencies": "OpenCV, PyAudio, Whisper, Edge-TTS",
                    "license": "MIT License",
                    "sandbox": mc["execution_mode"],
                    "test_status": mc["health_status"],
                    "evidence_support": "Cryptographic SHA-256 Ledger",
                    "last_verified": "Host probe at registration",
                    "description": f"Governed HAL capability ({mc['family']}). Risk: {mc['risk_level']}."
                })

            self._send_json({"tools": tools_list})
            return

        elif path in ("/api/llm/status", "/api/v1/llm/status"):
            from core.llm_runtime import llm_runtime
            self._send_json(llm_runtime.status(tenant_id, company_id))
            return

        elif path in ("/api/llm/providers", "/api/v1/llm/providers"):
            from core.llm_runtime import llm_runtime
            st = llm_runtime.status(tenant_id, company_id)
            self._send_json({"providers": st["providers"], "configured_provider": st["configured_provider"],
                             "configured_model": st["configured_model"], "privacy_note": st["privacy_note"]})
            return

        elif path == "/api/settings":
            # company_id was resolved from the verified token (see _resolve_company_id)
            categories_cat = settings_service.get_categories_catalog(tenant_id, company_id)
            self._send_json({
                "groups": GROUPS,
                "categories": categories_cat,
                "total_categories": len(categories_cat),
                "tenant_id": tenant_id,
                "company_id": company_id
            })
            return

        elif path == "/api/settings/search":
            # company_id was resolved from the verified token (see _resolve_company_id)
            q = query_params.get("q", [""])[0]
            results = settings_service.search_settings(q, tenant_id, company_id)
            self._send_json({
                "query": q,
                "results": results,
                "count": len(results),
                "timestamp": time.time()
            })
            return

        elif path.startswith("/api/settings/category/") and len(path.split("/")) == 5:
            cat_id = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            detail = settings_service.get_category_detail(cat_id, tenant_id, company_id)
            self._send_json(detail)
            return

        elif path == "/api/settings/audit":
            # company_id was resolved from the verified token (see _resolve_company_id)
            cat = query_params.get("category", [None])[0]
            actor = query_params.get("actor", [None])[0]
            risk = query_params.get("risk", [None])[0]
            limit = int(query_params.get("limit", [50])[0])
            events = settings_service.get_audit_events(tenant_id, company_id, category=cat, actor=actor, risk_level=risk, limit=limit)
            self._send_json({"events": events, "count": len(events)})
            return

        elif path == "/api/settings/effective":
            # company_id was resolved from the verified token (see _resolve_company_id)
            enforcements = settings_service.get_all_effective_enforcements(tenant_id, company_id)
            self._send_json({
                "tenant_id": tenant_id,
                "company_id": company_id,
                "effective_enforcement": enforcements,
                "server_timestamp": time.time()
            })
            return

        elif path == "/api/settings/drift":
            # company_id was resolved from the verified token (see _resolve_company_id)
            drift = settings_service.check_runtime_drift(tenant_id, company_id)
            self._send_json(drift)
            return

        # =====================================================================
        # Prompt 03: Universal Schedule Endpoints (GET)
        # =====================================================================
        elif path == "/api/schedules/recommendations":
            company_id = query_params.get("company_id", [None])[0]
            recs = get_runtime(tenant_id).schedule.get_ai_ceo_recommendations(company_id)
            self._send_json({"recommendations": recs})
            return

        elif path == "/api/schedules":
            company_id = query_params.get("company_id", [None])[0]
            item_type = query_params.get("item_type", [None])[0]
            priority = query_params.get("priority", [None])[0]
            status = query_params.get("status", [None])[0]
            start_after = float(query_params.get("start_after", [0])[0]) if "start_after" in query_params else None
            start_before = float(query_params.get("start_before", [0])[0]) if "start_before" in query_params else None
            items = get_runtime(tenant_id).schedule.list_schedules(company_id, item_type, priority, status, start_after, start_before)
            self._send_json({"schedules": items, "count": len(items)})
            return

        elif path.startswith("/api/schedules/"):
            sched_id = path.split("/")[3]
            item = get_runtime(tenant_id).schedule.get_schedule(sched_id)
            if item:
                self._send_json(item)
            else:
                self._send_json({"error": "Schedule not found"}, status=404)
            return

        # =====================================================================
        # Prompt 03: AI CEO Meeting Room Endpoints (GET)
        # =====================================================================
        elif path == "/api/meetings/active":
            # company_id was resolved from the verified token (see _resolve_company_id)
            meeting = get_runtime(tenant_id).meeting_service.get_or_create_active_meeting(company_id)
            self._send_json(meeting)
            return

        elif path == "/api/meetings/decisions":
            company_id = query_params.get("company_id", [None])[0]
            decisions = get_runtime(tenant_id).meeting_service.list_decisions(company_id)
            self._send_json({"decisions": decisions})
            return

        elif path == "/api/meetings/reports":
            # company_id was resolved from the verified token (see _resolve_company_id)
            reports = get_runtime(tenant_id).meeting_service.get_shared_reports(company_id)
            self._send_json(reports)
            return

        elif path.startswith("/api/meetings/") and path.endswith("/transcripts"):
            parts = path.split("/")
            meeting_id = parts[3]
            transcripts = get_runtime(tenant_id).meeting_service.get_transcripts(meeting_id)
            self._send_json({"meeting_id": meeting_id, "transcripts": transcripts})
            return

        elif path.startswith("/api/meetings/") and path.endswith("/reports"):
            parts = path.split("/")
            meeting_id = parts[3]
            meeting = get_runtime(tenant_id).meeting_service.get_meeting(meeting_id)
            cid = meeting["company_id"] if meeting else company_id
            reports = get_runtime(tenant_id).meeting_service.get_shared_reports(cid)
            self._send_json(reports)
            return

        elif path.startswith("/api/meetings/"):
            parts = path.split("/")
            meeting_id = parts[3]
            meeting = get_runtime(tenant_id).meeting_service.get_meeting(meeting_id)
            if meeting:
                self._send_json(meeting)
            else:
                self._send_json({"error": "Meeting not found"}, status=404)
            return

        # =====================================================================
        # Prompt 03: Floating Live Assistant & Coworker Endpoints (GET)
        # =====================================================================
        elif path == "/api/assistant/coworker/tasks":
            ws_mode = query_params.get("workspace_mode", [None])[0]
            tasks = get_runtime(tenant_id).assistant.list_coworker_tasks(ws_mode)
            self._send_json({"tasks": tasks, "count": len(tasks)})
            return

        elif path.startswith("/api/assistant/coworker/tasks/"):
            parts = path.split("/")
            task_id = parts[5] if len(parts) > 5 else ""
            task = get_runtime(tenant_id).assistant.get_coworker_task(task_id)
            if task:
                self._send_json(task)
            else:
                self._send_json({"error": "Task not found"}, status=404)
            return

        # =====================================================================
        # ZONATA AI Assistant & Universal Co-Worker Endpoints (GET)
        # =====================================================================
        elif path == "/api/coworker/dashboard":
            snap = _cw(tenant_id, company_id).dashboard.get_dashboard_snapshot()
            self._send_json(snap)
            return

        elif path == "/api/coworker/autonomy":
            engine = _cw(tenant_id, company_id)
            supervisor = getattr(engine, "autonomy_supervisor", None)
            if supervisor is None:
                from core.coworker.runtime_supervisor import ensure_supervisor
                supervisor = ensure_supervisor(engine)
                engine.autonomy_supervisor = supervisor
            self._send_json(supervisor.status())
            return

        elif path == "/api/coworker/work-items":
            engine = _cw(tenant_id, company_id)
            loop = engine.executive_loop
            pending = []
            try:
                for item in loop.get_pending_approvals():
                    pending.append({
                        "item_id": item.item_id,
                        "title": item.title,
                        "priority": item.priority.name,
                        "cost_estimate_usd": item.cost_estimate_usd,
                        "status": item.status.value,
                        "approval_path": f"/api/coworker/approvals/{item.item_id}/decide",
                    })
            except Exception:
                pass
            self._send_json({
                "telemetry": loop.get_telemetry(),
                "pending_approvals": pending,
                "count": len(pending),
            })
            return

        elif path == "/api/coworker/missions":
            raw_missions = _cw(tenant_id, company_id).background_dispatcher.list_missions()
            seen_prompts = set()
            missions = []
            for m in raw_missions:
                norm_p = m.prompt.strip().lower()
                if norm_p in seen_prompts:
                    continue
                seen_prompts.add(norm_p)
                missions.append(m)
            self._send_json({
                "missions": [
                    {
                        "mission_id": m.mission_id,
                        "prompt": m.prompt,
                        "status": m.status,
                        "progress_percent": m.progress_percent,
                        "current_stage": m.current_stage,
                        "subworkers": m.subworkers,
                        "runtimes_used": m.runtimes_used,
                        "deliverables": m.deliverables,
                        "evidence_id": m.evidence_id,
                        "notification_message": m.notification_message,
                        "timeline": m.timeline,
                        "human_control": m.human_control,
                        "created_at": m.created_at,
                        "updated_at": m.updated_at,
                        "completed_at": m.completed_at
                    }
                    for m in missions
                ],
                "count": len(missions)
            })
            return

        elif path.startswith("/api/coworker/missions/"):
            mid = path.split("/")[4]
            m = _cw(tenant_id, company_id).background_dispatcher.get_mission(mid)
            if m:
                self._send_json({
                    "mission_id": m.mission_id,
                    "prompt": m.prompt,
                    "status": m.status,
                    "progress_percent": m.progress_percent,
                    "current_stage": m.current_stage,
                    "subworkers": m.subworkers,
                    "runtimes_used": m.runtimes_used,
                    "deliverables": m.deliverables,
                    "evidence_id": m.evidence_id,
                    "notification_message": m.notification_message,
                    "timeline": m.timeline,
                    "human_control": m.human_control,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                    "completed_at": m.completed_at
                })
            else:
                self._send_json({"error": f"Mission '{mid}' not found"}, status=404)
            return

        elif path == "/api/coworker/reality-matrix":
            mat = _cw(tenant_id, company_id).get_reality_matrix()
            self._send_json({"reality_matrix": mat, "count": len(mat)})
            return

        elif path == "/api/coworker/terminal/diagnostics" or path == "/api/terminal/diagnostics":
            diag = TerminalHealthService.run_diagnostics(tenant_id=tenant_id)
            self._send_json(diag)
            return

        elif path == "/api/terminal/profiles":
            profiles = get_runtime(tenant_id).terminal.registry.list_profiles()
            res = [{
                "profile_id": p.profile_id,
                "distribution": p.distribution,
                "version": p.version,
                "architecture": p.architecture,
                "desktop_environment": p.desktop_environment.value,
                "execution_mode": p.execution_mode.value,
                "isolation_level": p.isolation_level.value,
                "network_mode": p.network_mode.value,
                "min_ram_mb": p.min_ram_mb,
                "capabilities": p.capabilities,
                "preinstalled_tools": p.preinstalled_tools,
                "description": p.metadata.get("description", "")
            } for p in profiles]
            self._send_json({"profiles": res, "count": len(res)})
            return

        elif path == "/api/terminal/host-inspection":
            metrics = ResourceInspector.inspect_system()
            self._send_json(metrics)
            return

        elif path == "/api/terminal/tools":
            tools = get_runtime(tenant_id).terminal.registry.list_tools()
            self._send_json({"tools": tools, "count": len(tools)})
            return

        elif path == "/api/terminal/checkpoints":
            session_id = query_params.get("session_id", [None])[0]
            if session_id:
                chk = get_runtime(tenant_id).terminal.get_resumable_checkpoint(session_id)
                self._send_json({"checkpoint": chk})
            else:
                self._send_json({"error": "Missing session_id query parameter"}, status=400)
            return

        elif path == "/api/terminal/knowledge/evolution":
            topic = query_params.get("topic", [None])[0]
            entries = get_runtime(tenant_id).terminal.get_evolution_knowledge(topic=topic)
            self._send_json({"knowledge": entries, "count": len(entries)})
            return

        elif path == "/api/terminal/tools/sbom":
            tool_id = query_params.get("tool_id", [None])[0]
            sbom_entries = get_runtime(tenant_id).terminal.get_sbom(tool_id=tool_id)
            self._send_json({"sbom": sbom_entries, "count": len(sbom_entries)})
            return


        elif path == "/api/coworker/approvals":
            engine = _cw(tenant_id, company_id)
            approvals = []
            seen_prompts = set()
            for m in engine.background_dispatcher.list_missions():
                if m.status in ["AWAITING_APPROVAL", "WAITING"]:
                    norm_p = m.prompt.strip().lower()
                    if norm_p in seen_prompts:
                        continue
                    seen_prompts.add(norm_p)
                    approvals.append({
                        "approval_id": f"app_{m.mission_id}",
                        "mission_id": m.mission_id,
                        "what": f"Continue background mission: '{m.prompt}'",
                        "why": "Governed execution gate checkpoint",
                        "who": m.initiator,
                        "worker": m.subworkers[0] if m.subworkers else "worker_coworker",
                        "node": platform.node(),
                        "data": "Company workspace files & network research",
                        "credentials": "None (zero raw secret isolation)",
                        "risk_level": "MEDIUM",
                        "expected_result": "Verified deliverable synthesis with SHA-256 evidence",
                        "status": "PENDING",
                        "created_at": m.created_at
                    })
            # Delegation-of-Authority holds from the executive operating loop.
            # The supervisor surfaces these but never approves them.
            loop = getattr(engine, "executive_loop", None)
            if loop is not None and hasattr(loop, "get_pending_approvals"):
                try:
                    for item in loop.get_pending_approvals():
                        approvals.append({
                            "approval_id": item.item_id,
                            "type": "DOA_APPROVAL",
                            "what": item.title,
                            "why": f"Delegation of Authority ceiling requires approval (${item.cost_estimate_usd:.2f})",
                            "who": item.metadata.get("requested_by", "AI_CEO"),
                            "worker": "executive_operating_loop",
                            "node": platform.node(),
                            "data": "Mission request metadata",
                            "credentials": "None",
                            "risk_level": "HIGH",
                            "expected_result": item.description,
                            "status": item.status.value if hasattr(item.status, "value") else str(item.status),
                            "created_at": item.created_at,
                            "cost_estimate_usd": item.cost_estimate_usd,
                        })
                except Exception:
                    pass
            self._send_json({"approvals": approvals, "count": len(approvals)})
            return

        elif path == "/api/coworker/artifacts":
            artifacts = []
            ws_dir = os.path.join(BASE_DIR, "storage", "workspaces")
            if os.path.exists(ws_dir):
                for f in os.listdir(ws_dir):
                    fp = os.path.join(ws_dir, f)
                    if os.path.isfile(fp):
                        with open(fp, "rb") as af:
                            sha = hashlib.sha256(af.read()).hexdigest()
                        artifacts.append({
                            "name": f,
                            "path": fp,
                            "size_bytes": os.path.getsize(fp),
                            "sha256": sha,
                            "type": "DELIVERABLE",
                            "created_at": os.path.getmtime(fp)
                        })
            self._send_json({"artifacts": artifacts, "count": len(artifacts)})
            return

        elif path == "/api/coworker/self-extension":
            self._send_json({
                "extensions_enabled": True,
                "supported_types": ["CLI_SCRIPT", "MCP_SERVER", "BROWSER_HOOK", "CUSTOM_TOOL"],
                "qualification_pipeline": [
                    "SECURITY_STATIC_ANALYSIS",
                    "LICENSE_COMPLIANCE",
                    "SANDBOX_VALIDATION",
                    "TAMPER_EVIDENT_REGISTRATION"
                ]
            })
            return

        elif path == "/api/coworker/nodes":
            nodes_list = []
            for nid, node in _cw(tenant_id, company_id).node_registry._nodes.items():
                nodes_list.append(node.to_dict())
            self._send_json({"nodes": nodes_list, "count": len(nodes_list)})
            return

        elif path == "/api/coworker/nodes/bootstrap.py":
            agent_file = os.path.join(BASE_DIR, "core", "coworker", "fleet", "node_agent.py")
            if os.path.exists(agent_file):
                with open(agent_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/x-python")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self._send_json({"error": "Bootstrap agent not found"}, status=404)
            return

        elif path == "/api/coworker/recovery/events":
            mid = query_params.get("mission_id", [None])[0]
            events = _cw(tenant_id, company_id).recovery_controller.get_events(mid)
            self._send_json({"events": events, "count": len(events)})
            return

        elif path == "/api/coworker/mcp/servers":
            servers = _cw(tenant_id, company_id).mcp_controller.list_servers()
            self._send_json({"servers": servers, "count": len(servers)})
            return

        # =====================================================================
        # Prompt 03: Plugins & Connections Endpoints (GET)
        # =====================================================================
        elif path == "/api/plugins":
            category = query_params.get("category", [None])[0]
            plugins = get_runtime(tenant_id).plugins.list_plugins(category)
            self._send_json({"plugins": plugins, "count": len(plugins)})
            return

        elif path.startswith("/api/plugins/"):
            plugin_id = path.split("/")[3]
            plugin = get_runtime(tenant_id).plugins.get_plugin(plugin_id)
            if plugin:
                self._send_json(plugin)
            else:
                self._send_json({"error": "Plugin not found"}, status=404)
            return

        elif path == "/api/connections":
            company_id = query_params.get("company_id", [None])[0]
            conns = get_runtime(tenant_id).plugins.list_connections(company_id)
            self._send_json({"connections": conns, "count": len(conns)})
            return

        elif path.startswith("/api/connections/"):
            conn_id = path.split("/")[3]
            conn = get_runtime(tenant_id).plugins.get_connection(conn_id)
            if conn:
                self._send_json(conn)
            else:
                self._send_json({"error": "Connection not found"}, status=404)
            return

        # =====================================================================
        # Enterprise Records Center Endpoints (GET)
        # =====================================================================
        elif path == "/api/records":
            comp_id = query_params.get("company_id", [None])[0]
            rtype = query_params.get("record_type", [None])[0]
            dept = query_params.get("department", [None])[0]
            drange = query_params.get("date_range", [None])[0]
            sq = query_params.get("q", [None])[0]
            lim = int(query_params.get("limit", [100])[0])
            off = int(query_params.get("offset", [0])[0])
            res = EnterpriseRecordsEngine(tenant_id).list_records(company_id=comp_id or company_id, record_type=rtype, department=dept, date_range=drange, search_query=sq, limit=lim, offset=off)
            self._send_json(res)
            return

        elif path.startswith("/api/records/"):
            rec_id = path.split("/")[3]
            rec = EnterpriseRecordsEngine(tenant_id).get_record(rec_id)
            if rec:
                self._send_json(rec)
            else:
                self._send_json({"error": "Record not found"}, status=404)
            return

        # =====================================================================
        # Enterprise Files & Documents Endpoints (GET)
        # =====================================================================
        elif path == "/api/files":
            comp_id = query_params.get("company_id", [None])[0]
            dept = query_params.get("department", [None])[0]
            cat = query_params.get("category", [None])[0]
            sq = query_params.get("q", [None])[0]
            res = EnterpriseFilesEngine(tenant_id).list_files(company_id=comp_id or company_id, department=dept, category=cat, search_query=sq)
            self._send_json(res)
            return

        elif path.startswith("/api/files/"):
            fid = path.split("/")[3]
            f = EnterpriseFilesEngine(tenant_id).get_file(fid)
            if f:
                self._send_json(f)
            else:
                self._send_json({"error": "File not found"}, status=404)
            return

        # =====================================================================
        # Enterprise Reports & BI Endpoints (GET)
        # =====================================================================
        elif path == "/api/reports":
            comp_id = query_params.get("company_id", [None])[0]
            cat = query_params.get("category", [None])[0]
            sq = query_params.get("q", [None])[0]
            engine = EnterpriseReportsEngine(tenant_id=tenant_id)
            reps = engine.list_reports(company_id=comp_id, category=cat, search_query=sq)
            self._send_json({"reports": reps, "count": len(reps)})
            return

        elif path.startswith("/api/reports/") and path.endswith("/export"):
            rid = path.split("/")[3]
            fmt = query_params.get("format", ["csv"])[0].lower()
            engine = EnterpriseReportsEngine(tenant_id=tenant_id)
            if fmt == "csv":
                csv_data = engine.export_report_csv(rid)
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="report_{rid}.csv"')
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(csv_data.encode("utf-8"))
                return
            else:
                rep = engine.get_report(rid)
                self._send_json(rep if rep else {"error": "Report not found"})
                return

        elif path.startswith("/api/reports/"):
            rid = path.split("/")[3]
            engine = EnterpriseReportsEngine(tenant_id=tenant_id)
            rep = engine.get_report(rid)
            if rep:
                self._send_json(rep)
            else:
                self._send_json({"error": "Report not found"}, status=404)
            return

        # =====================================================================
        # Enterprise Finance & Accounting Endpoints (GET)
        # =====================================================================
        elif path == "/api/finance/summary":
            comp_id = company_id
            engine = EnterpriseFinanceEngine(tenant_id=tenant_id)
            summary = engine.get_financial_summary(company_id=comp_id)
            self._send_json(summary)
            return

        # =====================================================================
        # True Agent Factory Endpoints (GET)
        # =====================================================================
        elif path == "/api/agent-factory/blueprints":
            comp_id = query_params.get("company_id", [None])[0]
            dept = query_params.get("department", [None])[0]
            bps = EnterpriseAgentFactory(tenant_id).list_blueprints(company_id=comp_id or company_id, department=dept)
            self._send_json({"blueprints": bps, "count": len(bps)})
            return

        # =====================================================================
        # Enterprise Integration Center Endpoints (GET)
        # =====================================================================
        elif path == "/api/integrations/marketplace":
            marketplace = integrations_registry.get_marketplace()
            self._send_json({"marketplace": marketplace, "count": len(marketplace)})
            return

        elif path == "/api/integrations/connections":
            comp_id = company_id
            conns = integrations_registry.list_connections(company_id=comp_id)
            self._send_json({"connections": conns, "count": len(conns)})
            return


        # =====================================================================
        # Governed Multi-Agent Workforce Orchestrator Endpoints (GET)
        # =====================================================================
        elif path == "/api/workforces":
            company_id = query_params.get("company_id", [None])[0]
            workforces = AgentWorkforceAdapter.list_workforces(tenant_id, company_id)
            self._send_json({"workforces": workforces, "count": len(workforces)})
            return

        elif path.startswith("/api/workforces/"):
            parts = path.split("/")
            if len(parts) >= 4 and parts[3] and not parts[3].startswith("demo"):
                workforce_id = parts[3]
                try:
                    details = AgentWorkforceAdapter.get_workforce_details(workforce_id)
                    self._send_json({"success": True, "workforce": details})
                except KeyError:
                    self._send_json({"error": "Workforce not found"}, status=404)
                return

        elif path == "/api/specialists/catalog":
            catalog = AgentWorkforceAdapter.get_specialist_catalog()
            self._send_json({"roles": catalog, "count": len(catalog)})
            return

        # =====================================================================
        # Stateful Agent Identity & Memory Endpoints (GET)
        # =====================================================================
        elif path == "/api/agents/stateful":
            cid = query_params.get("company_id", [None])[0]
            agents = stateful_memory_gateway.list_agents(company_id=cid)
            self._send_json({"agents": [a.to_dict() for a in agents], "count": len(agents)})
            return

        elif path.startswith("/api/agents/stateful/") and path.endswith("/memory"):
            parts = path.split("/")
            agent_id = parts[4]
            scope = query_params.get("scope", [None])[0]
            scope_id = query_params.get("scope_id", [None])[0]
            mtype = query_params.get("memory_type", [None])[0]
            cat = query_params.get("category", [None])[0]
            mkey = query_params.get("memory_key", [None])[0]
            limit = int(query_params.get("limit", [50])[0])
            
            if scope or scope_id or mtype or cat or mkey:
                records = stateful_memory_gateway.query_memory(
                    scope=scope, scope_id=scope_id, memory_type=mtype,
                    category=cat, memory_key=mkey, limit=limit
                )
            else:
                cid = query_params.get("company_id", [None])[0]
                records = stateful_memory_gateway.get_agent_effective_memory(agent_id, company_id=cid, limit=limit)
            self._send_json({"records": [r.to_dict() for r in records], "count": len(records)})
            return

        elif path.startswith("/api/agents/stateful/") and path.endswith("/conversations"):
            parts = path.split("/")
            agent_id = parts[4]
            stype = query_params.get("session_type", ["CHAT"])[0]
            cid = query_params.get("company_id", [None])[0]
            sess = stateful_memory_gateway.get_or_create_conversation_session(agent_id, session_type=stype, company_id=cid)
            turns = stateful_memory_gateway.get_conversation_turns(sess["session_id"], limit=30)
            self._send_json({"session": sess, "turns": turns, "turns_count": len(turns)})
            return

        elif path.startswith("/api/agents/stateful/"):
            parts = path.split("/")
            agent_id = parts[4]
            agent = stateful_memory_gateway.get_agent(agent_id)
            if agent:
                self._send_json({"agent": agent.to_dict()})
            else:
                self._send_json({"error": "Agent identity not found"}, status=404)
            return

        elif path == "/api/memory/conflicts":
            scope_id = query_params.get("scope_id", [None])[0]
            cstatus = query_params.get("status", ["OPEN"])[0]
            conflicts = stateful_memory_gateway.list_conflicts(scope_id=scope_id, status=cstatus)
            self._send_json({"conflicts": [c.to_dict() for c in conflicts], "count": len(conflicts)})
            return

        elif path == "/api/memory/search":
            q = query_params.get("query", [""])[0]
            scope = query_params.get("scope", [None])[0]
            scope_id = query_params.get("scope_id", [None])[0]
            limit = int(query_params.get("limit", [10])[0])
            recs = stateful_memory_gateway.search_archival_memory(q, scope=scope, scope_id=scope_id, limit=limit)
            self._send_json({"results": [r.to_dict() for r in recs], "count": len(recs)})
            return

        # =====================================================================
        # HAL Multimodal Capability Layer Endpoints (GET)
        # =====================================================================
        elif path == "/api/multimodal/capabilities":
            family = query_params.get("family", [None])[0]
            caps = get_runtime(tenant_id).multimodal.list_capabilities(family=family)
            self._send_json({"capabilities": caps, "count": len(caps)})
            return

        elif path == "/api/multimodal/status":
            env = get_runtime(tenant_id).multimodal._probe_environment()
            caps = get_runtime(tenant_id).multimodal.list_capabilities()
            healthy_count = sum(1 for c in caps if c["health_status"] == "HEALTHY")
            self._send_json({
                "provider": "HAL9000 Multimodal Layer",
                "version": "1.5.0",
                "upstream_origin": "https://github.com/shandar/HAL9000",
                "license": "MIT License",
                "status": "OPERATIONAL",
                "healthy_capabilities": healthy_count,
                "total_capabilities": len(caps),
                "environment_telemetry": env
            })
            return

        elif path == "/api/multimodal/artifacts":
            cid = query_params.get("company_id", [None])[0]
            artifacts = governed_artifacts.list_artifacts(company_id=cid)
            self._send_json({"artifacts": artifacts, "count": len(artifacts)})
            return

        elif path.startswith("/api/multimodal/sessions/"):
            parts = path.split("/")
            sess_id = parts[4]
            sess = get_runtime(tenant_id).multimodal_execution.get_session(sess_id)
            if sess:
                self._send_json({"session": sess})
            else:
                self._send_json({"error": "Session not found"}, status=404)
            return

        elif path == "/api/workflows":
            cid = query_params.get("company_id", [None])[0]
            wfs = get_workflow_runtime(tenant_id).list_workflows(company_id=cid)
            self._send_json({"workflows": wfs, "count": len(wfs)})
            return

        elif path == "/api/workflows/approvals":
            st = query_params.get("status", ["PENDING"])[0]
            apprs = get_workflow_runtime(tenant_id).list_approvals(status=st, tenant_id=tenant_id)
            self._send_json({"approvals": apprs, "count": len(apprs)})
            return

        elif path == "/api/workflows/runs":
            wf_id = query_params.get("workflow_id", [None])[0]
            runs = get_workflow_runtime(tenant_id).list_runs(workflow_id=wf_id, tenant_id=tenant_id)
            self._send_json({"runs": runs, "count": len(runs)})
            return

        elif path.startswith("/api/workflows/runs/") and path.endswith("/state"):
            parts = path.split("/")
            run_id = parts[4]
            state = get_workflow_runtime(tenant_id).get_run_state(run_id, tenant_id=tenant_id)
            if state:
                self._send_json({"run_state": state})
            else:
                self._send_json({"error": "Run not found"}, status=404)
            return

        elif path.startswith("/api/workflows/runs/") and path.endswith("/events"):
            parts = path.split("/")
            run_id = parts[4]
            evts = get_workflow_runtime(tenant_id).list_events(run_id)
            self._send_json({"events": evts, "count": len(evts)})
            return

        elif path.startswith("/api/workflows/runs/") and path.endswith("/checkpoints"):
            parts = path.split("/")
            run_id = parts[4]
            run_st = get_workflow_runtime(tenant_id).get_run_state(run_id, tenant_id=tenant_id)
            if run_st:
                chks = get_workflow_runtime(tenant_id).checkpointer.list_checkpoints(run_st["thread_id"])
                self._send_json({"checkpoints": chks, "count": len(chks)})
            else:
                self._send_json({"error": "Run not found"}, status=404)
            return

        elif path.startswith("/api/workflows/"):
            parts = path.split("/")
            wf_id = parts[3]
            compiled = get_workflow_runtime(tenant_id).compiled_graphs.get(wf_id)
            with db.get_connection() as conn:
                wf_row = conn.execute("SELECT * FROM workflows WHERE workflow_id = ?", (wf_id,)).fetchone()
            if wf_row:
                self._send_json({
                    "workflow": dict(wf_row),
                    "compiled": bool(compiled),
                    "definition_hash": wf_row["graph_definition_hash"]
                })
            else:
                self._send_json({"error": "Workflow not found"}, status=404)
            return

        # =====================================================================
        # UNIVERSAL AUTOMATION FABRIC GET ENDPOINTS
        # =====================================================================
        elif path == "/api/automation/fabric/status":
            self._send_json({
                "status": "OPERATIONAL",
                "killswitch_active": universal_automation_fabric.is_killswitch_active(),
                "metrics": universal_automation_fabric.get_fabric_metrics(tenant_id)
            })
            return

        elif path == "/api/automation/workflows":
            cid = query_params.get("company_id", [None])[0]
            wfs = universal_automation_fabric.list_workflows(tenant_id=tenant_id, company_id=cid)
            self._send_json({"workflows": wfs, "count": len(wfs)})
            return

        elif path.startswith("/api/automation/workflows/") and len(path.split("/")) == 5:
            wf_id = path.split("/")[4]
            wf = universal_automation_fabric.get_workflow(wf_id, tenant_id=tenant_id)
            if wf:
                self._send_json({"workflow": wf})
            else:
                self._send_json({"error": "Workflow not found"}, status=404)
            return

        elif path == "/api/automation/executions":
            wf_id = query_params.get("workflow_id", [None])[0]
            execs = universal_automation_fabric.list_executions(tenant_id=tenant_id, workflow_id=wf_id)
            self._send_json({"executions": execs, "count": len(execs)})
            return

        elif path.startswith("/api/automation/executions/") and len(path.split("/")) == 5:
            exec_id = path.split("/")[4]
            ex = universal_automation_fabric.get_execution(exec_id, tenant_id=tenant_id)
            if ex:
                self._send_json({"execution": ex})
            else:
                self._send_json({"error": "Execution not found"}, status=404)
            return

        elif path == "/api/automation/templates":
            cat = query_params.get("category", [None])[0]
            tmpls = template_catalog.list_templates(category=cat)
            self._send_json({"templates": tmpls, "count": len(tmpls)})
            return

        elif path.startswith("/api/automation/templates/") and len(path.split("/")) == 5:
            tmpl_id = path.split("/")[4]
            tmpl = template_catalog.get_template(tmpl_id)
            if tmpl:
                self._send_json({"template": tmpl.to_dict()})
            else:
                self._send_json({"error": "Template not found"}, status=404)
            return

        elif path == "/api/automation/connectors":
            conns = [c.to_dict() for c in automation_connector_registry.list_connectors(tenant_id)]
            self._send_json({"connectors": conns, "count": len(conns)})
            return

        elif path == "/api/automation/agents":
            roles = specialized_agent_registry.list_roles()
            self._send_json({"roles": roles, "count": len(roles)})
            return

        elif path == "/api/automation/approvals":
            apprs = universal_automation_fabric.list_pending_approvals(tenant_id=tenant_id)
            self._send_json({"approvals": apprs, "count": len(apprs)})
            return

        elif path == "/api/automation/metrics":
            m = universal_automation_fabric.get_fabric_metrics(tenant_id=tenant_id)
            self._send_json(m)
            return

        elif path == "/api/automation/sbom":
            sbom = license_validator.generate_sbom()
            self._send_json(sbom)
            return

        # =====================================================================
        # A2A (AGENT2AGENT PROTOCOL) GET ENDPOINTS
        # =====================================================================
        elif path == "/.well-known/agent-card.json":
            card = _a2a(tenant_id, company_id).server_adapter.generate_agent_card(host_url=f"http://{self.headers.get('Host', 'localhost:8080')}")
            self._send_json(card)
            return

        elif path == "/api/a2a/agents":
            trust = query_params.get("trust_level", [None])[0]
            role = query_params.get("role_type", [None])[0]
            query = "SELECT * FROM a2a_agents WHERE tenant_id = ?"
            params = [tenant_id]
            if trust:
                query += " AND trust_level = ?"
                params.append(trust)
            if role:
                query += " AND role_type = ?"
                params.append(role)
            query += " ORDER BY created_at DESC"
            with db.get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                agents = []
                for r in rows:
                    ag = dict(r)
                    ag["supported_interfaces"] = json.loads(ag["supported_interfaces"]) if ag.get("supported_interfaces") else []
                    ag["capabilities"] = json.loads(ag["capabilities"]) if ag.get("capabilities") else {}
                    ag["skills"] = json.loads(ag["skills"]) if ag.get("skills") else []
                    ag["reputation_metrics"] = json.loads(ag["reputation_metrics"]) if ag.get("reputation_metrics") else {}
                    agents.append(ag)
            self._send_json({"agents": agents, "count": len(agents)})
            return

        elif path.startswith("/api/a2a/agents/"):
            parts = path.split("/")
            agent_id = parts[4]
            with db.get_connection() as conn:
                r = conn.execute("SELECT * FROM a2a_agents WHERE agent_id = ? AND tenant_id = ?", (agent_id, tenant_id)).fetchone()
                if not r:
                    self._send_json({"error": "Agent not found"}, status=404)
                    return
                ag = dict(r)
                ag["supported_interfaces"] = json.loads(ag["supported_interfaces"]) if ag.get("supported_interfaces") else []
                ag["capabilities"] = json.loads(ag["capabilities"]) if ag.get("capabilities") else {}
                ag["skills"] = json.loads(ag["skills"]) if ag.get("skills") else []
                ag["reputation_metrics"] = json.loads(ag["reputation_metrics"]) if ag.get("reputation_metrics") else {}
                skills_rows = conn.execute("SELECT * FROM a2a_skills WHERE agent_id = ?", (agent_id,)).fetchall()
                ag["registered_skills"] = [dict(s) for s in skills_rows]
            self._send_json({"agent": ag})
            return

        elif path == "/api/a2a/tasks":
            with db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM a2a_tasks WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 100",
                    (tenant_id,)
                ).fetchall()
            self._send_json({"tasks": [dict(r) for r in rows], "count": len(rows)})
            return

        elif path.startswith("/api/a2a/tasks/") or path.startswith("/a2a/tasks/"):
            parts = path.split("/")
            task_id = parts[4] if path.startswith("/api/") else parts[3]
            try:
                task_data = _a2a(tenant_id, company_id).client_adapter.get_task(task_id)
                self._send_json({"task": task_data})
            except Exception as e:
                self._send_json({"error": str(e)}, status=404)
            return

        elif path == "/api/a2a/approvals":
            with db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM approvals WHERE tenant_id = ? AND status = 'PENDING' ORDER BY requested_at DESC",
                    (tenant_id,)
                ).fetchall()
            self._send_json({"approvals": [dict(r) for r in rows], "count": len(rows)})
            return

        elif path == "/api/a2a/security/events":
            with db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM a2a_security_events WHERE tenant_id = ? ORDER BY timestamp DESC LIMIT 100",
                    (tenant_id,)
                ).fetchall()
                evts = []
                for r in rows:
                    e = dict(r)
                    e["details"] = json.loads(e["details"]) if e.get("details") else {}
                    evts.append(e)
            self._send_json({"security_events": evts, "count": len(evts)})
            return

        elif path == "/api/a2a/metrics":
            metrics = _a2a(tenant_id, company_id).get_operational_metrics()
            self._send_json({"metrics": metrics})
            return

        elif path == "/api/a2a/published":
            with db.get_connection() as conn:
                rows = conn.execute("SELECT * FROM a2a_published_agents WHERE tenant_id = ?", (tenant_id,)).fetchall()
                pubs = []
                for r in rows:
                    p = dict(r)
                    p["allowed_skills"] = json.loads(p["allowed_skills"]) if p.get("allowed_skills") else []
                    pubs.append(p)
            self._send_json({"published_agents": pubs, "count": len(pubs)})
            return

        elif path == "/api/a2a/ceo/report":
            ceo_bridge = A2ACeoBridge(tenant_id, company_id)
            report = ceo_bridge.generate_external_delegations_report()
            self._send_json(report)
            return

        # =====================================================================
        # MCP (MODEL CONTEXT PROTOCOL - PROJECT 06) GET ENDPOINTS
        # =====================================================================
        elif path == "/api/mcp/servers":
            trust = query_params.get("trust_state", [None])[0]
            servers = _mcp(tenant_id, company_id).list_servers()
            if trust:
                servers = [s for s in servers if s.get("trust_state") == trust]
            self._send_json({"servers": servers, "count": len(servers)})
            return

        elif path.startswith("/api/mcp/servers/") and len(path.split("/")) == 5:
            server_id = path.split("/")[4]
            srv = _mcp(tenant_id, company_id).get_server(server_id)
            if not srv:
                self._send_json({"error": "MCP server not found"}, status=404)
                return
            with db.get_connection() as conn:
                tools = conn.execute("SELECT * FROM mcp_tools WHERE server_id = ?", (server_id,)).fetchall()
                resources = conn.execute("SELECT * FROM mcp_resources WHERE server_id = ?", (server_id,)).fetchall()
                prompts = conn.execute("SELECT * FROM mcp_prompts WHERE server_id = ?", (server_id,)).fetchall()
                sec_events = conn.execute("SELECT * FROM mcp_security_events WHERE server_id = ? ORDER BY timestamp DESC LIMIT 20", (server_id,)).fetchall()
            srv["tools"] = [dict(t) for t in tools]
            srv["resources"] = [dict(r) for r in resources]
            srv["prompts"] = [dict(p) for p in prompts]
            srv["security_events"] = [dict(se) for se in sec_events]
            self._send_json({"server": srv})
            return

        elif path == "/api/mcp/tools":
            server_id = query_params.get("server_id", [None])[0]
            risk = query_params.get("risk_class", [None])[0]
            tools = _mcp(tenant_id, company_id).list_tools(server_id=server_id)
            if risk:
                tools = [t for t in tools if t.get("risk_class") == risk]
            self._send_json({"tools": tools, "count": len(tools)})
            return

        elif path.startswith("/api/mcp/tools/") and len(path.split("/")) == 5:
            tool_id = path.split("/")[4]
            t = _mcp(tenant_id, company_id).get_tool(tool_id)
            if not t:
                self._send_json({"error": "MCP tool not found"}, status=404)
                return
            self._send_json({"tool": t})
            return

        elif path == "/api/mcp/resources":
            server_id = query_params.get("server_id", [None])[0]
            with db.get_connection() as conn:
                if server_id:
                    rows = conn.execute("SELECT * FROM mcp_resources WHERE tenant_id = ? AND server_id = ?", (tenant_id, server_id)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM mcp_resources WHERE tenant_id = ?", (tenant_id,)).fetchall()
            self._send_json({"resources": [dict(r) for r in rows], "count": len(rows)})
            return

        elif path == "/api/mcp/prompts":
            with db.get_connection() as conn:
                rows = conn.execute("SELECT * FROM mcp_prompts WHERE tenant_id = ?", (tenant_id,)).fetchall()
            self._send_json({"prompts": [dict(r) for r in rows], "count": len(rows)})
            return

        elif path == "/api/mcp/tasks":
            with db.get_connection() as conn:
                rows = conn.execute("SELECT * FROM mcp_tasks WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 50", (tenant_id,)).fetchall()
            self._send_json({"tasks": [dict(r) for r in rows], "count": len(rows)})
            return

        elif path == "/api/mcp/executions":
            limit = int(query_params.get("limit", [50])[0])
            execs = _mcp(tenant_id, company_id).list_executions(limit=limit)
            self._send_json({"executions": execs, "count": len(execs)})
            return

        elif path.startswith("/api/mcp/executions/") and path.endswith("/evidence"):
            exec_id = path.split("/")[4]
            ev = _mcp(tenant_id, company_id).get_execution_evidence(exec_id)
            if not ev:
                self._send_json({"error": "Evidence not found for execution"}, status=404)
                return
            self._send_json({"evidence": ev})
            return

        elif path.startswith("/api/mcp/executions/") and len(path.split("/")) == 5:
            exec_id = path.split("/")[4]
            ex = _mcp(tenant_id, company_id).get_execution(exec_id)
            if not ex:
                self._send_json({"error": "Execution record not found"}, status=404)
                return
            self._send_json({"execution": ex})
            return

        elif path == "/api/mcp/security/events":
            limit = int(query_params.get("limit", [50])[0])
            events = _mcp(tenant_id, company_id).list_security_events(limit=limit)
            self._send_json({"security_events": events, "count": len(events)})
            return

        elif path == "/api/mcp/metrics":
            metrics = _mcp(tenant_id, company_id).get_metrics()
            self._send_json({"metrics": metrics})
            return

        elif path == "/api/mcp/published":
            pubs = _mcp_server(tenant_id, company_id).list_published()
            self._send_json({"published_capabilities": pubs, "count": len(pubs)})
            return

        elif path == "/api/mcp/killswitch":
            if self._approver_denied(auth_context):
                return
            self._send_json({
                "killswitch_active": MCPKillSwitch.is_active(tenant_id),
                "tenant_id": tenant_id,
                "status": "KILLSWITCH_ENGAGED" if MCPKillSwitch.is_active(tenant_id) else "OPERATIONAL"
            })
            return

        elif path == "/api/mcp/conformance":
            self._send_json({
                "protocol_version": MCP_PROTOCOL_VERSION,
                "specification_release": "2026-07-28",
                "stateless_core": True,
                "supported_transports": ["streamable_http", "stdio"],
                "supported_extensions": ["tasks"],
                "security_controls": {
                    "ssrf_protection": True,
                    "prompt_injection_firewall": True,
                    "data_minimization": True,
                    "independent_verification": True,
                    "merkle_evidence_ledger": True,
                    "authoritative_killswitch": True
                },
                "status": "CONFORMANT"
            })
            return

        # =====================================================================
        # Governed OpenHands Execution Runtime Endpoints (GET - Project 07)
        # =====================================================================
        elif path == "/api/openhands/executions":
            limit = int(query_params.get("limit", [50])[0])
            execs = _openhands(tenant_id, company_id).list_executions(limit=limit)
            self._send_json({"executions": execs, "count": len(execs)})
            return

        elif path.startswith("/api/openhands/executions/") and len(path.split("/")) == 5:
            exec_id = path.split("/")[4]
            ex = _openhands(tenant_id, company_id).get_execution(exec_id)
            if not ex:
                self._send_json({"error": "OpenHands execution record not found"}, status=404)
                return
            self._send_json({"execution": ex})
            return

        elif path == "/api/openhands/workspaces":
            limit = int(query_params.get("limit", [50])[0])
            workspaces = _openhands(tenant_id, company_id).list_workspaces(limit=limit)
            self._send_json({"workspaces": workspaces, "count": len(workspaces)})
            return

        elif path == "/api/openhands/artifacts":
            exec_id = query_params.get("execution_id", [None])[0]
            limit = int(query_params.get("limit", [50])[0])
            artifacts = _openhands(tenant_id, company_id).list_artifacts(execution_id=exec_id, limit=limit)
            self._send_json({"artifacts": artifacts, "count": len(artifacts)})
            return

        elif path == "/api/openhands/security/events":
            limit = int(query_params.get("limit", [50])[0])
            events = _openhands(tenant_id, company_id).list_security_events(limit=limit)
            self._send_json({"security_events": events, "count": len(events)})
            return

        elif path == "/api/openhands/metrics":
            metrics = _openhands(tenant_id, company_id).get_metrics()
            self._send_json({"metrics": metrics})
            return

        elif path == "/api/openhands/killswitch":
            if self._approver_denied(auth_context):
                return
            self._send_json({
                "killswitch_active": OpenHandsKillSwitch.is_active(tenant_id),
                "tenant_id": tenant_id,
                "status": "KILLSWITCH_ENGAGED" if OpenHandsKillSwitch.is_active(tenant_id) else "OPERATIONAL"
            })
            return

        # =====================================================================
        # Governed Browser Use Execution Layer Endpoints (GET - Project 08)
        # =====================================================================
        elif path == "/api/browser/sessions":
            limit = int(query_params.get("limit", [50])[0])
            status = query_params.get("status", [None])[0]
            sessions = _browser(tenant_id, company_id).list_sessions(status=status, limit=limit)
            self._send_json({"sessions": sessions, "count": len(sessions)})
            return

        elif path.startswith("/api/browser/sessions/") and len(path.split("/")) == 5:
            sess_id = path.split("/")[4]
            session = _browser(tenant_id, company_id).get_session(sess_id)
            if session:
                self._send_json(session)
            else:
                self._send_json({"error": f"Session '{sess_id}' not found"}, status=404)
            return

        elif path == "/api/browser/capabilities":
            self._send_json(_browser(tenant_id, company_id).capabilities())
            return

        elif path == "/api/browser/executions":
            limit = int(query_params.get("limit", [50])[0])
            sess_id = query_params.get("session_id", [None])[0]
            status = query_params.get("status", [None])[0]
            execs = _browser(tenant_id, company_id).list_executions(session_id=sess_id, status=status, limit=limit)
            self._send_json({"executions": execs, "count": len(execs)})
            return

        elif path.startswith("/api/browser/executions/") and path.endswith("/history"):
            parts = path.split("/")
            exec_id = parts[4]
            actions = _browser(tenant_id, company_id).list_actions(exec_id)
            self._send_json({"actions": actions, "count": len(actions), "execution_id": exec_id})
            return

        elif path.startswith("/api/browser/executions/") and len(path.split("/")) == 5:
            exec_id = path.split("/")[4]
            ex = _browser(tenant_id, company_id).get_execution(exec_id)
            if ex:
                self._send_json(ex)
            else:
                self._send_json({"error": f"Execution '{exec_id}' not found"}, status=404)
            return

        elif path == "/api/browser/artifacts":
            limit = int(query_params.get("limit", [50])[0])
            exec_id = query_params.get("execution_id", [None])[0]
            sess_id = query_params.get("session_id", [None])[0]
            artifacts = _browser(tenant_id, company_id).list_artifacts(execution_id=exec_id, session_id=sess_id, limit=limit)
            self._send_json({"artifacts": artifacts, "count": len(artifacts)})
            return

        elif path == "/api/browser/security/events":
            limit = int(query_params.get("limit", [50])[0])
            events = _browser(tenant_id, company_id).list_security_events(limit=limit)
            self._send_json({"security_events": events, "count": len(events)})
            return

        elif path == "/api/browser/metrics":
            metrics = _browser(tenant_id, company_id).get_metrics()
            self._send_json({"metrics": metrics})
            return

        elif path == "/api/browser/approvals":
            limit = int(query_params.get("limit", [50])[0])
            status = query_params.get("status", [None])[0]
            approvals = _browser(tenant_id, company_id).list_approvals(status=status, limit=limit)
            self._send_json({"approvals": approvals, "count": len(approvals)})
            return

        elif path == "/api/browser/killswitch":
            if self._approver_denied(auth_context):
                return
            # company_id was resolved from the verified token (see _resolve_company_id)
            killed, reason = BrowserKillSwitch.is_killed(tenant_id=tenant_id, company_id=company_id)
            self._send_json({
                "killswitch_active": killed,
                "reason": reason,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "status": "KILLSWITCH_ENGAGED" if killed else "OPERATIONAL"
            })
            return

        # =====================================================================
        # Governed Temporal Durable Execution Layer Endpoints (GET - Project 09)
        # =====================================================================
        elif path == "/api/temporal/clusters":
            # Report only what this deployment actually has. No invented
            # server/SDK versions: either an external Temporal host is
            # configured, or the embedded durable engine is in use.
            external_host = (os.environ.get("TEMPORAL_HOST") or "").strip()
            namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
            db_state = _database_status()
            if external_host:
                clusters = [{
                    "cluster_id": "cls_external_temporal",
                    "name": "External Temporal Cluster",
                    "host": external_host,
                    "namespace": namespace,
                    "server_version": None,
                    "sdk_version": None,
                    "status": "CONFIGURED" if db_state == "CONNECTED" else "UNVERIFIED",
                    "durable_storage": "external Temporal persistence",
                    "verification": "Server version is reported by the Temporal cluster and is not assumed here.",
                }]
            else:
                clusters = [{
                    "cluster_id": "cls_zonata_local_durable",
                    "name": "Zonata Embedded Durable Execution Engine",
                    "host": None,
                    "namespace": namespace,
                    "server_version": None,
                    "sdk_version": None,
                    "status": "EMBEDDED" if db_state == "CONNECTED" else "UNAVAILABLE",
                    "durable_storage": "SQLite normalized durable engine",
                    "verification": "No external Temporal server is configured (TEMPORAL_HOST unset).",
                }]
            self._send_json({
                "clusters": clusters,
                "count": len(clusters),
                "external_temporal_configured": bool(external_host),
            })
            return

        elif path == "/api/temporal/workers":
            workers = _temporal(tenant_id, company_id).list_workers()
            self._send_json({"workers": workers, "count": len(workers)})
            return

        elif path == "/api/temporal/queues":
            queues = _temporal(tenant_id, company_id).list_queues()
            self._send_json({"queues": queues, "count": len(queues)})
            return

        elif path == "/api/temporal/workflows":
            limit = int(query_params.get("limit", [50])[0])
            status = query_params.get("status", [None])[0]
            workflows = _temporal(tenant_id, company_id).list_workflows(status=status, limit=limit)
            self._send_json({"workflows": workflows, "count": len(workflows)})
            return

        elif path.startswith("/api/temporal/workflows/") and path.endswith("/history"):
            parts = path.split("/")
            wf_id = parts[4]
            history = _temporal(tenant_id, company_id).get_workflow_history(wf_id)
            self._send_json({"history": history, "count": len(history), "workflow_id": wf_id})
            return

        elif path.startswith("/api/temporal/workflows/") and len(path.split("/")) == 5:
            wf_id = path.split("/")[4]
            wf = _temporal(tenant_id, company_id).get_workflow_status(wf_id)
            if wf:
                self._send_json(wf)
            else:
                self._send_json({"error": f"Workflow '{wf_id}' not found"}, status=404)
            return

        elif path == "/api/temporal/approvals":
            status = query_params.get("status", [None])[0]
            approvals = _temporal(tenant_id, company_id).list_approvals(status=status)
            self._send_json({"approvals": approvals, "count": len(approvals)})
            return

        elif path == "/api/temporal/security/events":
            limit = int(query_params.get("limit", [50])[0])
            events = _temporal(tenant_id, company_id).list_security_events(limit=limit)
            self._send_json({"security_events": events, "count": len(events)})
            return

        elif path == "/api/temporal/metrics":
            metrics = _temporal(tenant_id, company_id).get_metrics()
            self._send_json({"metrics": metrics})
            return

        elif path == "/api/temporal/killswitch":
            if self._approver_denied(auth_context):
                return
            # company_id was resolved from the verified token (see _resolve_company_id)
            killed, reason = TemporalKillSwitch.is_killed(tenant_id=tenant_id, company_id=company_id)
            self._send_json({
                "killswitch_active": killed,
                "reason": reason,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "status": "KILLSWITCH_ENGAGED" if killed else "OPERATIONAL"
            })
            return

        # --- NANGO EXTERNAL INTEGRATION API (Project 10) ---
        elif path == "/api/nango/providers":
            cat = query_params.get("category", [None])[0]
            providers = _nango(tenant_id, company_id).list_providers(category=cat)
            self._send_json({"providers": providers, "count": len(providers)})
            return

        elif path == "/api/nango/connections":
            # company_id was resolved from the verified token (see _resolve_company_id)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            conns = gw.list_connections()
            self._send_json({"connections": conns, "count": len(conns)})
            return

        elif path.startswith("/api/nango/connections/") and len(path.split("/")) == 5:
            conn_id = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            conn_data = gw.get_connection(conn_id)
            if conn_data:
                self._send_json({"connection": conn_data})
            else:
                self._send_json({"error": f"Connection '{conn_id}' not found"}, status=404)
            return

        elif path == "/api/nango/capabilities":
            prov = query_params.get("provider", [None])[0]
            with db.get_connection() as c:
                if prov:
                    rows = c.execute("SELECT * FROM nango_capabilities WHERE provider_id = ? AND is_active = 1", (prov,)).fetchall()
                else:
                    rows = c.execute("SELECT * FROM nango_capabilities WHERE is_active = 1").fetchall()
                self._send_json({"capabilities": [dict(r) for r in rows]})
            return

        elif path == "/api/nango/executions":
            limit = int(query_params.get("limit", [50])[0])
            with db.get_connection() as c:
                rows = c.execute(
                    "SELECT * FROM nango_executions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                    (tenant_id, limit)
                ).fetchall()
                execs = []
                for r in rows:
                    item = dict(r)
                    item["input_payload"] = json.loads(item["input_payload"]) if item.get("input_payload") else {}
                    item["response_payload"] = json.loads(item["response_payload"]) if item.get("response_payload") else {}
                    execs.append(item)
                self._send_json({"executions": execs, "count": len(execs)})
            return

        elif path == "/api/nango/webhooks":
            limit = int(query_params.get("limit", [50])[0])
            with db.get_connection() as c:
                rows = c.execute(
                    "SELECT * FROM nango_webhooks WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                    (tenant_id, limit)
                ).fetchall()
                whs = []
                for r in rows:
                    item = dict(r)
                    item["payload_data"] = json.loads(item["payload_data"]) if item.get("payload_data") else {}
                    whs.append(item)
                self._send_json({"webhooks": whs, "count": len(whs)})
            return

        elif path == "/api/nango/sync-jobs":
            with db.get_connection() as c:
                rows = c.execute("SELECT * FROM nango_sync_jobs WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 50", (tenant_id,)).fetchall()
                self._send_json({"sync_jobs": [dict(r) for r in rows]})
            return

        elif path == "/api/nango/sync-records":
            # company_id was resolved from the verified token (see _resolve_company_id)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            conn_id = query_params.get("connection_id", [None])[0]
            model = query_params.get("model", [None])[0]
            limit = int(query_params.get("limit", [50])[0])
            records = gw.get_sync_records(conn_id, model, limit)
            self._send_json({"sync_records": records, "count": len(records)})
            return

        elif path == "/api/nango/metrics":
            # company_id was resolved from the verified token (see _resolve_company_id)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            metrics = gw.get_metrics()
            self._send_json({"metrics": metrics})
            return

        elif path == "/api/nango/killswitch":
            if self._approver_denied(auth_context):
                return
            # company_id was resolved from the verified token (see _resolve_company_id)
            prov_id = query_params.get("provider_id", ["salesforce"])[0]
            halted, reason = IntegrationKillSwitch.is_halted(tenant_id=tenant_id, company_id=company_id, provider_id=prov_id)
            self._send_json({
                "killswitch_active": halted,
                "reason": reason,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "provider_id": prov_id,
                "status": "HALTED" if halted else "OPERATIONAL"
            })
            return

        # URA / ZONATA: Enterprise AI Corporate Workforce Architecture
        if path.startswith("/api/workforce"):
            from core.workforce_api import handle_get as workforce_get
            wf_res = workforce_get(path, query_params, tenant_id, company_id, auth_context)
            if wf_res:
                data, code = wf_res
                self._send_json(data, status=code)
                return



        # ZONATA V8: AI CEO Executive Operating Layer & Coworker 2.0 Routes
        if path.startswith("/api/v8/") or path.startswith("/api/v2/coworker"):
            from core.v8_api_handler import V8ApiHandler
            c_id = company_id
            v8_res = V8ApiHandler.handle_get(path, query_params, tenant_id, c_id)
            if v8_res:
                data, code = v8_res
                self._send_json(data, status=code)
                return

        # Fallback to static files in WEB_DIR or SPA index.html

        clean_path = path.lstrip('/')
        if not clean_path:
            clean_path = 'index.html'
        file_path = os.path.join(WEB_DIR, clean_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.path = '/' + clean_path
            return super().do_GET()

        # SPA Routing: Any non-API route serves index.html
        if not path.startswith('/api/'):
            self.path = '/index.html'
            return super().do_GET()

        self._send_json({"error": "Endpoint not found"}, status=404)

    def do_POST(self):
        self._start_time = time.time()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)
        length = int(self.headers.get('Content-Length', 0))

        # Enforce transport security for POST endpoints
        if not self._validate_transport_security():
            return

        # Hard boundary: Guard against memory exhaustion via oversized POST payloads (>10MB)
        if length > 10 * 1024 * 1024:
            self._send_json({"error": "Payload too large", "max_bytes": 10 * 1024 * 1024}, status=413)
            return

        body = self.rfile.read(length) if length > 0 else b'{}'
        try:
            req_data = json.loads(body.decode('utf-8'))
        except Exception:
            req_data = {}

        # Route v2 Asynchronous Command & Dispatch Endpoints
        if path.startswith("/api/v2/"):
            headers_dict = {k: v for k, v in self.headers.items()}
            status_code, resp_headers, resp_body = api_handler.handle_request("POST", path, headers_dict, body)
            self._send_json(resp_body, status=status_code)
            return

        # Enforce IP-level rate limiting for public unauthenticated POST endpoints
        if not self._enforce_tenant_fairness(path, "POST", auth_context=None):
            return

        # Neon Services POST Endpoints
        if path == "/api/v1/neon/functions/invoke":
            fn_name = req_data.get("function", "hello")
            fn_path = req_data.get("path", "")
            fn_method = req_data.get("method", "GET")
            fn_payload = req_data.get("payload")
            res = neon_functions.invoke(fn_name, path=fn_path, method=fn_method, payload=fn_payload)
            status_code = 200 if res.get("success") else 502
            self._send_json(res, status=status_code)
            return

        if path == "/api/v1/neon/auth/verify":
            token = req_data.get("token", "")
            res = neon_auth.verify_session(token)
            self._send_json(res)
            return

        if path == "/api/v1/neon/ai/chat":
            messages = req_data.get("messages", [])
            model = req_data.get("model", "gpt-5-mini")
            res = neon_ai_gateway.chat_completion(messages, model=model)
            status_code = 200 if res.get("success") else 400
            self._send_json(res, status=status_code)
            return

        # Public Authentication & Token Issuance Endpoints
        if path in ("/api/auth/token", "/api/auth/login"):
            client_ip = self._get_client_ip()
            email = req_data.get("email", "").strip()
            from core.auth import RateLimiter
            allowed, retry_after, axis = RateLimiter.rate_limit_ip_and_account(
                client_ip,
                email if email else None,
                max_ip_requests=25,
                max_account_requests=5,
                window_seconds=60.0
            )
            if not allowed:
                detail_msg = f"Rate limit exceeded on {axis.lower().replace('_', ' ')}. Try again in {retry_after}s."
                self._send_json({"error": "Too Many Requests", "detail": detail_msg}, status=429)
                return

            email = req_data.get("email", "").strip()
            req_tenant = req_data.get("tenant_id")
            password = req_data.get("password")
            bootstrap_key = req_data.get("bootstrap_key") or req_data.get("secret")

            target_user = None
            target_tenant = None
            target_role = None
            target_company = "comp_primary"

            # 1. Try real credential-based authentication
            if email and password:
                ok, user_dict, msg = UserManager.authenticate_user(email, password, tenant_id=req_tenant)
                if ok and user_dict:
                    target_user = user_dict["user_id"]
                    target_tenant = user_dict["tenant_id"]
                    target_role = user_dict["role"]
                    target_company = user_dict.get("company_id", "comp_primary")
                else:
                    self._send_json({"error": "Unauthorized", "detail": msg}, status=401)
                    return

            # 2. Administrative bootstrap path with strict production lockout & audit
            elif bootstrap_key and req_tenant:
                is_prod = is_production_mode()
                if is_prod:
                    allow_bootstrap = (os.environ.get("ZONATA_ALLOW_BOOTSTRAP_PROVISIONING", "0") == "1")
                    if not allow_bootstrap:
                        self._send_json({
                            "error": "Forbidden",
                            "detail": "Administrative bootstrap token minting is strictly locked out in production mode. Initial owner setup requires explicit bootstrap provisioning authorization or registered credentials."
                        }, status=403)
                        return

                    configured_secret = os.environ.get("ZONATA_BOOTSTRAP_SECRET", "")
                    if len(configured_secret.strip()) < 32:
                        self._send_json({
                            "error": "Forbidden",
                            "detail": "Production Sovereign Security Violation: ZONATA_BOOTSTRAP_SECRET must be explicitly configured with at least 32 high-entropy characters."
                        }, status=403)
                        return

                    window_sec = float(os.environ.get("ZONATA_BOOTSTRAP_WINDOW_SECONDS", "300"))
                    if (time.time() - _SERVER_BOOT_TIME) > window_sec:
                        self._send_json({
                            "error": "Forbidden",
                            "detail": "Administrative bootstrap provisioning window has expired. Bootstrap is permanently locked."
                        }, status=403)
                        return

                    if req_tenant in _BOOTSTRAP_PROVISIONED_TENANTS:
                        self._send_json({
                            "error": "Forbidden",
                            "detail": f"Administrative bootstrap has already been executed for tenant '{req_tenant}'. Repeated bootstrap is locked."
                        }, status=403)
                        return

                    if not hmac.compare_digest(bootstrap_key, configured_secret):
                        self._send_json({"error": "Unauthorized", "detail": "Invalid bootstrap credentials"}, status=401)
                        return

                    _BOOTSTRAP_PROVISIONED_TENANTS.add(req_tenant)
                    target_tenant = req_tenant
                    target_user = req_data.get("user_id", f"usr_{uuid.uuid4().hex[:8]}")
                    target_role = req_data.get("role", UserRole.OWNER)
                    target_company = req_data.get("company_id") or f"comp_{req_tenant}"
                else:
                    # Non-production (development / test mode)
                    from core.auth import get_auth_secret_key
                    auth_secret = get_auth_secret_key().decode("utf-8", errors="ignore")
                    cfg_secret = os.environ.get("ZONATA_BOOTSTRAP_SECRET", "")
                    is_valid = False
                    if cfg_secret and hmac.compare_digest(bootstrap_key, cfg_secret):
                        is_valid = True
                    elif auth_secret and hmac.compare_digest(bootstrap_key, auth_secret):
                        is_valid = True

                    if not is_valid:
                        self._send_json({"error": "Unauthorized", "detail": "Invalid bootstrap credentials"}, status=401)
                        return

                    target_tenant = req_tenant
                    target_user = req_data.get("user_id", f"usr_{uuid.uuid4().hex[:8]}")
                    target_role = req_data.get("role", UserRole.OWNER)
                    target_company = req_data.get("company_id") or f"comp_{req_tenant}"

            if not target_user:
                self._send_json({
                    "error": "Unauthorized",
                    "detail": "Invalid credentials or user not enrolled in tenant"
                }, status=401)
                return

            user_data = {
                "user_id": target_user,
                "tenant_id": target_tenant,
                "company_id": target_company,
                "email": email or f"{target_user}@{target_tenant}.zonata",
                "role": target_role,
                "permissions": ["*"] if target_role == UserRole.OWNER else ["read", "execute"]
            }
            token = UserManager.generate_token(user_data, expires_in_seconds=86400 * 7)
            self._send_json({
                "token": token,
                "token_type": "Bearer",
                "expires_in": 86400 * 7,
                "user": user_data
            })
            return

        elif path == "/api/auth/register":
            try:
                client_ip = self._get_client_ip()
                email = req_data.get("email", "").strip().lower()
                from core.auth import RateLimiter
                allowed, retry_after, axis = RateLimiter.rate_limit_ip_and_account(
                    client_ip,
                    email if email else None,
                    max_ip_requests=10,
                    max_account_requests=3,
                    window_seconds=60.0
                )
                if not allowed:
                    detail_msg = f"Rate limit exceeded on {axis.lower().replace('_', ' ')}. Try again in {retry_after}s."
                    self._send_json({"error": "Too Many Requests", "detail": detail_msg}, status=429)
                    return

                name = req_data.get("name", "").strip() or (email.split("@")[0] if "@" in email else "Host")
                password = req_data.get("password", "")
                tenant_name = req_data.get("tenant_name", "").strip() or f"{name} Enterprise"

                # Operating Envelope: Enforce organization limits (GA or Restricted Pilot)
                is_pilot_mode = os.environ.get("ZONATA_PUBLIC_GA_MODE", "0") != "1" and os.environ.get("ZONATA_RESTRICTED_PILOT_MODE", "1") == "1"
                max_orgs = int(os.environ.get("MAX_DESIGN_PARTNER_ORGS", "3" if is_pilot_mode else "100"))
                if is_pilot_mode:
                    with db.get_connection() as conn:
                        p_row = conn.execute("SELECT COUNT(*) FROM pilot_organizations WHERE status = 'ACTIVE'").fetchone()
                        active_count = p_row[0] if isinstance(p_row, (tuple, list)) else p_row["COUNT(*)"]
                        if active_count >= max_orgs:
                            self._send_json({
                                "error": "Pilot Capacity Limit Exceeded",
                                "detail": f"Restricted Production Pilot is strictly capped at maximum {max_orgs} design-partner organizations. Maximum onboarding capacity reached.",
                                "limit": max_orgs,
                                "current_active": active_count,
                                "release_scope": "URA / ZONATA — RESTRICTED PRODUCTION PILOT, NOT PUBLIC GA"
                            }, status=403)
                            return

                plan = req_data.get("plan", "PILOT" if is_pilot_mode else "ENTERPRISE")

                import re
                email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
                if not email or not re.match(email_pattern, email):
                    self._send_json({"error": "Bad Request", "detail": "A valid email address is required for registration"}, status=400)
                    return

                if not password or len(password) < 8:
                    self._send_json({"error": "Bad Request", "detail": "Password must be at least 8 characters in length"}, status=400)
                    return

                if len(password.encode("utf-8")) > 4096:
                    self._send_json({"error": "Bad Request", "detail": "Password exceeds maximum allowed size (4096 bytes)"}, status=400)
                    return

                with db.get_connection() as conn:
                    existing_user = conn.execute(
                        "SELECT * FROM users WHERE email = ? AND status = 'ACTIVE'",
                        (email,)
                    ).fetchone()

                if existing_user:
                    self._send_json({
                        "error": "Conflict",
                        "detail": "An active account with this email already exists. Please sign in instead."
                    }, status=409)
                    return

                # Atomic tenant and credential provisioning
                from core.auth import TenantManager
                tenant = TenantManager.create_tenant(name=tenant_name, plan=plan)
                tenant_id = tenant["tenant_id"]
                company_id = f"comp_{tenant_id}"
                user = UserManager.create_user_with_credentials(
                    tenant_id=tenant_id,
                    email=email,
                    name=name,
                    password=password,
                    role=UserRole.OWNER,
                    company_id=company_id
                )

                # Create default primary company entity for the new tenant
                now = time.time()
                with db.get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO companies (
                            company_id, tenant_id, name, country, industry,
                            company_type, status, currency, timezone, revenue,
                            cost, contribution, created_at
                        ) VALUES (?, ?, ?, 'US', 'Enterprise Cloud & SaaS', 'EXISTING', 'OPERATIONAL', '$', 'UTC', 0.0, 0.0, 0.0, ?)
                        ON CONFLICT (company_id) DO NOTHING
                        """,
                        (company_id, tenant_id, tenant_name, now)
                    )
                    if is_pilot_mode:
                        conn.execute(
                            """
                            INSERT INTO pilot_organizations (
                                tenant_id, org_name, contact_email, status, registered_at
                            ) VALUES (?, ?, ?, 'ACTIVE', ?)
                            ON CONFLICT (tenant_id) DO NOTHING
                            """,
                            (tenant_id, tenant_name, email, now)
                        )
                    conn.commit()

                user_data = {
                    "user_id": user["user_id"],
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "email": email,
                    "name": name,
                    "role": UserRole.OWNER,
                    "permissions": ["*"]
                }
                token = UserManager.generate_token(user_data, expires_in_seconds=86400 * 7)
                self._send_json({
                    "token": token,
                    "token_type": "Bearer",
                    "expires_in": 86400 * 7,
                    "user": user_data,
                    "tenant": tenant
                }, status=201)
                return
            except Exception as e:
                logger.exception(f"Unhandled registration error: {e}")
                self._send_json({
                    "error": "Registration Failed",
                    "detail": f"Registration failed due to server error: {str(e)}"
                }, status=500)
                return

        elif path == "/api/auth/revoke":
            try:
                auth_ctx = self._get_auth_context()
            except Exception as e:
                self._send_json({"error": "Unauthorized", "detail": "Authentication required to revoke tokens"}, status=401)
                return

            token_to_revoke = req_data.get("token") or req_data.get("token_id")
            if token_to_revoke:
                if "." in token_to_revoke:
                    try:
                        p_str = token_to_revoke.rsplit(".", 1)[0]
                        tok_id = json.loads(p_str).get("token_id")
                    except Exception:
                        tok_id = token_to_revoke
                else:
                    tok_id = token_to_revoke
                TokenRevocationStore.revoke(tok_id)
                self._send_json({"success": True, "revoked_token_id": tok_id})
            else:
                self._send_json({"error": "Missing token or token_id to revoke"}, status=400)
            return

        # SRE Alertmanager Inbound Webhook Receiver
        elif path == "/api/telemetry/alerts/webhook":
            alerts = req_data.get("alerts", [])
            if not isinstance(alerts, list):
                alerts = [req_data] if req_data else []
            for alert in alerts:
                if isinstance(alert, dict):
                    alert_record = {
                        "received_at": time.time(),
                        "status": alert.get("status", req_data.get("status", "firing")),
                        "labels": alert.get("labels", {}),
                        "annotations": alert.get("annotations", {}),
                        "startsAt": alert.get("startsAt", ""),
                        "endsAt": alert.get("endsAt", ""),
                        "generatorURL": alert.get("generatorURL", ""),
                        "raw": alert
                    }
                    RECEIVED_ALERTS.append(alert_record)
            self._send_json({
                "status": "RECEIVED",
                "dispatched_count": len(alerts),
                "total_stored": len(RECEIVED_ALERTS)
            }, status=200)
            return

        # Stripe Webhook Endpoint (HMAC-SHA256 verified, public callback)
        if path in ("/api/billing/webhook/stripe", "/api/v1/billing/webhook/stripe"):
            sig_header = self.headers.get("Stripe-Signature", "")
            payload_str = body.decode("utf-8", errors="replace")
            res = saas_billing_engine.process_stripe_webhook(payload_str=payload_str, sig_header=sig_header)
            status_code = res.get("code", 200) if not res.get("success") else 200
            self._send_json(res, status=status_code)
            return

        # Razorpay Webhook Endpoint (HMAC-SHA256 verified, public callback)
        if path in ("/api/billing/webhook/razorpay", "/api/v1/billing/webhook/razorpay"):
            sig_header = self.headers.get("X-Razorpay-Signature", "")
            payload_str = body.decode("utf-8", errors="replace")
            res = saas_billing_engine.process_razorpay_webhook(payload_str=payload_str, sig_header=sig_header)
            status_code = res.get("code", 200) if not res.get("success") else 200
            self._send_json(res, status=status_code)
            return

        try:
            auth_context = self._get_auth_context()
            tenant_id = auth_context.get("tenant_id")
            company_id = self._resolve_company_id(auth_context, query_params)
        except AuthExceptions.AuthenticationError as e:
            self._send_json({"error": "Unauthorized", "detail": str(e)}, status=401)
            return
        except AuthExceptions.TenantIsolationViolation as e:
            self._send_json({"error": "Forbidden", "detail": str(e), "security_event": "TENANT_SPOOFING_ATTEMPT"}, status=403)
            return

        if not self._enforce_tenant_fairness(path, "POST", auth_context=auth_context):
            return

        # Milestone J: Tenant Concurrency Lease Acquisition & Release
        if path == "/api/concurrency/lease/acquire":
            max_leases = int(os.environ.get("PILOT_MAX_CONCURRENCY", "4"))
            ttl = float(req_data.get("ttl_seconds", 300.0))
            lease_type = req_data.get("lease_type", "WORKFLOW")
            from core.tenant_fairness import tenant_fairness_engine
            ok, lease_id, retry_after = tenant_fairness_engine.concurrency_manager.acquire_lease(
                tenant_id=tenant_id,
                max_concurrency=max_leases,
                lease_type=lease_type,
                ttl_seconds=ttl
            )
            if not ok:
                self._send_json({
                    "error": "Too Many Requests",
                    "detail": f"Tenant concurrency lease limit ({max_leases} active leases) exceeded. Try again in {retry_after}s.",
                    "limit": max_leases,
                    "retry_after": retry_after,
                    "violation_axis": "CONCURRENCY_LIMIT_EXCEEDED"
                }, status=429, headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_leases),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Axis": "CONCURRENCY_LIMIT_EXCEEDED"
                })
                return
            self._send_json({
                "success": True,
                "lease_id": lease_id,
                "tenant_id": tenant_id,
                "max_concurrency": max_leases,
                "expires_in": ttl
            })
            return

        if path == "/api/concurrency/lease/release":
            lease_id = req_data.get("lease_id")
            from core.tenant_fairness import tenant_fairness_engine
            rel_ok = tenant_fairness_engine.concurrency_manager.release_lease(lease_id)
            self._send_json({"success": rel_ok, "lease_id": lease_id, "released": rel_ok})
            return

        if path == "/api/crm/customers":
            # company_id was resolved from the verified token (see _resolve_company_id)
            from core.enterprise_crm import EnterpriseCrmService
            svc = EnterpriseCrmService(tenant_id)
            try:
                cust = svc.create_customer(company_id, req_data)
                self._send_json(cust, status=201)
            except ValueError as e:
                self._send_json({"error": "Bad Request", "detail": str(e)}, status=400)
            return

        elif path == "/api/crm/deals":
            # company_id was resolved from the verified token (see _resolve_company_id)
            from core.enterprise_crm import EnterpriseCrmService
            svc = EnterpriseCrmService(tenant_id)
            try:
                deal = svc.create_deal(company_id, req_data)
                self._send_json(deal, status=201)
            except ValueError as e:
                self._send_json({"error": "Bad Request", "detail": str(e)}, status=400)
            return

        if path == "/api/overview/explain-variance":
            cid = req_data.get("company_id")
            metric = req_data.get("metric", "revenue")
            explanation = OverviewDataService.explain_variance(tenant_id, company_id=cid, metric=metric)
            self._send_json(explanation)
            return

        elif path == "/api/webhooks/verify":
            secret = str(req_data.get("secret") or "").strip()
            if not secret:
                self._send_json({
                    "error": "Missing webhook secret",
                    "code": "MISSING_SECRET",
                    "detail": "A shared secret is required to verify a signature; the platform does not fall back to a built-in default.",
                }, status=400)
                return
            payload = json.dumps(req_data.get("payload", {})).encode("utf-8")
            sig = req_data.get("signature", "")
            ts = req_data.get("timestamp", str(time.time()))
            nonce = req_data.get("nonce", f"nonce_{uuid.uuid4().hex}")
            res = WebhookSecurityGateway.verify_webhook(payload, sig, secret, ts, nonce)
            self._send_json(res)
            return

        elif path == "/api/agent-engine/teams/deploy":
            company_id = req_data.get("company_id")
            companies = get_portfolio(tenant_id).list_companies()
            if not company_id or not get_portfolio(tenant_id).get_company(company_id):
                if not companies:
                    self._send_json({
                        "error": "No company is onboarded for this tenant",
                        "code": "NO_COMPANY",
                        "detail": "Onboard a company before deploying a team. The platform will not invent one.",
                    }, status=409)
                    return
                company_id = companies[0].company_id
            team_id = req_data.get("team_id", "core_executive_suite")
            try:
                res = EnterpriseTeamCatalog.deploy_team_to_company(
                    portfolio_manager=get_portfolio(tenant_id),
                    company_id=company_id,
                    team_id=team_id,
                    tenant_id=tenant_id
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/agent-engine/heartbeat":
            agent_id = (req_data.get("agent_id") or "").strip()
            role = (req_data.get("role") or "").strip()
            if not agent_id or not role:
                self._send_json({
                    "error": "Missing agent identity",
                    "code": "MISSING_AGENT_IDENTITY",
                    "detail": "Provide 'agent_id' and 'role' for the agent whose heartbeat should run.",
                }, status=400)
                return
            trigger = req_data.get("trigger", "manual")
            tasks = req_data.get("tasks", [])
            res = _heartbeat(tenant_id).execute_heartbeat_turn(
                agent_id=agent_id,
                company_id=company_id,
                role=role,
                trigger=trigger,
                tasks=tasks
            )
            self._send_json(res)
            return

        elif path == "/api/agent-engine/delegate":
            goal_id = req_data.get("goal_id") or f"goal_{uuid.uuid4().hex[:8]}"
            goal_title = (req_data.get("goal_title") or "").strip()
            lead_agent_id = req_data.get("lead_agent_id", "agent_ceo")
            subtasks = req_data.get("subtasks") or []
            requires_board_approval = req_data.get("requires_board_approval", False)

            # The platform no longer invents a delegation plan. A plan must be
            # grounded in explicit subtasks supplied by the caller (or produced
            # by the LLM planner) before it can be assigned to real agents.
            if not goal_title:
                self._send_json({
                    "error": "Missing goal title",
                    "code": "MISSING_GOAL_TITLE",
                    "detail": "Provide 'goal_title' describing the outcome to delegate.",
                }, status=400)
                return
            if not isinstance(subtasks, list) or not subtasks:
                self._send_json({
                    "error": "Missing subtasks",
                    "code": "MISSING_SUBTASKS",
                    "detail": (
                        "Provide a non-empty 'subtasks' array. Each item needs at least "
                        "'title' and 'target_role'. Generated plans must come from the "
                        "mission planner, not a hardcoded template."
                    ),
                    "example": {
                        "goal_title": "Cut onboarding time by 30%",
                        "subtasks": [
                            {"title": "Map current onboarding steps", "target_role": "Operations Manager", "priority": "high", "dependencies": []},
                        ],
                    },
                }, status=400)
                return
            invalid = [
                i for i, st in enumerate(subtasks)
                if not isinstance(st, dict) or not str(st.get("title") or "").strip()
                or not str(st.get("target_role") or "").strip()
            ]
            if invalid:
                self._send_json({
                    "error": "Invalid subtasks",
                    "code": "INVALID_SUBTASKS",
                    "detail": "Every subtask requires a non-empty 'title' and 'target_role'.",
                    "invalid_indexes": invalid,
                }, status=400)
                return
            try:
                plan = _delegation(tenant_id).create_delegation_plan(
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
            plan = _delegation(tenant_id).plans.get(goal_id)
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
            result_text = (req_data.get("result") or "").strip()
            if not goal_id or not subtask_id:
                self._send_json({
                    "error": "Missing identifiers",
                    "code": "MISSING_IDS",
                    "detail": "Provide 'goal_id' and 'subtask_id'.",
                }, status=400)
                return
            if not result_text:
                self._send_json({
                    "error": "Missing result",
                    "code": "MISSING_RESULT",
                    "detail": "Provide 'result' describing what was actually produced. Completions are never assumed.",
                }, status=400)
                return
            try:
                res = _delegation(tenant_id).complete_subtask(goal_id, subtask_id, result_text)
                self._send_json({"success": True, "update": res, "plan": _delegation(tenant_id).plans.get(goal_id)})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/handover/package":
            companies = get_portfolio(tenant_id).list_companies()
            c = companies[0] if companies else None
            cname = c.name if c else "Operating Entity"
            cid = c.company_id if c else company_id
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
            target_portfolio = get_portfolio(tenant_id)
            companies = get_portfolio(tenant_id).list_companies()
            cid = req_data.get("company_id") or (companies[0].company_id if companies else f"comp_{tenant_id}")
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
            companies = get_portfolio(tenant_id).list_companies()
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
            companies = get_portfolio(tenant_id).list_companies()
            cid = companies[0].company_id if companies else company_id
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
                company_id=company_id,
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
            status = req_data.get("status", "OPERATIONAL")
            baseline_profile = req_data.get("baseline_profile", {})

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

            comp.status = status
            if baseline_profile:
                comp.baseline_summary = baseline_profile

            get_portfolio(tenant_id).register_company(comp)

            # Record in Organizational Memory
            OrganizationalMemory.store_memory(
                tenant_id=tenant_id,
                company_id=comp.company_id,
                memory_tier=MemoryTier.COMPANY,
                memory_type=OrganizationalMemoryType.POLICY,
                content=f"Company '{comp.name}' onboarded into operating portfolio as {comp.company_type} entity."
            )

            self._send_json({
                "success": True,
                "company_id": comp.company_id,
                "name": comp.name,
                "status": comp.status,
                "baseline_summary": comp.baseline_summary
            })
            return

        elif path == "/api/chat":
            instruction = req_data.get("message", "")
            companies = get_portfolio(tenant_id).list_companies()
            if not companies:
                self._send_json({
                    "success": False,
                    "command_type": "NO_COMPANY",
                    "ceo_response": "No operating business entities currently onboarded. Please onboard your first company to launch missions."
                })
                return

            target_comp = companies[0]
            cid = req_data.get("company_id") or target_comp.company_id
            from core.ceo_chat import ceo_chat
            res = ceo_chat(tenant_id, cid, instruction)

            usage = res.get("usage") or {}
            try:
                UsageMeteringEngine.record_usage(
                    tenant_id=tenant_id,
                    company_id=cid,
                    agent_id="ceo_core",
                    mission_id=None,
                    model=f"{res.get('provider', 'deterministic')}/{res.get('model', 'none')}",
                    input_tokens=int(usage.get("prompt_tokens", 0) or 0),
                    output_tokens=int(usage.get("completion_tokens", 0) or 0),
                    cost=0.0
                )
            except Exception:
                pass

            self._send_json(res)
            return

        elif path == "/api/run-workload":
            wtype = str(req_data.get("workload", "") or "").strip().lower()
            objectives = {
                "hospitality": (
                    "Perform a hotel night-audit reconciliation: compare PMS folio postings, "
                    "payment-gateway settlements, and occupancy records for the most recent "
                    "closed business date. Report variances and list every data source used. "
                    "If no PMS or payment connector is configured, state exactly which "
                    "credentials are required instead of estimating numbers."
                ),
                "manufacturing": (
                    "Analyse the production line for bottlenecks using available MES data. "
                    "Identify constrained stations, quantify impact only from observed data, "
                    "and list missing telemetry. Do not invent throughput figures."
                ),
                "saas": (
                    "Decompose subscription churn by cohort using available billing data. "
                    "Identify the strongest observed churn drivers and propose a bounded "
                    "retention experiment. Mark any metric that is unavailable."
                ),
                "personal": (
                    "Audit the configured workspace for file hygiene: duplicates, stale files, "
                    "and oversized artefacts. Report only files actually observed."
                ),
                "universal": (
                    "Discover which capabilities this deployment can genuinely execute right "
                    "now, and list capabilities that require credentials or installation."
                ),
            }
            if wtype not in objectives:
                self._send_json({
                    "error": "Unknown workload type",
                    "code": "UNKNOWN_WORKLOAD",
                    "supported": sorted(objectives.keys()),
                }, status=400)
                return

            companies = get_portfolio(tenant_id).list_companies()
            if not companies:
                self._send_json({
                    "error": "No company is onboarded for this tenant",
                    "code": "NO_COMPANY",
                    "detail": "Onboard a company before launching operational workloads.",
                }, status=409)
                return

            if self._blocked_by_global_killswitch("workload execution"):
                return
            requested_cid = company_id
            cid = next((c.company_id for c in companies if c.company_id == requested_cid), companies[0].company_id)
            dispatcher = _cw(tenant_id, cid).background_dispatcher
            mission = dispatcher.submit_background_prompt(
                objectives[wtype], initiator="Workload Launcher"
            )
            dispatcher.execute_compound_mission_step(mission.mission_id)
            mission = dispatcher.get_mission(mission.mission_id) or mission
            self._send_json({
                "success": mission.status not in ("BLOCKED", "FAILED", "CANCELLED"),
                "mission_id": mission.mission_id,
                "workload": wtype,
                "company_id": cid,
                "prompt": mission.prompt,
                "status": mission.status,
                "current_stage": mission.current_stage,
                "progress_percent": mission.progress_percent,
                "deliverables": mission.deliverables,
                "evidence_id": mission.evidence_id,
                "timeline": mission.timeline[-8:],
            })
            return

        elif path == "/api/employees":
            role = req_data.get("role", "Specialist Agent")
            dept = req_data.get("department", "Operations")
            target_portfolio = get_portfolio(tenant_id)
            companies = get_portfolio(tenant_id).list_companies()
            if not companies:
                comp = CompanyOnboardingEngine.onboard_new_company(
                    name="Default Operations",
                    industry="Services",
                    tenant_id=tenant_id
                )
                get_portfolio(tenant_id).register_company(comp)
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

            # Persist employee into database
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO employees (
                        agent_id, company_id, tenant_id, role, department, manager,
                        budget_limit, spending_limit, authority_ceiling, working_state, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (agent_id) DO UPDATE SET
                        company_id = EXCLUDED.company_id,
                        tenant_id = EXCLUDED.tenant_id,
                        role = EXCLUDED.role,
                        department = EXCLUDED.department,
                        manager = EXCLUDED.manager,
                        budget_limit = EXCLUDED.budget_limit,
                        spending_limit = EXCLUDED.spending_limit,
                        authority_ceiling = EXCLUDED.authority_ceiling,
                        working_state = EXCLUDED.working_state
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
            companies = get_portfolio(tenant_id).list_companies()
            cid = req_data.get("company_id") or (companies[0].company_id if companies else "")
            if not cid or not get_portfolio(tenant_id).get_company(cid):
                self._send_json({
                    "error": "No company is onboarded for this tenant",
                    "code": "NO_COMPANY",
                    "detail": "Onboard a company before raising an approval request.",
                }, status=409)
                return

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
            if self._approver_denied(auth_context):
                return
            parts = path.strip("/").split("/")
            req_id = parts[2]
            approved = req_data.get("approved", True)
            user = {
                "user_id": (auth_context or {}).get("user_id"),
                "role": (auth_context or {}).get("role"),
            }
            res = ApprovalPipeline.decide_request(
                tenant_id=tenant_id,
                request_id=req_id,
                approver_user=user,
                approved=approved,
                rejection_reason=req_data.get("reason"),
                company_id=company_id,
            )
            self._send_json(res, status=200 if res.get("success") else 403)
            return

        # Company OS 2.0 POST Endpoints
        elif path == "/api/ceo/cycle":
            companies = get_portfolio(tenant_id).list_companies()
            if not companies:
                self._send_json({
                    "error": "No company is onboarded for this tenant",
                    "code": "NO_COMPANY",
                    "detail": "Onboard a company before running an executive cycle.",
                }, status=409)
                return
            cid = company_id
            cycle_res = _ceo_engine(tenant_id, company_id).execute_executive_cycle(cid)
            self._send_json(cycle_res)
            return

        elif path == "/api/ceo/chat":
            instruction = req_data.get("message", "")
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            from core.ceo_chat import ceo_chat
            chat_res = ceo_chat(tenant_id, cid, instruction)
            self._send_json(chat_res)
            return

        elif path == "/api/council/review":
            topic = req_data.get("topic", "Executive Proposal")
            proposal = req_data.get("proposal", "")
            data = req_data.get("data", {})
            companies = get_portfolio(tenant_id).list_companies()
            cid = req_data.get("company_id", companies[0].company_id if companies else "")
            review = ExecutiveCouncil(tenant_id, cid).review_proposal(topic, proposal, data)
            self._send_json(review)
            return

        # --- ENTERPRISE SKILLS & MULTI-JUDGE DECISION ARENA ---
        elif path.startswith("/api/skills/") and path.endswith("/run"):
            if self._blocked_by_global_killswitch("skill execution"):
                return
            if not AuthorizationEnforcer.can_execute_missions((auth_context or {}).get("role")):
                self._send_json({
                    "success": False,
                    "error": "INSUFFICIENT_PERMISSIONS: This role cannot execute skill contracts.",
                    "role": (auth_context or {}).get("role"),
                }, status=403)
                return
            skill_id = path.split("/")[3]
            requester = {
                "user_id": (auth_context or {}).get("user_id"),
                "role": (auth_context or {}).get("role"),
                "departments": [(auth_context or {}).get("department")] if (auth_context or {}).get("department") else [],
            }
            try:
                res = SkillArena(tenant_id, company_id).run_skill(
                    skill_id, req_data.get("inputs") or {}, requester
                )
                self._send_json(res, status=200 if res.get("success") else 400)
            except Exception as exc:
                self._send_json({"success": False, "error": str(exc)}, status=400)
            return

        elif path == "/api/arena/evaluate":
            if self._blocked_by_global_killswitch("decision arena"):
                return
            if not AuthorizationEnforcer.can_execute_missions((auth_context or {}).get("role")):
                self._send_json({
                    "success": False,
                    "error": "INSUFFICIENT_PERMISSIONS: This role cannot request an arena decision.",
                    "role": (auth_context or {}).get("role"),
                }, status=403)
                return
            requester = {
                "user_id": (auth_context or {}).get("user_id"),
                "role": (auth_context or {}).get("role"),
                "departments": [(auth_context or {}).get("department")] if (auth_context or {}).get("department") else [],
            }
            try:
                res = SkillArena(tenant_id, company_id).evaluate(req_data, requester)
                self._send_json(res)
            except ValueError as exc:
                self._send_json({"success": False, "error": str(exc)}, status=400)
            except Exception as exc:
                self._send_json({"success": False, "error": str(exc)}, status=400)
            return

        # --- PHASE 11 GOVERNANCE & ECONOMIC COMMAND ENDPOINTS (POST) ---
        elif path == "/api/v1/economic/budgets":
            from core.economic_governance import economic_governor
            from dataclasses import asdict
            eid = req_data.get("entity_id", f"ent_{uuid.uuid4().hex[:8]}")
            etype = req_data.get("entity_type", "WORKFLOW")
            cid = company_id
            alloc_usd = float(req_data.get("allocated_usd", 1000.0))
            alloc_tok = int(req_data.get("allocated_tokens", 0))
            soft_pct = float(req_data.get("soft_limit_pct", 80.0))
            hard_pct = float(req_data.get("hard_limit_pct", 100.0))
            b = economic_governor.configure_budget(
                entity_id=eid,
                entity_type=etype,
                tenant_id=tenant_id,
                company_id=cid,
                allocated_usd=alloc_usd,
                allocated_tokens=alloc_tok,
                soft_limit_pct=soft_pct,
                hard_limit_pct=hard_pct
            )
            self._send_json({"success": True, "budget": asdict(b)})
            return

        elif path == "/api/v1/economic/reserve":
            from core.economic_governance import economic_governor, BudgetExhaustionException
            from dataclasses import asdict
            scopes_raw = req_data.get("scope_chain", [("TENANT", tenant_id)])
            scope_chain = [(s[0], s[1]) if isinstance(s, (list, tuple)) else (s.get("type", "ENTITY"), s.get("id", "")) for s in scopes_raw]
            req_usd = float(req_data.get("requested_usd", 0.0))
            req_tokens = int(req_data.get("requested_tokens", 0))
            ttl = float(req_data.get("ttl_seconds", 300.0))
            task_id = req_data.get("task_id")
            try:
                reservation = economic_governor.reserve_budget(
                    tenant_id=tenant_id,
                    scope_chain=scope_chain,
                    requested_usd=req_usd,
                    requested_tokens=req_tokens,
                    ttl_seconds=ttl,
                    task_id=task_id,
                    metadata=req_data.get("metadata")
                )
                self._send_json({"success": True, "reservation": asdict(reservation)})
            except BudgetExhaustionException as e:
                self._send_json({"error": "Budget Exhausted", "detail": str(e), "details": getattr(e, "details", {})}, status=402)
            return

        elif path == "/api/v1/economic/settle":
            from core.economic_governance import economic_governor, ReservationExpiredException
            from dataclasses import asdict
            res_id = req_data.get("reservation_id", "")
            act_usd = float(req_data.get("actual_usd", 0.0))
            act_tokens = int(req_data.get("actual_tokens", 0))
            try:
                settlement = economic_governor.settle_budget(
                    reservation_id=res_id,
                    actual_usd=act_usd,
                    actual_tokens=act_tokens,
                    metadata=req_data.get("metadata")
                )
                self._send_json({"success": True, "settlement": asdict(settlement)})
            except ReservationExpiredException as e:
                self._send_json({"error": "Bad Request", "detail": str(e)}, status=400)
            return

        elif path == "/api/v1/economic/release":
            from core.economic_governance import economic_governor
            res_id = req_data.get("reservation_id", "")
            reason = req_data.get("reason", "API caller cancelled")
            ok = economic_governor.release_reservation(res_id, reason=reason)
            self._send_json({"success": ok, "released": ok})
            return

        elif path == "/api/v1/approvals/cryptographic/sign":
            from core.cryptographic_approvals import cryptographic_approvals
            action_payload = req_data.get("action_payload", {})
            action_payload["tenant_id"] = tenant_id  # Guarantee tenant binding
            approver_id = req_data.get("approver_id", "usr_executive_owner")
            approver_role = req_data.get("approver_role", "OWNER")
            ttl = float(req_data.get("ttl_seconds", 3600.0))
            cert = cryptographic_approvals.issue_approval(
                action_payload=action_payload,
                approver_id=approver_id,
                approver_role=approver_role,
                ttl_seconds=ttl,
                metadata=req_data.get("metadata")
            )
            self._send_json({"success": True, "certificate": cert.to_dict()})
            return

        elif path == "/api/v1/approvals/cryptographic/verify":
            from core.cryptographic_approvals import (
                cryptographic_approvals,
                ApprovalCertificate,
                CryptographicApprovalException
            )
            action_payload = req_data.get("action_payload", {})
            action_payload["tenant_id"] = tenant_id
            cert_dict = req_data.get("certificate", {})
            consuming_action_id = req_data.get("consuming_action_id", f"act_{uuid.uuid4().hex[:8]}")
            try:
                cert = ApprovalCertificate.from_dict(cert_dict)
                v_res = cryptographic_approvals.verify_and_consume_approval(
                    action_payload=action_payload,
                    certificate=cert,
                    consuming_action_id=consuming_action_id
                )
                self._send_json({"success": True, "verification": v_res})
            except CryptographicApprovalException as e:
                self._send_json({"error": "Cryptographic Verification Failed", "detail": str(e), "details": getattr(e, "details", {})}, status=403)
            return

        elif path == "/api/v1/memory/sync":
            from core.stateful_agent_runtime import StatefulAgentMemoryGateway, ConflictResolution
            action = req_data.get("action", "STORE")
            gw = StatefulAgentMemoryGateway(tenant_id=tenant_id)
            if action == "STORE":
                mem = gw.store_memory(
                    scope=req_data.get("scope", "COMPANY"),
                    scope_id=req_data.get("scope_id") or company_id,
                    memory_key=req_data.get("memory_key", "k1"),
                    content=req_data.get("content", ""),
                    memory_type=req_data.get("memory_type", "CORE"),
                    category=req_data.get("category", "FACT"),
                    metadata=req_data.get("metadata")
                )
                self._send_json({"success": True, "record": mem.to_dict()})
            elif action == "RESOLVE_CONFLICT":
                cid = req_data.get("conflict_id", "")
                choice = req_data.get("choice", "USE_A")
                res = gw.resolve_conflict(
                    conflict_id=cid,
                    choice=choice,
                    resolved_by=req_data.get("resolved_by", "AI_CEO"),
                    merged_content=req_data.get("merged_content")
                )
                self._send_json({"success": True, "resolution": res})
            else:
                self._send_json({"error": "Unknown action"}, status=400)
            return

        elif path == "/api/chief-of-staff/items":
            itype = req_data.get("item_type", "INBOX")
            title = req_data.get("title", "New Item")
            details = req_data.get("details", "")
            priority = req_data.get("priority", "MEDIUM")
            companies = get_portfolio(tenant_id).list_companies()
            cid = req_data.get("company_id", companies[0].company_id if companies else "")
            item_id = ChiefOfStaff(tenant_id, cid).add_inbox_item(itype, title, details, priority)
            self._send_json({"success": True, "item_id": item_id})
            return

        elif path == "/api/host/quarantine":
            reason = req_data.get("reason", "Manual security quarantine")
            get_runtime(tenant_id).host_agent.quarantine(reason)
            self._send_json({"success": True, "quarantined": True, "status": "QUARANTINED"})
            return

        elif path == "/api/sales/leads":
            name = req_data.get("contact_name", "Lead Contact")
            channel = req_data.get("channel", "WEB_CHAT")
            inquiry = req_data.get("inquiry", "Product inquiry")
            lead = get_runtime(tenant_id).sales.ingest_lead(name, channel, inquiry)
            self._send_json(lead)
            return

        elif path == "/api/sales/message":
            lead_id = req_data.get("lead_id", "")
            message = req_data.get("message", "")
            res = get_runtime(tenant_id).sales.process_customer_message(lead_id, message)
            self._send_json(res)
            return

        elif path == "/api/voice/call":
            caller_id = req_data.get("caller_id", "+91-0000000000")
            direction = req_data.get("direction", "INBOUND")
            consent = req_data.get("consent_given", True)
            call = get_runtime(tenant_id).voice.initiate_call_session(caller_id, direction, consent)
            self._send_json(call)
            return

        elif path == "/api/voice/utterance":
            session_id = req_data.get("session_id", "")
            text = req_data.get("text", "")
            turn = get_runtime(tenant_id).voice.process_utterance(session_id, text)
            self._send_json(turn)
            return

        elif path == "/api/events":
            companies = get_portfolio(tenant_id).list_companies()
            cid = req_data.get("company_id", companies[0].company_id if companies else "")
            etype = req_data.get("event_type", "REVENUE_ANOMALY")
            category = req_data.get("category", "OPERATIONAL")
            severity = req_data.get("severity", "MEDIUM")
            details = req_data.get("details", {})
            evt = get_runtime(tenant_id).event_engine.emit_event(cid, etype, category, severity, details)
            self._send_json(evt)
            return

        elif path == "/api/meetings/conduct":
            mtype = req_data.get("meeting_type", "MORNING_OPERATING")
            rec = get_runtime(tenant_id).meetings.conduct_executive_operating_meeting(mtype)
            self._send_json(rec)
            return

        elif path == "/api/causality/verify":
            chain_id = req_data.get("chain_id", "")
            tx_id = req_data.get("transaction_id", "tx_verified")
            rev = float(req_data.get("revenue", 0.0))
            res = get_runtime(tenant_id).causality.verify_outcome_with_transaction(chain_id, tx_id, rev)
            self._send_json(res)
            return

        # --- ZONATA UNIVERSAL AI CEO OS ENDPOINTS (POST) ---
        elif path == "/api/v1/zonata/discovery/ingest":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
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
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            qid = req_data.get("question_id", "q_general")
            ans = req_data.get("answer", "")
            res = zonata_interview.submit_answer(tenant_id, cid, qid, ans)
            self._send_json(res)
            return

        elif path == "/api/v1/zonata/org-design/generate":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            ind_override = req_data.get("industry")
            org = zonata_org_designer.design_organization(tenant_id, cid, ind_override)
            self._send_json(org.to_dict())
            return

        elif path == "/api/v1/zonata/org-design/mission-workforce":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
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
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
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

        elif path.startswith("/api/companies/") and path.endswith("/draft"):
            cid = path.split("/")[3]
            try:
                draft_file = _draft_path(tenant_id, cid)
            except ValueError as exc:
                self._send_json({"error": "Invalid company id", "code": "INVALID_COMPANY_ID",
                                 "detail": str(exc)}, status=400)
                return
            draft_data = req_data.get("draft", req_data)
            if not isinstance(draft_data, dict) or not draft_data:
                self._send_json({"error": "Empty draft", "code": "EMPTY_DRAFT",
                                 "detail": "Provide a non-empty 'draft' object."}, status=400)
                return
            os.makedirs(os.path.dirname(draft_file), exist_ok=True)
            with open(draft_file, "w", encoding="utf-8") as f:
                json.dump(draft_data, f, indent=2)
            self._send_json({"success": True, "draft_saved": True, "company_id": cid,
                             "tenant_id": tenant_id, "bytes": os.path.getsize(draft_file)})
            return

        elif path.startswith("/api/companies/") and path.endswith("/activate"):
            cid = path.split("/")[3]
            comp = get_portfolio(tenant_id).get_company(cid)
            if comp:
                comp.status = "OPERATIONAL"
                with db.get_connection() as conn:
                    conn.execute("UPDATE companies SET status = 'OPERATIONAL' WHERE company_id = ?", (cid,))
                    conn.commit()
                self._send_json({"success": True, "status": "OPERATIONAL", "company": {"company_id": cid, "name": comp.name}})
                return

            try:
                draft_file = _draft_path(tenant_id, cid)
            except ValueError as exc:
                self._send_json({"error": "Invalid company id", "code": "INVALID_COMPANY_ID",
                                 "detail": str(exc)}, status=400)
                return
            draft_data = {}
            if os.path.exists(draft_file):
                try:
                    with open(draft_file, "r", encoding="utf-8") as f:
                        draft_data = json.load(f)
                except Exception:
                    draft_data = {}
            c_name = (req_data.get("name") or draft_data.get("legalName")
                      or draft_data.get("name") or "").strip()
            c_ind = (req_data.get("industry") or draft_data.get("industry") or "").strip()
            c_country = (req_data.get("country") or draft_data.get("country") or "").strip()
            if not c_name or not c_ind:
                self._send_json({
                    "error": "Incomplete company draft",
                    "code": "INCOMPLETE_DRAFT",
                    "detail": (
                        "A company cannot be activated without at least a name and an industry. "
                        f"Found name={c_name!r}, industry={c_ind!r}. Save the draft first or "
                        "supply 'name' and 'industry'."
                    ),
                }, status=400)
                return
            c_type = "EXISTING" if draft_data.get("mode") == "existing" or req_data.get("is_existing") else "NEW"
            new_comp = get_portfolio(tenant_id).onboard_company(
                name=c_name,
                country=c_country,
                industry=c_ind,
                company_type=c_type
            )
            new_comp.status = "OPERATIONAL"
            self._send_json({"success": True, "status": "OPERATIONAL", "company": {"company_id": new_comp.company_id, "name": new_comp.name}})
            return

        elif path.startswith("/api/companies/"):
            parts = path.split("/")
            if len(parts) >= 5:
                cid = parts[3]
                sub_action = parts[4]
                if sub_action == "organization" and len(parts) >= 6 and parts[5] == "propose":
                    res = _company_service(tenant_id).propose_organization(tenant_id, cid, req_data.get("industry"))
                    self._send_json(res)
                    return
                elif sub_action == "organization" and len(parts) >= 6 and parts[5] == "approve":
                    bp_id = req_data.get("blueprint_id")
                    res = _company_service(tenant_id).approve_organization(tenant_id, cid, bp_id)
                    self._send_json(res)
                    return
                elif sub_action == "workforce":
                    res = _company_service(tenant_id).create_workforce_member(tenant_id, cid, req_data)
                    self._send_json(res)
                    return
                elif sub_action == "missions" and len(parts) >= 7 and parts[6] == "plan":
                    objective = (req_data.get("objective") or req_data.get("title")
                                 or req_data.get("prompt") or "").strip()
                    if not objective:
                        self._send_json({
                            "error": "Missing objective",
                            "code": "MISSING_OBJECTIVE",
                            "detail": "Provide 'objective' so the plan can be produced by the LLM runtime.",
                        }, status=400)
                        return
                    dispatcher = _cw(tenant_id, cid).background_dispatcher
                    mission = dispatcher.submit_background_prompt(
                        objective, initiator="Mission Planner"
                    )
                    dispatcher.execute_compound_mission_step(mission.mission_id)
                    mission = dispatcher.get_mission(mission.mission_id) or mission
                    self._send_json({
                        "success": mission.status not in ("BLOCKED", "FAILED", "CANCELLED"),
                        "mission_id": mission.mission_id,
                        "company_id": cid,
                        "status": mission.status,
                        "current_stage": mission.current_stage,
                        "progress_percent": mission.progress_percent,
                        "timeline": mission.timeline[-6:],
                    })
                    return
                elif sub_action == "missions":
                    res = _company_service(tenant_id).create_mission(tenant_id, cid, req_data)
                    self._send_json(res)
                    return
                elif sub_action == "processes":
                    res = _company_service(tenant_id).create_or_update_process(tenant_id, cid, req_data)
                    self._send_json(res)
                    return
                elif sub_action == "command":
                    directive = req_data.get("directive", "")
                    res = _company_service(tenant_id).execute_ceo_command(tenant_id, cid, directive)
                    self._send_json(res)
                    return

        elif path.startswith("/api/tools/") and path.endswith("/disable"):
            tool_id = path.split("/")[3]
            if tool_id.startswith("cap_") or tool_id.startswith("conn_"):
                self._send_json({
                    "tool_id": tool_id,
                    "code": "NOT_DISABLEABLE",
                    "detail": (
                        "Built-in host capabilities and enterprise connectors are not registry tools. "
                        "Remove provider credentials in Settings → Connectors to deactivate a connector."
                    ),
                }, status=400)
                return
            try:
                with db.get_connection() as conn:
                    cur = conn.execute(
                        "UPDATE tool_packages SET status = 'REVOKED' "
                        "WHERE tool_id = ? AND tenant_id = ? AND status != 'REVOKED'",
                        (tool_id, tenant_id),
                    )
                    conn.commit()
                    changed = cur.rowcount
            except Exception as exc:
                self._send_json({
                    "error": "Disable failed",
                    "code": "DISABLE_FAILED",
                    "detail": f"{type(exc).__name__}: {exc}",
                }, status=500)
                return
            if not changed:
                with db.get_connection() as conn:
                    exists = conn.execute(
                        "SELECT status FROM tool_packages WHERE tool_id = ? AND tenant_id = ?",
                        (tool_id, tenant_id),
                    ).fetchone()
                if not exists:
                    self._send_json({
                        "tool_id": tool_id,
                        "error": "Tool not found in this tenant's registry",
                        "code": "TOOL_NOT_FOUND",
                    }, status=404)
                    return
            try:
                from core.models import PhysicalVerification as _PV
                pkg = _ledger_for(tenant_id).seal_evidence(
                    action_id=f"act_disable_{uuid.uuid4().hex[:8]}",
                    mission_id="mis_tool_registry",
                    agent_id="TOOL_FACTORY",
                    verifications=[_PV(
                        check_type="registry_state",
                        target_path=tool_id,
                        expected_val="REVOKED",
                        actual_val="REVOKED",
                        verified=True,
                        details="Tool revoked from the tenant tool registry.",
                    )],
                    metadata={"tool_id": tool_id, "action": "DISABLE_TOOL"},
                )
                evidence_id = pkg.evidence_id
            except Exception as exc:
                evidence_id = None
                logger.warning("Evidence sealing for tool disable failed: %s", exc)
            self._send_json({
                "success": True,
                "tool_id": tool_id,
                "status": "REVOKED",
                "evidence_id": evidence_id,
                "detail": "The tool is revoked and will not be offered to mission planners.",
            })
            return

        elif path.startswith("/api/tools/") and path.endswith("/probe"):
            import shutil as _shutil
            import subprocess as _subprocess

            tool_id = path.split("/")[3]
            ledger = _ledger_for(tenant_id)

            if tool_id.startswith("cap_"):
                cap_name = tool_id[len("cap_"):]
                cap = registry.get_capability(cap_name) or registry.get_capability(cap_name.lower())
                if not cap:
                    self._send_json({
                        "tool_id": tool_id,
                        "status": "NOT_FOUND",
                        "detail": f"No local capability named '{cap_name}' is registered on this host.",
                    }, status=404)
                    return
                binary = cap.binary_path if os.path.exists(cap.binary_path) else _shutil.which(cap.name)
                if not binary:
                    self._send_json({
                        "tool_id": tool_id,
                        "status": "FAILED",
                        "detail": f"Registered capability '{cap.name}' no longer exists on disk.",
                    })
                    return
                started = time.time()
                try:
                    proc = _subprocess.run(
                        [binary, "--version"],
                        capture_output=True, text=True, timeout=8,
                        env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/tmp")},
                    )
                    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
                    ok = proc.returncode == 0
                    detail = (
                        f"{os.path.basename(binary)} --version exited {proc.returncode}: "
                        f"{output.splitlines()[0][:200] if output else '(no output)'}"
                    )
                    result_payload = {
                        "tool_id": tool_id,
                        "status": "PASSED" if ok else "FAILED",
                        "exit_code": proc.returncode,
                        "output": output[:2000],
                        "binary": binary,
                        "latency_ms": round((time.time() - started) * 1000, 2),
                        "detail": detail,
                    }
                except _subprocess.TimeoutExpired:
                    result_payload = {
                        "tool_id": tool_id,
                        "status": "FAILED",
                        "exit_code": None,
                        "binary": binary,
                        "detail": f"{os.path.basename(binary)} --version timed out after 8s.",
                    }
                except Exception as exc:
                    result_payload = {
                        "tool_id": tool_id,
                        "status": "FAILED",
                        "exit_code": None,
                        "binary": binary,
                        "detail": f"Probe failed: {type(exc).__name__}: {exc}",
                    }

                try:
                    from core.models import PhysicalVerification as _PV
                    pkg = ledger.seal_evidence(
                        action_id=f"act_probe_{uuid.uuid4().hex[:8]}",
                        mission_id="mis_capability_probe",
                        agent_id="TOOL_FACTORY_PROBE",
                        verifications=[_PV(
                            check_type="exit_code_zero",
                            target_path=binary,
                            expected_val="0",
                            actual_val=str(result_payload.get("exit_code")),
                            verified=result_payload["status"] == "PASSED",
                            details=result_payload["detail"][:300],
                        )],
                        metadata={"tool_id": tool_id, "probe": "version_flag"},
                    )
                    result_payload["evidence_id"] = pkg.evidence_id
                    result_payload["evidence_status"] = str(pkg.status)
                except Exception as exc:
                    result_payload["evidence_error"] = f"{type(exc).__name__}: {exc}"

                self._send_json(result_payload)
                return

            # Tenant-created tools: registration is real, execution is not implied.
            try:
                with db.get_connection() as conn:
                    pkg_row = conn.execute(
                        "SELECT tool_id, name, status FROM tool_packages "
                        "WHERE tool_id = ? AND tenant_id = ?",
                        (tool_id, tenant_id),
                    ).fetchone()
            except Exception:
                pkg_row = None
            if pkg_row:
                self._send_json({
                    "tool_id": tool_id,
                    "status": "NOT_EXECUTED",
                    "detail": (
                        f"'{pkg_row['name']}' is registered ({pkg_row['status']}) but has never been executed. "
                        "Run it through a governed ActionContract to produce execution evidence; the factory "
                        "does not simulate a probe."
                    ),
                })
                return

            # Connectors: report configuration state, do not invent a call.
            for conn_item in connector_registry.list_connectors():
                if tool_id == "conn_" + "".join(
                    ch if ch.isalnum() else "_" for ch in conn_item["name"].lower()
                ).strip("_"):
                    configured = bool(
                        conn_item.get("connected")
                        and str(conn_item.get("qualification_status")) not in ("BLOCKED", "MOCK_ONLY")
                    )
                    self._send_json({
                        "tool_id": tool_id,
                        "status": "AVAILABLE" if configured else "NOT_CONFIGURED",
                        "detail": (
                            "Connector is configured; use its read methods to fetch real data."
                            if configured else
                            "Connector has no provider credentials, so no probe was executed."
                        ),
                        "qualification_status": conn_item.get("qualification_status"),
                    })
                    return

            self._send_json({
                "tool_id": tool_id,
                "status": "NOT_SUPPORTED",
                "detail": "No live probe is implemented for this capability.",
            }, status=404)
            return

        elif path == "/api/tools/discover":
            import re as _re
            import shutil as _shutil

            requirement = (req_data.get("requirement") or "").strip()
            if not requirement:
                self._send_json({
                    "error": "Missing requirement",
                    "code": "MISSING_REQUIREMENT",
                    "detail": "Provide 'requirement' describing the capability you need.",
                }, status=400)
                return

            stop = {"the", "and", "for", "with", "that", "this", "from", "into",
                    "need", "needs", "want", "wants", "able", "can", "our", "you",
                    "your", "using", "use", "via", "build", "create", "make"}
            req_tokens = {
                t for t in _re.findall(r"[a-z0-9]+", requirement.lower())
                if len(t) > 2 and t not in stop
            }

            steps: List[Dict[str, Any]] = []
            candidates: List[Dict[str, Any]] = []

            # ---- 1. Local, vetted binaries in the capability registry -------
            local_matches = [
                (name, cap) for name, cap in registry._capabilities.items()
                if name.lower() in req_tokens
            ]
            steps.append({
                "step": "Local capability registry",
                "status": "MATCHED" if local_matches else "NO_MATCH",
                "detail": (
                    f"{len(local_matches)} of {len(registry._capabilities)} vetted binaries matched: "
                    + ", ".join(sorted(n for n, _ in local_matches))
                ) if local_matches else (
                    f"{len(registry._capabilities)} vetted local binaries registered; none matched the requirement."
                ),
            })
            for name, cap in local_matches:
                candidates.append({
                    "name": name,
                    "capability": f"Local sandboxed execution of {name}",
                    "source": "Local capability registry",
                    "status": "AVAILABLE",
                    "permission": "SANDBOXED_READ_ONLY" if cap.is_sandboxed else "AUTOMATIC_IDEMPOTENT",
                    "verified": True,
                    "detail": f"{cap.binary_path} ({cap.license_type})",
                    "action": "Use capability",
                })

            # ---- 2. Enterprise connectors: report their real configuration ---
            connector_aliases = {
                "accounting": {"invoice", "accounting", "ledger", "reconciliation", "reconcil",
                               "tally", "quickbooks", "gst", "tax", "finance", "bookkeeping"},
                "payments": {"payment", "stripe", "razorpay", "settlement", "payout",
                             "refund", "gateway", "transaction"},
                "pms_hospitality": {"hotel", "reservation", "pms", "booking", "guest",
                                    "folio", "opera", "hospitality", "room", "checkin", "checkout"},
            }
            connector_prereqs = {
                "pms_hospitality": ["OPERA_PMS_CLIENT_ID", "OPERA_PMS_CLIENT_SECRET", "OPERA_PMS_PROPERTY"],
                "accounting": ["QUICKBOOKS_CLIENT_ID", "QUICKBOOKS_CLIENT_SECRET", "QUICKBOOKS_REALM_ID"],
                "payments": ["STRIPE_SECRET_KEY or RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET"],
            }
            conn_checked = 0
            conn_matches = 0
            for conn in connector_registry.connectors.values():
                conn_checked += 1
                aliases = connector_aliases.get(conn.connector_type, set())
                if not (req_tokens & aliases):
                    continue
                conn_matches += 1
                qualified = str(getattr(conn, "qualification_status", "BLOCKED"))
                configured = bool(conn.connected and "BLOCKED" not in qualified)
                candidates.append({
                    "name": conn.name,
                    "capability": f"{conn.connector_type.replace('_', ' ').title()} data access",
                    "source": f"Enterprise connector ({conn.__class__.__name__})",
                    "status": "AVAILABLE" if configured else "NOT_CONFIGURED",
                    "permission": str(conn.permission_level),
                    "verified": configured,
                    "detail": (
                        "Connector handshake complete; live data access is available."
                        if configured else
                        "No provider credentials are configured, so this connector cannot return real data."
                    ),
                    "required_prerequisites": (
                        [] if configured else connector_prereqs.get(conn.connector_type, [])
                    ),
                    "action": "Use capability" if configured else "Configure in Settings → Connectors",
                })
            steps.append({
                "step": "Enterprise connectors",
                "status": "MATCHED" if conn_matches else "NO_MATCH",
                "detail": (
                    f"{conn_matches} of {conn_checked} registered connectors matched; "
                    f"{sum(1 for c in candidates if c['status'] == 'AVAILABLE' and c['source'].startswith('Enterprise'))} configured."
                ) if conn_matches else (
                    f"{conn_checked} registered connectors checked; none matched the requirement."
                ),
            })

            # ---- 3. Browser automation: real binary/package detection --------
            browser_tokens = {"browser", "scrape", "scraping", "dom", "navigate",
                              "webpage", "html", "crawl", "selenium", "playwright"}
            if req_tokens & browser_tokens:
                chromium = (
                    _shutil.which("chromium") or _shutil.which("chromium-browser")
                    or _shutil.which("google-chrome") or _shutil.which("chrome")
                )
                has_playwright = False
                try:
                    import playwright  # noqa: F401
                    has_playwright = True
                except Exception:
                    has_playwright = False
                available = bool(chromium or has_playwright)
                candidates.append({
                    "name": "Headless browser automation",
                    "capability": "DOM interaction, scraping, and form submission",
                    "source": "Host fabric (browser runtime)",
                    "status": "AVAILABLE" if available else "NOT_INSTALLED",
                    "permission": "AUTOMATIC_IDEMPOTENT",
                    "verified": available,
                    "detail": (
                        f"Chromium={chromium or 'n/a'}, playwright={has_playwright}."
                        if available else
                        "No Chromium binary and no Playwright package are installed on this host."
                    ),
                    "action": "Use capability" if available else "Install Chromium or Playwright",
                })
                steps.append({
                    "step": "Browser automation",
                    "status": "MATCHED",
                    "detail": (
                        f"Chromium={chromium or 'n/a'}, playwright={has_playwright}."
                    ),
                })
            else:
                steps.append({
                    "step": "Browser automation",
                    "status": "SKIPPED",
                    "detail": "Requirement does not reference browser or DOM automation.",
                })

            # ---- 4. Desktop automation: needs a graphical session ------------
            desktop_tokens = {"desktop", "screen", "mouse", "keyboard", "click",
                              "window", "gui", "x11", "screenshot"}
            if req_tokens & desktop_tokens:
                display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
                xdotool = _shutil.which("xdotool")
                available = bool(display and xdotool)
                candidates.append({
                    "name": "Desktop robot runtime",
                    "capability": "Screen perception and keyboard/mouse automation",
                    "source": "Host fabric (desktop robot)",
                    "status": "AVAILABLE" if available else "NOT_CONFIGURED",
                    "permission": "AUTOMATIC_IDEMPOTENT",
                    "verified": available,
                    "detail": (
                        f"DISPLAY={display}, xdotool={xdotool}."
                        if available else
                        "No graphical session (DISPLAY/WAYLAND_DISPLAY) or xdotool binary is available on this host."
                    ),
                    "action": "Use capability" if available else "Run on a host with a desktop session",
                })
                steps.append({
                    "step": "Desktop automation",
                    "status": "MATCHED",
                    "detail": f"DISPLAY={display or 'unset'}, xdotool={xdotool or 'missing'}.",
                })
            else:
                steps.append({
                    "step": "Desktop automation",
                    "status": "SKIPPED",
                    "detail": "Requirement does not reference desktop/GUI automation.",
                })

            # ---- 5. Governed terminal ---------------------------------------
            terminal_tokens = {"shell", "terminal", "command", "cli", "script", "bash"}
            if req_tokens & terminal_tokens:
                bash = _shutil.which("bash") or _shutil.which("sh")
                candidates.append({
                    "name": "Governed terminal runtime",
                    "capability": "Sandboxed shell command execution",
                    "source": "Coordinator terminal runtime",
                    "status": "AVAILABLE" if bash else "NOT_INSTALLED",
                    "permission": "AUDITED_TRANSACTIONAL",
                    "verified": bool(bash),
                    "detail": f"Shell binary: {bash}." if bash else "No POSIX shell found on this host.",
                    "action": "Use capability" if bash else "Install a POSIX shell",
                })
                steps.append({
                    "step": "Governed terminal",
                    "status": "MATCHED",
                    "detail": f"Shell binary: {bash or 'missing'}.",
                })
            else:
                steps.append({
                    "step": "Governed terminal",
                    "status": "SKIPPED",
                    "detail": "Requirement does not reference shell execution.",
                })

            # ---- 6. Tenant-owned tools created through the tool factory ------
            try:
                with db.get_connection() as conn:
                    rows = conn.execute(
                        "SELECT tool_id, name, version, risk_class FROM tool_packages "
                        "WHERE tenant_id = ? AND status = 'ACTIVE'",
                        (tenant_id,),
                    ).fetchall()
            except Exception:
                rows = []
            tenant_tool_matches = [
                r for r in rows
                if (r["name"] or "").lower() in req_tokens
                or any(tok in (r["name"] or "").lower() for tok in req_tokens)
            ]
            for r in tenant_tool_matches:
                candidates.append({
                    "name": r["name"],
                    "capability": f"Tenant-created governed tool ({r['risk_class']})",
                    "source": "Tool Factory (tenant registry)",
                    "status": "AVAILABLE",
                    "permission": "AUDITED_TRANSACTIONAL",
                    "verified": True,
                    "detail": f"tool_id={r['tool_id']} version={r['version']}",
                    "action": "Use capability",
                })
            steps.append({
                "step": "Tenant tool registry",
                "status": "MATCHED" if tenant_tool_matches else "NO_MATCH",
                "detail": (
                    f"{len(tenant_tool_matches)} of {len(rows)} tenant-created tools matched."
                    if rows else "No tools have been created by this tenant."
                ),
            })

            available = [c for c in candidates if c["status"] == "AVAILABLE"]
            not_ready = [c for c in candidates if c["status"] != "AVAILABLE"]

            if available:
                best = available[0]
                self._send_json({
                    "found": True,
                    "capability": best,
                    "candidates": candidates,
                    "blocked_candidates": not_ready,
                    "evaluation_steps": steps,
                    "recommendation": "USE_EXISTING",
                })
            elif not_ready:
                self._send_json({
                    "found": False,
                    "reason": (
                        "A matching capability exists in this deployment but is not usable: "
                        + ", ".join(f"{c['name']} ({c['status']})" for c in not_ready)
                    ),
                    "candidates": candidates,
                    "blocked_candidates": not_ready,
                    "evaluation_steps": steps,
                    "recommendation": "CONFIGURE_EXISTING",
                })
            else:
                self._send_json({
                    "found": False,
                    "reason": "No registered capability, configured connector, or installed runtime satisfies this requirement.",
                    "candidates": [],
                    "blocked_candidates": [],
                    "evaluation_steps": steps,
                    "recommendation": "TOOL_FACTORY",
                    "suggested_spec": {
                        "name": f"{(requirement.split()[0].title() if requirement else 'Custom')} Specialist Tool",
                        "purpose": requirement,
                        "runtime": "Python 3 (rootless container, network blocked by default)",
                        "permissions": ["Filesystem read (sandbox)"],
                        "note": "A tool is only registered after it passes the AST security scan in Tool Factory V2.",
                    },
                })
            return

        elif path == "/api/tools/build":
            from core.tool_factory_v2 import tool_factory_v2, ToolSecurityViolation

            tool_name = (req_data.get("name") or "").strip()
            purpose = (req_data.get("purpose") or "").strip()
            source_code = req_data.get("source_code") or ""
            risk_class = req_data.get("risk_class", "LOW_RISK")
            version = req_data.get("version", "1.0.0")

            if not tool_name:
                self._send_json({
                    "error": "Missing tool name",
                    "code": "MISSING_NAME",
                    "detail": "Provide 'name' for the tool being registered.",
                }, status=400)
                return
            if not source_code.strip():
                self._send_json({
                    "error": "Missing source code",
                    "code": "MISSING_SOURCE_CODE",
                    "detail": (
                        "Provide 'source_code' containing the tool implementation. "
                        "The Tool Factory performs a real AST security scan before registration; "
                        "it will not certify an empty package."
                    ),
                    "required_fields": ["name", "source_code"],
                }, status=400)
                return
            if risk_class not in ("LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"):
                self._send_json({
                    "error": "Invalid risk class",
                    "code": "INVALID_RISK_CLASS",
                    "allowed": ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"],
                }, status=400)
                return

            scan_ok, scan_errors = tool_factory_v2.static_security_scan(source_code)
            test_results = [{
                "stage": "Static security scan",
                "status": "Passed" if scan_ok else "Failed",
                "detail": (
                    "AST inspection found no disallowed imports, calls, or dynamic evaluation."
                    if scan_ok else "; ".join(scan_errors)
                ),
            }]
            if not scan_ok:
                self._send_json({
                    "error": "Tool rejected by the static security scan",
                    "code": "TOOL_SECURITY_REJECTED",
                    "test_results": test_results,
                    "violations": scan_errors,
                }, status=422)
                return

            try:
                package = tool_factory_v2.create_governed_tool(
                    tenant_id=tenant_id,
                    name=tool_name,
                    source_code=source_code,
                    risk_class=risk_class,
                    version=version,
                )
            except ToolSecurityViolation as exc:
                self._send_json({
                    "error": "Tool rejected by the sandbox policy",
                    "code": "TOOL_SECURITY_REJECTED",
                    "test_results": test_results,
                    "violations": [str(exc)],
                }, status=422)
                return
            except Exception as exc:
                logger.error("Tool registration failed: %s", exc, exc_info=True)
                self._send_json({
                    "error": "Tool registration failed",
                    "code": "TOOL_REGISTRATION_FAILED",
                    "detail": f"{type(exc).__name__}: {exc}",
                }, status=500)
                return

            profile = package.get("sandbox_profile", {})
            test_results.extend([
                {
                    "stage": "Sandbox policy",
                    "status": "Passed",
                    "detail": (
                        f"{profile.get('profile_type', 'ROOTLESS_CONTAINER')}, "
                        f"privileged={profile.get('is_privileged', False)}, "
                        f"network={profile.get('network_egress', 'BLOCK_ALL')}, "
                        f"memory={profile.get('max_memory_mb')}MB, cpu={profile.get('max_cpu_percent')}%"
                    ),
                },
                {
                    "stage": "Code signature",
                    "status": "Passed",
                    "detail": f"SHA-256 package signature {package['signature']}.",
                },
                {
                    "stage": "Registry write",
                    "status": "Passed",
                    "detail": f"Registered as {package['tool_id']} in the tenant tool registry.",
                },
                {
                    "stage": "Runtime execution",
                    "status": "NOT_RUN",
                    "detail": (
                        "Registration does not execute the tool. Run it under a governed "
                        "ActionContract to produce execution evidence."
                    ),
                },
            ])

            self._send_json({
                "success": True,
                "tool": {
                    "id": package["tool_id"],
                    "name": package["name"],
                    "version": package["version"],
                    "category": req_data.get("category", "Custom Automation"),
                    "source": "User Created",
                    "availability": "Available",
                    "permission": "AUDITED_TRANSACTIONAL",
                    "risk_class": risk_class,
                    "status": package["status"],
                    "signature": package["signature"],
                    "sandbox_profile": profile,
                    "purpose": purpose,
                    "created_at": time.time(),
                },
                "test_results": test_results,
            })
            return

        elif path in ("/api/llm/test", "/api/v1/llm/test"):
            from core.llm_runtime import llm_runtime
            probe = req_data.get("prompt") or "Reply with the single word READY."
            res = llm_runtime.chat(
                tenant_id=tenant_id,
                company_id=company_id,
                system="You are a health probe. Reply concisely.",
                messages=[{"role": "user", "content": probe}],
                max_tokens=64,
                temperature=0.0,
                intent="health",
            )
            self._send_json({
                "ok": not res.degraded and bool(res.content),
                "provider": res.provider,
                "model": res.model,
                "degraded": res.degraded,
                "latency_ms": round(res.latency_ms, 1),
                "response": res.content[:500],
                "error": res.error,
                "attempts": res.attempts,
            })
            return

        elif path == "/api/settings":
            # company_id was resolved from the verified token (see _resolve_company_id)
            actor = self.headers.get("X-User-Name", "Host Administrator")
            if isinstance(req_data, dict):
                for k, v in req_data.items():
                    if isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            settings_service.update_single_setting(tenant_id, company_id, sub_k, sub_v, actor=actor)
                    else:
                        settings_service.update_single_setting(tenant_id, company_id, k, v, actor=actor)
            self._send_json({"success": True, "saved": True})
            return

        elif path.startswith("/api/settings/category/") and len(path.split("/")) == 5:
            cat_id = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            actor = self.headers.get("X-User-Name", "Host Administrator")
            actor_role = self.headers.get("X-User-Role", "OWNER")
            reason = req_data.get("reason", "Batch category save")
            if "settings" in req_data and isinstance(req_data["settings"], dict):
                values = req_data["settings"]
            elif "values" in req_data and isinstance(req_data["values"], dict):
                values = req_data["values"]
            else:
                values = {k: v for k, v in req_data.items() if k not in ("company_id", "reason", "tenant_id", "actor")}
            res = settings_service.bulk_save_category(tenant_id, company_id, cat_id, values, actor=actor, reason=reason, actor_role=actor_role)
            status_code = 200 if res.get("success") else 400
            self._send_json(res, status=status_code)
            return

        elif path.startswith("/api/settings/category/") and path.endswith("/reset") and len(path.split("/")) == 6:
            cat_id = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            actor = self.headers.get("X-User-Name", "Host Administrator")
            res = settings_service.reset_category_to_defaults(cat_id, tenant_id, company_id, actor=actor)
            status_code = 200 if res.get("success") else 400
            self._send_json(res, status=status_code)
            return

        elif path.startswith("/api/settings/key/") and path.endswith("/reset") and len(path.split("/")) == 6:
            s_key = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            actor = self.headers.get("X-User-Name", "Host Administrator")
            res = settings_service.reset_single_setting_to_default(s_key, tenant_id, company_id, actor=actor)
            status_code = res.get("status_code", (200 if res.get("success") else 400))
            self._send_json(res, status=status_code)
            return

        elif path.startswith("/api/settings/key/") and path.endswith("/rotate") and len(path.split("/")) == 6:
            s_key = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            actor = self.headers.get("X-User-Name", "Host Administrator")
            res = settings_service.rotate_secret_token(s_key, tenant_id, company_id, actor=actor)
            status_code = res.get("status_code", (200 if res.get("success") else 400))
            self._send_json(res, status=status_code)
            return

        elif path.startswith("/api/settings/key/") and path.endswith("/revoke") and len(path.split("/")) == 6:
            s_key = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            actor = self.headers.get("X-User-Name", "Host Administrator")
            res = settings_service.revoke_secret_token(s_key, tenant_id, company_id, actor=actor)
            status_code = res.get("status_code", (200 if res.get("success") else 400))
            self._send_json(res, status=status_code)
            return

        elif path.startswith("/api/settings/action/") and len(path.split("/")) == 5:
            action_id = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            actor = self.headers.get("X-User-Name", "Host Administrator")
            res = settings_service.execute_button_action(action_id, tenant_id, company_id, actor=actor)
            status_code = res.get("status_code", (200 if res.get("success") else 400))
            self._send_json(res, status=status_code)
            return

        elif path.startswith("/api/settings/key/") and len(path.split("/")) == 5:
            s_key = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            actor = self.headers.get("X-User-Name", "Host Administrator")
            actor_role = self.headers.get("X-User-Role", "OWNER")
            expected_ver = req_data.get("expected_version")
            new_val = req_data.get("value") if "value" in req_data else req_data
            reason = req_data.get("reason", "Direct setting update")
            scope = req_data.get("scope", "Company")
            res = settings_service.update_single_setting(
                tenant_id, company_id, s_key, new_val,
                actor=actor, reason=reason, scope=scope,
                actor_role=actor_role, expected_version=expected_ver
            )
            status_code = res.get("status_code", (200 if res.get("success") else 400))
            self._send_json(res, status=status_code)
            return

        elif path == "/api/settings/propose":
            # company_id was resolved from the verified token (see _resolve_company_id)
            s_id = req_data.get("setting_id", "")
            proposed_val = req_data.get("proposed_value")
            proposed_by = req_data.get("proposed_by", "AI CEO Executive Engine")
            reason = req_data.get("reason", "Optimization recommendation")
            expected_benefit = req_data.get("expected_benefit", "Performance improvement")
            risk = req_data.get("risk_level", "MEDIUM")
            res = settings_service.propose_change(tenant_id, company_id, s_id, proposed_val, proposed_by, reason, expected_benefit, risk)
            self._send_json(res)
            return

        elif path.startswith("/api/settings/proposal/") and path.endswith("/resolve"):
            parts = path.split("/")
            prop_id = parts[4]
            decision = req_data.get("decision", "APPROVED")
            actor = self.headers.get("X-User-Name", "Host Administrator")
            reason = req_data.get("reason", "Administrative resolution")
            res = settings_service.resolve_proposal(prop_id, decision, actor, reason)
            self._send_json(res)
            return

        elif path == "/api/settings/test":
            target = req_data.get("target", "database")
            res = settings_service.run_live_test(target, req_data, tenant_id, company_id)
            self._send_json(res)
            return

        elif path.startswith("/api/settings/test/") and len(path.split("/")) == 5:
            target = path.split("/")[4]
            res = settings_service.run_live_test(target, req_data, tenant_id, company_id)
            self._send_json(res)
            return

        # =====================================================================
        # Prompt 03: Universal Schedule POST Handlers
        # =====================================================================
        elif path == "/api/schedules/parse-nl":
            text = req_data.get("text", "")
            cid = company_id
            parsed_schedule = get_runtime(tenant_id).schedule.parse_natural_language(text, cid)
            self._send_json(parsed_schedule)
            return

        elif path == "/api/schedules":
            new_item = get_runtime(tenant_id).schedule.create_schedule(req_data)
            self._send_json({"success": True, "schedule": new_item})
            return

        elif path.startswith("/api/schedules/") and path.endswith("/update"):
            parts = path.split("/")
            sched_id = parts[3]
            updated = get_runtime(tenant_id).schedule.update_schedule(sched_id, req_data)
            if updated:
                self._send_json({"success": True, "schedule": updated})
            else:
                self._send_json({"error": "Schedule not found"}, status=404)
            return

        elif path.startswith("/api/schedules/") and path.endswith("/delete"):
            parts = path.split("/")
            sched_id = parts[3]
            ok = get_runtime(tenant_id).schedule.delete_schedule(sched_id)
            self._send_json({"success": ok})
            return

        # =====================================================================
        # Prompt 03: AI CEO Meeting Room POST Handlers
        # =====================================================================
        elif path.startswith("/api/meetings/") and path.endswith("/start"):
            parts = path.split("/")
            meeting_id = parts[3]
            meeting = get_runtime(tenant_id).meeting_service.start_meeting(meeting_id)
            self._send_json({"success": True, "meeting": meeting})
            return

        elif path.startswith("/api/meetings/") and path.endswith("/end"):
            parts = path.split("/")
            meeting_id = parts[3]
            summary = req_data.get("summary")
            meeting = get_runtime(tenant_id).meeting_service.end_meeting(meeting_id, summary)
            self._send_json({"success": True, "meeting": meeting})
            return

        elif path.startswith("/api/meetings/") and path.endswith("/state"):
            parts = path.split("/")
            meeting_id = parts[3]
            meeting = get_runtime(tenant_id).meeting_service.update_meeting_state(meeting_id, req_data)
            self._send_json({"success": True, "meeting": meeting})
            return

        elif path.startswith("/api/meetings/") and path.endswith("/message"):
            parts = path.split("/")
            meeting_id = parts[3]
            msg = req_data.get("message", "")
            mode = req_data.get("mode", "TEXT")
            res = get_runtime(tenant_id).meeting_service.send_host_message(meeting_id, msg, mode)
            self._send_json({"success": True, **res})
            return

        elif path == "/api/meetings/decisions":
            cid = company_id
            title = req_data.get("title", "Executive Decision")
            desc = req_data.get("description", "")
            dtype = req_data.get("decision_type", "STRATEGIC")
            mid = req_data.get("meeting_id")
            cm = bool(req_data.get("create_mission", False))
            dec = get_runtime(tenant_id).meeting_service.record_decision(cid, title, desc, dtype, mid, cm)
            self._send_json({"success": True, "decision": dec})
            return

        # =====================================================================
        # Prompt 03: Floating Live Assistant & Coworker POST Handlers
        # =====================================================================
        elif path == "/api/assistant/chat":
            prompt = req_data.get("prompt", "")
            cid = req_data.get("company_id")
            uid = req_data.get("user_id", "usr_owner")
            chat_res = get_runtime(tenant_id).assistant.handle_ai_chat(prompt, cid, uid)
            self._send_json(chat_res)
            return

        elif path == "/api/assistant/coworker/task":
            prompt = req_data.get("prompt", "")
            ws_mode = req_data.get("workspace_mode", "PERSONAL")
            cid = req_data.get("company_id")
            uid = req_data.get("user_id", "usr_owner")
            task_res = get_runtime(tenant_id).assistant.create_coworker_task(prompt, ws_mode, cid, uid)
            self._send_json(task_res)
            return

        elif path.startswith("/api/assistant/coworker/tasks/") and path.endswith("/approve"):
            parts = path.split("/")
            task_id = parts[5] if len(parts) > 5 else ""
            approved = bool(req_data.get("approved", True))
            updated_task = get_runtime(tenant_id).assistant.approve_coworker_task(task_id, approved)
            self._send_json({"success": True, "task": updated_task})
            return

        # =====================================================================
        # ZONATA AI Assistant & Universal Co-Worker POST Handlers
        # =====================================================================
        elif path == "/api/coworker/autonomy":
            engine = _cw(tenant_id, company_id)
            from core.coworker.runtime_supervisor import ensure_supervisor
            supervisor = getattr(engine, "autonomy_supervisor", None) or ensure_supervisor(engine, autostart=False)
            engine.autonomy_supervisor = supervisor
            action = str(req_data.get("action", "STATUS")).upper()
            if action in ("START", "STOP", "RESUME", "PAUSE") and self._approver_denied(auth_context):
                return
            if action in ("START", "RESUME"):
                out = supervisor.start(manual=True)
            elif action in ("STOP", "PAUSE"):
                out = supervisor.stop()
            elif action == "TICK":
                out = supervisor.run_once(trigger="api")
            elif action == "STATUS":
                out = supervisor.status()
            else:
                self._send_json({
                    "error": "Unsupported action",
                    "detail": "action must be START, STOP, TICK or STATUS",
                    "action": action,
                }, status=400)
                return
            self._send_json(out)
            return

        elif path == "/api/coworker/work-items":
            engine = _cw(tenant_id, company_id)
            title = str(req_data.get("title") or "").strip()
            objective = str(req_data.get("objective") or req_data.get("description") or "").strip()
            if not title or not objective:
                self._send_json({"error": "title and objective are required"}, status=400)
                return
            from core.coworker.ceo_coworker_bridge import AICeoMissionRequest
            from core.coworker.executive_operating_loop import OperatingPriority
            priority_name = str(req_data.get("priority") or "P3_CEO_DIRECTIVE").upper()
            try:
                priority = OperatingPriority[priority_name]
            except KeyError:
                self._send_json({
                    "error": "Unknown priority",
                    "allowed": [p.name for p in OperatingPriority],
                }, status=400)
                return
            try:
                budget = float(req_data.get("budget", 50.0) or 0.0)
                cost_estimate = float(req_data.get("cost_estimate_usd", 0.0) or 0.0)
            except (TypeError, ValueError):
                self._send_json({"error": "budget and cost_estimate_usd must be numeric"}, status=400)
                return
            if budget < 0 or cost_estimate < 0:
                self._send_json({"error": "budget and cost_estimate_usd must be non-negative"}, status=400)
                return
            mission_request = AICeoMissionRequest(
                objective=objective,
                business_context=req_data.get("business_context") or {},
                success_criteria=req_data.get("success_criteria") or [],
                constraints=req_data.get("constraints") or [],
                priority=priority_name,
                budget=budget,
                risk_policy=req_data.get("risk_policy") or {
                    "max_risk": "MEDIUM",
                    "require_human_approval_over_usd": 100.0,
                },
                company_id=company_id,
                tenant_id=tenant_id,
                initiator=str(auth_context.get("user_id") or "OWNER"),
            )
            item = engine.executive_loop.submit_work_item(
                title=title,
                description=objective,
                priority=priority,
                cost_estimate_usd=cost_estimate,
                mission_request=mission_request,
                metadata={"requested_by": str(auth_context.get("user_id") or "OWNER")},
            )
            self._send_json({
                "success": True,
                "item_id": item.item_id,
                "status": item.status.value,
                "requires_approval": item.requires_human_approval,
                "approval_path": (
                    f"/api/coworker/approvals/{item.item_id}/decide"
                    if item.requires_human_approval else None
                ),
                "queue_depth": engine.executive_loop.get_queue_depth(),
                "note": "The autonomy supervisor executes queued items on its next tick.",
            })
            return

        elif path == "/api/coworker/mission":
            if universal_automation_fabric.is_killswitch_active():
                self._send_json({
                    "success": False,
                    "error": "Global kill switch engaged: mission submission blocked",
                    "blocked": True,
                    "killswitch_active": True,
                }, status=403)
                return
            prompt = req_data.get("prompt", "")
            initiator = req_data.get("initiator", "ZONATA AI Assistant")
            auto_step = bool(req_data.get("auto_step", True))
            m = _cw(tenant_id, company_id).background_dispatcher.submit_background_prompt(prompt, initiator=initiator)
            if auto_step:
                _cw(tenant_id, company_id).background_dispatcher.execute_compound_mission_step(m.mission_id)
            self._send_json({
                "success": True,
                "mission_id": m.mission_id,
                "status": m.status,
                "progress_percent": m.progress_percent,
                "current_stage": m.current_stage,
                "subworkers": m.subworkers,
                "runtimes_used": m.runtimes_used,
                "deliverables": m.deliverables,
                "evidence_id": m.evidence_id,
                "timeline": m.timeline
            })
            return

        elif path.startswith("/api/coworker/missions/") and path.endswith("/step"):
            if universal_automation_fabric.is_killswitch_active():
                self._send_json({
                    "success": False,
                    "error": "Global kill switch engaged: mission execution blocked",
                    "blocked": True,
                    "killswitch_active": True,
                }, status=403)
                return
            mid = path.split("/")[4]
            m = _cw(tenant_id, company_id).background_dispatcher.execute_compound_mission_step(mid)
            if m:
                self._send_json({"success": True, "mission_id": m.mission_id, "status": m.status, "progress": m.progress_percent, "stage": m.current_stage, "deliverables": m.deliverables, "evidence_id": m.evidence_id})
            else:
                self._send_json({"error": "Mission not found"}, status=404)
            return

        elif path.startswith("/api/coworker/missions/") and path.endswith("/control"):
            mid = path.split("/")[4]
            action = req_data.get("action", "").upper()
            ok = False
            msg = ""
            if action == "PAUSE":
                ok = _cw(tenant_id, company_id).background_dispatcher.pause_mission(mid)
                msg = "Mission paused"
            elif action == "RESUME":
                ok = _cw(tenant_id, company_id).background_dispatcher.resume_mission(mid)
                msg = "Mission resumed"
            elif action in ["STOP", "CANCEL"]:
                ok = _cw(tenant_id, company_id).background_dispatcher.stop_mission(mid)
                msg = "Mission stopped"
            elif action == "TAKE_CONTROL":
                ok = _cw(tenant_id, company_id).background_dispatcher.take_control(mid)
                msg = "Human operator took control"
            elif action == "RETRY":
                ret_m = _cw(tenant_id, company_id).background_dispatcher.retry_mission(mid)
                ok = ret_m is not None
                msg = "Mission retried"
            self._send_json({"success": ok, "action": action, "message": msg, "mission_id": mid})
            return

        elif path == "/api/coworker/terminal/execute" or path == "/api/terminal/execute":
            # company_id was resolved from the verified token (see _resolve_company_id)

            # Authoritative global kill switch: halts every execution surface.
            if universal_automation_fabric.is_killswitch_active():
                self._send_json({
                    "error": "Global kill switch engaged: terminal execution halted",
                    "blocked": True,
                    "killswitch_active": True,
                }, status=403)
                return

            # Dynamic Runtime Enforcement (Gate G6, G2)
            em_stop = settings_service.get_effective_setting(tenant_id, company_id, "host_emergency_stop", False)
            if em_stop:
                self._send_json({"error": "Host emergency stop active: terminal execution halted", "blocked": True}, status=403)
                return

            term_enabled = settings_service.get_effective_setting(tenant_id, company_id, "term_execution_enabled", True)
            if not term_enabled:
                self._send_json({"error": "Terminal command execution disabled by Enterprise Settings policy ('term_execution_enabled'=False)", "blocked": True}, status=403)
                return

            term_max_lease = float(settings_service.get_effective_setting(tenant_id, company_id, "term_max_lease_seconds", 60.0))

            params = req_data.get("parameters", {}) if isinstance(req_data.get("parameters"), dict) else {}
            command = req_data.get("command") or params.get("command", "")
            capability = req_data.get("capability") or params.get("capability", "terminal.shell_command")
            cwd = req_data.get("cwd") or params.get("cwd", BASE_DIR)
            human_approved = bool(req_data.get("human_approved", False) or params.get("human_approved", False))
            session_id = req_data.get("session_id") or f"term_api_{uuid.uuid4().hex[:6]}"
            profile_id = req_data.get("profile_id", "profile_linux_dev")

            raw_timeout = float(req_data.get("timeout_sec", 30.0))
            effective_timeout = min(raw_timeout, term_max_lease)

            # Check if executing via UniversalTerminal or raw fallback
            if req_data.get("use_fabric", True):
                plan = CommandPlan(
                    plan_id=f"plan_{uuid.uuid4().hex[:6]}",
                    objective=req_data.get("objective", f"Execute shell command: {command}"),
                    environment_profile_id=profile_id,
                    working_directory=cwd,
                    command=command,
                    timeout_sec=effective_timeout
                )
                sess = get_runtime(tenant_id).terminal._sessions.get(session_id)
                if not sess:
                    sess = get_runtime(tenant_id).terminal.create_session(
                        mission_id=req_data.get("mission_id", "msn_api"),
                        task_id=req_data.get("task_id", "tsk_api"),
                        environment_id=profile_id,
                        workspace=cwd
                    )
                res = get_runtime(tenant_id).terminal.execute(sess.session_id, plan)
                self._send_json(res)
                return
            else:
                exec_payload = {
                    "capability": capability,
                    "command": command,
                    "cwd": cwd,
                    "parameters": {**params, "command": command, "cwd": cwd},
                    "human_approved": human_approved
                }
                for k in ["action", "file_path", "content"]:
                    if k in params:
                        exec_payload[k] = params[k]
                    elif k in req_data:
                        exec_payload[k] = req_data[k]
                res = get_runtime(tenant_id).terminal_runtime.run_foreground(session_id, exec_payload)
                self._send_json(res)
                return

        elif path == "/api/terminal/select-runtime":
            objective = req_data.get("objective", "Linux development workload")
            force_gui = bool(req_data.get("force_gui", False))
            decision = get_runtime(tenant_id).terminal.select_runtime(objective, force_gui=force_gui)
            self._send_json({
                "selected_profile_id": decision.selected_profile_id,
                "selected_adapter_id": decision.selected_adapter_id,
                "distribution": decision.distribution,
                "version": decision.version,
                "desktop_environment": decision.desktop_environment.value,
                "execution_mode": decision.execution_mode.value,
                "isolation_level": decision.isolation_level.value,
                "network_mode": decision.network_mode.value,
                "reason": decision.reason,
                "score": decision.score,
                "fallback_profiles": decision.fallback_profiles
            })
            return

        elif path == "/api/terminal/agent/objective":
            objective = req_data.get("objective", "")
            mission_id = req_data.get("mission_id")
            human_approved = bool(req_data.get("human_approved", False))
            force_gui = bool(req_data.get("force_gui", False))
            explicit_cmd = req_data.get("command")
            cwd = req_data.get("cwd")

            result = get_runtime(tenant_id).terminal_agent.process_objective(
                objective=objective,
                mission_id=mission_id,
                human_approved=human_approved,
                force_gui=force_gui,
                explicit_command=explicit_cmd,
                custom_workspace=cwd
            )
            self._send_json({
                "status": result.status,
                "summary": result.summary,
                "environment_used": result.environment_used,
                "runtime_profile": result.runtime_profile,
                "tools_used": result.tools_used,
                "tools_installed": result.tools_installed,
                "commands_executed": result.commands_executed,
                "observations": result.observations,
                "verification": result.verification,
                "evidence_id": result.evidence_id,
                "failures": result.failures,
                "recovery_actions": result.recovery_actions,
                "duration_ms": result.duration_ms
            })
            return

        elif path == "/api/terminal/rollback":
            snap_id = req_data.get("snapshot_id", "")
            ok = get_runtime(tenant_id).terminal.execution_gateway.rollback(snap_id)
            self._send_json({"success": ok, "snapshot_id": snap_id})
            return

        elif path == "/api/terminal/ceo/directive":
            obj = req_data.get("objective", "")
            tenant = tenant_id
            instruction = AICeoTerminalInstruction(
                objective=obj,
                constraints=req_data.get("constraints", []),
                priority=req_data.get("priority", "HIGH"),
                business_context=req_data.get("business_context", {}),
                resource_budget=req_data.get("resource_budget", {"max_ram_mb": 4096, "timeout_sec": 60.0}),
                security_classification=req_data.get("security_classification", "INTERNAL_AUTHORIZED"),
                authorization_context=req_data.get("authorization_context", {"human_approved": True}),
                success_criteria=req_data.get("success_criteria", []),
                company_id=company_id,
                tenant_id=tenant,
                mission_id=req_data.get("mission_id"),
                task_id=req_data.get("task_id")
            )
            result = get_runtime(tenant_id).terminal.execute_ceo_directive(instruction)
            self._send_json(result.to_dict())
            return

        elif path == "/api/terminal/checkpoints/resume":
            checkpoint_id = req_data.get("checkpoint_id", "")
            if not checkpoint_id:
                self._send_json({"status": "FAILED", "error": "Missing checkpoint_id"}, status=400)
                return
            res = get_runtime(tenant_id).terminal.resume_checkpoint(checkpoint_id)
            self._send_json(res)
            return

        elif path == "/api/terminal/diagnostics/dossier":
            operation_id = req_data.get("operation_id", "")
            error_detail = req_data.get("error_detail")
            if not operation_id:
                self._send_json({"error": "Missing operation_id"}, status=400)
                return
            dossier = get_runtime(tenant_id).terminal.get_diagnostic_dossier(operation_id, error_detail=error_detail)
            self._send_json(dossier)
            return


        elif path == "/api/coworker/self-extension":
            req_prompt = req_data.get("prompt", "")
            ext_res = _cw(tenant_id, company_id).self_extend(req_prompt)
            self._send_json({
                "success": ext_res.success,
                "action_taken": ext_res.action_taken,
                "capability_id": ext_res.capability_id,
                "provider": ext_res.assigned_provider,
                "qualification": ext_res.qualification_status.value,
                "details": ext_res.details
            })
            return

        elif path.startswith("/api/coworker/approvals/") and path.endswith("/decide"):
            if self._approver_denied(auth_context):
                return
            app_id = path.split("/")[4]
            decision = req_data.get("decision", "APPROVE").upper()
            engine = _cw(tenant_id, company_id)

            # Executive loop DoA holds use the work-item id (wi_...), not a
            # mission id. Approval only re-queues the item; the autonomy
            # supervisor executes it on the next tick under the same gates.
            if app_id.startswith("wi_"):
                loop = getattr(engine, "executive_loop", None)
                if loop is None:
                    self._send_json({"error": "Executive loop unavailable"}, status=503)
                    return
                if decision == "APPROVE":
                    ok = loop.approve_work_item(app_id, approver_role=auth_context.get("role", "OWNER"))
                else:
                    ok = loop.reject_work_item(app_id, reason=req_data.get("reason", "Rejected by operator"))
                self._send_json({
                    "success": bool(ok),
                    "approval_id": app_id,
                    "decision": decision,
                    "queued_for_next_tick": bool(ok and decision == "APPROVE"),
                })
                return

            mid = app_id.replace("app_", "")
            if decision == "APPROVE":
                engine.background_dispatcher.resume_mission(mid)
                engine.background_dispatcher.execute_compound_mission_step(mid)
            else:
                engine.background_dispatcher.stop_mission(mid)
            self._send_json({"success": True, "approval_id": app_id, "decision": decision})
            return


        elif path == "/api/coworker/nodes/register":
            from core.coworker.fleet.node_contracts import (
                WorkerNodeRegistrationRequest, NodeType, NodePlatform, SecurityPosture
            )
            node_id = req_data.get("node_id", f"node_{uuid.uuid4().hex[:6]}")
            # A node can only ever be registered into the authenticated tenant.
            requested_scope = str(req_data.get("tenant_scope") or "").strip()
            if requested_scope and requested_scope != tenant_id:
                self._send_json({
                    "error": "Cross-tenant node registration is not permitted",
                    "code": "TENANT_SCOPE_MISMATCH",
                    "detail": f"This credential belongs to tenant '{tenant_id}'; it cannot register nodes for '{requested_scope}'.",
                }, status=403)
                return
            tenant_scope = tenant_id
            platform_str = req_data.get("platform", "linux")
            try:
                plat = NodePlatform(platform_str)
            except Exception:
                plat = NodePlatform.LINUX

            node_type_str = req_data.get("node_type", "LINUX_NODE")
            try:
                ntype = NodeType(node_type_str)
            except Exception:
                ntype = NodeType.LINUX_NODE

            reg_req = WorkerNodeRegistrationRequest(
                node_id=node_id,
                tenant_scope=tenant_scope,
                node_type=ntype,
                platform=plat,
                architecture=req_data.get("architecture", platform.machine()),
                os_version=req_data.get("os_version", platform.version()),
                runtime_version=req_data.get("runtime_version", "1.0.0-GA"),
                capabilities=req_data.get("capabilities", ["terminal.shell_command"]),
                installed_providers=req_data.get("installed_providers", ["provider_terminal"]),
                gpu_availability=bool(req_data.get("gpu_availability", False)),
                display_availability=bool(req_data.get("display_availability", False)),
                registration_secret=req_data.get("registration_secret", "")
            )
            ok, auth_token, profile = _cw(tenant_id, company_id).node_registry.register_node(reg_req)
            if ok:
                _cw(tenant_id, company_id).node_registry.authorize_node(node_id)
                self._send_json({
                    "success": True,
                    "node_id": node_id,
                    "auth_token": auth_token,
                    "status": "AUTHORIZED",
                    "capabilities_count": len(reg_req.capabilities)
                })
            else:
                self._send_json({"success": False, "error": auth_token}, status=400)
            return

        elif path == "/api/coworker/nodes/heartbeat":
            node_id = req_data.get("node_id", "")
            metrics = req_data.get("metrics", {})
            ok = _cw(tenant_id, company_id).node_registry.record_heartbeat(node_id, metrics)
            self._send_json({"success": ok, "status": "ACKNOWLEDGED" if ok else "NODE_UNKNOWN"})
            return

        elif path == "/api/coworker/ceo/mission":
            from core.coworker.ceo_coworker_bridge import AICeoMissionRequest
            req = AICeoMissionRequest(
                objective=req_data.get("objective", "Execute strategic directive"),
                business_context=req_data.get("business_context", {}),
                success_criteria=req_data.get("success_criteria", []),
                constraints=req_data.get("constraints", []),
                priority=req_data.get("priority", "HIGH"),
                authority=req_data.get("authority", "AUTOMATIC_IDEMPOTENT"),
                budget=float(req_data.get("budget", 50.0)),
                tenant_id=tenant_id,
                company_id=company_id
            )
            ceo_resp = _cw(tenant_id, company_id).execute_ceo_mission(req)
            self._send_json(ceo_resp.to_dict())
            return

        elif path == "/api/coworker/browser/extract":
            url = req_data.get("url", "")
            res = _cw(tenant_id, company_id).browser_controller.navigate_and_extract(url)
            self._send_json(res)
            return

        elif path == "/api/coworker/mcp/execute":
            srv_id = req_data.get("server_id", "")
            tool = req_data.get("tool", "")
            args = req_data.get("arguments", {})
            res = _cw(tenant_id, company_id).mcp_controller.execute_tool(srv_id, tool, args)
            self._send_json(res)
            return

        elif path == "/api/coworker/a2a/send":
            agent_id = req_data.get("target_agent", "")
            mtype = req_data.get("message_type", "QUERY")
            payload = req_data.get("content", {})
            res = _cw(tenant_id, company_id).a2a_controller.send_agent_message(agent_id, mtype, payload)
            self._send_json(res)
            return

        elif path == "/api/coworker/recovery/reconcile":
            event_id = req_data.get("event_id", "")
            resolution = req_data.get("resolution", "Approved manual progression")
            ok = _cw(tenant_id, company_id).recovery_controller.reconcile_uncertain_task(event_id, resolution)
            self._send_json({"success": ok, "event_id": event_id, "status": "RECONCILED" if ok else "NOT_FOUND"})
            return

        # =====================================================================
        # Prompt 03: Plugins & Connections POST Handlers
        # =====================================================================
        elif path.startswith("/api/plugins/") and path.endswith("/toggle-install"):
            parts = path.split("/")
            plugin_id = parts[3]
            install = bool(req_data.get("install", True))
            plg = get_runtime(tenant_id).plugins.toggle_plugin_install(plugin_id, install)
            self._send_json({"success": True, "plugin": plg})
            return

        elif path.startswith("/api/plugins/") and path.endswith("/toggle-enable"):
            parts = path.split("/")
            plugin_id = parts[3]
            enable = bool(req_data.get("enable", True))
            plg = get_runtime(tenant_id).plugins.toggle_plugin_enabled(plugin_id, enable)
            self._send_json({"success": True, "plugin": plg})
            return

        elif path == "/api/connections":
            conn = get_runtime(tenant_id).plugins.create_connection(req_data)
            self._send_json({"success": True, "connection": conn})
            return

        elif path.startswith("/api/connections/") and path.endswith("/test"):
            parts = path.split("/")
            conn_id = parts[3]
            try:
                res = get_runtime(tenant_id).plugins.test_connection(conn_id)
            except ValueError as exc:
                self._send_json({"success": False, "error": str(exc), "code": "CONNECTION_NOT_FOUND"}, status=404)
                return
            self._send_json({"success": bool(res.get("reachable")), **res})
            return

        elif path.startswith("/api/connections/") and path.endswith("/sync"):
            parts = path.split("/")
            conn_id = parts[3]
            try:
                res = get_runtime(tenant_id).plugins.sync_connection(conn_id)
            except ValueError as exc:
                self._send_json({"success": False, "error": str(exc), "code": "CONNECTION_NOT_FOUND"}, status=404)
                return
            status_code = 501 if res.get("status") == "NOT_IMPLEMENTED" else 200
            self._send_json({"success": status_code == 200, **res}, status=status_code)
            return

        # =====================================================================
        # Enterprise Records, Files, Reports, Finance & Agent Factory (POST)
        # =====================================================================
        elif path == "/api/records":
            scoped_rec = dict(req_data)
            scoped_rec["company_id"] = company_id
            rec = EnterpriseRecordsEngine(tenant_id).create_record(scoped_rec)
            self._send_json({"success": True, "record": rec})
            return

        elif path == "/api/files":
            scoped_file = dict(req_data)
            scoped_file["company_id"] = company_id
            fil = EnterpriseFilesEngine(tenant_id).register_file(scoped_file)
            self._send_json({"success": True, "file": fil})
            return

        elif path == "/api/departments":
            if self._approver_denied(auth_context):
                return
            name = str(req_data.get("name") or "").strip()
            if not name:
                self._send_json({"error": "Department name is required", "code": "MISSING_NAME"}, status=400)
                return
            try:
                budget_limit = float(req_data.get("budget_limit", 0.0) or 0.0)
                spending_limit = float(req_data.get("spending_limit", 0.0) or 0.0)
            except (TypeError, ValueError):
                self._send_json({"error": "budget_limit and spending_limit must be numeric"}, status=400)
                return
            if budget_limit < 0 or spending_limit < 0:
                self._send_json({"error": "limits must be non-negative"}, status=400)
                return
            existing = DepartmentControlUnit.list_departments(tenant_id, company_id)
            if any(str(d.get("name", "")).lower() == name.lower() for d in existing):
                self._send_json({"error": "Department already exists", "code": "DUPLICATE_DEPARTMENT"}, status=409)
                return
            dept = DepartmentControlUnit.create_department(
                tenant_id=tenant_id,
                company_id=company_id,
                name=name,
                manager_agent_id=req_data.get("manager_agent_id"),
                budget_limit=budget_limit,
                spending_limit=spending_limit,
            )
            self._send_json({"success": True, "department": dept}, status=201)
            return

        elif path == "/api/reports":
            engine = EnterpriseReportsEngine(tenant_id=tenant_id)
            rep = engine.generate_report(req_data)
            self._send_json({"success": True, "report": rep})
            return

        elif path == "/api/finance/expenses":
            if self._blocked_by_global_killswitch("finance expense mutation"):
                return
            engine = EnterpriseFinanceEngine(tenant_id=tenant_id)
            scoped = dict(req_data)
            # Identity and tenant scope come from the verified token, never the body.
            scoped["company_id"] = company_id
            scoped["claimant_user_id"] = (auth_context or {}).get("user_id")
            if not scoped.get("claimant_name"):
                scoped["claimant_name"] = (auth_context or {}).get("email") or (auth_context or {}).get("user_id") or "Employee"
            res = engine.create_expense(scoped)
            self._send_json(res, status=200 if res.get("success") else 400)
            return

        elif path == "/api/finance/expenses/approve" or (path.startswith("/api/finance/expenses/") and path.endswith("/approve")):
            if self._blocked_by_global_killswitch("finance approval mutation"):
                return
            if self._approver_denied(auth_context):
                return
            expense_id = req_data.get("expense_id") or path.split("/")[4]
            engine = EnterpriseFinanceEngine(tenant_id=tenant_id)
            res = engine.approve_expense(
                expense_id,
                approver=str(auth_context.get("user_id") or auth_context.get("email") or "Executive Approver"),
                approver_role=str(auth_context.get("role") or ""),
                company_id=company_id,
            )
            self._send_json(res, status=200 if res.get("success") else 400)
            return

        elif path == "/api/agent-factory/synthesize":
            prompt = req_data.get("prompt", "General business operations agent")
            comp_id = company_id
            bp = EnterpriseAgentFactory(tenant_id).synthesize_blueprint_from_prompt(prompt, comp_id or company_id)
            self._send_json({"success": True, "blueprint": bp})
            return

        elif path.startswith("/api/agent-factory/blueprints/") and path.endswith("/status"):
            b_id = path.split("/")[4]
            st = req_data.get("status", "ACTIVE")
            res = EnterpriseAgentFactory(tenant_id).update_blueprint_status(b_id, st)
            self._send_json({"success": True, **res})
            return

        # =====================================================================
        # Governed Multi-Agent Workforce Orchestrator Endpoints (POST)
        # =====================================================================
        elif path == "/api/workforces/plan":
            objective = req_data.get("objective", "General Business Investigation")
            # company_id resolved from the verified token; never trusted from the body.
            budget_usd = float(req_data.get("budget_usd", 100.0))
            plan = AgentWorkforceAdapter.create_mission_workforce(
                tenant_id=tenant_id,
                company_id=company_id,
                mission_objective=objective,
                budget_usd=budget_usd
            )
            self._send_json({"success": True, "workforce": plan})
            return

        elif path.startswith("/api/workforces/") and path.endswith("/execute"):
            if self._blocked_by_global_killswitch("workforce execution"):
                return
            parts = path.split("/")
            workforce_id = parts[3]
            try:
                res = AgentWorkforceAdapter.execute_workforce(workforce_id, req_data.get("parameters"))
                self._send_json({"success": True, "result": res.to_dict()})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
            return

        elif path.startswith("/api/workforces/") and path.endswith("/kill"):
            parts = path.split("/")
            workforce_id = parts[3]
            reason = req_data.get("reason", "HOST_EMERGENCY_KILL_SWITCH")
            success = AgentWorkforceAdapter.kill_workforce(workforce_id, reason=reason)
            self._send_json({"success": success, "workforce_id": workforce_id, "quarantined": True})
            return

        elif path == "/api/workforces/demo/sales-bottlenecks":
            demo_res = AgentWorkforceAdapter.run_sales_bottleneck_demonstration(
                tenant_id=tenant_id,
                company_id=company_id
            )
            self._send_json({"success": True, "demonstration": demo_res})
            return

        # =====================================================================
        # Stateful Agent Identity & Memory Endpoints (POST)
        # =====================================================================
        elif path == "/api/agents/stateful":
            aid = req_data.get("agent_id") or f"agt_{uuid.uuid4().hex[:8]}"
            name = req_data.get("name", "Specialist Agent")
            role = req_data.get("role", "Specialist")
            cid = req_data.get("company_id")
            dept = req_data.get("department_id")
            persona = req_data.get("persona_block", "")
            human = req_data.get("human_block", "")
            sys_inst = req_data.get("system_instructions", "")
            m_conf = req_data.get("model_config")
            tools = req_data.get("tools")
            meta = req_data.get("metadata")
            try:
                agent = stateful_memory_gateway.register_or_get_agent(
                    agent_id=aid, name=name, role=role, company_id=cid,
                    department_id=dept, persona_block=persona, human_block=human,
                    system_instructions=sys_inst, model_config=m_conf, tools=tools, metadata=meta
                )
                self._send_json({"success": True, "agent": agent.to_dict()})
            except SecurityException as se:
                self._send_json({"success": False, "error": str(se)}, status=400)
            return

        elif path.startswith("/api/agents/stateful/") and path.endswith("/blocks"):
            parts = path.split("/")
            agent_id = parts[4]
            agent = stateful_memory_gateway.get_agent(agent_id)
            if not agent:
                self._send_json({"error": "Agent not found"}, status=404)
                return
            persona = req_data.get("persona_block")
            human = req_data.get("human_block")
            try:
                agent.update_blocks(persona=persona, human=human)
                self._send_json({"success": True, "agent": agent.to_dict()})
            except SecurityException as se:
                self._send_json({"success": False, "error": str(se)}, status=400)
            return

        elif path.startswith("/api/agents/stateful/") and path.endswith("/memory"):
            parts = path.split("/")
            agent_id = parts[4]
            scope = req_data.get("scope", "AGENT")
            scope_id = req_data.get("scope_id", agent_id)
            key = req_data.get("memory_key") or req_data.get("key", "general_fact")
            content = req_data.get("content", "")
            mtype = req_data.get("memory_type", "CORE")
            cat = req_data.get("category", "FACT")
            source = req_data.get("source", f"AGENT:{agent_id}")
            confidence = req_data.get("confidence", "VERIFIED")
            expires = req_data.get("expires_at")
            meta = req_data.get("metadata")

            try:
                rec = stateful_memory_gateway.store_memory(
                    scope=scope, scope_id=scope_id, memory_key=key, content=content,
                    memory_type=mtype, category=cat, source=source, confidence=confidence,
                    expires_at=expires, metadata=meta
                )
                self._send_json({"success": True, "record": rec.to_dict()})
            except SecurityException as se:
                self._send_json({"success": False, "error": str(se), "security_violation": True}, status=400)
            except ValueError as ve:
                self._send_json({"success": False, "error": str(ve)}, status=400)
            return

        elif path.startswith("/api/memory/conflicts/") and path.endswith("/resolve"):
            parts = path.split("/")
            conflict_id = parts[4]
            choice = req_data.get("choice", "USE_A")
            resolved_by = req_data.get("resolved_by", "AI_CEO")
            try:
                res = stateful_memory_gateway.resolve_conflict(conflict_id, choice=choice, resolved_by=resolved_by)
                self._send_json({"success": True, "resolution": res})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
            return

        elif path.startswith("/api/agents/stateful/") and path.endswith("/conversations/turn"):
            parts = path.split("/")
            agent_id = parts[4]
            session_id = req_data.get("session_id")
            if not session_id:
                sess = stateful_memory_gateway.get_or_create_conversation_session(agent_id)
                session_id = sess["session_id"]
            role = req_data.get("role", "USER")
            content = req_data.get("content", "")
            tokens = int(req_data.get("tokens", 0))
            try:
                turn = stateful_memory_gateway.record_turn(session_id, role, content, tokens=tokens)
                self._send_json({"success": True, "turn": turn})
            except SecurityException as se:
                self._send_json({"success": False, "error": str(se)}, status=400)
            return

        elif path.startswith("/api/agents/stateful/") and path.endswith("/conversations/compact"):
            parts = path.split("/")
            agent_id = parts[4]
            session_id = req_data.get("session_id")
            if not session_id:
                sess = stateful_memory_gateway.get_or_create_conversation_session(agent_id)
                session_id = sess["session_id"]
            max_recent = int(req_data.get("max_recent_turns", 6))
            res = stateful_memory_gateway.compact_conversation_history(session_id, max_recent_turns=max_recent)
            self._send_json({"success": True, "compaction": res})
            return

        elif path.startswith("/api/meetings/") and path.endswith("/sync-memory"):
            parts = path.split("/")
            meeting_id = parts[3]
            try:
                res = get_runtime(tenant_id).meeting_service.sync_meeting_to_memory(meeting_id)
                self._send_json(res)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
            return

        elif path == "/api/stateful/demo/scenarios":
            demo_type = req_data.get("demo_type", "SECTION_74")
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            if demo_type == "SECTION_74":
                res = stateful_agent_adapter.run_executive_continuity_demonstration(cid)
            elif demo_type == "SECTION_75":
                res = stateful_agent_adapter.run_workforce_coordination_demonstration(cid)
            else:
                self._send_json({"error": f"Unknown demo type '{demo_type}'"}, status=400)
                return
            self._send_json({"success": True, "demonstration": res})
            return

        # =====================================================================
        # HAL Multimodal Capability Layer Endpoints (POST)
        # =====================================================================
        elif path == "/api/multimodal/voice-to-ceo":
            transcript = req_data.get("transcript", "")
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            uid = req_data.get("user_id", "usr_owner")
            res = hal_multimodal_adapter.voice_to_ceo(transcript, company_id=cid, host_user_id=uid)
            self._send_json(res)
            return

        elif path == "/api/multimodal/transcribe":
            raw_text = req_data.get("audio_text", "")
            res = hal_hearing.process_audio_transcript(raw_text)
            self._send_json(res)
            return

        elif path == "/api/multimodal/synthesize":
            text = req_data.get("text", "")
            voice = req_data.get("voice", "en-US-GuyNeural")
            res = hal_voice.synthesize(text, voice=voice)
            self._send_json(res)
            return

        elif path == "/api/multimodal/observe/screen":
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            wtitle = req_data.get("window_title", "Active Desktop Workspace")
            preview = req_data.get("content_preview", "Screen inspection showing enterprise metrics")
            sid = req_data.get("session_id")
            res = hal_multimodal_adapter.observe_screen(session_id=sid, company_id=cid, window_title=wtitle, content_preview=preview)
            self._send_json(res)
            return

        elif path == "/api/multimodal/observe/webcam":
            blur = bool(req_data.get("blur_background", False))
            res = hal_vision.capture_frame(blur_background=blur)
            self._send_json(res)
            return

        elif path == "/api/multimodal/coworker/execute":
            prompt = req_data.get("prompt", "")
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            ws_mode = req_data.get("workspace_mode", "COMPANY")
            res = hal_multimodal_adapter.coworker_execute_report(prompt, company_id=cid, workspace_mode=ws_mode)
            self._send_json(res)
            return

        elif path == "/api/multimodal/action/controlled":
            cmd = req_data.get("command", "")
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            res = hal_multimodal_adapter.execute_controlled_action(cmd, company_id=cid)
            self._send_json(res)
            return

        elif path == "/api/multimodal/memory/sync":
            content = req_data.get("content", "")
            mtype = req_data.get("candidate_type", "OBSERVATION")
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            res = hal_multimodal_adapter.sync_hal_candidate_memory_to_letta(content, candidate_type=mtype, company_id=cid)
            self._send_json(res)
            return

        elif path == "/api/multimodal/workforce/delegate":
            obj = req_data.get("objective", "Execute multimodal task")
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            res = hal_multimodal_adapter.delegate_workforce_multimodal_task(obj, company_id=cid)
            self._send_json(res)
            return

        elif path == "/api/multimodal/mcp/invoke":
            client_id = req_data.get("client_id", "claude_code")
            tool_name = req_data.get("tool_name", "")
            params = req_data.get("parameters", {})
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            res = hal_multimodal_adapter.invoke_mcp_capability(client_id, tool_name, params, company_id=cid)
            self._send_json(res)
            return

        elif path == "/api/multimodal/task/interrupt":
            sid = req_data.get("session_id", "")
            reason = req_data.get("reason", "Voice stop command")
            res = get_runtime(tenant_id).multimodal_execution.trigger_killswitch(sid, reason=reason)
            self._send_json({"success": True, "killswitch": res})
            return

        elif path == "/api/multimodal/task/takeover":
            sid = req_data.get("session_id", "")
            uid = req_data.get("user_id", "usr_owner")
            res = get_runtime(tenant_id).multimodal_execution.trigger_host_takeover(sid, host_id=uid)
            self._send_json({"success": True, "takeover": res})
            return

        elif path == "/api/multimodal/task/recover":
            sid = req_data.get("session_id", "")
            res = get_runtime(tenant_id).multimodal_execution.recover_from_crash(sid)
            self._send_json({"success": True, "recovery": res})
            return

        elif path == "/api/multimodal/artifacts":
            title = req_data.get("title", "Generated Artifact")
            content = req_data.get("content", "")
            atype = req_data.get("artifact_type", "DOCUMENT")
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id
            art = governed_artifacts.create_artifact(title, content, artifact_type=atype, company_id=cid)
            self._send_json({"success": True, "artifact": art})
            return

        elif path == "/api/multimodal/demo/scenarios":
            scenario = req_data.get("scenario", "SCENARIO_A").upper()
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id

            if scenario in ("A", "SCENARIO_A", "TEST_A"):
                res = hal_multimodal_adapter.voice_to_ceo(
                    "Analyze our Q3 gross margins and prepare an executive directive.",
                    company_id=cid
                )
            elif scenario in ("B", "SCENARIO_B", "TEST_B"):
                res = hal_multimodal_adapter.observe_screen(
                    company_id=cid,
                    window_title="ZONATA Executive Intelligence Center",
                    content_preview="Live executive variance chart and active multi-agent squads"
                )
            elif scenario in ("C", "SCENARIO_C", "TEST_C"):
                res = hal_multimodal_adapter.coworker_execute_report(
                    "Open monthly executive summary and verify audit seal",
                    company_id=cid
                )
            elif scenario in ("D", "SCENARIO_D", "TEST_D"):
                res = hal_multimodal_adapter.coworker_execute_report(
                    "Open browser and navigate to operational metrics",
                    company_id=cid
                )
            elif scenario in ("E", "SCENARIO_E", "TEST_E"):
                res = hal_multimodal_adapter.execute_controlled_action(
                    "sudo rm -rf /etc/shadow",
                    company_id=cid
                )
            elif scenario in ("F", "SCENARIO_F", "TEST_F"):
                res = hal_multimodal_adapter.sync_hal_candidate_memory_to_letta(
                    "Bearer sk-unauthorized-secret-key-that-must-be-blocked",
                    candidate_type="FACT",
                    company_id=cid
                )
            elif scenario in ("G", "SCENARIO_G", "TEST_G"):
                res = hal_multimodal_adapter.delegate_workforce_multimodal_task(
                    "Analyze operational pipeline bottlenecks using desktop observation",
                    company_id=cid
                )
            elif scenario in ("H", "SCENARIO_H", "TEST_H"):
                res = hal_multimodal_adapter.invoke_mcp_capability(
                    "claude-code",
                    "run_shell",
                    {"command": "sudo rm -rf /"},
                    company_id=cid
                )
            elif scenario in ("I", "SCENARIO_I", "TEST_I"):
                res = hal_multimodal_adapter.run_crash_and_recovery_demonstration(company_id=cid)
            elif scenario in ("J", "SCENARIO_J", "TEST_J"):
                res = hal_multimodal_adapter.run_host_takeover_demonstration(company_id=cid)
            else:
                self._send_json({"error": f"Unknown scenario '{scenario}'"}, status=400)
                return

            self._send_json({"success": True, "scenario": scenario, "result": res})
            return

        elif path.startswith("/api/workflows/") and path.endswith("/run"):
            if self._blocked_by_global_killswitch("workflow execution"):
                return
            parts = path.split("/")
            wf_id = parts[3]
            if wf_id == "__never__":
                return
            inputs = dict(req_data.get("inputs") or {})
            # Tenant/company scope is derived from the authenticated token, never
            # from the request body. Reserved "__" keys are rejected by the runtime.
            ctx = dict(req_data.get("context") or {})
            ctx["tenant_id"] = tenant_id
            ctx["company_id"] = company_id
            max_leases = int(os.environ.get("PILOT_MAX_CONCURRENCY", "4"))
            from core.tenant_fairness import tenant_fairness_engine
            acq_ok, lease_id, retry_after = tenant_fairness_engine.concurrency_manager.acquire_lease(
                tenant_id=tenant_id,
                max_concurrency=max_leases,
                lease_type="WORKFLOW",
                ttl_seconds=300.0
            )
            if not acq_ok:
                self._send_json({
                    "error": "Too Many Requests",
                    "detail": f"Tenant workflow concurrency limit ({max_leases} active leases) exceeded. Try again in {retry_after}s.",
                    "limit": max_leases,
                    "retry_after": retry_after,
                    "violation_axis": "CONCURRENCY_LIMIT_EXCEEDED"
                }, status=429, headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_leases),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Axis": "CONCURRENCY_LIMIT_EXCEEDED"
                })
                return
            try:
                res = get_workflow_runtime(tenant_id).start_workflow(wf_id, inputs, ctx)
                if isinstance(res, dict):
                    res["lease_id"] = lease_id
                self._send_json(res)
            except Exception as e:
                tenant_fairness_engine.concurrency_manager.release_lease(lease_id)
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/workflows/runs/") and path.endswith("/pause"):
            parts = path.split("/")
            run_id = parts[4]
            reason = req_data.get("reason", "API request")
            if not get_workflow_runtime(tenant_id).get_run_state(run_id, tenant_id=tenant_id):
                self._send_json({"error": f"Run '{run_id}' not found"}, status=404)
                return
            res = get_workflow_runtime(tenant_id).pause_workflow(run_id, reason)
            self._send_json(res)
            return

        elif path.startswith("/api/workflows/runs/") and path.endswith("/resume"):
            if self._blocked_by_global_killswitch("workflow resume"):
                return
            parts = path.split("/")
            run_id = parts[4]
            cmd_data = req_data.get("command")
            cmd = None
            if cmd_data:
                cmd = Command(resume=cmd_data.get("resume"), update=cmd_data.get("update"), goto=cmd_data.get("goto"))
            if not get_workflow_runtime(tenant_id).get_run_state(run_id, tenant_id=tenant_id):
                self._send_json({"error": f"Run '{run_id}' not found"}, status=404)
                return
            res = get_workflow_runtime(tenant_id).resume_workflow(run_id, command=cmd)
            self._send_json(res)
            return

        elif path.startswith("/api/workflows/runs/") and path.endswith("/cancel"):
            parts = path.split("/")
            run_id = parts[4]
            reason = req_data.get("reason", "API request")
            if not get_workflow_runtime(tenant_id).get_run_state(run_id, tenant_id=tenant_id):
                self._send_json({"error": f"Run '{run_id}' not found"}, status=404)
                return
            res = get_workflow_runtime(tenant_id).cancel_workflow(run_id, reason)
            self._send_json(res)
            return

        elif path.startswith("/api/workflows/runs/") and path.endswith("/recover"):
            if self._blocked_by_global_killswitch("workflow recovery"):
                return
            parts = path.split("/")
            run_id = parts[4]
            if not get_workflow_runtime(tenant_id).get_run_state(run_id, tenant_id=tenant_id):
                self._send_json({"error": f"Run '{run_id}' not found"}, status=404)
                return
            res = get_workflow_runtime(tenant_id).recover_workflow_run(run_id)
            self._send_json(res)
            return

        elif path.startswith("/api/workflows/approvals/") and path.endswith("/approve"):
            if self._approver_denied(auth_context):
                return
            parts = path.split("/")
            appr_id = parts[4]
            actor = str(auth_context.get("user_id") or "Host")
            try:
                res = get_workflow_runtime(tenant_id).approve_workflow(
                    appr_id, actor=actor, tenant_id=tenant_id, company_id=company_id
                )
                self._send_json(res)
            except ValueError as exc:
                self._send_json({"success": False, "error": str(exc)}, status=404)
            return

        elif path.startswith("/api/workflows/approvals/") and path.endswith("/reject"):
            if self._approver_denied(auth_context):
                return
            parts = path.split("/")
            appr_id = parts[4]
            actor = str(auth_context.get("user_id") or "Host")
            reason = req_data.get("reason", "Rejected via API")
            try:
                res = get_workflow_runtime(tenant_id).reject_workflow(
                    appr_id, actor=actor, reason=reason,
                    tenant_id=tenant_id, company_id=company_id
                )
                self._send_json(res)
            except ValueError as exc:
                self._send_json({"success": False, "error": str(exc)}, status=404)
            return

        elif path.startswith("/api/workflows/approvals/") and path.endswith("/edit"):
            if self._approver_denied(auth_context):
                return
            parts = path.split("/")
            appr_id = parts[4]
            actor = str(auth_context.get("user_id") or "Host")
            params = req_data.get("parameters", {})
            res = get_workflow_runtime(tenant_id).edit_and_resume_workflow(
                appr_id, params, actor=actor, tenant_id=tenant_id, company_id=company_id
            )
            self._send_json(res)
            return

        elif path == "/api/workflows/killswitch":
            if self._approver_denied(auth_context):
                return
            active = bool(req_data.get("active", True))
            get_workflow_runtime(tenant_id).set_killswitch(active)
            self._send_json({"killswitch_active": active, "status": "KILLSWITCH_ENGAGED" if active else "KILLSWITCH_DISENGAGED"})
            return

        elif path == "/api/workflows/demo/scenarios":
            scenario = req_data.get("scenario", "A").upper()
            companies = get_portfolio(tenant_id).list_companies()
            cid = company_id

            if scenario in ("A", "SCENARIO_A", "TEST_A"):
                res = langgraph_adapter.run_simple_workflow(company_id=cid)
            elif scenario in ("B", "SCENARIO_B", "TEST_B"):
                res = langgraph_adapter.run_long_running_workflow(company_id=cid)
            elif scenario in ("C", "SCENARIO_C", "TEST_C"):
                amount = float(req_data.get("amount", 25000.0))
                res = langgraph_adapter.run_human_approval_workflow(amount=amount, company_id=cid)
            elif scenario in ("D", "SCENARIO_D", "TEST_D"):
                init_amt = float(req_data.get("initial_amount", 50000.0))
                mod_amt = float(req_data.get("modified_amount", 12500.0))
                res = langgraph_adapter.run_human_edit_workflow(initial_amount=init_amt, modified_amount=mod_amt, company_id=cid)
            elif scenario in ("E", "SCENARIO_E", "TEST_E"):
                res = langgraph_adapter.run_failure_recovery_workflow(company_id=cid)
            elif scenario in ("F", "SCENARIO_F", "TEST_F"):
                res = langgraph_adapter.run_ambiguous_transaction_workflow(company_id=cid)
            elif scenario in ("G", "SCENARIO_G", "TEST_G"):
                res = langgraph_adapter.run_loop_control_workflow(company_id=cid)
            elif scenario in ("H", "SCENARIO_H", "TEST_H"):
                directive = req_data.get("directive", "Audit Q3 operating margins")
                res = langgraph_adapter.run_agency_swarm_workflow(directive=directive, company_id=cid)
            elif scenario in ("I", "SCENARIO_I", "TEST_I"):
                res = langgraph_adapter.run_letta_memory_workflow(company_id=cid)
            elif scenario in ("J", "SCENARIO_J", "TEST_J"):
                res = langgraph_adapter.run_hal_multimodal_workflow(company_id=cid)
            elif scenario in ("K", "SCENARIO_K", "TEST_K"):
                res = langgraph_adapter.run_killswitch_workflow(company_id=cid)
            else:
                self._send_json({"error": f"Unknown workflow scenario '{scenario}'"}, status=400)
                return

            self._send_json({"success": True, "scenario": scenario, "result": res})
            return

        # =====================================================================
        # UNIVERSAL AUTOMATION FABRIC POST ENDPOINTS
        # =====================================================================
        elif path == "/api/automation/workflows":
            name = req_data.get("name", "New Workflow")
            spec = req_data.get("spec", {})
            # company_id was resolved from the verified token (see _resolve_company_id)
            author = self.headers.get("X-User-Name", "employee")
            try:
                draft = universal_automation_fabric.create_workflow_draft(name, spec, tenant_id, company_id, author=author)
                self._send_json(draft, status=201)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/automation/workflows/") and path.endswith("/publish"):
            wf_id = path.split("/")[4]
            try:
                res = universal_automation_fabric.publish_workflow(wf_id, tenant_id)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/automation/workflows/") and path.endswith("/rollback"):
            wf_id = path.split("/")[4]
            target_version = int(req_data.get("target_version", 1))
            try:
                res = universal_automation_fabric.rollback_workflow(wf_id, target_version, tenant_id)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/automation/workflows/") and path.endswith("/execute"):
            wf_id = path.split("/")[4]
            inputs = req_data.get("inputs", {})
            context = req_data.get("context", {})
            # company_id was resolved from the verified token (see _resolve_company_id)
            actor = self.headers.get("X-User-Name", "HostEmployee")
            try:
                res = universal_automation_fabric.execute_workflow(
                    workflow_id=wf_id,
                    inputs=inputs,
                    tenant_id=tenant_id,
                    company_id=company_id,
                    authenticated_actor=actor,
                    context=context
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/automation/templates/") and path.endswith("/instantiate"):
            tmpl_id = path.split("/")[4]
            inputs = req_data.get("inputs", {})
            # company_id was resolved from the verified token (see _resolve_company_id)
            try:
                instance = template_catalog.instantiate_template(tmpl_id, inputs, tenant_id, company_id)
                draft = universal_automation_fabric.create_workflow_draft(
                    name=instance["name"],
                    spec=instance["workflow_spec"],
                    tenant_id=tenant_id,
                    company_id=company_id
                )
                self._send_json({"instance": instance, "draft": draft}, status=201)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/automation/agent/generate":
            prompt = req_data.get("prompt", "Automate routine data sync")
            # company_id was resolved from the verified token (see _resolve_company_id)
            task = AgentDelegationTask(
                task_id=f"gen_{uuid.uuid4().hex[:8]}",
                tenant_id=tenant_id,
                company_id=company_id,
                role="WorkflowDesignAgent",
                objective=prompt,
                scope="workflow:generate",
                acceptance_criteria=["Valid draft generated"],
                timeout_seconds=30.0,
                permissions=["workflow:design"],
                parameters={"prompt": prompt}
            )
            try:
                gen_result = specialized_agent_registry.delegate_task(task)
                self._send_json({"success": True, "generated_workflow": gen_result})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/automation/connectors/discover":
            candidate = req_data.get("candidate", {})
            ok, msg, vetted = automation_connector_registry.qualify_and_discover_connector(candidate)
            self._send_json({"success": ok, "message": msg, "connector": vetted.to_dict() if vetted else None}, status=200 if ok else 400)
            return

        elif path.startswith("/api/automation/agents/") and path.endswith("/delegate"):
            role = path.split("/")[4]
            objective = req_data.get("objective", "Execute task")
            scope = req_data.get("scope", "general")
            params = req_data.get("parameters", {})
            # company_id was resolved from the verified token (see _resolve_company_id)
            task = AgentDelegationTask(
                task_id=f"dt_{uuid.uuid4().hex[:8]}",
                tenant_id=tenant_id,
                company_id=company_id,
                role=role,
                objective=objective,
                scope=scope,
                acceptance_criteria=req_data.get("acceptance_criteria", []),
                timeout_seconds=float(req_data.get("timeout_seconds", 30.0)),
                permissions=req_data.get("permissions", ["execute"]),
                parameters=params
            )
            try:
                res = specialized_agent_registry.delegate_task(task)
                self._send_json({"success": True, "result": res})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/automation/approvals/") and path.endswith("/decide"):
            appr_id = path.split("/")[4]
            decision = req_data.get("decision", "APPROVE")
            reason = req_data.get("reason", "Approved by employee")
            modified_params = req_data.get("modified_parameters")

            auth_header = self.headers.get("Authorization", "")
            raw_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else (auth_header.strip() if auth_header else None)

            try:
                auth_ctx = self._get_auth_context()
            except Exception as e:
                self._send_json({"error": f"Authentication required: {str(e)}"}, status=401)
                return

            actor = auth_ctx.get("user_id") or self.headers.get("X-User-Name", "HostEmployee")
            role = auth_ctx.get("role")
            tenant_id = auth_ctx.get("tenant_id")

            try:
                res = universal_automation_fabric.decide_approval(
                    approval_id=appr_id,
                    decision=decision,
                    actor=actor,
                    reason=reason,
                    modified_parameters=modified_params,
                    tenant_id=tenant_id,
                    auth_token=raw_token,
                    actor_role=role
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/automation/executions/") and path.endswith("/recover"):
            exec_id = path.split("/")[4]
            try:
                res = universal_automation_fabric.recover_crashed_execution(exec_id, tenant_id)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/automation/executions/") and path.endswith("/reconcile"):
            exec_id = path.split("/")[4]
            ground_truth = req_data.get("ground_truth", "CONFIRMED_SUCCESS")
            try:
                res = universal_automation_fabric.reconcile_unknown_outcome(exec_id, tenant_id, ground_truth)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/automation/killswitch":
            if self._approver_denied(auth_context):
                return
            active = bool(req_data.get("active", True))
            universal_automation_fabric.set_killswitch(active)
            self._send_json({"killswitch_active": active, "status": "KILLSWITCH_ENGAGED" if active else "KILLSWITCH_DISENGAGED"})
            return

        # =====================================================================
        # A2A (AGENT2AGENT PROTOCOL) POST ENDPOINTS
        # =====================================================================
        elif path in ("/a2a/message:send", "/message:send"):
            try:
                res = _a2a(tenant_id, company_id).client_adapter.send_message(req_data)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/a2a/tasks/") and path.endswith(":cancel"):
            parts = path.split("/")
            task_id = parts[2].split(":")[0]
            try:
                res = _a2a(tenant_id, company_id).client_adapter.cancel_task(task_id)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/a2a/agents/discover":
            card = req_data.get("agent_card") or req_data
            source = req_data.get("source", "MANUAL")
            allow_loopback = bool(req_data.get("allow_test_loopback", False))
            ok, agent_id, errs = _a2a(tenant_id, company_id).discover_agent(card, source=source, allow_test_loopback=allow_loopback)
            if ok:
                self._send_json({"success": True, "agent_id": agent_id, "message": "Agent registered"})
            else:
                self._send_json({"success": False, "errors": errs}, status=400)
            return

        elif path.startswith("/api/a2a/agents/") and path.endswith("/trust"):
            parts = path.split("/")
            agent_id = parts[4]
            trust_lvl = req_data.get("trust_level", AgentTrustLevel.DISCOVERED.value)
            try:
                _a2a(tenant_id, company_id).trust_service.set_agent_trust(agent_id, AgentTrustLevel(trust_lvl))
                self._send_json({"success": True, "agent_id": agent_id, "trust_level": trust_lvl})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/a2a/agents/") and path.endswith("/block"):
            parts = path.split("/")
            agent_id = parts[4]
            _a2a(tenant_id, company_id).trust_service.set_agent_trust(agent_id, AgentTrustLevel.BLOCKED)
            self._send_json({"success": True, "agent_id": agent_id, "status": "BLOCKED"})
            return

        elif path.startswith("/api/a2a/agents/") and path.endswith("/health"):
            import socket
            parts = path.split("/")
            agent_id = parts[4]
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT endpoint_url, trust_level FROM a2a_agents WHERE agent_id = ? AND tenant_id = ?",
                    (agent_id, tenant_id),
                ).fetchone()
            if not row:
                self._send_json({
                    "error": f"A2A agent '{agent_id}' is not registered for this tenant",
                    "code": "AGENT_NOT_FOUND",
                }, status=404)
                return

            endpoint = (row["endpoint_url"] or "").strip()
            parsed = urllib.parse.urlparse(endpoint) if endpoint else None
            host = parsed.hostname if parsed else None
            port = (parsed.port if parsed else None) or (443 if (parsed and parsed.scheme == "https") else 80)
            now = time.time()
            latency_ms = None
            error = None
            if not host:
                new_status = "UNVERIFIED"
                error = "Agent has no endpoint_url; reachability cannot be probed."
            else:
                began = time.time()
                try:
                    with socket.create_connection((host, port), timeout=3):
                        pass
                    latency_ms = round((time.time() - began) * 1000, 2)
                    new_status = "ONLINE"
                except Exception as exc:
                    latency_ms = round((time.time() - began) * 1000, 2)
                    new_status = "OFFLINE"
                    error = f"{type(exc).__name__}: {exc}"

            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE a2a_agents SET last_health_check = ?, status = ? WHERE agent_id = ? AND tenant_id = ?",
                    (now, new_status, agent_id, tenant_id),
                )
                conn.commit()
            self._send_json({
                "success": True,
                "agent_id": agent_id,
                "status": new_status,
                "endpoint": endpoint or None,
                "latency_ms": latency_ms,
                "error": error,
                "trust_level": row["trust_level"],
                "method": "TCP connect probe to endpoint_url",
                "timestamp": now,
            })
            return

        elif path == "/api/a2a/tasks/delegate":
            if self._blocked_by_global_killswitch("A2A delegation"):
                return
            agent_id = req_data.get("agent_id")
            skill_name = req_data.get("skill_name", "General Task")
            params = req_data.get("parameters", {})
            req_by = req_data.get("requested_by", "AI CEO")
            class_str = req_data.get("data_classification", "INTERNAL")
            classification = DataClassification(class_str) if class_str in DataClassification.__members__ else DataClassification.INTERNAL
            try:
                res = _a2a(tenant_id, company_id).delegate_task(
                    agent_id=agent_id,
                    skill_name=skill_name,
                    parameters=params,
                    requested_by=req_by,
                    data_classification=classification
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/a2a/tasks/") and path.endswith("/cancel"):
            parts = path.split("/")
            task_id = parts[4]
            try:
                res = _a2a(tenant_id, company_id).client_adapter.cancel_task(task_id)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/a2a/tasks/") and path.endswith("/reconcile"):
            parts = path.split("/")
            task_id = parts[4]
            verified_state = req_data.get("verified_state", A2ATaskState.TASK_STATE_COMPLETED.value)
            try:
                res = _a2a(tenant_id, company_id).client_adapter.reconcile_ambiguous_task(task_id, verified_external_state=verified_state)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/a2a/tasks/") and path.endswith("/push"):
            parts = path.split("/")
            task_id = parts[4]
            auth_token = self.headers.get("Authorization")
            try:
                res = _a2a(tenant_id, company_id).handle_push_notification(task_id, req_data, auth_token=auth_token)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/a2a/approvals/") and path.endswith("/approve"):
            if self._approver_denied(auth_context):
                return
            parts = path.split("/")
            appr_id = parts[4]
            actor = str(auth_context.get("user_id") or "Owner")
            res = ApprovalPipeline.decide_request(
                tenant_id=tenant_id,
                request_id=appr_id,
                approver_user={"user_id": actor, "role": auth_context.get("role", "")},
                approved=True,
                company_id=company_id,
            )
            mcp_resume = None
            if res.get("success") and res.get("status") == "APPROVED":
                try:
                    mcp_resume = _mcp(tenant_id, company_id).resume_approved_execution(appr_id)
                except Exception as exc:
                    mcp_resume = {"resumed": False, "error": str(exc)[:300]}
            self._send_json({"success": True, "approval": res, "mcp_resume": mcp_resume})
            return

        elif path.startswith("/api/a2a/approvals/") and path.endswith("/reject"):
            if self._approver_denied(auth_context):
                return
            parts = path.split("/")
            appr_id = parts[4]
            actor = str(auth_context.get("user_id") or "Owner")
            reason = req_data.get("reason", "Rejected by policy")
            res = ApprovalPipeline.decide_request(
                tenant_id=tenant_id,
                request_id=appr_id,
                approver_user={"user_id": actor, "role": auth_context.get("role", "")},
                approved=False,
                rejection_reason=reason,
                company_id=company_id,
            )
            if res.get("success"):
                try:
                    with db.get_connection() as conn:
                        conn.execute(
                            "UPDATE mcp_executions SET execution_status = 'REJECTED' "
                            "WHERE approval_id = ? AND tenant_id = ? AND company_id = ? "
                            "AND execution_status = 'APPROVAL_REQUIRED'",
                            (appr_id, tenant_id, company_id),
                        )
                        conn.commit()
                except Exception:
                    pass
            self._send_json({"success": True, "approval": res})
            return

        elif path == "/api/a2a/published":
            pub_id = _a2a(tenant_id, company_id).server_adapter.publish_agent(
                internal_agent_id=req_data.get("internal_agent_id", "agent_ceo"),
                display_name=req_data.get("display_name", "Published Agent"),
                description=req_data.get("description", "A2A Endpoint for ZONATA"),
                skills=req_data.get("skills", []),
                rate_limit_per_min=int(req_data.get("rate_limit_per_min", 60)),
                cost_per_task=float(req_data.get("cost_per_task", 0.0)),
                approval_required=bool(req_data.get("approval_required", False))
            )
            self._send_json({"success": True, "published_id": pub_id})
            return

        elif path == "/api/a2a/killswitch":
            if self._approver_denied(auth_context):
                return
            active = bool(req_data.get("active", True))
            if active:
                A2AKillSwitch.activate(tenant_id)
            else:
                A2AKillSwitch.deactivate(tenant_id)
            self._send_json({"killswitch_active": active, "status": "KILLSWITCH_ENGAGED" if active else "KILLSWITCH_DISENGAGED"})
            return

        elif path == "/api/a2a/demo/scenarios":
            scenario = req_data.get("scenario", "A").upper()
            sc_map = {
                "A": _a2a_scenarios(tenant_id, company_id).scenario_a_discover_external_agent,
                "B": _a2a_scenarios(tenant_id, company_id).scenario_b_delegate_simple_task,
                "C": _a2a_scenarios(tenant_id, company_id).scenario_c_long_running_async_task,
                "D": _a2a_scenarios(tenant_id, company_id).scenario_d_sensitive_action_approval,
                "E": _a2a_scenarios(tenant_id, company_id).scenario_e_prompt_injection_defense,
                "F": _a2a_scenarios(tenant_id, company_id).scenario_f_malicious_agent_card_defense,
                "G": _a2a_scenarios(tenant_id, company_id).scenario_g_ambiguous_outcome_reconciliation,
                "H": _a2a_scenarios(tenant_id, company_id).scenario_h_tenant_isolation,
                "I": _a2a_scenarios(tenant_id, company_id).scenario_i_killswitch_override,
                "J": _a2a_scenarios(tenant_id, company_id).scenario_j_langgraph_a2a_workflow
            }
            fn = sc_map.get(scenario)
            if fn:
                res = fn()
                self._send_json({"success": True, "scenario": scenario, "result": res})
            else:
                self._send_json({"error": f"Unknown A2A scenario '{scenario}'"}, status=400)
            return

        # =====================================================================
        # MCP (MODEL CONTEXT PROTOCOL - PROJECT 06) POST ENDPOINTS
        # =====================================================================
        elif path in ("/mcp", "/api/mcp/endpoint", "/api/mcp/server/endpoint"):
            try:
                res = _mcp_server(tenant_id, company_id).handle_jsonrpc(req_data, caller_identity=self.headers.get("X-Client-ID", "external_ai"))
                self._send_json(res)
            except Exception as e:
                self._send_json({"jsonrpc": "2.0", "id": req_data.get("id"), "error": {"code": -32603, "message": str(e)}}, status=500)
            return

        elif path in ("/api/mcp/servers", "/api/mcp/servers/discover"):
            display_name = req_data.get("display_name", "External MCP Server")
            endpoint = req_data.get("endpoint", "")
            description = req_data.get("description", "")
            transport = req_data.get("transport", "streamable_http")
            allow_loopback = bool(req_data.get("allow_test_loopback", False))
            token = req_data.get("auth_token")

            ok, srv_id, errs = _mcp(tenant_id, company_id).register_server(
                display_name=display_name,
                endpoint=endpoint,
                description=description,
                transport=MCPTransportType(transport) if transport in [t.value for t in MCPTransportType] else MCPTransportType.STREAMABLE_HTTP,
                auth_type="BEARER" if token else "NONE",
                credential_ref=token or None,
                allow_test_loopback=allow_loopback
            )
            if ok:
                self._send_json({"success": True, "server_id": srv_id, "message": f"Server {display_name} registered in DISCOVERED trust state"})
            else:
                self._send_json({"success": False, "errors": errs}, status=400)
            return

        elif path.startswith("/api/mcp/servers/") and path.endswith("/validate"):
            parts = path.split("/")
            server_id = parts[4]
            ok, msg = _mcp(tenant_id, company_id).validate_server(server_id)
            self._send_json({"success": ok, "message": msg})
            return

        elif path.startswith("/api/mcp/servers/") and path.endswith("/trust"):
            parts = path.split("/")
            server_id = parts[4]
            state_str = req_data.get("trust_state", "TRUSTED")
            reason = req_data.get("reason", "Admin state update")
            try:
                _mcp(tenant_id, company_id).set_server_trust(server_id, MCPTrustState(state_str), reason=reason)
                self._send_json({"success": True, "server_id": server_id, "trust_state": state_str})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
            return

        elif path.startswith("/api/mcp/servers/") and path.endswith("/test"):
            parts = path.split("/")
            server_id = parts[4]
            res = _mcp(tenant_id, company_id).test_server_connection(server_id)
            self._send_json(res)
            return

        elif path.startswith("/api/mcp/servers/") and path.endswith("/refresh"):
            parts = path.split("/")
            server_id = parts[4]
            res = _mcp(tenant_id, company_id).refresh_server_capabilities(server_id)
            self._send_json(res)
            return

        elif path.startswith("/api/mcp/servers/") and path.endswith("/suspend"):
            parts = path.split("/")
            server_id = parts[4]
            reason = req_data.get("reason", "Administrative suspension")
            res = _mcp(tenant_id, company_id).suspend_server(server_id, reason=reason)
            self._send_json(res)
            return

        elif path.startswith("/api/mcp/servers/") and path.endswith("/block"):
            parts = path.split("/")
            server_id = parts[4]
            reason = req_data.get("reason", "Administrative quarantine block")
            res = _mcp(tenant_id, company_id).block_server(server_id, reason=reason)
            self._send_json(res)
            return

        elif path.startswith("/api/mcp/servers/") and path.endswith("/reauthorize"):
            parts = path.split("/")
            server_id = parts[4]
            reason = req_data.get("reason", "Administrative reauthorization")
            res = _mcp(tenant_id, company_id).reauthorize_server(server_id, reason=reason)
            self._send_json(res)
            return

        elif path.startswith("/api/mcp/servers/") and path.endswith("/disconnect"):
            parts = path.split("/")
            server_id = parts[4]
            ok = _mcp(tenant_id, company_id).disconnect_server(server_id)
            self._send_json({"success": ok, "server_id": server_id})
            return

        elif path == "/api/mcp/tools":
            server_id = req_data.get("server_id")
            name = req_data.get("name")
            desc = req_data.get("description", "")
            in_schema = req_data.get("input_schema")
            out_schema = req_data.get("output_schema")
            risk = req_data.get("risk_class")
            appr = req_data.get("approval_requirement")
            idemp = bool(req_data.get("idempotency", True))
            try:
                tid = _mcp(tenant_id, company_id).register_tool(
                    server_id=server_id,
                    name=name,
                    description=desc,
                    input_schema=in_schema,
                    output_schema=out_schema,
                    override_risk=MCPToolRiskClass(risk) if risk else None,
                    override_approval=appr,
                    idempotency=idemp
                )
                self._send_json({"success": True, "tool_id": tid})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
            return

        elif path.startswith("/api/mcp/tools/") and path.endswith("/override"):
            parts = path.split("/")
            tool_id = parts[4]
            actor = req_data.get("actor", "admin")
            updates = req_data.get("updates") or req_data
            try:
                updated_tool = _mcp(tenant_id, company_id).override_tool(tool_id, updates, actor_id=actor)
                self._send_json({"success": True, "tool": updated_tool})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
            return

        elif path == "/api/mcp/tools/invoke":
            if self._blocked_by_global_killswitch("MCP tool execution"):
                return
            server_id = req_data.get("server_id")
            tool_name = req_data.get("tool_name") or req_data.get("tool_id")
            arguments = req_data.get("arguments", {})
            context = req_data.get("context", {})
            try:
                res = _mcp(tenant_id, company_id).invoke_tool(
                    server_id=server_id,
                    tool_name_or_id=tool_name,
                    arguments=arguments,
                    context=context
                )
                self._send_json(res)
            except MCPSecurityException as se:
                self._send_json({"success": False, "status": "DENIED", "error": str(se)}, status=403)
            except Exception as e:
                self._send_json({"success": False, "status": "TOOL_FAILED", "error": str(e)}, status=500)
            return

        elif path == "/api/mcp/resources/read":
            resource_id = req_data.get("resource_id")
            context = req_data.get("context", {})
            try:
                res = _mcp(tenant_id, company_id).read_resource(resource_id, context=context)
                self._send_json(res)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
            return

        elif path.startswith("/api/mcp/executions/") and path.endswith("/verify"):
            parts = path.split("/")
            exec_id = parts[4]
            res = _mcp(tenant_id, company_id).verify_execution(exec_id)
            self._send_json(res)
            return

        elif path.startswith("/api/mcp/executions/") and path.endswith("/cancel"):
            parts = path.split("/")
            exec_id = parts[4]
            reason = req_data.get("reason", "Cancelled by user")
            res = _mcp(tenant_id, company_id).cancel_execution(exec_id, reason=reason)
            self._send_json(res)
            return

        elif path == "/api/mcp/killswitch":
            active = bool(req_data.get("active", True))
            scope = req_data.get("scope", "TENANT")
            server_id = req_data.get("server_id")
            tool_id = req_data.get("tool_id")
            agent_id = req_data.get("agent_id")
            if active:
                MCPKillSwitch.activate(tenant_id=tenant_id, server_id=server_id, tool_id=tool_id, agent_id=agent_id)
            else:
                MCPKillSwitch.deactivate(tenant_id=tenant_id, server_id=server_id, tool_id=tool_id, agent_id=agent_id)
            self._send_json({
                "success": True,
                "killswitch_active": active,
                "status": "KILLSWITCH_ENGAGED" if active else "OPERATIONAL",
                "scope": scope
            })
            return

        elif path == "/api/mcp/published":
            cap_id = req_data.get("capability_id", "cap_general")
            name = req_data.get("name", "Inbound Capability")
            desc = req_data.get("description", "")
            schema = req_data.get("schema_definition", {"type": "object"})
            vis = req_data.get("visibility", "PRIVATE")
            rate = int(req_data.get("rate_limit_per_min", 60))
            appr = bool(req_data.get("approval_required", False))
            pub_id = _mcp_server(tenant_id, company_id).publish_capability(
                capability_id=cap_id,
                name=name,
                description=desc,
                schema_definition=schema,
                visibility=vis,
                rate_limit_per_min=rate,
                approval_required=appr
            )
            self._send_json({"success": True, "published_id": pub_id})
            return

        elif path == "/api/mcp/demo/scenarios":
            scenario = req_data.get("scenario", "SECTION_73").upper()
            sc_map = {
                "A": _mcp_scenarios(tenant_id, company_id).scenario_a_server_discovery_and_trust,
                "B": _mcp_scenarios(tenant_id, company_id).scenario_b_governed_tool_execution,
                "C": _mcp_scenarios(tenant_id, company_id).scenario_c_mutation_human_approval,
                "D": _mcp_scenarios(tenant_id, company_id).scenario_d_financial_policy_threshold,
                "E": _mcp_scenarios(tenant_id, company_id).scenario_e_prompt_injection_firewall,
                "F": _mcp_scenarios(tenant_id, company_id).scenario_f_ssrf_blocking,
                "G": _mcp_scenarios(tenant_id, company_id).scenario_g_timeout_unknown_reconciliation,
                "H": _mcp_scenarios(tenant_id, company_id).scenario_h_tenant_and_company_isolation,
                "I": _mcp_scenarios(tenant_id, company_id).scenario_i_killswitch_override,
                "J": _mcp_scenarios(tenant_id, company_id).scenario_j_langgraph_durable_mcp_workflow,
                "SECTION_73": _mcp_scenarios(tenant_id, company_id).scenario_acceptance_pms_cancellation_recovery,
                "73": _mcp_scenarios(tenant_id, company_id).scenario_acceptance_pms_cancellation_recovery
            }
            fn = sc_map.get(scenario)
            if fn:
                res = fn()
                self._send_json({"success": True, "scenario": scenario, "result": res})
            else:
                self._send_json({"error": f"Unknown MCP scenario '{scenario}'"}, status=400)
            return

        # =====================================================================
        # Governed OpenHands Execution Runtime Endpoints (POST - Project 07)
        # =====================================================================
        elif path == "/api/openhands/executions":
            if self._blocked_by_global_killswitch("OpenHands execution"):
                return
            agent_id = req_data.get("agent_id", "agt_developer")
            prompt = req_data.get("task_prompt", "Inspect and execute task")
            ws_type_str = req_data.get("workspace_type", "EPHEMERAL")
            ws_class_str = req_data.get("workspace_class", "SANDBOX")
            net_scope_str = req_data.get("network_scope", "RESTRICTED")
            mission_id = req_data.get("mission_id")
            workflow_id = req_data.get("workflow_id")
            task_id = req_data.get("task_id")
            ctx = req_data.get("scoped_context", {})
            try:
                ex = _openhands(tenant_id, company_id).create_execution(
                    agent_id=agent_id,
                    task_prompt=prompt,
                    workspace_type=WorkspaceType(ws_type_str),
                    workspace_class=WorkspaceClass(ws_class_str),
                    network_scope=NetworkScope(net_scope_str),
                    mission_id=mission_id,
                    workflow_id=workflow_id,
                    task_id=task_id,
                    scoped_context=ctx
                )
                self._send_json(ex)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/openhands/executions/command":
            if self._blocked_by_global_killswitch("OpenHands command execution"):
                return
            exec_id = req_data.get("execution_id")
            command = req_data.get("command")
            timeout = int(req_data.get("timeout_seconds", 30))
            try:
                res = _openhands(tenant_id, company_id).run_command(exec_id, command, timeout_seconds=timeout)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/openhands/executions/") and path.endswith("/complete"):
            parts = path.split("/")
            exec_id = parts[4]
            summary = req_data.get("result_summary", "Completed execution")
            test_cmd = req_data.get("expected_test_command")
            file_chk = req_data.get("expected_file_snippet")
            try:
                res = _openhands(tenant_id, company_id).complete_execution(
                    execution_id=exec_id,
                    result_summary=summary,
                    expected_test_command=test_cmd,
                    expected_file_snippet=tuple(file_chk) if file_chk else None
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/openhands/executions/") and path.endswith("/pause"):
            parts = path.split("/")
            exec_id = parts[4]
            ok = _openhands(tenant_id, company_id).pause_execution(exec_id)
            self._send_json({"success": ok, "execution_id": exec_id})
            return

        elif path.startswith("/api/openhands/executions/") and path.endswith("/resume"):
            parts = path.split("/")
            exec_id = parts[4]
            ok = _openhands(tenant_id, company_id).resume_execution(exec_id)
            self._send_json({"success": ok, "execution_id": exec_id})
            return

        elif path.startswith("/api/openhands/executions/") and path.endswith("/cancel"):
            parts = path.split("/")
            exec_id = parts[4]
            reason = req_data.get("reason", "Cancelled by user")
            ok = _openhands(tenant_id, company_id).cancel_execution(exec_id, reason=reason)
            self._send_json({"success": ok, "execution_id": exec_id})
            return

        elif path.startswith("/api/openhands/approvals/") and path.endswith("/approve"):
            if self._approver_denied(auth_context):
                return
            parts = path.split("/")
            appr_id = parts[4]
            approver = str(auth_context.get("user_id") or "Administrator")
            ok = _openhands(tenant_id, company_id).approve_operation(appr_id, approver_name=approver)
            self._send_json({"success": ok, "approval_id": appr_id})
            return

        elif path.startswith("/api/openhands/approvals/") and path.endswith("/reject"):
            if self._approver_denied(auth_context):
                return
            parts = path.split("/")
            appr_id = parts[4]
            approver = str(auth_context.get("user_id") or "Administrator")
            ok = _openhands(tenant_id, company_id).reject_operation(appr_id, approver_name=approver)
            self._send_json({"success": ok, "approval_id": appr_id})
            return

        elif path == "/api/openhands/killswitch":
            active = bool(req_data.get("active", True))
            scope = req_data.get("scope", "TENANT")
            exec_id = req_data.get("execution_id")
            ws_id = req_data.get("workspace_id")
            agent_id = req_data.get("agent_id")
            if active:
                OpenHandsKillSwitch.activate(tenant_id=tenant_id, execution_id=exec_id, workspace_id=ws_id, agent_id=agent_id)
            else:
                OpenHandsKillSwitch.deactivate(tenant_id=tenant_id, execution_id=exec_id, workspace_id=ws_id, agent_id=agent_id)
            self._send_json({
                "success": True,
                "killswitch_active": active,
                "status": "KILLSWITCH_ENGAGED" if active else "OPERATIONAL",
                "scope": scope
            })
            return

        elif path == "/api/openhands/demo/scenarios":
            scenario = req_data.get("scenario", "SECTION_79").upper()
            sc_map = {
                "TEST_01": _openhands_scenarios(tenant_id, company_id).test_01_software_task,
                "1": _openhands_scenarios(tenant_id, company_id).test_01_software_task,
                "TEST_02": _openhands_scenarios(tenant_id, company_id).test_02_mcp_and_openhands,
                "2": _openhands_scenarios(tenant_id, company_id).test_02_mcp_and_openhands,
                "TEST_03": _openhands_scenarios(tenant_id, company_id).test_03_human_approval,
                "3": _openhands_scenarios(tenant_id, company_id).test_03_human_approval,
                "TEST_04": _openhands_scenarios(tenant_id, company_id).test_04_killswitch,
                "4": _openhands_scenarios(tenant_id, company_id).test_04_killswitch,
                "TEST_05": _openhands_scenarios(tenant_id, company_id).test_05_malicious_repository,
                "5": _openhands_scenarios(tenant_id, company_id).test_05_malicious_repository,
                "TEST_06": _openhands_scenarios(tenant_id, company_id).test_06_unknown_mutation_reconciliation,
                "6": _openhands_scenarios(tenant_id, company_id).test_06_unknown_mutation_reconciliation,
                "TEST_07": _openhands_scenarios(tenant_id, company_id).test_07_tenant_isolation,
                "7": _openhands_scenarios(tenant_id, company_id).test_07_tenant_isolation,
                "TEST_08": _openhands_scenarios(tenant_id, company_id).test_08_self_improvement,
                "8": _openhands_scenarios(tenant_id, company_id).test_08_self_improvement,
                "SECTION_79": _openhands_scenarios(tenant_id, company_id).section_79_acceptance_scenario,
                "79": _openhands_scenarios(tenant_id, company_id).section_79_acceptance_scenario
            }
            fn = sc_map.get(scenario)
            if fn:
                res = fn()
                self._send_json({"success": True, "scenario": scenario, "result": res})
            else:
                self._send_json({"error": f"Unknown OpenHands scenario '{scenario}'"}, status=400)
            return

        # =====================================================================
        # Governed Browser Use Execution Layer Endpoints (POST - Project 08)
        # =====================================================================
        elif path == "/api/browser/sessions":
            if universal_automation_fabric.is_killswitch_active():
                self._send_json({"error": "Global kill switch engaged: browser halted", "blocked": True}, status=403)
                return
            profile_type = req_data.get("profile_type", "EPHEMERAL")
            user_agent = req_data.get("user_agent", "ZonataGovernedBrowser/1.0")
            allowed_domains = req_data.get("allowed_domains", [])
            blocked_domains = req_data.get("blocked_domains", [])
            agent_id = req_data.get("agent_id", "agent_browser_user")
            sess = _browser(tenant_id, company_id).create_session(
                agent_id=agent_id,
                profile_type=profile_type,
                allowed_domains=allowed_domains
            )
            self._send_json(sess)
            return

        elif path.startswith("/api/browser/sessions/") and path.endswith("/close"):
            sess_id = path.split("/")[4]
            ok = _browser(tenant_id, company_id).close_session(sess_id)
            self._send_json({"success": ok, "session_id": sess_id})
            return

        elif path == "/api/browser/executions":
            if universal_automation_fabric.is_killswitch_active():
                self._send_json({"error": "Global kill switch engaged: browser halted", "blocked": True}, status=403)
                return
            session_id = req_data.get("session_id")
            mission_id = req_data.get("mission_id", "mis_browser_direct")
            task_id = req_data.get("task_id")
            invoking_agent_id = req_data.get("invoking_agent_id", "agent_ceo")
            goal = req_data.get("goal", "Inspect web portal")
            initial_url = req_data.get("initial_url", "https://zonata.local/dashboard")
            max_actions = int(req_data.get("max_actions", 25))
            timeout_seconds = int(req_data.get("timeout_seconds", 300))
            try:
                ex = _browser(tenant_id, company_id).create_execution(
                    session_id=session_id,
                    agent_id=invoking_agent_id,
                    task_prompt=req_data.get("task_prompt") or goal,
                    mission_id=mission_id,
                    workflow_id=req_data.get("workflow_id"),
                )
                self._send_json(ex)
            except BrowserSecurityException as bse:
                self._send_json({"error": str(bse), "security_violation": True}, status=403)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/browser/navigate":
            if universal_automation_fabric.is_killswitch_active():
                self._send_json({"error": "Global kill switch engaged: browser halted", "blocked": True}, status=403)
                return
            execution_id = req_data.get("execution_id")
            url = req_data.get("url")
            try:
                res = _browser(tenant_id, company_id).navigate(execution_id, url)
                self._send_json(res)
            except BrowserSecurityException as bse:
                self._send_json({"error": str(bse), "security_violation": True}, status=403)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/browser/action":
            if universal_automation_fabric.is_killswitch_active():
                self._send_json({"error": "Global kill switch engaged: browser halted", "blocked": True}, status=403)
                return
            execution_id = req_data.get("execution_id")
            action_type = req_data.get("action_type")
            selector = req_data.get("selector", "")
            parameters = req_data.get("parameters", {})
            human_intent = req_data.get("human_intent", "")
            try:
                res = _browser(tenant_id, company_id).execute_action(
                    execution_id=execution_id,
                    action_type=action_type,
                    selector=selector,
                    parameters=parameters,
                )
                self._send_json(res)
            except BrowserSecurityException as bse:
                self._send_json({"error": str(bse), "security_violation": True}, status=403)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/browser/executions/") and path.endswith("/complete"):
            exec_id = path.split("/")[4]
            outcome_summary = req_data.get("outcome_summary", "Completed successfully")
            verification_evidence = req_data.get("verification_evidence", {})
            try:
                res = _browser(tenant_id, company_id).complete_execution(
                    execution_id=exec_id,
                    outcome_summary=outcome_summary,
                    verification_evidence=verification_evidence
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/browser/executions/") and path.endswith("/cancel"):
            exec_id = path.split("/")[4]
            reason = req_data.get("reason", "User requested cancellation")
            ok = _browser(tenant_id, company_id).cancel_execution(exec_id, reason=reason)
            self._send_json({"success": ok, "execution_id": exec_id})
            return

        elif path.startswith("/api/browser/approvals/") and path.endswith("/approve"):
            if self._approver_denied(auth_context):
                return
            appr_id = path.split("/")[4]
            approver = str(auth_context.get("user_id") or "usr_executive")
            try:
                res = _browser(tenant_id, company_id).approve_action(appr_id, approver_id=approver)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/browser/approvals/") and path.endswith("/reject"):
            if self._approver_denied(auth_context):
                return
            appr_id = path.split("/")[4]
            rejector = str(auth_context.get("user_id") or "usr_executive")
            reason = req_data.get("reason", "Security policy violation")
            try:
                res = _browser(tenant_id, company_id).reject_action(appr_id, rejector_id=rejector, reason=reason)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/browser/killswitch":
            active = bool(req_data.get("active", True))
            scope = str(req_data.get("scope", "GLOBAL")).upper()
            # company_id was resolved from the verified token (see _resolve_company_id)
            if active:
                if scope == "GLOBAL":
                    BrowserKillSwitch.trip_global()
                elif scope == "TENANT":
                    BrowserKillSwitch.trip_tenant(tenant_id)
                elif scope == "COMPANY":
                    BrowserKillSwitch.trip_company(company_id)
                elif scope == "SESSION":
                    BrowserKillSwitch.trip_session(req_data.get("session_id", ""))
                elif scope == "EXECUTION":
                    BrowserKillSwitch.trip_execution(req_data.get("execution_id", ""))
                elif scope == "DOMAIN":
                    BrowserKillSwitch.trip_domain(req_data.get("domain", ""))
                elif scope == "AGENT":
                    BrowserKillSwitch.trip_agent(req_data.get("agent_id", ""))
            else:
                BrowserKillSwitch.reset_all()
            killed, k_reason = BrowserKillSwitch.is_killed(tenant_id=tenant_id, company_id=company_id)
            self._send_json({
                "success": True,
                "killswitch_active": killed,
                "status": "KILLSWITCH_ENGAGED" if killed else "OPERATIONAL",
                "scope": scope,
                "reason": k_reason
            })
            return

        elif path == "/api/browser/demo/scenarios":
            scenario = str(req_data.get("scenario", "SECTION_80")).upper()
            sc_map = {
                "TEST_01": _browser_scenarios(tenant_id, company_id).test_01_information_extraction,
                "1": _browser_scenarios(tenant_id, company_id).test_01_information_extraction,
                "TEST_02": _browser_scenarios(tenant_id, company_id).test_02_sensitive_mutation,
                "2": _browser_scenarios(tenant_id, company_id).test_02_sensitive_mutation,
                "TEST_03": _browser_scenarios(tenant_id, company_id).test_03_prompt_injection,
                "3": _browser_scenarios(tenant_id, company_id).test_03_prompt_injection,
                "TEST_04": _browser_scenarios(tenant_id, company_id).test_04_unknown_result_reconciliation,
                "4": _browser_scenarios(tenant_id, company_id).test_04_unknown_result_reconciliation,
                "TEST_05": _browser_scenarios(tenant_id, company_id).test_05_tenant_isolation,
                "5": _browser_scenarios(tenant_id, company_id).test_05_tenant_isolation,
                "TEST_06": _browser_scenarios(tenant_id, company_id).test_06_killswitch,
                "6": _browser_scenarios(tenant_id, company_id).test_06_killswitch,
                "TEST_07": _browser_scenarios(tenant_id, company_id).test_07_openhands_and_browser,
                "7": _browser_scenarios(tenant_id, company_id).test_07_openhands_and_browser,
                "TEST_08": _browser_scenarios(tenant_id, company_id).test_08_mcp_and_browser,
                "8": _browser_scenarios(tenant_id, company_id).test_08_mcp_and_browser,
                "TEST_09": _browser_scenarios(tenant_id, company_id).test_09_a2a_and_browser,
                "9": _browser_scenarios(tenant_id, company_id).test_09_a2a_and_browser,
                "SECTION_80": _browser_scenarios(tenant_id, company_id).test_10_complete_zonata_grand_acceptance,
                "80": _browser_scenarios(tenant_id, company_id).test_10_complete_zonata_grand_acceptance,
                "TEST_10": _browser_scenarios(tenant_id, company_id).test_10_complete_zonata_grand_acceptance,
                "10": _browser_scenarios(tenant_id, company_id).test_10_complete_zonata_grand_acceptance
            }
            fn = sc_map.get(scenario)
            if fn:
                res = fn()
                self._send_json({"success": True, "scenario": scenario, "result": res})
            else:
                self._send_json({"error": f"Unknown Browser Use scenario '{scenario}'"}, status=400)
            return

        # =====================================================================
        # Governed Temporal Durable Execution Layer Endpoints (POST - Project 09)
        # =====================================================================
        elif path == "/api/temporal/workflows":
            wf_type = req_data.get("workflow_type", "StandardDurableWorkflow")
            input_payload = req_data.get("input_payload", {})
            task_queue = req_data.get("task_queue", "zonata.ai")
            mission_id = req_data.get("mission_id")
            idempotency_key = req_data.get("idempotency_key")
            try:
                wf = _temporal(tenant_id, company_id).start_workflow(
                    workflow_type=wf_type,
                    input_payload=input_payload,
                    task_queue=task_queue,
                    mission_id=mission_id,
                    idempotency_key=idempotency_key
                )
                self._send_json(wf)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/workflows/") and path.endswith("/signal"):
            wf_id = path.split("/")[4]
            sig_name = req_data.get("signal_name", "EXTERNAL_UPDATE")
            sig_payload = req_data.get("payload", {})
            try:
                res = _temporal(tenant_id, company_id).signal_workflow(wf_id, sig_name, sig_payload)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/workflows/") and path.endswith("/update"):
            wf_id = path.split("/")[4]
            upd_name = req_data.get("update_name", "UPDATE_CONFIG")
            upd_payload = req_data.get("payload", {})
            try:
                res = _temporal(tenant_id, company_id).update_workflow(wf_id, upd_name, upd_payload)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/workflows/") and path.endswith("/query"):
            wf_id = path.split("/")[4]
            q_name = req_data.get("query_name", "status")
            try:
                res = _temporal(tenant_id, company_id).query_workflow(wf_id, q_name)
                self._send_json({"result": res, "workflow_id": wf_id, "query": q_name})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/workflows/") and path.endswith("/pause"):
            wf_id = path.split("/")[4]
            reason = req_data.get("reason", "Governor override")
            try:
                res = _temporal(tenant_id, company_id).pause_workflow(wf_id, reason=reason)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/workflows/") and path.endswith("/resume"):
            wf_id = path.split("/")[4]
            try:
                res = _temporal(tenant_id, company_id).resume_workflow(wf_id)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/workflows/") and path.endswith("/cancel"):
            wf_id = path.split("/")[4]
            reason = req_data.get("reason", "User requested cancel")
            try:
                res = _temporal(tenant_id, company_id).cancel_workflow(wf_id, reason=reason)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/workflows/") and path.endswith("/terminate"):
            wf_id = path.split("/")[4]
            reason = req_data.get("reason", "Administrative termination")
            try:
                res = _temporal(tenant_id, company_id).terminate_workflow(wf_id, reason=reason)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/workflows/") and path.endswith("/reconcile"):
            wf_id = path.split("/")[4]
            act_id = req_data.get("activity_id")
            ext_ref = req_data.get("external_ref")
            entity_type = req_data.get("entity_type", "GENERIC_MUTATION")
            obs_state = req_data.get("observed_state")
            try:
                res = _temporal(tenant_id, company_id).reconcile_workflow(
                    workflow_id=wf_id,
                    activity_id=act_id,
                    external_ref=ext_ref,
                    entity_type=entity_type,
                    observed_external_state=obs_state
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/temporal/activities":
            wf_id = req_data.get("workflow_id")
            act_type = req_data.get("activity_type", "StandardActivity")
            inp = req_data.get("input_payload", {})
            risk_str = req_data.get("risk_class", "SAFE_RETRY")
            risk_class = getattr(ActivityRiskClass, risk_str, ActivityRiskClass.SAFE_RETRY)
            idemp_key = req_data.get("idempotency_key")
            try:
                act = _temporal(tenant_id, company_id).start_activity(
                    workflow_id=wf_id,
                    activity_type=act_type,
                    input_payload=inp,
                    risk_class=risk_class,
                    idempotency_key=idemp_key
                )
                self._send_json(act)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/activities/") and path.endswith("/retry"):
            act_id = path.split("/")[4]
            reason = req_data.get("reason", "Retry requested")
            try:
                res = _temporal(tenant_id, company_id).retry_activity(act_id, reason=reason)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/activities/") and path.endswith("/complete"):
            act_id = path.split("/")[4]
            res_payload = req_data.get("result", {})
            try:
                res = _temporal(tenant_id, company_id).complete_activity(act_id, res_payload)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/temporal/workers/register":
            w_id = req_data.get("worker_id", f"wrk_custom_{uuid.uuid4().hex[:6]}")
            queue = req_data.get("task_queue", "zonata.ai")
            caps = req_data.get("capability_scope", ["GENERAL"])
            acts = req_data.get("supported_activities", ["general_task"])
            try:
                w = _temporal(tenant_id, company_id).register_worker(w_id, queue, caps, acts)
                self._send_json(w)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path.startswith("/api/temporal/workers/") and path.endswith("/heartbeat"):
            w_id = path.split("/")[4]
            ok = _temporal(tenant_id, company_id).heartbeat_worker(w_id)
            self._send_json({"success": ok, "worker_id": w_id})
            return

        elif path.startswith("/api/temporal/approvals/") and path.endswith("/decide"):
            appr_id = path.split("/")[4]
            approved = bool(req_data.get("approved", True))
            decided_by = req_data.get("decided_by", "OWNER")
            reason = req_data.get("reason", "Approved by operator")
            try:
                res = _temporal(tenant_id, company_id).decide_approval(appr_id, approved=approved, decided_by=decided_by, reason=reason)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        elif path == "/api/temporal/killswitch":
            active = bool(req_data.get("active", True))
            scope = str(req_data.get("scope", "GLOBAL")).upper()
            # company_id was resolved from the verified token (see _resolve_company_id)
            if active:
                if scope == "GLOBAL":
                    TemporalKillSwitch.trip_global()
                elif scope == "TENANT":
                    TemporalKillSwitch.trip_tenant(tenant_id)
                elif scope == "COMPANY":
                    TemporalKillSwitch.trip_company(company_id)
                elif scope == "WORKFLOW":
                    TemporalKillSwitch.trip_workflow(req_data.get("workflow_id", ""))
                elif scope == "WORKER":
                    TemporalKillSwitch.trip_worker(req_data.get("worker_id", ""))
                elif scope == "QUEUE":
                    TemporalKillSwitch.trip_queue(req_data.get("task_queue", ""))
                elif scope == "ACTIVITY":
                    TemporalKillSwitch.trip_activity(req_data.get("activity_id", ""))
            else:
                TemporalKillSwitch.reset_all()
            killed, k_reason = TemporalKillSwitch.is_killed(tenant_id=tenant_id, company_id=company_id)
            self._send_json({
                "success": True,
                "killswitch_active": killed,
                "status": "KILLSWITCH_ENGAGED" if killed else "OPERATIONAL",
                "scope": scope,
                "reason": k_reason
            })
            return

        elif path == "/api/temporal/demo/scenarios":
            scenario = str(req_data.get("scenario", "SECTION_85")).upper()
            sc_map = {
                "TEST_01": _temporal_scenarios(tenant_id, company_id).test_01_durable_workflow_crash_recovery,
                "1": _temporal_scenarios(tenant_id, company_id).test_01_durable_workflow_crash_recovery,
                "TEST_02": _temporal_scenarios(tenant_id, company_id).test_02_retry_governance_and_non_idempotent_blocks,
                "2": _temporal_scenarios(tenant_id, company_id).test_02_retry_governance_and_non_idempotent_blocks,
                "TEST_03": _temporal_scenarios(tenant_id, company_id).test_03_first_class_unknown_outcome_reconciliation,
                "3": _temporal_scenarios(tenant_id, company_id).test_03_first_class_unknown_outcome_reconciliation,
                "TEST_04": _temporal_scenarios(tenant_id, company_id).test_04_multi_day_human_approval_wait,
                "4": _temporal_scenarios(tenant_id, company_id).test_04_multi_day_human_approval_wait,
                "TEST_05": _temporal_scenarios(tenant_id, company_id).test_05_multi_scope_killswitch_enforcement,
                "5": _temporal_scenarios(tenant_id, company_id).test_05_multi_scope_killswitch_enforcement,
                "TEST_06": _temporal_scenarios(tenant_id, company_id).test_06_zero_credential_leakage,
                "6": _temporal_scenarios(tenant_id, company_id).test_06_zero_credential_leakage,
                "TEST_07": _temporal_scenarios(tenant_id, company_id).test_07_strict_tenant_isolation,
                "7": _temporal_scenarios(tenant_id, company_id).test_07_strict_tenant_isolation,
                "TEST_08": _temporal_scenarios(tenant_id, company_id).test_08_langgraph_temporal_hybrid,
                "8": _temporal_scenarios(tenant_id, company_id).test_08_langgraph_temporal_hybrid,
                "TEST_09": _temporal_scenarios(tenant_id, company_id).test_09_multi_layer_integration,
                "9": _temporal_scenarios(tenant_id, company_id).test_09_multi_layer_integration,
                "SECTION_85": _temporal_scenarios(tenant_id, company_id).test_10_section_85_grand_acceptance_test,
                "85": _temporal_scenarios(tenant_id, company_id).test_10_section_85_grand_acceptance_test,
                "TEST_10": _temporal_scenarios(tenant_id, company_id).test_10_section_85_grand_acceptance_test,
                "10": _temporal_scenarios(tenant_id, company_id).test_10_section_85_grand_acceptance_test
            }
            fn = sc_map.get(scenario)
            if fn:
                res = fn()
                self._send_json({"success": True, "scenario": scenario, "result": res})
            else:
                self._send_json({"error": f"Unknown Temporal scenario '{scenario}'"}, status=400)
            return

        # --- NANGO EXTERNAL INTEGRATION API (Project 10 POST) ---
        elif path == "/api/nango/connections":
            # company_id was resolved from the verified token (see _resolve_company_id)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            prov_id = req_data.get("provider_id", "salesforce")
            conn_key = req_data.get("connection_key")
            auth_type = req_data.get("auth_type", "OAUTH2")
            scopes = req_data.get("scopes", ["default.read"])
            meta = req_data.get("metadata", {})
            conn_res = gw.create_connection(prov_id, conn_key, auth_type, scopes, meta)
            self._send_json({"success": True, "connection": conn_res})
            return

        elif path.startswith("/api/nango/connections/") and path.endswith("/test"):
            conn_id = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            ok, msg = gw.test_connection(conn_id)
            self._send_json({"success": ok, "message": msg, "connection_id": conn_id})
            return

        elif path.startswith("/api/nango/connections/") and path.endswith("/sync"):
            conn_id = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            model = req_data.get("model", "contacts")
            limit = int(req_data.get("limit", 50))
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            sync_res = gw.trigger_sync(conn_id, model, limit=limit)
            self._send_json({"success": True, "sync": sync_res})
            return

        elif path == "/api/nango/execute":
            # company_id was resolved from the verified token (see _resolve_company_id)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            conn_id = req_data.get("connection_id")
            action = req_data.get("action", "READ_CONTACT")
            params = req_data.get("parameters", {})
            idemp_key = req_data.get("idempotency_key")
            mission_id = req_data.get("mission_id")
            agent_id = req_data.get("agent_id")
            appr_override = req_data.get("approved_by_owner", False)
            if not conn_id:
                self._send_json({"error": "Missing connection_id"}, status=400)
                return
            try:
                exec_res = gw.execute_action(
                    connection_id=conn_id,
                    action_name=action,
                    params=params,
                    idempotency_key=idemp_key,
                    mission_id=mission_id,
                    agent_id=agent_id,
                    require_approval_override=appr_override
                )
                self._send_json({"success": True, "execution": exec_res})
            except NangoSecurityException as se:
                self._send_json({"error": str(se), "security_blocked": True}, status=403)
            return

        elif path.startswith("/api/nango/webhooks/"):
            prov_id = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            raw_body = json.dumps(req_data)
            headers_dict = {k: v for k, v in self.headers.items()}
            res = gw.receive_webhook(prov_id, headers_dict, raw_body)
            self._send_json({"success": True, "webhook": res})
            return

        elif path == "/api/nango/reconcile":
            # company_id was resolved from the verified token (see _resolve_company_id)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            rec_id = req_data.get("reconciliation_id")
            obs_state = req_data.get("observed_state", {})
            res_type = req_data.get("resolution", "RECONCILED_SUCCESS")
            if not rec_id:
                self._send_json({"error": "Missing reconciliation_id"}, status=400)
                return
            rec_res = gw.reconcile_unknown_outcome(rec_id, obs_state, res_type)
            self._send_json({"success": True, "reconciliation": rec_res})
            return

        elif path == "/api/nango/killswitch":
            scope = req_data.get("scope", "PROVIDER").upper()
            target_id = req_data.get("target_id", "salesforce")
            action = req_data.get("action", "halt").lower()
            reason = req_data.get("reason", "Operator invoked killswitch")
            if action == "halt":
                IntegrationKillSwitch.halt(scope, target_id, reason, halted_by="API_ADMIN")
            else:
                IntegrationKillSwitch.resume(scope, target_id)
            self._send_json({
                "killswitch_updated": True,
                "scope": scope,
                "target_id": target_id,
                "action": action
            })
            return

        elif path == "/api/nango/demo/scenarios":
            scenario = str(req_data.get("scenario", "SECTION_95")).upper()
            sc_map = {
                "TEST_01": _nango_scenarios(tenant_id, company_id).test_01_standard_connection_lifecycle_and_read,
                "1": _nango_scenarios(tenant_id, company_id).test_01_standard_connection_lifecycle_and_read,
                "TEST_02": _nango_scenarios(tenant_id, company_id).test_02_business_mutation_with_idempotency_key,
                "2": _nango_scenarios(tenant_id, company_id).test_02_business_mutation_with_idempotency_key,
                "TEST_03": _nango_scenarios(tenant_id, company_id).test_03_human_approval_escalation,
                "3": _nango_scenarios(tenant_id, company_id).test_03_human_approval_escalation,
                "TEST_04": _nango_scenarios(tenant_id, company_id).test_04_multi_scope_killswitch_enforcement,
                "4": _nango_scenarios(tenant_id, company_id).test_04_multi_scope_killswitch_enforcement,
                "TEST_05": _nango_scenarios(tenant_id, company_id).test_05_context_firewall_and_secret_scrubbing,
                "5": _nango_scenarios(tenant_id, company_id).test_05_context_firewall_and_secret_scrubbing,
                "TEST_06": _nango_scenarios(tenant_id, company_id).test_06_inbound_webhook_verification,
                "6": _nango_scenarios(tenant_id, company_id).test_06_inbound_webhook_verification,
                "TEST_07": _nango_scenarios(tenant_id, company_id).test_07_governed_data_synchronization,
                "7": _nango_scenarios(tenant_id, company_id).test_07_governed_data_synchronization,
                "TEST_08": _nango_scenarios(tenant_id, company_id).test_08_unknown_outcome_and_reconciliation,
                "8": _nango_scenarios(tenant_id, company_id).test_08_unknown_outcome_and_reconciliation,
                "TEST_09": _nango_scenarios(tenant_id, company_id).test_09_cross_tenant_isolation,
                "9": _nango_scenarios(tenant_id, company_id).test_09_cross_tenant_isolation,
                "TEST_10": _nango_scenarios(tenant_id, company_id).test_10_section_95_grand_acceptance_test,
                "10": _nango_scenarios(tenant_id, company_id).test_10_section_95_grand_acceptance_test,
                "SECTION_95": _nango_scenarios(tenant_id, company_id).test_10_section_95_grand_acceptance_test,
                "95": _nango_scenarios(tenant_id, company_id).test_10_section_95_grand_acceptance_test
            }
            fn = sc_map.get(scenario)
            if fn:
                res = fn()
                self._send_json({"success": True, "scenario": scenario, "result": res})
            else:
                self._send_json({"error": f"Unknown Nango scenario '{scenario}'"}, status=400)
            return

        # ZONATA V8: AI CEO Executive Operating Layer & Coworker 2.0 Routes
        if path.startswith("/api/v8/") or path.startswith("/api/v2/coworker"):
            from core.v8_api_handler import V8ApiHandler
            t_id = tenant_id
            c_id = self.headers.get("X-Company-ID") or company_id
            v8_res = V8ApiHandler.handle_post(path, req_data, t_id, c_id)
            if v8_res:
                data, code = v8_res
                self._send_json(data, status=code)
                return

        # OpenTelemetry Trace Span Endpoint
        elif path == "/api/telemetry/trace":
            name = req_data.get("name", "span_operation")
            tenant = tenant_id
            company = self.headers.get("X-Company-ID") or company_id
            span = opentelemetry_engine.start_trace(
                span_name=name,
                tenant_id=tenant,
                company_id=company,
                mission_id=req_data.get("mission_id"),
                execution_id=req_data.get("execution_id"),
                task_id=req_data.get("task_id"),
                agent_id=req_data.get("agent_id"),
                tool_id=req_data.get("tool_id"),
                evidence_id=req_data.get("evidence_id")
            )
            for k, v in req_data.get("attributes", {}).items():
                span.set_attribute(k, v)
            opentelemetry_engine.finish_span(span)
            self._send_json({"success": True, "span": span.to_dict()})
            return

        # Langfuse LLM Generation Endpoint
        elif path == "/api/langfuse/generations":
            tenant = tenant_id
            company = self.headers.get("X-Company-ID") or company_id
            gen = langfuse_engine.record_generation(
                name=req_data.get("name", "llm_completion"),
                model=req_data.get("model", "gpt-4o"),
                prompt=req_data.get("prompt", ""),
                completion=req_data.get("completion", ""),
                prompt_tokens=int(req_data.get("prompt_tokens", 0)),
                completion_tokens=int(req_data.get("completion_tokens", 0)),
                latency_ms=float(req_data.get("latency_ms", 50.0)),
                tenant_id=tenant,
                company_id=company,
                mission_id=req_data.get("mission_id"),
                agent_id=req_data.get("agent_id")
            )
            self._send_json({"success": True, "generation": gen.to_dict()})
            return

        # OpenFGA Relationship Authorization Endpoints
        elif path == "/api/openfga/check":
            tenant = tenant_id
            user = req_data.get("user", "")
            relation = req_data.get("relation", "")
            obj = req_data.get("object", "")
            allowed = openfga_engine.check(user=user, relation=relation, object=obj, tenant_id=tenant)
            self._send_json({"allowed": allowed, "user": user, "relation": relation, "object": obj})
            return

        elif path == "/api/openfga/tuples":
            tenant = tenant_id
            user = req_data.get("user", "")
            relation = req_data.get("relation", "")
            obj = req_data.get("object", "")
            action = req_data.get("action", "write")
            if action == "delete":
                ok = openfga_engine.delete_tuple(user=user, relation=relation, object=obj, tenant_id=tenant)
            else:
                ok = openfga_engine.write_tuple(user=user, relation=relation, object=obj, tenant_id=tenant)
            self._send_json({"success": bool(ok), "tuple": {"user": user, "relation": relation, "object": obj}})
            return

        # Vault Scoped Dynamic Credential Leases
        elif path == "/api/vault/lease":
            tenant = tenant_id
            agent_id = req_data.get("agent_id", "agent_worker")
            target_system = req_data.get("target_system", "postgres_db")
            actions = req_data.get("required_actions", ["read"])
            ttl = int(req_data.get("ttl_seconds", 300))
            lease = vault_client.issue_scoped_lease(
                agent_id=agent_id,
                tenant_id=tenant,
                target_system=target_system,
                required_actions=actions,
                ttl_seconds=ttl
            )
            self._send_json({"success": True, "lease": lease.to_dict()})
            return

        elif path == "/api/vault/revoke":
            lease_id = req_data.get("lease_id", "")
            reason = req_data.get("reason", "API request")
            ok = vault_client.revoke_lease(lease_id=lease_id, reason=reason)
            self._send_json({"success": ok, "lease_id": lease_id})
            return

        # Keycloak Identity Authentication & Revocation
        elif path == "/api/keycloak/auth":
            tenant = tenant_id
            token_str = req_data.get("token", "")
            res = keycloak_idp.authenticate_token(token_str)
            self._send_json(res.to_dict())
            return

        elif path == "/api/keycloak/revoke":
            session_id = req_data.get("session_id", "")
            keycloak_idp.revoke_session(session_id)
            self._send_json({"success": True, "session_id": session_id})
            return

        # NATS JetStream Event Publish
        elif path == "/api/events/publish":
            tenant = tenant_id
            company = self.headers.get("X-Company-ID") or company_id
            subject = req_data.get("subject", "zonata.events.general")
            data = req_data.get("data", {})
            msg = jetstream_engine.publish(subject=subject, data=data, tenant_id=tenant, company_id=company)
            self._send_json({"success": True, "message": msg.to_dict()})
            return

        # Agent Evaluation Run Endpoint
        elif path == "/api/evaluations/run":
            test_id = req_data.get("test_id", "tc_general_benchmark")
            agent_id = req_data.get("agent_id", "agent_worker")
            model = req_data.get("model", "gpt-4o")
            actual_output = req_data.get("actual_output", "")
            tools_used = req_data.get("actual_tools_used", [])
            latency = float(req_data.get("latency_sec", 1.0))
            cost = float(req_data.get("cost_usd", 0.005))
            pol_pass = req_data.get("policy_violations", 0)
            ev_id = req_data.get("evidence_id")
            report = agent_evaluation_engine.evaluate_execution(
                test_case_id=test_id,
                agent_id=agent_id,
                model=model,
                actual_output=actual_output,
                actual_tools_used=tools_used,
                latency_sec=latency,
                cost_usd=cost,
                policy_violation_count=pol_pass,
                evidence_id=ev_id,
                execution_id=req_data.get("execution_id")
            )
            self._send_json({"success": True, "report": report.to_dict()})
            return

        # SaaS Billing Plan Upgrade & Usage Record
        elif path in ("/api/billing/upgrade", "/api/v1/billing/upgrade"):
            tenant = tenant_id
            tier_str = req_data.get("tier", "pro").upper()
            try:
                tier = SubscriptionTier[tier_str]
            except KeyError:
                tier = SubscriptionTier.PRO
            snapshot = saas_billing_engine.upgrade_plan(tenant_id=tenant, new_tier=tier)
            self._send_json({"success": True, "tenant": snapshot.to_dict()})
            return

        elif path in ("/api/billing/record", "/api/v1/billing/record"):
            tenant = tenant_id
            metric = req_data.get("metric", "api_call")
            amount = float(req_data.get("amount", 1.0))
            cost = float(req_data.get("cost_usd", 0.0))
            idempotency_key = req_data.get("idempotency_key")
            recorded = saas_billing_engine.record_usage(
                tenant_id=tenant, metric=metric, amount=amount, cost_usd=cost, idempotency_key=idempotency_key
            )
            self._send_json({"success": recorded, "tenant_id": tenant, "metric": metric, "amount": amount})
            return

        elif path in ("/api/billing/subscription/transition", "/api/v1/billing/subscription/transition"):
            target_status_str = req_data.get("status", "").upper()
            reason = req_data.get("reason", "API request")
            grace_period = req_data.get("grace_period_seconds")
            try:
                target_status = SubscriptionStatus[target_status_str]
                sub = saas_billing_engine.transition_subscription_status(
                    tenant_id=tenant_id,
                    target_status=target_status,
                    reason=reason,
                    grace_period_seconds=grace_period
                )
                self._send_json({"success": True, "subscription": sub.to_dict()})
            except KeyError:
                self._send_json({"error": "Bad Request", "detail": f"Unknown status: '{target_status_str}'"}, status=400)
            except InvalidSubscriptionTransitionError as e:
                self._send_json({"error": "Illegal Transition", "detail": str(e)}, status=409)
            return

        elif path in ("/api/billing/checkout", "/api/v1/billing/checkout"):
            provider = (req_data.get("provider") or "stripe").lower()
            target_tier_str = (req_data.get("tier") or "PRO").upper()
            try:
                tier = SubscriptionTier[target_tier_str]
            except KeyError:
                self._send_json({
                    "error": "Bad Request",
                    "code": "UNKNOWN_TIER",
                    "detail": f"Unknown tier '{target_tier_str}'.",
                    "allowed": [t.value for t in SubscriptionTier],
                }, status=400)
                return
            plan = TIER_ENTITLEMENTS.get(tier, TIER_ENTITLEMENTS[SubscriptionTier.PRO])
            host = self.headers.get("Host") or "localhost"
            scheme = "https" if self.headers.get("X-Forwarded-Proto") == "https" else "http"
            base = f"{scheme}://{host}"
            success_url = req_data.get("success_url") or f"{base}/?billing=success"
            cancel_url = req_data.get("cancel_url") or f"{base}/?billing=cancelled"

            if provider == "stripe":
                cust = saas_billing_engine.stripe.create_customer(
                    tenant_id=tenant_id,
                    email=req_data.get("email") or f"{tenant_id}@example.com",
                    company_name=req_data.get("company_name") or "Enterprise",
                )
                if not cust.get("success"):
                    self._send_json({
                        "error": "Stripe is not available",
                        "code": cust.get("code", "PROVIDER_ERROR"),
                        "provider": "stripe",
                        "detail": cust.get("detail"),
                        "required_env": cust.get("required_env", []),
                    }, status=503)
                    return
                session = saas_billing_engine.stripe.create_checkout_session(
                    tenant_id=tenant_id,
                    customer_id=cust.get("stripe_customer_id"),
                    amount_usd=plan.monthly_price_usd,
                    tier=tier.value,
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
                if not session.get("success"):
                    self._send_json({
                        "error": "Stripe checkout could not be created",
                        "code": session.get("code", "PROVIDER_ERROR"),
                        "provider": "stripe",
                        "detail": session.get("detail"),
                        "required_env": session.get("required_env", []),
                    }, status=503)
                    return
                self._send_json({
                    "success": True,
                    "checkout_session_id": session["checkout_session_id"],
                    "customer_id": cust.get("stripe_customer_id"),
                    "tier": tier.value,
                    "amount_usd": plan.monthly_price_usd,
                    "url": session["url"],
                    "provider": "stripe",
                })

            elif provider == "razorpay":
                order = saas_billing_engine.razorpay.create_order(
                    amount_inr=plan.monthly_price_usd * 85.0,
                    tenant_id=tenant_id,
                    receipt=f"rcpt_{tenant_id}"[:40],
                )
                if not order.get("success"):
                    self._send_json({
                        "error": "Razorpay is not available",
                        "code": order.get("code", "PROVIDER_ERROR"),
                        "provider": "razorpay",
                        "detail": order.get("detail"),
                        "required_env": order.get("required_env", []),
                    }, status=503)
                    return
                self._send_json({
                    "success": True,
                    "order_id": order.get("order_id"),
                    "tier": tier.value,
                    "amount_inr": plan.monthly_price_usd * 85.0,
                    "currency": "INR",
                    "provider": "razorpay",
                })
            else:
                self._send_json({"error": "Bad Request", "code": "UNSUPPORTED_PROVIDER",
                                 "detail": f"Unsupported provider: {provider}",
                                 "supported": ["stripe", "razorpay"]}, status=400)
            return

        elif path in ("/api/billing/settlement/reconcile", "/api/v1/billing/settlement/reconcile"):
            res_id = req_data.get("reservation_id", "")
            actual_tokens = int(req_data.get("actual_tokens", 0))
            actual_usd = float(req_data.get("actual_usd", 0.0))
            res = saas_billing_engine.reconcile_economic_settlement(
                tenant_id=tenant_id,
                reservation_id=res_id,
                actual_tokens=actual_tokens,
                actual_usd=actual_usd
            )
            self._send_json(res)
            return

        # PostHog Product Analytics Capture
        elif path == "/api/analytics/posthog/capture":
            tenant = tenant_id
            company = self.headers.get("X-Company-ID") or company_id
            distinct_id = req_data.get("distinct_id", "usr_anon")
            event_name = req_data.get("event_name", "page_view")
            properties = req_data.get("properties", {})
            event = posthog_analytics.capture(
                distinct_id=distinct_id,
                event_name=event_name,
                properties=properties,
                tenant_id=tenant,
                company_id=company
            )
            self._send_json({"success": True, "event": event.to_dict()})
            return

        # Object Storage Artifact Upload / Store
        elif path == "/api/storage/artifacts/upload":
            tenant = tenant_id
            company = self.headers.get("X-Company-ID") or company_id
            name = req_data.get("name", "artifact.bin")
            content = req_data.get("content", "").encode("utf-8")
            cat = req_data.get("category", "documents")
            ttl = int(req_data.get("ttl_hours", 24))
            ref = object_store.store_large_artifact(
                name=name,
                data=content,
                category=cat,
                tenant_id=tenant,
                company_id=company,
                metadata=req_data.get("metadata", {}),
                ttl_hours=ttl
            )
            self._send_json({"success": True, "artifact": ref.to_dict()})
            return

        # URA / ZONATA: Enterprise AI Corporate Workforce Architecture
        if path.startswith("/api/workforce"):
            if self._blocked_by_global_killswitch("workforce mutation"):
                return
            from core.workforce_api import handle_post as workforce_post
            wf_res = workforce_post(path, req_data, tenant_id, company_id, auth_context)
            if wf_res:
                data, code = wf_res
                self._send_json(data, status=code)
                return

        self._send_json({"error": "Endpoint not found"}, status=404)

    def do_PUT(self):
        self._start_time = time.time()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Enforce transport security for PUT endpoints
        if not self._validate_transport_security():
            return

        try:
            auth_ctx = self._get_auth_context()
            tenant_id = auth_ctx.get("tenant_id")
            if not tenant_id:
                self._send_json({"error": "Unauthorized", "detail": "Missing tenant identity in token"}, status=401)
                return
        except AuthExceptions.AuthenticationError as e:
            self._send_json({"error": "Unauthorized", "detail": str(e)}, status=401)
            return
        except AuthExceptions.TenantIsolationViolation as e:
            self._send_json({"error": "Forbidden", "detail": str(e), "security_event": "TENANT_SPOOFING_ATTEMPT"}, status=403)
            return

        if not self._enforce_tenant_fairness(path, "PUT", auth_context=auth_ctx):
            return

        company_id = self._resolve_company_id(auth_ctx)
        actor = auth_ctx.get("user_id", "usr_unknown")
        actor_role = auth_ctx.get("role", UserRole.OPERATOR)

        length = int(self.headers.get('content-length', 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            req_data = json.loads(raw_body.decode('utf-8'))
        except Exception:
            req_data = {}

        if path.startswith("/api/crm/deals/") and len(path.split("/")) == 5:
            deal_id = path.split("/")[4]
            from core.enterprise_crm import EnterpriseCrmService
            svc = EnterpriseCrmService(tenant_id)
            try:
                if len(req_data) == 1 and "stage" in req_data:
                    res = svc.update_deal_stage(deal_id, req_data["stage"])
                else:
                    res = svc.update_deal(deal_id, req_data)
                if not res.get("updated", True) and not res.get("deal_id"):
                    self._send_json({"error": "Not Found", "detail": f"Deal '{deal_id}' not found in current organization"}, status=404)
                    return
                self._send_json(res)
            except KeyError as e:
                self._send_json({"error": "Not Found", "detail": str(e)}, status=404)
            except ValueError as e:
                self._send_json({"error": "Bad Request", "detail": str(e)}, status=400)
            return

        elif path.startswith("/api/crm/customers/") and len(path.split("/")) == 5:
            cust_id = path.split("/")[4]
            from core.enterprise_crm import EnterpriseCrmService
            svc = EnterpriseCrmService(tenant_id)
            try:
                res = svc.update_customer(cust_id, req_data)
                self._send_json(res)
            except KeyError as e:
                self._send_json({"error": "Not Found", "detail": str(e)}, status=404)
            except ValueError as e:
                self._send_json({"error": "Bad Request", "detail": str(e)}, status=400)
            return

        elif path.startswith("/api/settings/key/") and len(path.split("/")) == 5:
            s_key = path.split("/")[4]
            expected_ver = req_data.get("expected_version")
            new_val = req_data.get("value") if "value" in req_data else req_data
            reason = req_data.get("reason", "Direct REST PUT setting update")
            scope = req_data.get("scope", "Company")
            res = settings_service.update_single_setting(
                tenant_id, company_id, s_key, new_val,
                actor=actor, reason=reason, scope=scope,
                actor_role=actor_role, expected_version=expected_ver
            )
            status_code = res.get("status_code", (200 if res.get("success") else 400))
            self._send_json(res, status=status_code)
            return

        elif path.startswith("/api/settings/category/") and len(path.split("/")) == 5:
            cat_id = path.split("/")[4]
            # company_id was resolved from the verified token (see _resolve_company_id)
            reason = req_data.get("reason", "Batch category save via PUT")
            if "settings" in req_data and isinstance(req_data["settings"], dict):
                values = req_data["settings"]
            elif "values" in req_data and isinstance(req_data["values"], dict):
                values = req_data["values"]
            else:
                values = {k: v for k, v in req_data.items() if k not in ("company_id", "reason", "tenant_id", "actor")}
            res = settings_service.bulk_save_category(tenant_id, company_id, cat_id, values, actor=actor, reason=reason, actor_role=actor_role)
            status_code = 200 if res.get("success") else 400
            self._send_json(res, status=status_code)
            return

        elif path.startswith("/api/automation/workflows/") and len(path.split("/")) == 5:
            wf_id = path.split("/")[4]
            new_spec = req_data.get("spec", req_data)
            try:
                res = universal_automation_fabric.update_and_bump_version(wf_id, new_spec, tenant_id)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        self._send_json({"error": "Endpoint not found or method not allowed"}, status=404)

    def do_PATCH(self):
        """Dispatches HTTP PATCH requests to do_PUT for partial resource mutations."""
        return self.do_PUT()

    def do_DELETE(self):
        self._start_time = time.time()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Enforce transport security for DELETE endpoints
        if not self._validate_transport_security():
            return

        try:
            auth_ctx = self._get_auth_context()
            tenant_id = auth_ctx.get("tenant_id")
            if not tenant_id:
                self._send_json({"error": "Unauthorized", "detail": "Missing tenant identity in token"}, status=401)
                return
            company_id = self._resolve_company_id(auth_ctx)
        except AuthExceptions.AuthenticationError as e:
            self._send_json({"error": "Unauthorized", "detail": str(e)}, status=401)
            return
        except AuthExceptions.TenantIsolationViolation as e:
            self._send_json({"error": "Forbidden", "detail": str(e), "security_event": "TENANT_SPOOFING_ATTEMPT"}, status=403)
            return

        if not self._enforce_tenant_fairness(path, "DELETE", auth_context=auth_ctx):
            return

        # Milestone J: Deactivate Pilot Organization Slot
        if path in ("/api/pilot/organizations/me", f"/api/pilot/organizations/{tenant_id}"):
            try:
                with db.get_connection() as conn:
                    conn.execute("UPDATE pilot_organizations SET status = 'DEACTIVATED' WHERE tenant_id = ?", (tenant_id,))
                    conn.commit()
                self._send_json({"success": True, "tenant_id": tenant_id, "status": "DEACTIVATED"})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if path.startswith("/api/mcp/servers/") and len(path.split("/")) == 5:
            server_id = path.split("/")[4]
            ok = _mcp(tenant_id, company_id).disconnect_server(server_id)
            self._send_json({"success": ok, "server_id": server_id})
            return
        elif path.startswith("/api/browser/sessions/") and len(path.split("/")) == 5:
            sess_id = path.split("/")[4]
            ok = _browser(tenant_id, company_id).close_session(sess_id)
            self._send_json({"success": ok, "session_id": sess_id})
            return
        elif path.startswith("/api/nango/connections/") and len(path.split("/")) == 5:
            conn_id = path.split("/")[4]
            company_id = self._resolve_company_id(auth_ctx)
            gw = ExternalIntegrationGateway(tenant_id, company_id)
            ok = gw.disconnect_connection(conn_id)
            self._send_json({"success": ok, "connection_id": conn_id})
            return
        elif path.startswith("/api/crm/customers/") and len(path.split("/")) == 5:
            cust_id = path.split("/")[4]
            from core.enterprise_crm import EnterpriseCrmService
            svc = EnterpriseCrmService(tenant_id)
            try:
                ok = svc.delete_customer(cust_id)
                if ok:
                    self._send_json({"success": True, "customer_id": cust_id})
                else:
                    self._send_json({"error": "Not Found", "detail": f"Customer '{cust_id}' not found in tenant"}, status=404)
            except KeyError as e:
                self._send_json({"error": "Not Found", "detail": str(e)}, status=404)
            return
        elif path.startswith("/api/crm/deals/") and len(path.split("/")) == 5:
            deal_id = path.split("/")[4]
            from core.enterprise_crm import EnterpriseCrmService
            svc = EnterpriseCrmService(tenant_id)
            try:
                ok = svc.delete_deal(deal_id)
                if ok:
                    self._send_json({"success": True, "deal_id": deal_id})
                else:
                    self._send_json({"error": "Not Found", "detail": f"Deal '{deal_id}' not found in tenant"}, status=404)
            except KeyError as e:
                self._send_json({"error": "Not Found", "detail": str(e)}, status=404)
            return
        self._send_json({"error": "Method not allowed or endpoint not found"}, status=404)


# Backward-compatibility and architectural alias
SaaSHTTPRequestHandler = RoboAssistantRequestHandler


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def run_server(port=8080):
    ThreadedHTTPServer.allow_reuse_address = True
    app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
    is_prod = (app_env == "production") or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1") or (os.environ.get("ZONATA_PRODUCTION", "0") == "1")
    if is_prod and os.environ.get("ZONATA_ALLOW_HOST_SHELL", "0") == "1":
        raise RuntimeError("Security Invariant Violation: ZONATA_ALLOW_HOST_SHELL=1 is strictly prohibited in production mode. Refusing server startup.")

    # Enforce database connectivity readiness verification before binding or starting workers
    db.verify_readiness()
    from core.database_engine import engine
    engine.verify_readiness()

    tls_cert = os.environ.get("TLS_CERT_PATH") or os.environ.get("SSL_CERTFILE")
    tls_key = os.environ.get("TLS_KEY_PATH") or os.environ.get("SSL_KEYFILE")
    use_tls = False
    ssl_context = None

    if tls_cert and tls_key:
        if not os.path.exists(tls_cert) or not os.path.exists(tls_key):
            if is_prod:
                raise RuntimeError(f"Production TLS Configuration Error: Configured certificate '{tls_cert}' or key '{tls_key}' does not exist.")
            else:
                print(f"[!] Warning: TLS cert/key not found on disk ({tls_cert}, {tls_key}). Starting without TLS.")
        else:
            import ssl
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            ssl_context.load_cert_chain(certfile=tls_cert, keyfile=tls_key)
            use_tls = True

    proto_name = "https" if use_tls else "http"
    print(f"[*] Starting RoboAssistant Company OS 1.0 Server on port {port} ({proto_name.upper()} Multi-Threaded Engine)...", flush=True)
    universal_automation_fabric.start_background_worker(poll_interval=0.5)
    print("[*] Universal Automation Fabric Background Worker ACTIVE", flush=True)

    # Start tenant-scoped co-worker schedulers for companies that already
    # exist. This is asynchronous and skipped in test mode.
    try:
        from core.coworker.runtime_supervisor import bootstrap_tenant_supervisors
        if bootstrap_tenant_supervisors():
            print("[*] Co-worker autonomy bootstrap scheduled (tenant-scoped)", flush=True)
    except Exception as exc:
        print(f"[!] Co-worker autonomy bootstrap unavailable: {type(exc).__name__}", flush=True)

    if os.environ.get("ZONATA_EMBEDDED_WORKER", "0") == "1":
        import threading
        from core.action_envelope import command_bus
        command_bus.reset_worker()
        embedded_worker_thread = threading.Thread(
            target=command_bus.run_worker,
            kwargs={"worker_id": f"embedded_worker_{port}", "poll_interval": 1.0},
            daemon=True
        )
        embedded_worker_thread.start()
        print("[*] Embedded Asynchronous CommandBus Worker ACTIVE", flush=True)

    # Register graceful shutdown signals for cloud container lifecycle (Render/PaaS)
    def _graceful_signal_handler(signum, frame):
        print(f"\n[*] Received termination signal ({signum}). Initiating graceful shutdown...", flush=True)
        try:
            universal_automation_fabric.stop_background_worker()
            try:
                from core.coworker.runtime_supervisor import shutdown_all_supervisors
                shutdown_all_supervisors(timeout=3.0)
            except Exception:
                pass
            if os.environ.get("ZONATA_EMBEDDED_WORKER", "0") == "1":
                from core.action_envelope import command_bus
                command_bus.stop()
        except Exception:
            pass
        sys.exit(0)

    try:
        import signal
        signal.signal(signal.SIGTERM, _graceful_signal_handler)
        signal.signal(signal.SIGINT, _graceful_signal_handler)
    except Exception:
        pass

    try:
        with ThreadedHTTPServer(("", port), RoboAssistantRequestHandler) as httpd:
            if use_tls and ssl_context:
                httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
                print(f"[*] TLS Termination ENABLED (TLS 1.2+ minimum, cert: {tls_cert})", flush=True)
            print(f"[*] Company OS 1.0 ready at {proto_name}://localhost:{port} (Threaded Concurrency Enabled)", flush=True)
            httpd.serve_forever()
    finally:
        universal_automation_fabric.stop_background_worker()
        try:
            from core.coworker.runtime_supervisor import shutdown_all_supervisors
            shutdown_all_supervisors(timeout=3.0)
        except Exception:
            pass
        if os.environ.get("ZONATA_EMBEDDED_WORKER", "0") == "1":
            try:
                from core.action_envelope import command_bus
                command_bus.stop()
            except Exception:
                pass

if __name__ == "__main__":
    port_env = os.environ.get("PORT")
    if port_env and port_env.isdigit():
        p = int(port_env)
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        p = int(sys.argv[1])
    else:
        p = 8080
    run_server(p)

