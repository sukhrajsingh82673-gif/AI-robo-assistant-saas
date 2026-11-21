"""ZONATA Sovereign Core — Ports & Provider Framework."""

from core.ports.base import (
    Port,
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    NotImplementedProvider,
    SandboxProvider,
    PortRegistry,
    port_registry,
)

# Convenience port accessor
get_port = port_registry.get
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

__all__ = [
    "Port",
    "PortStatus",
    "ProviderResult",
    "NotConfiguredProvider",
    "NotImplementedProvider",
    "SandboxProvider",
    "PortRegistry",
    "port_registry",
    # Storage
    "StoragePort",
    "SeaweedFSS3Provider",
    "NotConfiguredStorageProvider",
    "SandboxStorageProvider",
    "resolve_storage_provider",
    # Antivirus
    "AntivirusPort",
    "ClamAVDaemonProvider",
    "NotConfiguredAntivirusProvider",
    "SandboxAntivirusProvider",
    "resolve_antivirus_provider",
    # Text Extraction
    "TextExtractionPort",
    "ApacheTikaProvider",
    "NotConfiguredTextExtractionProvider",
    "SandboxTextExtractionProvider",
    "resolve_text_extraction_provider",
    # OCR
    "OCRPort",
    "ApacheTikaOCRProvider",
    "NotConfiguredOCRProvider",
    "SandboxOCRProvider",
    "resolve_ocr_provider",
    # Email
    "EmailOutPort",
    "SMTPEmailProvider",
    "NotConfiguredEmailProvider",
    "SandboxEmailProvider",
    "resolve_email_provider",
    # KMS
    "KeyManagementPort",
    "SovereignEnvelopeKMSProvider",
    "NotConfiguredKMSProvider",
    "SandboxKMSProvider",
    "resolve_kms_provider",
]
