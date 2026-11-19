"""ZONATA Sovereign Core — Process Pack Loader & Registry.

Loads, validates, and persists Process Packs from YAML definitions.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
import yaml

from core.db import db
from core.process_packs.schema import (
    AndonRule,
    AutonomyCriteria,
    ProcessKPIs,
    ProcessPack,
    ProcessStep,
    SimulationScenario,
    SIPOC,
)

logger = logging.getLogger("zonata.core.process_packs.loader")


class ProcessPackLoader:
    """Discovers, parses, validates, and stores Process Packs."""

    def __init__(self, db_conn_factory=None):
        self.db_conn_factory = db_conn_factory or db.get_connection
        self._ensure_table()

    def _ensure_table(self):
        with self.db_conn_factory() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS af_process_packs (
                    pack_id TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    name TEXT NOT NULL,
                    owner_role TEXT NOT NULL,
                    current_autonomy_level INTEGER NOT NULL DEFAULT 0,
                    definition JSON NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def parse_dict(self, data: Dict[str, Any]) -> ProcessPack:
        """Parses a dictionary representation into a ProcessPack instance."""
        sipoc_data = data.get("SIPOC", {})
        sipoc = SIPOC(
            suppliers=sipoc_data.get("suppliers", []),
            inputs=sipoc_data.get("inputs", []),
            process_steps=sipoc_data.get("process_steps", []),
            outputs=sipoc_data.get("outputs", []),
            customers=sipoc_data.get("customers", [])
        )

        steps = []
        for s in data.get("steps", []):
            steps.append(
                ProcessStep(
                    id=s["id"],
                    name=s.get("name", s["id"]),
                    actor=s.get("actor", "agent"),
                    role=s.get("role", "specialist"),
                    tool_capabilities=s.get("tool_capabilities", []),
                    gate_checks=s.get("gate_checks", []),
                    reversible=s.get("reversible", True),
                    timeout_seconds=s.get("timeout_seconds", 3600),
                    retry_max=s.get("retry_max", 3)
                )
            )

        kpi_data = data.get("KPIs", {})
        kpis = ProcessKPIs(
            target_cycle_time_seconds=float(kpi_data.get("target_cycle_time_seconds", 3600.0)),
            target_first_pass_yield=float(kpi_data.get("target_first_pass_yield", 0.95)),
            target_cost_per_unit_usd=float(kpi_data.get("target_cost_per_unit_usd", 10.0)),
            target_error_rate=float(kpi_data.get("target_error_rate", 0.02)),
            target_customer_satisfaction=float(kpi_data["target_customer_satisfaction"]) if "target_customer_satisfaction" in kpi_data else None
        )

        andon_rules = []
        for a in data.get("andon", []):
            andon_rules.append(
                AndonRule(
                    condition_id=a["condition_id"],
                    rule_name=a.get("rule_name", a["condition_id"]),
                    trigger_expression=a["trigger_expression"],
                    action=a.get("action", "HALT_AND_ESCALATE"),
                    escalate_to_role=a.get("escalate_to_role", "COO"),
                    description=a.get("description", "")
                )
            )

        autonomy_data = data.get("autonomy", {})
        autonomy = AutonomyCriteria(
            current_level=int(autonomy_data.get("current_level", 0)),
            promotion_criteria=autonomy_data.get("promotion_criteria", {}),
            demotion_criteria=autonomy_data.get("demotion_criteria", {})
        )

        scenarios = []
        for sc in data.get("simulation_scenarios", []):
            scenarios.append(
                SimulationScenario(
                    scenario_id=sc["scenario_id"],
                    name=sc.get("name", sc["scenario_id"]),
                    description=sc.get("description", ""),
                    initial_inputs=sc.get("initial_inputs", {}),
                    expected_outputs=sc.get("expected_outputs", {}),
                    expected_status=sc.get("expected_status", "COMPLETED")
                )
            )

        pack_id = data.get("pack") or data.get("pack_id")
        if not pack_id:
            raise KeyError("Process pack dictionary must include 'pack' or 'pack_id'.")
        pack_name = data.get("name", pack_id)

        pack = ProcessPack(
            pack_id=pack_id,
            version=str(data.get("version", "1.0.0")),
            name=pack_name,
            description=data.get("description", ""),
            owner_role=data.get("owner_role", "COO"),
            trigger_events=data.get("trigger_events", []),
            sipoc=sipoc,
            steps=steps,
            policies=data.get("policies", {}),
            kpis=kpis,
            waste_tags=data.get("waste_tags", []),
            andon=andon_rules,
            autonomy=autonomy,
            simulation_scenarios=scenarios
        )

        errors = pack.validate()
        if errors:
            raise ValueError(f"ProcessPack validation failed for '{pack.pack_id}': {'; '.join(errors)}")

        return pack

    def load_file(self, file_path: str) -> ProcessPack:
        """Loads and validates a single YAML or JSON Process Pack file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Process Pack file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        pack = self.parse_dict(data)
        self.save_pack(pack)
        return pack

    def save_pack(self, pack: ProcessPack) -> None:
        now = time.time()
        with self.db_conn_factory() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO af_process_packs
                (pack_id, version, name, owner_role, current_autonomy_level, definition, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (
                    pack.pack_id,
                    pack.version,
                    pack.name,
                    pack.owner_role,
                    pack.autonomy.current_level,
                    json.dumps(pack.to_dict()),
                    now,
                    now
                )
            )
            conn.commit()

    def get_pack(self, pack_id: str) -> Optional[ProcessPack]:
        with self.db_conn_factory() as conn:
            cur = conn.execute(
                "SELECT definition FROM af_process_packs WHERE pack_id = ?",
                (pack_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            data = json.loads(row[0])
            # Reconstruct
            return self.parse_dict(data)

    def list_packs(self) -> List[Dict[str, Any]]:
        with self.db_conn_factory() as conn:
            cur = conn.execute(
                "SELECT pack_id, version, name, owner_role, current_autonomy_level, status FROM af_process_packs ORDER BY pack_id"
            )
            rows = cur.fetchall()
            return [
                {
                    "pack_id": r[0],
                    "version": r[1],
                    "name": r[2],
                    "owner_role": r[3],
                    "current_autonomy_level": r[4],
                    "status": r[5]
                }
                for r in rows
            ]
