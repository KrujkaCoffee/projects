import os.path
import pickle
import hashlib
import shutil
import logging
import stat
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from time import sleep
import sys, io
from win32com.client import gencache

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import xlwings
from werkzeug import Request, Response

from formul_xl_parser import LoadFormulas, FormulaXLSX

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(module)s.%(funcName)s] - %(message)s'
)
logger = logging.getLogger('werkzeug')

msg_format = '\n{lines}\nКлиент: {user}\nВ модуле: {module}\nСделал запрос: {query}\n{lines}\n'

FORM_PATH = Path(r'Z:\Data\TehKart\Data\bin')
ACTIONS = { # dir: attr
    'Операции': {
        'have_parent': False,
    },
    'Переходы': {
        'have_parent': True
    }
}
OP_DIR = 'Операции'
PER_DIR = 'Переходы'

CACHE_DIR = Path(__file__).parent / 'cache_xlsx'
CACHE_DIR = (Path(tempfile.gettempdir()).parent / 'cache_xlsx').absolute()
ORGANIZATIONS = {'0': 'Powerz', '1': 'Келаст'}

### ==== UTILS ====
def hash_dict(input_dict):
    import json
    try:
        dict_string = json.dumps(input_dict, sort_keys=True)
        hash_object = hashlib.sha256(dict_string.encode())
        return hash_object.hexdigest()
    except Exception as e:
        print("Ошибка хэширования параметров", e)

def log_block(fn):
    def wrapper(*args, **kwargs):
        separ = "=" * 15
        logger.info(f'\nСовершен запрос\n{kwargs}\n{separ}')
        return fn(*args, **kwargs)
    return wrapper

def kill_excel():
    try:
        # Выполняем команду для завершения процесса Excel
        subprocess.run(['taskkill', '/IM', 'excel.exe', '/F'], check=True)
        print("Процесс Excel завершен.")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при завершении процесса: {e}")

class HTTPSrv:
    def __init__(self):
        logger.info('Инициализация сервера...')
        from collections import defaultdict
        self.cache = defaultdict(dict)
        self.formulas = None
        self.source_xl_dir = FORM_PATH
        self.cache_dir = CACHE_DIR
        self.actions = ACTIONS
        self.organizations = ORGANIZATIONS
        CACHE_DIR.mkdir(exist_ok=True)
        if not self.source_xl_dir.exists():
            print(str(self.source_xl_dir))
            logger.error('Папка с формулами отсутствует или к ней нету доступа')
            return
        self.template_xl = self.source_xl_dir / 'Образец.xlsx'
        self.prepare_form_object()
        self.files_caches = {}

    def prepare_form_object(self):
        logging.info('Чистка excel com кэша...')
        gencache.Rebuild()
        logging.info('Чистка кэша калькуляций')
        self.cache = defaultdict(dict)
        logging.info('Подготовка excel файлов...')

        self.close_any_xlsx() #todo del
        if not isinstance(self.formulas, LoadFormulas):
            self.formulas = LoadFormulas(self.source_xl_dir, self.actions, self.organizations)

        self.drop_undue_files()
        self.check_cache()
        self.formulas.load_xlsx()

    def is_xlsx(self, filename: str):
        return (
            not filename.startswith('~$') and
            filename.endswith('.xlsx') and
            filename.split('.')[0]
        )

    def get_path_list_xlsx2(self, path: str | Path):
        return [
            file
            for file in os.listdir(str(path))
            if self.is_xlsx(file)
        ]

    def get_path_list_xlsx(self, path: str | Path):
        return [os.path.join(base_path, file) for base_path, paths, files in os.walk(path) for file in files if
             self.is_xlsx(file)]

    def check_cache(self):
        for poki in self.organizations:
            poki = str(poki)
            for action in self.actions:
                files = [(f, action) for f in self.get_path_list_xlsx(self.source_xl_dir / poki / action)]
                for file, path_name in files:
                    self.check_file(file, path_name, poki)

    def clean_xlsx_process(self, path: str):
        for app in xlwings.apps:
            for book in app.books:
                if book.fullname == path:
                    return book.close()

    def file_hash(self, file_path: str):
        """Вычисляет хеш файла."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def drop_undue_files(self):
        logging.info('Очистка кэша..')
        if os.path.isdir(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)


    def make_cache_path(self, abs_path: str, rel_path: str, poki: str) -> Path:
        is_per = rel_path == 'Переходы'
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        target_item = Path(abs_path)
        item_name = target_item.name.replace('.xlsx', '')
        oper_name = target_item.parent.name if is_per else item_name
        pereh_name = item_name if is_per else ''
        hash_name = self.formulas.hash_name(poki, oper_name, pereh_name)
        key_for_object = self.formulas.prepare_filename(oper_name, pereh_name)
        cache_path = self.cache_dir / f'{hash_name}.xlsx'
        match self.formulas.operations[poki][rel_path].get(key_for_object):
            case {'hash': hash_xl, 'cache_path': cache_path, 'xlsx': xlsx} if isinstance(xlsx, FormulaXLSX):
                if hash_xl == hash_xl and cache_path == cache_path.absolute() and xlsx.params:
                    return cache_path
            case _:
                self.formulas.operations[poki][rel_path][key_for_object] = {'hash': hash_name, 'cache_path': cache_path.absolute()}
        return cache_path

    def check_file(self, abs_file_path: str, dir_name: str, poki: str):
        logging.info(f'Копирование {abs_file_path}...')
        cache_path = self.make_cache_path(abs_file_path, dir_name, poki)
        try:
            if not cache_path.exists():
                shutil.copyfile(abs_file_path, str(cache_path))
            os.chmod(str(cache_path), stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)

            return True
        except Exception as e:
            logger.error(e)
            return False

    def write_msg(self, e, req, bytes):
        try:
            msg = f'{"=" * 10}\n{e}\n{req}\n'
            with open('./xl.log', 'a+') as f:
                f.write(msg)
        except Exception as e:
            return

    def wsgi_app(self, environ, start_response):
        request, bytes = None, None
        response = Response('error', status=500) # PATH_INFO
        path_info = environ['PATH_INFO']
        if path_info == '/ping':
            return Response(status=200)
        for i in range(2):
            try:
                if request is None and not bytes:
                    request = Request(environ)
                    bytes = pickle.loads(request.data)
                    if bytes is None: break
                result = self.dispatch(path_info=environ['PATH_INFO'], **bytes)
                response = Response(pickle.dumps(result))
                break
            except (pickle.PickleError, EOFError, ImportError) as e:
                logger.error(e)
                break
            except Exception as e:
                logging.error('Ошибка запроса', exc_info=True)
                sleep(0.5)
                if i == 1:
                    self.prepare_form_object()
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def clear_calc_cache(self, oper, pereh, poki):
        try:
            have_cache = self.cache.pop((oper, pereh, poki))
        except Exception as e:
            print(f'Кэш на комбинацию: {oper}.{pereh} не найден')

    def get_calc_cache(self, oper_name, pereh_name, poki, params):
        var_row = (oper_name, pereh_name, poki)
        hashed_params = hash_dict(params)
        if not hashed_params:
            return
        combination_cache = self.cache.get(var_row)
        if combination_cache and isinstance(combination_cache, dict):
            param_cache = combination_cache.get(hashed_params)
            if param_cache:
                return param_cache

    def put_calc_cache(self, oper, pereh, poki, params, value):
        var_row = (oper, pereh, poki)
        hashed_params = hash_dict(params)
        if not hashed_params:
            return
        try:
            self.cache[var_row][hashed_params] = value
        except Exception as e:
            print(f'Ошибка записи кэша: {e}')
    @log_block
    def dispatch(self, *, query: str, poki: str, body: dict | None = None, **kwargs):
        response = defaultdict(dict)
        oper_name = body.get('Операции')
        pereh_name = body.get('Переходы', '')
        # self.formulas.app.visible = False
        match query.split():
            case ['ALL']:
                org_actions = self.formulas.operations.get(poki)
                if isinstance(org_actions, dict):
                    for action, opers in org_actions.items():
                        for oper_name, oper_params in opers.items():
                            response[action][oper_name] = oper_params['xlsx'].params
                return response
            case ['CALC', action]:
                name = self.formulas.prepare_filename(oper_name, pereh_name)
                dic = self.formulas.operations.get(poki)[action][name]
                params = body.get('params')
                have_cache = self.get_calc_cache(oper_name, pereh_name, poki, params)
                if have_cache:
                    return have_cache
                result = dic['xlsx'].recalculation(params)
                self.put_calc_cache(oper_name, pereh_name, poki, params, result)
                return result
            case ['CREATE', action]:
                self.clear_calc_cache(oper_name, pereh_name, poki)
                return self.create(action, poki, oper_name, pereh_name)
            case ['RELOAD', action]:
                self.clear_calc_cache(oper_name, pereh_name, poki)
                return self.reload(action, poki, oper_name, pereh_name)
            case ['REMOVE', action]:
                self.clear_calc_cache(oper_name, pereh_name, poki)
                self.remove_one(action, oper_name, pereh_name, str(poki))
                return 'Успешно'
            case _:
                msg = f'Запрошена неизвестная команда {query}'
                logger.warning(f'Запрошена неизвестная команда {query}')
                return msg

    def create(self, action: str, poki: str, oper_name: str, pereh_name: str):
        try:
            hash_name = self.formulas.hash_name(poki, oper_name, pereh_name)
            filename = f'{hash_name}.xlsx'
            source_path = self.formulas.get_source_path(poki=poki, action=action, operation=oper_name, pereh=pereh_name)
            dest_path = self.cache_dir / filename
            if not dest_path.exists():
                if self.template_xl.exists():
                    shutil.copy2(str(self.template_xl), str(dest_path))
                    shutil.copy2(str(self.template_xl), str(source_path))
                    os.chmod(str(dest_path), stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
                    key_name = self.formulas.prepare_filename(oper_name, pereh_name)
                    self.formulas.operations[poki][action][key_name] = {
                        'hash': hash_name,
                        'cache_path': str(dest_path),
                        'xlsx': self.formulas.get_xlsx(str(dest_path))
                    }
                    return True
        except Exception as e:
            logger.error(f'Не удалось создать {action}: "{oper_name}.{pereh_name}"', exc_info=True)


    def reload(self, action: str, poki: str, oper_name: str, pereh_name: str):
        """
            Перезапуск .xlsx файла
            @action_name ('Операции', 'Переходы')
            @name 'Слесарная'
            @poki ('0', '1') Индекс организации из таблицы places
        """
        full_path = self.formulas.get_source_path(poki=poki, action=action, operation=oper_name, pereh=pereh_name)
        key_name = self.formulas.prepare_filename(oper_name, pereh_name)
        xl_params = self.formulas.get_object_params(poki, action, oper_name, pereh_name)
        if xl_params and 'xlsx' in xl_params and isinstance(xl_params['xlsx'], FormulaXLSX):
            xl_obj = xl_params['xlsx']
            xl_obj.close_if_exists()
            xl_obj.remove()
            self.check_file(full_path, action, poki)
            new_obj = self.formulas.get_xlsx(xl_params['cache_path'])
            self.formulas.operations[poki][action][key_name]['xlsx'] = new_obj
            return new_obj.params
        else:
            self.check_file(full_path, action, poki)
            new_obj = self.formulas.get_xlsx(xl_params['cache_path'])
            self.formulas.operations[poki][action][key_name]['xlsx'] = new_obj
            return new_obj.params

    def remove_one(self, action: str, opername: str, pereh: str, poki: str) -> bool:
        try:
            oper_obj = self.formulas.get_object_params(poki=poki, action=action, oper_name=opername, pereh_name=pereh)
            if oper_obj and 'xlsx' in oper_obj and isinstance(oper_obj['xlsx'], FormulaXLSX):
                key_name = self.formulas.prepare_filename(opername, pereh)
                oper_object = self.formulas.operations[poki][action].pop(key_name)
                oper_object['xlsx'].close_if_exists()
                oper_object['xlsx'].remove()
                return True
        except Exception as e:
            print(e)
        return False

    def close_any_xlsx(self):
        logging.info('Завершение устаревших сеансов excel...')
        for app in xlwings.apps:
            app.quit()
        # for book in (book for app in xlwings.apps for book in app.books):
        #     logging.info('Завершение: %s' % Path(book.fullname).name)
        #     book.close()

    def __del__(self): #todo del
        self.close_any_xlsx()


def run(HOST: str, PORT: int | str):
    from werkzeug.serving import run_simple
    kill_excel()
    srv = HTTPSrv()
    try:
        run_simple(HOST, PORT, srv)
    except Exception as e:
        srv.formulas.close_xlsx()
