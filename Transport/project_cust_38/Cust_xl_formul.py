import logging
import pickle
import subprocess, os
from datetime import datetime
from functools import reduce
from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import QWidget, QTableWidget
from PyQt5.QtGui import QPainter, QColor
from PyQt5 import QtWidgets
import requests

from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_mes as CMS
from project_cust_38 import Cust_config as CFG

logging.basicConfig(level=logging.INFO)


class XLClient:
    def __init__(self, poki):
        self.poki = poki
        if not 'XL_SRV_LIVE' in os.environ:
            os.environ['XL_SRV_LIVE'] = '1'

    def get_credentials(self):
        try:
            from project_cust_38 import Cust_client_socket as CSQ
            db, port = CSQ.db_path('DB_xl_formulas.db')
            return CSQ.ip, port
        except Exception as e:
            logging.error('Не удалось извлечь данные сервера')
            return None, None

    def post(self, query: str, body: dict | None = None, raise_exc: bool = False):
        # if os.environ['XL_SRV_LIVE'] == '0': # todo заменить на ping
        #     return False
        try:
            ip, port = self.get_credentials()
            params = requests.post(f'http://{ip}:{port}', data=pickle.dumps({
                'query': query,
                'body': body,
                'user': F.user_name(),
                'module': F.name_of_executable_file_c(),
                'poki': str(self.poki)
            }))
            result = pickle.loads(params.content)
        except Exception as e:
            logging.info('Сервер с формулами расчета excel недоступен!')
            os.environ['XL_SRV_LIVE'] = '0'
            if raise_exc:
                raise e
            return False
        return result

    def srv_operation_params(self) -> dict[str, dict]:
        return self.post('ALL', body={})

    def srv_operation_calc(self, oper_name, pereh_name, params):
        if isinstance(params, list):
            params = F.list_of_lists_to_list_of_dicts(params)[0]
        return self.post(f'CALC Операции', {'Операции': oper_name, 'Переходы': pereh_name, 'params': params}, raise_exc=True)

    def srv_pereh_calc(self, oper_name, pereh_name, params):
        if isinstance(params, list):
            params = F.list_of_lists_to_list_of_dicts(params)[0]
        response = self.post('CALC Переходы', {'Операции': oper_name, 'Переходы': pereh_name, 'params': params}, raise_exc=True)
        if response and len(response) >= 1:
            return response[0]
        else:
            logging.info(f'Не удалось вычислить {oper_name}.{pereh_name} с парамтрами {params}')
            return 0


    def create(self, action, operation: str, pereh: str) -> dict:
        return self.post(f'CREATE {action}', body={'Операции': operation, 'Переходы': pereh})

    def reload_formula(self, action, operation: str, pereh: str) -> dict:
        return self.post(f'RELOAD {action}', body={'Операции': operation, 'Переходы': pereh})

    def remove_cache(self, action: str, operation: str, pereh: str) -> dict:
        return self.post(f'REMOVE {action}', body={'Операции': operation, 'Переходы': pereh})


class CircleWidget(QWidget):
    def __init__(self, is_green=True):
        super().__init__()
        self.is_green = is_green

    def paintEvent(self, event):
        painter = QPainter(self)
        color = QColor(0, 255, 0) if self.is_green else QColor(255, 0, 0)  # Зеленый или красный
        painter.setBrush(color)

        diameter = self.height() // 2
        painter.drawEllipse((self.width() - diameter) // 2, (self.height() - diameter) // 2, diameter, diameter)


class TableXLFormula:
    def __init__(self, instance: QtWidgets.QTableWidget):
        self.__instance = instance

    def currentRow(self):
        row = self.__instance.currentRow()
        if row == -1 or row is None:
            return CQT.msgbox('Сначала необходимо выбрать строку')
        return row

    def textItem(self, row: int, col_name: str):
        col = CQT.num_col_by_name_c(self.__instance, col_name)
        if col is None:
            return CQT.msgbox(f'Не найдена колонка: "{col_name}"')
        item = self.__instance.item(row, col)
        if item is None:
            return CQT.msgbox(f'Не найдена строчка: {row} в олонке "{col_name}"')
        return item.text()

    def __getattr__(self, item):
        return getattr(self.__instance, item)


class XlFormula:
    default_attrs = {'approved': False, 'sum': False}

    def __init__(self, window=None):
        self.base_dir = Path(CFG.Config.project.tk_temp_folder)
        self.template = self.base_dir / 'Образец.xlsx'
        self.poki = self.check_poki()
        self.main_tbl = None
        self.srv_sep = '\\'
        self.params_sep = '|'

        self.client = XLClient(self.poki)
        self.window = window
        self.params = self.__get_params()
        self.params_last_update_date = self.params_last_update()
        self.xl_srv_data = self.client.srv_operation_params()

        if window is not None:
            tbl: QtWidgets.QTableWidget = self.window.ui.tbl_formulas
            self.main_tbl: QtWidgets.QTableWidget = TableXLFormula(tbl)
            self.main_tbl.itemSelectionChanged.connect(self.on_row_changed)
            window.ui.btn_add_formula.setText('Открыть')
            window.ui.btn_add_formula.clicked.connect(self.toggled_btn_create_open)
            window.ui.btn_reload_formula.clicked.connect(self.reload)
            window.ui.btn_del_formula.clicked.connect(self.remove)

    def get_pereh_txt_path(self, oper_name: str):
        """
        Принимает имя операции
        Возвращает путь к блокноту с переходами учитывая poki
        Нпрм. "Z:\\Data\\TehKart\\Data\\bin\\0\\Гибка.txt"
        """
        return str(self.base_dir / self.poki / f'{oper_name}.txt')

    def get_actual_srv_data(self):
        data = self.client.srv_operation_params()
        self.xl_srv_data = data
        return data

    def on_row_changed(self, *args):
        row = self.main_tbl.currentRow()
        action = self.get_action(row)
        text = 'Создать'
        enable_reload = False
        enable_delete = self.is_excel(row) or action != 'Переходы'
        if self.is_excel(row):
            text = 'Открыть'
            enable_reload = True
        self.window.ui.btn_reload_formula.setEnabled(enable_reload)
        self.window.ui.btn_del_formula.setEnabled(enable_delete)
        self.window.ui.btn_add_formula.setText(text)

    def check_poki(self) -> str:
        config = CFG.Config
        organization = CFG.Place(
            bd_naryad=config.project.db_naryad,
            organization_str=config.user_config.Organization['Значение']
        )
        if organization.poki is None:
            raise Exception('Не удалось определить текущую организацию')
        poki = organization.poki
        return str(poki)

    def __remove_pereh(self, oper, pereh):
        path = self.base_dir / self.poki / f'{oper}.txt'
        if path.exists():
            arr_tmp = F.open_file_c(str(path), False, "|")
            for idx, (name, rating, *args) in enumerate(arr_tmp):
                if name == pereh:
                    arr_tmp.pop(idx)
                    F.write_file_c(str(path), arr_tmp, "|")
                    return True

    def __dump_params(self):
        path = self.base_dir / str(self.poki) / 'params.pickle'
        with open(str(path), 'wb') as desc:
            pickle.dump(self.params, desc)
            return True

    def check_approved(self, *, operation: str, pereh: str = '') -> bool:
        full_name = self.params_sep.join((operation, pereh))
        return self.params.get(full_name, {}).get('approved', False)

    def check_strict_calc(self, *, operation: str, pereh: str = '') -> bool:
        full_name = self.params_sep.join((operation, pereh))
        return self.params.get(full_name, {}).get('strict_calc', False)

    def check_perm_for_amount(self, operation: str) -> bool:
        return self.params.get(f'{operation}|', {}).get('sum', False)

    def add_reestr(self, oper, pereh, rating, is_excel: bool):
        full_name = '|'.join((oper, pereh))
        param = self.params.get(full_name, self.default_attrs.copy())
        if param.get('rating') is None or param.get('last_update') is None:
            param['rating'] = rating
            param['last_update'] = datetime.now()
            return
        difference = datetime.now() - param['last_update']
        approved = param.get('approved', False)
        if rating == '1' and difference.days >= 14 and not is_excel and not approved:
            self.__remove_pereh(oper, pereh)
        self.params[full_name] = param

    def all_operations(self):
        DICT_OPERS = self.window.DICT_OPERS
        hat_c = ['Операции', 'Переходы', 'Рейтинг', 'Использовать в расчетах', 'ФормулаДата', 'СерверДата', 'СерверСтатус', 'ОбязательныйСчет']
        xl_data = self.get_actual_srv_data()
        cache_pickle = self.base_dir / 'cache.pickle'
        lst_op = []
        list_xl = []
        for file in os.listdir(str(self.base_dir / self.poki)):
            full_path = self.base_dir / self.poki / file
            opername = file.replace('.txt', '')
            if os.path.isfile(str(full_path)) and file.endswith('.txt') and file.replace('.txt', '') in DICT_OPERS:
                for pereh in F.open_file_c(str(full_path), False, "|"):
                    key_name = self.srv_key_oper(opername, pereh[0])
                    is_excel = xl_data and key_name in xl_data['Переходы']
                    if xl_data and key_name in xl_data['Переходы']:
                        list_xl.append([opername, pereh[0], pereh[1],
                               '',
                               xl_data['Переходы'][key_name]['created_at'],
                               xl_data['Переходы'][key_name]['updated_at'],
                               '', ''])
                    else:
                        lst_op.append([opername, pereh[0], pereh[1], ''])
                        self.add_reestr(opername, pereh[0], pereh[1], is_excel=is_excel)
        F.write_file_c(str(cache_pickle), lst_op, pickl=True)
        self.__dump_params()
        for oper in DICT_OPERS:
            is_xl = self.check_op(oper, approved=False) and oper in xl_data['Операции']
            elem = [oper, '', '', '',
                            xl_data['Операции'][oper]['created_at'] if is_xl else '',
                            xl_data['Операции'][oper]['updated_at'] if is_xl else '',
                            '', '']
            if is_xl:
                list_xl.append(elem)
            else:
                lst_op.append(elem)
        lst_op.sort(key=lambda x: (x[0], x[2]))
        return [hat_c, *list_xl, *lst_op]

    def get_action(self, row, *args, **kwargs):
        tbl = self.window.ui.tbl_formulas
        oper = tbl.item(row, CQT.num_col_by_name_c(tbl, 'Операции')).text()
        pereh = tbl.item(row, CQT.num_col_by_name_c(tbl, 'Переходы')).text()
        if not pereh.strip():
            return ('Операции', oper)
        return ('Переходы', pereh)

    def is_excel(self, row):
        tbl = self.window.ui.tbl_formulas
        action, _ = self.get_action(row)
        oper = tbl.item(row, CQT.num_col_by_name_c(tbl, 'Операции')).text()
        pereh = tbl.item(row, CQT.num_col_by_name_c(tbl, 'Переходы')).text()
        path = str(self.base_dir / self.poki / action / oper / pereh) + '.xlsx'
        if F.existence_file_c(path):
            return True
        return False

    def toggled_btn_create_open(self, *args):
        row = self.main_tbl.currentRow()
        if row is not None:
            tbl = self.window.ui.tbl_formulas
            btn_text = self.window.ui.btn_add_formula.text()
            match btn_text:
                case 'Создать': self.create(tbl.currentRow())
                case 'Открыть': self.open_formula(row)
                case _: return

    def open_formula(self, row, *args):
        action, _ = self.get_action(row)
        oper_name = self.main_tbl.textItem(row, 'Операции')
        pereh_name = self.main_tbl.textItem(row, 'Переходы')
        row_path = self.build_path(self.base_dir, self.poki, action, oper_name, pereh_name)
        filename = f'{row_path}.xlsx'
        if F.existence_file_c(filename):
            try:
                subprocess.Popen(['start', 'excel', filename], shell=True)
            except Exception as e:
                CQT.msgbox(f'Не удалось открыть формулу {filename}')
        return

    def create(self, row):
        if not CMS.user_access(F.scfg('Naryad'), 'тк_корректировка_удаление_формул', F.user_name()):
            return
        action, _ = self.get_action(row)
        oper_name = self.main_tbl.textItem(row, 'Операции')
        pereh_name = self.main_tbl.textItem(row, 'Переходы')
        full_name = f'{oper_name}.{pereh_name}' if pereh_name else oper_name
        if not CQT.msgboxgYN(f'Вы уверены что хотите создать {action} с именем {full_name}'):
            return
        if not self.client.create(action, oper_name, pereh_name):
            return CQT.msgbox(f'Не удалось создать {action}: "{full_name}"')
        if action == 'Переходы':
            self.up_rating(row, pereh_name)
        self.on_row_changed(row)
        self.open_formula(row)
        self.fill_table()

    def reload(self, *args):
        if not CMS.user_access(F.scfg('Naryad'), 'тк_корректировка_удаление_формул', F.user_name()):
            return
        tbl = self.window.ui.tbl_formulas
        row = tbl.currentRow()
        if row == -1 or row is None:
            CQT.msgbox('Сначала необходимо выделить строку')
            return
        if not self.is_excel(row):
            return
        action, _ = self.get_action(row)
        oper_name = self.main_tbl.textItem(row, 'Операции')
        pereh_name = self.main_tbl.textItem(row, 'Переходы')
        response = self.client.reload_formula(action, oper_name, pereh_name)
        status = False
        if isinstance(response, dict):
            status = response.get('status')
        tbl.setCellWidget(
            row,
            CQT.num_col_by_name_c(tbl, 'СерверСтатус'),
            CircleWidget() if status else CircleWidget(is_green=False)
        )

    def build_path(self, base_dir: str | Path, *args):
        base_dir = Path(base_dir)
        lst_dir = [base_dir, *args]
        return reduce(lambda accum, current: accum / str(current), lst_dir)

    def up_rating(self, row: int, name: str):
        tbl = self.window.ui.tbl_formulas
        name_op = tbl.item(row, CQT.num_col_by_name_c(tbl, 'Операции')).text()
        path = str(self.base_dir / self.poki / f'{name_op}.txt')

        min_rating = int(F.scfg('limit_p')) + 1
        if F.existence_file_c(path):
            arr_tmp = F.open_file_c(path, False, "|")
            for idx, (cur_per, rating, *args) in enumerate(arr_tmp):
                if cur_per == name and int(rating) < min_rating:
                    arr_tmp[idx][1] = min_rating
                    F.write_file_c(path, arr_tmp, "|")
                    break

    def remove(self, *args):
        row = self.main_tbl.currentRow()
        if row is None: return
        action, _ = self.get_action(row)
        oper_name = self.main_tbl.textItem(row, 'Операции')
        pereh_name = self.main_tbl.textItem(row, 'Переходы')
        if not self.is_excel(row) and action != 'Переходы':
            return
        if not CMS.user_access(F.scfg('Naryad'), 'тк_корректировка_удаление_формул', F.user_name()):
            return
        self.remove_xlsx(action, oper_name, pereh_name)
        tbl = self.window.ui.tbl_formulas
        msg = 'Вы уверены что хотите полностью удалить \n'
        try:
            if pereh_name.strip():
                postfix = f'Переход: {pereh_name}'
                path_obj_txt = self.build_path(self.base_dir, self.poki, oper_name)
                txt_path = f'{path_obj_txt}.txt'
                if F.existence_file_c(txt_path) and CQT.msgboxgYN(msg + postfix):
                    arr_tmp = F.open_file_c(txt_path, False, "|")
                    for idx, (name, rating, *args) in enumerate(arr_tmp):
                        if name == pereh_name:
                            arr_tmp.pop(idx)
                            F.write_file_c(txt_path, arr_tmp, "|")
                            tbl.removeRow(row)
                            return True
                    return False
        except Exception as e:
            print(e)
            CQT.msgbox('Не удалось удалить формулу')
            return False

    def remove_xlsx(self, action: str, oper_name: str, pereh_name: str):
        path_obj = self.build_path(self.base_dir, self.poki, action, oper_name, pereh_name)
        postfix = f'{action}: {oper_name}.{pereh_name}'
        oper_path = f'{path_obj}.xlsx'
        if F.existence_file_c(oper_path) and CQT.msgboxgYN(f'Удалить excel привязанный к: {postfix}'):
            os.remove(oper_path)
            self.client.remove_cache(action, oper_name, pereh_name)
            self.fill_table()
            return True
        return False

    def approve_formula(self, checked: bool, row: int, col: int):
        if not CMS.user_access(F.scfg('Naryad'), 'тк_корректировка_удаление_формул', F.user_name()):
            return
        tbl: QtWidgets.QTableWidget = self.window.ui.tbl_formulas
        nk_col = CQT.num_col_by_name_c(tbl, 'Использовать в расчетах')
        item = tbl.cellWidget(row, nk_col)
        if self.put_params(row, 'approved', checked):
            item.setChecked(checked)

    def set_strict_calc(self, checked: bool, row: int, col: int):
        if not CMS.user_access(F.scfg('Naryad'), 'тк_корректировка_удаление_формул', F.user_name()):
            return
        tbl: QtWidgets.QTableWidget = self.window.ui.tbl_formulas
        nk_col = CQT.num_col_by_name_c(tbl, 'ОбязательныйСчет')
        item = tbl.cellWidget(row, nk_col)
        if self.put_params(row, 'strict_calc', checked):
            item.setChecked(checked)

    def check_status(self, row):
        action, _ = self.get_action(row)
        oper_name = self.main_tbl.textItem(row, 'Операции')
        pereh_name = self.main_tbl.textItem(row, 'Переходы')
        name = self.srv_key_oper(oper_name, pereh_name)
        if not self.xl_srv_data:
            return False
        if action == 'Операции' and name in self.xl_srv_data['Операции']:
            return self.xl_srv_data['Операции'][name]['status']
        elif action == 'Переходы' and name in self.xl_srv_data['Переходы']:
            return self.xl_srv_data['Переходы'][name]['status']
        return False

    def check_operation(self, row):
        action, name = self.get_action(row)
        return action == 'Операции'

    def create_buttons(self):
        tbl = self.window.ui.tbl_formulas
        xl_widgets = XLWidgets(self, tbl)
        for row in range(tbl.rowCount()):
            xl_widgets.create_status_checkbox(row)
            xl_widgets.create_server_status_circle(row)
            xl_widgets.create_strict_status_checkbox(row)

    def fix_column_size(self):
        ignore = ('Операции', 'Переходы')
        font = self.main_tbl.font()
        metrics = self.main_tbl.fontMetrics()

        for i in range(self.main_tbl.columnCount()):
            horizontal_header = self.main_tbl.horizontalHeaderItem(i)
            header_name = horizontal_header.text()
            if header_name not in ignore:
                header_text = horizontal_header.text()
                header_width = metrics.horizontalAdvance(header_text) + metrics.horizontalAdvance(' ' * 11)
                self.main_tbl.setColumnWidth(i, header_width)

    def convert_old_struct(self, oper: str, pereh: str = ''):
        key_oper = self.srv_key_oper(oper, pereh)
        action = 'Операции' if not pereh else 'Переходы'
        struct = self.xl_srv_data[action][key_oper]
        xl_params = {}
        for desc in struct['desc']:
            vals = {}
            if desc in struct['default']:
                defaults = struct['default'][desc].split('|')
                if len(defaults) > 1:
                    use_range = not len(defaults[0].split('-')) >= 2
                    for idx, o in enumerate(struct['default'][desc].split('|')):
                        if o == '':
                            continue
                        if use_range:
                            vals[idx] = {'val': o[0], 'prim': ''}
                        else:
                            key = o.split('-', 1)[0].strip()
                            value = o.split('-', 1)[1].strip()
                            vals[key] = {'val': value, 'prim': ''}
            comment = struct['comments'].get(desc, '')
            xl_params[desc] = {'type': float, 'comment': comment, 'vals': {**vals}}
        return xl_params

    def check_minmax(self, user_params: dict, srv_params: dict):
        errors = {}
        for key, value in user_params.items():
            min_max = srv_params['min/max'].get(key, '').split('-')
            min = min_max[0] if len(min_max) >= 1 else None
            max = min_max[1] if len(min_max) >= 2 else 9999
            if min is not None and F.is_numeric(min) and F.is_numeric(max) and F.is_numeric(value):
                if min > value:
                    errors[key] = 'Меньше минимума'
                if max < value:
                    errors[key] = 'Больше максимума'
        return errors

    def __checker(self, key_name: str):
        return bool(self.xl_srv_data and isinstance(self.xl_srv_data, dict) and self.xl_srv_data.get(key_name))

    def srv_key_oper(self, oper_name: str, pereh_name: str) -> str:
        return self.srv_sep.join(elem for elem in (oper_name, pereh_name) if elem)

    def check_op(self, operation: str, approved: bool = False):
        is_having = self.__checker('Операции') and operation in self.xl_srv_data['Операции']
        if approved:
            return is_having and self.check_approved(operation=operation)
        return is_having

    def check_per(self, operation: str, pereh: str, approved: bool = False):
        key_name = self.srv_key_oper(operation, pereh)
        is_having = self.__checker('Переходы') and key_name in self.xl_srv_data['Переходы']
        if approved:
            return is_having and self.check_approved(operation=operation, pereh=pereh)
        return is_having

    def get_op_params(self, operation: str) -> list:
        if self.check_op(operation):
            return list(self.xl_srv_data['Операции'][operation]['desc'].keys())
        return []

    def get_per_params(self, operation: str, pereh: str) -> list:
        key_name = self.srv_key_oper(oper_name=operation, pereh_name=pereh)
        if self.check_per(operation, pereh):
            return list(self.xl_srv_data['Переходы'][key_name]['desc'].keys())
        return []

    @property
    def params_path(self) -> Path:
        return self.base_dir / str(self.poki) / 'params.pickle'

    def params_last_update(self):
        return datetime.fromtimestamp(self.params_path.stat().st_mtime)

    def __get_params(self):
        path = self.base_dir / str(self.poki) / 'params.pickle'
        try:
            if path.exists():
                with open(str(path), 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            print(e)
        return dict()

    def full_name_operation(self, row):
        tbl = self.window.ui.tbl_formulas
        oper = tbl.item(row, CQT.num_col_by_name_c(tbl, 'Операции')).text()
        pereh = tbl.item(row, CQT.num_col_by_name_c(tbl, 'Переходы')).text()
        return '|'.join((oper, pereh))

    def put_params(self, row: int, param: str, state: Any):
        # if self.params_last_update() != self.params_last_update_date:
        #     CQT.msgbox('Страница была изменена обновить?')
        #     return
        full_name = self.full_name_operation(row)
        oper = self.params.get(full_name, self.default_attrs.copy())
        oper[param] = state
        self.params[full_name] = oper
        self.__dump_params()

    def check_op_per_sum(self, row):
        full_name_oper = self.full_name_operation(row)
        oper = self.params.get(full_name_oper, {})
        return oper.get('sum', False)

    def toggle_sum_op_per(self, checked: bool, row: int, col: int):
        if not CMS.user_access(F.scfg('Naryad'), 'тк_корректировка_удаление_формул', F.user_name()):
            return
        tbl: QtWidgets.QTableWidget = self.window.ui.tbl_formulas
        item = tbl.cellWidget(row, col)
        if self.put_params(row, 'sum', checked):
            item.setChecked(checked)

    def fill_table(self):
        self.params = self.__get_params()
        tbl: QtWidgets.QTableWidget = self.window.ui.tbl_formulas
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.clear()
        lst = self.all_operations()
        CQT.fill_wtabl(lst, tbl, StretchLastSection=True, height_row=20,min_width_col=180,ogr_maxshir_kol=500)
        self.create_buttons()
        self.fix_column_size()
        CMS.fill_filtr_c(self.window, self.window.ui.tbl_formulas_filtr, tbl, hidden_scroll=True)
        CMS.update_width_filtr(tbl, self.window.ui.tbl_formulas_filtr)


class XLWidgets:
    def __init__(self, xl_formula: XlFormula, tbl):
        self.xl_formula = xl_formula
        self.tbl = tbl

    def create_status_checkbox(self, row):
        oper = self.tbl.item(row, CQT.num_col_by_name_c(self.tbl, 'Операции')).text()
        pereh = self.tbl.item(row, CQT.num_col_by_name_c(self.tbl, 'Переходы')).text()
        CQT.add_check_box(self.tbl, row,
                          CQT.num_col_by_name_c(self.tbl, 'Использовать в расчетах'),
                          val=self.xl_formula.check_approved(operation=oper, pereh=pereh),
                          conn_func_checked_row_col=self.xl_formula.approve_formula
                          )

    def create_strict_status_checkbox(self, row):
        action, _ = self.xl_formula.get_action(row)
        oper = self.tbl.item(row, CQT.num_col_by_name_c(self.tbl, 'Операции')).text()
        pereh = self.tbl.item(row, CQT.num_col_by_name_c(self.tbl, 'Переходы')).text()
        if action == 'Операции':
        # if self.xl_formula.is_excel(row):
            CQT.add_check_box(self.tbl, row,
                              CQT.num_col_by_name_c(self.tbl, 'ОбязательныйСчет'),
                              val=self.xl_formula.check_strict_calc(operation=oper, pereh=pereh),
                              conn_func_checked_row_col=self.xl_formula.set_strict_calc
                              )

    def create_sum_checkbox(self, row):
        action, _ = self.xl_formula.get_action(row)
        if action == 'Операции':
            CQT.add_check_box(self.tbl, row,
                              CQT.num_col_by_name_c(self.tbl, 'Суммировать операцию с переходом'),
                              val=self.xl_formula.check_op_per_sum(row),
                              conn_func_checked_row_col=self.xl_formula.toggle_sum_op_per
                          )

    def create_server_status_circle(self, row):
        if self.xl_formula.is_excel(row):
            self.tbl.setCellWidget(
                row,
                CQT.num_col_by_name_c(self.tbl, 'СерверСтатус'),
                CircleWidget() if self.xl_formula.check_status(row) else CircleWidget(is_green=False)
            )
