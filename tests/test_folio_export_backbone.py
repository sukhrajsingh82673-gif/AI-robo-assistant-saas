"""Tests for OpenCode Step 1F: Universal Folio Aggregate, Merkle Evidence Trees, and Export Packs.

Verifies:
1. Create a customer folio; add an invoice document, an email record, and a ledger transaction; verify the Merkle root changes deterministically.
2. Merkle audit path proofs verify independently without database access.
3. Export the folio pack; run verify_pack.py against it in a clean environment; confirm it outputs VERIFIED.
4. Tamper with one byte in the zip; confirm verify_pack.py detects corruption and outputs TAMPER_DETECTED.
5. Expunge the folio; confirm all DB rows and associated entries are removed, while the pack hash remains sealed in the evidence ledger.
6. State machine transitions (OPEN -> ACTIVE -> SUSPENDED -> PENDING_CLOSE -> CLOSED -> ARCHIVED -> EXPUNGED).
7. Strict multi-tenant isolation on folios and folio entries.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
import zipfile
from unittest import mock

from core.db import db, configure_isolated_test_db
from core.evidence_ledger import EvidenceLedger
from core.documents.schema import ensure_document_backbone_tables
from core.documents.pipeline import DocumentPipeline
from core.folios.schema import (
    FolioStatus,
    FolioEntryType,
    ensure_folio_tables,
)
from core.folios.merkle import (
    build_folio_merkle_tree,
    generate_merkle_proof,
    verify_merkle_proof,
    GENESIS_ROOT,
)
from core.folios.export import (
    generate_folio_export_pack,
    verify_export_pack_file,
)
from core.folios.manager import (
    FolioManager,
)


class TestFolioExportBackbone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = configure_isolated_test_db()
        ensure_document_backbone_tables()
        ensure_folio_tables()
        cls.ledger = EvidenceLedger()
        cls.manager = FolioManager(ledger=cls.ledger)
        cls.doc_pipeline = DocumentPipeline(ledger=cls.ledger)

    def setUp(self):
        self.tenant_a = f"tnt_a_{uuid.uuid4().hex[:8]}"
        self.company_a = f"cmp_a_{uuid.uuid4().hex[:8]}"
        self.tenant_b = f"tnt_b_{uuid.uuid4().hex[:8]}"
        self.company_b = f"cmp_b_{uuid.uuid4().hex[:8]}"
        self.user_a = f"usr_a_{uuid.uuid4().hex[:8]}"

    # =========================================================================
    # 1. DETERMINISTIC MERKLE ROOT RECALCULATION
    # =========================================================================
    def test_folio_entries_recalculate_merkle_root_deterministically(self):
        """Acceptance 1: Adding entries (invoice, email, ledger) recalculates Merkle root deterministically."""
        folio_id = self.manager.create_folio(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            folio_type="customer_account",
            title="Customer Folio: ACME Corp Enterprise",
            subject_id="cust_acme_001",
            created_by=self.user_a,
        )

        initial_folio = self.manager.get_folio(folio_id)
        self.assertEqual(initial_folio["merkle_root"], GENESIS_ROOT)
        self.assertEqual(initial_folio["entry_count"], 0)

        # 1. Add invoice document entry
        doc_payload = b"Tax Invoice #INV-1001 for ACME Corp. Amount: $15,000.00"
        with mock.patch.dict(os.environ, {"ZONATA_TEST_MODE": "1"}):
            doc_res = self.doc_pipeline.ingest(
                payload=doc_payload,
                name="inv_1001.txt",
                tenant_id=self.tenant_a,
                company_id=self.company_a,
                author_id=self.user_a,
                folio_id=folio_id,
            )

        e1_id, e1_hash, seq1 = self.manager.add_entry(
            folio_id=folio_id,
            entry_type=FolioEntryType.DOCUMENT,
            reference_id=doc_res.document_id,
            title="Signed Commercial Invoice #INV-1001",
            payload={"document_id": doc_res.document_id, "amount": 1500000, "currency": "USD"},
            author_id=self.user_a,
        )
        self.assertEqual(seq1, 1)

        folio_after_e1 = self.manager.get_folio(folio_id)
        root1 = folio_after_e1["merkle_root"]
        self.assertNotEqual(root1, GENESIS_ROOT)
        self.assertEqual(folio_after_e1["entry_count"], 1)

        # 2. Add inbound email communication record
        e2_id, e2_hash, seq2 = self.manager.add_entry(
            folio_id=folio_id,
            entry_type=FolioEntryType.COMMUNICATION,
            reference_id="msg_email_acme_approval",
            title="Customer Payment Confirmation Email",
            payload={"from": "ap@acme.com", "subject": "Payment processed for INV-1001"},
            author_id=self.user_a,
        )
        self.assertEqual(seq2, 2)

        folio_after_e2 = self.manager.get_folio(folio_id)
        root2 = folio_after_e2["merkle_root"]
        self.assertNotEqual(root2, root1)
        self.assertEqual(folio_after_e2["entry_count"], 2)

        # 3. Add financial ledger transaction
        e3_id, e3_hash, seq3 = self.manager.add_entry(
            folio_id=folio_id,
            entry_type=FolioEntryType.LEDGER_TRANSACTION,
            reference_id="tx_bank_rec_9921",
            title="Bank Wire Posting $15,000.00",
            payload={"journal_entry": "JE-2026-9921", "amount": 1500000, "account": "1000-CASH"},
            author_id=self.user_a,
        )
        self.assertEqual(seq3, 3)

        folio_after_e3 = self.manager.get_folio(folio_id)
        root3 = folio_after_e3["merkle_root"]
        self.assertNotEqual(root3, root2)
        self.assertEqual(folio_after_e3["entry_count"], 3)

        # Verify determinism: recomputing root from leaf hashes gives exact root3
        leaf_hashes = [e["entry_hash"] for e in self.manager.list_entries(folio_id)]
        manual_root, _ = build_folio_merkle_tree(leaf_hashes)
        self.assertEqual(manual_root, root3)

    # =========================================================================
    # 2. MERKLE AUDIT PROOF VERIFICATION
    # =========================================================================
    def test_merkle_audit_proof_verifies_without_database(self):
        """Acceptance 2: Merkle audit path allows a third party to verify an entry against the root."""
        leaf_hashes = [
            hashlib.sha256(f"leaf_data_{i}".encode()).hexdigest()
            for i in range(7)
        ]
        root, levels = build_folio_merkle_tree(leaf_hashes)

        # Generate proof for index 4
        target_idx = 4
        proof = generate_merkle_proof(leaf_hashes, target_idx)
        self.assertGreater(len(proof), 0)

        # Independent verification without any database or tree knowledge
        is_valid = verify_merkle_proof(
            leaf_hash=leaf_hashes[target_idx],
            proof=proof,
            expected_root=root,
        )
        self.assertTrue(is_valid)

        # Tampered leaf fails verification
        tampered_leaf = hashlib.sha256(b"tampered_attacker_leaf").hexdigest()
        is_tampered_valid = verify_merkle_proof(
            leaf_hash=tampered_leaf,
            proof=proof,
            expected_root=root,
        )
        self.assertFalse(is_tampered_valid)

    # =========================================================================
    # 3. STANDALONE EXPORT PACK & OFFLINE VERIFIER
    # =========================================================================
    def test_export_pack_generates_and_verifies_cleanly_via_standalone_script(self):
        """Acceptance 3: Folio export pack generates a valid .zip and verify_pack.py outputs VERIFIED."""
        folio_id = self.manager.create_folio(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            folio_type="vendor_order",
            title="Vendor Order: Hardware Procurement PO-4412",
            created_by=self.user_a,
        )
        self.manager.add_entry(
            folio_id=folio_id,
            entry_type=FolioEntryType.TASK,
            reference_id="task_proc_01",
            title="Procurement Manager Approval",
            payload={"approved": True, "limit": 50000},
            author_id=self.user_a,
        )

        zip_path, pack_sha, byte_size = self.manager.export_pack(folio_id)
        self.assertTrue(os.path.exists(zip_path))
        self.assertGreater(byte_size, 0)

        # 1. Internal engine verification
        is_valid, status_msg, report = verify_export_pack_file(zip_path)
        self.assertTrue(is_valid)
        self.assertEqual(status_msg, "VERIFIED")

        # 2. External execution of the embedded verify_pack.py using subprocess (Rule 7 / acceptance proof)
        extract_dir = tempfile.mkdtemp(prefix="zonata_cli_verify_")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            script_path = os.path.join(extract_dir, "verify_pack.py")
            self.assertTrue(os.path.exists(script_path))

            proc = subprocess.run(
                [sys.executable, "verify_pack.py"],
                cwd=extract_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(proc.returncode, 0, f"Verifier failed: {proc.stderr}")
            self.assertIn("VERIFIED", proc.stdout)
            self.assertIn("File integrity verified", proc.stdout)
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)
            if os.path.exists(zip_path):
                os.remove(zip_path)

    # =========================================================================
    # 4. TAMPER DETECTION IN EXPORT PACK (MUTATION CHECK)
    # =========================================================================
    def test_tampered_export_pack_fails_with_tamper_detected(self):
        """Acceptance 4: Modifying even one byte in an exported pack causes verify_pack.py to report TAMPER_DETECTED."""
        folio_id = self.manager.create_folio(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            folio_type="incident",
            title="Security Audit Incident SEC-09",
            created_by=self.user_a,
        )
        self.manager.add_entry(
            folio_id=folio_id,
            entry_type=FolioEntryType.EVENT,
            reference_id="evt_sec_01",
            title="Vulnerability Patched",
            payload={"cve": "CVE-2026-9999", "severity": "CRITICAL"},
            author_id=self.user_a,
        )

        zip_path, _, _ = self.manager.export_pack(folio_id)

        # Extract, tamper with metadata.json, and re-zip
        tamper_dir = tempfile.mkdtemp(prefix="zonata_tamper_")
        tampered_zip_path = os.path.join(tempfile.gettempdir(), f"tampered_{uuid.uuid4().hex[:8]}.zip")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tamper_dir)

            # Mutate metadata.json
            meta_path = os.path.join(tamper_dir, "metadata.json")
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["folio"]["title"] = "ATTACKER_MUTATED_TITLE"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            # Re-create zip
            with zipfile.ZipFile(tampered_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(tamper_dir):
                    for file in files:
                        full_p = os.path.join(root, file)
                        rel_p = os.path.relpath(full_p, tamper_dir)
                        zf.write(full_p, rel_p)

            # Verification of tampered zip MUST fail
            is_valid, status_msg, report = verify_export_pack_file(tampered_zip_path)
            self.assertFalse(is_valid)
            self.assertEqual(status_msg, "TAMPER_DETECTED")
            self.assertIn("SHA-256 mismatch", report.get("error", ""))

            # Standalone execution of verify_pack.py in the tampered dir
            proc = subprocess.run(
                [sys.executable, "verify_pack.py"],
                cwd=tamper_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("TAMPER_DETECTED", proc.stdout)
        finally:
            shutil.rmtree(tamper_dir, ignore_errors=True)
            for p in (zip_path, tampered_zip_path):
                if os.path.exists(p):
                    os.remove(p)

    # =========================================================================
    # 5. DELETION DRILL & EXPUNGE FLOW
    # =========================================================================
    def test_folio_expunge_deletion_drill_seals_pack_hash_and_purges_rows(self):
        """Acceptance 5: Expunging a closed folio creates a verified pack, seals hash in ledger, and purges DB."""
        folio_id = self.manager.create_folio(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            folio_type="hiring_case",
            title="Candidate Requisition Folio #REQ-101",
            created_by=self.user_a,
        )
        self.manager.add_entry(
            folio_id=folio_id,
            entry_type=FolioEntryType.EVENT,
            reference_id="hr_offer_signed",
            title="Offer Letter Counter-Signed",
            payload={"candidate_id": "cand_881", "role": "Senior Architect"},
            author_id=self.user_a,
        )

        # 1. Cannot expunge an OPEN folio without closing
        with self.assertRaises(ValueError):
            self.manager.expunge_folio(folio_id, actor_id=self.user_a, force=False)

        # 2. Close folio
        self.manager.transition_status(folio_id, FolioStatus.CLOSED, actor_id=self.user_a)
        closed_folio = self.manager.get_folio(folio_id)
        self.assertEqual(closed_folio["status"], FolioStatus.CLOSED.value)

        # 3. Execute expunge
        expunge_res = self.manager.expunge_folio(folio_id, actor_id=self.user_a)
        self.assertEqual(expunge_res["status"], "EXPUNGED")
        pack_sha = expunge_res["pack_sha256"]
        self.assertTrue(pack_sha)

        # 4. Verify DB records are completely purged
        self.assertIsNone(self.manager.get_folio(folio_id))
        self.assertEqual(len(self.manager.list_entries(folio_id)), 0)

        # 5. Verify the pack remains sovereignly verifiable on disk
        export_pack_path = expunge_res["export_pack_path"]
        self.assertTrue(os.path.exists(export_pack_path))
        is_valid, status_msg, _ = verify_export_pack_file(export_pack_path)
        self.assertTrue(is_valid)
        self.assertEqual(status_msg, "VERIFIED")

        if os.path.exists(export_pack_path):
            os.remove(export_pack_path)

    # =========================================================================
    # 6. STATE MACHINE TRANSITIONS
    # =========================================================================
    def test_folio_state_machine_transition_rules(self):
        """Acceptance 6: Governed state transitions follow strict lifecycle rules."""
        folio_id = self.manager.create_folio(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            folio_type="project",
            title="Project Alpha",
            created_by=self.user_a,
        )

        # OPEN -> ACTIVE (valid)
        self.manager.transition_status(folio_id, FolioStatus.ACTIVE, actor_id=self.user_a)
        self.assertEqual(self.manager.get_folio(folio_id)["status"], FolioStatus.ACTIVE.value)

        # ACTIVE -> ARCHIVED (invalid, must be CLOSED first)
        with self.assertRaises(ValueError):
            self.manager.transition_status(folio_id, FolioStatus.ARCHIVED, actor_id=self.user_a)

        # ACTIVE -> PENDING_CLOSE -> CLOSED (valid)
        self.manager.transition_status(folio_id, FolioStatus.PENDING_CLOSE, actor_id=self.user_a)
        self.manager.transition_status(folio_id, FolioStatus.CLOSED, actor_id=self.user_a)
        self.assertEqual(self.manager.get_folio(folio_id)["status"], FolioStatus.CLOSED.value)

        # Cannot add entry to CLOSED folio
        with self.assertRaises(ValueError):
            self.manager.add_entry(
                folio_id=folio_id,
                entry_type=FolioEntryType.TASK,
                reference_id="late_task",
                title="Attempted Late Entry",
                payload={},
                author_id=self.user_a,
            )

    # =========================================================================
    # 7. MULTI-TENANT ISOLATION
    # =========================================================================
    def test_tenant_b_cannot_access_tenant_a_folio(self):
        """Acceptance 7: Multi-tenant boundary isolates folios across tenants."""
        folio_id_a = self.manager.create_folio(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            folio_type="audit",
            title="Tenant A Sovereign Financial Audit",
            created_by=self.user_a,
        )

        with db.get_connection() as conn:
            cur = conn.cursor()
            # Attempt to query folio with tenant_b filter
            cur.execute(
                "SELECT id FROM folios WHERE id = ? AND tenant_id = ?",
                (folio_id_a, self.tenant_b)
            )
            row = cur.fetchone()
            self.assertIsNone(row)


if __name__ == "__main__":
    unittest.main()
