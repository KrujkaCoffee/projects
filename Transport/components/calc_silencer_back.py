import os
import copy
import io
import json
import math
import pickle
import re
import time

import flet as ft

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Excel as CEX
import project_cust_38.Cust_emoji as Cust_emoji
import project_cust_38.Cust_SQLite as CSQ
import Config.srv_config as SRVCFG
from components import (
    calc_silencer_input_params,
    calc_acoustic_input_params,
)
from components import silencer_calculation_core as calculation_core
from components.tech_report_excel import sort_key_params

import components.common_funcs as CMF
from components.common_funcs import Table_data
import data_class as DTCLS

CONSTANTS = calculation_core.CONSTANTS
INPUT_PARAMS = calculation_core.INPUT_PARAMS
INPUT_PARAM_NAMES = calculation_core.INPUT_PARAM_NAMES
BLANK_ZERO_INPUT_NAMES = calculation_core.BLANK_ZERO_INPUT_NAMES
OUTPUT_PARAMS = calculation_core.OUTPUT_PARAMS
CALC_FUNCTIONS = calculation_core.CALC_FUNCTIONS
GROUPS = calculation_core.GROUPS

class Cust_module_params():
    def __init__(self):
        self.ver_tbls_data = 2
        self.input_tbl_editbl: Table_data | None = None
        self.input_tbl_not_editbl: Table_data | None = None
        self.output_tbl: Table_data | None = None
        self.filtr_seach_history: str = ''
        self.last_calculated: dict | None = None
        self.last_input_vals: dict | None = None
        self.last_calc_errors: list[dict] = []
        self.last_metrics_ms: dict[str, float] = {}

TBL_INPUT = Table_data()
TBL_INPUT.append_column_desc(name='name', header='Имя', hidden=True, editable=False, unique=True)
TBL_INPUT.append_column_desc(name='header', header='Параметр', hidden=False, editable=False, width=300)
TBL_INPUT.append_column_desc(name='dimension', header='Ед.изм', hidden=False, editable=False, width=80)
TBL_INPUT.append_column_desc(name='val', header='Значение', hidden=False, editable=True, width=180)

TBL_OUTPUT_ERR = Table_data()
TBL_OUTPUT_ERR.append_column_desc(name='name', header='№', hidden=False, editable=False, width=50, unique=True)
TBL_OUTPUT_ERR.append_column_desc(name='header', header='Параметр', hidden=False, editable=False, width=300)
TBL_OUTPUT_ERR.append_column_desc(name='val', header='Значение', hidden=False, editable=False, width=130)
TBL_OUTPUT_ERR.append_column_desc(name='err', header='Ошибка', hidden=False, editable=False, width=300)

TBL_OUTPUT = Table_data()
TBL_OUTPUT.append_column_desc(name='name', header='Имя', hidden=True, editable=False, unique=True)
TBL_OUTPUT.append_column_desc(name='header', header='Параметр', hidden=False, editable=False, width=300)
TBL_OUTPUT.append_column_desc(name='val', header='Значение', hidden=False, editable=False, width=130)
TBL_OUTPUT.append_column_desc(name='dimension', header='Ед.изм', hidden=False, editable=False)
TBL_OUTPUT.append_column_desc(name='comment', header='Примечание', hidden=False, editable=False, width=500)

TBL_HISTORY = Table_data()
TBL_HISTORY.append_column_desc(name='s_num', header='Номер', hidden=True, editable=False, unique=True)
TBL_HISTORY.append_column_desc(name='date', header='Дата', hidden=False, editable=False, width=300)
TBL_HISTORY.append_column_desc(name='name', header='Название', hidden=False, editable=False, width=500)




def is_empty(val) -> bool:
    """True если значение нельзя выводить в результирующую таблицу."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == '':
        return True
    if isinstance(val, float):
        try:
            if math.isnan(val) or math.isinf(val):
                return True
        except Exception:
            pass
    return False


def calc_new_tbl_input():
    new_tbl_input_copy = copy.deepcopy(TBL_INPUT)
    new_tbl_input_copy.add_table_name(F.get_time_shtamp_c(), 'Ввод параметров:')
    prev_gr = ''
    for item in INPUT_PARAMS:
        name = item['name']
        header = item['header']
        dimension = item['dimension']

        data_type = None
        if 'data_type' in item:
            data_type = item['data_type']

        val = 0
        if data_type is str:
            val = ''
        default_val = None
        if 'default_val' in item:
            default_val = item['default_val']
            val = copy.deepcopy(default_val)
        min_max_list = None
        if "min_max_list" in item:
            min_max_list = item["min_max_list"]
            if isinstance(min_max_list, tuple) and data_type == None:
                data_type = int
        visible = True
        if 'visible' in item:
            visible = item['visible']
        if visible:
            comment = None
            if "comment" in item:
                comment = item["comment"]
            accuracy = 5
            if 'accuracy' in item:
                accuracy = item['accuracy']


            if 'group_name' in item:
                if prev_gr != item['group_name']:
                    prev_gr = item['group_name']
                    new_tbl_input_copy.add_group(name,prev_gr)

            row = CMF.Row_data()
            row.append(name, CMF.Cell_description())
            row.append(header, CMF.Cell_description())
            row.append(dimension, CMF.Cell_description())
            row.append(val, CMF.Cell_description(min_max_list, comment=comment, data_type=data_type, accuracy=accuracy, default_val=default_val))
            new_tbl_input_copy.add_row(row)
    return new_tbl_input_copy


def generate_input_data(
        fnc_onchange,
        ref,
        default_vals: dict | None = None,
        page: ft.Page | None = None,
) -> tuple[ft.DataTable, Table_data]:
    # Модель ввода должна принадлежать конкретной странице. Ранее один объект
    # ``new_tbl_input`` разделялся всеми Flet-сессиями.
    new_tbl_input = calc_new_tbl_input()
    if default_vals:
        new_tbl_input.set_vals_into_field(default_vals, 'val')

    table_view = CMF.Table_view(
        new_tbl_input,
        ref=ref,
        fnc_onchange=fnc_onchange,
        keyboard_navigation=page is not None,
        page=page,
    )


    return table_view, new_tbl_input


def prepare_calc_new_data(data: list[dict], Data: DTCLS.Data_page) -> tuple[dict | None, list[dict], bool]:
    sync_started = time.perf_counter()
    if not Data.Data_module.cust_data.input_tbl_editbl.sync_ui_to_data('val'):
        return None, [], False
    sync_ms = (time.perf_counter() - sync_started) * 1000

    data_params = Data.Data_module.cust_data.input_tbl_editbl.to_dict_by_unique()
    formula_started = time.perf_counter()
    calculated, errors, success = calc_new_data({k: v['val'] for k, v in data_params.items()})
    Data.Data_module.cust_data.last_metrics_ms.update({
        'sync_input': sync_ms,
        'formula': (time.perf_counter() - formula_started) * 1000,
    })
    return calculated, errors, success


def generate_rez_tbl(e: ft.ControlEvent, tbl: ft.DataTable, ref_out, fnc_cell_click=None) -> bool | None:
    """Генерация таблицы результатов."""

    total_started = time.perf_counter()

    def _has_any_data_rows(tbl_data: CMF.Table_data) -> bool:
        """Присутствуют ли данные в таблице output"""
        if tbl_data is None:
            return False
        for row in getattr(tbl_data, 'rows', []):
            if not getattr(row, 'merge', False) and not getattr(row, 'table_header', False):
                return True
        return False
    Data: DTCLS.Data_page = e.page.data
    data = CMF.datatable_to_dicts(tbl)
    Data.Data_module.cust_data: Cust_module_params
    Data.Data_module.cust_data.output_tbl = None

    calculated, errors, success = prepare_calc_new_data(data, Data)
    if calculated is None:
        return

    Data.Data_module.cust_data.last_calculated = calculated
    Data.Data_module.cust_data.last_calc_errors = errors

    result_model_started = time.perf_counter()
    tbl_output = make_res_tbl(calculated, ref_out, fnc_cell_click)
    Data.Data_module.cust_data.last_metrics_ms.update({
        'result_model': (time.perf_counter() - result_model_started) * 1000,
        'server_total_before_push': (time.perf_counter() - total_started) * 1000,
    })
    warning_symbol = Cust_emoji.СтатусыПроизводства.warning.symbol
    success_symbol = Cust_emoji.СтатусыПроизводства.success.symbol
    if errors and not _has_any_data_rows(tbl_output):
        tbl_output = make_err_tbl(errors, ref_out)
        Data.Data_module.cust_data.output_tbl = tbl_output
        Data.Data_module.status_bar.set_text(f"{warning_symbol} Ошибка расчёта: рассчитанных параметров нет")
        return False

    Data.Data_module.cust_data.output_tbl = tbl_output

    if errors:
        headers = '\n '.join(f"{msg.get('header')}" for msg in errors if msg.get('header'))
        Data.Data_module.status_bar.set_text(
            f"{warning_symbol} Произошли ошибки при расчете {len(errors)} параметров ({headers})"
        )
    else:
        total_ms = Data.Data_module.cust_data.last_metrics_ms.get('server_total_before_push', 0.0)
        Data.Data_module.status_bar.set_text(
            f"{success_symbol} Успешно рассчитано · сервер {total_ms:.0f} мс"
        )
    return True


def make_res_tbl(data: dict, ref_out=None, fnc_cell_click=None) -> CMF.Table_data:
    new_tbl_output: Table_data = copy.deepcopy(TBL_OUTPUT)
    new_tbl_output.add_table_name(F.get_time_shtamp_c(), 'Расчетные данные:')

    list_groups = [group for group, is_view in GROUPS.items() if is_view]

    list_groups = sorted(list_groups)
    for group in list_groups:
        group_items: list[tuple[str, object]] = []
        for name, val in data.items():
            if name not in OUTPUT_PARAMS:
                continue
            if not OUTPUT_PARAMS[name].get('view', True):
                continue
            current_group = OUTPUT_PARAMS[name].get('group_name', '')
            if current_group != group:
                continue
            if is_empty(val):
                continue
            group_items.append((name, val))

        if not group_items:
            continue
        group_items.sort(key=lambda kv: sort_key_params(kv[0], OUTPUT_PARAMS))
        new_tbl_output.add_group(F.get_time_shtamp_c(), group)

        for name, val in group_items:
            row = CMF.Row_data()
            row.group_name = group
            row.append(name, CMF.Cell_description())
            row.append(OUTPUT_PARAMS[name]['header'], CMF.Cell_description())
            if F.is_numeric(val):
                accuracy = OUTPUT_PARAMS[name]['accuracy']
                row.append(val, CMF.Cell_description(accuracy=accuracy, data_type=float))
            else:
                row.append(val, CMF.Cell_description(data_type=str))
            row.append(OUTPUT_PARAMS[name]['dimension'], CMF.Cell_description())
            comment = OUTPUT_PARAMS[name].get('comment') or ''
            row.append(comment, CMF.Cell_description())

            new_tbl_output.add_row(row)
    CMF.Table_view(new_tbl_output, ref=ref_out, fnc_on_click=fnc_cell_click, lazy_groups=True, single_group_expand=True)

    return new_tbl_output


def make_err_tbl(data, ref_out=None) -> CMF.Table_data:
    new_tbl_output_err = copy.deepcopy(TBL_OUTPUT_ERR)
    for i, item in enumerate(data):
        row = CMF.Row_data()
        row.append(str(i + 1), CMF.Cell_description())
        row.append(item['header'], CMF.Cell_description())
        row.append(item['val'], CMF.Cell_description())
        row.append(item['Exception'], CMF.Cell_description())
        new_tbl_output_err.add_row(row)

    CMF.Table_view(new_tbl_output_err, ref=ref_out)
    return  new_tbl_output_err


_HISTORY_SCHEMA_VERSION = 2


class _LegacyHistoryUnpickler(pickle.Unpickler):
    """Ограниченный загрузчик прежнего формата истории.

    Старые записи содержат только модели таблиц. Произвольные глобальные
    объекты запрещены, поэтому содержимое БД не может вызвать выполнение кода.
    """

    _ALLOWED_CLASSES = {
        ("components.common_funcs", name): getattr(CMF, name)
        for name in (
            "Table_data",
            "Field_params",
            "Row_data",
            "_Cell_data",
            "Cell_description",
        )
    }
    _ALLOWED_BUILTINS = {
        "bool": bool,
        "dict": dict,
        "float": float,
        "int": int,
        "list": list,
        "set": set,
        "str": str,
        "tuple": tuple,
    }

    def find_class(self, module: str, name: str):
        allowed = self._ALLOWED_CLASSES.get((module, name))
        if allowed is not None:
            return allowed
        if module == "builtins" and name in self._ALLOWED_BUILTINS:
            return self._ALLOWED_BUILTINS[name]
        raise pickle.UnpicklingError(f"Запрещённый объект legacy-истории: {module}.{name}")


def _load_legacy_history(raw_data):
    if isinstance(raw_data, memoryview):
        raw_data = raw_data.tobytes()
    if not isinstance(raw_data, (bytes, bytearray)):
        raise ValueError("Legacy-история должна быть бинарной")
    return _LegacyHistoryUnpickler(io.BytesIO(raw_data)).load()


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (tuple, list, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


def table_data_to_payload(table_data: CMF.Table_data) -> dict:
    """Сериализует только данные модели таблицы, без Flet-ссылок и кода."""
    return {
        'name': table_data.name,
        'fields': [
            {
                'name': field.name,
                'header': field.header,
                'hidden': field.hidden,
                'editable': field.editable,
                'width': field.width,
                'unique': field.unique,
            }
            for field in table_data.list_fields
        ],
        'rows': [
            {
                'merge': bool(getattr(row, 'merge', False)),
                'group_name': getattr(row, 'group_name', None),
                'table_header': bool(getattr(row, 'table_header', False)),
                'cells': [
                    {
                        'value': _json_safe(cell.val),
                        'description': {
                            'min_max_list': _json_safe(cell.description.min_max_list),
                            'accuracy': cell.description.accuracy,
                            'comment': _json_safe(cell.description.comment),
                            'data_type': getattr(cell.description.data_type, '__name__', 'str'),
                            'default_val': _json_safe(cell.description.default_val),
                        },
                    }
                    for cell in row.cells
                ],
            }
            for row in table_data.rows
        ],
    }


def table_data_from_payload(payload: dict) -> CMF.Table_data:
    if not isinstance(payload, dict):
        raise ValueError('Некорректная модель таблицы в истории')

    table_data = CMF.Table_data()
    fields = payload.get('fields')
    rows = payload.get('rows')
    if not isinstance(fields, list) or not isinstance(rows, list):
        raise ValueError('В истории отсутствуют поля или строки таблицы')

    for field in fields:
        table_data.append_column_desc(
            name=str(field['name']),
            header=str(field.get('header') or ''),
            hidden=bool(field.get('hidden', False)),
            editable=bool(field.get('editable', False)),
            width=field.get('width', 100),
            unique=bool(field.get('unique', False)),
        )

    for row_payload in rows:
        cell_payloads = row_payload.get('cells')
        if not isinstance(cell_payloads, list) or len(cell_payloads) != len(fields):
            raise ValueError('Количество ячеек истории не соответствует структуре таблицы')
        row = CMF.Row_data(merge=bool(row_payload.get('merge', False)))
        row.group_name = row_payload.get('group_name')
        row.table_header = bool(row_payload.get('table_header', False))
        for cell_payload in cell_payloads:
            desc_payload = cell_payload.get('description') or {}
            min_max = desc_payload.get('min_max_list')
            if isinstance(min_max, list) and len(min_max) == 2 and all(
                isinstance(item, (int, float)) and not isinstance(item, bool) for item in min_max
            ):
                min_max = tuple(min_max)
            description = CMF.Cell_description(
                min_max_list=min_max,
                accuracy=int(desc_payload.get('accuracy', 3)),
                comment=desc_payload.get('comment'),
                data_type=str(desc_payload.get('data_type') or 'str'),
                default_val=desc_payload.get('default_val'),
            )
            row.append(cell_payload.get('value'), description)
        table_data.add_row(row)

    table_data.name = payload.get('name')
    return table_data


def build_history_blob(input_tbl: CMF.Table_data, output_tbl: CMF.Table_data) -> bytes:
    payload = {
        'schema_version': _HISTORY_SCHEMA_VERSION,
        'input_tbl': table_data_to_payload(input_tbl),
        'output_tbl': table_data_to_payload(output_tbl),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def decode_history_blob(raw_data) -> tuple[CMF.Table_data, CMF.Table_data]:
    """Читает безопасный JSON v2; pickle v1 поддерживается только как legacy."""
    if isinstance(raw_data, memoryview):
        raw_data = raw_data.tobytes()
    try:
        text = raw_data.decode('utf-8') if isinstance(raw_data, bytes) else str(raw_data)
        payload = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        legacy = _load_legacy_history(raw_data)
        if not isinstance(legacy, dict) or 'input_tbl' not in legacy or 'output_tbl' not in legacy:
            raise ValueError('Некорректная запись истории расчёта')
        input_tbl = legacy['input_tbl']
        output_tbl = legacy['output_tbl']
        if not isinstance(input_tbl, CMF.Table_data) or not isinstance(output_tbl, CMF.Table_data):
            raise ValueError('Некорректные таблицы в legacy-истории расчёта')
        return input_tbl, output_tbl

    if not isinstance(payload, dict):
        raise ValueError('Некорректный JSON истории расчёта')
    if payload.get('schema_version') != _HISTORY_SCHEMA_VERSION:
        raise ValueError('Неподдерживаемая версия JSON истории')
    try:
        return (
            table_data_from_payload(payload['input_tbl']),
            table_data_from_payload(payload['output_tbl']),
        )
    except KeyError as exc:
        raise ValueError('В JSON истории отсутствует таблица') from exc


def load_from_db_history_calc(
        Data: DTCLS.Data_page,
        s_num: int,
) -> tuple[CMF.Table_data, CMF.Table_data] | bool:
    data = CSQ.custom_request_c(
        Data.Data_user.db_flet,
        "SELECT data FROM silencer_history WHERE s_num = ? AND login = ?",
        list_of_lists_c=[[int(s_num), Data.Data_user.login]],
        one=True,
        one_column=True,
        hat_c=False,
    )
    if not data:
        return False
    return decode_history_blob(data)


def get_name_new_calc(input_vals: dict | None = None) -> str:
    """Генерация имени расчёта по входным параметрам"""

    def sanitize_part(s: str) -> str:
        s = re.sub(r'[<>:"/\\|?*]+', '_', s)
        return s.strip()

    if not input_vals:
        return f"calc_{F.now('%Y-%m-%d(%H%M%S)')}"

    project_name = sanitize_part(str(input_vals.get('nazvanie_proekta', '') or ''))
    project_num = sanitize_part(str(input_vals.get('nomer_proekta', '') or ''))

    pos_raw = input_vals.get('pozicii', '')
    pos_str = ''
    if pos_raw is None:
        pos_str = ''
    else:
        try:
            pos_int = int(str(pos_raw).strip())
            pos_str = f"{pos_int:02d}" if 0 <= pos_int < 100 else str(pos_int)
        except Exception:
            pos_str = sanitize_part(str(pos_raw))
            if pos_str.isdigit() and len(pos_str) == 1:
                pos_str = pos_str.zfill(2)

    parts = [p for p in (project_name, project_num, pos_str) if p]
    return '.'.join(parts) if parts else f"calc_{F.now('%Y-%m-%d(%H%M%S)')}"


def generate_rezult_data_for_save(name: str, input_tbl: ft.DataTable, output_tbl: ft.DataTable) -> dict:
    list_dict_rez_input = CMF.datatable_to_dicts(input_tbl)
    list_dict_rez_output = CMF.datatable_to_dicts(output_tbl)
    return {'name': name, 'input': list_dict_rez_input, 'output': list_dict_rez_output}


def get_vals_from_input_data_tbl(tbl: ft.DataTable):
    table_data = getattr(tbl, 'table_data', None)
    if isinstance(table_data, CMF.Table_data):
        if table_data.sync_ui_to_data('val') is False:
            raise ValueError('Не удалось синхронизировать входную таблицу')
        data_params = table_data.to_dict_by_unique()
        return {
            name: values['val']
            for name, values in data_params.items()
            if name in INPUT_PARAM_NAMES
        }

    # Обычный ft.DataTable оставляем типизировать расчётному ядру. Иначе
    # F.valm превращал строки (например, среду и единицу расхода) в ноль.
    return {
        row['Имя']: row['Значение']
        for row in CMF.datatable_to_dicts(tbl)
        if row.get('Имя') in INPUT_PARAM_NAMES
    }

def save_exel(list_dict_rez_input: list, list_dict_rez_output: list, name: str, dir_save: str, name_module: str) -> str | bool:
    list_dict_rez_input = [{k: v for k, v in _.items() if k != 'Имя'} for _ in list_dict_rez_input]
    list_dict_rez_output = [{k: v for k, v in _.items() if k != 'Имя'} for _ in list_dict_rez_output]

    def dict_lists_to_side_by_side_table(list1, list2):
        """
        Объединяет два списка словарей в таблицу, располагая их горизонтально,
        разделяя двумя пустыми колонками. Если словари имеют разное количество ключей,
        дополняет их пустыми значениями (None).

        :param list1: Первый список словарей
        :param list2: Второй список словарей
        :return: Список списков (таблица, где строки — объединённые записи)
        """

        # Преобразуем в списки
        keys1 = list(list1[0].keys())
        keys2 = list(list2[0].keys())

        # Определяем максимальное количество строк (по самому длинному списку)
        max_rows = max(len(list1), len(list2))

        # Создаём таблицу
        table = []

        # Добавляем заголовки (ключи первого и второго списка + 2 пустых колонки между ними)
        header = keys1 + ['', ''] + keys2
        table.append(header)

        # Заполняем строки данными
        for i in range(max_rows):
            row = []

            # Данные из первого списка (если есть, иначе None)
            if i < len(list1):
                row.extend([list1[i].get(key, '') for key in keys1])
            else:
                row.extend([''] * len(keys1))

            # Добавляем 2 пустые колонки-разделители
            row.extend(['', ''])

            # Данные из второго списка (если есть, иначе None)
            if i < len(list2):
                row.extend([list2[i].get(key, '') for key in keys2])
            else:
                row.extend([''] * len(keys2))

            table.append(row)

        return table

    # rez_spis = dict_lists_to_side_by_side_table(list_dict_rez_input, list_dict_rez_output)
    folder = dir_save
    name_file = f'{name}.docx'
    template_path = os.path.join(SRVCFG.DOCX_TEMPLATES_PATH, 'report.docx')
    path = os.path.join(dir_save, name_file)
    rez = CEX.make_docx_report(name_module, list_dict_rez_input, list_dict_rez_output, output_docx_path=path,
                           template_name=template_path)
    # rez = CEX.zap_spis(rez_spis, folder, name_file, '1', 1, 1, return_putf=True)
    if not rez:
        return False
    return rez

def file_into_blob(putf):
    return F.file_into_blob(putf)


def make_history_tbl_data(Data: DTCLS.Data_page):
    TBL_HISTORY_TMP = copy.deepcopy(TBL_HISTORY)
    query = "SELECT * FROM silencer_history WHERE login = ?"
    params = [Data.Data_user.login]
    history_filter = str(Data.Data_module.cust_data.filtr_seach_history or '').strip()
    if history_filter:
        query += " AND name LIKE ?"
        params.append(f'%{history_filter}%')
    query += " ORDER BY s_num DESC LIMIT 20;"
    list_calcs = CSQ.custom_request_c(
        Data.Data_user.db_flet,
        query,
        list_of_lists_c=[params],
        rez_dict=True,
    ) or []
    for calc in list_calcs:
        row = CMF.Row_data()
        row.append(calc['s_num'], CMF.Cell_description())
        row.append(calc['date'], CMF.Cell_description())
        row.append(calc['name'], CMF.Cell_description())
        TBL_HISTORY_TMP.add_row(row)

    return TBL_HISTORY_TMP


def save_in_db(e: ft.ControlEvent, name: str):
    Data: DTCLS.Data_page = e.page.data
    Module_data: Cust_module_params = Data.Data_module.cust_data
    input_tbl = Module_data.input_tbl_not_editbl or Module_data.input_tbl_editbl
    if input_tbl is None or Module_data.output_tbl is None:
        return False
    row = [
        F.now(),
        name,
        Data.Data_user.login,
        build_history_blob(input_tbl, Module_data.output_tbl),
    ]
    rez = CSQ.custom_request_c(
        Data.Data_user.db_flet,
        "INSERT INTO silencer_history (date, name, login, data) VALUES (?, ?, ?, ?)",
        list_of_lists_c=[row],
    )
    return rez


calc_new_data = calculation_core.calc_new_data


def oform_kolichestvo_kasset(cell:CMF._Cell_data,new_val):
    row_data: CMF.Row_data = cell.parent_row
    table_input_data:CMF.Table_data = row_data.parent_table_data
    dict_settings_kolichestvo_kasset = {
        1: {'tuple_fields_show': ('r2_rasstoyanie_m_u_1_i_2_kassetoj_mm', 't2_tolschina_2_kassety_mm') ,'name_field_middle':("r2 - Расстояние м/у 1 и 2 кассетой, мм","t2 - Толщина 2 кассеты, мм"),'name_field_end':("r2 - Расстояние м/у 1 кассетой и облицовкой, мм","t2 - Толщина облицовки, мм")},
        2: {'tuple_fields_show': ('r3_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm', 't3_tolschina_oblicovki_mm') ,'name_field_middle':("r3 - Расстояние м/у 2 и 3 кассетой, мм","t3 - Толщина 3 кассеты, мм"),'name_field_end':("r3 - Расстояние м/у 2 кассетой и облицовкой, мм","t3 - Толщина облицовки, мм")},
        3: {'tuple_fields_show': ('r4_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm', 't4_tolschina_oblicovki_mm'),'name_field_middle':("r4 - Расстояние м/у 3 и 4 кассетой, мм","t4 - Толщина 4 кассеты, мм"),'name_field_end':("r4 - Расстояние м/у 3 кассетой и облицовкой, мм","t4 - Толщина облицовки, мм")},
        4: {'tuple_fields_show': ('r5_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm', 't5_tolschina_oblicovki_mm'),'name_field_middle':("r5 - Расстояние м/у 4 и 5 кассетой, мм","t5 - Толщина 5 кассеты, мм"),'name_field_end':("r5 - Расстояние м/у 4 кассетой и облицовкой, мм","t5 - Толщина облицовки, мм")},
        5: {'tuple_fields_show': ('r6_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm', 't6_tolschina_oblicovki_mm'),'name_field_middle':("r6 - Расстояние м/у 5 кассетой и облицовкой, мм","t6 - Толщина облицовки, мм"),'name_field_end':("r6 - Расстояние м/у 5 кассетой и облицовкой, мм","t6 - Толщина облицовки, мм")},

    }

    for kolich, values in dict_settings_kolichestvo_kasset.items():
        list_fields = values['tuple_fields_show']
        for i, field in enumerate(list_fields) :
            row = table_input_data.get_row_by_unique_name(field)
            if kolich <= new_val:  # show
                if kolich < new_val:
                    row.set_new_val('header', values['name_field_middle'][i])
                else:
                    row.set_new_val('header', values['name_field_end'][i])
                row.style_cell('val', text_color=ft.Colors.ON_SURFACE, disabled=False, row_height=50)
                row.set_visible()
                if row.get_val('val') == 0:
                    row.set_default_val('val')

            else:
                row.set_new_val('val', 0)
                row.set_new_val('header', '')
                row.style_cell('val', text_color=ft.Colors.TRANSPARENT, disabled=True, row_height=0)
                row.set_visible(False)

def oform_kolichestvo_stupenej_drosselirovaniya_sht(cell:CMF._Cell_data,new_val):
    row_data: CMF.Row_data = cell.parent_row
    table_input_data:CMF.Table_data = row_data.parent_table_data
    row = table_input_data.get_row_by_unique_name('pokazatel_gradienta')
    if new_val == 1:
        row.set_default_val('val')
        row.set_new_val('header', 'Показатель градиента ')
        row.style_cell('val', text_color=ft.Colors.ON_SURFACE, disabled=False, row_height=50)
        row.set_visible()
    else:
        row.set_new_val('val', 0)
        row.set_new_val('header', '')
        row.style_cell('val', text_color=ft.Colors.TRANSPARENT, disabled=True, row_height=0)
        row.set_visible(False)

def oform_edinica_rashoda(cell:CMF._Cell_data,new_val):
    row_data: CMF.Row_data = cell.parent_row
    table_input_data:CMF.Table_data = row_data.parent_table_data
    row = table_input_data.get_row_by_unique_name('rashod')
    row.set_new_val('dimension', new_val)
