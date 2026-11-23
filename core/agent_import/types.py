"""
ZONATA Sovereign Core — Agent Factory Import Lane Contracts (OpenCode Step 3J).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ImportSourceType(str, Enum):
    GITHUB_REPO = "GITHUB_REPO"
    PYPI_PACKAGE = "PYPI_PACKAGE"
    NPM_PACKAGE = "NPM_PACKAGE"
    LOCAL_ARCHIVE = "LOCAL_ARCHIVE"


class SkillCertificationStatus(str, Enum):
    PENDING_SCAN = "PENDING_SCAN"
    CERTIFIED = "CERTIFIED"
    REJECTED_LICENSE = "REJECTED_LICENSE"
    REJECTED_MALWARE = "REJECTED_MALWARE"
    REJECTED_DANGEROUS_CODE = "REJECTED_DANGEROUS_CODE"


class LicenseViolationError(Exception):
    """Raised when an imported package carries an unapproved or copyleft license."""
    pass


class MalwareDetectedError(Exception):
    """Raised when ClamAV or malware heuristics flag an imported artifact."""
    pass


class DangerousCodeRejectedError(Exception):
    """Raised when static analysis detects dangerous AST patterns (eval, exec, fork bombs)."""
    pass


class SandboxExecutionError(Exception):
    """Raised when sandboxed execution exceeds quotas or violates sandbox boundary."""
    pass


@dataclass
class ImportedSkillPackage:
    skill_id: str
    name: str
    version: str
    source_type: ImportSourceType
    source_url: str
    license_name: str
    sha256: str
    certification_status: SkillCertificationStatus = SkillCertificationStatus.PENDING_SCAN
    quarantine_path: Optional[str] = None
    imported_at: float = field(default_factory=time.time)
    security_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "source_type": self.source_type.value,
            "source_url": self.source_url,
            "license_name": self.license_name,
            "sha256": self.sha256,
            "certification_status": self.certification_status.value,
            "quarantine_path": self.quarantine_path,
            "imported_at": self.imported_at,
            "security_metadata": self.security_metadata,
        }
