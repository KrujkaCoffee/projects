import dataclasses
import os
import logging
import hashlib
from collections import defaultdict
from datetime import datetime
from functools import reduce
from pathlib import Path

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


@dataclasses.dataclass
class FormulaXLSX:
    name: str # Сварка
    params: dict[str, dict] = dataclasses.field(init=False)
    xlsx: xw.Book
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
        self.fullname = self.xlsx.fullname
        try:
            import time
            start = time.time()
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
            self.params = result

    def recalculation(self, params: dict[str, str | int]):
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


def is_excel(name: str) -> bool:
    return name.endswith('.xlsx') and not name.startswith('~$')


Poki = TypeVar('Poki', bound=int)

class LoadFormulas:
    def __init__(self, srv_dir: Path, actions: dict, organizations: dict):
        self.key_sep = '\\'
        self.organizations = organizations

        self.source_dir = srv_dir
        self.cache_dir = Path(__file__).parent / 'cache_xlsx'
        self.cache_dir.mkdir(exist_ok=True)

        self.actions = actions
        # self.operations: dict[int | str, dict[str, FormulaXLSX]] = {}
        self.operations: dict[str, dict[str, dict]] = self.__prepare_struct()
        self.transition: dict[int | str, dict[str, FormulaXLSX]] = {}

        self._close_any_pid() #todo del
        self.app = xw.App(visible=False, add_book=False)
        self.app.display_alerts = False
        # self.app = self._get_last_pid()

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
        # full_path = str((folder / filename).absolute())
        if os.path.isfile(abs_path):
            create_time = os.path.getctime(abs_path)
            created_at = datetime.fromtimestamp(create_time)

            update_time = os.path.getmtime(abs_path)
            updated_at = datetime.fromtimestamp(update_time)

            wb: xw.Book = self.app.books.open(abs_path, update_links=False)
            return FormulaXLSX(
                name=abs_path,
                xlsx=wb,
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
                    params['xlsx'] = self.get_xlsx(str(params['cache_path']))
        # for poki in self.organizations:
        #     poki = str(poki)
        #     for action, attr in self.actions.items():
        #         getattr(self, attr)[poki] = {
        #             self.prepare_filename(filename, action): self.get_xlsx(filename)
        #             for filename in self.get_path_list_xlsx(self.cache_dir / poki / action)
        #         }

    def load_xlsx2(self):
        logging.info('Загрузка excel файлов...')
        for poki in self.organizations:
            poki = str(poki)
            for action, attr in self.actions.items():
                getattr(self, attr)[poki] = {
                    self.prepare_filename(filename, action): self.get_xlsx(filename)
                    for filename in self.get_path_list_xlsx(self.cache_dir / poki / action)
                }

    def _close_any_pid(self):
        gen = (book for app in xw.apps for book in app.books)
        for book in gen:
            book.close()

    def close_xlsx(self):
        for book in self.app.books:
            book.close()

    def __del__(self): #todo del
        self.close_xlsx()
