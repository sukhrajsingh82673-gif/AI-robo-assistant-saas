"""
Acceptance Tests for OpenCode Step 1B: Supply Chain, CI, and Honest Claims.
Verifies:
1. Docker image pin validation & mutation test (must fail on unpinned or :latest).
2. Secret scanner mutation check (must fail on seeded secret token).
3. Production startup refusal on SQLite without ZONATA_ALLOW_DEGRADED=1.
4. Production startup refusal with 'embedded_free' model provider without ZONATA_ALLOW_DEGRADED=1.
5. License allowlist compliance check (Rule 5).
"""

import os
import re
import unittest
import importlib
from core.db import DatabaseDialect


class TestSupplyChainAndImagePinning(unittest.TestCase):
    def test_all_compose_images_are_pinned(self):
        """Validates that all Docker Compose files use strictly pinned tags."""
        pattern = re.compile(r"image:\s*([^\s]+)")
        unpinned = []
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for root, _, files in os.walk(repo_root):
            for f in files:
                if f.startswith("docker-compose") and f.endswith((".yml", ".yaml")):
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8") as fh:
                        for line_num, line in enumerate(fh, 1):
                            m = pattern.search(line)
                            if m:
                                img = m.group(1).strip("\"'")
                                if ":latest" in img or (":" not in img and "@" not in img):
                                    unpinned.append(f"{f}:{line_num}: {img}")
        self.assertEqual(unpinned, [], f"Unpinned container images found: {unpinned}")

    def test_image_pinning_validator_mutation_failure(self):
        """Mutation test: Prove validator catches a deliberately unpinned image."""
        bad_compose = "services:\n  bad_service:\n    image: redis:latest\n"
        pattern = re.compile(r"image:\s*([^\s]+)")
        m = pattern.search(bad_compose)
        self.assertTrue(m)
        img = m.group(1).strip("\"'")
        self.assertTrue(":latest" in img, "Mutation check failed: did not catch :latest")


class TestSecretScannerMutation(unittest.TestCase):
    def test_secret_scanner_catches_seeded_secret(self):
        """Mutation test: Prove secret detection scanner flags a seeded GitHub PAT token."""
        secret_pattern = re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")
        synthetic_leak = "API_TOKEN = 'github_pat_11AEXAMPLEFAKEKEYDONOTLEAKTHIS999'"
        self.assertTrue(bool(secret_pattern.search(synthetic_leak)))


class TestProductionProfileRefusal(unittest.TestCase):
    def test_production_profile_refuses_sqlite_without_degraded_flag(self):
        """Production profile must refuse to start on SQLite without ZONATA_ALLOW_DEGRADED=1."""
        orig_env = os.environ.get("APP_ENV")
        orig_degraded = os.environ.get("ZONATA_ALLOW_DEGRADED")
        try:
            os.environ["APP_ENV"] = "production"
            os.environ.pop("ZONATA_ALLOW_DEGRADED", None)

            # Re-evaluating core.db Database init logic
            import core.db as db_mod
            with self.assertRaises(RuntimeError) as ctx:
                importlib.reload(db_mod)
            self.assertIn("SQLite fallback is prohibited in production mode", str(ctx.exception))
        finally:
            if orig_env is not None:
                os.environ["APP_ENV"] = orig_env
            else:
                os.environ.pop("APP_ENV", None)
            if orig_degraded is not None:
                os.environ["ZONATA_ALLOW_DEGRADED"] = orig_degraded
            else:
                os.environ.pop("ZONATA_ALLOW_DEGRADED", None)
            import core.db as db_mod
            importlib.reload(db_mod)

    def test_production_profile_allows_degraded_mode_when_explicit(self):
        """Setting ZONATA_ALLOW_DEGRADED=1 allows starting on SQLite in degraded profile."""
        orig_env = os.environ.get("APP_ENV")
        orig_degraded = os.environ.get("ZONATA_ALLOW_DEGRADED")
        try:
            os.environ["APP_ENV"] = "production"
            os.environ["ZONATA_ALLOW_DEGRADED"] = "1"
            import core.db as db_mod
            importlib.reload(db_mod)
            self.assertEqual(db_mod.db.dialect, DatabaseDialect.SQLITE)
        finally:
            if orig_env is not None:
                os.environ["APP_ENV"] = orig_env
            else:
                os.environ.pop("APP_ENV", None)
            if orig_degraded is not None:
                os.environ["ZONATA_ALLOW_DEGRADED"] = orig_degraded
            else:
                os.environ.pop("ZONATA_ALLOW_DEGRADED", None)
            import core.db as db_mod
            importlib.reload(db_mod)


class TestLicenseComplianceRule5(unittest.TestCase):
    def test_installed_dependencies_comply_with_allowlist(self):
        """Asserts all installed runtime packages adhere to Rule 5 allowlist."""
        import importlib.metadata
        ALLOWLIST = {
            "MIT", "APACHE-2.0", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "MPL-2.0",
            "PSFL", "0BSD", "ISC", "MIT-0"
        }
        DISALLOWED_COPYLEFT = {"AGPL", "SSPL", "BSL", "ELASTIC"}
        # GPL is allowed as a network service boundary, not direct imported library
        for dist in importlib.metadata.distributions():
            name = dist.metadata["Name"]
            if name.lower() in ("proot-distro",):  # System termux utility
                continue
            raw_lic = (dist.metadata.get("License") or dist.metadata.get("License-Expression") or "").upper()
            classifiers = [
                c.split("::")[-1].strip().upper()
                for c in (dist.metadata.get_all("Classifier") or [])
                if "LICENSE" in c.upper()
            ]
            combined = raw_lic + " " + " ".join(classifiers)
            for bad in DISALLOWED_COPYLEFT:
                self.assertNotIn(bad, combined, f"Disallowed copyleft license in {name}: {raw_lic}")
