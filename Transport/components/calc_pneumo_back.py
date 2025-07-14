import os

import components.common_funcs as CMF
from components.common_funcs import Table_data
import flet as ft
import math
import project_cust_38.Cust_Functions as F
import copy
import project_cust_38.Cust_Excel as CEX
import data_class as DTCLS
import project_cust_38.Cust_SQLite as CSQ
import Config.srv_config as SRVCFG


class Cust_module_params():
    def __init__(self):
        self.ver_tbls_data = 1
        self.input_tbl_editbl: Table_data | None = None
        self.input_tbl_not_editbl: Table_data | None = None
        self.output_tbl: Table_data | None = None
        self.filtr_seach_history: str = ''

TBL_INPUT = Table_data()
TBL_INPUT.append_column_desc(name='name', header='Имя', hidden=True, editable=False, unique=True)
TBL_INPUT.append_column_desc(name='header', header='Параметр', hidden=False, editable=False, width=300)
TBL_INPUT.append_column_desc(name='dimension', header='Ед.изм', hidden=False, editable=False)
TBL_INPUT.append_column_desc(name='val', header='Значение', hidden=False, editable=True, width=130)

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

OUTPUT_PARAMS = {
    "pump_mass_vol": {
        "header": "Массовый объем насоса",
        "dimension": "кг",
        "comment": None
    },
    "pump_cycles": {
        "header": "Количество циклов насоса",
        "dimension": "цикл/ч",
        "comment": None
    },
    "solid_flow": {
        "header": "Расход твердого вещества",
        "dimension": "м3/ч",
        "comment": 'Возможно исходя формулы для Расход воздуха, там используется Расход золы системы (исправлено)'
    },
    "air_flow": {
        "header": "Расход воздуха",
        "dimension": "м3/мин",
        "comment": ""
    },
    "pipe_diam": {
        "header": "Диаметр трубы",
        "dimension": "м",
        "comment": ""
    },
    "reynolds_num": {
        "header": "Число Рейнольдса(Re)",
        "dimension": "",
        "comment": ""
    },
    "pipe_resist_coef": {
        "header": "Коэффициент сопротивления трубы",
        "dimension": "",
        "comment": None
    },
    "froude_num": {
        "header": "Число Фруда (Fr)",
        "dimension": "",
        "comment": None
    },
    "pipe_equiv_len": {
        "header": "Приведенная длина трассы",
        "dimension": "м",
        "comment": None
    },
    "air_press_loss": {
        "header": "Потеря давления воздуха",
        "dimension": "мм.вод.ст.",
        "comment": None
    },
    "mat_press_loss": {
        "header": "Потеря давления материала",
        "dimension": "мм.вод.ст.",
        "comment": None
    },
    "settling_vel": {
        "header": "Скорость витания",
        "dimension": "м/с",
        "comment": None
    },
    "vert_lift_loss": {
        "header": "Потеря давления на подъем верт.участка",
        "dimension": "мм.вод.ст.",
        "comment": 'Формула возможно не корректна (деление Скорость воздуха на себя, Скорость витания  не учтена) (исправлено)'
    },
    "mat_accel_loss": {
        "header": "Потеря давления на разгон материала",
        "dimension": "мм.вод.ст.",
        "comment": None
    },
    "total_press_loss": {
        "header": "Общая потеря давления на трассе",
        "dimension": "мм.вод.ст.",
        "comment": None
    },
    "blower_press": {
        "header": "Давление,создающееся в воздуходуйной машине",
        "dimension": "Атм",
        "comment": "Потери давления в компрессоре в кг/см² несовместим с Рабочее давление в начальной точке трубопровода в атм. (исправлено)"
    },
    "pipe_start_press": {
        "header": "Рабочее давление в начальной точке трубопровода",
        "dimension": "Атм",
        "comment": None
    },
    "blower_theor_power": {
        "header": "Теоретическая работа воздуходуйной машины",
        "dimension": "кгм/м3",
        "comment": None
    },
    "blower_act_power": {
        "header": "Потребляемая мощность воздуходуйной машины",
        "dimension": "кВт",
        "comment": None
    },
    "air_vel_start": {
        "header": "Скорость воздуха в начале трубы",
        "dimension": "м/с",
        "comment": None
    },
    "air_vel_end": {
        "header": "Скорость воздуха в конце трубы",
        "dimension": "м/с",
        "comment": "Проверить"
    },
    "system_temp_k": {
        "header": "Температура системы К",
        "dimension": "К",
        "comment": None
    },
    "viscosity_150C": {
        "header": "Динамическая вязкость при 150 С",
        "dimension": "Па*с",
        "comment": None
    },
    "air_density_150C": {
        "header": "Плотность воздуха при 150 С",
        "dimension": "кг/м3",
        "comment": 'должны использоваться Кельвины (K)'
    },
    "pump_purge_time": {
        "header": "Время продувки насоса",
        "dimension": "сек",
        "comment": None
    },
    "pump_fill_time": {
        "header": "Время заполнения насоса",
        "dimension": "сек",
        "comment": None
    },
    "load_time": {
        "header": "Время нагрузки",
        "dimension": "сек",
        "comment": None
    },
    "unload_time": {
        "header": "Время разгрузки",
        "dimension": "сек",
        "comment": None
    },
    "wait_time": {
        "header": "Остальное время ожидания",
        "dimension": "сек",
        "comment": None
    },
    "avg_part_size": {
        "header": "Средний размер частиц",
        "dimension": "мм",
        "comment": None
    }
}

list_dicts_data_input = [
    {'name': 'pump_volume', 'header': 'Объем насоса', 'min_max_list': (0.1, 10), 'default_val': 0, 'dimension': 'м3',
     'data_type': float, 'comment': None, },
    {'name': 'pump_purge_time', 'header': 'Время продувки насоса', 'min_max_list': (5, 60), 'default_val': 0,
     'dimension': 'сек', 'data_type': float, 'comment': None, },
    {'name': 'pump_fill_time', 'header': 'Время заполнения насоса', 'min_max_list': (60, 600), 'default_val': 0,
     'dimension': 'сек', 'data_type': float, 'comment': None, },
    {'name': 'load_time', 'header': 'Время нагрузки', 'min_max_list': (5, 30), 'default_val': 0, 'dimension': 'сек',
     'data_type': float, 'comment': None, },
    {'name': 'unload_time', 'header': 'Время разгрузки', 'min_max_list': (10, 60), 'default_val': 0, 'dimension': 'сек',
     'data_type': float, 'comment': None, },
    {'name': 'wait_time', 'header': 'Остальное время ожидания', 'min_max_list': (5, 30), 'default_val': 0,
     'dimension': 'сек', 'data_type': float, 'comment': None, },
    {'name': 'avg_particle_size', 'header': 'Средний размер частиц', 'min_max_list': (0.000001, 0.001),
     'default_val': 0, 'dimension': 'м', 'data_type': float, 'comment': None, 'accuracy':6 },
    {'name': 'material_density', 'header': 'Плотность материала', 'min_max_list': (500, 3000), 'default_val': 0,
     'dimension': 'кг/м3', 'data_type': float, 'comment': None, },
    {'name': 'bulk_density', 'header': 'Насыпная плотность', 'min_max_list': (300, 1500), 'default_val': 0,
     'dimension': 'кг/м3', 'data_type': float, 'comment': None, },
    {'name': 'system_temp', 'header': 'Температура системы C', 'min_max_list': (0, 200), 'default_val': 0,
     'dimension': 'С', 'data_type': float, 'comment': None, },
    {'name': 'pipe_start_pressure', 'header': 'Рабочее давление в начальной точке трубопровода',
     'min_max_list': (1, 10), 'default_val': 0, 'dimension': 'Атм', 'data_type': float, 'comment': None, },
    {'name': 'gas_constant', 'header': 'Газовая постоянная', 'min_max_list': None, 'default_val': 287,
     'dimension': 'Дж/кг*К', 'data_type': float, 'comment': None, },
    {'name': 'pipe_horiz_length', 'header': 'Длина  горизонтального трубопровода', 'min_max_list': (1, 500),
     'default_val': 0, 'dimension': 'м', 'data_type': float, 'comment': None, },
    {'name': 'pipe_vert_length', 'header': 'Длина вертикального участка', 'min_max_list': (1, 100), 'default_val': 0,
     'dimension': 'м', 'data_type': float, 'comment': None, },
    {'name': 'ash_field_rate', 'header': 'Расход золы поля', 'min_max_list': (100, 10000), 'default_val': 0,
     'dimension': 'кг/ч', 'data_type': float, 'comment': None, },
    {'name': 'ash_system_rate', 'header': 'Расход золы системы', 'min_max_list': (100, 15000), 'default_val': 0,
     'dimension': 'кг/ч', 'data_type': float, 'comment': None, },
    {'name': 'gravity', 'header': 'Ускорение свободного падения', 'min_max_list': None, 'default_val': 9.81,
     'dimension': 'м/с2', 'data_type': float, 'comment': None, },
    {'name': 'mass_concentration', 'header': 'Массовая концентрация ', 'min_max_list': (1, 30), 'default_val': 0,
     'dimension': 'кг/кг', 'data_type': float, 'comment': "Принимается от 15 до 25 для пылевидных материалов", },
    {'name': 'pi', 'header': 'Число ПИ', 'min_max_list': None, 'default_val': 3.14, 'dimension': '', 'data_type': float,
     'comment': None, },
    {'name': 'air_velocity', 'header': 'Скорость воздуха', 'min_max_list': (20, 30), 'default_val': 0,
     'dimension': 'м/с', 'data_type': float, 'comment': "Принимается от 20 до 30 м/с для пылевидных материалов", },
    {'name': 'material_resistance_coef', 'header': 'Коэффициент сопротивления материала', 'min_max_list': None,
     'default_val': 0, 'dimension': '', 'data_type': float, 'comment': "Принимается 0,023 для золы по таблице", },
    {'name': 'turns_90deg', 'header': 'Количество поворотов трассы 90гр.', 'min_max_list': [10, 20], 'default_val': 0,
     'dimension': 'шт.', 'data_type': int, 'comment': None, },
    {'name': 'turns_60deg', 'header': 'Количество поворотов трассы 60гр.', 'min_max_list': (0, 10), 'default_val': 0,
     'dimension': 'шт.', 'data_type': int, 'comment': None, },
    {'name': 'turns_30deg', 'header': 'Количество поворотов трассы 30гр.', 'min_max_list': (0, 10), 'default_val': 0,
     'dimension': 'шт.', 'data_type': int, 'comment': None, },
    {'name': 'flow_switchers', 'header': 'Количество переключателей потока на трассе', 'min_max_list': (0, 5),
     'default_val': 0, 'dimension': 'шт.', 'data_type': int, 'comment': None, },
    {'name': 'accel_zone_coef', 'header': 'Коэффицент сопротивления разгонного участка', 'min_max_list': (1.5, 3.0),
     'default_val': 2.2, 'dimension': '', 'data_type': float,
     'comment': "Приниматеся 2,2 для золы и диаметра трубы 100мм", },
    {'name': 'compressor_efficiency', 'header': 'КПД компрессора', 'min_max_list': (0.55, 0.75), 'default_val': 0.65,
     'dimension': '', 'data_type': float, 'comment': "Принимается от 0,55 до 0,75", },
    {'name': 'compressor_pressure_loss', 'header': 'Потери давления в компрессоре', 'min_max_list': None,
     'default_val': 0.3, 'dimension': 'кг/см2', 'data_type': float, 'comment': "Принимается равным 0,3", },
    {'name': 'atm_pressure', 'header': 'Атмосферное давление', 'min_max_list': None, 'default_val': 1.033,
     'dimension': 'кг/см2', 'data_type': float, 'comment': None, },
    {'name': 'safety_factor', 'header': 'Коэффициент запаса', 'min_max_list': (1.15, 1.25), 'default_val': 1.2,
     'dimension': '', 'data_type': float,
     'comment': "коэффициент, учитывающий потери в загрузочном устройстве,принимаемый 1,15-1,25", },
    ]


def calc_new_tbl_input():
    new_tbl_input = copy.deepcopy(TBL_INPUT)
    for item in list_dicts_data_input:
        name = item['name']
        header = item['header']
        dimension = item['dimension']

        data_type = None
        if 'data_type' in item:
            data_type = item['data_type']

        val = 0
        if data_type is str:
            val = ''

        if 'default_val' in item:
            val = item['default_val']

        min_max_list = None
        if "min_max_list" in item:
            min_max_list = item["min_max_list"]
            if isinstance(min_max_list, tuple) and data_type == None:
                data_type = int

        comment = None
        if "comment" in item:
            comment = item["comment"]
        accuracy = 5
        if 'accuracy' in item:
            accuracy = item['accuracy']
        row = CMF.Row_data()
        row.append(name, CMF.Cell_description())
        row.append(header, CMF.Cell_description())
        row.append(dimension, CMF.Cell_description())
        row.append(val, CMF.Cell_description(min_max_list, comment=comment, data_type=data_type, accuracy=accuracy))
        new_tbl_input.add_row(row)
    return new_tbl_input


new_tbl_input = calc_new_tbl_input()


def generate_input_data(fnc_onchange, ref, default_vals: dict | None = None) -> (ft.DataTable, Table_data):
    if default_vals:
        new_tbl_input.set_vals_into_field(default_vals, 'val')
    return CMF.generate_param_table(new_tbl_input, ref=ref, fnc_onchange=fnc_onchange), new_tbl_input


def prepare_calc_new_data(data: list[dict], Data: DTCLS.Data_page) -> list[dict] | dict:
    data_params = {_['Имя']: F.valm(_['Значение']) for _ in data}
    #data_params = F.load_file_pickle('test_data_params.pickle')
    Data.Data_module.cust_data: Cust_module_params
    Data.Data_module.cust_data.input_tbl_not_editbl = copy.deepcopy(Data.Data_module.cust_data.input_tbl_editbl)
    Data.Data_module.cust_data.input_tbl_not_editbl.set_vals_into_field(data_params, 'val')
    Data.Data_module.cust_data.input_tbl_not_editbl.set_lock_vals('val', True)
    rez = calc_new_data(data_params)
    return rez
    # F.save_file_pickle('test_data_params.pickle',{_['Имя']:F.valm(_['Значение']) for _ in data})


def generate_rez_tbl(e: ft.ControlEvent, tbl: ft.DataTable, ref_out) -> (
ft.DataTable | None, Table_data | None, bool | None):
    Data: DTCLS.Data_page = e.page.data
    data = CMF.datatable_to_dicts(tbl)
    new_data = prepare_calc_new_data(data, Data)
    if not len(new_data):
        return
    if isinstance(new_data, list):
        datatable, tbl_output = make_err_tbl(new_data, ref_out)
        return datatable, new_data, False
    elif isinstance(new_data, dict):
        datatable, tbl_output = make_res_tbl(new_data, ref_out)
        Data.Data_module.cust_data.output_tbl = tbl_output
        return datatable, new_data, True
        # return  CMF.generate_param_table(Data.Data_module.cust_data.input_tbl_not_editbl,ref_out), new_data, True

    return None, None, None


def make_res_tbl(data: dict, ref_out=None) -> (ft.DataTable, CMF.Table_data):
    new_tbl_output: Table_data = copy.deepcopy(TBL_OUTPUT)
    for name, val in data.items():
        row = CMF.Row_data()
        row.append(name, CMF.Cell_description())
        row.append(OUTPUT_PARAMS[name]['header'], CMF.Cell_description())
        row.append(val, CMF.Cell_description(accuracy=5, data_type=float))
        row.append(OUTPUT_PARAMS[name]['dimension'], CMF.Cell_description())
        comment = ''
        if OUTPUT_PARAMS[name]['comment']:
            comment = OUTPUT_PARAMS[name]['comment']
        row.append(comment, CMF.Cell_description())

        new_tbl_output.add_row(row)

    tbl = CMF.generate_param_table(new_tbl_output, ref=ref_out)
    return tbl, new_tbl_output


def make_err_tbl(data, ref_out=None) -> (ft.DataTable, CMF.Table_data):
    new_tbl_output_err = copy.deepcopy(TBL_OUTPUT_ERR)
    for i, item in enumerate(data):
        row = CMF.Row_data()
        row.append(str(i + 1), CMF.Cell_description())
        row.append(item['header'], CMF.Cell_description())
        row.append(item['val'], CMF.Cell_description())
        row.append(item['Exception'], CMF.Cell_description())

        new_tbl_output_err.add_row(row)

    tbl = CMF.generate_param_table(new_tbl_output_err, ref=ref_out)
    return tbl, new_tbl_output_err


def load_from_db_history_calc(Data: DTCLS.Data_page, s_num: int) -> (CMF.Table_data, CMF.Table_data):
    data = CSQ.custom_request_c(Data.Data_user.db_flet, f"""SELECT data FROM
                        pneumatic_transport_history WHERE s_num == {s_num}""", one=True, one_column=True, hat_c=False)
    if not data:
        return False
    data_obj = F.from_binary_pickle(data[0])
    ver = data_obj['ver']
    input_tbl = data_obj['input_tbl']
    output_tbl = data_obj['output_tbl']

    return input_tbl, output_tbl


def get_name_new_calc(prefix=""):
    return f'calc_{prefix}_{F.now("%Y-%m-%d(%H%M%S)")}'


def generate_rezult_data_for_save(name: str, input_tbl: ft.DataTable, output_tbl: ft.DataTable) -> dict:
    list_dict_rez_input = CMF.datatable_to_dicts(input_tbl)
    list_dict_rez_output = CMF.datatable_to_dicts(output_tbl)
    return {'name': name, 'input': list_dict_rez_input, 'output': list_dict_rez_output}


def get_vals_from_input_data_tbl(tbl: ft.DataTable):
    tbl_pre = CMF.datatable_to_dicts(tbl)
    data_params = {_['Имя']: F.valm(_['Значение']) for _ in tbl_pre}
    return data_params


def save_exel(list_dict_rez_input: list, list_dict_rez_output: list, name: str, dir_save: str) -> str | bool:
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
    # folder = dir_save
    name_file = f'{name}.docx'
    path = os.path.join(dir_save, name_file)
    template_path = os.path.join(SRVCFG.DOCX_TEMPLATES_PATH, 'report.docx')
    rez = CEX.make_docx_report(name, list_dict_rez_input, list_dict_rez_output, output_docx_path=path,
                           template_name=template_path)
    # rez = CEX.zap_spis(rez_spis, folder, name_file, '1', 1, 1, return_putf=True)
    if not rez:
        return False
    return rez


def file_into_blob(putf):
    return F.file_into_blob(putf)


def make_history_tbl_data(Data: DTCLS.Data_page):
    TBL_HISTORY_TMP = copy.deepcopy(TBL_HISTORY)
    if Data.Data_module.cust_data.filtr_seach_history == "":
        where = ''
    else:
        where = f'and name like "%{Data.Data_module.cust_data.filtr_seach_history}%"'
    list_calcs = CSQ.custom_request_c(Data.Data_user.db_flet,
                                      f"""SELECT * FROM pneumatic_transport_history WHERE ip = '{Data.Data_user.ip}' {where} LIMIT 20;""",
                                      rez_dict=True)
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
    if Module_data.input_tbl_not_editbl == None or Module_data.output_tbl == None:
        return False
    data_save = {'ver': Module_data.ver_tbls_data, 'input_tbl': Module_data.input_tbl_not_editbl,
                 'output_tbl': Module_data.output_tbl}
    row = [F.now(), name, Data.Data_user.ip, F.to_binary_pickle(data_save)]
    rez = CSQ.custom_request_c(Data.Data_user.db_flet, f"""INSERT INTO pneumatic_transport_history 
                        (date, 
                            name, 
                            ip, 
                            data)
                              VALUES ({CSQ.questions_for_mask(row)})""", list_of_lists_c=[row])
    return rez


def calc_new_data(input_data: dict) -> list | dict:
    list_err = []
    calculated = {}

    # Константы
    constants = {
        'gas_constant': 287,
        'gravity': 9.81,
        'pi': 3.14,
        'accel_zone_coef': 2.2,
        'compressor_efficiency': 0.65,
        'compressor_pressure_loss': 0.3,
        'atm_pressure': 1.033,
        'safety_factor': 1.2
    }

    # Объединяем входные данные с константами
    params = {**constants, **input_data}

    # Вспомогательные функции проверки
    def check_positive(name, value, header):
        if value <= 0:
            list_err.append({
                'header': header,
                'val': value,
                'Exception': f"{header} должно быть положительным числом"
            })
            return False
        return True

    def check_range(name, value, min_val, max_val, header):
        if not (min_val <= value <= max_val):
            list_err.append({
                'header': header,
                'val': value,
                'Exception': f"{header} должно быть в диапазоне [{min_val}, {max_val}]"
            })
            return False
        return True

    # Функции расчета для каждого параметра OUTPUT

    def calc_pump_mass_vol():
        def check_pump_mass_vol():
            one = check_positive('pump_volume', params.get('pump_volume', 0), 'Объем насоса')
            two = check_positive('bulk_density', params.get('bulk_density', 0), 'Насыпная плотность')
            return one and two

        if not check_pump_mass_vol():
            return None

        return params['pump_volume'] * params['bulk_density']

    def calc_pump_cycles():
        def check_pump_cycles():
            return check_positive('ash_field_rate', params.get('ash_field_rate', 0), 'Расход золы поля')

        if not check_pump_cycles():
            return None
        pump_mass_vol = calc_pump_mass_vol()
        if pump_mass_vol is None:
            return None
        return params['ash_field_rate'] / pump_mass_vol

    def calc_solid_flow():
        def check_solid_flow():
            return check_positive('ash_system_rate', params.get('ash_system_rate', 0), 'Расход золы системы')
        def check_bulk_density():
            return check_positive('bulk_density', params.get('bulk_density', 0), 'Насыпная плотность')

        if not check_solid_flow() or not check_bulk_density():
            return None

        return params['ash_system_rate'] / params['bulk_density']

    def calc_air_flow():
        def check_air_flow():
            return (check_positive('ash_system_rate', params.get('ash_system_rate', 0), 'Расход золы системы') and
                    check_positive('mass_concentration', params.get('mass_concentration', 0), 'Массовая концентрация'))

        if not check_air_flow():
            return None

        # Рассчитываем плотность воздуха при 150°C
        air_density = 1.293 * 273 / (273 + params['system_temp'])
        return params['ash_system_rate'] / (60 * air_density *  params['mass_concentration'])

    def calc_pipe_diam():
        def check_pipe_diam():
            return (check_positive('air_flow', params.get('air_flow', 0), 'Расход воздуха') and
                    check_positive('air_velocity', params.get('air_velocity', 0), 'Скорость воздуха') and
                    check_range('air_velocity', params.get('air_velocity', 0), 20, 30, 'Скорость воздуха'))

        if not check_pipe_diam():
            return None

        air_flow = calc_air_flow()
        if air_flow is None:
            return None
        return math.sqrt(4 * air_flow / (60 * params['pi'] * params['air_velocity']))

    def calc_reynolds_num():
        def check_reynolds_num():
            return (check_positive('air_velocity', params.get('air_velocity', 0), 'Скорость воздуха') and
                    check_positive('pipe_diam', params.get('pipe_diam', 0), 'Диаметр трубы'))

        if not check_reynolds_num():
            return None
        viscosity = calc_viscosity_150C()
        pipe_diam = calc_pipe_diam()
        if pipe_diam is None or viscosity is None:
            return None

        # Рассчитываем вязкость воздуха при 150°C
        temp_k = 273 + params['system_temp']
        viscosity = 1.458e-6 * (temp_k ** 1.5) / (temp_k + 110.4)

        # Плотность воздуха при 150°C
        air_density = 1.293 * 273 / (273 + params['system_temp'])

        return params['air_velocity'] * pipe_diam * air_density / viscosity

    def calc_pipe_resist_coef():
        def check_pipe_resist_coef():
            return check_positive('reynolds_num', params.get('reynolds_num', 0), 'Число Рейнольдса')

        if not check_pipe_resist_coef():
            return None

        reynolds_num = calc_reynolds_num()
        if reynolds_num is None:
            return None
        return 0.0052 + 0.5 / (reynolds_num ** 0.32)

    def calc_froude_num():
        def check_froude_num():
            return (check_positive('air_velocity', params.get('air_velocity', 0), 'Скорость воздуха') and
                    check_positive('pipe_diam', params.get('pipe_diam', 0), 'Диаметр трубы') and
                    check_positive('gravity', params.get('gravity', 0), 'Ускорение свободного падения'))

        if not check_froude_num():
            return None

        pipe_diam = calc_pipe_diam()
        if pipe_diam is None:
            return None
        return params['air_velocity'] / math.sqrt(pipe_diam * params['gravity'])

    def calc_pipe_equiv_len():
        def check_pipe_equiv_len():
            return (check_positive('pipe_horiz_length', params.get('pipe_horiz_length', 0),
                                   'Длина горизонтального трубопровода') and
                    check_positive('pipe_vert_length', params.get('pipe_vert_length', 0),
                                   'Длина вертикального участка') and
                    check_positive('turns_90deg', params.get('turns_90deg', 0), 'Количество поворотов 90°') and
                    check_positive('turns_60deg', params.get('turns_60deg', 0), 'Количество поворотов 60°') and
                    check_positive('turns_30deg', params.get('turns_30deg', 0), 'Количество поворотов 30°') and
                    check_positive('flow_switchers', params.get('flow_switchers', 0),
                                   'Количество переключателей потока'))

        if not check_pipe_equiv_len():
            return None

        return (params['pipe_horiz_length'] + params['pipe_vert_length'] +
                ((params['turns_90deg'] + params['turns_60deg'] + params['turns_30deg']) * 10) +
                (params['flow_switchers'] * 10))

    def calc_air_press_loss():
        def check_air_press_loss():
            return (check_positive('pipe_resist_coef', params.get('pipe_resist_coef', 0),
                                   'Коэффициент сопротивления трубы') and
                    check_positive('pipe_equiv_len', params.get('pipe_equiv_len', 0), 'Приведенная длина трассы') and
                    check_positive('pipe_diam', params.get('pipe_diam', 0), 'Диаметр трубы') and
                    check_positive('air_velocity', params.get('air_velocity', 0), 'Скорость воздуха'))

        if not check_air_press_loss():
            return None

        pipe_resist_coef = calc_pipe_resist_coef()
        pipe_equiv_len = calc_pipe_equiv_len()
        pipe_diam = calc_pipe_diam()

        if pipe_resist_coef is None or pipe_equiv_len is None or pipe_diam is None:
            return None

        # Плотность воздуха при 150°C
        air_density = 1.293 * 273 / (273 + params['system_temp'])

        return (pipe_resist_coef * (pipe_equiv_len / pipe_diam) *
                ((params['air_velocity'] ** 2) * air_density / (2 * params['gravity'])))

    def calc_mat_press_loss():
        def check_mat_press_loss():
            return (check_positive('material_resistance_coef', params.get('material_resistance_coef', 0),
                                   'Коэффициент сопротивления материала') and
                    check_positive('mass_concentration', params.get('mass_concentration', 0),
                                   'Массовая концентрация') and
                    check_positive('pipe_equiv_len', params.get('pipe_equiv_len', 0), 'Приведенная длина трассы') and
                    check_positive('air_velocity', params.get('air_velocity', 0), 'Скорость воздуха') and
                    check_positive('pipe_diam', params.get('pipe_diam', 0), 'Диаметр трубы'))

        if not check_mat_press_loss():
            return None

        pipe_equiv_len = calc_pipe_equiv_len()
        pipe_diam = calc_pipe_diam()

        if pipe_equiv_len is None or pipe_diam is None:
            return None

        # Плотность воздуха при 150°C
        air_density = 1.293 * 273 / (273 + params['system_temp'])

        return ((params['material_resistance_coef'] * params['mass_concentration']) *
                (pipe_equiv_len * (params['air_velocity'] ** 2) * air_density) /
                (pipe_diam * 2 * params['gravity']))

    def calc_settling_vel():
        def check_settling_vel():
            return (check_positive('avg_particle_size', params.get('avg_particle_size', 0), 'Средний размер частиц') and
                    check_positive('material_density', params.get('material_density', 0), 'Плотность материала') and
                    check_positive('gravity', params.get('gravity', 0), 'Ускорение свободного падения'))

        if not check_settling_vel():
            return None

        # Рассчитываем вязкость воздуха при 150°C
        temp_k = 273 + params['system_temp']
        viscosity = 1.458e-6 * (temp_k ** 1.5) / (temp_k + 110.4)

        return ((params['avg_particle_size'] ** 2) * params['material_density'] * params['gravity']) / (18 * viscosity)

    def calc_vert_lift_loss():
        def check_vert_lift_loss():
            return (check_positive('pipe_vert_length', params.get('pipe_vert_length', 0),
                                   'Длина вертикального участка') and
                    check_positive('mass_concentration', params.get('mass_concentration', 0),
                                   'Массовая концентрация') and
                    check_positive('air_velocity', params.get('air_velocity', 0), 'Скорость воздуха') and
                    check_positive('settling_vel', params.get('settling_vel', 0), 'Скорость витания'))

        if not check_vert_lift_loss():
            return None

        settling_vel = calc_settling_vel()
        if settling_vel is None:
            return None

        # Плотность воздуха при 150°C
        air_density = 1.293 * 273 / (273 + params['system_temp'])
        vert_lift_loss = (params['pipe_vert_length'] * air_density * params['mass_concentration'] *
            (1 - (settling_vel / params['air_velocity'])))
        return vert_lift_loss

    def calc_mat_accel_loss():
        def check_mat_accel_loss():
            return (check_positive('accel_zone_coef', params.get('accel_zone_coef', 0),
                                   'Коэффициент сопротивления разгонного участка') and
                    check_positive('mass_concentration', params.get('mass_concentration', 0),
                                   'Массовая концентрация') and
                    check_positive('air_velocity', params.get('air_velocity', 0), 'Скорость воздуха'))

        if not check_mat_accel_loss():
            return None

        # Плотность воздуха при 150°C
        air_density = 1.293 * 273 / (273 + params['system_temp'])

        return (params['accel_zone_coef'] * params['mass_concentration'] *
                ((params['air_velocity'] ** 2) * air_density) / (2 * params['gravity']))

    def calc_total_press_loss():
        def check_total_press_loss():
            return (check_positive('air_press_loss', params.get('air_press_loss', 0), 'Потеря давления воздуха') and
                    check_positive('mat_press_loss', params.get('mat_press_loss', 0), 'Потеря давления материала') and
                    check_positive('vert_lift_loss', params.get('vert_lift_loss', 0), 'Потеря давления на подъем') and
                    check_positive('mat_accel_loss', params.get('mat_accel_loss', 0),
                                   'Потеря давления на разгон материала'))

        if not check_total_press_loss():
            return None

        air_press_loss = calc_air_press_loss()
        mat_press_loss = calc_mat_press_loss()
        vert_lift_loss = calc_vert_lift_loss()
        mat_accel_loss = calc_mat_accel_loss()

        if air_press_loss is None or mat_press_loss is None or vert_lift_loss is None or mat_accel_loss is None:
            return None

        return air_press_loss + mat_press_loss + vert_lift_loss + mat_accel_loss

    def calc_blower_press():
        def check_blower_press():
            return (check_positive('total_press_loss', params.get('total_press_loss', 0), 'Общая потеря давления') and
                    check_positive('safety_factor', params.get('safety_factor', 0), 'Коэффициент запаса') and
                    check_range('safety_factor', params.get('safety_factor', 0), 1.15, 1.25, 'Коэффициент запаса'))

        if not check_blower_press():
            return None

        total_press_loss = calc_total_press_loss()
        if total_press_loss is None:
            return None

            # Приводим все единицы к атм:
        compressor_loss_atm = params['compressor_pressure_loss'] / 1.0332  # кг/см² → атм

        return params['pipe_start_pressure'] * params['safety_factor'] + compressor_loss_atm

    def calc_blower_theor_power():
        def check_blower_theor_power():
            return (check_positive('blower_press', params.get('blower_press', 0), 'Давление в воздуходуйной машине') and
                    check_positive('atm_pressure', params.get('atm_pressure', 0), 'Атмосферное давление'))

        if not check_blower_theor_power():
            return None

        blower_press = calc_blower_press()
        if blower_press is None:
            return None

        return 23030 * params['atm_pressure'] * math.log10(blower_press / params['atm_pressure'])

    def calc_pipe_start_press():
        def check_pipe_start_press():
            return (check_positive('pipe_start_pressure', params.get('pipe_start_pressure', 0),
                                   'Рабочее давление в начальной точке трубопровода'))

        if not check_pipe_start_press():
            return None
        return params['pipe_start_pressure']

    def calc_blower_act_power():
        def check_blower_act_power():
            return (check_positive('blower_theor_power', params.get('blower_theor_power', 0),
                                   'Теоретическая мощность') and
                    check_positive('air_flow', params.get('air_flow', 0), 'Расход воздуха') and
                    check_positive('compressor_efficiency', params.get('compressor_efficiency', 0),
                                   'КПД компрессора') and
                    check_range('compressor_efficiency', params.get('compressor_efficiency', 0), 0.55, 0.75,
                                'КПД компрессора'))

        if not check_blower_act_power():
            return None

        blower_theor_power = calc_blower_theor_power()
        air_flow = calc_air_flow()

        if blower_theor_power is None or air_flow is None:
            return None

        return (blower_theor_power * air_flow) / (60 * 102 * params['compressor_efficiency'])

    def calc_air_vel_start():
        def check_air_vel_start():
            return (check_positive('solid_flow', params.get('solid_flow', 0), 'Расход твердого вещества') and
                    check_positive('pipe_diam', params.get('pipe_diam', 0), 'Диаметр трубы') and
                    check_positive('mass_concentration', params.get('mass_concentration', 0), 'Массовая концентрация'))

        if not check_air_vel_start():
            return None


        pipe_diam = calc_pipe_diam()

        if pipe_diam is None:
            return None

        # Плотность воздуха при 150°C
        air_density = 1.293 * 273 / (273 + params['system_temp'])

        return 4 * params['ash_field_rate'] / (params['pi'] * (pipe_diam ** 2) * params['mass_concentration'] * air_density * 3600)

    def calc_air_vel_end():
        def check_air_vel_end():
            return (check_positive('air_flow', params.get('air_flow', 0), 'Расход воздуха') and
                    check_positive('pipe_diam', params.get('pipe_diam', 0), 'Диаметр трубы') and
                    check_positive('pipe_start_pressure', params.get('pipe_start_pressure', 0), 'Рабочее давление'))

        if not check_air_vel_end():
            return None

        air_flow = calc_air_flow()
        pipe_diam = calc_pipe_diam()

        if air_flow is None or pipe_diam is None:
            return None

        # Плотность воздуха при 150°C
        air_density = 1.293 * 273 / (273 + params['system_temp'])

        # Переводим давление из Атм в Па (1 Атм = 101325 Па)
        start_pressure_pa = params['pipe_start_pressure'] * 101325

        # Физически точный расчёт (в м/с):
        #return  (4 * air_flow * 287 * params['system_temp_k']) /        (60 * params['pi'] * pipe_diam**2 * params['pipe_start_pressure'] * 101325)
        return  (100000 * 4 * air_flow * 60) /        (params['pi'] * pipe_diam**2 * 3600 * air_density * params['system_temp_k']*  params['gas_constant'])

    def calc_system_temp_k():
        return 273 + params['system_temp']

    def calc_viscosity_150C():
        temp_k =  params['system_temp_k']
        return 1.458e-6 * (temp_k ** 1.5) / (temp_k + 110.4)

    def calc_air_density_150C():
        """Плотность воздуха (кг/м³) при 150°C.
          Температура system_temp подается в °C и преобразуется в K."""
        return 1.293 * 273 / (params['system_temp_k'])

    def calc_pump_purge_time():
        return params['pump_purge_time']

    def calc_pump_fill_time():
        return params['pump_fill_time']

    def calc_load_time():
        return params['load_time']

    def calc_unload_time():
        return params['unload_time']

    def calc_wait_time():
        return params['wait_time']

    def calc_avg_part_size():
        return params['avg_particle_size'] * 1000

    def united_params_calculated():
        for k, v in calculated.items():
            if v == None:
                continue
            params[k] = v

    # Выполняем расчеты
    calculated['system_temp_k'] = calc_system_temp_k()
    united_params_calculated()
    calculated['pump_mass_vol'] = calc_pump_mass_vol()
    united_params_calculated()
    calculated['pump_cycles'] = calc_pump_cycles()
    united_params_calculated()
    calculated['solid_flow'] = calc_solid_flow()
    united_params_calculated()
    calculated['air_flow'] = calc_air_flow()
    united_params_calculated()
    calculated['pipe_diam'] = calc_pipe_diam()
    united_params_calculated()
    calculated['reynolds_num'] = calc_reynolds_num()
    united_params_calculated()
    calculated['pipe_resist_coef'] = calc_pipe_resist_coef()
    united_params_calculated()
    calculated['froude_num'] = calc_froude_num()
    united_params_calculated()
    calculated['pipe_equiv_len'] = calc_pipe_equiv_len()
    united_params_calculated()
    calculated['air_press_loss'] = calc_air_press_loss()
    united_params_calculated()
    calculated['mat_press_loss'] = calc_mat_press_loss()
    united_params_calculated()
    calculated['settling_vel'] = calc_settling_vel()
    united_params_calculated()
    calculated['vert_lift_loss'] = calc_vert_lift_loss()
    united_params_calculated()
    calculated['mat_accel_loss'] = calc_mat_accel_loss()
    united_params_calculated()
    calculated['total_press_loss'] = calc_total_press_loss()
    united_params_calculated()
    calculated['blower_press'] = calc_blower_press()
    united_params_calculated()
    calculated['blower_theor_power'] = calc_blower_theor_power()
    united_params_calculated()
    calculated['pipe_start_press'] = calc_pipe_start_press()
    united_params_calculated()
    calculated['blower_act_power'] = calc_blower_act_power()
    united_params_calculated()
    calculated['air_vel_start'] = calc_air_vel_start()
    united_params_calculated()
    calculated['air_vel_end'] = calc_air_vel_end()
    united_params_calculated()
    calculated['system_temp_k'] = calc_system_temp_k()
    united_params_calculated()
    calculated['viscosity_150C'] = calc_viscosity_150C()
    united_params_calculated()
    calculated['air_density_150C'] = calc_air_density_150C()
    united_params_calculated()
    calculated['pump_purge_time'] = calc_pump_purge_time()
    united_params_calculated()
    calculated['pump_fill_time'] = calc_pump_fill_time()
    united_params_calculated()
    calculated['load_time'] = calc_load_time()
    united_params_calculated()
    calculated['unload_time'] = calc_unload_time()
    united_params_calculated()
    calculated['wait_time'] = calc_wait_time()
    united_params_calculated()
    calculated['avg_part_size'] = calc_avg_part_size()
    united_params_calculated()

    # Возвращаем результат в зависимости от наличия ошибок
    if list_err:
        return list_err
    else:
        return calculated
