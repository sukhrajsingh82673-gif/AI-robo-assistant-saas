"""
Unit & SRE Qualification Tests for Production Observability, Alerting & SLOs
Validates BLK-05 resolution:
- Prometheus Alert Rules syntax, coverage, severities, runbooks
- SRE Metrics Registry, latencies, database pool counters, disk utilization
- Live Prometheus standard text exposition format
- ProductionConfigValidator Gate 7 alert rules enforcement
"""

import os
import re
import shutil
import tempfile
import unittest
import yaml

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    from core.db import db, configure_isolated_test_db
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "isolated_obs.db")
    configure_isolated_test_db(isolated_db)
    with db.get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS transactional_outbox (id TEXT PRIMARY KEY, status TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS executive_incidents (id TEXT PRIMARY KEY, current_state TEXT)")
        conn.commit()

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        from core.db import db
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()

class TestProductionObservabilityAlerting(unittest.TestCase):

    def setUp(self):
        from core.observability_stack import sre_metrics
        sre_metrics.reset()
        self.rules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "prometheus_rules.yml"))
        self.prom_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "prometheus.yml"))
        self.compose_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docker-compose.prod.yml"))

    def test_prometheus_rules_syntax_and_structure(self):
        """Validates that config/prometheus_rules.yml is well-formed Prometheus 2.x YAML."""
        self.assertTrue(os.path.exists(self.rules_path), f"Rules file missing: {self.rules_path}")
        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIn("groups", data, "Alert rules file must contain top-level 'groups'")
        self.assertIsInstance(data["groups"], list, "'groups' must be a list")
        self.assertGreater(len(data["groups"]), 0, "Must contain at least one alert group")

        group = data["groups"][0]
        self.assertEqual(group.get("name"), "zonata_platform_alerts")
        self.assertIn("rules", group)
        self.assertIsInstance(group["rules"], list)
        self.assertGreaterEqual(len(group["rules"]), 10, "Must define at least 10 core alert rules")

    def test_required_alert_rules_presence(self):
        """Validates that all 12 mandatory platform alerts are explicitly defined."""
        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        rules = data["groups"][0]["rules"]
        alert_names = {r.get("alert") for r in rules}

        mandatory_alerts = [
            "DatabaseServiceDown",
            "DatabaseConnectionPoolSaturated",
            "DatabaseConnectionPoolExhausted",
            "PostgresWalArchivingFailed",
            "HighHttp5xxErrorRate",
            "ApiLatencyP95SlaBreach",
            "HighDiskUtilizationWarning",
            "CriticalDiskUtilization",
            "WorkerCrashLoopDetected",
            "AuthenticationAnomalySpike",
            "OutboxQueueStalled",
            "ExecutiveIncidentActive"
        ]

        for expected in mandatory_alerts:
            self.assertIn(expected, alert_names, f"Mandatory alert rule missing: {expected}")

    def test_alert_rules_labels_and_severities(self):
        """Validates that every alert rule defines valid severity and tier labels."""
        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        rules = data["groups"][0]["rules"]
        valid_severities = {"critical", "warning", "info"}
        valid_tiers = {"database", "storage", "api", "infrastructure", "worker", "security", "governance"}

        for r in rules:
            alert = r.get("alert")
            self.assertIn("expr", r, f"Alert {alert} missing PromQL 'expr'")
            self.assertIn("for", r, f"Alert {alert} missing 'for' duration")
            self.assertIn("labels", r, f"Alert {alert} missing 'labels'")

            labels = r["labels"]
            self.assertIn("severity", labels, f"Alert {alert} missing 'severity' label")
            self.assertIn(labels["severity"], valid_severities, f"Alert {alert} has invalid severity: {labels['severity']}")
            self.assertIn("tier", labels, f"Alert {alert} missing 'tier' label")
            self.assertIn(labels["tier"], valid_tiers, f"Alert {alert} has invalid tier: {labels['tier']}")

    def test_alert_rules_annotations_and_runbooks(self):
        """Validates that every alert rule includes summary, description, and actionable runbook URL."""
        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        rules = data["groups"][0]["rules"]
        for r in rules:
            alert = r.get("alert")
            self.assertIn("annotations", r, f"Alert {alert} missing 'annotations'")
            annotations = r["annotations"]
            self.assertIn("summary", annotations, f"Alert {alert} missing summary")
            self.assertIn("description", annotations, f"Alert {alert} missing description")
            self.assertIn("runbook_url", annotations, f"Alert {alert} missing runbook_url")

            runbook = annotations["runbook_url"]
            self.assertTrue(runbook.startswith("https://docs.zonata.internal/runbooks/"), f"Alert {alert} runbook URL invalid: {runbook}")

    def test_prometheus_config_includes_rule_files(self):
        """Validates that config/prometheus.yml includes rule_files referencing alert_rules.yml."""
        with open(self.prom_config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self.assertIn("rule_files", config, "config/prometheus.yml missing 'rule_files' directive")
        rule_files = config["rule_files"]
        self.assertIsInstance(rule_files, list)
        self.assertTrue(
            any("alert_rules.yml" in rf or "prometheus_rules.yml" in rf for rf in rule_files),
            f"rule_files does not reference alert_rules.yml: {rule_files}"
        )

    def test_docker_compose_mounts_alert_rules(self):
        """Validates that docker-compose.prod.yml mounts prometheus_rules.yml into the prometheus container."""
        with open(self.compose_path, "r", encoding="utf-8") as f:
            compose = yaml.safe_load(f)

        services = compose.get("services", {})
        self.assertIn("prometheus", services, "docker-compose.prod.yml missing prometheus service")
        prom_service = services["prometheus"]
        volumes = prom_service.get("volumes", [])

        has_rules_mount = any("prometheus_rules.yml" in v and "alert_rules.yml" in v for v in volumes)
        self.assertTrue(has_rules_mount, f"Prometheus service does not mount prometheus_rules.yml: {volumes}")

    def test_metrics_registry_request_and_error_recording(self):
        """Validates that PrometheusMetricsRegistry records requests, errors, auth failures and latencies."""
        from core.observability_stack import sre_metrics

        sre_metrics.record_request(status_code=200, latency_ms=12.5)
        sre_metrics.record_request(status_code=200, latency_ms=15.0)
        sre_metrics.record_request(status_code=500, latency_ms=45.0)
        sre_metrics.record_request(status_code=401, latency_ms=8.0)
        sre_metrics.record_request(status_code=403, latency_ms=9.0)

        self.assertEqual(sre_metrics._counters["zonata_api_requests_total"], 5.0)
        self.assertEqual(sre_metrics._counters["zonata_api_errors_total"], 1.0)
        self.assertEqual(sre_metrics._counters["zonata_auth_failures_total"], 2.0)
        self.assertEqual(len(sre_metrics._latencies), 5)

    def test_metrics_registry_wal_and_worker_events(self):
        """Validates recording of continuous WAL archiving and worker crash events."""
        from core.observability_stack import sre_metrics

        sre_metrics.record_wal_event(success=True)
        sre_metrics.record_wal_event(success=True)
        sre_metrics.record_wal_event(success=False)
        sre_metrics.record_worker_crash()

        self.assertEqual(sre_metrics._counters["zonata_wal_archive_success_total"], 2.0)
        self.assertEqual(sre_metrics._counters["zonata_wal_archive_failures_total"], 1.0)
        self.assertEqual(sre_metrics._counters["zonata_worker_crash_loops_total"], 1.0)

    def test_prometheus_exposition_format_compliance(self):
        """Validates that scrape_prometheus_format() conforms strictly to Prometheus exposition format."""
        from core.observability_stack import sre_metrics

        sre_metrics.record_request(status_code=200, latency_ms=25.0)
        output = sre_metrics.scrape_prometheus_format()

        self.assertIsInstance(output, str)
        self.assertIn("# HELP zonata_api_requests_total", output)
        self.assertIn("# TYPE zonata_api_requests_total counter", output)
        self.assertIn("zonata_api_requests_total 1.0", output)

        self.assertIn("# HELP zonata_db_connected", output)
        self.assertIn("# TYPE zonata_db_connected gauge", output)

        self.assertIn("# HELP zonata_disk_utilization_pct", output)
        self.assertIn("# TYPE zonata_disk_utilization_pct gauge", output)

        self.assertIn("# HELP zonata_api_latency_ms", output)
        self.assertIn("# TYPE zonata_api_latency_ms summary", output)
        self.assertIn('zonata_api_latency_ms{quantile="0.5"}', output)
        self.assertIn('zonata_api_latency_ms{quantile="0.95"}', output)
        self.assertIn('zonata_api_latency_ms{quantile="0.99"}', output)

    def test_slo_tracker_evaluation(self):
        """Validates SLO compliance calculation against availability and p95 latency targets."""
        from core.observability_stack import sre_metrics, SLOTracker

        # Record 100 requests: 99 successful (latency 50ms), 1 failure
        for _ in range(99):
            sre_metrics.record_request(status_code=200, latency_ms=50.0)
        sre_metrics.record_request(status_code=500, latency_ms=100.0)

        slo = SLOTracker.evaluate_slos(sre_metrics)

        self.assertIn("api_availability", slo)
        self.assertEqual(slo["api_availability"]["current"], 99.0)
        self.assertFalse(slo["api_availability"]["compliant"])  # Target is 99.9%

        self.assertIn("api_p95_latency", slo)
        self.assertEqual(slo["api_p95_latency"]["current_ms"], 50.0)
        self.assertTrue(slo["api_p95_latency"]["compliant"])  # Target is 200ms

    def test_production_config_gate7_rules_enforcement(self):
        """Validates Gate 7 alert rules file existence check in production mode."""
        from core.production_config import ProductionConfigValidator, ConfigurationError

        valid_env = {
            "APP_ENV": "production",
            "SECRET_VAULT_KEY": "a" * 32,
            "APPLICATION_SIGNING_KEY": "b" * 32,
            "SOVEREIGN_ROOT_KEY_ID": "key_root_001",
            "DATABASE_DIALECT": "sqlite",
            "ALLOWED_ORIGINS": "https://zonata.app",
            "PROMETHEUS_RULES_PATH": "config/prometheus_rules.yml"
        }

        # 1. Valid environment with real prometheus_rules.yml -> PASS
        res = ProductionConfigValidator.validate_environment(valid_env)
        self.assertTrue(res["valid"])

        # 2. Missing alert rules path -> FAIL
        invalid_env = dict(valid_env)
        invalid_env["PROMETHEUS_RULES_PATH"] = "config/nonexistent_alert_rules.yml"
        with self.assertRaises(ConfigurationError) as cm:
            ProductionConfigValidator.validate_environment(invalid_env)
        self.assertIn("Prometheus alert rules file missing", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
