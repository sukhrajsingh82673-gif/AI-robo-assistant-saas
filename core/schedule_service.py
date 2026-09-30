"""
RoboAssistant Company OS 1.0 — Universal SaaS Schedule & Planning Engine
Production planning layer connecting AI CEO, missions, TaskMaker, processes,
workforce, financial deadlines, and robotic desktop execution.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
import json
import re
from datetime import datetime, timedelta
from .db import db

SCHEDULE_ITEM_TYPES = [
    "meeting",
    "mission_milestone",
    "deadline",
    "process_run",
    "budget_review",
    "approval_deadline",
    "coworker_task",
    "ai_workforce_shift",
    "customer_touchpoint",
    "report_generation",
    "reminder",
    "maintenance",
    "compliance_audit",
    "desktop_automation",
    "strategic_review"
]

class UniversalScheduleService:
    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    def list_schedules(
        self,
        company_id: Optional[str] = None,
        item_type: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        start_after: Optional[float] = None,
        start_before: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Lists schedule items with optional filtering."""
        query = "SELECT * FROM universal_schedules WHERE tenant_id = ?"
        params: List[Any] = [self.tenant_id]

        if company_id and company_id != "all":
            query += " AND (company_id = ? OR company_id = 'all')"
            params.append(company_id)

        if item_type and item_type != "all":
            query += " AND item_type = ?"
            params.append(item_type)

        if priority and priority != "all":
            query += " AND priority = ?"
            params.append(priority)

        if status and status != "all":
            query += " AND status = ?"
            params.append(status)

        if start_after is not None:
            query += " AND start_time >= ?"
            params.append(start_after)

        if start_before is not None:
            query += " AND start_time <= ?"
            params.append(start_before)

        query += " ORDER BY start_time ASC"

        with db.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        items = []
        for r in rows:
            meta = {}
            if r["metadata"]:
                try:
                    meta = json.loads(r["metadata"])
                except Exception:
                    meta = {}
            items.append({
                "schedule_id": r["schedule_id"],
                "tenant_id": r["tenant_id"],
                "company_id": r["company_id"],
                "title": r["title"],
                "description": r["description"] or "",
                "item_type": r["item_type"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "recurrence": r["recurrence"],
                "priority": r["priority"],
                "status": r["status"],
                "assigned_to": r["assigned_to"],
                "related_entity_type": r["related_entity_type"],
                "related_entity_id": r["related_entity_id"],
                "conflict_detected": bool(r["conflict_detected"]),
                "conflict_reason": r["conflict_reason"],
                "metadata": meta,
                "created_at": r["created_at"]
            })

        # If zero items exist in DB, seed canonical initial schedule items for companies
        if not items and (not company_id or company_id == "all"):
            self._seed_initial_schedules()
            return self.list_schedules(company_id, item_type, priority, status, start_after, start_before)

        return items

    def create_schedule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new schedule item with automatic conflict detection."""
        schedule_id = data.get("schedule_id") or f"sch_{uuid.uuid4().hex[:8]}"
        now = time.time()
        company_id = data.get("company_id") or "comp_primary"
        title = data.get("title", "Untitled Schedule Item").strip()
        description = data.get("description", "")
        item_type = data.get("item_type", "meeting")
        if item_type not in SCHEDULE_ITEM_TYPES:
            item_type = "reminder"
        
        start_time = float(data.get("start_time", now + 3600))
        end_time = float(data.get("end_time", start_time + 3600))
        recurrence = data.get("recurrence", "NONE")
        priority = data.get("priority", "MEDIUM").upper()
        status = data.get("status", "SCHEDULED")
        assigned_to = data.get("assigned_to", "AI CEO")
        related_entity_type = data.get("related_entity_type")
        related_entity_id = data.get("related_entity_id")
        metadata = data.get("metadata", {})

        # Run conflict check
        conflict_detected, conflict_reason = self._check_conflicts(company_id, start_time, end_time, schedule_id)

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO universal_schedules (
                    schedule_id, tenant_id, company_id, title, description,
                    item_type, start_time, end_time, recurrence, priority,
                    status, assigned_to, related_entity_type, related_entity_id,
                    conflict_detected, conflict_reason, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    schedule_id, self.tenant_id, company_id, title, description,
                    item_type, start_time, end_time, recurrence, priority,
                    status, assigned_to, related_entity_type, related_entity_id,
                    1 if conflict_detected else 0, conflict_reason,
                    json.dumps(metadata), now
                )
            )
            conn.commit()

        return {
            "schedule_id": schedule_id,
            "company_id": company_id,
            "title": title,
            "description": description,
            "item_type": item_type,
            "start_time": start_time,
            "end_time": end_time,
            "recurrence": recurrence,
            "priority": priority,
            "status": status,
            "assigned_to": assigned_to,
            "related_entity_type": related_entity_type,
            "related_entity_id": related_entity_id,
            "conflict_detected": conflict_detected,
            "conflict_reason": conflict_reason,
            "metadata": metadata,
            "created_at": now
        }

    def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates an existing schedule item."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM universal_schedules WHERE schedule_id = ? AND tenant_id = ?",
                (schedule_id, self.tenant_id)
            ).fetchone()
            if not row:
                return None

            company_id = updates.get("company_id", row["company_id"])
            title = updates.get("title", row["title"])
            description = updates.get("description", row["description"])
            item_type = updates.get("item_type", row["item_type"])
            start_time = float(updates.get("start_time", row["start_time"]))
            end_time = float(updates.get("end_time", row["end_time"] or start_time + 3600))
            recurrence = updates.get("recurrence", row["recurrence"])
            priority = updates.get("priority", row["priority"])
            status = updates.get("status", row["status"])
            assigned_to = updates.get("assigned_to", row["assigned_to"])
            related_entity_type = updates.get("related_entity_type", row["related_entity_type"])
            related_entity_id = updates.get("related_entity_id", row["related_entity_id"])
            
            existing_meta = json.loads(row["metadata"]) if row["metadata"] else {}
            new_meta = updates.get("metadata", existing_meta)

            conflict_detected, conflict_reason = self._check_conflicts(company_id, start_time, end_time, schedule_id)

            conn.execute(
                """
                UPDATE universal_schedules SET
                    company_id = ?, title = ?, description = ?, item_type = ?,
                    start_time = ?, end_time = ?, recurrence = ?, priority = ?,
                    status = ?, assigned_to = ?, related_entity_type = ?,
                    related_entity_id = ?, conflict_detected = ?, conflict_reason = ?,
                    metadata = ?
                WHERE schedule_id = ? AND tenant_id = ?
                """,
                (
                    company_id, title, description, item_type,
                    start_time, end_time, recurrence, priority,
                    status, assigned_to, related_entity_type,
                    related_entity_id, 1 if conflict_detected else 0, conflict_reason,
                    json.dumps(new_meta), schedule_id, self.tenant_id
                )
            )
            conn.commit()

        return self.get_schedule(schedule_id)

    def delete_schedule(self, schedule_id: str) -> bool:
        """Deletes a schedule item."""
        with db.get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM universal_schedules WHERE schedule_id = ? AND tenant_id = ?",
                (schedule_id, self.tenant_id)
            )
            conn.commit()
            return cur.rowcount > 0

    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM universal_schedules WHERE schedule_id = ? AND tenant_id = ?",
                (schedule_id, self.tenant_id)
            ).fetchone()
            if not r:
                return None
            meta = {}
            if r["metadata"]:
                try:
                    meta = json.loads(r["metadata"])
                except Exception:
                    meta = {}
            return {
                "schedule_id": r["schedule_id"],
                "tenant_id": r["tenant_id"],
                "company_id": r["company_id"],
                "title": r["title"],
                "description": r["description"] or "",
                "item_type": r["item_type"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "recurrence": r["recurrence"],
                "priority": r["priority"],
                "status": r["status"],
                "assigned_to": r["assigned_to"],
                "related_entity_type": r["related_entity_type"],
                "related_entity_id": r["related_entity_id"],
                "conflict_detected": bool(r["conflict_detected"]),
                "conflict_reason": r["conflict_reason"],
                "metadata": meta,
                "created_at": r["created_at"]
            }

    def _check_conflicts(self, company_id: str, start_time: float, end_time: float, current_id: Optional[str] = None) -> tuple:
        """Detects time-window collision with other high-priority or meeting schedule items."""
        with db.get_connection() as conn:
            query = """
                SELECT schedule_id, title, item_type, priority FROM universal_schedules
                WHERE tenant_id = ? AND status != 'CANCELLED'
                  AND start_time < ? AND end_time > ?
            """
            params: List[Any] = [self.tenant_id, end_time, start_time]
            if current_id:
                query += " AND schedule_id != ?"
                params.append(current_id)

            rows = conn.execute(query, params).fetchall()

        if rows:
            conflicting_titles = [f"{r['title']} ({r['item_type']})" for r in rows[:2]]
            reason = f"Time window overlap with: {', '.join(conflicting_titles)}"
            return True, reason

        return False, None

    def parse_natural_language(self, text: str, company_id: str = "comp_primary") -> Dict[str, Any]:
        """Parses natural language input into a schedule proposal."""
        raw = text.strip()
        now = datetime.now()
        start_dt = now + timedelta(hours=1)
        item_type = "meeting"
        priority = "MEDIUM"

        text_lower = raw.lower()

        # Item Type Detection
        if any(w in text_lower for w in ["milestone", "deliverable"]):
            item_type = "mission_milestone"
        elif any(w in text_lower for w in ["deadline", "due", "cutoff"]):
            item_type = "deadline"
            priority = "HIGH"
        elif any(w in text_lower for w in ["night audit", "process", "workflow", "routine sync", "sync"]):
            item_type = "process_run"
        elif any(w in text_lower for w in ["budget", "financial", "cashflow", "expense"]):
            item_type = "budget_review"
        elif any(w in text_lower for w in ["compliance", "regulatory", "audit"]):
            item_type = "compliance_audit"
        elif any(w in text_lower for w in ["report", "analytics", "digest"]):
            item_type = "report_generation"
        elif any(w in text_lower for w in ["automation", "desktop", "robot", "scraping"]):
            item_type = "desktop_automation"
        elif any(w in text_lower for w in ["customer", "lead", "client", "call"]):
            item_type = "customer_touchpoint"
        elif any(w in text_lower for w in ["strategy", "board", "quarterly", "executive"]):
            item_type = "strategic_review"
            priority = "HIGH"

        # Priority Detection
        if any(w in text_lower for w in ["urgent", "critical", "asap", "emergency"]):
            priority = "URGENT"
        elif any(w in text_lower for w in ["high priority", "important"]):
            priority = "HIGH"

        # Time offsets
        if "tomorrow" in text_lower:
            start_dt = now + timedelta(days=1)
        elif "next week" in text_lower:
            start_dt = now + timedelta(days=7)
        elif "next monday" in text_lower:
            days_ahead = (0 - now.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            start_dt = now + timedelta(days=days_ahead)
        elif "friday" in text_lower:
            days_ahead = (4 - now.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            start_dt = now + timedelta(days=days_ahead)

        # Time of day detection
        hour_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text_lower)
        if hour_match:
            h = int(hour_match.group(1))
            m = int(hour_match.group(2) or 0)
            meridiem = hour_match.group(3)
            if meridiem == "pm" and h < 12:
                h += 12
            elif meridiem == "am" and h == 12:
                h = 0
            start_dt = start_dt.replace(hour=h, minute=m, second=0, microsecond=0)
        else:
            # Default to rounded next hour
            start_dt = start_dt.replace(minute=0, second=0, microsecond=0)

        end_dt = start_dt + timedelta(hours=1)
        start_ts = start_dt.timestamp()
        end_ts = end_dt.timestamp()

        # Clean title
        title = re.sub(r'^(schedule|create|add|set up|plan)\s+', '', raw, flags=re.IGNORECASE).strip()
        if not title:
            title = "Scheduled Operating Item"

        conflict, reason = self._check_conflicts(company_id, start_ts, end_ts)

        return {
            "title": title,
            "company_id": company_id,
            "item_type": item_type,
            "priority": priority,
            "start_time": start_ts,
            "end_time": end_ts,
            "recurrence": "NONE",
            "assigned_to": "AI CEO",
            "conflict_detected": conflict,
            "conflict_reason": reason,
            "interpreted_prompt": raw
        }

    def get_ai_ceo_recommendations(self, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Synthesizes smart schedule recommendations based on pending approvals, missions, and risks."""
        recs = []
        now = time.time()

        with db.get_connection() as conn:
            # 1. Pending Approvals Requiring SLA Scheduling
            app_rows = conn.execute(
                "SELECT request_id, action_desc, risk_level, company_id FROM approvals WHERE status = 'PENDING' LIMIT 3"
            ).fetchall()
            for a in app_rows:
                recs.append({
                    "recommendation_id": f"rec_app_{a['request_id']}",
                    "title": f"Executive Governance Review: {a['action_desc'][:40]}...",
                    "item_type": "approval_deadline",
                    "priority": "HIGH" if a['risk_level'] in ['HIGH', 'CRITICAL'] else "MEDIUM",
                    "suggested_start": now + 7200,
                    "reason": f"Approval request {a['request_id']} has pending owner sign-off.",
                    "company_id": a['company_id']
                })

            # 2. Active Missions Approaching Review
            m_rows = conn.execute(
                "SELECT mission_id, title, company_id FROM missions WHERE status IN ('DISCOVER', 'PLAN') LIMIT 2"
            ).fetchall()
            for m in m_rows:
                recs.append({
                    "recommendation_id": f"rec_mis_{m['mission_id']}",
                    "title": f"Milestone Sync: {m['title']}",
                    "item_type": "mission_milestone",
                    "priority": "MEDIUM",
                    "suggested_start": now + 86400,
                    "reason": f"Mission {m['mission_id']} is progressing; needs milestone alignment.",
                    "company_id": m['company_id']
                })

        # 3. Always include routine operations check
        recs.append({
            "recommendation_id": f"rec_ops_audit",
            "title": "Universal Daily Operational & Ledger Re-verification",
            "item_type": "process_run",
            "priority": "LOW",
            "suggested_start": now + 43200,
            "reason": "Routine reconciliation for operating consistency.",
            "company_id": company_id or "comp_primary"
        })

        return recs

    def _seed_initial_schedules(self):
        """Seeds realistic initial schedules across companies for immediate productivity."""
        now = time.time()
        # Seed 6 diverse items spanning today, tomorrow, and this week
        seed_items = [
            {
                "title": "Daily AI CEO Executive Briefing & Alignment",
                "description": "Cross-departmental situational awareness with AI CEO, reviewing cash velocity and active missions.",
                "item_type": "meeting",
                "start_time": now + 1800, # In 30 mins
                "end_time": now + 3600,
                "priority": "HIGH",
                "recurrence": "DAILY",
                "assigned_to": "Host & AI CEO",
                "company_id": "comp_primary"
            },
            {
                "title": "Q3 Revenue Pipeline & Margin Review",
                "description": "Reconcile commercial bookings against verified bank deposits and evaluate sales velocity.",
                "item_type": "budget_review",
                "start_time": now + 14400, # In 4 hours
                "end_time": now + 18000,
                "priority": "HIGH",
                "recurrence": "WEEKLY",
                "assigned_to": "CFO Agent",
                "company_id": "comp_primary"
            },
            {
                "title": "Autonomous Night Audit & Ledger Checksum Verification",
                "description": "Background verification across connected PMS/ERP data sources and sandbox integrity.",
                "item_type": "process_run",
                "start_time": now + 43200, # In 12 hours
                "end_time": now + 46800,
                "priority": "MEDIUM",
                "recurrence": "DAILY",
                "assigned_to": "Autonomous Worker",
                "company_id": "comp_primary"
            },
            {
                "title": "High-Value Enterprise Customer Touchpoint",
                "description": "Follow up with qualified leads requesting contract scope expansion.",
                "item_type": "customer_touchpoint",
                "start_time": now + 86400, # Tomorrow
                "end_time": now + 90000,
                "priority": "MEDIUM",
                "recurrence": "NONE",
                "assigned_to": "Commercial Sales Agent",
                "company_id": "comp_primary"
            },
            {
                "title": "Host Node Security & Software Profile Audit",
                "description": "Inspect registered host daemons, browser sessions, and verify credential handles.",
                "item_type": "maintenance",
                "start_time": now + 172800, # In 2 days
                "end_time": now + 176400,
                "priority": "LOW",
                "recurrence": "WEEKLY",
                "assigned_to": "Security Sentry",
                "company_id": "comp_primary"
            },
            {
                "title": "Quarterly Strategic Council & Expansion Roadmap",
                "description": "Executive council debate on capacity utilization and autonomous capability acquisition.",
                "item_type": "strategic_review",
                "start_time": now + 259200, # In 3 days
                "end_time": now + 266400,
                "priority": "URGENT",
                "recurrence": "MONTHLY",
                "assigned_to": "Executive Council",
                "company_id": "comp_primary"
            }
        ]

        for s in seed_items:
            self.create_schedule(s)
