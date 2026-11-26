"""ZONATA Governed Document Backbone.

Implements OpenCode Step 1E: Universal Document, File, Folio, and Ledger System.
"""

from core.documents.schema import (
    DocumentStatus,
    SensitivityLevel,
    DocumentChannel,
    ClassificationMethod,
    ReviewStatus,
    VersionStatus,
    ensure_document_backbone_tables,
)
from core.documents.safety import (
    SniffResult,
    sniff_content_safety,
    wrap_untrusted_content_for_model,
    scan_for_prompt_injections,
)
from core.documents.pipeline import (
    DocumentPipeline,
    PipelineResult,
)
from core.documents.versioning import (
    create_document_version,
    get_document_version_payload,
    run_integrity_sweep,
    BlobCorruptionError,
)
from core.documents.retention import (
    apply_legal_hold,
    release_legal_hold,
    dispose_document,
    LegalHoldEnforcedError,
    RetentionPeriodActiveError,
)
from core.documents.sharing import (
    create_access_grant,
    check_access,
    create_share_link,
    access_share_link,
    revoke_share_link,
    AccessDeniedError,
    ShareLinkExpiredError,
    ShareLinkRevokedError,
)
from core.documents.search import (
    search_documents,
)
from core.documents.generation import (
    generate_document_from_template,
    sign_pdf_document,
    SIGNATURE_LEGAL_DISCLAIMER,
)

__all__ = [
    "DocumentStatus",
    "SensitivityLevel",
    "DocumentChannel",
    "ClassificationMethod",
    "ReviewStatus",
    "VersionStatus",
    "ensure_document_backbone_tables",
    "SniffResult",
    "sniff_content_safety",
    "wrap_untrusted_content_for_model",
    "scan_for_prompt_injections",
    "DocumentPipeline",
    "PipelineResult",
    "create_document_version",
    "get_document_version_payload",
    "run_integrity_sweep",
    "BlobCorruptionError",
    "apply_legal_hold",
    "release_legal_hold",
    "dispose_document",
    "LegalHoldEnforcedError",
    "RetentionPeriodActiveError",
    "create_access_grant",
    "check_access",
    "create_share_link",
    "access_share_link",
    "revoke_share_link",
    "AccessDeniedError",
    "ShareLinkExpiredError",
    "ShareLinkRevokedError",
    "search_documents",
    "generate_document_from_template",
    "sign_pdf_document",
    "SIGNATURE_LEGAL_DISCLAIMER",
]
