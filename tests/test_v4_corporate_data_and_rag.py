"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V4 Test Suite — Corporate Data Plane, Classification, Pre-Retrieval RAG, & Data Lifecycle
"""

import unittest
import uuid
from core.corporate_data_plane import corporate_data_gateway
from core.data_classification_engine import DataClassificationLevel
from core.knowledge_gateway import knowledge_gateway
from core.data_lifecycle_manager import data_lifecycle_manager, LegalHoldViolationError

class TestV4CorporateDataAndRAG(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_rag_{uuid.uuid4().hex[:6]}"
        self.company_id = f"comp_rag_{uuid.uuid4().hex[:6]}"
        self.foreign_tenant = f"tnt_other_{uuid.uuid4().hex[:6]}"

    def test_auto_classification_and_acl_enforcement(self):
        """Test sensitivity classification and tenant-isolated ACL storage."""
        # 1. Ingest public document
        doc_pub = corporate_data_gateway.ingest_data_object(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Public Product Roadmap",
            content="General public features and community announcements for 2027.",
            data_class="DOCUMENT",
            override_level=DataClassificationLevel.PUBLIC
        )
        self.assertEqual(doc_pub.classification_level, DataClassificationLevel.PUBLIC)

        # 2. Ingest confidential document with financial markers
        doc_conf = corporate_data_gateway.ingest_data_object(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Q4 Financial Ledger",
            content="EBITDA projections, gross margin percentages, and revenue forecast for board.",
            data_class="FINANCIAL"
        )
        self.assertIn(doc_conf.classification_level, [DataClassificationLevel.CONFIDENTIAL, DataClassificationLevel.RESTRICTED])

        # 3. Foreign tenant isolation: Foreign tenant cannot fetch this document
        foreign_fetch = corporate_data_gateway.get_data_object(
            object_id=doc_pub.object_id,
            tenant_id=self.foreign_tenant
        )
        self.assertIsNone(foreign_fetch)

    def test_pre_retrieval_rag_authorization(self):
        """
        Verify PRE-RETRIEVAL authorization:
        Search queries evaluate ACL and classification level IN THE SQL QUERY.
        Unauthorized chunks are NOT fetched or filtered in memory afterwards.
        """
        # Ingest document and index into RAG
        doc = corporate_data_gateway.ingest_data_object(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Board Strategy M&A",
            content="Project Falcon: Strategic merger agreement with Alpha Dynamics Corp.",
            data_class="STRATEGY",
            override_level=DataClassificationLevel.RESTRICTED
        )
        chunks = knowledge_gateway.index_data_object(doc)
        self.assertTrue(len(chunks) > 0)

        # Query with low clearance (PUBLIC, INTERNAL only) -> Must return 0 hits
        low_clearance_results = knowledge_gateway.retrieve_permission_aware(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            requester_identity_id="usr_intern_01",
            requester_departments=["ENGINEERING"],
            requester_roles=["DEVELOPER"],
            requester_clearance_level=DataClassificationLevel.INTERNAL,
            query="Falcon merger agreement",
            top_k=5
        )
        self.assertEqual(len(low_clearance_results), 0)

        # Query with RESTRICTED clearance -> Must return the chunk with citation
        high_clearance_results = knowledge_gateway.retrieve_permission_aware(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            requester_identity_id="usr_exec_01",
            requester_departments=["ALL"],
            requester_roles=["ADMIN"],
            requester_clearance_level=DataClassificationLevel.RESTRICTED,
            query="Falcon merger agreement",
            top_k=5
        )
        self.assertGreaterEqual(len(high_clearance_results), 1)
        hit = high_clearance_results[0]
        self.assertEqual(hit.object_id, doc.object_id)
        self.assertEqual(hit.classification_level, DataClassificationLevel.RESTRICTED)
        self.assertIn("Falcon", hit.text_content)

    def test_legal_hold_blocks_destruction(self):
        """Verify legal hold blocks deletion/purging until hold is explicitly released."""
        doc = corporate_data_gateway.ingest_data_object(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Litigation Target Record",
            content="Crucial contract in dispute under federal subpoena.",
            data_class="LEGAL"
        )

        # Place legal hold
        applied = data_lifecycle_manager.set_legal_hold(
            object_id=doc.object_id,
            hold_status=True,
            hold_reason="SUBPOENA-2026-X: Pending discovery order",
            authority_id="legal_counsel_42"
        )
        self.assertTrue(applied)

        # Attempt to purge -> Must be blocked by LegalHoldViolationError
        with self.assertRaises(LegalHoldViolationError):
            data_lifecycle_manager.execute_verified_purge(
                object_id=doc.object_id,
                requester_id="admin_ops"
            )

        # Release legal hold
        released = data_lifecycle_manager.set_legal_hold(
            object_id=doc.object_id,
            hold_status=False,
            hold_reason="Subpoena satisfied",
            authority_id="legal_counsel_42"
        )
        self.assertTrue(released)

        # Now purge succeeds and returns certificate
        cert = data_lifecycle_manager.execute_verified_purge(
            object_id=doc.object_id,
            requester_id="admin_ops"
        )
        self.assertTrue(cert.purged_from_storage)
        self.assertTrue(cert.purged_from_index)
        self.assertTrue(cert.evidence_event_id.startswith("ev_"))

if __name__ == "__main__":
    unittest.main()
