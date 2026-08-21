from __future__ import annotations

import argparse
import atexit
import contextlib
import dataclasses
import datetime as dt
import hashlib
import json
import math
import ntpath
import os
import pathlib
import queue
import random
import re
import socket
import sys
import tempfile
import threading
import time
import uuid
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any, Protocol


__all__ = [
    "RUNTIME_VERSION",
    "ExecutorConfig",
    "PreparedQuery",
    "ProbeConfig",
    "PostgreSqlExecutor",
    "PostgreSqlTransaction",
    "Stage2Probe",
    "PostgresRuntimeError",
    "PostgresConfigurationError",
    "PostgresDependencyError",
    "PostgresExecutionError",
    "PostgresCommitOutcomeUnknown",
    "SchemaResolutionError",
    "configure_default_runtime",
    "configure_default_from_env",
    "custom_request_c",
    "transaction",
    "stage2_observe_request",
    "observe_request",
    "stage2_snapshot",
    "shutdown_default_runtime",
]


RUNTIME_VERSION = "0.1.0-stage2"
PROBE_SQL = "SELECT 123 AS mes_connection_probe"
SNAPSHOT_SCHEMA_VERSION = 1
_READ_ONLY_STATEMENTS = frozenset({"SELECT", "SHOW", "VALUES", "TABLE"})
_WRITE_STATEMENTS = frozenset(
    {"INSERT", "UPDATE", "DELETE", "MERGE", "CALL", "COPY", "CREATE", "ALTER", "DROP", "TRUNCATE", "GRANT", "REVOKE"}
)
_SAFE_ISOLATION_LEVELS = frozenset({"READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"})
_RTT_BUCKETS_MS = (5, 10, 25, 50, 100, 250, 500, 1000)


class PostgresRuntimeError(RuntimeError):
    """Базовая ошибка PostgreSQL runtime."""


class PostgresConfigurationError(PostgresRuntimeError):
    """Конфигурация runtime неполна или небезопасна."""


class PostgresDependencyError(PostgresRuntimeError):
    """На клиенте отсутствует обязательный PG-драйвер."""


class SchemaResolutionError(PostgresConfigurationError):
    """SQLite-алиас не сопоставлен со схемой PostgreSQL."""


class PostgresExecutionError(PostgresRuntimeError):
    """Запрос завершился ошибкой; исходное исключение доступно через __cause__."""

    def __init__(self, statement_type: str, message: str):
        self.statement_type = statement_type
        super().__init__(message)


class PostgresCommitOutcomeUnknown(PostgresExecutionError):
    """Связь потеряна во время записи: нельзя доказать, был ли COMMIT принят."""


@dataclasses.dataclass(frozen=True, slots=True)
class ExecutorConfig:
    """Настройки process-local пула и защитных таймаутов.
    """

    conninfo: str = "postgresql://postgres:Adr1959967 @srv-mes:5432/postgres"
    application_name: str = "mes-client"
    min_size: int = 0
    max_size: int = 1
    pool_timeout_sec: float = 3.0
    max_waiting: int = 8
    connect_timeout_sec: float = 3.0
    max_idle_sec: float = 300.0
    max_lifetime_sec: float = 1800.0
    reconnect_timeout_sec: float = 5.0
    tcp_user_timeout_ms: int = 10_000
    keepalives_idle_sec: int = 10
    keepalives_interval_sec: int = 3
    keepalives_count: int = 3
    statement_timeout_ms: int = 120_000
    lock_timeout_ms: int = 5_000
    idle_in_transaction_session_timeout_ms: int = 15_000
    read_disconnect_retries: int = 1
    pool_name: str = "mes-pg-client"

    def __post_init__(self) -> None:
        if not self.conninfo or not self.conninfo.strip():
            raise PostgresConfigurationError("Не задан conninfo/DSN PostgreSQL")
        if self.min_size < 0 or self.max_size < 1 or self.min_size > self.max_size:
            raise PostgresConfigurationError("Некорректные границы пула PostgreSQL")
        if self.pool_timeout_sec <= 0 or self.connect_timeout_sec <= 0:
            raise PostgresConfigurationError("Таймауты соединения должны быть больше нуля")
        if self.max_idle_sec <= 0 or self.max_lifetime_sec <= 0:
            raise PostgresConfigurationError("Время жизни/простоя соединения должно быть больше нуля")
        if (
            self.tcp_user_timeout_ms <= 0
            or self.keepalives_idle_sec <= 0
            or self.keepalives_interval_sec <= 0
            or self.keepalives_count <= 0
        ):
            raise PostgresConfigurationError("TCP timeout/keepalive параметры должны быть больше нуля")
        if self.max_waiting < 0:
            raise PostgresConfigurationError("max_waiting не может быть отрицательным")
        if self.read_disconnect_retries not in (0, 1):
            raise PostgresConfigurationError("Для чтения разрешено не более одного автоповтора")

    @classmethod
    def from_env(cls, prefix: str = "MES_PG_") -> "ExecutorConfig":
        env = os.environ
        conninfo = env.get(prefix + "DSN", "")
        return cls(
            conninfo=conninfo or "postgresql://postgres:Adr1959967 @srv-mes:5432/postgres",
            application_name=env.get(prefix + "APPLICATION_NAME", _default_application_name()),
            min_size=_env_int(prefix + "POOL_MIN_SIZE", 0),
            max_size=_env_int(prefix + "POOL_MAX_SIZE", 1),
            pool_timeout_sec=_env_float(prefix + "POOL_TIMEOUT_SEC", 3.0),
            max_waiting=_env_int(prefix + "POOL_MAX_WAITING", 8),
            connect_timeout_sec=_env_float(prefix + "CONNECT_TIMEOUT_SEC", 3.0),
            max_idle_sec=_env_float(prefix + "MAX_IDLE_SEC", 300.0),
            max_lifetime_sec=_env_float(prefix + "MAX_LIFETIME_SEC", 1800.0),
            reconnect_timeout_sec=_env_float(prefix + "RECONNECT_TIMEOUT_SEC", 5.0),
            tcp_user_timeout_ms=_env_int(prefix + "TCP_USER_TIMEOUT_MS", 10_000),
            keepalives_idle_sec=_env_int(prefix + "KEEPALIVES_IDLE_SEC", 10),
            keepalives_interval_sec=_env_int(prefix + "KEEPALIVES_INTERVAL_SEC", 3),
            keepalives_count=_env_int(prefix + "KEEPALIVES_COUNT", 3),
            statement_timeout_ms=_env_int(prefix + "STATEMENT_TIMEOUT_MS", 120_000),
            lock_timeout_ms=_env_int(prefix + "LOCK_TIMEOUT_MS", 5_000),
            idle_in_transaction_session_timeout_ms=_env_int(
                prefix + "IDLE_IN_TRANSACTION_TIMEOUT_MS", 15_000
            ),
            read_disconnect_retries=_env_int(prefix + "READ_DISCONNECT_RETRIES", 1),
            pool_name=env.get(prefix + "POOL_NAME", "mes-pg-client"),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ProbeConfig:

    enabled: bool = True
    queue_size: int = 256
    failure_threshold: int = 3
    cooldown_steps_sec: tuple[float, ...] = (60.0, 300.0, 900.0)
    cooldown_jitter_ratio: float = 0.15
    connection_timeout_sec: float = 2.0
    stall_timeout_sec: float = 15.0
    flush_interval_sec: float = 60.0
    worker_idle_exit_sec: float = 30.0
    spool_dir: pathlib.Path = dataclasses.field(
        default_factory=lambda: pathlib.Path(tempfile.gettempdir()) / "mes_pg_stage2"
    )
    telemetry_table: str | None = 'mes_probe.client_sessions'
    app_version: str = ""
    client_id: str = ""
    identity_salt: str = "mes-stage2"

    def __post_init__(self) -> None:
        if self.queue_size < 1:
            raise PostgresConfigurationError("Размер очереди probe должен быть больше нуля")
        if self.failure_threshold < 1:
            raise PostgresConfigurationError("Порог circuit breaker должен быть больше нуля")
        if not self.cooldown_steps_sec or any(value <= 0 for value in self.cooldown_steps_sec):
            raise PostgresConfigurationError("Интервалы circuit breaker должны быть положительными")
        if not 0 <= self.cooldown_jitter_ratio <= 0.5:
            raise PostgresConfigurationError("Jitter circuit breaker должен быть в диапазоне 0..0.5")
        if (
            self.connection_timeout_sec <= 0
            or self.stall_timeout_sec <= 0
            or self.flush_interval_sec <= 0
            or self.worker_idle_exit_sec <= 0
        ):
            raise PostgresConfigurationError("Таймаут/интервал probe должен быть больше нуля")
        if self.telemetry_table:
            _split_qualified_identifier(self.telemetry_table)

    @classmethod
    def from_env(cls, prefix: str = "MES_PG_PROBE_") -> "ProbeConfig":
        env = os.environ
        cooldown_raw = env.get(prefix + "COOLDOWN_STEPS_SEC", "60,300,900")
        try:
            cooldowns = tuple(float(item.strip()) for item in cooldown_raw.split(",") if item.strip())
        except ValueError as exc:
            raise PostgresConfigurationError("Некорректный MES_PG_PROBE_COOLDOWN_STEPS_SEC") from exc
        spool = env.get(prefix + "SPOOL_DIR", "")
        return cls(
            enabled=_env_bool(prefix + "ENABLED", True),
            queue_size=_env_int(prefix + "QUEUE_SIZE", 256),
            failure_threshold=_env_int(prefix + "FAILURE_THRESHOLD", 3),
            cooldown_steps_sec=cooldowns,
            cooldown_jitter_ratio=_env_float(prefix + "COOLDOWN_JITTER_RATIO", 0.15),
            connection_timeout_sec=_env_float(prefix + "CONNECTION_TIMEOUT_SEC", 2.0),
            stall_timeout_sec=_env_float(prefix + "STALL_TIMEOUT_SEC", 15.0),
            flush_interval_sec=_env_float(prefix + "FLUSH_INTERVAL_SEC", 60.0),
            worker_idle_exit_sec=_env_float(prefix + "WORKER_IDLE_EXIT_SEC", 30.0),
            spool_dir=pathlib.Path(spool) if spool else pathlib.Path(tempfile.gettempdir()) / "mes_pg_stage2",
            telemetry_table=env.get(prefix + "TELEMETRY_TABLE") or 'mes_probe.client_sessions',
            app_version=env.get("MES_APP_VERSION", ""),
            client_id=env.get(prefix + "CLIENT_ID", ""),
            identity_salt=env.get(prefix + "IDENTITY_SALT", "mes-stage2"),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class PreparedQuery:
    """PG-native SQL, нормализованные параметры и режим выполнения."""

    sql: str
    params: tuple[Any, ...] | Mapping[str, Any] | list[tuple[Any, ...]] | list[Mapping[str, Any]]
    many: bool
    statement_type: str


class SqlPreparer(Protocol):
    def __call__(self, sql: str, params: Any) -> PreparedQuery:
        ...


class _ProbeExecutor(Protocol):
    def probe_once(self, *, timeout_sec: float) -> float:
        ...

    def pool_stats(self) -> dict[str, Any]:
        ...

    def invalidate_pool(self) -> None:
        ...

    def upsert_probe_snapshot(self, table_name: str, snapshot: Mapping[str, Any], *, timeout_sec: float) -> None:
        ...

    def close(self) -> None:
        ...


def _default_application_name() -> str:
    executable = pathlib.Path(sys.argv[0] or "mes-client").stem
    return _safe_label(executable or "mes-client", max_length=40)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on", "да"}:
        return True
    if normalized in {"0", "false", "no", "off", "нет"}:
        return False
    raise PostgresConfigurationError(f"Переменная {name} должна быть boolean")


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise PostgresConfigurationError(f"Переменная {name} должна быть целым числом") from exc


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise PostgresConfigurationError(f"Переменная {name} должна быть числом") from exc


def _safe_label(value: Any, *, max_length: int = 63) -> str:
    text = re.sub(r"[^0-9A-Za-zА-Яа-яЁё_.:@+-]+", "-", str(value or "")).strip("-.")
    encoded = (text or "unknown").encode("utf-8")[:max_length]
    return encoded.decode("utf-8", errors="ignore") or "unknown"


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso_utc(value: dt.datetime | None = None) -> str:
    return (value or _utc_now()).isoformat(timespec="milliseconds")


def _duration_bucket(value_ms: float) -> str:
    label = f">={_RTT_BUCKETS_MS[-1]}ms"
    for upper in _RTT_BUCKETS_MS:
        if value_ms < upper:
            return f"<{upper}ms"
    return label


def _split_qualified_identifier(value: str) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in value.split("."))
    if len(parts) not in (1, 2) or any(not part for part in parts):
        raise PostgresConfigurationError("Имя таблицы должно иметь форму table или schema.table")
    pattern = re.compile(r"^[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_$]*$")
    if any(not pattern.fullmatch(part) for part in parts):
        raise PostgresConfigurationError("Имя таблицы telemetry содержит недопустимые символы")
    return parts


def _normalize_db_alias(value: Any) -> str:
    for attr in ("alias", "absolute_path"):
        candidate = getattr(value, attr, None)
        if candidate:
            value = candidate
            break
    text = str(value or "").strip()
    if "SRV:" in text:
        text = text.split("SRV:", 1)[1]
        text = re.split(r"[\\/]", text, maxsplit=1)[0]
    else:
        text = ntpath.basename(text.rstrip("\\/"))
    if text.lower().endswith(".db"):
        text = text[:-3]
    return text or "unknown"


def _first_statement_keyword(sql: str) -> str:
    """Возвращает первое слово вне BOM, пробелов и SQL-комментариев.

    ``WITH`` намеренно остаётся ``WITH``
    """

    if not isinstance(sql, str) or not sql.strip():
        raise PostgresConfigurationError("SQL-запрос пуст")
    index = 0
    length = len(sql)
    if sql.startswith("\ufeff"):
        index = 1
    while index < length:
        while index < length and sql[index].isspace():
            index += 1
        if sql.startswith("--", index):
            newline = sql.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            if end < 0:
                raise PostgresConfigurationError("В SQL не закрыт блочный комментарий")
            index = end + 2
            continue
        break
    match = re.match(r"[A-Za-zА-Яа-яЁё_]+", sql[index:])
    return match.group(0).upper() if match else "UNKNOWN"


def _is_obviously_read_only(statement_type: str) -> bool:
    return statement_type in _READ_ONLY_STATEMENTS


def _is_write(statement_type: str) -> bool:
    return statement_type in _WRITE_STATEMENTS or not _is_obviously_read_only(statement_type)


def _native_sql_preparer(sql: str, params: Any) -> PreparedQuery:
    statement_type = _first_statement_keyword(sql)
    if params is None or params == [] or params == [[]] or params == ():
        return PreparedQuery(sql=sql, params=(), many=False, statement_type=statement_type)
    if isinstance(params, Mapping):
        return PreparedQuery(sql=sql, params=params, many=False, statement_type=statement_type)
    if isinstance(params, (str, bytes, bytearray, memoryview)):
        return PreparedQuery(sql=sql, params=(params,), many=False, statement_type=statement_type)
    if not isinstance(params, Sequence):
        return PreparedQuery(sql=sql, params=(params,), many=False, statement_type=statement_type)

    values = list(params)
    if not values:
        return PreparedQuery(sql=sql, params=(), many=False, statement_type=statement_type)
    first = values[0]
    if isinstance(first, Mapping):
        rows = [item for item in values if isinstance(item, Mapping)]
        if len(rows) != len(values):
            raise PostgresConfigurationError("Нельзя смешивать dict и позиционные параметры")
        if len(rows) == 1:
            return PreparedQuery(sql=sql, params=rows[0], many=False, statement_type=statement_type)
        return PreparedQuery(sql=sql, params=rows, many=True, statement_type=statement_type)
    if isinstance(first, Sequence) and not isinstance(first, (str, bytes, bytearray, memoryview)):
        rows: list[tuple[Any, ...]] = []
        for row in values:
            if not isinstance(row, Sequence) or isinstance(row, (str, bytes, bytearray, memoryview)):
                raise PostgresConfigurationError("Нельзя смешивать строки параметров и скалярные значения")
            rows.append(tuple(row))
        if len(rows) == 1:
            return PreparedQuery(sql=sql, params=rows[0], many=False, statement_type=statement_type)
        if _is_obviously_read_only(statement_type):
            return PreparedQuery(sql=sql, params=rows[0], many=False, statement_type=statement_type)
        return PreparedQuery(sql=sql, params=rows, many=True, statement_type=statement_type)
    return PreparedQuery(sql=sql, params=tuple(values), many=False, statement_type=statement_type)


def _is_disconnect_error(exc: BaseException) -> bool:
    sqlstate = str(getattr(exc, "sqlstate", "") or getattr(exc, "pgcode", "") or "")
    if sqlstate.startswith("08") or sqlstate in {"57P01", "57P02", "57P03", "58P01"}:
        return True
    class_name = type(exc).__name__.lower()
    return class_name in {"operationalerror", "connectiontimeout", "poolclosed"} and any(
        token in str(exc).lower()
        for token in ("connection", "server closed", "terminat", "broken", "network", "socket")
    )


def _is_timeout_error(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    sqlstate = str(getattr(exc, "sqlstate", "") or getattr(exc, "pgcode", "") or "")
    if sqlstate == "57014":
        return True
    return "timeout" in type(exc).__name__.lower() or "timed out" in str(exc).lower()


def _unpack_single_value(result: Any) -> Any:
    if result and isinstance(result, list):
        return _unpack_single_value(result[0])
    if result and isinstance(result, dict):
        return _unpack_single_value(list(result.values()))
    return result


def _format_rows(
    rows: Sequence[Sequence[Any]],
    columns: Sequence[str],
    *,
    hat_c: bool,
    rez_dict: bool,
    one: bool,
    one_column: bool,
) -> Any:
    if rez_dict and one_column:
        raise PostgresConfigurationError("rez_dict=True нельзя совмещать с one_column=True")
    selected = list(rows[:1] if one else rows)
    if rez_dict:
        result_dicts: list[dict[str, Any]] = []
        for row in selected:
            item: dict[str, Any] = {}
            for index, (column, value) in enumerate(zip(columns, row)):
                key = column if column not in item else f"{index}_{column}"
                item[key] = value
            result_dicts.append(item)
        if one:
            return result_dicts[0] if result_dicts else {}
        return result_dicts

    result_lists = [list(row) for row in selected]
    if hat_c:
        result_lists.insert(0, list(columns))
    if one_column:
        result: Any = [row[0] for row in result_lists if row]
    else:
        result = result_lists
    if one and one_column:
        return _unpack_single_value(result)
    return result


class SchemaRegistry:
    """Явное сопоставление старых имён файлов и PG-схем."""

    def __init__(self, mapping: Mapping[str, str] | None = None):
        self._mapping: dict[str, str] = {}
        for alias, schema in (mapping or {}).items():
            normalized = _normalize_db_alias(alias).casefold()
            if not normalized:
                raise PostgresConfigurationError("Пустой alias в schema_map")
            _validate_schema_name(schema)
            self._mapping[normalized] = schema

    @classmethod
    def from_env(cls, name: str = "MES_PG_SCHEMA_MAP_JSON") -> "SchemaRegistry":
        raw = os.environ.get(name, "").strip()
        if not raw:
            return cls()
        try:
            mapping = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PostgresConfigurationError(f"{name} содержит некорректный JSON") from exc
        if not isinstance(mapping, dict):
            raise PostgresConfigurationError(f"{name} должен быть JSON-объектом")
        return cls({str(key): str(value) for key, value in mapping.items()})

    def resolve(self, db_alias: Any) -> str:
        normalized = _normalize_db_alias(db_alias).casefold()
        # schema = self._mapping.get(normalized)
        # todo тестовый режим одной схемы
        schema = "files_stage"
        if not schema:
            raise SchemaResolutionError(
                f"Для alias '{_normalize_db_alias(db_alias)}' не задана PostgreSQL-схема"
            )
        return schema

    def resolve_many(self, main: Any, attached: tuple[Any, ...] | list[Any] | Any = ()) -> tuple[str, ...]:
        values = (attached,) if isinstance(attached, (str, bytes)) or not isinstance(attached, Sequence) else attached
        schemas = [self.resolve(main)]
        for value in values or ():
            schema = self.resolve(value)
            if schema not in schemas:
                schemas.append(schema)
        return tuple(schemas)


def _validate_schema_name(value: str) -> None:
    if (
        not value
        or "\x00" in value
        or "." in value
        or any(ord(char) < 32 for char in value)
        or len(value.encode("utf-8")) > 63
    ):
        raise PostgresConfigurationError("Имя PG-схемы должно быть одним идентификатором")


def _load_psycopg() -> tuple[Any, Any]:
    try:
        import psycopg
        import psycopg_pool
    except ImportError as exc:
        raise PostgresDependencyError(
            'Не установлен Psycopg 3 с пулом: pip install "psycopg[binary,pool]"'
        ) from exc
    return psycopg, psycopg_pool


class _ProcessLocalPool:
    """Ленивый пул, который никогда не переиспользуется между процессами."""

    def __init__(self, config: ExecutorConfig):
        self.config = config
        self._lock = threading.RLock()
        self._pool: Any = None
        self._pid = os.getpid()
        self._generation = 0
        if hasattr(os, "register_at_fork"):
            os.register_at_fork(after_in_child=self._after_fork_child)

    def _after_fork_child(self) -> None:
        self._lock = threading.RLock()
        self._pool = None
        self._pid = os.getpid()
        self._generation += 1

    def _configure_connection(self, conn: Any) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    set_config('statement_timeout', %s, false),
                    set_config('lock_timeout', %s, false),
                    set_config('idle_in_transaction_session_timeout', %s, false)
                """,
                (
                    f"{self.config.statement_timeout_ms}ms",
                    f"{self.config.lock_timeout_ms}ms",
                    f"{self.config.idle_in_transaction_session_timeout_ms}ms",
                ),
            )

    def _new_pool(self) -> Any:
        _, psycopg_pool = _load_psycopg()
        app_name = _safe_label(self.config.application_name, max_length=63)
        pool = psycopg_pool.ConnectionPool(
            conninfo=self.config.conninfo,
            kwargs={
                "autocommit": True,
                "application_name": app_name,
                "connect_timeout": max(2, int(math.ceil(self.config.connect_timeout_sec))),
                "tcp_user_timeout": self.config.tcp_user_timeout_ms,
                "keepalives": 1,
                "keepalives_idle": self.config.keepalives_idle_sec,
                "keepalives_interval": self.config.keepalives_interval_sec,
                "keepalives_count": self.config.keepalives_count,
            },
            min_size=self.config.min_size,
            max_size=self.config.max_size,
            open=False,
            configure=self._configure_connection,
            name=f"{_safe_label(self.config.pool_name, max_length=35)}-{os.getpid()}",
            timeout=self.config.pool_timeout_sec,
            max_waiting=self.config.max_waiting,
            max_lifetime=self.config.max_lifetime_sec,
            max_idle=self.config.max_idle_sec,
            reconnect_timeout=self.config.reconnect_timeout_sec,
            num_workers=1,
        )
        pool.open(wait=False)
        return pool

    def ensure(self) -> Any:
        current_pid = os.getpid()
        with self._lock:
            if self._pid != current_pid:
                self._after_fork_child()
            if self._pool is None:
                self._pool = self._new_pool()
                self._generation += 1
            return self._pool

    @contextlib.contextmanager
    def connection(self, *, timeout_sec: float | None = None) -> Iterator[Any]:
        pool = self.ensure()
        timeout = self.config.pool_timeout_sec if timeout_sec is None else timeout_sec
        with pool.connection(timeout=timeout) as conn:
            yield conn

    def invalidate(self) -> None:
        with self._lock:
            pool, self._pool = self._pool, None
            self._generation += 1
        if pool is not None:
            try:
                pool.close(timeout=0.2)
            except Exception:
                pass

    def close(self) -> None:
        with self._lock:
            pool, self._pool = self._pool, None
        if pool is not None:
            try:
                pool.close(timeout=1.0)
            except Exception:
                pass

    def stats(self) -> dict[str, Any]:
        with self._lock:
            pool = self._pool
            generation = self._generation
        if pool is None:
            return {"pool_created": False, "pool_generation": generation}
        try:
            stats = dict(pool.get_stats())
        except Exception:
            stats = {}
        stats["pool_created"] = True
        stats["pool_generation"] = generation
        return stats


class PostgreSqlExecutor:
    """Синхронный PG executor с одним ленивым process-local пулом."""

    def __init__(
        self,
        config: ExecutorConfig,
        *,
        schema_map: Mapping[str, str] | SchemaRegistry | None = None,
        sql_preparer: SqlPreparer | None = None,
    ):
        self.config = config
        self.schemas = schema_map if isinstance(schema_map, SchemaRegistry) else SchemaRegistry(schema_map)
        self.sql_preparer = sql_preparer or _native_sql_preparer
        self._pool = _ProcessLocalPool(config)

    def close(self) -> None:
        self._pool.close()

    def invalidate_pool(self) -> None:
        self._pool.invalidate()

    def pool_stats(self) -> dict[str, Any]:
        return self._pool.stats()

    def transaction(
        self,
        bd: Any,
        *,
        attach_dbs: tuple[Any, ...] | list[Any] | Any = (),
        read_only: bool = False,
        isolation: str = "READ COMMITTED",
        timeout_sec: float | None = None,
    ) -> "PostgreSqlTransaction":
        isolation_normalized = " ".join(isolation.upper().split())
        if isolation_normalized not in _SAFE_ISOLATION_LEVELS:
            raise PostgresConfigurationError(f"Неподдерживаемый уровень изоляции: {isolation}")
        schemas = self.schemas.resolve_many(bd, attach_dbs)
        return PostgreSqlTransaction(
            self,
            schemas=schemas,
            read_only=read_only,
            isolation=isolation_normalized,
            timeout_sec=timeout_sec,
        )

    def custom_request_c(
        self,
        bd: Any,
        custom_request_c: str,
        conn: Any = "",
        hat_c: bool = True,
        list_of_lists_c: Any = None,
        rez_dict: bool = False,
        one: bool = False,
        cur: Any = "",
        one_column: bool = False,
        attach_dbs: tuple[Any, ...] | str = (),
        lazy_method_hours: float = 0,
        debug: bool = True,
    ) -> Any:
        """Совместимый по сигнатуре вход для PG-native SQL.
        ``lazy_method_hours`` принят ради совместимости сигнатуры
        """

        del lazy_method_hours, debug
        params = [[]] if list_of_lists_c is None else list_of_lists_c
        prepared = self.sql_preparer(custom_request_c, params)
        options = {
            "hat_c": bool(hat_c),
            "rez_dict": bool(rez_dict),
            "one": bool(one),
            "one_column": bool(one_column),
        }
        if isinstance(conn, PostgreSqlTransaction):
            if conn.executor is not self:
                raise PostgresConfigurationError("Транзакция принадлежит другому PostgreSqlExecutor")
            return conn._execute_prepared(prepared, **options)
        if not _empty_handle(cur):
            return self._execute_on_cursor(cur, prepared, **options)
        if not _empty_handle(conn):
            with conn.cursor() as external_cursor:
                # Внешним соединением и его COMMIT/ROLLBACK управляет вызывающий код.
                return self._execute_on_cursor(external_cursor, prepared, **options)

        retries_left = self.config.read_disconnect_retries if _is_obviously_read_only(prepared.statement_type) else 0
        while True:
            try:
                with self.transaction(bd, attach_dbs=attach_dbs) as tx:
                    return tx._execute_prepared(prepared, **options)
            except PostgresCommitOutcomeUnknown:
                raise
            except Exception as exc:
                if retries_left and _is_disconnect_error(exc):
                    retries_left -= 1
                    self.invalidate_pool()
                    continue
                if isinstance(exc, PostgresRuntimeError):
                    raise
                if _is_write(prepared.statement_type) and _is_disconnect_error(exc):
                    raise PostgresCommitOutcomeUnknown(
                        prepared.statement_type,
                        "Связь потеряна при записи; результат COMMIT неизвестен, автоповтор запрещён",
                    ) from exc
                raise PostgresExecutionError(
                    prepared.statement_type,
                    f"PostgreSQL-запрос типа {prepared.statement_type} завершился ошибкой",
                ) from exc

    def _execute_on_cursor(
        self,
        cursor: Any,
        prepared: PreparedQuery,
        *,
        hat_c: bool,
        rez_dict: bool,
        one: bool,
        one_column: bool,
    ) -> Any:
        rows: list[Sequence[Any]] = []
        columns: list[str] = []
        if prepared.many:
            wants_rows = bool(re.search(r"\bRETURNING\b", prepared.sql, flags=re.IGNORECASE))
            cursor.executemany(prepared.sql, prepared.params, returning=wants_rows)
            if wants_rows:
                while True:
                    if cursor.description:
                        if not columns:
                            columns = [item.name if hasattr(item, "name") else item[0] for item in cursor.description]
                        rows.extend(cursor.fetchall())
                    if not cursor.nextset():
                        break
        else:
            cursor.execute(prepared.sql, prepared.params)
            if cursor.description:
                columns = [item.name if hasattr(item, "name") else item[0] for item in cursor.description]
                if one:
                    first = cursor.fetchone()
                    rows = [] if first is None else [first]
                else:
                    rows = cursor.fetchall()
        if not columns:
            return True
        return _format_rows(
            rows,
            columns,
            hat_c=hat_c,
            rez_dict=rez_dict,
            one=one,
            one_column=one_column,
        )

    def probe_once(self, *, timeout_sec: float) -> float:
        started = time.perf_counter()
        with self._pool.connection(timeout_sec=timeout_sec) as conn:
            row = conn.execute(PROBE_SQL).fetchone()
        if not row or row[0] != 123:
            raise PostgresExecutionError("SELECT", "Probe PostgreSQL вернул неожиданный ответ")
        return (time.perf_counter() - started) * 1000.0

    def upsert_probe_snapshot(
        self,
        table_name: str,
        snapshot: Mapping[str, Any],
        *,
        timeout_sec: float,
    ) -> None:
        psycopg, _ = _load_psycopg()
        parts = _split_qualified_identifier(table_name)
        table_ident = psycopg.sql.Identifier(*parts)
        query = psycopg.sql.SQL(
            """
            INSERT INTO {} (
                session_id, client_id, app_name, app_version, process_id,
                started_at, last_seen_at, snapshot
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET
                last_seen_at = %s,
                snapshot = %s,
                received_at = clock_timestamp()
            """
        ).format(table_ident)
        identity = snapshot["identity"]
        timestamps = snapshot["timestamps"]
        payload = psycopg.types.json.Jsonb(dict(snapshot))
        values = (
            identity["session_id"],
            identity["client_id"],
            identity["app_name"],
            identity["app_version"],
            identity["process_id"],
            timestamps["started_at"],
            timestamps["last_seen_at"],
            payload,
            timestamps["last_seen_at"],
            payload,
        )
        with self._pool.connection(timeout_sec=timeout_sec) as conn:
            conn.execute(query, values)


def _empty_handle(value: Any) -> bool:
    return value is None or value is False or (isinstance(value, str) and value == "")


class PostgreSqlTransaction:
    """Одна явная транзакция на одном соединении из пула."""

    def __init__(
        self,
        executor: PostgreSqlExecutor,
        *,
        schemas: tuple[str, ...],
        read_only: bool,
        isolation: str,
        timeout_sec: float | None,
    ):
        self.executor = executor
        self.schemas = schemas
        self.read_only = read_only
        self.isolation = isolation
        self.timeout_sec = timeout_sec
        self._connection_cm: Any = None
        self._transaction_cm: Any = None
        self._conn: Any = None
        self._entered = False
        self._write_attempted = False

    def __enter__(self) -> "PostgreSqlTransaction":
        if self._entered:
            raise PostgresConfigurationError("Один объект транзакции нельзя открывать повторно")
        self._connection_cm = self.executor._pool.connection(timeout_sec=self.timeout_sec)
        self._conn = self._connection_cm.__enter__()
        try:
            self._transaction_cm = self._conn.transaction()
            self._transaction_cm.__enter__()
            self._configure_transaction()
        except BaseException:
            self._connection_cm.__exit__(*sys.exc_info())
            self._conn = None
            raise
        self._entered = True
        return self

    def _configure_transaction(self) -> None:
        psycopg, _ = _load_psycopg()
        with self._conn.cursor() as cursor:
            isolation_sql = psycopg.sql.SQL(self.isolation)
            cursor.execute(psycopg.sql.SQL("SET TRANSACTION ISOLATION LEVEL {}").format(isolation_sql))
            if self.read_only:
                cursor.execute("SET TRANSACTION READ ONLY")
            search_path = psycopg.sql.SQL(", ").join(psycopg.sql.Identifier(schema) for schema in self.schemas)
            cursor.execute(psycopg.sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(search_path))

    def custom_request_c(
        self,
        custom_request_c: str,
        *,
        hat_c: bool = True,
        list_of_lists_c: Any = None,
        rez_dict: bool = False,
        one: bool = False,
        one_column: bool = False,
    ) -> Any:
        prepared = self.executor.sql_preparer(
            custom_request_c,
            [[]] if list_of_lists_c is None else list_of_lists_c,
        )
        return self._execute_prepared(
            prepared,
            hat_c=hat_c,
            rez_dict=rez_dict,
            one=one,
            one_column=one_column,
        )

    execute = custom_request_c

    def _execute_prepared(
        self,
        prepared: PreparedQuery,
        *,
        hat_c: bool,
        rez_dict: bool,
        one: bool,
        one_column: bool,
    ) -> Any:
        if not self._entered or self._conn is None:
            raise PostgresConfigurationError("Запрос выполнен вне открытого transaction context")
        if self.read_only and prepared.statement_type in _WRITE_STATEMENTS:
            raise PostgresConfigurationError(
                f"Запрос {prepared.statement_type} запрещён в read_only транзакции"
            )
        self._write_attempted = self._write_attempted or _is_write(prepared.statement_type)
        with self._conn.cursor() as cursor:
            return self.executor._execute_on_cursor(
                cursor,
                prepared,
                hat_c=hat_c,
                rez_dict=rez_dict,
                one=one,
                one_column=one_column,
            )

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        if not self._entered:
            return False
        transaction_result = False
        transaction_error: BaseException | None = None
        try:
            transaction_result = bool(self._transaction_cm.__exit__(exc_type, exc, traceback))
        except BaseException as caught:
            transaction_error = caught
        finally:
            try:
                if transaction_error is None:
                    self._connection_cm.__exit__(exc_type, exc, traceback)
                else:
                    self._connection_cm.__exit__(
                        type(transaction_error), transaction_error, transaction_error.__traceback__
                    )
            finally:
                self._entered = False
                self._conn = None
        if transaction_error is not None:
            if exc_type is None and self._write_attempted and _is_disconnect_error(transaction_error):
                raise PostgresCommitOutcomeUnknown(
                    "WRITE",
                    "Соединение потеряно при завершении транзакции; результат COMMIT неизвестен",
                ) from transaction_error
            raise transaction_error
        return transaction_result


@dataclasses.dataclass(frozen=True, slots=True)
class _ProbeEvent:
    db_alias: str
    statement_type: str
    enqueued_monotonic: float


class _CircuitBreaker:
    def __init__(self, config: ProbeConfig):
        self.config = config
        self._lock = threading.Lock()
        self._state = "closed"
        self._consecutive_failures = 0
        self._cooldown_index = 0
        self._open_until_monotonic = 0.0
        self._half_open_in_flight = False
        self._last_open_seconds = 0.0

    def fast_is_open(self, now: float) -> bool:
        with self._lock:
            return self._state == "open" and now < self._open_until_monotonic

    def before_execute(self, now: float) -> bool:
        with self._lock:
            if self._state == "closed":
                return True
            if self._state == "open":
                if now < self._open_until_monotonic:
                    return False
                self._state = "half_open"
                self._half_open_in_flight = True
                return True
            if self._state == "half_open":
                if self._half_open_in_flight:
                    return False
                self._half_open_in_flight = True
                return True
            return False

    def success(self) -> None:
        with self._lock:
            self._state = "closed"
            self._consecutive_failures = 0
            self._cooldown_index = 0
            self._open_until_monotonic = 0.0
            self._half_open_in_flight = False

    def failure(self, now: float) -> bool:
        """Учитывает ошибку и возвращает True, если breaker был открыт."""

        with self._lock:
            self._consecutive_failures += 1
            should_open = self._state == "half_open" or self._consecutive_failures >= self.config.failure_threshold
            self._half_open_in_flight = False
            if not should_open:
                return False
            base = self.config.cooldown_steps_sec[min(self._cooldown_index, len(self.config.cooldown_steps_sec) - 1)]
            jitter = base * self.config.cooldown_jitter_ratio
            seconds = max(0.1, base + random.uniform(-jitter, jitter))
            self._state = "open"
            self._open_until_monotonic = now + seconds
            self._last_open_seconds = seconds
            self._cooldown_index = min(self._cooldown_index + 1, len(self.config.cooldown_steps_sec) - 1)
            return True

    def force_open(self, now: float) -> bool:
        """Открывает breaker при зависшем worker, не выполняя сетевых действий."""

        with self._lock:
            if self._state == "open" and now < self._open_until_monotonic:
                return False
            base = self.config.cooldown_steps_sec[min(self._cooldown_index, len(self.config.cooldown_steps_sec) - 1)]
            jitter = base * self.config.cooldown_jitter_ratio
            seconds = max(0.1, base + random.uniform(-jitter, jitter))
            self._state = "open"
            self._open_until_monotonic = now + seconds
            self._last_open_seconds = seconds
            self._half_open_in_flight = False
            self._cooldown_index = min(self._cooldown_index + 1, len(self.config.cooldown_steps_sec) - 1)
            return True

    def snapshot(self, now: float) -> dict[str, Any]:
        with self._lock:
            remaining = max(0.0, self._open_until_monotonic - now) if self._state == "open" else 0.0
            return {
                "state": self._state,
                "consecutive_failures": self._consecutive_failures,
                "cooldown_index": self._cooldown_index,
                "open_remaining_sec": round(remaining, 3),
                "last_open_seconds": round(self._last_open_seconds, 3),
            }


class Stage2Probe:

    def __init__(self, executor: _ProbeExecutor, config: ProbeConfig):
        self.executor = executor
        self.config = config
        self._pid = os.getpid()
        self._queue: queue.Queue[_ProbeEvent] = queue.Queue(maxsize=config.queue_size)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._breaker = _CircuitBreaker(config)
        self._counters: Counter[str] = Counter()
        self._by_statement: Counter[str] = Counter()
        self._by_db_alias: Counter[str] = Counter()
        self._rtt_buckets: Counter[str] = Counter()
        self._rtt_sum_ms = 0.0
        self._rtt_max_ms = 0.0
        self._queue_wait_buckets: Counter[str] = Counter()
        self._queue_wait_sum_ms = 0.0
        self._queue_wait_max_ms = 0.0
        self._in_flight_started_monotonic = 0.0
        self._stall_reported = False
        self._started_at = _utc_now()
        self._last_seen_at = self._started_at
        self._session_id = uuid.uuid4().hex
        self._client_id = _safe_label(config.client_id, max_length=40) if config.client_id else self._derive_client_id()
        self._snapshot_path = config.spool_dir / f"{self._client_id}_{self._session_id}.json"
        self._last_flush_monotonic = time.monotonic()
        if hasattr(os, "register_at_fork"):
            os.register_at_fork(after_in_child=self._after_fork_child)

    def _derive_client_id(self) -> str:
        raw = f"{self.config.identity_salt}|{socket.gethostname()}"
        return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:20]

    def _after_fork_child(self) -> None:
        self._pid = os.getpid()
        self._queue = queue.Queue(maxsize=self.config.queue_size)
        self._stop_event = threading.Event()
        self._thread = None
        self._start_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._breaker = _CircuitBreaker(self.config)
        self._counters = Counter()
        self._by_statement = Counter()
        self._by_db_alias = Counter()
        self._rtt_buckets = Counter()
        self._rtt_sum_ms = 0.0
        self._rtt_max_ms = 0.0
        self._queue_wait_buckets = Counter()
        self._queue_wait_sum_ms = 0.0
        self._queue_wait_max_ms = 0.0
        self._in_flight_started_monotonic = 0.0
        self._stall_reported = False
        self._started_at = _utc_now()
        self._last_seen_at = self._started_at
        self._session_id = uuid.uuid4().hex
        self._snapshot_path = self.config.spool_dir / f"{self._client_id}_{self._session_id}.json"

    @property
    def snapshot_path(self) -> pathlib.Path:
        return self._snapshot_path

    def observe(self, bd: Any, sql: str) -> bool:
        """Пытается поставить probe в очередь и всегда быстро возвращается."""

        try:
            now = time.monotonic()
            try:
                statement = _first_statement_keyword(sql)
            except Exception:
                statement = "UNKNOWN"
            alias = _safe_label(_normalize_db_alias(bd), max_length=64)
            with self._stats_lock:
                self._counters["eligible_requests"] += 1
                self._by_statement[statement] += 1
                self._by_db_alias[alias] += 1
                self._last_seen_at = _utc_now()
                if not self.config.enabled:
                    self._counters["disabled_skipped"] += 1
                    return False
                if self._stop_event.is_set():
                    self._counters["shutdown_skipped"] += 1
                    return False
                if (
                    self._in_flight_started_monotonic
                    and now - self._in_flight_started_monotonic >= self.config.stall_timeout_sec
                ):
                    if not self._stall_reported:
                        self._counters["probe_stall_detected"] += 1
                        self._stall_reported = True
                    if self._breaker.force_open(now):
                        self._counters["breaker_opened"] += 1
                    self._counters["breaker_skipped"] += 1
                    return False
                if self._breaker.fast_is_open(now):
                    self._counters["breaker_skipped"] += 1
                    return False
                event = _ProbeEvent(alias, statement, now)
                try:
                    self._queue.put_nowait(event)
                except queue.Full:
                    self._counters["queue_dropped"] += 1
                    return False
                self._counters["enqueued"] += 1
                self._counters["pending_events"] += 1
            self._ensure_worker()
            return True
        except Exception:
            try:
                self._inc("hook_internal_error")
            except Exception:
                pass
            return False

    def _ensure_worker(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        with self._start_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._worker,
                name="mes-pg-stage2-probe",
                daemon=True,
            )
            self._thread.start()

    def _worker(self) -> None:
        last_event_monotonic = time.monotonic()
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                event = self._queue.get(timeout=0.25)
            except queue.Empty:
                self._flush_if_due()
                if (
                    not self._stop_event.is_set()
                    and time.monotonic() - last_event_monotonic >= self.config.worker_idle_exit_sec
                ):
                    self._flush_snapshot(remote=True)
                    with self._start_lock:
                        if self._queue.empty() and not self._stop_event.is_set():
                            self._thread = None
                            return
                    last_event_monotonic = time.monotonic()
                continue
            last_event_monotonic = time.monotonic()
            try:
                now = time.monotonic()
                self._record_queue_wait((now - event.enqueued_monotonic) * 1000.0)
                if not self._breaker.before_execute(now):
                    self._terminal("breaker_skipped")
                    continue
                self._inc("probe_started")
                with self._stats_lock:
                    self._counters["in_flight"] += 1
                    self._in_flight_started_monotonic = time.monotonic()
                try:
                    rtt_ms = self.executor.probe_once(timeout_sec=self.config.connection_timeout_sec)
                except Exception as exc:
                    if _is_timeout_error(exc):
                        self._terminal("probe_timeout")
                    else:
                        self._terminal("probe_error")
                    opened = self._breaker.failure(time.monotonic())
                    if opened:
                        self._inc("breaker_opened")
                        self.executor.invalidate_pool()
                else:
                    self._record_rtt(rtt_ms)
                    self._terminal("probe_success")
                    self._breaker.success()
                finally:
                    with self._stats_lock:
                        self._counters["in_flight"] -= 1
                        self._in_flight_started_monotonic = 0.0
                        self._stall_reported = False
            finally:
                self._queue.task_done()
                self._flush_if_due()
        self._flush_snapshot(remote=True)

    def _inc(self, key: str, amount: int = 1) -> None:
        with self._stats_lock:
            self._counters[key] += amount

    def _terminal(self, key: str) -> None:
        with self._stats_lock:
            self._counters[key] += 1
            self._counters["pending_events"] -= 1

    def _record_rtt(self, rtt_ms: float) -> None:
        label = _duration_bucket(rtt_ms)
        with self._stats_lock:
            self._rtt_buckets[label] += 1
            self._rtt_sum_ms += rtt_ms
            self._rtt_max_ms = max(self._rtt_max_ms, rtt_ms)

    def _record_queue_wait(self, wait_ms: float) -> None:
        label = _duration_bucket(wait_ms)
        with self._stats_lock:
            self._queue_wait_buckets[label] += 1
            self._queue_wait_sum_ms += wait_ms
            self._queue_wait_max_ms = max(self._queue_wait_max_ms, wait_ms)
            self._counters["queue_dequeued"] += 1

    def _flush_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_flush_monotonic >= self.config.flush_interval_sec:
            self._last_flush_monotonic = now
            self._flush_snapshot(remote=True)

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        with self._stats_lock:
            counters = dict(self._counters)
            statements = dict(self._by_statement)
            aliases = dict(self._by_db_alias)
            buckets = dict(self._rtt_buckets)
            rtt_sum = self._rtt_sum_ms
            rtt_max = self._rtt_max_ms
            queue_wait_buckets = dict(self._queue_wait_buckets)
            queue_wait_sum = self._queue_wait_sum_ms
            queue_wait_max = self._queue_wait_max_ms
            in_flight_started = self._in_flight_started_monotonic
            started_at = self._started_at
            last_seen_at = self._last_seen_at
        successes = int(counters.get("probe_success", 0))
        terminal = sum(
            int(counters.get(key, 0))
            for key in (
                "probe_success",
                "probe_timeout",
                "probe_error",
                "queue_dropped",
                "breaker_skipped",
                "disabled_skipped",
                "shutdown_skipped",
            )
        )
        eligible = int(counters.get("eligible_requests", 0))
        queued = self._queue.qsize()
        in_flight = int(counters.get("in_flight", 0))
        in_flight_age = max(0.0, now - in_flight_started) if in_flight_started else 0.0
        dequeued = int(counters.get("queue_dequeued", 0))
        pending = int(counters.get("pending_events", 0))
        equation_delta = eligible - terminal - pending
        return {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "identity": {
                "session_id": self._session_id,
                "client_id": self._client_id,
                "app_name": self.executor.config.application_name
                if isinstance(self.executor, PostgreSqlExecutor)
                else "self-test",
                "app_version": self.config.app_version,
                "runtime_version": RUNTIME_VERSION,
                "process_id": self._pid,
            },
            "timestamps": {
                "started_at": _iso_utc(started_at),
                "last_seen_at": _iso_utc(last_seen_at),
                "snapshot_at": _iso_utc(),
            },
            "probe": {
                "enabled": self.config.enabled,
                "queue_size_limit": self.config.queue_size,
                "queue_depth": queued,
                "in_flight_age_sec": round(in_flight_age, 3),
                "counters": counters,
                "by_statement_type": statements,
                "by_db_alias": aliases,
                "rtt_ms": {
                    "count": successes,
                    "average": round(rtt_sum / successes, 3) if successes else None,
                    "max": round(rtt_max, 3) if successes else None,
                    "buckets": buckets,
                },
                "queue_wait_ms": {
                    "count": dequeued,
                    "average": round(queue_wait_sum / dequeued, 3) if dequeued else None,
                    "max": round(queue_wait_max, 3) if dequeued else None,
                    "buckets": queue_wait_buckets,
                },
                "accounting": {
                    "eligible": eligible,
                    "terminal": terminal,
                    "pending": pending,
                    "queued": queued,
                    "in_flight": in_flight,
                    "delta": equation_delta,
                    "valid": equation_delta == 0,
                },
                "circuit_breaker": self._breaker.snapshot(now),
            },
            "pool": self.executor.pool_stats(),
        }

    def _flush_snapshot(self, *, remote: bool) -> None:
        snapshot = self.snapshot()
        try:
            self.config.spool_dir.mkdir(parents=True, exist_ok=True)
            temporary = self._snapshot_path.with_suffix(self._snapshot_path.suffix + ".tmp")
            data = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2)
            temporary.write_text(data, encoding="utf-8")
            os.replace(temporary, self._snapshot_path)
            self._inc("local_flush_success")
        except Exception:
            self._inc("local_flush_error")
        if remote and self.config.telemetry_table:
            try:
                self.executor.upsert_probe_snapshot(
                    self.config.telemetry_table,
                    snapshot,
                    timeout_sec=self.config.connection_timeout_sec,
                )
                self._inc("remote_flush_success")
            except Exception:
                self._inc("remote_flush_error")

    def close(self, *, drain_timeout_sec: float = 1.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(0.0, drain_timeout_sec))
        if thread is None or not thread.is_alive():
            self._flush_snapshot(remote=False)
        self.executor.close()


_default_lock = threading.RLock()
_default_executor: PostgreSqlExecutor | None = None
_default_probe: Stage2Probe | None = None


def configure_default_runtime(
    executor_config: ExecutorConfig,
    *,
    probe_config: ProbeConfig | None = None,
    schema_map: Mapping[str, str] | SchemaRegistry | None = None,
    sql_preparer: SqlPreparer | None = None,
) -> PostgreSqlExecutor:
    """Атомарно устанавливает runtime по умолчанию, не открывая соединение."""

    global _default_executor, _default_probe
    executor = PostgreSqlExecutor(
        executor_config,
        schema_map=schema_map,
        sql_preparer=sql_preparer,
    )
    probe = Stage2Probe(executor, probe_config) if probe_config is not None else None
    with _default_lock:
        old_probe, old_executor = _default_probe, _default_executor
        _default_executor, _default_probe = executor, probe
    if old_probe is not None:
        old_probe.close(drain_timeout_sec=0.2)
    elif old_executor is not None:
        old_executor.close()
    return executor


def configure_default_from_env(*, strict: bool = False) -> bool:
    """Конфигурирует runtime из env; при strict=False безопасно возвращает False."""

    try:
        probe_config = ProbeConfig.from_env()
        if not probe_config.enabled and not strict:
            return False
        executor_config = ExecutorConfig.from_env()
        schema_registry = SchemaRegistry.from_env()
        configure_default_runtime(
            executor_config,
            probe_config=probe_config,
            schema_map=schema_registry,
        )
        return True
    except Exception:
        if strict:
            raise
        return False


def _require_default_executor() -> PostgreSqlExecutor:
    with _default_lock:
        executor = _default_executor
    if executor is None:
        raise PostgresConfigurationError(
            "PostgreSQL runtime не настроен; вызовите configure_default_runtime()/configure_default_from_env()"
        )
    return executor


def custom_request_c(
    bd: Any,
    custom_request_c: str,
    conn: Any = "",
    hat_c: bool = True,
    list_of_lists_c: Any = None,
    rez_dict: bool = False,
    one: bool = False,
    cur: Any = "",
    one_column: bool = False,
    attach_dbs: tuple[Any, ...] | str = (),
    lazy_method_hours: float = 0,
    debug: bool = True,
) -> Any:

    return _require_default_executor().custom_request_c(
        bd,
        custom_request_c,
        conn=conn,
        hat_c=hat_c,
        list_of_lists_c=list_of_lists_c,
        rez_dict=rez_dict,
        one=one,
        cur=cur,
        one_column=one_column,
        attach_dbs=attach_dbs,
        lazy_method_hours=lazy_method_hours,
        debug=debug,
    )


def transaction(
    bd: Any,
    *,
    attach_dbs: tuple[Any, ...] | list[Any] | Any = (),
    read_only: bool = False,
    isolation: str = "READ COMMITTED",
    timeout_sec: float | None = None,
) -> PostgreSqlTransaction:
    return _require_default_executor().transaction(
        bd,
        attach_dbs=attach_dbs,
        read_only=read_only,
        isolation=isolation,
        timeout_sec=timeout_sec,
    )


def stage2_observe_request(bd: Any, sql: str) -> bool:

    with _default_lock:
        probe = _default_probe
    if probe is None:
        return False
    return probe.observe(bd, sql)

def observe_request(bd: Any, sql: str) -> bool:

    with _default_lock:
        probe = _default_probe
    if probe is None:
        return False
    return probe.observe(bd, sql)


def stage2_snapshot() -> dict[str, Any]:
    with _default_lock:
        probe = _default_probe
    return probe.snapshot() if probe is not None else {"configured": False}


def make_snapshot() -> dict[str, Any]:
    with _default_lock:
        probe = _default_probe
    return probe.snapshot() if probe is not None else {"configured": False}


def shutdown_default_runtime() -> None:
    global _default_executor, _default_probe
    with _default_lock:
        probe, executor = _default_probe, _default_executor
        _default_probe, _default_executor = None, None
    if probe is not None:
        probe.close(drain_timeout_sec=1.0)
    elif executor is not None:
        executor.close()


atexit.register(shutdown_default_runtime)


class _SelfTestExecutor:
    def __init__(self, outcomes: list[Any] | None = None):
        self.outcomes = queue.Queue()
        for item in outcomes or []:
            self.outcomes.put(item)
        self.closed = False
        self.invalidations = 0

    def probe_once(self, *, timeout_sec: float) -> float:
        del timeout_sec
        try:
            outcome = self.outcomes.get_nowait()
        except queue.Empty:
            outcome = 2.0
        if isinstance(outcome, BaseException):
            raise outcome
        return float(outcome)

    def pool_stats(self) -> dict[str, Any]:
        return {"self_test": True}

    def invalidate_pool(self) -> None:
        self.invalidations += 1

    def upsert_probe_snapshot(self, table_name: str, snapshot: Mapping[str, Any], *, timeout_sec: float) -> None:
        del table_name, snapshot, timeout_sec

    def close(self) -> None:
        self.closed = True


def _wait_for(predicate: Callable[[], bool], timeout_sec: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _run_self_test() -> None:
    assert _first_statement_keyword("\ufeff -- comment\n /* x */ SELECT 1") == "SELECT"
    assert _first_statement_keyword("WITH x AS (SELECT 1) SELECT * FROM x") == "WITH"
    assert _normalize_db_alias(r"C:\\DB_srv\\Naryad.db") == "Naryad"
    assert _normalize_db_alias(r"SRV:BD_users.db\\ignored") == "BD_users"
    assert _native_sql_preparer("SELECT %s", [[7]]).params == (7,)
    assert _native_sql_preparer("UPDATE t SET x=%s", [[1], [2]]).many is True
    assert _format_rows([(1, 2)], ["x", "x"], hat_c=False, rez_dict=True, one=True, one_column=False) == {
        "x": 1,
        "1_x": 2,
    }
    assert _format_rows([(123,)], ["probe"], hat_c=False, rez_dict=False, one=True, one_column=True) == 123

    with tempfile.TemporaryDirectory(prefix="mes_pg_stage2_test_") as temp_dir:
        executor = _SelfTestExecutor([3.0, 7.0, 12.0])
        probe = Stage2Probe(
            executor,
            ProbeConfig(
                enabled=True,
                queue_size=8,
                failure_threshold=2,
                cooldown_steps_sec=(10.0,),
                cooldown_jitter_ratio=0,
                flush_interval_sec=0.05,
                worker_idle_exit_sec=0.05,
                spool_dir=pathlib.Path(temp_dir),
            ),
        )
        for _ in range(3):
            assert probe.observe("SRV:Naryad.db", "SELECT 1")
        assert _wait_for(lambda: probe.snapshot()["probe"]["counters"].get("probe_success") == 3)
        assert probe.snapshot()["probe"]["accounting"]["valid"] is True
        assert _wait_for(lambda: probe._thread is None)
        assert probe.observe("SRV:Naryad.db", "SELECT 2")
        assert _wait_for(lambda: probe.snapshot()["probe"]["counters"].get("probe_success") == 4)
        probe.close()
        assert probe.snapshot_path.exists()

    with tempfile.TemporaryDirectory(prefix="mes_pg_stage2_breaker_") as temp_dir:
        executor = _SelfTestExecutor([TimeoutError("test timeout")])
        probe = Stage2Probe(
            executor,
            ProbeConfig(
                enabled=True,
                queue_size=4,
                failure_threshold=1,
                cooldown_steps_sec=(10.0,),
                cooldown_jitter_ratio=0,
                flush_interval_sec=10.0,
                spool_dir=pathlib.Path(temp_dir),
            ),
        )
        assert probe.observe("BD_users.db", "UPDATE employee SET x = 1")
        assert _wait_for(lambda: probe.snapshot()["probe"]["counters"].get("probe_timeout") == 1)
        assert probe.observe("BD_users.db", "SELECT 1") is False
        assert probe.snapshot()["probe"]["counters"].get("breaker_skipped") == 1
        assert executor.invalidations == 1
        probe.close()

    with tempfile.TemporaryDirectory(prefix="mes_pg_stage2_stall_") as temp_dir:
        executor = _SelfTestExecutor()
        probe = Stage2Probe(
            executor,
            ProbeConfig(
                enabled=True,
                stall_timeout_sec=0.01,
                spool_dir=pathlib.Path(temp_dir),
            ),
        )
        probe._in_flight_started_monotonic = time.monotonic() - 1.0
        assert probe.observe("BD_users.db", "SELECT 1") is False
        counters = probe.snapshot()["probe"]["counters"]
        assert counters.get("probe_stall_detected") == 1
        assert counters.get("breaker_skipped") == 1
        probe.close()

    print("SELF-TEST OK: executor helpers, formatter, queue и circuit breaker")


def _run_live_probe(count: int) -> None:
    executor_config = ExecutorConfig.from_env()
    executor = PostgreSqlExecutor(executor_config)
    try:
        timings = [executor.probe_once(timeout_sec=2.0) for _ in range(count)]
        print(
            json.dumps(
                {
                    "success": len(timings),
                    "rtt_ms": [round(item, 3) for item in timings],
                    "pool": executor.pool_stats(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        executor.close()


def _main() -> None:
    parser = argparse.ArgumentParser(description="MES PostgreSQL executor / Stage 2 probe")
    parser.add_argument(
        "--live-probe",
        action="store_true",
        help="явно выполнить SELECT 123 по MES_PG_DSN (по умолчанию сеть не используется)",
    )
    parser.add_argument("--count", type=int, default=3, help="число запросов для --live-probe")
    args = parser.parse_args()
    if args.live_probe:
        if args.count < 1 or args.count > 100:
            raise SystemExit("--count должен быть в диапазоне 1..100")
        _run_live_probe(args.count)
    else:
        _run_self_test()


if __name__ == "__main__":
    _main()
