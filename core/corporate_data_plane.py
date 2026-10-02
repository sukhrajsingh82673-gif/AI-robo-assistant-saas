"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 5 — Enterprise Corporate Data Plane
Governed data gateway for all enterprise information: documents, emails, CRM, ERP, code, and databases.
Enforces multi-tenant isolation, row-level ACLs, residency boundaries, and legal holds.

Constitutional Invariants:
  CAPABILITY != DATA_ACCESS
  DATA_ACCESS != TOOL_ACCESS
  TENANT_A_DATA != TENANT_B_DATA
  DELETED_DATA != RETRIEVABLE_DATA
"""

import time
import json
import uuid
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from core.database_engine import engine, WorkloadType
from core.data_classification_engine import classification_engine, DataClassificationLevel, SensitivityCategory, CLASSIFICATION_ORDER

logger = logging.getLogger("zonata.corporate.data")

class DataObjectClass:
    DOCUMENT = "DOCUMENT"
    SPREADSHEET = "SPREADSHEET"
    EMAIL = "EMAIL"
    CRM_RECORD = "CRM_RECORD"
    ERP_RECORD = "ERP_RECORD"
    HR_RECORD = "HR_RECORD"
    SUPPORT_TICKET = "SUPPORT_TICKET"
    SOURCE_CODE = "SOURCE_CODE"
    DATABASE_ROW = "DATABASE_ROW"
    LOG = "LOG"

class DeletionState:
    ACTIVE = "ACTIVE"
    MARKED_FOR_DELETION = "MARKED_FOR_DELETION"
    PURGED = "PURGED"

@dataclass
class DataObjectACL:
    allowed_departments: List[str]
    allowed_roles: List[str]
    allowed_identities: List[str]
    requires_mfa: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed_departments": self.allowed_departments,
            "allowed_roles": self.allowed_roles,
            "allowed_identities": self.allowed_identities,
            "requires_mfa": self.requires_mfa
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'DataObjectACL':
        return cls(
            allowed_departments=d.get("allowed_departments", []),
            allowed_roles=d.get("allowed_roles", []),
            allowed_identities=d.get("allowed_identities", []),
            requires_mfa=d.get("requires_mfa", False)
        )

@dataclass
class CorporateDataObject:
    object_id: str
    tenant_id: str
    company_id: str
    title: str
    data_class: str
    source_system: str
    source_object_id: str
    classification_level: str
    sensitivity_categories: List[str]
    owner_identity_id: str
    acl: DataObjectACL
    content_hash: str
    raw_content: str
    residency_region: str
    retention_days: int
    legal_hold: bool
    deletion_state: str
    created_at: float
    updated_at: float
    provenance: Dict[str, Any]

class CorporateDataGateway:
    """
    Central Corporate Data Plane Gateway.
    All enterprise business records and documents must pass through this gateway.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS corporate_data_objects (
                object_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                title TEXT NOT NULL,
                data_class TEXT NOT NULL,
                source_system TEXT NOT NULL,
                source_object_id TEXT NOT NULL,
                classification_level TEXT NOT NULL,
                sensitivity_categories JSON NOT NULL,
                owner_identity_id TEXT NOT NULL,
                acl JSON NOT NULL,
                content_hash TEXT NOT NULL,
                raw_content TEXT NOT NULL,
                residency_region TEXT NOT NULL DEFAULT 'US-EAST',
                retention_days INTEGER NOT NULL DEFAULT 365,
                legal_hold INTEGER NOT NULL DEFAULT 0,
                deletion_state TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                provenance JSON
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_corp_tenant ON corporate_data_objects(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_corp_class ON corporate_data_objects(classification_level);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_corp_del ON corporate_data_objects(deletion_state);")

    # -------------------------------------------------------------
    # 1. Ingest & Seal Data Object
    # -------------------------------------------------------------
    def ingest_data_object(
        self,
        tenant_id: str,
        company_id: str,
        title: str,
        content: str,
        data_class: str = "DOCUMENT",
        source_system: str = "INTERNAL_DOC",
        source_object_id: Optional[str] = None,
        owner_identity_id: str = "usr_system",
        acl: Optional[DataObjectACL] = None,
        admin_classification_override: Optional[str] = None,
        override_level: Optional[str] = None,
        residency_region: str = "US-EAST",
        retention_days: int = 365,
        provenance_metadata: Optional[Dict[str, Any]] = None
    ) -> CorporateDataObject:
        """Ingest, classify, hash, and persist a corporate data object."""
        admin_override = admin_classification_override or override_level
        eff_source_obj_id = source_object_id or f"src_{uuid.uuid4().hex[:8]}"

        # 1. Auto-classify content with policy floor
        eff_level, categories, reasons = classification_engine.classify_content(
            text_content=content,
            admin_policy_level=admin_override,
            source_system=source_system
        )

        object_id = f"doc_{uuid.uuid4().hex[:12]}"
        now = time.time()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        default_acl = acl or DataObjectACL(
            allowed_departments=["ALL"],
            allowed_roles=["VIEWER", "EMPLOYEE", "ADMIN", "OWNER"],
            allowed_identities=[]
        )

        obj = CorporateDataObject(
            object_id=object_id,
            tenant_id=tenant_id,
            company_id=company_id,
            title=title,
            data_class=data_class,
            source_system=source_system,
            source_object_id=eff_source_obj_id,
            classification_level=eff_level,
            sensitivity_categories=categories,
            owner_identity_id=owner_identity_id,
            acl=default_acl,
            content_hash=content_hash,
            raw_content=content,
            residency_region=residency_region,
            retention_days=retention_days,
            legal_hold=False,
            deletion_state=DeletionState.ACTIVE,
            created_at=now,
            updated_at=now,
            provenance={
                **(provenance_metadata or {}),
                "classification_reasons": reasons,
                "ingestion_timestamp": now
            }
        )

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO corporate_data_objects (
                object_id, tenant_id, company_id, title, data_class, source_system,
                source_object_id, classification_level, sensitivity_categories,
                owner_identity_id, acl, content_hash, raw_content, residency_region,
                retention_days, legal_hold, deletion_state, created_at, updated_at, provenance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obj.object_id, obj.tenant_id, obj.company_id, obj.title, obj.data_class,
                obj.source_system, obj.source_object_id, obj.classification_level,
                json.dumps(obj.sensitivity_categories), obj.owner_identity_id,
                json.dumps(obj.acl.to_dict()), obj.content_hash, obj.raw_content,
                obj.residency_region, obj.retention_days, 0, obj.deletion_state,
                obj.created_at, obj.updated_at, json.dumps(obj.provenance)
            ))

        logger.info(f"Ingested corporate data object: {object_id} ({title}) [Level: {eff_level}]")
        return obj

    # -------------------------------------------------------------
    # 2. Authorization & Access Gate
    # -------------------------------------------------------------
    def check_access(
        self,
        tenant_id: str,
        company_id: str,
        requester_identity_id: str,
        requester_departments: List[str],
        requester_roles: List[str],
        requester_clearance_level: str,
        object_id: str,
        action: str = "READ"
    ) -> Tuple[bool, str]:
        """
        Evaluate access permission to a corporate data object.
        Returns: (is_allowed, reason)
        """
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("SELECT * FROM corporate_data_objects WHERE object_id = ?", (object_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Data object not found."

        # Invariant 1: Multi-tenant boundary
        if row["tenant_id"] != tenant_id:
            return False, "Tenant isolation boundary violation (TENANT_A_DATA != TENANT_B_DATA)."

        # Invariant 2: Deletion state
        if row["deletion_state"] != DeletionState.ACTIVE:
            return False, f"Data object cannot be accessed (State: {row['deletion_state']}). DELETED_DATA != RETRIEVABLE_DATA."

        # Invariant 3: Classification clearance check
        doc_level = row["classification_level"]
        doc_score = CLASSIFICATION_ORDER.get(doc_level, 5)
        clearance_score = CLASSIFICATION_ORDER.get(requester_clearance_level, 1)

        if clearance_score < doc_score:
            return False, f"Insufficient security clearance ({requester_clearance_level}) for {doc_level} document."

        # Invariant 4: ACL verification
        acl_data = json.loads(row["acl"])
        allowed_depts = acl_data.get("allowed_departments", [])
        allowed_roles = acl_data.get("allowed_roles", [])
        allowed_ids = acl_data.get("allowed_identities", [])

        # Check explicit identity allowlist or ownership
        if requester_identity_id == row["owner_identity_id"] or requester_identity_id in allowed_ids:
            return True, "Access granted via direct identity authorization."

        # Check department and role intersection
        dept_match = "ALL" in allowed_depts or any(d in allowed_depts for d in requester_departments)
        role_match = "ALL" in allowed_roles or any(r in allowed_roles for r in requester_roles)

        if dept_match and role_match:
            return True, "Access granted via department and role ACL."

        return False, "Access denied by data object ACL."

    def get_data_object(self, object_id: str, tenant_id: Optional[str] = None) -> Optional[CorporateDataObject]:
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("SELECT * FROM corporate_data_objects WHERE object_id = ?", (object_id,))
            row = cursor.fetchone()
            if not row:
                return None
            if tenant_id and row["tenant_id"] != tenant_id:
                return None
            return CorporateDataObject(
                object_id=row["object_id"],
                tenant_id=row["tenant_id"],
                company_id=row["company_id"],
                title=row["title"],
                data_class=row["data_class"],
                source_system=row["source_system"],
                source_object_id=row["source_object_id"],
                classification_level=row["classification_level"],
                sensitivity_categories=json.loads(row["sensitivity_categories"]),
                owner_identity_id=row["owner_identity_id"],
                acl=DataObjectACL.from_dict(json.loads(row["acl"])),
                content_hash=row["content_hash"],
                raw_content=row["raw_content"],
                residency_region=row["residency_region"],
                retention_days=row["retention_days"],
                legal_hold=bool(row["legal_hold"]),
                deletion_state=row["deletion_state"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                provenance=json.loads(row["provenance"]) if row["provenance"] else {}
            )

    def mark_for_deletion(self, object_id: str, requested_by: str) -> bool:
        """Mark an object for deletion, checking legal hold first."""
        obj = self.get_data_object(object_id)
        if not obj:
            return False

        if obj.legal_hold:
            raise PermissionError(f"Cannot delete object {object_id}: Under active LEGAL HOLD.")

        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE corporate_data_objects
            SET deletion_state = 'MARKED_FOR_DELETION', updated_at = ?
            WHERE object_id = ?
            """, (now, object_id))
        logger.info(f"Object {object_id} marked for deletion by {requested_by}")
        return True

# Global singleton
corporate_data_gateway = CorporateDataGateway()
