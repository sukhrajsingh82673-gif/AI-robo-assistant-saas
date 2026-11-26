"""
Portable repository path resolution.

Defaults derive from this file's location, with an explicit
``ZONATA_REPO_ROOT`` override, and recognise the canonical path
so already-recorded absolute paths still resolve.
"""

import os

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

CANONICAL_ROOT = os.environ.get("ZONATA_CANONICAL_ROOT", REPO_ROOT)


def get_repo_root() -> str:
    """Return the active checkout root (``ZONATA_REPO_ROOT`` wins)."""
    override = os.environ.get("ZONATA_REPO_ROOT")
    return os.path.abspath(override) if override else REPO_ROOT
