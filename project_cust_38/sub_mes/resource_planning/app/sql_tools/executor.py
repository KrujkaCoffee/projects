from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import tuple_row

from .analyzer import SqlAnalysis, SqlSafetyError, analyze_sql


class SqlExecutionCancelled(RuntimeError):
    pass


@dataclass(frozen=True)
class SqlExecutionRequest:
    sql: str
    allow_writes: bool = False
    row_limit: int = 1000
    timeout_ms: int = 30_000


@dataclass(frozen=True)
class SqlExecutionResult:
    analysis: SqlAnalysis
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    affected_rows: int | None
    truncated: bool
    duration_ms: int
    notices: tuple[str, ...] = ()


class SqlQueryRunner:
    """Execute exactly one bounded SQL statement on the shared one-slot pool."""

    def __init__(self, db) -> None:
        self.db = db
        self._lock = threading.Lock()
        self._active_connection = None
        self._cancel_requested = threading.Event()

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested.is_set()

    def execute(self, request: SqlExecutionRequest) -> SqlExecutionResult:
        analysis = analyze_sql(request.sql)
        if analysis.is_write and not request.allow_writes:
            raise SqlSafetyError(
                f"{analysis.command} изменяет данные. Включите «Разрешить изменения» для этого запуска."
            )
        row_limit = max(1, min(int(request.row_limit), 100_000))
        timeout_ms = max(100, min(int(request.timeout_ms), 3_600_000))
        notices: list[str] = []
        started = time.monotonic()

        with self.db.session() as conn:
            self._set_active_connection(conn)
            handler = self._notice_handler(notices)
            add_notice_handler = getattr(conn, "add_notice_handler", None)
            remove_notice_handler = getattr(conn, "remove_notice_handler", None)
            if callable(add_notice_handler):
                add_notice_handler(handler)
            try:
                self._raise_if_cancelled()
                with conn.transaction():
                    self._configure_transaction(
                        conn,
                        request.allow_writes and analysis.is_write,
                        timeout_ms,
                    )
                    self._raise_if_cancelled()
                    columns, rows, affected, truncated = self._execute_statement(
                        conn,
                        analysis,
                        row_limit,
                    )
                    self._raise_if_cancelled()
            except psycopg.errors.QueryCanceled as exc:
                message = (
                    "Запрос PostgreSQL отменён пользователем"
                    if self._cancel_requested.is_set()
                    else "Запрос PostgreSQL прерван по timeout"
                )
                raise SqlExecutionCancelled(message) from exc
            finally:
                if callable(remove_notice_handler):
                    try:
                        remove_notice_handler(handler)
                    except (AttributeError, RuntimeError, ValueError):
                        # The handler may already have been detached by a
                        # broken connection. Transaction cleanup still wins.
                        pass
                self._clear_active_connection(conn)

        duration_ms = max(0, int((time.monotonic() - started) * 1000))
        return SqlExecutionResult(
            analysis=analysis,
            columns=columns,
            rows=rows,
            affected_rows=affected,
            truncated=truncated,
            duration_ms=duration_ms,
            notices=tuple(notices),
        )

    def cancel(self, *, timeout: float = 3.0) -> bool:
        self._cancel_requested.set()
        with self._lock:
            conn = self._active_connection
            if conn is None:
                return False
            cancel_safe = getattr(conn, "cancel_safe", None)
            if not callable(cancel_safe):
                return False
            # Keep the lock until libpq has sent the cancel packet. The worker
            # cannot return this connection to the shared pool meanwhile, so a
            # late cancel can never hit the next tab's unrelated query.
            cancel_safe(timeout=timeout)
            return True

    def _set_active_connection(self, conn) -> None:
        with self._lock:
            self._active_connection = conn

    def _clear_active_connection(self, conn) -> None:
        with self._lock:
            if self._active_connection is conn:
                self._active_connection = None

    def _raise_if_cancelled(self) -> None:
        if self._cancel_requested.is_set():
            raise SqlExecutionCancelled("Запрос отменён до выполнения")

    @staticmethod
    def _configure_transaction(conn, allow_writes: bool, timeout_ms: int) -> None:
        with conn.cursor(row_factory=tuple_row) as cur:
            if not allow_writes:
                cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                [str(timeout_ms)],
            )
            cur.execute(
                "SELECT set_config('lock_timeout', %s, true)",
                [str(min(timeout_ms, 10_000))],
            )

    @classmethod
    def _execute_statement(
        cls,
        conn,
        analysis: SqlAnalysis,
        row_limit: int,
    ) -> tuple[tuple[str, ...], tuple[tuple[Any, ...], ...], int | None, bool]:
        cursor_name = f"admin_sql_{uuid.uuid4().hex}"
        if analysis.stream_results:
            with conn.cursor(name=cursor_name, row_factory=tuple_row) as cur:
                cur.execute(analysis.statement)
                columns = cls._column_names(cur.description)
                fetched = list(cur.fetchmany(row_limit + 1))
                rows = tuple(
                    cls._row_values(row, columns) for row in fetched[:row_limit]
                )
                return columns, rows, None, len(fetched) > row_limit

        with conn.cursor(row_factory=tuple_row) as cur:
            cur.execute(analysis.statement)
            columns = cls._column_names(cur.description)
            fetched: Sequence[Any] = ()
            if columns:
                fetched = cur.fetchmany(row_limit + 1)
            rows = tuple(cls._row_values(row, columns) for row in fetched[:row_limit])
            affected = (
                int(cur.rowcount)
                if cur.rowcount is not None and cur.rowcount >= 0
                else None
            )
            return columns, rows, affected, len(fetched) > row_limit

    @staticmethod
    def _column_names(description) -> tuple[str, ...]:
        if not description:
            return ()
        names = []
        for column in description:
            value = getattr(column, "name", None)
            if value is None:
                value = column[0]
            names.append(str(value))
        return tuple(names)

    @staticmethod
    def _row_values(row: Any, columns: tuple[str, ...]) -> tuple[Any, ...]:
        if isinstance(row, Mapping):
            return tuple(row.get(column) for column in columns)
        return tuple(row)

    @staticmethod
    def _notice_handler(target: list[str]):
        def handler(diag) -> None:
            severity = str(getattr(diag, "severity_nonlocalized", "") or "").strip()
            message = str(getattr(diag, "message_primary", "") or "").strip()
            rendered = ": ".join(part for part in (severity, message) if part)
            if rendered:
                target.append(rendered)

        return handler


__all__ = [
    "SqlExecutionCancelled",
    "SqlExecutionRequest",
    "SqlExecutionResult",
    "SqlQueryRunner",
]
