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

    # Результаты расчета системы пневмотранспорта
    "P_0": {
        "header": "Плотность воздуха при нормальных условиях",
        "dimension": "кг/м3",
        "comment": "Плотность при 0°C и 101325 Па",
        "accuracy": 4
    },
    "D_2": {
        "header": "Диаметр камеры ввода",
        "dimension": "мм",
        "comment": "На уровне обреза сопла",
        "accuracy": 1
    },
    "L_2": {
        "header": "Длина камеры смешения",
        "dimension": "мм",
        "comment": "Цилиндрической части",
        "accuracy": 1
    },
    "L_3": {
        "header": "Длина конфузора",
        "dimension": "мм",
        "comment": "Диффузорной части",
        "accuracy": 1
    },
    "T_*_pneumo": {
        "header": "Температура торможения газа",
        "dimension": "К",
        "comment": "С учетом сжатия",
        "accuracy": 2
    },
    "а_кр_pneumo": {
        "header": "Критическая скорость",
        "dimension": "м/с",
        "comment": "Для условий пневмотранспорта",
        "accuracy": 2
    },
    "η_pneumo": {
        "header": "Вязкость воздуха",
        "dimension": "Па*с",
        "comment": "При рабочих условиях",
        "accuracy": 6
    },
    "p_*": {
        "header": "Абсолютное давление перед соплом",
        "dimension": "Па",
        "comment": "С учетом потерь",
        "accuracy": 0
    },
    "d_H": {
        "header": "Наружный диаметр сопла",
        "dimension": "мм",
        "comment": None,
        "accuracy": 1
    },
    "F_2": {
        "header": "Площадь сечения камеры подачи материала",
        "dimension": "м2",
        "comment": None,
        "accuracy": 6
    },
    "m": {
        "header": "Коэффициент расхода",
        "dimension": "",
        "comment": "Для сопла",
        "accuracy": 4
    },
    "F_4": {
        "header": "Площадь выходного сечения трубы",
        "dimension": "м2",
        "comment": None,
        "accuracy": 6
    },
    "F_3": {
        "header": "Площадь на выходе из диффузора",
        "dimension": "м2",
        "comment": None,
        "accuracy": 6
    },
    "F_1": {
        "header": "Площадь входного сечения",
        "dimension": "м2",
        "comment": "Для рабочего газа",
        "accuracy": 6
    },
    "F_k": {
        "header": "Критическое сечение",
        "dimension": "м2",
        "comment": "Минимальное сечение сопла",
        "accuracy": 6
    },
    "G_1": {
        "header": "Массовый расход газа через сопло",
        "dimension": "кг/с",
        "comment": None,
        "accuracy": 4
    },
    "Q_1_pneumo": {
        "header": "Объемный расход (норм. условия)",
        "dimension": "м3/мин",
        "comment": None,
        "accuracy": 2
    },
    "G_2": {
        "header": "Расход эжектируемого воздуха",
        "dimension": "кг/с",
        "comment": None,
        "accuracy": 4
    },
    "G": {
        "header": "Суммарный расход воздуха",
        "dimension": "кг/с",
        "comment": None,
        "accuracy": 4
    },
    "μ": {
        "header": "Расходная концентрация материала",
        "dimension": "кг/кг",
        "comment": "Массовая концентрация",
        "accuracy": 4
    },
    "p_1": {
        "header": "Плотность газа перед соплом",
        "dimension": "кг/м3",
        "comment": None,
        "accuracy": 4
    },
    "p_5": {
        "header": "Плотность газа на выходе",
        "dimension": "кг/м3",
        "comment": None,
        "accuracy": 4
    },
    "w_5": {
        "header": "Скорость воздуха на выходе",
        "dimension": "м/с",
        "comment": None,
        "accuracy": 2
    },
    "w_1": {
        "header": "Скорость в подводящей трубе",
        "dimension": "м/с",
        "comment": None,
        "accuracy": 2
    },
    "α": {
        "header": "Геометрический параметр эжектора",
        "dimension": "",
        "comment": None,
        "accuracy": 3
    },
    "p_3*": {
        "header": "Полное давление в камере смешения",
        "dimension": "Па",
        "comment": None,
        "accuracy": 0
    },
    "λ_3": {
        "header": "Приведенная скорость в выходном сечении камеры смешения",
        "dimension": "",
        "comment": "Подбор",
        "accuracy": 5
    },
    "q(λ_3)_theor": {
        "header": "Теоретическое q(λ3)",
        "dimension": "",
        "comment": "Газодинамическая функция",
        "accuracy": 4
    },
    "q(λ_3)_empir": {
        "header": "Эмпирическое q(λ3)",
        "dimension": "",
        "comment": "Расчетное значение",
        "accuracy": 4
    },
    "невязка_pneumo": {
        "header": "Невязка q(λ3)",
        "dimension": "",
        "comment": "Разница теоретического и эмпирического",
        "accuracy": 6
    },
    "w_3": {
        "header": "Скорость в камере смешения",
        "dimension": "м/с",
        "comment": None,
        "accuracy": 2
    },
    "pi(λ_3)": {
        "header": "Газодинамическая функция камеры смешения",
        "dimension": "",
        "comment": "Газодинамическая функция",
        "accuracy": 4
    },
    "p_3": {
        "header": "Статическое давление в камере",
        "dimension": "Па",
        "comment": None,
        "accuracy": 0
    },
    "p_3_rho": {
        "header": "Плотность в камере",
        "dimension": "кг/м3",
        "comment": None,
        "accuracy": 4
    },
    "f": {
        "header": "Параметр диффузора",
        "dimension": "",
        "comment": "Отношение площадей",
        "accuracy": 3
    },
    "ζ_диф": {
        "header": "Коэффициент сопротивления диффузора",
        "dimension": "",
        "comment": None,
        "accuracy": 3
    },
    "Δp_диф": {
        "header": "Потери давления в диффузоре",
        "dimension": "Па",
        "comment": None,
        "accuracy": 0
    },
    "p_4*": {
        "header": "Полное давление на выходе",
        "dimension": "Па",
        "comment": None,
        "accuracy": 0
    },
    "λ_4": {
        "header": "Приведенная скорость в выходном сечении диффузора",
        "dimension": "",
        "comment": "Подбор",
        "accuracy": 5
    },
    "q(λ_4)_theor": {
        "header": "Теоретическое q(λ4)",
        "dimension": "",
        "comment": "Газодинамическая функция",
        "accuracy": 4
    },
    "q(λ_4)_empir": {
        "header": "Эмпирическое q(λ4)",
        "dimension": "",
        "comment": "Расчетное значение",
        "accuracy": 4
    },
    "невязка_pneumo2": {
        "header": "Невязка q(λ4)",
        "dimension": "",
        "comment": "Разница теоретического и эмпирического",
        "accuracy": 6
    },
    "w_4": {
        "header": "Скорость в диффузоре",
        "dimension": "м/с",
        "comment": None,
        "accuracy": 2
    },
    "pi(λ_4)": {
        "header": "Газодинамическая функция диффузора",
        "dimension": "",
        "comment": "Газодинамическая функция",
        "accuracy": 4
    },
    "p_4": {
        "header": "Статическое давление в диффузоре",
        "dimension": "Па",
        "comment": None,
        "accuracy": 0
    },
    "p_4_rho": {
        "header": "Плотность в диффузоре",
        "dimension": "кг/м3",
        "comment": None,
        "accuracy": 4
    },
    "Δp_L": {
        "header": "Потери давления по длине",
        "dimension": "Па",
        "comment": None,
        "accuracy": 0
    },
    "Δp_R": {
        "header": "Потери на разгон материала",
        "dimension": "Па",
        "comment": None,
        "accuracy": 0
    },
    "Δp_H": {
        "header": "Потери на подъем",
        "dimension": "Па",
        "comment": None,
        "accuracy": 0
    },
    "Δp_м": {
        "header": "Местные потери",
        "dimension": "Па",
        "comment": None,
        "accuracy": 0
    },
    "Δp": {
        "header": "Суммарные потери давления",
        "dimension": "Па",
        "comment": "Общие потери в транспортном тракте",
        "accuracy": 0
    }
}
list_dicts_data_input = [


    # Параметры системы пневмотранспорта
    {'name': 'p_0_pneumo', 'header': 'Давление', 'min_max_list': None, 'default_val': 101325,
     'dimension': 'Па', 'data_type': float, 'comment': None},

    {'name': 't_pneumo', 'header': 'Температура сжатого воздуха', 'min_max_list': (-50, 100),
     'default_val': 20, 'dimension': '℃', 'data_type': float, 'comment': None},

    {'name': 'T_0_pneumo', 'header': 'Термодинамическая температура', 'min_max_list': None,
     'default_val': 273.15, 'dimension': 'K', 'data_type': float, 'comment': None},

    {'name': 'R_pneumo', 'header': 'Удельная газовая постоянная воздуха', 'min_max_list': None,
     'default_val': 287.1, 'dimension': 'Дж/(кг*К)', 'data_type': float, 'comment': None},

    {'name': 'k_pneumo', 'header': 'Коэффициент адиабаты', 'min_max_list': (1.1, 1.5),
     'default_val': 1.4, 'dimension': '', 'data_type': float, 'comment': None},

    {'name': 'G_t_pneumo', 'header': 'Производительность', 'min_max_list': (100, 10000),
     'default_val': 3000, 'dimension': 'кг/ч', 'data_type': float, 'comment': None},

    {'name': 'd_cp_pneumo', 'header': 'Средний диаметр частиц', 'min_max_list': (1, 500),
     'default_val': 40, 'dimension': 'мкм', 'data_type': float, 'comment': None},

    {'name': 'p_H_pneumo', 'header': 'Насыпная плотность', 'min_max_list': (300, 1500),
     'default_val': 600, 'dimension': 'кг/м3', 'data_type': float, 'comment': None},

    {'name': 'p_t_pneumo', 'header': 'Плотность твёрдой фазы', 'min_max_list': (500, 5000),
     'default_val': 2650, 'dimension': 'кг/м3', 'data_type': float, 'comment': None},

    {'name': 'L_t', 'header': 'Длина траспортного тракта', 'min_max_list': (1, 500),
     'default_val': 50, 'dimension': 'м', 'data_type': float, 'comment': None},

    {'name': 'D_4', 'header': 'Диаметр транспортной трубы', 'min_max_list': (10, 200),
     'default_val': 47, 'dimension': 'мм', 'data_type': float, 'comment': None},

    {'name': 'D_3', 'header': 'Диаметр камеры смещения', 'min_max_list': (10, 100),
     'default_val': 30, 'dimension': 'мм', 'data_type': float, 'comment': None},

    {'name': 'd_1', 'header': 'Диаметр патрубка подвода воздуха', 'min_max_list': (5, 50),
     'default_val': 20, 'dimension': 'мм', 'data_type': float, 'comment': None},

    {'name': 'd_k', 'header': 'Диаметр критического сечения сопла', 'min_max_list': (1, 20),
     'default_val': 8, 'dimension': 'мм', 'data_type': float, 'comment': None},

    {'name': 'L_1', 'header': 'Расстояние от сопла до камеры смещения', 'min_max_list': (1, 20),
     'default_val': 8, 'dimension': 'мм', 'data_type': float, 'comment': None},

    {'name': 'p_8', 'header': 'Давление торможения', 'min_max_list': (1, 10),
     'default_val': 5, 'dimension': 'атм', 'data_type': float, 'comment': None},

    {'name': 'σ', 'header': 'Коэффициент потерь давления в сопле', 'min_max_list': (0.8, 1.0),
     'default_val': 0.89, 'dimension': '', 'data_type': float, 'comment': None},

    {'name': 'j', 'header': 'Относительная скорость частиц', 'min_max_list': (0.5, 1.0),
     'default_val': 0.9, 'dimension': '', 'data_type': float, 'comment': None},

    {'name': 'K', 'header': 'Коэффициент Гастерштадта', 'min_max_list': (1.0, 1.2),
     'default_val': 1.09996, 'dimension': '', 'data_type': float, 'comment': None},

    {'name': 'ζ', 'header': 'Коэффициент сопротивления трубы', 'min_max_list': (0.01, 0.05),
     'default_val': 0.018, 'dimension': '', 'data_type': float, 'comment': None},

    {'name': 'ζ_м', 'header': 'Местный коэффициент на входе', 'min_max_list': (0.1, 1.0),
     'default_val': 0.5, 'dimension': '', 'data_type': float, 'comment': None},

    {'name': 'H_pneumo', 'header': 'Высота подъема транспортного тракта', 'min_max_list': (1, 50),
     'default_val': 8, 'dimension': 'м', 'data_type': float, 'comment': None}
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
        row.append(val, CMF.Cell_description(accuracy=OUTPUT_PARAMS[name]['accuracy'], data_type=float))
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
                        pneumatic_jet_history WHERE s_num == {s_num}""", one=True, one_column=True, hat_c=False)
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
    if Data.Data_module.cust_data.filtr_seach_history == "":
        where = ''
    else:
        where = f'and name like "%{Data.Data_module.cust_data.filtr_seach_history}%"'
    list_calcs = CSQ.custom_request_c(Data.Data_user.db_flet,
                                      f"""SELECT * FROM pneumatic_jet_history WHERE ip = '{Data.Data_user.ip}' {where} LIMIT 20;""",
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
    rez = CSQ.custom_request_c(Data.Data_user.db_flet, f"""INSERT INTO pneumatic_jet_history 
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
        'pi': math.pi,
        'gravity': 9.81,
        'η_0': 1.73e-05,
        'h_c': 1,
        'λ_3': 1,
        'λ_4': 1,

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


    # Функции расчета для системы пневмотранспорта
    def calc_P_0():
        p_0 = params['p_0_pneumo']
        R = params['R_pneumo']
        T_0 = params['T_0_pneumo']
        return p_0 / (R * T_0)

    def calc_D_2():
        D_3 = params['D_3']
        L_1 = params['L_1']
        return D_3 + 2 * L_1

    def calc_L_2():
        D_2 = params['D_2']
        return 5 * D_2

    def calc_L_3():
        D_3 = params['D_3']
        D_4 = params['D_4']
        return (D_4 - D_3) / math.tan(math.radians(15))

    def calc_T_star_pneumo():
        return params['T_0_pneumo'] + params['t_pneumo']

    def calc_a_crit_pneumo():
        k = params['k_pneumo']
        R = params['R_pneumo']
        T_star = calc_T_star_pneumo()
        if T_star is None:
            return None
        return math.sqrt((2 * k / (k + 1)) * R * T_star)

    def calc_eta_pneumo():
        T_star = calc_T_star_pneumo()
        if T_star is None:
            return None
        return 1.73e-5 * (T_star / params['T_0_pneumo']) ** 0.75

    def calc_p_star():
        sigma = params['p_8']
        p_0 = params['p_0_pneumo']
        return sigma * p_0

    def calc_d_H():
        d_k = params['d_k']
        return 2 * d_k

    def calc_F_2():
        D_2 = params['D_2']
        d_H = calc_d_H()
        if d_H is None:
            return None
        return (math.pi / 4) * ((D_2 / 1000) ** 2 - (d_H / 1000) ** 2)

    def calc_m():
        k = params['k_pneumo']
        R = params['R_pneumo']
        return math.sqrt((k / R) * (2 / (k + 1)) ** ((k + 1) / (k - 1)))

    def calc_F_4():
        D_4 = params['D_4']
        return (math.pi / 4) * (D_4 / 1000) ** 2

    def calc_F_3():
        D_3 = params['D_3']
        return (math.pi / 4) * (D_3 / 1000) ** 2

    def calc_F_1():
        d_1 = params['d_1']
        return (math.pi / 4) * (d_1 / 1000) ** 2

    def calc_F_k():
        d_k = params['d_k']
        return (math.pi / 4) * (d_k / 1000) ** 2

    def calc_G_1():
        σ = params['σ']
        m = calc_m()
        F_k = calc_F_k()
        p_star = calc_p_star()
        T_star = calc_T_star_pneumo()
        if None in [m, F_k, p_star, T_star]:
            return None
        return σ * m * ((p_star * F_k) / math.sqrt(T_star))

    def calc_Q_1_pneumo():
        G_1 = calc_G_1()
        P_0 = calc_P_0()
        if None in [G_1, P_0]:
            return None
        return 60 * (G_1 / P_0)

    def calc_G_2():
        G_1 = calc_G_1()
        if G_1 is None:
            return None
        return 0.05 * G_1

    def calc_G():
        G_1 = calc_G_1()
        G_2 = calc_G_2()
        if None in [G_1, G_2]:
            return None
        return G_1 + G_2

    def calc_mu():
        G_t = params['G_t_pneumo'] / 3600  # переводим кг/ч в кг/с
        G = calc_G()
        if G is None:
            return None
        return G_t / G

    def calc_p_1():
        p_star = calc_p_star()
        R = params['R_pneumo']
        T_star = calc_T_star_pneumo()
        if T_star is None:
            return None
        return p_star / (R * T_star)

    def calc_p_5():
        p_0 = params['p_0_pneumo']
        R = params['R_pneumo']
        T_star = calc_T_star_pneumo()
        if T_star is None:
            return None
        return p_0 / (R * T_star)

    def calc_w_5():
        G = calc_G()
        p_5 = calc_p_5()
        F_4 = calc_F_4()
        if None in [G, p_5, F_4]:
            return None
        return G / (p_5 * F_4)

    def calc_w_1():
        G_1 = calc_G_1()
        p_1 = calc_p_1()
        F_1 = calc_F_1()
        if None in [G_1, p_1, F_1]:
            return None
        return G_1 / (p_1 * F_1)

    def calc_alpha():
        F_k = calc_F_k()
        F_3 = calc_F_3()
        if None in [F_k, F_3]:
            return None
        return F_k / (F_3 - F_k)

    def calc_p_3_star():
        alpha = calc_alpha()
        p_star = calc_p_star()
        p_0 = params['p_0_pneumo']
        if alpha is None:
            return None
        return (alpha * p_star + p_0) / (alpha + 1)

    def calc_q_lambda3_theor():
        k = params['k_pneumo']
        lambda_3 = params['λ_3']
        return ((k + 1) / 2) ** (1 / (k - 1)) * lambda_3 * (1 - ((k - 1) / (k + 1)) * lambda_3 ** 2) ** (1 / (k - 1))

    def calc_q_lambda3_empir():
        G = calc_G()
        T_star = calc_T_star_pneumo()
        p_3_star = calc_p_3_star()
        F_3 = calc_F_3()
        m = calc_m()
        if None in [G, T_star, p_3_star, F_3, m]:
            return None
        return (G * math.sqrt(T_star)) / (p_3_star * F_3 * m)

    def calc_discrepancy_pneumo():
        q_theor = calc_q_lambda3_theor()
        q_empir = calc_q_lambda3_empir()
        if None in [q_theor, q_empir]:
            return None
        return q_theor - q_empir

    def calc_λ_3():
        discrepancy = 1
        step = 0.00001
        limit_iter = 100000
        count = 1
        while round(discrepancy, 3) != 0.0000:
            count += 1
            params['λ_3'] -= step
            if count > limit_iter:
                break
            discrepancy = calc_discrepancy_pneumo()
        else:
            print(f'iters: {count}')
            print(discrepancy)
        return params['λ_3']

    def calc_w_3():
        a_crit = calc_a_crit_pneumo()
        lambda_3 = params['λ_3']
        if a_crit is None:
            return None
        return a_crit * lambda_3

    def calc_pi_lambda3():
        k = params['k_pneumo']
        lambda_3 = params['λ_3']
        return (1 - ((k - 1) / (k + 1)) * lambda_3 ** 2) ** (k / (k - 1))

    def calc_p_3():
        p_3_star = calc_p_3_star()
        pi_lambda3 = calc_pi_lambda3()
        if None in [p_3_star, pi_lambda3]:
            return None
        return p_3_star * pi_lambda3

    def calc_p_3_rho():
        G = calc_G()
        F_3 = calc_F_3()
        w_3 = calc_w_3()
        if None in [G, F_3, w_3]:
            return None
        return G / (F_3 * w_3)

    def calc_f():
        F_4 = calc_F_4()
        F_3 = calc_F_3()
        if None in [F_4, F_3]:
            return None
        return F_4 / F_3

    def calc_zeta_diff():
        f = calc_f()
        if f is None:
            return None
        return 0.35 * ((f - 1) ** 2)

    def calc_delta_p_diff():
        zeta_diff = calc_zeta_diff()
        p_3_rho = calc_p_3_rho()
        w_3 = calc_w_3()
        if None in [zeta_diff, p_3_rho, w_3]:
            return None
        return zeta_diff * p_3_rho * (w_3 ** 2) / 2

    def calc_p_4_star():
        p_3_star = calc_p_3_star()
        delta_p_diff = calc_delta_p_diff()
        if None in [p_3_star, delta_p_diff]:
            return None
        return p_3_star - delta_p_diff

    def calc_q_lambda4_theor():
        k = params['k_pneumo']
        lambda_4 = params['λ_4']
        return (((k + 1) / 2) ** (1 / (k - 1))) * lambda_4 * (1 - ((k - 1) / (k + 1)) * lambda_4 ** 2) ** (1 / (k - 1))

    def calc_q_lambda4_empir():
        G = calc_G()
        T_star = calc_T_star_pneumo()
        p_4_star = calc_p_4_star()
        F_4 = calc_F_4()
        m = calc_m()
        if None in [G, T_star, p_4_star, F_4, m]:
            return None
        return (G * math.sqrt(T_star)) / (p_4_star * F_4 * m)

    def calc_discrepancy_pneumo2():
        q_theor = calc_q_lambda4_theor()
        q_empir = calc_q_lambda4_empir()
        if None in [q_theor, q_empir]:
            return None
        return q_theor - q_empir

    def calc_λ_4():
        discrepancy = 1
        step = 0.00001
        limit_iter = 100000
        count = 1
        while round(discrepancy, 3) != 0.0000:
            count += 1
            params['λ_4'] -= step
            if count > limit_iter:
                break
            discrepancy = calc_discrepancy_pneumo2()
        else:
            print(f'iters: {count}')
            print(discrepancy)
        return params['λ_4']

    def calc_w_4():
        a_crit = calc_a_crit_pneumo()
        lambda_4 = params['λ_4']
        if a_crit is None:
            return None
        return a_crit * lambda_4

    def calc_pi_lambda4():
        k = params['k_pneumo']
        lambda_4 = params['λ_4']
        return (1 - ((k - 1) / (k + 1)) * lambda_4 ** 2) ** (k / (k - 1))

    def calc_p_4():
        p_4_star = calc_p_4_star()
        pi_lambda4 = calc_pi_lambda4()
        if None in [p_4_star, pi_lambda4]:
            return None
        return p_4_star * pi_lambda4

    def calc_p_4_rho():
        G = calc_G()
        F_4 = calc_F_4()
        w_4 = calc_w_4()
        if None in [G, F_4, w_4]:
            return None
        return G / (F_4 * w_4)

    def calc_delta_p_L():
        zeta = params['ζ']
        L_t = params['L_t']
        D_4 = params['D_4']
        K = params['K']
        mu = calc_mu()
        p_4_rho = calc_p_4_rho()
        w_4 = calc_w_4()
        if None in [mu, p_4_rho, w_4]:
            return None
        return (zeta * (L_t / (D_4 * 0.001)) * (1 + K * mu) * p_4_rho * (w_4 ** 2)) / 2

    def calc_delta_p_R():
        G_t = params['G_t_pneumo'] / 3600  # переводим кг/ч в кг/с
        j = params['j']
        w_4 = calc_w_4()
        F_4 = calc_F_4()
        if None in [w_4, F_4]:
            return None
        return (G_t * (w_4 * j)) / F_4

    def calc_delta_p_H():
        p_4_rho = calc_p_4_rho()
        H = params['H_pneumo']
        mu = calc_mu()
        if None in [p_4_rho, mu]:
            return None
        return p_4_rho * 9.81 * H * mu

    def calc_delta_p_m():
        zeta_m = params['ζ_м']
        K = params['K']
        mu = calc_mu()
        p_4_rho = calc_p_4_rho()
        w_4 = calc_w_4()
        if None in [mu, p_4_rho, w_4]:
            return None
        return zeta_m * (1 + K * mu) * p_4_rho * (w_4 ** 2) / 2

    def calc_delta_p():
        delta_p_L = calc_delta_p_L()
        delta_p_R = calc_delta_p_R()
        delta_p_H = calc_delta_p_H()
        delta_p_m = calc_delta_p_m()
        if None in [delta_p_L, delta_p_R, delta_p_H, delta_p_m]:
            return None
        return delta_p_L + delta_p_R + delta_p_H + delta_p_m

    def united_params_calculated():
        for k, v in calculated.items():
            if v == None:
                continue
            params[k] = v

    # Выполняем расчеты для системы пневмотранспорта
    calculated['P_0'] = calc_P_0()
    united_params_calculated()
    calculated['D_2'] = calc_D_2()
    united_params_calculated()
    calculated['L_2'] = calc_L_2()
    united_params_calculated()
    calculated['L_3'] = calc_L_3()
    united_params_calculated()
    calculated['T_*_pneumo'] = calc_T_star_pneumo()
    united_params_calculated()
    calculated['а_кр_pneumo'] = calc_a_crit_pneumo()
    united_params_calculated()
    calculated['η_pneumo'] = calc_eta_pneumo()
    united_params_calculated()
    calculated['p_*'] = calc_p_star()
    united_params_calculated()
    calculated['d_H'] = calc_d_H()
    united_params_calculated()
    calculated['F_2'] = calc_F_2()
    united_params_calculated()
    calculated['m'] = calc_m()
    united_params_calculated()
    calculated['F_4'] = calc_F_4()
    united_params_calculated()
    calculated['F_3'] = calc_F_3()
    united_params_calculated()
    calculated['F_1'] = calc_F_1()
    united_params_calculated()
    calculated['F_k'] = calc_F_k()
    united_params_calculated()
    calculated['G_1'] = calc_G_1()
    united_params_calculated()
    calculated['Q_1_pneumo'] = calc_Q_1_pneumo()
    united_params_calculated()
    calculated['G_2'] = calc_G_2()
    united_params_calculated()
    calculated['G'] = calc_G()
    united_params_calculated()
    calculated['μ'] = calc_mu()
    united_params_calculated()
    calculated['p_1'] = calc_p_1()
    united_params_calculated()
    calculated['p_5'] = calc_p_5()
    united_params_calculated()
    calculated['w_5'] = calc_w_5()
    united_params_calculated()
    calculated['w_1'] = calc_w_1()
    united_params_calculated()
    calculated['α'] = calc_alpha()
    united_params_calculated()
    calculated['p_3*'] = calc_p_3_star()
    united_params_calculated()

    calculated['λ_3'] = calc_λ_3()#невязка
    united_params_calculated()


    calculated['q(λ_3)_theor'] = calc_q_lambda3_theor()
    united_params_calculated()
    calculated['q(λ_3)_empir'] = calc_q_lambda3_empir()
    united_params_calculated()
    calculated['невязка_pneumo'] = calc_discrepancy_pneumo()
    united_params_calculated()
    calculated['w_3'] = calc_w_3()
    united_params_calculated()
    calculated['pi(λ_3)'] = calc_pi_lambda3()
    united_params_calculated()
    calculated['p_3'] = calc_p_3()
    united_params_calculated()
    calculated['p_3_rho'] = calc_p_3_rho()
    united_params_calculated()
    calculated['f'] = calc_f()
    united_params_calculated()
    calculated['ζ_диф'] = calc_zeta_diff()
    united_params_calculated()
    calculated['Δp_диф'] = calc_delta_p_diff()
    united_params_calculated()
    calculated['p_4*'] = calc_p_4_star()
    united_params_calculated()


    calculated['λ_4'] = calc_λ_4()#невязка
    united_params_calculated()


    calculated['q(λ_4)_theor'] = calc_q_lambda4_theor()
    united_params_calculated()
    calculated['q(λ_4)_empir'] = calc_q_lambda4_empir()
    united_params_calculated()
    calculated['невязка_pneumo2'] = calc_discrepancy_pneumo2()
    united_params_calculated()
    calculated['w_4'] = calc_w_4()
    united_params_calculated()
    calculated['pi(λ_4)'] = calc_pi_lambda4()
    united_params_calculated()
    calculated['p_4'] = calc_p_4()
    united_params_calculated()
    calculated['p_4_rho'] = calc_p_4_rho()
    united_params_calculated()
    calculated['Δp_L'] = calc_delta_p_L()
    united_params_calculated()
    calculated['Δp_R'] = calc_delta_p_R()
    united_params_calculated()
    calculated['Δp_H'] = calc_delta_p_H()
    united_params_calculated()
    calculated['Δp_м'] = calc_delta_p_m()
    united_params_calculated()
    calculated['Δp'] = calc_delta_p()
    united_params_calculated()

    # Возвращаем результат в зависимости от наличия ошибок
    if list_err:
        return list_err
    else:
        return calculated