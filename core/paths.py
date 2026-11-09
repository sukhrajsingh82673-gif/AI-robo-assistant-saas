"""
Portable repository path resolution.

Several subsystems historically defaulted to the reference deployment path
``/root/roboassistant``. That is correct on the sovereign host but wrong in CI
and in any other checkout, where the default silently pointed at a directory
that does not exist. Defaults now derive from this file's location, with an
explicit ``ZONATA_REPO_ROOT`` override, and keep recognising the canonical path
so already-recorded absolute paths still resolve.
"""

import os

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

CANONICAL_ROOT = "/root/roboassistant"


def get_repo_root() -> str:
    """Return the active checkout root (``ZONATA_REPO_ROOT`` wins)."""
    override = os.environ.get("ZONATA_REPO_ROOT")
    return os.path.abspath(override) if override else REPO_ROOT
