"""
ZONATA Industry Pack Repository & Discovery Registry (OpenCode Step 1H)
Provides access to validated, declarative industry blueprints across the platform.
"""

import os
import pathlib
from typing import Any, Dict, List, Optional

from core.industry_packs.loader import IndustryPackLoader
from core.industry_packs.schema import validate_industry_pack_dict


class IndustryPackRegistry:
    """Discovers and caches declarative industry packs from packs/industries."""

    def __init__(self, packs_root: Optional[str] = None):
        if packs_root:
            self.root = pathlib.Path(packs_root)
        else:
            base_dir = pathlib.Path(__file__).resolve().parent.parent.parent
            self.root = base_dir / "packs" / "industries"

        self._loader = IndustryPackLoader()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._isic_index: Dict[str, str] = {}
        self._discovered = False

    def discover_packs(self) -> None:
        """Discovers all pack.yaml and pack.json files under packs/industries."""
        if not self.root.exists():
            self._discovered = True
            return

        for p in self.root.rglob("pack.y*ml"):
            try:
                pack_data = self._loader.load_pack_from_file(str(p))
                pack_id = pack_data["metadata"]["pack_id"]
                isic_code = pack_data["metadata"]["industry_code"]
                self._cache[pack_id] = pack_data
                self._isic_index[isic_code] = pack_id
            except Exception:
                pass

        for p in self.root.rglob("pack.json"):
            try:
                pack_data = self._loader.load_pack_from_file(str(p))
                pack_id = pack_data["metadata"]["pack_id"]
                isic_code = pack_data["metadata"]["industry_code"]
                self._cache[pack_id] = pack_data
                self._isic_index[isic_code] = pack_id
            except Exception:
                pass

        self._discovered = True

    def register_pack(self, pack_data: Dict[str, Any]) -> None:
        """Manually registers an in-memory validated industry pack."""
        validated = validate_industry_pack_dict(pack_data)
        pack_id = validated["metadata"]["pack_id"]
        isic_code = validated["metadata"]["industry_code"]
        self._cache[pack_id] = validated
        self._isic_index[isic_code] = pack_id

    def get_pack(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a pack by its pack_id."""
        if not self._discovered:
            self.discover_packs()
        return self._cache.get(pack_id)

    def find_by_isic(self, isic_code: str) -> Optional[Dict[str, Any]]:
        """Retrieves a pack matching a UN ISIC Rev. 4 taxonomy code."""
        if not self._discovered:
            self.discover_packs()
        clean = isic_code.strip().upper()
        pack_id = self._isic_index.get(clean)
        if pack_id:
            return self._cache.get(pack_id)
        # Search by partial or division match
        for code, p_id in self._isic_index.items():
            if code.startswith(clean) or clean.startswith(code):
                return self._cache.get(p_id)
        return None

    def list_packs(self) -> List[Dict[str, Any]]:
        """Lists metadata for all discovered industry packs."""
        if not self._discovered:
            self.discover_packs()
        return [
            {
                "pack_id": p["metadata"]["pack_id"],
                "name": p["metadata"]["name"],
                "version": p["metadata"]["version"],
                "industry_code": p["metadata"]["industry_code"],
                "description": p["metadata"].get("description", ""),
            }
            for p in self._cache.values()
        ]


# Singleton global registry instance
industry_pack_registry = IndustryPackRegistry()
