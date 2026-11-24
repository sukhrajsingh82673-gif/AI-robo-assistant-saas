"""
Unit & Contract Tests for Step 7I: Research & Development Depth.
================================================================
"""

import pytest
from core.rnd.experiment_tracker import ExperimentTracker, Experiment
from core.rnd.prd import (
    ProductRequirementsDocument, PRDRequirement, PRDValidator
)
from core.rnd.prototype_runner import (
    SandboxedPrototypeRunner, PrototypeExecutionRequest
)


# --- 1. IMMUTABLE EXPERIMENT TRACKER TESTS ---

def test_01_experiment_tracking_immutability():
    tracker = ExperimentTracker()
    exp = tracker.start_experiment(
        experiment_id="EXP-101",
        tenant_id="t1",
        company_id="c1",
        name="Transformer Routing Efficiency",
        hypothesis="Dynamic expert pruning reduces inference latency by 20%",
        parameters={"model": "deepseek-v3", "experts": 8, "prune_ratio": 0.25},
        code_commit_hash="a1b2c3d4e5f6",
        dataset_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )

    # Log metrics during run
    tracker.log_metric("EXP-101", "latency_ms", 42.5)
    tracker.log_metric("EXP-101", "accuracy_top1", 0.945)

    # Complete experiment -> freezes immutably
    tracker.complete_experiment("EXP-101", final_status="completed", artifacts={"model_weights.bin": "hash_weights_123"})
    assert exp.status == "completed"
    assert exp.is_frozen is True

    # Mutability attempt: logging new metric on finalized experiment MUST fail
    with pytest.raises(RuntimeError):
        tracker.log_metric("EXP-101", "latency_ms", 39.0)


def test_02_mlflow_metadata_export():
    tracker = ExperimentTracker()
    tracker.start_experiment(
        experiment_id="EXP-202",
        tenant_id="t1",
        company_id="c1",
        name="Vector Quantization Trial",
        hypothesis="4-bit quantization retains 98% accuracy",
        parameters={"bits": 4},
        code_commit_hash="commit_xyz",
        dataset_sha256="hash_dataset_456"
    )
    tracker.log_metric("EXP-202", "compression_ratio", 4.0)
    tracker.complete_experiment("EXP-202")

    meta = tracker.export_mlflow_metadata("EXP-202")
    assert meta["run_id"] == "EXP-202"
    assert meta["status"] == "COMPLETED"
    assert any(p["key"] == "bits" and p["value"] == "4" for p in meta["params"])
    assert any(m["key"] == "compression_ratio" and m["value"] == 4.0 for m in meta["metrics"])
    assert meta["tags"]["hypothesis"] == "4-bit quantization retains 98% accuracy"


# --- 2. PRD VALIDATION ENGINE TESTS ---

def test_03_prd_validation_completeness():
    # Incomplete PRD: missing non-goals and missing acceptance criteria
    bad_prd = ProductRequirementsDocument(
        prd_id="PRD-01",
        title="Agent Tool Gateway",
        author_principal_id="pm_lead",
        problem_statement="Too short",
        target_users=["Engineers"],
        non_goals=[],  # Missing
        requirements=[
            PRDRequirement(req_id="REQ-1", title="Dynamic Proxy", description="Proxy API calls", acceptance_criteria=[])  # Missing criteria
        ],
        success_metrics=["Latency < 50ms"],
        risks_and_mitigations=[]
    )
    bad_res = PRDValidator.validate_prd(bad_prd)
    assert bad_res.is_valid is False
    assert len(bad_res.missing_elements) >= 3

    # Valid PRD: complete across all standard sections
    good_prd = ProductRequirementsDocument(
        prd_id="PRD-02",
        title="Sovereign Document Intelligence Engine",
        author_principal_id="principal_architect",
        problem_statement="Enterprises require sovereign OCR and tabular parsing without transmitting confidential invoices to public cloud endpoints.",
        target_users=["Compliance Officers", "AP Clerks", "Auditors"],
        non_goals=["Does not support hand-written cursive scripts in v1"],
        requirements=[
            PRDRequirement(
                req_id="REQ-01",
                title="NIC Schema v1.03 Compliance",
                description="Export generated e-invoices matching the official GST schema.",
                acceptance_criteria=["Validates against official NIC JSON schema", "Generates 64-character SHA256 IRN hash"]
            )
        ],
        success_metrics=["OCR precision > 99.0%", "Processing latency < 2.0s per page"],
        risks_and_mitigations=[{"risk": "Scanned document blurriness", "mitigation": "Flag low-DPI scans for manual human review"}]
    )
    good_res = PRDValidator.validate_prd(good_prd)
    assert good_res.is_valid is True
    assert len(good_res.missing_elements) == 0


# --- 3. SANDBOXED PROTOTYPE RUNNER TESTS ---

def test_04_sandboxed_prototype_runner_execution_and_artifacts():
    runner = SandboxedPrototypeRunner()

    # Code that computes value and writes an artifact file
    code_snippet = """
import hashlib

data = "Sovereign Prototype Computation"
with open("result.txt", "w") as f:
    f.write(data)

print("PROTOTYPE_SUCCESS: Output calculated")
"""
    req = PrototypeExecutionRequest(
        code=code_snippet,
        timeout_seconds=5.0,
        expected_artifacts=["result.txt"]
    )
    res = runner.execute_prototype(req)

    assert res.exit_code == 0
    assert "PROTOTYPE_SUCCESS" in res.stdout
    assert res.timed_out is False
    assert "result.txt" in res.artifact_hashes
    assert len(res.artifact_hashes["result.txt"]) == 64


def test_05_sandboxed_prototype_timeout_enforcement():
    runner = SandboxedPrototypeRunner()
    # Code that loops indefinitely
    infinite_code = """
import time
while True:
    time.sleep(0.1)
"""
    req = PrototypeExecutionRequest(
        code=infinite_code,
        timeout_seconds=1.0  # 1 second timeout
    )
    res = runner.execute_prototype(req)
    assert res.timed_out is True
    assert res.exit_code == -1
    assert "timed out" in res.stderr
