"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 20 — Enterprise Security Center & Threat Monitoring Plane
Monitors authentication failures, privilege escalation, cross-tenant violations,
prompt injection, tool abuse, DLP exfiltration, and abnormal financial mutations.

Constitutional Invariant:
  EVIDENCE_BASED_THREAT_DETECTION
  SECURITY_VIOLATIONS_SEALED_IN_AUDIT_LEDGER
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.database_engine import engine, WorkloadType
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.security.center")

class SecurityThreatSeverity:
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ThreatCategory:
    AUTH_FAILURE = "AUTH_FAILURE"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    CROSS_TENANT_VIOLATION = "CROSS_TENANT_VIOLATION"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    TOOL_ABUSE = "TOOL_ABUSE"
    DLP_EXFILTRATION_ATTEMPT = "DLP_EXFILTRATION_ATTEMPT"
    FINANCIAL_ANOMALY = "FINANCIAL_ANOMALY"
    MERKLE_TAMPER_DETECTED = "MERKLE_TAMPER_DETECTED"

@dataclass
class SecurityIncident:
    incident_id: str
    tenant_id: str
    company_id: str
    category: str
    severity: str
    source_entity_id: str
    description: str
    details: Dict[str, Any]
    is_mitigated: bool
    timestamp: float

class SecurityCenter:
    """
    Central Threat Monitoring and Security Intelligence Plane.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS security_incidents (
                incident_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                description TEXT NOT NULL,
                details JSON NOT NULL,
                is_mitigated INTEGER NOT NULL DEFAULT 0,
                timestamp REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sec_tenant ON security_incidents(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sec_sev ON security_incidents(severity);")

    def record_incident(
        self,
        tenant_id: str,
        company_id: str,
        category: str,
        severity: str,
        source_entity_id: str,
        description: str,
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityIncident:
        """Log a security incident and seal cryptographic evidence."""
        incident_id = f"sec_inc_{uuid.uuid4().hex[:12]}"
        now = time.time()
        det = details or {}

        inc = SecurityIncident(
            incident_id=incident_id,
            tenant_id=tenant_id,
            company_id=company_id,
            category=category,
            severity=severity,
            source_entity_id=source_entity_id,
            description=description,
            details=det,
            is_mitigated=False,
            timestamp=now
        )

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO security_incidents (
                incident_id, tenant_id, company_id, category, severity,
                source_entity_id, description, details, is_mitigated, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                inc.incident_id, inc.tenant_id, inc.company_id, inc.category,
                inc.severity, inc.source_entity_id, inc.description,
                json.dumps(inc.details), now
            ))

        # Seal cryptographic event
        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="SECURITY_INCIDENT_RAISED",
            payload={
                "incident_id": incident_id,
                "category": category,
                "severity": severity,
                "source_entity_id": source_entity_id,
                "description": description
            }
        )

        logger.warning(f"[SECURITY ALERT - {severity}] {category} by {source_entity_id}: {description}")
        return inc

    def get_active_incidents(self, tenant_id: str, min_severity: str = SecurityThreatSeverity.LOW) -> List[SecurityIncident]:
        """Fetch unmitigated security incidents."""
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("""
            SELECT * FROM security_incidents
            WHERE tenant_id = ? AND is_mitigated = 0
            ORDER BY timestamp DESC
            """, (tenant_id,))
            rows = cursor.fetchall()
            return [
                SecurityIncident(
                    incident_id=r["incident_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    category=r["category"],
                    severity=r["severity"],
                    source_entity_id=r["source_entity_id"],
                    description=r["description"],
                    details=json.loads(r["details"]),
                    is_mitigated=bool(r["is_mitigated"]),
                    timestamp=r["timestamp"]
                )
                for r in rows
            ]

# Global singleton
security_center = SecurityCenter()
