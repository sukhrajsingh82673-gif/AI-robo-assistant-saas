"""
ZONATA Declarative Industry Pack Loader & Provisioning Engine (OpenCode Step 1H)
Installs data-driven industry blueprints into a tenant/company without any hardcoded branching.
"""

import json
import os
import pathlib
import time
from typing import Any, Dict, List, Optional
import uuid
import yaml

from core.db import db, tenant_scoped
from core.industry_packs.isic import get_isic_details
from core.industry_packs.schema import (
    MalformedChartOfAccountsError,
    PackValidationError,
    validate_industry_pack_dict,
)
from core.ledger.kernel import LedgerKernel
from core.ledger.schema import AccountType


def ensure_industry_pack_tables(conn: Optional[Any] = None) -> None:
    """Ensures installed_industry_packs and company_folio_types tables exist."""
    import pathlib
    from core.db import db, DatabaseDialect

    migration_file = "0017_industry_packs.sql"
    root_dir = pathlib.Path(__file__).resolve().parent.parent.parent

    ddl_sqlite = """
    CREATE TABLE IF NOT EXISTS installed_industry_packs (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        company_id TEXT NOT NULL,
        pack_id TEXT NOT NULL,
        name TEXT NOT NULL,
        version TEXT NOT NULL,
        isic_code TEXT NOT NULL,
        raw_manifest TEXT NOT NULL,
        installed_at REAL NOT NULL,
        UNIQUE (tenant_id, company_id, pack_id)
    );

    CREATE TABLE IF NOT EXISTS company_folio_types (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        company_id TEXT NOT NULL,
        pack_id TEXT NOT NULL,
        folio_type TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        config TEXT NOT NULL,
        created_at REAL NOT NULL,
        UNIQUE (tenant_id, company_id, folio_type)
    );
    """

    def _exec(target_conn):
        if db.pg_tables_ready(target_conn, "installed_industry_packs", "company_folio_types"):
            return
        if db.dialect == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                target_conn.executescript(sql_path.read_text(encoding="utf-8"))
            else:
                target_conn.executescript(ddl_sqlite)
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                target_conn.execute(sql_path.read_text(encoding="utf-8"))
            # Ensure column types are REAL (epoch seconds) across all environments
            target_conn.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'company_folio_types' AND column_name = 'created_at' AND data_type IN ('timestamp with time zone', 'timestamp without time zone')
                ) THEN
                    ALTER TABLE company_folio_types ALTER COLUMN created_at TYPE REAL USING EXTRACT(EPOCH FROM created_at);
                END IF;
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'installed_industry_packs' AND column_name = 'installed_at' AND data_type IN ('timestamp with time zone', 'timestamp without time zone')
                ) THEN
                    ALTER TABLE installed_industry_packs ALTER COLUMN installed_at TYPE REAL USING EXTRACT(EPOCH FROM installed_at);
                END IF;
            END $$;
            """)

    if conn is not None:
        _exec(conn)
    else:
        with db.get_connection() as c:
            _exec(c)


class IndustryPackLoader:
    """Loads, validates, and installs declarative zonata.industry-pack/v1 blueprints."""

    def __init__(self, ledger_kernel: Optional[LedgerKernel] = None):
        self.ledger = ledger_kernel or LedgerKernel()
        ensure_industry_pack_tables()

    def load_pack_from_file(self, file_path: str) -> Dict[str, Any]:
        """Loads and parses an industry pack from a YAML or JSON file."""
        p = pathlib.Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Industry pack file not found at {file_path}")

        text = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text)
        elif p.suffix == ".json":
            data = json.loads(text)
        else:
            raise ValueError(f"Unsupported industry pack extension: {p.suffix}")

        return validate_industry_pack_dict(data)

    @tenant_scoped
    def install_pack(
        self,
        tenant_id: str,
        company_id: str,
        pack_data: Dict[str, Any],
        caller_principal_type: str = "HUMAN",
    ) -> Dict[str, Any]:
        """Installs a validated industry pack into a tenant/company. Enforces Rule 15."""
        if caller_principal_type in ("AGENT", "AI_EMPLOYEE", "MODEL", "SYSTEM_AGENT") or caller_principal_type.startswith(("agt_", "ai_emp_")):
            raise PermissionError(f"Rule 15 Violation: Principal '{caller_principal_type}' cannot mutate industry packs or pack review status")

        validated = validate_industry_pack_dict(pack_data)
        meta = validated["metadata"]
        now = time.time()

        accounts_created: List[Dict[str, Any]] = []
        accounts_skipped: List[str] = []

        # 1. Provision Chart of Accounts
        for acct_def in validated.get("chart_of_accounts", []):
            code = acct_def["code"].strip()
            existing = self.ledger.get_account_by_code(tenant_id, company_id, code)
            if existing:
                accounts_skipped.append(code)
            else:
                acct_id = self.ledger.create_account(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    code=code,
                    name=acct_def["name"],
                    account_type=AccountType(acct_def["type"]),
                    currency=acct_def["currency"],
                )
                accounts_created.append({"account_id": acct_id, "code": code, "name": acct_def["name"]})

        # 2. Provision Folio Types
        folio_types_installed: List[str] = []
        with db.get_connection() as conn:
            cur = conn.cursor()
            for ft in validated.get("folio_types", []):
                ft_code = ft["folio_type"]
                ft_id = f"cft_{uuid.uuid4().hex[:16]}"
                config_json = json.dumps({
                    "required_documents": ft.get("required_documents", []),
                    "optional_documents": ft.get("optional_documents", []),
                    "required_tasks": ft.get("required_tasks", []),
                })
                if db.is_postgresql():
                    cur.execute(
                        """
                        INSERT INTO company_folio_types (
                            id, tenant_id, company_id, pack_id, folio_type, name, description, config, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (tenant_id, company_id, folio_type) DO UPDATE SET
                            pack_id = EXCLUDED.pack_id,
                            name = EXCLUDED.name,
                            description = EXCLUDED.description,
                            config = EXCLUDED.config,
                            created_at = EXCLUDED.created_at
                        """,
                        (
                            ft_id,
                            tenant_id,
                            company_id,
                            meta["pack_id"],
                            ft_code,
                            ft.get("name", ft_code),
                            ft.get("description", ""),
                            config_json,
                            now,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO company_folio_types (
                            id, tenant_id, company_id, pack_id, folio_type, name, description, config, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (tenant_id, company_id, folio_type) DO UPDATE SET
                            pack_id = EXCLUDED.pack_id,
                            name = EXCLUDED.name,
                            description = EXCLUDED.description,
                            config = EXCLUDED.config
                        """,
                        (
                            ft_id,
                            tenant_id,
                            company_id,
                            meta["pack_id"],
                            ft_code,
                            ft.get("name", ft_code),
                            ft.get("description", ""),
                            config_json,
                            now,
                        ),
                    )
                folio_types_installed.append(ft_code)

            # 3. Record Installed Pack in Registry
            inst_id = f"inst_{uuid.uuid4().hex[:16]}"
            raw_manifest = json.dumps(validated)
            if db.is_postgresql():
                cur.execute(
                    """
                    INSERT INTO installed_industry_packs (
                        id, tenant_id, company_id, pack_id, name, version, isic_code, raw_manifest, installed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (tenant_id, company_id, pack_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        version = EXCLUDED.version,
                        isic_code = EXCLUDED.isic_code,
                        raw_manifest = EXCLUDED.raw_manifest,
                        installed_at = EXCLUDED.installed_at
                    """,
                    (
                        inst_id,
                        tenant_id,
                        company_id,
                        meta["pack_id"],
                        meta["name"],
                        meta["version"],
                        meta["industry_code"],
                        raw_manifest,
                        now,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO installed_industry_packs (
                        id, tenant_id, company_id, pack_id, name, version, isic_code, raw_manifest, installed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (tenant_id, company_id, pack_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        version = EXCLUDED.version,
                        isic_code = EXCLUDED.isic_code,
                        raw_manifest = EXCLUDED.raw_manifest,
                        installed_at = EXCLUDED.installed_at
                    """,
                    (
                        inst_id,
                        tenant_id,
                        company_id,
                        meta["pack_id"],
                        meta["name"],
                        meta["version"],
                        meta["industry_code"],
                        raw_manifest,
                        now,
                    ),
                )
            conn.commit()

        isic_info = get_isic_details(meta["industry_code"])

        return {
            "status": "INSTALLED",
            "installation_id": inst_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "pack_id": meta["pack_id"],
            "name": meta["name"],
            "version": meta["version"],
            "isic_code": meta["industry_code"],
            "isic_name": isic_info["name"] if isic_info else "",
            "accounts_created_count": len(accounts_created),
            "accounts_skipped_count": len(accounts_skipped),
            "folio_types_provisioned": folio_types_installed,
            "templates_count": len(validated.get("document_templates", [])),
            "workflows_count": len(validated.get("workflows", [])),
        }

    @tenant_scoped
    def get_installed_pack(self, tenant_id: str, company_id: str, pack_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves installed pack details for a company."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT pack_id, name, version, isic_code, raw_manifest, installed_at
                FROM installed_industry_packs
                WHERE tenant_id = ? AND company_id = ? AND pack_id = ?
                """,
                (tenant_id, company_id, pack_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "pack_id": row[0],
                "name": row[1],
                "version": row[2],
                "isic_code": row[3],
                "manifest": json.loads(row[4]),
                "installed_at": row[5],
            }
