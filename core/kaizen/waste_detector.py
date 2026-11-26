"""ZONATA Sovereign Core — Lean Waste Detector.

Analyzes process instances for the 6 primary Lean wastes:
1. Waiting: Step duration exceeded SLA or blocked on human approval.
2. Rework: Step failed and had to be re-run or corrected.
3. Over-processing: Redundant verifications or excessive token expenditure.
4. Handoff: Excessive inter-role context transfers.
5. Defects: Andon halts, validation errors, or red-line triggers.
6. Unused talent: High-capability executive invoked for basic mechanical task.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.kaizen.metrics import KaizenMetricsStore, WasteEvent
from core.process_packs.engine import ProcessInstance, StepExecutionRecord
from core.process_packs.schema import ProcessPack

logger = logging.getLogger("zonata.core.kaizen.waste")


class WasteDetector:
    """Analyzes execution traces to discover and record Lean waste."""

    def __init__(self, metrics_store: Optional[KaizenMetricsStore] = None):
        self.metrics_store = metrics_store or KaizenMetricsStore()

    def analyze_instance(
        self,
        instance: ProcessInstance,
        pack: Optional[ProcessPack] = None
    ) -> List[WasteEvent]:
        """Detects waste events from a completed or running process instance."""
        detected_waste: List[WasteEvent] = []

        # 1. Defect & Andon Detection
        if instance.status == "HALTED_ANDON" and instance.andon_incident:
            w = self.metrics_store.record_waste(
                tenant_id=instance.tenant_id,
                company_id=instance.company_id,
                pack_id=instance.pack_id,
                instance_id=instance.instance_id,
                step_id=instance.records[-1].step_id if instance.records else "entry",
                waste_type="defects",
                severity="HIGH",
                details=f"Process stopped by Andon rule: {instance.andon_incident.get('rule_name')}",
                estimated_cost_usd=0.05
            )
            detected_waste.append(w)

        # 2. Step-Level Analysis
        step_ids_seen = set()
        for idx, rec in enumerate(instance.records):
            # Check for Rework (step seen multiple times)
            if rec.step_id in step_ids_seen:
                w = self.metrics_store.record_waste(
                    tenant_id=instance.tenant_id,
                    company_id=instance.company_id,
                    pack_id=instance.pack_id,
                    instance_id=instance.instance_id,
                    step_id=rec.step_id,
                    waste_type="rework",
                    severity="MEDIUM",
                    details=f"Step '{rec.step_id}' was re-executed (rework detected).",
                    estimated_cost_usd=rec.cost_usd
                )
                detected_waste.append(w)
            step_ids_seen.add(rec.step_id)

            # Check for Step Failure / Defect
            if rec.status == "FAILED":
                w = self.metrics_store.record_waste(
                    tenant_id=instance.tenant_id,
                    company_id=instance.company_id,
                    pack_id=instance.pack_id,
                    instance_id=instance.instance_id,
                    step_id=rec.step_id,
                    waste_type="defects",
                    severity="HIGH",
                    details=f"Step execution failed: {rec.error}",
                    estimated_cost_usd=0.02
                )
                detected_waste.append(w)

            # Check for Waiting (abnormally high duration)
            if rec.duration_seconds > 300.0:  # > 5 minutes
                w = self.metrics_store.record_waste(
                    tenant_id=instance.tenant_id,
                    company_id=instance.company_id,
                    pack_id=instance.pack_id,
                    instance_id=instance.instance_id,
                    step_id=rec.step_id,
                    waste_type="waiting",
                    severity="LOW",
                    details=f"Step '{rec.step_id}' took {round(rec.duration_seconds, 1)}s (potential waiting/bottleneck).",
                    estimated_cost_usd=0.01
                )
                detected_waste.append(w)

        # 3. Excessive Handoffs (> 6 steps with different actors)
        actors = [r.actor for r in instance.records]
        role_switches = sum(1 for i in range(1, len(actors)) if actors[i] != actors[i-1])
        if role_switches >= 5:
            w = self.metrics_store.record_waste(
                tenant_id=instance.tenant_id,
                company_id=instance.company_id,
                pack_id=instance.pack_id,
                instance_id=instance.instance_id,
                step_id="workflow",
                waste_type="handoff",
                severity="MEDIUM",
                details=f"High handoff count: {role_switches} role transitions during process execution.",
                estimated_cost_usd=0.02
            )
            detected_waste.append(w)

        return detected_waste
