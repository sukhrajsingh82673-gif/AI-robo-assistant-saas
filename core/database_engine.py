"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Distributed Production Database Engine & Connection Pool Architecture
Supports authoritative PostgreSQL (production) and hardened SQLite (local/test/dev).
"""

import os
import sys
import time
import json
import sqlite3
import threading
import logging
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from contextlib import contextmanager

logger = logging.getLogger("zonata.db")

class DatabaseDialect:
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

class WorkloadType:
    CONTROL_PLANE = "CONTROL_PLANE"
    READ = "READ"
    WRITE = "WRITE"

class DatabaseException(Exception):
    """Base exception for database operations."""
    pass

class ConnectionPoolExhausted(DatabaseException):
    """Raised when admission control or pool limit rejects connection request."""
    pass

class OptimisticLockError(DatabaseException):
    """Raised when a concurrent modification is detected via version mismatch."""
    pass

class TransactionTimeout(DatabaseException):
    """Raised when a transaction exceeds the maximum allowed duration."""
    pass

class PooledConnection:
    """Wrapper around raw DB connection with activity tracking and isolation."""
    def __init__(self, raw_conn: Any, dialect: str, pool_type: str):
        self.raw_conn = raw_conn
        self.dialect = dialect
        self.pool_type = pool_type
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.in_use = False
        self.transaction_active = False

    def execute(self, sql: str, params: Union[Tuple, List, Dict] = ()):
        self.last_used_at = time.time()
        if self.dialect == DatabaseDialect.SQLITE:
            return self.raw_conn.execute(sql, params)
        else:
            # PostgreSQL protocol simulation / driver execution
            cursor = self.raw_conn.cursor()
            cursor.execute(sql, params)
            return cursor

    def commit(self):
        self.raw_conn.commit()
        self.transaction_active = False

    def rollback(self):
        try:
            self.raw_conn.rollback()
        except Exception as e:
            logger.warning(f"Rollback error: {e}")
        self.transaction_active = False

    def close(self):
        try:
            self.raw_conn.close()
        except Exception:
            pass

class DeferredPooledConnection:
    """Proxy pooled connection returned during module import when live database is unreachable."""
    def __init__(self, dialect: str, pool_type: str):
        self.raw_conn = None
        self.dialect = dialect
        self.pool_type = pool_type
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.in_use = True
        self.transaction_active = False

    def execute(self, sql: str, params: Union[Tuple, List, Dict] = ()):
        class DummyCursor:
            def fetchone(self): return None
            def fetchall(self): return []
            @property
            def rowcount(self): return 0
            def __iter__(self): return iter([])
        return DummyCursor()

    def commit(self):
        self.transaction_active = False

    def rollback(self):
        self.transaction_active = False

    def close(self):
        pass


class DatabaseConnectionPool:
    """
    Production-grade multi-workload connection pool with admission control,
    idle recycling, health checks, and strict pool exhaustion guards.
    """
    def __init__(
        self,
        dialect: str,
        connection_factory: Callable[[], Any],
        min_pool_size: int = 5,
        max_pool_size: int = 25,
        connection_timeout: float = 30.0,
        idle_timeout: float = 300.0,
        max_lifetime: float = 3600.0,
        pool_type: str = WorkloadType.CONTROL_PLANE,
        deferred_mode: bool = False
    ):
        self.dialect = dialect
        self.connection_factory = connection_factory
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        self.max_lifetime = max_lifetime
        self.pool_type = pool_type
        self._deferred_import_mode = deferred_mode

        self._pool: List[PooledConnection] = []
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._closed = False
        self._active_connections = 0

        # Pre-warm minimum pool only if not deferred
        if not self._deferred_import_mode:
            self._prewarm()

    def _prewarm(self):
        with self._lock:
            for _ in range(self.min_pool_size):
                try:
                    raw = self.connection_factory()
                    wrapped = PooledConnection(raw, self.dialect, self.pool_type)
                    self._pool.append(wrapped)
                    self._active_connections += 1
                except Exception as e:
                    logger.warning(f"Failed to prewarm pool connection: {e}")
                    break

    def acquire(self, timeout: Optional[float] = None) -> Union[PooledConnection, DeferredPooledConnection]:
        """Acquire a verified connection from the pool with admission control."""
        if self._deferred_import_mode:
            return DeferredPooledConnection(self.dialect, self.pool_type)

        timeout = timeout or self.connection_timeout
        start_time = time.time()

        with self._lock:
            while True:
                if self._closed:
                    raise DatabaseException("Database connection pool is closed.")

                # Clean expired idle connections
                now = time.time()
                for conn in list(self._pool):
                    if not conn.in_use and (now - conn.created_at > self.max_lifetime or now - conn.last_used_at > self.idle_timeout):
                        self._pool.remove(conn)
                        conn.close()
                        self._active_connections -= 1

                # Check for idle connection
                for conn in self._pool:
                    if not conn.in_use:
                        conn.in_use = True
                        conn.last_used_at = now
                        return conn

                # Can we create a new connection?
                if self._active_connections < self.max_pool_size:
                    try:
                        raw = self.connection_factory()
                        conn = PooledConnection(raw, self.dialect, self.pool_type)
                        conn.in_use = True
                        self._pool.append(conn)
                        self._active_connections += 1
                        return conn
                    except Exception as e:
                        raise DatabaseException(f"Failed to create new pool connection: {e}")

                # Pool exhausted - wait with timeout
                remaining = timeout - (time.time() - start_time)
                if remaining <= 0:
                    raise ConnectionPoolExhausted(
                        f"Database pool exhausted for {self.pool_type} "
                        f"(Active: {self._active_connections}/{self.max_pool_size})"
                    )

                self._cond.wait(timeout=min(remaining, 1.0))

    def release(self, conn: Union[PooledConnection, DeferredPooledConnection]):
        """Release connection back to pool."""
        if isinstance(conn, DeferredPooledConnection):
            return
        with self._lock:
            if conn.transaction_active:
                conn.rollback()
            conn.in_use = False
            conn.last_used_at = time.time()
            self._cond.notify()

    def close_all(self):
        """Gracefully terminate all pooled connections."""
        with self._lock:
            self._closed = True
            for conn in self._pool:
                conn.close()
            self._pool.clear()
            self._active_connections = 0
            self._cond.notify_all()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            in_use_count = sum(1 for c in self._pool if c.in_use)
            return {
                "pool_type": self.pool_type,
                "total_connections": self._active_connections,
                "in_use": in_use_count,
                "idle": self._active_connections - in_use_count,
                "max_size": self.max_pool_size,
                "min_size": self.min_pool_size
            }


class DatabaseEngine:
    """
    Unified Database Engine with workload separation (Control Plane, Read, Write),
    PostgreSQL & SQLite dialect abstraction, and transaction lifecycle control.
    """
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        dialect_env = os.getenv("ZONATA_DB_DIALECT", "").lower()
        if (self.database_url and (self.database_url.startswith("postgresql://") or self.database_url.startswith("postgres://"))) or dialect_env == "postgresql":
            self.dialect = DatabaseDialect.POSTGRESQL
        else:
            self.dialect = DatabaseDialect.SQLITE

        self._custom_db_path = None
        self._is_ready = (self.dialect == DatabaseDialect.SQLITE)
        self._deferred_import_mode = (self.dialect == DatabaseDialect.POSTGRESQL)

        # Initialize workload-separated pools
        self.pools: Dict[str, DatabaseConnectionPool] = {
            WorkloadType.CONTROL_PLANE: DatabaseConnectionPool(
                dialect=self.dialect,
                connection_factory=self._create_raw_connection,
                min_pool_size=3,
                max_pool_size=10,
                connection_timeout=15.0,
                pool_type=WorkloadType.CONTROL_PLANE,
                deferred_mode=self._deferred_import_mode
            ),
            WorkloadType.WRITE: DatabaseConnectionPool(
                dialect=self.dialect,
                connection_factory=self._create_raw_connection,
                min_pool_size=5,
                max_pool_size=20,
                connection_timeout=30.0,
                pool_type=WorkloadType.WRITE,
                deferred_mode=self._deferred_import_mode
            ),
            WorkloadType.READ: DatabaseConnectionPool(
                dialect=self.dialect,
                connection_factory=self._create_raw_connection,
                min_pool_size=5,
                max_pool_size=30,
                connection_timeout=20.0,
                pool_type=WorkloadType.READ,
                deferred_mode=self._deferred_import_mode
            )
        }

    @property
    def db_path(self) -> str:
        if self._custom_db_path:
            return self._custom_db_path
        env_path = os.getenv("ZONATA_DB_PATH") or os.getenv("ROBOASSISTANT_DB_PATH") or os.getenv("SQLITE_DB_PATH")
        if env_path:
            return os.path.abspath(env_path)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "storage", "roboassistant.db")

    @db_path.setter
    def db_path(self, val: str):
        self._custom_db_path = os.path.abspath(val) if val else None

    def _create_raw_connection(self) -> Any:
        """Create dialect-specific raw database connection."""
        if self.dialect == DatabaseDialect.SQLITE:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path, timeout=60.0, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 60000")
            conn.execute("PRAGMA synchronous = NORMAL")
            return conn
        else:
            # PostgreSQL connection via psycopg2 or pg8000
            from core.db import sanitize_db_url
            try:
                import psycopg2
                import psycopg2.extras
                conn = psycopg2.connect(self.database_url, connect_timeout=10)
                conn.autocommit = False
                return conn
            except ImportError:
                pass
            except Exception as e:
                sanitized_url = sanitize_db_url(self.database_url or "")
                sanitized_err = sanitize_db_url(str(e))
                raise DatabaseException(f"Failed to connect to PostgreSQL database at '{sanitized_url}': {sanitized_err}")

            try:
                import pg8000
                import urllib.parse
                parsed = urllib.parse.urlsplit(self.database_url)
                user = parsed.username or "postgres"
                password = parsed.password or ""
                host = parsed.hostname or "localhost"
                port = parsed.port or 5432
                database = parsed.path.lstrip("/") or "postgres"
                conn = pg8000.connect(
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    database=database,
                    timeout=10
                )
                conn.autocommit = False
                return conn
            except ImportError:
                raise DatabaseException("PostgreSQL driver (psycopg2 or pg8000) not available. Set SQLITE_DB_PATH or install driver.")
            except Exception as e:
                sanitized_url = sanitize_db_url(self.database_url or "")
                sanitized_err = sanitize_db_url(str(e))
                raise DatabaseException(f"Failed to connect to PostgreSQL database at '{sanitized_url}': {sanitized_err}")

    @contextmanager
    def connection(self, workload: str = WorkloadType.CONTROL_PLANE):
        """Context manager to check out a pooled connection and release it safely."""
        pool = self.pools.get(workload, self.pools[WorkloadType.CONTROL_PLANE])
        conn = pool.acquire()
        try:
            yield conn
        finally:
            pool.release(conn)

    @contextmanager
    def transaction(self, workload: str = WorkloadType.WRITE, timeout_seconds: float = 30.0):
        """Context manager executing inside an atomic transaction with automatic rollback."""
        pool = self.pools.get(workload, self.pools[WorkloadType.WRITE])
        conn = pool.acquire()
        conn.transaction_active = True
        start_time = time.time()
        try:
            yield conn
            if time.time() - start_time > timeout_seconds:
                raise TransactionTimeout(f"Transaction exceeded {timeout_seconds}s deadline.")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.release(conn)

    def execute_optimistic_update(
        self,
        table: str,
        set_clauses: Dict[str, Any],
        id_column: str,
        id_value: Any,
        expected_version: int,
        workload: str = WorkloadType.WRITE
    ) -> bool:
        """
        Execute update enforcing optimistic concurrency check via row version counter.
        Returns True if updated successfully, raises OptimisticLockError on collision.
        """
        clauses = [f"{k} = ?" for k in set_clauses.keys()]
        clauses.append("version = version + 1")
        clause_str = ", ".join(clauses)

        sql = f"UPDATE {table} SET {clause_str} WHERE {id_column} = ? AND version = ?"
        params = list(set_clauses.values()) + [id_value, expected_version]

        with self.transaction(workload=workload) as conn:
            cursor = conn.execute(sql, params)
            affected = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
            if affected == 0:
                raise OptimisticLockError(
                    f"Optimistic lock conflict on {table}. Expected version {expected_version}, but record was concurrently modified."
                )
            return True

    def is_ready(self) -> bool:
        """Returns True if the database engine connection pool has been verified."""
        if self.dialect == DatabaseDialect.SQLITE:
            return True
        return bool(self._is_ready)

    def verify_readiness(self) -> bool:
        """Verifies genuine database connectivity across pools. Fails closed with sanitized error."""
        if self.dialect == DatabaseDialect.SQLITE:
            self._is_ready = True
            self._deferred_import_mode = False
            for p in self.pools.values():
                p._deferred_import_mode = False
            return True

        from core.db import sanitize_db_url
        if not self.database_url:
            raise DatabaseException("Database Readiness Error: DATABASE_URL is not configured.")

        try:
            raw = self._create_raw_connection()
            try:
                cur = raw.cursor()
                cur.execute("SELECT 1")
                res = cur.fetchone()
                if not res or res[0] != 1:
                    raise DatabaseException("Database ping returned invalid result.")
            finally:
                try:
                    raw.close()
                except Exception:
                    pass
            self._is_ready = True
            self._deferred_import_mode = False
            for p in self.pools.values():
                p._deferred_import_mode = False
                p._prewarm()
            return True
        except Exception as e:
            self._is_ready = False
            sanitized_url = sanitize_db_url(self.database_url)
            sanitized_err = sanitize_db_url(str(e))
            raise DatabaseException(f"Database Pool Readiness Verification Failed for '{sanitized_url}': {sanitized_err}")

    def health_check(self) -> Dict[str, Any]:
        """Perform active database ping across all pools."""
        results = {}
        overall_healthy = True
        for pool_type, pool in self.pools.items():
            try:
                conn = pool.acquire(timeout=5.0)
                try:
                    cursor = conn.execute("SELECT 1")
                    val = cursor.fetchone()[0] if cursor else None
                    results[pool_type] = {"status": "HEALTHY", "ping": val, "stats": pool.get_stats()}
                finally:
                    pool.release(conn)
            except Exception as e:
                overall_healthy = False
                results[pool_type] = {"status": "UNHEALTHY", "error": str(e), "stats": pool.get_stats()}

        return {
            "status": "HEALTHY" if overall_healthy else "UNHEALTHY",
            "dialect": self.dialect,
            "pools": results
        }

    def shutdown(self):
        """Gracefully close all pools."""
        for pool in self.pools.values():
            pool.close_all()

# Global Database Engine instance
engine = DatabaseEngine()
