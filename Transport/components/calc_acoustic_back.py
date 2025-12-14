import os
import copy
import operator

import flet as ft

import Config.srv_config as SRVCFG

import data_class as DTCLS
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Excel as CEX
import project_cust_38.Cust_emoji as Cust_emoji
import project_cust_38.Cust_SQLite as CSQ

from components.calc_acoustic_input_params import list_dicts_data_input
from components.calc_silencer_input_params import constants as SILENCER_CONSTANT
from components.calc_acoustic_output_params import OUTPUT_PARAMS
import components.calc_acoustic_functions as calc_acoustic_functions
import components.common_funcs as CMF
from components.common_funcs import Table_data

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




def calc_new_tbl_input():
    new_tbl_input_copy = copy.deepcopy(TBL_INPUT)
    new_tbl_input_copy.add_table_name(F.get_time_shtamp_c(), 'Ввод параметров:')
    prev_gr = ''
    from components import calc_silencer_input_params
    for item in [ *calc_silencer_input_params.list_dicts_data_input,*list_dicts_data_input]:
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

    data_params = Data.Data_module.cust_data.input_tbl_editbl.to_dict_by_unique()
    rez, success = calc_new_data({k: v['val'] for k,v in data_params.items()})
    return rez, success
    # F.save_file_pickle('test_data_params.pickle',{_['Имя']:F.valm(_['Значение']) for _ in data})


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
        #Data.Data_module.cust_data.input_tbl_editbl.set_all_cells_disabled(True)
    else:
        # return  CMF.generate_param_table(Data.Data_module.cust_data.input_tbl_not_editbl,ref_out), new_data, True
        tbl_output = make_err_tbl(new_data, ref_out)
    DTCLS.Data_page.Data_module.cust_data.output_tbl: CMF.Table_data = tbl_output
    return success


def make_res_tbl(data: dict, ref_out=None,fnc_cell_click=None) ->  CMF.Table_data:
    new_tbl_output: Table_data = copy.deepcopy(TBL_OUTPUT)
    new_tbl_output.add_table_name(F.get_time_shtamp_c(), 'Расчетные данные:')
    list_groups = []
    for key, _ in OUTPUT_PARAMS.items():
        if key not in data:
            continue
        group = ''
        if 'group_name' in _:
            group = _['group_name']
        if _['group_name'] not in list_groups:
            list_groups.append(group)


    for group in list_groups:
        new_tbl_output.add_group(F.get_time_shtamp_c(), group)
        for name, val in data.items():
            current_group = ''
            if 'group_name' in OUTPUT_PARAMS[name]:
                current_group = OUTPUT_PARAMS[name]['group_name']
            if current_group != group:
                continue

            row = CMF.Row_data()
            row.group_name = current_group
            row.append(name, CMF.Cell_description())
            row.append(OUTPUT_PARAMS[name]['header'], CMF.Cell_description())
            if F.is_numeric(val):
                accuracy = OUTPUT_PARAMS[name]['accuracy']
                row.append(val, CMF.Cell_description(accuracy=accuracy, data_type=float))
            else:
                row.append(val, CMF.Cell_description( data_type=str))
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
                        silencer_history WHERE s_num == {s_num}""", one=True, one_column=True, hat_c=False)
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
                                      f"""SELECT * FROM silencer_history WHERE ip = '{Data.Data_user.ip}' {where} LIMIT 20;""",
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
    rez = CSQ.custom_request_c(Data.Data_user.db_flet, f"""INSERT INTO silencer_history 
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
    constants = SILENCER_CONSTANT
    operators = {
        '<=': operator.le,
        '>=': operator.ge,
        '=': operator.eq
    }

    # Объединяем входные данные с константами
    params = {**constants, **input_data, **calc_acoustic_functions.CONSTANTS}

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
    # Выполняем расчеты
    for key, info in calc_acoustic_functions.CALC_FUNCTIONS.items():
        fn = info['fnc']
        # try:
        validate = set()
        if 'depends' in OUTPUT_PARAMS[key]:
            for depend_key, creds in OUTPUT_PARAMS[key]['depends'].items():
                op = operators[creds['operator']]
                target_value = creds['value']
                current_value = params[depend_key]
                validate.add(op(target_value, current_value))
        if all(validate):
            calculated[key] = fn({**params, **calculated})
        else:
            params[key] = 0
        # except Exception as e:
        #     calculated[key] = None
        #     name = key
        #     if key in OUTPUT_PARAMS:
        #         name= OUTPUT_PARAMS[key]['header']
        #     print(f"[ERROR] {key}: {e}")
        #     list_err.append({
        #         'header': name,
        #         'val': '',
        #         'Exception': f"{e}"
        #     })

    # Возвращаем результат в зависимости от наличия ошибок
    if list_err:
        return list_err, False
    else:
        return calculated, True


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


