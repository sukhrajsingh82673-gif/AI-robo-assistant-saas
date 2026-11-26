"""
Legal and Statutory Translation Guard (Rule 71 & Rule 73)
Enforces certified human review for statutory contracts, tax filings, and regulatory compliance.
Unreviewed machine translations are strictly rejected to prevent non-compliance liability.
"""

from typing import Dict, Any, Optional
import datetime


class UnreviewedLegalTranslationBlockedError(PermissionError):
    """Raised when machine translation is attempted on legal/statutory documents without certified human review."""
    pass


class TranslationGuard:
    """Guards statutory, financial, and legal texts from unverified automated translation."""

    RESTRICTED_DOCUMENT_TYPES = {
        "STATUTORY_TAX_FILING",
        "LEGAL_CONTRACT",
        "CONSOLIDATED_FINANCIAL_REPORT",
        "REGULATORY_SUBMISSION",
        "EMPLOYMENT_AGREEMENT",
        "DATA_PROTECTION_AGREEMENT",
    }

    @classmethod
    def verify_translation_eligibility(
        cls,
        document_type: str,
        source_lang: str,
        target_lang: str,
        is_human_certified: bool = False,
        certified_reviewer_id: Optional[str] = None,
        certification_timestamp: Optional[str] = None,
    ) -> bool:
        """
        Validates whether translation is allowed for the document type.
        If the document type is restricted and not human-certified, raises UnreviewedLegalTranslationBlockedError.
        """
        if document_type.upper() in cls.RESTRICTED_DOCUMENT_TYPES:
            if not is_human_certified or not certified_reviewer_id:
                raise UnreviewedLegalTranslationBlockedError(
                    f"UNREVIEWED_LEGAL_TRANSLATION_BLOCKED: Document type '{document_type}' requires "
                    f"certified human translation review before delivery to legal or tax authorities. "
                    f"Source: {source_lang}, Target: {target_lang}."
                )

        return True
