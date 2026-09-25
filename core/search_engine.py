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
            for r in conn.execute("SELECT mission_id, title, department, status, target_outcome FROM missions WHERE tenant_id = ?", (tenant_id,)).fetchall():
                if q in r["title"].lower() or q in (r["target_outcome"] or "").lower():
                    results["missions"].append(dict(r))

            # Search approvals
            for r in conn.execute("SELECT request_id, action_desc, reason, risk_level, status FROM approvals WHERE tenant_id = ?", (tenant_id,)).fetchall():
                if q in r["action_desc"].lower() or q in r["reason"].lower():
                    results["approvals"].append(dict(r))

            # Search knowledge facts
            for r in conn.execute("SELECT fact_id, category, subject, predicate, object_val, truth_state FROM company_knowledge WHERE tenant_id = ?", (tenant_id,)).fetchall():
                if q in r["predicate"].lower() or q in r["object_val"].lower():
                    results["knowledge_facts"].append(dict(r))

        total_matches = sum(len(v) for v in results.values())
        return {
            "query": query,
            "tenant_id": tenant_id,
            "total_matches": total_matches,
            "results": results
        }
