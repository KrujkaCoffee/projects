import sys
import os
import logging
import zipfile
import importlib.util
from unittest.mock import patch

import requests

PROJECT_CUST = 'Z://'
CUST_API = 'http://mesinfo.powerz.ru:20011/files/project-cust/'
logging.basicConfig(level=logging.INFO)
EXTRACT_TO_DIRECTORY = os.path.join(PROJECT_CUST, 'project_cust_38')

def start(module):
    sys.path.append(PROJECT_CUST)
    logging.info('Загрузка project_cust_38...')
    response = requests.get(CUST_API)
    if not response.ok:
        logging.info('клиент не смог получить актуальную версию пакета "project-cust" из-за проблем на сервере')
        return
    logging.info(f'Распаковка...{EXTRACT_TO_DIRECTORY}')
    zip_file_path = "project_cust_38.zip"
    with open(zip_file_path, 'wb') as f:
        f.write(response.content)
    os.makedirs(EXTRACT_TO_DIRECTORY, exist_ok=True)
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(EXTRACT_TO_DIRECTORY)
    logging.info(f'Запуск {module}')

    os.remove(zip_file_path)
    logging.info('Подмена "project_cust_38.Cust_Functions.name_of_executable_file_c"...')
    with patch('project_cust_38.Cust_Functions.name_of_executable_file_c', return_value=f'{module}.py'):
        module = importlib.import_module(module)



if __name__ == '__main__':
    if len(sys.argv) > 1:
        start(sys.argv[1])
    else:
        logging.info('Введите имя модуля: server_runner.py Mkart')