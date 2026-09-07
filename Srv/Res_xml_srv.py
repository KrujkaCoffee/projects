import Srv_tcp as Srv

HOST = "192.168.100.135"  
PORT = 20005  

if __name__ == '__main__':
    Srv.run(HOST, PORT)
    quit(2)