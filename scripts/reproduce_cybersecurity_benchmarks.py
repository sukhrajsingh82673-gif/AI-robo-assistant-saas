"""
ZONATA / URA — Reproducible Cybersecurity & AI DLP Performance Benchmark Suite
==============================================================================
Empirically measures and outputs:
- Presidio Entity Scanning latency (P50, P95, throughput)
- Presidio Anonymization latency (P50, P95, throughput)
- Class 1 Allow Automatically end-to-end latency
- Class 3 Restrict & Continue end-to-end latency
- Memory baseline vs peak RSS overhead
Documented parameters:
- Concurrency: 1 (Sequential in-process execution)
- Warm-up: 50 iterations per test
- Sample count: 200 iterations per test
- Platform: Linux aarch64, Python 3.14
"""

import time
import os
import sys
import resource
import statistics
import json
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.presidio_dlp_engine import presidio_analyzer, presidio_anonymizer
from core.ai_dlp_gateway import (
    ai_dlp_gateway,
    OutboundSecurityContext,
    OutboundChannel,
    DestinationTrustLevel,
    SecurityResponseClass
)

def get_process_memory_mb() -> float:
    """Returns current process VmRSS in megabytes from /proc/self/status or getrusage."""
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return float(parts[1]) / 1024.0
    except Exception:
        pass
    # Fallback to getrusage (ru_maxrss in KB on Linux)
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

def calculate_percentiles(latencies_ms: List[float]) -> Dict[str, float]:
    latencies_sorted = sorted(latencies_ms)
    n = len(latencies_sorted)
    p50_idx = int(0.50 * n)
    p95_idx = int(0.95 * n)
    avg = sum(latencies_sorted) / n
    throughput = (1000.0 / avg) if avg > 0 else 0.0
    return {
        "p50_ms": round(latencies_sorted[p50_idx], 3),
        "p95_ms": round(latencies_sorted[p95_idx], 3),
        "avg_ms": round(avg, 3),
        "min_ms": round(latencies_sorted[0], 3),
        "max_ms": round(latencies_sorted[-1], 3),
        "throughput_req_per_sec": round(throughput, 1)
    }

def run_benchmarks():
    print("=" * 80)
    print("ZONATA / URA REPRODUCIBLE CYBERSECURITY BENCHMARK RUN")
    print("=" * 80)

    mem_start = get_process_memory_mb()
    print(f"Initial Process RSS Memory: {mem_start:.2f} MB")

    # Workload payloads
    payload_small = "Staff ZN-EMP-10492 handling account CUST-984210 under confidential Project Falcon with PAN ABCDE1234F."
    payload_medium = (
        "Internal enterprise task review: Employee John (john.doe@zonata.internal, IP 10.0.4.15) SSN 987-65-4321, "
        "Card 4111-2222-3333-4444. Reviewing account CUST-992144 and Indian tax registration GSTIN 22AAAAA0000A1Z5. "
        "Project Falcon status report: budget allocated under sovereign kernel authority. "
    ) * 4 # ~1.2 KB

    warmup_n = 50
    sample_n = 200

    # 1. Presidio Entity Analyzer Benchmark
    print(f"\n[1] Benchmarking Presidio Entity Analyzer ({sample_n} samples, {warmup_n} warmup)...")
    for _ in range(warmup_n):
        presidio_analyzer.analyze(payload_medium)

    analyzer_latencies = []
    for _ in range(sample_n):
        t0 = time.perf_counter()
        res = presidio_analyzer.analyze(payload_medium)
        t1 = time.perf_counter()
        analyzer_latencies.append((t1 - t0) * 1000.0)

    analyzer_metrics = calculate_percentiles(analyzer_latencies)
    print(f"    Analyzer P50: {analyzer_metrics['p50_ms']} ms | P95: {analyzer_metrics['p95_ms']} ms | Throughput: {analyzer_metrics['throughput_req_per_sec']} req/s")

    # 2. Presidio Anonymizer Benchmark
    print(f"\n[2] Benchmarking Presidio Anonymizer ({sample_n} samples, {warmup_n} warmup)...")
    pre_analyzed_res = presidio_analyzer.analyze(payload_medium)
    for _ in range(warmup_n):
        presidio_anonymizer.anonymize(payload_medium, pre_analyzed_res)

    anonymizer_latencies = []
    for _ in range(sample_n):
        t0 = time.perf_counter()
        anon_res = presidio_anonymizer.anonymize(payload_medium, pre_analyzed_res)
        t1 = time.perf_counter()
        anonymizer_latencies.append((t1 - t0) * 1000.0)

    anonymizer_metrics = calculate_percentiles(anonymizer_latencies)
    print(f"    Anonymizer P50: {anonymizer_metrics['p50_ms']} ms | P95: {anonymizer_metrics['p95_ms']} ms | Throughput: {anonymizer_metrics['throughput_req_per_sec']} req/s")

    # 3. Class 1 (Allow Automatically) End-to-End Gateway Benchmark
    print(f"\n[3] Benchmarking Class 1 Allow Automatically ({sample_n} samples, {warmup_n} warmup)...")
    ctx_allow = OutboundSecurityContext(
        tenant_id="tnt_bench",
        principal_id="usr_bench",
        principal_role="OPERATOR",
        calling_agent_id="worker_bench",
        channel=OutboundChannel.LLM_PROMPT,
        destination_name="LOCAL_SOVEREIGN",
        destination_trust=DestinationTrustLevel.LOCAL_SOVEREIGN
    )
    routine_payload = "Calculate quarterly inventory forecast and summary."
    for _ in range(warmup_n):
        ai_dlp_gateway.inspect_and_enforce(ctx_allow, routine_payload)

    class1_latencies = []
    for _ in range(sample_n):
        t0 = time.perf_counter()
        d = ai_dlp_gateway.inspect_and_enforce(ctx_allow, routine_payload)
        t1 = time.perf_counter()
        class1_latencies.append((t1 - t0) * 1000.0)

    class1_metrics = calculate_percentiles(class1_latencies)
    print(f"    Class 1 P50: {class1_metrics['p50_ms']} ms | P95: {class1_metrics['p95_ms']} ms | Throughput: {class1_metrics['throughput_req_per_sec']} req/s")

    # 4. Class 3 (Restrict & Continue) Strike 1 Immediate Denial Benchmark
    print(f"\n[4] Benchmarking Class 3 Restrict & Continue ({sample_n} samples, {warmup_n} warmup)...")
    ctx_restrict = OutboundSecurityContext(
        tenant_id="tnt_bench",
        principal_id="usr_bench",
        principal_role="OPERATOR",
        calling_agent_id="worker_bench_rest",
        channel=OutboundChannel.LLM_PROMPT,
        destination_name="UNAPPROVED_EXTERNAL_API",
        destination_trust=DestinationTrustLevel.UNAPPROVED_EXTERNAL
    )
    secret_payload = "Exfiltrating private key: -----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
    for _ in range(warmup_n):
        ai_dlp_gateway.inspect_and_enforce(ctx_restrict, secret_payload)

    class3_latencies = []
    for _ in range(sample_n):
        t0 = time.perf_counter()
        d = ai_dlp_gateway.inspect_and_enforce(ctx_restrict, secret_payload)
        t1 = time.perf_counter()
        class3_latencies.append((t1 - t0) * 1000.0)

    class3_metrics = calculate_percentiles(class3_latencies)
    print(f"    Class 3 P50: {class3_metrics['p50_ms']} ms | P95: {class3_metrics['p95_ms']} ms | Throughput: {class3_metrics['throughput_req_per_sec']} req/s")

    mem_end = get_process_memory_mb()
    mem_overhead = mem_end - mem_start
    print(f"\nPeak Process RSS Memory: {mem_end:.2f} MB")
    print(f"Measured Memory Overhead for Benchmark Execution: {mem_overhead:.2f} MB")

    benchmark_summary = {
        "timestamp": time.time(),
        "workload_parameters": {
            "samples": sample_n,
            "warmup": warmup_n,
            "concurrency": 1,
            "payload_sizes_bytes": {
                "small": len(payload_small),
                "medium": len(payload_medium),
                "secret": len(secret_payload)
            }
        },
        "memory_mb": {
            "baseline_rss": round(mem_start, 2),
            "peak_rss": round(mem_end, 2),
            "delta_rss": round(mem_overhead, 2)
        },
        "presidio_analyzer": analyzer_metrics,
        "presidio_anonymizer": anonymizer_metrics,
        "class_1_allow": class1_metrics,
        "class_3_restrict": class3_metrics
    }

    with open("storage/cybersecurity_benchmark_reproducible.json", "w") as f:
        json.dump(benchmark_summary, f, indent=2)
    print("\nBenchmark results persisted to storage/cybersecurity_benchmark_reproducible.json")

if __name__ == "__main__":
    run_benchmarks()
