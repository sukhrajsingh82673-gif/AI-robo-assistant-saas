"""
Coworker §7 records + real X11 window perception.

Two things are verified here:

1. Resource manifests: download digests, installation records and the file
   ownership gate that stops a task deleting something it does not own.
2. X11 perception: `xwininfo` enumeration returns real windows with real
   geometry. With no display it must return nothing rather than invent windows.
"""

import os
import shutil
import tempfile
import unittest

from core.coworker.computer_use_engine import ComputerUseEngine
from core.coworker.resource_manifests import ResourceManifestStore


class TestResourceManifests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "manifests.db")
        self.store = ResourceManifestStore(db_path=self.db, tenant_id="tnt_test")
        self.file = os.path.join(self.dir, "artifact.bin")
        with open(self.file, "wb") as fh:
            fh.write(b"zonata-manifest-test")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_01_download_manifest_and_digest(self):
        m = self.store.record_download(
            url="https://example.invalid/artifact.bin",
            target_path=self.file,
            task_id="task_dl",
        )
        self.assertEqual(m.byte_count, len(b"zonata-manifest-test"))
        self.assertEqual(len(m.sha256), 64)
        self.assertEqual(self.store.verify_download(m.manifest_id), (True, "DIGEST_MATCH"))

        # A modified file must fail verification, not silently pass.
        with open(self.file, "wb") as fh:
            fh.write(b"tampered")
        ok, reason = self.store.verify_download(m.manifest_id)
        self.assertFalse(ok)
        self.assertIn("DIGEST_MISMATCH", reason)

        self.assertEqual(len(self.store.get_downloads(task_id="task_dl")), 1)
        self.assertEqual(len(self.store.get_downloads(task_id="other")), 0)

    def test_02_installation_manifest(self):
        m = self.store.record_installation(
            package="pytest",
            version="9.0.2",
            interpreter="/tmp/venv/bin/python",
            venv_path="/tmp/venv",
            task_id="task_inst",
            mission_id="msn_inst",
            smoke_test_passed=True,
        )
        records = self.store.get_installations(mission_id="msn_inst")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["package"], "pytest")
        self.assertEqual(records[0]["smoke_test_passed"], 1)
        self.assertEqual(len(m.interpreter), len("/tmp/venv/bin/python"))

    def test_03_ownership_gate(self):
        # Unknown path: never deletable.
        allowed, why = self.store.can_reclaim(self.file, "task_a")
        self.assertFalse(allowed)
        self.assertEqual(why, "NO_OWNERSHIP_RECORD")

        self.store.register_ownership(self.file, "task_a", kind="TEMP_FILE")
        self.assertEqual(self.store.can_reclaim(self.file, "task_a"), (True, "OWNED_BY_REQUESTER"))

        allowed, why = self.store.can_reclaim(self.file, "task_b")
        self.assertFalse(allowed)
        self.assertIn("OWNED_BY_ANOTHER_TASK", why)

        # A path inside an owned directory belongs to that directory's task.
        nested = os.path.join(self.dir, "workspace", "nested.txt")
        os.makedirs(os.path.dirname(nested))
        open(nested, "w").close()
        self.store.register_ownership(os.path.join(self.dir, "workspace"), "task_c", kind="DIRECTORY")
        self.assertEqual(self.store.can_reclaim(nested, "task_c"), (True, "OWNED_BY_REQUESTER"))
        self.assertFalse(self.store.can_reclaim(nested, "task_a")[0])


class TestX11WindowTree(unittest.TestCase):
    def test_01_no_display_means_no_invented_windows(self):
        saved = os.environ.pop("DISPLAY", None)
        try:
            engine = ComputerUseEngine()
            self.assertEqual(engine.x11_window_tree(), [])
            obs = engine.observe()
            self.assertFalse(obs.window_tree_available)
            self.assertEqual(obs.window_elements, [])
            self.assertEqual(obs.perception_source, "IN_MEMORY_SYNTHETIC")
            self.assertIsNone(engine.find_in_window_tree("anything"))
        finally:
            if saved is not None:
                os.environ["DISPLAY"] = saved

    def test_02_real_display_returns_real_windows(self):
        if not os.environ.get("DISPLAY"):
            self.skipTest("No DISPLAY: real X11 enumeration covered by "
                          "/tmp/opencode/verify_cue_x11.py under Xvfb.")
        engine = ComputerUseEngine()
        windows = engine.x11_window_tree()
        for w in windows:
            self.assertEqual(w.metadata["source"], "x11_window_tree")
            self.assertGreater(w.box.width, 1)
            self.assertGreater(w.box.height, 1)
            self.assertTrue(w.label)
        obs = engine.observe()
        self.assertEqual(obs.window_tree_available, bool(windows))
        if windows:
            self.assertTrue(obs.perception_source.startswith("X11_WINDOW_TREE"))


if __name__ == "__main__":
    unittest.main()
