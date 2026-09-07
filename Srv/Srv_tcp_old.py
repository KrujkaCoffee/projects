import project_cust_38.Cust_Functions as F
import pickle
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.logistic_srv as LOG
import socketserver


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


def run(HOST: str, PORT: int, ansvwer: bool = True):
    # Standard loopback interface address (localhost)
    # Port to listen on (non-privileged ports are > 1023)
    print(HOST)
    print(PORT)
    while True:
        print('SRV: listen....')
        with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
            # Activate the server; this will keep running until you
            # interrupt the program with Ctrl-C
            server.serve_forever()
