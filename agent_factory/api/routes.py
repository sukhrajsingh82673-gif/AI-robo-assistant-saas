"""
ZONATA Agent Factory — API Layer (Phase 2 & Phase 3 Routes)
Mounted at /api/v8/agent-factory/...
Implements RFC 9457 error contracts, idempotency, tenant validation, and evidence tracking.
"""

from __future__ import annotations
import os
import time
import json
import uuid
import hashlib
from typing import Dict, List, Optional, Any, Tuple

from agent_factory.ports import Principal, Resource, Decision, EvidenceEvent
from agent_factory.adapters.zonata import (
    ZonataAuthorityAdapter, ZonataEvidenceAdapter,
    ZonataKillSwitchAdapter, ZonataPolicyAdapter
)
from agent_factory.domain.transition import (
    transition, TransitionContext, InvalidTransitionError, TransitionForbiddenError
)
from agent_factory.control.orchestrator import DbQueueOrchestrator
from agent_factory.templates.loader import TemplateLoader, TemplateManifest
from agent_factory.roles.requirement_analyst import RequirementAnalyst
from agent_factory.spec.validator import SpecValidator
from agent_factory.spec.calculator import compute_permission_profile
from agent_factory.control.planner import (
    plan, next_ready, propagate_failure, batch_verdict, compile_team_manifest, PlanError
)
from agent_factory.control.quotas import (
    reserve_quota, release_quota, get_quota_status
)

# Feature Flag
def is_af_enabled() -> bool:
    return os.environ.get("AF_ENABLED", "1") in ("1", "true", "TRUE", "yes")


class AgentFactoryRouter:
    def __init__(self, db_conn_factory=None, ledger_file: Optional[str] = None):
        self.db_conn_factory = db_conn_factory
        self.authority = ZonataAuthorityAdapter()
        self.evidence = ZonataEvidenceAdapter(ledger_file=ledger_file)
        self.killswitch = ZonataKillSwitchAdapter()
        self.policy = ZonataPolicyAdapter()
        self.orchestrator = DbQueueOrchestrator(db_conn_factory=db_conn_factory)
        self.template_loader = TemplateLoader()
        self.requirement_analyst = RequirementAnalyst(self.template_loader)
        self.validator = SpecValidator()

    def _get_connection(self):
        if self.db_conn_factory:
            return self.db_conn_factory()
        from core.db import db
        return db.get_connection()

    def _error(self, code: str, title: str, status: int, detail: str, req_id: str) -> Dict[str, Any]:
        return {
            "type": f"https://zonata.ai/errors/{code.lower()}",
            "title": title,
            "status": status,
            "code": code,
            "detail": detail,
            "correlation_id": req_id,
            "errors": []
        }

    def dispatch(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body_bytes: bytes,
        auth_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
        req_id = headers.get("X-Request-ID") or f"req_af_{uuid.uuid4().hex[:10]}"
        res_headers = {"X-Request-ID": req_id}

        # Health & Readiness routes do not require authentication or feature flags
        if path in ("/api/v8/agent-factory/health", "/health"):
            return 200, {
                "status": "HEALTHY",
                "service": "zonata.agent_factory",
                "version": "1.0.0",
                "af_enabled": is_af_enabled(),
                "time": time.time()
            }, res_headers

        if path in ("/api/v8/agent-factory/ready", "/ready"):
            return 200, {
                "ready": True,
                "af_enabled": is_af_enabled(),
                "orchestrator": "DbQueueOrchestrator",
                "sandbox_tiers_available": ["T0"],
                "real_model_profile_required": False
            }, res_headers

        if not is_af_enabled():
            return 503, self._error("AF-DISABLED", "Agent Factory Disabled", 503, "Feature flag AF_ENABLED is false", req_id), res_headers

        # Authentication check
        auth_context = auth_context or {}
        tenant_id = auth_context.get("tenant_id") or headers.get("X-Tenant-ID")
        principal_id = auth_context.get("user_id") or auth_context.get("principal_id") or headers.get("X-User-ID")
        company_id = headers.get("X-Company-ID") or auth_context.get("company_id")

        if not tenant_id or not principal_id:
            return 401, self._error("AF-UNAUTHORIZED", "Unauthorized", 401, "Valid credentials required", req_id), res_headers

        if not company_id:
            return 404, self._error("AF-TENANT-MISMATCH", "Company Not Found", 404, "X-Company-ID header required", req_id), res_headers

        principal = Principal(
            principal_id=principal_id,
            tenant_id=tenant_id,
            company_id=company_id,
            kind="ai_employee" if "emp." in principal_id else "human_owner",
            roles=["owner"] if "owner" in principal_id else ["employee"]
        )

        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            return 400, self._error("AF-VALIDATION", "Invalid JSON", 400, "Request body must be valid JSON", req_id), res_headers

        # ----------------- ROUTE 1: POST /requests -----------------
        if method == "POST" and path == "/api/v8/agent-factory/requests":
            idempotency_key = headers.get("Idempotency-Key")
            if not idempotency_key:
                return 400, self._error("AF-VALIDATION", "Missing Idempotency-Key", 400, "Idempotency-Key header is required", req_id), res_headers

            mode = body.get("mode", "single")
            nl = body.get("natural_language", "")
            if len(nl) < 10 or len(nl) > 20000:
                return 422, self._error("AF-VALIDATION", "Invalid Specification Length", 422, "natural_language must be 10-20000 characters", req_id), res_headers

            budget_cap = body.get("budget_cap_usd", 10.0)
            now = time.time()
            request_id = f"req_af_{uuid.uuid4().hex[:12]}"

            with self._get_connection() as conn:
                # Check idempotency replay
                cur = conn.execute("SELECT id, status, natural_language FROM af_request WHERE tenant_id = ? AND idempotency_key = ?", (tenant_id, idempotency_key))
                existing = cur.fetchone()
                if existing:
                    if existing[2] == nl:
                        res_headers["Idempotent-Replay"] = "true"
                        return 200, {"request_id": existing[0], "status": existing[1], "replayed": True}, res_headers
                    return 409, self._error("AF-IDEMPOTENCY-MISMATCH", "Idempotency Conflict", 409, "Different payload with same Idempotency-Key", req_id), res_headers

                # Check killswitch
                if self.killswitch.is_killed("TENANT", tenant_id, tenant_id):
                    return 423, self._error("AF-KILLED", "Tenant Execution Killed", 423, "KillSwitch is active for this tenant", req_id), res_headers

                # Compute risk tier
                risk_tier = self.policy.evaluate_risk([], [], [])

                # Insert request in initial state
                conn.execute("""
                    INSERT INTO af_request (
                        id, tenant_id, company_id, requester_principal_id, requester_kind,
                        mode, natural_language, status, risk_tier, budget_cap_usd,
                        spent_usd, idempotency_key, correlation_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'REQUESTED', ?, ?, 0.0, ?, ?, ?, ?)
                """, (
                    request_id, tenant_id, company_id, principal.principal_id, principal.kind,
                    mode, nl, risk_tier, budget_cap, idempotency_key, req_id, now, now
                ))

                # Transition helper records evidence and lifecycle event
                t_ctx = TransitionContext(
                    tenant_id=tenant_id,
                    principal=principal,
                    conn=conn,
                    authority_port=self.authority,
                    evidence_port=self.evidence,
                    killswitch_port=self.killswitch,
                    meta={"correlation_id": req_id}
                )
                evidence_id = transition(
                    t_ctx, "request", request_id, "ANALYSING",
                    reason="Initial manufacturing intake",
                    expect_from="REQUESTED",
                    payload_hashes={"nl_sha256": hashlib.sha256(nl.encode()).hexdigest()}
                )
                conn.commit()

            res_headers["X-Evidence-Id"] = evidence_id
            res_headers["Location"] = f"/api/v8/agent-factory/requests/{request_id}"
            return 202, {
                "request_id": request_id,
                "status": "ANALYSING",
                "risk_tier": risk_tier,
                "evidence_id": evidence_id
            }, res_headers

        # ----------------- ROUTE 2: GET /requests -----------------
        if method == "GET" and path == "/api/v8/agent-factory/requests":
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT id, mode, status, risk_tier, budget_cap_usd, spent_usd, created_at FROM af_request WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 50",
                    (tenant_id,)
                )
                items = [
                    {"id": r[0], "mode": r[1], "status": r[2], "risk_tier": r[3], "budget_cap_usd": r[4], "spent_usd": r[5], "created_at": r[6]}
                    for r in cur.fetchall()
                ]
            return 200, {"items": items}, res_headers

        # ----------------- ROUTE 3: POST /requests/{id}/clarifications -----------------
        if method == "POST" and "/clarifications" in path:
            req_target_id = path.replace("/api/v8/agent-factory/requests/", "").replace("/clarifications", "")
            answers = body.get("answers", {})
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id, status, natural_language FROM af_request WHERE tenant_id = ? AND id = ?", (tenant_id, req_target_id))
                row = cur.fetchone()
                if not row:
                    return 404, self._error("AF-NOT-FOUND", "Request Not Found", 404, f"Request {req_target_id} not found", req_id), res_headers

                # Record clarification evidence
                ev_id = self.evidence.append_event(EvidenceEvent(
                    subject_kind="request",
                    subject_id=req_target_id,
                    event_type="request.clarification_answered",
                    actor=principal.principal_id,
                    payload_hashes={"answers_sha256": hashlib.sha256(json.dumps(answers).encode()).hexdigest()},
                    timestamp=time.time(),
                    tenant_id=tenant_id
                ))
            res_headers["X-Evidence-Id"] = ev_id
            return 200, {
                "request_id": req_target_id,
                "clarifications_recorded": True,
                "evidence_id": ev_id
            }, res_headers

        # ----------------- ROUTE 4: POST /requests/{id}/analyze -----------------
        if method == "POST" and path.endswith("/analyze"):
            req_target_id = path.replace("/api/v8/agent-factory/requests/", "").replace("/analyze", "")
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id, natural_language, template_ref, mode, status FROM af_request WHERE tenant_id = ? AND id = ?", (tenant_id, req_target_id))
                row = cur.fetchone()
                if not row:
                    return 404, self._error("AF-NOT-FOUND", "Request Not Found", 404, f"Request {req_target_id} not found", req_id), res_headers

                # Run RequirementAnalyst
                ars = self.requirement_analyst.analyze(
                    request_id=req_target_id,
                    natural_language=row[1],
                    template_ref=row[2],
                    mode=row[3]
                )

                # Persist ARS in af_requirement_spec
                now = time.time()
                ars_json = json.dumps(ars)
                ars_sha256 = hashlib.sha256(ars_json.encode("utf-8")).hexdigest()
                open_q = json.dumps(ars.get("clarifications_needed", []))
                conn.execute("""
                    INSERT INTO af_requirement_spec (
                        id, tenant_id, request_id, version, body,
                        body_sha256, authored_by, open_questions, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ars["id"], tenant_id, req_target_id, ars["version"], ars_json,
                    ars_sha256, principal.principal_id, open_q, now
                ))

                # Transition to DESIGNING or CLARIFYING
                target_state = "CLARIFYING" if ars["clarifications_needed"] else "DESIGNING"
                t_ctx = TransitionContext(
                    tenant_id=tenant_id,
                    principal=principal,
                    conn=conn,
                    authority_port=self.authority,
                    evidence_port=self.evidence,
                    killswitch_port=self.killswitch,
                    meta={"correlation_id": req_id}
                )
                evidence_id = transition(
                    t_ctx, "request", req_target_id, target_state,
                    reason="Requirement analysis complete",
                    expect_from=row[4],
                    payload_hashes={"ars_id": ars["id"], "risk": ars["risk_tier_inferred"]}
                )
                conn.commit()

            res_headers["X-Evidence-Id"] = evidence_id
            return 200, {
                "request_id": req_target_id,
                "ars": ars,
                "new_status": target_state,
                "evidence_id": evidence_id
            }, res_headers

        # ----------------- ROUTE 5: GET /requests/{id}/estimate -----------------
        if (method == "GET" or method == "POST") and path.endswith("/estimate"):
            req_target_id = path.replace("/api/v8/agent-factory/requests/", "").replace("/estimate", "")
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id, natural_language, risk_tier, budget_cap_usd FROM af_request WHERE tenant_id = ? AND id = ?", (tenant_id, req_target_id))
                row = cur.fetchone()
                if not row:
                    return 404, self._error("AF-NOT-FOUND", "Request Not Found", 404, f"Request {req_target_id} not found", req_id), res_headers

                risk = row[2] or "R1"
                token_est = 15000 if risk in ("R0", "R1") else 35000
                cost_est = 0.25 if risk in ("R0", "R1") else 0.85
                wall_clock_sec = 60 if risk in ("R0", "R1") else 180

                estimate = {
                    "request_id": req_target_id,
                    "estimated_tokens": token_est,
                    "estimated_cost_usd": cost_est,
                    "estimated_wall_clock_seconds": wall_clock_sec,
                    "sandbox_tier_required": "T0",
                    "quota_impact": {
                        "builds": 1,
                        "cost_usd": cost_est
                    }
                }
            return 200, estimate, res_headers

        # ----------------- ROUTE 2B: GET /requests/{id} -----------------
        if method == "GET" and path.startswith("/api/v8/agent-factory/requests/"):
            req_target_id = path.split("/")[-1]
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT id, mode, natural_language, status, risk_tier, budget_cap_usd, spent_usd, created_at, updated_at FROM af_request WHERE tenant_id = ? AND id = ?",
                    (tenant_id, req_target_id)
                )
                row = cur.fetchone()
                if not row:
                    return 404, self._error("AF-NOT-FOUND", "Request Not Found", 404, f"Request {req_target_id} not found", req_id), res_headers

                cur_lc = conn.execute(
                    "SELECT from_state, to_state, actor, reason, evidence_ledger_id, created_at FROM af_lifecycle_event WHERE tenant_id = ? AND subject_id = ? ORDER BY id ASC",
                    (tenant_id, req_target_id)
                )
                events = [
                    {"from": r[0], "to": r[1], "actor": r[2], "reason": r[3], "evidence_ledger_id": r[4], "at": r[5]}
                    for r in cur_lc.fetchall()
                ]

            return 200, {
                "request_id": row[0],
                "mode": row[1],
                "natural_language": row[2],
                "status": row[3],
                "risk_tier": row[4],
                "budget_cap_usd": row[5],
                "spent_usd": row[6],
                "created_at": row[7],
                "updated_at": row[8],
                "lifecycle_events": events
            }, res_headers

        # ----------------- ROUTE 13: GET /templates -----------------
        if method == "GET" and path == "/api/v8/agent-factory/templates":
            templates = self.template_loader.list_templates()
            return 200, {"items": templates}, res_headers

        # ----------------- ROUTE 14: GET /templates/{name} or /versions -----------------
        if method == "GET" and path.startswith("/api/v8/agent-factory/templates/"):
            parts = path.replace("/api/v8/agent-factory/templates/", "").split("/")
            tpl_name = parts[0]
            if len(parts) == 1:
                tpl = self.template_loader.resolve(tpl_name)
                if not tpl:
                    return 404, self._error("AF-NOT-FOUND", "Template Not Found", 404, f"Template {tpl_name} not found", req_id), res_headers
                return 200, tpl.to_dict(), res_headers
            elif len(parts) == 2 and parts[1] == "versions":
                tpl_versions = self.template_loader._templates.get(tpl_name, {})
                return 200, {"name": tpl_name, "versions": sorted(list(tpl_versions.keys()))}, res_headers
            elif len(parts) == 3 and parts[1] == "versions":
                ver = parts[2]
                tpl = self.template_loader._templates.get(tpl_name, {}).get(ver)
                if not tpl:
                    return 404, self._error("AF-NOT-FOUND", "Version Not Found", 404, f"Template {tpl_name}@{ver} not found", req_id), res_headers
                return 200, tpl.to_dict(), res_headers

        # ----------------- ROUTE 14B: POST /templates (Propose Template) -----------------
        if method == "POST" and path == "/api/v8/agent-factory/templates":
            tpl_manifest = TemplateManifest(body)
            if not tpl_manifest.name:
                return 422, self._error("AF-VALIDATION", "Invalid Template Manifest", 422, "Template name required", req_id), res_headers
            self.template_loader.register(tpl_manifest)
            ev_id = self.evidence.append_event(EvidenceEvent(
                subject_kind="template",
                subject_id=tpl_manifest.name,
                event_type="template.proposed",
                actor=principal.principal_id,
                payload_hashes={"name": tpl_manifest.name, "version": tpl_manifest.version},
                timestamp=time.time(),
                tenant_id=tenant_id
            ))
            res_headers["X-Evidence-Id"] = ev_id
            return 201, {
                "name": tpl_manifest.name,
                "version": tpl_manifest.version,
                "status": "DRAFT",
                "evidence_id": ev_id
            }, res_headers

        # ----------------- ROUTE 15: POST /templates/{name}/versions/{semver}/submit -----------------
        if method == "POST" and "/submit" in path and "/templates/" in path:
            parts = path.replace("/api/v8/agent-factory/templates/", "").replace("/submit", "").split("/versions/")
            tpl_name = parts[0]
            ver = parts[1] if len(parts) > 1 else "1.0.0"
            ev_id = self.evidence.append_event(EvidenceEvent(
                subject_kind="template",
                subject_id=f"{tpl_name}@{ver}",
                event_type="template.submitted_for_review",
                actor=principal.principal_id,
                payload_hashes={"name": tpl_name, "version": ver},
                timestamp=time.time(),
                tenant_id=tenant_id
            ))
            res_headers["X-Evidence-Id"] = ev_id
            return 200, {
                "name": tpl_name,
                "version": ver,
                "status": "IN_REVIEW",
                "evidence_id": ev_id
            }, res_headers

        # ----------------- ROUTE 16: POST /templates/{name}/versions/{semver}/publish -----------------
        if method == "POST" and "/publish" in path and "/templates/" in path:
            approval_id = body.get("approval_id")
            if not approval_id:
                return 400, self._error("AF-VALIDATION", "Approval Required", 400, "approval_id is mandatory to publish a template", req_id), res_headers
            parts = path.replace("/api/v8/agent-factory/templates/", "").replace("/publish", "").split("/versions/")
            tpl_name = parts[0]
            ver = parts[1] if len(parts) > 1 else "1.0.0"
            ev_id = self.evidence.append_event(EvidenceEvent(
                subject_kind="template",
                subject_id=f"{tpl_name}@{ver}",
                event_type="template.published",
                actor=principal.principal_id,
                payload_hashes={"name": tpl_name, "version": ver, "approval_id": approval_id},
                timestamp=time.time(),
                tenant_id=tenant_id
            ))
            res_headers["X-Evidence-Id"] = ev_id
            return 200, {
                "name": tpl_name,
                "version": ver,
                "status": "PUBLISHED",
                "evidence_id": ev_id
            }, res_headers

        # ----------------- ROUTE 7: POST /batches -----------------
        if method == "POST" and path == "/api/v8/agent-factory/batches":
            req_target_id = body.get("request_id")
            if not req_target_id:
                return 400, self._error("AF-VALIDATION", "Missing request_id", 400, "request_id is required", req_id), res_headers

            release_policy = body.get("release_policy", "atomic_team")
            items = body.get("items", [])
            raw_edges = body.get("edges", [])

            nodes = [it["agent_key"] for it in items if "agent_key" in it]
            if not nodes or len(nodes) > 500:
                return 422, self._error("AF-VALIDATION", "Invalid Agent Count", 422, "Batch must have between 1 and 500 agents", req_id), res_headers

            edges = [(e[0], e[1], e[2]) for e in raw_edges]
            try:
                batch_plan = plan(nodes, edges, max_parallel=body.get("max_parallel", 4))
            except PlanError as e:
                return 422, self._error("AF-DAG-INVALID", "DAG Validation Failed", 422, str(e), req_id), res_headers

            batch_id = f"bat_{uuid.uuid4().hex[:12]}"
            manifest_json = json.dumps({"nodes": nodes, "edges": raw_edges, "plan": batch_plan})
            manifest_sha256 = hashlib.sha256(manifest_json.encode()).hexdigest()
            now = time.time()

            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO af_batch (
                        id, tenant_id, company_id, request_id, release_policy,
                        agent_count, waves, dependency_graph, manifest_sha256,
                        status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PLANNED', ?, ?)
                """, (
                    batch_id, tenant_id, company_id, req_target_id, release_policy,
                    len(nodes), len(batch_plan["waves"]), json.dumps(raw_edges),
                    manifest_sha256, now, now
                ))

                for it in items:
                    key = it["agent_key"]
                    item_id = f"bit_{uuid.uuid4().hex[:12]}"
                    req_spec_id = it.get("requirement_spec_id") or f"ars_stub_{key}"
                    conn.execute("""
                        INSERT INTO af_batch_item (
                            id, tenant_id, batch_id, agent_key, role_title,
                            requirement_spec_id, depends_on, wave, status, attempts
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0)
                    """, (
                        item_id, tenant_id, batch_id, key, it.get("role_title", key),
                        req_spec_id, json.dumps(batch_plan["requires"].get(key, [])),
                        batch_plan["wave"].get(key, 0)
                    ))
                conn.commit()

            ev_id = self.evidence.append_event(EvidenceEvent(
                subject_kind="batch",
                subject_id=batch_id,
                event_type="batch.planned",
                actor=principal.principal_id,
                payload_hashes={"manifest_sha256": manifest_sha256, "agents": len(nodes)},
                timestamp=now,
                tenant_id=tenant_id
            ))
            res_headers["X-Evidence-Id"] = ev_id
            return 202, {
                "batch_id": batch_id,
                "status": "PLANNED",
                "waves": len(batch_plan["waves"]),
                "agent_count": len(nodes),
                "plan": batch_plan,
                "evidence_id": ev_id
            }, res_headers

        # ----------------- ROUTE 8: GET /batches/{id} -----------------
        if method == "GET" and path.startswith("/api/v8/agent-factory/batches/") and not path.endswith("/start") and not path.endswith("/cancel"):
            batch_id = path.replace("/api/v8/agent-factory/batches/", "").split("/")[0]
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT id, status, release_policy, agent_count, waves, dependency_graph, created_at FROM af_batch WHERE tenant_id = ? AND id = ?",
                    (tenant_id, batch_id)
                )
                b_row = cur.fetchone()
                if not b_row:
                    return 404, self._error("AF-NOT-FOUND", "Batch Not Found", 404, f"Batch {batch_id} not found", req_id), res_headers

                cur_it = conn.execute(
                    "SELECT agent_key, role_title, status, wave, attempts, last_error FROM af_batch_item WHERE tenant_id = ? AND batch_id = ?",
                    (tenant_id, batch_id)
                )
                items = [
                    {"agent_key": r[0], "role_title": r[1], "status": r[2], "wave": r[3], "attempts": r[4], "last_error": r[5]}
                    for r in cur_it.fetchall()
                ]

            return 200, {
                "batch_id": b_row[0],
                "status": b_row[1],
                "release_policy": b_row[2],
                "agent_count": b_row[3],
                "waves": b_row[4],
                "items": items
            }, res_headers

        # ----------------- ROUTE 9: POST /batches/{id}/start -----------------
        if method == "POST" and path.endswith("/start") and "/batches/" in path:
            batch_id = path.replace("/api/v8/agent-factory/batches/", "").replace("/start", "")
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id, status, release_policy, dependency_graph FROM af_batch WHERE tenant_id = ? AND id = ?", (tenant_id, batch_id))
                b_row = cur.fetchone()
                if not b_row:
                    return 404, self._error("AF-NOT-FOUND", "Batch Not Found", 404, f"Batch {batch_id} not found", req_id), res_headers

                # Atomic Quota Reservation
                if not reserve_quota(conn, tenant_id, "builds", amount=1.0):
                    return 429, self._error("AF-QUOTA-EXCEEDED", "Build Quota Exceeded", 429, "Tenant monthly build quota limit reached", req_id), res_headers

                # Update batch status to BUILDING
                conn.execute("UPDATE af_batch SET status = 'BUILDING', updated_at = ? WHERE id = ?", (time.time(), batch_id))

                # Fetch all items to compute next_ready
                cur_it = conn.execute("SELECT agent_key, status, wave, depends_on FROM af_batch_item WHERE batch_id = ?", (batch_id,))
                status_map = {}
                p_requires = {}
                p_wave = {}
                for r in cur_it.fetchall():
                    status_map[r[0]] = r[1]
                    p_wave[r[0]] = r[2]
                    p_requires[r[0]] = json.loads(r[3])

                p_struct = {"requires": p_requires, "wave": p_wave, "max_parallel": 4}
                ready_items = next_ready(p_struct, status_map)

                for rk in ready_items:
                    conn.execute("UPDATE af_batch_item SET status = 'BUILDING' WHERE batch_id = ? AND agent_key = ?", (batch_id, rk))

                conn.commit()

            return 200, {
                "batch_id": batch_id,
                "status": "BUILDING",
                "ready_items": ready_items
            }, res_headers

        # ----------------- ROUTE 10: POST /batches/{id}/cancel -----------------
        if method == "POST" and path.endswith("/cancel") and "/batches/" in path:
            batch_id = path.replace("/api/v8/agent-factory/batches/", "").replace("/cancel", "")
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id, status FROM af_batch WHERE tenant_id = ? AND id = ?", (tenant_id, batch_id))
                b_row = cur.fetchone()
                if not b_row:
                    return 404, self._error("AF-NOT-FOUND", "Batch Not Found", 404, f"Batch {batch_id} not found", req_id), res_headers

                conn.execute("UPDATE af_batch SET status = 'CANCELLED', updated_at = ? WHERE id = ?", (time.time(), batch_id))
                conn.execute("UPDATE af_batch_item SET status = 'KILLED' WHERE batch_id = ? AND status IN ('PENDING', 'READY', 'BUILDING')", (batch_id,))
                conn.commit()

            return 200, {"batch_id": batch_id, "status": "CANCELLED"}, res_headers

        # ----------------- ROUTE 11: POST /batches/{id}/items/{key}/retry -----------------
        if method == "POST" and "/items/" in path and path.endswith("/retry"):
            parts = path.replace("/api/v8/agent-factory/batches/", "").split("/")
            batch_id = parts[0]
            agent_key = parts[2]
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id, status, attempts FROM af_batch_item WHERE tenant_id = ? AND batch_id = ? AND agent_key = ?", (tenant_id, batch_id, agent_key))
                row = cur.fetchone()
                if not row:
                    return 404, self._error("AF-NOT-FOUND", "Batch Item Not Found", 404, f"Item {agent_key} not found", req_id), res_headers

                attempts = row[2]
                if attempts >= 3:
                    return 409, self._error("AF-CONFLICT-STATE", "Max Retries Exceeded", 409, f"Item {agent_key} has exceeded 3 attempts", req_id), res_headers

                conn.execute(
                    "UPDATE af_batch_item SET status = 'PENDING', attempts = attempts + 1 WHERE id = ?",
                    (row[0],)
                )
                conn.commit()

            return 200, {
                "batch_id": batch_id,
                "agent_key": agent_key,
                "status": "PENDING",
                "attempt": attempts + 1
            }, res_headers

        # ----------------- ROUTE 12: GET /jobs/{id} -----------------
        if method == "GET" and path.startswith("/api/v8/agent-factory/jobs/"):
            build_id = path.split("/")[-1]
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT id, status, worker_id, sandbox_profile, tokens_in, tokens_out, cost_usd, started_at, finished_at, error FROM af_build WHERE tenant_id = ? AND id = ?",
                    (tenant_id, build_id)
                )
                row = cur.fetchone()
                if not row:
                    return 404, self._error("AF-NOT-FOUND", "Job Not Found", 404, f"Build job {build_id} not found", req_id), res_headers

            return 200, {
                "build_id": row[0],
                "status": row[1],
                "worker_id": row[2],
                "sandbox_profile": row[3],
                "tokens": {"in": row[4], "out": row[5]},
                "cost_usd": row[6],
                "started_at": row[7],
                "finished_at": row[8],
                "error": row[9]
            }, res_headers

        # ----------------- ROUTE 36: POST /kill -----------------
        if method == "POST" and path == "/api/v8/agent-factory/kill":
            scope = body.get("scope", "AGENT").upper()
            target_id = body.get("target_id")
            reason = body.get("reason", "Administrative emergency halt")
            if not target_id:
                return 400, self._error("AF-VALIDATION", "Missing target_id", 400, "target_id required for kill switch", req_id), res_headers

            try:
                from core.distributed_coordination import coordination
                from core.killswitch_matrix import KillSwitchMatrix
                coordination.set_killswitch_state(scope, target_id, True, reason)
                ks = KillSwitchMatrix(tenant_id=tenant_id)
                ks.activate(scope, target_id, reason=reason, activated_by=principal.principal_id)
            except Exception as e:
                return 500, self._error("AF-INTERNAL", "KillSwitch Failure", 500, str(e), req_id), res_headers

            # Evidence append
            ev_id = self.evidence.append_event(EvidenceEvent(
                subject_kind="kill_switch",
                subject_id=target_id,
                event_type="kill_switch.activated",
                actor=principal.principal_id,
                payload_hashes={"scope": scope, "target_id": target_id, "reason": reason},
                timestamp=time.time(),
                tenant_id=tenant_id
            ))
            res_headers["X-Evidence-Id"] = ev_id
            return 200, {
                "killed": True,
                "scope": scope,
                "target_id": target_id,
                "reason": reason,
                "evidence_id": ev_id
            }, res_headers

        # ----------------- ROUTE 37: GET /quotas -----------------
        if method == "GET" and path == "/api/v8/agent-factory/quotas":
            period = time.strftime("%Y-%m")
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT metric, used, limit_value FROM af_quota_usage WHERE tenant_id = ? AND period = ?",
                    (tenant_id, period)
                )
                quotas = {r[0]: {"used": r[1], "limit": r[2]} for r in cur.fetchall()}
                if not quotas:
                    quotas = {
                        "builds": {"used": 0, "limit": 10},
                        "agents_published": {"used": 0, "limit": 50},
                        "cost_usd": {"used": 0.0, "limit": 25.0}
                    }
            return 200, {"tenant_id": tenant_id, "period": period, "quotas": quotas}, res_headers

        # ----------------- ROUTE 38: GET /evidence/{id} -----------------
        if method == "GET" and path.startswith("/api/v8/agent-factory/evidence/"):
            ev_query_id = path.split("/")[-1]
            try:
                from core.evidence_ledger import EvidenceLedger
                ledger = EvidenceLedger()
                record = ledger.get_evidence(ev_query_id)
                if not record:
                    return 404, self._error("AF-NOT-FOUND", "Evidence Not Found", 404, f"Evidence {ev_query_id} not found", req_id), res_headers
                return 200, record, res_headers
            except Exception as e:
                return 500, self._error("AF-INTERNAL", "Evidence Retrieval Error", 500, str(e), req_id), res_headers

        return 404, self._error("AF-NOT-FOUND", "Endpoint Not Found", 404, f"Route {method} {path} not found", req_id), res_headers
