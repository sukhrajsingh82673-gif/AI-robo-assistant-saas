"""Tenant-scoped company lifecycle service.

Owns the company record (fields, status transitions), drafts, connection
records and the protected deletion state machine. It is deliberately separate
from ``core.portfolio.CompanyPortfolioManager`` so the operating context path
keeps working unchanged; after a mutation we refresh the cached portfolio so
the rest of the app sees the new company immediately.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from core.auth import verify_password
from core.company_setup import audit
from core.company_setup.permissions import (
    PermissionDenied,
    Principal,
    assert_can_create,
    assert_can_delete,
    assert_can_draft,
    assert_can_edit,
    assert_can_submit,
    assert_can_view,
    can_manage_connections,
)
from core.company_setup.schema import ensure_schema
from core.company_setup.status import (
    CompanyStatus,
    InvalidTransition,
    normalize_status,
    validate_transition,
)
from core.db import db

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
URL_RE = re.compile(r"^https?://[^\s<>\"']{3,2048}$", re.IGNORECASE)
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
PERIODS = {"DAILY", "WEEKLY", "MONTHLY", "QUARTERLY", "ANNUAL", "ONE_TIME"}
COMPANY_TYPES = {"NEW", "EXISTING"}

MAX_NAME = 160
MAX_TITLE = 200
MAX_DESCRIPTION = 20000
MAX_TEXT = 2000


BUILD_PHASES_NEW = [
    "INTAKE",
    "RESEARCH",
    "PLAN",
    "BUILD",
    "LEGAL_PACK",
    "VERIFY",
    "OPERATIONAL",
]
BUILD_PHASES_EXISTING = [
    "CONNECT_VERIFY",
    "STUDY",
    "DIAGNOSE",
    "PLAN",
    "ACT",
    "OPERATIONAL",
]


class CompanySetupError(Exception):
    """Domain error carrying an HTTP status and a stable machine code."""

    def __init__(self, code: str, message: str, status: int = 400, detail: Optional[Any] = None):
        self.code = code
        self.message = message
        self.status = status
        self.detail = detail
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        payload = {"error": self.message, "code": self.code}
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload


def _now() -> float:
    return time.time()


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _json_dump(value: Any) -> str:
    return json.dumps(value if value is not None else {})


def _row_to_dict(row: Any) -> Dict[str, Any]:
    if row is None:
        return {}
    try:
        return {key: row[key] for key in row.keys()}
    except Exception:
        return dict(row)


def _clean_text(value: Any, max_len: int = MAX_TEXT, strip_angles: bool = False) -> str:
    text = str(value or "")
    text = CONTROL_CHARS_RE.sub("", text).strip()
    if strip_angles:
        text = text.replace("<", "").replace(">", "")
    return text[:max_len]


def _validate_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value or ""))


class CompanySetupService:
    """All company setup operations for a single tenant."""

    def __init__(self, tenant_id: str):
        if not tenant_id:
            raise CompanySetupError("TENANT_REQUIRED", "tenant_id is required", status=401)
        self.tenant_id = tenant_id
        ensure_schema()

    # ------------------------------------------------------------------ utils
    def _granted(self, company_id: str, user_id: str) -> bool:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM company_admin_grants WHERE tenant_id = ? AND company_id = ? AND user_id = ?",
                (self.tenant_id, company_id, user_id),
            ).fetchone()
        return bool(row)

    def _refresh_portfolio(self) -> None:
        """Refresh the cached portfolio so other screens see the change.

        Only refreshes a runtime that is already loaded; importing the tenancy
        module just to update a cache would pull in the whole executive stack.
        """
        try:
            import sys

            module = sys.modules.get("core.tenancy")
            if not module:
                return
            for key, runtime in list(getattr(module, "_REGISTRY", {}).items()):
                if key.startswith(f"{self.tenant_id}::"):
                    try:
                        runtime.portfolio._load_existing_from_db()
                    except Exception:
                        pass
        except Exception:
            pass

    def _fetch_company_row(self, company_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        if not company_id:
            return None
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM companies WHERE company_id = ? AND tenant_id = ?",
                (company_id, self.tenant_id),
            ).fetchone()
        record = _row_to_dict(row)
        if not record:
            return None
        status = normalize_status(record.get("status"))
        if status == CompanyStatus.DELETED and not include_deleted:
            return None
        record["status"] = status
        return record

    def _require_company(self, company_id: str, include_deleted: bool = False) -> Dict[str, Any]:
        record = self._fetch_company_row(company_id, include_deleted=include_deleted)
        if not record:
            # A company in another tenant is indistinguishable from a missing one.
            raise CompanySetupError("COMPANY_NOT_FOUND", "Company not found", status=404)
        return record

    def require_company(self, principal: Principal, company_id: str, include_deleted: bool = False) -> Dict[str, Any]:
        """Public, permission-checked company read used by thin routes."""
        assert_can_view(principal, self.tenant_id)
        return self._require_company(company_id, include_deleted=include_deleted)

    # --------------------------------------------------------------- mapping
    def _serialize(self, record: Dict[str, Any]) -> Dict[str, Any]:
        status = normalize_status(record.get("status"))
        revenue_amount = record.get("revenue_amount")
        if revenue_amount is None:
            revenue_amount = record.get("revenue")
        company = {
            "id": record.get("company_id"),
            "tenant_id": record.get("tenant_id"),
            "type": record.get("company_type"),
            "name": record.get("name"),
            "title": record.get("title"),
            "description": record.get("description"),
            "owner": {
                "name": record.get("owner_name"),
                "email": record.get("owner_email"),
                "role": record.get("owner_role"),
            },
            "country": record.get("country"),
            "industry": record.get("industry"),
            "status": status,
            "status_label": CompanyStatus.LABELS.get(status, status),
            "currency": record.get("currency"),
            "timezone": record.get("timezone"),
            "website": record.get("website"),
            "business_model": record.get("business_model"),
            "target_customers": record.get("target_customers"),
            "budget": {
                "amount": record.get("budget_amount"),
                "currency": record.get("budget_currency"),
            },
            "timeline": record.get("timeline"),
            "setup_notes": record.get("setup_notes"),
            "assets": _json_load(record.get("assets"), []),
            "revenue": {
                "amount": revenue_amount or 0.0,
                "currency": record.get("revenue_currency") or record.get("currency"),
                "period": record.get("revenue_period"),
            },
            "readiness_score": record.get("readiness_score"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at") or record.get("created_at"),
            "created_by": record.get("created_by"),
            "deleted_at": record.get("deleted_at"),
        }
        return company

    # -------------------------------------------------------------- listing
    def list_companies(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        company_type: Optional[str] = None,
        query: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        safe_page = max(1, int(page or 1))
        safe_size = max(1, min(int(page_size or 20), 100))
        offset = (safe_page - 1) * safe_size

        clauses = ["tenant_id = ?"]
        params: List[Any] = [self.tenant_id]
        if status:
            normalized = normalize_status(status)
            if normalized == CompanyStatus.NEEDS_ATTENTION:
                clauses.append("status IN (?, ?)")
                params.extend([CompanyStatus.NEEDS_ATTENTION, "ATTENTION"])
            else:
                clauses.append("status = ?")
                params.append(normalized)
        elif not include_deleted:
            clauses.append("status <> ?")
            params.append(CompanyStatus.DELETED)
        if company_type:
            clauses.append("company_type = ?")
            params.append(str(company_type).upper())
        if query:
            like = f"%{_clean_text(query, 120).lower()}%"
            clauses.append(
                "(lower(name) LIKE ? OR lower(coalesce(title, '')) LIKE ? OR lower(coalesce(description, '')) LIKE ?)"
            )
            params.extend([like, like, like])

        where = " AND ".join(clauses)
        with db.get_connection() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS n FROM companies WHERE {where}", tuple(params)
            ).fetchone()
            rows = conn.execute(
                f"SELECT * FROM companies WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                tuple(params + [safe_size, offset]),
            ).fetchall()
        total = int(total_row["n"] if total_row else 0)
        items = [self._serialize(_row_to_dict(r)) for r in rows]
        return {
            "companies": items,
            "total": total,
            "page": safe_page,
            "page_size": safe_size,
            "has_more": offset + len(items) < total,
        }

    def get_company(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        assert_can_view(principal, self.tenant_id)
        record = self._require_company(company_id)
        company = self._serialize(record)
        company["permissions"] = self._permissions_for(principal, company_id)
        company["build"] = self.get_build(company_id)
        company["deletion"] = self.get_deletion(company_id)
        return company

    def _permissions_for(self, principal: Principal, company_id: str) -> Dict[str, bool]:
        granted = self._granted(company_id, principal.user_id)
        from core.company_setup import permissions as perms

        return {
            "view": perms.can_view(principal),
            "edit": perms.can_edit(principal, granted),
            "submit": perms.can_submit(principal, granted),
            "delete": perms.can_delete(principal, granted),
            "manage_connections": perms.can_manage_connections(principal, granted),
            "manage_settings": perms.can_manage_settings(principal),
        }

    # -------------------------------------------------------------- creation
    def _validate_company_payload(
        self,
        payload: Dict[str, Any],
        *,
        require_complete: bool,
        company_type: str,
    ) -> Dict[str, Any]:
        errors: List[Dict[str, str]] = []
        clean: Dict[str, Any] = {}

        def add_error(field: str, code: str, message: str) -> None:
            errors.append({"field": field, "code": code, "message": message})

        name = _clean_text(payload.get("name"), MAX_NAME, strip_angles=True)
        if not name:
            if require_complete:
                add_error("name", "REQUIRED", "Company name is required")
        elif len(name) < 2:
            add_error("name", "TOO_SHORT", "Company name must be at least 2 characters")
        clean["name"] = name

        title = _clean_text(payload.get("title"), MAX_TITLE, strip_angles=True)
        if require_complete and not title:
            add_error("title", "REQUIRED", "A one-line title is required")
        clean["title"] = title

        description = _clean_text(payload.get("description"), MAX_DESCRIPTION)
        if require_complete:
            if not description:
                add_error("description", "REQUIRED", "A description is required")
            elif len(description) < 20:
                add_error("description", "TOO_SHORT", "Please describe the company in at least 20 characters")
        clean["description"] = description

        owner = payload.get("owner") if isinstance(payload.get("owner"), dict) else {}
        owner_name = _clean_text(owner.get("name") or payload.get("owner_name"), MAX_NAME, strip_angles=True)
        owner_email = _clean_text(owner.get("email") or payload.get("owner_email"), 254)
        owner_role = _clean_text(owner.get("role") or payload.get("owner_role"), 120, strip_angles=True)
        if require_complete:
            if not owner_name:
                add_error("owner.name", "REQUIRED", "Your name is required")
            if owner_email and not _validate_email(owner_email):
                add_error("owner.email", "INVALID_EMAIL", "Enter a valid email address")
        elif owner_email and not _validate_email(owner_email):
            add_error("owner.email", "INVALID_EMAIL", "Enter a valid email address")
        clean["owner_name"] = owner_name
        clean["owner_email"] = owner_email
        clean["owner_role"] = owner_role

        country = _clean_text(payload.get("country"), 80, strip_angles=True).upper()
        industry = _clean_text(payload.get("industry"), 120, strip_angles=True)
        if require_complete:
            if not country:
                add_error("country", "REQUIRED", "Country is required")
            if not industry:
                add_error("industry", "REQUIRED", "Industry is required")
        clean["country"] = country or "IN"
        clean["industry"] = industry or "General Business"

        website = _clean_text(payload.get("website"), 2048)
        if website:
            if not URL_RE.match(website):
                add_error("website", "INVALID_URL", "Website must start with http:// or https://")
            elif not website.lower().startswith("http://") and not website.lower().startswith("https://"):
                add_error("website", "INVALID_URL", "Website must start with http:// or https://")
        clean["website"] = website

        business_model = _clean_text(payload.get("business_model"), 4000)
        clean["business_model"] = business_model

        target_customers = _clean_text(payload.get("target_customers"), 500)
        clean["target_customers"] = target_customers

        timeline = _clean_text(payload.get("timeline"), 120, strip_angles=True)
        clean["timeline"] = timeline

        setup_notes = _clean_text(payload.get("setup_notes"), 4000)
        clean["setup_notes"] = setup_notes

        budget = payload.get("budget") if isinstance(payload.get("budget"), dict) else {}
        budget_amount: Optional[float] = None
        budget_raw = budget.get("amount", payload.get("budget_amount"))
        if budget_raw not in (None, ""):
            try:
                budget_amount = float(budget_raw)
                if budget_amount < 0:
                    add_error("budget.amount", "INVALID_AMOUNT", "Budget cannot be negative")
            except (TypeError, ValueError):
                add_error("budget.amount", "INVALID_AMOUNT", "Budget must be a number")
        budget_currency = _clean_text(
            budget.get("currency") or payload.get("budget_currency") or payload.get("currency"), 8
        ).upper()
        if budget_currency and len(budget_currency) != 3:
            add_error("budget.currency", "INVALID_CURRENCY", "Use a 3-letter currency code such as INR or USD")
        clean["budget_amount"] = budget_amount
        clean["budget_currency"] = budget_currency

        assets_raw = payload.get("assets")
        assets: List[str] = []
        if isinstance(assets_raw, str):
            stripped = assets_raw.strip()
            if stripped.startswith("["):
                try:
                    assets_raw = json.loads(stripped)
                except (TypeError, ValueError):
                    assets_raw = []
            else:
                assets_raw = [part.strip() for part in stripped.split(",") if part.strip()]
        if isinstance(assets_raw, (list, tuple)):
            for item in list(assets_raw)[:5]:
                url = _clean_text(item, 2048)
                if not url:
                    continue
                if not URL_RE.match(url):
                    add_error("assets", "INVALID_URL", "Each asset link must start with http:// or https://")
                    continue
                assets.append(url)
        clean["assets"] = assets

        revenue = payload.get("revenue") if isinstance(payload.get("revenue"), dict) else {}
        amount_raw = revenue.get("amount", payload.get("revenue_amount"))
        amount: Optional[float] = None
        if amount_raw not in (None, ""):
            try:
                amount = float(amount_raw)
                if amount < 0:
                    add_error("revenue.amount", "INVALID_AMOUNT", "Revenue cannot be negative")
            except (TypeError, ValueError):
                add_error("revenue.amount", "INVALID_AMOUNT", "Revenue must be a number")
        elif require_complete and company_type == "EXISTING":
            add_error("revenue.amount", "REQUIRED", "Revenue amount is required")

        currency = _clean_text(
            revenue.get("currency") or payload.get("revenue_currency") or payload.get("currency"), 8
        ).upper()
        if currency and len(currency) != 3:
            add_error("revenue.currency", "INVALID_CURRENCY", "Use a 3-letter currency code such as INR or USD")
        period = _clean_text(revenue.get("period") or payload.get("revenue_period"), 20).upper()
        if period and period not in PERIODS:
            add_error("revenue.period", "INVALID_PERIOD", "Revenue period must be one of DAILY, WEEKLY, MONTHLY, QUARTERLY, ANNUAL, ONE_TIME")
        if require_complete and company_type == "EXISTING":
            if not currency:
                add_error("revenue.currency", "REQUIRED", "Revenue currency is required")
            if not period:
                add_error("revenue.period", "REQUIRED", "Revenue period is required")

        if require_complete and company_type == "EXISTING" and not business_model:
            add_error("business_model", "REQUIRED", "Describe what the company does and how it works")
        if require_complete and company_type == "EXISTING" and not owner_role:
            add_error("owner.role", "REQUIRED", "Your role in the company is required")

        clean.update(
            {
                "revenue_amount": amount,
                "revenue_currency": currency,
                "revenue_period": period,
            }
        )

        timezone = _clean_text(payload.get("timezone"), 80, strip_angles=True)
        clean["timezone"] = timezone
        return {"values": clean, "errors": errors}

    def _duplicate(self, name: str, exclude_company_id: Optional[str] = None) -> Optional[str]:
        if not name:
            return None
        query = (
            "SELECT company_id FROM companies WHERE tenant_id = ? "
            "AND lower(trim(name)) = lower(trim(?)) AND status <> 'DELETED'"
        )
        params: List[Any] = [self.tenant_id, name]
        if exclude_company_id:
            query += " AND company_id <> ?"
            params.append(exclude_company_id)
        with db.get_connection() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
        return row["company_id"] if row else None

    def create_company(self, principal: Principal, payload: Dict[str, Any]) -> Dict[str, Any]:
        assert_can_create(principal, self.tenant_id)
        company_type = str(payload.get("type") or payload.get("company_type") or "NEW").upper()
        if company_type not in COMPANY_TYPES:
            raise CompanySetupError("INVALID_COMPANY_TYPE", "Company type must be NEW or EXISTING")
        # A create call always starts as a draft; submitting is a separate action.
        validated = self._validate_company_payload(payload, require_complete=False, company_type=company_type)
        values = validated["values"]
        errors = validated["errors"]

        if values.get("name"):
            duplicate = self._duplicate(values["name"])
            if duplicate and not payload.get("allow_duplicate"):
                raise CompanySetupError(
                    "DUPLICATE_COMPANY_NAME",
                    "A company with this name already exists in your organisation",
                    status=409,
                    detail={"duplicate_of": duplicate, "allow_duplicate": True},
                )
        if errors:
            raise CompanySetupError("VALIDATION_FAILED", "Please fix the highlighted fields", status=422, detail=errors)

        company_id = f"comp_{uuid.uuid4().hex[:12]}"
        now = _now()
        currency = values.get("revenue_currency") or "INR"
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO companies (
                    company_id, tenant_id, name, country, industry, company_type, status,
                    currency, timezone, revenue, cost, contribution, understanding_pct,
                    operating_rules, baseline_summary, created_at,
                    title, description, owner_name, owner_email, owner_role, created_by,
                    updated_at, website, business_model, revenue_amount, revenue_currency,
                    revenue_period, readiness_score, target_customers, budget_amount,
                    budget_currency, timeline, setup_notes, assets
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    self.tenant_id,
                    values.get("name") or "Untitled company",
                    values.get("country") or "IN",
                    values.get("industry") or "General Business",
                    company_type,
                    CompanyStatus.DRAFT,
                    currency,
                    values.get("timezone") or "Asia/Kolkata",
                    values.get("revenue_amount") or 0.0,
                    0.0,
                    0.0,
                    0.0,
                    _json_dump([]),
                    None,
                    now,
                    values.get("title") or "",
                    values.get("description") or "",
                    values.get("owner_name") or "",
                    values.get("owner_email") or "",
                    values.get("owner_role") or "",
                    principal.user_id,
                    now,
                    values.get("website") or "",
                    values.get("business_model") or "",
                    values.get("revenue_amount"),
                    values.get("revenue_currency") or "",
                    values.get("revenue_period") or "",
                    0.0,
                    values.get("target_customers") or "",
                    values.get("budget_amount"),
                    values.get("budget_currency") or "",
                    values.get("timeline") or "",
                    values.get("setup_notes") or "",
                    _json_dump(values.get("assets") or []),
                ),
            )
            conn.commit()

        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.created",
            {"type": company_type, "name": values.get("name")},
        )
        self._refresh_portfolio()
        return self.get_company(principal, company_id)

    # ---------------------------------------------------------------- update
    _UPDATABLE = {
        "name",
        "title",
        "description",
        "country",
        "industry",
        "website",
        "business_model",
        "currency",
        "timezone",
        "readiness_score",
        "target_customers",
        "budget",
        "timeline",
        "setup_notes",
        "assets",
    }

    def update_company(self, principal: Principal, company_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        assert_can_edit(principal, self.tenant_id, granted=granted)

        if str(payload.get("company_type") or payload.get("type") or "").upper() not in ("", record["company_type"]):
            raise CompanySetupError("COMPANY_TYPE_IMMUTABLE", "Company type cannot be changed after creation")

        merged = dict(record)
        if isinstance(payload.get("owner"), dict):
            merged["owner"] = payload["owner"]
        if isinstance(payload.get("revenue"), dict):
            merged["revenue"] = payload["revenue"]
        merged.update({k: v for k, v in payload.items() if k in self._UPDATABLE})
        validated = self._validate_company_payload(merged, require_complete=False, company_type=record["company_type"])
        if validated["errors"]:
            raise CompanySetupError("VALIDATION_FAILED", "Please fix the highlighted fields", status=422, detail=validated["errors"])
        values = validated["values"]

        if values.get("name"):
            duplicate = self._duplicate(values["name"], exclude_company_id=company_id)
            if duplicate and not payload.get("allow_duplicate"):
                raise CompanySetupError(
                    "DUPLICATE_COMPANY_NAME",
                    "A company with this name already exists in your organisation",
                    status=409,
                    detail={"duplicate_of": duplicate, "allow_duplicate": True},
                )

        now = _now()
        build = self.get_build(company_id)
        build_running = bool(build and build.get("phase_state") == "RUNNING")
        changed = []
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE companies SET
                    name = ?, title = ?, description = ?, owner_name = ?, owner_email = ?,
                    owner_role = ?, country = ?, industry = ?, website = ?, business_model = ?,
                    currency = ?, timezone = ?, revenue = ?, revenue_amount = ?,
                    revenue_currency = ?, revenue_period = ?, target_customers = ?,
                    budget_amount = ?, budget_currency = ?, timeline = ?, setup_notes = ?,
                    assets = ?, updated_at = ?
                WHERE company_id = ? AND tenant_id = ?
                """,
                (
                    values.get("name") or record["name"],
                    values.get("title") or record.get("title") or "",
                    values.get("description") or record.get("description") or "",
                    values.get("owner_name") or record.get("owner_name") or "",
                    values.get("owner_email") or record.get("owner_email") or "",
                    values.get("owner_role") or record.get("owner_role") or "",
                    values.get("country") or record.get("country") or "IN",
                    values.get("industry") or record.get("industry") or "General Business",
                    values.get("website") or "",
                    values.get("business_model") or record.get("business_model") or "",
                    values.get("revenue_currency") or record.get("currency") or "INR",
                    values.get("timezone") or record.get("timezone") or "Asia/Kolkata",
                    values.get("revenue_amount") if values.get("revenue_amount") is not None else (record.get("revenue") or 0.0),
                    values.get("revenue_amount"),
                    values.get("revenue_currency") or record.get("revenue_currency") or "",
                    values.get("revenue_period") or record.get("revenue_period") or "",
                    values.get("target_customers") if values.get("target_customers") is not None else (record.get("target_customers") or ""),
                    values.get("budget_amount") if values.get("budget_amount") is not None else record.get("budget_amount"),
                    values.get("budget_currency") or record.get("budget_currency") or "",
                    values.get("timeline") if values.get("timeline") is not None else (record.get("timeline") or ""),
                    values.get("setup_notes") if values.get("setup_notes") is not None else (record.get("setup_notes") or ""),
                    _json_dump(values.get("assets") if values.get("assets") is not None else _json_load(record.get("assets"), [])),
                    now,
                    company_id,
                    self.tenant_id,
                ),
            )
            conn.commit()

        for field in ("name", "title", "description", "country", "industry"):
            if str(values.get(field) or "") != str(record.get(field) or ""):
                changed.append(field)

        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.updated",
            {"fields": changed, "build_running": build_running},
        )
        if build_running and any(f in ("name", "title", "description") for f in changed):
            # Stage 3 will notify the running Company Build workflow.
            audit.record_event(
                self.tenant_id,
                company_id,
                principal.user_id,
                principal.role,
                "company.build_change_notice_pending",
                {"fields": changed},
            )
        self._refresh_portfolio()
        return self.get_company(principal, company_id)

    # ---------------------------------------------------------------- submit
    def submit_company(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        record = self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        assert_can_submit(principal, self.tenant_id, granted=granted)

        if normalize_status(record["status"]) != CompanyStatus.DRAFT:
            raise CompanySetupError(
                "ALREADY_SUBMITTED",
                "This company has already been submitted",
                status=409,
                detail={"status": record["status"]},
            )

        company_type = record["company_type"]
        validated = self._validate_company_payload(record, require_complete=True, company_type=company_type)
        if validated["errors"]:
            raise CompanySetupError(
                "VALIDATION_FAILED",
                "The company is not ready to submit",
                status=422,
                detail=validated["errors"],
            )

        target = CompanyStatus.BY_COMPANY_TYPE.get(company_type)
        if not target:
            raise CompanySetupError("INVALID_COMPANY_TYPE", "Company type must be NEW or EXISTING")
        new_status = validate_transition(record["status"], target)

        now = _now()
        phases = BUILD_PHASES_NEW if company_type == "NEW" else BUILD_PHASES_EXISTING
        build_id = f"bld_{uuid.uuid4().hex[:12]}"
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE companies SET status = ?, updated_at = ? WHERE company_id = ? AND tenant_id = ?",
                (new_status, now, company_id, self.tenant_id),
            )
            conn.execute(
                """
                INSERT INTO company_build_runs (
                    build_id, tenant_id, company_id, run_type, workflow_id, phase, phase_state,
                    progress, estimate_min_days, estimate_max_days, started_at, log,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    build_id,
                    self.tenant_id,
                    company_id,
                    "BUILD" if company_type == "NEW" else "ONBOARDING",
                    None,
                    phases[0],
                    "PENDING",
                    0.0,
                    1,
                    3,
                    None,
                    _json_dump({"phases": phases, "log": []}),
                    now,
                    now,
                ),
            )
            conn.commit()

        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.submitted",
            {"status": new_status, "build_id": build_id, "type": company_type},
        )

        workflow = {"started": False, "reason": "The build engine is unavailable."}
        try:
            from core.company_setup.build_workflow import CompanyBuildWorkflow

            workflow = CompanyBuildWorkflow(self.tenant_id, company_id, principal).start()
        except Exception as exc:  # visible failure, never a fake success
            workflow = {"started": False, "reason": str(exc)}

        if workflow.get("started"):
            audit.record_event(
                self.tenant_id,
                company_id,
                principal.user_id,
                principal.role,
                "company.build_started",
                {"workflow_id": workflow.get("workflow_id"), "run_id": workflow.get("run_id")},
            )

        self._refresh_portfolio()
        return {
            "company": self.get_company(principal, company_id),
            "build": self.get_build(company_id),
            "workflow_started": bool(workflow.get("started")),
            "workflow_note": None if workflow.get("started") else workflow.get("reason"),
        }

    # ---------------------------------------------------------------- drafts
    def save_draft(
        self,
        principal: Principal,
        payload: Dict[str, Any],
        company_id: Optional[str] = None,
        draft_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        assert_can_draft(principal, self.tenant_id)
        if company_id:
            # Drafts may target an existing company in this tenant only.
            self._require_company(company_id)
        body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        company_type = str(payload.get("company_type") or payload.get("type") or "").upper() or None
        now = _now()
        with db.get_connection() as conn:
            if draft_id:
                row = conn.execute(
                    "SELECT draft_id FROM company_drafts WHERE draft_id = ? AND tenant_id = ? AND user_id = ?",
                    (draft_id, self.tenant_id, principal.user_id),
                ).fetchone()
                if not row:
                    raise CompanySetupError("DRAFT_NOT_FOUND", "Draft not found", status=404)
                conn.execute(
                    "UPDATE company_drafts SET payload = ?, company_type = ?, company_id = ?, updated_at = ? WHERE draft_id = ?",
                    (_json_dump(body), company_type, company_id, now, draft_id),
                )
            else:
                draft_id = f"drf_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO company_drafts
                        (draft_id, tenant_id, company_id, user_id, company_type, payload, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (draft_id, self.tenant_id, company_id, principal.user_id, company_type, _json_dump(body), now, now),
                )
            conn.commit()
        return {"draft_id": draft_id, "updated_at": now, "company_id": company_id}

    def get_draft(self, principal: Principal, draft_id: str) -> Dict[str, Any]:
        assert_can_draft(principal, self.tenant_id)
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM company_drafts WHERE draft_id = ? AND tenant_id = ? AND user_id = ?",
                (draft_id, self.tenant_id, principal.user_id),
            ).fetchone()
        record = _row_to_dict(row)
        if not record:
            raise CompanySetupError("DRAFT_NOT_FOUND", "Draft not found", status=404)
        return {
            "draft_id": record["draft_id"],
            "company_id": record.get("company_id"),
            "company_type": record.get("company_type"),
            "payload": _json_load(record.get("payload"), {}),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        }

    def list_drafts(self, principal: Principal) -> List[Dict[str, Any]]:
        assert_can_draft(principal, self.tenant_id)
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT draft_id, company_id, company_type, payload, created_at, updated_at "
                "FROM company_drafts WHERE tenant_id = ? AND user_id = ? ORDER BY updated_at DESC",
                (self.tenant_id, principal.user_id),
            ).fetchall()
        drafts = []
        for row in rows:
            record = _row_to_dict(row)
            payload = _json_load(record.get("payload"), {})
            drafts.append(
                {
                    "draft_id": record["draft_id"],
                    "company_id": record.get("company_id"),
                    "company_type": record.get("company_type"),
                    "name": (payload or {}).get("name"),
                    "updated_at": record.get("updated_at"),
                }
            )
        return drafts

    def delete_draft(self, principal: Principal, draft_id: str) -> Dict[str, Any]:
        assert_can_draft(principal, self.tenant_id)
        with db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM company_drafts WHERE draft_id = ? AND tenant_id = ? AND user_id = ?",
                (draft_id, self.tenant_id, principal.user_id),
            )
            conn.commit()
            removed = int(getattr(cursor, "rowcount", 0) or 0)
        if not removed:
            raise CompanySetupError("DRAFT_NOT_FOUND", "Draft not found", status=404)
        return {"deleted": True, "draft_id": draft_id}

    # ----------------------------------------------------------------- build
    def get_build(self, company_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM company_build_runs WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (self.tenant_id, company_id),
            ).fetchone()
        record = _row_to_dict(row)
        if not record:
            return None
        meta = _json_load(record.get("log"), {})
        phases = meta.get("phases") or []
        if phases and isinstance(phases[0], str):
            # Rows written before Stage 3 stored phase ids as plain strings.
            phases = [
                {
                    "id": phase_id,
                    "label": phase_id.replace("_", " ").title(),
                    "state": "PENDING",
                    "note": "",
                    "started_at": None,
                    "finished_at": None,
                }
                for phase_id in phases
            ]
        progress = record.get("progress")
        try:
            progress_pct = int(round(float(progress or 0) * 100))
        except (TypeError, ValueError):
            progress_pct = 0
        gaps = meta.get("gaps") or []
        return {
            "build_id": record["build_id"],
            "company_id": record["company_id"],
            "run_type": record.get("run_type"),
            "workflow_id": record.get("workflow_id"),
            "workflow_run_id": record.get("workflow_run_id"),
            "phase": record.get("phase"),
            "phase_state": record.get("phase_state"),
            "progress": progress,
            "progress_percent": progress_pct,
            "attempt": meta.get("attempt", 1),
            "estimate": {
                "min_days": record.get("estimate_min_days"),
                "max_days": record.get("estimate_max_days"),
                "is_estimate": True,
            },
            "started_at": record.get("started_at"),
            "finished_at": record.get("finished_at"),
            "failure_reason": record.get("failure_reason"),
            "phases": phases,
            "log": meta.get("log") or [],
            "gaps": gaps,
            "waiting_on": meta.get("waiting_on") if meta.get("waiting_on") is not None else gaps,
            "checks": meta.get("checks") or [],
            "brief": meta.get("brief") or {},
            "plan": meta.get("plan") or {},
            "updated_at": record.get("updated_at"),
        }

    # ----------------------------------------------------------- build retry
    def retry_build(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        """Resume a failed build, or re-run a build that finished with gaps.

        A running build is never restarted. A previous attempt is kept, and the
        new attempt starts from a fresh checkpoint.
        """
        record = self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        assert_can_submit(principal, self.tenant_id, granted=granted)

        status = normalize_status(record["status"])
        if status not in (CompanyStatus.CREATING, CompanyStatus.NEEDS_ATTENTION):
            raise CompanySetupError(
                "BUILD_NOT_RETRYABLE",
                "Only a company that is creating or needs attention can retry its build",
                status=409,
                detail={"status": status},
            )

        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT phase_state, build_id FROM company_build_runs "
                "WHERE tenant_id = ? AND company_id = ? ORDER BY created_at DESC LIMIT 1",
                (self.tenant_id, company_id),
            ).fetchone()
        if row and str(row["phase_state"]) == "RUNNING":
            raise CompanySetupError(
                "BUILD_RUNNING",
                "The build is already running",
                status=409,
                detail={"build_id": row["build_id"]},
            )

        from core.company_setup.build_workflow import CompanyBuildWorkflow

        workflow = CompanyBuildWorkflow(self.tenant_id, company_id, principal).retry()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.build_retry_requested",
            {"started": workflow.get("started"), "reason": workflow.get("reason")},
        )
        self._refresh_portfolio()
        return {
            "company": self.get_company(principal, company_id),
            "build": self.get_build(company_id),
            "workflow_started": bool(workflow.get("started")),
            "workflow_note": None if workflow.get("started") else workflow.get("reason"),
        }

    # ----------------------------------------------------------- connections
    def list_connections(self, principal: Principal, company_id: str) -> List[Dict[str, Any]]:
        assert_can_view(principal, self.tenant_id)
        self._require_company(company_id)
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM external_connections WHERE tenant_id = ? AND company_id = ? ORDER BY created_at DESC",
                (self.tenant_id, company_id),
            ).fetchall()
        out = []
        for row in rows:
            record = _row_to_dict(row)
            out.append(
                {
                    "connection_id": record["connection_id"],
                    "company_id": record["company_id"],
                    "provider_id": record.get("provider_id") or "custom",
                    "name": record.get("name"),
                    "service_type": record.get("service_type"),
                    "scope": _json_load(record.get("scope"), []),
                    "status": record.get("status") or (record.get("auth_status") or "").lower() or "needs_check",
                    "auth_status": record.get("auth_status"),
                    "verified_at": record.get("verified_at"),
                    "verification_method": record.get("verification_method"),
                    "last_check_at": record.get("last_check_at"),
                    "skipped": bool(record.get("skipped")),
                    "skip_reason": record.get("skip_reason"),
                    "has_secret": bool(record.get("secret_ref")),
                    "created_at": record.get("created_at"),
                }
            )
        return out

    def connect(self, principal: Principal, company_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        if not can_manage_connections(principal, granted=granted):
            raise PermissionDenied("connect a data source")

        provider_id = _clean_text(payload.get("provider_id") or payload.get("provider"), 80, strip_angles=True)
        if not provider_id:
            raise CompanySetupError("PROVIDER_REQUIRED", "A provider is required")
        name = _clean_text(payload.get("name") or provider_id, 160, strip_angles=True)
        service_type = _clean_text(payload.get("service_type") or "CUSTOM_API", 80, strip_angles=True).upper()
        scope = payload.get("scope") or []
        if not isinstance(scope, list):
            raise CompanySetupError("INVALID_SCOPE", "Scope must be a list of permissions")
        scope = [_clean_text(item, 80, strip_angles=True) for item in scope][:40]
        if any("write" in item.lower() and "read" not in item.lower() for item in scope):
            # Least privilege: read-only by default in this stage.
            raise CompanySetupError(
                "WRITE_SCOPE_NOT_ALLOWED",
                "Only read-only scopes are allowed until write approval is configured",
                status=422,
            )

        connection_id = f"con_{uuid.uuid4().hex[:12]}"
        now = _now()
        secret_ref = None
        secret = payload.get("secret") or payload.get("api_key")
        if secret:
            secret_ref = self._store_secret(connection_id, company_id, principal, str(secret))
        elif payload.get("requires_secret"):
            raise CompanySetupError(
                "SECRET_REQUIRED",
                "This provider requires a credential",
                status=422,
            )

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO external_connections (
                    connection_id, tenant_id, company_id, name, service_type, connector_adapter,
                    auth_status, health_score, latency_ms, field_mappings, permission_scope,
                    endpoint_url, created_at, updated_at,
                    provider_id, scope, status, secret_ref, skipped
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    connection_id,
                    self.tenant_id,
                    company_id,
                    name,
                    service_type,
                    f"{provider_id}_adapter",
                    "PENDING",
                    0.0,
                    0,
                    None,
                    _json_dump(scope),
                    _clean_text(payload.get("endpoint_url"), 2048),
                    now,
                    now,
                    provider_id,
                    _json_dump(scope),
                    "NEEDS_CHECK",
                    secret_ref,
                    0,
                ),
            )
            conn.commit()

        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.connection.added",
            {"connection_id": connection_id, "provider_id": provider_id, "scope": scope, "has_secret": bool(secret_ref)},
        )
        return {
            "connection_id": connection_id,
            "provider_id": provider_id,
            "status": "NEEDS_CHECK",
            # Real state: no provider handshake has run yet.
            "verified": False,
            "note": "Connection stored. A provider handshake is required before any data is read.",
        }

    def _store_secret(self, connection_id: str, company_id: str, principal: Principal, secret: str) -> str:
        try:
            from core.settings.models import ScopeType
            from core.settings.secrets import SettingsSecretVault

            vault = SettingsSecretVault()
            if not vault.available:
                raise CompanySetupError(
                    "SECRET_STORE_UNAVAILABLE",
                    "Encrypted secret storage is not configured on this deployment",
                    status=503,
                )
            with db.get_connection() as conn:
                ref = vault.put(
                    conn,
                    tenant_id=self.tenant_id,
                    company_id=company_id,
                    scope_type=ScopeType.COMPANY,
                    scope_id=connection_id,
                    name="connection_credential",
                    value=secret,
                    created_by=principal.user_id,
                    commit=False,
                )
                conn.commit()
            return ref.name if not getattr(ref, "secret_id", None) else ref.secret_id
        except CompanySetupError:
            raise
        except Exception:
            raise CompanySetupError(
                "SECRET_STORE_UNAVAILABLE",
                "Encrypted secret storage is not configured on this deployment",
                status=503,
            )

    def test_connection(self, principal: Principal, company_id: str, connection_id: str) -> Dict[str, Any]:
        self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        if not can_manage_connections(principal, granted=granted):
            raise PermissionDenied("test a connection")
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM external_connections WHERE connection_id = ? AND company_id = ? AND tenant_id = ?",
                (connection_id, company_id, self.tenant_id),
            ).fetchone()
        if not row:
            raise CompanySetupError("CONNECTION_NOT_FOUND", "Connection not found", status=404)
        now = _now()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE external_connections SET last_check_at = ?, status = ?, updated_at = ? WHERE connection_id = ?",
                (now, "NEEDS_CHECK", now, connection_id),
            )
            conn.commit()
        # Honest: no provider adapter exists yet, so the check cannot succeed.
        return {
            "connection_id": connection_id,
            "status": "NEEDS_CHECK",
            "verified": False,
            "simulated": True,
            "error": "No provider adapter is configured yet. Nothing was read.",
            "checked_at": now,
        }

    def disconnect(self, principal: Principal, company_id: str, connection_id: str) -> Dict[str, Any]:
        self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        if not can_manage_connections(principal, granted=granted):
            raise PermissionDenied("disconnect a data source")
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT connection_id, secret_ref, provider_id FROM external_connections "
                "WHERE connection_id = ? AND company_id = ? AND tenant_id = ?",
                (connection_id, company_id, self.tenant_id),
            ).fetchone()
        record = _row_to_dict(row)
        if not record:
            raise CompanySetupError("CONNECTION_NOT_FOUND", "Connection not found", status=404)

        revoked = False
        if record.get("secret_ref"):
            try:
                from core.settings.models import ScopeType
                from core.settings.secrets import SettingsSecretVault

                vault = SettingsSecretVault()
                with db.get_connection() as conn:
                    revoked = vault.revoke(
                        conn,
                        tenant_id=self.tenant_id,
                        scope_type=ScopeType.COMPANY,
                        scope_id=connection_id,
                        name="connection_credential",
                        commit=True,
                    )
            except Exception:
                revoked = False

        with db.get_connection() as conn:
            conn.execute(
                "DELETE FROM external_connections WHERE connection_id = ? AND company_id = ? AND tenant_id = ?",
                (connection_id, company_id, self.tenant_id),
            )
            conn.commit()

        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.connection.removed",
            {"connection_id": connection_id, "secret_revoked": revoked},
        )
        return {"connection_id": connection_id, "disconnected": True, "secret_revoked": revoked}

    # --------------------------------------------------------------- deletion
    def _mfa_required(self, company_id: str) -> bool:
        try:
            from core.settings_service import settings_service

            return bool(settings_service.get_effective_setting(self.tenant_id, company_id, "sec_require_mfa", False))
        except Exception:
            return False

    def _deletion_row(self, company_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM company_deletion_requests WHERE tenant_id = ? AND company_id = ? "
                "AND status <> 'CANCELLED' AND status <> 'COMPLETED' ORDER BY created_at DESC LIMIT 1",
                (self.tenant_id, company_id),
            ).fetchone()
        record = _row_to_dict(row)
        return record or None

    def _deletion_payload(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "request_id": record["request_id"],
            "company_id": record["company_id"],
            "status": record["status"],
            "steps_done": _json_load(record.get("steps_done"), []),
            "removal_summary": _json_load(record.get("removal_summary"), {}),
            "export_status": record.get("export_status"),
            "export_parts": record.get("export_parts"),
            "email_status": record.get("email_status"),
            "download_confirmed_at": record.get("download_confirmed_at"),
            "purge_after": record.get("purge_after"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        }

    def get_deletion(self, company_id: str) -> Optional[Dict[str, Any]]:
        record = self._deletion_row(company_id)
        return self._deletion_payload(record) if record else None

    def _removal_summary(self, company_id: str) -> Dict[str, Any]:
        counts = {}
        with db.get_connection() as conn:
            for key, sql in (
                ("departments", "SELECT COUNT(*) AS n FROM departments WHERE company_id = ? AND tenant_id = ?"),
                ("employees", "SELECT COUNT(*) AS n FROM employees WHERE company_id = ? AND tenant_id = ?"),
                ("workflows", "SELECT COUNT(*) AS n FROM workflows WHERE company_id = ? AND tenant_id = ?"),
                ("connections", "SELECT COUNT(*) AS n FROM external_connections WHERE company_id = ? AND tenant_id = ?"),
                ("files", "SELECT COUNT(*) AS n FROM company_files WHERE company_id = ? AND tenant_id = ?"),
                ("approvals", "SELECT COUNT(*) AS n FROM approvals WHERE company_id = ? AND tenant_id = ?"),
            ):
                try:
                    row = conn.execute(sql, (company_id, self.tenant_id)).fetchone()
                    counts[key] = int(row["n"] if row else 0)
                except Exception:
                    counts[key] = 0
        return {
            "will_remove": counts,
            "will_keep": ["a minimal audit record of the deletion"],
            "will_stop": ["running workflows", "scheduled work", "connection access"],
        }

    def request_deletion(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        record = self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)

        existing = self._deletion_row(company_id)
        if existing:
            return self._deletion_payload(existing)

        now = _now()
        request_id = f"del_{uuid.uuid4().hex[:12]}"
        summary = self._removal_summary(company_id)
        steps = ["requested"]
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO company_deletion_requests (
                    request_id, tenant_id, company_id, status, steps_done, removal_summary,
                    export_status, export_parts, email_status, requested_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    self.tenant_id,
                    company_id,
                    "AWAITING_NAME",
                    _json_dump(steps),
                    _json_dump(summary),
                    "NOT_STARTED",
                    0,
                    "NOT_SENT",
                    principal.user_id,
                    now,
                    now,
                ),
            )
            conn.commit()

        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.delete.requested",
            {"request_id": request_id, "removal_summary": summary},
        )
        return self._deletion_payload(self._deletion_row(company_id) or {})

    def _require_deletion(self, company_id: str) -> Dict[str, Any]:
        record = self._deletion_row(company_id)
        if not record:
            raise CompanySetupError("DELETION_NOT_REQUESTED", "Start the deletion flow first", status=409)
        return record

    def confirm_delete_name(self, principal: Principal, company_id: str, name: str) -> Dict[str, Any]:
        record = self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)

        request = self._require_deletion(company_id)
        if request["status"] != "AWAITING_NAME":
            raise CompanySetupError(
                "STEP_OUT_OF_ORDER",
                "The company name step has already been completed",
                status=409,
                detail={"status": request["status"]},
            )
        if str(name or "").strip() != str(record["name"]).strip():
            raise CompanySetupError(
                "NAME_MISMATCH",
                "The company name does not match exactly",
                status=400,
            )

        mfa = self._mfa_required(company_id)
        next_status = "AWAITING_IDENTITY"
        steps = _json_load(request.get("steps_done"), [])
        steps.append("name_confirmed")
        now = _now()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE company_deletion_requests SET status = ?, steps_done = ?, updated_at = ? WHERE request_id = ?",
                (next_status, _json_dump(steps), now, request["request_id"]),
            )
            conn.commit()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.delete.name_confirmed",
            {"request_id": request["request_id"], "mfa_required": mfa},
        )
        return self._deletion_payload(self._deletion_row(company_id) or {})

    def confirm_delete_identity(
        self,
        principal: Principal,
        company_id: str,
        password: Optional[str] = None,
        two_step_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)

        request = self._require_deletion(company_id)
        if request["status"] != "AWAITING_IDENTITY":
            raise CompanySetupError(
                "STEP_OUT_OF_ORDER",
                "Identity confirmation is not the current step",
                status=409,
                detail={"status": request["status"]},
            )

        if not self._verify_owner_password(principal, password):
            raise CompanySetupError("INVALID_PASSWORD", "Password is incorrect", status=403)

        if self._mfa_required(company_id) and not two_step_code:
            raise CompanySetupError(
                "TWO_STEP_REQUIRED",
                "A two-step verification code is required",
                status=400,
            )
        if self._mfa_required(company_id):
            # No real TOTP verifier is wired yet; never accept a dummy value.
            raise CompanySetupError(
                "TWO_STEP_NOT_CONFIGURED",
                "Two-step verification is enabled but no verifier is configured on this deployment",
                status=501,
            )

        steps = _json_load(request.get("steps_done"), [])
        steps.append("identity_confirmed")
        now = _now()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE company_deletion_requests SET status = ?, steps_done = ?, updated_at = ? WHERE request_id = ?",
                ("EXPORTING", _json_dump(steps), now, request["request_id"]),
            )
            conn.commit()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.delete.identity_confirmed",
            {"request_id": request["request_id"]},
        )
        return {
            "deletion": self._deletion_payload(self._deletion_row(company_id) or {}),
            "export": {
                "status": "NOT_STARTED",
                "message": "Export generation is implemented in Stage 5. Nothing has been deleted.",
            },
        }

    def _verify_owner_password(self, principal: Principal, password: Optional[str]) -> bool:
        if not password:
            return False
        try:
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT password_hash, salt FROM auth_credentials WHERE user_id = ?",
                    (principal.user_id,),
                ).fetchone()
        except Exception:
            return False
        if not row:
            return False
        try:
            return bool(verify_password(str(password), row["salt"], row["password_hash"]))
        except Exception:
            return False

    def cancel_deletion(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        record = self._require_company(company_id, include_deleted=True)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)
        request = self._require_deletion(company_id)
        if request["status"] == "COMPLETED":
            raise CompanySetupError("ALREADY_DELETED", "This company has already been deleted", status=409)

        now = _now()
        previous_status = record["status"]
        restore_to = CompanyStatus.OPERATIONAL
        restored = None
        if previous_status in (CompanyStatus.PENDING_EXPORT, CompanyStatus.PENDING_DELETION):
            try:
                restore_to = validate_transition(previous_status, CompanyStatus.OPERATIONAL)
            except InvalidTransition:
                restore_to = CompanyStatus.NEEDS_ATTENTION
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE company_deletion_requests SET status = 'CANCELLED', updated_at = ? WHERE request_id = ?",
                (now, request["request_id"]),
            )
            if previous_status in (CompanyStatus.PENDING_EXPORT, CompanyStatus.PENDING_DELETION):
                conn.execute(
                    "UPDATE companies SET status = ?, updated_at = ? WHERE company_id = ? AND tenant_id = ?",
                    (restore_to, now, company_id, self.tenant_id),
                )
                restored = restore_to
            conn.commit()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.delete.cancelled",
            {"request_id": request["request_id"], "restored_status": restored or previous_status},
        )
        return {"cancelled": True, "company_status": normalize_status(restored or previous_status)}

    def download_export(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        self._require_company(company_id, include_deleted=True)
        assert_can_view(principal, self.tenant_id)
        request = self._deletion_row(company_id)
        if not request or request.get("export_status") not in ("READY", "EMAILED"):
            raise CompanySetupError(
                "EXPORT_NOT_READY",
                "No company export is available yet",
                status=409,
            )
        # Actual PDF/ZIP streaming is delivered in Stage 5.
        raise CompanySetupError(
            "EXPORT_NOT_READY",
            "The export file is not available on this deployment yet",
            status=409,
        )

    # ---------------------------------------------------------------- admins
    def list_admins(self, principal: Principal, company_id: str) -> List[Dict[str, Any]]:
        self._require_company(company_id)
        assert_can_view(principal, self.tenant_id)
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT user_id, granted_by, created_at FROM company_admin_grants "
                "WHERE tenant_id = ? AND company_id = ? ORDER BY created_at ASC",
                (self.tenant_id, company_id),
            ).fetchall()
        return [
            {"user_id": r["user_id"], "granted_by": r["granted_by"], "created_at": r["created_at"]}
            for r in rows
        ]

    def grant_admin(self, principal: Principal, company_id: str, user_id: str) -> Dict[str, Any]:
        self._require_company(company_id)
        if principal.is_agent or not principal.is_owner:
            raise PermissionDenied("grant a company admin", "Only the owner may add company admins")
        target = _clean_text(user_id, 120, strip_angles=True)
        if not target:
            raise CompanySetupError("USER_REQUIRED", "A user id is required", status=422)
        now = _now()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO company_admin_grants (tenant_id, company_id, user_id, granted_by, created_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT (tenant_id, company_id, user_id) DO NOTHING",
                (self.tenant_id, company_id, target, principal.user_id, now),
            )
            conn.commit()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.admin.granted",
            {"user_id": target},
        )
        return {"company_id": company_id, "user_id": target, "granted": True}

    def revoke_admin(self, principal: Principal, company_id: str, user_id: str) -> Dict[str, Any]:
        self._require_company(company_id)
        if principal.is_agent or not principal.is_owner:
            raise PermissionDenied("revoke a company admin", "Only the owner may remove company admins")
        with db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM company_admin_grants WHERE tenant_id = ? AND company_id = ? AND user_id = ?",
                (self.tenant_id, company_id, user_id),
            )
            conn.commit()
            removed = int(getattr(cursor, "rowcount", 0) or 0)
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.admin.revoked",
            {"user_id": user_id, "removed": bool(removed)},
        )
        return {"company_id": company_id, "user_id": user_id, "revoked": bool(removed)}

    # ----------------------------------------------------------------- audit
    def audit_events(self, principal: Principal, company_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        self._require_company(company_id, include_deleted=True)
        assert_can_view(principal, self.tenant_id)
        events = audit.list_events(self.tenant_id, company_id, limit=limit, offset=offset)
        return {"events": events, "total": audit.count_events(self.tenant_id, company_id)}
