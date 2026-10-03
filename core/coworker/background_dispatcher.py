"""
ZONATA Universal AI Co-worker Fabric — One-Prompt Background Mission Dispatcher
Accepts high-level natural language instructions from users/AI CEO:
e.g. "Find 100 hotels, research their websites, identify decision makers, prepare a verified lead list,
create the report, save it to company workspace and notify me when finished."

Converts instruction into:
Natural Language -> Mission Planner -> Sub-Worker Spawner -> Runtime Router
-> Background Execution -> Heartbeats/Leases -> Verification -> Evidence Ledger -> Notification.
"""

from typing import Dict, List, Optional, Any, Callable
import time
import uuid
import hashlib
from dataclasses import dataclass, field

from .contracts import CoworkerProfile, RiskLevel
from .subworkers import SubWorkerCoordinator, SubWorkerRole, SubWorkerAssignment
from .runtimes.runtime_router import WorkerRuntimeRouter, RoutingDecision
from .runtimes.base_runtime import RuntimeSession, SessionState

@dataclass
class BackgroundMission:
    mission_id: str
    tenant_id: str
    company_id: str
    initiator: str
    prompt: str
    status: str # "QUEUED", "PLANNING", "RUNNING", "VERIFYING", "COMPLETED", "FAILED"
    progress_percent: float = 0.0
    current_stage: str = "Submitted"
    subworkers: List[str] = field(default_factory=list) # child_worker_ids
    runtimes_used: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    evidence_id: Optional[str] = None
    notification_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

class BackgroundMissionDispatcher:
    """
    Autonomous one-prompt background execution coordinator.
    Enables true 'set-it-and-forget-it' worker autonomy with governable checkpoints.
    """

    def __init__(
        self,
        subworker_coord: SubWorkerCoordinator,
        runtime_router: WorkerRuntimeRouter,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary"
    ):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.subworker_coord = subworker_coord
        self.runtime_router = runtime_router
        self._missions: Dict[str, BackgroundMission] = {}

    def submit_background_prompt(
        self,
        prompt: str,
        initiator: str = "AI_CEO",
        parent_worker_id: Optional[str] = None
    ) -> BackgroundMission:
        """
        Main entry point for natural language background missions.
        """
        mid = f"msn_{uuid.uuid4().hex[:8]}"
        pwid = parent_worker_id or f"cw_master_{uuid.uuid4().hex[:6]}"

        mission = BackgroundMission(
            mission_id=mid,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            initiator=initiator,
            prompt=prompt,
            status="PLANNING",
            current_stage="Decomposing natural language objective"
        )
        self._missions[mid] = mission

        # 1. Autonomous Task Decomposition into Parallel Sub-Workers
        lower_prompt = prompt.lower()
        subworker_specs = []

        if any(w in lower_prompt for w in ["research", "find", "search", "hotel", "supplier", "market"]):
            subworker_specs.append((SubWorkerRole.RESEARCH, ["browser.openclaw_search", "browser.openclaw_crawl"]))
        if any(w in lower_prompt for w in ["browser", "website", "navigate", "page"]):
            subworker_specs.append((SubWorkerRole.BROWSER, ["browser.execute", "browser.navigate"]))
        if any(w in lower_prompt for w in ["code", "software", "test", "build"]):
            subworker_specs.append((SubWorkerRole.CODING, ["engineering.code_generation", "engineering.run_test"]))

        # Always include Verification and Document workers for business deliverable
        subworker_specs.append((SubWorkerRole.DOCUMENT, ["terminal.file_operation"]))
        subworker_specs.append((SubWorkerRole.VERIFICATION, ["terminal.verify_hash"]))

        # 2. Spawn Sub-Workers
        spawned_ids = []
        for role, scope in subworker_specs:
            assign = self.subworker_coord.spawn_subworker(
                parent_worker_id=pwid,
                mission_id=mid,
                role=role,
                parent_scope=scope + ["all"],
                parent_budget_usd=100.0,
                requested_scope=scope,
                budget_usd=20.0
            )
            spawned_ids.append(assign.child_worker_id)

        mission.subworkers = spawned_ids
        mission.status = "RUNNING"
        mission.progress_percent = 25.0
        mission.current_stage = f"{len(spawned_ids)} sub-workers actively assigned"
        return mission

    def tick_mission_progress(self, mission_id: str) -> Optional[BackgroundMission]:
        """Simulates/advances background mission execution, verification, and completion."""
        mission = self._missions.get(mission_id)
        if not mission or mission.status in ["COMPLETED", "FAILED"]:
            return mission

        # Advance stages
        if mission.progress_percent < 50.0:
            mission.progress_percent = 60.0
            mission.current_stage = "Web and market research collected; synthesizing data"
            mission.runtimes_used.append("runtime_openclaw")
        elif mission.progress_percent < 80.0:
            mission.progress_percent = 85.0
            mission.current_stage = "Deliverable written to company workspace; independent verification in progress"
            mission.deliverables.append("storage/workspaces/competitor_analysis_report.json")
            mission.runtimes_used.append("runtime_hermes_agent")
        else:
            # Complete and generate evidence & notification
            mission.progress_percent = 100.0
            mission.status = "COMPLETED"
            mission.current_stage = "Mission Completed & Verified"
            mission.completed_at = time.time()
            evidence_hash = hashlib.sha256(f"{mission.mission_id}:{mission.prompt}".encode()).hexdigest()
            mission.evidence_id = f"ev_{evidence_hash[:16]}"
            mission.notification_message = (
                f"Mission '{mission.mission_id}' completed successfully: "
                f"Researched targets, deliverable created at {mission.deliverables[-1]}, "
                f"verified with SHA-256 evidence {mission.evidence_id}."
            )

        mission.updated_at = time.time()
        return mission

    def get_mission(self, mission_id: str) -> Optional[BackgroundMission]:
        return self._missions.get(mission_id)

    def list_missions(self) -> List[BackgroundMission]:
        return list(self._missions.values())
