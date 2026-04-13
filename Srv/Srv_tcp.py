import json
import pickle
import logging
import pathlib
import re
import sqlite3
import os
import traceback
import time
from urllib.parse import quote

os.environ['MES_IS_SERVER'] = '1'

from werkzeug import Request, Response
from werkzeug.routing import Map, Rule
from waitress import serve

import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_client_socket as CCS
from project_cust_38 import context_admin as CTXADM
from project_cust_38 import srv_sql_cache as SQLCACHE
import Cust_postgresql_cache as CPG # noqa

import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(format='%(asctime)s -  %(message)s', level=logging.INFO, encoding='utf8')
logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)
msg_format = '\n{lines}\nКлиент: {user}\nВ модуле: {module}\nСделал запрос: {query}\n{lines}\n'
DB_PATH = pathlib.Path(r'C://DB_srv//').absolute()

url_map = Map()
route_handlers = {}
_NO_PAYLOAD = object()


def route(rule):
    def decorator(func):
        endpoint = func.__name__
        url_map.add(Rule(rule, endpoint=endpoint))
        route_handlers[endpoint] = func

        def wrapper_route(*args, **kwargs):
            self = args[0] if args else None
            try:
                start = time.time()
                # conn, cur = CPG.connect_pg(CPG.PostgresConfig())
                logger.info(f'[PG] start connection { time.time() - start:.2f}s')
                # CPG.Connect = conn
                # CPG.Cursor = cur
                logger.info('start request')
                result = func(*args, **kwargs)
                logger.info(f'end: {time.time() - start}')
                if isinstance(result, Response):
                    if self is not None:
                        for key, value in getattr(self, 'headers', {}).items():
                            result.headers[key] = value
                    return result
                payload = b'' if result is _NO_PAYLOAD else pickle.dumps(result)
                response = Response(payload, status=200)
                if self is not None:
                    for key, value in getattr(self, 'headers', {}).items():
                        response.headers[key] = value
                return response
            except Exception as e:
                logger.error(f'Ошибка: {e}')
                return Response('Error', status=502)
            finally:
                start_cache_bypass = time.time()
                # CPG.close_pg(CPG.Connect, CPG.Cursor)
                # CPG.Cursor = None
                # CPG.Connect = None
                logger.info(f'[PG] end connection { time.time() - start_cache_bypass:.2f}s')


        return wrapper_route

    return decorator


class HTTPSrv:
    def __init__(self):
        self.headers = {}
        self.admin_repo = CTXADM.ContextAdminRepo()
        self.request_cache = SQLCACHE.FileRequestCache()

    def dispatch_query(self, msg: dict):
        message = msg_format.format(
            user=msg.get('client'),
            module=msg.get('module'),
            query=msg.get('custom_request_c'),
            lines='=' * 80
        )
        logger.info(message)

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        adapter = url_map.bind_to_environ(environ)
        self.headers = {}
        try:
            endpoint, values = adapter.match()
            func = getattr(self, endpoint)
            if not func:
                response = Response(status=404)
            else:
                response = func(request, **values)
        except Exception:
            response = Response(status=501)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def request_headers(self, request: Request | None) -> dict[str, str]:
        if request is None:
            return {}
        try:
            return {str(k).upper(): str(v) for k, v in request.headers.items()}
        except Exception:
            return {}

    def _set_cache_headers(self, *, request_key: str, entry: dict | None = None, status: str = '', data_sent: str = '1'):
        if not status:
            return
        self.headers[CCS.SrvHeaders.CACHE_STATUS.value] = status
        self.headers[CCS.SrvHeaders.REQUEST_KEY.value] = request_key
        self.headers[CCS.SrvHeaders.DATA_SENT.value] = data_sent
        if entry:
            self.headers[CCS.SrvHeaders.BODY_HASH.value] = str(entry.get('body_hash') or '')
            self.headers[CCS.SrvHeaders.LAST_REFRESH_AT.value] = str(entry.get('last_refresh_at') or '')
            self.headers[CCS.SrvHeaders.CACHE_LIFETIME_SEC.value] = str(entry.get('cache_lifetime_sec') or '')
            self.headers[CCS.SrvHeaders.STALE_AFTER_DT.value] = str(entry.get('stale_after_dt') or '')
            self.headers[CCS.SrvHeaders.DEPENDENCY_FINGERPRINT.value] = str(entry.get('dependency_fingerprint') or '')

    def attached_alias_paths(self, lst_dbs: tuple | str):
        lst_dbs = (lst_dbs,) if isinstance(lst_dbs, str) else lst_dbs
        result = {}
        for path in lst_dbs or ():
            match = re.search(r'(?<=:)(\w+\.db)', str(path))
            if not match:
                continue
            db_name = match.group(0).strip()
            alias = db_name.split('.')[0]
            result[alias] = str(DB_PATH / db_name)
        return result

    def is_cache_bypass(self, *, bd: str, custom_request_c: str, attach_dbs=()):
        if not SQLCACHE.is_cacheable_sql(custom_request_c):
            return True
        if SQLCACHE.is_db_files_path(bd):
            return True
        for attach_db in SQLCACHE.normalize_attach_dbs(attach_dbs):
            attach_path = ''
            if str(attach_db).startswith('SRV:'):
                try:
                    attach_path, _ = CCS.db_path(str(attach_db))
                except Exception:
                    attach_path = str(attach_db)
            else:
                attach_path = str(attach_db)
            if SQLCACHE.is_db_files_path(attach_path):
                return True
        return False

    def resolve_request_key(self, *, bd: str, custom_request_c: str, list_of_lists_c, rez_dict: bool, one: bool,
                            one_column: bool, hat_c: bool, attach_dbs, request_headers: dict[str, str]) -> str:
        computed = SQLCACHE.build_request_key(
            db_path=bd,
            sql_text=custom_request_c,
            params=list_of_lists_c,
            rez_dict=rez_dict,
            one=one,
            one_column=one_column,
            hat_c=hat_c,
            attach_dbs=attach_dbs,
        )
        client_key = request_headers.get(CCS.SrvHeaders.REQUEST_KEY.value, '')
        if client_key and client_key == computed:
            return client_key
        return computed

    def get_entry_payload_bytes(self, request_key: str):
        sql = f"""
        SELECT payload_bytes
        FROM {REQUEST_CACHE_META_TABLE}
        WHERE request_key = {request_key!r}
        """
        return CPG.custom_request_pg(sql, one=True, one_column=True)

    def try_serve_from_cache(self, *, request_key: str, request_headers: dict[str, str]):
        if not request_key or self.request_cache is None:
            return None, False
        start_entry_calc = time.time()
        entry = self.request_cache.get_entry_meta(request_key)
        logger.info(f'[try_serve_from_cache] entry calc 1 {time.time()-start_entry_calc:.2f}s')

        start_check_fresh = time.time()
        if not entry or not self.request_cache.is_entry_fresh(entry):
            logger.info('[try_serve_from_cache] Данные кэша устаревшие')
            return entry, False
        logger.info(f'[try_serve_from_cache] check_entry_fresh {time.time()-start_check_fresh:.2f}s')
        client_body_hash = request_headers.get(CCS.SrvHeaders.CLIENT_BODY_HASH.value, '')
        client_cached_at = request_headers.get(CCS.SrvHeaders.CLIENT_CACHED_AT.value, '')
        start_check_client_fresh = time.time()
        if self.request_cache.is_client_fresh(entry, client_body_hash=client_body_hash, client_cached_at=client_cached_at):
            start_touch = time.time()
            logger.info(f'[try_serve_from_cache] check_client_fresh {time.time() - start_check_client_fresh:.2f}s')

            self.request_cache.touch_entry(request_key, refresh=False, verified=True)
            start_calc_entry = time.time()
            entry = self.request_cache.get_entry_meta(request_key) or entry
            self._set_cache_headers(request_key=request_key, entry=entry, status=SQLCACHE.CACHE_STATUS.CLIENT_FRESH, data_sent='0')
            logger.info('[try_serve_from_cache] Данные клиента свежие')
            logger.info(f'[try_serve_from_cache] touch {time.time() - start_touch:.2f}s')
            logger.info(f'[try_serve_from_cache] entry calc 2 {time.time() - start_calc_entry:.2f}s')
            return _NO_PAYLOAD, True
        raw = self.request_cache.get_entry_payload(request_key)
        payload = self.request_cache.deserialize_payload(raw)
        if payload is None:
            logger.info('[try_serve_from_cache] Данные в кэше не корректные')

            return entry, False

        status = SQLCACHE.CACHE_STATUS.SERVER_HIT
        if client_body_hash and client_body_hash == str(entry.get('body_hash') or '') and client_cached_at:
            status = SQLCACHE.CACHE_STATUS.CLIENT_STALE
        self.request_cache.touch_entry(request_key, refresh=False, verified=True)
        entry = self.request_cache.get_entry_meta(request_key) or entry
        self._set_cache_headers(request_key=request_key, entry=entry, status=status, data_sent='1')
        logger.info('[try_serve_from_cache] Кэш данные сервера')

        return payload, True

    def execute_sql(self, *, bd, custom_request_c, hat_c, list_of_lists_c, rez_dict, one, one_column, attach_dbs):
        conn, cur = CSQ.connect_bd(bd)
        try:
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=FULL;")
            cur.execute("PRAGMA busy_timeout = 30000;")
            cur.execute("PRAGMA wal_autocheckpoint = 1000;")
        except Exception as e:
            logger.error(f' {e}')
        self.attach_db(cur, lst_dbs=attach_dbs)
        try:
            return CSQ.custom_request_c('', custom_request_c, conn=conn, cur=cur, hat_c=hat_c, list_of_lists_c=list_of_lists_c,
                                        rez_dict=rez_dict, one=one, one_column=one_column)
        finally:
            CSQ.close_bd(conn, cur)

    def store_cache_after_read(self, *, request_key: str, bd: str, custom_request_c: str, list_of_lists_c, rez_dict: bool,
                               one: bool, one_column: bool, hat_c: bool, attach_dbs, payload, status: str):
        if self.request_cache is None:
            return
        table_records = SQLCACHE.extract_query_table_records(
            sql_text=custom_request_c,
            main_db_path=bd,
            attached_alias_paths=self.attached_alias_paths(attach_dbs),
        )
        table_keys = [record['table_key'] for record in table_records if record.get('table_key')]
        policy = self.request_cache.compute_policy(table_keys=table_keys)
        entry = self.request_cache.store_entry(
            request_key=request_key,
            db_path=bd,
            sql_text=custom_request_c,
            params=list_of_lists_c,
            options={
                'rez_dict': bool(rez_dict),
                'one': bool(one),
                'one_column': bool(one_column),
                'hat_c': bool(hat_c),
            },
            payload=payload,
            body_hash=SQLCACHE.build_body_hash(payload),
            table_keys=table_keys,
            dependency_fingerprint=policy.get('dependency_fingerprint') or '',
            cache_lifetime_sec=int(policy.get('cache_lifetime_sec') or SQLCACHE.DEFAULT_CACHE_LIFETIME_SEC),
            stale_after_dt=policy.get('stale_after_dt'),
            notes=f'server_cache:{status.lower()}',
        )
        self._set_cache_headers(request_key=request_key, entry=entry, status=status, data_sent='1')

    def attach_db(self, cursor, lst_dbs: tuple):
        lst_dbs = (lst_dbs, ) if isinstance(lst_dbs, str) else lst_dbs
        for path in lst_dbs:
            match = re.search(r'(?<=:)(\w+\.db)', str(path))
            if match:
                db_name = match.group(0).strip()
                learn_name = db_name.split('.')[0]
                cursor.execute(f'ATTACH DATABASE "{str(DB_PATH / db_name)}" AS {learn_name}')

    def run_invalidation_hook(self, bd, custom_request_c, attach_dbs, client='', module='', result=None):
        if result is False or not CTXADM.is_sql_write(custom_request_c):
            return
        try:
            response = self.admin_repo.mark_sql_write_invalidated(
                sql=custom_request_c,
                main_db_path=bd,
                attach_dbs=attach_dbs,
                notes=f'server_write:{client}:{module}',
                attached_alias_paths=self.attached_alias_paths(attach_dbs),
            )
            affected_tables = response.get('affected_tables') or []
            if self.request_cache is not None and affected_tables:
                self.request_cache.invalidate_by_table_keys(affected_tables, notes=f'invalidated:{client}:{module}')
            if affected_tables:
                logger.info('[context_admin] invalidated tables=%s sources=%s variants=%s',
                            response.get('affected_tables'),
                            response.get('affected_sources'),
                            response.get('affected_variants'))
        except Exception as e:
            traceback.print_exc()
            logger.error(f'[context_admin] hook error: {e}')

    def use_db(self, bd, zapros='', shapka=True, spisok_spiskov=(()), rez_dict=False, one=False, module='', client='',
               one_column=False, hat_c='', custom_request_c='', list_of_lists_c='', attach_dbs: tuple = (), _request: Request | None = None):
        if hat_c == '':
            hat_c = shapka
        if custom_request_c == '':
            custom_request_c = zapros
        if list_of_lists_c == '':
            list_of_lists_c = spisok_spiskov
        request_headers = self.request_headers(_request)

        start_cache_bypass = time.time()
        cache_bypass = self.is_cache_bypass(bd=bd, custom_request_c=custom_request_c, attach_dbs=attach_dbs)
        logger.info(f'[use_db] cache bypass { time.time() - start_cache_bypass:.2f}s')

        request_key = ''
        prev_entry = None
        if not cache_bypass:
            start_cache_resolve = time.time()
            request_key = self.resolve_request_key(
                bd=bd,
                custom_request_c=custom_request_c,
                list_of_lists_c=list_of_lists_c,
                rez_dict=rez_dict,
                one=one,
                one_column=one_column,
                hat_c=hat_c,
                attach_dbs=attach_dbs,
                request_headers=request_headers,
            )
            logger.info(f'[use_db] cache resolve {time.time() - start_cache_resolve:.2f}s')

            start_server_from_cache = time.time()
            prev_entry, cache_hit = self.try_serve_from_cache(request_key=request_key, request_headers=request_headers)
            logger.info(f'[use_db] try servr from {time.time() - start_server_from_cache:.2f}s')

            logger.info(f'[cache_hit] {cache_hit}')
            if cache_hit:
                logger.info('[CACHED]')
                return prev_entry
        else:
            self.headers[CCS.SrvHeaders.CACHE_STATUS.value] = SQLCACHE.CACHE_STATUS.BYPASS
            self.headers[CCS.SrvHeaders.DATA_SENT.value] = '1'

        try:
            res = self.execute_sql(
                bd=bd,
                custom_request_c=custom_request_c,
                hat_c=hat_c,
                list_of_lists_c=list_of_lists_c,
                rez_dict=rez_dict,
                one=one,
                one_column=one_column,
                attach_dbs=attach_dbs,
            )
            self.run_invalidation_hook(bd=bd, custom_request_c=custom_request_c, attach_dbs=attach_dbs,
                                       client=client, module=module, result=res)
            if not cache_bypass and SQLCACHE.is_cacheable_sql(custom_request_c):
                status = SQLCACHE.CACHE_STATUS.REFRESH if prev_entry else SQLCACHE.CACHE_STATUS.MISS
                self.store_cache_after_read(
                    request_key=request_key,
                    bd=bd,
                    custom_request_c=custom_request_c,
                    list_of_lists_c=list_of_lists_c,
                    rez_dict=rez_dict,
                    one=one,
                    one_column=one_column,
                    hat_c=hat_c,
                    attach_dbs=attach_dbs,
                    payload=res,
                    status=status,
                )
            return res
        except (sqlite3.OperationalError, sqlite3.IntegrityError, sqlite3.ProgrammingError, sqlite3.DataError) as e:
            logger.error(f'Ошибка: {e}')
            self.headers[CCS.SrvHeaders.SYNTAX_ERROR.value] = '1'
            self.headers[CCS.SrvHeaders.EXCEPTION_MESSAGE.value] = quote(str(e))
        except Exception as e:
            logger.error(f'Ошибка: {e}')
            self.headers[CCS.SrvHeaders.SYNTAX_ERROR.value] = '1'
            self.headers[CCS.SrvHeaders.EXCEPTION_MESSAGE.value] = quote(str(e))

    def _extract_external_table_names(self, payload: dict) -> list[str]:
        changed = payload.get('changed')
        if not isinstance(changed, (list, tuple)):
            return []

        result = []
        for item in changed:
            if isinstance(item, dict):
                table_name = str(item.get('table') or '').strip()
            else:
                table_name = str(item or '').strip()

            if table_name:
                result.append(table_name)

        seen = set()
        ordered = []
        for name in result:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered

    @route('/ping')
    def ping(self, request: Request):
        return 'pong'

    @route('/')
    def db_request(self, request: Request):
        data = pickle.loads(request.data)
        self.dispatch_query(data)
        return self.use_db(**data, _request=request)

    @route('/cache/invalidate')
    def cache_invalidate(self, request: Request):
        try:
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                raw = request.get_data(as_text=True) or '{}'
                payload = json.loads(raw)

            table_names = self._extract_external_table_names(payload)
            if not table_names:
                body = {
                    'invalidate': False,
                }
                return Response(
                    json.dumps(body, ensure_ascii=False),
                    status=400,
                    content_type='application/json; charset=utf-8',
                )

            notes = str(payload.get('notes') or 'external_tcl_invalidation')
            logger.info('[external_invalidate] payload=%s', payload)
            logger.info('[external_invalidate] table_names=%s', table_names)

            ok = False
            if self.request_cache is not None:
                ok = bool(self.request_cache.invalidate_by_table_names(table_names, notes=notes))

            body = {
                'ok': ok,
                'table_names': table_names,
                'notes': notes,
                'invalidated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            return Response(
                json.dumps(body, ensure_ascii=False),
                status=200,
                content_type='application/json; charset=utf-8',
            )
        except Exception as e:
            logger.error('[external_invalidate] error: %s', e)
            body = {'ok': False, 'error': str(e)}
            return Response(
                json.dumps(body, ensure_ascii=False),
                status=500,
                content_type='application/json; charset=utf-8',
            )


def background_task(HOST, PORT):
    import os
    try:
        CPG.get_process_conn(CPG.PostgresConfig())
        logger.info('[PG] process connection warmed')
    except Exception as e:
        logger.error(f'[PG] warm connect error: {e}')

    logger.info(f"Процесс создан с pid: {os.getpid()}")
    serve(HTTPSrv(), host=HOST, port=PORT, threads=1,
          channel_timeout=660,
          cleanup_interval=30,
          )


def func_ping(HOST, PORT):
    import requests, time
    try:
        time.sleep(60 * 5)
        response = requests.get(f'http://{HOST}:{PORT}/ping')
        logger.info(f'SERVER: {HOST}:{PORT} проверка доступности: {response.ok!r}')
        return response.ok
    except KeyboardInterrupt:
        logger.info("Перезапуск...")
    except Exception as e:
        logger.error(f'Ошибка доступа к серверу: {e}')
    return False


def run(HOST: str, PORT: int | str):
    import multiprocessing
    HOST = "192.168.100.135"

    print('START SERVER')
    table_ports = {
        20002: [5200, 5201, 5202, 5203, 5204, 5205, 5206, 5207, 5208],
        20006: [5600, 5601, 5602, 5603, 5604, 5605, 5606, 5607, 5608],
        20007: [5700, 5701, 5702, 5703, 5704, 5705, 5706, 5707, 5708],
        20010: [5100, 5101, 5102, 5103, 5104, 5105, 5106, 5107, 5108],
    }
    sub_ports = table_ports.get(PORT)
    started_process = []
    import time
    try:
        if sub_ports:
            for port in sub_ports:
                process = multiprocessing.Process(target=background_task, args=(HOST, port))
                process.start()
                started_process.append((process, HOST, port))
        else:
            process = multiprocessing.Process(target=background_task, args=(HOST, PORT))
            process.start()
            started_process.append((process, HOST, PORT))
        while True:
            cleaned_process = []
            for process, host, port in started_process:
                if not func_ping(host, port):
                    try:
                        process.kill()
                        time.sleep(2)
                    except Exception as e:
                        print(e)
                    try:
                        logger.info("Попытка создаия процесса")
                        process = multiprocessing.Process(target=background_task, args=(host, port))
                        process.start()
                        time.sleep(2)
                    except Exception as e:
                        logger.error(f"Ошибка создания процесса: {e}")
                cleaned_process.append((process, host, port))
            started_process = cleaned_process
    except KeyboardInterrupt:
        logger.info("Перезапуск...")
    except Exception as e:
        print(f'Работа сервера завершена: {e}')
    finally:
        for process, host, port in started_process:
            process.kill()
