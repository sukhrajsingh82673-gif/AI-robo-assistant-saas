"""
RoboAssistant Company OS 1.0 — Layered Organizational Memory
Tiers: PLATFORM -> COMPANY -> DEPARTMENT -> EMPLOYEE -> MISSION.
Types: FACT, PREFERENCE, POLICY, DECISION, LESSON, ASSUMPTION, OUTCOME.
"""

from typing import List, Dict, Any, Optional
import time
import uuid
from .db import db

class MemoryTier:
    PLATFORM = "PLATFORM"
    COMPANY = "COMPANY"
    DEPARTMENT = "DEPARTMENT"
    EMPLOYEE = "EMPLOYEE"
    MISSION = "MISSION"

class MemoryType:
    FACT = "FACT"
    PREFERENCE = "PREFERENCE"
    POLICY = "POLICY"
    DECISION = "DECISION"
    LESSON = "LESSON"
    ASSUMPTION = "ASSUMPTION"
    OUTCOME = "OUTCOME"

class OrganizationalMemory:
    @staticmethod
    def store_memory(
        tenant_id: str,
        memory_tier: str,
        memory_type: str,
        content: str,
        company_id: Optional[str] = None,
        department_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        provenance: str = "EXECUTIVE_ACTION"
    ) -> str:
        mem_id = f"mem_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO organizational_memory (
                    memory_id, tenant_id, company_id, department_id,
                    agent_id, mission_id, memory_tier, memory_type,
                    content, provenance, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mem_id, tenant_id, company_id, department_id, agent_id, mission_id,
                 memory_tier, memory_type, content, provenance, now)
            )
            conn.commit()
        return mem_id

    @staticmethod
    def query_memory(
        tenant_id: str,
        company_id: Optional[str] = None,
        memory_tier: Optional[str] = None,
        memory_type: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            sql = "SELECT * FROM organizational_memory WHERE tenant_id = ?"
            params = [tenant_id]
            if company_id:
                sql += " AND (company_id = ? OR company_id IS NULL)"
                params.append(company_id)
            if memory_tier:
                sql += " AND memory_tier = ?"
                params.append(memory_tier)
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)
            if agent_id:
                sql += " AND agent_id = ?"
                params.append(agent_id)
            sql += " ORDER BY created_at DESC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
