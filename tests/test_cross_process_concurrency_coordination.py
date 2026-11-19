"""
ZONATA Enterprise SaaS — Cross-Process Concurrency Coordination Suite
Verifies:
1. Two distinct operating system processes coordinate leases via Neon PostgreSQL / shared DB.
2. Cross-process enforcement of the 4-lease ceiling (P1=2, P2=2 -> 5th lease rejected in both processes).
3. Cross-process lease release and acquisition handoff.
4. Fail-closed behavior on database error in PostgreSQL mode (preventing uncoordinated split-brain).
"""

import os
import sys
import time
import uuid
import unittest
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, DatabaseDialect
from core.tenant_fairness import ConcurrencyLeaseManager


def run_subcommand(subcmd_code: str) -> str:
    res = subprocess.run(
        [sys.executable, "-c", subcmd_code],
        capture_output=True,
        text=True,
        timeout=30,
        env=os.environ.copy()
    )
    if res.returncode != 0:
        raise RuntimeError(f"Subprocess failed ({res.returncode}): {res.stderr}\n{res.stdout}")
    return res.stdout.strip()


class TestCrossProcessConcurrencyCoordination(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.initialize()
        cls.tenant_id = f"tnt_proc_{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        with db.get_connection() as conn:
            try:
                conn.execute("DELETE FROM tenant_concurrency_leases WHERE tenant_id = ?", (self.tenant_id,))
                conn.commit()
            except Exception:
                pass

    def test_01_cross_process_lease_coordination(self):
        """Two separate OS processes must coordinate against shared DB and enforce max 4 leases."""
        tenant_id = self.tenant_id

        # Subprocess 1 acquires 2 leases
        p1_code = f"""
import sys, os
sys.path.insert(0, '{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}')
from dotenv import load_dotenv
load_dotenv('{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")}')
from core.db import db
db.initialize()
from core.tenant_fairness import ConcurrencyLeaseManager
mgr = ConcurrencyLeaseManager()
ok1, l1, _ = mgr.acquire_lease('{tenant_id}', max_concurrency=4, ttl_seconds=120)
ok2, l2, _ = mgr.acquire_lease('{tenant_id}', max_concurrency=4, ttl_seconds=120)
print(f"{{ok1}},{{l1}},{{ok2}},{{l2}}")
"""
        p1_out = run_subcommand(p1_code)
        ok1, l1, ok2, l2 = p1_out.split(",")
        self.assertEqual(ok1, "True")
        self.assertEqual(ok2, "True")

        # Subprocess 2 acquires 2 leases (reaching the 4-lease ceiling)
        p2_code = f"""
import sys, os
sys.path.insert(0, '{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}')
from dotenv import load_dotenv
load_dotenv('{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")}')
from core.db import db
db.initialize()
from core.tenant_fairness import ConcurrencyLeaseManager
mgr = ConcurrencyLeaseManager()
ok3, l3, _ = mgr.acquire_lease('{tenant_id}', max_concurrency=4, ttl_seconds=120)
ok4, l4, _ = mgr.acquire_lease('{tenant_id}', max_concurrency=4, ttl_seconds=120)
print(f"{{ok3}},{{l3}},{{ok4}},{{l4}}")
"""
        p2_out = run_subcommand(p2_code)
        ok3, l3, ok4, l4 = p2_out.split(",")
        self.assertEqual(ok3, "True")
        self.assertEqual(ok4, "True")

        # Subprocess 1 attempts 5th lease -> MUST BE REJECTED
        p1_overflow = f"""
import sys, os
sys.path.insert(0, '{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}')
from dotenv import load_dotenv
load_dotenv('{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")}')
from core.db import db
db.initialize()
from core.tenant_fairness import ConcurrencyLeaseManager
mgr = ConcurrencyLeaseManager()
ok5, l5, retry = mgr.acquire_lease('{tenant_id}', max_concurrency=4, ttl_seconds=120)
print(f"{{ok5}},{{retry}}")
"""
        p1_overflow_out = run_subcommand(p1_overflow)
        ok5, retry = p1_overflow_out.split(",")
        self.assertEqual(ok5, "False")
        self.assertGreater(int(retry), 0)

        # Subprocess 2 releases 1 lease (l3)
        p2_release = f"""
import sys, os
sys.path.insert(0, '{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}')
from dotenv import load_dotenv
load_dotenv('{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")}')
from core.db import db
db.initialize()
from core.tenant_fairness import ConcurrencyLeaseManager
mgr = ConcurrencyLeaseManager()
rel = mgr.release_lease('{l3}')
print(f"{{rel}}")
"""
        p2_rel_out = run_subcommand(p2_release)
        self.assertEqual(p2_rel_out, "True")

        # Subprocess 1 can now acquire the freed slot
        p1_acquire_freed = f"""
import sys, os
sys.path.insert(0, '{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}')
from dotenv import load_dotenv
load_dotenv('{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")}')
from core.db import db
db.initialize()
from core.tenant_fairness import ConcurrencyLeaseManager
mgr = ConcurrencyLeaseManager()
ok_freed, l_freed, _ = mgr.acquire_lease('{tenant_id}', max_concurrency=4, ttl_seconds=120)
print(f"{{ok_freed}},{{l_freed}}")
"""
        p1_freed_out = run_subcommand(p1_acquire_freed)
        ok_freed, l_freed = p1_freed_out.split(",")
        self.assertEqual(ok_freed, "True")
        self.assertTrue(l_freed.startswith("lease_"))

    def test_02_postgresql_fail_closed_on_db_exception(self):
        """In PostgreSQL production mode, database exceptions must fail closed, NOT fall back to split-brain in-memory."""
        mgr = ConcurrencyLeaseManager()
        # Mock connection failure to verify fail-closed
        from unittest.mock import patch
        with patch.object(db, "get_connection", side_effect=RuntimeError("Neon connection timeout")):
            with patch.object(db, "get_dialect", return_value=DatabaseDialect.POSTGRESQL):
                ok, lid, retry = mgr.acquire_lease(self.tenant_id, max_concurrency=4)
                self.assertFalse(ok)
                self.assertIsNone(lid)
                self.assertGreater(retry, 0)


if __name__ == "__main__":
    unittest.main()
