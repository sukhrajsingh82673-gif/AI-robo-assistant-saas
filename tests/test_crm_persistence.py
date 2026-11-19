"""
ZONATA Enterprise SaaS — Commercial CRM & Deals Persistence Test Suite
Verifies:
1. Customer creation, retrieval, listing, and updates
2. Deal creation, retrieval, and stage progression
3. Strict multi-tenant isolation across CRM records
4. Relational database persistence across connections and simulated server restarts
"""

import os
import sys
import time
import tempfile
import unittest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.enterprise_crm import EnterpriseCrmService

MODULE_TEMP_DIR = None
MODULE_ORIG_DB_PATH = None
MODULE_ORIG_ENV_DB_PATH = None

def setUpModule():
    global MODULE_TEMP_DIR, MODULE_ORIG_DB_PATH, MODULE_ORIG_ENV_DB_PATH
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_ORIG_ENV_DB_PATH = os.environ.get("ZONATA_DB_PATH")
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "crm_test_isolated.db")
    configure_isolated_test_db(isolated_db)

def tearDownModule():
    global MODULE_TEMP_DIR, MODULE_ORIG_DB_PATH, MODULE_ORIG_ENV_DB_PATH
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
    if MODULE_ORIG_ENV_DB_PATH is not None:
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_ENV_DB_PATH
    else:
        os.environ.pop("ZONATA_DB_PATH", None)
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


class TestCrmPersistence(unittest.TestCase):
    def setUp(self):
        self.orig_db_path = db.db_path
        self.orig_env_db_path = os.environ.get("ZONATA_DB_PATH")
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.environ["ZONATA_DB_PATH"] = self.temp_db_path
        self.db = db
        self.db.set_db_path(self.temp_db_path)

        # Setup 2 distinct tenants for isolation testing
        with self.db.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES ('tnt_alpha', 'Alpha Corp', ?)", (time.time(),))
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES ('tnt_beta', 'Beta Global', ?)", (time.time(),))
            conn.commit()

        self.crm_alpha = EnterpriseCrmService(tenant_id="tnt_alpha")
        self.crm_beta = EnterpriseCrmService(tenant_id="tnt_beta")

    def tearDown(self):
        if hasattr(self, "orig_db_path") and self.orig_db_path:
            db.set_db_path(self.orig_db_path)
        if hasattr(self, "orig_env_db_path"):
            if self.orig_env_db_path is not None:
                os.environ["ZONATA_DB_PATH"] = self.orig_env_db_path
            else:
                os.environ.pop("ZONATA_DB_PATH", None)
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except Exception:
            pass

    def test_01_create_and_retrieve_customer(self):
        """Verify creating a customer persists record and is retrievable."""
        cust = self.crm_alpha.create_customer(
            company_id="comp_alpha_1",
            data={
                "name": "Acme Innovations Ltd",
                "tier": "ENTERPRISE_PLATINUM",
                "industry": "Robotics & AI",
                "status": "ACTIVE",
                "health_score": 95,
                "arr": "₹1,500,000",
                "ltv": "₹4,500,000",
                "contacts": [{"name": "John Doe", "email": "john@acme.example.com", "role": "CTO"}]
            }
        )
        self.assertIsNotNone(cust)
        self.assertTrue(cust.get("success"))
        cust_id = cust["customer_id"]

        # Retrieve by ID
        fetched = self.crm_alpha.get_customer(cust_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Acme Innovations Ltd")
        self.assertEqual(fetched["tenant_id"], "tnt_alpha")
        self.assertEqual(len(fetched["contacts"]), 1)
        self.assertEqual(fetched["contacts"][0]["role"], "CTO")

    def test_02_create_and_update_deal(self):
        """Verify deal creation and stage progression."""
        cust = self.crm_alpha.create_customer(
            company_id="comp_alpha_1",
            data={"name": "Delta Industrial", "arr": "₹500,000"}
        )
        deal = self.crm_alpha.create_deal(
            company_id="comp_alpha_1",
            data={
                "title": "Facility Automation System",
                "customer_id": cust["customer_id"],
                "stage": "Discovery",
                "value": 750000.0,
                "probability": 0.4,
                "owner": "SDR Team"
            }
        )
        self.assertIsNotNone(deal)
        self.assertTrue(deal.get("success"))
        deal_id = deal["deal_id"]

        # Advance deal to Proposal Submitted
        updated = self.crm_alpha.update_deal_stage(
            deal_id=deal_id,
            stage="Proposal Submitted"
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated["stage"], "Proposal Submitted")

        deals = self.crm_alpha.list_deals()
        self.assertEqual(len(deals), 1)
        self.assertEqual(deals[0]["stage"], "Proposal Submitted")
        self.assertEqual(deals[0]["value"], 750000.0)

    def test_03_multi_tenant_isolation(self):
        """Verify Tenant Alpha cannot see or mutate Tenant Beta records."""
        # Create records in Tenant Alpha
        cust_a = self.crm_alpha.create_customer(
            company_id="comp_alpha_1",
            data={"name": "Alpha Customer Private", "arr": "₹1,000,000"}
        )
        deal_a = self.crm_alpha.create_deal(
            company_id="comp_alpha_1",
            data={"title": "Alpha Deal", "value": 100000.0}
        )

        # Create records in Tenant Beta
        cust_b = self.crm_beta.create_customer(
            company_id="comp_beta_1",
            data={"name": "Beta Customer Confidential", "arr": "₹2,000,000"}
        )

        # Tenant Beta listing must only show Beta records
        customers_beta = self.crm_beta.list_customers()
        self.assertEqual(len(customers_beta), 1)
        self.assertEqual(customers_beta[0]["name"], "Beta Customer Confidential")

        # Tenant Beta must NOT be able to read Tenant Alpha's customer
        fetched_a_from_b = self.crm_beta.get_customer(cust_a["customer_id"])
        self.assertIsNone(fetched_a_from_b)

        # Tenant Beta deals list must have 0 deals
        deals_beta = self.crm_beta.list_deals()
        self.assertEqual(len(deals_beta), 0)

        # Tenant Beta attempting to mutate Tenant Alpha deal has no effect on Alpha deal
        self.crm_beta.update_deal_stage(deal_id=deal_a["deal_id"], stage="Won / Closed")
        # Check Alpha deal stage is unchanged
        alpha_deals = self.crm_alpha.list_deals()
        self.assertNotEqual(alpha_deals[0]["stage"], "Won / Closed")

    def test_04_persistence_across_connection_recycle(self):
        """Verify data persists when database connections are completely recycled."""
        cust = self.crm_alpha.create_customer(
            company_id="comp_alpha_1",
            data={"name": "Persistent Partner Ltd", "arr": "₹3,000,000"}
        )
        deal = self.crm_alpha.create_deal(
            company_id="comp_alpha_1",
            data={
                "title": "Autonomous Operating Core",
                "customer_id": cust["customer_id"],
                "stage": "Won / Closed",
                "value": 3000000.0
            }
        )

        # Re-initialize CRM service on clean instance
        reloaded_crm = EnterpriseCrmService(tenant_id="tnt_alpha")

        reloaded_customers = reloaded_crm.list_customers()
        self.assertEqual(len(reloaded_customers), 1)
        self.assertEqual(reloaded_customers[0]["name"], "Persistent Partner Ltd")

        reloaded_deals = reloaded_crm.list_deals()
        self.assertEqual(len(reloaded_deals), 1)
        self.assertEqual(reloaded_deals[0]["title"], "Autonomous Operating Core")
        self.assertEqual(reloaded_deals[0]["value"], 3000000.0)


if __name__ == "__main__":
    unittest.main()
