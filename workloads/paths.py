"""
Portable filesystem resolution for operational workloads.

The workloads used to hard-code the canonical deployment directory
``/roboassistant/storage/sandbox``. That path is valid on the reference host
but does not exist in CI or in any other checkout, so execution failed with
``PermissionError: '/roboassistant'`` instead of producing artifacts.

Resolution order:
1. ``ZONATA_SANDBOX_DIR`` — explicit override (tests / CI).
2. ``$ZONATA_STORAGE_DIR/sandbox`` — shared storage relocation.
3. ``<checkout>/storage/sandbox`` — default derived from this module.
"""

import os

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)


def get_sandbox_dir() -> str:
    """Return the writable sandbox directory, creating it if needed."""
    override = os.environ.get("ZONATA_SANDBOX_DIR")
    if override:
        root = os.path.abspath(override)
    else:
        storage_root = os.environ.get("ZONATA_STORAGE_DIR")
        root = (
            os.path.abspath(os.path.join(storage_root, "sandbox"))
            if storage_root
            else os.path.join(REPO_ROOT, "storage", "sandbox")
        )
    os.makedirs(root, exist_ok=True)
    return root


def sandbox_artifact(*parts: str) -> str:
    """Absolute path to an artifact inside the governed sandbox."""
    return os.path.join(get_sandbox_dir(), *parts)
