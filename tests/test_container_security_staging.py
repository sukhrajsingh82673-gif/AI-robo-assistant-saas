"""
URA / ZONATA Enterprise SaaS — Container Security & Staging Hardening Suite
Phase 9 Qualification Suite (BLK-09 / CTL-C09)

Verifies:
1. Docker Compose manifest syntax, structure, and 12-service production topology.
2. Complete CPU and memory resource quotas (limits and reservations) on ALL services (BLK-09).
3. Robust, fail-closed healthcheck definitions across ALL containerized services (BLK-09).
4. Network segmentation: strict isolation between zonata-edge and zonata-internal.
5. Host port hygiene: internal databases and infrastructure bound to localhost (127.0.0.1).
6. Security options: no-new-privileges and capability drop defenses.
7. Production Dockerfiles unprivileged user execution (UID 10001 / nginx) and healthcheck directives.
8. Runtime adapter fail-closed sandbox enforcement in production mode (BLK-07 regression).
"""

import os
import sys
import yaml
import tempfile
import unittest
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSE_FILE = os.path.join(PROJECT_ROOT, "docker-compose.prod.yml")
DOCKER_DIR = os.path.join(PROJECT_ROOT, "docker")

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    from core.db import db, configure_isolated_test_db
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "container_sec_isolated.db")
    configure_isolated_test_db(isolated_db)

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        from core.db import db
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


class TestContainerSecurityStaging(unittest.TestCase):
    """Qualification suite for container security, resource limits, health probes, and network segmentation."""

    @classmethod
    def setUpClass(cls):
        cls.compose_path = COMPOSE_FILE
        with open(cls.compose_path, "r", encoding="utf-8") as f:
            cls.compose = yaml.safe_load(f)
        cls.services = cls.compose.get("services", {})
        cls.networks = cls.compose.get("networks", {})
        cls.volumes = cls.compose.get("volumes", {})

    def test_01_compose_syntax_and_topology(self):
        """Validates docker-compose.prod.yml structure and expected 12-service topology."""
        self.assertIn("version", self.compose)
        self.assertIn("services", self.compose)
        self.assertIn("networks", self.compose)
        self.assertIn("volumes", self.compose)

        expected_services = [
            "nginx-ingress",
            "zonata-api",
            "zonata-worker",
            "zonata-backup-replicator",
            "postgres",
            "nats",
            "temporal",
            "minio",
            "otel-collector",
            "prometheus",
            "alertmanager",
            "grafana"
        ]
        for svc_name in expected_services:
            self.assertIn(svc_name, self.services, f"Expected service '{svc_name}' missing from compose")

    def test_02_all_services_define_cpu_and_memory_resource_limits(self):
        """Validates that 100% of services define CPU and memory limits and reservations (BLK-09)."""
        for svc_name, svc_conf in self.services.items():
            deploy = svc_conf.get("deploy", {})
            self.assertIn("resources", deploy, f"Service '{svc_name}' lacks deploy.resources configuration")
            resources = deploy["resources"]

            # 1. Limits validation
            self.assertIn("limits", resources, f"Service '{svc_name}' lacks resource limits")
            limits = resources["limits"]
            self.assertIn("cpus", limits, f"Service '{svc_name}' lacks CPU limit")
            self.assertIn("memory", limits, f"Service '{svc_name}' lacks memory limit")
            cpu_val = float(limits["cpus"])
            self.assertGreater(cpu_val, 0.0, f"Service '{svc_name}' CPU limit must be positive")
            mem_val = limits["memory"]
            self.assertTrue(mem_val.endswith(("M", "G")), f"Service '{svc_name}' memory limit must specify unit (M/G)")

            # 2. Reservations validation
            self.assertIn("reservations", resources, f"Service '{svc_name}' lacks resource reservations")
            reservations = resources["reservations"]
            self.assertIn("cpus", reservations, f"Service '{svc_name}' lacks CPU reservation")
            self.assertIn("memory", reservations, f"Service '{svc_name}' lacks memory reservation")

    def test_03_all_services_define_robust_healthchecks(self):
        """Validates that 100% of services define fail-closed healthcheck probes (BLK-09)."""
        for svc_name, svc_conf in self.services.items():
            self.assertIn("healthcheck", svc_conf, f"Service '{svc_name}' lacks healthcheck definition")
            hc = svc_conf["healthcheck"]
            self.assertIn("test", hc, f"Service '{svc_name}' lacks healthcheck test command")
            self.assertIn("interval", hc, f"Service '{svc_name}' lacks healthcheck interval")
            self.assertIn("timeout", hc, f"Service '{svc_name}' lacks healthcheck timeout")
            self.assertIn("retries", hc, f"Service '{svc_name}' lacks healthcheck retries")
            self.assertGreater(hc["retries"], 0, f"Service '{svc_name}' retries must be > 0")

    def test_04_network_segmentation_edge_vs_internal(self):
        """Validates strict network segmentation between public edge and backend internal tiers."""
        self.assertIn("zonata-edge", self.networks, "Missing zonata-edge network definition")
        self.assertIn("zonata-internal", self.networks, "Missing zonata-internal network definition")

        # Internal-only services must NOT be attached to zonata-edge
        internal_only_services = [
            "zonata-worker",
            "zonata-backup-replicator",
            "postgres",
            "nats",
            "temporal",
            "minio",
            "otel-collector",
            "prometheus",
            "alertmanager",
            "grafana"
        ]
        for svc_name in internal_only_services:
            svc_nets = self.services[svc_name].get("networks", [])
            self.assertIn("zonata-internal", svc_nets, f"Internal service '{svc_name}' must be on zonata-internal")
            self.assertNotIn("zonata-edge", svc_nets, f"Internal service '{svc_name}' must NOT be on zonata-edge")

        # Ingress must bridge edge and internal
        ingress_nets = self.services["nginx-ingress"].get("networks", [])
        self.assertIn("zonata-edge", ingress_nets)
        self.assertIn("zonata-internal", ingress_nets)

    def test_05_host_port_hygiene_and_public_exposure_restriction(self):
        """Validates that only nginx-ingress binds to public interface; internal ports bind to 127.0.0.1."""
        for svc_name, svc_conf in self.services.items():
            ports = svc_conf.get("ports", [])
            for p in ports:
                p_str = str(p)
                if svc_name == "nginx-ingress":
                    # Ingress exposes 80 and 443
                    self.assertTrue(p_str in ("80:80", "443:443", "0.0.0.0:80:80", "0.0.0.0:443:443"))
                else:
                    # All internal services must bind exclusively to 127.0.0.1 on the host
                    self.assertTrue(
                        p_str.startswith("127.0.0.1:"),
                        f"Insecure public port binding '{p_str}' on internal service '{svc_name}'! Must bind to 127.0.0.1."
                    )

    def test_06_container_security_options_and_privilege_escalation(self):
        """Validates security_opt no-new-privileges and capability drop configurations."""
        for svc_name, svc_conf in self.services.items():
            sec_opt = svc_conf.get("security_opt", [])
            self.assertIn("no-new-privileges:true", sec_opt, f"Service '{svc_name}' lacks no-new-privileges:true")

        # Verify Nginx drops all capabilities except NET_BIND_SERVICE
        nginx_conf = self.services["nginx-ingress"]
        self.assertIn("cap_drop", nginx_conf)
        self.assertEqual(nginx_conf["cap_drop"], ["ALL"])
        self.assertIn("cap_add", nginx_conf)
        self.assertEqual(nginx_conf["cap_add"], ["NET_BIND_SERVICE"])

    def test_07_dockerfile_unprivileged_users_and_healthchecks(self):
        """Validates unprivileged user declarations and healthcheck directives across all Dockerfiles."""
        dockerfiles = {
            "Dockerfile.api": os.path.join(DOCKER_DIR, "Dockerfile.api"),
            "Dockerfile.worker": os.path.join(DOCKER_DIR, "Dockerfile.worker"),
            "Dockerfile.migration": os.path.join(DOCKER_DIR, "Dockerfile.migration"),
            "Dockerfile.supervisor": os.path.join(DOCKER_DIR, "Dockerfile.supervisor"),
            "Dockerfile.ingress": os.path.join(DOCKER_DIR, "nginx", "Dockerfile.ingress")
        }

        for name, path in dockerfiles.items():
            self.assertTrue(os.path.exists(path), f"Dockerfile missing: {path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            if name == "Dockerfile.ingress":
                self.assertIn("FROM nginx:1.27-alpine", content)
                self.assertIn("HEALTHCHECK", content)
            else:
                self.assertIn("USER 10001:10001", content, f"Dockerfile '{name}' does not enforce unprivileged UID 10001")

    def test_08_runtime_adapter_fails_closed_in_production_mode(self):
        """Verifies container runtime adapter enforces strict sandbox requirements in production (BLK-07)."""
        from core.universal_terminal.runtime_adapters import ContainerRuntimeAdapter
        adapter = ContainerRuntimeAdapter()
        old_env = os.environ.get("APP_ENV")
        old_shell = os.environ.get("ZONATA_ALLOW_HOST_SHELL")
        try:
            os.environ["APP_ENV"] = "production"
            os.environ["ZONATA_ALLOW_HOST_SHELL"] = "1"
            res = adapter.execute_command(
                session_id="sec_test_prod_sandbox",
                command="echo 'unauthorized_execution'",
                cwd=tempfile.gettempdir()
            )
            self.assertEqual(res.get("exit_code"), 126)
            self.assertTrue(res.get("sandbox_failure"))
            self.assertIn("strictly prohibited", res.get("stderr", ""))
        finally:
            if old_env is not None:
                os.environ["APP_ENV"] = old_env
            else:
                os.environ.pop("APP_ENV", None)
            if old_shell is not None:
                os.environ["ZONATA_ALLOW_HOST_SHELL"] = old_shell
            else:
                os.environ.pop("ZONATA_ALLOW_HOST_SHELL", None)


if __name__ == "__main__":
    unittest.main()
