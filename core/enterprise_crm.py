"""
RoboAssistant Company OS 1.0 — Enterprise CRM & Commercial Pipeline Service
Normalized relational persistence for customer accounts, contacts, and commercial deals.
Strict tenant and company isolation, zero synthetic mock fallbacks.
"""

import time
import uuid
import json
from typing import Dict, Any, List, Optional
from core.db import db

def _parse_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = "".join(ch for ch in val if ch.isdigit() or ch in ".-")
        try:
            return float(cleaned) if cleaned else default
        except Exception:
            return default
    return default

class EnterpriseCrmService:
    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    def list_customers(
        self,
        company_id: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            query = "SELECT * FROM crm_customers WHERE tenant_id = ?"
            params: List[Any] = [self.tenant_id]

            if company_id and company_id != "all":
                query += " AND company_id = ?"
                params.append(company_id)

            if status and status != "ALL":
                query += " AND status = ?"
                params.append(status)

            if tier and tier != "ALL":
                query += " AND tier = ?"
                params.append(tier)

            if search:
                query += " AND (name LIKE ? OR legal_name LIKE ? OR industry LIKE ?)"
                wild = f"%{search}%"
                params.extend([wild, wild, wild])

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()

            customers = []
            for r in rows:
                c = dict(r)
                c["id"] = c.get("customer_id")
                if isinstance(c.get("contacts"), str):
                    try:
                        c["contacts"] = json.loads(c["contacts"])
                    except Exception:
                        c["contacts"] = []
                customers.append(c)
            return customers

    def create_customer(self, company_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        cid = data.get("customer_id") or f"cust_{uuid.uuid4().hex[:8]}"
        name = data.get("name", "").strip()
        if not name:
            raise ValueError("Customer name is required")

        now = time.time()
        contacts = data.get("contacts", [])
        if isinstance(contacts, (list, dict)):
            contacts_json = json.dumps(contacts)
        else:
            contacts_json = "[]"

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO crm_customers (
                    customer_id, tenant_id, company_id, name, legal_name, tier,
                    industry, status, health_score, arr, ltv, gstin, address,
                    sla_level, renewal_date, assigned_agent, contacts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    self.tenant_id,
                    company_id,
                    name,
                    data.get("legal_name", name),
                    data.get("tier", "STANDARD"),
                    data.get("industry", "Enterprise"),
                    data.get("status", "ACTIVE"),
                    _parse_float(data.get("health_score", 100.0)),
                    _parse_float(data.get("arr", 0.0)),
                    _parse_float(data.get("ltv", 0.0)),
                    data.get("gstin", ""),
                    data.get("address", ""),
                    data.get("sla_level", "Standard 99.9%"),
                    data.get("renewal_date", ""),
                    data.get("assigned_agent", "Account Executive"),
                    contacts_json,
                    now,
                    now
                )
            )
            conn.commit()

        c = self.get_customer(cid)
        if c:
            c["success"] = True
        return c or {"customer_id": cid, "success": True}

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM crm_customers WHERE customer_id = ? AND tenant_id = ?",
                (customer_id, self.tenant_id)
            ).fetchone()
            if not row:
                return None
            c = dict(row)
            c["id"] = c.get("customer_id")
            if isinstance(c.get("contacts"), str):
                try:
                    c["contacts"] = json.loads(c["contacts"])
                except Exception:
                    c["contacts"] = []

            # Attach deals for this customer (strictly scoped to this tenant)
            deals_rows = conn.execute(
                "SELECT * FROM crm_deals WHERE customer_id = ? AND tenant_id = ? ORDER BY created_at DESC",
                (customer_id, self.tenant_id)
            ).fetchall()
            c["deals"] = []
            for d in deals_rows:
                dd = dict(d)
                dd["id"] = dd.get("deal_id")
                c["deals"].append(dd)
            return c

    def update_customer(self, customer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates customer attributes strictly within tenant boundary."""
        now = time.time()
        with db.get_connection() as conn:
            # Check existence and ownership
            existing = conn.execute(
                "SELECT customer_id FROM crm_customers WHERE customer_id = ? AND tenant_id = ?",
                (customer_id, self.tenant_id)
            ).fetchone()
            if not existing:
                raise KeyError(f"Customer '{customer_id}' not found in tenant '{self.tenant_id}'")

            updates = []
            params = []
            for field in ["name", "legal_name", "tier", "industry", "status", "gstin", "address", "sla_level", "renewal_date", "assigned_agent"]:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])
            for num_field in ["health_score", "arr", "ltv"]:
                if num_field in data:
                    updates.append(f"{num_field} = ?")
                    params.append(_parse_float(data[num_field]))
            if "contacts" in data:
                updates.append("contacts = ?")
                params.append(json.dumps(data["contacts"]) if isinstance(data["contacts"], (list, dict)) else "[]")

            if updates:
                updates.append("updated_at = ?")
                params.append(now)
                params.extend([customer_id, self.tenant_id])
                query = f"UPDATE crm_customers SET {', '.join(updates)} WHERE customer_id = ? AND tenant_id = ?"
                conn.execute(query, params)
                conn.commit()

        return self.get_customer(customer_id) or {"customer_id": customer_id, "updated": True}

    def delete_customer(self, customer_id: str) -> bool:
        """Deletes customer and associated deals, strictly within tenant boundary."""
        with db.get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM crm_customers WHERE customer_id = ? AND tenant_id = ?",
                (customer_id, self.tenant_id)
            )
            deleted = cur.rowcount > 0
            if deleted:
                conn.execute(
                    "DELETE FROM crm_deals WHERE customer_id = ? AND tenant_id = ?",
                    (customer_id, self.tenant_id)
                )
            conn.commit()
        return deleted

    def list_deals(self, company_id: Optional[str] = None, stage: Optional[str] = None) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            query = "SELECT * FROM crm_deals WHERE tenant_id = ?"
            params: List[Any] = [self.tenant_id]

            if company_id and company_id != "all":
                query += " AND company_id = ?"
                params.append(company_id)

            if stage and stage != "ALL":
                query += " AND stage = ?"
                params.append(stage)

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
            deals = []
            for r in rows:
                d = dict(r)
                d["id"] = d.get("deal_id")
                deals.append(d)
            return deals

    def get_deal(self, deal_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single deal strictly scoped to tenant."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM crm_deals WHERE deal_id = ? AND tenant_id = ?",
                (deal_id, self.tenant_id)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["id"] = d.get("deal_id")
            return d

    def create_deal(self, company_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        deal_id = data.get("deal_id") or f"deal_{uuid.uuid4().hex[:8]}"
        title = data.get("title", "").strip()
        if not title:
            raise ValueError("Deal title is required")

        # Object Ownership Check: Verify referenced customer belongs to this tenant
        cust_id = data.get("customer_id")
        if cust_id:
            cust = self.get_customer(cust_id)
            if not cust:
                raise ValueError(f"Direct Object Access Violation: Customer '{cust_id}' not found in current organization")

        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO crm_deals (
                    deal_id, tenant_id, company_id, customer_id, title, stage,
                    value, probability, closing_date, owner, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deal_id,
                    self.tenant_id,
                    company_id,
                    cust_id,
                    title,
                    data.get("stage", "discovery"),
                    _parse_float(data.get("value", 0.0)),
                    _parse_float(data.get("probability", 0.5)),
                    data.get("closing_date", ""),
                    data.get("owner", "Sales Lead"),
                    now,
                    now
                )
            )
            conn.commit()

        return {"deal_id": deal_id, "success": True}

    def update_deal_stage(self, deal_id: str, stage: str) -> Dict[str, Any]:
        """Updates deal stage, strictly scoped to tenant."""
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.execute(
                "UPDATE crm_deals SET stage = ?, updated_at = ? WHERE deal_id = ? AND tenant_id = ?",
                (stage, now, deal_id, self.tenant_id)
            )
            updated = cur.rowcount > 0
            conn.commit()
        return {"deal_id": deal_id, "stage": stage, "updated_at": now, "updated": updated}

    def update_deal(self, deal_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates deal attributes, strictly validating tenant ownership and referenced customer."""
        now = time.time()
        with db.get_connection() as conn:
            existing = conn.execute(
                "SELECT deal_id, customer_id FROM crm_deals WHERE deal_id = ? AND tenant_id = ?",
                (deal_id, self.tenant_id)
            ).fetchone()
            if not existing:
                raise KeyError(f"Deal '{deal_id}' not found in tenant '{self.tenant_id}'")

            if "customer_id" in data and data["customer_id"]:
                new_cust_id = data["customer_id"]
                cust = self.get_customer(new_cust_id)
                if not cust:
                    raise ValueError(f"Direct Object Access Violation: Customer '{new_cust_id}' not found in current organization")

            updates = []
            params = []
            for field in ["title", "stage", "closing_date", "owner", "customer_id"]:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])
            for num_field in ["value", "probability"]:
                if num_field in data:
                    updates.append(f"{num_field} = ?")
                    params.append(_parse_float(data[num_field]))

            if updates:
                updates.append("updated_at = ?")
                params.append(now)
                params.extend([deal_id, self.tenant_id])
                query = f"UPDATE crm_deals SET {', '.join(updates)} WHERE deal_id = ? AND tenant_id = ?"
                conn.execute(query, params)
                conn.commit()

        return self.get_deal(deal_id) or {"deal_id": deal_id, "updated": True}

    def delete_deal(self, deal_id: str) -> bool:
        """Deletes deal, verifying tenant ownership."""
        with db.get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM crm_deals WHERE deal_id = ? AND tenant_id = ?",
                (deal_id, self.tenant_id)
            )
            deleted = cur.rowcount > 0
            conn.commit()
        return deleted
