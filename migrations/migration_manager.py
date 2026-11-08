"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Production Schema Migration Engine (Alembic-Equivalent)
Tracks versioned migrations, validates cryptographic checksums, and executes atomic DDL transactions.
"""

import os
import re
import sys
import time
import hashlib
import logging
from typing import List, Dict, Tuple, Optional
import sqlite3

logger = logging.getLogger("zonata.migrations")

MIGRATIONS_DIR = os.path.dirname(os.path.abspath(__file__))

_DOLLAR_QUOTE_RE = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$")


def split_sql_statements(sql_content: str, dialect: str = "sqlite") -> List[str]:
    """Split a migration file into executable statements.

    The previous implementation split on every semicolon.  That corrupts
    SQLite ``CREATE TRIGGER ... BEGIN ... END`` bodies and PostgreSQL
    dollar-quoted function bodies.  This splitter is deliberately small and
    dependency-free:

    * SQLite uses ``sqlite3.complete_statement``, which understands triggers.
    * PostgreSQL handles single/double quotes, line/block comments, and
      dollar-quoted bodies without needing a PL/pgSQL parser.
    """
    if not sql_content or not sql_content.strip():
        return []

    if (dialect or "").lower() == "sqlite":
        statements: List[str] = []
        buffer = ""
        for line in sql_content.splitlines(keepends=True):
            buffer += line
            if sqlite3.complete_statement(buffer):
                statement = buffer.strip()
                if statement:
                    statements.append(statement)
                buffer = ""
        if buffer.strip():
            statements.append(buffer.strip())
        return statements

    statements = []
    buffer: List[str] = []
    index = 0
    length = len(sql_content)
    state = "normal"
    dollar_tag = ""
    while index < length:
        char = sql_content[index]
        nxt = sql_content[index + 1] if index + 1 < length else ""

        if state == "normal":
            if char == "'":
                state = "single"
                buffer.append(char)
            elif char == '"':
                state = "double"
                buffer.append(char)
            elif char == "-" and nxt == "-":
                state = "line_comment"
                buffer.append("--")
                index += 2
                continue
            elif char == "/" and nxt == "*":
                state = "block_comment"
                buffer.append("/*")
                index += 2
                continue
            elif char == "$":
                match = _DOLLAR_QUOTE_RE.match(sql_content, index)
                if match:
                    dollar_tag = match.group(0)
                    state = "dollar"
                    buffer.append(dollar_tag)
                    index += len(dollar_tag)
                    continue
                buffer.append(char)
            elif char == ";":
                statement = "".join(buffer).strip()
                if statement:
                    statements.append(statement)
                buffer = []
            else:
                buffer.append(char)
        elif state == "single":
            buffer.append(char)
            if char == "'":
                if nxt == "'":
                    buffer.append("'")
                    index += 2
                    continue
                state = "normal"
        elif state == "double":
            buffer.append(char)
            if char == '"':
                if nxt == '"':
                    buffer.append('"')
                    index += 2
                    continue
                state = "normal"
        elif state == "line_comment":
            buffer.append(char)
            if char == "\n":
                state = "normal"
        elif state == "block_comment":
            buffer.append(char)
            if char == "*" and nxt == "/":
                buffer.append("/")
                index += 2
                state = "normal"
                continue
        elif state == "dollar":
            if sql_content.startswith(dollar_tag, index):
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                state = "normal"
                continue
            buffer.append(char)
        index += 1

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements

class MigrationManager:
    def __init__(self, db_conn_factory=None):
        self.db_conn_factory = db_conn_factory or self._default_conn_factory

    def _default_conn_factory(self):
        from core.database_engine import engine, WorkloadType
        return engine.pools[WorkloadType.CONTROL_PLANE].acquire()

    def init_migration_table(self, conn):
        """Ensure schema_migrations table exists."""
        sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at REAL NOT NULL,
            execution_time_ms REAL NOT NULL,
            status TEXT NOT NULL
        );
        """
        conn.execute(sql)
        conn.commit()

    def get_applied_migrations(self, conn) -> Dict[str, str]:
        """Return dict of version -> checksum for all applied migrations."""
        self.init_migration_table(conn)
        cursor = conn.execute("SELECT version, checksum FROM schema_migrations WHERE status = 'APPLIED' ORDER BY version ASC")
        return {row[0]: row[1] for row in cursor.fetchall()}

    def get_available_migrations(self, dialect: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """Scan migrations directory for .sql files matching common + dialect."""
        from core.database_engine import engine
        dialect = dialect or engine.dialect
        dirs_to_scan = [
            os.path.join(MIGRATIONS_DIR, "common"),
            os.path.join(MIGRATIONS_DIR, "pg" if dialect == "postgresql" else "sqlite")
        ]
        available = []
        for d in dirs_to_scan:
            if not os.path.exists(d):
                continue
            for fname in sorted(os.listdir(d)):
                if fname.endswith(".sql"):
                    parts = fname.split("_", 1)
                    if len(parts) == 2:
                        version = parts[0]
                        name = parts[1][:-4]
                        available.append((version, name, os.path.join(d, fname)))
        return sorted(available, key=lambda x: x[0])

    def calculate_checksum(self, filepath: str) -> str:
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        return sha.hexdigest()

    def apply_pending_migrations(self) -> List[Dict]:
        """Apply all pending migrations in strict sequential order."""
        applied_results = []
        from core.database_engine import engine, WorkloadType
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            self.init_migration_table(conn)
            applied = self.get_applied_migrations(conn)
            available = self.get_available_migrations()

            for version, name, filepath in available:
                file_checksum = self.calculate_checksum(filepath)
                if version in applied:
                    if applied[version] != file_checksum:
                        raise ValueError(f"Migration checksum mismatch for version {version}! Database: {applied[version]}, File: {file_checksum}")
                    continue

                # Apply migration
                logger.info(f"Applying migration {version}_{name}...")
                start_time = time.time()
                with open(filepath, "r", encoding="utf-8") as f:
                    sql_content = f.read()

                # Execute statement by statement.  Use the dialect-aware
                # splitter so trigger bodies and dollar-quoted functions are
                # not torn apart at their internal semicolons.
                statements = split_sql_statements(sql_content, dialect=getattr(engine, "dialect", "sqlite"))
                for stmt in statements:
                    conn.execute(stmt)

                duration_ms = (time.time() - start_time) * 1000.0
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, checksum, applied_at, execution_time_ms, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (version, name, file_checksum, time.time(), duration_ms, "APPLIED")
                )
                applied_results.append({
                    "version": version,
                    "name": name,
                    "checksum": file_checksum,
                    "duration_ms": duration_ms
                })

        return applied_results

    def get_status(self) -> Dict:
        """Report on migration status across files and database."""
        from core.database_engine import engine, WorkloadType
        with engine.connection(workload=WorkloadType.CONTROL_PLANE) as conn:
            self.init_migration_table(conn)
            applied = self.get_applied_migrations(conn)
            available = self.get_available_migrations()

            status_list = []
            for version, name, filepath in available:
                is_applied = version in applied
                status_list.append({
                    "version": version,
                    "name": name,
                    "applied": is_applied,
                    "checksum": self.calculate_checksum(filepath)
                })

            return {
                "total_available": len(available),
                "total_applied": len(applied),
                "pending": len(available) - len(applied),
                "migrations": status_list
            }

if __name__ == "__main__":
    mgr = MigrationManager()
    status = mgr.get_status()
    print("Migration Status:", status)
