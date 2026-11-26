"""
ZONATA Agent Factory — Open-Source Licence Gate (Rule 5).

Audits imported agent/skill packages against approved permissive open-source licences:
Permitted: MIT, Apache 2.0, BSD-2/3-Clause, ISC, CC0, Unlicense.
Forbidden: GPL, AGPL, SSPL, BSL, Elastic, Sustainable-Use (Copyleft / Source-Available).
"""

from __future__ import annotations

import re
from typing import Set

from core.agent_import.types import LicenseViolationError

# Permitted permissive licenses under Rule 5
PERMITTED_LICENSES: Set[str] = {
    "mit",
    "apache-2.0",
    "apache 2.0",
    "apache-2",
    "apache2",
    "bsd-2-clause",
    "bsd-3-clause",
    "bsd",
    "isc",
    "cc0-1.0",
    "cc0",
    "unlicense",
    "0bsd",
}

DISALLOWED_PATTERN = re.compile(
    r"\b(AGPL|SSPL|BSL|ELASTIC|SUSTAINABLE-USE)\b|\b(?<!L)GPL\b",
    re.IGNORECASE,
)


class LicenseGate:
    """
    Validates open-source package licenses against Rule 5 compliance rules.
    """

    @classmethod
    def verify_license(cls, license_name: str) -> bool:
        clean = license_name.strip()
        if not clean:
            raise LicenseViolationError("Package lacks an identifiable license.")

        # Check explicit copyleft regex
        if DISALLOWED_PATTERN.search(clean):
            raise LicenseViolationError(
                f"License '{clean}' is a disallowed copyleft or source-available license per Rule 5."
            )

        # Check allow-list
        norm = clean.lower().replace("_", "-")
        if any(norm == p or norm.startswith(p + " ") or f"({p})" in norm for p in PERMITTED_LICENSES):
            return True

        # Unknown license fails closed
        raise LicenseViolationError(
            f"License '{clean}' is not recognized on the Rule 5 permissive allow-list."
        )
