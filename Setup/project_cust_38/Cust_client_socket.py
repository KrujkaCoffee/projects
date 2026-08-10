import socket
import pickle
import typing
import zlib
import datetime
import errno
import json
import pathlib
import uuid
from collections import Counter, UserString, deque

import time
import requests
import enum
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from project_cust_38 import srv_sql_cache as SQLCACHE

ip = 'mesinfo.powerz.ru'

CONNECTION_ATTEMPTS = 3

class SrvHeaders(enum.Enum):
    """Единые константы заголовков http ответа для клиента/сервера"""
    EXCEPTION_MESSAGE = 'X-SRV-EXCEPTION-MESSAGE'       # Сообщение из исключения во время ошибки на стороне сервера
    SYNTAX_ERROR = 'X-SRV-SYNTAX-ERROR'                 # Флаг синтаксической ошибки
    REQUEST_KEY = 'X-SQL-REQUEST-KEY'
    CLIENT_BODY_HASH = 'X-SQL-CLIENT-BODY-HASH'
    CLIENT_CACHED_AT = 'X-SQL-CLIENT-CACHED-AT'
    CACHE_STATUS = 'X-SQL-CACHE-STATUS'
    BODY_HASH = 'X-SQL-BODY-HASH'
    LAST_REFRESH_AT = 'X-SQL-LAST-REFRESH-AT'
    CACHE_LIFETIME_SEC = 'X-SQL-CACHE-LIFETIME-SEC'
    STALE_AFTER_DT = 'X-SQL-STALE-AFTER-DT'
    DEPENDENCY_FINGERPRINT = 'X-SQL-DEPENDENCY-FP'
    DEPENDENCY_FP = 'X-SQL-DEPENDENCY-FP'
    DATA_SENT = 'X-SQL-DATA-SENT' # 15.04.2026
    # Заголовки запроса юзера
    CAN_ACCEPT_COMPRESS = 'X-CAN-ACCEPT-COMPRESS'
    # Заголовки ответа сервера
    CONTENT_IS_COMPRESS_ZLIB = 'X-CONTENT-IS-COMPRESSION-ZLIB'



class HttpSessionTelemetry:
    EVENTS = deque(maxlen=14)
    COUNTER = Counter()
    SEQUENCE = 0
    STARTED_AT = datetime.datetime.now(datetime.timezone.utc).isoformat()

    HTTP_FAST_FAIL_MS = 500.0

    @classmethod
    def add(cls, event: dict) -> dict:
        item = dict(event)
        item.setdefault('created_at', datetime.datetime.now(datetime.timezone.utc).isoformat())
        cls.SEQUENCE += 1
        item['sequence'] = cls.SEQUENCE
        cls.EVENTS.append(item)
        cls.COUNTER[item.get('case', 'unknown')] += 1
        for retry_item in item.get('retry_history') or ():
            if retry_item.get('status') is not None:
                cls.COUNTER[f"retry_status:{retry_item['status']}"] += 1
            elif retry_item.get('error_type'):
                cls.COUNTER[f"retry_error:{retry_item['error_type']}"] += 1
        return item

    @classmethod
    def snapshot(cls, *, failures_only: bool = False) -> list[dict]:
        rows = [dict(item) for item in cls.EVENTS]
        if failures_only:
            rows = [item for item in rows if item.get('case') not in ('ok', 'ok_after_retry')]
        return rows

    @classmethod
    def summary(cls) -> dict:
        return {
            'started_at': cls.STARTED_AT,
            'events_in_memory': len(cls.EVENTS),
            'max_events': cls.EVENTS.maxlen,
            'counters': dict(cls.COUNTER),
        }

    def clear(self) -> None:
        self.EVENTS.clear()
        self.COUNTER.clear()

    @classmethod
    def dump_jsonl(cls, path: str | pathlib.Path, *, failures_only: bool = False) -> pathlib.Path:
        target = pathlib.Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        rows = cls.snapshot(failures_only=failures_only)
        with target.open('w', encoding='utf-8') as stream:
            for item in rows:
                stream.write(json.dumps(item, ensure_ascii=False, default=str) + '\n')
        return target

    @staticmethod
    def compact_sql(sql: typing.Any, limit: int = 300) -> str:
        text = ' '.join(str(sql or '').split())
        return text[:limit]

    @staticmethod
    def retry_history(response: requests.Response) -> list[dict]:
        result = []
        retry_obj = getattr(getattr(response, 'raw', None), 'retries', None)
        for item in getattr(retry_obj, 'history', ()) or ():
            error = getattr(item, 'error', None)
            result.append({
                'method': getattr(item, 'method', None),
                'url': getattr(item, 'url', None),
                'status': getattr(item, 'status', None),
                'error_type': type(error).__name__ if error is not None else None,
                'error': str(error)[:500] if error is not None else None,
                'redirect_location': getattr(item, 'redirect_location', None),
            })
        return result

    @staticmethod
    def selected_response_headers(headers: typing.Mapping) -> dict[str, str]:
        names = {
            'SERVER', 'VIA', 'X-CACHE', 'X-CACHE-STATUS', 'X-SQUID-ERROR',
            'CF-RAY', 'X-ENVOY-UPSTREAM-SERVICE-TIME', 'CONTENT-TYPE',
            'CONTENT-LENGTH', 'RETRY-AFTER',
            SrvHeaders.REQUEST_ID.value,
            SrvHeaders.ORIGIN.value,
            SrvHeaders.EXCEPTION_MESSAGE.value,
            SrvHeaders.SYNTAX_ERROR.value,
            SrvHeaders.CACHE_STATUS.value,
            SrvHeaders.DATA_SENT.value,
        }
        normalized = {str(key).upper(): str(value) for key, value in headers.items()}
        return {key: normalized[key] for key in names if key in normalized}

    @staticmethod
    def body_preview(response: requests.Response, limit: int = 512) -> str:
        try:
            raw = bytes(response.content[:limit])
            content_type = str(response.headers.get('Content-Type') or '').lower()
            if 'text' in content_type or 'json' in content_type or raw.startswith((b'<', b'{', b'[')):
                return raw.decode(response.encoding or 'utf-8', errors='replace')
            return raw.hex()
        except Exception:
            return ''

    def base_http_event(self, *, trace_id: str, url: str, bd, port, name_module: str,
                         client_name: str, custom_request_c, started: float) -> dict:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        sql_text = str(custom_request_c or '')
        return {
            'trace_id': trace_id,
            'url': url,
            'host': ip,
            'port': port,
            'db': str(bd),
            'module': name_module,
            'client': client_name,
            'sql_preview': self.compact_sql(sql_text),
            'duration_ms': duration_ms,
            'fast_fail': duration_ms <= self.HTTP_FAST_FAIL_MS,
        }

    def record_http_response(self, *, response: requests.Response, trace_id: str, url: str,
                              bd, port, name_module: str, client_name: str,
                              custom_request_c, started: float,
                              payload_source: str = 'network') -> dict:
        event = self.base_http_event(
            trace_id=trace_id, url=url, bd=bd, port=port,
            name_module=name_module, client_name=client_name,
            custom_request_c=custom_request_c, started=started,
        )
        retry_history = self.retry_history(response)
        if response.ok:
            case = 'ok_after_retry' if retry_history else 'ok'
        else:
            case = 'http_error_origin_unknown'
        event.update({
            'case': case,
            'subtype': f'http_{response.status_code}',
            'response_received': True,
            'status_code': response.status_code,
            'reason': str(response.reason or ''),
            'headers_elapsed_ms': round(response.elapsed.total_seconds() * 1000, 3),
            'response_size': len(response.content or b''),
            'response_headers': self.selected_response_headers(response.headers),
            'retry_history': retry_history,
            'payload_source': payload_source,
            'body_preview': self.body_preview(response) if not response.ok else '',
        })
        return self.add(event)

    @staticmethod
    def iter_exception_chain(exc: BaseException):
        stack = [exc]
        seen = set()
        while stack:
            current = stack.pop()
            if not isinstance(current, BaseException) or id(current) in seen:
                continue
            seen.add(id(current))
            yield current
            for attr_name in ('__cause__', '__context__', 'reason', 'original_error'):
                nested = getattr(current, attr_name, None)
                if isinstance(nested, BaseException):
                    stack.append(nested)
            for arg in getattr(current, 'args', ()):
                if isinstance(arg, BaseException):
                    stack.append(arg)
    @staticmethod
    def exception_errno(chain: list[BaseException]) -> int | None:
        for item in chain:
            value = getattr(item, 'errno', None)
            if isinstance(value, int):
                return value
        return None

    def classify_request_exception(self, exc: BaseException) -> tuple[str, str]:
        chain = list(self.iter_exception_chain(exc))
        names = {type(item).__name__ for item in chain}
        err_no = self.exception_errno(chain)

        if isinstance(exc, requests.exceptions.ProxyError) or 'ProxyError' in names:
            return 'intermediary_reject', 'proxy_error'
        if 'NameResolutionError' in names or any(isinstance(item, socket.gaierror) for item in chain):
            return 'transport_reject', 'dns_error'
        if err_no in {getattr(errno, 'ECONNREFUSED', 111), 10061} or any(
                isinstance(item, ConnectionRefusedError) for item in chain):
            return 'transport_reject', 'connection_refused'
        if err_no in {getattr(errno, 'ECONNRESET', 104), getattr(errno, 'ECONNABORTED', 103), 10053, 10054} or any(
                isinstance(item, ConnectionResetError) for item in chain):
            return 'transport_reject', 'connection_reset'
        if isinstance(exc, requests.exceptions.ReadTimeout) or 'ReadTimeoutError' in names or 'ReadTimeout' in names:
            return 'timeout_no_response', 'read_timeout'
        if isinstance(exc, requests.exceptions.ConnectTimeout) or ('ConnectTimeoutError' in names and 'NewConnectionError' not in names):
            return 'timeout_no_response', 'connect_timeout'
        if err_no in {getattr(errno, 'ETIMEDOUT', 110), 10060}:
            return 'timeout_no_response', 'socket_timeout'
        if isinstance(exc, requests.exceptions.Timeout) or 'TimeoutError' in names:
            return 'timeout_no_response', 'timeout'
        if isinstance(exc, requests.exceptions.RetryError) or 'ResponseError' in names:
            return 'retry_exhausted', 'status_retry_exhausted'
        if isinstance(exc, requests.exceptions.SSLError) or 'SSLError' in names:
            return 'transport_error', 'tls_error'
        if isinstance(exc, requests.exceptions.ConnectionError):
            return 'transport_error', 'connection_error'
        return 'transport_error', type(exc).__name__

    def record_http_exception(self, *, exc: BaseException, trace_id: str, url: str,
                               bd, port, name_module: str, client_name: str,
                               custom_request_c, started: float) -> dict:
        event = self.base_http_event(
            trace_id=trace_id, url=url, bd=bd, port=port,
            name_module=name_module, client_name=client_name,
            custom_request_c=custom_request_c, started=started,
        )
        chain = list(self.iter_exception_chain(exc))
        case, subtype = self.classify_request_exception(exc)
        event.update({
            'case': case,
            'subtype': subtype,
            'response_received': False,
            'responder': 'none',
            'status_code': None,
            'exception_type': type(exc).__name__,
            'exception': str(exc)[:2000],
            'exception_chain': [
                {'type': type(item).__name__, 'message': str(item)[:1000], 'errno': getattr(item, 'errno', None)}
                for item in chain
            ],
            'errno': self.exception_errno(chain),
            'retry_history': [],
        })
        return self.add(event)


class SessionManager:
    session = None
    HTTP_TIMEOUT = (3.0, 120.0)

    def __enter__(self):
        if SessionManager.session is None:
            SessionManager.session = requests.Session()
            retries = Retry(
                total=CONNECTION_ATTEMPTS,
                backoff_factor=0.3,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(['POST']),
                raise_on_status=False,
            )
            SessionManager.session.mount(
                'http://',
                HTTPAdapter(
                    max_retries=retries,
                    pool_connections=50,
                    pool_maxsize=50,
                    pool_block=True
                )
            )
            SessionManager.session.headers.update({"Connection": "keep-alive"})
        return SessionManager.session

    def __exit__(self, exc_type, exc_val, exc_tb): ...

class _ServerItem(UserString):
    alias: str                                  # "Naryad.db"
    absolute_path: str                          # "C://DB_srv//Naryad.db"
    port: typing.Union[int, str, None] = None   # 20002

    def __init__(self, alias: str, absolute_path: str = '', port: typing.Union[int, str, None] = None):
        super().__init__(f'SRV:{alias}')
        self.alias = alias
        self.absolute_path = absolute_path
        self.port = port

class _ClassDict(type):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls._declared_attrs = {k: dct.get(k) for k in dct.get("__annotations__", {})}
        cls.__by_alias = {attr.alias: attr for name, attr in cls._declared_attrs.items() if isinstance(attr, _ServerItem)}
        cls.__by_name = {attr: attr for attr in cls._declared_attrs.values()}

    def __getitem__(cls, item):
        return cls.__by_alias.get(item) or cls.__by_name.get(item)


class Servers(metaclass=_ClassDict):
    db_naryad: _ServerItem = _ServerItem(alias='Naryad.db', absolute_path='C://DB_srv//Naryad.db', port=20002)
    db_dse: _ServerItem = _ServerItem(alias='BD_dse.db', absolute_path='C://DB_srv//BD_dse.db', port=20003)
    db_resxml: _ServerItem = _ServerItem(alias='BD_resxml.db', absolute_path='C://DB_srv//BD_resxml.db', port=20005)
    db_files: _ServerItem = _ServerItem(alias='BD_files.db', absolute_path='C://DB_srv//BD_files.db', port=20006)
    db_kplan: _ServerItem = _ServerItem(alias='DB_kplan.db', absolute_path='C://DB_srv//DB_kplan.db', port=20007)
    db_users: _ServerItem = _ServerItem(alias='BD_users.db', absolute_path='C://DB_srv//BD_users.db', port=20009)
    db_nomen: _ServerItem = _ServerItem(alias='DB_nomenklatura_erp.db', absolute_path='C://DB_srv//DB_nomenklatura_erp.db', port=20010)
    db_flet: _ServerItem = _ServerItem(alias='db_flet.db', absolute_path='C://DB_srv//db_flet.db', port=20014)

    xl_formulas: _ServerItem = _ServerItem(alias='DB_xl_formulas.db', port=20012)
    mes_api: _ServerItem = _ServerItem(alias='MES_api', port=20011)


def db_path(name:str):
    name_db = name.split('SRV:')[-1].split('\\')[0] # 16.04.2026
    server = Servers[name_db]
    if server is None:
        return None, None
    return server.absolute_path, server.port


def client_sql_query(bd: _ServerItem, custom_request_c, hat_c = True, list_of_lists_c = [[]], rez_dict=False, one = False, name_module='', client_name ='', port='', one_column=False, attach_dbs=()):
    session_telemetry = HttpSessionTelemetry()

    msgFromClient = {"client": client_name, "module": name_module, "bd": bd, "custom_request_c": custom_request_c,
                     "hat_c": hat_c, "list_of_lists_c": list_of_lists_c,
                     "rez_dict": rez_dict, "one": one, "one_column":one_column, "attach_dbs": attach_dbs}
    message_str = None
    cache_enabled = SQLCACHE.cacheable_request(bd, custom_request_c, attach_dbs=attach_dbs, function_db_path=db_path)
    request_key = ''
    local_entry = None
    if cache_enabled:
        request_key = SQLCACHE.build_request_key(
            db_path=bd,
            sql_text=custom_request_c,
            hat_c=hat_c,
            params=list_of_lists_c,
            rez_dict=rez_dict,
            one=one,
            one_column=one_column,
            attach_dbs=attach_dbs,
        )
        local_entry = SQLCACHE.get_valid_local_entry(request_key)
        if local_entry is None:
            SQLCACHE.clear_local_cache(request_key)
    url = f'http://{ip}:{port}'
    trace_id = uuid.uuid4().hex
    started = time.perf_counter()
    try:
        headers = {
            SrvHeaders.CAN_ACCEPT_COMPRESS.value: '1' # 15.04.2026
        }
        if cache_enabled and request_key and local_entry is not None:
            headers = {
                SrvHeaders.REQUEST_KEY.value: request_key,
                SrvHeaders.CLIENT_BODY_HASH.value: str(local_entry.get('body_hash') or ''),
                SrvHeaders.CLIENT_CACHED_AT.value: str(local_entry.get('cached_at') or ''),
                SrvHeaders.CAN_ACCEPT_COMPRESS.value: '1'
            }
        try:
            with SessionManager() as session:
                response = session.post(
                    url,
                    data=pickle.dumps(msgFromClient),
                    headers=headers,
                    timeout=SessionManager.HTTP_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            session_telemetry.record_http_exception(
                exc=e, trace_id=trace_id, url=url, bd=bd, port=port,
                name_module=name_module, client_name=client_name,
                custom_request_c=custom_request_c, started=started,
            )
            print(f'HTTP запрос не получил ответа: {type(e).__name__}: {e}')
            return None
        except Exception as e:
            # Ошибка до/вокруг requests (например pickle.dumps), а не HTTP-ответ.
            session_telemetry.record_http_exception(
                exc=e, trace_id=trace_id, url=url, bd=bd, port=port,
                name_module=name_module, client_name=client_name,
                custom_request_c=custom_request_c, started=started,
            )
            print(f'Ошибка подготовки/выполнения HTTP запроса: {type(e).__name__}: {e}')
            return None
        headers = {str(k).upper(): v for k, v in response.headers.items()}
        srv_exception_message = headers.get(SrvHeaders.EXCEPTION_MESSAGE.value)
        srv_syntax_error_flag = headers.get(SrvHeaders.SYNTAX_ERROR.value)
        if srv_syntax_error_flag: # 23.06.2026
            from urllib.parse import unquote_plus
            print('\n[СЕРВЕРНАЯ ОШИБКА]', unquote_plus(srv_exception_message), '\n')
            session_telemetry.record_http_exception(
                exc=Exception(f'Синтаксическая ошибка sql: {unquote_plus(srv_exception_message)}'), trace_id=trace_id, url=url, bd=bd, port=port,
                name_module=name_module, client_name=client_name,
                custom_request_c=custom_request_c, started=started,
            )
            return None
        cache_status = headers.get(SrvHeaders.CACHE_STATUS.value) or ''
        data_sent = headers.get(SrvHeaders.DATA_SENT.value) or '1'
        is_compressed = headers.get(SrvHeaders.CONTENT_IS_COMPRESS_ZLIB.value) == '1' # 15.04.2026

        if cache_enabled and cache_status == 'CLIENT_FRESH' and local_entry is not None:
            return local_entry['payload']
        if response.content:
            content = response.content
            if is_compressed: # 15.04.2026
                content = zlib.decompress(content)
            message_str = pickle.loads(content)
            if cache_enabled and request_key and data_sent == '1' and cache_status != 'BYPASS' and message_str not in (True, False):
                SQLCACHE.write_cache_entry(request_key, message_str, headers, SrvHeaders=SrvHeaders)
        elif cache_enabled and data_sent == '0' and local_entry is not None:
            return local_entry['payload']
    except Exception as e:
        print(f'От сервера получен None на запрос {msgFromClient} Ошибка: {e}')
        session_telemetry.record_http_exception(
            exc=e, trace_id=trace_id, url=url, bd=bd, port=port,
            name_module=name_module, client_name=client_name,
            custom_request_c=custom_request_c, started=started,
        )
        return
    return message_str
