import os
import tempfile
import zipfile
import pickle
import hashlib
import pathlib
import shutil
import tarfile
import subprocess
import logging
import socket

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import api_srv_config
from project_cust_38 import Cust_Functions as F



# router = APIRouter(prefix='/files', tags=['files'])
router = APIRouter(prefix='/files', tags=['files'])

ZIP_SIZE_KEY = 'ZIP_SIZE_PATH'
PATH_NAME = 'py'
executor = pathlib.Path(r'C:\srv_mes\srv_mes') / 'interpreter' / 'py' / 'python.exe'

def check_dns() -> bool:
    """Проверяет доступ к DNS."""
    try:
        socket.gethostbyname("www.google.com")
        return True
    except socket.gaierror:
        return False

def make_files_tree_struct() -> list[pathlib.Path]:
    exclude_folders = ('.git', '__pycache__', '.idea', 'venv')
    tree = []
    for abs_path, folders, filenames in os.walk(api_srv_config.DIRECTORY_TO_ARCHIVE):
        base_path = pathlib.Path(abs_path)
        if all(ex_path not in str(base_path) for ex_path in exclude_folders):
            for filename in filenames:
                tree.append(base_path / filename)
    return tree

@router.get("/project-cust/")
async def download_archive():
    if not os.path.isdir(api_srv_config.DIRECTORY_TO_ARCHIVE):
        raise HTTPException(status_code=404, detail="Сервер не смог найти папку project_cust_38")
    temp_dir = tempfile.mkdtemp()
    archive_path = os.path.join(temp_dir, api_srv_config.ARCHIVE_NAME)
    with zipfile.ZipFile(archive_path, 'w') as archive:
        for item_path in make_files_tree_struct():
            relative_path = os.path.relpath(str(item_path), 'project_cust_38')
            if item_path.is_file():
                archive.write(str(item_path), arcname=f'./{pathlib.Path(item_path).name}')
    return FileResponse(archive_path, media_type='application/zip', filename=api_srv_config.ARCHIVE_NAME)

@router.get("/project-cust/hash/")
async def download_archive():
    hash_object = hashlib.sha256()
    dir_path = pathlib.Path(api_srv_config.DIRECTORY_TO_ARCHIVE)
    if dir_path.is_dir():
        for path in make_files_tree_struct():
            with path.open('rb') as f:
                hash_object.update(f.read())
            hash_object.update(path.name.encode('utf-8'))
        return hash_object.hexdigest()

def get_installed_packages():
    """Получаем список установленных пакетов и их версий."""
    result = subprocess.run([str(executor), '-m', 'pip', 'freeze'], capture_output=True, text=True)
    if result.returncode == 0:
        libs = result.stdout.split()
        return libs

def get_py_size():
    py_path = str(executor.parent)
    return sum(
        os.path.getsize(os.path.join(dir_path, file))
        for dir_path, _, files in os.walk(str(py_path))
        for file in files
    )

def download_and_archive_packages(packages: list[str]) -> str:
    """Скачиваем и архивируем указанные пакеты."""
    archive_name = 'downloaded_packages.tar.gz'

    if not check_dns():
        return archive_name
    os.makedirs('temp_download', exist_ok=True)

    for package in packages:
        subprocess.run(['pip', 'download', package], cwd='temp_download', check=True)
    with open('temp_download/pack.pickle', 'wb+') as f:
        pickle.dump(packages, f)
    with tarfile.open(archive_name, "w:gz") as tar:
        for filename in os.listdir('temp_download'):
            tar.add(os.path.join('temp_download', filename), arcname=filename)
    shutil.rmtree('temp_download')
    return archive_name

@router.get('/py/packages/list/')
def get_list_srv_packages():
    if not executor.exists():
        logging.info(f'[/files/py] Не найден файл {executor.absolute()!r}')
        return {}
    return {'packages': get_installed_packages(), 'size': get_py_size()}


@router.post('/py/packages/')
def upload_dependencies(data: list[str]):
    """Маршрут для загрузки зависимостей и отправки недостающих."""
    try:
        if len(data) > 0:
            temp_download = download_and_archive_packages(data)
            return FileResponse(temp_download, filename=temp_download)
    except Exception as e:
        print(e)

@router.get('/py/')
async def download_file():
    filepath = api_srv_config.FILES_PYTHON_INTERPRETER_PATH
    if os.path.exists(filepath):
        return FileResponse(filepath, filename='python.zip')
    return {"error": "File not found"}

@router.get('/py/hash/')
async def get_py_lib_hash():
    """Возвращает актуальный хэш клиентских библиотек python"""
    if os.environ.get(ZIP_SIZE_KEY) and len(os.environ[ZIP_SIZE_KEY]) == 64:
        return os.environ[ZIP_SIZE_KEY]
    path = pathlib.Path(rf'C:\srv_mes\srv_mes') / 'interpreter' / 'lib_hash.pickle'
    if path.exists():
        with open(str(path), 'rb') as desc:
            actual_hash = pickle.load(desc)
            os.environ[ZIP_SIZE_KEY] = actual_hash
            return actual_hash
