import datetime
import stat
import os
import pickle
import hashlib
import shutil
import getpass
import sys
import logging
import zipfile
import re
import subprocess
import tarfile
import io
import tempfile
from typing import List
from pathlib import Path

import requests

SRV_ADDRESS = 'http://mesinfo.powerz.ru:20011'

KEY_SRV_HASH = 'PROJECT_CUST_SRV_HASH'
KEY_SERVER_NOT_AVAILABLE = 'KEY_SERVER_NOT_AVAILABLE'

logging.basicConfig(level=logging.INFO)


class Crypt:
    def generate_file_hash(self, file_path):
        """Генерирует хэш-сумму для указанного файла."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def text_hash(self, text: [str, bytes]):
        hash_md5 = hashlib.md5()
        hash_md5.update(text)
        return hash_md5.hexdigest()

def request(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logging.error(e)
            return
    return wrapper


@request
def fetch_ping():
    response = requests.get(SRV_ADDRESS, timeout=3, verify=False)
    response.raise_for_status()
    return response.ok

def ping(fn):
    def wrapper(*args, **kwargs):
        flag = os.environ.get('KEY_SERVER_NOT_AVAILABLE')
        if flag is None and fetch_ping():
            return fn(*args, **kwargs)
        os.environ[KEY_SERVER_NOT_AVAILABLE] = '1'
    return wrapper


class LoneInterpreter:
    def __init__(self):
        self.home_path = str(Path().home() / 'MES')
        from project_cust_38.Cust_client_socket import ip
        SRV_PORT = 20011
        self.server_url = f'http://{ip}:{SRV_PORT}/files'
        self.system_interpreter_path = r'Z:\Setup\python.zip'
        self.is_actual = self.check_python_available(self.python_path) and self.check_actual_interpreter()

        self.usr_hash = self.usr_packages = None

    def create_run_bat(self, program_path_embed: str, program_name: str):
        try:
            executor = self.interpreter.python_path
            src_mini_git_path = os.path.join(r'Z:\Setup', 'mini_git.py')
            dest_mini_git_path = str((Path(program_path_embed) / 'mini_git.py').absolute())
            bat_source = f"@echo off\ncopy /Y {src_mini_git_path} {dest_mini_git_path}\n{executor} mini_git.py\n{executor} {self.DICT_PROG[program_name]["Название"]} %*"
            with open(os.path.join(program_path_embed, 'run.bat'), 'w+') as desc:
                desc.write(bat_source)
        except Exception as e:
            logging.error(e)

    @property
    def python_folder(self):
        py = shutil.which("python")
        if os.path.exists(py) and 'Microsoft' not in py:
            return str(Path(py).parent.absolute())
        return str((Path(self.home_path) / 'py').absolute())

    @property
    def python_path(self):
        py = shutil.which("python")
        if os.path.exists(py) and 'Microsoft' not in py:
            return py
        return str((Path(self.python_folder) / 'python.exe').absolute())

    def __server_inter_size(self):
        try:
            response = requests.get(f'{self.server_url}/py/hash/')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error('[python]Не удалось запросить актуальный хэш python интерпретатора')
            logging.error(e)

    def __main_inter_size(self):
        """Возвращает общий размер всех файлов в указанной директории в байтах."""
        temp = tempfile.gettempdir()
        path = Path(temp) / 'mes_libs' / 'lib_hash.pickle'
        if not os.path.exists(self.python_path): return False
        try:
            if not subprocess.run([self.python_path, r'Z:\Setup\generate_hash.py'], check=True, encoding='utf8'):
                return logging.error(f'[python]Не удалось актуализировать хэш у библиотек с аргументами [python={self.python_path}, hash_path={path}]')
            usr_py_info = pickle.load(path.open('rb'))
            usr_hash = usr_py_info.get('packages_hash')

            if usr_hash and len(usr_hash) == 64:
                return usr_hash
        except Exception as e:
            print()

    def check_actual_interpreter(self):
        if not os.path.exists(self.python_path):
            return False
        try:
            srv_info = self.get_srv_size()
            if isinstance(srv_info, dict) and all(key in srv_info for key in ('packages', 'size')):
                srv_packages = srv_info['packages']
                srv_size = srv_info['size']
                usr_packages = self.get_installed_packages()
                usr_size = self.get_py_size()
                if (usr_size / srv_size) * 100 > 80:
                    necessary_libs = set(srv_packages).difference(usr_packages)
                    return not bool(necessary_libs)
                return False
        except Exception as e:
            logging.error(e)

    def replace_interpreter(self):
        try:
            if os.path.exists(self.system_interpreter_path) and os.path.getsize(self.system_interpreter_path) > 300_000:
                filename = self.system_interpreter_path
            else:
                filename = self.download_file()
            if filename is None:
                return logging.error('[python_download] Не удалось загрузить интерпретатор с сервера')
            extract_to = os.path.join(self.home_path, 'py')
            if self.unzip_file(filename, extract_to):
                self.is_actual = True
        except Exception as e:
            print(e)

    def extract_filename(self, content_disposition):
        match = re.search(r'filename="([^"]+)"', content_disposition)
        if match:
            return match.group(1)
        return None

    def unzip_file(self, zip_file_path, extract_to_folder):
        if not os.path.exists(zip_file_path):
            print(f"Файл {zip_file_path} не найден.")
            return
        os.makedirs(extract_to_folder, exist_ok=True)
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to_folder)
            print(f"Файлы распакованы в {extract_to_folder}")
            return True

    def download_file(self):
        try:
            response = requests.get(f'{self.server_url}/py/', stream=True, verify=False)
            response.raise_for_status()
            if content_disposition := response.headers.get('Content-Disposition'):
                filename = self.extract_filename(content_disposition)
                with open(filename, 'wb+') as file:
                    for chunk in response.iter_content(chunk_size=8192):  # 8192
                        file.write(chunk)
                print(f"Файл '{filename}' успешно скачан.")
                return filename
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при скачивании файла: {e}")

    def check_python_available(self, python_path: str):
        python_exec_path = str(Path(python_path) / 'python.exe')
        if not os.path.exists(python_exec_path):
            return False
        try:
            result = subprocess.run([python_exec_path, '--version'], capture_output=True, text=True, check=True)
            print(result.stdout.strip())
            return True
        except subprocess.CalledProcessError:
            return False

    def get_installed_packages(self):
        """Получаем список установленных пакетов и их версий."""
        temp = tempfile.gettempdir()
        path = Path(temp) / 'mes_libs' / 'lib_hash.pickle'
        if not os.path.exists(self.python_path): return False
        if not subprocess.run([self.python_path, r'Z:\Setup\generate_hash.py'], check=True, encoding='utf8', creationflags=subprocess.CREATE_NO_WINDOW):
            return logging.error(
                f'[python]Не удалось актуализировать хэш у библиотек с аргументами [python={self.python_path}, hash_path={path}]')
        usr_py_info = pickle.load(path.open('rb'))
        usr_packages = usr_py_info.get('packages')
        if isinstance(usr_packages, list):
            return usr_packages

    def get_py_size(self):
        return sum(
            os.path.getsize(os.path.join(dir_path, file))
            for dir_path, _, files in os.walk(self.python_folder)
            for file in files
        )

    def drop_superfluous_libs(self, lib_list: List[str]):
        for package in lib_list:
            try:
                script_folder = Path(r'Z:\Setup') / 'uninstall_lib.bat'
                subprocess.check_call([str(script_folder), self.python_path, package], shell=True)
            except Exception as e:
                print(e)
    def get_srv_size(self):
        response = requests.get(f'{self.server_url}/py/packages/list/', verify=False)
        if response.ok:
            return response.json()

    def download_srv_packages(self, libs: List[str]):
        temp_dir = tempfile.gettempdir()
        response = requests.post(f'{self.server_url}/py/packages/', json=list(libs), verify=False)
        temp_libs = Path(temp_dir) / 'mes_libs'
        temp_libs.mkdir(exist_ok=True, parents=True)
        if response.ok:
            try:
                with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
                    tar.extractall(str(temp_libs))
                    for lib in libs:
                        script_folder = Path(r'Z:\Setup') / 'install_lib.bat'
                        lib_name, version = lib.split('==')
                        subprocess.check_call([str(script_folder), self.python_path, str(temp_libs), lib_name, version], shell=True)
            except Exception as e:
                logging.error(f'Ошибка во время установки библиотек {libs}', exc_info=True)

    def actualize_py_libs(self):
        srv_info = self.get_srv_size()
        if isinstance(srv_info, dict) and all(key in srv_info for key in ('packages', 'size')):
            srv_packages = srv_info['packages']
            srv_size = srv_info['size']
            usr_packages = self.get_installed_packages()
            usr_size = self.get_py_size()
            if (usr_size / srv_size) * 100 > 80:
                superfluous_libs = set(usr_packages).difference(srv_packages)
                necessary_libs = set(srv_packages).difference(usr_packages)
                if necessary_libs:
                    self.download_srv_packages(necessary_libs)
                if self.check_actual_interpreter():
                    logging.info('Библитеки успешно обновлены')
            else:
                self.replace_interpreter()

    def check_python_home_version(self):
        return self.check_python_available(self.python_folder) and self.check_actual_interpreter()


class ProjectCust38:
    def __init__(self, window = None):
        self.is_download = False
        self.content = None
        self.PUT_PO_UMOLCH = str(Path().home() / 'MES')
        if window:
            self.PUT_PO_UMOLCH = window.PUT_PO_UMOLCH
        self.path = os.path.join(self.PUT_PO_UMOLCH, "project_cust_38.zip")
        self.crypt = Crypt()
        self.BASE_URL = SRV_ADDRESS
        self.PROJECT_CUST_FILE_URL = f'{self.BASE_URL}/files/project-cust/'
        self.PROJECT_CUST_HASH_URL = f'{self.BASE_URL}/files/project-cust/hash/'

    def __enter__(self):
        if not self.is_download:
            self.download_project_cust_38()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.path.exists(self.path):
            os.remove(self.path)
        self.is_download = False

    def put_full_perm_on_path(self, path: str):
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

    def recurse_put_permissions_on_file(self, path: str):
        self.put_full_perm_on_path(path)
        for bas_dir, dirs, files in os.walk(path):
            for file in files:
                file_abs_path = os.path.join(bas_dir, file)
                self.put_full_perm_on_path(file_abs_path)
            for dir in dirs:
                dir_abs_path = os.path.join(bas_dir, dir)
                self.put_full_perm_on_path(dir_abs_path)

    def check_exclude_dirs(self):
        try:
            dirs = ('.git', 'venv')
            for dir_name in dirs:
                path = Path(self.PUT_PO_UMOLCH) / dir_name
                if path.exists():
                    self.recurse_put_permissions_on_file(str(path))
                    shutil.rmtree(str(path))
                if os.path.exists(path):
                    with open(r'Z:\MES_setup\errors\broken_clients.txt', 'a+') as f:
                        username = os.getenv('USERNAME')
                        computer_name = os.getenv('COMPUTERNAME')
                        f.write(f'{username}|{computer_name}|{dir_name}\n')
        except Exception as e:
            print(e)

    @ping
    def download_project_cust_38(self):
        logging.info('Загрузка библиотеки project_cust_38 с сервера...')
        response = requests.get(self.PROJECT_CUST_FILE_URL)
        response.raise_for_status()
        if not response.ok:
            logging.info(
                '[project_cust_38]клиент не смог получить актуальную версию пакета из-за проблем на сервере')
            return
        with open(self.path, 'wb') as f:
            f.write(response.content)
            self.content = response.content
            self.is_download = True
            logging.info('[project_cust_38]Загрузка библиотеки успешно завершена...')

    @ping
    def __srv_hash(self):
        if srv_hash := os.environ.get(KEY_SRV_HASH):
            return srv_hash
        try:
            response = requests.get(self.PROJECT_CUST_HASH_URL, timeout=3)
            response.raise_for_status()
            new_hash = response.json()
        except Exception as e:
            logging.error('[project_cust] Ошибка при запросе хэша', exc_info=e)
            return
        os.environ[KEY_SRV_HASH] = new_hash
        return new_hash

    def __user_hash(self, proj_path: str) -> str:
        hash_object = hashlib.sha256()
        dir_path = Path(proj_path) / 'project_cust_38'
        dir_path.mkdir(exist_ok=True, parents=True)
        for path in self.make_files_tree_struct(str(dir_path)):
            if path.is_file():
                with path.open('rb') as f:
                    hash_object.update(f.read())
                hash_object.update(path.name.encode('utf-8'))
        return hash_object.hexdigest()

    def make_files_tree_struct(self, proj_path):
        exclude_folders = ('.git', '__pycache__', '.idea', 'venv')
        tree = []
        for abs_path, folders, filenames in os.walk(proj_path):
            base_path = Path(abs_path)
            if base_path.name not in exclude_folders:
                for filename in filenames:
                    tree.append(base_path / filename)
        return tree

    def check_project_cust_38(self, path: str, check_srv_not_available: bool = False):
        if check_srv_not_available and os.environ.get(KEY_SERVER_NOT_AVAILABLE):
            return True
        if not os.path.exists(path):
            return False
        return self.__srv_hash() == self.__user_hash(path)

    @ping
    def update(self, path: str):
        with self:
            list_dirs = []
            dir_to_extract = os.path.join(path, 'project_cust_38')
            try:
                with zipfile.ZipFile(self.path, 'r') as zip_ref:
                    list_dirs.extend(file.filename for file in zip_ref.filelist)
                    zip_ref.extractall(dir_to_extract)
                    logging.info('[project_cust_38]Обновление успешно завершено!')
            except Exception as e:
                logging.error('[project_cust_38]Обновление завершилось неудачей', exc_info=e)
            self.drop_unnecessary_files(base_dir=dir_to_extract, lst_zip=list_dirs)

    def drop_unnecessary_files(self, base_dir, lst_zip):
        logging.info('[project_cust_38]Удаление лишних модулей')
        for filename in os.listdir(base_dir):
            if filename not in lst_zip:
                abs_path = os.path.join(base_dir, filename)
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
                if os.path.isdir(abs_path):
                    shutil.rmtree(abs_path, onerror=self.on_delete_error)

    def on_delete_error(self, fn, path, exc):
        try:
            os.chmod(path, 0o777)
            os.remove(path)
        except Exception as e:
            print(e)

    def hash_files_in_directory(self, directory):
        """Генерирует хэш-суммы для всех файлов в указанной директории."""
        file_hashes = set()
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_hashes.add(self.generate_file_hash(file_path))
        return file_hashes

    def eq_hashes(self, server_hashes: dict, client_hashes: dict):
        for file_path, file_hash in server_hashes.items():
            cl_file_hash = client_hashes.get(file_path)
            if cl_file_hash and cl_file_hash == file_hash:
                continue
            else:
                return False
        return True

IGNORE_DIRS = ('venv', 'clients_errors', '__pycache__', '.idea', '.git', 'Scripts', 'Lib', 'project_cust_38', 'Doc', 'include', 'tcl')
SET_PY_FILES = {'Lib', 'libcrypto-1_1.dll', 'libffi-8.dll', 'libssl-1_1.dll', 'pyexpat.pyd', 'python.cat', 'python.exe',
              'python3.dll', 'python311.dll', 'python311.zip', 'python311._pth', 'pythonw.exe', 'Scripts', 'select.pyd',
              'sqlite3.dll', 'unicodedata.pyd', 'vcruntime140.dll', 'vcruntime140_1.dll', 'winsound.pyd',
              'xlwings32-0.30.10.dll', 'xlwings64-0.30.10.dll', '_asyncio.pyd', '_bz2.pyd', '_ctypes.pyd',
              '_decimal.pyd', '_elementtree.pyd', '_hashlib.pyd', '_lzma.pyd', '_msi.pyd', '_multiprocessing.pyd',
              '_overlapped.pyd', '_queue.pyd', '_socket.pyd', '_sqlite3.pyd', '_ssl.pyd', '_uuid.pyd', '_zoneinfo.pyd'}

class Main:
    def __init__(self, srv_dir: str = '', usr_dir: str = None, app_name: str = None):
        self.developers = ()
        self.current_dir = usr_dir
        self.app_executor = None
        self.server_dir = srv_dir
        self.app_name = app_name
        self.ip = None
        self.pickle_name = 'hashed_files.pickle'
        self.list_apps = r'Z:\MES_setup\list.txt'
        if not self.current_dir or not self.server_dir or not self.app_name:
            self.fill_params()
            self.current_dir, self.current_file = os.path.split(os.path.abspath(__file__))
        self.pickle_path = str((Path(self.server_dir) / self.pickle_name).absolute())
        self.who_im()
        self.is_windows = True
        self.ignore_files = [self.pickle_name, '.gitignore', 'python', 'window_free.vbs', 'window.vbs', 'run.bat', 'ver', 'mini_git.py', 'remote_run.bat'] + list(SET_PY_FILES)  #  игонрируются _*
        self.ignore_dirs = ['venv', 'clients_errors', '__pycache__', '.idea', '.git', 'Scripts', 'Lib', 'project_cust_38'] + list(SET_PY_FILES)
        self.project_cust = ProjectCust38()
        self.interpreter = LoneInterpreter()

    def test_func(self):
        '''Принудительное задание роли'''
        self.is_server = True

    def push(self, no_update: bool = False):
        if no_update:
            return
        if self.is_server:
            self.server_actions()  # успешно
        else:
            self.client_actions()  # успешно

    def who_im(self):
        self.is_server = None
        self.is_client_or_test = None
        pc_login = getpass.getuser()

        if self.current_dir.startswith("Z:"):
            self.is_server = True
        elif pc_login in self.developers:
            raise ValueError('сработала защита накатывания обновления разработчику от сервера(диска Z)')
        else:
            self.is_client_or_test = None

    def fill_params(self):
        """импорт происходит в рамках локальной области видимости"""

        if not os.path.exists(self.list_apps):
            logging.warning(f'не найдена директория: {self.list_apps}')
            return
        with open(self.list_apps, 'r', encoding='utf8') as desc:
            list_apps = desc.readlines()
        self.apps = [line.replace('\n', '').split('|') for line in list_apps]
        apps_by_module = {line[2]: line for line in self.apps}
        files = set(os.listdir(os.path.curdir)).intersection(apps_by_module.keys())
        if files and len(files) == 1:
            line = apps_by_module[files.pop()]
            self.server_dir = os.path.join(line[1].replace(r'\ProdSoft', ''), 'embed')
            self.app_name = line[0]
            self.app_executor = line[2]
            if not os.path.exists(self.server_dir):
                logging.warning(f'Не найдена директория {self.server_dir} возможно нету доступа к диску Z')
                return

    def load_cust_mes_config(self):
        try:
            from project_cust_38 import Cust_mes as CMS
            config = CMS.ProjectConfig()
            self.developers = config.developers
            if '--strict' in sys.argv:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                config.set('last_update', now, self.app_name)
        except ImportError:
            print('не удалось загрузить настройки cust_mes из-за отсутсвия модуля')

    def get_project_cust_lib(self):
        msg_form = '[project_cust_38] %s'
        logging.info(msg_form % 'Проверка актуальности хэша...')
        if self.project_cust.check_project_cust_38(self.current_dir):
            return logging.info(msg_form % 'Библиотека актуальна')
        logging.info(msg_form % 'Библиотека неактуальна. Загрузка с сервера...')
        self.project_cust.update(self.current_dir)

    def change_executor(self):
        abs_path = str(Path(self.current_dir) / self.app_executor)
        setup_path = r'Z:\Setup\Setup.exe'
        script = f"import os;os.startfile({setup_path!r}, arguments={self.app_name!r})"
        try:
            with open(abs_path, 'w+', encoding='utf8') as f:
                f.write(script)
        except Exception as e:
            print(e)

    def client_actions(self):
        logging.info('[mini_git]client actions')

        if Path().absolute().drive != 'Z:':
            try: # обновление библиотек python
                self.interpreter.actualize_py_libs()
            except Exception as e:
                logging.error(
                    '[self.interpreter.actualize_py_libs]Произошла ошибка при попытке актуализации библиотек python',
                    exc_info=True
                )
            try: # актуализация run.bat
                self.interpreter.create_run_bat(self.current_dir, self.app_name)
            except Exception as e:
                logging.error(e)
            self.project_cust.check_exclude_dirs()
            self.get_project_cust_lib()

        if os.path.exists(self.pickle_path):
            srv_files, srv_dirs = self.load_pickle(self.pickle_path)
            client_files, client_dirs = self.get_hashed_files()
            res_check_dirs = self.difference_dirs(srv_dirs, client_dirs)
            if res_check_dirs:
                create_dirs, del_dirs = res_check_dirs
                if create_dirs:
                    self.make_dirs(create_dirs, self.current_dir)
            self.check_files(srv_files, client_files, self.current_dir, self.server_dir, del_file=False)
        else:
            print(f'[mini_git]на сервере нет {self.pickle_name} клиент не имеет право его там создавать')
        if Path().absolute().drive != 'Z:':
            if self.is_old_struct(self.current_dir) and not self.is_old_struct(self.server_dir):
                self.change_executor()

    def server_actions(self):
        print('server_actions')
        files, dirs = self.get_hashed_files()
        self.save_hashed_fils(files, dirs)

    def del_file(self, full_path):
        if os.path.exists(full_path):
            if self.is_windows:
                os.chmod(full_path, 0o777)
            name = Path(full_path).name
            if name not in self.ignore_files and name not in SET_PY_FILES:
                os.remove(full_path)

    def del_dir(self, dir_path):
        try:
            shutil.rmtree(dir_path)
        except OSError as e:
            print(f'папка уже была удалена ранним проходом {e}')

    def copy_file(self, file_path, source, distanation, del_file=True):
        source = os.path.join(source, file_path)
        distinct = os.path.join(distanation, file_path)

        if del_file and os.path.exists(distinct):
            self.del_file(distinct)
        shutil.copy(source, distinct)

    def make_dirs(self, create_dirs, path):
        for dir in create_dirs:
            path = os.path.join(path, dir)
            Path(path).mkdir(parents=True, exist_ok=True)

    def del_dirs(self, del_dirs, destanation):
        for dir in del_dirs:
            path = os.path.join(destanation, dir)
            try:
                shutil.rmtree(path)
            except (FileNotFoundError, PermissionError) as e:
                print(f'папка уже была удалена ранним проходом {e}')

    def difference_dirs(self, mast_be_dirs, check_dirs):
        '''различия между папками, получить папки на удаление и на создание'''
        if mast_be_dirs != check_dirs:
            set_mast_be_dirs = set(mast_be_dirs)
            set_check_dirs = set(check_dirs)
            create_dirs = set_mast_be_dirs.difference(set_check_dirs)
            del_dirs = set_check_dirs.difference(set_mast_be_dirs)
            return self.none_or_val(create_dirs), self.none_or_val(del_dirs)

    def none_or_val(self, val):
        return val if val != {} else None

    def file_ignore_condition(self, file: str):
        path, file = os.path.split(file)
        if file.startswith('_'):
            return True
        elif file.endswith('.dll') or file.endswith('.pickle') or file.endswith('.zip'):
            return True
        return False

    def get_files(self, check_dir=None):
        my_files = []
        my_dirs = []
        if not check_dir:
            check_dir = self.current_dir
        for root, dirs, files in os.walk(check_dir):
            dirs[:] = [dir for dir in dirs if dir not in self.ignore_dirs ]

            for dir in dirs:
                dir_path = os.path.join(root, dir)
                my_dirs.append(dir_path.replace(check_dir, '')[1:])

            files[:] = [file for file in files if (file not in self.ignore_files) and not self.file_ignore_condition(file)]
            for fname in files:
                filename = os.path.join(root, fname)
                my_files.append(filename.replace(check_dir, '')[1:])
        return my_files, my_dirs

    def get_hashed_files(self, check_dir=None):
        files, dirs = self.get_files(check_dir)
        hashed_files = {}
        for file in files:
            if not check_dir:
                file_path = os.path.join(self.current_dir, file)
            else:
                file_path = os.path.join(check_dir, file)
            hashed_files[file] = self.hash_file(file_path)
        return hashed_files, dirs

    def hash_file(self, file):
        hash_md5 = hashlib.md5()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def save_hashed_fils(self, hashed_files, dirs, path=None):
        save_full_dir_dict = {}
        save_full_dir_dict['files'] = hashed_files
        save_full_dir_dict['dirs'] = dirs
        if not path:
            path = self.pickle_path
        with open(path, 'wb') as file:
            pickle.dump(save_full_dir_dict, file)

    def load_pickle(self, path):
        with open(path, 'rb') as file:
            full_di = pickle.load(file)
        hashed_files = full_di['files']
        dirs = full_di['dirs']
        return hashed_files, dirs

    def get_server_files(self):
        if os.path.exists(self.pickle_path):
            print(f'ошибка на сервере нет {self.pickle_name} файла')
        else:
            return self.load_pickle(self.pickle_path)

    def have_difference(self):
        if not os.path.exists(self.pickle_path): return False
        srv_files, srv_dirs = self.load_pickle(self.pickle_path)
        usr_files, client_dirs = self.get_hashed_files()
        usr_files = {k: v for k, v in usr_files.items() if k not in self.ignore_files}
        srv_files = {k: v for k, v in srv_files.items() if k not in self.ignore_files}
        return not all(usr_files.get(f) == h for f, h in srv_files.items())

    def check_files(self, server_files_dict, client_files_dict, distanation, source, del_file):
        server_files = server_files_dict.keys()
        client_files = client_files_dict.keys()
        _ = [self.del_file(os.path.join(distanation, file)) for file in client_files if file not in server_files]
        for server_file, serverr_file_hash in server_files_dict.items():
            client_file_hash = client_files_dict.get(server_file)
            if client_file_hash:
                if not serverr_file_hash == client_file_hash:
                    print(f'копирование с заменой {server_file}')
                    self.copy_file(server_file, source, distanation, del_file)
            else:
                print(f'копирование {server_file}')
                self.copy_file(server_file, source, distanation, del_file)

    def is_old_struct(self, dir) -> bool:
        srv_files = os.listdir(dir)
        intersections = SET_PY_FILES.intersection(srv_files)
        return bool(intersections)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='CLI обновления программ MES')
    parser.add_argument(
        '--no-update',
        action='store_true',
        default=False,
        help='Отключает проврку обновления файлов клиента'
    )

    args = parser.parse_args()
    m = Main()
    m.push(no_update=args.no_update)
