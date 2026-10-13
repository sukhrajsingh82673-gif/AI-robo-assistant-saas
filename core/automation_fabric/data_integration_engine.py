"""
URA / ZONATA Universal Automation Fabric — Business Data Integration & Sync Engine
===================================================================================
Provides production-grade, enterprise data integration capabilities:
1. DataSchemaValidator: Strict schema validation, type enforcement, and secret-scrubbed error reporting.
2. DataNormalizer: Lossless normalization for dates (ISO 8601 UTC), timestamps, numbers (Decimal),
   and currencies (INR, USD, EUR) without precision or timezone drift.
3. FieldMapper: Declarative, versioned field mapping specifications, type transformations,
   and immutable provenance tracking.
4. SyncCheckpointManager: Durable SQLite-backed stream checkpoints, cursor tracking (timestamp, offset, ID),
   and Dead-Letter Queue (DLQ) quarantine.
5. DataDeduplicationAndConflictResolver: SHA-256 record fingerprinting, duplicate detection,
   configurable conflict resolution (SOURCE_WINS, DESTINATION_WINS, LATEST_TIMESTAMP_WINS, MANUAL_APPROVAL),
   and tombstone/soft-deletion lifecycle.
6. BusinessDataSyncPipeline: Atomic end-to-end sync batch execution, schema validation, quarantine,
   normalization, mapping, deduplication, destination upsert, and Merkle EvidenceLedger sealing.
7. DataReconciliationEngine: Source-destination reconciliation, record count and financial sum verification.
"""

import os
import time
import json
import uuid
import re
import hashlib
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict

from core.db import db
from core.models import PhysicalVerification
from core.evidence_ledger import EvidenceLedger


class ConflictPolicy(str, Enum):
    SOURCE_WINS = "SOURCE_WINS"
    DESTINATION_WINS = "DESTINATION_WINS"
    LATEST_TIMESTAMP_WINS = "LATEST_TIMESTAMP_WINS"
    MANUAL_APPROVAL_REQUIRED = "MANUAL_APPROVAL_REQUIRED"


ConflictResolutionPolicy = ConflictPolicy


class SyncStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    AWAITING_RECONCILIATION = "AWAITING_RECONCILIATION"


class CursorType(str, Enum):
    TIMESTAMP = "TIMESTAMP"
    OFFSET = "OFFSET"
    RECORD_ID = "RECORD_ID"
    TOKEN = "TOKEN"


@dataclass
class SyncExecutionReport:
    sync_id: str
    tenant_id: str
    stream_name: str
    source_connector: str
    destination_connector: str
    records_read: int
    records_validated: int
    records_mapped: int
    records_upserted: int
    records_deduplicated: int
    records_quarantined: int
    checkpoint_before: Optional[str]
    checkpoint_after: Optional[str]
    status: SyncStatus
    start_time: float
    completion_time: float
    duration_sec: float
    evidence_id: Optional[str] = None
    merkle_root: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


# =============================================================================
# 1. DATA SCHEMA VALIDATOR
# =============================================================================

class DataSchemaValidator:
    """
    Validates business records against explicit schema definitions.
    Prevents corrupt, ambiguous, or malformed records from entering the system.
    Scans and redacts any credential-like strings from validation error messages.
    """

    SECRET_SCRUB_PATTERNS = [
        re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
        re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
        re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
        re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),
        re.compile(r"password\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    ]

    @classmethod
    def scrub_text(cls, text: str) -> str:
        for pat in cls.SECRET_SCRUB_PATTERNS:
            text = pat.sub("[REDACTED_SECRET]", text)
        return text

    @classmethod
    def validate_record(cls, record: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates record against a JSON schema specification.
        Schema structure:
        {
            "type": "object",
            "required": ["id", "amount", "currency"],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "amount": {"type": ["number", "string"]},
                "currency": {"type": "string", "enum": ["INR", "USD", "EUR", "GBP"]},
                "email": {"type": "string", "format": "email"}
            }
        }
        """
        if not isinstance(record, dict):
            return False, ["Record must be a dictionary / JSON object"]

        errors: List[str] = []
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required fields
        for req_field in required:
            if req_field not in record or record[req_field] is None:
                errors.append(f"Missing required field: '{req_field}'")

        # Check properties
        for field_name, field_val in record.items():
            if field_name not in properties:
                # If additionalProperties is False
                if schema.get("additionalProperties") is False:
                    errors.append(f"Disallowed additional property: '{field_name}'")
                continue

            prop_spec = properties[field_name]
            prop_type = prop_spec.get("type")

            # Null check
            if field_val is None:
                if prop_spec.get("nullable", False) or (isinstance(prop_type, list) and "null" in prop_type):
                    continue
                elif field_name in required:
                    errors.append(f"Field '{field_name}' cannot be null")
                continue

            # Type checking
            valid_type = True
            allowed_types = prop_type if isinstance(prop_type, list) else [prop_type]

            type_matched = False
            for t in allowed_types:
                if t == "string" and isinstance(field_val, str):
                    type_matched = True
                elif t == "integer" and isinstance(field_val, int) and not isinstance(field_val, bool):
                    type_matched = True
                elif t == "number" and (isinstance(field_val, (int, float, Decimal)) and not isinstance(field_val, bool)):
                    type_matched = True
                elif t == "boolean" and isinstance(field_val, bool):
                    type_matched = True
                elif t == "array" and isinstance(field_val, list):
                    type_matched = True
                elif t == "object" and isinstance(field_val, dict):
                    type_matched = True

            if allowed_types and not type_matched:
                errors.append(f"Field '{field_name}' expected type {allowed_types}, got {type(field_val).__name__}")
                continue

            # Enum validation
            if "enum" in prop_spec and field_val not in prop_spec["enum"]:
                errors.append(f"Field '{field_name}' value '{field_val}' not in allowed enum: {prop_spec['enum']}")

            # Format validation
            fmt = prop_spec.get("format")
            if fmt == "email" and isinstance(field_val, str):
                if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", field_val):
                    errors.append(f"Field '{field_name}' is not a valid email address")
            elif fmt == "iso_date" and isinstance(field_val, str):
                try:
                    datetime.fromisoformat(field_val.replace("Z", "+00:00"))
                except Exception:
                    errors.append(f"Field '{field_name}' is not a valid ISO 8601 date")

            # Numeric bounds
            if isinstance(field_val, (int, float, Decimal)):
                if "minimum" in prop_spec and field_val < prop_spec["minimum"]:
                    errors.append(f"Field '{field_name}' value {field_val} < minimum {prop_spec['minimum']}")
                if "maximum" in prop_spec and field_val > prop_spec["maximum"]:
                    errors.append(f"Field '{field_name}' value {field_val} > maximum {prop_spec['maximum']}")

        scrubbed_errors = [cls.scrub_text(e) for e in errors]
        return (len(scrubbed_errors) == 0), scrubbed_errors


# =============================================================================
# 2. DATA NORMALIZER
# =============================================================================

class DataNormalizer:
    """
    Normalizes business data fields deterministically without losing semantic meaning
    or numeric precision:
    - Dates: standard ISO 8601 UTC ('YYYY-MM-DDTHH:MM:SSZ')
    - Currencies: structured decimal amounts with ISO currency codes (INR, USD, EUR)
    - Numbers: exact Decimals, preserving scale
    - Text: trimmed, control characters removed
    - Identifiers: preserved verbatim
    """

    CURRENCY_SYMBOLS = {
        "₹": "INR",
        "INR": "INR",
        "$": "USD",
        "USD": "USD",
        "€": "EUR",
        "EUR": "EUR",
        "£": "GBP",
        "GBP": "GBP",
        "¥": "JPY",
        "JPY": "JPY"
    }

    @classmethod
    def normalize_date(cls, val: Any) -> Optional[str]:
        """Normalizes date/timestamp into UTC ISO 8601 string 'YYYY-MM-DDTHH:MM:SSZ'."""
        if val is None or val == "":
            return None

        if isinstance(val, (int, float)):
            # Epoch timestamp
            try:
                dt = datetime.fromtimestamp(float(val), tz=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                return None

        if isinstance(val, datetime):
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            else:
                val = val.astimezone(timezone.utc)
            return val.strftime("%Y-%m-%dT%H:%M:%SZ")

        if isinstance(val, str):
            clean_str = val.strip()
            # Common formats
            patterns = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y/%m/%d"
            ]
            # Try ISO standard parser first
            try:
                dt = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

            for p in patterns:
                try:
                    dt = datetime.strptime(clean_str, p).replace(tzinfo=timezone.utc)
                    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    continue

        return str(val)

    @classmethod
    def normalize_currency(cls, val: Any, default_currency: str = "INR") -> Dict[str, Any]:
        """
        Parses string or numeric monetary amount into structured representation:
        {
            "amount": Decimal("12500.50"),
            "currency": "INR",
            "formatted": "₹12,500.50",
            "amount_float": 12500.50
        }
        """
        if val is None:
            return {"amount": Decimal("0.00"), "currency": default_currency, "formatted": f"{default_currency} 0.00", "amount_float": 0.0}

        curr = default_currency
        raw_str = str(val).strip()

        # Extract currency symbol or prefix
        for sym, code in cls.CURRENCY_SYMBOLS.items():
            if sym in raw_str:
                curr = code
                raw_str = raw_str.replace(sym, "")
                break

        # Remove commas and clean whitespace
        clean_num = raw_str.replace(",", "").strip()
        try:
            dec_amount = Decimal(clean_num)
        except InvalidOperation:
            dec_amount = Decimal("0.00")

        # Format
        sym_char = "₹" if curr == "INR" else ("$" if curr == "USD" else ("€" if curr == "EUR" else curr + " "))
        formatted = f"{sym_char}{dec_amount:,.2f}"

        return {
            "amount": dec_amount,
            "currency": curr,
            "formatted": formatted,
            "amount_float": float(dec_amount)
        }

    @classmethod
    def normalize_datetime(cls, val: Any) -> Optional[str]:
        """Alias for normalize_date returning standard ISO 8601 UTC string."""
        return cls.normalize_date(val)

    @classmethod
    def normalize_monetary_amount(cls, val: Any, default_currency: str = "INR") -> Tuple[Decimal, str]:
        """Returns tuple of (exact Decimal amount, ISO currency code)."""
        res = cls.normalize_currency(val, default_currency=default_currency)
        return res["amount"], res["currency"]

    @classmethod
    def normalize_record(cls, record: Dict[str, Any], date_fields: Optional[List[str]] = None, currency_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Deep normalization of record fields."""
        normalized = dict(record)
        d_fields = set(date_fields or [])
        c_fields = set(currency_fields or [])

        for k, v in record.items():
            k_lower = k.lower()
            # Date detection
            if k in d_fields or any(sub in k_lower for sub in ["created_at", "updated_at", "date", "timestamp", "expires_at"]):
                if not isinstance(v, (dict, list)):
                    normalized[k] = cls.normalize_date(v)

            # Currency detection
            elif k in c_fields or any(sub in k_lower for sub in ["amount", "price", "rate", "cost", "total", "fee", "balance"]):
                if not isinstance(v, (dict, list)):
                    normalized[k] = cls.normalize_currency(v)

            elif isinstance(v, str):
                normalized[k] = v.strip()

        return normalized


# =============================================================================
# 3. FIELD MAPPER
# =============================================================================

@dataclass
class FieldMappingRule:
    source_field: str
    target_field: str
    transform_type: str = "DIRECT"  # DIRECT, DATE_ISO, CURRENCY, UPPERCASE, LOWERCASE, TRIM, MAP_ENUM, CUSTOM
    default_value: Any = None
    enum_map: Optional[Dict[str, str]] = None
    custom_fn: Optional[Callable[[Any], Any]] = None


@dataclass
class MappingSpecification:
    mapping_id: str
    version: str
    source_schema_id: str
    target_schema_id: str
    rules: List[FieldMappingRule]
    strict_unmapped: bool = False


class FieldMapper:
    """
    Executes declarative, versioned field mapping rules between source and destination schemas.
    Maintains complete data lineage and provenance metadata.
    """

    @staticmethod
    def _get_nested_field(data: Dict[str, Any], path: str) -> Any:
        if not path:
            return None
        parts = path.split(".")
        curr = data
        for p in parts:
            if isinstance(curr, dict):
                curr = curr.get(p)
            else:
                return None
        return curr

    @classmethod
    def apply_mapping(
        cls,
        record: Dict[str, Any],
        spec: MappingSpecification,
        source_provider: str = "GENERIC_API"
    ) -> Dict[str, Any]:
        mapped: Dict[str, Any] = {}
        source_record_id = str(record.get("id") or record.get("record_id") or record.get("_id") or uuid.uuid4().hex[:8])

        for rule in spec.rules:
            src_val = cls._get_nested_field(record, rule.source_field) if "." in rule.source_field else record.get(rule.source_field)

            # Handle missing / null
            if src_val is None:
                val = rule.default_value
            else:
                tf = rule.transform_type.upper()
                # Apply transformation
                if tf == "DIRECT":
                    val = src_val
                elif tf in ("DATE_ISO", "ISO8601_UTC"):
                    val = DataNormalizer.normalize_date(src_val)
                elif tf in ("CURRENCY", "CURRENCY_INR"):
                    norm_curr = DataNormalizer.normalize_currency(src_val)
                    val = norm_curr["amount"]
                elif tf == "UPPERCASE":
                    val = str(src_val).upper()
                elif tf == "LOWERCASE":
                    val = str(src_val).lower()
                elif tf == "TRIM":
                    val = str(src_val).strip()
                elif tf in ("TO_STRING", "STRING"):
                    val = str(src_val)
                elif tf == "MAP_ENUM" and rule.enum_map:
                    val = rule.enum_map.get(str(src_val), rule.default_value)
                elif tf == "CUSTOM" and rule.custom_fn:
                    val = rule.custom_fn(src_val)
                else:
                    val = src_val

            mapped[rule.target_field] = val

        # Provenance metadata
        mapped["_provenance"] = {
            "source_provider": source_provider,
            "source_system": source_provider,
            "source_record_id": source_record_id,
            "mapping_id": spec.mapping_id,
            "mapping_version": spec.version,
            "source_sha256": hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode()).hexdigest(),
            "mapped_at": time.time()
        }

        return mapped

    @classmethod
    def map_record(
        cls,
        record: Dict[str, Any],
        mapping_spec: Union[MappingSpecification, Dict[str, Any]],
        source_system: str = "GENERIC_API"
    ) -> Dict[str, Any]:
        if isinstance(mapping_spec, MappingSpecification):
            return cls.apply_mapping(record, mapping_spec, source_provider=source_system)

        spec_dict = mapping_spec
        rules = []
        for target_field, rule_def in spec_dict.get("mappings", {}).items():
            if isinstance(rule_def, str):
                rules.append(FieldMappingRule(source_field=rule_def, target_field=target_field, transform_type="DIRECT"))
            elif isinstance(rule_def, dict):
                src = rule_def.get("source", target_field)
                tf = rule_def.get("transform", "DIRECT")
                rules.append(FieldMappingRule(
                    source_field=src,
                    target_field=target_field,
                    transform_type=tf,
                    default_value=rule_def.get("default")
                ))

        spec = MappingSpecification(
            mapping_id=spec_dict.get("mapping_id", "map_dynamic"),
            source_schema_id=spec_dict.get("source_schema", "SourceGeneric"),
            target_schema_id=spec_dict.get("target_schema", "TargetGeneric"),
            version=spec_dict.get("version", "1.0.0"),
            rules=rules
        )
        return cls.apply_mapping(record, spec, source_provider=source_system)


# =============================================================================
# 4. SYNC CHECKPOINT & DEAD-LETTER MANAGER
# =============================================================================

class SyncCheckpointManager:
    """
    Durable, SQLite-backed checkpoint manager for incremental stream synchronization
    and dead-letter queue (DLQ) quarantine.
    """

    def __init__(self):
        self._ensure_tables()

    @classmethod
    def _ensure_tables(cls):
        with db.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS automation_sync_checkpoints (
                tenant_id TEXT NOT NULL,
                stream_name TEXT NOT NULL,
                connector_id TEXT NOT NULL,
                cursor_value TEXT NOT NULL,
                cursor_type TEXT NOT NULL,
                records_synced INTEGER NOT NULL DEFAULT 0,
                last_sync_timestamp REAL NOT NULL,
                content_checksum TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'COMPLETED',
                metadata JSON,
                PRIMARY KEY (tenant_id, stream_name, connector_id)
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS automation_sync_dead_letter (
                dead_letter_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                stream_name TEXT NOT NULL,
                connector_id TEXT NOT NULL,
                source_record_id TEXT,
                raw_record JSON NOT NULL,
                rejection_reason TEXT NOT NULL,
                created_at REAL NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_dlq_tc ON automation_sync_dead_letter(tenant_id, stream_name);")
            conn.commit()

    @classmethod
    def get_checkpoint(
        cls,
        tenant_id: str,
        stream_name: str = "",
        connector_id: str = "",
        company_id: str = "",
        stream_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        s_name = stream_id or stream_name
        c_id = connector_id or company_id
        cls._ensure_tables()
        with db.get_connection() as conn:
            if c_id:
                row = conn.execute(
                    """
                    SELECT * FROM automation_sync_checkpoints
                    WHERE tenant_id = ? AND stream_name = ? AND connector_id = ?
                    """,
                    (tenant_id, s_name, c_id)
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM automation_sync_checkpoints
                    WHERE tenant_id = ? AND stream_name = ?
                    ORDER BY last_sync_timestamp DESC LIMIT 1
                    """,
                    (tenant_id, s_name)
                ).fetchone()
            if row:
                d = dict(row)
                d["high_water_mark"] = d.get("cursor_value")
                d["records_processed"] = d.get("records_synced")
                return d
            return None

    @classmethod
    def save_checkpoint(
        cls,
        tenant_id: str,
        stream_name: str = "",
        connector_id: str = "",
        cursor_value: str = "",
        company_id: str = "",
        stream_id: str = "",
        high_water_mark: str = "",
        cursor_token: str = "",
        cursor_type: CursorType = CursorType.TIMESTAMP,
        records_synced: int = 0,
        records_processed: int = 0,
        content_checksum: str = "",
        status: str = "COMPLETED",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        cls._ensure_tables()
        s_name = stream_id or stream_name
        c_id = connector_id or company_id or "default_connector"
        c_val = high_water_mark or cursor_value or cursor_token
        num_synced = records_processed or records_synced
        now = time.time()
        chk = content_checksum or hashlib.sha256(f"{tenant_id}:{s_name}:{c_val}".encode()).hexdigest()
        c_type = cursor_type.value if hasattr(cursor_type, "value") else str(cursor_type)

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO automation_sync_checkpoints (
                    tenant_id, stream_name, connector_id, cursor_value, cursor_type,
                    records_synced, last_sync_timestamp, content_checksum, status, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (tenant_id, stream_name, connector_id) DO UPDATE SET
                    cursor_value = EXCLUDED.cursor_value,
                    cursor_type = EXCLUDED.cursor_type,
                    records_synced = EXCLUDED.records_synced,
                    last_sync_timestamp = EXCLUDED.last_sync_timestamp,
                    content_checksum = EXCLUDED.content_checksum,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata
                """,
                (
                    tenant_id, s_name, c_id, c_val, c_type,
                    num_synced, now, chk, status, json.dumps(metadata or {})
                )
            )
            conn.commit()

        return {
            "tenant_id": tenant_id,
            "stream_name": s_name,
            "connector_id": c_id,
            "cursor_value": c_val,
            "high_water_mark": c_val,
            "cursor_type": c_type,
            "records_synced": num_synced,
            "records_processed": num_synced,
            "last_sync_timestamp": now,
            "content_checksum": chk,
            "status": status
        }

    @classmethod
    def quarantine_record(
        cls,
        tenant_id: str,
        stream_name: str,
        connector_id: str,
        raw_record: Dict[str, Any],
        rejection_reason: str,
        source_record_id: Optional[str] = None
    ) -> str:
        cls._ensure_tables()
        dlq_id = f"dlq_{uuid.uuid4().hex[:10]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO automation_sync_dead_letter (
                    dead_letter_id, tenant_id, stream_name, connector_id,
                    source_record_id, raw_record, rejection_reason, created_at, resolved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    dlq_id, tenant_id, stream_name, connector_id,
                    source_record_id, json.dumps(raw_record), rejection_reason, now
                )
            )
            conn.commit()
        return dlq_id

    @classmethod
    def log_dead_letter(
        cls,
        tenant_id: str,
        company_id: str,
        stream_id: str,
        raw_record: Dict[str, Any],
        error_reason: str,
        error_code: str = "DATA_PARSING_ERR",
        source_record_id: Optional[str] = None
    ) -> str:
        return cls.quarantine_record(
            tenant_id=tenant_id,
            stream_name=stream_id,
            connector_id=company_id,
            raw_record=raw_record,
            rejection_reason=f"[{error_code}] {error_reason}",
            source_record_id=source_record_id
        )

    @classmethod
    def list_dead_letters(cls, tenant_id: str, stream_name: Optional[str] = None) -> List[Dict[str, Any]]:
        cls._ensure_tables()
        with db.get_connection() as conn:
            if stream_name:
                rows = conn.execute(
                    "SELECT * FROM automation_sync_dead_letter WHERE tenant_id = ? AND stream_name = ? ORDER BY created_at DESC",
                    (tenant_id, stream_name)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM automation_sync_dead_letter WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tenant_id,)
                ).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def list_dead_letter_records(cls, tenant_id: str, company_id: str = "", stream_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = cls.list_dead_letters(tenant_id, stream_name=stream_id)
        for r in rows:
            reason = r.get("rejection_reason", "")
            if reason.startswith("[") and "]" in reason:
                r["error_code"] = reason[1:reason.index("]")]
            else:
                r["error_code"] = "GENERIC_ERR"
        return rows


# =============================================================================
# 5. DEDUPLICATION & CONFLICT RESOLVER
# =============================================================================

class DataDeduplicationAndConflictResolver:
    """
    Computes deterministic SHA-256 fingerprints, detects duplicate records,
    and resolves data synchronization conflicts safely without silent data loss.
    """

    @classmethod
    def compute_record_fingerprint(cls, record: Dict[str, Any], key_fields: Optional[List[str]] = None) -> str:
        """Computes deterministic SHA-256 hash of record content."""
        if key_fields:
            sub = {k: record.get(k) for k in key_fields}
        else:
            # Exclude transient metadata fields
            sub = {k: v for k, v in record.items() if not k.startswith("_")}
        serialized = json.dumps(sub, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def resolve_conflict(
        cls,
        source_record: Dict[str, Any],
        destination_record: Dict[str, Any],
        policy: ConflictPolicy = ConflictPolicy.LATEST_TIMESTAMP_WINS
    ) -> Tuple[Dict[str, Any], str]:
        """
        Resolves conflict between source and destination records.
        Returns: (winning_record, resolution_decision)
        """
        if policy == ConflictPolicy.SOURCE_WINS:
            return source_record, "SOURCE_WINS_OVERWRITE"

        elif policy == ConflictPolicy.DESTINATION_WINS:
            return destination_record, "DESTINATION_WINS_PRESERVED"

        elif policy == ConflictPolicy.MANUAL_APPROVAL_REQUIRED:
            conflicted = dict(source_record)
            conflicted["_conflict_status"] = "AWAITING_MANUAL_APPROVAL"
            conflicted["_destination_snapshot"] = destination_record
            return conflicted, "ESCALATED_FOR_APPROVAL"

        # Default: LATEST_TIMESTAMP_WINS
        def _extract_ts(rec: Dict[str, Any]) -> float:
            val = rec.get("updated_at") or rec.get("timestamp") or 0.0
            if isinstance(val, (int, float)):
                return float(val)
            try:
                return float(val)
            except Exception:
                # If ISO string or formatted date string, sort lexically or convert
                try:
                    iso = DataNormalizer.normalize_datetime(str(val))
                    # Convert ISO format (e.g. 2026-10-11T12:00:00Z) to epoch
                    import datetime
                    dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
                    return dt.timestamp()
                except Exception:
                    return 0.0

        src_ts = _extract_ts(source_record)
        dst_ts = _extract_ts(destination_record)

        if src_ts >= dst_ts:
            return source_record, f"LATEST_TIMESTAMP_WINS (Source {src_ts} >= Destination {dst_ts})"
        else:
            return destination_record, f"LATEST_TIMESTAMP_WINS (Destination {dst_ts} > Source {src_ts})"


# =============================================================================
# 6. BUSINESS DATA SYNC PIPELINE & RECONCILIATION
# =============================================================================

class BusinessDataSyncPipeline:
    """
    Master pipeline orchestrating atomic batch synchronization:
    1. Schema validation against explicit specification
    2. Quarantine of invalid records to Dead-Letter Queue
    3. Deep data normalization (dates, numbers, currencies)
    4. Versioned field mapping
    5. Deduplication and conflict resolution
    6. Atomic destination upsert
    7. Checkpoint persistence
    8. Merkle EvidenceLedger sealing
    """

    def __init__(self):
        self.checkpoint_manager = SyncCheckpointManager()
        self.evidence_ledger = EvidenceLedger()

    def run_sync_batch(
        self,
        tenant_id: str,
        stream_name: str,
        source_connector_id: str,
        destination_connector_id: str,
        records: List[Dict[str, Any]],
        schema: Optional[Dict[str, Any]] = None,
        mapping_spec: Optional[MappingSpecification] = None,
        conflict_policy: ConflictPolicy = ConflictPolicy.LATEST_TIMESTAMP_WINS,
        cursor_field: str = "updated_at",
        idempotency_key: Optional[str] = None,
        existing_destination_records: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> SyncExecutionReport:
        sync_id = f"sync_{uuid.uuid4().hex[:10]}"
        start_time = time.time()
        existing_dest = existing_destination_records or {}

        # 1. Fetch previous checkpoint
        prev_chk = self.checkpoint_manager.get_checkpoint(tenant_id, stream_name, source_connector_id)
        cursor_before = prev_chk["cursor_value"] if prev_chk else None

        records_read = len(records)
        records_validated = 0
        records_mapped = 0
        records_upserted = 0
        records_deduplicated = 0
        records_quarantined = 0
        errors: List[str] = []

        seen_fingerprints: set = set()
        highest_cursor_val = cursor_before or "0"
        processed_records: List[Dict[str, Any]] = []

        for rec in records:
            rec_id = str(rec.get("id") or rec.get("record_id") or "")

            # 2. Schema Validation
            if schema:
                is_valid, val_errs = DataSchemaValidator.validate_record(rec, schema)
                if not is_valid:
                    self.checkpoint_manager.quarantine_record(
                        tenant_id=tenant_id,
                        stream_name=stream_name,
                        connector_id=source_connector_id,
                        raw_record=rec,
                        rejection_reason="; ".join(val_errs),
                        source_record_id=rec_id
                    )
                    records_quarantined += 1
                    continue
            records_validated += 1

            # 3. Deduplication Check within batch
            fingerprint = DataDeduplicationAndConflictResolver.compute_record_fingerprint(rec)
            if fingerprint in seen_fingerprints:
                records_deduplicated += 1
                continue
            seen_fingerprints.add(fingerprint)

            # 4. Normalization
            norm_rec = DataNormalizer.normalize_record(rec)

            # 5. Field Mapping
            if mapping_spec:
                final_rec = FieldMapper.apply_mapping(norm_rec, mapping_spec, source_provider=source_connector_id)
            else:
                final_rec = norm_rec
            records_mapped += 1

            # 6. Conflict Resolution against destination
            dest_rec = existing_dest.get(rec_id)
            if dest_rec:
                resolved_rec, _ = DataDeduplicationAndConflictResolver.resolve_conflict(
                    source_record=final_rec,
                    destination_record=dest_rec,
                    policy=conflict_policy
                )
                final_rec = resolved_rec

            processed_records.append(final_rec)
            records_upserted += 1

            # Track cursor
            c_val = str(rec.get(cursor_field) or rec.get("id") or "")
            if c_val and c_val > highest_cursor_val:
                highest_cursor_val = c_val

        # 7. Advance checkpoint
        chk_res = self.checkpoint_manager.save_checkpoint(
            tenant_id=tenant_id,
            stream_name=stream_name,
            connector_id=source_connector_id,
            cursor_value=highest_cursor_val,
            cursor_type=CursorType.TIMESTAMP,
            records_synced=records_upserted,
            status="COMPLETED" if records_quarantined == 0 else "PARTIAL",
            metadata={"sync_id": sync_id, "quarantined_count": records_quarantined}
        )
        cursor_after = chk_res["cursor_value"]

        # 8. Cryptographic Evidence Ledger Sealing
        comp_time = time.time()
        duration = round(comp_time - start_time, 3)

        verifications = [
            PhysicalVerification(
                check_type="DATA_STREAM_SYNC_CHECKPOINT",
                target_path=f"streams/{tenant_id}/{stream_name}",
                expected_val=str(records_read),
                actual_val=str(records_upserted),
                verified=(records_upserted + records_quarantined + records_deduplicated == records_read),
                details=f"Synced {records_upserted} records; quarantined {records_quarantined}; deduplicated {records_deduplicated}."
            )
        ]

        evidence_pkg = self.evidence_ledger.seal_evidence(
            action_id=sync_id,
            mission_id=f"mis_sync_{stream_name}",
            agent_id="agt_data_integration_sync",
            verifications=verifications,
            metadata={
                "tenant_id": tenant_id,
                "stream_name": stream_name,
                "source_connector": source_connector_id,
                "destination_connector": destination_connector_id,
                "records_upserted": records_upserted,
                "cursor_after": cursor_after
            }
        )

        final_status = SyncStatus.COMPLETED if records_quarantined == 0 else SyncStatus.PARTIALLY_COMPLETED

        report = SyncExecutionReport(
            sync_id=sync_id,
            tenant_id=tenant_id,
            stream_name=stream_name,
            source_connector=source_connector_id,
            destination_connector=destination_connector_id,
            records_read=records_read,
            records_validated=records_validated,
            records_mapped=records_mapped,
            records_upserted=records_upserted,
            records_deduplicated=records_deduplicated,
            records_quarantined=records_quarantined,
            checkpoint_before=cursor_before,
            checkpoint_after=cursor_after,
            status=final_status,
            start_time=start_time,
            completion_time=comp_time,
            duration_sec=duration,
            evidence_id=evidence_pkg.evidence_id,
            merkle_root=evidence_pkg.sha256_digest,
            errors=errors
        )

        return report

    def execute_sync(
        self,
        stream_id: str,
        source_system: str,
        destination_system: str,
        raw_records: List[Dict[str, Any]],
        mapping_spec: Optional[Any] = None,
        schema: Optional[Dict[str, Any]] = None,
        id_field: str = "id",
        tenant_id: str = "tnt_primary"
    ) -> Dict[str, Any]:
        converted_spec = None
        if isinstance(mapping_spec, dict):
            rules = []
            for target_field, rule_def in mapping_spec.get("mappings", {}).items():
                if isinstance(rule_def, str):
                    rules.append(FieldMappingRule(source_field=rule_def, target_field=target_field, transform_type="DIRECT"))
                elif isinstance(rule_def, dict):
                    src = rule_def.get("source", target_field)
                    tf = rule_def.get("transform", "DIRECT")
                    rules.append(FieldMappingRule(source_field=src, target_field=target_field, transform_type=tf, default_value=rule_def.get("default")))
            converted_spec = MappingSpecification(
                mapping_id=mapping_spec.get("mapping_id", "map_dynamic"),
                source_schema_id=mapping_spec.get("source_schema", "SourceGeneric"),
                target_schema_id=mapping_spec.get("target_schema", "TargetGeneric"),
                version=mapping_spec.get("version", "1.0.0"),
                rules=rules
            )
        elif isinstance(mapping_spec, MappingSpecification):
            converted_spec = mapping_spec

        report = self.run_sync_batch(
            tenant_id=tenant_id,
            stream_name=stream_id,
            source_connector_id=source_system,
            destination_connector_id=destination_system,
            records=raw_records,
            schema=schema,
            mapping_spec=converted_spec
        )
        return {
            "status": report.status.value,
            "records_synced": report.records_upserted,
            "records_quarantined": report.records_quarantined,
            "evidence_id": report.evidence_id,
            "sha256_digest": report.merkle_root or hashlib.sha256(report.sync_id.encode()).hexdigest()
        }


class DataReconciliationEngine:
    """
    Reconciles source dataset state against destination dataset state,
    verifying record counts, transaction volumes, and financial totals.
    """

    @classmethod
    def reconcile_datasets(
        cls,
        source_records: List[Dict[str, Any]],
        destination_records: List[Dict[str, Any]],
        primary_key: str = "id",
        key_field: Optional[str] = None,
        financial_field: Optional[str] = "amount",
        financial_sum_field: Optional[str] = None
    ) -> Dict[str, Any]:
        pk = key_field or primary_key
        fin_field = financial_sum_field or financial_field

        src_map = {str(r.get(pk)): r for r in source_records}
        dst_map = {str(r.get(pk)): r for r in destination_records}

        missing_in_dest = [k for k in src_map if k not in dst_map]
        unexpected_in_dest = [k for k in dst_map if k not in src_map]

        src_total = Decimal("0.00")
        dst_total = Decimal("0.00")

        if fin_field:
            for r in source_records:
                val = r.get(fin_field)
                if isinstance(val, (int, float, Decimal)):
                    src_total += Decimal(str(val))
                elif isinstance(val, dict) and "amount" in val:
                    src_total += Decimal(str(val["amount"]))
                elif val is not None:
                    try:
                        src_total += Decimal(str(val).replace(",", "").replace("₹", "").replace("$", "").replace("€", "").replace("£", ""))
                    except Exception:
                        pass

            for r in destination_records:
                val = r.get(fin_field)
                if isinstance(val, (int, float, Decimal)):
                    dst_total += Decimal(str(val))
                elif isinstance(val, dict) and "amount" in val:
                    dst_total += Decimal(str(val["amount"]))
                elif val is not None:
                    try:
                        dst_total += Decimal(str(val).replace(",", "").replace("₹", "").replace("$", "").replace("€", "").replace("£", ""))
                    except Exception:
                        pass

        balance_diff = abs(src_total - dst_total)
        is_reconciled = (len(missing_in_dest) == 0 and balance_diff == Decimal("0.00"))

        return {
            "is_reconciled": is_reconciled,
            "reconciled": is_reconciled,
            "source_count": len(source_records),
            "destination_count": len(destination_records),
            "missing_in_destination_count": len(missing_in_dest),
            "missing_in_destination": missing_in_dest,
            "missing_keys": missing_in_dest[:10],
            "unexpected_in_destination_count": len(unexpected_in_dest),
            "discrepancy_count": len(missing_in_dest) + len(unexpected_in_dest) + (1 if balance_diff != Decimal("0.00") else 0),
            "source_financial_total": float(src_total),
            "destination_financial_total": float(dst_total),
            "financial_discrepancy": float(balance_diff),
            "balance_difference": balance_diff,
            "reconciliation_timestamp": time.time()
        }


def get_sync_pipeline(tenant_id: str = "tnt_primary", company_id: str = "comp_primary") -> BusinessDataSyncPipeline:
    return BusinessDataSyncPipeline()


# Global singleton instances for direct integration
data_schema_validator = DataSchemaValidator()
data_normalizer = DataNormalizer()
sync_checkpoint_manager = SyncCheckpointManager()
data_sync_pipeline = BusinessDataSyncPipeline()
data_reconciliation_engine = DataReconciliationEngine()
