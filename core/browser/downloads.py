"""
ZONATA Browser Download Pipeline & Malware Defense (Rule 32 / Sub-Step 3E)
Routes downloads through ClamAV scanning and blocks executable files from local execution.
"""

from __future__ import annotations

import os
import hashlib
import uuid
import logging
from typing import Dict, Optional, Any

from core.ports.antivirus import resolve_antivirus_provider
from core.documents.schema import DocumentChannel
from core.evidence_service import evidence_service
from .types import BrowserDownloadResult

logger = logging.getLogger("zonata.browser.downloads")

EXECUTABLE_EXTENSIONS = {
    ".exe", ".dmg", ".pkg", ".deb", ".rpm", ".sh", ".bat",
    ".ps1", ".msi", ".jar", ".wasm", ".bin", ".elf", ".so",
    ".dll", ".cmd", ".vbs", ".command", ".scr", ".app"
}


class BrowserDownloadPipeline:
    """
    Governs files downloaded by the browser.
    Scans with ClamAV and strictly forbids execution of downloaded binaries.
    """

    def __init__(self):
        pass

    def process_download(
        self,
        filename: str,
        payload: bytes,
        tenant_id: str,
        company_id: str,
        actor_id: str = "browser_agent",
    ) -> BrowserDownloadResult:
        download_id = f"dwn_{uuid.uuid4().hex[:12]}"
        byte_size = len(payload)
        sha256_hash = hashlib.sha256(payload).hexdigest()
        ext = os.path.splitext(filename)[1].lower()

        # 1. Antivirus / ClamAV Scanning via AntivirusPort (Step 1E intake)
        av_provider = resolve_antivirus_provider()
        scan_res = av_provider.scan_bytes(data=payload, filename=filename)

        is_infected = scan_res.metadata.get("verdict") == "INFECTED"
        quarantine_id = f"quar_{download_id}" if is_infected else None

        # 2. Executable File Analysis (Rule 32)
        is_executable = ext in EXECUTABLE_EXTENSIONS

        if is_infected:
            execution_permitted = False
            retention_status = "QUARANTINED"
            rejection_reason = f"MALWARE_DETECTED_CLAMAV: {scan_res.threat_name or 'Infected'}"
        elif is_executable:
            # Rule 32: Executables require human approval to retain and cannot be executed
            execution_permitted = False
            retention_status = "REQUIRES_HUMAN_APPROVAL_TO_RETAIN"
            rejection_reason = "EXECUTION_FORBIDDEN_RULE_32: Downloaded executable files cannot be executed by browser hand or host agent."
        else:
            execution_permitted = True
            retention_status = "RETAINED"
            rejection_reason = None

        # 3. Cryptographic Evidence Ledger Recording
        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="BROWSER_DOWNLOAD_PROCESSED",
            payload={
                "download_id": download_id,
                "filename": filename,
                "extension": ext,
                "byte_size": byte_size,
                "sha256": sha256_hash,
                "clamav_clean": not is_infected,
                "is_executable": is_executable,
                "execution_permitted": execution_permitted,
                "retention_status": retention_status,
                "rejection_reason": rejection_reason,
            },
        )

        return BrowserDownloadResult(
            download_id=download_id,
            filename=filename,
            extension=ext,
            byte_size=byte_size,
            sha256=sha256_hash,
            clamav_scanned=True,
            is_infected=is_infected,
            is_executable=is_executable,
            execution_permitted=execution_permitted,
            retention_status=retention_status,
            rejection_reason=rejection_reason,
            quarantine_id=quarantine_id,
        )
