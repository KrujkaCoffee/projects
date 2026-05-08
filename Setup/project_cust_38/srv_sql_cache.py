from __future__ import annotations

import zlib

import copy
import datetime
import logging
import os
import pickle
import re
import threading
import time
import traceback
import typing
import tempfile
import pathlib
import hashlib
import json
import shutil
from typing import Any, Iterable, Mapping, Sequence

import project_cust_38.Cust_Functions as F  # noqa
import project_cust_38.Cust_SQLite as CSQ   # noqa

try:
    import Cust_postgresql_cache as CPG
except Exception as e:
    CPG = None

__all__ = [
    'CACHE_STATUS',
    'FileRequestCache',
    'build_request_key',
    'build_body_hash',
    'extract_query_table_records',
    'is_cacheable_sql',
    'is_db_files_path',
    'normalize_attach_dbs',

    'get_entry_meta',
    'touch_entry',
]

logger = logging.getLogger()

_LOCAL_SQL_CACHE_DIR = pathlib.Path(tempfile.gettempdir()) / 'mes_local_sql_cache'
_LOCAL_SQL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

class CACHE_STATUS:
    BYPASS = 'BYPASS'
    MISS = 'MISS'
    SERVER_HIT = 'SERVER_HIT'
    CLIENT_FRESH = 'CLIENT_FRESH'
    CLIENT_STALE = 'CLIENT_STALE'
    REFRESH = 'REFRESH'


DEFAULT_CACHE_LIFETIME_SEC = 120 * 60
_DB_FILES_BASENAMES = {'bd_files.db', 'db_files.db'}
REQUEST_CACHE_META_TABLE = 'admin_request_cache_meta'
REQUEST_CACHE_TABLES_TABLE = 'admin_request_cache_tables'
SERVER_CACHE_DIR = pathlib.Path(tempfile.gettempdir()) / 'mes_srv_sql_cache'
SERVER_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class _CacheUtils:
    @staticmethod
    def json_dumps(data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, sort_keys=False, default=str, separators=(',', ':'))

    @staticmethod
    def sha256_text(text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    @staticmethod
    def normalize_attach_dbs(value: Iterable[str] | str | None) -> tuple[str, ...]:
        if value in (None, '', ()):
            return ()
        if isinstance(value, str):
            return (str(value),)
        return tuple(str(item) for item in value if item not in (None, ''))

    @staticmethod
    def normalize_path(value: Any) -> str:
        if value in (None, ''):
            return ''
        text = str(value).strip().strip('"').strip("'")
        if not text:
            return ''
        return str(pathlib.Path(text))

    def normalize_params(self, params: Any) -> Any:
        if isinstance(params, tuple):
            return [self.normalize_params(v) for v in params]
        if isinstance(params, list):
            return [self.normalize_params(v) for v in params]
        if isinstance(params, Mapping):
            return {str(k): self.normalize_params(v) for k, v in params.items()}
        return self.to_jsonable(params)

    def to_jsonable(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, Mapping):
            return {str(k): self.to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self.to_jsonable(v) for v in value]
        if isinstance(value, pathlib.Path):
            return str(value)
        return repr(value)

    @staticmethod
    def parse_dt(value: Any) -> datetime.datetime | None:
        if value in (None, ''):
            return None
        if isinstance(value, datetime.datetime):
            return value
        text = str(value).strip()
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.datetime.strptime(text, fmt)
            except Exception as e:
                traceback.print_exc()
                print(e)
                pass
        try:
            return datetime.datetime.fromisoformat(text)
        except Exception as e:
            traceback.print_exc()
            print(e)
            return None

    @staticmethod
    def strip_sql_comments(sql: str) -> str:
        sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.S)
        sql = re.sub(r'--[^\n]*', ' ', sql)
        return sql
    @staticmethod
    def normalize_sql_name(token: str) -> str:
        text = str(token).strip().strip(',;')
        text = text.strip('"').strip('`').strip('[').strip(']')
        return text

    def extract_cte_names(self, sql: str) -> set[str]:
        cleaned = self.strip_sql_comments(sql)
        found = set()
        for match in re.finditer(r'\bWITH\s+([A-Za-z_][\w]*)\s+AS\b', cleaned, flags=re.I): # noqa
            found.add(match.group(1))
        for match in re.finditer(r',\s*([A-Za-z_][\w]*)\s+AS\b', cleaned, flags=re.I): # noqa
            found.add(match.group(1))
        return found

    @staticmethod
    def is_suspicious_payload(payload) -> bool:
        return payload in (None, [], {}, (), True, False)

    @staticmethod
    def cache_file_path(request_key: str) -> pathlib.Path:
        return _LOCAL_SQL_CACHE_DIR / f'{request_key}.pickle'

    def read_cache_entry_local(self, request_key: str):
        path = self.cache_file_path(request_key)
        if not path.exists():
            return None
        try:
            with open(path, 'rb') as desc:
                data = pickle.load(desc)
            if not isinstance(data, dict) or 'payload' not in data:
                return None
            return data
        except Exception: # noqa
            try:
                path.unlink(missing_ok=True)
            except Exception: # noqa
                pass
            return None

    @staticmethod
    def inspect_local_cache() -> dict:
        files = sorted(_LOCAL_SQL_CACHE_DIR.glob('*.pickle'))
        return {
            'cache_dir': str(_LOCAL_SQL_CACHE_DIR),
            'entries': len(files),
            'files': [file.name for file in files],
        }

    @staticmethod
    def purge_expired_local_cache(max_age_days: int = 14) -> int:
        now_stamp = time.time()
        removed = 0
        for file_path in _LOCAL_SQL_CACHE_DIR.glob('*.pickle'):
            try:
                age_seconds = now_stamp - file_path.stat().st_mtime
                if age_seconds >= max_age_days * 24 * 60 * 60:
                    file_path.unlink(missing_ok=True)
                    removed += 1
            except Exception: # noqa
                continue
        return removed

class CacheBuilder:
    def __init__(self):
        self.db = F.scfg('files')
        self.utils = _CacheUtils()

    def write_cache_entry(self, request_key: str, payload, response_headers=None, *, SrvHeaders):  # noqa
        if self.utils.is_suspicious_payload(payload):
            clear_local_cache(request_key)
            return None
        response_headers = response_headers or {}
        entry = {
            'request_key': request_key,
            'payload': payload,
            'body_hash': response_headers.get(SrvHeaders.BODY_HASH.value) or self.build_body_hash(payload),
            'cached_at': response_headers.get(SrvHeaders.LAST_REFRESH_AT.value) or time.strftime('%Y-%m-%d %H:%M:%S'),
            'cache_status': response_headers.get(SrvHeaders.CACHE_STATUS.value) or 'MISS',
            'cache_lifetime_sec': int(response_headers.get(SrvHeaders.CACHE_LIFETIME_SEC.value) or 0),
            'dependency_fingerprint': str(response_headers.get(SrvHeaders.DEPENDENCY_FINGERPRINT.value) or ''),
            'stale_after_dt': str(response_headers.get(SrvHeaders.STALE_AFTER_DT.value) or ''),
        }
        path = self.utils.cache_file_path(request_key)
        tmp_path = path.with_suffix('.tmp')
        with open(tmp_path, 'wb') as desc:
            pickle.dump(entry, desc, protocol=4) # noqa
        os.replace(tmp_path, path)
        return entry

    def get_valid_local_entry(self, request_key: str):
        entry = self.utils.read_cache_entry_local(request_key)
        if not self.entry_is_fresh(entry):
            self.clear_local_cache(request_key)
            return None
        return entry

    def entry_is_fresh(self, entry: dict | None) -> bool:
        if not entry:
            return False
        if self.utils.is_suspicious_payload(entry.get('payload')):
            return False
        try:
            lifetime = int(entry.get('cache_lifetime_sec') or 0)
        except Exception: # noqa
            lifetime = 0
        cached_at = str(entry.get('cached_at') or '')
        stale_after_dt = str(entry.get('stale_after_dt') or '')
        now = time.time()
        if stale_after_dt:
            try:
                import datetime as _dt
                if _dt.datetime.now() >= _dt.datetime.fromisoformat(stale_after_dt.replace(' ', 'T')):
                    return False
            except Exception: # noqa
                pass
        if lifetime > 0 and cached_at:
            try:
                import datetime as _dt
                dt = _dt.datetime.fromisoformat(cached_at.replace(' ', 'T'))
                if now - dt.timestamp() >= lifetime:
                    return False
            except Exception: # noqa
                return False
        return True

    def is_db_files_path(self, db_path: str | None) -> bool:
        norm = self.utils.normalize_path(db_path)
        if not norm:
            return False
        if pathlib.Path(norm).name.lower() in _DB_FILES_BASENAMES:
            return True
        return bool(self.db and self.db == norm)

    def cacheable_request(self, bd: str, custom_request_c: str, attach_dbs=(), function_db_path: typing.Callable = None):
        if not self.is_cacheable_sql(custom_request_c):
            return False
        if self.is_db_files_path(bd):
            return False
        for attach_db in self.utils.normalize_attach_dbs(attach_dbs):
            attach_path = ''
            try:
                if str(attach_db).startswith('SRV:'):
                    attach_path, _ = function_db_path(str(attach_db))
                else:
                    attach_path = str(attach_db)
            except Exception: # noqa
                attach_path = str(attach_db)
            if self.is_db_files_path(attach_path):
                return False
        return True

    def clear_local_cache(self, request_key: str | None = None):
        if request_key:
            path = self.utils.cache_file_path(request_key)
            try:
                path.unlink(missing_ok=True)
            except Exception: # noqa
                return False
            return True
        try:
            shutil.rmtree(_LOCAL_SQL_CACHE_DIR, ignore_errors=True)
            _LOCAL_SQL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            return True
        except Exception: # noqa
            return False

    @staticmethod
    def is_cacheable_sql(sql_text: str) -> bool:
        text = str(sql_text or '').strip()
        if not text:
            return False
        head = text.split(None, 1)[0].upper()
        return head in {'SELECT', 'WITH'}

    def build_request_key(self, *, db_path: str, sql_text: str, params: Any = None,
                          rez_dict: bool = False, one: bool = False, one_column: bool = False,
                          hat_c: bool = True, attach_dbs: Iterable[str] | str | None = None) -> str:
        payload = {
            'db_path': self.utils.normalize_path(db_path),
            'sql_text': str(sql_text or ''),
            'params': self.utils.normalize_params(params),
            'options': {
                'rez_dict': bool(rez_dict),
                'one': bool(one),
                'one_column': bool(one_column),
                'hat_c': bool(hat_c),
            },
            'attach_dbs': list(self.utils.normalize_attach_dbs(attach_dbs)),
        }
        return self.utils.sha256_text(self.utils.json_dumps(payload))

    def build_body_hash(self, payload: Any) -> str:
        try:
            return hashlib.sha256(pickle.dumps(payload, protocol=4)).hexdigest()
        except Exception:
            serialized = self.utils.json_dumps(self.utils.to_jsonable(payload))
            return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def extract_query_table_records(self, *, sql_text: str, main_db_path: str,
                                    attached_alias_paths: Mapping[str, str] | None = None) -> list[dict[str, str]]:
        cleaned = self.utils.strip_sql_comments(sql_text)
        attached_alias_paths = dict(attached_alias_paths or {})
        cte_names = {name.lower() for name in self.utils.extract_cte_names(cleaned)}
        refs: list[tuple[str, str]] = []

        patterns = (
            r'\bFROM\s+([^\s,()]+)',
            r'\bJOIN\s+([^\s,()]+)',
            r',\s*([^\s,()]+)\s+ON\b',  # новый паттерн для old-style join через запятую
        )

        for pattern in patterns:
            for match in re.finditer(pattern, cleaned, flags=re.I):
                raw = self.utils.normalize_sql_name(match.group(1))
                if not raw or raw.lower() in cte_names or raw.lower() == 'select':
                    continue
                if raw.startswith('('):
                    continue

                if '.' in raw:
                    alias, table_name = raw.split('.', 1)
                    db_path = self.utils.normalize_path(
                        attached_alias_paths.get(self.utils.normalize_sql_name(alias), main_db_path)
                    )
                    table_name = self.utils.normalize_sql_name(table_name)
                else:
                    db_path = self.utils.normalize_path(main_db_path)
                    table_name = raw

                refs.append((db_path, table_name))

        result: list[dict[str, str]] = []
        seen = set()
        for db_path, table_name in refs:
            if not table_name:
                continue
            key = (db_path, table_name)
            if key in seen:
                continue
            seen.add(key)
            db_key = pathlib.Path(db_path).stem or 'unknown_db'
            result.append({
                'db_path': db_path,
                'db_key': db_key,
                'table_name': table_name,
                'table_key': f'{db_key}.{table_name}',
            })
        return result

    def extract_query_table_records_old(self, *, sql_text: str, main_db_path: str,
                                    attached_alias_paths: Mapping[str, str] | None = None) -> list[dict[str, str]]:
        cleaned = self.utils.strip_sql_comments(sql_text)
        attached_alias_paths = dict(attached_alias_paths or {})
        cte_names = {name.lower() for name in self.utils.extract_cte_names(cleaned)}
        refs: list[tuple[str, str]] = []
        for pattern in (r'\bFROM\s+([^\s,()]+)', r'\bJOIN\s+([^\s,()]+)'):
            for match in re.finditer(pattern, cleaned, flags=re.I):
                raw = self.utils.normalize_sql_name(match.group(1))
                if not raw or raw.lower() in cte_names or raw.lower() == 'select':
                    continue
                if raw.startswith('('):
                    continue
                if '.' in raw:
                    alias, table_name = raw.split('.', 1)
                    db_path = self.utils.normalize_path(attached_alias_paths.get(self.utils.normalize_sql_name(alias), main_db_path))
                    table_name = self.utils.normalize_sql_name(table_name)
                else:
                    db_path = self.utils.normalize_path(main_db_path)
                    table_name = raw
                refs.append((db_path, table_name))
        result: list[dict[str, str]] = []
        seen = set()
        for db_path, table_name in refs:
            if not table_name:
                continue
            key = (db_path, table_name)
            if key in seen:
                continue
            seen.add(key)
            db_key = pathlib.Path(db_path).stem or 'unknown_db'
            result.append({'db_path': db_path, 'db_key': db_key, 'table_name': table_name, 'table_key': f'{db_key}.{table_name}'})
        return result




class FileRequestCache:
    def __init__(self, cache_dir: pathlib.Path | None = None):
        self._lock = threading.RLock()
        self.utils = _CacheUtils()
        self.cache_dir = pathlib.Path(cache_dir or SERVER_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _payload_path(self, request_key: str) -> pathlib.Path:
        return self.cache_dir / f'{request_key}.pickle'

    def serialize_payload(self, payload, *, compress_min_bytes: int = 256 * 1024, compress_level: int = 3):
        """
        Возвращает:
            payload_bytes: bytes
            payload_is_compressed: bool
        """
        raw = pickle.dumps(payload, protocol=4)

        if len(raw) < compress_min_bytes:
            return raw, False

        compressed = zlib.compress(raw, level=compress_level)

        if len(compressed) >= len(raw):
            return raw, False

        return compressed, True

    def deserialize_payload(self, entry: dict):
        """
        Ожидает, что entry уже содержит payload_bytes и payload_is_compressed
        """
        try:
            raw = entry.get('payload_bytes')
            if raw is None:
                return None

            if isinstance(raw, memoryview):
                raw = raw.tobytes()
            elif isinstance(raw, bytearray):
                raw = bytes(raw)

            is_compressed = bool(entry.get('payload_is_compressed') or False)
            if is_compressed:
                raw = zlib.decompress(raw)

            return pickle.loads(raw)
        except Exception:
            return None

    def get_entry_payload_record(self, request_key: str) -> dict[str, Any] | None:
        sql = f"""
        SELECT
            payload_bytes,
            payload_is_compressed
        FROM {REQUEST_CACHE_META_TABLE}
        WHERE request_key = {request_key!r}
        """
        row = CPG.custom_request_pg(sql, one=True, rez_dict=True)
        if not row:
            return None
        return row

    def serialize_payload_old(self, payload: Any) -> bytes:
        try:
            return pickle.dumps(payload, protocol=4)
        except Exception: ...

    def deserialize_payload_old(self, raw):
        try:
            if raw is None:
                return None
            if isinstance(raw, memoryview):
                raw = raw.tobytes()
            elif isinstance(raw, bytearray):
                raw = bytes(raw)
            return pickle.loads(raw)
        except Exception:
            return None

    def _write_payload(self, request_key: str, payload: Any) -> pathlib.Path:
        path = self._payload_path(request_key)
        tmp_path = path.with_suffix('.tmp')
        with tmp_path.open('wb') as desc:
            pickle.dump(payload, desc, protocol=4)
        tmp_path.replace(path)
        return path

    def _remove_payload(self, request_key: str) -> None:
        path = self._payload_path(request_key)
        try:
            path.unlink(missing_ok=True)
        except Exception: # noqa
            pass

    def clear(self) -> None:
        conn, cur = CPG.connect_pg(CPG.PostgresConfig())
        drop_1 = CPG.custom_request_pg(
        f'DELETE FROM {REQUEST_CACHE_META_TABLE}', conn=conn, cur=cur)
        drop_2 = CPG.custom_request_pg(
        f'DELETE FROM {REQUEST_CACHE_TABLES_TABLE}', conn=conn, cur=cur)
        print('[srv_sql_cache.clear] drop status:}', str(drop_1), str(drop_2))

    def get_entry_meta(self, request_key: str) -> dict[str, Any] | None:
        sql = f"""
        SELECT
            request_key,
            db_key,
            db_path,
            sql_text,
            params_json,
            options_json,
            body_hash,
            result_state,
            dependency_fingerprint,
            cache_lifetime_sec,
            stale_after_dt,
            invalidated_at,
            last_used_at,
            last_refresh_at,
            last_verified_at,
            notes,
            updated_at
        FROM {REQUEST_CACHE_META_TABLE}
        WHERE request_key = {request_key!r}
        """
        meta = CPG.custom_request_pg(sql, one=True, rez_dict=True)
        print('META RESPONSE:',str( (meta or {}).keys()))
        if not meta:
            return None
        # if not meta.get('payload_bytes'):
        #     return None
        return meta

    def get_entry_payload(self, request_key: str):
        sql = f"""
        SELECT payload_bytes
        FROM {REQUEST_CACHE_META_TABLE}
        WHERE request_key = {request_key!r}
        """
        return CPG.custom_request_pg(sql, one=True, one_column=True)

    def touch_entry(self, request_key: str, *, refresh: bool = True, verified: bool = True) -> bool:
        now = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        sets = [f"last_used_at = {now!r}", f"updated_at = {now!r}"]
        if refresh:
            sets += [f"last_refresh_at = {now!r}", 'invalidated_at = NULL']
        if verified:
            sets += [f"last_verified_at = {now!r}"]
        return CPG.custom_request_pg(f"UPDATE {REQUEST_CACHE_META_TABLE} SET {', '.join(sets)} WHERE request_key = {request_key!r}")

    def current_dependency_fingerprint(self, request_key: str) -> str:
        if not request_key:
            return ''
        try:
            rows = CPG.custom_request_pg(
                f'SELECT table_key FROM {REQUEST_CACHE_TABLES_TABLE} WHERE request_key = {request_key!r}',
                rez_dict=True
            ) or []
            table_keys = [row['table_key'] for row in rows if row.get('table_key')]
            if not table_keys:
                return ''
            policy = self.compute_policy(table_keys=table_keys)
            return str(policy.get('dependency_fingerprint') or '')
        except Exception:
            return ''

    def is_entry_fresh(self, entry: Mapping[str, Any] | None, *, now: datetime.datetime | None = None) -> bool:
        if not entry:
            return False
        if entry.get('invalidated_at'):
            return False
        if entry.get('result_state') == 'empty':
            return False
        now = now or datetime.datetime.now()
        stale_after = self.utils.parse_dt(entry.get('stale_after_dt'))
        if stale_after is not None and stale_after <= now:
            return False
        stored_dependency_fingerprint = str(entry.get('dependency_fingerprint') or '')
        if stored_dependency_fingerprint:
            current_dependency_fingerprint = self.current_dependency_fingerprint(str(entry.get('request_key') or ''))
            if current_dependency_fingerprint and current_dependency_fingerprint != stored_dependency_fingerprint:
                return False
        logger.info(f'[is_entry_fresh]stored_dependency_fingerprint: {stored_dependency_fingerprint}')

        last_refresh = self.utils.parse_dt(entry.get('last_refresh_at')) or self.utils.parse_dt(entry.get('updated_at'))
        if last_refresh is None:
            return False
        lifetime_sec = int(entry.get('cache_lifetime_sec') or DEFAULT_CACHE_LIFETIME_SEC)
        return (now - last_refresh).total_seconds() < lifetime_sec

    def is_client_fresh(self, entry: Mapping[str, Any] | None, *, client_body_hash: str | None = None,
                        client_cached_at: str | None = None,
                        now: datetime.datetime | None = None
                        ) -> bool:
        if not self.is_entry_fresh(entry, now=now) or not entry:
            return False
        if not client_body_hash or str(client_body_hash) != str(entry.get('body_hash') or ''):
            return False
        client_dt = self.utils.parse_dt(client_cached_at)
        if client_dt is None:
            return False
        now = now or datetime.datetime.now()
        stale_after = self.utils.parse_dt(entry.get('stale_after_dt'))
        if stale_after is not None and client_dt >= stale_after:
            return False
        lifetime_sec = int(entry.get('cache_lifetime_sec') or DEFAULT_CACHE_LIFETIME_SEC)
        return (now - client_dt).total_seconds() < lifetime_sec

    def compute_policy(
            self,
            *,
            table_keys: Sequence[str],
            default_lifetime_sec: int = DEFAULT_CACHE_LIFETIME_SEC
    ) -> dict[str, Any]:
        lifetime_sec = int(default_lifetime_sec)
        stale_candidates: list[datetime.datetime] = []

        normalized_keys = []
        seen = set()
        for table_key in table_keys or ():
            key = str(table_key or '').strip()
            if not key:
                continue
            if key not in seen:
                seen.add(key)
                normalized_keys.append(key)

        if not normalized_keys:
            return {
                'cache_enabled': False,
                'cache_lifetime_sec': lifetime_sec,
                'stale_after_dt': None,
                'dependency_fingerprint': ''
            }

        placeholders = ','.join(['%s'] * len(normalized_keys))
        sql = f"""
            SELECT
                table_key,
                cache_enabled,
                validity_mark,
                updated_at,
                invalidated_at,
                stale_after_dt,
                cache_lifetime_min
            FROM admin_physical_tables
            WHERE table_key IN ({placeholders})
            ORDER BY table_key
        """

        dependency_rows = CPG.custom_request_pg(
            sql,
            params=normalized_keys,
            rez_dict=True,
        )

        if not isinstance(dependency_rows, list):
            print(f'[compute_policy] не соответствующий тип данных ответа {dependency_rows}')
            return {
                'cache_enabled': False,
                'cache_lifetime_sec': lifetime_sec,
                'stale_after_dt': None,
                'dependency_fingerprint': ''
            }

        found_keys = {str(row.get('table_key') or '') for row in dependency_rows}
        if len(found_keys) != len(normalized_keys):
            return {
                'cache_enabled': False,
                'cache_lifetime_sec': lifetime_sec,
                'stale_after_dt': None,
                'dependency_fingerprint': ''
            }

        cache_enabled = True

        for row in dependency_rows:
            raw_enabled = row.get('cache_enabled')
            is_enabled = bool(int(raw_enabled)) if raw_enabled not in (None, '', True, False) else bool(raw_enabled)
            if not is_enabled:
                cache_enabled = False

            cache_lifetime_min = int(row.get('cache_lifetime_min') or (default_lifetime_sec // 60))
            lifetime_sec = min(lifetime_sec, max(1, cache_lifetime_min) * 60)

            stale_dt = self.utils.parse_dt(row.get('stale_after_dt'))
            if stale_dt is not None:
                stale_candidates.append(stale_dt)

        stale_after_dt = min(stale_candidates).strftime('%Y-%m-%d %H:%M:%S') if stale_candidates else None

        dependency_fingerprint = self.utils.sha256_text(
            self.utils.json_dumps({
                'table_keys': normalized_keys,
                'rows': dependency_rows,
            })
        )

        return {
            'cache_enabled': cache_enabled,
            'cache_lifetime_sec': lifetime_sec,
            'stale_after_dt': stale_after_dt,
            'dependency_fingerprint': dependency_fingerprint
        }

    def compute_policy_(self, *, table_keys: Sequence[str],
                       default_lifetime_sec: int = DEFAULT_CACHE_LIFETIME_SEC) -> dict[str, Any]:
        lifetime_sec = int(default_lifetime_sec)
        stale_candidates: list[datetime.datetime] = []

        cache_enabled = True
        raw_table_keys = ','.join(str(table_key) for table_key in table_keys)
        dependency_rows: list[dict[str, Any]] = CPG.custom_request_pg(
            f"SELECT table_key, cache_enabled, validity_mark, updated_at, invalidated_at, stale_after_dt, cache_lifetime_min FROM admin_physical_tables WHERE table_key IN ({raw_table_keys})",
            rez_dict=True,
        )
        if not isinstance(dependency_rows, list):
            print(f'[compute_policy] не соответствующий тип данных ответа {dependency_rows}')
            return {
                'cache_enabled': False,
                'cache_lifetime_sec': lifetime_sec,
                'stale_after_dt': None,
                'dependency_fingerprint': ''
            }
        for row in dependency_rows:
            if not row.get('cache_enabled'):
                cache_enabled = False
            cache_lifetime_min = int(row.get('cache_lifetime_min') or (default_lifetime_sec // 60))
            lifetime_sec = min(lifetime_sec, max(1, cache_lifetime_min) * 60)
            stale_dt = self.utils.parse_dt(row.get('stale_after_dt'))
            if stale_dt is not None:
                stale_candidates.append(stale_dt)
        stale_after_dt = min(stale_candidates).strftime('%Y-%m-%d %H:%M:%S') if stale_candidates else None
        dependency_fingerprint = self.utils.sha256_text(self.utils.json_dumps({'table_keys': list(table_keys), 'rows': dependency_rows})) if table_keys else ''
        return {
            'cache_enabled': cache_enabled,
            'cache_lifetime_sec': lifetime_sec,
            'stale_after_dt': stale_after_dt,
            'dependency_fingerprint': dependency_fingerprint
        }

    def compute_policy_old(self, *, table_keys: Sequence[str],
                       default_lifetime_sec: int = DEFAULT_CACHE_LIFETIME_SEC) -> dict[str, Any]:
        logger.info(f'[compute_policy] {table_keys} \n default_lifetime_sec: {default_lifetime_sec}')
        lifetime_sec = int(default_lifetime_sec)
        stale_candidates: list[datetime.datetime] = []
        dependency_rows: list[dict[str, Any]] = []
        cache_enabled = True
        for table_key in table_keys:
            row = CPG.custom_request_pg(
                f"SELECT table_key, cache_enabled, validity_mark, updated_at, invalidated_at, stale_after_dt, cache_lifetime_min FROM admin_physical_tables WHERE table_key = {table_key!r}",
                rez_dict=True,
                one=True
            )
            if not isinstance(row, dict):
                print(f'[compute_policy] не соответствующий тип данных ответа {row}')
                continue

            if not row.get('cache_enabled'):
                cache_enabled = False
            dependency_rows.append(row)
            cache_lifetime_min = int(row.get('cache_lifetime_min') or (default_lifetime_sec // 60))
            lifetime_sec = min(lifetime_sec, max(1, cache_lifetime_min) * 60)
            stale_dt = self.utils.parse_dt(row.get('stale_after_dt'))
            if stale_dt is not None:
                stale_candidates.append(stale_dt)
        stale_after_dt = min(stale_candidates).strftime('%Y-%m-%d %H:%M:%S') if stale_candidates else None
        dependency_fingerprint = self.utils.sha256_text(self.utils.json_dumps({'table_keys': list(table_keys), 'rows': dependency_rows})) if table_keys else ''
        return {
            'cache_enabled': cache_enabled,
            'cache_lifetime_sec': lifetime_sec,
            'stale_after_dt': stale_after_dt,
            'dependency_fingerprint': dependency_fingerprint
        }

    def store_entry(self, *, request_key: str, db_path: str, sql_text: str, params: Any, options: Mapping[str, Any],
                    payload: Any, body_hash: str, table_keys: Sequence[str], dependency_fingerprint: str = '',
                    cache_lifetime_sec: int = DEFAULT_CACHE_LIFETIME_SEC, stale_after_dt: str | None = None,
                    notes: str = '') -> dict[str, Any]:
        now = F.now()
        db_path = self.utils.normalize_path(db_path)
        db_key = pathlib.Path(db_path).stem or 'unknown_db'
        suspicious_empty = payload in (None, [], {}, (), True, False)

        if suspicious_empty:
            self.delete_entry(request_key)
            return {
                'request_key': request_key,
                'db_key': db_key,
                'db_path': db_path,
                'body_hash': body_hash,
                'cache_lifetime_sec': int(cache_lifetime_sec or DEFAULT_CACHE_LIFETIME_SEC),
                'stale_after_dt': stale_after_dt,
                'dependency_fingerprint': dependency_fingerprint or '',
                'last_refresh_at': now,
                'result_state': 'empty',
            }
        # payload_bytes = self.serialize_payload(payload)
        payload_bytes, payload_is_compressed = self.serialize_payload(payload)
        logger.info(f'[store_entry] {request_key} compressed {payload_is_compressed}')

        meta_record = {
            'request_key': request_key,
            'db_key': db_key,
            'db_path': db_path,
            'sql_text': str(sql_text or ''),
            'params_json': self.utils.json_dumps(self.utils.normalize_params(params)),
            'options_json': self.utils.json_dumps(dict(options or {})),
            'body_hash': body_hash,
            'payload_bytes': payload_bytes,
            'payload_is_compressed': payload_is_compressed,
            # 'data_version': 1,
            'result_state': 'filled',
            'dependency_fingerprint': dependency_fingerprint or '',
            'cache_lifetime_sec': int(cache_lifetime_sec or DEFAULT_CACHE_LIFETIME_SEC),
            'stale_after_dt': stale_after_dt,
            'invalidated_at': None,
            'last_used_at': now,
            'last_refresh_at': now,
            'last_verified_at': now,
            'notes': notes or '',
            'updated_at': now,
        }
        cols = list(meta_record.keys())
        placeholders = []
        for col in cols:
            if col == 'payload_bytes':
                placeholders.append('%b')
            else:
                placeholders.append('%s')
        placeholders = ','.join(placeholders)
        # placeholders = ','.join('%s' for _ in cols)
        update_sql = ', '.join(f'{col}=excluded.{col}' for col in cols if col != 'request_key')

        sql = f"INSERT INTO {REQUEST_CACHE_META_TABLE} ({', '.join(cols)}) VALUES ({placeholders}) ON CONFLICT(request_key) DO UPDATE SET {update_sql};"
        start_insert_main_data = time.time()
        insert_cache_meta = CPG.custom_request_pg(sql, params=tuple(meta_record[col] for col in cols))
        logger.info(f'[store_entry] {time.time() - start_insert_main_data} insert_cache_meta result: {insert_cache_meta}')
        # delete_cache_table = CSQ.custom_request_c(repo.db_files, f'DELETE FROM {REQUEST_CACHE_TABLES_TABLE} WHERE request_key = {request_key!r}')
        start_drop_main_data = time.time()

        insert_cache_tables = CPG.custom_request_pg(f'DELETE FROM {REQUEST_CACHE_TABLES_TABLE} WHERE request_key = {request_key!r}')
        logger.info(f'[store_entry] {time.time() - start_drop_main_data} drop_cache_tables result: {insert_cache_tables}')
        insert_fields_results = []
        if table_keys:
            rows = [[request_key, table_key] for table_key in dict.fromkeys(str(item) for item in table_keys if item not in (None, ''))]
            # CSQ.custom_request_c(repo.db_files, f'INSERT INTO {REQUEST_CACHE_TABLES_TABLE}(request_key, table_key) VALUES ({mask})', list_of_lists_c=rows)
            a = CPG.custom_request_pg(f'INSERT INTO {REQUEST_CACHE_TABLES_TABLE}(request_key, table_key) VALUES (%s, %s)', params=rows)
            insert_fields_results.append(a)
        logger.info(f'[store_entry] insert_fields_results results: {insert_fields_results}')
        # entry = meta_record
        # entry['payload'] = payload
        # return entry
        return {
            'request_key': request_key,
            'db_key': db_key,
            'db_path': db_path,
            'body_hash': body_hash,
            'result_state': 'filled',
            'dependency_fingerprint': dependency_fingerprint or '',
            'cache_lifetime_sec': int(cache_lifetime_sec or DEFAULT_CACHE_LIFETIME_SEC),
            'stale_after_dt': stale_after_dt,
            'last_refresh_at': now,
            'last_used_at': now,
            'last_verified_at': now,
            'notes': notes or '',
            'updated_at': now,
        }

    def delete_entry(self, request_key: str) -> None:
        # state_delete_payload = self._remove_payload(request_key) # todo

        state_delete_payload_1 = CPG.custom_request_pg( f'DELETE FROM {REQUEST_CACHE_TABLES_TABLE} WHERE request_key = {request_key!r}')
        state_delete_payload_2 = CPG.custom_request_pg(f'DELETE FROM {REQUEST_CACHE_META_TABLE} WHERE request_key = {request_key!r}')
        print(f'[delete_entry]  {state_delete_payload_1} {state_delete_payload_2}')

    def invalidate_by_table_keys(self, table_keys: Sequence[str], *, notes: str = '') -> int:
        keys = [str(item) for item in table_keys if item not in (None, '')]
        if not keys:
            return 0
        joined = ','.join(repr(k) for k in keys)
        rows = CPG.custom_request_pg( f'SELECT DISTINCT request_key FROM {REQUEST_CACHE_TABLES_TABLE} WHERE table_key IN ({joined})', rez_dict=True) or []
        logger.info(f'[invalidate_by_table_keys] result rows {rows}')
        request_keys = [row['request_key'] for row in rows if row.get('request_key')]
        if not request_keys:
            return 0
        now = F.now()
        joined_req = ','.join(repr(k) for k in request_keys)
        set_notes = '' if not notes else f", notes = CASE WHEN notes = '' THEN {notes!r} ELSE notes END"
        update_invalidated = CPG.custom_request_pg(f"UPDATE {REQUEST_CACHE_META_TABLE} SET invalidated_at = {now!r}, updated_at = {now!r}{set_notes} WHERE request_key IN ({joined_req})")
        logger.info(f'[invalidate_by_table_keys] update inv rows {update_invalidated}')
        return len(request_keys)
    ###
    def invalidate_by_table_names(self, table_names, notes: str = '', return_details: bool = False):
        names = []
        seen = set()

        for name in table_names or ():
            text = str(name or '').strip()
            if not text:
                continue
            if '.' in text:
                text = text.split('.')[-1].strip()
            if text and text not in seen:
                seen.add(text)
                names.append(text)

        if not names:
            return {'ok': False, 'table_names': [], 'table_keys': []} if return_details else False

        def esc_sql_text(val: str) -> str:
            return str(val).replace("'", "''")

        def esc_like(val: str) -> str:
            val = str(val).replace('\\', '\\\\')
            val = val.replace('%', '\\%')
            val = val.replace('_', '\\_')
            return val

        where_sql = ' OR '.join(
            [f"table_key LIKE '{esc_sql_text(f'%.{esc_like(name)}')}' ESCAPE '\\'" for name in names]
        )

        rows = CPG.custom_request_pg(
            f"""
            SELECT DISTINCT table_key
            FROM {REQUEST_CACHE_TABLES_TABLE}
            WHERE {where_sql}
            """,
            rez_dict=True,
        ) or []
        print('[invalidate_by_table_names] result rows: ', rows)

        table_keys = []
        seen_keys = set()
        for row in rows:
            key = row.get('table_key')
            if key and key not in seen_keys:
                seen_keys.add(key)
                table_keys.append(key)

        ok = False
        if table_keys:
            ok = bool(self.invalidate_by_table_keys(table_keys, notes=notes))

        if return_details:
            return {
                'ok': ok,
                'table_names': names,
                'table_keys': table_keys,
                'notes': notes,
            }
        return ok


__cache_builder = CacheBuilder()
__utils = __cache_builder.utils
__cache = FileRequestCache()


build_body_hash = __cache_builder.build_body_hash
is_cacheable_sql = __cache_builder.is_cacheable_sql
normalize_attach_dbs = __utils.normalize_attach_dbs
is_db_files_path = __cache_builder.is_db_files_path
build_request_key = __cache_builder.build_request_key
extract_query_table_records = __cache_builder.extract_query_table_records
cacheable_request = __cache_builder.cacheable_request
clear_local_cache = __cache_builder.clear_local_cache
get_valid_local_entry = __cache_builder.get_valid_local_entry
write_cache_entry = __cache_builder.write_cache_entry

get_entry_meta = __cache.get_entry_meta
touch_entry = __cache.touch_entry


