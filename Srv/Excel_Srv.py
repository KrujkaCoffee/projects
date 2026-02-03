import formul_xl_srv as Srv
import socket

PORT = 20012
if __name__ == '__main__':
    Srv.run("192.168.100.135", PORT)
    quit(2)
