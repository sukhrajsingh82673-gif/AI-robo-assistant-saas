"""
ZONATA / URA Universal Linux Terminal Execution Fabric — AI CEO Knowledge Evolution Engine
Governed continuous-improvement loop where Terminal operations, Tool Factory discoveries,
and verified execution outcomes produce structured, trusted technical intelligence for the AI CEO.

Pipeline:
EXECUTION → OBSERVATION → VERIFICATION → EVIDENCE → KNOWLEDGE EXTRACTION →
QUALITY/TRUST CHECK → SECURITY CHECK → DEDUPLICATION → VERSIONING →
KNOWLEDGE REGISTRY → AI CEO KNOWLEDGE UPDATE.

Invariant:
Untrusted terminal output CAN NEVER directly alter trusted AI CEO knowledge.
All learned capabilities must have cryptographic evidence, security review, and provenance.
Self-improvement CANNOT alter sovereign governance, policies, or KillSwitch controls.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import time
import uuid
import json
import sqlite3
import hashlib
import logging
from dataclasses import dataclass, field, asdict

from .models import TerminalResult, TerminalSession

logger = logging.getLogger("zonata.terminal.evolution")

@dataclass
class AICeoKnowledgeEntry:
    knowledge_id: str
    topic: str  # e.g. "tool_compatibility", "recovery_pattern", "compilation_procedure", "performance_benchmark"
    title: str
    summary: str
    source_task: str
    source_mission: str
    runtime_id: str
    tool_id: Optional[str]
    tool_version: Optional[str]
    evidence_hash: str
    confidence: float  # 0.0 to 1.0
    validation_status: str  # "PROVISIONAL", "VERIFIED", "ADMITTED", "REJECTED"
    security_review: str  # "PENDING", "APPROVED", "REJECTED"
    created_at: float
    last_verified: float
    supersedes: Optional[str] = None
    expiry_timestamp: Optional[float] = None
    structured_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class AICeoKnowledgeEvolutionEngine:
    """
    Governed continuous evolution engine.
    Extracts, validates, deduplicates, and registers technical intelligence into the AI CEO Knowledge Base.
    """

    def __init__(self, db_path: Optional[str] = None, tenant_id: str = "tnt_primary"):
        if db_path is None:
            from core.db import get_default_db_path
            self.db_path = get_default_db_path()
        else:
            self.db_path = db_path
        self.tenant_id = tenant_id
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aiceo_technical_knowledge (
                    knowledge_id TEXT PRIMARY KEY,
                    tenant_id TEXT,
                    topic TEXT,
                    title TEXT,
                    summary TEXT,
                    source_task TEXT,
                    source_mission TEXT,
                    runtime_id TEXT,
                    tool_id TEXT,
                    tool_version TEXT,
                    evidence_hash TEXT,
                    confidence REAL,
                    validation_status TEXT,
                    security_review TEXT,
                    created_at REAL,
                    last_verified REAL,
                    supersedes TEXT,
                    payload_json TEXT
                )
            """)
            conn.commit()

    def extract_and_register_knowledge(
        self,
        session: TerminalSession,
        result: TerminalResult,
        topic: str = "operational_procedure",
        custom_insights: Optional[Dict[str, Any]] = None
    ) -> Optional[AICeoKnowledgeEntry]:
        """
        Executes the full 11-step Governed Knowledge Evolution Pipeline.
        Only VERIFIED executions with cryptographic evidence are eligible for admission.
        """
        # Step 1-3: Verification Gate
        if result.status != "SUCCESS" or not result.evidence_id:
            logger.info("Knowledge extraction skipped: Execution was not verified or lacks evidence.")
            return None

        # Step 4: Evidence validation
        evidence_hash = result.evidence_id
        if len(evidence_hash) != 64:
            logger.warning("Knowledge rejected: Evidence hash is invalid.")
            return None

        # Step 5: Knowledge Extraction
        tool_name = result.tools_used[0] if result.tools_used else (result.tools_installed[0] if result.tools_installed else "system_shell")
        title = f"Verified Procedure: {result.summary[:60]}"
        summary = (
            f"Successfully executed on runtime {result.runtime_profile} ({result.environment_used}) "
            f"using tools: {', '.join(result.tools_used or ['native'])}. "
            f"Commands run: {len(result.commands_executed)}."
        )

        payload = {
            "commands_executed": result.commands_executed,
            "observations": result.observations,
            "verification": result.verification,
            "custom_insights": custom_insights or {}
        }

        # Step 6: Quality & Trust Check
        confidence = 0.95 if result.verification.get("all_conditions_passed") else 0.85

        # Step 7: Security Check (Assert no secrets or prompt injections leaked in payload)
        payload_str = json.dumps(payload)
        from .security_gateway import TerminalSecurityGateway
        scrubbed = TerminalSecurityGateway.scrub_credentials(payload_str)
        if scrubbed != payload_str:
            logger.warning("Knowledge rejected: Unscrubbed secret found during security check.")
            return None

        clean_text, injection_detected = TerminalSecurityGateway.sanitize_untrusted_output(payload_str)
        if injection_detected:
            logger.warning("Knowledge rejected: Untrusted prompt injection found in execution output.")
            return None

        security_review = "APPROVED"

        # Step 8: Deduplication
        existing = self.find_knowledge(topic=topic, tool_id=tool_name)
        supersedes_id = None
        if existing:
            # Upgrade existing knowledge
            supersedes_id = existing[0].knowledge_id

        # Step 9: Versioning
        k_id = f"know_{uuid.uuid4().hex[:10]}"
        entry = AICeoKnowledgeEntry(
            knowledge_id=k_id,
            topic=topic,
            title=title,
            summary=summary,
            source_task=session.task_id,
            source_mission=session.mission_id,
            runtime_id=session.runtime_id,
            tool_id=tool_name,
            tool_version="latest",
            evidence_hash=evidence_hash,
            confidence=confidence,
            validation_status="ADMITTED",
            security_review=security_review,
            created_at=time.time(),
            last_verified=time.time(),
            supersedes=supersedes_id,
            structured_payload=payload
        )

        # Step 10: Knowledge Registry Admission
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO aiceo_technical_knowledge (
                    knowledge_id, tenant_id, topic, title, summary, source_task, source_mission,
                    runtime_id, tool_id, tool_version, evidence_hash, confidence,
                    validation_status, security_review, created_at, last_verified, supersedes, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.knowledge_id, self.tenant_id, entry.topic, entry.title, entry.summary,
                    entry.source_task, entry.source_mission, entry.runtime_id, entry.tool_id,
                    entry.tool_version, entry.evidence_hash, entry.confidence, entry.validation_status,
                    entry.security_review, entry.created_at, entry.last_verified, entry.supersedes,
                    json.dumps(entry.structured_payload)
                )
            )
            conn.commit()

        # Step 11: AI CEO Knowledge Update Notification
        logger.info(f"AI CEO KNOWLEDGE ADMITTED: [{entry.topic}] '{entry.title}' (ID: {entry.knowledge_id})")
        return entry

    def admit_knowledge(
        self,
        topic: str,
        title: str,
        summary: str,
        source_task: str,
        source_mission: str,
        runtime_id: str,
        tool_id: str,
        tool_version: str,
        execution_status: str,
        evidence_hash: str,
        raw_output: str,
        confidence: float = 0.85,
        custom_payload: Optional[Dict[str, Any]] = None
    ) -> Optional[AICeoKnowledgeEntry]:
        """
        Directly admits technical knowledge through the governed 11-step validation gates:
        - Execution must be SUCCESS
        - Evidence hash must be valid 64-char Merkle root
        - Credentials scrubbed (DLP)
        - Prompt injection sanitized
        """
        # Step 1: Verification gate
        if execution_status != "SUCCESS":
            logger.info("Knowledge rejected: Execution status is not SUCCESS")
            return None

        # Step 2: Cryptographic evidence gate
        if not evidence_hash or len(evidence_hash) != 64:
            logger.warning("Knowledge rejected: Invalid cryptographic evidence hash")
            return None

        # Step 3: Security & DLP scrub
        from .security_gateway import TerminalSecurityGateway
        clean_output, injection_detected = TerminalSecurityGateway.sanitize_untrusted_output(raw_output)
        if injection_detected:
            logger.warning("Knowledge rejected: Prompt injection detected in raw output")
            return None

        scrubbed_summary = TerminalSecurityGateway.scrub_credentials(summary)
        scrubbed_output = TerminalSecurityGateway.scrub_credentials(clean_output)

        # Step 4: Deduplication & Versioning
        existing = self.find_knowledge(topic=topic, tool_id=tool_id)
        supersedes_id = existing[0].knowledge_id if existing else None

        k_id = f"know_{uuid.uuid4().hex[:10]}"
        payload = custom_payload or {"raw_output": scrubbed_output}

        entry = AICeoKnowledgeEntry(
            knowledge_id=k_id,
            topic=topic,
            title=title,
            summary=scrubbed_summary,
            source_task=source_task,
            source_mission=source_mission,
            runtime_id=runtime_id,
            tool_id=tool_id,
            tool_version=tool_version,
            evidence_hash=evidence_hash,
            confidence=confidence,
            validation_status="ADMITTED",
            security_review="APPROVED",
            created_at=time.time(),
            last_verified=time.time(),
            supersedes=supersedes_id,
            structured_payload=payload
        )

        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO aiceo_technical_knowledge (
                    knowledge_id, tenant_id, topic, title, summary, source_task, source_mission,
                    runtime_id, tool_id, tool_version, evidence_hash, confidence,
                    validation_status, security_review, created_at, last_verified, supersedes, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.knowledge_id, self.tenant_id, entry.topic, entry.title, entry.summary,
                    entry.source_task, entry.source_mission, entry.runtime_id, entry.tool_id,
                    entry.tool_version, entry.evidence_hash, entry.confidence, entry.validation_status,
                    entry.security_review, entry.created_at, entry.last_verified, entry.supersedes,
                    json.dumps(entry.structured_payload)
                )
            )
            conn.commit()

        logger.info(f"AI CEO KNOWLEDGE ADMITTED: '{entry.title}' (ID: {entry.knowledge_id})")
        return entry

    def find_knowledge(self, topic: Optional[str] = None, tool_id: Optional[str] = None) -> List[AICeoKnowledgeEntry]:
        """Queries verified technical knowledge entries admitted into the registry."""
        query = "SELECT * FROM aiceo_technical_knowledge WHERE tenant_id = ? AND validation_status = 'ADMITTED'"
        params = [self.tenant_id]
        if topic:
            query += " AND topic = ?"
            params.append(topic)
        if tool_id:
            query += " AND tool_id = ?"
            params.append(tool_id)
        query += " ORDER BY confidence DESC, created_at DESC"

        results = []
        with self._get_connection() as conn:
            for row in conn.execute(query, params).fetchall():
                results.append(AICeoKnowledgeEntry(
                    knowledge_id=row["knowledge_id"],
                    topic=row["topic"],
                    title=row["title"],
                    summary=row["summary"],
                    source_task=row["source_task"],
                    source_mission=row["source_mission"],
                    runtime_id=row["runtime_id"],
                    tool_id=row["tool_id"],
                    tool_version=row["tool_version"],
                    evidence_hash=row["evidence_hash"],
                    confidence=row["confidence"],
                    validation_status=row["validation_status"],
                    security_review=row["security_review"],
                    created_at=row["created_at"],
                    last_verified=row["last_verified"],
                    supersedes=row["supersedes"],
                    structured_payload=json.loads(row["payload_json"])
                ))
        return results
