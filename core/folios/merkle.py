"""ZONATA Sovereign Core — Folio Merkle Evidence Tree Engine.

Implements OpenCode Step 1F:
- Verifiable binary Merkle tree over all folio entries (documents, ledger, tasks, events).
- Deterministic root recalculation on every entry addition or update.
- Third-party zero-knowledge audit proofs: verification requires only leaf hash, audit path, and root.
"""

from __future__ import annotations
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple

from core.db import db


GENESIS_ROOT = "0000000000000000000000000000000000000000000000000000000000000000"


def compute_pair_hash(left_hash: str, right_hash: str) -> str:
    """Computes SHA-256 parent hash of two child nodes."""
    return hashlib.sha256((left_hash + right_hash).encode("utf-8")).hexdigest()


def build_folio_merkle_tree(leaf_hashes: List[str]) -> Tuple[str, List[List[str]]]:
    """Constructs a deterministic binary Merkle tree from a list of leaf hashes.

    Returns (root_hash, levels).
    """
    if not leaf_hashes:
        return GENESIS_ROOT, [[]]

    levels: List[List[str]] = [leaf_hashes]
    current_level = list(leaf_hashes)

    while len(current_level) > 1:
        next_level: List[str] = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if (i + 1 < len(current_level)) else left
            next_level.append(compute_pair_hash(left, right))
        levels.append(next_level)
        current_level = next_level

    return current_level[0], levels


def generate_merkle_proof(
    leaf_hashes: List[str],
    target_index: int
) -> List[Dict[str, str]]:
    """Generates an audit path proof for the leaf at target_index.

    Returns a list of dicts: [{"direction": "left"|"right", "hash": "..."}]
    """
    if not leaf_hashes or target_index < 0 or target_index >= len(leaf_hashes):
        return []

    root, levels = build_folio_merkle_tree(leaf_hashes)
    proof: List[Dict[str, str]] = []
    current_idx = target_index

    for level in levels[:-1]:
        if current_idx % 2 == 0:
            # Current node is left child; sibling is right child
            sibling_idx = current_idx + 1 if (current_idx + 1 < len(level)) else current_idx
            proof.append({"direction": "right", "hash": level[sibling_idx]})
        else:
            # Current node is right child; sibling is left child
            sibling_idx = current_idx - 1
            proof.append({"direction": "left", "hash": level[sibling_idx]})
        current_idx //= 2

    return proof


def verify_merkle_proof(
    leaf_hash: str,
    proof: List[Dict[str, str]],
    expected_root: str
) -> bool:
    """Verifies that leaf_hash belongs to the Merkle tree with expected_root given audit path proof."""
    current_hash = leaf_hash
    for step in proof:
        sibling = step["hash"]
        direction = step["direction"]
        if direction == "right":
            current_hash = compute_pair_hash(current_hash, sibling)
        else:
            current_hash = compute_pair_hash(sibling, current_hash)
    return current_hash == expected_root


def recompute_folio_merkle_root(folio_id: str) -> str:
    """Fetches all entries for folio_id, recalculates Merkle root, and updates database."""
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT entry_hash
            FROM folio_entries
            WHERE folio_id = ?
            ORDER BY sequence_number ASC
            """,
            (folio_id,)
        )
        rows = cur.fetchall()
        leaf_hashes = [r[0] for r in rows]

        root, _ = build_folio_merkle_tree(leaf_hashes)
        now = time.time()
        conn.execute(
            "UPDATE folios SET merkle_root = ?, updated_at = ? WHERE id = ?",
            (root, now, folio_id)
        )
        return root
