"""
ZONATA Universal AI Co-worker Fabric — Master Orchestration Engine
Integrates the complete Co-worker stack:
CapabilityRegistry, ProviderRegistry, CapabilityRouter, FallbackManager,
CredentialAuthority, PolicyEvaluator, HumanTakeoverManager, IndependentVerificationEngine,
EvidenceLedgerAdapter, WorkerSupervisor, and RecoveryEngine.
Preserves ZONATA sovereignty over all external capability providers.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
import uuid
import os
import json
import sqlite3

from .contracts import (
    CapabilityDefinition, CapabilityCategory, RiskLevel, CostClass, LatencyClass,
    ProviderHealthStatus, ExecutionState, VerificationStatus, SupervisedControlMode,
    TaskNode, ExecutionGraph, CoworkerProfile, ExecutionResult, VerificationResult
)
from .capability_registry import CapabilityRegistry
from .provider_registry import ProviderRegistry, ProviderHealthMonitor
from .router import CapabilityRouter
from .fallback_manager import FallbackManager
from .credential_authority import CredentialAuthority
from .policy_evaluator import CoworkerPolicyEvaluator, RiskClassifier
from .human_takeover import HumanTakeoverManager
from .verification_engine import IndependentVerificationEngine
from .evidence_ledger_adapter import EvidenceLedgerAdapter
from .supervisor import WorkerSupervisor, ExecutionLeaseManager
from .recovery_engine import RecoveryEngine
from .template_factory import CoworkerTemplateFactory
from .operating_instructions import OperatingInstructionParser, DeterministicSafetyRuleEngine
from .worker_managers import (
    DesktopWorkerManager, BrowserWorkerManager, APIWorkerManager,
    RPAWorkerManager, VisualComputerWorkerManager, FileWorkerManager,
    TerminalWorkerManager
)
from .tool_discovery import ToolDiscoveryEngine
from .self_extension import SelfExtensionEngine
from .qualification_harness import ProviderQualificationHarness
from ..killswitch_matrix import KillSwitchMatrix, KillSwitchLevel
from .db_store import CoworkerDBStore
from .fleet import (
    GovernedNodeRegistry, GovernedFleetRouter, RemoteNodeWorkerAgent,
    WorkerNodeProfile, NodeTaskAssignment, NodeTaskResult,
    NodePlatform, NodeType
)
from .hermes_agent import HermesAgenticOrchestrator, HermesToolCall, HermesStepResult
from .soak import SupervisorEnduranceRunner, FailureInjectionEngine, SoakTelemetryMetrics

class UniversalCoworkerEngine:

    """
    Master Engine for the ZONATA Universal AI Co-worker Fabric.
    Executes multi-capability missions across desktop, browser, API, RPA, and visual CUAs
    under strict sovereign governance.
    """

    _instances: Dict[str, "UniversalCoworkerEngine"] = {}

    @classmethod
    def get_instance(cls, tenant_id: str = "tnt_primary") -> "UniversalCoworkerEngine":
        if tenant_id not in cls._instances:
            cls._instances[tenant_id] = cls(tenant_id=tenant_id)
        return cls._instances[tenant_id]

    def __init__(self, tenant_id: str = "tnt_primary", db_path: str = "storage/roboassistant.db"):
        self.tenant_id = tenant_id
        self.db_path = db_path

        # 1. Registries & Providers
        self.capability_reg = CapabilityRegistry()
        self.provider_reg = ProviderRegistry()
        self.health_monitor = ProviderHealthMonitor(self.provider_reg)

        # 2. Routing & Fallbacks
        self.router = CapabilityRouter(self.capability_reg, self.provider_reg)
        self.fallback_mgr = FallbackManager(self.provider_reg)

        # 3. Domain Worker Managers
        self.desktop_mgr = DesktopWorkerManager(self.provider_reg)
        self.browser_mgr = BrowserWorkerManager(self.provider_reg)
        self.api_mgr = APIWorkerManager(self.provider_reg)
        self.rpa_mgr = RPAWorkerManager(self.provider_reg)
        self.visual_mgr = VisualComputerWorkerManager(self.provider_reg)
        self.file_mgr = FileWorkerManager(self.provider_reg)
        self.terminal_mgr = TerminalWorkerManager(self.provider_reg)

        # 4. Tool Discovery & Self-Extension
        self.tool_discovery = ToolDiscoveryEngine(tenant_id)
        self.self_extension = SelfExtensionEngine(
            self.capability_reg, self.provider_reg, self.tool_discovery, self.router, tenant_id
        )
        self.qualification_harness = ProviderQualificationHarness(self.provider_reg)

        # 5. Governance, Safety & Authentication
        self.credential_authority = CredentialAuthority(tenant_id)
        self.policy_evaluator = CoworkerPolicyEvaluator(tenant_id)
        self.killswitch = KillSwitchMatrix(tenant_id)
        self.takeover_mgr = HumanTakeoverManager()

        # 6. Verification & Evidence
        self.verifier = IndependentVerificationEngine(tenant_id)
        self.evidence_adapter = EvidenceLedgerAdapter(tenant_id)

        # 7. 24x7 Operations & Supervision
        self.supervisor = WorkerSupervisor()
        self.recovery_engine = RecoveryEngine(self.provider_reg)

        # 8. Governed Distributed Worker Fleet & Node Routing
        self.node_registry = GovernedNodeRegistry()
        self.fleet_router = GovernedFleetRouter(self.node_registry)

        # 9. Hermes Agentic Orchestrator & Multi-Step Reasoning
        self.hermes = HermesAgenticOrchestrator(self)

        # 10. 24x7 Soak Endurance Runner & Chaos Failure Injector
        self.soak_runner = SupervisorEnduranceRunner(self)
        self.chaos_injector = FailureInjectionEngine(self)

        # In-memory execution graphs & DB persistence
        self._active_graphs: Dict[str, ExecutionGraph] = {}
        self.store = CoworkerDBStore(db_path)


    def create_coworker(self, role_or_prompt: str) -> CoworkerProfile:
        """Instantiates and registers a new AI Co-worker profile."""
        profile = CoworkerTemplateFactory.compile_from_natural_language(role_or_prompt, self.tenant_id)
        self.supervisor.register_worker(profile)
        self.store.save_worker_profile(profile)
        return profile

    def get_coworker(self, worker_id: str) -> Optional[CoworkerProfile]:
        w = self.supervisor.get_worker(worker_id)
        if w:
            return w
        row = self.store.get_worker_profile(worker_id)
        if row:
            profile = CoworkerProfile(
                worker_id=row["worker_id"],
                tenant_id=row["tenant_id"],
                role=row["role"],
                department=row["department"],
                skills=json.loads(row["skills"]) if isinstance(row["skills"], str) else row["skills"],
                capabilities=json.loads(row["capabilities"]) if isinstance(row["capabilities"], str) else row["capabilities"],
                authority_scope=json.loads(row["authority_scope"]) if isinstance(row["authority_scope"], str) else row["authority_scope"],
                credential_scope=json.loads(row["credential_scope"]) if isinstance(row["credential_scope"], str) else row["credential_scope"],
                platform_scope=["linux", "windows", "darwin"],
                allowed_providers=json.loads(row["allowed_providers"]) if isinstance(row["allowed_providers"], str) else row["allowed_providers"],
                risk_limit=RiskLevel(row["risk_limit"]),
                budget_limit=row["budget_limit"],
                status=row["status"],
                created_at=row["created_at"]
            )
            self.supervisor.register_worker(profile)
            return profile
        return None

    def get_mission(self, mission_id: str) -> Optional[ExecutionGraph]:
        if mission_id in self._active_graphs:
            return self._active_graphs[mission_id]
        with self.store._get_connection() as conn:
            cur = conn.cursor()
            row = cur.execute("SELECT * FROM coworker_execution_graphs WHERE mission_id = ?", (mission_id,)).fetchone()
            if row:
                graph = ExecutionGraph(
                    mission_id=row["mission_id"],
                    tenant_id=row["tenant_id"],
                    owner_objective=row["owner_objective"],
                    nodes={},
                    status=ExecutionState(row["status"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                self._active_graphs[mission_id] = graph
                return graph
        return None

    def create_mission_from_objective(self, natural_objective: str) -> ExecutionGraph:
        """Translates an owner natural language prompt into a structured ExecutionGraph."""
        graph = OperatingInstructionParser.parse_objective_to_graph(natural_objective, tenant_id=self.tenant_id)
        self._active_graphs[graph.mission_id] = graph
        return graph

    def execute_task(
        self,
        task: TaskNode,
        worker: CoworkerProfile,
        human_approval_granted: bool = False
    ) -> Tuple[ExecutionResult, VerificationResult, ExecutionState]:
        """
        Executes a single TaskNode through the full 14-stage governance pipeline:
        DISCOVER -> UNDERSTAND -> CHECK_CAPABILITIES -> PLAN -> RISK_ASSESS ->
        REQUEST_AUTHORITY -> REQUEST_APPROVAL -> PREPARE -> EXECUTE ->
        OBSERVE -> VERIFY -> COMMIT -> EVIDENCE -> SUCCESS
        """
        task.attempts += 1

        # 1. KillSwitch Check
        if self.killswitch.is_activated(KillSwitchLevel.GLOBAL) or \
           self.killswitch.is_activated(KillSwitchLevel.TENANT, self.tenant_id):
            task.state = ExecutionState.KILLSWITCH
            res = ExecutionResult(
                provider_id="none",
                capability_id=task.capability_id,
                execution_id=f"ks_{task.task_id}",
                status="BLOCKED_BY_KILLSWITCH",
                error_message="Execution halted by active KillSwitch"
            )
            ver = VerificationResult(status=VerificationStatus.FAILED, verified_by="KillSwitchMatrix")
            return res, ver, ExecutionState.KILLSWITCH

        # 2. Check capability
        task.state = ExecutionState.CHECK_CAPABILITIES
        cap = self.capability_reg.get_capability(task.capability_id)
        if not cap:
            task.state = ExecutionState.EXECUTION_FAILURE
            res = ExecutionResult(
                provider_id="none",
                capability_id=task.capability_id,
                execution_id="missing_cap",
                status="FAILED",
                error_message=f"Capability '{task.capability_id}' not found in registry"
            )
            ver = VerificationResult(status=VerificationStatus.FAILED, verified_by="CapabilityRegistry")
            return res, ver, ExecutionState.EXECUTION_FAILURE

        # 3. Policy & Authority Evaluation
        task.state = ExecutionState.REQUEST_AUTHORITY
        allowed, requires_approval, assessed_risk, denial_msg = self.policy_evaluator.evaluate_request(
            worker, cap, task.parameters
        )

        if not allowed:
            task.state = ExecutionState.POLICY_DENIED
            res = ExecutionResult(
                provider_id="none",
                capability_id=task.capability_id,
                execution_id="pol_denied",
                status="POLICY_DENIED",
                error_message=denial_msg
            )
            ver = VerificationResult(status=VerificationStatus.FAILED, verified_by="PolicyEvaluator")
            return res, ver, ExecutionState.POLICY_DENIED

        # 4. Human Approval Gate
        if requires_approval and not human_approval_granted:
            task.state = ExecutionState.REQUEST_APPROVAL
            res = ExecutionResult(
                provider_id="none",
                capability_id=task.capability_id,
                execution_id="await_approval",
                status="AWAITING_HUMAN_APPROVAL",
                error_message="Consequential or financial action requires human approval"
            )
            ver = VerificationResult(status=VerificationStatus.NOT_VERIFIED, verified_by="ApprovalGateway")
            return res, ver, ExecutionState.REQUEST_APPROVAL

        # 5. Route to optimal provider
        selected_provider, route_reason, fallback_ids = self.router.route_capability(
            task.capability_id,
            platform="linux",
            risk_tolerance=worker.risk_limit,
            preferred_provider_override=task.preferred_provider
        )

        if not selected_provider:
            task.state = ExecutionState.EXECUTION_FAILURE
            res = ExecutionResult(
                provider_id="none",
                capability_id=task.capability_id,
                execution_id="route_fail",
                status="FAILED",
                error_message=route_reason
            )
            ver = VerificationResult(status=VerificationStatus.FAILED, verified_by="CapabilityRouter")
            return res, ver, ExecutionState.EXECUTION_FAILURE

        task.selected_provider = selected_provider.providerId()

        # 6. Acquire Execution Lease
        lease = self.supervisor.lease_mgr.acquire_lease(task.task_id, worker.worker_id)

        # 7. Execute with Fallback Manager
        task.state = ExecutionState.EXECUTE
        exec_res, trace = self.fallback_mgr.execute_with_fallback(
            task.capability_id,
            task.parameters,
            {"worker_id": worker.worker_id, "tenant_id": self.tenant_id},
            selected_provider,
            fallback_ids
        )
        if task.idempotency_key and not exec_res.idempotency_key:
            exec_res.idempotency_key = task.idempotency_key


        # 8. Observe and Independently Verify
        task.state = ExecutionState.VERIFY
        verification = self.verifier.verify_execution(
            task.capability_id,
            exec_res,
            task.parameters
        )

        # Release Lease
        self.supervisor.lease_mgr.release_lease(lease.lease_id)

        # 9. Handle Verification Outcome
        if verification.status == VerificationStatus.VERIFIED or verification.status == VerificationStatus.PARTIALLY_VERIFIED:
            task.state = ExecutionState.SUCCESS
            task.result = exec_res
            task.verification = verification

            # 10. Record Tamper-Evident Evidence
            self.evidence_adapter.record_coworker_action(
                task.mission_id,
                task,
                exec_res,
                verification,
                authorization_id=f"auth_{worker.worker_id[:8]}"
            )
            return exec_res, verification, ExecutionState.SUCCESS

        elif verification.status == VerificationStatus.UNCERTAIN:
            # UNCERTAIN must NEVER be marked as SUCCESS
            task.state = ExecutionState.VERIFY_UNCERTAIN
            self.supervisor.escalate_to_human(
                task,
                reason="Verification returned UNCERTAIN; potential unconfirmed side effect",
                context={"exec_result": exec_res.output, "trace": trace}
            )
            return exec_res, verification, ExecutionState.VERIFY_UNCERTAIN

        else:
            task.state = ExecutionState.EXECUTION_FAILURE
            return exec_res, verification, ExecutionState.EXECUTION_FAILURE

    def execute_mission(
        self,
        graph: ExecutionGraph,
        worker: CoworkerProfile,
        auto_approve_human_tasks: bool = False
    ) -> ExecutionGraph:
        """
        Executes an entire multi-task ExecutionGraph in dependency order.
        """
        graph.status = ExecutionState.EXECUTE

        for node_id, node in graph.nodes.items():
            res, ver, final_state = self.execute_task(
                node,
                worker,
                human_approval_granted=auto_approve_human_tasks
            )
            if final_state in [
                ExecutionState.EXECUTION_FAILURE,
                ExecutionState.VERIFY_UNCERTAIN,
                ExecutionState.POLICY_DENIED,
                ExecutionState.KILLSWITCH,
                ExecutionState.REQUEST_APPROVAL,
                ExecutionState.AUTH_REQUIRED
            ]:
                graph.status = final_state
                self.store.save_graph(graph)
                return graph

        graph.status = ExecutionState.SUCCESS
        graph.updated_at = time.time()
        self.store.save_graph(graph)
        return graph

    def self_extend(self, capability_request: str) -> Any:
        """AI CEO requests a capability: system discovers, sandboxes, qualifies and routes."""
        return self.self_extension.request_capability(capability_request)

    def discover_tools(self, query: str) -> List[Any]:
        return self.tool_discovery.discover_tools(query)

    def qualify_all_providers(self, test_server_url: Optional[str] = None) -> Dict[str, Any]:
        results = self.qualification_harness.qualify_all(test_server_url=test_server_url)
        return {pid: res.to_dict() for pid, res in results.items()}

    def get_reality_matrix(self) -> List[Dict[str, Any]]:
        if not self.qualification_harness._results:
            self.qualification_harness.qualify_all()
        return self.qualification_harness.generate_provider_reality_matrix()

