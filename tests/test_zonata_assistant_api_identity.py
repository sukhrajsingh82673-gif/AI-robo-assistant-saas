"""
ZONATA AI Assistant API — identity, ownership and honesty regression tests.

These exercise the live HTTP handler rather than calling services directly, so
the authenticated user/company resolution and document authorization paths are
covered end to end.
"""

import json
import os
import shutil
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from core.auth import UserManager, UserRole
from core.db import db, configure_isolated_test_db
from core.document_generator import document_generator, DocumentFormat, StorageBoundary, DocumentCategory


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestAssistantApiIdentityBoundaries(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.orig_db_path = db.db_path
        cls.test_dir = tempfile.mkdtemp(prefix="zonata_assistant_api_")
        cls.isolated_db = os.path.join(cls.test_dir, "assistant_api.db")
        configure_isolated_test_db(cls.isolated_db)

        cls.orig_doc_dir = document_generator.base_dir
        cls.doc_dir = os.path.join(cls.test_dir, "documents")
        os.makedirs(cls.doc_dir, exist_ok=True)
        document_generator.base_dir = cls.doc_dir

        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                ("tnt_primary", "Primary Tenant", "ENTERPRISE", "ACTIVE", time.time()),
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, status, revenue, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("comp_primary", "tnt_primary", "Primary Corp", "Technology", "NEW", "OPERATIONAL", 0.0, time.time()),
            )
            conn.commit()

        from api_server import ThreadedHTTPServer, RoboAssistantRequestHandler
        cls.port = get_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server = ThreadedHTTPServer(("127.0.0.1", cls.port), RoboAssistantRequestHandler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        time.sleep(1.0)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.shutdown()
            cls.server.server_close()
        except Exception:
            pass
        document_generator.base_dir = cls.orig_doc_dir
        if cls.orig_db_path:
            db.set_db_path(cls.orig_db_path)
            os.environ["ZONATA_DB_PATH"] = cls.orig_db_path
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def _headers(self, user_id="usr_api_owner", role=UserRole.OWNER, company_id="comp_primary"):
        token = UserManager.generate_token({
            "user_id": user_id,
            "tenant_id": "tnt_primary",
            "company_id": company_id,
            "role": role,
            "permissions": ["*"],
        })
        return {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tnt_primary",
            "X-Company-ID": company_id,
            "Content-Type": "application/json",
        }

    def _post(self, path, payload, headers=None):
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=headers or self._headers(),
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def _get(self, path, headers=None):
        req = urllib.request.Request(f"{self.base_url}{path}", headers=headers or self._headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                try:
                    return resp.status, json.loads(body.decode("utf-8"))
                except Exception:
                    return resp.status, {"bytes": body}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                return exc.code, json.loads(raw)
            except Exception:
                return exc.code, {"raw": raw}

    def test_interact_ignores_body_identity_spoof(self):
        status, res = self._post("/api/assistant/interact", {
            "prompt": "My personal gym plan for this week",
            "workspace_mode": "PERSONAL",
            "user_id": "usr_spoofed_attacker",
            "company_id": "comp_attacker",
            "session_id": "sess_api_spoof",
        })
        self.assertEqual(status, 200)
        self.assertEqual(res["workspace_mode"], "PERSONAL")

        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT user_id, company_id, workspace_mode FROM assistant_messages WHERE session_id = ?",
                ("sess_api_spoof",),
            ).fetchall()
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row["user_id"], "usr_api_owner")
            self.assertIsNone(row["company_id"])
            self.assertEqual(row["workspace_mode"], "PERSONAL")

    def test_meeting_schedule_is_blocked_without_provider(self):
        status, res = self._post("/api/assistant/meetings/schedule", {
            "prompt": "Schedule a board alignment tomorrow at 3pm",
        })
        self.assertEqual(status, 409)
        self.assertFalse(res["success"])
        self.assertEqual(res["provider_status"], "BLOCKED")
        self.assertNotIn("google_meet_url", res)

    def test_document_search_and_download_are_owner_scoped(self):
        other = document_generator.generate_document(
            title="Other Owner Private Record",
            format_type=DocumentFormat.TXT,
            category=DocumentCategory.PERSONAL_DOCUMENT,
            content="other owner private",
            storage_boundary=StorageBoundary.PERSONAL,
            user_id="usr_someone_else",
            tenant_id="tnt_primary",
        )

        status, res = self._get(
            "/api/assistant/documents/search?boundary=PERSONAL&q=Other%20Owner&user_id=usr_someone_else",
            headers=self._headers(user_id="usr_api_owner"),
        )
        self.assertEqual(status, 200)
        ids = {d["doc_id"] for d in res["documents"]}
        self.assertNotIn(other["doc_id"], ids)

        status, _ = self._get(
            f"/api/assistant/documents/{other['doc_id']}/download",
            headers=self._headers(user_id="usr_api_owner"),
        )
        self.assertEqual(status, 403)

    def test_upload_is_stored_and_downloadable_only_by_owner(self):
        raw = b"owner upload content"
        import base64
        status, res = self._post("/api/assistant/documents/upload", {
            "filename": "owner-note.txt",
            "content_base64": base64.b64encode(raw).decode("ascii"),
            "storage_boundary": "PERSONAL",
        })
        self.assertEqual(status, 200)
        doc = res["document"]
        self.assertEqual(doc["storage_boundary"], "PERSONAL")
        self.assertTrue(os.path.exists(doc["file_path"]))

        status, _ = self._get(
            f"/api/assistant/documents/{doc['doc_id']}/download",
            headers=self._headers(user_id="usr_api_owner"),
        )
        self.assertEqual(status, 200)

        status, _ = self._get(
            f"/api/assistant/documents/{doc['doc_id']}/download",
            headers=self._headers(user_id="usr_intruder"),
        )
        self.assertEqual(status, 403)

    def test_emergency_stop_requires_approver_and_engages_matrix(self):
        status, _ = self._post(
            "/api/assistant/emergency-stop",
            {"reason": "observer attempt"},
            headers=self._headers(role=UserRole.OBSERVER),
        )
        self.assertEqual(status, 403)

        status, res = self._post("/api/assistant/emergency-stop", {"reason": "test containment"})
        self.assertEqual(status, 200)
        self.assertTrue(res["success"])
        self.assertEqual(res["state"], "ENGAGED")
        self.assertTrue(res["switch_id"].startswith("ks_"))


if __name__ == "__main__":
    unittest.main()
