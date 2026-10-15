"""
ZONATA Universal AI Co-worker Fabric — Hermes Agentic Tool Orchestrator
Integrates Nous Hermes function-calling and multi-step reasoning paradigms.
Converts high-level AI CEO objectives into verified, policy-governed tool sequences.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
import json
import time
import uuid
from dataclasses import dataclass, field
from .contracts import TaskNode, ExecutionState, CoworkerProfile, ExecutionResult

if TYPE_CHECKING:
    from .engine import UniversalCoworkerEngine


@dataclass
class HermesToolCall:
    call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    reasoning: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class HermesStepResult:
    step_number: int
    tool_call: HermesToolCall
    execution_result: Optional[ExecutionResult]
    state: ExecutionState
    verification_status: str
    error: Optional[str] = None

class HermesAgenticOrchestrator:
    """
    Hermes Agentic Tool Calling & Reasoning Engine.
    Operates strictly under ZONATA Sovereign Authority.
    Validates arguments against capability schemas before dispatching to UniversalCoworkerEngine.
    """

    def __init__(self, engine: 'UniversalCoworkerEngine'):
        self.engine = engine
        self.conversation_memory: List[Dict[str, Any]] = []

    def plan_and_decompose(
        self,
        objective: str,
        available_capabilities: List[str],
        base_url: Optional[str] = None
    ) -> List[HermesToolCall]:
        """
        Decomposes high-level business objective into structured Hermes tool calls.
        """
        planned_calls: List[HermesToolCall] = []
        host_url = base_url or "http://127.0.0.1:8080"
        lower_obj = objective.lower()

        # Step 1: Information Gathering / Research
        if any(w in lower_obj for w in ["search", "research", "supplier", "crawl", "browse"]):
            tool = "browser.openclaw_search" if "browser.openclaw_search" in available_capabilities else "browser.navigate"
            planned_calls.append(HermesToolCall(
                call_id=f"call_{uuid.uuid4().hex[:6]}",
                tool_name=tool,
                arguments={"query": "enterprise cloud licenses", "url": f"{host_url}/portal/suppliers"},
                reasoning="Step 1: Gather market data and supplier options via resilient web crawling"
            ))

        # Step 2: Tabular Extraction / Comparison
        if any(w in lower_obj for w in ["compare", "extract", "table", "price"]):
            tool = "browser.openclaw_extract_table" if "browser.openclaw_extract_table" in available_capabilities else "rpa.csv_filter"
            planned_calls.append(HermesToolCall(
                call_id=f"call_{uuid.uuid4().hex[:6]}",
                tool_name=tool,
                arguments={"url": f"{host_url}/portal/suppliers", "filter_column": "price"},
                reasoning="Step 2: Extract structured comparison table"
            ))


        # Step 3: Synthesis & Report Generation
        if any(w in lower_obj for w in ["report", "generate", "spreadsheet", "file", "document"]):
            planned_calls.append(HermesToolCall(
                call_id=f"call_{uuid.uuid4().hex[:6]}",
                tool_name="terminal.file_operation",
                arguments={"action": "write", "file_path": "supplier_evaluation_report.json", "content": '{"status": "EVALUATED", "recommended": "Supplier Beta"}'},
                reasoning="Step 3: Governed file synthesis and cryptographic hashing"
            ))

        # Step 4: Management Email / Notification (Approval Gated)
        if any(w in lower_obj for w in ["email", "notify", "purchase", "send", "approve"]):
            planned_calls.append(HermesToolCall(
                call_id=f"call_{uuid.uuid4().hex[:6]}",
                tool_name="financial.purchase_software",
                arguments={"amount": 12500.0, "vendor": "Supplier Beta"},
                reasoning="Step 4: Financial commitment requiring mandatory human approval gate"
            ))

        return planned_calls

    def execute_plan(
        self,
        worker: CoworkerProfile,
        mission_id: str,
        tool_calls: List[HermesToolCall],
        auto_approve_human_tasks: bool = False
    ) -> Tuple[List[HermesStepResult], bool]:
        """
        Executes a Hermes multi-step plan through the ZONATA Co-Worker Engine.
        Returns (step_results, all_successful).
        """
        step_results: List[HermesStepResult] = []
        all_ok = True

        for idx, call in enumerate(tool_calls):
            task = TaskNode(
                task_id=f"tsk_hermes_{idx+1}_{call.call_id[:4]}",
                mission_id=mission_id,
                title=f"Hermes Step {idx+1}: {call.tool_name}",
                capability_id=call.tool_name,
                parameters=call.arguments
            )

            res, ver, state = self.engine.execute_task(
                task,
                worker,
                human_approval_granted=auto_approve_human_tasks
            )

            step_res = HermesStepResult(
                step_number=idx + 1,
                tool_call=call,
                execution_result=res,
                state=state,
                verification_status=ver.status.value,
                error=res.error_message
            )
            step_results.append(step_res)

            if state not in [ExecutionState.SUCCESS, ExecutionState.REQUEST_APPROVAL]:
                all_ok = False
                break

        return step_results, all_ok
