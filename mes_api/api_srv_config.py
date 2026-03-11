import socket
import os
PORT = 20011
IS_PROD= False
if socket.gethostname() == 'POW18-15':#"POW-ING22":
    HOST = '192.168.14.71'# AG local
    DIR_BUDGETS = r'C:\1c\Бюджеты\бюджеты'  # AG local
    PREFIX_DOWNLOAD_PATH = fr'C:\Python\gui_flet_mes\Modules_data'
    PREFIX_OPEN_LOCAL_DIR = fr'\\srv-fs\Disk_Z'
else:
    HOST = '192.168.100.135'# server
    DIR_BUDGETS = r'C:\srv_mes\1c\Бюджеты'  # server
    PREFIX_DOWNLOAD_PATH = fr'C:\srv_mes\web_app_mes\Modules_data'
    PREFIX_OPEN_LOCAL_DIR = fr'\\srv-fs\Disk_Z'
    IS_PROD =True
# file server
SHARED_FOLDER = r'C:\srv_mes\shared' #10.03.2026
PASSWORD_STORAGE = os.path.join(SHARED_FOLDER, 'authenticate', 'Riba.pickle')

FILES_PYTHON_INTERPRETER_PATH = r"C:\srv_mes\srv_mes\interpreter\python.zip"
DIRECTORY_TO_ARCHIVE = r"C:\srv_mes\srv_mes\project_cust_38"
ARCHIVE_NAME = "project_cust_38.zip"
