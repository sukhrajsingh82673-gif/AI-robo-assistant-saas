#!/usr/bin/env python3
"""
ZONATA Sovereign Core — Step 3 Qualification Scenario: Hands (OpenCode Step 3K).

Validates all 10 hands components end-to-end:
1. Preflight & Capability Truth
2. Host Permission Model & Device Pairing (3B)
3. Desktop Perception & Control (3C)
4. Origin-Bound Credential Vault (3D)
5. Governed Browser Engine & Download Scanning (3E)
6. Anti-Evasion Policy & Rule 25 Deny-List (3F)
7. Remote View & Human Takeover (3G)
8. Research Hand & Search Provider (3H)
9. Terminal Governance & Safety Controls (3I)
10. Agent Factory Import Lane & Sandboxing (3J)
"""

from __future__ import annotations

import os
import sys
import time

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.db import db
from core.agent_import.license_gate import LicenseGate
from core.agent_import.sandbox_runner import SandboxSkillRunner
from core.agent_import.scanner import SkillImportScanner
from core.agent_import.types import (
    DangerousCodeRejectedError,
    LicenseViolationError,
)
from core.browser import BrowserDownloadPipeline, GovernedBrowserEngine
from core.browser.challenge_policy import ChallengePolicyEngine
from core.browser.rate_limiter import GovernedRateLimiter
from core.browser.types import ChallengeDetectionResult, ChallengeType
from core.capability_probe import probe_all_capabilities, probe_search
from core.host import (
    GrantMode,
    GrantScope,
    HostGrantManager,
    PairingManager,
    ZonataHostAgent,
)
from core.host.interaction import (
    InteractionPrimitive,
    OutOfGrantCoordinatesError,
)
from core.host.perception import (
    BoundingRect,
    DesktopPerceptionEngine,
)
from core.host.types import ensure_host_permission_tables
from core.ports.base import PortStatus
from core.ports.browser import browser_port
from core.ports.terminal import TerminalPort
from core.remote_view.takeover import HumanTakeoverManager
from core.remote_view.types import (
    AgentExecutionSuppressedError,
    RemoteTargetType,
    TakeoverHandbackAssertion,
    ViewportBounds,
)
from core.research.engine import ResearchEngine
from core.security.anti_evasion import (
    AntiEvasionViolationError,
    scan_repository_anti_evasion,
)
from core.terminal.classifier import CommandClassifier
from core.terminal.types import (
    CommandTier,
    DangerousCommandForbiddenError,
    HighImpactApprovalRequiredError,
)
from core.vault import (
    CredentialInjector,
    OriginBoundSecretVault,
    OriginMismatchError,
    SecretExportForbiddenError,
    SecretType,
)


def log_milestone(num: int, title: str) -> None:
    print(f"\n[{num:02d}/10] {title}")
    print("-" * 70)


def main() -> int:
    os.environ["ZONATA_TEST_MODE"] = "1"
    os.environ["ZONATA_STEP3_HOST_ENABLED"] = "1"
    os.environ["ZONATA_STEP3_BROWSER_ENABLED"] = "1"
    os.environ["ZONATA_STEP3_RESEARCH_ENABLED"] = "1"

    print("=" * 70)
    print("ZONATA SOVEREIGN CORE — STEP 3 QUALIFICATION SCENARIO (HANDS)")
    print("=" * 70)

    # Initialize and verify database readiness
    db.verify_readiness()
    ensure_host_permission_tables()
    with db.get_connection() as conn:
        OriginBoundSecretVault().ensure_tables(conn)

    # Seed baseline tenant and company for scenario
    with db.get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES (?, ?, ?)",
            ("ten_qual", "Tenant Step 3 Qualification", time.time()),
        )
        conn.execute(
            "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, created_at) VALUES (?, ?, ?, 'TECH', 'NEW', ?)",
            ("co_qual", "ten_qual", "Company Step 3 Qualification", time.time()),
        )
        if hasattr(conn, "commit"):
            conn.commit()

    # -------------------------------------------------------------------------
    # Milestone 1: Capability Truth Probe
    # -------------------------------------------------------------------------
    log_milestone(1, "Capability Truth Probes & Reality Table")
    probe_results = probe_all_capabilities()
    assert len(probe_results) == 18, f"Expected 18 capabilities, found {len(probe_results)}"
    active_count = len([r for r in probe_results.values() if r.status in (PortStatus.OK, PortStatus.SANDBOX)])
    print(f"Verified 18 standard capabilities probed. Status OK/SANDBOX: {active_count}/18.")

    # -------------------------------------------------------------------------
    # Milestone 2: Host Permission Model & Pairing (3B)
    # -------------------------------------------------------------------------
    log_milestone(2, "Host Agent Pairing & Sovereign Key Cryptography (Rule 23)")
    agent = ZonataHostAgent(device_name="Workstation-Qual", os_type="linux")
    agent.tenant_id = "ten_qual"
    agent.company_id = "co_qual"

    dev_id, code, expires_at = PairingManager.initiate_pairing(
        tenant_id="ten_qual",
        company_id="co_qual",
        owner_id="user_admin",
        device_name="Workstation-Qual",
        os_type="linux",
    )
    agent.device_id = dev_id

    pair_record = PairingManager.complete_pairing(
        device_id=dev_id,
        one_time_code=code,
        public_key=agent.public_key_hex,
        is_human_step_up_authenticated=True,
    )
    assert pair_record.pairing_status.value == "PAIRED"

    # Enforce grant validation on host
    grant = HostGrantManager.create_grant(
        device_id=dev_id,
        tenant_id="ten_qual",
        company_id="co_qual",
        scope_type=GrantScope.PERSONAL,
        mode=GrantMode.AUTONOMOUS_IN_SCOPE,
        allowed_apps=["code", "terminal"],
        allowed_folders=["/home/user/workspace"],
        allowed_domains=["github.com"],
        allowed_actions=["READ_ONLY", "GUI_INPUT"],
        created_by_principal_id="user_admin",
        created_by_principal_type="HUMAN",
        valid_duration_seconds=3600.0,
    )
    agent.sync_local_grant(grant)

    cmd_res = agent.execute_command({
        "app_name": "code",
        "action_type": "type",
        "action_class": "GUI_INPUT",
    })
    assert cmd_res["status"] == "SUCCESS"
    print("Host pairing verified with Ed25519 mutual authentication and local grant enforcement.")

    # -------------------------------------------------------------------------
    # Milestone 3: Desktop Perception & Control (3C)
    # -------------------------------------------------------------------------
    log_milestone(3, "Desktop Perception (A11y Tree First) & Interaction Dispatch")
    perception = DesktopPerceptionEngine()
    window_bounds = BoundingRect(x=100, y=200, width=1024, height=768)
    sample_a11y_data = {
        "window_id": "win_step3_qual",
        "window_title": "Sovereign IDE",
        "nodes": [
            {
                "node_id": "btn_run",
                "role": "button",
                "name": "Run Qualification",
                "bounds": {"x": 150, "y": 250, "width": 100, "height": 35},
                "is_interactive": True,
            },
            {
                "node_id": "input_api_key",
                "role": "password_field",
                "name": "API Key",
                "bounds": {"x": 150, "y": 300, "width": 250, "height": 30},
                "is_interactive": True,
                "is_password": True,
                "value": "super_secret_raw_key",
            },
        ],
    }

    tree = perception.parse_accessibility_snapshot(sample_a11y_data, window_bounds)
    pwd_node = tree.find_by_id("input_api_key")
    assert pwd_node is not None and pwd_node.value == "[MASKED_INPUT]"

    masked_frame = perception.mask_visual_frame({"window_id": tree.window_id}, tree)
    assert masked_frame["masked_status"] == "CREDENTIALS_REDACTED"
    assert "input_api_key" in [r["node_id"] for r in masked_frame["masked_regions"]]

    in_grant_action = agent.dispatch_gui_action(
        primitive=InteractionPrimitive.CLICK,
        window_bounds=window_bounds,
        relative_coords=(50, 50),
    )
    assert in_grant_action.executed

    try:
        agent.dispatch_gui_action(
            primitive=InteractionPrimitive.CLICK,
            window_bounds=window_bounds,
            relative_coords=(2000, 2000),
        )
        assert False, "Should have raised OutOfGrantCoordinatesError"
    except OutOfGrantCoordinatesError:
        pass
    print("Desktop perception accessibility hierarchy, password masking, and coordinate bounds enforced.")

    # -------------------------------------------------------------------------
    # Milestone 4: Origin-Bound Credential Vault (3D)
    # -------------------------------------------------------------------------
    log_milestone(4, "Origin-Bound Credential Vault (Rule 24)")
    vault = OriginBoundSecretVault()
    placeholder = vault.store_credential(
        tenant_id="ten_qual",
        company_id="co_qual",
        name="github_token",
        origin="https://github.com:443",
        secret="ghp_real_secret_token_1234567890",
        secret_type=SecretType.API_KEY,
    )
    assert placeholder.startswith("{{CREDENTIAL:")

    # Origin match succeeds
    _, token = vault.inject_credential(
        tenant_id="ten_qual",
        company_id="co_qual",
        name="github_token",
        target_url="https://github.com:443/api/v3/user",
    )
    assert token == "ghp_real_secret_token_1234567890"

    # Cross-origin rejected
    try:
        vault.inject_credential(
            tenant_id="ten_qual",
            company_id="co_qual",
            name="github_token",
            target_url="https://evil.example.com/api",
        )
        assert False, "Should have raised OriginMismatchError"
    except OriginMismatchError:
        pass

    # Secret export rejected (fail-closed)
    try:
        vault.export_secret()
        assert False, "Should have raised SecretExportForbiddenError"
    except SecretExportForbiddenError:
        pass
    print("Origin-bound credential late-binding injection and zero-export invariant verified.")

    # -------------------------------------------------------------------------
    # Milestone 5: Governed Browser Engine & Download Scanning (3E)
    # -------------------------------------------------------------------------
    log_milestone(5, "Governed Browser Engine & ClamAV Download Scanner (Rule 26, 32)")
    sandbox = browser_port.sandbox_provider
    sandbox.set_fixture_page(
        url="https://portal.example.corp:443/login",
        html="<html><head><title>Portal Login</title></head><body><h1>Enterprise Portal</h1></body></html>",
        title="Portal Login",
    )

    injector = CredentialInjector(vault=vault)
    browser_engine = GovernedBrowserEngine(vault=vault, injector=injector)
    nav_res = browser_engine.navigate("https://portal.example.corp:443/login", tenant_id="ten_qual", company_id="co_qual")
    assert nav_res.status == PortStatus.OK
    assert "<<<PAGE_CONTENT>>>" in nav_res.page_snapshot.content_delimited

    dl_pipeline = BrowserDownloadPipeline()
    dl_res = dl_pipeline.process_download("quarterly_report.pdf", b"%PDF-1.4 financial summary data", "ten_qual", "co_qual")
    assert dl_res.clamav_scanned
    assert not dl_res.is_infected
    assert not dl_res.is_executable
    print("Governed browser content delimiting and download pipeline verified.")

    # -------------------------------------------------------------------------
    # Milestone 6: Anti-Evasion Policy & Rate Limiting (3F)
    # -------------------------------------------------------------------------
    log_milestone(6, "Anti-Evasion Policy & Governed Backoff (Rule 25)")
    repo_violations = scan_repository_anti_evasion(REPO_ROOT)
    assert len(repo_violations) == 0, f"Found Rule 25 violations in repository: {repo_violations}"

    limiter = GovernedRateLimiter()
    try:
        limiter.request_proxy_rotation("http://proxy.internal:8080")
        assert False, "Should have raised AntiEvasionViolationError"
    except AntiEvasionViolationError:
        pass

    chal_res = ChallengePolicyEngine.evaluate_challenge(
        detection=ChallengeDetectionResult(
            has_challenge=True,
            challenge_type=ChallengeType.CLOUDFLARE_TURNSTILE,
            signatures_detected=["challenges.cloudflare.com"],
            masked_widget_bounds={"x": 50, "y": 50, "width": 300, "height": 65},
        ),
        task_id="task_qual_01",
        tenant_id="ten_qual",
        company_id="co_qual",
        url="https://github.com/login",
    )
    assert chal_res["status"] == "BLOCKED"
    print("Rule 25 AST repository hygiene, proxy rotation denial, and challenge halting verified.")

    # -------------------------------------------------------------------------
    # Milestone 7: Remote View & Human Takeover (3G)
    # -------------------------------------------------------------------------
    log_milestone(7, "Remote View Bounded Capture & Human Takeover (Rule 27, 28)")
    rv_mgr = HumanTakeoverManager()
    rv_sess = rv_mgr.create_session(
        tenant_id="ten_qual",
        company_id="co_qual",
        target_type=RemoteTargetType.BROWSER_TAB,
        target_id="tab_qual_1",
        viewport=ViewportBounds(x=0, y=0, width=1280, height=720),
    )
    rv_mgr.initiate_takeover(rv_sess, human_principal_id="user_admin")
    try:
        rv_mgr.assert_agent_permitted(rv_sess)
        assert False, "Should have raised AgentExecutionSuppressedError"
    except AgentExecutionSuppressedError:
        pass

    rv_mgr.release_takeover_with_assertion(
        TakeoverHandbackAssertion(
            session_id=rv_sess,
            human_principal_id="user_admin",
            status_asserted="CHALLENGE_SOLVED",
        )
    )
    rv_mgr.assert_agent_permitted(rv_sess)
    print("Remote view bounded streaming, agent suppression, and handback assertions verified.")

    # -------------------------------------------------------------------------
    # Milestone 8: Research Hand & Search Provider (3H)
    # -------------------------------------------------------------------------
    log_milestone(8, "Research Hand & SearchPort Delimited Citations (Rule 26, 30)")
    research_engine = ResearchEngine()
    research_output = research_engine.execute_research_query("cloud security frameworks")
    assert research_output["status"] == "OK"
    assert "<<<SEARCH_RESULTS" in research_output["delimited_content"]
    assert len(research_output["citations"]) >= 1
    print("Research hand structured search and Rule 26 citation boundaries verified.")

    # -------------------------------------------------------------------------
    # Milestone 9: Terminal Governance & Safety Controls (3I)
    # -------------------------------------------------------------------------
    log_milestone(9, "Terminal Safety Controls & Command Gating (Rule 23, 27)")
    term_port = TerminalPort()
    # Forbidden command denied
    try:
        term_port.execute("sudo rm -rf /", "ten_qual", "co_qual")
        assert False, "Should have raised DangerousCommandForbiddenError"
    except DangerousCommandForbiddenError:
        pass

    # High impact command requires approval
    try:
        term_port.execute("rm -f test.log", "ten_qual", "co_qual", is_human_approved=False)
        assert False, "Should have raised HighImpactApprovalRequiredError"
    except HighImpactApprovalRequiredError:
        pass

    # Safe read-only command executes
    safe_res = term_port.execute("git status", "ten_qual", "co_qual")
    assert safe_res.status == PortStatus.OK
    assert safe_res.tier == CommandTier.SAFE_READ_ONLY
    assert "<<<TERMINAL_OUTPUT" in safe_res.delimited_output
    print("Terminal command classifier, sudo/rm denial, and safe execution verified.")

    # -------------------------------------------------------------------------
    # Milestone 10: Agent Factory Import Lane & Sandboxing (3J)
    # -------------------------------------------------------------------------
    log_milestone(10, "Agent Factory Import Lane, Licence Gate & Sandboxing (Rule 5, 32)")
    # Permissive allowed, copyleft rejected
    assert LicenseGate.verify_license("MIT")
    try:
        LicenseGate.verify_license("GPL-3.0")
        assert False, "Should have raised LicenseViolationError"
    except LicenseViolationError:
        pass

    # Unsafe eval detected
    try:
        SkillImportScanner.scan_code_bytes(b"eval('dangerous')", "test_eval.py")
        assert False, "Should have raised DangerousCodeRejectedError"
    except DangerousCodeRejectedError:
        pass

    # Clean skill sandboxed execution
    runner = SandboxSkillRunner(tenant_id="ten_qual", skill_id="skill_qual_99")
    run_res = runner.run_skill_task(lambda scratch: f"wrote_to_{scratch}")
    assert run_res["success"]
    print("Agent Factory import lane licence gate, security scan, and sandboxing verified.")

    # -------------------------------------------------------------------------
    # Final Qualification Sign-Off
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STEP 3 QUALIFICATION SCENARIO: 10/10 MILESTONES PASSED [GREEN]")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
