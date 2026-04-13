import os
import re
import logging
import subprocess
import zipfile
import pickle
import tarfile
import io
import shutil
import tempfile
from typing import List
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO)

KEY_SRV_HASH = 'PROJECT_CUST_SRV_HASH'



class LoneInterpreter:
    def __init__(self):
        self.home_path = str(Path().home() / 'MES')
        from project_cust_38.Cust_client_socket import ip
        SRV_PORT = 20011
        self.server_url = f'http://{ip}:{SRV_PORT}/files'
        self.system_interpreter_path = r'Z:\Setup\python.zip'
        self.is_actual = self.check_python_available(self.python_path) and self.check_actual_interpreter()

        self.usr_hash = self.usr_packages = None

    @property
    def python_folder(self):
        py = shutil.which("python")
        if os.path.exists(py):
            return str(Path(py).parent.absolute())
        return str((Path(self.home_path) / 'py').absolute())

    @property
    def python_path(self):
        py = shutil.which("python")
        if os.path.exists(py):
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
        path = Path().home() / 'MES' / 'lib_hash.pickle'
        if not os.path.exists(self.python_path): return False
        # module_path = Path(__file__).parent
        # script_path = str(module_path / 'gen_hash.bat')
        # if not subprocess.run([script_path, self.python_path, str(module_path.absolute())], check=True, encoding='utf8'):
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
        return os.path.exists(self.python_path)
        # return self.__server_inter_size() == self.__main_inter_size()

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
        path = Path().home() / 'MES' / 'lib_hash.pickle'
        if not os.path.exists(self.python_path): return False
        # module_path = Path(__file__).parent
        # script_path = str(module_path / 'gen_hash.bat')
        # if not subprocess.run([script_path, self.python_path, str(module_path.absolute())], check=True, encoding='utf8'):
        if not subprocess.run([self.python_path, r'Z:\Setup\generate_hash.py'], check=True, encoding='utf8'):
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
                        script_folder = Path('Z:\Setup') / 'install_lib.bat'
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


if __name__ == '__main__':
    l = LoneInterpreter()
    python_path = l.python_path
    python_folder = l.python_folder
    libs = l.actualize_py_libs()
    print()