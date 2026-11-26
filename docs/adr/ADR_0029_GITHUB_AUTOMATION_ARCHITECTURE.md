# ADR 0029: Governed GitHub Automation Architecture & Public-Repo Hygiene

- **Status:** APPROVED
- **Date:** 2026-11-24
- **Decision Makers:** Antigravity Architect, OpenCode Security Arbiter, Repository Owner
- **Governing Rules:** Rule 54 (Public-Repo Hygiene), Rule 57 (Humans Merge Only)

---

## 1. Context & Problem Statement
ZONATA must be capable of autonomous self-maintenance and software evolution via GitHub pull requests on its own repository (`sukhrajsingh82673-gif/AI-robo-assistant-saas`). Because the repository is public, public issues, pull requests, and comments can become untrusted attack vectors for prompt injection and secret exfiltration.

## 2. Decision
1. **GitHub App Scoping & Principle of Least Privilege:** Automation operates via a dedicated GitHub App installed strictly on this repository with least privilege.
   - Explicitly granted: `contents: write` (for branches `ai/*`), `pull_requests: write`, `issues: read`, `checks: read`.
   - Explicitly **prohibited**: `workflows` (cannot modify CI), `administration` (cannot modify settings), `secrets` (zero vault access).
2. **Pull Request Protocol:** AI principals may open feature branches (`ai/<class>/<id>`) and submit pull requests with evidence summaries. AI principals are mechanically barred from approving or merging pull requests (Rule 57).
3. **Public Input Sanitization:** Issues, PR reviews, and comments from external contributors are treated as untrusted data inputs. They are ingested by an isolated triage worker possessing zero write tools and zero secrets.
4. **CI Fork Security:** Pull requests from forks must never run with repository secrets. Workflows avoid `pull_request_target` with untrusted checkout.

## 3. Consequences
- Immune to public prompt injection attacks targeting CI execution.
- Human ownership is maintained for all code merges and production releases.
