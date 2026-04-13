from __future__ import annotations

import dataclasses
import os
import pickle
import re
import threading

try:
    import psycopg  # type: ignore
except Exception:
    psycopg = None  # type: ignore

try:
    import psycopg2  # type: ignore
except Exception:
    psycopg2 = None  # type: ignore


__all__ = [
    'PostgresConfig',
    'PostgresConnectionError',
    'PostgresDriverUnavailable',
    'connect_pg',
    'close_pg',
    'custom_request_pg',
    'pg_placeholders',
    'PostgresPayloadCache',
]
Connect = None
Cursor = None


import dataclasses
import os
import threading

try:
    import psycopg  # type: ignore
except Exception:
    psycopg = None  # type: ignore


_PG_LOCK = threading.RLock()
_PG_CONN = None
_PG_CONN_PID = None


def _is_psycopg3_cursor(cur) -> bool:
    try:
        return cur.__class__.__module__.startswith('psycopg')
    except Exception:
        return False


def _normalize_pg_bytes(raw):
    if raw in (None, ''):
        return None
    if isinstance(raw, memoryview):
        return raw.tobytes()
    if isinstance(raw, bytearray):
        return bytes(raw)
    return raw

def _conn_closed(conn) -> bool:
    if conn is None:
        return True
    try:
        return bool(conn.closed)
    except Exception:
        return True


def reset_process_conn():
    global _PG_CONN, _PG_CONN_PID
    with _PG_LOCK:
        try:
            if _PG_CONN is not None:
                _PG_CONN.close()
        except Exception:
            pass
        _PG_CONN = None
        _PG_CONN_PID = None


def get_process_conn(config=None):
    global _PG_CONN, _PG_CONN_PID

    if config is None:
        config = PostgresConfig()

    pid = os.getpid()
    with _PG_LOCK:
        # защита от reuse после fork
        if _PG_CONN_PID != pid:
            reset_process_conn()
            _PG_CONN_PID = pid

        if _conn_closed(_PG_CONN):
            _PG_CONN = psycopg.connect(
                host=config.host,
                port=config.port,
                dbname=config.dbname,
                user=config.user,
                password=config.password,
                connect_timeout=config.connect_timeout,
                application_name=config.application_name,
                sslmode=config.sslmode,
                gssencmode=config.gssencmode,
                options=config.options or None,
                autocommit=True,
            )

        return _PG_CONN

class PostgresConnectionError(RuntimeError):
    pass


class PostgresDriverUnavailable(RuntimeError):
    pass


def _driver_name() -> str:
    if psycopg is not None:
        return 'psycopg'
    if psycopg2 is not None:
        return 'psycopg2'
    raise PostgresDriverUnavailable(
        'Не найден драйвер PostgreSQL. Установи psycopg (v3) или psycopg2.'
    )


def _safe_ident(value: str, *, label: str = 'identifier') -> str:
    text = str(value or '').strip()
    if not text:
        raise ValueError(f'Пустой {label}')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', text):
        raise ValueError(f'Некорректный {label}: {value!r}')
    return text


def pg_placeholders(values_or_count) -> str:
    if isinstance(values_or_count, int):
        count = int(values_or_count)
    else:
        count = len(values_or_count)
    if count <= 0:
        return ''
    return ', '.join(['%s'] * count)


@dataclasses.dataclass
class PostgresConfig:
    host: str = '127.0.0.1'
    port: int = 5432
    dbname: str = ''
    user: str = 'postgres'
    password: str = 'Adr1959967 '
    connect_timeout: int = 5
    application_name: str = 'mes_pg_cache'
    schema_name: str = 'public'
    table_name: str = 'mes_request_cache_payload'
    options: str = ''
    sslmode: str = 'disable'
    gssencmode: str = 'disable'

    @classmethod
    def from_env(cls, prefix: str = 'MES_PG_') -> 'PostgresConfig':
        def env(name: str, default: str = '') -> str:
            return os.environ.get(prefix + name, default)

        port_raw = env('PORT', '5432')
        timeout_raw = env('CONNECT_TIMEOUT', '5')
        return cls(
            host=env('HOST', '127.0.0.1'),
            port=int(port_raw or 5432),
            dbname='mes_cache', # env('DBNAME', ''),
            user='postgres', # env('USER', ''),
            password='Adr1959967', # env('PASSWORD', ''),
            connect_timeout=int(timeout_raw or 5),
            application_name=env('APPLICATION_NAME', 'mes_pg_cache'),
            sslmode=env('SSLMODE', 'prefer'),
            schema_name=env('SCHEMA', 'public'),
            table_name=env('TABLE', 'mes_request_cache_payload'),
            options=env('OPTIONS', ''),
        )

    @property
    def schema(self) -> str:
        return _safe_ident(self.schema_name, label='schema_name')

    @property
    def table(self) -> str:
        return _safe_ident(self.table_name, label='table_name')

    @property
    def qualified_table(self) -> str:
        return f'{self.schema}.{self.table}'

    def masked_dsn(self) -> str:
        pwd = '***' if self.password else ''
        return (
            f'host={self.host} port={self.port} dbname={self.dbname} '
            f'user={self.user} password={pwd} application_name={self.application_name}'
        )


def connect_pg(config: PostgresConfig):
    driver = _driver_name()
    try:
        if driver == 'psycopg':
            conn = psycopg.connect(  # type: ignore[attr-defined]
                host=config.host,
                port=config.port,
                dbname=config.dbname,
                user=config.user,
                password=config.password,
                connect_timeout=config.connect_timeout,
                application_name=config.application_name,
                sslmode=config.sslmode,
                options=config.options or None,
                autocommit=True,
                gssencmode=config.gssencmode,
            )
            cur = conn.cursor()
            return conn, cur

        conn = psycopg2.connect(  # type: ignore[attr-defined]
            host=config.host,
            port=config.port,
            dbname=config.dbname,
            user=config.user,
            password=config.password,
            connect_timeout=config.connect_timeout,
            application_name=config.application_name,
            sslmode=config.sslmode,
            options=config.options or None,
        )
        conn.autocommit = True
        cur = conn.cursor()
        return conn, cur
    except Exception as e:
        raise PostgresConnectionError(
            f'Ошибка подключения к PostgreSQL: {config.masked_dsn()} | {e}'
        ) from e


def close_pg(conn, cur=''):
    try:
        if cur not in ('', None):
            cur.close()
    except Exception:
        pass
    try:
        if conn not in ('', None):
            conn.close()
    except Exception:
        pass


def _rows_to_dict(cur, rows) -> list[dict]:
    cols = [col[0] for col in (cur.description or [])]
    result = []
    for row in rows:
        result.append({cols[i]: row[i] for i in range(len(cols))})
    return result


def custom_request_pg(
    query: str,
    params=None,
    *,
    rez_dict: bool = False,
    one: bool = False,
    one_column: bool = False,
    conn='',
    cur='',
        config = None
):
    if config is None:
        config = PostgresConfig()
    conn = conn or get_process_conn(config)

    cur = conn.cursor()
    # if Connect is not None and not Connect.closed:
    #     conn = Connect
    #
    # if Cursor is not None:
    #     cur = Cursor

    own_conn = False
    if conn in ('', None) or cur in ('', None):
        conn, cur = connect_pg(config)
        own_conn = True

    try:
        if params and len(params) >= 1 and isinstance(params[0], (list, tuple)):
            cur.executemany(query, params)
        else:
            cur.execute(query, params)
        has_result = cur.description is not None

        if not has_result:
            return True

        if one:
            row = cur.fetchone()
            rows = [] if row is None else [row]
        else:
            rows = cur.fetchall()

        if rez_dict:
            data = _rows_to_dict(cur, rows)
            if one:
                data = data[0] if data else {}
        else:
            data = [list(row) for row in rows]
            if one:
                data = data[0] if data else []

        if one_column:
            if rez_dict:
                if one:
                    if isinstance(data, dict) and data:
                        return next(iter(data.values()))
                    return None
                return [next(iter(item.values())) for item in data if item]
            if one:
                if isinstance(data, list) and data:
                    return data[0]
                return None
            return [row[0] for row in data]

        return data
    finally:
        if own_conn:
            close_pg(conn, cur)


class PostgresPayloadCache:
    def __init__(self, config: PostgresConfig):
        self.config = config
        self._lock = threading.RLock()

    def ensure_schema(self) -> bool:
        schema = self.config.schema
        table = self.config.table
        ddl_schema = f'CREATE SCHEMA IF NOT EXISTS {schema};'
        ddl_table = f"""
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            request_key TEXT PRIMARY KEY,
            body_hash TEXT NOT NULL DEFAULT '',
            payload_bytes BYTEA NOT NULL
        );
        """
        ddl_index = f"""
        CREATE INDEX IF NOT EXISTS idx_{table}_body_hash
            ON {schema}.{table}(body_hash);
        """
        with self._lock:
            custom_request_pg(self.config, ddl_schema)
            custom_request_pg(self.config, ddl_table)
            custom_request_pg(self.config, ddl_index)
        return True

    def exists(self, request_key: str) -> bool:
        sql = f'SELECT 1 FROM {self.config.qualified_table} WHERE request_key = %s'
        row = custom_request_pg(self.config, sql, [str(request_key)], one=True)
        return bool(row)

    def get_body_hash(self, request_key: str) -> str | None:
        sql = f'SELECT body_hash FROM {self.config.qualified_table} WHERE request_key = %s'
        return custom_request_pg(self.config, sql, [str(request_key)], one=True, one_column=True)

    def write_payload(self, request_key: str, payload, body_hash: str = '') -> bool:
        payload_bytes = pickle.dumps(payload, protocol=4)
        sql = f"""
        INSERT INTO {self.config.qualified_table} (request_key, body_hash, payload_bytes)
        VALUES (%s, %s, %s)
        ON CONFLICT (request_key)
        DO UPDATE SET
            body_hash = EXCLUDED.body_hash,
            payload_bytes = EXCLUDED.payload_bytes
        """
        with self._lock:
            return bool(custom_request_pg(
                self.config,
                sql,
                [str(request_key), str(body_hash or ''), payload_bytes],
            ))

    def read_payload_bytes(self, request_key: str) -> bytes | None:
        sql = f'SELECT payload_bytes FROM {self.config.qualified_table} WHERE request_key = %s'
        raw = custom_request_pg(self.config, sql, [str(request_key)], one=True, one_column=True)
        if raw in (None, ''):
            return None
        if isinstance(raw, memoryview):
            return raw.tobytes()
        if isinstance(raw, bytearray):
            return bytes(raw)
        return raw

    def read_payload(self, request_key: str):
        raw = self.read_payload_bytes(request_key)
        if raw is None:
            return None
        try:
            return pickle.loads(raw)
        except Exception:
            return None

    def read_entry(self, request_key: str) -> dict | None:
        sql = f"""
        SELECT request_key, body_hash, payload_bytes
        FROM {self.config.qualified_table}
        WHERE request_key = %s
        """
        row = custom_request_pg(self.config, sql, [str(request_key)], one=True, rez_dict=True)
        if not row:
            return None
        payload_bytes = row.get('payload_bytes')
        if isinstance(payload_bytes, memoryview):
            payload_bytes = payload_bytes.tobytes()
        elif isinstance(payload_bytes, bytearray):
            payload_bytes = bytes(payload_bytes)
        row['payload'] = pickle.loads(payload_bytes)
        return row

    def delete_payload(self, request_key: str) -> bool:
        sql = f'DELETE FROM {self.config.qualified_table} WHERE request_key = %s'
        with self._lock:
            return bool(custom_request_pg(self.config, sql, [str(request_key)]))

    def clear(self) -> bool:
        sql = f'DELETE FROM {self.config.qualified_table}'
        with self._lock:
            return bool(custom_request_pg(self.config, sql))

    def _read_payload(self, request_key: str):
        return self.read_payload(request_key)

    def _write_payload(self, request_key: str, payload, body_hash: str = '') -> bool:
        return self.write_payload(request_key=request_key, payload=payload, body_hash=body_hash)

    def _remove_payload(self, request_key: str) -> bool:
        return self.delete_payload(request_key)
