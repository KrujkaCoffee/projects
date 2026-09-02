from __future__ import annotations

import dataclasses
import re
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
)

import psycopg
from psycopg.pq import ConnStatus
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolClosed, PoolTimeout

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_T = TypeVar("_T")


class DbError(RuntimeError):
    """Raised for user-facing database errors."""


@dataclass
class ColumnInfo:
    name: str
    data_type: str = ""
    nullable: bool = True
    ordinal_position: int = 0


@dataclasses.dataclass
class PostgresConfig:
    host: str = "localhost"
    port: int = 5432
    dbname: str = ""
    user: str = "postgres"
    password: str = "123123"
    connect_timeout: int = 5
    application_name: str = "mes_pg_cache"
    schema_name: str = "public"
    table_name: str = "mes_request_cache_payload"
    options: str = ""
    sslmode: str = "disable"
    gssencmode: str = "disable"

    # Desktop lifecycle policy: no permanent session and never more than one
    # physical PostgreSQL connection for this application process.
    pool_min_size: int = 0
    pool_max_size: int = 1
    pool_acquire_timeout_sec: float = 8.0
    pool_max_idle_sec: float = 300.0
    pool_max_lifetime_sec: float = 3600.0
    pool_reconnect_timeout_sec: float = 20.0
    pool_max_waiting: int = 4
    pool_num_workers: int = 1

    # Detect half-open TCP sessions before they can remain unnoticed for hours.
    keepalives: int = 1
    keepalives_idle: int = 60
    keepalives_interval: int = 15
    keepalives_count: int = 4


config = PostgresConfig()


class PostgresDatabase:
    """PostgreSQL adapter with a lazy, bounded connection lifecycle.

    The process owns one pool with ``min_size=0`` and ``max_size=1``. Therefore
    it never keeps more than one physical connection, releases that connection
    after a period of inactivity and creates/checks it again on demand.

    Read-only operations may be repeated once *only* when the checked-out
    connection is demonstrably broken. Writes and explicit transactions are
    never repeated automatically because their commit outcome may be unknown.
    """

    def __init__(self, pool_factory=None) -> None:
        self._pool_factory = pool_factory or ConnectionPool
        self._pool = None
        self._lock = threading.RLock()
        self._shutdown = False
        self._last_error = ""
        self.dsn: Dict[str, Any] = self._connection_parameters()

    # ------------------------------------------------------------------ lifecycle
    @property
    def is_connected(self) -> bool:
        """Whether the connection manager is open, not whether a socket is idle.

        With ``min_size=0`` the pool can intentionally contain zero physical
        connections. Existing UI guards can still treat the database as ready:
        the next operation will acquire a checked connection automatically.
        """

        pool = self._pool
        return bool(pool is not None and not getattr(pool, "closed", True) and not self._shutdown)

    @property
    def has_live_connection(self) -> bool:
        snapshot = self.connection_snapshot()
        return int(snapshot.get("pool_size") or 0) > 0

    @property
    def last_error(self) -> str:
        return self._last_error

    def _connection_parameters(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "host": config.host,
            "port": config.port,
            "dbname": config.dbname,
            "user": config.user,
            "password": config.password,
            "connect_timeout": config.connect_timeout,
            "application_name": config.application_name,
            "sslmode": config.sslmode,
            "options": config.options or None,
            "gssencmode": config.gssencmode,
            "keepalives": config.keepalives,
            "keepalives_idle": config.keepalives_idle,
            "keepalives_interval": config.keepalives_interval,
            "keepalives_count": config.keepalives_count,
        }
        return {key: value for key, value in params.items() if value is not None}

    def start(self) -> Dict[str, Any]:
        """Open the pool manager without keeping a mandatory connection alive."""

        with self._lock:
            if self.is_connected:
                return dict(self.dsn)

            self._shutdown = False
            self.dsn = self._connection_parameters()
            pool_kwargs = dict(self.dsn)
            pool_kwargs.update({"autocommit": True, "row_factory": dict_row})
            check_callback = getattr(self._pool_factory, "check_connection", ConnectionPool.check_connection)

            pool = self._pool_factory(
                conninfo="",
                kwargs=pool_kwargs,
                min_size=config.pool_min_size,
                max_size=config.pool_max_size,
                open=False,
                check=check_callback,
                timeout=config.pool_acquire_timeout_sec,
                max_waiting=config.pool_max_waiting,
                max_lifetime=config.pool_max_lifetime_sec,
                max_idle=config.pool_max_idle_sec,
                reconnect_timeout=config.pool_reconnect_timeout_sec,
                num_workers=config.pool_num_workers,
                name="admin-panel",
            )
            pool.open(wait=False)
            self._pool = pool
            return dict(self.dsn)

    def connect(self) -> Dict[str, Any]:
        """Start the manager and perform one bounded startup health check.

        A failed health check does not destroy the manager. The next user
        operation can therefore wake the application and request a fresh
        connection without a manual reconnect button or a reconnect loop.
        """

        self.start()
        self.ping()
        return dict(self.dsn)

    def ping(self) -> None:
        try:
            with self._borrow_connection():
                pass
        except (PoolTimeout, PoolClosed, psycopg.OperationalError, psycopg.InterfaceError) as exc:
            self._record_error(exc)
            raise DbError(self._connection_error_message(exc)) from exc

    def close(self) -> None:
        with self._lock:
            pool = self._pool
            self._pool = None
            self._shutdown = True
        if pool is not None and not getattr(pool, "closed", True):
            try:
                pool.close(timeout=3.0)
            finally:
                self._last_error = ""

    def connection_snapshot(self) -> Dict[str, Any]:
        pool = self._pool
        if pool is None or getattr(pool, "closed", True) or self._shutdown:
            return {
                "manager_open": False,
                "pool_size": 0,
                "pool_available": 0,
                "requests_waiting": 0,
                "last_error": self._last_error,
            }
        try:
            stats = dict(pool.get_stats())
        except Exception:
            stats = {}
        return {
            "manager_open": True,
            "pool_size": int(stats.get("pool_size") or 0),
            "pool_available": int(stats.get("pool_available") or 0),
            "requests_waiting": int(stats.get("requests_waiting") or 0),
            "last_error": self._last_error,
        }

    def _require_pool(self):
        if not self.is_connected:
            if self._shutdown:
                raise PoolClosed("Менеджер соединений PostgreSQL закрыт")
            self.start()
        pool = self._pool
        if pool is None:
            raise PoolClosed("Менеджер соединений PostgreSQL не запущен")
        return pool

    @contextmanager
    def _borrow_connection(self, timeout: Optional[float] = None) -> Iterator[Any]:
        pool = self._require_pool()
        acquire_timeout = config.pool_acquire_timeout_sec if timeout is None else timeout
        with pool.connection(timeout=acquire_timeout) as conn:
            self._last_error = ""
            yield conn

    @contextmanager
    def session(self, timeout: Optional[float] = None) -> Iterator[Any]:
        """Yield one raw checked connection for an interactive bounded operation.

        The caller owns statement transaction semantics and must not persist
        session-level settings. Pool acquisition failures are translated to the
        same user-facing ``DbError`` used by the rest of the application; SQL
        diagnostics raised inside the session remain available to the caller.
        """

        try:
            with self._borrow_connection(timeout) as conn:
                yield conn
        except (PoolTimeout, PoolClosed) as exc:
            self._record_error(exc)
            raise DbError(self._connection_error_message(exc)) from exc

    def _record_error(self, exc: BaseException) -> None:
        self._last_error = str(exc).strip() or exc.__class__.__name__

    @staticmethod
    def _is_broken_connection(exc: BaseException, conn: Any) -> bool:
        sqlstate = str(getattr(exc, "sqlstate", "") or "")
        if sqlstate.startswith("08") or sqlstate in {"57P01", "57P02", "57P03"}:
            return True
        if bool(getattr(conn, "closed", False)) or bool(getattr(conn, "broken", False)):
            return True
        try:
            return conn.info.status == ConnStatus.BAD
        except Exception:
            return False

    @staticmethod
    def _connection_error_message(exc: BaseException) -> str:
        if isinstance(exc, PoolTimeout):
            return (
                f"PostgreSQL не предоставил соединение за {config.pool_acquire_timeout_sec:g} с. "
                "Следующее действие повторит попытку; одновременно создаётся не более одного соединения."
            )
        if isinstance(exc, PoolClosed):
            return "Менеджер соединений PostgreSQL закрыт."
        return f"Соединение с PostgreSQL недоступно: {exc}"

    @staticmethod
    def _write_error_message(exc: BaseException, conn: Any) -> str:
        if PostgresDatabase._is_broken_connection(exc, conn):
            return (
                "Соединение потеряно во время изменения данных. Результат операции может быть неизвестен; "
                "обновите таблицу перед ручным повтором. Автоматический retry записи не выполнялся."
            )
        return str(exc)

    def _run_read(self, operation: Callable[[Any], _T]) -> _T:
        """Run a read and retry once only after a proven connection failure."""

        for attempt in range(2):
            conn = None
            try:
                with self._borrow_connection() as conn:
                    return operation(conn)
            except (PoolTimeout, PoolClosed) as exc:
                self._record_error(exc)
                raise DbError(self._connection_error_message(exc)) from exc
            except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
                self._record_error(exc)
                if attempt == 0 and conn is not None and self._is_broken_connection(exc, conn):
                    continue
                raise DbError(self._connection_error_message(exc)) from exc
            except psycopg.Error as exc:
                raise DbError(str(exc)) from exc
        raise DbError("Не удалось выполнить чтение из PostgreSQL")

    def _run_write(self, operation: Callable[[Any], _T]) -> _T:
        """Run a write exactly once; never hide an ambiguous commit outcome."""

        conn = None
        try:
            with self._borrow_connection() as conn:
                return operation(conn)
        except (PoolTimeout, PoolClosed) as exc:
            self._record_error(exc)
            raise DbError(self._connection_error_message(exc)) from exc
        except psycopg.Error as exc:
            if conn is None or self._is_broken_connection(exc, conn):
                self._record_error(exc)
            raise DbError(self._write_error_message(exc, conn)) from exc

    # ------------------------------------------------------------------ basic operations
    def fetchall(self, query: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        def operation(conn) -> List[Dict[str, Any]]:
            with conn.cursor() as cur:
                cur.execute(query, params or [])
                return [dict(row) for row in cur.fetchall()]

        return self._run_read(operation)

    def fetchone(self, query: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
        def operation(conn) -> Optional[Dict[str, Any]]:
            with conn.cursor() as cur:
                cur.execute(query, params or [])
                row = cur.fetchone()
                return dict(row) if row is not None else None

        return self._run_read(operation)

    def execute(self, query: str, params: Optional[Sequence[Any]] = None) -> int:
        def operation(conn) -> int:
            with conn.cursor() as cur:
                cur.execute(query, params or [])
                return cur.rowcount

        return self._run_write(operation)

    def executemany(self, query: str, rows: Iterable[Sequence[Any]]) -> int:
        def operation(conn) -> int:
            total = 0
            with conn.transaction():
                with conn.cursor() as cur:
                    for params in rows:
                        cur.execute(query, params)
                        if cur.rowcount > 0:
                            total += cur.rowcount
            return total

        return self._run_write(operation)

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Yield one cursor in an explicit atomic transaction, without retry."""

        conn = None
        try:
            with self._borrow_connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        yield cur
        except (PoolTimeout, PoolClosed) as exc:
            self._record_error(exc)
            raise DbError(self._connection_error_message(exc)) from exc
        except psycopg.Error as exc:
            if conn is None or self._is_broken_connection(exc, conn):
                self._record_error(exc)
            raise DbError(self._write_error_message(exc, conn)) from exc

    # ------------------------------------------------------------------ SQL helpers
    @staticmethod
    def quote_ident(name: str) -> str:
        if name is None or name == "":
            raise DbError("Пустой SQL identifier")
        return '"' + str(name).replace('"', '""') + '"'

    @classmethod
    def qname(cls, schema: str, table: str) -> str:
        return f"{cls.quote_ident(schema)}.{cls.quote_ident(table)}"

    @staticmethod
    def split_table_name(full_name: str) -> Tuple[str, str]:
        if "." in full_name:
            schema, table = full_name.split(".", 1)
            return schema, table
        return "public", full_name

    def table_exists(self, schema: str, table: str) -> bool:
        row = self.fetchone(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            LIMIT 1
            """,
            [schema, table],
        )
        return row is not None

    def list_tables(self, include_views: bool = False) -> List[Dict[str, Any]]:
        table_types = ["BASE TABLE"]
        if include_views:
            table_types.append("VIEW")
        return self.fetchall(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_type = ANY(%s::text[])
            ORDER BY table_schema, table_name
            """,
            [table_types],
        )

    def list_admin_tables(self) -> List[Dict[str, Any]]:
        return self.fetchall(
            """
            SELECT table_key, db_key, table_name, is_enabled, cache_enabled, schema_enabled,
                   stale_after_dt, cache_lifetime_min, validity_mark, content_hash, version,
                   invalidated_at, notes, updated_at
            FROM public.admin_physical_tables
            ORDER BY db_key, table_name
            """
        )

    def get_columns(self, schema: str, table: str) -> List[ColumnInfo]:
        rows = self.fetchall(
            """
            SELECT column_name, data_type, is_nullable, ordinal_position
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            [schema, table],
        )
        return [
            ColumnInfo(
                name=row["column_name"],
                data_type=row.get("data_type") or "",
                nullable=(row.get("is_nullable") == "YES"),
                ordinal_position=int(row.get("ordinal_position") or 0),
            )
            for row in rows
        ]

    def get_primary_keys(self, schema: str, table: str) -> List[str]:
        rows = self.fetchall(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
             AND tc.table_name = kcu.table_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = %s
              AND tc.table_name = %s
            ORDER BY kcu.ordinal_position
            """,
            [schema, table],
        )
        return [r["column_name"] for r in rows]

    def admin_tables_available(self) -> Tuple[bool, List[str]]:
        names = [
            "admin_physical_tables",
            "admin_table_fields",
            "admin_table_relations",
            "admin_relation_field_pairs",
        ]
        missing = [name for name in names if not self.table_exists("public", name)]
        return len(missing) == 0, missing


def normalize_table_key(text: str) -> str:
    """Convert an arbitrary table name into a stable readable metadata key."""

    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9_\.]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "table"
