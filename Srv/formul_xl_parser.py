import dataclasses
import os
import logging
import hashlib
import tempfile
from contextlib import contextmanager
from datetime import datetime
from functools import reduce
from pathlib import Path
import gc
import pythoncom
from dataclasses import dataclass
from typing import Dict, Any, Tuple
import win32com.client
import pywintypes

import xlwings as xw
from typing_extensions import TypeVar


class Settings:
    start: int = 2
    vars: str = 'A'
    values: str = 'B'
    min_max: str = 'C'
    desc: str = 'D'
    default: str = 'E'
    comment: str = 'F'


@dataclass
class FormulaXLSX_COM:
    name: str
    workbook_path: str
    created_at: datetime
    updated_at: datetime
    wb: str

    params: Dict[str, Any] = dataclasses.field(init=False)
    fullname: str = dataclasses.field(init=False)
    _app: Any = dataclasses.field(default=None, repr=False, init=False)
    _wb: Any = dataclasses.field(default=None, repr=False, init=False)


    def __post_init__(self):
        result = {
            'vars': {},
            'min/max': {},
            'desc': {},
            'default': {},
            'status': False,
            'comments': {},
            'created_at': datetime.strftime(self.created_at, '%Y-%m-%d %H:%M'),
            'updated_at': datetime.strftime(self.updated_at, '%Y-%m-%d %H:%M'),
        }
        self.params = result
        self.fullname = os.path.abspath(self.workbook_path)
        pythoncom.CoInitialize()
        try:
            try:
                self._app = win32com.client.DispatchEx("Excel.Application")
                self._app.Visible = False
                self._app.DisplayAlerts = False
                self._wb = self._app.Workbooks.Open(self.fullname, ReadOnly=True)
            except pywintypes.com_error as ce:
                raise

            sheet = self._wb.Sheets(1)

            def read_range_values(range_str: str):
                """Возвращает список значений из диапазона (в одну колонку).
                   COM может возвращать кортежи (rows, cols) или скаляры.
                """
                rng = sheet.Range(range_str)
                val = rng.Value
                if val is None:
                    return []
                if isinstance(val, tuple):
                    flat = []
                    for row in val:
                        if isinstance(row, tuple):
                            flat.append(row[0])
                        else:
                            flat.append(row)
                    return flat
                return [val]

            def lamb_l(ran: str):
                values = read_range_values(ran)
                return {str(v).strip(): f'{ran.split(":")[0][0]}{idx}'
                        for idx, v in enumerate(values, start=Settings.start) if v is not None}

            def lamb_r(ran: str):
                values = read_range_values(ran)
                col_letter = ran.split(":")[0][0]
                return {f'{col_letter}{idx}': str(v).strip()
                        for idx, v in enumerate(values, start=Settings.start) if v is not None}

            last_row = 60
            result['vars'] = lamb_r(f'{Settings.vars}2:{Settings.vars}{last_row}')
            result['min/max'] = lamb_r(f'{Settings.min_max}2:{Settings.min_max}{last_row}')
            result['desc'] = lamb_l(f'{Settings.desc}2:{Settings.desc}{last_row}')
            def_vars = lamb_r(f'{Settings.default}2:{Settings.default}{last_row}')
            com_vars = lamb_r(f'{Settings.comment}2:{Settings.comment}{last_row}')

            result['default'] = {
                desc: def_vars[coord.replace(Settings.desc, Settings.default)]
                for desc, coord in result['desc'].items()
                if coord.replace(Settings.desc, Settings.default) in def_vars
            }
            result['comments'] = {
                desc: com_vars[coord.replace(Settings.desc, Settings.comment)]
                for desc, coord in result['desc'].items()
                if coord.replace(Settings.desc, Settings.comment) in com_vars
            }

            result['values'] = {value: coord.replace(Settings.desc, Settings.values) for value, coord in result['desc'].items()}
            result['status'] = True
            self.params = result
        except Exception as e:
            import traceback; traceback.print_exc()
            pass
        finally:
            pythoncom.CoUninitialize()

    def recalculation(self, params: Dict[str, Any]) -> Tuple[Any, Any]:
        """Записывает params в ячейки значений, вызывает Calculate и читает результаты."""
        pythoncom.CoInitialize()
        try:
            if self._wb is None or self._app is None:
                self._app = win32com.client.DispatchEx("Excel.Application")
                self._app.Visible = False
                self._app.DisplayAlerts = False
                self._wb = self._app.Workbooks.Open(self.fullname, ReadOnly=False)

            sheet = self._wb.Sheets(1)
            for key, value in params.items():
                if key in self.params.get('values', {}):
                    coord = self.params['values'][key]
                    try:
                        sheet.Range(coord).Value = str(value)
                    except Exception:
                        pass
            try:
                self._app.Calculate()
            except Exception:
                pass
            last_index = self._wb.Sheets.Count
            res_sheet = self._wb.Sheets(last_index)
            tsht = res_sheet.Range('A2').Value
            tpz = res_sheet.Range('B2').Value
            return tsht, tpz
        finally:
            pythoncom.CoUninitialize()

    def close(self):
        """Закрывает рабочую книгу и приложение, если они были открыты этим объектом."""
        pythoncom.CoInitialize()
        try:
            try:
                if self._wb is not None:
                    try:
                        self._wb.Close(SaveChanges=False)
                    except Exception:
                        pass
                    del self._wb
                    self._wb = None
            except Exception:
                pass

            try:
                if self._app is not None:
                    try:
                        self._app.Quit()
                    except Exception:
                        pass
                    del self._app
                    self._app = None
            except Exception:
                pass

            gc.collect()
        finally:
            pythoncom.CoUninitialize()

    def close_if_exists(self):
        """Ищет открытые книги Excel и закрывает ту, что совпадает по fullname.
           В COM-контексте это будет действовать только для экземпляров Excel,
           к которым у текущего процесса есть доступ; мы же закрываем наш локальный экземпляр.
        """
        self.close()

    @property
    def parent_name(self) -> str:
        return Path(self.fullname).parent.name

    def remove(self):
        self.close()
        try:
            os.remove(self.fullname)
        except FileNotFoundError:
            pass


@contextmanager
def init_book(abs_path: str, app: xw.App = None):
    if app is None:
        app = xw.App(visible=False, add_book=False)
        app.api.ScreenUpdating = False
        app.api.EnableEvents = False
        app.api.DisplayAlerts = False
        app.api.AskToUpdateLinks = False
    xlsx = app.books.open(fullname=abs_path, update_links=False, read_only=False, ignore_read_only_recommended=True)
    yield xlsx
    try:
        xlsx.close()
        app.kill()
    except Exception as e:
        print(e)


@dataclasses.dataclass
class FormulaXLSX:
    name: str # Сварка
    params: dict[str, dict] = dataclasses.field(init=False)
    xlsx: xw.Book = dataclasses.field(init=False)
    created_at: datetime
    updated_at: datetime
    fullname: str = dataclasses.field(init=False)

    def __post_init__(self):
        result = {
            'vars': {},
            'min/max': {},
            'desc': {},
            'default': {},
            'status': False,
            'comments': {},
            'created_at': datetime.strftime(self.created_at, '%Y-%m-%d %H:%M'),
            'updated_at': datetime.strftime(self.updated_at, '%Y-%m-%d %H:%M'),
        }
        try:
            with init_book(self.name) as xlsx:
                self.xlsx = xlsx
                self.fullname = self.xlsx.fullname
                sheet = self.xlsx.sheets[self.xlsx.sheet_names[0]]
                lamb_l = lambda ran: {str(value).strip(): f'{ran[0]}{idx}' for idx, value in enumerate(sheet[ran].value, start=Settings.start) if value is not None}
                lamb_r = lambda ran: { f'{ran[0]}{idx}': str(value).strip() for idx, value in enumerate(sheet[ran].value, start=Settings.start) if value is not None}
                # last_row = sheet.range(f'{Settings.desc}2').end('down').row
                last_row = 60
                result['vars'] = lamb_r(f'{Settings.vars}2:{Settings.vars}{last_row}')
                result['min/max'] = lamb_r(f'{Settings.min_max}2:{Settings.min_max}{last_row}')
                result['desc'] = lamb_l(f'{Settings.desc}2:{Settings.desc}{last_row}')
                def_vars = lamb_r(f'{Settings.default}2:{Settings.default}{last_row}')
                com_vars = lamb_r(f'{Settings.comment}2:{Settings.comment}{last_row}')
                result['default'] = {
                    desc: def_vars[coord.replace(Settings.desc, Settings.default)]
                    for desc, coord in result['desc'].items()
                    if coord.replace(Settings.desc, Settings.default) in def_vars}
                result['comments'] = {
                    desc: com_vars[coord.replace(Settings.desc, Settings.comment)]
                    for desc, coord in result['desc'].items()
                    if coord.replace(Settings.desc, Settings.comment) in com_vars}
                result['values'] = {value: coord.replace(Settings.desc, Settings.values) for value, coord in result['desc'].items()}
                result['status'] = True
                self.params = result
                return
        except Exception as e:
            print(e)
            self.params = result

    def recalculation(self, params: dict[str, str | int]):
        with init_book(self.name) as xlsx:
            self.xlsx = xlsx
            sheet = self.xlsx.sheets[self.xlsx.sheet_names[0]]
            for key, value in params.items():
                if key in self.params['values']:
                    sheet.range(self.params['values'][key]).value = str(value)
            self.xlsx.app.calculate()
            tsht = self.xlsx.sheets[self.xlsx.sheet_names[-1]].range('A2').value
            tpz = self.xlsx.sheets[self.xlsx.sheet_names[-1]].range('B2').value
            return tsht, tpz

    def close_if_exists(self):
        for app in xw.apps:
            for book in app.books:
                if book.fullname == self.fullname:
                    book.close()
    @property
    def parent_name(self) -> str:
        return Path(self.fullname).parent.name

    def remove(self):
        os.remove(self.fullname)

    def __str__(self):
        return self.name


def is_excel(name: str) -> bool:
    return name.endswith('.xlsx') and not name.startswith('~$')


Poki = TypeVar('Poki', bound=int)

class LoadFormulas:
    def __init__(self, srv_dir: Path, actions: dict, organizations: dict):
        self.key_sep = '\\'
        self.organizations = organizations

        self.source_dir = srv_dir
        self.cache_dir = (Path(tempfile.gettempdir()).parent / 'cache_xlsx').absolute()
        self.cache_dir.mkdir(exist_ok=True)

        self.actions = actions
        self.operations: dict[str, dict[str, dict]] = self.__prepare_struct()
        self.transition: dict[int | str, dict[str, FormulaXLSX]] = {}

        self._close_any_pid() #todo del
        # self.app = self.create_app()

    def create_app(self):
        app = xw.App(visible=False, add_book=False)
        app.api.ScreenUpdating = False
        app.api.EnableEvents = False
        app.api.DisplayAlerts = False
        app.api.AskToUpdateLinks = False
        # app = xw.App(visible=False, add_book=False)
        app.display_alerts = False
        return app

    def __prepare_struct(self):
        return {
            organization: {action: {} for action in self.actions}
            for organization in self.organizations
        }

    def _get_last_pid(self):
        """
        Возвращает последний активный процсс созданный xlwings
        (функция для отладки)
        """
        dump = r'C:\DB_srv\cache_xlsx\pid.txt'
        if os.path.exists(dump):
            with open(dump, 'r') as f:
                pid = f.read()
                for app in xw.apps:
                    if str(app.pid) == str(pid):
                        return app
        app = xw.App(visible=False, add_book=False)
        app.display_alerts = False
        return app

    def get_xlsx(self, abs_path: str):
        logging.info(f'Создание объекта {abs_path}')
        if os.path.isfile(abs_path):
            create_time = os.path.getctime(abs_path)
            created_at = datetime.fromtimestamp(create_time)

            update_time = os.path.getmtime(abs_path)
            updated_at = datetime.fromtimestamp(update_time)

            return FormulaXLSX(
                name=abs_path,
                created_at=created_at,
                updated_at=updated_at,
            )

    def get_object_params(self, poki: str, action: str, oper_name: str, pereh_name: str):
        key_name = self.prepare_filename(oper_name, pereh_name)
        hierarchy = (poki, action, key_name)
        return reduce(lambda obj, key: obj.get(key, {}), hierarchy, self.operations)

    def build_path(self, base_dir: str | Path, *args) -> Path:
        base_dir = Path(base_dir)
        lst_dir = [base_dir, *args]
        return reduce(lambda accum, current: accum / str(current), lst_dir)

    def get_cache_path(self, *, poki: str, action: str, operation: str, pereh: str = '') -> Path:
        return self.build_path(self.cache_dir, poki, action, operation, pereh)

    def get_source_path(self, *, poki: str, action: str, operation: str, pereh: str = '') -> str:
        path = self.build_path(self.source_dir, poki, action, operation, pereh)
        path.parent.mkdir(parents=True, exist_ok=True)
        return f'{path}.xlsx'

    def find_active_book(self, full_path: str):
        for app in xw.apps:
            for book in app.books:
                if book.fullname == full_path:
                    return book

    def hash_name(self, poki: str, oper_name: str, pereh_name: str) -> str:
        full_name = '.'.join([poki, oper_name, pereh_name])
        hashed_name = hashlib.sha256(full_name.encode('utf8')).hexdigest()
        return hashed_name

    def is_xlsx(self, filename: str):
        return (
            not filename.startswith('~$') and
            filename.endswith('.xlsx') and
            filename.split('.')[0]
        )

    def prepare_filename(self, oper_name: str, pereh_name: str):
        full_name = self.key_sep.join(elem for elem in (oper_name, pereh_name) if elem)
        return full_name.replace('.xlsx', '')

    def prepare_filename2(self, abs_path: str, dir_name: str):
        parts = Path(abs_path).parts
        if dir_name in parts and parts.index(dir_name) + 1 < len(parts):
            idx_first = parts.index(dir_name) + 1
            return '\\'.join(parts[idx_first:]).replace('.xlsx', '')

    def get_path_list_xlsx(self, path: str | Path):
        return [os.path.join(base_path, file) for base_path, paths, files in os.walk(str(path)) for file in files if
             self.is_xlsx(file)]

    def load_xlsx(self):
        logging.info('Загрузка excel файлов...')
        for organization, actions in self.operations.items():
            for action, opers in actions.items():
                for oper, params in opers.items():
                    name = str(params['cache_path'].absolute())
                    existing_obj = params.get('xlsx')
                    if isinstance(existing_obj, FormulaXLSX) and existing_obj.params:
                        print(f'Пропуск создания объекта. Объект {name!r} уже существует.')
                        continue
                    params['xlsx'] = self.get_xlsx(name)


    def _close_any_pid(self):
        gen = (book for app in xw.apps for book in app.books)
        for book in gen:
            book.close()

    def close_xlsx(self):
        for app in xw.apps:
            for book in app.books:
                try:
                    book.close()
                except:
                    ...

    def __del__(self): #todo del
        self.close_xlsx()
