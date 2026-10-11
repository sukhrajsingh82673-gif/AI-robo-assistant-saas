"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
Nine-Level Enterprise KillSwitch Matrix
Deterministic execution barrier evaluated at kernel boundary across:
GLOBAL, TENANT, COMPANY, SESSION, EXECUTION, DOMAIN, AGENT, EMPLOYEE, TOOL.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Set
from .db import db

logger = logging.getLogger("zonata.killswitch")

class KillSwitchEngagedException(Exception):
    """Raised when an operation is halted by an active KillSwitch barrier."""
    pass

class KillSwitchLevel:
    GLOBAL = "GLOBAL"
    TENANT = "TENANT"
    COMPANY = "COMPANY"
    SESSION = "SESSION"
    EXECUTION = "EXECUTION"
    DOMAIN = "DOMAIN"
    AGENT = "AGENT"
    EMPLOYEE = "EMPLOYEE"
    TOOL = "TOOL"

class KillSwitchMatrix:
    """
    Evaluates and enforces multi-tiered KillSwitch activations.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._ensure_table()

    def _ensure_table(self):
        with db.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_killswitch_matrix (
                switch_id TEXT PRIMARY KEY,
                level TEXT NOT NULL, -- GLOBAL, TENANT, COMPANY, SESSION, EXECUTION, DOMAIN, AGENT, EMPLOYEE, TOOL
                target_id TEXT NOT NULL, -- Target entity ID or '*'
                reason TEXT NOT NULL,
                activated_by TEXT NOT NULL,
                activated_at REAL NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                deactivated_at REAL,
                deactivated_by TEXT
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ks_level ON enterprise_killswitch_matrix(level, target_id, is_active);")
            conn.commit()

    def activate(
        self,
        level: str,
        target_id: str,
        reason: str,
        activated_by: str = "HUMAN_OWNER"
    ) -> str:
        """Engages a KillSwitch at a specified level."""
        switch_id = f"ks_{level.lower()}_{target_id[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO enterprise_killswitch_matrix (
                    switch_id, level, target_id, reason, activated_by, activated_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (switch_id, level, target_id, reason, activated_by, now))
            conn.commit()
            logger.warning(f"KILLSWITCH ENGAGED: Level={level}, Target={target_id}, Reason={reason}")
            return switch_id

    def deactivate(
        self,
        switch_id_or_level: str,
        target_id: Optional[str] = None,
        deactivated_by: str = "HUMAN_OWNER"
    ) -> bool:
        """Disengages an active KillSwitch by switch_id or (level, target_id)."""
        now = time.time()
        with db.get_connection() as conn:
            if target_id is not None:
                res = conn.execute("""
                    UPDATE enterprise_killswitch_matrix
                    SET is_active = 0, deactivated_at = ?, deactivated_by = ?
                    WHERE level = ? AND (target_id = ? OR target_id = '*') AND is_active = 1
                """, (now, deactivated_by, switch_id_or_level, target_id))
            else:
                res = conn.execute("""
                    UPDATE enterprise_killswitch_matrix
                    SET is_active = 0, deactivated_at = ?, deactivated_by = ?
                    WHERE (switch_id = ? OR level = ?) AND is_active = 1
                """, (now, deactivated_by, switch_id_or_level, switch_id_or_level))
            conn.commit()
            return res.rowcount > 0

    def is_activated(self, level: str, target_id: Optional[str] = None) -> bool:
        """Checks if a KillSwitch is currently active at level (and optional target)."""
        with db.get_connection() as conn:
            if target_id and target_id != "*":
                row = conn.execute("""
                    SELECT 1 FROM enterprise_killswitch_matrix
                    WHERE level = ? AND (target_id = ? OR target_id = '*') AND is_active = 1
                """, (level, target_id)).fetchone()
            else:
                row = conn.execute("""
                    SELECT 1 FROM enterprise_killswitch_matrix
                    WHERE level = ? AND is_active = 1
                """, (level,)).fetchone()
            return row is not None

    def is_engaged(self, level: str, target_id: Optional[str] = None) -> bool:
        """Alias for is_activated."""
        return self.is_activated(level, target_id)

    def assert_can_execute(
        self,
        company_id: Optional[str] = None,
        session_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        domain: Optional[str] = None,
        agent_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        tool_id: Optional[str] = None
    ):
        """
        Evaluates all 9 levels.
        Raises KillSwitchEngagedException immediately if any level is active.
        """
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM enterprise_killswitch_matrix WHERE is_active = 1"
            ).fetchall()

            for r in rows:
                lvl = r["level"]
                tgt = r["target_id"]
                reason = r["reason"]

                # 1. Global
                if lvl == KillSwitchLevel.GLOBAL:
                    raise KillSwitchEngagedException(f"GLOBAL KillSwitch active: {reason}")

                # 2. Tenant
                if lvl == KillSwitchLevel.TENANT and tgt == self.tenant_id:
                    raise KillSwitchEngagedException(f"TENANT KillSwitch active for '{self.tenant_id}': {reason}")

                # 3. Company
                if lvl == KillSwitchLevel.COMPANY and company_id and tgt == company_id:
                    raise KillSwitchEngagedException(f"COMPANY KillSwitch active for '{company_id}': {reason}")

                # 4. Session
                if lvl == KillSwitchLevel.SESSION and session_id and tgt == session_id:
                    raise KillSwitchEngagedException(f"SESSION KillSwitch active for '{session_id}': {reason}")

                # 5. Execution
                if lvl == KillSwitchLevel.EXECUTION and execution_id and tgt == execution_id:
                    raise KillSwitchEngagedException(f"EXECUTION KillSwitch active for '{execution_id}': {reason}")

                # 6. Domain
                if lvl == KillSwitchLevel.DOMAIN and domain and tgt == domain:
                    raise KillSwitchEngagedException(f"DOMAIN KillSwitch active for '{domain}': {reason}")

                # 7. Agent
                if lvl == KillSwitchLevel.AGENT and agent_id and tgt == agent_id:
                    raise KillSwitchEngagedException(f"AGENT KillSwitch active for '{agent_id}': {reason}")

                # 8. Employee
                if lvl == KillSwitchLevel.EMPLOYEE and employee_id and tgt == employee_id:
                    raise KillSwitchEngagedException(f"EMPLOYEE KillSwitch active for '{employee_id}': {reason}")

                # 9. Tool
                if lvl == KillSwitchLevel.TOOL and tool_id and tgt == tool_id:
                    raise KillSwitchEngagedException(f"TOOL KillSwitch active for '{tool_id}': {reason}")
