"""
ZONATA / RoboAssistant — Tenant Runtime Registry
==========================================================
Every stateful subsystem (portfolio, AI CEO, co-worker fabric, evidence
ledger) must be bound to the authenticated tenant.  Historically the API
server instantiated a single global runtime pinned to ``tnt_primary``,
which leaked companies, missions and evidence across tenants.

This module is the single source of truth for tenant-scoped runtimes.
Nothing here trusts client-supplied identifiers: callers must pass the
tenant/company resolved from the verified bearer token.
"""

from __future__ import annotations

import os
import re
import threading
from typing import Any, Dict, Optional


_SAFE = re.compile(r"[^a-zA-Z0-9_.-]+")


def safe_tenant_key(tenant_id: str) -> str:
    key = _SAFE.sub("_", (tenant_id or "").strip())
    return key[:96] or "unknown_tenant"


def tenant_ledger_path(tenant_id: str) -> str:
    """Per-tenant evidence ledger path. Legacy primary tenant keeps its file."""
    explicit = os.environ.get("ZONATA_EVIDENCE_PATH")
    if explicit:
        # Test harness override: isolate the whole process to one file.
        return os.path.abspath(explicit)
    storage_root = os.environ.get("ZONATA_STORAGE_DIR")
    base = os.path.abspath(storage_root) if storage_root else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage"
    )
    if tenant_id in (None, "", "tnt_primary"):
        return os.path.join(base, "evidence", "audit_ledger.jsonl")
    return os.path.join(base, "evidence", "tenants", safe_tenant_key(tenant_id), "audit_ledger.jsonl")


class TenantRuntime:
    """Lazily-constructed, process-cached runtime for one tenant/company."""

    def __init__(self, tenant_id: str, company_id: Optional[str] = None):
        if not tenant_id:
            raise ValueError("tenant_id is required for a tenant runtime")
        self.tenant_id = tenant_id
        self.company_id = company_id or f"comp_{tenant_id}"
        self._portfolio = None
        self._ceo_engine = None
        self._ceo_command = None
        self._ceo_reports = None
        self._coworker = None
        self._ledger = None
        self._lock = threading.RLock()

    # ------------------------------------------------------------- portfolio
    @property
    def portfolio(self):
        from core.portfolio import CompanyPortfolioManager
        with self._lock:
            if self._portfolio is None:
                self._portfolio = CompanyPortfolioManager(
                    tenant_id=self.tenant_id, load_from_db=True
                )
            return self._portfolio

    # --------------------------------------------------------------- AI CEO
    @property
    def ceo_engine(self):
        from core.ceo_engine import CEOExecutiveEngine
        with self._lock:
            if self._ceo_engine is None:
                self._ceo_engine = CEOExecutiveEngine(self.portfolio, tenant_id=self.tenant_id)
            return self._ceo_engine

    @property
    def ceo_command(self):
        from core.ceo import CeoCommandEngine
        with self._lock:
            if self._ceo_command is None:
                self._ceo_command = CeoCommandEngine(self.portfolio)
            return self._ceo_command

    @property
    def ceo_reports(self):
        from core.ceo import ExecutiveReportEngine
        with self._lock:
            if self._ceo_reports is None:
                self._ceo_reports = ExecutiveReportEngine(self.portfolio)
            return self._ceo_reports

    # ------------------------------------------------------------- co-worker
    @property
    def coworker(self):
        from core.coworker.engine import UniversalCoworkerEngine
        with self._lock:
            if self._coworker is None:
                self._coworker = UniversalCoworkerEngine.get_instance(
                    tenant_id=self.tenant_id, company_id=self.company_id
                )
            return self._coworker

    # ------------------------------------------------------- tenant services
    @property
    def company_service(self):
        from zonata.company_api_service import CompanyApiService
        with self._lock:
            if not hasattr(self, "_company_service") or self._company_service is None:
                self._company_service = CompanyApiService(self.portfolio)
            return self._company_service

    @property
    def event_engine(self):
        from core.event_engine import EnterpriseEventEngine
        with self._lock:
            if not hasattr(self, "_event_engine") or self._event_engine is None:
                self._event_engine = EnterpriseEventEngine(self.portfolio, tenant_id=self.tenant_id)
            return self._event_engine

    @property
    def meetings(self):
        from core.interactive_meeting import InteractiveMeetingSystem
        with self._lock:
            if not hasattr(self, "_meetings") or self._meetings is None:
                self._meetings = InteractiveMeetingSystem(
                    self.portfolio, tenant_id=self.tenant_id, company_id=self.company_id
                )
            return self._meetings

    @property
    def schedule(self):
        from core.schedule_service import UniversalScheduleService
        with self._lock:
            if not hasattr(self, "_schedule") or self._schedule is None:
                self._schedule = UniversalScheduleService(tenant_id=self.tenant_id)
            return self._schedule

    @property
    def meeting_service(self):
        from core.meeting_service import AiCeoMeetingService
        with self._lock:
            if not hasattr(self, "_meeting_service") or self._meeting_service is None:
                self._meeting_service = AiCeoMeetingService(tenant_id=self.tenant_id)
            return self._meeting_service

    @property
    def assistant(self):
        from core.assistant_service import FloatingAssistantService
        with self._lock:
            if not hasattr(self, "_assistant") or self._assistant is None:
                self._assistant = FloatingAssistantService(tenant_id=self.tenant_id)
            return self._assistant

    @property
    def plugins(self):
        from core.plugins_service import PluginsAndConnectionsService
        with self._lock:
            if not hasattr(self, "_plugins") or self._plugins is None:
                self._plugins = PluginsAndConnectionsService(tenant_id=self.tenant_id)
            return self._plugins

    @property
    def host_agent(self):
        from core.host_fabric import UniversalHostAgent
        with self._lock:
            if not hasattr(self, "_host_agent") or self._host_agent is None:
                self._host_agent = UniversalHostAgent(tenant_id=self.tenant_id)
            return self._host_agent

    @property
    def desktop_robot(self):
        from core.desktop_robot import UniversalDesktopRobot
        with self._lock:
            if not hasattr(self, "_desktop_robot") or self._desktop_robot is None:
                self._desktop_robot = UniversalDesktopRobot(self.host_agent, ledger=self.ledger)
            return self._desktop_robot

    @property
    def sales(self):
        from core.sales_workforce import AISalesWorkforce
        with self._lock:
            if not hasattr(self, "_sales") or self._sales is None:
                self._sales = AISalesWorkforce(tenant_id=self.tenant_id)
            return self._sales

    @property
    def voice(self):
        from core.voice_agent import GovernedVoiceAgent
        with self._lock:
            if not hasattr(self, "_voice") or self._voice is None:
                self._voice = GovernedVoiceAgent(tenant_id=self.tenant_id)
            return self._voice

    @property
    def causality(self):
        from core.business_causality import BusinessCausalityEngine
        with self._lock:
            if not hasattr(self, "_causality") or self._causality is None:
                self._causality = BusinessCausalityEngine(tenant_id=self.tenant_id)
            return self._causality

    @property
    def workforce_intel(self):
        from core.workforce_intelligence import WorkforceIntelligenceEngine
        with self._lock:
            if not hasattr(self, "_workforce_intel") or self._workforce_intel is None:
                self._workforce_intel = WorkforceIntelligenceEngine(tenant_id=self.tenant_id)
            return self._workforce_intel

    @property
    def terminal(self):
        from core.universal_terminal import UniversalTerminal
        with self._lock:
            if not hasattr(self, "_terminal") or self._terminal is None:
                self._terminal = UniversalTerminal(
                    tenant_id=self.tenant_id, company_id=self.company_id
                )
            return self._terminal

    @property
    def terminal_runtime(self):
        from core.coworker.runtimes.terminal_runtime import TerminalWorkerRuntime
        with self._lock:
            if not hasattr(self, "_terminal_runtime") or self._terminal_runtime is None:
                self._terminal_runtime = TerminalWorkerRuntime(
                    tenant_id=self.tenant_id, company_id=self.company_id
                )
            return self._terminal_runtime

    @property
    def terminal_agent(self):
        from core.universal_terminal import TerminalHandlingAgent
        with self._lock:
            if not hasattr(self, "_terminal_agent") or self._terminal_agent is None:
                self._terminal_agent = TerminalHandlingAgent(
                    tenant_id=self.tenant_id, company_id=self.company_id
                )
            return self._terminal_agent

    @property
    def kernel(self):
        from core.control_kernel import UniversalControlKernel
        with self._lock:
            if not hasattr(self, "_kernel") or self._kernel is None:
                self._kernel = UniversalControlKernel(self.ledger)
            return self._kernel

    @property
    def multimodal(self):
        from core.multimodal_capability_runtime import MultimodalCapabilityRegistry
        with self._lock:
            if not hasattr(self, "_multimodal") or self._multimodal is None:
                self._multimodal = MultimodalCapabilityRegistry(tenant_id=self.tenant_id)
            return self._multimodal

    @property
    def multimodal_execution(self):
        from core.multimodal_capability_runtime import MultimodalExecutionManager
        with self._lock:
            if not hasattr(self, "_multimodal_execution") or self._multimodal_execution is None:
                self._multimodal_execution = MultimodalExecutionManager(tenant_id=self.tenant_id)
            return self._multimodal_execution

    @property
    def heartbeat(self):
        from src.services.agent_engine import HeartbeatCoordinator
        with self._lock:
            if not hasattr(self, "_heartbeat") or self._heartbeat is None:
                self._heartbeat = HeartbeatCoordinator()
            return self._heartbeat

    @property
    def delegation(self):
        from src.services.agent_engine import DelegationEngine
        with self._lock:
            if not hasattr(self, "_delegation") or self._delegation is None:
                self._delegation = DelegationEngine()
            return self._delegation

    @property
    def a2a(self):
        from core.a2a_interoperability_runtime import A2AGateway
        with self._lock:
            if not hasattr(self, "_a2a") or self._a2a is None:
                self._a2a = A2AGateway(self.tenant_id, self.company_id)
            return self._a2a

    @property
    def a2a_scenarios(self):
        from zonata.a2a_adapter import A2ACanonicalScenarios
        with self._lock:
            if not hasattr(self, "_a2a_scenarios") or self._a2a_scenarios is None:
                self._a2a_scenarios = A2ACanonicalScenarios(self.tenant_id, self.company_id)
            return self._a2a_scenarios

    @property
    def mcp(self):
        from core.mcp_interoperability_runtime import MCPGateway
        with self._lock:
            if not hasattr(self, "_mcp") or self._mcp is None:
                self._mcp = MCPGateway(self.tenant_id, self.company_id)
            return self._mcp

    @property
    def mcp_scenarios(self):
        from zonata.mcp_adapter import McpCanonicalScenarios
        with self._lock:
            if not hasattr(self, "_mcp_scenarios") or self._mcp_scenarios is None:
                self._mcp_scenarios = McpCanonicalScenarios(self.tenant_id, self.company_id)
            return self._mcp_scenarios

    @property
    def mcp_server(self):
        from core.mcp_interoperability_runtime import ZonataMcpServer
        with self._lock:
            if not hasattr(self, "_mcp_server") or self._mcp_server is None:
                self._mcp_server = ZonataMcpServer(self.tenant_id, self.company_id)
            return self._mcp_server

    @property
    def openhands(self):
        from core.openhands_execution_runtime import OpenHandsRuntimeGateway
        with self._lock:
            if not hasattr(self, "_openhands") or self._openhands is None:
                self._openhands = OpenHandsRuntimeGateway(self.tenant_id, self.company_id)
            return self._openhands

    @property
    def openhands_scenarios(self):
        from zonata.openhands_adapter import OpenHandsCanonicalScenarios
        with self._lock:
            if not hasattr(self, "_openhands_scenarios") or self._openhands_scenarios is None:
                self._openhands_scenarios = OpenHandsCanonicalScenarios(self.tenant_id, self.company_id)
            return self._openhands_scenarios

    @property
    def browser(self):
        from core.browser_use_execution_runtime import BrowserExecutionGateway
        with self._lock:
            if not hasattr(self, "_browser") or self._browser is None:
                self._browser = BrowserExecutionGateway(self.tenant_id, self.company_id)
            return self._browser

    @property
    def browser_scenarios(self):
        from zonata.browser_use_adapter import BrowserUseCanonicalScenarios
        with self._lock:
            if not hasattr(self, "_browser_scenarios") or self._browser_scenarios is None:
                self._browser_scenarios = BrowserUseCanonicalScenarios(self.tenant_id, self.company_id)
            return self._browser_scenarios

    @property
    def nango(self):
        from core.nango_integration_runtime import ExternalIntegrationGateway
        with self._lock:
            if not hasattr(self, "_nango") or self._nango is None:
                self._nango = ExternalIntegrationGateway(self.tenant_id, self.company_id)
            return self._nango

    @property
    def nango_scenarios(self):
        from zonata.nango_adapter import NangoCanonicalScenarios
        with self._lock:
            if not hasattr(self, "_nango_scenarios") or self._nango_scenarios is None:
                self._nango_scenarios = NangoCanonicalScenarios(self.tenant_id, self.company_id)
            return self._nango_scenarios

    @property
    def temporal(self):
        from core.temporal_durable_execution_runtime import TemporalDurableExecutionGateway
        with self._lock:
            if not hasattr(self, "_temporal") or self._temporal is None:
                self._temporal = TemporalDurableExecutionGateway(
                    self.tenant_id, self.company_id
                )
            return self._temporal

    @property
    def temporal_scenarios(self):
        from zonata.temporal_adapter import TemporalCanonicalScenarios
        with self._lock:
            if not hasattr(self, "_temporal_scenarios") or self._temporal_scenarios is None:
                self._temporal_scenarios = TemporalCanonicalScenarios(
                    self.tenant_id, self.company_id
                )
            return self._temporal_scenarios

    # -------------------------------------------------------------- evidence
    @property
    def ledger(self):
        from core.evidence_ledger import EvidenceLedger
        with self._lock:
            if self._ledger is None:
                self._ledger = EvidenceLedger(tenant_ledger_path(self.tenant_id))
            return self._ledger


_REGISTRY: Dict[str, TenantRuntime] = {}
_REGISTRY_LOCK = threading.Lock()


def get_runtime(tenant_id: str, company_id: Optional[str] = None) -> TenantRuntime:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    key = f"{tenant_id}::{company_id or 'default'}"
    with _REGISTRY_LOCK:
        rt = _REGISTRY.get(key)
        if rt is None:
            rt = TenantRuntime(tenant_id, company_id)
            _REGISTRY[key] = rt
        elif company_id and rt.company_id != company_id:
            rt.company_id = company_id
        return rt


def get_portfolio(tenant_id: str):
    return get_runtime(tenant_id).portfolio


def get_ledger(tenant_id: str):
    return get_runtime(tenant_id).ledger


def get_coworker(tenant_id: str, company_id: Optional[str] = None):
    return get_runtime(tenant_id, company_id).coworker


def invalidate(tenant_id: str) -> None:
    """Drop cached runtimes for a tenant (after onboarding/offboarding)."""
    with _REGISTRY_LOCK:
        for key in [k for k in _REGISTRY if k.startswith(f"{tenant_id}::")]:
            _REGISTRY.pop(key, None)
