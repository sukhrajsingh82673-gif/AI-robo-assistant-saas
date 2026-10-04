"""
ZONATA Universal AI Co-worker Fabric — Observability Dashboard Service
Provides single-pane observability into the unified Co-Worker persona while
enabling drill-down into specialized runtimes (Hermes, OpenHands, OpenClaw, Browser, CUA),
distributed fleet nodes, memory tiers, active background missions, and kill switches.
"""

from typing import Dict, List, Optional, Any
import time

class CoworkerDashboardService:
    """
    Telemetry aggregator for the ZONATA Universal AI Co-Worker.
    """

    def __init__(self, engine: Any):
        self.engine = engine

    def get_dashboard_snapshot(self) -> Dict[str, Any]:
        """
        Gathers comprehensive live status across all co-worker subsystems.
        """
        # 1. Active Workers & Supervisor Health
        active_workers = []
        if hasattr(self.engine, "supervisor"):
            for w in self.engine.supervisor.list_workers():
                active_workers.append({
                    "worker_id": w.worker_id,
                    "role": w.role,
                    "department": w.department,
                    "status": w.status,
                    "risk_limit": w.risk_limit.value if hasattr(w.risk_limit, "value") else str(w.risk_limit)
                })

        # 2. Node Health from Fleet Registry
        fleet_nodes = []
        if hasattr(self.engine, "node_registry"):
            nodes = self.engine.node_registry.list_nodes()
            for n in nodes:
                fleet_nodes.append({
                    "node_id": n.node_id,
                    "platform": n.platform.value if hasattr(n.platform, "value") else str(n.platform),
                    "node_type": n.node_type.value if hasattr(n.node_type, "value") else str(n.node_type),
                    "status": (n.state.value if hasattr(n.state, "value") else str(n.state)) if hasattr(n, "state") else str(getattr(n, "status", "REGISTERED")),
                    "last_heartbeat_sec_ago": round(time.time() - n.last_heartbeat, 1)
                })

        # 3. Active Runtimes & Routing History
        runtimes_info = []
        routing_history_count = 0
        if hasattr(self.engine, "runtime_router"):
            for r in self.engine.runtime_router.list_runtimes():
                runtimes_info.append({
                    "runtime_id": r.runtime_id(),
                    "type": r.runtime_type(),
                    "version": r.version(),
                    "capabilities_count": len(r.supported_capabilities())
                })
            routing_history_count = len(self.engine.runtime_router.get_routing_history())

        # 4. Kill Switch Status
        killswitch_active = False
        if hasattr(self.engine, "killswitch"):
            killswitch_active = self.engine.killswitch.is_activated("GLOBAL", "*") or \
                                self.engine.killswitch.is_activated("TENANT", self.engine.tenant_id)

        # 5. Background Missions
        missions_info = []
        if hasattr(self.engine, "background_dispatcher"):
            for m in self.engine.background_dispatcher.list_missions():
                missions_info.append({
                    "mission_id": m.mission_id,
                    "prompt": m.prompt[:60] + "..." if len(m.prompt) > 60 else m.prompt,
                    "status": m.status,
                    "progress_percent": m.progress_percent,
                    "current_stage": m.current_stage,
                    "subworkers_count": len(m.subworkers)
                })

        return {
            "product": "ZONATA Universal AI Co-Worker",
            "sovereign_tenant_id": self.engine.tenant_id,
            "timestamp": time.time(),
            "killswitch_engaged": killswitch_active,
            "metrics": {
                "active_coworkers_count": len(active_workers),
                "fleet_nodes_count": len(fleet_nodes),
                "runtimes_registered_count": len(runtimes_info),
                "total_routing_decisions": routing_history_count,
                "background_missions_count": len(missions_info)
            },
            "active_workers": active_workers,
            "fleet_nodes": fleet_nodes,
            "specialized_runtimes": runtimes_info,
            "background_missions": missions_info
        }
