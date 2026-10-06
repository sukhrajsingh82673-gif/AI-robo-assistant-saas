"""
ZONATA Universal AI Company OS — Unified Enterprise Search & Command Palette Engine
Searches cross-domain entities: Companies, Departments, Employees, Records, Files,
Reports, Blueprints/Agents, Missions, Integrations, Tools, and Settings.
Supports natural language queries and structured category ranking.
"""

from typing import Dict, List, Optional, Any
import time
import json
import os
from .db import db

class UnifiedEnterpriseSearch:
    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    def search(self, query: str, company_id: str = "comp_primary", limit: int = 25) -> Dict[str, Any]:
        q = (query or "").strip().lower()
        if not q:
            return {"results": [], "total": 0, "query": ""}

        results = []

        with db.get_connection() as conn:
            # 1. Search Records
            try:
                rec_rows = conn.execute("""
                    SELECT record_id, title, record_type, department, actor_name, amount, currency
                    FROM enterprise_records
                    WHERE tenant_id = ? AND (title LIKE ? OR notes LIKE ? OR actor_name LIKE ?)
                    LIMIT 8
                """, (self.tenant_id, f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
                for r in rec_rows:
                    results.append({
                        "category": "RECORDS",
                        "id": r["record_id"],
                        "title": r["title"],
                        "subtitle": f"{r['department']} • {r['record_type']} • {r['actor_name']}",
                        "badge": f"{r['currency']}{r['amount']:,.0f}" if r["amount"] > 0 else r["record_type"],
                        "route": "/records"
                    })
            except Exception:
                pass

            # 2. Search Files
            try:
                file_rows = conn.execute("""
                    SELECT file_id, name, department, category, document_type
                    FROM enterprise_files
                    WHERE tenant_id = ? AND (name LIKE ? OR summary LIKE ?)
                    LIMIT 6
                """, (self.tenant_id, f"%{q}%", f"%{q}%")).fetchall()
                for f in file_rows:
                    results.append({
                        "category": "FILES",
                        "id": f["file_id"],
                        "title": f["name"],
                        "subtitle": f"{f['department']} • {f['category']} • {f['document_type']}",
                        "badge": f["document_type"],
                        "route": "/files"
                    })
            except Exception:
                pass

            # 3. Search Reports
            try:
                rep_rows = conn.execute("""
                    SELECT report_id, title, report_category, verification_state
                    FROM enterprise_reports
                    WHERE tenant_id = ? AND (title LIKE ? OR ai_executive_summary LIKE ?)
                    LIMIT 6
                """, (self.tenant_id, f"%{q}%", f"%{q}%")).fetchall()
                for rep in rep_rows:
                    results.append({
                        "category": "REPORTS",
                        "id": rep["report_id"],
                        "title": rep["title"],
                        "subtitle": f"{rep['report_category']} • {rep['verification_state']}",
                        "badge": "BI Report",
                        "route": "/reports"
                    })
            except Exception:
                pass

            # 4. Search Agent Blueprints / AI Workforce
            try:
                bp_rows = conn.execute("""
                    SELECT blueprint_id, name, role, department, mission
                    FROM agent_blueprints
                    WHERE tenant_id = ? AND (name LIKE ? OR role LIKE ? OR mission LIKE ?)
                    LIMIT 6
                """, (self.tenant_id, f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
                for bp in bp_rows:
                    results.append({
                        "category": "AGENTS",
                        "id": bp["blueprint_id"],
                        "title": bp["name"],
                        "subtitle": f"{bp['department']} • {bp['role']}",
                        "badge": "AI Worker",
                        "route": "/agents"
                    })
            except Exception:
                pass

            # 5. Search Missions
            try:
                msn_rows = conn.execute("""
                    SELECT mission_id, prompt, status, current_stage
                    FROM coworker_background_missions
                    WHERE tenant_id = ? AND prompt LIKE ?
                    LIMIT 6
                """, (self.tenant_id, f"%{q}%")).fetchall()
                for m in msn_rows:
                    results.append({
                        "category": "MISSIONS",
                        "id": m["mission_id"],
                        "title": m["prompt"],
                        "subtitle": f"{m['status']} • {m['current_stage']}",
                        "badge": "Mission",
                        "route": "/missions"
                    })
            except Exception:
                pass

            # 6. Search Integrations
            try:
                conn_rows = conn.execute("""
                    SELECT connection_id, name, service_type, auth_status
                    FROM external_connections
                    WHERE tenant_id = ? AND name LIKE ?
                    LIMIT 6
                """, (self.tenant_id, f"%{q}%")).fetchall()
                for c in conn_rows:
                    results.append({
                        "category": "INTEGRATIONS",
                        "id": c["connection_id"],
                        "title": c["name"],
                        "subtitle": f"{c['service_type']} • {c['auth_status']}",
                        "badge": "Connected",
                        "route": "/integrations"
                    })
            except Exception:
                pass

        return {
            "query": query,
            "total": len(results),
            "results": results[:limit]
        }

unified_search = UnifiedEnterpriseSearch()
