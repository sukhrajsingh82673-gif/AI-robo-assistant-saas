"""
URA Assistant Stage 3 tests — background jobs, web access policy, adapters.

The web search adapters are exercised with the clearly-labelled sample provider
so no network call is made.  Real providers are asserted to be "not configured"
without their environment keys.
"""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.db import configure_isolated_test_db, db

TEST_DB = os.path.join(tempfile.mkdtemp(prefix="ura_jobs_"), "assistant.db")
configure_isolated_test_db(TEST_DB)

from core.settings_service import settings_service  # noqa: E402
from core.ura_assistant_jobs import (  # noqa: E402
    AssistantJobRunner,
    AssistantJobStore,
    MAX_ACTIVE_JOBS,
)
from core.ura_assistant_service import URAAssistantService  # noqa: E402
from core.ura_assistant_web import (  # noqa: E402
    NoWebSearchProvider,
    SampleWebSearchProvider,
    WebAccessPolicy,
    WebResult,
    filter_results,
    get_web_search_provider,
    load_web_access,
)

TENANT = "tnt_stage3"


def seed_company(company_id: str = "comp_stage3", name: str = "Stage 3 Co") -> None:
    now = time.time()
    with db.get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) "
                "VALUES (?, 'Stage 3', 'ENTERPRISE', 'ACTIVE', ?)",
                (TENANT, now),
            )
        except Exception:
            pass
        try:
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, created_at) "
                "VALUES (?, ?, ?, 'Hospitality', 'EXISTING', ?)",
                (company_id, TENANT, name, now),
            )
        except Exception:
            pass
        conn.commit()


def set_web_access(mode: str, allow: str = "", block: str = "", company_id: str = "comp_stage3") -> None:
    for key, value in (
        ("assistant_web_access", mode),
        ("assistant_web_allowlist", allow),
        ("assistant_web_blocklist", block),
    ):
        res = settings_service.update_single_setting(
            TENANT, company_id, key, value, actor="test", actor_role="OWNER"
        )
        assert res.get("success"), res


def wait_for(service: URAAssistantService, job_id: str, user_id: str, timeout: float = 15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        jobs = service.recover_jobs(user_id)
        found = next((j for j in jobs if j["job_id"] == job_id), None)
        if found and found["status"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return found
        time.sleep(0.1)
    raise AssertionError("job did not reach a terminal state in time")


class SlowSampleProvider(SampleWebSearchProvider):
    """Sample provider with a delay, so pause/cancel/limit tests are deterministic."""

    delay = 0.8

    def search(self, query, limit=5):
        time.sleep(self.delay)
        return super().search(query, limit)


class TestWebAccessPolicy(unittest.TestCase):
    def test_off_blocks_everything(self):
        policy = WebAccessPolicy(mode="off")
        allowed, reason = policy.check("https://example.com/page")
        self.assertFalse(allowed)
        self.assertIn("off", reason.lower())

    def test_allowlist_only_allows_listed_domains(self):
        policy = WebAccessPolicy(mode="allowlist", allowlist=["example.com", "*.trusted.org"])
        self.assertTrue(policy.check("https://example.com/a")[0])
        self.assertTrue(policy.check("https://news.trusted.org/a")[0])
        self.assertFalse(policy.check("https://evil.test/a")[0])

    def test_blocklist_wins_even_when_open(self):
        policy = WebAccessPolicy(mode="open", blocklist=["bad.example"])
        allowed, reason = policy.check("https://bad.example/x")
        self.assertFalse(allowed)
        self.assertIn("block list", reason)
        self.assertTrue(policy.check("https://good.example/x")[0])

    def test_filter_reports_blocked_sources(self):
        results = [
            WebResult(title="A", url="https://good.example/a"),
            WebResult(title="B", url="https://bad.example/b"),
        ]
        allowed, blocked = filter_results(results, WebAccessPolicy(mode="open", blocklist=["bad.example"]))
        self.assertEqual([r.url for r in allowed], ["https://good.example/a"])
        self.assertEqual(len(blocked), 1)
        self.assertIn("block list", blocked[0]["reason"])


class TestProviders(unittest.TestCase):
    def test_no_provider_is_the_default(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("URA_ASSISTANT_WEB_SEARCH")}
        env.pop("TAVILY_API_KEY", None)
        env.pop("BRAVE_SEARCH_API_KEY", None)
        env.pop("BRAVE_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            provider = get_web_search_provider()
            self.assertIsInstance(provider, NoWebSearchProvider)
            self.assertFalse(provider.configured())

    def test_sample_provider_is_explicit_and_labelled(self):
        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}):
            provider = get_web_search_provider()
            self.assertIsInstance(provider, SampleWebSearchProvider)
            results = provider.search("hotel crm", limit=3)
            self.assertTrue(results)
            self.assertTrue(all(r.sample for r in results))
            self.assertTrue(all(r.url.startswith("https://example.com/") for r in results))

    def test_sample_provider_never_claims_real_pages(self):
        provider = SampleWebSearchProvider()
        for result in provider.search("anything"):
            self.assertIn("sample", result.snippet.lower())


class TestJobStore(unittest.TestCase):
    def setUp(self):
        seed_company()
        self.store = AssistantJobStore(TENANT)

    def test_create_list_and_active_count(self):
        job = self.store.create("usr_store", "A job", "do the thing", kind="research")
        self.assertEqual(job["status"], "QUEUED")
        self.assertEqual(self.store.active_count("usr_store"), 1)
        self.assertEqual(len(self.store.list("usr_store")), 1)
        self.assertEqual(self.store.list("usr_other"), [])

    def test_unseen_notifications(self):
        job = self.store.create("usr_seen", "A job", "do the thing")
        self.store.update(job["job_id"], status="SUCCEEDED", progress=100, step="Completed")
        self.assertEqual(self.store.unseen_count("usr_seen"), 1)
        self.store.mark_all_seen("usr_seen")
        self.assertEqual(self.store.unseen_count("usr_seen"), 0)

    def test_retry_resets_a_finished_job(self):
        job = self.store.create("usr_retry", "A job", "do the thing")
        self.store.update(job["job_id"], status="FAILED", error="boom", progress=100)
        reset = self.store.reset_for_retry(job["job_id"], "usr_retry")
        self.assertEqual(reset["status"], "QUEUED")
        self.assertIsNone(reset["error"])
        self.assertIsNone(reset["result"])


class TestJobsWithProviders(unittest.TestCase):
    def setUp(self):
        seed_company()
        set_web_access("open")
        self.svc = URAAssistantService(TENANT)

    def test_research_job_succeeds_and_cites_sources(self):
        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}):
            created = self.svc.create_job(
                "research the best hospitality CRM", "usr_job", workspace_mode="PERSONAL",
                company_id="comp_stage3",
            )
            self.assertTrue(created["success"], created)
            job = wait_for(self.svc, created["job"]["job_id"], "usr_job")
        self.assertEqual(job["status"], "SUCCEEDED", job.get("error"))
        self.assertTrue(job["result"]["summary"])
        self.assertGreaterEqual(len(job["citations"]), 1)
        self.assertTrue(all(c["source_type"] == "WEB" for c in job["citations"]))
        self.assertEqual(job["progress"], 100)
        self.assertTrue(any(step["label"] for step in job["steps"]))

    def test_limit_is_three_active_jobs(self):
        job_ids = []
        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}), \
                patch("core.ura_assistant_web.get_web_search_provider", return_value=SlowSampleProvider()):
            for index in range(MAX_ACTIVE_JOBS):
                created = self.svc.create_job(
                    f"research topic {index}", "usr_limit", workspace_mode="PERSONAL",
                    company_id="comp_stage3",
                )
                self.assertTrue(created["success"], created)
                job_ids.append(created["job"]["job_id"])
            refused = self.svc.create_job(
                "research one more", "usr_limit", workspace_mode="PERSONAL",
                company_id="comp_stage3",
            )
            self.assertFalse(refused["success"])
            self.assertIn(str(MAX_ACTIVE_JOBS), refused["error"])
            self.assertEqual(refused["active"], MAX_ACTIVE_JOBS)
            for job_id in job_ids:
                self.assertEqual(wait_for(self.svc, job_id, "usr_limit")["status"], "SUCCEEDED")

    def test_no_provider_fails_honestly(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("URA_ASSISTANT_WEB_SEARCH")}
        env["URA_ASSISTANT_WEB_SEARCH_PROVIDER"] = "none"
        with patch.dict(os.environ, env, clear=True):
            created = self.svc.create_job(
                "research a topic", "usr_noprov", workspace_mode="PERSONAL",
                company_id="comp_stage3",
            )
            job = wait_for(self.svc, created["job"]["job_id"], "usr_noprov")
        self.assertEqual(job["status"], "FAILED")
        self.assertIn("provider is configured", job["error"].lower())
        self.assertFalse(job["result"])

    def test_web_access_off_fails_honestly(self):
        seed_company("comp_web_off", "Web Off Co")
        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}):
            created = self.svc.create_job(
                "research a topic", "usr_off", workspace_mode="PERSONAL",
                company_id="comp_web_off",
            )
            job = wait_for(self.svc, created["job"]["job_id"], "usr_off")
        self.assertEqual(job["status"], "FAILED")
        self.assertIn("web access is off", job["error"].lower())

    def test_query_job_needs_company_scope(self):
        created = self.svc.create_job(
            "how many approvals are waiting?", "usr_query", workspace_mode="PERSONAL",
            company_id="comp_stage3",
        )
        job = wait_for(self.svc, created["job"]["job_id"], "usr_query")
        self.assertEqual(job["status"], "FAILED")
        self.assertIn("company scope", job["error"].lower())

    def test_pause_resume_and_cancel(self):
        class SlowProvider(SampleWebSearchProvider):
            def search(self, query, limit=5):
                time.sleep(0.6)
                return super().search(query, limit)

        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}), \
                patch("core.ura_assistant_web.get_web_search_provider", return_value=SlowProvider()):
            created = self.svc.create_job(
                "research a slow topic", "usr_pause", workspace_mode="PERSONAL",
                company_id="comp_stage3",
            )
            job_id = created["job"]["job_id"]
            paused = self.svc.job_action(job_id, "usr_pause", "pause")
            self.assertTrue(paused["success"], paused)
            time.sleep(0.2)
            current = AssistantJobStore(TENANT).get(job_id, "usr_pause")
            self.assertEqual(current["status"], "PAUSED")
            resumed = self.svc.job_action(job_id, "usr_pause", "resume")
            self.assertTrue(resumed["success"], resumed)
            job = wait_for(self.svc, job_id, "usr_pause")
        self.assertEqual(job["status"], "SUCCEEDED")

    def test_cancel_stops_work(self):
        class SlowProvider(SampleWebSearchProvider):
            def search(self, query, limit=5):
                time.sleep(0.6)
                return super().search(query, limit)

        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}), \
                patch("core.ura_assistant_web.get_web_search_provider", return_value=SlowProvider()):
            created = self.svc.create_job(
                "research a slow topic", "usr_cancel", workspace_mode="PERSONAL",
                company_id="comp_stage3",
            )
            job_id = created["job"]["job_id"]
            stopped = self.svc.job_action(job_id, "usr_cancel", "cancel")
            self.assertTrue(stopped["success"], stopped)
            job = wait_for(self.svc, job_id, "usr_cancel")
        self.assertEqual(job["status"], "CANCELLED")
        self.assertFalse(job["result"])

    def test_takeover_pauses_and_hands_off(self):
        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}), \
                patch("core.ura_assistant_web.get_web_search_provider", return_value=SlowSampleProvider()):
            created = self.svc.create_job(
                "research a topic", "usr_takeover", workspace_mode="PERSONAL",
                company_id="comp_stage3",
            )
            job_id = created["job"]["job_id"]
            store = AssistantJobStore(TENANT)
            deadline = time.time() + 5
            while time.time() < deadline:
                current = store.get(job_id, "usr_takeover")
                if current and current["status"] == "RUNNING":
                    break
                time.sleep(0.05)
            res = self.svc.job_action(job_id, "usr_takeover", "takeover")
            self.assertTrue(res["success"], res)
            self.assertEqual(res["handoff"]["path"], "/coworker")
            self.assertEqual(res["job"]["status"], "PAUSED")
            # Release the paused worker so the thread pool can shut down.
            self.assertTrue(self.svc.job_action(job_id, "usr_takeover", "cancel")["success"])
            self.assertEqual(wait_for(self.svc, job_id, "usr_takeover")["status"], "CANCELLED")

    def test_retry_reruns_a_failed_job(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("URA_ASSISTANT_WEB_SEARCH")}
        env["URA_ASSISTANT_WEB_SEARCH_PROVIDER"] = "none"
        with patch.dict(os.environ, env, clear=True):
            created = self.svc.create_job(
                "research a retry topic", "usr_rerun", workspace_mode="PERSONAL",
                company_id="comp_stage3",
            )
            job = wait_for(self.svc, created["job"]["job_id"], "usr_rerun")
            self.assertEqual(job["status"], "FAILED")
        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}):
            retried = self.svc.job_action(job["job_id"], "usr_rerun", "retry")
            self.assertTrue(retried["success"], retried)
            final = wait_for(self.svc, job["job_id"], "usr_rerun")
        self.assertEqual(final["status"], "SUCCEEDED")

    def test_recover_marks_an_orphaned_running_job_failed(self):
        store = AssistantJobStore(TENANT)
        job = store.create("usr_orphan", "Orphan", "research x", kind="research")
        store.update(job["job_id"], status="RUNNING", progress=40, step="Searching")
        AssistantJobRunner.instance()._jobs.pop(job["job_id"], None)
        jobs = self.svc.recover_jobs("usr_orphan")
        found = next(j for j in jobs if j["job_id"] == job["job_id"])
        self.assertEqual(found["status"], "FAILED")
        self.assertIn("restarted", found["error"].lower())


class TestDirectChatResearch(unittest.TestCase):
    def setUp(self):
        seed_company()
        set_web_access("open")
        self.svc = URAAssistantService(TENANT)

    def test_web_research_tool_returns_sources(self):
        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}):
            result = self.svc.execute_tool(
                "web_research", {"query": "hotel crm"}, user_id="usr_chat",
                scope="PERSONAL", company_id="comp_stage3",
            )
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["citations"]), 2)
        self.assertEqual(result["card"]["type"], "WEB_SOURCES")
        self.assertTrue(result["card"]["sample"])

    def test_web_research_respects_the_blocklist(self):
        set_web_access("open", block="example.com")
        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}):
            result = self.svc.execute_tool(
                "web_research", {"query": "hotel crm"}, user_id="usr_chat",
                scope="PERSONAL", company_id="comp_stage3",
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["card"]["type"], "WEB_NO_SOURCES")

    def test_stream_marks_research_as_source_backed(self):
        with patch.dict(os.environ, {"URA_ASSISTANT_WEB_SEARCH_PROVIDER": "sample"}):
            events = list(self.svc.stream(
                prompt="research hotel crm tools",
                user_id="usr_chat",
                workspace_mode="PERSONAL",
                company_id="comp_stage3",
                page_context={"page": "overview"},
            ))
        types = [e["type"] for e in events]
        self.assertIn("tool", types)
        done = events[-1]
        self.assertEqual(done["type"], "done")
        self.assertEqual(done["routed_to"], "WEB_RESEARCH")
        self.assertGreaterEqual(len(done["citations"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
