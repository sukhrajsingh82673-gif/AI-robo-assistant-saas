# Sub-Step 3C Handoff: Desktop Perception and Control

**Sub-Step:** 3C  
**Branch:** `step3-hands`  
**Builder:** Antigravity  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-23  

---

## 1. Files Changed (`git diff --stat`)

```text
 .github/workflows/ci.yml                            |   2 +-
 core/coworker/providers/desktop_native_providers.py |  12 ++
 core/host/__init__.py                               |  32 +++-
 core/host/agent.py                                  |  64 +++++++-
 core/host/interaction.py                            | 205 ++++++++++++++++++++++++
 core/host/perception.py                             | 377 +++++++++++++++++++++++++++++++++++++++++++
 tests/test_step3_desktop_control.py                 | 245 ++++++++++++++++++++++++++++
 7 files changed, 933 insertions(+), 4 deletions(-)
```

---

## 2. Commands to Re-run

```bash
# 1. Run unit tests for Sub-Step 3C
python -m unittest tests/test_step3_desktop_control.py

# 2. Run all Step 3 test suites together
pytest tests/test_step3_preflight.py tests/test_step3_host_agent.py tests/test_step3_desktop_control.py -v
```

---

## 3. Claims Made & Verified

1. **Layer 1 Accessibility Tree Parsing:** `DesktopPerceptionEngine.parse_accessibility_snapshot` extracts semantic nodes and converts absolute coordinates into window-relative coordinates `(rx, ry)`. Verified in `test_01`.
2. **Host-Side Password Masking (Rule 24):** In Layer 1, passwords, secrets, and credential fields have values replaced with `[MASKED_INPUT]`. In Layer 2, visual frames blackout password and challenge widgets on the host before transmission. Verified in `test_02`.
3. **Two-Tier Perception Preference (ADR 0003):** Layer 1 preferred when accessibility data is present. Layer 2 is triggered only on empty tree, high-impact pre-action confirmation (Rule 27), or explicit visual inspection tasks. Verified in `test_03` & `test_04`.
4. **Out-of-Grant Coordinate Rejection (Rule 23 & 28):** Synthetic click and drag coordinates exceeding window bounds `[0..w, 0..h]` or negative coordinates are rejected on the host with `OutOfGrantCoordinatesError`. Verified in `test_05`.
5. **Instant Human Physical Override:** Physical mouse or keyboard activity or hotkey halts execution immediately with `HostSecurityViolation`. Verified in `test_06`.
6. **Physical-Speed Throttling:** Human typing speed is clamped to ~12 chars/sec (~120 wpm) and click pauses enforced to prevent OS buffer flooding. Verified in `test_07`.
7. **Minimum Necessary Capture (Rule 28):** All perception and interaction bounds are strictly clamped to the granted window rectangle. Verified in `test_08`.

---

## 4. Known Gaps / Next Sub-Steps

- Sub-Step 3C delivers desktop perception and interaction primitives.
- Sub-Step 3D will deliver the origin-bound credential vault (`enterprise_secret_vault`).
