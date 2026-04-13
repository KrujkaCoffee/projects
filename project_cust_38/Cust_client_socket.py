import socket
import pickle
import project_cust_38.logistic_srv as LOG
import os
import time
import logging
import requests
import enum
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from project_cust_38 import srv_sql_cache as SQLCACHE

#ip = '192.168.50.208'# AG local
ip = 'mesinfo.powerz.ru'# server domain  ip = '192.168.50.44'# server
# ip = '192.168.14.71'# AF local

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
    DATA_SENT = 'X-SQL-DATA-SENT'


class SessionManager:
    session = None

    def __enter__(self):
        if SessionManager.session is None:
            SessionManager.session = requests.Session()
            retries = Retry(
                total=CONNECTION_ATTEMPTS,
                backoff_factor=0.3,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(['POST'])
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


def db_path(name:str):
    dict_path = {'Naryad.db':'C://DB_srv//Naryad.db','BD_dse.db':'C://DB_srv//BD_dse.db',
                 'BD_zayav_out.db':'C://DB_srv//BD_zayav_out.db',
                 'BD_resxml.db': 'C://DB_srv//BD_resxml.db',
                'BD_files.db': 'C://DB_srv//BD_files.db',
                 'DB_kplan.db': 'C://DB_srv//DB_kplan.db',
                 'BD_users.db': 'C://DB_srv//BD_users.db',
                 'DB_invest.db': 'C://DB_srv//DB_invest.db',
                 'DB_nomenklatura_erp.db': 'C://DB_srv//DB_nomenklatura_erp.db',
                 'DB_xl_formulas.db': 'C://DB_srv//DB_xl_formulas.db',
                 'db_flet.db': 'C://DB_srv//db_flet.db',
                 }
    dict_port = {'Naryad.db': 20002, 'BD_dse.db': 20003, 'BD_zayav_out.db': 20004, 'BD_resxml.db': 20005,
                 'BD_files.db': 20006, 'DB_kplan.db': 20007,'DB_invest.db':20008,'BD_users.db':20009,
                 'DB_nomenklatura_erp.db':20010,'MES_api':20011,'DB_xl_formulas.db':20012,'db_flet.db':20014}
    name_db = name.split('SRV:')[-1].split('\\')[0]
    return dict_path[name_db], dict_port[name_db]

def check_protocol(server_address_port, message_str: dict) -> bool:
    logging.info('Check protocol')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        copy_msg = message_str.copy()
        copy_msg['custom_request_c'] = 'SELECT 12345'
        contains = b'<!DOCTYPE HTML>'
        count_tryes = 3
        for i in range(count_tryes):
            try:
                sock.connect(server_address_port)
                break
            except Exception as e:
                print(f'Ошибка: {e}')
                time.sleep(0.5)
        try:
            LOG.reliable_send(sock, pickle.dumps(copy_msg))

            bytes_response = sock.recv(15)
            if bytes_response == contains:
                return True
        except Exception as e:
            print(e)
            return False
        sock.close()
        return False


def client_sql_query(bd,custom_request_c,hat_c = True,list_of_lists_c = [[]],rez_dict=False, one = False,name_module='',client_name = '',port='',one_column=False, attach_dbs=()):
    def answer(msg_from_client):
        bytesToSend = pickle.dumps(msg_from_client)
        LOG.reliable_send(sock, bytesToSend)
        msg_from_server = LOG.reliable_receive(sock)
        if msg_from_server == None:
            return
        try:
            message_str = pickle.loads(msg_from_server)
        except:
            return
        return message_str

    msgFromClient = {"client": client_name, "module": name_module, "bd": bd, "custom_request_c": custom_request_c,
                     "hat_c": hat_c, "list_of_lists_c": list_of_lists_c,
                     "rez_dict": rez_dict, "one": one, "one_column":one_column, "attach_dbs": attach_dbs}
    serverAddressPort = (ip, port)
    count_tryes = 3
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
    current_protocol = 'HTTP'
    if not current_protocol:
        http = check_protocol(serverAddressPort, msgFromClient)
        current_protocol = 'HTTP' if http else 'UDP'
        os.environ['PROTOCOL'] = current_protocol
    if current_protocol == 'HTTP':
        try:
            headers = {}
            if cache_enabled and request_key and local_entry is not None:
                headers = {
                    SrvHeaders.REQUEST_KEY.value: request_key,
                    SrvHeaders.CLIENT_BODY_HASH.value: str(local_entry.get('body_hash') or ''),
                    SrvHeaders.CLIENT_CACHED_AT.value: str(local_entry.get('cached_at') or ''),
                }
            with SessionManager() as session:
                response = session.post(f'http://{ip}:{port}',
                                         data=pickle.dumps(msgFromClient),
                                         headers=headers)
                headers = {str(k).upper(): v for k, v in response.headers.items()}
                srv_exception_message = headers.get(SrvHeaders.EXCEPTION_MESSAGE.value)
                srv_syntax_error_flag = headers.get(SrvHeaders.SYNTAX_ERROR.value)
                if not response.ok and srv_syntax_error_flag:
                    print('Сообщение сервера', srv_exception_message)
                    print(f'Ошибка синтаксиса в запросе: \n{custom_request_c}')
                    return None
                cache_status = headers.get(SrvHeaders.CACHE_STATUS.value) or ''
                data_sent = headers.get(SrvHeaders.DATA_SENT.value) or '1'
                if cache_enabled and cache_status == 'CLIENT_FRESH' and local_entry is not None:
                    return local_entry['payload']
                if response.content:
                    message_str = pickle.loads(response.content)
                    if cache_enabled and request_key and data_sent == '1' and cache_status != 'BYPASS' and message_str not in (True, False):
                        SQLCACHE.write_cache_entry(request_key, message_str, headers, SrvHeaders=SrvHeaders)
                elif cache_enabled and data_sent == '0' and local_entry is not None:
                    return local_entry['payload']
        except Exception as e:
            print(f'От сервера получен None на запрос {msgFromClient} Ошибка: {e}')
            return
        return message_str
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            for i in range(count_tryes):
                try:
                    sock.connect(serverAddressPort)
                    message_str = answer(msgFromClient)
                    break
                except:
                    time.sleep(0.5)

        if message_str == None:
            print(f'От сервера получен None на запрос {msgFromClient}')
            return
        if cache_enabled and request_key:
            SQLCACHE.write_cache_entry(request_key, message_str, SrvHeaders=SrvHeaders)
        return message_str



def client_sql_query_old(bd,custom_request_c,hat_c = True,list_of_lists_c = [[]],rez_dict=False, one = False,name_module='',client_name = '',port=''):

    def readexactly(bytes_count: int) -> bytes:
        """
        Функция приёма определённого количества байт
        """
        b = b''
        while len(b) < bytes_count:  # Пока не получили нужное количество байт
            part = UDPClientSocket.recv(bytes_count - len(b))  # Получаем оставшиеся байты
            if not part:  # Если из сокета ничего не пришло, значит его закрыли с другой стороны
                print("Соединение потеряно")
                return
            b += part
        return b

    def reliable_receive(UDPClientSocket) -> bytes:
        """
        Функция приёма данных
        Обратите внимание, что возвращает тип bytes
        """
        b = b''
        while True:
            try:
                part = readexactly(2)
                if part == None:
                    return b
                part_len = int.from_bytes(part, "big")  # Определяем длину ожидаемого куска
                if part_len == 0 or part_len == None:  # Если пришёл кусок нулевой длины, то приём окончен
                    return b
            except:
                return b
            try:
                b += readexactly(part_len)  # Считываем сам кусок
            except:
                return

    def reliable_send(conn,data: bytes) -> None:
        """
        Функция отправки данных в сокет
        Обратите внимание, что данные ожидаются сразу типа bytes
        """
        # Разбиваем передаваемые данные на куски максимальной длины 0xffff (65535)
        for chunk in (data[_:_ + 0xffff] for _ in range(0, len(data), 0xffff)):
            conn.send(len(chunk).to_bytes(2, "big"))  # Отправляем длину куска (2 байта)
            conn.send(chunk)  # Отправляем сам кусок
        conn.send(b"\x00\x00")  # Обозначаем конец передачи куском нулевой длины

    def answer(msgFromClient, serverAddressPort):
        bytesToSend = pickle.dumps(msgFromClient)
        try:
            UDPClientSocket.connect(serverAddressPort)
        except:
            return
        #UDPClientSocket.sendall(bytesToSend)
        reliable_send(UDPClientSocket,bytesToSend)
        #msgFromServer = UDPClientSocket.recv(bufferSize)
        msgFromServer = reliable_receive(UDPClientSocket)
        if msgFromServer == None:
            return
        try:
            message_str = pickle.loads(msgFromServer)
        except:
            return
        return message_str

    msgFromClient = {"client": client_name, "module": name_module, "bd": bd, "custom_request_c": custom_request_c, "hat_c": hat_c, "list_of_lists_c": list_of_lists_c,
                     "rez_dict": rez_dict, "one": one, }
    # bytesToSend = str.encode(msgFromClient)
    serverAddressPort = (ip, port)
    bufferSize = 2048

    # Create a UDP socket at client side
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

    # Send to server using created UDP socket
    message_str = answer(msgFromClient, serverAddressPort)
    if message_str == None:
        return
    return message_str

#print(client_sql_query(DB,query,hat_c_,list_of_lists_c_,rez_dict_,one_))
