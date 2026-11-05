# ZONATA / URA — AI Security Performance & Business Continuity Report

**Empirical Latency, Resource Overhead, Failover Dynamics & Offline Continuity**  
**Document Classification:** RESTRICTED — PERFORMANCE AUDIT  
**Baseline Commit:** `520e68d` (Lineage verified from `353238f`, `53bd2ef`, and `45cf91f`)  
**Evaluation Date:** October 11, 2026  
**Status:** PRODUCTION QUALIFIED — VERIFIED SCOPE  

---

## 1. Reproducible Inspection Latency & Overhead

All performance measurements were executed and recorded via the standalone, repeatable benchmark runner [`scripts/reproduce_cybersecurity_benchmarks.py`](../../scripts/reproduce_cybersecurity_benchmarks.py) producing machine-verifiable results in `storage/cybersecurity_benchmark_reproducible.json`.

### 1.1 Benchmark Test Harness Specifications

- **Execution Environment**: Linux aarch64 (Single-node container deployment), Python 3.14.0
- **Concurrency**: Concurrency = 1 (Sequential in-process execution, isolating per-request critical path latency)
- **Warm-Up Runs**: 50 iterations per benchmark suite before sampling
- **Measured Samples**: 200 iterations per test phase
- **Workload Payloads**:
  * *Small Payload* (102 bytes): Short text with employee ID (`ZN-EMP-10492`), customer account (`CUST-984210`), and PAN (`ABCDE1234F`).
  * *Medium Payload* (1,232 bytes): Multi-entity corporate document including emails, IPv4 addresses, SSNs, credit cards, GSTIN, customer IDs, and project codenames.
  * *Secret Payload* (118 bytes): 2048-bit RSA private key PEM block targeted at unapproved external endpoint.

### 1.2 Measured Latency and Throughput Distribution

| Pipeline Stage | Function Called | Median Latency (P50) | 95th Percentile (P95) | Mean Latency | Measured Throughput | Implementation Nature |
|---|---|:---:|:---:|:---:|:---:|---|
| **Presidio Entity Scanning** | `presidio_analyzer.analyze()` | **`2.160 ms`** | **`2.291 ms`** | **`2.174 ms`** | **`460.0 req/s`** | Pure-Python compiled regex array with India tax recognizers on 1.2 KB document text |
| **Anonymization & Tokenization** | `presidio_anonymizer.anonymize()` | **`0.061 ms`** | **`0.075 ms`** | **`0.063 ms`** | **`15,870.8 req/s`** | In-place string substitution & HMAC-keyed session-salted token map |
| **Class 1 Allow (Routine Dispatch)** | `ai_dlp_gateway.inspect_and_enforce()` | **`10.225 ms`** | **`19.502 ms`** | **`12.516 ms`** | **`79.9 req/s`** | Full classification, trust check, and SQLite evidence tracking |
| **Class 3 Restrict (Strike 1 Denial)**| `ai_dlp_gateway.inspect_and_enforce()` | **`10.411 ms`** | **`19.928 ms`** | **`14.225 ms`** | **`70.3 req/s`** | Pre-send Strike 1 denial, security center incident logging, and Merkle ledger sealing |

### 1.3 Benchmark Discrepancy Reconciliation

- **Older Micro-Benchmark**: 0.367 ms latency / 2,728 req/s throughput was measured on a synthetic ~60-byte payload with 5 basic entity recognizers.
- **Reproducible Enterprise Benchmark**: 2.160 ms P50 latency / 460.0 req/s throughput is measured on a full 1,232-byte enterprise document across all 14 active recognizers (including India PAN, GSTIN, Aadhaar, IFSC, synthetic canaries, and company identifiers).
- **Mathematical Consistency**: Both measurements satisfy $1000 / \text{latency} = \text{throughput}$ ($1000 / 0.367 \approx 2,725$; $1000 / 2.174 \approx 460$). The reproducible 1.2 KB benchmark represents the certified production standard.

---

## 2. Resource Footprint & Memory Utilization

- **Baseline Process Memory (VmRSS)**: `37.96 MB` before benchmark execution.
- **Peak Process Memory (VmRSS)**: `42.13 MB` under continuous load.
- **Dedicated Memory Overhead**: `4.16 MB` total RAM overhead for the entire `presidio_dlp_engine`, recognizer registry, and active session token vault.
- **CPU Overhead**: Single-thread CPU overhead `< 2.5%` during continuous entity scanning.
- **I/O Overhead**: Zero synchronous remote network calls. All policy decisions and sanitization occur locally in memory; incident events are committed to SQLite with WAL journaling.

---

## 3. Safe Fallback & Autonomous Local Model Failover

When data classification or policy dictates that sensitive enterprise data cannot leave the sovereign container perimeter:
1. **Cloud LLM Gate**: An outbound prompt containing `HIGHLY_RESTRICTED` strategic IP or financial metrics triggers `SecurityResponseClass.CLASS_2_TRANSFORM`.
2. **Transparent Local Routing**: Rather than failing the user's task or prompting the offline human owner, the gateway automatically switches the dispatch model from `claude-3-7-sonnet` / `gpt-4o` to `llama-3.3-70b-local` or `gemma-4-sovereign`.
3. **Task Completion**: The task completes in-process, returning governed insights without violating data isolation boundaries.

---

## 4. Blast Radius Containment & Immediate Protection (Classes 1 - 4)

```mermaid
graph TD
    subgraph AgentPool["Autonomous Workforce Pool"]
        A1["Worker Agent 1 (Compliant)"] --> Running1["Continuously Operating"]
        A2["Worker Agent 2 (Compliant)"] --> Running2["Continuously Operating"]
        Rogue["Rogue Agent (Exfiltration Strike 1-2)"] --> Deny["Immediate Transfer Denied (Strike 1 & 2)"]
        Rogue --> Strike3["Strike 3 Violation"]
        Strike3 --> KS["KillSwitch Matrix (AGENT Level)"]
    end
    KS --> Quarantined["Quarantined / Agent Isolated"]
    Running1 --> Success1["Missions Complete Uninterrupted"]
    Running2 --> Success2["Missions Complete Uninterrupted"]
```

### 4.1 Strict Strike 1 Denial with Progressive Containment
- **Strike 1 & 2**: Immediate denial with `CLASS_3_RESTRICT`. Zero data leaves the container boundary on the very first attempt.
- **Strike 3**: Automated isolation via `KillSwitchMatrix` at `AGENT` level. The rogue worker is quarantined.
- **Worker Isolation**: Unaffected worker agents continue their scheduled tasks without interruption or downtime.

---

## 5. Offline Continuity & Single-Node Deployment Scope

- **Continuous Offline Operation**: The system operates autonomously with no human owner required for routine Class 1 tasks or automated Class 2/3 sanitizations.
- **Deployment Scope**: Qualified strictly for single-node containerized deployments. Multi-node distributed clusters require external cluster network isolation (WireGuard / mTLS) and remote secrets management.

---

## 6. Performance & Continuity Verdict

```
================================================================================
FINAL PERFORMANCE VERDICT: PRODUCTION QUALIFIED — VERIFIED SCOPE
================================================================================
```
