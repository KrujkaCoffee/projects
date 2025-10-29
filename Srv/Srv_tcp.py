import pickle
import socketserver
import logging
import pathlib
import re
import sqlite3
import time
import os
from urllib.parse import quote
os.environ['MES_IS_SERVER'] = '1'

from werkzeug import Request, Response
from werkzeug.routing import Map, Rule
from waitress import serve

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_client_socket as CCS


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

def route(rule):
    def decorator(func):
        endpoint = func.__name__
        url_map.add(Rule(rule, endpoint=endpoint))
        route_handlers[endpoint] = func
        def wrapper_route(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return Response(pickle.dumps(result), status=200)
            except Exception as e:
                logger.error(f'Ошибка: {e}')
                return Response('Error', status=502)
        return wrapper_route
    return decorator


class HTTPSrv:
    def __init__(self):
        self.headers = {}

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
        except Exception as e:
            response = Response(status=501)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def use_db(self, bd, zapros='', shapka=True, spisok_spiskov=(()), rez_dict=False, one=False, module='', client='',
               one_column=False, hat_c='', custom_request_c='', list_of_lists_c='', attach_dbs: tuple = ()):
        if hat_c == '':
            hat_c = shapka
        if custom_request_c == '':
            custom_request_c = zapros
        if list_of_lists_c == '':
            list_of_lists_c = spisok_spiskov
        conn, cur = CSQ.connect_bd(bd)
        try:
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=FULL;")
            cur.execute("PRAGMA busy_timeout = 30000;")
            cur.execute("PRAGMA wal_autocheckpoint = 1000;")
        except Exception as e:
            logger.error(f' {e}')
        self.attach_db(cur, lst_dbs=attach_dbs)
        res = False
        try:
            res = CSQ.custom_request_c('', custom_request_c, conn=conn, cur=cur, hat_c=hat_c, list_of_lists_c=list_of_lists_c,
                                       rez_dict=rez_dict, one=one, one_column=one_column)
        except (sqlite3.OperationalError, sqlite3.IntegrityError, sqlite3.ProgrammingError, sqlite3.DataError) as e:
            logger.error(f'Ошибка: {e}')
            self.headers[CCS.SrvHeaders.SYNTAX_ERROR.value] = '1'
            self.headers[CCS.SrvHeaders.EXCEPTION_MESSAGE.value] = quote(str(e))
        except Exception as e:
            logger.error(f'Ошибка: {e}')
            self.headers[CCS.SrvHeaders.SYNTAX_ERROR.value] = '1'

            self.headers[CCS.SrvHeaders.EXCEPTION_MESSAGE.value] = quote(str(e))
        finally:
            CSQ.close_bd(conn, cur)
        return res

    @route('/ping')
    def ping(self, request: Request):
        return 'pong'

    @route('/')
    def db_request(self, request: Request):
        data = pickle.loads(request.data)
        self.dispatch_query(data)
        return self.use_db(**data)

    def attach_db(self, cursor, lst_dbs: tuple):
        lst_dbs = (lst_dbs, ) if isinstance(lst_dbs, str) else lst_dbs
        for path in lst_dbs:
            match = re.search(r'(?<=:)(\w+\.db)', path)
            if match:
                db_name = match.group(0).strip()
                learn_name = db_name.split('.')[0]
                cursor.execute(f'ATTACH DATABASE "{str(DB_PATH / db_name)}" AS {learn_name}')

def background_task(HOST, PORT):
    # from werkzeug.serving import run_simple
    # run_simple(HOST, PORT, HTTPSrv())
    import os
    logger.info(f"Процесс создан с pid: {os.getpid()}")
    serve(HTTPSrv(), host=HOST, port=PORT)


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

    print('START SERVER')
    table_ports = {
        20002: [5200, 5201, 5202, 5203, 5204],
        20006: [5600, 5601, 5602, 5603, 5604],
        20007: [5700, 5701, 5702, 5703, 5704],
        20010: [5100, 5101, 5102, 5103, 5104],
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
                        pass
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
