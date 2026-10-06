"""
RoboAssistant Company OS 1.0 — Global Search & Configuration Search Engine
Implements Section 66:
Unified search across companies, employees, departments, missions, reports,
evidence, data sources, hosts, tools, and approvals.
Translates configuration intents (e.g. 'make everything cheaper') into PROPOSED CHANGES.
"""

from typing import Dict, Any, List, Optional
import re
from .db import db

class GlobalSearchEngine:
    @staticmethod
    def search_all(tenant_id: str, query: str) -> Dict[str, Any]:
        q = query.lower().strip()
        results: Dict[str, List[Dict[str, Any]]] = {
            "companies": [],
            "departments": [],
            "employees": [],
            "missions": [],
            "approvals": [],
            "knowledge_facts": [],
            "proposed_configuration_actions": []
        }

        # Check for natural-language configuration intent
        if "cheap" in q or "cost" in q or "save" in q or "limit" in q:
            results["proposed_configuration_actions"].append({
                "action_type": "PROPOSED_CONFIGURATION_CHANGE",
                "title": "Enable Global Cost-Minimization Doctrine",
                "description": "Cap monthly token expenditures and prioritize local/open-source models.",
                "status": "PROPOSED_AWAITING_OWNER_CONFIRMATION",
                "consequential": True
            })

        with db.get_connection() as conn:
            # Search companies
            for r in conn.execute("SELECT company_id, name, industry, status FROM companies WHERE tenant_id = ?", (tenant_id,)).fetchall():
                if q in r["name"].lower() or q in r["industry"].lower() or q in r["status"].lower():
                    results["companies"].append(dict(r))

            # Search departments
            for r in conn.execute("SELECT department_id, company_id, name, budget_limit FROM departments WHERE tenant_id = ?", (tenant_id,)).fetchall():
                if q in r["name"].lower():
                    results["departments"].append(dict(r))

            # Search employees
            for r in conn.execute("SELECT agent_id, role, department, authority_ceiling, working_state FROM employees WHERE tenant_id = ?", (tenant_id,)).fetchall():
                if q in r["role"].lower() or q in r["department"].lower():
                    results["employees"].append(dict(r))

            # Search missions
            for r in conn.execute("SELECT mission_id, prompt, status, current_stage FROM coworker_background_missions WHERE tenant_id = ?", (tenant_id,)).fetchall():
                if q in r["prompt"].lower():
                    results["missions"].append(dict(r))

            # Search approvals
            for r in conn.execute("SELECT request_id, action_desc, reason, risk_level, status FROM approvals WHERE tenant_id = ?", (tenant_id,)).fetchall():
                if q in r["action_desc"].lower() or q in r["reason"].lower():
                    results["approvals"].append(dict(r))

            # Search records
            try:
                for r in conn.execute("SELECT record_id, title, record_type, department, actor_name, amount, currency FROM enterprise_records WHERE tenant_id = ?", (tenant_id,)).fetchall():
                    if q in r["title"].lower() or q in r["actor_name"].lower() or q in r["record_type"].lower():
                        results.setdefault("records", []).append(dict(r))
            except Exception:
                pass

            # Search files
            try:
                for r in conn.execute("SELECT file_id, name, department, category, document_type FROM enterprise_files WHERE tenant_id = ?", (tenant_id,)).fetchall():
                    if q in r["name"].lower() or q in r["category"].lower() or q in r["department"].lower():
                        results.setdefault("files", []).append(dict(r))
            except Exception:
                pass

            # Search reports
            try:
                for r in conn.execute("SELECT report_id, title, report_category, verification_state FROM enterprise_reports WHERE tenant_id = ?", (tenant_id,)).fetchall():
                    if q in r["title"].lower() or q in r["report_category"].lower():
                        results.setdefault("reports", []).append(dict(r))
            except Exception:
                pass

            # Search blueprints
            try:
                for r in conn.execute("SELECT blueprint_id, name, role, department, mission FROM agent_blueprints WHERE tenant_id = ?", (tenant_id,)).fetchall():
                    if q in r["name"].lower() or q in r["role"].lower() or q in r["mission"].lower():
                        results.setdefault("agent_blueprints", []).append(dict(r))
            except Exception:
                pass

        # Build flat ranked items list for topbar Command Palette
        items = []
        for c in results["companies"]:
            items.append({"category": "Companies", "title": c["name"], "subtitle": f"{c.get('industry', 'Operations')} • {c.get('status', 'ACTIVE')}", "route": "/company"})
        for r in results.get("records", []):
            items.append({"category": "Records", "title": r["title"], "subtitle": f"{r['department']} • {r['record_type']} • {r['actor_name']}", "route": "/records"})
        for f in results.get("files", []):
            items.append({"category": "Files", "title": f["name"], "subtitle": f"{f['department']} • {f['category']} • {f['document_type']}", "route": "/files"})
        for rep in results.get("reports", []):
            items.append({"category": "Reports", "title": rep["title"], "subtitle": f"{rep['report_category']} • {rep['verification_state']}", "route": "/reports"})
        for bp in results.get("agent_blueprints", []):
            items.append({"category": "Agents", "title": bp["name"], "subtitle": f"{bp['department']} • {bp['role']}", "route": "/agents"})
        for m in results["missions"]:
            items.append({"category": "Missions", "title": m.get("prompt", m.get("title", "")), "subtitle": f"{m.get('status', '')}", "route": "/missions"})

        total_matches = sum(len(v) for v in results.values())
        return {
            "query": query,
            "tenant_id": tenant_id,
            "total_matches": total_matches,
            "results": results,
            "items": items[:20]
        }
