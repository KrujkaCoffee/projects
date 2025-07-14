import socket
import project_cust_38.Cust_Functions as F
import pickle
import project_cust_38.Cust_SQLite as CSQ
import struct

#HOST = "192.168.44.22"  # Standard loopback interface address (localhost)
#PORT = 20002  # Port to listen on (non-privileged ports are > 1023)

#https://temofeev.ru/info/articles/rukovodstvo-po-programmirovaniyu-soketov-na-python-klient-server-i-neskolko-soedineniy/


def use_db(bd,custom_request_c,hat_c = True,list_of_lists_c = [[]],rez_dict=False, one = False, module = '', client = ''):
    conn, cur = CSQ.connect_bd(bd)
    res = CSQ.custom_request_c('',custom_request_c,conn=conn,cur=cur,hat_c=hat_c,list_of_lists_c=list_of_lists_c,rez_dict=rez_dict,one=one)
    CSQ.close_bd(conn,cur)
    pickle_file = pickle.dumps(res)
    return pickle_file

def check_query(msg:dict):
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
    path = r'O:\Журналы и графики\Ведомости для передачи\MES_setup\errors\err_serv.txt'
    if F.existence_file_c(path) == False:
        F.save_file(path,'')
    F.add_rec_into_file_c(path,str(msg),sep='')


def readexactly(conn,bytes_count: int) -> bytes:
    """
    Функция приёма определённого количества байт
    """
    b = b''
    while len(b) < bytes_count:  # Пока не получили нужное количество байт
        part = conn.recv(bytes_count - len(b))  # Получаем оставшиеся байты
        if part == b"\x00\x00":
            return b
        if not part:  # Если из сокета ничего не пришло, значит его закрыли с другой стороны
            #print("Соединение потеряно")
            return
        b += part
    return b

def reliable_receive(conn) -> bytes:
    """
    Функция приёма данных
    Обратите внимание, что возвращает тип bytes
    """
    b = b''
    while True:
        try:
            part_len = int.from_bytes(readexactly(conn,2), "big")  # Определяем длину ожидаемого куска
            if part_len == 0 or part_len == None:  # Если пришёл кусок нулевой длины, то приём окончен
                return b
        except:
            return b
        try:
            b += readexactly(conn, part_len)  # Считываем сам кусок
        except:
            return False

def run(HOST:str,PORT:int,ansvwer:bool=True):
    def reliable_send(data: bytes) -> None:
        """
        Функция отправки данных в сокет
        Обратите внимание, что данные ожидаются сразу типа bytes
        """
        # Разбиваем передаваемые данные на куски максимальной длины 0xffff (65535)
        try:
            for chunk in (data[_:_ + 0xffff] for _ in range(0, len(data), 0xffff)):
                conn.send(len(chunk).to_bytes(2, "big"))  # Отправляем длину куска (2 байта)
                conn.send(chunk)  # Отправляем сам кусок
        except:
            conn.send(b"\x00\x00")
        conn.send(b"\x00\x00")  # Обозначаем конец передачи куском нулевой длины

    # Standard loopback interface address (localhost)
    # Port to listen on (non-privileged ports are > 1023)
    while True:
        with socket.socket(socket.AF_INET,
                           socket.SOCK_STREAM) as s:  # создаётся объект сокета, которым поддерживается тип
            # контекстного менеджера, который используется в операторе with. Вызывать s.close() не нужно
            # AF_INET — это семейство интернет-адресов для IPv4
            # SOCK_STREAM — это тип сокета для TCP и протокол, который будет использоваться для передачи сообщений в сети.
            s.bind((HOST, PORT))
            # Метод .bind() применяется для привязки сокета к конкретному сетевому интерфейсу и номеру порта
            s.listen()  # подключения на сервере принимаются благодаря .listen(), а сам сервер становится «прослушиваемым» сокетом:
            print('SRV: listen....')
            conn, addr = s.accept()  # Методом .accept() выполнение блокируется, и ожидается входящее подключение. При подключении клиента возвращается новый объект сокета, который представляет собой подключение и кортеж с адресом клиента.
            with conn:  # Если в conn.recv() возвращается пустой объект bytes и b'', значит, в клиенте подключение закрыто и цикл завершён. Чтобы автоматически закрыть сокет в конце блока, с conn применяется оператор with.
                print(f"{F.now()} Connected by {addr}")
                while True:
                    try:
                        # data = conn.recv(2048)
                        data = reliable_receive(conn)
                        if not data:
                            break
                        message_str = pickle.loads(data)
                        query = check_query(message_str)

                        print(f'Query: {message_str}')
                    except:
                        print(f'!!!   Ошибка получения')
                        reliable_send(pickle.dumps(False))
                        break

                    try:
                        if query == None:
                            response = False
                        else:
                            response = use_db(**query)
                    except:
                        print(f'!!!   Ошибка обработки запроса {message_str}')
                        reliable_send(pickle.dumps(False))
                        log_errors(message_str)
                        break

                    try:
                        reliable_send(response)
                        try:
                            if ansvwer:
                                print(f'Answer: {pickle.loads(response)[:5]}', end='\n\n')
                        except:
                            pass
                        # conn.sendall(response)
                    except:

                        print(f'!!!   Ошибка отправки')
                        try:
                            reliable_send(pickle.dumps(None))
                        except:
                            pass
                        finally:
                            break
