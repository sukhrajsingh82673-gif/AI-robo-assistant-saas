"""
Regional Cellular Routing and Sovereign Data Residency (Rule 73 & ADR 0044)
Enforces cell isolation: tenant data strictly resides within the designated jurisdiction cell.
Direct unencrypted or un-consented cross-region operations are refused at the routing layer.
"""

from typing import Dict, Any, Optional, Set
from dataclasses import dataclass


class CrossRegionOperationRefusedError(PermissionError):
    """Raised when an operation attempts to move or query data across regional cells without lawful basis."""
    pass


@dataclass
class RegionalCell:
    cell_id: str
    jurisdiction_code: str       # ISO 3166-1 alpha-2 or regional code (e.g., 'EU', 'US', 'IN')
    cloud_region: str            # e.g., 'europe-west3', 'us-east-1', 'asia-south1'
    sovereign_boundary: str      # e.g., 'GDPR_EEA', 'US_COMMERCIAL', 'INDIA_DPDP'
    is_active: bool = True


class CellRouter:
    """Routes and validates tenant operations against regional sovereign cells."""

    CELLS: Dict[str, RegionalCell] = {
        "cell-eu-frankfurt": RegionalCell(
            cell_id="cell-eu-frankfurt",
            jurisdiction_code="EU",
            cloud_region="europe-west3",
            sovereign_boundary="GDPR_EEA"
        ),
        "cell-us-east": RegionalCell(
            cell_id="cell-us-east",
            jurisdiction_code="US",
            cloud_region="us-east-1",
            sovereign_boundary="US_COMMERCIAL"
        ),
        "cell-in-mumbai": RegionalCell(
            cell_id="cell-in-mumbai",
            jurisdiction_code="IN",
            cloud_region="asia-south1",
            sovereign_boundary="INDIA_DPDP"
        ),
    }

    # Map country codes to sovereign cells
    JURISDICTION_TO_CELL: Dict[str, str] = {
        "DE": "cell-eu-frankfurt",
        "FR": "cell-eu-frankfurt",
        "BE": "cell-eu-frankfurt",
        "IT": "cell-eu-frankfurt",
        "PL": "cell-eu-frankfurt",
        "ES": "cell-eu-frankfurt",
        "NL": "cell-eu-frankfurt",
        "SE": "cell-eu-frankfurt",
        "AT": "cell-eu-frankfurt",
        "EU": "cell-eu-frankfurt",
        "US": "cell-us-east",
        "CA": "cell-us-east",
        "IN": "cell-in-mumbai",
    }

    @classmethod
    def get_cell_for_jurisdiction(cls, country_code: str) -> str:
        """Resolves target cell id for a country code, defaulting to isolated regional cell."""
        return cls.JURISDICTION_TO_CELL.get(country_code.upper(), "cell-us-east")

    @classmethod
    def validate_cross_cell_access(
        cls,
        source_cell_id: str,
        target_cell_id: str,
        operation_type: str,
        has_lawful_transfer_mechanism: bool = False,
        transfer_basis: Optional[str] = None
    ) -> bool:
        """
        Validates cross-cell interaction.
        If cells are identical, returns True.
        If cells differ, requires lawful transfer mechanism (e.g. EU Standard Contractual Clauses, Adequacy).
        Otherwise raises CrossRegionOperationRefusedError.
        """
        if source_cell_id == target_cell_id:
            return True

        if not has_lawful_transfer_mechanism or not transfer_basis:
            raise CrossRegionOperationRefusedError(
                f"CROSS_REGION_OPERATION_REFUSED: Direct data operation between '{source_cell_id}' "
                f"and '{target_cell_id}' for operation '{operation_type}' is blocked under Rule 73. "
                f"Requires lawful transfer mechanism (e.g., SCC, BCR, or Adequacy Decision)."
            )

        return True
