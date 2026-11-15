"""Tenant-scoped company lifecycle service.

Owns the company record (fields, status transitions), drafts, connection
records and the protected deletion state machine. It is deliberately separate
from ``core.portfolio.CompanyPortfolioManager`` so the operating context path
keeps working unchanged; after a mutation we refresh the cached portfolio so
the rest of the app sees the new company immediately.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import re
import shutil
import time
import uuid
from typing import Any, Dict, List, Optional

from core.auth import verify_password
from core.company_setup import audit
from core.company_setup import ingestion as ingestion_module
from core.company_setup import readiness as readiness_module
from core.company_setup import sources as source_module
from core.company_setup.connections import get_adapter
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

DEFAULT_EXPORT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "storage", "company_exports")
)
EXPORT_AUDIT_LIMIT = 500
EXPORT_TABLE_LIMIT = 500
#: Tables that must survive a purge: the company tombstone, the audit trail and
#: the deletion request itself are the minimal record promised to the owner.
PURGE_KEEP_TABLES = {"companies", "company_audit_events", "company_deletion_requests"}


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
    if value is None or isinstance(value, bool):
        return ""
    if not isinstance(value, (str, int, float)):
        # Objects, arrays and other JSON shapes are not text; never store their
        # Python representation as if the user had typed it.
        return ""
    text = str(value)
    text = CONTROL_CHARS_RE.sub("", text).strip()
    if strip_angles:
        text = text.replace("<", "").replace(">", "")
    return text[:max_len]


def _validate_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value or ""))


class CompanySetupService:
    """All company setup operations for a single tenant."""

    def __init__(self, tenant_id: str, tenant_scope_id: Optional[str] = None):
        if not tenant_id:
            raise CompanySetupError("TENANT_REQUIRED", "tenant_id is required", status=401)
        self.tenant_id = tenant_id
        # The company that owns tenant-wide settings in the settings console
        # (the token's company). Company-specific overrides still win.
        self.tenant_scope_id = tenant_scope_id
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

    def company_exists(self, company_id: str) -> bool:
        """Tenant-scoped existence check (never reveals another tenant)."""
        return self._fetch_company_row(company_id) is not None

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

    # ----------------------------------------------------------- preferences
    def _effective(self, company_id: str, key: str, default: Any = None) -> Any:
        """Read one effective enterprise setting for this tenant/company.

        Resolution order: the company's own override, then the tenant's
        settings scope (the token company that the settings console writes to),
        then the tenant primary store, then the global store/schema default.
        Any failure falls back to the supplied default so a settings outage can
        never block company setup.
        """
        scopes: List[str] = []
        for scope in (company_id, self.tenant_scope_id, "comp_primary"):
            if scope and scope not in scopes:
                scopes.append(scope)
        try:
            with db.get_connection() as conn:
                for scope in scopes:
                    row = conn.execute(
                        "SELECT setting_value_json FROM enterprise_settings "
                        "WHERE tenant_id = ? AND company_id = ? AND setting_key = ?",
                        (self.tenant_id, scope, key),
                    ).fetchone()
                    if row:
                        raw = row[0]
                        try:
                            return json.loads(raw)
                        except Exception:
                            return raw
        except Exception:
            pass
        try:
            from core.settings_service import settings_service

            return settings_service.get_effective_setting(
                self.tenant_id, "comp_primary", key, default
            )
        except Exception:
            return default

    @staticmethod
    def _currency_meta(label: Any) -> Dict[str, str]:
        """Turn a ``comp_base_currency`` label into a code, symbol and name."""
        text = str(label or "").strip() or "INR (₹)"
        code = (text.split()[0] or "INR").upper()
        symbol = ""
        if "(" in text and ")" in text:
            symbol = text[text.index("(") + 1:text.rindex(")")].strip()
        names = {
            "INR": "Indian Rupee",
            "USD": "US Dollar",
            "EUR": "Euro",
            "GBP": "British Pound",
            "AED": "UAE Dirham",
            "SGD": "Singapore Dollar",
            "JPY": "Japanese Yen",
        }
        return {"code": code, "symbol": symbol or code, "name": names.get(code, code)}

    @staticmethod
    def _timezone_list(value: Any) -> List[str]:
        if isinstance(value, (list, tuple)):
            items = [str(item).strip() for item in value]
        elif isinstance(value, str):
            items = [part.strip() for part in value.split(",")]
        else:
            items = []
        return [item for item in items if item]

    def preferences(self, principal: Principal, company_id: Optional[str] = None) -> Dict[str, Any]:
        """Real, tenant/company-scoped preferences consumed by the UI runtime.

        This endpoint does not invent capabilities. It reports the effective
        values of settings that already exist, plus honest flags for features
        that are not wired (quiet hours, a two-step verifier).
        """
        assert_can_view(principal, self.tenant_id)
        if company_id:
            self._require_company(company_id)
            scope_id = company_id
        else:
            # No active company: resolve the tenant-level preference store.
            scope_id = self.tenant_scope_id or "comp_primary"

        locale = str(self._effective(scope_id, "loc_base_locale", "en-IN") or "en-IN")
        language = "ar" if locale.lower().startswith("ar") else "en"
        number_label = str(
            self._effective(scope_id, "loc_number_format", "1,00,000.00 (Indian Lakh/Crore)")
        )
        number_formats = {
            "1,00,000.00 (Indian Lakh/Crore)": "indian",
            "100,000.00 (International Standard)": "international",
            "100.000,00 (Continental European)": "continental",
        }
        display_label = str(self._effective(scope_id, "loc_currency_display", "Symbol (₹)"))
        display_formats = {
            "Symbol (₹)": "symbol",
            "ISO Code (INR)": "iso",
            "Full Name (Indian Rupee)": "name",
        }
        currency = self._currency_meta(self._effective(scope_id, "comp_base_currency", "INR (₹)"))
        timezones = self._timezone_list(
            self._effective(scope_id, "comp_operating_timezones", ["Asia/Kolkata", "UTC"])
        ) or ["Asia/Kolkata"]
        assistant_scope = str(self._effective(scope_id, "assistant_default_scope", "PERSONAL") or "PERSONAL")
        recovery_days = self._recovery_days(scope_id)
        mfa_required = self._mfa_required(scope_id)

        return {
            "tenant_id": self.tenant_id,
            "company_id": company_id,
            "language": language,
            "locale": locale,
            "direction": "rtl" if language == "ar" else "ltr",
            "number_format": {
                "id": number_formats.get(number_label, "indian"),
                "label": number_label,
            },
            "currency": {
                **currency,
                "display": display_formats.get(display_label, "symbol"),
                "display_label": display_label,
            },
            "default_currency": currency["code"],
            "country": self._locale_country(locale),
            "timezone": timezones[0],
            "timezones": timezones,
            "assistant": {"default_scope": assistant_scope},
            "recovery_days": recovery_days,
            "mfa_required": mfa_required,
            "two_step_configured": True,
            "two_step_enrolled": None,
            "quiet_hours": None,
            "quiet_hours_supported": False,
        }

    def _preference_defaults(self) -> Dict[str, str]:
        """Server-side defaults used when a company payload omits currency/timezone."""
        scope_id = self.tenant_scope_id or "comp_primary"
        currency = self._currency_meta(self._effective(scope_id, "comp_base_currency", "INR (₹)"))
        timezones = self._timezone_list(
            self._effective(scope_id, "comp_operating_timezones", ["Asia/Kolkata", "UTC"])
        ) or ["Asia/Kolkata"]
        return {"currency": currency["code"], "timezone": timezones[0]}

    @staticmethod
    def _locale_country(locale: Any) -> str:
        parts = str(locale or "").replace("_", "-").split("-")
        if len(parts) > 1 and len(parts[1]) == 2 and parts[1].isalpha():
            return parts[1].upper()
        return "IN"

    def _default_country(self) -> str:
        scope_id = self.tenant_scope_id or "comp_primary"
        return self._locale_country(self._effective(scope_id, "loc_base_locale", "en-IN"))

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
        clean["country"] = country or self._default_country()
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
                if not math.isfinite(budget_amount):
                    add_error("budget.amount", "INVALID_AMOUNT", "Budget must be a finite number")
                    budget_amount = None
                elif budget_amount < 0:
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
                if not math.isfinite(amount):
                    add_error("revenue.amount", "INVALID_AMOUNT", "Revenue must be a finite number")
                    amount = None
                elif amount < 0:
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
        defaults = self._preference_defaults()
        currency = values.get("revenue_currency") or defaults["currency"]
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
                    values.get("timezone") or defaults["timezone"],
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
        defaults = self._preference_defaults()
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
                    values.get("title") or "",
                    values.get("description") or "",
                    values.get("owner_name") or "",
                    values.get("owner_email") or "",
                    values.get("owner_role") or "",
                    values.get("country") or record.get("country") or "IN",
                    values.get("industry") or record.get("industry") or "General Business",
                    values.get("website") or "",
                    values.get("business_model") or "",
                    values.get("revenue_currency") or record.get("currency") or defaults["currency"],
                    values.get("timezone") or record.get("timezone") or defaults["timezone"],
                    values.get("revenue_amount") if values.get("revenue_amount") is not None else 0.0,
                    values.get("revenue_amount"),
                    values.get("revenue_currency") or "",
                    values.get("revenue_period") or "",
                    values.get("target_customers") or "",
                    values.get("budget_amount") if values.get("budget_amount") is not None else None,
                    values.get("budget_currency") or "",
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
            if company_type == "EXISTING":
                from core.company_setup.onboarding_workflow import CompanyOnboardingWorkflow

                workflow = CompanyOnboardingWorkflow(self.tenant_id, company_id, principal).start()
            else:
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
            "study": meta.get("study") or {},
            "diagnosis": meta.get("diagnosis") or {},
            "sources": meta.get("sources") or [],
            "readiness": meta.get("readiness") or {},
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
        if status not in (CompanyStatus.CREATING, CompanyStatus.ONBOARDING, CompanyStatus.NEEDS_ATTENTION):
            raise CompanySetupError(
                "BUILD_NOT_RETRYABLE",
                "Only a company that is creating, onboarding or needs attention can retry",
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

        workflow_cls = CompanyBuildWorkflow
        if str(record.get("company_type") or "NEW").upper() == "EXISTING":
            from core.company_setup.onboarding_workflow import CompanyOnboardingWorkflow

            workflow_cls = CompanyOnboardingWorkflow

        workflow = workflow_cls(self.tenant_id, company_id, principal).retry()
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
        return self._connections_payload(company_id)

    def _connections_payload(self, company_id: str) -> List[Dict[str, Any]]:
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
                    "source_id": record.get("source_id") or record.get("provider_id") or "custom",
                    "classification": record.get("classification"),
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
        source_id = _clean_text(payload.get("source_id"), 80, strip_angles=True).lower() or None
        source = source_module.find_source(source_id or provider_id)
        if source and not provider_id:
            provider_id = source["id"]
            source_id = source["id"]
        if not provider_id:
            raise CompanySetupError("PROVIDER_REQUIRED", "A provider is required")
        name = _clean_text(payload.get("name") or (source or {}).get("name") or provider_id, 160, strip_angles=True)
        service_type = _clean_text(payload.get("service_type") or "CUSTOM_API", 80, strip_angles=True).upper()
        scope = payload.get("scope") or []
        if not isinstance(scope, list):
            raise CompanySetupError("INVALID_SCOPE", "Scope must be a list of permissions")
        scope = [_clean_text(item, 80, strip_angles=True) for item in scope][:40]
        if not scope and source:
            # Use the read-only scope published in the catalogue, never more.
            scope = list(source.get("scope") or [])
        if any("write" in item.lower() and "read" not in item.lower() for item in scope):
            # Least privilege: read-only by default in this stage.
            raise CompanySetupError(
                "WRITE_SCOPE_NOT_ALLOWED",
                "Only read-only scopes are allowed until write approval is configured",
                status=422,
            )
        classification = (source or {}).get("category") or _clean_text(
            payload.get("classification"), 40, strip_angles=True
        ).upper() or None

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
                    provider_id, source_id, classification, scope, status, secret_ref, skipped
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    source_id,
                    classification,
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
            "source_id": source_id or provider_id,
            "classification": classification,
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
        adapter = get_adapter(row["source_id"] if "source_id" in row.keys() and row["source_id"] else row["provider_id"])
        result = adapter.test(dict(row))
        status = "NEEDS_CHECK" if result.get("status") in (None, "UNAVAILABLE") else result.get("status")
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE external_connections SET last_check_at = ?, status = ?, updated_at = ? WHERE connection_id = ?",
                (now, status, now, connection_id),
            )
            conn.commit()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.connection.tested",
            {"connection_id": connection_id, "status": status, "verified": bool(result.get("verified"))},
        )
        # Honest: a null adapter reports that it could not read anything.
        return {
            "connection_id": connection_id,
            "provider_id": result.get("provider_id"),
            "status": status,
            "verified": bool(result.get("verified")),
            "simulated": False,
            "available": bool(result.get("available")),
            "error": result.get("error"),
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

    # ----------------------------------------------------- source catalogue
    def _source_rows(self, company_id: str) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM external_connections WHERE tenant_id = ? AND company_id = ? ORDER BY created_at DESC",
                (self.tenant_id, company_id),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def list_sources(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        assert_can_view(principal, self.tenant_id)
        self._require_company(company_id)
        return self._sources_payload(company_id)

    def _sources_payload(self, company_id: str) -> Dict[str, Any]:
        rows = self._source_rows(company_id)
        by_source: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            source_id = str(row.get("source_id") or row.get("provider_id") or "custom")
            if source_id in by_source:
                continue
            skipped = bool(row.get("skipped"))
            verified = bool(row.get("verified_at"))
            by_source[source_id] = {
                "connection_id": row.get("connection_id"),
                "status": "SKIPPED" if skipped else ("VERIFIED" if verified else "NEEDS_CHECK"),
                "skipped": skipped,
                "skip_reason": row.get("skip_reason") or "",
                "verified": verified,
            }

        items = []
        for source in source_module.catalogue():
            state = by_source.get(source["id"]) or {
                "connection_id": None,
                "status": "NOT_STARTED",
                "skipped": False,
                "skip_reason": "",
                "verified": False,
            }
            items.append(dict(source, **state))

        return {
            "sources": items,
            "counts": {
                "connected": len([item for item in items if item["status"] in ("NEEDS_CHECK", "VERIFIED")]),
                "verified": len([item for item in items if item["verified"]]),
                "skipped": len([item for item in items if item["skipped"]]),
                "not_started": len([item for item in items if item["status"] == "NOT_STARTED"]),
            },
        }

    def skip_source(self, principal: Principal, company_id: str, source_id: str, reason: str) -> Dict[str, Any]:
        self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        if not can_manage_connections(principal, granted=granted):
            raise PermissionDenied("skip a source")

        source = source_module.find_source(source_id)
        if not source:
            raise CompanySetupError("SOURCE_NOT_FOUND", "Unknown source", status=404)
        text = _clean_text(reason, 500, strip_angles=True)
        if len(text) < 5:
            raise CompanySetupError(
                "SKIP_REASON_REQUIRED",
                "A short reason is required when skipping a source",
                status=422,
            )

        rows = self._source_rows(company_id)
        existing_skipped = None
        for row in rows:
            sid = str(row.get("source_id") or row.get("provider_id") or "")
            if sid != source["id"]:
                continue
            if not row.get("skipped"):
                raise CompanySetupError(
                    "SOURCE_ALREADY_CONNECTED",
                    "This source is already connected. Disconnect it before skipping.",
                    status=409,
                )
            existing_skipped = row

        now = _now()
        if existing_skipped:
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE external_connections SET skip_reason = ?, updated_at = ? WHERE connection_id = ?",
                    (text, now, existing_skipped["connection_id"]),
                )
                conn.commit()
            connection_id = existing_skipped["connection_id"]
        else:
            connection_id = f"con_{uuid.uuid4().hex[:12]}"
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO external_connections (
                        connection_id, tenant_id, company_id, name, service_type, connector_adapter,
                        auth_status, health_score, latency_ms, field_mappings, permission_scope,
                        endpoint_url, created_at, updated_at,
                        provider_id, source_id, classification, scope, status, skipped, skip_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        connection_id,
                        self.tenant_id,
                        company_id,
                        source["name"],
                        "SKIPPED_SOURCE",
                        f"{source['id']}_adapter",
                        "SKIPPED",
                        0.0,
                        0,
                        None,
                        _json_dump([]),
                        None,
                        now,
                        now,
                        source["id"],
                        source["id"],
                        source.get("category"),
                        _json_dump([]),
                        "SKIPPED",
                        1,
                        text,
                    ),
                )
                conn.commit()

        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.source.skipped",
            {"source_id": source["id"], "reason": text, "connection_id": connection_id},
        )
        self._refresh_readiness(company_id)
        return {
            "connection_id": connection_id,
            "source_id": source["id"],
            "skipped": True,
            "skip_reason": text,
            "readiness": self.readiness(company_id),
        }

    def unskip_source(self, principal: Principal, company_id: str, source_id: str) -> Dict[str, Any]:
        self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        if not can_manage_connections(principal, granted=granted):
            raise PermissionDenied("restore a source")

        source = source_module.find_source(source_id)
        if not source:
            raise CompanySetupError("SOURCE_NOT_FOUND", "Unknown source", status=404)
        rows = self._source_rows(company_id)
        skipped = [
            row
            for row in rows
            if str(row.get("source_id") or row.get("provider_id") or "") == source["id"] and row.get("skipped")
        ]
        if not skipped:
            raise CompanySetupError("SOURCE_NOT_SKIPPED", "This source is not skipped", status=404)
        with db.get_connection() as conn:
            conn.execute(
                "DELETE FROM external_connections WHERE connection_id = ? AND tenant_id = ?",
                (skipped[0]["connection_id"], self.tenant_id),
            )
            conn.commit()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.source.restored",
            {"source_id": source["id"]},
        )
        self._refresh_readiness(company_id)
        return {"source_id": source["id"], "skipped": False, "readiness": self.readiness(company_id)}

    # --------------------------------------------------- ownership verify
    def request_verification(
        self,
        principal: Principal,
        company_id: str,
        connection_id: str,
        method: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        if not can_manage_connections(principal, granted=granted):
            raise PermissionDenied("verify a connection")

        rows = self._source_rows(company_id)
        row = next((item for item in rows if item.get("connection_id") == connection_id), None)
        if not row or row.get("skipped"):
            raise CompanySetupError("CONNECTION_NOT_FOUND", "Connection not found", status=404)

        from core.company_setup.connections import OwnershipVerifier

        verifier = OwnershipVerifier()
        chosen = str(method or "DNS_TXT").upper()
        if chosen not in ("DNS_TXT", "EMAIL"):
            raise CompanySetupError("INVALID_VERIFICATION_METHOD", "Use DNS_TXT or EMAIL", status=422)

        if not verifier.available:
            audit.record_event(
                self.tenant_id,
                company_id,
                principal.user_id,
                principal.role,
                "company.connection.verification_unavailable",
                {"connection_id": connection_id, "method": chosen},
            )
            raise CompanySetupError(
                "VERIFICATION_NOT_CONFIGURED",
                verifier.unavailable_reason(),
                status=501,
                detail=verifier.instructions(chosen),
            )

        token = verifier.issue_token()
        now = _now()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE external_connections SET verification_token = ?, verification_method = ?, "
                "verification_requested_at = ?, status = 'PENDING_VERIFICATION', updated_at = ? "
                "WHERE connection_id = ? AND tenant_id = ?",
                (token, chosen, now, now, connection_id, self.tenant_id),
            )
            conn.commit()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.connection.verification_requested",
            {"connection_id": connection_id, "method": chosen},
        )
        return {
            "connection_id": connection_id,
            "status": "PENDING_VERIFICATION",
            "method": chosen,
            "token": token,
            "configured": True,
            "instructions": verifier.instructions(chosen, token)["instructions"],
        }

    def confirm_verification(
        self,
        principal: Principal,
        company_id: str,
        connection_id: str,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        if not can_manage_connections(principal, granted=granted):
            raise PermissionDenied("verify a connection")

        from core.company_setup.connections import OwnershipVerifier

        verifier = OwnershipVerifier()
        if not verifier.available:
            raise CompanySetupError(
                "VERIFICATION_NOT_CONFIGURED",
                verifier.unavailable_reason(),
                status=501,
            )
        # No verifier exists today; a future one must check the real DNS/mailbox.
        raise CompanySetupError(
            "VERIFICATION_NOT_IMPLEMENTED",
            "No ownership verifier is wired yet",
            status=501,
        )

    # ---------------------------------------------------------- readiness
    def readiness(self, company_id: str) -> Dict[str, Any]:
        record = self._require_company(company_id, include_deleted=True)
        rows = self._source_rows(company_id)
        file_count = 0
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM company_files WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, company_id),
            ).fetchone()
            file_count = int((row["n"] if row else 0) or 0)
        result = readiness_module.compute(record, rows, file_count)
        result["company_id"] = company_id
        return result

    def _refresh_readiness(self, company_id: str) -> None:
        try:
            score = self.readiness(company_id)["score"]
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE companies SET readiness_score = ?, updated_at = ? WHERE tenant_id = ? AND company_id = ?",
                    (score, _now(), self.tenant_id, company_id),
                )
                conn.commit()
        except Exception:
            pass

    def get_readiness(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        assert_can_view(principal, self.tenant_id)
        result = self.readiness(company_id)
        self._refresh_readiness(company_id)
        return result

    # ------------------------------------------------------------ ingestion
    def list_files(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        assert_can_view(principal, self.tenant_id)
        self._require_company(company_id)
        return self._files_payload(company_id)

    def _files_payload(self, company_id: str) -> Dict[str, Any]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM company_files WHERE tenant_id = ? AND company_id = ? ORDER BY created_at DESC",
                (self.tenant_id, company_id),
            ).fetchall()
        files = []
        for row in rows:
            record = _row_to_dict(row)
            files.append(
                {
                    "file_id": record["file_id"],
                    "company_id": record["company_id"],
                    "kind": record.get("kind"),
                    "filename": record.get("filename"),
                    "mime": record.get("mime"),
                    "size_bytes": record.get("size_bytes"),
                    "sha256": record.get("sha256"),
                    "scan_status": record.get("scan_status"),
                    "flags": _json_load(record.get("flags"), []),
                    "stored": bool(record.get("storage_key")),
                    "uploaded_by": record.get("uploaded_by"),
                    "created_at": record.get("created_at"),
                }
            )
        return {"files": files, "total": len(files)}

    def record_file(self, principal: Principal, company_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        if not can_manage_connections(principal, granted=granted):
            raise PermissionDenied("add a file")

        inspected = ingestion_module.inspect(payload)
        if not inspected["ok"]:
            raise CompanySetupError(
                "VALIDATION_FAILED",
                "The file could not be accepted",
                status=422,
                detail=inspected["errors"],
            )

        file_meta = inspected["file"]
        with db.get_connection() as conn:
            duplicate = conn.execute(
                "SELECT file_id, filename FROM company_files WHERE tenant_id = ? AND company_id = ? AND sha256 = ?",
                (self.tenant_id, company_id, file_meta["sha256"]),
            ).fetchone()
        if duplicate:
            raise CompanySetupError(
                "DUPLICATE_FILE",
                "This file has already been recorded for this company",
                status=409,
                detail={"file_id": duplicate["file_id"], "filename": duplicate["filename"]},
            )

        file_id = f"fil_{uuid.uuid4().hex[:12]}"
        now = _now()
        scan_status = "FLAGGED" if file_meta["flagged"] else "UNSCANNED"
        flags = inspected["warnings"]
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO company_files (
                    file_id, tenant_id, company_id, kind, filename, mime, size_bytes,
                    storage_key, sha256, scan_status, flags, uploaded_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    self.tenant_id,
                    company_id,
                    file_meta["kind"],
                    file_meta["filename"],
                    file_meta["mime"],
                    file_meta["size_bytes"],
                    file_meta["sha256"],
                    scan_status,
                    _json_dump(flags),
                    principal.user_id,
                    now,
                ),
            )
            conn.commit()

        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.file.flagged" if file_meta["flagged"] else "company.file.recorded",
            {
                "file_id": file_id,
                "filename": file_meta["filename"],
                "sha256": file_meta["sha256"],
                "scan_status": scan_status,
            },
        )
        self._refresh_readiness(company_id)
        return {
            "file_id": file_id,
            "filename": file_meta["filename"],
            "mime": file_meta["mime"],
            "size_bytes": file_meta["size_bytes"],
            "sha256": file_meta["sha256"],
            "scan_status": scan_status,
            "flags": flags,
            "stored": False,
            "note": inspected["note"],
            "readiness": self.readiness(company_id),
        }

    # --------------------------------------------------------------- legal
    def list_legal_items(self, principal: Principal, company_id: str) -> List[Dict[str, Any]]:
        assert_can_view(principal, self.tenant_id)
        self._require_company(company_id, include_deleted=True)
        return self._legal_items_payload(company_id)

    def _legal_items_payload(self, company_id: str) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM company_legal_items WHERE tenant_id = ? AND company_id = ? ORDER BY created_at ASC",
                (self.tenant_id, company_id),
            ).fetchall()
        items: List[Dict[str, Any]] = []
        for row in rows:
            record = _row_to_dict(row)
            items.append(
                {
                    "item_id": record.get("item_id"),
                    "name": record.get("name"),
                    "authority": record.get("authority"),
                    "status": record.get("status"),
                    "instructions": record.get("instructions"),
                    "draft_disclaimer": record.get("draft_disclaimer"),
                    "created_at": record.get("created_at"),
                    "updated_at": record.get("updated_at"),
                }
            )
        return items

    # --------------------------------------------------------------- deletion
    def _mfa_required(self, company_id: str) -> bool:
        try:
            return bool(self._effective(company_id, "sec_require_mfa", False))
        except Exception:
            return False

    def _two_step_enrolled(self, user_id: str) -> bool:
        """Whether this account has a confirmed TOTP secret, not just a setting."""
        if not user_id:
            return False
        try:
            from core.two_step import TwoStepService

            return TwoStepService().enrolled(user_id)
        except Exception:
            return False

    def _recovery_days(self, company_id: str) -> int:
        try:
            value = self._effective(company_id, "company_delete_recovery_days", 7)
            days = int(value)
        except Exception:
            days = 7
        return max(0, min(days, 365))

    def _deletion_row(self, company_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM company_deletion_requests WHERE tenant_id = ? AND company_id = ? "
                "AND status <> 'CANCELLED' AND status <> 'COMPLETED' ORDER BY created_at DESC LIMIT 1",
                (self.tenant_id, company_id),
            ).fetchone()
        record = _row_to_dict(row)
        return record or None

    def _latest_deletion(self, company_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM company_deletion_requests WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (self.tenant_id, company_id),
            ).fetchone()
        record = _row_to_dict(row)
        return record or None

    def _mask_email(self, email: Optional[str]) -> str:
        text = str(email or "").strip()
        if not text or "@" not in text:
            return ""
        local, domain = text.split("@", 1)
        visible = local[:1]
        return f"{visible}{'*' * max(1, len(local) - 1)}@{domain}"

    def _deletion_payload(self, record: Optional[Dict[str, Any]], principal: Optional[Principal] = None) -> Optional[Dict[str, Any]]:
        if not record:
            return None
        export_status = record.get("export_status")
        export_available = export_status in ("READY", "EMAILED") and bool(record.get("export_ref"))
        status = str(record.get("status") or "")
        enrolled = self._two_step_enrolled(principal.user_id) if principal else None
        return {
            "request_id": record["request_id"],
            "company_id": record["company_id"],
            "status": status,
            "steps_done": _json_load(record.get("steps_done"), []),
            "removal_summary": _json_load(record.get("removal_summary"), {}),
            "previous_status": record.get("previous_status"),
            "export_status": export_status,
            "export_parts": record.get("export_parts"),
            "export_ready_at": record.get("export_ready_at"),
            "export_size_bytes": record.get("export_size_bytes"),
            "export_sha256": record.get("export_sha256"),
            "export_available": export_available,
            "export_filename": os.path.basename(str(record.get("export_ref") or "")),
            "export_download_path": (
                f"/api/v1/companies/{record['company_id']}/export" if export_available else None
            ),
            "email_status": record.get("email_status"),
            "email_recipient": record.get("email_recipient"),
            "download_confirmed_at": record.get("download_confirmed_at"),
            "purge_after": record.get("purge_after"),
            "purge_blocked_reason": record.get("purge_blocked_reason"),
            "recovery_days": record.get("recovery_days"),
            "mfa_required": self._mfa_required(record["company_id"]),
            "two_step_configured": True,
            "two_step_enrolled": enrolled,
            "can_cancel": status in ("AWAITING_NAME", "AWAITING_IDENTITY", "EXPORTING", "PENDING_DELETION"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "completed_at": record.get("completed_at"),
        }

    def get_deletion(self, company_id: str) -> Optional[Dict[str, Any]]:
        self.purge_due(company_id=company_id)
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

    def deletion_plan(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        """Non-mutating preview of what a deletion would do.

        The wizard shows this before it creates a deletion request, so the
        owner sees real counts, the real recovery window and whether email can
        actually be delivered on this deployment.
        """
        record = self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)
        recipient, verified = self._account_email(principal)
        return {
            "company_id": company_id,
            "company_name": record.get("name"),
            "removal_summary": self._removal_summary(company_id),
            "recovery_days": self._recovery_days(company_id),
            "mfa_required": self._mfa_required(company_id),
            "two_step_configured": True,
            "two_step_enrolled": self._two_step_enrolled(principal.user_id),
            "email_available": bool(verified and recipient),
            "email_recipient": self._mask_email(recipient) if verified and recipient else "",
            "export_format": "PDF, split into numbered parts and zipped when needed",
        }

    def request_deletion(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        record = self._require_company(company_id)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)

        if normalize_status(record["status"]) in (CompanyStatus.PENDING_EXPORT, CompanyStatus.PENDING_DELETION):
            existing = self._deletion_row(company_id)
            if existing:
                return self._deletion_payload(existing, principal)
            raise CompanySetupError(
                "DELETION_ALREADY_STARTED",
                "This company is already in the deletion workflow",
                status=409,
            )

        existing = self._deletion_row(company_id)
        if existing:
            return self._deletion_payload(existing, principal)

        now = _now()
        request_id = f"del_{uuid.uuid4().hex[:12]}"
        summary = self._removal_summary(company_id)
        steps = ["requested"]
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO company_deletion_requests (
                    request_id, tenant_id, company_id, status, steps_done, removal_summary,
                    export_status, export_parts, email_status, requested_by, created_at, updated_at,
                    previous_status, recovery_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    normalize_status(record["status"]),
                    self._recovery_days(company_id),
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
        return self._deletion_payload(self._deletion_row(company_id), principal)

    def _require_deletion(self, company_id: str) -> Dict[str, Any]:
        record = self._deletion_row(company_id)
        if not record:
            raise CompanySetupError("DELETION_NOT_REQUESTED", "Start the deletion flow first", status=409)
        return record

    def _update_deletion(self, request_id: str, **fields: Any) -> None:
        if not fields:
            return
        allowed = {
            "status",
            "steps_done",
            "export_status",
            "export_parts",
            "export_ref",
            "export_sha256",
            "export_size_bytes",
            "export_content_type",
            "export_ready_at",
            "email_status",
            "email_recipient",
            "download_confirmed_at",
            "purge_after",
            "purge_blocked_reason",
            "previous_status",
            "recovery_days",
            "completed_at",
            "updated_at",
        }
        assignments = []
        values: List[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            assignments.append(f"{key} = ?")
            if key in ("steps_done",):
                values.append(_json_dump(value))
            else:
                values.append(value)
        if not assignments:
            return
        assignments.append("updated_at = ?")
        values.append(_now())
        values.append(request_id)
        with db.get_connection() as conn:
            conn.execute(
                f"UPDATE company_deletion_requests SET {', '.join(assignments)} WHERE request_id = ?",
                tuple(values),
            )
            conn.commit()

    def _set_company_status(self, company_id: str, target: str) -> str:
        record = self._require_company(company_id, include_deleted=True)
        normalized = validate_transition(record["status"], target)
        now = _now()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE companies SET status = ?, updated_at = ? WHERE company_id = ? AND tenant_id = ?",
                (normalized, now, company_id, self.tenant_id),
            )
            conn.commit()
        self._refresh_portfolio()
        return normalized

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
        steps = _json_load(request.get("steps_done"), [])
        if "name_confirmed" not in steps:
            steps.append("name_confirmed")
        self._update_deletion(
            request["request_id"],
            status="AWAITING_IDENTITY",
            steps_done=steps,
            previous_status=normalize_status(record["status"]),
        )
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.delete.name_confirmed",
            {"request_id": request["request_id"], "mfa_required": mfa},
        )
        return self._deletion_payload(self._deletion_row(company_id), principal) or {}

    def confirm_delete_identity(
        self,
        principal: Principal,
        company_id: str,
        password: Optional[str] = None,
        two_step_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        record = self._require_company(company_id)
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

        if self._mfa_required(company_id):
            from core.two_step import TwoStepError, TwoStepService

            verifier = TwoStepService()
            delivered = str(two_step_code or "").strip()
            if not verifier.enrolled(principal.user_id):
                raise CompanySetupError(
                    "TWO_STEP_NOT_ENROLLED",
                    "Two-step verification is required. Set it up before deleting this company.",
                    status=409,
                    detail={"enrollment_required": True, "settings_path": "/settings/security"},
                )
            if not delivered:
                raise CompanySetupError(
                    "TWO_STEP_REQUIRED",
                    "Enter the current code from your authenticator app",
                    status=400,
                )
            try:
                ok, reason = verifier.verify_code(principal.user_id, delivered)
            except TwoStepError as err:
                raise CompanySetupError(err.code, err.message, status=err.status, detail=err.detail)
            if not ok:
                if reason == "TWO_STEP_LOCKED":
                    raise CompanySetupError(
                        "TWO_STEP_LOCKED",
                        "Too many incorrect codes. Try again shortly.",
                        status=429,
                    )
                raise CompanySetupError(
                    "INVALID_TWO_STEP_CODE",
                    "That two-step code is not valid",
                    status=403,
                )

        previous_status = normalize_status(record["status"])
        target = validate_transition(previous_status, CompanyStatus.PENDING_EXPORT)
        steps = _json_load(request.get("steps_done"), [])
        if "identity_confirmed" not in steps:
            steps.append("identity_confirmed")
        self._update_deletion(
            request["request_id"],
            status="EXPORTING",
            steps_done=steps,
            previous_status=previous_status,
            export_status="GENERATING",
            purge_blocked_reason=None,
        )
        self._set_company_status(company_id, target)
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.delete.identity_confirmed",
            {"request_id": request["request_id"], "previous_status": previous_status},
        )
        self._stop_company_work(company_id, principal)

        try:
            export = self._generate_export(company_id, request["request_id"])
        except Exception as exc:
            self._update_deletion(
                request["request_id"],
                export_status="FAILED",
                purge_blocked_reason="EXPORT_FAILED",
            )
            audit.record_event(
                self.tenant_id,
                company_id,
                principal.user_id,
                principal.role,
                "company.export.failed",
                {"request_id": request["request_id"], "error_type": type(exc).__name__},
            )
            return {
                "deletion": self._deletion_payload(self._deletion_row(company_id), principal),
                "export": {
                    "status": "FAILED",
                    "message": "The export could not be generated. Nothing has been purged.",
                },
            }

        return self._finalize_export(principal, company_id, export, transition=True)

    def retry_export(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        record = self._require_company(company_id, include_deleted=True)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)
        request = self._require_deletion(company_id)
        if request["status"] not in ("EXPORTING", "PENDING_DELETION"):
            raise CompanySetupError(
                "STEP_OUT_OF_ORDER",
                "The export can only be retried after identity confirmation",
                status=409,
                detail={"status": request["status"]},
            )
        self._update_deletion(request["request_id"], export_status="GENERATING", purge_blocked_reason=None)
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.export.retry_requested",
            {"request_id": request["request_id"]},
        )
        try:
            export = self._generate_export(company_id, request["request_id"])
        except Exception as exc:
            self._update_deletion(request["request_id"], export_status="FAILED", purge_blocked_reason="EXPORT_FAILED")
            audit.record_event(
                self.tenant_id,
                company_id,
                principal.user_id,
                principal.role,
                "company.export.failed",
                {"request_id": request["request_id"], "error_type": type(exc).__name__},
            )
            raise CompanySetupError(
                "EXPORT_FAILED",
                "The export could not be generated. Nothing has been purged.",
                status=500,
            )
        return self._finalize_export(
            principal,
            company_id,
            export,
            transition=normalize_status(record["status"]) == CompanyStatus.PENDING_EXPORT,
        )

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

    def _account_email(self, principal: Principal) -> tuple:
        """Return the signed-in account email and whether it is a verified identity.

        The only verified identity we can prove without an email challenge is
        the address on the authenticated account itself. A company profile
        email that is not tied to the signed-in account is never used for
        outbound deletion mail.
        """
        try:
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT email FROM users WHERE user_id = ? AND tenant_id = ?",
                    (principal.user_id, self.tenant_id),
                ).fetchone()
        except Exception:
            return None, False
        email = str(row["email"] if row else "").strip()
        return (email, True) if email else (None, False)

    def _export_base_dir(self) -> str:
        return os.path.abspath(os.environ.get("ZONATA_COMPANY_EXPORT_DIR") or DEFAULT_EXPORT_DIR)

    def _export_data(self, record: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        company_id = record["company_id"]
        return {
            "export_type": "ZONATA company export",
            "request_id": request_id,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "company": self._serialize(record),
            "build": self.get_build(company_id),
            "readiness": self.readiness(company_id),
            "sources": self._sources_payload(company_id),
            "connections": self._connections_payload(company_id),
            "files": self._files_payload(company_id).get("files", []),
            "legal_items": self._legal_items_payload(company_id),
            "audit": audit.list_events(self.tenant_id, company_id, limit=EXPORT_AUDIT_LIMIT),
            "counts": self._removal_summary(company_id).get("will_remove", {}),
        }

    def _generate_export(self, company_id: str, request_id: str) -> Dict[str, Any]:
        from core.company_setup.export import build_company_export

        record = self._require_company(company_id, include_deleted=True)
        data = self._export_data(record, request_id)
        base_dir = self._export_base_dir()
        os.makedirs(base_dir, exist_ok=True, mode=0o750)
        return build_company_export(data, base_dir, self.tenant_id, company_id, request_id)

    def _finalize_export(
        self,
        principal: Principal,
        company_id: str,
        export: Dict[str, Any],
        transition: bool = True,
    ) -> Dict[str, Any]:
        request = self._require_deletion(company_id)
        days = self._recovery_days(company_id)
        recipient, verified = self._account_email(principal)
        email_status = "SKIPPED_UNVERIFIED"
        email_detail = "The signed-in account has no verified email address; use the in-app download."
        if verified and recipient:
            from core.company_setup.email_adapter import export_email_adapter

            try:
                with open(export["path"], "rb") as handle:
                    content = handle.read()
                result = export_email_adapter.send(
                    tenant_id=self.tenant_id,
                    company_id=company_id,
                    company_name=(self._require_company(company_id, include_deleted=True).get("name") or "your company"),
                    recipient=recipient,
                    filename=export["filename"],
                    content=content,
                    content_type=export["content_type"],
                    recovery_days=days,
                )
                email_status = str(result.get("status") or "FAILED")
                email_detail = str(result.get("detail") or "")
            except Exception as exc:
                email_status = "FAILED"
                email_detail = "The email could not be sent. Use the in-app download instead."
                audit.record_event(
                    self.tenant_id,
                    company_id,
                    principal.user_id,
                    principal.role,
                    "company.export.email_failed",
                    {"request_id": request["request_id"], "error_type": type(exc).__name__},
                )

        now = _now()
        purge_after = now if days == 0 else now + days * 86400
        export_status = "EMAILED" if email_status == "SENT" else "READY"
        blocked = None if email_status == "SENT" else "WAITING_FOR_DOWNLOAD"
        steps = _json_load(request.get("steps_done"), [])
        for step in ("export_ready", "email_sent" if email_status == "SENT" else "in_app_download"):
            if step not in steps:
                steps.append(step)

        if transition:
            self._set_company_status(company_id, CompanyStatus.PENDING_DELETION)
        self._update_deletion(
            request["request_id"],
            status="PENDING_DELETION",
            steps_done=steps,
            export_status=export_status,
            export_parts=export.get("parts") or 1,
            export_ref=export.get("relative_ref"),
            export_sha256=export.get("sha256"),
            export_size_bytes=export.get("size_bytes"),
            export_content_type=export.get("content_type"),
            export_ready_at=now,
            email_status=email_status,
            email_recipient=self._mask_email(recipient),
            purge_after=purge_after,
            purge_blocked_reason=blocked,
            recovery_days=days,
        )
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.export.generated",
            {
                "request_id": request["request_id"],
                "filename": export.get("filename"),
                "parts": export.get("parts"),
                "pages": export.get("pages"),
                "sha256": export.get("sha256"),
                "size_bytes": export.get("size_bytes"),
                "archive": export.get("archive"),
                "replaced_characters": export.get("replaced_characters"),
            },
        )
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.export.email",
            {
                "request_id": request["request_id"],
                "status": email_status,
                "recipient": self._mask_email(recipient),
                "detail": email_detail,
            },
        )
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.delete.pending_purge",
            {
                "request_id": request["request_id"],
                "purge_after": purge_after,
                "recovery_days": days,
                "email_status": email_status,
            },
        )

        purged = None
        if days == 0 and email_status == "SENT":
            purged = self._purge_company_data(
                company_id,
                request["request_id"],
                principal.user_id,
                principal.role,
                reason="IMMEDIATE_WINDOW_AFTER_EMAIL",
            )

        payload = self._deletion_payload(self._deletion_row(company_id) or self._latest_deletion(company_id), principal)
        return {
            "deletion": payload,
            "export": {
                "status": export_status,
                "filename": export.get("filename"),
                "parts": export.get("parts"),
                "pages": export.get("pages"),
                "size_bytes": export.get("size_bytes"),
                "sha256": export.get("sha256"),
                "content_type": export.get("content_type"),
                "archive": export.get("archive"),
                "download_path": f"/api/v1/companies/{company_id}/export",
                "message": (
                    "The export was emailed. The recovery window has started."
                    if email_status == "SENT"
                    else email_detail or "Download the export from this device before the recovery window ends."
                ),
            },
            "email": {
                "status": email_status,
                "recipient": self._mask_email(recipient),
                "detail": email_detail,
            },
            "recovery_days": days,
            "purge_after": purge_after,
            "purged": bool(purged),
        }

    def cancel_deletion(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        record = self._require_company(company_id, include_deleted=True)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)
        request = self._require_deletion(company_id)
        if request["status"] == "COMPLETED" or normalize_status(record["status"]) == CompanyStatus.DELETED:
            raise CompanySetupError("ALREADY_DELETED", "This company has already been deleted", status=409)

        now = _now()
        previous_status = normalize_status(record["status"])
        desired = normalize_status(request.get("previous_status") or "")
        restore_to = None
        if previous_status in (CompanyStatus.PENDING_EXPORT, CompanyStatus.PENDING_DELETION):
            candidates = [desired] if desired else []
            candidates.extend([CompanyStatus.OPERATIONAL, CompanyStatus.NEEDS_ATTENTION])
            for candidate in candidates:
                if not candidate:
                    continue
                try:
                    restore_to = validate_transition(previous_status, candidate)
                    break
                except InvalidTransition:
                    continue
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE company_deletion_requests SET status = 'CANCELLED', updated_at = ?, purge_blocked_reason = NULL "
                "WHERE request_id = ?",
                (now, request["request_id"]),
            )
            if restore_to:
                conn.execute(
                    "UPDATE companies SET status = ?, updated_at = ? WHERE company_id = ? AND tenant_id = ?",
                    (restore_to, now, company_id, self.tenant_id),
                )
            conn.commit()
        self._refresh_portfolio()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.delete.cancelled",
            {
                "request_id": request["request_id"],
                "restored_status": restore_to or previous_status,
                "recovery_days": request.get("recovery_days"),
                "export_status": request.get("export_status"),
            },
        )
        return {"cancelled": True, "company_status": normalize_status(restore_to or previous_status)}

    def _export_file_path(self, request: Dict[str, Any]) -> str:
        base = self._export_base_dir()
        ref = str(request.get("export_ref") or "")
        if not ref:
            raise CompanySetupError("EXPORT_NOT_READY", "No company export is available yet", status=409)
        candidate = os.path.realpath(os.path.join(base, ref))
        base_real = os.path.realpath(base)
        if candidate != base_real and not candidate.startswith(base_real + os.sep):
            raise CompanySetupError("EXPORT_NOT_FOUND", "The export file is not available", status=404)
        if not os.path.isfile(candidate):
            raise CompanySetupError(
                "EXPORT_NOT_FOUND",
                "The export file is no longer on this deployment",
                status=410,
            )
        return candidate

    def download_export_file(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        record = self._require_company(company_id, include_deleted=True)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)
        request = self._latest_deletion(company_id)
        if not request or request.get("export_status") not in ("READY", "EMAILED"):
            raise CompanySetupError("EXPORT_NOT_READY", "No company export is available yet", status=409)
        path = self._export_file_path(request)
        with open(path, "rb") as handle:
            content = handle.read()
        expected = str(request.get("export_sha256") or "")
        if expected and hashlib.sha256(content).hexdigest() != expected:
            raise CompanySetupError(
                "EXPORT_CORRUPT",
                "The export file failed its integrity check and will not be served",
                status=500,
            )

        now = _now()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE company_deletion_requests SET download_confirmed_at = ?, purge_blocked_reason = ?, updated_at = ? "
                "WHERE request_id = ? AND download_confirmed_at IS NULL",
                (now, None if request.get("email_status") == "SENT" else "DOWNLOADED", now, request["request_id"]),
            )
            conn.commit()
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.export.downloaded",
            {"request_id": request["request_id"], "size_bytes": len(content)},
        )

        if (
            request.get("status") == "PENDING_DELETION"
            and request.get("email_status") != "SENT"
            and now >= float(request.get("purge_after") or 0)
        ):
            self._purge_company_data(
                company_id,
                request["request_id"],
                principal.user_id,
                principal.role,
                reason="DOWNLOADED_AFTER_WINDOW",
            )
        elif request.get("status") == "PENDING_DELETION":
            self.purge_due(company_id=company_id)

        return {
            "__file__": content,
            "filename": os.path.basename(path),
            "content_type": request.get("export_content_type") or (
                "application/zip" if path.lower().endswith(".zip") else "application/pdf"
            ),
            "size_bytes": len(content),
            "sha256": expected or hashlib.sha256(content).hexdigest(),
        }

    def download_export(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        """Metadata-only view used by tests and non-browser clients."""
        payload = self.download_export_file(principal, company_id)
        return {
            "filename": payload["filename"],
            "content_type": payload["content_type"],
            "size_bytes": payload["size_bytes"],
            "sha256": payload["sha256"],
            "download_path": f"/api/v1/companies/{company_id}/export",
        }

    def purge_now(self, principal: Principal, company_id: str) -> Dict[str, Any]:
        record = self._require_company(company_id, include_deleted=True)
        granted = self._granted(company_id, principal.user_id)
        assert_can_delete(principal, self.tenant_id, granted=granted)
        request = self._require_deletion(company_id)
        if request["status"] != "PENDING_DELETION":
            raise CompanySetupError(
                "STEP_OUT_OF_ORDER",
                "The deletion is not waiting for its recovery window",
                status=409,
                detail={"status": request["status"]},
            )
        now = _now()
        if float(request.get("purge_after") or 0) > now:
            raise CompanySetupError(
                "RECOVERY_WINDOW_ACTIVE",
                "The recovery window has not ended yet",
                status=409,
                detail={"purge_after": request.get("purge_after")},
            )
        if request.get("email_status") != "SENT" and not request.get("download_confirmed_at"):
            raise CompanySetupError(
                "EXPORT_NOT_DELIVERED",
                "Download the export or configure email delivery before purging",
                status=409,
            )
        return self._purge_company_data(
            company_id,
            request["request_id"],
            principal.user_id,
            principal.role,
            reason="OWNER_CONFIRMED_DUE",
        )

    def purge_due(self, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        now = _now()
        clauses = ["tenant_id = ?", "status = 'PENDING_DELETION'", "purge_after IS NOT NULL", "purge_after <= ?"]
        params: List[Any] = [self.tenant_id, now]
        if company_id:
            clauses.append("company_id = ?")
            params.append(company_id)
        with db.get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM company_deletion_requests WHERE {' AND '.join(clauses)}", tuple(params)
            ).fetchall()
        purged: List[Dict[str, Any]] = []
        for row in rows:
            request = _row_to_dict(row)
            if request.get("email_status") != "SENT" and not request.get("download_confirmed_at"):
                self._update_deletion(request["request_id"], purge_blocked_reason="WAITING_FOR_DOWNLOAD")
                continue
            result = self._purge_company_data(
                request["company_id"],
                request["request_id"],
                str(request.get("requested_by") or "system"),
                "SYSTEM",
                reason="RECOVERY_WINDOW_ENDED",
            )
            purged.append(result)
        return purged

    def _company_scoped_tables(self) -> Dict[str, bool]:
        """Map table -> has_tenant_id for every company-scoped base table."""
        found: Dict[str, bool] = {}
        dialect = getattr(db, "dialect", "sqlite")
        if dialect == "postgresql":
            with db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT table_name, column_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_type = 'BASE TABLE' "
                    "AND column_name IN ('company_id', 'tenant_id')"
                ).fetchall()
            for row in rows:
                table = str(row[0])
                if str(row[1]) == "tenant_id":
                    found[table] = True
                else:
                    found.setdefault(table, False)
            return found

        with db.get_connection() as conn:
            tables = [
                str(row[0])
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            ]
            for table in tables:
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
                    continue
                columns = {
                    str(row[1]).lower()
                    for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
                }
                if "company_id" in columns:
                    found[table] = "tenant_id" in columns
        return found

    def _delete_company_scoped_rows(self, company_id: str) -> List[Dict[str, str]]:
        errors: List[Dict[str, str]] = []
        tables = self._company_scoped_tables()
        for table, has_tenant in sorted(tables.items()):
            if table in PURGE_KEEP_TABLES:
                continue
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
                continue
            try:
                with db.get_connection() as conn:
                    if has_tenant:
                        conn.execute(
                            f'DELETE FROM "{table}" WHERE company_id = ? AND tenant_id = ?',
                            (company_id, self.tenant_id),
                        )
                    else:
                        conn.execute(f'DELETE FROM "{table}" WHERE company_id = ?', (company_id,))
                    conn.commit()
            except Exception as exc:
                errors.append({"table": table, "error_type": type(exc).__name__})
        return errors

    def _delete_company_storage(self, company_id: str) -> None:
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(company_id or ""))
        if not safe_id or safe_id in (".", ".."):
            return
        try:
            from core.document_generator import DocumentGenerator

            base = DocumentGenerator().base_dir
        except Exception:
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage"))
        target = os.path.realpath(os.path.join(base, "companies", safe_id))
        root = os.path.realpath(os.path.join(base, "companies"))
        if target.startswith(root + os.sep) and os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)

    def _stop_company_work(self, company_id: str, principal: Principal) -> bool:
        cancelled = False
        try:
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT workflow_run_id FROM company_build_runs WHERE tenant_id = ? AND company_id = ? "
                    "AND workflow_run_id IS NOT NULL ORDER BY created_at DESC LIMIT 1",
                    (self.tenant_id, company_id),
                ).fetchone()
            run_id = str(row["workflow_run_id"] if row else "").strip()
            if run_id:
                from core.durable_workflow_runtime import get_workflow_runtime

                get_workflow_runtime(self.tenant_id).cancel_workflow(run_id, reason="COMPANY_DELETION")
                cancelled = True
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE company_build_runs SET phase_state = 'CANCELLED', "
                    "failure_reason = 'Stopped because deletion was requested', updated_at = ? "
                    "WHERE tenant_id = ? AND company_id = ? AND phase_state IN ('RUNNING', 'PENDING')",
                    (_now(), self.tenant_id, company_id),
                )
                conn.commit()
        except Exception:
            cancelled = False
        audit.record_event(
            self.tenant_id,
            company_id,
            principal.user_id,
            principal.role,
            "company.work.stopped",
            {"workflow_cancelled": cancelled},
        )
        return cancelled

    def _purge_company_data(
        self,
        company_id: str,
        request_id: str,
        actor_id: str,
        actor_role: str,
        reason: str,
    ) -> Dict[str, Any]:
        record = self._require_company(company_id, include_deleted=True)
        summary = self._removal_summary(company_id)
        errors = self._delete_company_scoped_rows(company_id)
        self._delete_company_storage(company_id)
        now = _now()
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE companies SET
                    status = ?, deleted_at = ?, deleted_by = ?, updated_at = ?,
                    description = NULL, owner_email = NULL, website = NULL,
                    business_model = NULL, target_customers = NULL, setup_notes = NULL,
                    assets = '[]', revenue = 0, revenue_amount = NULL, cost = 0, contribution = 0
                WHERE company_id = ? AND tenant_id = ?
                """,
                (CompanyStatus.DELETED, now, actor_id, now, company_id, self.tenant_id),
            )
            conn.execute(
                "UPDATE company_deletion_requests SET status = 'COMPLETED', completed_at = ?, updated_at = ?, "
                "purge_blocked_reason = NULL WHERE request_id = ? AND tenant_id = ?",
                (now, now, request_id, self.tenant_id),
            )
            conn.commit()
        self._refresh_portfolio()
        audit.record_event(
            self.tenant_id,
            company_id,
            actor_id,
            actor_role,
            "company.delete.purged",
            {
                "request_id": request_id,
                "reason": reason,
                "removed": summary.get("will_remove", {}),
                "kept": "minimal company record and audit trail",
                "purge_errors": errors,
                "completed_at": now,
            },
        )
        return {
            "purged": True,
            "company_id": company_id,
            "request_id": request_id,
            "completed_at": now,
            "removed": summary.get("will_remove", {}),
            "purge_errors": errors,
        }


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
