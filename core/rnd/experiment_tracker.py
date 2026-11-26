"""
Immutable Experiment Tracking Engine
====================================
Tracks R&D experiments with cryptographic hashes of code, datasets, and artifacts.
Once an experiment is marked completed, its state is frozen immutably.
Exports metadata compatible with MLflow and Weights & Biases (W&B).
"""

import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class Experiment(BaseModel):
    experiment_id: str
    tenant_id: str
    company_id: str
    name: str
    hypothesis: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)
    code_commit_hash: str
    dataset_sha256: str
    artifact_hashes: Dict[str, str] = Field(default_factory=dict)
    status: str = "running"  # 'running', 'completed', 'failed', 'abandoned'
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    is_frozen: bool = False


class ExperimentTracker:
    """Manages experiment registration, metric logging, and MLflow-compatible metadata export."""

    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}

    def start_experiment(
        self,
        experiment_id: str,
        tenant_id: str,
        company_id: str,
        name: str,
        hypothesis: str,
        parameters: Dict[str, Any],
        code_commit_hash: str,
        dataset_sha256: str
    ) -> Experiment:
        exp = Experiment(
            experiment_id=experiment_id,
            tenant_id=tenant_id,
            company_id=company_id,
            name=name,
            hypothesis=hypothesis,
            parameters=parameters,
            code_commit_hash=code_commit_hash,
            dataset_sha256=dataset_sha256,
            status="running"
        )
        self.experiments[experiment_id] = exp
        return exp

    def log_metric(self, experiment_id: str, metric_name: str, value: float) -> Experiment:
        exp = self.experiments.get(experiment_id)
        if not exp:
            raise KeyError(f"Experiment {experiment_id} not found")

        # Invariant: Completed / frozen experiments cannot be altered
        if exp.is_frozen or exp.status in ("completed", "failed", "abandoned"):
            raise RuntimeError(f"Cannot log metric: Experiment {experiment_id} is immutable and finalized")

        exp.metrics[metric_name] = value
        return exp

    def complete_experiment(
        self,
        experiment_id: str,
        final_status: str = "completed",
        artifacts: Optional[Dict[str, str]] = None
    ) -> Experiment:
        exp = self.experiments.get(experiment_id)
        if not exp:
            raise KeyError(f"Experiment {experiment_id} not found")

        if exp.is_frozen:
            raise RuntimeError(f"Experiment {experiment_id} is already frozen")

        exp.status = final_status
        exp.completed_at = datetime.now(timezone.utc).isoformat()
        if artifacts:
            exp.artifact_hashes.update(artifacts)
        exp.is_frozen = True
        return exp

    def export_mlflow_metadata(self, experiment_id: str) -> Dict[str, Any]:
        """Exports MLflow / W&B compatible metadata structure."""
        exp = self.experiments.get(experiment_id)
        if not exp:
            raise KeyError(f"Experiment {experiment_id} not found")

        return {
            "run_id": exp.experiment_id,
            "experiment_name": exp.name,
            "status": exp.status.upper(),
            "start_time": exp.created_at,
            "end_time": exp.completed_at,
            "params": [{"key": k, "value": str(v)} for k, v in exp.parameters.items()],
            "metrics": [{"key": k, "value": v, "timestamp": exp.completed_at or exp.created_at} for k, v in exp.metrics.items()],
            "tags": {
                "hypothesis": exp.hypothesis,
                "code_commit": exp.code_commit_hash,
                "dataset_hash": exp.dataset_sha256,
                "tenant_id": exp.tenant_id,
                "company_id": exp.company_id
            },
            "artifacts": exp.artifact_hashes
        }
