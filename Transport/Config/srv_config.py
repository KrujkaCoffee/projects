import socket
import os
import pathlib

PORT = 20013

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent  # Папка проекта C:\srv_mes\web_app_mes
ASSERT_PATH = str(BASE_DIR / "assets")
TEMPLATES_DIR = str(BASE_DIR / "templates")
DIR_ROOT = str(BASE_DIR)  # srv

if socket.gethostname() == 'POW18-15':#"POW-ING22":
    HOST = '192.168.14.71'# AG local
    DIR_ROOT = r'C:\Python\gui_flet_mes'  # AG local
elif socket.gethostname() == 'POW18-08':#"POW-ING22":
    HOST = 'localhost'# AG local
    DIR_ROOT = r'C:\Python\gui_flet_mes'  # AG local
else:
    HOST = 'mesinfo.powerz.ru'# server

IN_BROUSER = True

# windows auth
USE_DB_SESSION = True
DEFAULT_DOMAIN = os.getenv("MES_AUTH_DEFAULT_DOMAIN", "POWERZ")
SESSION_COOKIE_NAME = "mes_auth_sid"
MONTH_SECONDS = 60 * 60 * 24 * 30
DB_SESSION_TABLE = os.getenv("MES_AUTH_SESSION_TABLE", "mes_auth_sessions")
DB_SESSION_PATH = os.getenv("MES_AUTH_SESSION_DB", "SRV:db_flet.db")

DOCX_TEMPLATES_PATH = os.path.join(DIR_ROOT, 'Modules_data', 'templates')