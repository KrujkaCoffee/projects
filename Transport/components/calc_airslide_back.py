import os
import pathlib

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
    # Результаты расчета аэрожелоба
    "T_*": {
        "header": "Температура в кельвинах",
        "dimension": "К",
        "comment": "Сумма термодинамической температуры и температуры воздуха",
        "accuracy": 2
    },
    "η": {
        "header": "Вязкость воздуха",
        "dimension": "Па*с",
        "comment": "Расчетная вязкость воздуха при рабочей температуре",
        "accuracy": 6
    },
    "а_кр": {
        "header": "Критическая скорость",
        "dimension": "м/с",
        "comment": "Критическая скорость звука в газе",
        "accuracy": 2
    },
    "p_э": {
        "header": "Плотность газа",
        "dimension": "кг/м3",
        "comment": "Плотность воздуха при рабочих условиях",
        "accuracy": 4
    },
    "H": {
        "header": "Высота аэрожелоба",
        "dimension": "м",
        "comment": "Вертикальная составляющая длины желоба",
        "accuracy": 3
    },
    "F": {
        "header": "Площадь аэроднища",
        "dimension": "м2",
        "comment": "Площадь поверхности аэрации",
        "accuracy": 3
    },
    "Ar": {
        "header": "Архимедово число",
        "dimension": "",
        "comment": "Критерий подобия для псевдоожиженного слоя",
        "accuracy": 2
    },
    "Re_B": {
        "header": "Число Рейнольдса",
        "dimension": "",
        "comment": "Критерий Рейнольдса для частиц",
        "accuracy": 1
    },
    "w_B": {
        "header": "Скорость витания",
        "dimension": "м/с",
        "comment": "Скорость потока при витании частиц",
        "accuracy": 4
    },
    "ε_0": {
        "header": "Порозность неподвижного слоя",
        "dimension": "",
        "comment": "Объемная доля газа в неподвижном слое",
        "accuracy": 3
    },
    "ε_k": {
        "header": "Порозность кипящего слоя",
        "dimension": "",
        "comment": "Объемная доля газа в кипящем слое",
        "accuracy": 3
    },
    "ε": {
        "header": "Порозность подвижного слоя",
        "dimension": "",
        "comment": "Объемная доля газа в подвижном слое",
        "accuracy": 3
    },
    "Re_k": {
        "header": "Критерий Рейнольдса",
        "dimension": "",
        "comment": "Для кипящего слоя",
        "accuracy": 2
    },
    "w_k": {
        "header": "Скорость начала псевдоожижения",
        "dimension": "м/с",
        "comment": "Минимальная скорость для псевдоожижения",
        "accuracy": 4
    },
    "i_B": {
        "header": "Уклон аэрожелоба",
        "dimension": "",
        "comment": "Гидравлический уклон",
        "accuracy": 5
    },
    "C": {
        "header": "Коэффициент Шези",
        "dimension": "м^0,5/с",
        "comment": "Коэффициент для расчета скорости",
        "accuracy": 2
    },
    "h_c": {
        "header": "Высота слоя",
        "dimension": "м",
        "comment": "Подбор",
        "accuracy": 5
    },
    "u__": {
        "header": "Средняя скорость твердой фазы",
        "dimension": "м/с",
        "comment": "Средняя скорость движения материала",
        "accuracy": 4
    },
    "R_g": {
        "header": "Гидравлический радиус",
        "dimension": "м",
        "comment": "Характеристика сечения потока",
        "accuracy": 4
    },
    "u_": {
        "header": "Средняя скорость частиц",
        "dimension": "м/с",
        "comment": "Скорость движения частиц материала",
        "accuracy": 4
    },
    "невязка": {
        "header": "Разница между скоростями",
        "dimension": "",
        "comment": "Разница расчетных скоростей",
        "accuracy": 6
    },
    "Q_1": {
        "header": "Минимальный расход воздуха",
        "dimension": "м3/ч",
        "comment": "Для начала псевдоожижения",
        "accuracy": 1
    },
    "Q_2": {
        "header": "Максимальный расход воздуха",
        "dimension": "м3/ч",
        "comment": "Для транспортировки",
        "accuracy": 1
    },
    "μ_v1": {
        "header": "Объемная концентрация частиц (мин расход)",
        "dimension": "кг/м3",
        "comment": "При минимальном расходе воздуха",
        "accuracy": 3
    },
    "μ_v2": {
        "header": "Объемная концентрация частиц (макс расход)",
        "dimension": "кг/м3",
        "comment": "При максимальном расходе воздуха",
        "accuracy": 3
    },
    "p_a1": {
        "header": "Плотность аэропульпы (псевдоожижение)",
        "dimension": "кг/м3",
        "comment": "В режиме псевдоожижения",
        "accuracy": 3
    },
    "p_a2": {
        "header": "Плотность аэропульпы (рабочий режим)",
        "dimension": "кг/м3",
        "comment": "В рабочем режиме транспортировки",
        "accuracy": 3
    },

}
list_dicts_data_input = [
    # Параметры аэрожелоба
    {'name': 'p_0', 'header': 'Давление', 'min_max_list': None, 'default_val': 101325,
     'dimension': 'Па', 'data_type': int, 'comment': None},

    {'name': 'R', 'header': 'Удельная газовая постоянная для воздуха', 'min_max_list': None,
     'default_val': 287.1, 'dimension': 'Дж/(кг/К)', 'data_type': float, 'comment': None},

    {'name': 'T_0', 'header': 'Термодинамическая температура', 'min_max_list': None,
     'default_val': 273.15, 'dimension': 'К', 'data_type': float, 'comment': None},

    {'name': 't', 'header': 'Температура воздуха', 'min_max_list': (-50, 100), 'default_val': 20,
     'dimension': '℃', 'data_type': int, 'comment': None},

    {'name': 'β', 'header': 'Угол наклона желоба', 'min_max_list': (0, 45), 'default_val': 5,
     'dimension': '°', 'data_type': int, 'comment': None},

    {'name': 'L', 'header': 'Длина желоба', 'min_max_list': (0.1, 50), 'default_val': 5,
     'dimension': 'м', 'data_type': float, 'comment': None},

    {'name': 'B', 'header': 'Ширина аэрожелоба', 'min_max_list': (0.05, 1), 'default_val': 0.2,
     'dimension': 'м', 'data_type': float, 'comment': None},

    {'name': 'p_t', 'header': 'Плотность частиц твердой фазы', 'min_max_list': (500, 5000),
     'default_val': 3100, 'dimension': 'кг/м3', 'data_type': float, 'comment': None},

    {'name': 'd_cp', 'header': 'Средний размер частиц', 'min_max_list': (1, 500),
     'default_val': 40, 'dimension': 'мкм', 'data_type': float, 'comment': None},

    {'name': 'p_H', 'header': 'Насыпная плотность материала', 'min_max_list': (300, 2000),
     'default_val': 1100, 'dimension': 'кг/м3', 'data_type': int, 'comment': None},

    {'name': 'G_t', 'header': 'Производительность аэрожелоба', 'min_max_list': (1, 500),
     'default_val': 80, 'dimension': 'т/ч', 'data_type': int, 'comment': None},

    {'name': 'k', 'header': 'Коэффициент адиабаты', 'min_max_list': (1.1, 1.5), 'default_val': 1.4,
     'dimension': '', 'data_type': float, 'comment': None},


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

    table_view = CMF.Table_view(new_tbl_input, ref=ref, fnc_onchange=fnc_onchange)

    return table_view, new_tbl_input


def prepare_calc_new_data(data: list[dict], Data: DTCLS.Data_page) -> (list[dict] | dict,bool):
    data_params = {_['Имя']: F.valm(_['Значение']) for _ in data}
    #data_params = F.load_file_pickle('test_data_params.pickle')
    Data.Data_module.cust_data: Cust_module_params
    if not Data.Data_module.cust_data.input_tbl_editbl.sync_ui_to_data('val'):
        return None, False
    Data.Data_module.cust_data.input_tbl_editbl.set_all_cells_disabled(True)
    data_params = Data.Data_module.cust_data.input_tbl_editbl.to_dict_by_unique()
    rez, success = calc_new_data({k: v['val'] for k,v in data_params.items()})
    return rez, success


def generate_rez_tbl(e: ft.ControlEvent, tbl: ft.DataTable, ref_out,fnc_cell_click=None) -> bool | None:
    Data: DTCLS.Data_page = e.page.data
    data = CMF.datatable_to_dicts(tbl)
    DTCLS.Data_page.Data_module.cust_data: Cust_module_params
    DTCLS.Data_page.Data_module.cust_data.output_tbl = None
    new_data, success = prepare_calc_new_data(data, Data)
    if not new_data:
        return
    if success:
        tbl_output = make_res_tbl(new_data, ref_out, fnc_cell_click)
    else:
        # return  CMF.generate_param_table(Data.Data_module.cust_data.input_tbl_not_editbl,ref_out), new_data, True
        tbl_output = make_err_tbl(new_data, ref_out)
    DTCLS.Data_page.Data_module.cust_data.output_tbl: CMF.Table_data = tbl_output
    return success


def make_res_tbl(data: dict, ref_out=None,fnc_cell_click=None) -> CMF.Table_data:
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

    CMF.Table_view(new_tbl_output, ref=ref_out, fnc_on_click=fnc_cell_click)

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


def load_from_db_history_calc(Data: DTCLS.Data_page, s_num: int) -> (CMF.Table_data, CMF.Table_data):
    data = CSQ.custom_request_c(Data.Data_user.db_flet, f"""SELECT data FROM
                        airslide_history WHERE s_num == {s_num}""", one=True, one_column=True, hat_c=False)
    if not data:
        return False
    data_obj = F.from_binary_pickle(data)
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
    pathlib.Path(dir_save).mkdir(parents=True, exist_ok=True)
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
                                      f"""SELECT * FROM airslide_history WHERE ip = '{Data.Data_user.ip}' {where} LIMIT 20;""",
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
    rez = CSQ.custom_request_c(Data.Data_user.db_flet, f"""INSERT INTO airslide_history 
                        (date, 
                            name, 
                            ip, 
                            data)
                              VALUES ({CSQ.questions_for_mask(row)})""", list_of_lists_c=[row])
    return rez


def calc_new_data(input_data: dict) -> (list | dict, bool):
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

    # Функции расчета для аэрожелоба
    def calc_T_star():
        return params['T_0'] + params['t']

    def calc_eta():
        T_star = calc_T_star()
        if T_star is None:
            return None
        return 1.73e-5 * (T_star / params['T_0']) ** 0.75

    def calc_a_crit():
        k = params['k']
        R = params['R']
        T_star = calc_T_star()
        if T_star is None:
            return None
        return math.sqrt((2 * k / (k + 1)) * R * T_star)

    def calc_p_rho():
        p_0 = params['p_0']
        R = params['R']
        T_star = calc_T_star()
        if T_star is None:
            return None
        return p_0 / (R * T_star)

    def calc_H():
        L = params['L']
        beta = params['β']
        return L * math.sin(math.radians(beta))

    def calc_F():
        L = params['L']
        B = params['B']
        return L * B

    def calc_Ar():
        d_cp = params['d_cp'] * 1e-6  # переводим мкм в м
        p_rho = calc_p_rho()
        p_t = params['p_t']
        eta = calc_eta()
        if None in [d_cp, p_rho, eta]:
            return None
        return (9.81 * (d_cp ** 3) * p_rho * (p_t - p_rho)) / (eta ** 2)

    def calc_Re_B():
        Ar = calc_Ar()
        if Ar is None:
            return None
        return Ar / (18 + 0.61 * math.sqrt(Ar))

    def calc_w_B():
        Re_B = calc_Re_B()
        d_cp = params['d_cp'] * 1e-6
        p_rho = calc_p_rho()
        eta = calc_eta()
        if None in [Re_B, d_cp, p_rho, eta]:
            return None
        return (Re_B * eta) / (d_cp * p_rho)

    def calc_epsilon_0():
        p_H = params['p_H']
        p_t = params['p_t']
        return 1 - (p_H / p_t)

    def calc_epsilon_k():
        epsilon_0 = calc_epsilon_0()
        if epsilon_0 is None:
            return None
        return 1.15 * epsilon_0

    def calc_epsilon():
        epsilon_k = calc_epsilon_k()
        if epsilon_k is None:
            return None
        return 1.05 * epsilon_k

    def calc_Re_k():
        Ar = calc_Ar()
        epsilon_k = calc_epsilon_k()
        if None in [Ar, epsilon_k]:
            return None

        term1 = 150 * (1 - epsilon_k) / (epsilon_k ** 3)
        term2 =  (1.75 * Ar / (epsilon_k ** 3)) ** 0.5
        denominator = term1 + term2

        return Ar / denominator

    def calc_w_k():
        Re_k = calc_Re_k()
        d_cp = params['d_cp'] * 1e-6
        p_rho = calc_p_rho()
        eta = calc_eta()
        if None in [Re_k, d_cp, p_rho, eta]:
            return None
        return (Re_k * eta) / (d_cp * p_rho)

    def calc_i_B():
        H = calc_H()
        L = params['L']
        beta = params['β']
        if H is None:
            return None
        return H / (L * math.cos(math.radians(beta)))

    def calc_C():
        i_B = calc_i_B()
        if i_B is None:
            return None
        return 256 * i_B + 15.95

    def calc_u_avg():
        G_t = params['G_t'] * 1000 / 3600  # переводим т/ч в кг/с
        B = params['B']
        h_c = params['h_c']
        epsilon = calc_epsilon()
        p_t = params['p_t']
        if None in [epsilon]:
            return None
        return G_t / (B * h_c * (1 - epsilon) * p_t)

    def calc_R_g():
        B = params['B']
        h_c = params['h_c']
        return (B * h_c) / (2 * h_c + B)

    def calc_u_particles():
        koef_C = calc_C()
        R_g = calc_R_g()
        i_B = calc_i_B()
        if None in [koef_C, R_g, i_B]:
            return None
        return koef_C * math.sqrt(R_g * i_B)

    def calc_discrepancy():
        u_avg = calc_u_avg()
        u_particles = calc_u_particles()
        if None in [u_avg, u_particles]:
            return None
        return u_avg - u_particles

    def calc_h_c():
        discrepancy = 1
        step = 0.00001
        limit_iter = 100000
        count = 1
        while round(discrepancy, 3) != 0.0000:
            count += 1
            params['h_c'] -= step
            if count > limit_iter:
                break
            discrepancy = calc_discrepancy()
        else:
            print(f'iters: {count}')
            print(discrepancy)
        return  params['h_c']

    def calc_Q1():
        F = calc_F()
        w_k = calc_w_k()
        if None in [F, w_k]:
            return None
        return 3600 * F * w_k

    def calc_Q2():
        F = calc_F()
        w_B = calc_w_B()
        if None in [F, w_B]:
            return None
        return 3600 * F * w_B

    def calc_mu_v1():
        G_t = params['G_t']
        Q1 = calc_Q1()
        if Q1 is None:
            return None
        return (1000 * G_t) / Q1

    def calc_mu_v2():
        G_t = params['G_t']
        Q2 = calc_Q2()
        if Q2 is None:
            return None
        return (1000 * G_t) / Q2

    def calc_p_a1():
        epsilon_k = calc_epsilon_k()
        p_t = params['p_t']
        if None in [epsilon_k]:
            return None
        return (1 - epsilon_k) * p_t

    def calc_p_a2():
        epsilon = calc_epsilon()
        p_t = params['p_t']
        if None in [epsilon]:
            return None
        return (1 - epsilon) * p_t

    def united_params_calculated():
        for k, v in calculated.items():
            if v == None:
                continue
            params[k] = v

    # Выполняем расчеты для аэрожелоба
    calculated['T_*'] = calc_T_star()
    united_params_calculated()
    calculated['η'] = calc_eta()
    united_params_calculated()
    calculated['а_кр'] = calc_a_crit()
    united_params_calculated()
    calculated['p_э'] = calc_p_rho()
    united_params_calculated()
    calculated['H'] = calc_H()
    united_params_calculated()
    calculated['F'] = calc_F()
    united_params_calculated()
    calculated['Ar'] = calc_Ar()
    united_params_calculated()
    calculated['Re_B'] = calc_Re_B()
    united_params_calculated()
    calculated['w_B'] = calc_w_B()
    united_params_calculated()
    calculated['ε_0'] = calc_epsilon_0()
    united_params_calculated()
    calculated['ε_k'] = calc_epsilon_k()
    united_params_calculated()
    calculated['ε'] = calc_epsilon()
    united_params_calculated()
    calculated['Re_k'] = calc_Re_k()
    united_params_calculated()
    calculated['w_k'] = calc_w_k()
    united_params_calculated()
    calculated['i_B'] = calc_i_B()
    united_params_calculated()
    calculated['C'] = calc_C()
    united_params_calculated()

    calculated['h_c'] = calc_h_c()#невязка
    united_params_calculated()

    calculated['u__'] = calc_u_avg()
    united_params_calculated()
    calculated['R_g'] = calc_R_g()
    united_params_calculated()
    calculated['u_'] = calc_u_particles()
    united_params_calculated()
    calculated['невязка'] = calc_discrepancy()
    united_params_calculated()
    calculated['Q_1'] = calc_Q1()
    united_params_calculated()
    calculated['Q_2'] = calc_Q2()
    united_params_calculated()
    calculated['μ_v1'] = calc_mu_v1()
    united_params_calculated()
    calculated['μ_v2'] = calc_mu_v2()
    united_params_calculated()
    calculated['p_a1'] = calc_p_a1()
    united_params_calculated()
    calculated['p_a2'] = calc_p_a2()
    united_params_calculated()

    # Возвращаем результат в зависимости от наличия ошибок
    if list_err:
        return list_err, False
    else:
        return calculated, True