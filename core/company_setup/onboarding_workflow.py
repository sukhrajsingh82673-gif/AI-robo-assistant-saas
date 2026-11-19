"""Onboarding workflow for an existing company.

Runs on the same checkpointed runtime as the new-company build and projects the
same phase/log/gap shape, so the progress page and retry semantics are shared.

Honesty rules for this stage:

* Connecting and verifying sources, studying, diagnosing and acting all need a
  provider adapter. Every adapter is currently null, so the phase is recorded as
  ``SKIPPED`` with a reason and a gap. Nothing is read, no finding is invented
  and no write happens.
* The readiness score, the source inventory and the plan are real local work.
* The company only becomes ``OPERATIONAL`` when the run ends with no gaps. With
  null adapters that means ``NEEDS_ATTENTION``, which is the honest result.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.company_setup import readiness as readiness_module
from core.company_setup.build_workflow import CompanyBuildWorkflow, _add_gap, _log, _now, _set_phase
from core.company_setup.connections import get_adapter
from core.company_setup.sources import find_source
from core.db import db


class DiagnosisAdapter:
    """Null diagnosis provider. It never returns a finding."""

    provider_id = "diagnosis"
    available = False

    def unavailable_reason(self) -> str:
        return (
            "Diagnosis needs a connected source that has actually been read. "
            "No finding was invented to fill the gap."
        )


class CompanyOnboardingWorkflow(CompanyBuildWorkflow):
    """Existing-company onboarding, sharing the build projection."""

    RUN_TYPE = "ONBOARDING"
    DECISION_PHASE = "ACT"

    # ----------------------------------------------------------- inventory
    def _connection_rows(self) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM external_connections WHERE tenant_id = ? AND company_id = ? ORDER BY created_at ASC",
                (self.tenant_id, self.company_id),
            ).fetchall()
        return [dict(row) for row in rows]

    def _file_count(self) -> int:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM company_files WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, self.company_id),
            ).fetchone()
        return int((row["n"] if row else 0) or 0)

    def _source_state(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        source_id = str(connection.get("source_id") or connection.get("provider_id") or "custom")
        source = find_source(source_id) or {}
        skipped = bool(connection.get("skipped"))
        verified = bool(connection.get("verified_at"))
        status = "SKIPPED" if skipped else ("VERIFIED" if verified else "NEEDS_CHECK")
        return {
            "source_id": source_id,
            "name": connection.get("name") or source.get("name") or source_id,
            "status": status,
            "skipped": skipped,
            "skip_reason": connection.get("skip_reason") or "",
            "verified": verified,
            "classification": connection.get("classification") or source.get("category"),
            "requires_verification": bool(source.get("requires_verification")),
        }

    # -------------------------------------------------------------- phases
    def _phase_connect_verify(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        rows = self._connection_rows()
        state["sources"] = [self._source_state(row) for row in rows]

        live = [item for item in state["sources"] if not item["skipped"] and item["status"] != "SKIPPED"]
        skipped = [item for item in state["sources"] if item["skipped"]]
        unverified = [item for item in live if not item["verified"]]

        readiness = readiness_module.compute(record, rows, self._file_count())
        state["readiness"] = readiness

        for source in skipped:
            if not str(source.get("skip_reason") or "").strip():
                _add_gap(
                    state,
                    "CONNECT_VERIFY",
                    "skip_reason",
                    f"{source['name']} was skipped without a reason. Add one so the choice is clear.",
                    action="edit_source",
                )

        if not live and not skipped:
            _add_gap(
                state,
                "CONNECT_VERIFY",
                "sources",
                "Connect at least one source, or upload a file, before ZONATA can study the business.",
                action="connect",
            )
        elif not live:
            _add_gap(
                state,
                "CONNECT_VERIFY",
                "sources",
                "Every source was skipped. Nothing is connected, so nothing can be studied yet.",
                action="connect",
            )

        for source in unverified:
            _add_gap(
                state,
                "CONNECT_VERIFY",
                "verification",
                f"Ownership of {source['name']} is not confirmed yet. Nothing private is read until it is.",
                action="verify",
            )

        note = (
            f"{len(live)} connected · {len(live) - len(unverified)} verified · {len(skipped)} skipped"
        )
        _log(state, "CONNECT_VERIFY", "success" if live else "warning", f"Sources checked. {note}.")
        _log(
            state,
            "CONNECT_VERIFY",
            "info",
            f"Readiness is {readiness['score']} out of 100 ({readiness['band'].lower()}).",
        )
        _set_phase(state, "CONNECT_VERIFY", "DONE", note)
        return state

    def _phase_study(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        live = [item for item in state.get("sources") or [] if not item["skipped"]]
        study_sources: List[Dict[str, Any]] = []
        readable = 0

        for item in live:
            adapter = get_adapter(item["source_id"])
            if adapter.available:
                readable += 1
                study_sources.append({"source_id": item["source_id"], "read": True, "reason": ""})
            else:
                study_sources.append(
                    {
                        "source_id": item["source_id"],
                        "read": False,
                        "reason": adapter.unavailable_reason(),
                    }
                )

        file_count = self._file_count()
        state["study"] = {
            "sources": study_sources,
            "files": file_count,
            "read": readable > 0,
            "read_at": _now() if readable else None,
        }

        if not readable:
            if live:
                reason = (
                    "No provider adapter can read the connected sources yet, so nothing was read. "
                    "No data was guessed and no finding was invented."
                )
            else:
                reason = "No source is connected, so there was nothing to study."
            _set_phase(state, "STUDY", "SKIPPED", reason)
            _add_gap(state, "STUDY", "provider", reason, action="connect")
            _log(state, "STUDY", "warning", reason)
            return state

        _log(state, "STUDY", "success", f"Read {readable} connected source{'s' if readable != 1 else ''}.")
        _set_phase(state, "STUDY", "DONE", f"{readable} sources read")
        return state

    def _phase_diagnose(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        adapter = DiagnosisAdapter()
        study = state.get("study") or {}
        if not study.get("read"):
            reason = adapter.unavailable_reason()
            state["diagnosis"] = {
                "available": False,
                "findings": [],
                "reason": reason,
                "generated_at": _now(),
            }
            _set_phase(state, "DIAGNOSE", "SKIPPED", reason)
            _add_gap(state, "DIAGNOSE", "provider", reason, action="connect")
            _log(state, "DIAGNOSE", "warning", reason)
            return state

        # A real diagnosis provider would run here. None is configured, so the
        # phase still refuses to invent findings.
        reason = adapter.unavailable_reason()
        state["diagnosis"] = {
            "available": False,
            "findings": [],
            "reason": reason,
            "generated_at": _now(),
        }
        _set_phase(state, "DIAGNOSE", "SKIPPED", reason)
        _add_gap(state, "DIAGNOSE", "provider", reason, action="connect")
        _log(state, "DIAGNOSE", "warning", reason)
        return state

    def _phase_plan(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        readiness = state.get("readiness") or readiness_module.compute(record, self._connection_rows(), self._file_count())
        workstreams: List[Dict[str, str]] = []
        for check in (readiness.get("reasons") or [])[:5]:
            workstreams.append(
                {
                    "id": f"raise_{check['id']}",
                    "title": f"Raise readiness: {check['label']}",
                    "detail": check["detail"],
                }
            )
        if not workstreams:
            workstreams.append(
                {
                    "id": "connect_real_source",
                    "title": "Connect a real provider",
                    "detail": "The profile is complete. Replace the null adapters with a real provider to read data.",
                }
            )

        state["plan"] = {
            "workstreams": workstreams,
            "next_steps": [
                "Connect at least one source and confirm ownership.",
                "Upload a CSV, spreadsheet or PDF if a connection is not possible yet.",
                "Review the plan with the person accountable for the company.",
            ],
            "readiness_score": readiness.get("score"),
            "created_at": _now(),
        }
        _log(state, "PLAN", "success", f"Plan drafted with {len(workstreams)} workstreams based on readiness gaps.")
        _set_phase(state, "PLAN", "DONE", f"{len(workstreams)} workstreams")
        return state

    def _phase_act(self, state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
        reason = (
            "No approved action is ready to run. Writes always need approval, and no action adapter "
            "is configured on this deployment. Nothing was changed."
        )
        _set_phase(state, "ACT", "SKIPPED", reason)
        _add_gap(state, "ACT", "approval", reason, action="approve")
        _log(state, "ACT", "warning", reason)
        return state
