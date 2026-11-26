# ZONATA Public Exposure & Repository Security Audit Report

**Date of Audit:** 2026-11-24  
**Auditor:** Antigravity (Senior Systems Architect & Security Engineer)  
**Target Repository:** `sukhrajsingh82673-gif/AI-robo-assistant-saas`  
**Current Visibility:** `PUBLIC` (Switched from Private on 2026-11-24)  
**Governing Standard:** Antigravity Step 6 — Sub-Step 6A & Standing Rule 41 (Zero Plaintext Secrets)

---

## 1. Executive Summary & Immediate Recommendations

> [!WARNING]
> **PRIMARY RECOMMENDATION:** Set the repository visibility back to **PRIVATE** immediately in GitHub Settings (`Settings -> Danger Zone -> Change visibility -> Change to private`). This action is fast, reversible, and prevents further indexing, web scraping, and third-party mirrors while credential rotation and history mitigation are evaluated.

On 2026-11-24, repository visibility was changed from Private to Public to unblock GitHub Actions runner quota limits. While this enabled unlimited free runner minutes, git history prior to Step 1A contains historical commits with tracked database binaries and connection strings. Because git history is cloned and cached by public scanners immediately upon publicization, all historical secrets must be treated as **fully compromised**.

---

## 2. GitHub Configuration & Posture Audit (Read-Only)

| Setting / Control | Inspected Status | Assessment | Recommended Owner Action |
|---|---|---|---|
| **Repository Visibility** | `PUBLIC` | High Exposure Risk | Switch to `PRIVATE` until rotation is attested. |
| **Branch Protection (`main`)** | `NOT_PROTECTED` (HTTP 404) | High Risk | Require PR reviews, dismiss stale approvals, enforce linear history. |
| **Secret Scanning** | `DISABLED` | Vulnerable | Enable Secret Scanning in Security & Analysis. |
| **Push Protection** | `DISABLED` | Vulnerable | Enable Secret Scanning Push Protection to block new commits with keys. |
| **Dependabot Security Updates** | `DISABLED` | Moderate Risk | Enable automated dependency security updates. |
| **Self-Hosted Runners** | `NONE` (total_count: 0) | **OK** | Maintain: public repositories must never connect self-hosted runners. |
| **`pull_request_target` Usage** | `NONE` (0 occurrences) | **OK** | Maintain: avoids pwn-request token exfiltration vulnerabilities. |
| **CODEOWNERS** | `MISSING` | Needs Action | Add `.github/CODEOWNERS` mandating human owner sign-off for critical paths. |
| **Open Pull Requests** | `20 OPEN` (Dependabot) | Untrusted | Review and merge/close Dependabot bumps; reject untrusted contributor PRs. |
| **SPDX License File** | `MISSING` (Detected: "Other") | Owner Decision | Add authoritative `LICENSE` file defining intellectual property terms. |

---

## 3. Historical Secrets & Artifact Exposure Register

In strict compliance with **Rule 41**, zero secret values, token strings, or private payloads are printed or pasted below. Findings are listed by commit hash and file path only.

### 3.1 Tracked SQLite Database (`storage/roboassistant.db`)
- **Initial Introduction:** Commit `42e0465` (*"feat: initial commit for RoboAssistant Company OS 1.0"*).
- **Historical Modifications:** Commits `fafbb60`, `0266a40`, `3b21551`, `17746cd`, `35a4d7c`, `5fc8902`, `31fa1ed`, `fc52e81`, `50b3ca3`, `45cf91f`, `53bd2ef`, `d2eb0a1`, `5c30658`, `4ec9754`.
- **Working Tree Untracking:** Commit `a06045b` (*"feat(step1a): inventory, repo integrity, clean import, and untrack db"*).
- **Exposed Assets:** Schema contained user accounts, company entities, settings, signing keys, and encrypted vault rows.
- **Remediation Requirement:** Mandatory rotation of all signing keys, internal tokens, and master encryption keys.

### 3.2 Cloud Database Connection Strings (`neon.ts`, Deploy Scripts)
- **Commits:** `5eafcf6` (*"feat(phase-10.3): implement free-tier staging package with Render, Neon PostgreSQL 16"*), `b9793dc` (*"feat(deploy): wire Neon PostgreSQL, Auth, Functions, and Data API with live verification"*).
- **Files:** `neon.ts`, `deploy/free_tier/apply_neon_migrations.py`, `deploy/free_tier/verify_neon_e2e.py`.
- **Exposed Assets:** Neon PostgreSQL credentials and connection URLs.
- **Remediation Requirement:** Rotate database credentials in Neon console immediately; terminate existing connection pools.

### 3.3 Public Instruction & Memory Documents
- **Files:** `AGENTS.md`, `GEMINI.md`, `anti-gravity-instructions.md`, `PROJECT_MEMORY.md`, `scratch/`.
- **Exposed Assets:** Architectural prompts, operational rules, internal roadmaps.
- **Remediation Requirement:** Scrub any internal infrastructure references or proprietary prompt formulations if intended for proprietary licensing.

---

## 4. Privacy & Incident Assessment (GDPR Art. 33 / DPDP Act)

- **Nature of Data:** Audit of historical database states indicates data was synthetically generated during local testing (developer mocks, synthetic seeds, test user emails).
- **Statutory Incident Determination:**
  - If any production customer or live employee personal data was included in `storage/roboassistant.db`, a formal **Privacy Incident** must be declared under the Step 5F workflow (`BreachNotificationCoordinator`), triggering statutory notification within 72 hours.
  - If data was purely synthetic and test-mode fixtures, formal regulatory breach reporting is not triggered, but internal security rotation remains mandatory.

---

## 5. History Rewriting Limitations

> [!CAUTION]
> Rewriting git history via `git-filter-repo` or `BFG Repo-Cleaner` removes blobs from this repository instance, but **CANNOT** guarantee eradication across external mirrors, GitHub internal caches, or local clones already made by public crawlers. All credentials committed to git history must be treated as permanently compromised and rotated at the provider level.

---

## 6. Rotation Attestation Requirement

Under Rule 41 and Sub-Step 6A, Step 6 evolution execution is gated on the existence of an owner-signed rotation attestation ([`docs/security/OWNER_ROTATION_ATTESTATION.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/security/OWNER_ROTATION_ATTESTATION.md)).
Antigravity cannot externally verify provider-level credential rotation and will not fabricate verification claims.
