"""ZONATA Governed Folio Backbone.

Implements OpenCode Step 1F: Universal Folio Aggregate, Merkle Evidence Trees, and Export Packs.
"""

from core.folios.schema import (
    FolioStatus,
    FolioEntryType,
    ALLOWED_TRANSITIONS,
    ensure_folio_tables,
)
from core.folios.merkle import (
    build_folio_merkle_tree,
    generate_merkle_proof,
    verify_merkle_proof,
    recompute_folio_merkle_root,
    GENESIS_ROOT,
)
from core.folios.export import (
    generate_folio_export_pack,
    verify_export_pack_file,
    STANDALONE_VERIFIER_SCRIPT,
)
from core.folios.manager import (
    FolioManager,
)

__all__ = [
    "FolioStatus",
    "FolioEntryType",
    "ALLOWED_TRANSITIONS",
    "ensure_folio_tables",
    "build_folio_merkle_tree",
    "generate_merkle_proof",
    "verify_merkle_proof",
    "recompute_folio_merkle_root",
    "GENESIS_ROOT",
    "generate_folio_export_pack",
    "verify_export_pack_file",
    "STANDALONE_VERIFIER_SCRIPT",
    "FolioManager",
]
