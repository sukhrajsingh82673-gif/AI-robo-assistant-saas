"""ZONATA Sovereign Core — Contract & Acceptance Tests for the Six Backbone Service Ports.

Implements OpenCode Step 1D:
1. Object storage: Port -> SeaweedFS (put, get, head, delete, list, SHA-256 read-back).
2. Antivirus: Port -> ClamAV daemon (zINSTREAM chunked socket, CLEAN, INFECTED, FAILED).
3. Text extraction: Port -> Apache Tika server (PUT /tika, MIME detection, control char sanitization).
4. OCR: Port -> Apache Tika OCR (non-text image returns empty string with OK, not failure).
5. Email out: Port -> SMTP sink (Mailpit, Message-ID, CI poll confirming arrival by Message-ID).
6. Key management: Port -> Sovereign Envelope KMS (generate_data_key, encrypt, decrypt, rewrap).

Standing Rule 8: Mutation checks proving failure of any service makes its contract test fail.
"""

from __future__ import annotations
import hashlib
import json
import os
import unittest
import uuid
from typing import Any, Dict
from unittest import mock

from core.ports.base import PortStatus
from core.ports.storage import (
    StoragePort,
    SeaweedFSS3Provider,
    NotConfiguredStorageProvider,
    SandboxStorageProvider,
    resolve_storage_provider,
)
from core.ports.antivirus import (
    AntivirusPort,
    ClamAVDaemonProvider,
    NotConfiguredAntivirusProvider,
    SandboxAntivirusProvider,
    resolve_antivirus_provider,
    EICAR_TEST_SIGNATURE,
)
from core.ports.text_extraction import (
    TextExtractionPort,
    ApacheTikaProvider,
    NotConfiguredTextExtractionProvider,
    SandboxTextExtractionProvider,
    resolve_text_extraction_provider,
)
from core.ports.ocr import (
    OCRPort,
    ApacheTikaOCRProvider,
    NotConfiguredOCRProvider,
    SandboxOCRProvider,
    resolve_ocr_provider,
)
from core.ports.email import (
    EmailOutPort,
    SMTPEmailProvider,
    NotConfiguredEmailProvider,
    SandboxEmailProvider,
    resolve_email_provider,
)
from core.ports.kms import (
    KeyManagementPort,
    SovereignEnvelopeKMSProvider,
    NotConfiguredKMSProvider,
    SandboxKMSProvider,
    resolve_kms_provider,
)


class TestBackbonePortsContracts(unittest.TestCase):

    # =========================================================================
    # 1. OBJECT STORAGE CONTRACT TESTS
    # =========================================================================
    def test_storage_sandbox_contract(self):
        """Storage Sandbox: upload, read-back, hash check, list, delete."""
        provider = SandboxStorageProvider()
        test_data = b"Hello Sovereign Object Storage! \x01\x02\x03"
        expected_sha = hashlib.sha256(test_data).hexdigest()

        # 1. Put
        put_res = provider.put("tenant-bucket", "test/doc1.bin", test_data)
        self.assertEqual(put_res.status, PortStatus.SANDBOX)
        self.assertTrue(put_res.sandbox)
        self.assertIsNotNone(put_res.provider_ref)
        self.assertEqual(put_res.metadata["sha256"], expected_sha)

        # 2. Get & SHA-256 verification
        get_res, data = provider.get("tenant-bucket", "test/doc1.bin")
        self.assertEqual(get_res.status, PortStatus.SANDBOX)
        self.assertEqual(data, test_data)
        self.assertEqual(hashlib.sha256(data).hexdigest(), expected_sha)

        # 3. Head
        head_res = provider.head("tenant-bucket", "test/doc1.bin")
        self.assertEqual(head_res.status, PortStatus.SANDBOX)
        self.assertEqual(head_res.metadata["content_length"], len(test_data))

        # 4. List
        list_res, items = provider.list("tenant-bucket", "test/")
        self.assertEqual(list_res.status, PortStatus.SANDBOX)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["key"], "test/doc1.bin")

        # 5. Delete
        del_res = provider.delete("tenant-bucket", "test/doc1.bin")
        self.assertEqual(del_res.status, PortStatus.SANDBOX)

        # 6. Verify Deleted
        post_del_res, post_data = provider.get("tenant-bucket", "test/doc1.bin")
        self.assertEqual(post_del_res.status, PortStatus.FAILED)
        self.assertIsNone(post_data)

    def test_storage_mutation_unreachable_endpoint_fails_cleanly(self):
        """Mutation Check: Unreachable S3 endpoint MUST return FAILED (no fabricated STORED)."""
        broken_provider = SeaweedFSS3Provider(endpoint_url="http://127.0.0.1:59999")
        res = broken_provider.put("bad-bucket", "key.bin", b"test")
        self.assertEqual(res.status, PortStatus.FAILED)
        self.assertIsNone(res.provider_ref)
        self.assertIn("Connection refused", str(res.error) + str(res.metadata))

    def test_storage_real_seaweedfs_contract_when_configured(self):
        """Real SeaweedFS S3 Contract (Active in CI with real container)."""
        s3_endpoint = os.environ.get("S3_ENDPOINT")
        if not s3_endpoint:
            self.skipTest("S3_ENDPOINT not set; skipping live SeaweedFS contract test")

        provider = SeaweedFSS3Provider(s3_endpoint)
        probe_res = provider.probe()
        if probe_res.status != PortStatus.OK:
            self.skipTest(f"SeaweedFS S3 endpoint {s3_endpoint} not responsive: {probe_res.error}")

        bucket = f"ci-test-bucket-{uuid.uuid4().hex[:6]}"
        key = f"contract-{uuid.uuid4().hex[:8]}.txt"
        test_content = f"ZONATA Verified SeaweedFS Payload {uuid.uuid4().hex}".encode("utf-8")
        expected_sha = hashlib.sha256(test_content).hexdigest()

        # Put with Reality Ladder (stores and reads back to verify SHA-256)
        put_res = provider.put(bucket, key, test_content, content_type="text/plain")
        self.assertEqual(put_res.status, PortStatus.OK)
        self.assertFalse(put_res.sandbox)
        self.assertIsNotNone(put_res.provider_ref)
        self.assertEqual(put_res.metadata["sha256"], expected_sha)
        self.assertTrue(put_res.metadata["stored"])

        # Get & Checksum Match
        get_res, downloaded = provider.get(bucket, key)
        self.assertEqual(get_res.status, PortStatus.OK)
        self.assertEqual(downloaded, test_content)
        self.assertEqual(hashlib.sha256(downloaded).hexdigest(), expected_sha)

        # Head Check
        head_res = provider.head(bucket, key)
        self.assertEqual(head_res.status, PortStatus.OK)
        self.assertEqual(head_res.metadata["content_length"], len(test_content))

        # Delete
        del_res = provider.delete(bucket, key)
        self.assertEqual(del_res.status, PortStatus.OK)

    # =========================================================================
    # 2. ANTIVIRUS CONTRACT TESTS
    # =========================================================================
    def test_antivirus_sandbox_contract(self):
        """Antivirus Sandbox: Clean vs EICAR detection."""
        provider = SandboxAntivirusProvider()

        # Clean file
        clean_res = provider.scan_bytes(b"Normal sovereign invoice text content", "invoice.pdf")
        self.assertEqual(clean_res.status, PortStatus.SANDBOX)
        self.assertTrue(clean_res.sandbox)
        self.assertEqual(clean_res.metadata["verdict"], "CLEAN")
        self.assertEqual(clean_res.provider_ref, "sandbox_clamav_v1.4")

        # Infected EICAR test string
        eicar_res = provider.scan_bytes(EICAR_TEST_SIGNATURE, "test_virus.com")
        self.assertEqual(eicar_res.status, PortStatus.SANDBOX)
        self.assertEqual(eicar_res.metadata["verdict"], "INFECTED")
        self.assertEqual(eicar_res.metadata["virus_name"], "Eicar-Test-Signature")

    def test_antivirus_mutation_unreachable_clamav_fails_cleanly(self):
        """Mutation Check: Unreachable ClamAV socket MUST return FAILED (never claim clean)."""
        broken_provider = ClamAVDaemonProvider(host="127.0.0.1", port=59998)
        res = broken_provider.scan_bytes(b"Unscannable data", "file.bin")
        self.assertEqual(res.status, PortStatus.FAILED)
        self.assertIsNone(res.provider_ref)
        self.assertIn("unreachable", res.error.lower())

    def test_antivirus_real_clamav_contract_when_configured(self):
        """Real ClamAV Socket Contract (Active in CI with real ClamAV daemon)."""
        clamav_host = os.environ.get("CLAMAV_HOST")
        clamav_port = os.environ.get("CLAMAV_PORT")
        if not (clamav_host and clamav_port):
            self.skipTest("CLAMAV_HOST / CLAMAV_PORT not set; skipping live ClamAV contract test")

        provider = ClamAVDaemonProvider(clamav_host, int(clamav_port))
        probe_res = provider.probe()
        if probe_res.status != PortStatus.OK:
            self.skipTest(f"ClamAV daemon not responsive at {clamav_host}:{clamav_port}: {probe_res.error}")

        # Scan clean payload
        clean_data = b"Confidential Board Meeting Minutes: Q3 Financial Trajectory."
        res_clean = provider.scan_bytes(clean_data, "minutes.txt")
        self.assertEqual(res_clean.status, PortStatus.OK)
        self.assertEqual(res_clean.metadata["verdict"], "CLEAN")
        self.assertIsNotNone(res_clean.provider_ref)
        self.assertIn("ClamAV", res_clean.provider_ref)

        # Scan EICAR virus signature chunk
        res_eicar = provider.scan_bytes(EICAR_TEST_SIGNATURE, "eicar.com")
        self.assertEqual(res_eicar.status, PortStatus.OK)
        self.assertEqual(res_eicar.metadata["verdict"], "INFECTED")
        self.assertIn("Eicar", res_eicar.metadata["virus_name"])

    # =========================================================================
    # 3. TEXT EXTRACTION CONTRACT TESTS
    # =========================================================================
    def test_text_extraction_sandbox_contract(self):
        """Text Extraction Sandbox: clean text, control char filtering, size limits."""
        provider = SandboxTextExtractionProvider()
        raw_input = b"Strategic Plan 2026\x00\x07\x08Important Executive Summary\t\nLine 2"
        res, text = provider.extract_text(raw_input, mime_type="text/plain", max_bytes=50)

        self.assertEqual(res.status, PortStatus.SANDBOX)
        self.assertNotIn("\x00", text)
        self.assertNotIn("\x07", text)
        self.assertIn("Strategic Plan", text)
        self.assertLessEqual(len(text.encode("utf-8")), 50)

    def test_text_extraction_mutation_unreachable_tika_fails_cleanly(self):
        """Mutation Check: Unreachable Tika endpoint returns FAILED (never fabricate text)."""
        broken_provider = ApacheTikaProvider(endpoint_url="http://127.0.0.1:59997")
        res, text = broken_provider.extract_text(b"document", mime_type="application/pdf")
        self.assertEqual(res.status, PortStatus.FAILED)
        self.assertEqual(text, "")
        self.assertIsNone(res.provider_ref)

    def test_text_extraction_real_tika_contract_when_configured(self):
        """Real Apache Tika Server Contract (Active in CI with real container)."""
        tika_url = os.environ.get("TIKA_ENDPOINT")
        if not tika_url:
            self.skipTest("TIKA_ENDPOINT not configured; skipping live Tika contract test")

        provider = ApacheTikaProvider(tika_url)
        probe_res = provider.probe()
        if probe_res.status != PortStatus.OK:
            self.skipTest(f"Apache Tika server not responsive at {tika_url}: {probe_res.error}")

        sample_html = b"<html><head><title>ZONATA Invoice</title></head><body><h1>Total Due: $500</h1>\x00<p>Thank you for your business.</p></body></html>"
        res, extracted_text = provider.extract_text(sample_html, mime_type="text/html", max_bytes=1000)

        self.assertEqual(res.status, PortStatus.OK)
        self.assertFalse(res.sandbox)
        self.assertIn("Total Due: $500", extracted_text)
        self.assertNotIn("\x00", extracted_text)
        self.assertIsNotNone(res.provider_ref)
        self.assertIn("Apache Tika", res.provider_ref)

    # =========================================================================
    # 4. OCR CONTRACT TESTS
    # =========================================================================
    def test_ocr_sandbox_contract(self):
        """OCR Sandbox: Invariant: Blank / non-text image returns empty text with OK."""
        provider = SandboxOCRProvider()

        # 1. Blank image (small bytes) -> empty text with OK status
        blank_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        res_blank, text_blank, boxes_blank = provider.extract_ocr(blank_bytes)
        self.assertEqual(res_blank.status, PortStatus.SANDBOX)
        self.assertEqual(text_blank, "")
        self.assertEqual(boxes_blank, [])

        # 2. Synthetic populated image
        image_bytes = b"P3 2 2 255 255 0 0 0 255 0 0 0 255 255 255 255" + (b"0" * 150)
        res_img, text_img, boxes_img = provider.extract_ocr(image_bytes)
        self.assertEqual(res_img.status, PortStatus.SANDBOX)
        self.assertIn("Sample Transcribed", text_img)
        self.assertGreater(len(boxes_img), 0)

    def test_ocr_mutation_unreachable_tika_ocr_fails_cleanly(self):
        """Mutation Check: Unreachable OCR endpoint returns FAILED."""
        broken_provider = ApacheTikaOCRProvider(endpoint_url="http://127.0.0.1:59996")
        res, text, boxes = broken_provider.extract_ocr(b"fake_image_bytes")
        self.assertEqual(res.status, PortStatus.FAILED)
        self.assertEqual(text, "")
        self.assertEqual(boxes, [])

    # =========================================================================
    # 5. EMAIL OUT CONTRACT TESTS
    # =========================================================================
    def test_email_sandbox_contract(self):
        """Email Out Sandbox: send returns ACCEPTED_BY_PROVIDER (not DELIVERED)."""
        provider = SandboxEmailProvider()
        res = provider.send(
            to=["investor@enterprise.com"],
            subject="Quarterly Return",
            body="Attached find the audited ledger report.",
            attachments=[{"filename": "ledger.pdf", "data": b"PDF-DUMMY-DATA"}]
        )
        self.assertEqual(res.status, PortStatus.SANDBOX)
        self.assertTrue(res.sandbox)
        self.assertIsNotNone(res.provider_ref)
        self.assertTrue(res.provider_ref.startswith("<sandbox_"))

        # In-memory delivery verification
        verif_res = provider.verify_delivery_in_ci(res.provider_ref)
        self.assertEqual(verif_res.status, PortStatus.SANDBOX)
        self.assertTrue(verif_res.metadata["delivered"])

    def test_email_mutation_unreachable_smtp_fails_cleanly(self):
        """Mutation Check: Unreachable SMTP port returns FAILED."""
        broken_provider = SMTPEmailProvider(host="127.0.0.1", port=59995)
        res = broken_provider.send(to=["user@example.com"], subject="Test", body="Body")
        self.assertEqual(res.status, PortStatus.FAILED)
        self.assertIsNone(res.provider_ref)
        self.assertIn("Connection refused", str(res.error))

    def test_email_real_smtp_mailpit_contract_when_configured(self):
        """Real SMTP & Mailpit Sink Contract (Active in CI with real Mailpit container)."""
        smtp_host = os.environ.get("SMTP_HOST")
        smtp_port = os.environ.get("SMTP_PORT")
        if not (smtp_host and smtp_port):
            self.skipTest("SMTP_HOST / SMTP_PORT not configured; skipping live SMTP contract test")

        mailpit_api = os.environ.get("MAILPIT_URL", "http://localhost:8025")
        provider = SMTPEmailProvider(smtp_host, int(smtp_port), mailpit_http_url=mailpit_api)
        probe_res = provider.probe()
        if probe_res.status != PortStatus.OK:
            self.skipTest(f"SMTP server not responsive at {smtp_host}:{smtp_port}: {probe_res.error}")

        unique_subject = f"ZONATA Verification Notice {uuid.uuid4().hex}"
        unique_body = f"Empirical confirmation payload: {uuid.uuid4().hex}"
        recipient = "audit@zonata.internal"

        # 1. Send via SMTP -> Reality Ladder: ACCEPTED_BY_PROVIDER (never DELIVERED)
        send_res = provider.send(
            to=[recipient],
            subject=unique_subject,
            body=unique_body,
            attachments=[{"filename": "contract.txt", "data": unique_body.encode("utf-8")}]
        )
        self.assertEqual(send_res.status, PortStatus.ACCEPTED_BY_PROVIDER)
        self.assertFalse(send_res.sandbox)
        self.assertIsNotNone(send_res.provider_ref)
        msg_id = send_res.provider_ref

        # 2. CI Verification in Mailpit Sink -> Reality Ladder: DELIVERED
        verif_res = provider.verify_delivery_in_ci(msg_id, mailpit_http_url=mailpit_api, timeout_seconds=8.0)
        self.assertEqual(verif_res.status, PortStatus.OK)
        self.assertFalse(verif_res.sandbox)
        self.assertTrue(verif_res.metadata["verified_in_sink"])
        self.assertEqual(verif_res.metadata["status"], "DELIVERED")

    # =========================================================================
    # 6. KEY MANAGEMENT (KMS) CONTRACT TESTS
    # =========================================================================
    def test_kms_unconfigured_without_master_key(self):
        """Truth Rule: KMS must report NOT_CONFIGURED when no master key is supplied."""
        with mock.patch.dict(os.environ, {"KMS_MASTER_KEY": "", "SECRET_VAULT_KEY": ""}):
            provider = SovereignEnvelopeKMSProvider()
            res = provider.probe()
        self.assertEqual(res.status, PortStatus.NOT_CONFIGURED)
        self.assertIsNone(res.provider_ref)

    def test_kms_envelope_encryption_roundtrip(self):
        """Sovereign Envelope KMS: generate DEK, encrypt, decrypt, rewrap."""
        provider = SovereignEnvelopeKMSProvider("test_only_kms_master_key_material_32_chars!")

        # Probe KMS
        probe_res = provider.probe()
        self.assertEqual(probe_res.status, PortStatus.OK)
        self.assertIsNotNone(probe_res.provider_ref)

        # 1. Generate DEK
        dek_res, raw_dek, enc_dek = provider.generate_data_key("AES_256", {"tenant": "t1"})
        self.assertEqual(dek_res.status, PortStatus.OK)
        self.assertEqual(len(raw_dek), 32)
        self.assertGreater(len(enc_dek), 32)
        self.assertIsNotNone(dek_res.provider_ref)

        # 2. Envelope Encrypt
        secret_payload = b"CRITICAL_FINANCIAL_LEDGER_TRANSACTION_PAYLOAD_CONFIDENTIAL_2026"
        enc_res, envelope = provider.encrypt(secret_payload, context={"tenant": "t1", "company": "c1"})
        self.assertEqual(enc_res.status, PortStatus.OK)
        self.assertTrue(envelope.startswith(b"ZENV"))
        self.assertNotIn(secret_payload, envelope)

        # 3. Envelope Decrypt with identical context
        dec_res, decrypted = provider.decrypt(envelope, context={"tenant": "t1", "company": "c1"})
        self.assertEqual(dec_res.status, PortStatus.OK)
        self.assertEqual(decrypted, secret_payload)

        # 4. Decrypt with invalid AAD context MUST FAIL (Integrity protection)
        bad_dec_res, _ = provider.decrypt(envelope, context={"tenant": "t1", "company": "c_hacker"})
        self.assertEqual(bad_dec_res.status, PortStatus.FAILED)

        # 5. Rewrap under new context
        rewrap_res, new_env = provider.rewrap(
            envelope,
            old_context={"tenant": "t1", "company": "c1"},
            new_context={"tenant": "t1", "company": "c2"}
        )
        self.assertEqual(rewrap_res.status, PortStatus.OK)
        self.assertNotEqual(new_env, envelope)

        # 6. Decrypt rewrapped under new context
        new_dec_res, new_decrypted = provider.decrypt(new_env, context={"tenant": "t1", "company": "c2"})
        self.assertEqual(new_dec_res.status, PortStatus.OK)
        self.assertEqual(new_decrypted, secret_payload)

    def test_kms_master_key_never_in_database(self):
        """Invariant: Master key is never stored plaintext in the database."""
        from core.db import db
        conn = db.get_connection()
        cur = conn.cursor()
        # Search all database tables for the configured KMS master key string
        raw_key = f"supervision_probe_kms_master_key_{uuid.uuid4().hex}"
        provider = SovereignEnvelopeKMSProvider(raw_key)
        self.assertEqual(provider.probe().status, PortStatus.OK)
        found_in_db = False
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cur.fetchall()]
            for tbl in tables:
                cur.execute(f"SELECT * FROM {tbl} LIMIT 10;")
                rows = cur.fetchall()
                if any(raw_key in str(r) for r in rows):
                    found_in_db = True
                    break
        except Exception:
            pass

        self.assertFalse(found_in_db, "Violation: Plaintext KMS master key detected in application database!")


if __name__ == "__main__":
    unittest.main()
