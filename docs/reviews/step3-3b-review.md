# Sub-Step 3B Review: Host Permission Model and the Host Agent

**Sub-Step:** 3B  
**Branch:** `step3-hands`  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-22  
**Verdict:** **PASS**  

---

## 1. Audit Against Acceptance Criteria

| Criteria | Required Invariant | Audit Findings | Result |
| :--- | :--- | :--- | :--- |
| **New Component: Host Agent** | Small host agent connecting outbound-only to cloud (no inbound listening ports). Without it, desktop control is `NOT_CONFIGURED`. | `ZonataHostAgent` implemented in `core/host/agent.py`. `probe_desktop_control()` in `core/capability_probe.py` updated to return `NOT_CONFIGURED` without an active paired device. | **PASS** |
| **Pairing Protocol** | One-time code, Ed25519 keypair in local secure storage (private key never leaves host or enters DB), public key bound to tenant, requires human step-up auth. | `PairingManager` in `core/host/pairing.py` generates 6-digit one-time code, enforces `is_human_step_up_authenticated`, stores only public key. Verified in `test_01`. | **PASS** |
| **Cryptographic Signing & Anti-Replay** | Signed envelopes with sequence number, nonce, timestamp drift check (< 30s). Replays refused. | `HostSessionManager` in `core/host/session.py` enforces Ed25519 signature verification, monotonic sequence counter, and nonce replay cache. Verified in `test_02` & `test_03`. | **PASS** |
| **Grants & Principal Separation (Rule 15)** | Tables `devices`, `host_grants`, `grant_events` (append-only), `host_sessions`. Modes: `OBSERVE`, `CONFIRM_EACH`, `AUTONOMOUS_IN_SCOPE`. Grants created/revoked ONLY by authenticated human. | Tables defined in migrations `0029_host_permission_model.sql` with multi-tenant RLS. `HostGrantManager` strictly enforces `created_by_principal_type == 'HUMAN'`, raising `Rule15Violation` for non-human principals. Verified in `test_07`. | **PASS** |
| **Scope Separation** | `PERSONAL` (owner's grant only) vs `COMPANY` (requires AI CEO policy gate + owner's grant). | `GrantScope.PERSONAL` and `GrantScope.COMPANY` modeled and verified. | **PASS** |
| **Host-Side Enforcement (Rule 23)** | Allowlist checked locally on every command; cloud cannot widen grants. | `ZonataHostAgent.execute_command` verifies local grant store before execution. Unlisted apps rejected locally with `OutOfGrantError`. Verified in `test_04` & `test_05`. | **PASS** |
| **Deny-by-Default (Rule 23/27)** | Deny by default for password managers, banking apps, OS security settings, unless explicitly named AND human confirms. | `DENIED_BY_DEFAULT_APPS` contains 1Password, Bitwarden, KeePass, Chase, PayPal, etc. Wildcard grants fail to permit them. Verified in `test_08`. | **PASS** |
| **Physical Kill Switch** | Emergency kill hotkey / tray trigger stopping all activity instantly, dropping session, reporting to cloud, and appending audit event. | `ZonataHostAgent.trigger_kill_switch` halts local execution, marks cloud session `HALTED`, and appends `KILL_SWITCH_ENGAGED` event. Verified in `test_06`. | **PASS** |
| **Acceptance Testing** | Unit/contract tests verifying all 3B.6 acceptance scenarios. | `tests/test_step3_host_agent.py` ran 9 tests in 0.636s with 100% PASS. | **PASS** |

---

## 2. Reviewer Verdict

**STATUS: PASS.**  
Sub-Step 3B satisfies all host permission, device pairing, anti-replay, deny-by-default, principal separation, and local enforcement requirements. Verified 100% GREEN in authoritative GitHub Actions CI:
- **CI Run ID:** [45100113591](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/45100113591)
- **Status:** All 3 jobs passed (Supply Chain, SBOM, License & Image Pinning Audit: 2m4s; PostgreSQL 16 Contract Tests: 3m0s; SQLite Dev Suite: 2m4s).
Sub-Step 3B is formally SIGNED OFF. The builder is authorized to proceed to Sub-Step 3C.
