# OpenDots Integration Assessment

Status: **NOT INTEGRATED / HEURISTIC SHIM**
Spec reference: Coworker 2.0 §5 (OpenDots Integration)
Last reviewed: 2026-11-06

## Verdict

OpenDots could not be verified as a real, installable product with a public API,
SDK, licence and pricing on this host. No OpenDots package, model weights, or
endpoint exists in the environment, and no public artefact was confirmed.

Per §5 ("If unsuitable or unavailable, do not fabricate an integration"), the
project therefore does **not** claim an OpenDots integration. The file
`core/coworker/adapters/opendots_adapter.py` is retained because call sites use
it, but it is explicitly a deterministic **grounding shim**:

| Component | What it actually does | Label emitted |
|---|---|---|
| `ground_intent()` label hit | Exact lookup in the seeded perception tree | `PERCEPTION_TREE` |
| `ground_intent()` miss | Fixed normalised anchors per keyword (`search`, `submit`, `close`, `menu`, `login`) | `HEURISTIC_ANCHOR` |
| `click_intent()` | Grounds, then dispatches a real `xdotool` click via `ComputerUseEngine` | `executed` flag from the engine |
| Model inference | None | `SPECIFICATION["model_name"] = None` |

The earlier `SPECIFICATION` block advertised a `"OpenDots-Grounding-v1"` model
with `"evaluation_status": "REAL_PRODUCTION_QUALIFIED"`. That was false and has
been removed.

## §5 assessment checklist

1. **Product identity and official documentation** — Not confirmed. No verifiable
   official docs or repository were reachable during this review.
2. **Available APIs and SDKs** — None found. No Python package, gRPC/REST schema,
   or SDK is installed.
3. **Authentication model** — Unknown; nothing to authenticate to.
4. **Agent execution model** — Unknown; no scheduler or execution API observed.
5. **Memory and context capabilities** — Unknown.
6. **Desktop and browser capabilities** — Unknown. The local shim does coordinate
   grounding only; it does not provide agent execution or context management.
7. **Background execution support** — Unknown.
8. **Security and isolation** — Unknown; no artifact to audit.
9. **Resource requirements** — Untestable without an artifact.
10. **Licensing and cost** — Unverified. The shim itself is Apache-2.0 (this repo).

## What the Coworker uses instead

The capabilities §5 hoped to gain are covered by existing, verified components:

- **Specialised agents / delegation / context / long-running tasks** —
  `core/coworker/agent_factory_v2.py`, `core/coworker/subworkers_v2.py`,
  `core/coworker/orchestrator_v2.py` (12-state lifecycle, leases, cleanup
  manifests).
- **Background execution and recovery** — `core/coworker/background_dispatcher.py`
  plus `CoworkerLifecycleOrchestrator.recover_crashed_tasks()`.
- **Multiple execution capabilities** — the runtime router
  (`core/coworker/runtime_router.py`) with terminal, browser, computer-use,
  Hermes, OpenHands and OpenClaw runtimes.

## Re-evaluation trigger

Re-open this assessment only if a concrete OpenDots artifact appears: a package
name resolvable from PyPI, a pinned repository commit, or a documented endpoint
with a licence. Until then the adapter must keep emitting
`HEURISTIC_ANCHOR` / `PERCEPTION_TREE` and must never be described as an
OpenDots model integration.
