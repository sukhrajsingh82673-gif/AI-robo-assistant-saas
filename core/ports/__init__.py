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
    CapabilityTruthTable,
    capability_truth_table,
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
from core.ports.llm import (
    LLMGatewayPort,
    ModelTier,
    llm_gateway,
)
from core.ports.workflow import (
    WorkflowEnginePort,
    WorkflowEngineResult,
    WorkflowRunSpec,
    LocalWorkflowEngine,
    NotConfiguredWorkflowEngineProvider,
    SandboxWorkflowEngineProvider,
    resolve_workflow_provider,
)
from core.ports.browser import (
    BrowserPort,
    browser_port,
    BrowserExecutionResult,
    BrowserPageSnapshot,
    SandboxBrowserProvider,
)
from core.ports.search import (
    SearchPort,
    search_port,
    SearchExecutionResult,
    SearchResultItem,
    SandboxSearchProvider,
)
from core.ports.terminal import (
    TerminalPort,
    terminal_port,
    TerminalCommandResult,
    SandboxTerminalProvider,
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
    "CapabilityTruthTable",
    "capability_truth_table",
    # Workflow
    "WorkflowEnginePort",
    "WorkflowEngineResult",
    "WorkflowRunSpec",
    "LocalWorkflowEngine",
    "NotConfiguredWorkflowEngineProvider",
    "SandboxWorkflowEngineProvider",
    "resolve_workflow_provider",
    # LLM Gateway
    "LLMGatewayPort",
    "ModelTier",
    "llm_gateway",
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
    # Browser
    "BrowserPort",
    "browser_port",
    # Search
    "SearchPort",
    "search_port",
    "SearchExecutionResult",
    "SearchResultItem",
    # Terminal
    "TerminalPort",
    "terminal_port",
    "TerminalCommandResult",
]
