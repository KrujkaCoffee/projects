import Srv_tcp as Srv

HOST = "192.168.50.230"  # Standard loopback interface address (localhost)
HOST = "0.0.0.0"  # Standard loopback interface address (localhost)
PORT = 20010  # Port to listen on (non-privileged ports are > 1023)
if __name__ == '__main__':

    Srv.run(HOST, PORT)
