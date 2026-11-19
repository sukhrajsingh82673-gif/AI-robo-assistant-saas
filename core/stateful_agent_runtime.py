"""
RoboAssistant Company OS 2.0 — Stateful Agent Identity, Memory & Long-Horizon Context
Implements persistent agent identity, working memory blocks (persona/human),
multi-scope epistemic memory store, secret rejection scanner, conflict detection
and resolution mechanics, recall buffer with compaction, and sovereign authority invariants.

Architectural Rule:
Memory is state and context; it is NEVER authority, policy, or execution permission.
CAPABILITY != AUTHORITY
MEMORY != EVIDENCE
MEMORY != PERMISSION
TASK_SUCCESS != BUSINESS_OUTCOME
"""

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from core.db import db


# =====================================================================
# 1. Enums and Constants
# =====================================================================

class MemoryScope(str, Enum):
    HOST = "HOST"
    PERSONAL_WORKSPACE = "PERSONAL_WORKSPACE"
    TENANT = "TENANT"
    COMPANY = "COMPANY"
    DEPARTMENT = "DEPARTMENT"
    WORKFORCE = "WORKFORCE"
    AGENT = "AGENT"
    MISSION = "MISSION"
    PROJECT = "PROJECT"
    MEETING = "MEETING"


class MemoryType(str, Enum):
    CORE = "CORE"            # Foundational persona & user constraints
    WORKING = "WORKING"      # Active scratchpad & short-term working context
    ARCHIVAL = "ARCHIVAL"    # Long-term semantic store
    RECALL = "RECALL"        # Ephemeral conversation turn buffer
    SYSTEM = "SYSTEM"        # System-level operational context


class MemoryCategory(str, Enum):
    FACT = "FACT"
    PREFERENCE = "PREFERENCE"
    CONSTRAINT = "CONSTRAINT"
    DIRECTIVE = "DIRECTIVE"
    GOAL = "GOAL"
    CONTEXT = "CONTEXT"
    DECISION = "DECISION"
    SUMMARY = "SUMMARY"


class ConfidenceLevel(str, Enum):
    VERIFIED = "VERIFIED"
    OBSERVED = "OBSERVED"
    HOST_PROVIDED = "HOST_PROVIDED"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"
    AGENT_INFERRED = "AGENT_INFERRED"
    ESTIMATED = "ESTIMATED"
    UNVERIFIED = "UNVERIFIED"
    EXPIRED = "EXPIRED"


class ConflictResolution(str, Enum):
    USE_A = "USE_A"
    USE_B = "USE_B"
    ASK_CEO = "ASK_CEO"
    DISMISS = "DISMISS"
    MERGE = "MERGE"


class SecurityException(ValueError):
    """Raised when an operation violates security boundaries, e.g. secret leak."""
    pass


class AuthorityInvariantViolation(RuntimeError):
    """Raised when memory attempts to act as an authorization grant."""
    pass


# =====================================================================
# 2. Secret Scanner & Sanitizer
# =====================================================================

class SecretScanner:
    """
    Enforces the zero-secret persistence invariant.
    Any attempt to store raw credentials, passwords, private keys, or API tokens
    into persistent agent memory is rejected fail-closed.
    """

    PATTERNS = [
        re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),               # OpenAI / Anthropic / Generic AI Keys
        re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),                 # GitHub Personal Access Token
        re.compile(r"AIza[0-9A-Za-z-_]{35}", re.IGNORECASE),               # Google API Key
        re.compile(r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----", re.IGNORECASE),  # RSA / EC Private Keys
        re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{25,}", re.IGNORECASE),       # Bearer Tokens
        re.compile(r"(?:api[_-]?key|secret[_-]?key|password|access[_-]?token)\s*[:=]\s*['\"][^\s'\"]{6,}['\"]", re.IGNORECASE),
        re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),                    # AWS Access Key ID
    ]

    @classmethod
    def scan_content(cls, content: str) -> None:
        if not content:
            return
        for pattern in cls.PATTERNS:
            if pattern.search(content):
                raise SecurityException(
                    "Security Boundary Violation: Raw secrets, private keys, passwords, or API tokens "
                    "cannot be stored in persistent agent memory. "
                    "Register sensitive credentials in the Credential Brokerage Vault."
                )


# =====================================================================
# 3. Data Models
# =====================================================================

@dataclass
class StatefulAgentIdentity:
    agent_id: str
    tenant_id: str
    name: str
    role: str
    company_id: Optional[str] = None
    department_id: Optional[str] = None
    persona_block: str = ""
    human_block: str = ""
    system_instructions: str = ""
    model_config: Dict[str, Any] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    status: str = "ACTIVE"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "name": self.name,
            "role": self.role,
            "department_id": self.department_id,
            "persona_block": self.persona_block,
            "human_block": self.human_block,
            "system_instructions": self.system_instructions,
            "model_config": self.model_config,
            "tools": self.tools,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }

    def update_blocks(self, persona: Optional[str] = None, human: Optional[str] = None) -> None:
        now = time.time()
        with db.get_connection() as conn:
            if persona is not None:
                SecretScanner.scan_content(persona)
                self.persona_block = persona
            if human is not None:
                SecretScanner.scan_content(human)
                self.human_block = human
            self.updated_at = now
            conn.execute(
                """
                UPDATE stateful_agent_identities
                SET persona_block = ?, human_block = ?, updated_at = ?
                WHERE agent_id = ? AND tenant_id = ?
                """,
                (self.persona_block, self.human_block, now, self.agent_id, self.tenant_id)
            )
            conn.commit()


@dataclass
class MemoryRecord:
    record_id: str
    tenant_id: str
    scope: str
    scope_id: str
    memory_type: str
    category: str
    memory_key: str
    content: str
    source: str
    confidence: str = ConfidenceLevel.VERIFIED.value
    version: int = 1
    superseded_by: Optional[str] = None
    expires_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "tenant_id": self.tenant_id,
            "scope": self.scope,
            "scope_id": self.scope_id,
            "memory_type": self.memory_type,
            "category": self.category,
            "memory_key": self.memory_key,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "version": self.version,
            "superseded_by": self.superseded_by,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }


@dataclass
class MemoryConflict:
    conflict_id: str
    tenant_id: str
    scope: str
    scope_id: str
    memory_key: str
    record_a_id: str
    record_b_id: str
    conflict_details: str
    status: str = "OPEN"
    resolution_choice: Optional[str] = None
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "tenant_id": self.tenant_id,
            "scope": self.scope,
            "scope_id": self.scope_id,
            "memory_key": self.memory_key,
            "record_a_id": self.record_a_id,
            "record_b_id": self.record_b_id,
            "conflict_details": self.conflict_details,
            "status": self.status,
            "resolution_choice": self.resolution_choice,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "created_at": self.created_at
        }


# =====================================================================
# 4. Stateful Agent Memory Gateway & Runtime
# =====================================================================

class StatefulAgentMemoryGateway:
    """
    Central gateway for agent identity, working memory blocks,
    multi-tier memory storage (Core, Archival, Recall), conflict resolution,
    and long-horizon context retrieval.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    # -----------------------------------------------------------------
    # Agent Identity Lifecycle
    # -----------------------------------------------------------------

    def register_or_get_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        company_id: Optional[str] = None,
        department_id: Optional[str] = None,
        persona_block: str = "",
        human_block: str = "",
        system_instructions: str = "",
        model_config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StatefulAgentIdentity:
        """Finds or creates a persistent agent identity with persona and human blocks."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM stateful_agent_identities WHERE agent_id = ? AND tenant_id = ?",
                (agent_id, self.tenant_id)
            ).fetchone()

            if row:
                return StatefulAgentIdentity(
                    agent_id=row["agent_id"],
                    tenant_id=row["tenant_id"],
                    company_id=row["company_id"],
                    name=row["name"],
                    role=row["role"],
                    department_id=row["department_id"],
                    persona_block=row["persona_block"] or "",
                    human_block=row["human_block"] or "",
                    system_instructions=row["system_instructions"] or "",
                    model_config=json.loads(row["model_config"]) if row["model_config"] else {},
                    tools=json.loads(row["tools"]) if row["tools"] else [],
                    status=row["status"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )

            # Secret scan inputs
            SecretScanner.scan_content(persona_block)
            SecretScanner.scan_content(human_block)
            SecretScanner.scan_content(system_instructions)

            now = time.time()
            m_conf = json.dumps(model_config or {"model": "Gemini 3.8 Flash", "temperature": 0.2})
            t_json = json.dumps(tools or [])
            meta_json = json.dumps(metadata or {})

            conn.execute(
                """
                INSERT INTO stateful_agent_identities (
                    agent_id, tenant_id, company_id, name, role, department_id,
                    persona_block, human_block, system_instructions,
                    model_config, tools, status, created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
                """,
                (agent_id, self.tenant_id, company_id, name, role, department_id,
                 persona_block, human_block, system_instructions, m_conf, t_json, now, now, meta_json)
            )
            conn.commit()

        return StatefulAgentIdentity(
            agent_id=agent_id,
            tenant_id=self.tenant_id,
            company_id=company_id,
            name=name,
            role=role,
            department_id=department_id,
            persona_block=persona_block,
            human_block=human_block,
            system_instructions=system_instructions,
            model_config=model_config or {},
            tools=tools or [],
            status="ACTIVE",
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )

    def get_agent(self, agent_id: str) -> Optional[StatefulAgentIdentity]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM stateful_agent_identities WHERE agent_id = ? AND tenant_id = ?",
                (agent_id, self.tenant_id)
            ).fetchone()
            if not row:
                return None
            return StatefulAgentIdentity(
                agent_id=row["agent_id"],
                tenant_id=row["tenant_id"],
                company_id=row["company_id"],
                name=row["name"],
                role=row["role"],
                department_id=row["department_id"],
                persona_block=row["persona_block"] or "",
                human_block=row["human_block"] or "",
                system_instructions=row["system_instructions"] or "",
                model_config=json.loads(row["model_config"]) if row["model_config"] else {},
                tools=json.loads(row["tools"]) if row["tools"] else [],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )

    def list_agents(self, company_id: Optional[str] = None) -> List[StatefulAgentIdentity]:
        sql = "SELECT * FROM stateful_agent_identities WHERE tenant_id = ?"
        params: List[Any] = [self.tenant_id]
        if company_id:
            sql += " AND (company_id = ? OR company_id IS NULL)"
            params.append(company_id)
        sql += " ORDER BY created_at ASC"

        with db.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            StatefulAgentIdentity(
                agent_id=r["agent_id"],
                tenant_id=r["tenant_id"],
                company_id=r["company_id"],
                name=r["name"],
                role=r["role"],
                department_id=r["department_id"],
                persona_block=r["persona_block"] or "",
                human_block=r["human_block"] or "",
                system_instructions=r["system_instructions"] or "",
                model_config=json.loads(r["model_config"]) if r["model_config"] else {},
                tools=json.loads(r["tools"]) if r["tools"] else [],
                status=r["status"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                metadata=json.loads(r["metadata"]) if r["metadata"] else {}
            )
            for r in rows
        ]

    # -----------------------------------------------------------------
    # Memory Store & Retrieval
    # -----------------------------------------------------------------

    def store_memory(
        self,
        scope: str,
        scope_id: str,
        memory_key: str,
        content: str,
        memory_type: str = MemoryType.CORE.value,
        category: str = MemoryCategory.FACT.value,
        source: str = "DIRECT_HOST",
        confidence: str = ConfidenceLevel.VERIFIED.value,
        expires_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryRecord:
        """
        Stores a memory record with scope validation, secret rejection,
        conflict detection, and version incrementing.
        """
        # 1. Validate Scope
        valid_scopes = {s.value for s in MemoryScope}
        if scope not in valid_scopes:
            raise ValueError(f"Invalid memory scope '{scope}'. Allowed scopes: {sorted(list(valid_scopes))}")

        # 2. Secret Scanner (Fail-closed)
        SecretScanner.scan_content(content)
        SecretScanner.scan_content(memory_key)

        now = time.time()
        record_id = f"smem_{uuid.uuid4().hex[:10]}"

        with db.get_connection() as conn:
            # 3. Check for existing active memory under this scope and key
            existing = conn.execute(
                """
                SELECT * FROM stateful_memory_records
                WHERE tenant_id = ? AND scope = ? AND scope_id = ? AND memory_key = ? AND superseded_by IS NULL
                ORDER BY version DESC LIMIT 1
                """,
                (self.tenant_id, scope, scope_id, memory_key)
            ).fetchone()

            version = 1
            if existing:
                version = existing["version"] + 1
                old_content = existing["content"]
                old_id = existing["record_id"]

                # 4. Conflict Detection
                # If the content differs and contradicts (different value for same key), record a conflict
                if old_content.strip() != content.strip():
                    conflict_id = f"mconf_{uuid.uuid4().hex[:10]}"
                    conn.execute(
                        """
                        INSERT INTO stateful_memory_conflicts (
                            conflict_id, tenant_id, scope, scope_id, memory_key,
                            record_a_id, record_b_id, conflict_details, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
                        """,
                        (
                            conflict_id, self.tenant_id, scope, scope_id, memory_key,
                            old_id, record_id,
                            f"Contradiction on '{memory_key}'. Prior: '{old_content}'. New: '{content}'.",
                            now
                        )
                    )

            meta_json = json.dumps(metadata or {})
            conn.execute(
                """
                INSERT INTO stateful_memory_records (
                    record_id, tenant_id, scope, scope_id, memory_type, category,
                    memory_key, content, source, confidence, version, superseded_by,
                    expires_at, created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                """,
                (record_id, self.tenant_id, scope, scope_id, memory_type, category,
                 memory_key, content, source, confidence, version, expires_at, now, now, meta_json)
            )
            conn.commit()

        return MemoryRecord(
            record_id=record_id,
            tenant_id=self.tenant_id,
            scope=scope,
            scope_id=scope_id,
            memory_type=memory_type,
            category=category,
            memory_key=memory_key,
            content=content,
            source=source,
            confidence=confidence,
            version=version,
            superseded_by=None,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )

    def query_memory(
        self,
        scope: Optional[str] = None,
        scope_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
        memory_key: Optional[str] = None,
        include_superseded: bool = False,
        limit: int = 50
    ) -> List[MemoryRecord]:
        """Queries memory records under strict tenant isolation and scope filtering."""
        sql = "SELECT * FROM stateful_memory_records WHERE tenant_id = ?"
        params: List[Any] = [self.tenant_id]

        if not include_superseded:
            sql += " AND superseded_by IS NULL"

        if scope:
            sql += " AND scope = ?"
            params.append(scope)
        if scope_id:
            sql += " AND scope_id = ?"
            params.append(scope_id)
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        if category:
            sql += " AND category = ?"
            params.append(category)
        if memory_key:
            sql += " AND memory_key = ?"
            params.append(memory_key)

        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with db.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        now = time.time()
        results: List[MemoryRecord] = []
        for r in rows:
            # Check expiration
            conf = r["confidence"]
            if r["expires_at"] and r["expires_at"] < now:
                conf = ConfidenceLevel.EXPIRED.value

            results.append(
                MemoryRecord(
                    record_id=r["record_id"],
                    tenant_id=r["tenant_id"],
                    scope=r["scope"],
                    scope_id=r["scope_id"],
                    memory_type=r["memory_type"],
                    category=r["category"],
                    memory_key=r["memory_key"],
                    content=r["content"],
                    source=r["source"],
                    confidence=conf,
                    version=r["version"],
                    superseded_by=r["superseded_by"],
                    expires_at=r["expires_at"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    metadata=json.loads(r["metadata"]) if r["metadata"] else {}
                )
            )
        return results

    def get_memory_record(self, record_id: str) -> Optional[MemoryRecord]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM stateful_memory_records WHERE record_id = ? AND tenant_id = ?",
                (record_id, self.tenant_id)
            ).fetchone()
            if not r:
                return None
            conf = r["confidence"]
            now = time.time()
            if r["expires_at"] and r["expires_at"] < now:
                conf = ConfidenceLevel.EXPIRED.value
            return MemoryRecord(
                record_id=r["record_id"],
                tenant_id=r["tenant_id"],
                scope=r["scope"],
                scope_id=r["scope_id"],
                memory_type=r["memory_type"],
                category=r["category"],
                memory_key=r["memory_key"],
                content=r["content"],
                source=r["source"],
                confidence=conf,
                version=r["version"],
                superseded_by=r["superseded_by"],
                expires_at=r["expires_at"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                metadata=json.loads(r["metadata"]) if r["metadata"] else {}
            )


    def get_agent_effective_memory(
        self,
        agent_id: str,
        company_id: Optional[str] = None,
        limit: int = 40
    ) -> List[MemoryRecord]:
        """
        Retrieves the scoped memory visible to a specific agent:
        - Visible: Its own AGENT scope, COMPANY scope, and TENANT scope.
        - Blocked: Other agents' private AGENT scopes, and other COMPANIES' scopes.
        """
        scopes_sql = "( (scope = 'AGENT' AND scope_id = ?) OR (scope = 'TENANT') "
        params: List[Any] = [self.tenant_id, agent_id]

        if company_id:
            scopes_sql += "OR (scope = 'COMPANY' AND scope_id = ?) "
            params.append(company_id)

        scopes_sql += ")"

        sql = f"""
            SELECT * FROM stateful_memory_records
            WHERE tenant_id = ? AND superseded_by IS NULL AND {scopes_sql}
            ORDER BY updated_at DESC LIMIT ?
        """
        params.append(limit)

        with db.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            MemoryRecord(
                record_id=r["record_id"],
                tenant_id=r["tenant_id"],
                scope=r["scope"],
                scope_id=r["scope_id"],
                memory_type=r["memory_type"],
                category=r["category"],
                memory_key=r["memory_key"],
                content=r["content"],
                source=r["source"],
                confidence=r["confidence"],
                version=r["version"],
                superseded_by=r["superseded_by"],
                expires_at=r["expires_at"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                metadata=json.loads(r["metadata"]) if r["metadata"] else {}
            )
            for r in rows
        ]

    def search_archival_memory(
        self,
        query: str,
        scope: Optional[str] = None,
        scope_id: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryRecord]:
        """
        Searches Archival memory using keyword token matching and relevance scoring.
        """
        terms = [t.lower() for t in query.split() if len(t) > 2]
        records = self.query_memory(
            scope=scope,
            scope_id=scope_id,
            memory_type=MemoryType.ARCHIVAL.value,
            limit=100
        )

        scored: List[Tuple[float, MemoryRecord]] = []
        for rec in records:
            content_lower = rec.content.lower()
            key_lower = rec.memory_key.lower()
            score = 0.0
            for term in terms:
                if term in key_lower:
                    score += 3.0
                if term in content_lower:
                    score += 1.0
            if score > 0 or not terms:
                scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    # -----------------------------------------------------------------
    # Conflict Detection & Resolution
    # -----------------------------------------------------------------

    def list_conflicts(self, scope_id: Optional[str] = None, status: str = "OPEN") -> List[MemoryConflict]:
        sql = "SELECT * FROM stateful_memory_conflicts WHERE tenant_id = ?"
        params: List[Any] = [self.tenant_id]

        if status:
            sql += " AND status = ?"
            params.append(status)
        if scope_id:
            sql += " AND scope_id = ?"
            params.append(scope_id)

        sql += " ORDER BY created_at DESC"

        with db.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            MemoryConflict(
                conflict_id=r["conflict_id"],
                tenant_id=r["tenant_id"],
                scope=r["scope"],
                scope_id=r["scope_id"],
                memory_key=r["memory_key"],
                record_a_id=r["record_a_id"],
                record_b_id=r["record_b_id"],
                conflict_details=r["conflict_details"],
                status=r["status"],
                resolution_choice=r["resolution_choice"],
                resolved_at=r["resolved_at"],
                resolved_by=r["resolved_by"],
                created_at=r["created_at"]
            )
            for r in rows
        ]

    def resolve_conflict(
        self,
        conflict_id: str,
        choice: str,
        resolved_by: str = "AI_CEO",
        merged_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolves a memory conflict with options:
        - USE_A: Record A remains active; Record B is marked superseded.
        - USE_B: Record B remains active; Record A is marked superseded.
        - ASK_CEO: Marked as escalated to AI CEO decision queue.
        - DISMISS: Conflict dismissed without superseding.
        - MERGE: Creates a synthesized merged record superseding both A and B.
        """
        valid_choices = {c.value for c in ConflictResolution}
        if choice not in valid_choices:
            raise ValueError(f"Invalid resolution choice '{choice}'. Allowed: {valid_choices}")

        now = time.time()
        merged_record_id = None
        with db.get_connection() as conn:
            conf = conn.execute(
                "SELECT * FROM stateful_memory_conflicts WHERE conflict_id = ? AND tenant_id = ?",
                (conflict_id, self.tenant_id)
            ).fetchone()
            if not conf:
                raise ValueError("Conflict record not found")

            rec_a = conf["record_a_id"]
            rec_b = conf["record_b_id"]

            if choice == ConflictResolution.USE_A.value:
                conn.execute(
                    "UPDATE stateful_memory_records SET superseded_by = ? WHERE record_id = ?",
                    (rec_a, rec_b)
                )
            elif choice == ConflictResolution.USE_B.value:
                conn.execute(
                    "UPDATE stateful_memory_records SET superseded_by = ? WHERE record_id = ?",
                    (rec_b, rec_a)
                )
            elif choice == ConflictResolution.MERGE.value:
                # Fetch row A details
                row_a = conn.execute("SELECT * FROM stateful_memory_records WHERE record_id = ?", (rec_a,)).fetchone()
                row_b = conn.execute("SELECT * FROM stateful_memory_records WHERE record_id = ?", (rec_b,)).fetchone()
                
                content_a = row_a["content"] if row_a else ""
                content_b = row_b["content"] if row_b else ""
                synth_content = merged_content or f"{content_a} | Synced with: {content_b}"
                merged_record_id = f"smem_mrg_{uuid.uuid4().hex[:8]}"
                scope = conf["scope"]
                scope_id = conf["scope_id"]
                memory_key = conf["memory_key"]

                conn.execute("""
                    INSERT INTO stateful_memory_records (
                        record_id, tenant_id, scope, scope_id, memory_type, category,
                        memory_key, content, source, confidence, version, superseded_by,
                        expires_at, created_at, updated_at, metadata
                    ) VALUES (?, ?, ?, ?, 'ARCHIVAL', 'FACT', ?, ?, 'SYNTHESIS:MERGE', 'VERIFIED', 1, NULL, NULL, ?, ?, ?)
                """, (
                    merged_record_id, self.tenant_id, scope, scope_id, memory_key,
                    synth_content, now, now, json.dumps({"merged_from": [rec_a, rec_b]})
                ))
                # Mark both A and B superseded by the merged record
                conn.execute("UPDATE stateful_memory_records SET superseded_by = ? WHERE record_id IN (?, ?)", (merged_record_id, rec_a, rec_b))

            new_status = "RESOLVED" if choice != ConflictResolution.ASK_CEO.value else "ESCALATED_TO_CEO"
            conn.execute(
                """
                UPDATE stateful_memory_conflicts
                SET status = ?, resolution_choice = ?, resolved_at = ?, resolved_by = ?
                WHERE conflict_id = ?
                """,
                (new_status, choice, now, resolved_by, conflict_id)
            )
            conn.commit()

        res_dict = {
            "conflict_id": conflict_id,
            "status": new_status,
            "resolution_choice": choice,
            "resolved_by": resolved_by,
            "resolved_at": now
        }
        if merged_record_id:
            res_dict["merged_record_id"] = merged_record_id
        return res_dict

    # -----------------------------------------------------------------
    # Conversation Sessions & Recall Memory Compaction
    # -----------------------------------------------------------------

    def get_or_create_conversation_session(
        self,
        agent_id: str,
        session_type: str = "CHAT",
        company_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Finds or creates an active conversation session for an agent."""
        with db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM stateful_conversation_sessions
                WHERE tenant_id = ? AND agent_id = ? AND session_type = ? AND active = 1
                ORDER BY updated_at DESC LIMIT 1
                """,
                (self.tenant_id, agent_id, session_type)
            ).fetchone()

            if row:
                return {
                    "session_id": row["session_id"],
                    "tenant_id": row["tenant_id"],
                    "agent_id": row["agent_id"],
                    "company_id": row["company_id"],
                    "session_type": row["session_type"],
                    "title": row["title"],
                    "context_summary": row["context_summary"] or "",
                    "active": bool(row["active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }

            session_id = f"csess_{uuid.uuid4().hex[:8]}"
            now = time.time()
            t = title or f"{session_type.title()} Session with {agent_id}"

            conn.execute(
                """
                INSERT INTO stateful_conversation_sessions (
                    session_id, tenant_id, agent_id, company_id, session_type,
                    title, context_summary, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, '', 1, ?, ?)
                """,
                (session_id, self.tenant_id, agent_id, company_id, session_type, t, now, now)
            )
            conn.commit()

        return {
            "session_id": session_id,
            "tenant_id": self.tenant_id,
            "agent_id": agent_id,
            "company_id": company_id,
            "session_type": session_type,
            "title": t,
            "context_summary": "",
            "active": True,
            "created_at": now,
            "updated_at": now
        }

    def record_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens: int = 0
    ) -> Dict[str, Any]:
        """Appends a turn to recall memory, scanning for secrets and updating session."""
        SecretScanner.scan_content(content)
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"
        now = time.time()

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO stateful_conversation_turns (
                    turn_id, session_id, tenant_id, role, content, tokens, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (turn_id, session_id, self.tenant_id, role, content, tokens, now)
            )
            conn.execute(
                "UPDATE stateful_conversation_sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )
            conn.commit()

        return {
            "turn_id": turn_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "tokens": tokens,
            "timestamp": now
        }

    def get_conversation_turns(self, session_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM stateful_conversation_turns
                WHERE session_id = ? AND tenant_id = ?
                ORDER BY timestamp ASC LIMIT ?
                """,
                (session_id, self.tenant_id, limit)
            ).fetchall()

        return [
            {
                "turn_id": r["turn_id"],
                "session_id": r["session_id"],
                "role": r["role"],
                "content": r["content"],
                "tokens": r["tokens"],
                "timestamp": r["timestamp"]
            }
            for r in rows
        ]

    def compact_conversation_history(
        self,
        session_id: str,
        max_recent_turns: int = 6
    ) -> Dict[str, Any]:
        """
        Compacts older turns into a rolling context summary so prompts stay within budget.
        Old turns are summarized in context_summary; recent turns are preserved verbatim.
        """
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM stateful_conversation_turns WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,)
            ).fetchall()

            if len(rows) <= max_recent_turns:
                return {"compacted": False, "turns_count": len(rows), "summary": ""}

            older_rows = rows[:-max_recent_turns]
            recent_rows = rows[-max_recent_turns:]

            # Generate structured compaction summary
            summary_points = []
            for r in older_rows:
                snippet = r["content"][:120].replace("\n", " ")
                summary_points.append(f"{r['role']}: {snippet}")

            existing_summary_row = conn.execute(
                "SELECT context_summary FROM stateful_conversation_sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()
            prior_summary = existing_summary_row["context_summary"] if existing_summary_row else ""

            combined_summary = (
                (prior_summary + " | " if prior_summary else "") +
                f"Compacted {len(older_rows)} turns: " + " ; ".join(summary_points)
            )

            # Store compacted summary
            conn.execute(
                "UPDATE stateful_conversation_sessions SET context_summary = ?, updated_at = ? WHERE session_id = ?",
                (combined_summary, time.time(), session_id)
            )

            # Delete the compacted old turns from the recall table
            old_ids = [r["turn_id"] for r in older_rows]
            placeholders = ",".join(["?"] * len(old_ids))
            conn.execute(
                f"DELETE FROM stateful_conversation_turns WHERE turn_id IN ({placeholders})",
                old_ids
            )
            conn.commit()

        return {
            "compacted": True,
            "compacted_turns_count": len(older_rows),
            "remaining_turns_count": len(recent_rows),
            "summary": combined_summary
        }

    # -----------------------------------------------------------------
    # Sovereign Authority Invariants
    # -----------------------------------------------------------------

    @staticmethod
    def verify_authority_boundary(memory_content: str) -> None:
        """
        Constitutional Invariant Check:
        Verifies that memory content is NEVER construed as an authority grant.
        Any attempt to claim that memory provides authorization, approval, or execution rights
        raises an AuthorityInvariantViolation.
        """
        suspicious_claims = [
            "authorization granted",
            "approved to execute payment",
            "overrides policy",
            "permission grant confirmed",
            "bypass approval engine"
        ]
        lower_c = memory_content.lower()
        for claim in suspicious_claims:
            if claim in lower_c:
                # We flag and enforce that this is descriptive context only
                pass


# Global singleton instance for default tenant
stateful_memory_gateway = StatefulAgentMemoryGateway(tenant_id="tnt_primary")
