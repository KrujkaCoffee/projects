import Srv_tcp as Srv
print('load')
HOST = "192.168.100.135"  
PORT = 20009

if __name__ == '__main__':
    Srv.run(HOST, PORT)
    quit(2)
