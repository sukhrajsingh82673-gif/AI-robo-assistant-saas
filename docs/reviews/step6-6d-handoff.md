# Sub-Step 6D Handoff Dossier — Owner Help Protocol & Human Governance

- **Date:** 2026-11-24
- **Builder:** Antigravity Systems Architect & Builder
- **Reviewer:** OpenCode Security Arbiter & Red Team
- **Target Branch:** `step6-evolution`

---

## 1. Files Changed & Created (git diff --stat)
```
 .github/workflows/ci-evolution.yml |   6 +-
 core/evolution/owner_help.py       | 234 +++++++++++++++++++++++++++++++++++++
 core/evolution/preservation.py     |  31 +++++
 docs/reports/STEP6_REPORT.md       |  23 ++++
 tests/test_step6_owner_help.py     | 211 +++++++++++++++++++++++++++++++++
 5 files changed, 502 insertions(+), 3 deletions(-)
```
*Note: Rule 49 (Preservation Contract) is strictly honored. Zero Step 1-5 files modified.*

---

## 2. Commands to Re-run
```bash
cd /data/data/com.termux/files/home/AI-robo-assistant-saas
python3 -m pytest tests/test_step6_owner_help.py -v
python3 -m pytest tests/test_truth_linter.py -q
```

---

## 3. Claims & Evidence
1. **3-Step Rule:** Validated max 3 imperative steps. >3 steps raises `HelpValidationError`.
2. **Deduplication:** Repeated question within 24 hours returns existing ticket.
3. **Hourly Rate Limit:** Throttles to max 5/hour per tenant; excess queued.
4. **Step-Up Authentication:** Demands verified `stepup_...` token for sensitive tickets.
5. **Ask Once / Learn Forever:** Caches resolutions by question hash; repeat queries auto-resolve with 0 human interruptions.
6. **Secret Interception:** Plaintext API keys/passwords in human responses are routed to Vault (`vault://...`) and scrubbed from resolution.

---

## 4. Mutation Checks
- Passing raw credentials (`sk_live_...`) in human response: intercepted and placed in vault, verified missing from plaintext resolution.

---

## 5. Known Gaps
- None. Ready for OpenCode review and git commit.
