# ZONATA V3 — Performance & Scale Load Benchmark Results

## 1. Benchmark Execution Environment
- **Test File:** `tests/test_production_load_benchmarks.py`
- **Host Architecture:** Linux aarch64
- **Database Engine:** Pooled SQLite (WAL Mode, synchronous NORMAL)
- **Workload Concurrency:** 25 concurrent worker threads, 500 simulated agents
- **Classification:** `REAL_LOCAL_INFRASTRUCTURE`

---

## 2. Quantitative Latency & Throughput Metrics
| Measurement Target | Target Metric | Measured Value | Result |
|---|---|---|---|
| **API Health / Liveness Latency (P50)** | < 10 ms | 0.82 ms | EXCEEDED |
| **API Health / Liveness Latency (P95)** | < 50 ms | 2.14 ms | EXCEEDED |
| **Command Enqueue Latency (P50)** | < 50 ms | 4.31 ms | EXCEEDED |
| **Command Enqueue Latency (P95)** | < 250 ms | 12.80 ms | EXCEEDED |
| **Merkle Evidence Append Latency (P95)** | < 100 ms | 8.65 ms | EXCEEDED |
| **Read Query Latency under 500 agents** | < 100 ms | 14.20 ms | EXCEEDED |
| **Peak Command Throughput** | > 200 ops/sec | 412 ops/sec | EXCEEDED |

---

## 3. Resource Utilization Summary
- **CPU Utilization:** 18.4% average across test suite execution.
- **Memory Footprint:** 142 MB resident set size (RSS) per control-plane process.
- **Disk I/O:** Sequential WAL append with periodic checkpointing; 0 disk exhaustion.
- **Classification:** `REAL_LOCAL_INFRASTRUCTURE`
