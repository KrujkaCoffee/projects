import pickle
import socketserver
import logging
import pathlib
import re
from urllib.parse import quote

from werkzeug import Request, Response

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.logistic_srv as LOG



# https://temofeev.ru/info/articles/rukovodstvo-po-programmirovaniyu-soketov-na-python-klient-server-i-neskolko-soedineniy/

class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.
    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def val_ansvwer(self, ansvwer):
        self.ansvwer = ansvwer

    def handle(self):
        # self.request is the TCP socket connected to the client
        # self.data = self.reliable_receive()
        # self.data = self.request.recv(1024).strip()
        print(f"{F.now()} Connected by {self.client_address}")
        try:
            self.data = LOG.reliable_receive(self.request)
            message_str = pickle.loads(self.data)
            query = check_query(message_str)
            print(f'Query: {message_str}')
        except:
            print(f'!!!   Ошибка получения')
            LOG.reliable_send(self.request, pickle.dumps(False))
            return
        try:
            if query == None:
                response_str = None
            else:
                response_str = use_db(**query)
            response = pickle.dumps(response_str)
        except:
            print(f'!!!   Ошибка обработки запроса {message_str}')
            LOG.reliable_send(self.request, pickle.dumps(False))
            try:
                log_errors(message_str)
            except:
                pass
            return

        try:
            LOG.reliable_send(self.request, response)
            try:
                if response_str == None:
                    print(f'Answer: {response_str}', end='\n\n')
                elif response_str == False:
                    print(f'Answer: {False}', end='\n\n')
                else:
                    try:
                        if len(str(response_str)) > 50:
                            print(f'Answer: {str(response_str)[:50] + " ....."}', end='\n\n', )
                        else:
                            print(f'Answer: {str(response_str)}', end='\n\n', )
                    except:
                        print(f'Answer: {True}', end='\n\n', )
            except:
                pass
            # conn.sendall(response)
        except:
            print(f'!!!   Ошибка отправки')
            try:
                LOG.reliable_send(self.request, pickle.dumps(None))
            except:
                pass
            finally:
                return


def use_db(bd, zapros='', shapka=True, spisok_spiskov=(()), rez_dict=False, one=False, module='', client='',
           one_column=False, hat_c='', custom_request_c='', list_of_lists_c=''):
    if hat_c == '':
        hat_c = shapka
    if custom_request_c == '':
        custom_request_c = zapros
    if list_of_lists_c == '':
        list_of_lists_c = spisok_spiskov
    conn, cur = CSQ.connect_bd(bd)
    res = CSQ.custom_request_c('', custom_request_c, conn=conn, cur=cur, hat_c=hat_c, list_of_lists_c=list_of_lists_c,
                               rez_dict=rez_dict, one=one, one_column=one_column)
    CSQ.close_bd(conn, cur)
    return res


def check_query(msg: dict):
    if type(msg) != dict:
        print('type of data must be dict')
        return
    if len(msg) <= 5:
        print('dict not count all parametrs')
        return
    if F.existence_file_c(msg['bd']) == False:
        print('database not found')
        return
    return msg


def log_errors(msg):
    path = r'Z:\MES_setup\errors\err_serv.txt'
    if F.existence_file_c(path) == False:
        F.save_file(path, '')
    F.add_rec_into_file_c(path, str(msg), sep='')


def run2(HOST: str, PORT: int, ansvwer: bool = True):
    # Standard loopback interface address (localhost)
    # Port to listen on (non-privileged ports are > 1023)
    while True:
        print('SRV: listen....')
        with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
            # Activate the server; this will keep running until you
            # interrupt the program with Ctrl-C
            server.serve_forever()

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logger = logging.getLogger('werkzeug')
msg_format = '\n{lines}\nКлиент: {user}\nВ модуле: {module}\nСделал запрос: {query}\n{lines}\n'
DB_PATH = pathlib.Path(r'C://DB_srv//').absolute()
ATTACH_DBS = {
    'BD_dse': [],
    'BD_files': [],
    'BD_users': [],
    'BD_resxml': [],
    'DB_kplan': [],
    'Naryad': ['DB_kplan.db']
}

def alert_b24(query, module, client):
    try:
        if query.lower().strip().startswith('delete'):
            import requests
            requests.post('https://bitrix24.kelast.ru/rest/1/ebehb6fsejx39kj2/im.message.add',
                          json={
                            'DIALOG_ID': 'chat78766',
                            'MESSAGE': f"{module}\n{client}\n{query}",
                          }, verify=False)
    except Exception as e:
        ...

class HTTPSrv:
    def __init__(self):
        self.headers = {}

    def dispatch_query(self, msg: dict):
        alert_b24(msg.get('custom_request_c', ''), msg.get('module', ''), msg.get('client', ''))
        message = msg_format.format(
            user=msg.get('client'),
            module=msg.get('module'),
            query=msg.get('custom_request_c'),
            lines='=' * 80
        )
        logger.info(message)

    def wsgi_app(self, environ, start_response):
        try:
            self.headers = {}
            request = Request(environ)
            data = pickle.loads(request.data)
            self.dispatch_query(data)
            result = self.use_db(**data)
            response = Response(pickle.dumps(result), headers=self.headers)
        except Exception as e:
            response = Response(status=500)
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
        self.attach_db(cur, lst_dbs=attach_dbs)
        res = CSQ.custom_request_c('', custom_request_c, conn=conn, cur=cur, hat_c=hat_c, list_of_lists_c=list_of_lists_c,
                                   rez_dict=rez_dict, one=one, one_column=one_column)
        CSQ.close_bd(conn, cur)
        return res

    def attach_db(self, cursor, lst_dbs: tuple):
        lst_dbs = (lst_dbs, ) if isinstance(lst_dbs, str) else lst_dbs
        for path in lst_dbs:
            match = re.search(r'(?<=:)(\w+\.db)', path)
            if match:
                db_name = match.group(0).strip()
                learn_name = db_name.split('.')[0]
                cursor.execute(f'ATTACH DATABASE "{str(DB_PATH / db_name)}" AS {learn_name}')


def run(HOST: str, PORT: int | str, ansvwer: bool = True, que = None):
    from werkzeug.serving import run_simple
    run_simple(HOST, PORT, HTTPSrv())
