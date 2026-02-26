import socket
from os import path
PORT = 20014
if socket.gethostname() == 'POW18-15':#"POW-ING22":
    HOST = '192.168.14.71'# AG local
    DIR_ROOT = r'C:\Python\gui_flet_mes'  # AG local
elif socket.gethostname() == 'POW18-08':#"POW-ING22":
    HOST = 'localhost'# AG local
    DIR_ROOT = r'C:\Python\gui_flet_mes'  # AG local
else:


    HOST = '192.168.50.44'# server
    DIR_ROOT = r'C:\srv_mes\web_app_mes'  # srv

IN_BROUSER = True

DOCX_TEMPLATES_PATH = path.join(DIR_ROOT, 'Modules_data', 'templates')