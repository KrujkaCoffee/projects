import formul_xl_srv as Srv
import socket


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
HOST = s.getsockname()[0]
s.close()
PORT = 20012  # Port to listen on (non-privileged ports are > 1023)
# https://temofeev.ru/info/articles/rukovodstvo-po-programmirovaniyu-soketov-na-python-klient-server-i-neskolko-soedineniy/
Srv.run(HOST, PORT)
quit()
