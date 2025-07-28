import copy
import datetime
import pathlib
import time
from datetime import datetime as DT, timedelta
import shutil
import os
import subprocess
import sys
import win32net
import win32api
import pickle
import traceback
import zlib
import colorsys
import re
import base64
import tempfile
from time import sleep as time_sleep
import ctypes
try:
    import config
    import pyperclip
    import json as js
    from jsonlines import open as jslopen
    import hashlib
    import calendar
    
    from win32com.client import Dispatch
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal, getcontext
except:
    pass

if __name__ == 's__main__':
    exit()

def decode_1c_data_version_attribute(base64_string: str):
    """Декодировать атрибут DataVersion 1С в число"""
    decoded_bytes = base64.b64decode(base64_string)
    result_integer = int.from_bytes(decoded_bytes, byteorder='big')
    return result_integer

def file_into_blob(pathf):
    if not existence_file_c(pathf):
        raise FileNotFoundError
    with open(pathf, 'rb') as file:
        return file.read()

def pack_byte_file(data):
    compressed_data = zlib.compress(data, zlib.Z_BEST_COMPRESSION)
    print(f"Оригинальный размер: {sys.getsizeof(data)}")
    # Оригинальный размер: 
    print(f"Сжатый размер: {sys.getsizeof(compressed_data)}")
    # Сжатый размер: 
    return compressed_data


def unpack_byte_file(data):
    decompressed_data = zlib.decompress(data)
    print(f"Сжатый размер: {sys.getsizeof(data)}")
    # Сжатый размер: 1024
    print(f"Распакованный размер: {sys.getsizeof(decompressed_data)}")
    # Распакованный размер: 1000033
    return decompressed_data


def clear_free_items(spis: list):
    if '' in spis:
        spis.remove('')
    return spis


def name_of_executable_file_c():
    tmp = os.path.abspath(sys.modules['__main__'].__file__).split(os.sep)[-1]
    return tmp

#++08.07.25
def cache_result(minutes: int, tmp_path: str = None):
    """
    Использование:
        @cache_results(minutes=120)
        def get_many_data():
            return []

    Поведение: Кэширует результат функции на указанное кол-во минут
        Сохранение кэша: Если результат отсутствует запись в файл кэша не будет совершена
        Загрузка кэша: Если кэш каким-либо образом был загружен пустым/повредился/отчистился

    Если ошибка чтение/запись/хэширование аргументов:
        Оповещение ошибки в консоль + функция вызывается без кэширования не нарушая поведение программы

    Директория хранения:
        Кэш(tmp_path) хранится в папке ${TEMP} Windows
    """
    if tmp_path is None:
        tmp_path = tempfile.gettempdir()
    def wrap_fn(func):
        executor = name_of_executable_file_c()
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
#-- 08.07.25

def path_to_execut_file_c():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the pyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable _MEIPASS'.
        # application_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        return (os.path.dirname(sys.executable) + os.sep)
        # print(os.getcwd())
    else:
        os.path.abspath(sys.modules['__main__'].__file__)
        tmp = os.path.abspath(sys.modules['__main__'].__file__).split(os.sep)
        tmp.pop()
        return os.sep.join(tmp) + os.sep


def is_frozen():
    if getattr(sys, 'frozen', False):
        return True
    return False


def existence_file_c(putf):
    putf = os.path.normpath(putf)
    return os.path.exists(putf)


def cfg_dict():
    return cfg.as_dict()


def load_cfg(log=True):
    try:
        print('======Загрузка настроек ' + path_to_execut_file_c() + '======') if log else None
        put_conf = path_to_execut_file_c() + 'Config' + os.sep + 'CFG.cfg'
        if existence_file_c(put_conf) == True:
            try:
                cfg = config.Config(put_conf)
                print(f'    {put_conf}', end='\n') if log else None  # файл конфига, находится п папке конфиг
            except:
                print(f'    Не корректный файл {put_conf} формат должен быть без спецификации') if log else None
                return
            tmp_dict = dict()
            cfg_dict = cfg.as_dict()
            for key in cfg_dict.keys():
                list_path = cfg_dict[key].split(';')
                if len(list_path) > 1:
                    fl = False
                    for path in list_path:
                        if existence_file_c(path):
                            tmp_dict[key] = path
                            print(f'        Для {key} принят {path}') if log else None
                            fl = True
                            break
                        else:
                            pass
                            ## Если не сработало, пытаемся активировать диск
                            #if path.startswith('\\\\'):
                            #    # Для UNC-путей (\\server\share)
                            #    try:
                            #        # Создаем временный файловый дескриптор
                            #        with open(os.path.join(path, 'dummy.txt'), 'w') as f:
                            #            pass
                            #        os.remove(os.path.join(path, 'dummy.txt'))
                            #        return True
                            #    except:
                            #        pass
                            #
                            ## Для буквенных дисков (Z:\)
                            #elif ':' in path:
                            #    drive = path.split(':')[0] + ':'
                            #    try:
                            #        ctypes.windll.kernel32.SetErrorMode(0x8007)
                            #        ctypes.windll.kernel32.GetDiskFreeSpaceExW(drive, None, None, None)
                            #        time.sleep(1)  # Даем время на инициализацию
                            #        return os.path.exists(path)
                            #    except:
                            #        pass
                            #if existence_file_c(path):
                            #    tmp_dict[key] = path
                            #    print(f'        Для {key} принят {path}') if log else None
                            #    fl = True
                            #    break
                            
                    if fl == False:
                        print(f'    Не верный путь для {key}') if log else None
                        return
                else:
                    print(f'    {cfg_dict[key]}') if log else None
                    tmp_dict[key] = cfg_dict[key]
            print('=====Успешно=====') if log else None
            return tmp_dict
        else:
            print(f'    Файл настроек не найден по {put_conf}') if log else None
    except:
        print(f'    Не открыть файл CFG.cfg') if log else None
        return


cfg = load_cfg()


def tcfg(put_i_ima):
    try:
        return cfg[put_i_ima] + os.sep + put_i_ima + '.txt'
    except:
        print('Не найден ' + put_i_ima + ' в cfg')
        return ''


def pcfg(put_i_ima):
    try:
        return cfg[put_i_ima] + os.sep + put_i_ima + '.picle'
    except:
        print('Не найден ' + put_i_ima + ' в cfg')
        return ''


def bdcfg(imaf):
    try:
        put = os.path.normpath(cfg[imaf] + os.sep + imaf + '.db')
        if "SRV:" in put:
            return put
        if existence_file_c(put):
            return put
        else:
            print('Не найден ' + imaf + ' в cfg')
            return put
    except:
        print('Не найден ' + imaf + ' в cfg')
        return


def alfabet_to_number(letters: str) -> int:
    dictionary = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8, 'i': 9, 'j': 10, 'k': 11, 'l': 12,
                  'm': 13, 'n': 14, 'o': 15, 'p': 16, 'q': 17, 'r': 18, 's': 19, 't': 20, 'u': 21, 'v': 22, 'w': 23,
                  'x': 24, 'y': 25, 'z': 26}
    sum = 0
    for letter in letters:
        sum += dictionary[letter.lower()]
    return sum


def scientific_to_decimal_str(number) -> str:
    """
    Преобразует число из научной нотации (1.23e-5) в строку без 'e' (0.0000123).

    Параметры:
        number: число (int, float) или строка в формате "1.23e-5".

    Возвращает:
        Строковое представление числа без экспоненты.

    Пример:
        >>> scientific_to_decimal_str(1.23e-5)
        '0.0000123'
        >>> scientific_to_decimal_str("2.5e-8")
        '0.000000025'
    """
    # Устанавливаем достаточную точность для Decimal
    getcontext().prec = 28  # Стандартная точность Decimal (можно увеличить)

    # Если на входе строка, преобразуем её в Decimal
    if isinstance(number, str):
        try:
            num_decimal = Decimal(number)
        except:
            raise ValueError(f"Некорректный формат числа: '{number}'")
    # Если на входе число (int/float), сначала преобразуем в строку, чтобы избежать потерь точности
    else:
        num_decimal = Decimal(str(number))

    # Преобразуем Decimal в строку и убираем лишние нули
    result = format(num_decimal, 'f').rstrip('0').rstrip('.') if '.' in format(num_decimal, 'f') else format(
        num_decimal, 'f')

    return result

def scfg(put_bez_im):
    try:
        return cfg[put_bez_im]
    except:
        print('Не найден ' + put_bez_im + ' в cfg')
        return ''


def capital_letter_c(stroka):
    return stroka[0].upper() + stroka[1:]

def is_debug():
    gettrace = getattr(sys, 'gettrace', None)
    if gettrace is None:
        print('No sys.gettrace')
        return False
    else:
        v = gettrace()
        if v is None:
            return False
        else:
            return True

def open_dir_c(put):
    try:
        put = os.path.normpath(put)
        os.startfile(put)
    except:
        print('ОШибка Cust_Functions open_dir_c')


def run_file_c(putf, proverka=True):
    putf = os.path.normpath(putf)
    if proverka == True:
        if existence_file_c(putf) == False:
            return
    subprocess.Popen(putf, shell=True)


def run_file_os_c(putf,normalize=True):
    if normalize:
        putf = os.path.normpath(putf)
    os.startfile(putf)

def is_link_like(text: str):
    if isinstance(text, str) and (os.sep in text or '//' in text):
        return True
    return False

def run_vbs_c(putf):
    # putf = os.path.normpath(putf)
    os.system(putf)

def is_link_dir(put):
    put = os.path.normpath(put)
    if isinstance(put, str) and fr'e1c:\server' in put:
        return True
    if isinstance(put, str) and (os.sep in put or '//' in put or r'\\' in put):
        if os.path.isdir(put) or os.path.islink(put) or put.startswith(r'docs:') or put.startswith(
            'http:') or put.startswith(r'\\') or put.startswith(r'e1c:\server'):
            return True
    return False

def is_link_file(putf):
    put = os.path.normpath(putf)
    if is_link_like(put):
        if os.path.isfile(put):
            return True
    return False
    
def check_for_russian(string):
    alphabet = ["а", "б", "в", "г", "д", "е", "ё", "ж", "з", "и", "й", "к", "л", "м", "н", "о", "п", "р", "с", "т", "у",
                "ф", "х", "ц", "ч", "ш", "щ", "ъ", "ы", "ь", "э", "ю", "я"]
    for one_char in string:
        if one_char in alphabet:
            return True
    return False


def transliterate(name):
    """
    Не претендую на "хорошесть" словарика. В моем случае и такой пойдет,
    вы всегда сможете добавить свои символы и даже слова. Только
    это нужно делать в обоих списках, иначе будет ошибка.
    """
    # Слоаврь с заменами
    slov = {"а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "е": "e",
            "ё": "yo",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "й": "j",
            "к": "k",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ф": "f",
            "х": "h",
            "ц": "cz",
            "ч": "ch",
            "ш": "sh",
            "щ": "shh",
            "ъ": "``",
            "ы": "y`",
            "ь": "`",
            "э": "e`",
            "ю": "yu",
            "я": "ya"
            }

    # Циклически заменяем все буквы в строке
    for key in slov:
        name = name.replace(key.lower(), slov[key])
        name = name.replace(key.upper(), slov[key])
    return name


def ochist_papky(top):
    if (top == '/' or top == "\\"):
        return
    else:
        try:
            for root, dirs, files in os.walk(top, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
        except:
            return


def copy_file_c(putf, putf2):
    putf2 = os.path.normpath(putf2)
    putf = os.path.normpath(putf)
    arr = putf2.split(os.sep)
    imaf2 = str(arr[-1])
    fold2 = putf2.replace(imaf2, '')
    if existence_file_c(fold2) == False:
        create_dir_c(fold2)
    if existence_file_c(putf) == True:
        try:
            shutil.copyfile(putf, putf2)
            return True
        except:
            return False
    return False


def copytree(src, dst, symlinks=False, ignore=None):
    """Copy data from src to dst in the most efficient way possible.
        """
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)

        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                try:
                    shutil.copy2(s, d)
                except:
                    print(f'ошибка копирования {d}')


def delete_file_c(putf):
    putf = os.path.normpath(putf)
    if existence_file_c(putf) == True:
        os.remove(putf)


def delete_dir_c(putp):
    putp = os.path.normpath(putp)
    if existence_file_c(putp) == True:
        shutil.rmtree(putp, ignore_errors=True)


def rename_file_c(putf1, putf2):
    putf1 = os.path.normpath(putf1)
    putf2 = os.path.normpath(putf2)
    if existence_file_c(putf1) == True:
        shutil.move(putf1, putf2)
        return True
    return False


def create_dir_c(putt):
    try:
        os.makedirs(putt)
        return True
    except:
        print(f'PermissionError: [WinError 5] Отказано в доступе: {putt}')
        return False


def load_file(putima, sep='|'):
    if putima == '':
        return ['']
    if existence_file_c(putima) == False:
        print(f'Не найден файл {putima}')
        return False
    with open(putima, 'r', encoding='utf-8-sig', errors='ignore') as f:
        Stroki = f.readlines()
    for i in range(0, len(Stroki)):
        Stroki[i] = Stroki[i].replace('\n', '')
        if sep in Stroki[i]:
            Stroki[i] = Stroki[i].split(sep)
    if len(Stroki) == 0:
        return ''
    if len(Stroki) == 1:
        return Stroki[0]
    return Stroki


def open_file_c(putima, utf8=False, separ='', pickl=False, propuski=False):
    if putima == '':
        return ['']
    flag = 0
    if pickl == True:
        if existence_file_c(putima.replace('.txt', '.pickle')) == True:
            putima = putima.replace('.txt', '.pickle')
            flag = 1
        else:
            if existence_file_c(putima.replace('.pickle', '.txt')) == True:
                putima = putima.replace('.pickle', '.txt')
                flag = 2
            else:
                return ['']
    else:
        if existence_file_c(putima.replace('.pickle', '.txt')) == True:
            putima = putima.replace('.pickle', '.txt')
            flag = 2
        else:
            if existence_file_c(putima.replace('.txt', '.pickle')) == True:
                putima = putima.replace('.txt', '.pickle')
                flag = 1
            else:
                return ['']
    if flag == 0:
        return ['']
    if flag == 1:
        try:
            with open(putima, 'rb') as f:
                Stroki = pickle.load(f)
        except:
            return
        if separ != '':
            for i in range(0, len(Stroki)):
                Stroki[i] = Stroki[i].split(separ)
        return Stroki
    else:
        if utf8 == True:
            with open(putima, 'r', encoding='utf-8-sig', errors='ignore') as f:
                Stroki = f.readlines()
        else:
            with open(putima, 'r', encoding='cp1251', errors='replace') as f:
                Stroki = f.readlines()
        Stroki2 = []
        if propuski == False:
            if len(Stroki) > 1:
                for i in range(len(Stroki)):
                    if Stroki[i] != '\n':
                        Stroki2.append(Stroki[i])
                Stroki = Stroki2
        for i in range(0, len(Stroki)):
            Stroki[i] = Stroki[i].replace('\n', '')
            if separ != '':
                Stroki[i] = Stroki[i].split(separ)
        return Stroki


def transpose_c(spis, nom_kol=None, unikaln=False, hat_c=True):
    rez = []
    nach = 1 if hat_c else 0
    for i in range(nach, len(spis)):
        if len(spis[i]) - 1 >= nom_kol:
            rez.append(spis[i][nom_kol])
    if unikaln:
        rez = list(set(rez))
    return rez

def transpose_list_of_lists(list_list:list):
    return [list(i) for i in zip(*list_list)]

def save_tmp_win_dir_file(file_bytes:bytes,extention:str=None):
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=extention)
    tmpfile.write(file_bytes)
    tmpfile.close()
    temp_file_name = tmpfile.name
    return temp_file_name

def dir_workdesc_c():
    if existence_file_c(os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')):
        return os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
    else:
        return os.path.join(os.path.join(os.path.expanduser('~')), f'Work folders{sep()}Desktop')


def create_label_c(file, dir, ima_yar, put_ico=''):
    # os.symlink(file, dir)
    path = dir + sep() + ima_yar + '.lnk'  # Path to be saved (shortcut)
    target = file  # The shortcut target file or folder
    work_dir = sep().join(file.split(sep())[:-1])  # The parent folder of your file

    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = target
    shortcut.WorkingDirectory = work_dir
    if put_ico != '':
        shortcut.IconLocation = f"{put_ico},0"
    shortcut.save()


def save_file_pickle(putima, obj):
    with open(putima, 'wb') as f:
        pickle.dump(obj, f)


def to_binary_pickle(obj):
    return pickle.dumps(obj)


def from_binary_pickle(blob):
    try:
        return pickle.loads(blob)
    except:
        print('Не корректные данные from_binary_pickle')
        return


def load_file_pickle(putima):
    try:
        with open(putima, 'rb') as f:
            return pickle.load(f)
    except pickle.UnpicklingError as e:
        print(f'Ошибка десериализации файла: {putima!r}\n {e}')


def round_up(n, digit=0):
    koef = 10 ** (digit)
    n *= koef
    if n % 1 > 0:
        return (n // 1 + 1) / koef
    else:
        return n / koef


def generate_exel_copy_notation_text(spis):
    rez = []
    for i in range(len(spis)):
        for j in range(len(spis[0])):
            if is_numeric(spis[i][j]):
                spis[i][j] = str(spis[i][j])
            spis[i][j] = spis[i][j].replace('\t', '')
            spis[i][j] = spis[i][j].replace('\n', '')
            if is_numeric(spis[i][j]):
                spis[i][j] = spis[i][j].replace('.', ',')
        rez.append('\t'.join(spis[i]))
    return '\n'.join(rez)

def copy_bufer_list(spis):
    rez = generate_exel_copy_notation_text(spis)
    copy_bufer(rez)

def save_file(putima, obj_str, utf=True,sep='|',copy_bufer=False):
    c_encoding = 'utf-8'
    if utf == False:
        c_encoding = 'cp1251'
    if existence_file_c(os.sep.join(putima.split(os.sep)[:-1])) == False:
        print(f'НЕ НАЙДЕНА ПАПКА {os.sep.join(putima.split(os.sep)[:-1])}')
        return False
    if type(obj_str) is type(''):
        with open(putima, 'w', encoding=c_encoding, errors='ignore') as f:
            f.write(obj_str + "\n")
    else:
        for i in range(2):
            try:
                with open(putima, 'w', encoding=c_encoding, errors='ignore') as f:
                    for item in obj_str:
                        if type(item) is type(''):
                            f.write(str(item) + "\n")
                        elif isinstance(item, int) or isinstance(item, float):
                            f.write(str(item) + "\n")
                        else:
                            for i in range(len(item)):
                                item[i] = str(item[i])
                            f.write(sep.join(item) + "\n")
                if copy_bufer:
                    copy_bufer_list(obj_str)
                return
            except:
                print(f'save_file err')
                #sleep(0.2)
        

def write_file_c(putima, spisok, separ='', pickl=False, utf8=False):
    if existence_file_c(os.sep.join(putima.split(os.sep)[:-1])) == False:
        print('НЕ НАЙДЕНА ПАПКА')
        return False
    if pickl == False:
        if utf8 == True:
            with open(putima, 'w', encoding='utf-8', errors='ignore') as f:
                for item in spisok:

                    if separ == '':
                        f.write(item + "\n")
                    else:
                        for i in range(len(item)):
                            item[i] = str(item[i])
                        f.write(separ.join(item) + "\n")
        else:
            with open(putima, 'w', errors='ignore') as f:
                for item in spisok:
                    if separ == '':
                        f.write(item + "\n")
                    else:
                        if type(item) == list:
                            for i in range(len(item)):
                                item[i] = str(item[i])
                            f.write(separ.join(item) + "\n")
                        else:
                            f.write(item + "\n")
    else:
        putima = putima.replace('.txt', '.pickle')
        if separ != '':
            spisok2 = []
            for item in spisok:
                if type(item) == list:
                    for i in range(len(item)):
                        item[i] = str(item[i])
                    spisok2.append(separ.join(item))
                else:
                    spisok2.append(item)
            spisok = spisok2
        with open(putima, 'wb') as f:
            pickle.dump(spisok, f)


def user_full_namre():
    try:
        NetGetAnyDCName = win32net.NetGetAnyDCName()
    except:
        print('user_full_namre error get NetGetAnyDCName')
        return None
    user_info = win32net.NetUserGetInfo(NetGetAnyDCName, win32api.GetUserName(), 2)
    full_name = user_info["full_name"]
    return full_name


def user_name():
    return os.environ.get("USERNAME")

def computer_name():
    return os.environ.get('COMPUTERNAME')

def now(format="%Y-%m-%d %H:%M:%S"):
    """ use format = '' for return DT.today()"""
    if format == '':
        return DT.today()
    return DT.today().strftime(format)


def strtodateold(str, format="%d.%m.%Y %H:%M:%S"):
    if len(format) > 11:
        if len(str) < 11:
            str += ' 00:00:00'
    return DT.strptime(str, format)


def strtodate(str, format="%Y-%m-%d %H:%M:%S"):#"%d.%m.%Y"   "%Y-%m-%dT%H:%M:%S"
    if len(format) > 11:
        if len(str) < 11:
            str += ' 00:00:00'
    return DT.strptime(str, format)


def date_to_datetime(
        dt,
        hour: int = 0,
        minute: int = 0,
        second: int = 0):
    return DT(dt.year, dt.month, dt.day, hour, minute, second)

def miutes_to_time(minutes:float):
    dt =timedelta(minutes=minutes)
    if dt.microseconds > 0:
        dt -= timedelta(microseconds=dt.microseconds)
    return str(dt).replace('day', 'суток')

def datetime_to_date(datetime_dt):
    return datetime_dt.date()

def is_date(string: str, maska: str = "%Y-%m-%d %H:%M:%S"):
    # "%d.%m.%Y"
    try:
        DT.strptime(string, maska).date()
    except:
        return False
    return True

def datetostr(date, format="%Y-%m-%d %H:%M:%S"):#"%d.%m.%Y"   "%Y-%m-%dT%H:%M:%S"
    return date.strftime(format)


def month_rus_from_date(date, format="%Y-%m-%d %H:%M:%S", rodit_padej=True):
    month_list_rod = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                      'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    month_list_imen = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                       'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
    if type(date) == str:
        date = strtodate(date, format=format)
    month = date.month - 1
    if rodit_padej:
        return month_list_rod[month]
    else:
        return month_list_imen[month]
    
def date_from_month_rus(month_str, rodit_padej=True) -> int:
    month_list_rod = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                      'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    month_list_imen = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                       'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
    if rodit_padej:
        num_month = month_list_rod.index(month_str)+1
    else:
        num_month = month_list_imen.index(month_str)+1
    return num_month


def fromdateshtamp(shtamp: float, format="%Y-%m-%d %H:%M:%S"):
    if format == '':
        return DT.fromtimestamp(shtamp)
    return datetostr(DT.fromtimestamp(shtamp), format)


def shtamp_from_date(date: str, format="%Y-%m-%d %H:%M:%S"):
    if format == '':
        return DT.timestamp(date)
    return DT.timestamp(strtodate(date, format))


def date_add_time(date, time: str = '', format_time="%H:%M", hours: int = 0, minutes: int = 0):
    # date в DT либо time с формато либо hours:int=0,minutes:int=0
    if time != '':
        hours += DT.strptime(time, format_time).hour
        minutes += DT.strptime(time, format_time).minute
    date += timedelta(hours=hours, minutes=minutes)
    return date

def delta_days(date1,date2,only_work_days=False):
    if not only_work_days:
        return date2 - date1
    else:
        daygenerator = (date1 + timedelta(x + 1) for x in range((date2 - date1).days)) # generate all days from d1 to d2
    return timedelta(days= sum(1 for day in daygenerator if day.weekday() < 5)) 

def add_days(date1:datetime.datetime,time_delta:timedelta,only_work_days=False):
    if not only_work_days:
        return date1 + time_delta
    else:
        days = 0
        new_date = copy.deepcopy(date1)
        while True:
            if days == time_delta.days:
                break
            try:
                if time_delta.days <=0:
                    new_date = new_date - timedelta(1)
                else:
                    new_date = new_date + timedelta(1)
            except:
                print(f'err')
                return new_date
            
            if new_date.weekday() >= 5:
                continue
            if time_delta.days <= 0:
                days -= 1
            else:
                days += 1
        return new_date


def add_months(sourcedate:datetime.datetime, months: int):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return DT(year, month, day)


def date_add_days(date: str, days, format="%Y-%m-%d %H:%M:%S", format_out="%Y-%m-%d %H:%M:%S"):
    if type(date) == type(" "):
        date = strtodate(date, format=format)
    rez = date + timedelta(days=days)
    if format_out == '':
        return rez
    else:
        return datetostr(rez, format_out)


def start_end_dates_c(date: str = now(), format_in="%Y-%m-%d %H:%M:%S", vid: str = 'y', format_out="%Y-%m-%d %H:%M:%S"):
    """y,m,n,d"""
    if format_in == '':
        today = date
    else:
        today = strtodate(date, format_in)
    if vid == 'y':
        nach = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        out = nach, nach + relativedelta(years=1) - timedelta(seconds=1)
    if vid == 'm':
        nach = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        out = nach, nach + relativedelta(months=1) - timedelta(seconds=1)
    if vid == 'n':
        monday = today - timedelta(DT.weekday(today))
        nach = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        out = nach, nach + timedelta(days=7) - timedelta(seconds=1)
    if vid == 'd':
        nach = today.replace(hour=0, minute=0, second=0, microsecond=0)
        out = nach, nach + timedelta(days=1) - timedelta(seconds=1)
    if format_out == '':
        return out
    else:
        return datetostr(out[0], format_out), datetostr(out[1], format_out)


def date(god=2, vid: str = '', maska: str = "%Y-%m-%d"):
    if vid == 'd':
        return DT.today().strftime("%d")
    if vid == 'm':
        return DT.today().strftime("%m")
    if vid == 'yy':
        return DT.today().strftime("%y")
    if vid == 'yyyy':
        return DT.today().strftime("%Y")
    if god == 4:
        return DT.today().strftime(maska.replace('%y', '%Y'))
    else:
        return DT.today().strftime(maska.replace('%Y', '%y'))


def get_time_shtamp_c():
    return DT.timestamp(DT.today())


def clear_row_for_separ_c(stroka):
    tmp = stroka.replace("$", "&")
    tmp = tmp.replace("|", "L")
    tmp = tmp.replace("{", "[")
    tmp = tmp.replace("}", "]")
    return tmp

def clear_str_ntrs(text:str):
    return text.replace("\n", "").replace("\t", "").replace("\r", "").strip()

def clear_row_for_file_name_c(stroka):
    tmp = stroka.replace("/", "-")
    tmp = tmp.replace("\\", "-")
    tmp = tmp.replace("\n", "-")
    tmp = tmp.replace("\t", "")
    tmp = tmp.replace("\r", "")
    tmp = tmp.replace("/", "-")
    tmp = tmp.replace("$", "-")
    tmp = tmp.replace("*", "-")
    # tmp = tmp.replace("_", "-")
    tmp = tmp.replace(":", "-")
    tmp = tmp.replace("?", "-")
    tmp = tmp.replace("|", "I")
    tmp = tmp.replace("!", "I")
    tmp = tmp.replace('"', "")
    tmp = tmp.replace(">", ")")
    tmp = tmp.replace("<", "(")
    tmp = tmp.replace("~", "-")
    tmp = tmp.replace("`", "-")
    tmp = tmp.replace("'", "-")
    tmp = tmp.replace("×", "x")
    tmp = tmp.strip()
    return tmp


def list_txt_table_c(spis):
    spis_max = []
    for kol in range(len(spis[0])):
        max = 0
        for st in range(len(spis)):
            spis[st][kol] = spis[st][kol].replace('\n', ' ')
            spis[st][kol] = str(spis[st][kol])
            if len(spis[st][kol]) > max:
                max = len(spis[st][kol])+2
        spis_max.append('-' * max)
        for st in range(len(spis)):
            num_space = max - len(spis[st][kol])
            spis[st][kol] = ' ' + spis[st][kol]
            spis[st][kol] += ' ' * (num_space-1)
    rez = []
    sep = "+".join(spis_max)
    for st in range(len(spis)):
        rez.append('|'.join(spis[st]))
        rez.append(sep)
    return rez


def is_bool(string: str):
    if string.lower() in {'true','false','0','1'}:
        return True
    return False

def is_numeric(string: str):
    if type(string) == type(1.1):
        return True
    if type(string) == type(2):
        return True
    try:
        string = string.replace(',', '.')
    except:
        return False
    if string.isdigit():
        return True
    else:
        try:
            float(string)
            return True
        except ValueError:
            return False


def inscribe_c(slovo, zn, levz=':', prz=':', orient=1):
    if type(slovo) == type([]):
        slovo = ' '.join(slovo)
    if slovo == '':
        slovo = ' ' * (zn - 2)
    if len(slovo) + 2 > zn:
        zn = len(slovo) + 2
    prob = zn - 2 - len(slovo)
    k = 0
    if prob % 2 > 0:
        k = 1
    if orient == 0:
        strok = levz + slovo + (prob // 2 + prob // 2 + k) * ' ' + prz
    if orient == 1:
        strok = levz + (prob // 2) * ' ' + slovo + (prob // 2 + k) * " " + prz
    if orient == 2:
        strok = levz + (prob // 2 + prob // 2 + k) * ' ' + slovo + prz

    return strok


def sort_by_column_c(list_of_lists, name_kol, revers=False, date_time=False, date_format="%Y-%m-%d %H:%M:%S", hat_c=True, type_compare=None):
    """type_compare 'numeric'/'str' """
    if not list_of_lists:
        return list_of_lists
    dict_type =False
    if type(list_of_lists[0]) == type(dict()):
        dict_type = True
        body = list_of_lists
        nk = name_kol
    else:
        if hat_c:
            hat = list_of_lists[0]
            body = list_of_lists[1:]
            nk = num_col_by_name_in_hat_c(list_of_lists, name_kol)
        else:
            body = list_of_lists
            nk = name_kol
    if date_time:
        body = sorted(body, key=lambda x: strtodate(x[nk], date_format) if is_date(x[nk], date_format) else strtodate(
            "20.11.2001", "%d.%m.%Y"), reverse=revers)
    else:
        if len(body) >= 1:
            if isinstance(body[0][nk],int) or isinstance(body[0][nk],float) or type_compare == 'numeric':
                body = sorted(body, key=lambda x: x[nk] if x[nk] != '' else 0, reverse=False)
            else:
                if isinstance(body[0][nk],str) or type_compare == 'str':
                    body = sorted(body, key=lambda x: x[nk] if x[nk] != '' else '', reverse=False)
    if not dict_type:
        if hat_c:
            body.insert(0, hat)
    return body


def find_in_txt_c(putima, chto, ish_kol, vih_kol, separ=''):
    if existence_file_c(putima) == False:
        return
    if type(chto) == type([]):
        chto = chto[0]
    sp = open_file_c(putima, separ=separ)
    for i in range(0, len(sp)):
        if sp[i][ish_kol] == chto:
            return sp[i][vih_kol]
    return


def find_in_list_c(sp, vih_kol='', *chto):
    for i in range(0, len(sp)):
        flag = 1
        for j in chto:
            if j not in sp[i]:
                flag = 0
                break
        if flag == 1:
            if vih_kol == '':
                return i
            else:
                return sp[i][vih_kol]
    return None


def delete_column(spis: list, names_del: list = [], numbers_del: list = []) -> list:
    if names_del != []:
        numbers_del = []
        for name in names_del:
            nk = num_col_by_name_in_hat_c(spis, name)
            if nk == None:
                print(f'не найдена колонка {name}')
            else:
                numbers_del.append(nk)
    numbers_del = sorted(numbers_del, reverse=True)
    for row in spis:
        for col in numbers_del:
            del row[col]
    return spis

    return spis


def dict_key_from_value(dic: dict, val):
    for name, age in dic.items():  # for name, age in dictionary.iteritems():  (for Python 2.x)
        if age == val:
            return name


def list_to_dict(list_of_lists, key_to_dict=''):
    '''Если ключ = пусто то список словарей, если нет то словарь словарей по ключу'''
    if key_to_dict == '':
        rez = []
        hat_c = list_of_lists[0]
        for i in range(1, len(list_of_lists)):
            tmp = dict()
            for j in range(len(hat_c)):
                tmp[hat_c[j]] = list_of_lists[i][j]
            rez.append(tmp)
        return rez
    else:

        rez = dict()
        hat_c = list_of_lists[0]
        for i in range(1, len(list_of_lists)):
            tmp = dict()
            if type(key_to_dict) == str:
                for j in range(len(hat_c)):
                    tmp[hat_c[j]] = list_of_lists[i][j]
                if key_to_dict in tmp:
                    rez[tmp[key_to_dict]] = tmp
                else:
                    print(f'list_to_dict {key_to_dict} не найден в строке')
            else:
                tmp = list_of_lists[i]
                if len(tmp) < key_to_dict:
                    print(f'list_to_dict {key_to_dict} превышает длину')
                else:
                    rez[list_of_lists[i][key_to_dict]] = tmp
        return rez


def dict_to_list(dicton: dict, transponir=False):
    '''словарь в спискок в две колонки'''
    if transponir:
        roof = []
        body = []
        for key in dicton.keys():
            roof.append(key)

        for key in roof:
            body.append(dicton[key])
        rez = [roof, body]

    else:
        rez = [[key, dicton[key]] for key in dicton]
    return rez


def list_of_dicts_to_list_of_lists(list_of_dicts: list):
    list_keys = []
    for item in list_of_dicts:
        if isinstance(item,list):
            return list_of_dicts
        for key in item.keys():
            if key not in list_keys:
                list_keys.append(key)

    rez = [list_keys]
    for item in list_of_dicts:
        tmp = []
        for key in list_keys:
            if key in item:
                tmp.append(item[key])
            else:
                tmp.append('')
        rez.append(tmp)
    return rez


def list_of_lists_to_list_of_dicts(list_of_lists: list):
    rez = []
    for i in range(1, len(list_of_lists)):
        tmp = dict()
        for j in range(len(list_of_lists[0])):
            tmp[list_of_lists[0][j]] = list_of_lists[i][j]
        rez.append(tmp)
    return rez


def list_of_lists_to_dict_of_dicts(list_of_lists: list, field_name: str):
    # НАдо исправить
    rez = dict()
    for i in range(1, len(list_of_lists)):
        tmp = dict()
        for j in range(len(list_of_lists[0])):
            tmp[list_of_lists[0][j]] = list_of_lists[i][j]
        rez[tmp[field_name]] = tmp
    return rez


def dict_of_dicts_to_list_of_lists(dict_of_dicts: dict, name_first_column='Список'):
    list_keys = [name_first_column]
    for key in dict_of_dicts.keys():
        for key2 in dict_of_dicts[key].keys():
            if key2 not in list_keys:
                list_keys.append(key2)

    rez = [list_keys]
    for key in dict_of_dicts.keys():
        tmp = [key]
        for key2 in list_keys:
            if key2 != name_first_column:
                if key2 in dict_of_dicts[key]:
                    tmp.append(dict_of_dicts[key][key2])
                else:
                    tmp.append('')
        rez.append(tmp)
    return rez


def deploy_dict_c(list_dicts: list, name_key_column: str):
    '''список словарей в словарь словарей по ключу. ключ не вкладывается на 2 уровень'''
    if list_dicts == None or list_dicts == False:
        return False
    rez = dict()
    for dic in list_dicts:
        if type(dic) == type(dict()):
            if name_key_column in dic:
                if len(dic.keys()) == 2:
                    val = ''
                    for key in dic.keys():
                        if key != name_key_column:
                            val = dic[key]
                            break
                else:
                    val = dict()
                    for key in dic.keys():
                        if key != name_key_column:
                            val[key] = dic[key]
                rez[dic[name_key_column]] = val
    return rez


def get_key_index_dict(dictionary, target_key):
    """
    Возвращает порядковый номер (индекс) ключа в словаре.

    :param dictionary: Словарь для поиска
    :param target_key: Ключ, индекс которого нужно найти
    :return: Индекс ключа (начиная с 0) или None если ключ не найден
    """
    for index, key in enumerate(dictionary.keys()):
        if key == target_key:
            return index
    return None

def insert_key_to_dicts(list_of_dicts, insert_index, new_key, default_value=None):
    """
    Вставляет новый ключ в указанную позицию каждого словаря в списке.

    :param list_of_dicts: Список словарей для модификации
    :param insert_index: Позиция, на которую нужно вставить новый ключ (начиная с 0)
    :param new_key: Имя нового ключа
    :param default_value: Значение по умолчанию для нового ключа (None если не указано)
    :return: Новый список словарей с вставленным ключом
    """
    modified_list = []
    for original_dict in list_of_dicts:
        # Создаем новый словарь с элементами вставленными в нужном порядке
        new_dict = {}
        # Добавляем элементы до insert_index
        for i, (key, value) in enumerate(original_dict.items()):
            if i == insert_index:
                new_dict[new_key] = default_value
            new_dict[key] = value
        # Если insert_index находится после всех элементов
        if insert_index >= len(original_dict):
            new_dict[new_key] = default_value
        modified_list.append(new_dict)
    return modified_list

def num_col_by_name_in_hat_c(sp, ima):
    if type(sp[0]) == list:
        try:
            for i in range(len(sp[0])):
                if ima.upper() == str(sp[0][i]).upper():
                    return i
        except:
            print(f'Ошибка num_col_by_name_in_hat_c по {ima}')
            return
    if type(sp[0]) == dict:
        try:
            i= 0
            for key in sp[0].keys():
                if ima.upper() == str(key).upper():
                    return i
                i+=1
        except:
            print(f'Ошибка num_col_by_name_in_hat_c по {ima}')
            return

def find_in_list_1_1_c(sp, vhod_kol, chto, vih_kol='', soderg=False, s_konca=False):
    if s_konca == False:
        diap = range(0, len(sp))
    else:
        diap = range(len(sp) - 1, -1, -1)
    for i in diap:
        if soderg == False:
            if sp[i][vhod_kol] == chto:
                if vih_kol == '':
                    return i
                else:
                    return sp[i][vih_kol]
                break
        else:
            if chto in sp[i][vhod_kol]:
                if vih_kol == '':
                    return i
                else:
                    return sp[i][vih_kol]
                break
    return None


def write_in_list_1_1_c(sp, vhod_kol, chto, vih_kol='', chem='', append=False, vse=True):
    if vih_kol == '':
        vih_kol = vhod_kol

    for i in range(0, len(sp)):
        if sp[i][vhod_kol] == chto:
            if append == True:
                sp[i][vih_kol] = sp[i][vih_kol] + chem
            else:
                sp[i][vih_kol] = chem
            if vse == False:
                return


def find_in_list_c_2_1(sp, vhod_kol, chto, vhod_kol2, chto2, vih_kol=''):
    for i in range(0, len(sp)):
        if len(sp[i]) > 1:
            if sp[i][vhod_kol] == chto and sp[i][vhod_kol2] == chto2:
                if vih_kol == '':
                    return i
                else:
                    return sp[i][vih_kol]
                break
    return None


def list_of_files_c(path):
    try:
        tree = os.walk(path)
        sp = []
        try:
            for i in tree:
                sp.append(i)
        except:
            pass
        return sp
    except:
        return []

def copy_bufer(text):
    pyperclip.copy(text)


def paste_bufer(text=''):
    return text + pyperclip.paste()


def boolm(str:str):
    if str.lower() in {'false','0'}:
        return False
    if str.lower() in {'true','1'}:
        return True

def valm(ch):
    if isinstance(ch,bool):
        return int(ch)
    if ch == 'None':
        return 0
    if isinstance(ch,str):
        ch = ch.replace(',', '.')
        if 'e'  in ch.lower():
            return float(ch)
        if ch == '':
            return 0
        boolmval  =  boolm(ch)
        if boolmval != None:
            return int(boolmval)
        try:
            if '.' in ch:
                ch = float(ch.replace(' ', ''))
            else:
                ch = int(ch)
        except:
            return 0
    return ch


def curr_user_c():
    return os.environ.get("USERNAME")


def hex_to_rgb(hex):
    rgb = []
    for i in (0, 2, 4):
        decimal = int(hex[i:i + 2], 16)
        rgb.append(decimal)
    return tuple(rgb)


def rgb_to_hex(rgb: list):
    return '#%02x%02x%02x' % tuple(rgb)


def put_po_umolch():
    return os.path.expanduser('~')


def path_up_c(putt, level_c=1):
    glubina = len(putt.split(os.sep)) - 1
    if level_c > glubina: level_c = glubina
    putt = os.path.normpath(putt)
    arr = putt.split(os.sep)
    for i in range(level_c):
        arr.pop()
    arr = os.sep.join(arr)
    return arr


def throw_out_extention_c(file_name):
    arr = file_name.split('.')
    arr.pop()
    return '.'.join(arr)


def keep_extention_c(file_name):
    arr = file_name.split('.')
    ras = arr[-1]
    return "." + ras

def get_name_file_from_path(put,extention=True):
    if extention:
        return  put.split(sep())[-1]
    else:
        return '.'.join(put.split(sep())[-1].split('.')[:-1])

def numeric_to_str_separ(numeric:int|float,separ =' '):
    return '{:,}'.format(numeric).replace(',', separ)

def microseconds_passed(dateTime:datetime.datetime,len_obj:int=None):
    delta = (now('') - dateTime)
    mcsec = delta.seconds * 1000000 + delta.microseconds
    if len_obj:
        print(
        f"Микросекунд: {numeric_to_str_separ(mcsec)} /{len_obj} элементов. ({numeric_to_str_separ(round(mcsec / len_obj))} на элемент)")
    else:
        print(
            f"Микросекунд: {numeric_to_str_separ(mcsec)}")

def time_of_exec_func_c(funcd, *args):
    tmp_time = DT.now()

    def wrapper(*args):
        rez = funcd(*args)
        print(funcd.__name__ + ' ' + str(DT.now() - tmp_time))
        return rez

    return wrapper


def time_of_exec_cls_func_c(funcd):
    tmp_time = DT.now()

    def wrapper(self):
        rez = funcd(self)
        print(funcd.__name__ + ' ' + str(DT.now() - tmp_time))
        return rez

    return wrapper


def time_of_exec_cls_func_args_c(funcd):
    tmp_time = DT.now()

    def wrapper(self, *args):
        rez = funcd(self, *args)
        print(funcd.__name__ + ' ' + str(DT.now() - tmp_time))
        return rez

    return wrapper


def write_json_c(obj, putima, lines=True):
    if lines:
        with jslopen(putima, 'w') as writer:
            writer.write_all(obj)
    else:
        with open(putima, 'w') as f:
            js.dump(obj, f)


def load_json_c(putima, lines=True, encoding="utf-8"):
    loaded = []
    if lines:
        with jslopen(putima, 'r') as reader:
            for obj in reader.iter(type=dict, skip_invalid=True):
                loaded.append(obj)
    with open(putima, 'r', encoding=encoding) as f:
        loaded = js.load(f)
    return loaded


def add_rec_into_file_c(putima, stroka, utf8=False, sep=''):
    if sep != "":
        stroka = sep.join(stroka)
    if utf8 == True:
        with open(putima, 'a', encoding='utf-8') as f:
            f.write(stroka + '\n')
    else:
        with open(putima, 'a') as f:
            f.write(stroka + '\n')


def len_of_lines_file_c(putima):
    return sum(1 for line in open(putima, 'r', errors='ignore'))


def sleep(sec=1):
    time_sleep(sec)


def lock_file(putima):
    with open(putima + '_lock', 'wb'):
        sleep(0.5)
        dlina = len_of_lines_file_c(putima)
        return dlina


def unlock_file(putima):
    if existence_file_c(putima + '_lock'):
        delete_file_c(putima + '_lock')
        sleep(0.5)
        dlina = len_of_lines_file_c(putima)
        return dlina


def obr_lock_file(putima, zaderg: int = 20):
    if existence_file_c(putima + '_lock'):
        data_sozd = DT.fromtimestamp(os.path.getmtime(putima + '_lock'))
        while True:
            try:
                for _ in range(999):
                    if existence_file_c(putima + '_lock') == False:
                        return
                    now_date = DT.now()
                    delt = now_date - data_sozd
                    sec = delt.seconds
                    if sec > zaderg:
                        unlock_file(putima)
                        return
                    sleep(1)
            except:
                pass


def write_file_with_check_lock_c(putima, spisok, putima_err_j="", separ='', pickl=False, utf8=False, repeat: int = 10,
                                 zaderg: int = 10, dozapis=False):
    obr_lock_file(putima, zaderg)
    len_first = lock_file(putima)
    for _ in range(10):
        if dozapis == True:
            add_rec_into_file_c(putima, spisok, utf8, separ)
            len_first_itog = len_first + 1
        else:
            write_file_c(putima, spisok, separ, pickl, utf8)
            len_first_itog = len_first
        len_end = len_of_lines_file_c(putima)
        if len_end < len_first_itog:
            if putima_err_j != "":
                try:
                    err_spis = open_file_c(putima_err_j, False, '')
                    err_spis.append(
                        f"err файл журнал строк было {str(len_first)}, стало {str(len_end)}, время {str(now())}")
                    write_file_c(putima_err_j, err_spis, "", "", False)
                except:
                    pass
        else:
            unlock_file(putima)
            return True
    return False


def shifr(password):
    pass_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
    return pass_hash


def clear_for_filename_c(ima: str):
    spis = [r'#', r'<', r'$', r'+',
            r'%', r'>', r'!', r'`',
            r'&', r'*', r'‘', r'|',
            r'{', r'?', r'“', r'=',
            r'}', r'/', r':', r'\\', r' ', r'@']
    for s in spis:
        ima.replace(s, '')
    return ima


def load_file_convert_to_binary(put_filename, output_b64_string=False):
    if output_b64_string:
        blob = _convert_to_binary_data(put_filename)
        return base64.b64encode(blob).decode('utf-8') 
    return _convert_to_binary_data(put_filename)


def save_binary_convert_to_file(data, put_filename):
    return _write_to_file(data, put_filename)


def _convert_to_binary_data(put_filename):
    # Преобразование данных в двоичный формат
    with open(put_filename, 'rb') as file:
        blob_data = file.read()
    return blob_data


def _write_to_file(data, filename):
    # Преобразование двоичных данных в нужный формат
    with open(filename, 'wb') as file:
        file.write(data)
    print("Данный из blob сохранены в: ", filename, "\n")


def convert_binary_to_data(data_bin):
    # Преобразование данных из двоичный формат
    return data_bin.decode()


def convert_data_to_binary(data):
    # Преобразование данных в двоичный формат
    return str.encode(data)


def sep():
    return os.sep


def transliteration(text):
    cyrillic = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
    latin = 'a|b|v|g|d|e|yo|zh|z|i|j|k|l|m|n|o|p|r|s|t|u|f|h|cz|ch|sh|shh|``|y`|`|e`|yu|ya|A|B|V|G|D|E|Yo|Zh|Z|I|J|K|L|M|N|O|P|R|S|T|U|F|H|Cz|Ch|Sh|Shh|``|Y`|`|E`|Yu|Ya'.split(
        '|')
    return text.translate({ord(k): v for k, v in zip(cyrillic, latin)})


def to_cirillic(text):
    cyrillic = list('абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
    latin = 'a|b|v|g|d|e|yo|zh|z|i|j|k|l|m|n|o|p|r|s|t|u|f|h|cz|ch|sh|shh|``|y`|`|e`|yu|ya|A|B|V|G|D|E|Yo|Zh|Z|I|J|K|L|M|N|O|P|R|S|T|U|F|H|Cz|Ch|Sh|Shh|``|Y`|`|E`|Yu|Ya'.split(
        '|')
    for i in range(len(cyrillic) - 1, -1, -1):
        text = text.replace(latin[i], cyrillic[i])
    return text


def fix_decode(text):
    obr = list(r'абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ /.\,`~!@#$%^&*()_+-=|{}[]:;<>?')
    rez = []
    for item in text:
        if item in obr:
            rez.append(item)
    return ''.join(rez)


def to_snake_notation(text: str):
    text_tmp = text.replace(' ', '_')
    return transliteration(text)

def camel_to_snake(name):
    # Заменяем каждую заглавную букву на нижний регистр с предшествующим символом подчеркивания
    # Также учитываем, что могут быть русские буквы
    snake = re.sub(r'(?<!^)(?=[A-ZА-Я])', '_', name).lower()
    return snake


def align_colors(str_clrs:str,sep:str =';',level=80, level_percent=0, saturation = None, saturation_percent = None,sep_out= ';') -> str:
    '''стаблилизация цвета к уровню [level] - ментьше темнее; [saturation] - больше- насыщеннее'''
    if isinstance(str_clrs,tuple) or isinstance(str_clrs,list):
        rgb_t = str_clrs
    if isinstance(str_clrs, str):
        rgb_t = str_clrs.split(sep)
    list_clrs = [int(_)/255 for _ in  rgb_t]
    list_hls = [_ for _ in colorsys.rgb_to_hls(*list_clrs)]
    if level_percent:
        list_hls[1] = list_hls[1]* 1+(level_percent)/100
    else:
        list_hls[1] = level/255
        list_hls[1] = list_hls[1] * 1+(level_percent) / 100

    if list_hls[1] > 1:
        list_hls[1] = 1

    if saturation_percent:
        list_hls[2] = list_hls[2] * 1+(saturation_percent) / 100

    if saturation:
        list_hls[2] =saturation/255

    if list_hls[2] > 1:
        list_hls[2] = 1
    
    if sep_out == '':
        return [round(_ * 255) for _ in colorsys.hls_to_rgb(*list_hls)]
    list_rgb = [str(round(_ * 255)) for _ in colorsys.hls_to_rgb(*list_hls)]
    return sep_out.join(list_rgb)


def send_email_c(addr_from, addr_to, password, server, port, Tema, body):
    # Добавляем необходимые подклассы - MIME-типы
    from email.mime.multipart import MIMEMultipart  # Многокомпонентный объект
    from email.mime.text import MIMEText  # Текст/HTML
    # from email.mime.image import MIMEImage              # Изображения

    # addr_from = "from_address@mail.com"                 # Адресат
    # addr_to   = "to_address@mail.com"                   # Получатель
    # password  = "pass"                                  # Пароль

    msg = MIMEMultipart()  # Создаем сообщение
    msg['From'] = addr_from  # Адресат
    msg['To'] = addr_to  # Получатель
    msg['Subject'] = Tema  # Тема сообщения

    # body = "Текст сообщения"
    msg.attach(MIMEText(body, 'plain'))  # Добавляем в сообщение текст

    server = smtplib.SMTP(server, port)  # Создаем объект SMTP
    # server.set_debuglevel(True)                         # Включаем режим отладки - если отчет не нужен, строку можно закомментировать
    server.starttls()  # Начинаем шифрованный обмен по TLS
    server.login(addr_from, password)  # Получаем доступ
    server.send_message(msg)  # Отправляем сообщение
    server.quit()  # Выходим


def test_path():
    try:
        dict = cfg_dict()
        for key in dict.keys():
            print(key, dict[key])
            try:
                if os.sep in dict[key] and existence_file_c(dict[key]) == False:
                    msgbox(f'Не найден каталог {dict[key]}')
                    sys.exit()
            except:
                print('   ошибка проверки пути')
    except:
        print('Не загружены настройки')
        return False

# ++ 05.06.2025
def trim_collection(collection: dict | list | set):
    cp_collection = copy.deepcopy(collection)
    type_collection = type(collection)
    if type_collection in (list, set):
        for idx, item in enumerate(collection):
            if isinstance(item, str):
                cp_collection[idx] = item.strip()
    if type_collection == dict:
        for key, value in collection.items():
            if isinstance(value, str):
                cp_collection[key] = value.strip()
    return cp_collection
# -- 05.06.2025

def round_up(num):
    return int(-1 * valm(num) // 1 * -1)

def round_down(num):
    try:
        return int(num // 1)
    except (TypeError, ValueError):
        return 0  # или raise исключение

class dotdict(dict):
    """dot.notation access to dictionary attributes"""#TODO
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def inner_join(left_list, right_list, left_key, right_key):
    """
    Выполняет INNER JOIN двух списков словарей по указанным ключам.

    :param left_list: Левый список словарей
    :param right_list: Правый список словарей
    :param left_key: Ключ в словарях левого списка для соединения
    :param right_key: Ключ в словарях правого списка для соединения
    :return: Список объединенных словарей
    """
    # Создаем хеш-таблицу для правого списка по ключу соединения
    right_lookup = {}
    for item in right_list:
        key_value = item.get(right_key)
        if key_value is not None:
            if key_value not in right_lookup:
                right_lookup[key_value] = []
            right_lookup[key_value].append(item)

    # Выполняем соединение
    result = []
    for left_item in left_list:
        key_value = left_item.get(left_key)
        if key_value in right_lookup:
            for right_item in right_lookup[key_value]:
                # Создаем новый словарь, объединяя поля из обоих словарей
                merged = left_item.copy()
                merged.update(right_item)
                result.append(merged)

    return result


def left_join(left_list, right_list, left_key, right_key):
    """
    Выполняет LEFT JOIN двух списков словарей по указанным ключам.

    :param left_list: Левый список словарей
    :param right_list: Правый список словарей
    :param left_key: Ключ в словарях левого списка для соединения
    :param right_key: Ключ в словарях правого списка для соединения
    :return: Список объединенных словарей (все записи из left_list + совпадения из right_list)
    """
    # Создаем хеш-таблицу для правого списка по ключу соединения
    right_lookup = {}
    for item in right_list:
        key_value = item.get(right_key)
        if key_value is not None:
            if key_value not in right_lookup:
                right_lookup[key_value] = []
            right_lookup[key_value].append(item)

    # Выполняем LEFT JOIN
    result = []
    for left_item in left_list:
        key_value = left_item.get(left_key)
        if key_value in right_lookup:
            # Если есть совпадения, добавляем все комбинации
            for right_item in right_lookup[key_value]:
                merged = left_item.copy()
                merged.update(right_item)
                result.append(merged)
        else:
            # Если нет совпадений, добавляем левый словарь с NULL (None) для правых ключей
            merged = left_item.copy()
            # Добавляем ключи из правого списка с None, если их нет в левом
            for right_item_key in right_list[0].keys() if right_list else []:
                if right_item_key != right_key and right_item_key not in merged:
                    merged[right_item_key] = None
            result.append(merged)

    return result