"""ZONATA Agent Factory - Single-Agent Manufacturing Pipeline.

Implements the authoritative 7-stage manufacturing lifecycle:
- Stage 1: Requirements Intake & ARS Generation
- Stage 2: Architecture & Topology Design
- Stage 3: Spec Validation (Gate G01) & Deterministic Permission Calculation
- Stage 4: Code / Graph Assembly & Spec Compilation
- Stage 5: Independent Unit Verification (author_cases)
- Stage 6: Artifact Packaging & Detached Ed25519 Signing
- Stage 7: Staging Deployment & Runtime Activation

Supports:
- AT-01: Single agent end-to-end manufacturing
- AT-08: Checkpoint resumption on failed builds
- AT-11: Prevention of self-granted permissions
"""

from __future__ import annotations
import copy
import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agent_factory.ports import Principal, Resource, EvidenceEvent, BuildJob
from agent_factory.roles.requirement_analyst import RequirementAnalyst
from agent_factory.roles.architect import AgentArchitect
from agent_factory.roles.developer import AgentDeveloper
from agent_factory.roles.integration import AgentIntegrationEngineer
from agent_factory.spec.validator import SpecValidator
from agent_factory.spec.calculator import compute_permission_profile
from agent_factory.build.compiler import SpecCompiler
from agent_factory.build.governed_call import GovernedCallContext
from agent_factory.build.signer import sign_manifest, canonical


class BuildStageFailure(Exception):
    def __init__(self, stage: str, message: str, checkpoint: Dict[str, Any]):
        super().__init__(f"Stage '{stage}' failed: {message}")
        self.stage = stage
        self.message = message
        self.checkpoint = checkpoint


class SingleAgentPipeline:
    def __init__(
        self,
        db_conn_factory,
        authority_port,
        evidence_port,
        killswitch_port,
        runtime_port,
        signing_key: Optional[Ed25519PrivateKey] = None
    ):
        self.db_conn_factory = db_conn_factory
        self.authority = authority_port
        self.evidence = evidence_port
        self.killswitch = killswitch_port
        self.runtime = runtime_port
        self.signing_key = signing_key or Ed25519PrivateKey.generate()
        self.signing_key_id = "af_key_prod_01"

        self.analyst = RequirementAnalyst()
        self.architect = AgentArchitect()
        self.developer = AgentDeveloper()
        self.validator = SpecValidator()
        self.compiler = SpecCompiler()
        self.integration = AgentIntegrationEngineer()

    def _get_connection(self):
        return self.db_conn_factory()

    def run(
        self,
        request_id: str,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        resume_from_stage: Optional[str] = None,
        existing_checkpoint: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute single-agent manufacturing pipeline stages 1-7 with checkpointing."""
        checkpoint = copy.deepcopy(existing_checkpoint or {}) if "copy" in globals() else dict(existing_checkpoint or {})
        build_id = f"bld_{uuid.uuid4().hex[:12]}"
        now = time.time()

        with self._get_connection() as conn:
            # 1. Fetch request
            cur = conn.execute(
                "SELECT natural_language, template_ref, mode, budget_cap_usd FROM af_request WHERE tenant_id = ? AND id = ?",
                (tenant_id, request_id)
            )
            req_row = cur.fetchone()
            if not req_row:
                raise ValueError(f"Request '{request_id}' not found")
            nl_req, template_ref, mode, budget_cap = req_row

            # Register build record in af_build
            conn.execute("""
                INSERT INTO af_build (
                    id, tenant_id, status, worker_id,
                    sandbox_profile, stages, tokens_in, tokens_out,
                    cost_usd, started_at
                ) VALUES (?, ?, 'RUNNING', 'worker_af_t0', 'T0', ?, 0, 0, 0.0, ?)
            """, (build_id, tenant_id, json.dumps(["stage1"]), now))
            conn.commit()

        # STAGE 1: Intake & ARS Generation
        if "ars" not in checkpoint:
            ars = self.analyst.analyze(
                request_id=request_id,
                natural_language=nl_req,
                template_ref=template_ref,
                mode=mode
            )
            checkpoint["ars"] = ars
        else:
            ars = checkpoint["ars"]

        # STAGE 2: Architecture & Design
        if "design" not in checkpoint:
            design = self.architect.design(ars, tenant_id=tenant_id)
            checkpoint["design"] = design
        else:
            design = checkpoint["design"]

        # STAGE 3: Spec Drafting, Validation & Permission Calculation
        if "spec" not in checkpoint or "profile" not in checkpoint:
            raw_spec = self.developer.build_spec(ars, design)
            # Gate G01 validation
            val_res = self.validator.validate(raw_spec)
            if not val_res.is_valid:
                raise BuildStageFailure("stage3_validation", f"Spec validation failed: {val_res.errors}", checkpoint)

            # Deterministic permission calculation (AT-11 enforcement)
            profile = compute_permission_profile(
                requested_permissions=raw_spec.get("permissions", {}).get("requested", {}),
                requested_capabilities=raw_spec.get("capabilities", {}).get("requested", []),
                registry=self.validator.known_tools
            )
            checkpoint["spec"] = raw_spec
            checkpoint["profile"] = profile.to_dict()
        else:
            raw_spec = checkpoint["spec"]
            profile_dict = checkpoint["profile"]

        # STAGE 4: Graph Assembly & Compilation
        if "compiled" not in checkpoint:
            graph = self.compiler.compile(raw_spec)
            # Static check: ensure no unwrapped external nodes
            if not graph.verify_no_unwrapped_external_nodes():
                raise BuildStageFailure("stage4_compile", "Compiler invariant violated: unwrapped external nodes", checkpoint)
            checkpoint["compiled"] = True
        else:
            graph = self.compiler.compile(raw_spec)

        # STAGE 5: Unit Verification (author_cases)
        agent_meta = {
            "id": raw_spec["metadata"]["name"],
            "tenant_id": tenant_id,
            "company_id": company_id,
            "principal_id": f"agt.{raw_spec['metadata']['name']}"
        }
        g_ctx = GovernedCallContext(
            killswitch_port=self.killswitch,
            authority_port=self.authority,
            evidence_port=self.evidence,
            origin_principal=principal_id
        )
        passed, unit_results = self.integration.verify_author_cases(graph, raw_spec, g_ctx, agent_meta)
        if not passed:
            raise BuildStageFailure("stage5_unit_test", f"Unit verification failed: {unit_results}", checkpoint)
        checkpoint["unit_tests"] = unit_results

        # STAGE 6: Artifact Packaging & Detached Ed25519 Signing
        agent_id = f"agt_{uuid.uuid4().hex[:12]}"
        version_id = f"agv_{uuid.uuid4().hex[:12]}"
        manifest = {
            "agent_id": agent_id,
            "name": raw_spec["metadata"]["name"],
            "version": raw_spec["metadata"]["version"],
            "category": raw_spec["metadata"]["category"],
            "risk_tier": raw_spec["metadata"]["risk_tier"],
            "tenant_id": tenant_id,
            "company_id": company_id,
            "spec_sha256": hashlib.sha256(canonical(raw_spec)).hexdigest(),
            "permission_profile": checkpoint["profile"],
            "built_at": time.time()
        }
        signed_manifest = sign_manifest(self.signing_key, manifest, self.signing_key_id)
        package_body = {
            "manifest": manifest,
            "signature": signed_manifest,
            "spec": raw_spec
        }
        package_bytes = canonical(package_body)
        package_sha256 = hashlib.sha256(package_bytes).hexdigest()

        # Persist in af_artifact and af_agent / af_agent_version
        with self._get_connection() as conn:
            # Insert agent root
            conn.execute("""
                INSERT OR IGNORE INTO af_agent (
                    id, tenant_id, company_id, slug, display_name,
                    role_title, category, owner_principal_id, agent_principal_id,
                    template_name, lifecycle, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)
            """, (
                agent_id, tenant_id, company_id, raw_spec["metadata"]["name"],
                raw_spec["metadata"]["display_name"], raw_spec["role"]["title"],
                raw_spec["metadata"]["category"], principal_id, f"agt.{agent_id}",
                raw_spec["metadata"].get("template"), time.time(), time.time()
            ))

            # Insert agent version
            raw_spec_json = json.dumps(raw_spec)
            spec_sha256 = hashlib.sha256(raw_spec_json.encode("utf-8")).hexdigest()
            cap_profile_json = json.dumps(raw_spec.get("capabilities", {}))
            conn.execute("""
                INSERT INTO af_agent_version (
                    id, tenant_id, agent_id, semver, spec, spec_sha256,
                    capability_profile, permission_profile, risk_tier, build_id,
                    package_artifact_id, package_sha256, status, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'BUILT', ?, ?)
            """, (
                version_id, tenant_id, agent_id, raw_spec["metadata"]["version"],
                raw_spec_json, spec_sha256, cap_profile_json, json.dumps(checkpoint["profile"]),
                raw_spec["metadata"]["risk_tier"], build_id,
                f"art_{version_id}", package_sha256, principal_id, time.time()
            ))

            # Insert artifact
            conn.execute("""
                INSERT INTO af_artifact (
                    id, tenant_id, kind, sha256, size_bytes, storage_uri,
                    signature, signing_key_id, created_by, created_at
                ) VALUES (?, ?, 'agent_package', ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"art_{version_id}", tenant_id, package_sha256, len(package_bytes),
                f"storage://artifacts/{agent_id}/{version_id}.json",
                signed_manifest["signature"], signed_manifest["signing_key_id"],
                principal_id, time.time()
            ))

            # Update build status to SUCCEEDED and link agent_version_id
            stages = ["stage1_ars", "stage2_design", "stage3_validate", "stage4_compile", "stage5_unit", "stage6_package", "stage7_deploy"]
            conn.execute("""
                UPDATE af_build
                SET status = 'SUCCEEDED', finished_at = ?, stages = ?, cost_usd = 0.15, agent_version_id = ?
                WHERE id = ?
            """, (time.time(), json.dumps(stages), version_id, build_id))

            conn.commit()

        # STAGE 7: Staging Deployment
        deploy_job = BuildJob(
            build_id=build_id,
            request_id=request_id,
            tenant_id=tenant_id,
            agent_version_id=version_id,
            stages=stages,
            status="BUILT"
        )
        deploy_res = self.runtime.deploy(deploy_job, "staging")

        # Record evidence in EvidenceLedger
        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="agent_build",
            subject_id=build_id,
            event_type="agent.built",
            actor=principal_id,
            payload_hashes={
                "agent_id": agent_id,
                "version_id": version_id,
                "package_sha256": package_sha256,
                "signature": signed_manifest["signature"][:16]
            },
            timestamp=time.time(),
            tenant_id=tenant_id
        ))

        return {
            "build_id": build_id,
            "agent_id": agent_id,
            "agent_version_id": version_id,
            "status": "BUILT",
            "staging_deployed": deploy_res.get("status") == "ok",
            "evidence_id": ev_id,
            "package_sha256": package_sha256,
            "checkpoint": checkpoint
        }
