"""
ZONATA Sovereign Core — Sub-Step 5F: Compliance Engineering & Control Matrix Generator.
=======================================================================================
Governed by:
- Rule 46: No compliance claims. Code, UI and docs may state implemented controls
  and point to evidence. They never say 'compliant', 'certified' or 'secure' without
  an independent audit on record.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zonata.compliance.matrix")


# Rule 46: Banned phrases that make unverified marketing/legal claims
BANNED_COMPLIANCE_CLAIMS = [
    re.compile(r"\b(100%\s+compliant|fully\s+compliant|guaranteed\s+compliant)\b", re.IGNORECASE),
    re.compile(r"\b(certified\s+secure|100%\s+secure|completely\s+secure)\b", re.IGNORECASE),
    re.compile(r"\b(unhackable|impenetrable|bulletproof\s+security)\b", re.IGNORECASE),
]


class Rule46ClaimViolation(Exception):
    """Rule 46: Disallowed unsubstantiated compliance claim detected."""
    pass


@dataclass
class SecurityControlEntry:
    control_id: str
    framework: str
    requirement: str
    implementation_mechanism: str
    code_reference: str
    test_verification: str
    status: str = "IMPLEMENTED_CONTROL"  # Honest factual status (Rule 46)


class ControlMatrixGenerator:
    """Generates an honest, evidence-grounded security control matrix under Rule 46."""

    CONTROLS: List[SecurityControlEntry] = [
        SecurityControlEntry(
            control_id="ISO-27001-A.9.2",
            framework="ISO/IEC 27001:2022",
            requirement="User Registration and Access Management",
            implementation_mechanism="Keycloak OIDC JWT token validation, RoleTier hierarchy, SCIM user lifecycle",
            code_reference="core/ports/identity.py, core/identity/types.py",
            test_verification="tests/test_step5_identity_access.py::test_01_oidc_token_validation_lifecycle",
        ),
        SecurityControlEntry(
            control_id="ISO-27001-A.9.4.2",
            framework="ISO/IEC 27001:2022",
            requirement="Password and Credential Management",
            implementation_mechanism="Customer integration API keys with prefix lookup and salted SHA-256 storage (Rule 41)",
            code_reference="core/identity/api_keys.py",
            test_verification="tests/test_step5_identity_access.py::test_09_customer_api_key_lifecycle_and_scopes",
        ),
        SecurityControlEntry(
            control_id="ISO-27001-A.10.1",
            framework="ISO/IEC 27001:2022",
            requirement="Cryptographic Controls and Key Management",
            implementation_mechanism="OpenBao Transit envelope encryption, key rotation, and zero plaintext in DB (Rule 41)",
            code_reference="core/ports/secrets.py, core/ports/kms.py",
            test_verification="tests/test_step5_secrets_platform.py::test_03_transit_envelope_encryption_and_rotation",
        ),
        SecurityControlEntry(
            control_id="SOC2-CC6.1",
            framework="SOC 2 Type II",
            requirement="Logical Access Controls and Role Separation",
            implementation_mechanism="Owner principal immutability (Rule 44), dual-control cooling-off transfers, machine session prohibition",
            code_reference="core/identity/ownership.py, core/identity/workload.py",
            test_verification="tests/test_step5_identity_access.py::test_07_dual_control_ownership_transfer_and_cooling_off",
        ),
        SecurityControlEntry(
            control_id="SOC2-CC6.3",
            framework="SOC 2 Type II",
            requirement="Multi-Tenant Database Isolation and Access Boundaries",
            implementation_mechanism="Transaction-scoped tenant context (Rule 43) via set_config(..., true) and forced PostgreSQL RLS",
            code_reference="core/db.py, core/db_security.py",
            test_verification="tests/test_step5_database_isolation.py::test_01_transaction_scoped_tenant_context_rule43",
        ),
        SecurityControlEntry(
            control_id="SOC2-CC6.6",
            framework="SOC 2 Type II",
            requirement="Perimeter Defense and Application Boundary Protection",
            implementation_mechanism="Host header injection validation, ASVS V14.4 CORS controls, WAF attack inspection",
            code_reference="core/security/api_hardening.py",
            test_verification="tests/test_step5_app_supply_chain_security.py::test_01_host_header_validation_and_poisoning_rejection",
        ),
        SecurityControlEntry(
            control_id="HIPAA-164.312(a)",
            framework="HIPAA Security Rule",
            requirement="Unique User Identification & Emergency Access",
            implementation_mechanism="IdentityTokenContext with session IDs, MFA enforcement on high-privilege tiers, multi-channel recovery",
            code_reference="core/identity/ownership.py, core/ports/identity.py",
            test_verification="tests/test_step5_identity_access.py::test_08_multi_channel_recovery_rejects_email_alone_rule44",
        ),
        SecurityControlEntry(
            control_id="DPDP-SEC-8.5",
            framework="DPDP Act 2023",
            requirement="Data Subject Access & Right to Correction / Erasure",
            implementation_mechanism="DSAR export bundle generator and cryptographic shredding of tenant Transit keys",
            code_reference="core/privacy/dsar.py",
            test_verification="tests/test_step5_audit_privacy_compliance.py::test_04_crypto_shredding_erasure",
        ),
        SecurityControlEntry(
            control_id="GDPR-ART-33",
            framework="GDPR (EU 2016/679)",
            requirement="Notification of a Personal Data Breach to Supervisory Authority",
            implementation_mechanism="Statutory 72-hour breach notification package coordinator with evidence references",
            code_reference="core/privacy/dsar.py",
            test_verification="tests/test_step5_audit_privacy_compliance.py::test_05_breach_notification_report",
        ),
        SecurityControlEntry(
            control_id="SLSA-LEVEL-3",
            framework="SLSA / Supply Chain",
            requirement="Hermetic Builds, SBOM Generation & Cryptographic Signatures",
            implementation_mechanism="CycloneDX SBOM validation, Rule 5 open-source license deny-list, Cosign Transit signatures",
            code_reference="core/security/supply_chain.py",
            test_verification="tests/test_step5_app_supply_chain_security.py::test_08_cosign_artifact_signing_and_verification",
        ),
    ]

    @classmethod
    def generate_markdown(cls) -> str:
        lines = [
            "# ZONATA Sovereign OS — Security Controls & Implementation Matrix",
            "",
            "> **Governed by Standing Rule 46:** This matrix states factual implemented technical controls and points to",
            "> verifiable test evidence in the codebase. It does not make unverified claims of third-party certification.",
            "",
            "| Control ID | Framework | Technical Requirement | Implemented Mechanism | Code Reference | Verification Test | Status |",
            "|---|---|---|---|---|---|---|",
        ]

        for ctrl in cls.CONTROLS:
            lines.append(
                f"| `{ctrl.control_id}` | {ctrl.framework} | {ctrl.requirement} | {ctrl.implementation_mechanism} | "
                f"`{ctrl.code_reference}` | `{ctrl.test_verification}` | `{ctrl.status}` |"
            )

        lines.append("")
        return "\n".join(lines)

    @classmethod
    def write_to_file(cls, path: str = "docs/security/CONTROL_MATRIX.md") -> str:
        content = cls.generate_markdown()
        cls.verify_rule_46(content)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    @staticmethod
    def verify_rule_46(text: str) -> None:
        """Rule 46 Grep Linter: Rejects forbidden unsubstantiated marketing claims."""
        for pat in BANNED_COMPLIANCE_CLAIMS:
            m = pat.search(text)
            if m:
                raise Rule46ClaimViolation(
                    f"Rule 46 Violation: Document contains disallowed compliance claim: '{m.group(0)}'"
                )
