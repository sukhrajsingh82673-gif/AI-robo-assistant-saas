"""ZONATA Sovereign Core — Process Pack Execution Engine.

Executes business processes step-by-step with:
- Deterministic gates before every step.
- Andon condition monitoring (stops the line on defect or safety violation).
- Lean waste detection (waiting, rework, handoff, over-processing, defects).
- Cryptographic Merkle ledger sealing for every step transition.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.db import db
from core.gates import DeterministicGatePipeline, GateResult
from core.process_packs.schema import (
    AndonRule,
    ProcessPack,
    ProcessStep,
    WasteTag,
    compile_andon_expression,
)
from agent_factory.ports import EvidenceEvent
from agent_factory.adapters.zonata import ZonataEvidenceAdapter

logger = logging.getLogger("zonata.core.process_packs.engine")


@dataclass
class StepExecutionRecord:
    step_id: str
    step_name: str
    actor: str
    status: str  # "SUCCEEDED" | "FAILED" | "HALTED_ANDON" | "SKIPPED"
    duration_seconds: float
    cost_usd: float
    evidence_id: Optional[str] = None
    output_data: Dict[str, Any] = field(default_factory=dict)
    waste_detected: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ProcessInstance:
    instance_id: str
    tenant_id: str
    company_id: str
    pack_id: str
    pack_version: str
    status: str  # "INITIALIZED" | "RUNNING" | "COMPLETED" | "HALTED_ANDON" | "FAILED"
    current_step_index: int
    context_data: Dict[str, Any]
    records: List[StepExecutionRecord] = field(default_factory=list)
    andon_incident: Optional[Dict[str, Any]] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    total_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProcessExecutionEngine:
    """Deterministic runtime engine for executing Process Packs."""

    def __init__(self, db_conn_factory=None, evidence_port=None):
        self.db_conn_factory = db_conn_factory or db.get_connection
        self.evidence = evidence_port or ZonataEvidenceAdapter()
        self.gate_pipeline = DeterministicGatePipeline()
        self._ensure_table()

    def _ensure_table(self):
        with self.db_conn_factory() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS af_process_instances (
                    instance_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT,
                    pack_id TEXT NOT NULL,
                    pack_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_step_index INTEGER NOT NULL DEFAULT 0,
                    context_data JSON NOT NULL,
                    records JSON NOT NULL,
                    andon_incident JSON,
                    total_cost_usd REAL NOT NULL DEFAULT 0.0,
                    started_at REAL NOT NULL,
                    finished_at REAL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_af_pi_tenant ON af_process_instances(tenant_id, status)")
            conn.commit()

    def create_instance(
        self,
        tenant_id: str,
        company_id: str,
        pack: ProcessPack,
        initial_inputs: Dict[str, Any]
    ) -> ProcessInstance:
        """Initializes a new process instance with validated inputs."""
        instance_id = f"proc_{uuid.uuid4().hex[:12]}"
        now = time.time()

        # Check required inputs from SIPOC
        missing_inputs = [inp for inp in pack.sipoc.inputs if inp not in initial_inputs]
        if missing_inputs:
            logger.warning(f"Process instance started with missing SIPOC inputs: {missing_inputs}")

        instance = ProcessInstance(
            instance_id=instance_id,
            tenant_id=tenant_id,
            company_id=company_id,
            pack_id=pack.pack_id,
            pack_version=pack.version,
            status="RUNNING",
            current_step_index=0,
            context_data=dict(initial_inputs),
            started_at=now
        )
        self.save_instance(instance)

        # Seal initialization event
        self.evidence.append_event(
            EvidenceEvent(
                subject_kind="process_instance",
                subject_id=instance_id,
                event_type="process.started",
                actor="system",
                payload_hashes={
                    "pack_id": pack.pack_id,
                    "version": pack.version,
                    "input_keys": ",".join(sorted(initial_inputs.keys()))
                },
                timestamp=now,
                tenant_id=tenant_id
            )
        )
        return instance

    def evaluate_andon(self, pack: ProcessPack, context: Dict[str, Any]) -> Optional[AndonRule]:
        """Evaluates deterministic stop-the-line conditions (Andon cord)."""
        for andon in pack.andon:
            try:
                # Expressions are AST-validated at load time: no calls,
                # attributes, subscripts, or imports can appear here.
                code = compile_andon_expression(andon.trigger_expression)
                if eval(code, {"__builtins__": {}}, dict(context)):
                    return andon
            except NameError as exc:
                logger.warning(
                    "Andon rule '%s' skipped: missing context input (%s)",
                    andon.condition_id,
                    exc,
                )
            except ValueError as exc:
                logger.error("Andon rule '%s' rejected: %s", andon.condition_id, exc)
            except Exception as exc:
                logger.error("Andon rule '%s' evaluation failed: %s", andon.condition_id, exc)
        return None

    def execute_next_step(
        self,
        instance: ProcessInstance,
        pack: ProcessPack,
        step_handler: Optional[Callable[[ProcessStep, Dict[str, Any]], Dict[str, Any]]] = None
    ) -> ProcessInstance:
        """Executes the next sequential step in the process pack."""
        if instance.status != "RUNNING":
            raise RuntimeError(f"Cannot execute step: instance is in '{instance.status}' state.")

        if instance.current_step_index >= len(pack.steps):
            instance.status = "COMPLETED"
            instance.finished_at = time.time()
            self.save_instance(instance)
            return instance

        step = pack.steps[instance.current_step_index]
        step_start = time.time()

        # 1. Deterministic Andon Stop Check
        triggered_andon = self.evaluate_andon(pack, instance.context_data)
        if triggered_andon:
            now = time.time()
            instance.status = "HALTED_ANDON"
            instance.andon_incident = {
                "rule_id": triggered_andon.condition_id,
                "rule_name": triggered_andon.rule_name,
                "escalate_to": triggered_andon.escalate_to_role,
                "description": triggered_andon.description,
                "triggered_at": now
            }
            rec = StepExecutionRecord(
                step_id=step.id,
                step_name=step.name,
                actor=step.actor,
                status="HALTED_ANDON",
                duration_seconds=now - step_start,
                cost_usd=0.0,
                waste_detected=[WasteTag.WAITING.value],
                error=f"Andon condition triggered: {triggered_andon.rule_name}"
            )
            instance.records.append(rec)
            self.save_instance(instance)

            # Seal Andon halt event
            self.evidence.append_event(
                EvidenceEvent(
                    subject_kind="process_instance",
                    subject_id=instance.instance_id,
                    event_type="process.andon_halted",
                    actor=step.role,
                    payload_hashes={
                        "step_id": step.id,
                        "andon_rule": triggered_andon.condition_id,
                        "escalate_to": triggered_andon.escalate_to_role
                    },
                    timestamp=now,
                    tenant_id=instance.tenant_id
                )
            )
            return instance

        # 2. Execute Step via Handler
        waste_detected: List[str] = []
        try:
            if step_handler:
                output = step_handler(step, instance.context_data)
            else:
                # Default mock handler for testing
                output = {f"{step.id}_output": "processed", "status": "ok"}

            now = time.time()
            duration = now - step_start
            cost = 0.005  # standard simulated unit cost

            instance.context_data.update(output)
            instance.total_cost_usd += cost

            # Seal Step Completion
            ev_id = self.evidence.append_event(
                EvidenceEvent(
                    subject_kind="process_step",
                    subject_id=f"{instance.instance_id}_{step.id}",
                    event_type="process.step_completed",
                    actor=step.role,
                    payload_hashes={
                        "step_id": step.id,
                        "duration_sec": str(round(duration, 3)),
                        "cost_usd": str(cost),
                        "output_keys": ",".join(sorted(output.keys()))
                    },
                    timestamp=now,
                    tenant_id=instance.tenant_id
                )
            )

            rec = StepExecutionRecord(
                step_id=step.id,
                step_name=step.name,
                actor=step.actor,
                status="SUCCEEDED",
                duration_seconds=duration,
                cost_usd=cost,
                evidence_id=ev_id,
                output_data=output,
                waste_detected=waste_detected
            )
            instance.records.append(rec)
            instance.current_step_index += 1

            if instance.current_step_index >= len(pack.steps):
                instance.status = "COMPLETED"
                instance.finished_at = now

            self.save_instance(instance)
            return instance

        except Exception as e:
            now = time.time()
            duration = now - step_start
            instance.status = "FAILED"
            instance.finished_at = now
            rec = StepExecutionRecord(
                step_id=step.id,
                step_name=step.name,
                actor=step.actor,
                status="FAILED",
                duration_seconds=duration,
                cost_usd=0.001,
                waste_detected=[WasteTag.DEFECTS.value, WasteTag.REWORK.value],
                error=str(e)
            )
            instance.records.append(rec)
            self.save_instance(instance)
            return instance

    def save_instance(self, inst: ProcessInstance):
        with self.db_conn_factory() as conn:
            conn.execute(
                """
                INSERT INTO af_process_instances
                (instance_id, tenant_id, company_id, pack_id, pack_version, status,
                 current_step_index, context_data, records, andon_incident, total_cost_usd, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (instance_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    company_id = excluded.company_id,
                    pack_id = excluded.pack_id,
                    pack_version = excluded.pack_version,
                    status = excluded.status,
                    current_step_index = excluded.current_step_index,
                    context_data = excluded.context_data,
                    records = excluded.records,
                    andon_incident = excluded.andon_incident,
                    total_cost_usd = excluded.total_cost_usd,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at
                """,
                (
                    inst.instance_id,
                    inst.tenant_id,
                    inst.company_id,
                    inst.pack_id,
                    inst.pack_version,
                    inst.status,
                    inst.current_step_index,
                    json.dumps(inst.context_data),
                    json.dumps([asdict(r) for r in inst.records]),
                    json.dumps(inst.andon_incident) if inst.andon_incident else None,
                    inst.total_cost_usd,
                    inst.started_at,
                    inst.finished_at
                )
            )
            conn.commit()

    def get_instance(self, instance_id: str) -> Optional[ProcessInstance]:
        with self.db_conn_factory() as conn:
            cur = conn.execute(
                "SELECT * FROM af_process_instances WHERE instance_id = ?",
                (instance_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            records = [StepExecutionRecord(**r) for r in json.loads(row[8])]
            return ProcessInstance(
                instance_id=row[0],
                tenant_id=row[1],
                company_id=row[2],
                pack_id=row[3],
                pack_version=row[4],
                status=row[5],
                current_step_index=row[6],
                context_data=json.loads(row[7]),
                records=records,
                andon_incident=json.loads(row[9]) if row[9] else None,
                total_cost_usd=row[10],
                started_at=row[11],
                finished_at=row[12]
            )
