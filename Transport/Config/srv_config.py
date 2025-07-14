import os.path
import socket
PORT = 5000
DIR_ROOT = os.path.curdir
HOST = '127.0.0.1'
# if socket.gethostname() == 'POW18-15':#"POW-ING22":
#     HOST = '192.168.18.91'# AG local
#     DIR_ROOT = r'C:\Python\gui_flet_mes'  # AG local
# else:
#     HOST = '192.168.50.44'# server
#     DIR_ROOT = r'C:\srv_mes\web_app_mes'  # srv

IN_BROUSER = True

DOCX_TEMPLATES_PATH = os.path.join(DIR_ROOT, 'Modules_data', 'templates')
