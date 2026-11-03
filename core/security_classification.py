"""
ZONATA Corporate Security — 6-Tier Data Classification Matrix
"""
from enum import Enum
from typing import Dict, Any

class InformationClassification(str, Enum):
    PUBLIC = "PUBLIC"                              # Unrestricted external disclosure
    CUSTOMER_SHAREABLE = "CUSTOMER_SHAREABLE"      # Customers, partners; internal IDs stripped
    INTERNAL = "INTERNAL"                          # Company-wide; financial PII stripped
    CONFIDENTIAL = "CONFIDENTIAL"                  # Departmental managers; salaries masked
    RESTRICTED = "RESTRICTED"                      # C-Suite only; cryptographic tokenization
    HIGHLY_RESTRICTED = "HIGHLY_RESTRICTED"        # Sovereign Owner only; hardware enclave

CLASSIFICATION_LEVELS: Dict[str, int] = {
    InformationClassification.PUBLIC.value: 1,
    InformationClassification.CUSTOMER_SHAREABLE.value: 2,
    InformationClassification.INTERNAL.value: 3,
    InformationClassification.CONFIDENTIAL.value: 4,
    InformationClassification.RESTRICTED.value: 5,
    InformationClassification.HIGHLY_RESTRICTED.value: 6
}
