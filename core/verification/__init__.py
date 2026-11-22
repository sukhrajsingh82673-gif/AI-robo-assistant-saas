"""
ZONATA Verification Pyramid Subsystem
OpenCode Step 2H: Five-layer verification engine, layer results, and spot checks.
"""

import os
from core.db import db
from core.verification.types import (
    VerificationLayer,
    VerificationStatus,
    LayerResultStatus,
    VerificationError,
    VerificationLayerFailedError,
    UnauthorizedLayerInvokerError,
    VerificationRecipeNotFoundError,
    IncompleteVerificationError,
    VerificationLayerResult,
    VerificationReport,
    VerificationRecipe,
)
from core.verification.sampling import SpotCheckSampler
from core.verification.layers import (
    BaseVerificationLayer,
    SchemaVerificationLayer,
    DeterministicCodeVerificationLayer,
    CrossRecordVerificationLayer,
    PeerModelVerificationLayer,
    HumanVerificationLayer,
)
from core.verification.engine import VerificationEngine, verification_engine


def ensure_verification_tables(conn=None):
    """Initializes the verification pyramid database tables."""
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "migrations", "common", "0025_verification_pyramid.sql"
    )
    if os.path.exists(migration_path):
        with open(migration_path, "r", encoding="utf-8") as f:
            sql = f.read()
        if conn:
            conn.executescript(sql)
            conn.commit()
        else:
            with db.get_connection() as c:
                c.executescript(sql)
                c.commit()


__all__ = [
    "VerificationLayer",
    "VerificationStatus",
    "LayerResultStatus",
    "VerificationError",
    "VerificationLayerFailedError",
    "UnauthorizedLayerInvokerError",
    "VerificationRecipeNotFoundError",
    "IncompleteVerificationError",
    "VerificationLayerResult",
    "VerificationReport",
    "VerificationRecipe",
    "SpotCheckSampler",
    "BaseVerificationLayer",
    "SchemaVerificationLayer",
    "DeterministicCodeVerificationLayer",
    "CrossRecordVerificationLayer",
    "PeerModelVerificationLayer",
    "HumanVerificationLayer",
    "VerificationEngine",
    "verification_engine",
    "ensure_verification_tables",
]
