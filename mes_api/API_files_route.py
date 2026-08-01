import hashlib
import logging
import os
import pathlib
import pickle
import shutil
import socket
import subprocess
import tarfile
import tempfile
import zipfile
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import api_srv_config
from project_cust_38 import Cust_Functions as F  # noqa: F401  # совместимость с текущей структурой проекта


router = APIRouter(prefix='/files', tags=['files'])

ZIP_SIZE_KEY = 'ZIP_SIZE_PATH'
PATH_NAME = 'py'
executor = pathlib.Path(r'C:\srv_mes\srv_mes') / 'interpreter' / 'py' / 'python.exe'
EXCLUDE_FOLDERS = {'.git', '__pycache__', '.idea', 'venv'}


def check_dns() -> bool:
    """Проверяет доступ к DNS."""
    try:
        socket.gethostbyname('www.google.com')
        return True
    except socket.gaierror:
        return False


def _iter_project_files(root_dir: str | pathlib.Path | None = None):
    root = pathlib.Path(root_dir or api_srv_config.DIRECTORY_TO_ARCHIVE)
    if not root.exists():
        return
    for abs_path, folders, filenames in os.walk(root):
        folders[:] = sorted(folder for folder in folders if folder not in EXCLUDE_FOLDERS)
        base_path = pathlib.Path(abs_path)
        for filename in sorted(filenames):
            file_path = base_path / filename
            if not file_path.is_file():
                continue
            relative_path = file_path.relative_to(root).as_posix()
            yield file_path, relative_path


def make_files_tree_struct() -> list[pathlib.Path]:
    return [file_path for file_path, _ in _iter_project_files() or []]


@router.get('/project-cust/')
async def download_project_cust_archive():
    if not os.path.isdir(api_srv_config.DIRECTORY_TO_ARCHIVE):
        raise HTTPException(status_code=404, detail='Сервер не смог найти папку project_cust_38')
    temp_dir = tempfile.mkdtemp()
    archive_path = os.path.join(temp_dir, api_srv_config.ARCHIVE_NAME)
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for item_path, relative_path in _iter_project_files() or []:
            archive.write(str(item_path), arcname=relative_path)
    return FileResponse(archive_path, media_type='application/zip', filename=api_srv_config.ARCHIVE_NAME)


@router.get('/project-cust/hash/')
async def download_project_cust_hash():
    hash_object = hashlib.sha256()
    dir_path = pathlib.Path(api_srv_config.DIRECTORY_TO_ARCHIVE)
    if dir_path.is_dir():
        for path, relative_path in _iter_project_files(dir_path) or []:
            hash_object.update(relative_path.encode('utf-8'))
            hash_object.update(b'\0')
            with path.open('rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    hash_object.update(chunk)
        return hash_object.hexdigest()
    raise HTTPException(status_code=404, detail='Сервер не смог найти папку project_cust_38')


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

def have_members(path: str):
    try:
        with tarfile.open(path, mode="r:gz") as tf:
            members = tf.getmembers()
            return len(members) > 0
    except Exception as e:
        logging.warning('[have_members] Ошибка', exc_info=e)
    return False


def download_and_archive_packages(packages: list[str]) -> str | None:
    """Скачиваем и архивируем указанные пакеты."""
    temp = pathlib.Path(tempfile.gettempdir()) / 'mes-packages'
    unique_finger = hashlib.sha256(json.dumps(packages, sort_keys=True).encode(encoding='utf8')).hexdigest()
    current_day = datetime.now().strftime('%d')
    folder = temp / f'{unique_finger}{current_day}'
    archive_name = f'packages.tar.gz'
    path = temp / folder / archive_name

    if path.exists() and have_members(str(path)):
        return str(path)
    else:
        if not check_dns():
            return
        folder.mkdir(exist_ok=True, parents=True)
        for package in packages:
            subprocess.run(['pip', 'download', package, '--no-cache-dir', '--only-binary=:all:'], cwd=str(folder), check=True)
        with tarfile.open(str(path), 'w:gz') as tar:
            for filename in os.listdir(str(folder)):
                tar.add(str(folder / filename), arcname=filename)
        return str(path)


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
            if temp_download is None:
                return
            return FileResponse(temp_download, filename=temp_download)
    except Exception as e:
        logging.warning('Ошибка выдачи pip зависимостей', exc_info=e)


@router.get('/py/')
async def download_python_archive():
    filepath = api_srv_config.FILES_PYTHON_INTERPRETER_PATH
    if os.path.exists(filepath):
        return FileResponse(filepath, filename='python.zip')
    return {'error': 'File not found'}


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
