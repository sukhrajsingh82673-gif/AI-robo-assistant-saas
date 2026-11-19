"""Company Build workflow.

Runs a Company Build on the existing governed, checkpointed LangGraph runtime
(``core/durable_workflow_runtime.py``) and projects the phase state onto
``company_build_runs`` so the overview can show real progress, a plain-language
log and what is waiting on the user.

Honesty rules for this stage:

* Phases that have a real local implementation run for real: intake, plan,
  legal drafts, verification and the operational transition.
* Phases that need an external provider (market research, website/base-system
  building) use adapters. When the adapter reports that no provider is
  configured, the phase is recorded as ``SKIPPED`` with a reason and a gap; it
  is never marked ``DONE`` and no findings or assets are invented.
* The company only becomes ``OPERATIONAL`` when the verification phase has no
  gaps. Otherwise it moves to ``NEEDS_ATTENTION`` with the gaps listed.
* A failed run keeps its checkpoint. Retrying creates a fresh attempt with the
  same graph definition; the previous run stays in the history.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.company_setup import audit
from core.company_setup.permissions import Principal
from core.company_setup.schema import ensure_schema
from core.company_setup.status import CompanyStatus, InvalidTransition, normalize_status, validate_transition
from core.db import db
from core.durable_workflow_runtime import (
    NodeType,
    StateGraph,
    WorkflowState,
    get_workflow_runtime,
)

# ---------------------------------------------------------------------------
# Phase catalogue
# ---------------------------------------------------------------------------

PHASE_SPECS: Dict[str, List[Dict[str, str]]] = {
    "NEW": [
        {"id": "INTAKE", "label": "Understanding your brief", "description": "Reading the company brief and checking the essentials."},
        {"id": "RESEARCH", "label": "Researching the market", "description": "Market and competitor research from a connected provider."},
        {"id": "PLAN", "label": "Planning the company", "description": "Turning the brief into a build plan and first workstreams."},
        {"id": "BUILD", "label": "Building base systems", "description": "Website, storefronts and base systems from the builder adapter."},
        {"id": "LEGAL_PACK", "label": "Drafting the legal pack", "description": "Draft registration checklist, privacy policy and terms."},
        {"id": "VERIFY", "label": "Checking everything", "description": "Verifying what exists and listing what is still missing."},
        {"id": "OPERATIONAL", "label": "Going operational", "description": "Marking the company operational once verification passes."},
    ],
    "EXISTING": [
        {"id": "CONNECT_VERIFY", "label": "Connecting and verifying sources", "description": "Read-only connections and ownership checks."},
        {"id": "STUDY", "label": "Studying the business", "description": "Reading connected systems without writing back."},
        {"id": "DIAGNOSE", "label": "Diagnosing what to improve", "description": "Findings with evidence and confidence."},
        {"id": "PLAN", "label": "Planning the fixes", "description": "Turning findings into a governed plan."},
        {"id": "ACT", "label": "Acting on approved work", "description": "Executing only approved actions."},
        {"id": "OPERATIONAL", "label": "Going operational", "description": "Marking the company operational."},
    ],
}

PHASE_LABELS = {spec["id"]: spec["label"] for specs in PHASE_SPECS.values() for spec in specs}

TERMINAL_BAD_PHASE_STATES = {"DONE", "SKIPPED", "FAILED"}

START_MESSAGES = {
    "INTAKE": "Reading your brief and checking that nothing essential is missing.",
    "RESEARCH": "Looking for a connected research provider.",
    "PLAN": "Turning the brief into a build plan.",
    "BUILD": "Looking for a connected website and systems builder.",
    "LEGAL_PACK": "Preparing draft legal documents for your review.",
    "VERIFY": "Checking what exists and what is still missing.",
    "OPERATIONAL": "Finishing the build.",
}


# ---------------------------------------------------------------------------
# Adapters (honest null implementations until a provider is configured)
# ---------------------------------------------------------------------------

class NullAdapter:
    """Base class for a provider that is not configured in this deployment."""

    kind = "provider"
    provider_id = "provider"

    @property
    def available(self) -> bool:
        return False

    def unavailable_reason(self) -> str:
        return "No provider is connected for this step yet."

    def run(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "provider": self.provider_id,
            "available": False,
            "simulated": False,
            "reason": self.unavailable_reason(),
            "read_at": None,
        }


class ResearchAdapter(NullAdapter):
    provider_id = "research"

    def unavailable_reason(self) -> str:
        return "Market research needs a connected research provider. Nothing was researched or invented."


class WebsiteBuilderAdapter(NullAdapter):
    provider_id = "website_builder"

    def unavailable_reason(self) -> str:
        return "Base systems need a connected website builder. Nothing was built."


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


def _log(state: Dict[str, Any], phase: str, level: str, message: str) -> None:
    entries = state.setdefault("log", [])
    entries.append({"at": _now(), "phase": phase, "level": level, "message": message})
    # Keep the projected log bounded; the workflow event history is complete.
    if len(entries) > 200:
        del entries[:-200]


def _set_phase(state: Dict[str, Any], phase_id: str, phase_state: str, note: str = "") -> None:
    for phase in state.get("phases", []):
        if phase["id"] == phase_id:
            phase["state"] = phase_state
            if note:
                phase["note"] = note
            if phase_state in ("DONE", "SKIPPED", "FAILED") and not phase.get("finished_at"):
                phase["finished_at"] = _now()
            break
    state["phase"] = phase_id


def _add_gap(state: Dict[str, Any], phase: str, kind: str, message: str, action: str = "retry") -> None:
    state.setdefault("gaps", []).append({
        "phase": phase,
        "kind": kind,
        "message": message,
        "action": action,
    })


class CompanyBuildWorkflow:
    """One company's build, executed on the shared durable runtime.

    The base class implements the NEW-company graph. Existing companies reuse
    the same runtime, projection and retry semantics through
    :class:`core.company_setup.onboarding_workflow.CompanyOnboardingWorkflow`,
    which only adds its own phase handlers.
    """

    #: Stored on the build row and shown by the progress page.
    RUN_TYPE = "BUILD"
    #: The phase whose decision decides whether the company may go operational.
    DECISION_PHASE = "VERIFY"

    def __init__(self, tenant_id: str, company_id: str, principal: Principal):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.principal = principal
        ensure_schema()

    # ------------------------------------------------------------- type
    def _company_type(self) -> str:
        record = self._company() or {}
        return str(record.get("company_type") or "NEW").upper()

    def _specs(self) -> List[Dict[str, str]]:
        specs = PHASE_SPECS.get(self._company_type())
        return specs or PHASE_SPECS["NEW"]

    # ------------------------------------------------------------- records
    def _company(self) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM companies WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, self.company_id),
            ).fetchone()
        return dict(row) if row else None

    def _latest_run(self) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM company_build_runs WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (self.tenant_id, self.company_id),
            ).fetchone()
        return dict(row) if row else None

    def _attempt_number(self) -> int:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM company_build_runs WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, self.company_id),
            ).fetchone()
        return int((row["n"] if row else 0) or 0)

    # --------------------------------------------------------------- graph
    def _build_graph(self, record: Dict[str, Any], attempt: int) -> Tuple[str, str, Any]:
        specs = self._specs()
        graph = StateGraph({"phases": list, "log": list, "gaps": list})

        for spec in specs:
            phase_id = spec["id"]

            def handler(state, phase_id=phase_id):
                return self._run_phase(phase_id, state)

            graph.add_node(
                phase_id,
                handler,
                node_type=NodeType.AGENT,
                retry_policy={"max_retries": 0, "classification": "NO_AUTOMATIC_RETRY"},
                timeout_seconds=120.0,
                metadata={"phase": phase_id, "label": spec["label"]},
            )

        for left, right in zip(specs, specs[1:]):
            graph.add_edge(left["id"], right["id"])

        # The decision phase decides whether the company may go operational.
        # When gaps exist the run ends there instead of pretending.
        decision_id = self.DECISION_PHASE
        operational_id = "OPERATIONAL"
        if any(spec["id"] == decision_id for spec in specs) and any(spec["id"] == operational_id for spec in specs):
            graph.edges = [e for e in graph.edges if not (e["source"] == decision_id and e["target"] == operational_id)]
            graph.add_conditional_edges(
                decision_id,
                lambda state: "OPERATIONAL" if not state.get("gaps") else "END",
                {"OPERATIONAL": operational_id, "END": NodeType.END},
            )

        graph.set_entry_point(specs[0]["id"])
        graph.set_finish_point(operational_id if specs[-1]["id"] == operational_id else specs[-1]["id"])

        workflow_id = f"wfb_{self.company_id}_{attempt}_{uuid.uuid4().hex[:4]}"
        compiled = graph.compile()
        runtime = get_workflow_runtime(self.tenant_id)
        runtime.register_compiled_graph(
            workflow_id,
            compiled,
            {
                "company_id": self.company_id,
                "name": f"Company Build — {record.get('name') or self.company_id}",
                "owner": self.principal.user_id,
                "risk_level": "SAFE",
                "timeout": 3600.0,
            },
        )
        return workflow_id, runtime, compiled

    # ------------------------------------------------------------- phases
    def _run_phase(self, phase_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        record = self._company()
        if not record:
            raise ValueError("The company no longer exists")

        _set_phase(state, phase_id, "RUNNING")
        for phase in state.get("phases", []):
            if phase["id"] == phase_id and not phase.get("started_at"):
                phase["started_at"] = _now()
                break
        _log(state, phase_id, "info", START_MESSAGES.get(phase_id, f"Working on {PHASE_LABELS.get(phase_id, phase_id)}."))

        if phase_id == "INTAKE":
            return self._phase_intake(state, record)
        if phase_id == "RESEARCH":
            return self._phase_research(state, record)
        if phase_id == "PLAN":
            return self._phase_plan(state, record)
        if phase_id == "BUILD":
            return self._phase_build(state, record)
        if phase_id == "LEGAL_PACK":
            return self._phase_legal(state, record)
        if phase_id == "VERIFY":
            return self._phase_verify(state, record)
        if phase_id == "OPERATIONAL":
            _log(state, phase_id, "info", "All checks passed. Marking the company operational.")
            _set_phase(state, phase_id, "DONE", "Operational")
            state["operational"] = True
            return state

        handler = getattr(self, f"_phase_{phase_id.lower()}", None)
        if handler is not None:
            return handler(state, record)

        raise ValueError(f"Unknown build phase: {phase_id}")

    def _phase_intake(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        name = str(record.get("name") or "").strip()
        description = str(record.get("description") or "").strip()
        title = str(record.get("title") or "").strip()
        missing = [label for label, value in (("name", name), ("title", title), ("description", description)) if not value]
        if missing:
            raise ValueError(f"Brief is incomplete: {', '.join(missing)}")

        budget_amount = record.get("budget_amount")
        state["brief"] = {
            "name": name,
            "title": title,
            "description": description,
            "industry": record.get("industry"),
            "country": record.get("country"),
            "website": record.get("website") or "",
            "target_customers": record.get("target_customers") or "",
            "budget": {
                "amount": budget_amount,
                "currency": record.get("budget_currency") or record.get("currency") or "INR",
            },
            "timeline": record.get("timeline") or "",
            "notes": record.get("setup_notes") or "",
            "read_at": _now(),
        }
        _log(state, "INTAKE", "success", f"Brief confirmed for {name}.")
        if state["brief"]["country"] or state["brief"]["industry"]:
            _log(state, "INTAKE", "info", f"Country: {state['brief']['country'] or 'not set'} · Industry: {state['brief']['industry'] or 'not set'}.")
        _set_phase(state, "INTAKE", "DONE", "Brief confirmed")
        return state

    def _phase_research(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        adapter = ResearchAdapter()
        result = adapter.run(state.get("brief") or {})
        state["research"] = result
        if not result.get("available"):
            reason = result.get("reason") or adapter.unavailable_reason()
            _set_phase(state, "RESEARCH", "SKIPPED", reason)
            _add_gap(state, "RESEARCH", "provider", reason)
            _log(state, "RESEARCH", "warning", reason)
            return state
        _set_phase(state, "RESEARCH", "DONE", "Research completed")
        _log(state, "RESEARCH", "success", "Research completed from the connected provider.")
        return state

    def _phase_plan(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        brief = state.get("brief") or {}
        description = str(brief.get("description") or "").lower()
        workstreams = [
            {"id": "positioning", "title": "Positioning and offer", "detail": "Name the offer, the buyer and the proof."},
            {"id": "systems", "title": "Base systems", "detail": "Site, contact capture and one source of truth for customers."},
            {"id": "legal", "title": "Legal and compliance", "detail": "Registration checklist, privacy policy and terms."},
        ]
        if brief.get("target_customers"):
            workstreams[0]["detail"] = f"Start from the stated customers: {brief['target_customers']}."
        if "b2b" in description or "business" in description:
            workstreams.insert(1, {"id": "sales", "title": "Sales motion", "detail": "Define the first outbound and follow-up step."})
        state["plan"] = {
            "workstreams": workstreams,
            "next_steps": [
                "Review the draft legal pack with a professional.",
                "Connect a research provider to replace the skipped research phase.",
                "Connect a website builder to build the base systems.",
            ],
            "created_at": _now(),
        }
        _log(state, "PLAN", "success", f"Plan drafted with {len(workstreams)} workstreams.")
        _set_phase(state, "PLAN", "DONE", f"{len(workstreams)} workstreams")
        return state

    def _phase_build(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        adapter = WebsiteBuilderAdapter()
        result = adapter.run(state.get("brief") or {})
        state["build"] = result
        if not result.get("available"):
            reason = result.get("reason") or adapter.unavailable_reason()
            _set_phase(state, "BUILD", "SKIPPED", reason)
            _add_gap(state, "BUILD", "provider", reason)
            _log(state, "BUILD", "warning", reason)
            return state
        _set_phase(state, "BUILD", "DONE", "Base systems built")
        _log(state, "BUILD", "success", "Base systems built by the connected provider.")
        return state

    def _phase_legal(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        items = self._ensure_legal_items(record)
        state["legal_items"] = items
        _log(
            state,
            "LEGAL_PACK",
            "success",
            f"Prepared {len(items)} legal draft{'s' if len(items) != 1 else ''}. Each is a draft to verify with a qualified professional.",
        )
        _set_phase(state, "LEGAL_PACK", "DONE", f"{len(items)} drafts")
        return state

    def _phase_verify(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        phases = {phase["id"]: phase for phase in state.get("phases", [])}
        legal_items = state.get("legal_items")
        if legal_items is None:
            legal_items = self._legal_count()
        checks = [
            {"id": "brief", "label": "Brief is complete", "ok": bool(state.get("brief"))},
            {"id": "plan", "label": "Plan exists", "ok": bool(state.get("plan"))},
            {"id": "research", "label": "Research completed", "ok": phases.get("RESEARCH", {}).get("state") == "DONE"},
            {"id": "systems", "label": "Base systems built", "ok": phases.get("BUILD", {}).get("state") == "DONE"},
            {"id": "legal", "label": "Legal drafts prepared", "ok": len(legal_items or []) > 0},
        ]
        state["checks"] = checks
        state["waiting_on"] = list(state.get("gaps") or [])
        for check in checks:
            tone = "success" if check["ok"] else "warning"
            _log(state, "VERIFY", tone, f"{check['label']}: {'yes' if check['ok'] else 'no'}.")

        if state["waiting_on"]:
            _set_phase(state, "VERIFY", "DONE", "Built with gaps")
            _log(
                state,
                "VERIFY",
                "warning",
                "Waiting on you: " + "; ".join(gap["message"] for gap in state["waiting_on"]),
            )
        else:
            _set_phase(state, "VERIFY", "DONE", "All checks passed")
        return state

    # ------------------------------------------------------------- helpers
    def _legal_count(self) -> int:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM company_legal_items WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, self.company_id),
            ).fetchone()
        return int((row["n"] if row else 0) or 0)

    def _ensure_legal_items(self, record: Dict[str, Any]) -> List[str]:
        country = str(record.get("country") or "IN").upper()
        if country == "IN":
            items = [
                ("Company incorporation checklist", "Ministry of Corporate Affairs (MCA)"),
                ("GST registration checklist", "Goods and Services Tax Network"),
                ("Privacy policy", "Data protection"),
                ("Terms of service", "Consumer and contract law"),
            ]
        else:
            items = [
                ("Company registration checklist", "Local company registry"),
                ("Privacy policy", "Data protection"),
                ("Terms of service", "Consumer and contract law"),
            ]

        existing: Dict[str, str] = {}
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT name FROM company_legal_items WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, self.company_id),
            ).fetchall()
            existing = {str(row["name"]) for row in rows}
            now = _now()
            for name, authority in items:
                if name in existing:
                    continue
                conn.execute(
                    """
                    INSERT INTO company_legal_items (
                        item_id, tenant_id, company_id, name, authority, status,
                        instructions, draft_disclaimer, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'DRAFT', ?, ?, ?, ?)
                    """,
                    (
                        f"leg_{uuid.uuid4().hex[:12]}",
                        self.tenant_id,
                        self.company_id,
                        name,
                        authority,
                        "Draft for review. A qualified professional must verify it before use.",
                        "Draft: verify with a qualified professional",
                        now,
                        now,
                    ),
                )
            conn.commit()
        return [name for name, _ in items]

    # --------------------------------------------------------------- start
    def start(self, attempt: Optional[int] = None) -> Dict[str, Any]:
        record = self._company()
        if not record:
            raise ValueError("The company no longer exists")

        specs = self._specs()
        attempt = attempt or self._attempt_number()
        phases = [dict(spec, state="PENDING", note="", started_at=None, finished_at=None) for spec in specs]
        workflow_id, runtime, _ = self._build_graph(record, attempt)
        inputs = {"phases": phases, "log": [], "gaps": []}

        try:
            result = runtime.start_workflow(
                workflow_id,
                inputs,
                context={"company_id": self.company_id},
            )
        except Exception as exc:  # a start failure must be visible, never swallowed
            self._project_failure(str(exc), workflow_id, None)
            return {"started": False, "reason": str(exc), "workflow_id": workflow_id}

        projected = self._project(result, workflow_id, attempt)
        return {
            "started": True,
            "workflow_id": workflow_id,
            "run_id": result.get("run_id"),
            "status": result.get("status"),
            "build": projected,
        }

    def retry(self) -> Dict[str, Any]:
        latest = self._latest_run()
        if latest and str(latest.get("phase_state")) == "RUNNING":
            return {"started": False, "reason": "The build is already running."}
        attempt = self._attempt_number() + 1
        now = _now()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO company_build_runs (
                    build_id, tenant_id, company_id, run_type, workflow_id, workflow_run_id,
                    phase, phase_state, progress, estimate_min_days, estimate_max_days,
                    started_at, finished_at, failure_reason, log, created_at, updated_at
                ) VALUES (?, ?, ?, ?, NULL, NULL, ?, 'PENDING', 0.0, 1, 3, NULL, NULL, NULL, ?, ?, ?)
                """,
                (
                    f"bld_{uuid.uuid4().hex[:12]}",
                    self.tenant_id,
                    self.company_id,
                    self.RUN_TYPE,
                    self._specs()[0]["id"],
                    _json({"phases": [], "log": [], "gaps": [], "attempt": attempt}),
                    now,
                    now,
                ),
            )
            conn.commit()
        audit.record_event(
            self.tenant_id,
            self.company_id,
            self.principal.user_id,
            self.principal.role,
            "company.build_retried",
            {"attempt": attempt, "previous_build_id": (latest or {}).get("build_id")},
        )
        return self.start(attempt=attempt)

    # ----------------------------------------------------------- projection
    def _project(self, result: Dict[str, Any], workflow_id: str, attempt: int) -> Dict[str, Any]:
        state = result.get("state") or {}
        phases = state.get("phases") or []
        completed = [p for p in phases if p.get("state") == "DONE"]
        skipped = [p for p in phases if p.get("state") == "SKIPPED"]
        gaps = state.get("waiting_on") if state.get("waiting_on") is not None else state.get("gaps") or []
        total = len(phases) or len(self._specs())
        progress = round(len(completed) / total, 4) if total else 0.0
        success = result.get("status") == WorkflowState.COMPLETED
        now = _now()

        if not success:
            phase = state.get("phase") or self._specs()[0]["id"]
            phase_state = "FAILED"
            failure_reason = result.get("error") or "The build stopped unexpectedly."
            target_status = None
            finished_at = now
        elif gaps:
            phase = self.DECISION_PHASE
            phase_state = "DONE_WITH_GAPS"
            failure_reason = None
            target_status = CompanyStatus.NEEDS_ATTENTION
            finished_at = now
        else:
            phase = "OPERATIONAL"
            phase_state = "DONE"
            failure_reason = None
            target_status = CompanyStatus.OPERATIONAL
            finished_at = now

        log_payload = {
            "phases": phases,
            "log": state.get("log") or [],
            "gaps": gaps,
            "checks": state.get("checks") or [],
            "brief": state.get("brief") or {},
            "plan": state.get("plan") or {},
            "research": state.get("research") or {},
            "build": state.get("build") or {},
            "study": state.get("study") or {},
            "diagnosis": state.get("diagnosis") or {},
            "sources": state.get("sources") or [],
            "readiness": state.get("readiness") or {},
            "attempt": attempt,
        }

        latest = self._latest_run()
        build_id = (latest or {}).get("build_id") or f"bld_{uuid.uuid4().hex[:12]}"
        with db.get_connection() as conn:
            if latest:
                conn.execute(
                    """
                    UPDATE company_build_runs SET
                        workflow_id = ?, workflow_run_id = ?, phase = ?, phase_state = ?,
                        progress = ?, started_at = COALESCE(started_at, ?), finished_at = ?,
                        failure_reason = ?, log = ?, updated_at = ?
                    WHERE build_id = ? AND tenant_id = ?
                    """,
                    (
                        workflow_id,
                        result.get("run_id"),
                        phase,
                        phase_state,
                        progress,
                        now,
                        finished_at,
                        failure_reason,
                        _json(log_payload),
                        now,
                        build_id,
                        self.tenant_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO company_build_runs (
                        build_id, tenant_id, company_id, run_type, workflow_id, workflow_run_id,
                        phase, phase_state, progress, estimate_min_days, estimate_max_days,
                        started_at, finished_at, failure_reason, log, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 3, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        build_id,
                        self.tenant_id,
                        self.company_id,
                        self.RUN_TYPE,
                        workflow_id,
                        result.get("run_id"),
                        phase,
                        phase_state,
                        progress,
                        now,
                        finished_at,
                        failure_reason,
                        _json(log_payload),
                        now,
                        now,
                    ),
                )
            if target_status:
                self._transition_company(target_status, conn)
            conn.commit()

        if phase_state == "FAILED":
            audit.record_event(
                self.tenant_id,
                self.company_id,
                self.principal.user_id,
                self.principal.role,
                "company.build_failed",
                {"workflow_id": workflow_id, "reason": failure_reason, "attempt": attempt},
            )
        elif gaps:
            audit.record_event(
                self.tenant_id,
                self.company_id,
                self.principal.user_id,
                self.principal.role,
                "company.build_done_with_gaps",
                {"workflow_id": workflow_id, "gaps": [gap.get("phase") for gap in gaps], "attempt": attempt},
            )
        else:
            audit.record_event(
                self.tenant_id,
                self.company_id,
                self.principal.user_id,
                self.principal.role,
                "company.build_completed",
                {"workflow_id": workflow_id, "attempt": attempt},
            )
        return self._serialize_run(self._latest_run())

    def _project_failure(self, reason: str, workflow_id: str, run_id: Optional[str]) -> None:
        now = _now()
        latest = self._latest_run()
        payload = {"phases": [], "log": [{"at": now, "phase": "INTAKE", "level": "error", "message": reason}], "gaps": []}
        with db.get_connection() as conn:
            if latest:
                conn.execute(
                    "UPDATE company_build_runs SET phase_state = 'FAILED', failure_reason = ?, workflow_id = ?, "
                    "workflow_run_id = ?, log = ?, updated_at = ? WHERE build_id = ?",
                    (reason, workflow_id, run_id, _json(payload), now, latest["build_id"]),
                )
            conn.commit()

    def _transition_company(self, target: str, conn: Any) -> None:
        row = conn.execute(
            "SELECT status FROM companies WHERE tenant_id = ? AND company_id = ?",
            (self.tenant_id, self.company_id),
        ).fetchone()
        current = normalize_status((row["status"] if row else "") or "")
        if current == target:
            return
        try:
            validate_transition(current, target)
        except InvalidTransition:
            return
        conn.execute(
            "UPDATE companies SET status = ?, updated_at = ? WHERE tenant_id = ? AND company_id = ?",
            (target, _now(), self.tenant_id, self.company_id),
        )

    def _serialize_run(self, record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not record:
            return None
        meta = _load_json(record.get("log"), {})
        return {
            "build_id": record.get("build_id"),
            "company_id": record.get("company_id"),
            "run_type": record.get("run_type"),
            "workflow_id": record.get("workflow_id"),
            "workflow_run_id": record.get("workflow_run_id"),
            "phase": record.get("phase"),
            "phase_state": record.get("phase_state"),
            "progress": record.get("progress"),
            "attempt": meta.get("attempt", 1),
            "estimate": {
                "min_days": record.get("estimate_min_days"),
                "max_days": record.get("estimate_max_days"),
                "is_estimate": True,
            },
            "started_at": record.get("started_at"),
            "finished_at": record.get("finished_at"),
            "failure_reason": record.get("failure_reason"),
            "phases": meta.get("phases") or [],
            "log": meta.get("log") or [],
            "gaps": meta.get("gaps") or [],
            "waiting_on": meta.get("gaps") or [],
            "checks": meta.get("checks") or [],
            "brief": meta.get("brief") or {},
            "plan": meta.get("plan") or {},
            "study": meta.get("study") or {},
            "diagnosis": meta.get("diagnosis") or {},
            "sources": meta.get("sources") or [],
            "readiness": meta.get("readiness") or {},
            "updated_at": record.get("updated_at"),
        }


def _json(value: Any) -> str:
    import json

    return json.dumps(value, separators=(",", ":"), default=str)


def _load_json(value: Any, default: Any) -> Any:
    import json

    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default
