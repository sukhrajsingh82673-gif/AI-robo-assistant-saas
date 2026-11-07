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

        # 6. Enterprise Agent Cloud & Coworker 3.0 Telemetry
        # Every field here is derived from a live source. Nothing is hardcoded:
        # if a subsystem is not configured, the snapshot says so.
        agent_cloud_telemetry = self._agent_cloud_telemetry(active_workers)

        return {
            "product": "ZONATA Universal AI Co-Worker",
            "version": "3.0",
            "edition": "Coworker 3.0",
            "sovereign_tenant_id": self.engine.tenant_id,
            "timestamp": time.time(),
            "killswitch_engaged": killswitch_active,
            "metrics": {
                "active_coworkers_count": len(active_workers),
                "fleet_nodes_count": len(fleet_nodes),
                "runtimes_registered_count": len(runtimes_info),
                "total_routing_decisions": routing_history_count,
                "background_missions_count": len(missions_info),
                "agent_cloud_capacity": agent_cloud_telemetry.get("total_registered_agents", 0)
            },
            "agent_cloud": agent_cloud_telemetry,
            "active_workers": active_workers,
            "fleet_nodes": fleet_nodes,
            "specialized_runtimes": runtimes_info,
            "background_missions": missions_info
        }

    # --- Live telemetry probes -------------------------------------------------

    def _agent_cloud_telemetry(self, active_workers: List[Dict[str, Any]]) -> Dict[str, Any]:
        cloud = {
            "catalog_status": "NOT_INITIALIZED",
            "total_registered_agents": 0,
            "registered_agents": 0,
            "available_agents": 0,
            "active_agents": len(active_workers),
            "busy_agents": 0,
            "suspended_agents": 0,
            "failed_agents": 0,
            "max_bounded_workers": 0,
            "queue_depth": 0,
            "operating_mode": "UNKNOWN",
        }
        registry = getattr(self.engine, "agent_cloud", None)
        if registry is None:
            # Do not construct a registry here: its constructor starts worker
            # threads and creates a catalog database.
            cloud["catalog_status"] = "NOT_INITIALIZED"
            cloud["verified_integrations"] = self._integration_probes()
            cloud["cybersecurity"] = self._cybersecurity_snapshot()
            return cloud
        try:
            breakdown = registry.get_status_breakdown()
            telemetry = registry.get_scheduling_telemetry()
            cloud.update({
                "catalog_status": "ONLINE",
                "total_registered_agents": telemetry.get("total_registered_agents", sum(breakdown.values())),
                "registered_agents": breakdown.get("REGISTERED", 0),
                "available_agents": breakdown.get("REGISTERED", 0),
                "busy_agents": breakdown.get("BUSY", 0),
                "suspended_agents": breakdown.get("SUSPENDED", 0),
                "failed_agents": breakdown.get("FAILED", 0),
                "max_bounded_workers": telemetry.get("max_bounded_workers", 0),
                "queue_depth": telemetry.get("queue_depth", 0),
                "operating_mode": "BOUNDED_POOL",
            })
        except Exception as exc:
            cloud["catalog_status"] = f"UNAVAILABLE: {type(exc).__name__}"

        cloud["verified_integrations"] = self._integration_probes()
        cloud["cybersecurity"] = self._cybersecurity_snapshot()
        return cloud

    def _integration_probes(self) -> Dict[str, str]:
        import os
        import shutil
        probes: Dict[str, str] = {}

        # Hermes inference: needs a configured and reachable endpoint.
        try:
            from .hermes_agent_v3 import HermesInferenceGateway
            gw = HermesInferenceGateway()
            conn = gw.check_connection()
            probes["hermes_runtime"] = (
                "ENDPOINT_ONLINE" if conn.get("inference_available") else "LLM_UNAVAILABLE"
            )
        except Exception as exc:
            probes["hermes_runtime"] = f"UNAVAILABLE: {type(exc).__name__}"

        # OpenCode engine: implemented, but qualification is per-mission.
        try:
            from .opencode_engine import OpenCodeEngine  # noqa: F401
            probes["opencode_engine"] = "IMPLEMENTED_UNQUALIFIED"
        except Exception as exc:
            probes["opencode_engine"] = f"UNAVAILABLE: {type(exc).__name__}"

        # OpenCloud: only "operational" when at least one node is registered.
        try:
            from .opencloud_engine import OpenCloudEngine
            manager = getattr(self.engine, "opencloud_manager", None)
            if manager is None:
                probes["opencloud_remote_workers"] = "NO_NODES_CONFIGURED"
            else:
                nodes = manager.list_nodes()
                probes["opencloud_remote_workers"] = (
                    f"{len(nodes)}_NODE(S)_REGISTERED" if nodes else "NO_NODES_CONFIGURED"
                )
        except Exception as exc:
            probes["opencloud_remote_workers"] = f"UNAVAILABLE: {type(exc).__name__}"

        # OpenDots / X11 perception: depends on a display and capture tooling.
        has_display = bool(os.environ.get("DISPLAY"))
        has_tools = all(shutil.which(t) for t in ("xdotool", "wmctrl", "scrot"))
        probes["opendots_computer_use"] = (
            "X11_READY" if has_display and has_tools else
            ("NO_DISPLAY" if not has_display else "CAPTURE_TOOLING_MISSING")
        )

        # Terminal isolation: container runtime presence.
        probes["terminal_sandboxed"] = (
            "CONTAINER_AVAILABLE" if shutil.which("docker") else "HOST_EXECUTION_NO_CONTAINER"
        )

        # MCP registry: count registered servers.
        try:
            from ..mcp_interoperability_runtime import MCPGateway
            gateway = getattr(self.engine, "mcp_gateway", None)
            servers = gateway.list_servers() if gateway is not None and hasattr(gateway, "list_servers") else []
            probes["mcp_registry"] = f"{len(servers)}_SERVER(S)_REGISTERED"
        except Exception as exc:
            probes["mcp_registry"] = f"UNAVAILABLE: {type(exc).__name__}"

        return probes

    def _cybersecurity_snapshot(self) -> Dict[str, Any]:
        snapshot = {
            "patrol_status": "NOT_RUN",
            "threat_level": "UNKNOWN",
            "active_incidents": 0,
            "critical_findings": 0,
            "high_findings": 0,
            "last_patrol_timestamp": None,
        }
        try:
            from .defense_monitor import DefensiveCybersecurityMonitor
            monitor = getattr(self.engine, "defense_monitor", None)
            if monitor is None:
                monitor = DefensiveCybersecurityMonitor.get_instance()
            findings = getattr(monitor, "findings_history", []) or []
            critical = sum(1 for f in findings if getattr(getattr(f, "severity", None), "value", "") == "CRITICAL")
            high = sum(1 for f in findings if getattr(getattr(f, "severity", None), "value", "") == "HIGH")
            snapshot.update({
                "patrol_status": "COMPLETED" if getattr(monitor, "last_scan_time", None) else "NOT_RUN",
                "threat_level": "CRITICAL" if critical else ("HIGH" if high else "NOMINAL"),
                "critical_findings": critical,
                "high_findings": high,
                "last_patrol_timestamp": getattr(monitor, "last_scan_time", None),
            })
        except Exception as exc:
            snapshot["patrol_status"] = f"UNAVAILABLE: {type(exc).__name__}"
        return snapshot
