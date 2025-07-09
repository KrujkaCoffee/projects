import datetime
import hashlib
import pathlib
import pickle
import re
import time
import tempfile
from typing import Callable

from PyQt5.QtCore import QSettings

from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_mes as CMS
from PyQt5 import QtCore

def cache_result(minutes: int, tmp_path: str = None):
    """
    Использование: @cache_results(minutes=120)

    Поведение: Кэширует результат функции на указанное кол-во минут
        Сохранение кэша: Если результат отсутствует запись в файл кэша не будет совершена
        Загрузка кэша: Если кэш каким-либо образом был загружен пустым/повредился/отчистился возвращаем стандартное
            поведение декорированной функции

    Если ошибка чтение/запись/хэширование аргументов:
        Оповещение ошибки в консоль + функция вызывается без кэширования не нарушая поведение программы

    Директория хранения:
        Кэш(tmp_path) хранится в папке ${TEMP} Windows
    """
    if tmp_path is None:
        tmp_path = tempfile.gettempdir()
    def wrap_fn(func):
        executor = F.name_of_executable_file_c()
        func_module = func.__module__
        func_name = func.__name__

        error_write = f"Cust_Functions.cache_results | Ошибка кэширования функции: {func_name!r} в путь: {tmp_path!r}"
        error_read = f"Cust_Functions.cache_results | Ошибка чтения кэша функции: {func_name!r} из пути: {tmp_path!r}"
        error_hash = f"Cust_Functions.cache_results | Ошибка хэширования аргументов: %s функции: {func_name!r} из пути: {tmp_path!r}"

        filename = f'{executor}.{func_module}.{func_name}.pickle'
        def wrapper(*args, **kwargs):
            now_stamp = time.time()
            try:
                binary_args = pickle.dumps((args, kwargs))
                hash_args = hashlib.md5(binary_args).hexdigest()
            except Exception as e:
                print(error_hash % f"args: {args} kwargs: {kwargs}")
                return func(*args, **kwargs)
            cache_path = pathlib.Path(tmp_path) / (hash_args + filename)
            if cache_path.exists() and now_stamp - cache_path.stat().st_mtime < minutes * 60:
                try:
                    cache = pickle.loads(cache_path.read_bytes())
                except Exception as e:
                    print(error_read)
                    return func(*args, **kwargs)
                if cache:
                    return cache
            result = func(*args, **kwargs)
            if result:
                try:
                    cache_path.write_bytes(pickle.dumps(result))
                except Exception as e:
                    print(error_write, e)
            return result
        return wrapper
    return wrap_fn


query = """
select *
from dolgn_etap de 
where datetime('2025-01-03 15:01:01') < (
	CASE 
		WHEN ДействуетДо IS NULL OR ДействуетДо = ''
		THEN datetime(CURRENT_TIMESTAMP) 
		ELSE datetime(ДействуетДо) 
	END
)
"""

# @cache_result(minutes=1)
def list_dolgn_etap(date_str: str, date_maska: str = '%y-%m-%d'):
    replace_null_date = """
    CASE 
        WHEN ДействуетДо IS NULL OR ДействуетДо = ''
        THEN datetime(CURRENT_TIMESTAMP) 
        ELSE datetime(ДействуетДо) 
    END
    """
    date_obj = F.strtodate(date_str, date_maska)
    query = f"""
    SELECT employee.ФИО, employee.Пномер, employee.Должность, employee.Подразделение, dolgn_etap.этап
    from employee
    LEFT JOIN (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY Должность, Подразделение, Производство 
                ORDER BY ({replace_null_date}) 
                ) as rowNumber
        FROM dolgn_etap
        where ({replace_null_date}) > datetime({date_obj.isoformat()!r}) 
    ) as dolgn_etap ON employee.Должность = dolgn_etap.Должность AND employee.Подразделение = dolgn_etap.Подразделение AND 
               employee.Компания = dolgn_etap.Производство AND rowNumber = 1
    """
    etaps = CSQ.custom_request_c(
        CFG.Config.project.db_naryad,
        query,
        attach_dbs=(CFG.Config.project.db_users,),
        rez_dict=True
    )
    return etaps

a = list_dolgn_etap('25-03-12')
print()

def etap_by_employee(date_str: str, fio_uuid_pk: str, date_maska: str = '%y-%m-%d'):
    patterns = {
        r'^[0-9]+$': 'Пномер',
        r'^[А-ЯЁа-яё]+\s[А-ЯЁа-яё]+\s[А-ЯЁа-яё]+$': 'ФИО',
        r'^[a-f0-9\-]{36}$': 'ID_ФизЛица'
    }
    value_str = str(fio_uuid_pk)
    key = None
    for pattern, description in patterns.items():
        if re.match(pattern, value_str.strip()):
            key = description
            break
    if key is None:
        return
    query = f"""
        SELECT e.ФИО, de.Должность, de.этап, de.ДействуетДо, e.ID_ФизЛица, e.Пномер
        FROM employee e
        LEFT JOIN dolgn_etap de ON de.Должность = e.Должность AND de.Подразделение = e.Подразделение AND de.Производство = e.Компания
    """
    etaps = CSQ.custom_request_c(
        CFG.Config.project.db_naryad,
        query,
        attach_dbs=(CFG.Config.project.db_users,),
        rez_dict=True
    )
    cur_employee = []
    for employee in etaps:
        if employee[key] == fio_uuid_pk:
            cur_employee.append(employee)
    target_obj = None
    date_mk = datetime.datetime.strptime(date_str, date_maska)
    for empl in cur_employee:
        end_etap = empl['ДействуетДо']
        if not target_obj and not end_etap:
            target_obj = empl
        elif end_etap and date_mk < datetime.datetime.strptime(end_etap, '%Y-%m-%d'):
            target_obj = empl
    return target_obj['этап']

b = F.now('cache_dolgn_etap_employee_test_%Y%m%d%p.pickle')
# CMS.save_tmp_path()
c = str
struct = [1,2,3,4]
d = CMS.load_tmp_path(b)

print()
# CMS.save_tmp_path()
# if c.exists():
#     F
a = etap_by_employee(fio_uuid_pk='Кудряшов Даниил Романович', date_str='2025-01-06', date_maska='%Y-%m-%d')
print()
#
# uuid_pattern = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
# fio_pattern = r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)'
# number_pattern = r'^([\d]+)$'
# input_string = "12345 123e4567-e89b-12d3-a456-426614174000"
#
# uuid_match = re.search(uuid_pattern, input_string)
# fio_match = re.search(fio_pattern, input_string)
# number_match = re.search(number_pattern, input_string)
#
#
#
# if fio_match:
#     print("Найдено ФИО:", fio_match.group(0))
# if number_match:
#     print("Найдено число:", number_match.group(0))
# if uuid_match:
#     print("Найден UUID:", uuid_match.group(0))
