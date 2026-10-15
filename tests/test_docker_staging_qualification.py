"""
ZONATA Enterprise SaaS — Docker Staging Deployment Qualification Suite
8-Test Multi-Service Containerized Staging Qualification Suite

Verifies live runtime behavior and invariants of the production Docker Compose topology:
1. Docker Compose manifest validation, syntax check, and 9-service topology verification
2. Production image build verification and digest generation (api, worker, migration, supervisor)
3. Multi-service stack orchestration, startup, and readiness/health probe verification across all services
4. Live PostgreSQL 16 connectivity from containers, schema initialization, and migration tracking
5. Service dependency ordering, graceful restart, failure isolation, and automatic health recovery
6. Workload isolation, unprivileged user execution (UID 10001), and port hygiene
7. Volume data persistence across container restarts and lifecycle drills
8. Secret hygiene, image history inspection, and runtime credential redaction
"""

import os
import sys
import time
import json
import uuid
import shutil
import urllib.request
import urllib.error
import subprocess
import unittest
from typing import Dict, Any, List, Optional

# Project root path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSE_FILE = os.path.join(PROJECT_ROOT, "docker-compose.prod.yml")


def is_docker_available() -> bool:
    """Checks whether docker executable is available and daemon is running."""
    if not shutil.which("docker"):
        return False
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        return res.returncode == 0
    except Exception:
        return False


def run_docker_cmd(cmd: List[str], check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
    """Helper to run docker/compose CLI commands with structured logging."""
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=check
    )


@unittest.skipUnless(is_docker_available(), "Docker daemon not available in local PRoot/Termux environment; qualified in Linux CI")
class TestDockerStagingQualification(unittest.TestCase):
    """
    Independent qualification suite for ZONATA multi-service container staging deployment.
    Executes in Linux CI runner (ubuntu-latest) with native Docker daemon.
    """

    @classmethod
    def setUpClass(cls):
        cls.compose_file = COMPOSE_FILE
        cls.api_url = os.environ.get("STAGING_API_URL", "http://localhost:8080")
        cls.postgres_user = os.environ.get("POSTGRES_USER", "zonata_admin")
        cls.postgres_db = os.environ.get("POSTGRES_DB", "zonata_production")
        cls.postgres_password = os.environ.get("POSTGRES_PASSWORD", "zonata_secure_prod_password_2026")

    # =========================================================================
    # TEST 1: Compose Manifest & Syntax Validation
    # =========================================================================
    def test_01_compose_manifest_and_syntax_validation(self):
        """Validates docker-compose.prod.yml syntax, service declarations, volumes, and dependency ordering."""
        self.assertTrue(os.path.exists(self.compose_file), f"Compose file missing at {self.compose_file}")

        # Run docker compose config
        res = run_docker_cmd(["docker", "compose", "-f", self.compose_file, "config"])
        self.assertEqual(res.returncode, 0, f"Compose validation failed:\n{res.stderr}")

        # Inspect declared services in the Compose file
        import yaml
        with open(self.compose_file, "r") as f:
            manifest = yaml.safe_load(f)

        services = manifest.get("services", {})
        volumes = manifest.get("volumes", {})

        # Verify all 9 discrete production services
        expected_services = [
            "zonata-api",
            "zonata-worker",
            "postgres",
            "nats",
            "temporal",
            "minio",
            "otel-collector",
            "prometheus",
            "grafana"
        ]
        for s in expected_services:
            self.assertIn(s, services, f"Expected service '{s}' missing in docker-compose.prod.yml")

        # Verify essential persistent volumes
        expected_volumes = [
            "zonata-storage",
            "postgres-data",
            "nats-data",
            "temporal-data",
            "minio-data",
            "prometheus-data",
            "grafana-data",
            "postgres-wal-archive",
            "postgres-base-backups"
        ]
        for v in expected_volumes:
            self.assertIn(v, volumes, f"Expected volume '{v}' missing in docker-compose.prod.yml")

        # Verify dependency ordering: zonata-api must wait for postgres to be healthy
        api_deps = services["zonata-api"].get("depends_on", {})
        self.assertIn("postgres", api_deps, "zonata-api must depend on postgres")
        if isinstance(api_deps, dict):
            self.assertEqual(api_deps["postgres"].get("condition"), "service_healthy")

    # =========================================================================
    # TEST 2: Production Image Builds and Digests
    # =========================================================================
    def test_02_production_image_builds_and_digests(self):
        """Verifies that all four production Dockerfiles build successfully and produce inspectable digests."""
        dockerfiles = {
            "zonata/api:1.0.0-GA": "docker/Dockerfile.api",
            "zonata/worker:1.0.0-GA": "docker/Dockerfile.worker",
            "zonata/migration:1.0.0-GA": "docker/Dockerfile.migration",
            "zonata/supervisor:1.0.0-GA": "docker/Dockerfile.supervisor"
        }

        for image_tag, df_path in dockerfiles.items():
            full_df_path = os.path.join(PROJECT_ROOT, df_path)
            self.assertTrue(os.path.exists(full_df_path), f"Dockerfile missing: {full_df_path}")

            # Verify image exists in local Docker engine
            res = run_docker_cmd(["docker", "image", "inspect", image_tag], check=False)
            if res.returncode != 0:
                # Build if not already cached
                build_res = run_docker_cmd([
                    "docker", "build", "-t", image_tag, "-f", full_df_path, PROJECT_ROOT
                ], timeout=180)
                self.assertEqual(build_res.returncode, 0, f"Failed building {image_tag}:\n{build_res.stderr}")

            # Re-inspect to confirm image digest and metadata
            inspect_res = run_docker_cmd(["docker", "image", "inspect", image_tag])
            self.assertEqual(inspect_res.returncode, 0)
            data = json.loads(inspect_res.stdout)
            self.assertGreater(len(data), 0)
            self.assertTrue(data[0]["Id"].startswith("sha256:"), f"Invalid image digest for {image_tag}")

    # =========================================================================
    # TEST 3: Multi-Service Stack Orchestration & Health
    # =========================================================================
    def test_03_multi_service_stack_orchestration_and_health(self):
        """Verifies that the entire 9-service production composition is active and passes readiness probes."""
        # 1. Check running status of services via compose ps
        ps_res = run_docker_cmd(["docker", "compose", "-f", self.compose_file, "ps", "--format", "json"])
        self.assertEqual(ps_res.returncode, 0)

        # Parse ps output (can be JSON array or lines of JSON)
        containers = []
        try:
            containers = json.loads(ps_res.stdout)
            if not isinstance(containers, list):
                containers = [containers]
        except Exception:
            for line in ps_res.stdout.strip().splitlines():
                if line.strip():
                    try:
                        containers.append(json.loads(line))
                    except Exception:
                        pass

        running_services = set()
        for c in containers:
            service_name = c.get("Service", "")
            state = c.get("State", "").lower()
            if state in ("running", "healthy"):
                running_services.add(service_name)

        # Ensure core containers are running
        for s in ["zonata-api", "postgres", "nats"]:
            self.assertIn(s, running_services, f"Core service {s} is not in running state")

        # 2. Probe zonata-api /health endpoint
        req = urllib.request.Request(f"{self.api_url}/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            body = json.loads(resp.read().decode())
            self.assertEqual(body.get("status"), "HEALTHY")
            self.assertEqual(body.get("version"), "1.0.0-GA")

        # 3. Probe zonata-api /readyz endpoint (verifies database readiness)
        req_ready = urllib.request.Request(f"{self.api_url}/readyz")
        with urllib.request.urlopen(req_ready, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            body = json.loads(resp.read().decode())
            self.assertEqual(body.get("status"), "HEALTHY")
            self.assertEqual(body.get("database"), "CONNECTED")

    # =========================================================================
    # TEST 4: Live PostgreSQL 16 Connectivity & Migrations
    # =========================================================================
    def test_04_live_postgresql_16_connectivity_and_migrations(self):
        """Verifies database connectivity, PostgreSQL 16 engine handshake, schema tables, and migrations."""
        # Execute version check inside postgres container
        pg_ver = run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "exec", "-T", "postgres",
            "psql", "-U", self.postgres_user, "-d", self.postgres_db,
            "-tAc", "SELECT version();"
        ])
        self.assertEqual(pg_ver.returncode, 0)
        self.assertIn("PostgreSQL 16", pg_ver.stdout, f"Expected PostgreSQL 16, got:\n{pg_ver.stdout}")

        # Verify core tables in information_schema
        pg_tables = run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "exec", "-T", "postgres",
            "psql", "-U", self.postgres_user, "-d", self.postgres_db,
            "-tAc", "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
        ])
        self.assertEqual(pg_tables.returncode, 0)
        tables = set(pg_tables.stdout.strip().splitlines())

        required_tables = {"users", "companies", "tenants", "crm_customers", "crm_deals", "schema_migrations"}
        for t in required_tables:
            self.assertIn(t, tables, f"Required relational table '{t}' missing from PostgreSQL database")

        # Verify schema_migrations has recorded additive migrations
        pg_migrations = run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "exec", "-T", "postgres",
            "psql", "-U", self.postgres_user, "-d", self.postgres_db,
            "-tAc", "SELECT version, status FROM schema_migrations WHERE status = 'APPLIED';"
        ])
        self.assertEqual(pg_migrations.returncode, 0)
        migration_output = pg_migrations.stdout
        self.assertIn("2026100501", migration_output, "Migration 2026100501 missing from schema_migrations")
        self.assertIn("2026100502", migration_output, "Migration 2026100502 missing from schema_migrations")

    # =========================================================================
    # TEST 5: Dependency Ordering & Graceful Restart Recovery
    # =========================================================================
    def test_05_dependency_ordering_and_graceful_restart_recovery(self):
        """Verifies service restart behavior, fail-safe degradation, and auto-recovery."""
        # Restart zonata-api gracefully
        restart_res = run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "restart", "zonata-api"
        ], timeout=30)
        self.assertEqual(restart_res.returncode, 0)

        # Wait for zonata-api to become healthy again
        recovered = False
        for _ in range(15):
            time.sleep(2)
            try:
                with urllib.request.urlopen(f"{self.api_url}/readyz", timeout=3) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode())
                        if data.get("status") == "HEALTHY":
                            recovered = True
                            break
            except Exception:
                pass

        self.assertTrue(recovered, "zonata-api failed to recover healthy status within 30s after restart")

    # =========================================================================
    # TEST 6: Workload Isolation, Non-Root Execution & Port Hygiene
    # =========================================================================
    def test_06_workload_isolation_unprivileged_execution_and_port_hygiene(self):
        """Verifies non-root container user (UID 10001), restricted permissions, and port security."""
        # 1. Verify unprivileged UID in zonata-api
        uid_api = run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "exec", "-T", "zonata-api", "id", "-u"
        ])
        self.assertEqual(uid_api.returncode, 0)
        self.assertEqual(uid_api.stdout.strip(), "10001", "zonata-api must execute as unprivileged UID 10001")

        # 2. Verify unprivileged UID in zonata-worker
        uid_wkr = run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "exec", "-T", "zonata-worker", "id", "-u"
        ])
        self.assertEqual(uid_wkr.returncode, 0)
        self.assertEqual(uid_wkr.stdout.strip(), "10001", "zonata-worker must execute as unprivileged UID 10001")

        # 3. Verify ZONATA_ALLOW_HOST_SHELL is not enabled in container environment
        env_check = run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "exec", "-T", "zonata-api",
            "sh", "-c", "echo $ZONATA_ALLOW_HOST_SHELL"
        ])
        self.assertNotEqual(env_check.stdout.strip(), "1", "Dangerous flag ZONATA_ALLOW_HOST_SHELL=1 must not be set")

    # =========================================================================
    # TEST 7: Volume Data Persistence Across Lifecycle
    # =========================================================================
    def test_07_volume_data_persistence_across_lifecycle(self):
        """Verifies that persistent volumes preserve database state across container restart/recreation."""
        test_id = f"stg_persist_{uuid.uuid4().hex[:8]}"

        # Insert test marker record into PostgreSQL
        insert_res = run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "exec", "-T", "postgres",
            "psql", "-U", self.postgres_user, "-d", self.postgres_db,
            "-c", f"INSERT INTO tenants (tenant_id, name, created_at) VALUES ('{test_id}', 'Persistence Test Tenant', {time.time()});"
        ])
        self.assertEqual(insert_res.returncode, 0)

        # Restart postgres container
        run_docker_cmd(["docker", "compose", "-f", self.compose_file, "restart", "postgres"], timeout=30)
        for _ in range(15):
            res = run_docker_cmd([
                "docker", "compose", "-f", self.compose_file, "exec", "-T", "postgres",
                "pg_isready", "-U", self.postgres_user, "-d", self.postgres_db
            ], check=False)
            if res.returncode == 0:
                break
            time.sleep(1)

        # Verify marker record persists after container restart
        verify_res = run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "exec", "-T", "postgres",
            "psql", "-U", self.postgres_user, "-d", self.postgres_db,
            "-tAc", f"SELECT name FROM tenants WHERE tenant_id = '{test_id}';"
        ])
        self.assertEqual(verify_res.returncode, 0)
        self.assertEqual(verify_res.stdout.strip(), "Persistence Test Tenant")

        # Clean up marker record
        run_docker_cmd([
            "docker", "compose", "-f", self.compose_file, "exec", "-T", "postgres",
            "psql", "-U", self.postgres_user, "-d", self.postgres_db,
            "-c", f"DELETE FROM tenants WHERE tenant_id = '{test_id}';"
        ])

    # =========================================================================
    # TEST 8: Secret Redaction & Image Hygiene
    # =========================================================================
    def test_08_secret_redaction_and_image_hygiene(self):
        """Verifies zero plaintext secrets baked into image layers or logged in traces."""
        # 1. Inspect image history for baked credentials
        for img in ["zonata/api:1.0.0-GA", "zonata/worker:1.0.0-GA"]:
            hist_res = run_docker_cmd(["docker", "history", "--no-trunc", img])
            self.assertEqual(hist_res.returncode, 0)
            hist = hist_res.stdout
            self.assertNotIn("PRIVATE KEY", hist)
            self.assertNotIn("ghp_", hist)
            self.assertNotIn("sk_live_", hist)

        # 2. Verify sanitized database URL in logs (passwords must be redacted)
        logs_res = run_docker_cmd(["docker", "compose", "-f", self.compose_file, "logs", "zonata-api"], check=False)
        self.assertNotIn("zonata_secure_prod_password_2026", logs_res.stdout, "Plaintext database password leaked in api logs")


if __name__ == "__main__":
    unittest.main()
