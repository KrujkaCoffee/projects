from __future__ import annotations

import datetime
import os
import copy
import pathlib #27.10.25
import pprint
import sys
import hashlib
from builtins import dict

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
from lxml.etree import DTD
from project_cust_38 import Cust_config as CFG
from PyQt5.QtCore import QDate
from PyQt5 import QtGui, QtCore, QtWidgets
import gui_kal_plan as GPL
import gui_vol_plan as VPL
import pl_user_fiters as KPLUF
import make_poz_plan as POZPL
import project_cust_38.Cust_Excel as CEX
import project_cust_38.Erp_connector_plan as ERP
from pl_graf_pad_mosh import generate as GEN_PLG
import project_cust_38.Cust_odata_erp as CODAT
from typing import TYPE_CHECKING, TypeVar, Dict
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_b24 as CB24
import project_cust_38.Cust_emoji as CEMOJ
from data_class import Data_plan as DTCLS
from functools import partial
if TYPE_CHECKING:
    from MKart import mywindow



# exclude LIST_FREEZE_FIELDS 10.11.25
FOLDER_CLOSED = f'{CEMOJ.EmojiMain.ДокументыДанные.folder_closed.symbol}{CEMOJ.EmojiMain.ДокументыДанные.plus_circled.symbol}'
FOLDER_OPEN = f'{CEMOJ.EmojiMain.ДокументыДанные.folder.symbol}{CEMOJ.EmojiMain.ДокументыДанные.minus_circled.symbol}'
DOC_EMOJI = f'    {CEMOJ.EmojiMain.ДокументыДанные.document.symbol}'

"""
Оптимизировано представление динамически подгружаемых полей для плана
добавлена возможность включать в план абстрактные калькулируемые поля
ускорена загрузка данных для таблиц
проверены и настроены проверки при заполнении и изменении данных в позиции.
введена система псевдонимов для этапов и полей плана
оптимизирован принцип загрузки и применения пользовательских настроек
улучшен интерфейс настройки полей из плана. (имена этапов, имена полей, описание полей, порядок полей)
введены контекстные меню и интерактивные ссылки на объекты 1с (ЗК, ЗП и т.д.)
повышена скорость работы с гантом и табелями за счет агрегации таблиц
изменена архитектура построения полей таблицы плана для добавления новых полей
улучена визуальная часть для уплотнения и информативности таблиц 
добавлены автофильтры в основную таблицу
улучшен вывод таблиц в стаканах при месячном планировании
ускорена загрузка данных выбранной позиции, при работе со стаканом месяца
"""

class Check_field_rule(CMS._ImportDb):
    def __init__(self, it):
        self.id: int = None
        self.name: str = None
        self.descr: str = None
        self.priority: int = None
        self.parce_row_dict(it)



class Check_field_rules():
    def __init__(self):
        self.dict_rules: dict[int, Check_field_rule] = dict()
        data = CSQ.custom_request_c(DTCLS.db_kplan, f"""SELECT * FROM info_fields_kpl_check_rules""",
                                    rez_dict=True)
        for it in data:
            rule = Check_field_rule(it)
            self.dict_rules[rule.id] = rule
    @staticmethod
    def add_to_db(id_field:int,id_rule:int,comment=None):
        list_of_lists = [id_field, id_rule, comment]
        CSQ.custom_request_c(DTCLS.db_kplan,f'''INSERT INTO info_fields_kpl_check_rules_val
         (field,rule,comment) VALUES ({CSQ.questions_for_mask(list_of_lists)})''',list_of_lists_c=[list_of_lists])

    def find(self,id:int)->Check_field_rule|None:
        return self.dict_rules.get(id,None)

    def find_by_name(self,name:str)->Check_field_rule|None:
        for r in self.dict_rules.values():
            if r.name==name :
                return r

DTCLS.CHECK_FIELD_RULES = Check_field_rules()



DTCLS.FIELDS_DB_INFO = CMS.Fields_db_info(DTCLS.CHECK_FIELD_RULES)


def _________manage_kpl_________________________():pass



@CQT.onerror
def btn_config_limit_gant(*args):
    template = [{
        '_name':_.name,
        'Имя':_.alias,
        'Нормо-час':_.default_hours_day_gant
                 } for _ in DTCLS.FIELDS_DB_INFO.tables_db.tabels_ordered]

    def fnc_check(btn, dialog, tbl, *args):
        list_err = []
        if btn.text() == 'Применить':
            t = CQT.TableContext(tbl)
            for row in t.rows():
                val_str = row.value('Нормо-час')
                if  not val_str:
                    list_err.append(f'{row.value("Имя")}: не заполнено')
                if not F.is_numeric(val_str):
                    list_err.append(f'{row.value("Имя")}: не число')
            if list_err:
                CQT.msgbox(f"{'\n'.join(list_err)}",app_self=DTCLS.app_self)
                return
            dialog.accept()
        else:
            dialog.reject()

    def fnc_valid(data:list[dict])->dict:
        get_t = DTCLS.FIELDS_DB_INFO.tables_db.get_table
        return {_['_name']:F.valm(_['Нормо-час']) for _ in data if
                    get_t(_['_name']).default_hours_day_gant != F.valm(_['Нормо-час'])}

    def fnc_oform(tbl,*args):
        t= CQT.TableContext(tbl)
        t.hide_if_not_dev(CFG)
        t.set_editable('Нормо-час')

    rez = CQT.msgboxg_get_table(DTCLS.app_self,"Настройки нормо-час. по этапам:",template,'Применить',
                          not_standart_close=True,func_btn0=fnc_check, func_validate=fnc_valid, func_oform_tbl=fnc_oform,
                          styleSheet=CQT.MES_EDIT_CSS,)
    if not rez:
        return
    get_t = DTCLS.FIELDS_DB_INFO.tables_db.get_table
    for name_tbl, new_val in rez.items():
        tbl_db = get_t(name_tbl)
        tbl_db.update_default_hours_day_gant(new_val)


@CQT.onerror
def btn_config_fields(*args):

    dict_result_change = {'Этап плана':dict(),
                          '_s_num':dict(),
                          }
    fl_edit = False
    def fnc_get_data(data):
        return data
    def fnc_oform(tbl: QtWidgets.QTableWidget, *args):

        def fnc_dbl_clc_edit_row(t:CQT.TableContext,i:int,f:str):
            def fnc_check_edit_row(tbl_data:list[dict]):
                rez = [{_['Параметр']: CSQ.sanitize_sql_input(_['Значение']) for _ in tbl_data}]
                return rez
            def fnc_oform_edit_row(tbl:QtWidgets.QTableWidget):
                t = CQT.TableContext(tbl)
                for row in t.rows():
                    row.set_editable('Значение')
            def fnc_check_select(btn, dialog, tbl):
                t = CQT.TableContext(tbl)
                if btn.text() == 'Ввод':
                    for row in t.rows():
                        param = row.value('Параметр')
                        val = row.value('Значение').strip()
                        if param == 'Таблица':
                            pass
                        if param == 'Поле':
                            if len(val)<1:
                                CQT.msgbox('Поле должно иметь название')
                                return
                            pass
                        if param == 'Таблица':
                            pass
                    dialog.accept()
                else:
                    dialog.reject()

            curr_row = t.get_row(i)
            Таблица_val = curr_row.value('Таблица')
            Поле_val = curr_row.value('Поле')
            Описание_val = curr_row.value('Описание')
            template = [
                {'Параметр':'Таблица','Значение':Таблица_val},
                {'Параметр':'Поле','Значение':Поле_val},
                {'Параметр':'Описание','Значение':Описание_val},
            ]
            rez = CQT.msgboxg_get_table(DTCLS.app_self,'Настройка имен',template,func_validate=fnc_check_edit_row,
                                        func_oform_tbl=fnc_oform_edit_row,show_filtr=False,styleSheet=CQT.MES_EDIT_CSS,
                                        not_standart_close=True,func_btn0=fnc_check_select)

            if not rez:
                return
            rez = rez[0]
            tbl_mes = curr_row.value('Этап плана')
            s_num = int(curr_row.value('_s_num'))
            dict_result_change['_s_num'][s_num] = dict()
            if Таблица_val != rez['Таблица']:
                dict_result_change['Этап плана'][tbl_mes] = rez['Таблица']
                for row in t.rows():
                    if row.value('Этап плана') == tbl_mes:
                        row.set_value('Таблица',rez['Таблица'])
            if Поле_val != rez['Поле']:
                curr_row.set_value('Поле',rez['Поле'])
                dict_result_change['_s_num'][s_num]['field_alias'] = rez['Поле']
            if Описание_val != rez['Описание']:
                curr_row.set_value('Описание',rez['Описание'])
                dict_result_change['_s_num'][s_num]['description'] = rez['Описание']



        t = CQT.TableContext(tbl)
        t.add_column_events('Корр.',on_double_click=fnc_dbl_clc_edit_row)
        with CQT.table_updating(tbl):
            for row in t.rows():
                f = DTCLS.FIELDS_DB_INFO.dict_fields[row.value('_name_mes')]
                clr = f.table_color
                new_clr = clr.align_colors(level_percent=-1,saturation_percent=-1,copy=True)
                row.set_color_font(*new_clr.rgb)
                add_switcher(row)
                row.set_font_format(bold=True,col_name='Таблица')
                row.set_font_format(bold=True,col_name='Поле')
                row.set_font_format(bold=True,col_name='Описание')
            if not CFG.User_config.is_developer:
                t.hide_startsunderscore()

    def fnc_toggle_view(tbl: QtWidgets.QTableWidget, val: bool, i: int, j: int):
        tbl.item(i,j).setText(str(val))
        tbl.setProperty('_fl_edit','True')
    def add_switcher(row:CQT.TableRow):
        enable = True
        #if F.boolm(row.value('_system')):
        #    enable = False
        CQT.add_check_box_switcher(row.tbl, row.i, row.nf['Видимость'], F.boolm(row.value('Видимость')),
                                   fnc_toggle_view, enabled=enable)

    def fnc_drdr(tbl: QtWidgets.QTableWidget, row_from: int, row_to: int):
        if isinstance(row_from,int) and isinstance(row_to,int):
            with CQT.table_updating(tbl):
                t = CQT.TableContext(tbl)
                row = t.get_row(row_to)
                add_switcher(row)
                tbl.setProperty('_fl_edit','True')

    dict_cnf = DTCLS.FIELDS_DB_INFO.dict_fields.values()
    EDIT_EMOJ = CEMOJ.EmojiMain.ДокументыДанные.pencil_note.symbol

    template = [{'Корр.':EDIT_EMOJ,'Таблица':data.table_alias,'Поле':data.field_alias, '_system':data.is_system,
                 '_name_mes':data.name_mes,'Этап плана':data.table_mes,'_s_num':data.s_num,
                 'Видимость':not data.is_hidden,'_idx':data.usr_idx,'Описание':data.description}
                        for i,data in enumerate(dict_cnf) if (not data.sys_hide and data.enable)]

    rez_data_table, dict_prop = CQT.msgboxg_get_table(DTCLS.app_self,f'Настройка порядка и отображения',template,'Завершить',
                        styleSheet=CQT.MES_CSS,showMaximized=True,func_validate=fnc_get_data,func_oform_tbl=fnc_oform,
                                selectRows=True,fnc_drag_drop=fnc_drdr,property_in_rez=True)

    if not rez_data_table:
        return

    if '_fl_edit' in dict_prop:
        if F.boolm(dict_prop['_fl_edit']):
            fl_edit = True

    fl_update_db = False

    for tbl_mes, val in dict_result_change['Этап плана'].items():
        rez = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""UPDATE podrazdel
                        SET  (alias)
                            = (?)
                                WHERE Имя = "{tbl_mes}" ;""", list_of_lists_c=[val])
        if not rez:
            CQT.msgbox(f'Ошибка обновления таблицы {tbl_mes}')
        fl_edit = True
        fl_update_db = True
    for s_num , data_name_mes in dict_result_change['_s_num'].items():
        if 'field_alias' in data_name_mes:
            val = data_name_mes['field_alias']
            rez = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""UPDATE info_fields_kpl
                                    SET  (alias_usr)
                                        = (?)
                                            WHERE s_num = {s_num} ;""", list_of_lists_c=[val])
            if not rez:
                CQT.msgbox(f'Ошибка обновления поля {s_num}')
            fl_edit = True
            fl_update_db = True
        if 'description' in data_name_mes:
            val = data_name_mes['description']
            rez = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""UPDATE info_fields_kpl
                                    SET  (nickname)
                                        = (?)
                                            WHERE s_num = {s_num} ;""", list_of_lists_c=[val])
            if not rez:
                CQT.msgbox(f'Ошибка обновления описаня для {s_num}')
            fl_edit = True
            fl_update_db = True

    if not fl_edit:
        return

    for idx, it in enumerate(rez_data_table):
        name = it['_name_mes']
        hidden = not F.boolm(it['Видимость'])

        dict_fields = DTCLS.FIELDS_DB_INFO.dict_fields
        f = dict_fields[name]
        f.usr_idx = idx
        f.usr_hide = hidden

    DTCLS.FIELDS_DB_INFO.fix_indx()
    DTCLS.FIELDS_DB_INFO.save_user_data()
    if fl_update_db:
        DTCLS.FIELDS_DB_INFO = CMS.Fields_db_info(DTCLS.CHECK_FIELD_RULES)
    update_list_fields(False)
    load_table_db(DTCLS.app_self)

def ______________PKK________________________________():pass


def ______________SETTINGS________________________________():pass
def download_pkk(nom_file:int)->str|None:
    rez = CSQ.custom_request_c(DTCLS.db_fiels,
                               f'''SELECT file_name, file FROM project_cards WHERE s_nom = {nom_file}''',
                               one=True)
    if len(rez) <= 1:
        CQT.msgbox(f'Файл s_num {nom_file} в project_cards не найден')
        return
    file_blob_compr = rez[-1][1]
    file_name = rez[-1][0]
    file_blob = F.unpack_byte_file(file_blob_compr)
    return F.save_tmp_win_dir_file(file_blob, F.keep_extention_c(file_name))

def pre_del_file_pkk(t: CQT.TableContext, lbl: CQT.InteractiveLabelInstance, app_self, i, j, *args):
    row = t.get_row(i)
    row.set_value('Значение', '')
    lbl.set_text('')

def del_file_pkk(id:int)->bool:

    linked_kpl = CSQ.custom_request_c(DTCLS.db_kplan,
                                      f'''SELECT НомПл, ПКК FROM пл_оуп WHERE ПКК = ?''',
                                      rez_dict=True, list_of_lists_c=[[id]])
    if linked_kpl is None or isinstance(linked_kpl, bool) and not linked_kpl:
        return False

    if len(linked_kpl) < 2:
        rez = CSQ.custom_request_c(DTCLS.db_fiels,
                                   f'''DELETE FROM project_cards WHERE
                                                        s_nom = {id}''')

    return True

def show_file_pkk(t: CQT.TableContext, lbl: CQT.InteractiveLabelInstance, app_self, i, j, *args):
    row = t.get_row(i)
    if row.no_selection:
        return
    val = row.value('Значение')
    if not val:
        return
    if not F.is_numeric(val):
        return
    id = int(val)
    tmp_file = download_pkk(id)
    if tmp_file:
        F.run_file_os_c(tmp_file)


def pre_add_file_pkk(t: CQT.TableContext, lbl: CQT.InteractiveLabelInstance, app_self, i, j,
                 *args):
    MAX_FIRE_SIZE_MB = 5

    dir = CMS.load_tmp_path('kpl_pkk')
    file_path = CQT.f_dialog_name(DTCLS.app_self, 'Выбрать файл с карточкой проекта', dir, '*', True)
    if file_path == '.':
        return

    CMS.save_tmp_path('kpl_pkk', file_path, True)

    file_founding = F.load_file_convert_to_binary(file_path)
    size = sys.getsizeof(file_founding)
    if size > 1048576 * MAX_FIRE_SIZE_MB:
        CQT.msgbox(f'Размер файла должен быть не более {MAX_FIRE_SIZE_MB} мб')
        return
    row = t.get_row(i)
    row.set_value('Значение', file_path)
    lbl.set_text(CEMOJ.ДокументыДанные.document.symbol)

def upload_pkk(link:str)->int|None:
    MAX_FIRE_SIZE_MB = 5
    file_founding = F.load_file_convert_to_binary(link)
    size = sys.getsizeof(file_founding)
    if size > 1048576 * MAX_FIRE_SIZE_MB:
        CQT.msgbox(f'Размер файла должен быть не более {MAX_FIRE_SIZE_MB} мб')
        return
    hash = hashlib.sha1(file_founding).hexdigest()
    file_founding = F.pack_byte_file(file_founding)
    print(f'size {size}')

    def get_id(size, hash) -> int:
        id_file = CSQ.custom_request_c(DTCLS.db_fiels,
                                       f'''SELECT s_nom FROM project_cards WHERE size = {size} AND hash = "{hash}"''',
                                       one_column=True, one=True, hat_c=False)
        return id_file

    id_file = get_id(size, hash)
    name = link.split(F.sep())[-1]
    if not id_file:
        CSQ.custom_request_c(DTCLS.db_fiels,
                             """INSERT INTO  project_cards(file_name,size,hash,file) VALUES (?,?,?,?);""",
                             list_of_lists_c=[[name, size, hash, file_founding]])
        id_file = get_id(size, hash)
    return id_file

def add_file_pkk(row: CQT.TableRow, lbl: CQT.InteractiveLabelInstance, app_self, i, j,
                 *args):
    MAX_FIRE_SIZE_MB = 5
    update_db = False
    num_poz = 0

    if row is None:
        update_db = False
    else:
        num_poz = int(row.value('Значение'))

    file_path = row.value('Значение')

    file_founding = F.load_file_convert_to_binary(file_path)
    size = sys.getsizeof(file_founding)
    if size > 1048576 * MAX_FIRE_SIZE_MB:
        CQT.msgbox(f'Размер файла должен быть не более {MAX_FIRE_SIZE_MB} мб')
        return
    hash = hashlib.sha1(file_founding).hexdigest()
    file_founding = F.pack_byte_file(file_founding)
    print(f'size {size}')

    def get_id(size, hash) -> int:
        id_file = CSQ.custom_request_c(DTCLS.db_fiels,
                                       f'''SELECT s_nom FROM project_cards WHERE size = {size} AND hash = "{hash}"''',
                                       one_column=True, one=True, hat_c=False)
        return id_file

    id_file = get_id(size, hash)
    name = file_path.split(F.sep())[-1]
    if not id_file:
        CSQ.custom_request_c(DTCLS.db_fiels,
                             """INSERT INTO  project_cards(file_name,size,hash,file) VALUES (?,?,?,?);""",
                             list_of_lists_c=[[name, size, hash, file_founding]])
        id_file = get_id(size, hash)

    if update_db:
        CSQ.custom_request_c(DTCLS.db_kplan, f"""UPDATE пл_оуп SET ПКК = {id_file} WHERE  НомПл = {num_poz};""")




def add_widget_pkk(t: CQT.TableContext, row: CQT.TableRow):
    s_nom_project_cards = row.value('Значение')

    widg = CQT.add_interactive_label(t.tbl, row.i, row.nf['Значение'], row.value('Значение'),
                                     parent_self=DTCLS.app_self)
    if F.is_numeric(s_nom_project_cards) and int(s_nom_project_cards)>0:
        widg.set_text(CEMOJ.ДокументыДанные.document.symbol)
    else:
        row.set_value("Значение",'')

    widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать ПКК',
                    partial(pre_add_file_pkk, t),
                    cell_val=None, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                          'icons', 'btn_select']))
    widg.add_button(CEMOJ.EmojiMain.СтатусыПроизводства.error.symbol, 'Удалить ПКК',
                    partial(pre_del_file_pkk, t),
                    cell_val=None)


def ______________EDIT_________________________________():pass

def check_edit_permission()->tuple[bool,str]:
    tbl = DTCLS.app_self.ui.tbl_kal_pl
    t = CQT.TableContext(tbl)
    row = t.current_row()
    if row.no_selection:
        return False, ''
    name_field = t.current_column_name()
    DICT_FIELDS = DTCLS.FIELDS_DB_INFO.dict_fields
    field_o:CMS.Field_db_info = DICT_FIELDS[name_field]

    fl_check_field = True
    msg_err = ''

    if not field_o.hand_editable:
        msg_err = f'Корректировка поля запрещена'
        fl_check_field = False
    fl_access = CMS.access_kpl_tbl(DTCLS.app_self.Data_plan.DICT_INFO_FIELDS_KPL, field_o.name_mes)
    if fl_access == False:
        msg_err = f'Нет доступа'
        fl_check_field = False

    return fl_check_field, msg_err
@CQT.onerror
def tbl_kal_pl_cellChanged(self: mywindow, *args):
    tbl = self.ui.tbl_kal_pl

    t = CQT.TableContext(tbl)

    row = t.current_row()
    if row.no_selection:
        return

    name_field = t.current_column_name()
    DICT_FIELDS = DTCLS.FIELDS_DB_INFO.dict_fields
    field_o:CMS.Field_db_info = DICT_FIELDS[name_field]
    DTCLS.current_podr_for_edit = field_o.table_mes
    fl_check_field = check_edit_permission()

    s_num_kpl = int(row.value('plan.Пномер'))
    poz = CMS.Pozition(s_num_kpl, DTCLS.db_kplan, DTCLS.bd_naryad, DTCLS.db_resxml, DTCLS.db_users, self)

    new_val = row.value(name_field)
    data_row = load_db(self, s_num_kpl)
    old_val = data_row[name_field]

    checker_o = CMS.Checker_val_fields(poz,DTCLS.DICT_ITERS_FOR_CHECK_FIELDS)

    fl_update_val = False
    if fl_check_field:
        new_val = checker_o.fix_value_field(new_val, field_o)
        fl_update_val = checker_o.check_value_field(new_val, field_o)
        dict_checked = checker_o.get_results()
        msg_err = dict_checked[field_o.name_mes].msg

    fl_return_back = False
    if fl_check_field and fl_update_val:
        s_num = int(
            data_row[field_o.parent_tbale.source_table_primary_name.name_mes
            ])  # поле которое имеет ссылку на УИД по которому можно найти запись ячейки в ее таблице.
        rez = CSQ.custom_request_c(self.db_kplan, f"""UPDATE {field_o.select_db_tbl_name} SET ({field_o.field_mes})
                = (?) WHERE {field_o.parent_tbale.table_primary_name} 
          == {s_num};""", list_of_lists_c=[new_val])
        if rez:
            tbl.blockSignals(True)
            row.set_value(name_field, str(new_val))
            oforml_row_plan_tbl(row)
            new_val_dict = delta_dict = {field_o.name_mes :new_val}
            old_val_dict  = {field_o.name_mes :old_val}
            post_edit_handling(delta_dict,old_val_dict,new_val_dict,s_num_kpl)
            obj_jur = CMS.Logs(self.bd_files)
            obj_jur.add_note(s_num, name_field, new_val, 'tbl_kal_pl')
            tbl.blockSignals(False)

        else:
            msg_err = f'Ошибка записи в БД'
            fl_return_back = True
    else:
        fl_return_back = True

    if fl_return_back:
        tbl.blockSignals(True)
        row.set_value(name_field, str(old_val))
        tbl.blockSignals(False)
        CQT.msgbox(msg_err)
        return


def check_edit_poz(old_list:dict,dict_edit_new:dict,poz:CMS.Pozition)->bool:
    tbl_edit = DTCLS.app_self.ui.tbl_pl_add_poz
    checker_o = CMS.Checker_val_fields(poz,DTCLS.DICT_ITERS_FOR_CHECK_FIELDS)
    DICT_FIELDS = DTCLS.FIELDS_DB_INFO.dict_fields
    for key in dict_edit_new.keys():
        val = dict_edit_new[key]
        if str(val) == str(old_list[key]):
            continue

        field_o = DICT_FIELDS[key]
        val = checker_o.fix_value_field(val,field_o)
        succ = checker_o.check_value_field(val,field_o)


    dict_checked = checker_o.get_results()
    #======end for==============

    list_errors=[{'Поле':DICT_FIELDS[nf],'Содержимое':_.msg} for nf, _ in dict_checked.items() if not _.success ]

    if list_errors:
        CQT.msgboxg_get_table_ok_inf(DTCLS.app_self, 'Результаты проверки:', list_errors,
                                     WindowTitle=f'{CEMOJ.EmojiMain.Эмоции.confused} Ошибки при проверке',
                                     styleSheet=CQT.MES_CSS)
        return False
    return True
@CQT.onerror
def fnc_click_load_tbl_edit_poz(ind:QtCore.QModelIndex):
    t = CQT.TableContext(DTCLS.app_self.ui.tbl_select_etap_edit_poz)
    item = t.tbl.item(ind.row(), ind.column())
    data = CQT.getCustData(item,modifier=101)
    DTCLS.current_podr_for_edit = data
    attach_tbl_pl_add_poz_validator(DTCLS.app_self, DTCLS.app_self.ui.tbl_pl_add_poz)
    load_edit_poz(DTCLS.app_self)
@CQT.onerror
def load_edit_poz(self: mywindow):
    podr = DTCLS.current_podr_for_edit
    t = CQT.TableContext(self.ui.tbl_kal_pl)
    row = t.current_row()
    if row.no_selection:
        CQT.msgbox(f'Не выбрана строка плана')
        return
    if podr is None or podr == "":
        CQT.clear_tbl(self.ui.tbl_pl_add_poz)
        return
    podr_o = DTCLS.FIELDS_DB_INFO.tables_db.get_table(podr)
    if podr_o is None:
        CQT.msgbox(f'Ошибка сопоставления подразделений')
        return
    pnom = row.value('plan.Пномер')
    if pnom == '-1':
        return
    poz = CMS.Pozition(pnom,
                       CFG.Config.project.db_kplan,
                       CFG.Config.project.db_naryad,
                       CFG.Config.project.db_resxml,
                       CFG.Config.project.db_users,
                       self
                       )
    poz.load_kpl_table('пл_оуп')
    data_oup = poz.dict_tables['пл_оуп']

    dict_from_db = get_line_to_edit_podr(self, pnom,podr_o)
    list_fix_names = []
    DICT_FIELDS = DTCLS.FIELDS_DB_INFO.dict_fields
    for k,v in dict_from_db[0].items():
        name = f'{podr_o.name}.{k}'
        if name in DICT_FIELDS:
            if DICT_FIELDS[name].for_edit:
                field_o = DICT_FIELDS[name]
                list_fix_names.append({
                                        '_s_num':field_o.usr_idx,
                                        '_Name':name,
                                       'Параметр':field_o.name_alias,
                                       'Значение':v,
                                       'Описание':field_o.description})
        else:
            raise ValueError(f'Неверное имя столбца:{name}')
    list_fix_names.sort(key=lambda x: x["_s_num"])  # Сортировка по номерам полей
    CQT.fill_wtabl(list_fix_names, self.ui.tbl_pl_add_poz,
                   auto_type=False,styleSheet=CQT.MES_EDIT_CSS,height_row=44,
                   )

    t = CQT.TableContext(self.ui.tbl_pl_add_poz)
    def fnc_switch(field_o:CMS.Field_db_info,row:CQT.TableRow,tbl:CQT.QtWidgets.QTableWidget,new_val:bool,i,j):
        with CQT.table_updating(tbl):
            if str(F.valm(new_val)) == str(field_o.is_bool):
                row.set_value('Значение','1')
            else:
                row.set_value('Значение', '0')
        pass

    t.hide_if_not_dev(CFG)
    for row in t.rows():
        name = row.value("_Name")
        field_o = DICT_FIELDS[name]
        if field_o.sys_hide:
            row.hide(True)
        if field_o.is_bool:
            is_on = row.value('Значение') == str(field_o.is_bool)
            CQT.add_check_box_switcher(t.tbl,row.i,row.nf['Значение'], is_on,partial(fnc_switch,field_o,row))
    def fnc_select_date(lbl:CQT.InteractiveLabelInstance,self,i,j,tbl:QtWidgets.QTableWidget,*args):
        suc, rez = CQT.get_data_dialog_choose(self,'')
        if not suc:
            return
        date = rez['date_from']
        date_str = F.datetostr(date,"%Y-%m-%d")
        lbl.set_text(date_str)
        tbl.item(i,j).setText(date_str)

    for row in t.rows():
        name = row.value("_Name")
        field_o = DICT_FIELDS[name]
        if field_o.field_mes == podr_o.table_primary_name:
            row.set_editable('Значение', False)
        else:
            if 'дата' not in field_o.field_mes.lower():
                row.set_editable('Значение', True)
            else:
                row.set_editable('Значение', False)
                widg = CQT.add_interactive_label(t.tbl, row.i, row.nf['Значение'], row.value('Значение'),
                                                 parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать дату', fnc_select_date,
                                cell_val=t.tbl, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                      'icons', 'btn_select']))

    if podr == 'plan':
        for row in t.rows():
            name = row.value("_Name")

            if name == 'plan.Направление_деятельности':

                widg = CQT.add_interactive_label(t.tbl, row.i, t.nf['Значение'], '',
                                                 parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать', on_clicked=fnc_select_nd,
                                cell_val=t.tbl, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                          'icons', 'btn_select']))
                napr_val = row.value('Значение')
                if F.is_numeric(napr_val):
                    if int(napr_val) in self.Data_plan.DICT_NAPR_DEYAT:
                        name_napr = self.Data_plan.DICT_NAPR_DEYAT[int(napr_val)]['Псевдоним']
                        widg.set_text(name_napr)

            if name == 'plan.Статус':

                list_status = []
                for key in self.Data_plan.DICT_STATUS_POZ.keys():
                    list_status.append(self.Data_plan.DICT_STATUS_POZ[key]['Имя'])

                CQT.add_combobox(self, self.ui.tbl_pl_add_poz, row.i, t.nf['Значение'], list_status, first_void=False,
                                 conn_func=select_status)
                try:
                    row.widget('Значение').setCurrentText(
                        self.Data_plan.DICT_STATUS_POZ[int(row.value('Значение'))]['Имя'])
                except:
                    pass

            if name == 'plan.Статус_норм':
                list_status_norm = []
                for key in self.Data_plan.DICT_STATUS_NORM.keys():
                    list_status_norm.append(self.Data_plan.DICT_STATUS_NORM[key]['Имя'])

                CQT.add_combobox(self, self.ui.tbl_pl_add_poz, row.i, t.nf['Значение'], list_status_norm, first_void=False,
                                 conn_func=select_status_norm)
                try:
                    row.widget('Значение').setCurrentText(
                        self.Data_plan.DICT_STATUS_NORM[int(row.value('Значение'))]['Имя'])
                except:
                    pass

            if name == 'plan.Этапы_ЕРП':
                list_etapi_erp = []
                for key in self.Data_plan.DICT_STATUS_ETAPI_ERP.keys():
                    list_etapi_erp.append(self.Data_plan.DICT_STATUS_ETAPI_ERP[key]['Имя'])
                CQT.add_combobox(self, self.ui.tbl_pl_add_poz, row.i, t.nf['Значение'], list_etapi_erp, first_void=False,
                                 conn_func=select_etapi_erp)
                try:
                    row.widget('Значение').setCurrentText(
                        self.Data_plan.DICT_STATUS_ETAPI_ERP[int(row.value('Значение'))]['Имя'])
                except:
                    pass

    if podr == 'пл_топ':
        for row in t.rows():
            name = row.value("_Name")
            if name == 'пл_топ.Вид':
                widget = CMS.TypesWorkingByDirections().change_vid_po_napr(  # 25.08.25
                    self,
                    self.ui.tbl_pl_add_poz,
                    row.i,
                    row.nf['Значение'],
                )
                if int(row.value('Значение')) in self.Data_plan.DICT_VID_PO_NAPR:
                    lbl:CQT.QtWidgets.QLabel = widget.label
                    lbl.setText(
                        self.Data_plan.DICT_VID_PO_NAPR[int(row.value('Значение'))]['Имя'])

            if name  in ('пл_топ.Отв_технолог', 'пл_топ.Отв_по_ресурсной'):
                field_o = DICT_FIELDS[name]
                def fnc_select_accountable_tech(lbl: CQT.InteractiveLabelInstance, app_self, i, j, tbl: CQT.QtWidgets.QTableWidget):
                    def fnc_oform(tbl):
                        t = CQT.TableContext(tbl)
                        t.hide_if_not_dev(CFG)

                    tmpl = [{
                        '_Пномер': _['Пномер'],
                        '': CEMOJ.ПерсоналРоли.engineer.symbol,
                        'Должность': _['Должность'],
                        'ФИО': name,
                    } for name, _ in DTCLS.app_self.DICT_EMPLOEE_FULL.items() if
                        _['Подразделение'] == 'Технологический отдел Производства' and _['Компания'] == CFG.Config.place.Имя]
                    t = CQT.TableContext(tbl)
                    row = t.get_row(i)
                    rez = CQT.msgboxg_get_table(DTCLS.app_self, f'Выбор {field_o.field_alias}', tmpl, styleSheet=CQT.MES_CSS,
                                                selectRows=True, ExtendedSelection=False, func_oform_tbl=fnc_oform,
                                                selection_from_tbl=True)
                    if not rez:
                        return

                    row.set_value('Значение', rez['ФИО'])
                    lbl.set_text(rez['ФИО'])


                widg = CQT.add_interactive_label(t.tbl, row.i, t.nf['Значение'], '',
                                                 parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать', on_clicked=fnc_select_accountable_tech,
                                cell_val=t.tbl, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                       'icons', 'btn_select']))

    if podr == 'пл_оуп':
        for row in t.rows():
            name = row.value("_Name")
            if name == 'пл_оуп.№ERP':
                Пномер_ЗП = data_oup['Пномер_ЗП']
                ref_zp = None
                if F.is_numeric(Пномер_ЗП) and Пномер_ЗП:
                    ref_zp = CSQ.custom_request_c(self.db_kplan,f"""SELECT 
                                               Ref_Key_py 
                                        FROM знпр WHERE s_num == {Пномер_ЗП}; """,one_column=True,
                                                  one=True,hat_c=False)
                if F.is_unique_identifier(Пномер_ЗП):
                    ref_zp = Пномер_ЗП
                widg = CQT.add_interactive_label(t.tbl, row.i, row.nf['Значение'], row.value('Значение'),
                                                 parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать ЗП', select_py,
                                cell_val=None, img_path=  F.sep().join([F.path_to_execut_file_c(),
                                                                                  'icons','btn_select']))
                if ref_zp:
                    add_btns_select_poz_after_py(self,t.tbl,ref_zp)

            if name == 'пл_оуп.ПКК':
                add_widget_pkk(t,row)

    if podr == 'пл_компл':
        for row in t.rows():
            name = row.value("_Name")
            if name == 'пл_компл.Статус_тара':
                list_status_tara = dict()
                for key in self.Data_plan.DICT_STATUS_TARA_NAME.keys():
                    list_status_tara[key] = self.Data_plan.DICT_STATUS_TARA_NAME[key]['prim']

                CQT.add_combobox(self, self.ui.tbl_pl_add_poz, row.i, row.nf['Значение'], list_status_tara,
                                 first_void=False,
                                 conn_func=select_status_tara)
                try:
                    row.set_value ('Значение',
                        self.Data_plan.DICT_STATUS_TARA_NUM[int(row.value('Значение'))]['name'])
                except:
                    pass

def ______________NEW_________________________________():pass

@CQT.onerror
def load_tbl_add_new_poz(self: mywindow, *args)->bool:
    def fill_val(list_fields:list[dict], name:str,value:str='')->list[dict]:
        for it in list_fields:
            if it['_Name'] == name:
                it['Значение'] = value
                break
        return list_fields

    list_fields = [{'_s_num':_.usr_idx,
        '_Name': _.name_mes,
     'Параметр': _.name_alias,
     'Значение': '',
     'Описание': _.description} for _ in DTCLS.FIELDS_DB_INFO.list_fields if _.for_insert]

    list_fields.sort(key=lambda x:x["_s_num"])#Сортировка по номерам полей
    # ===========================
    t = CQT.TableContext(self.ui.tbl_kal_pl)
    cur_row = t.current_row()
    if not  cur_row.no_selection and CQT.get_key_modifiers(self) == ['shift']:
        num_kpl = int(cur_row.value('plan.Пномер'))
        if num_kpl <0:
            CQT.msgbox(f'Не выбрана строка позиции в плане')
            return
        poz = CMS.Pozition(num_kpl, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
        poz.load_kpl_table('пл_оуп')
        nom_pr = poz.dict_tables['пл_оуп']['№проекта']
        nom_pu = poz.dict_tables['пл_оуп']['№ERP']
        nom_pkk = poz.dict_tables['пл_оуп']['ПКК'] if F.is_numeric(poz.dict_tables['пл_оуп']['ПКК'])  else ''
        ref_Key_py = poz.dict_tables['пл_оуп']['Ref_Key_py']
        list_fields = fill_val(list_fields, 'знпр.№проекта', nom_pr)
        list_fields = fill_val(list_fields, 'знпр.№ERP', nom_pu)
        list_fields = fill_val(list_fields, 'пл_оуп.ПКК', nom_pkk)
        list_fields = fill_val(list_fields, 'знпр.Ref_Key_py', ref_Key_py)


    # ===========================
    CQT.fill_wtabl(list_fields, self.ui.tbl_pl_add_poz,auto_type=False,
                   styleSheet=CQT.MES_EDIT_CSS,selectionMode='SingleSelection', height_row=44,
                   )

    DICT_FIELDS = DTCLS.FIELDS_DB_INFO.dict_fields
    t_pl = CQT.TableContext(self.ui.tbl_pl_add_poz)
    with CQT.table_updating(t_pl.tbl):
        for row in t_pl.rows():
            name = row.value("_Name")
            if name in DICT_FIELDS:
                clr = DICT_FIELDS[name].table_color
                clr = clr.align_colors(level_percent=-30, saturation_percent=-20,copy=True)
                row.set_color_font(*clr.rgb,col_name='Параметр')
                row.set_font_format(bold=True,col_name='Параметр')

            if name=='знпр.Ref_Key_py':
                if row.value("Значение"):
                    add_btns_select_poz_after_py(self,t_pl.tbl,row.value("Значение"))
                row.hide()
            if name in ('пл_оуп.Номенклатура_ЕРП',
                       'пл_оуп.Количество',
                       'пл_ко.Вес_ВО',
                       'пл_оуп.Вес_кг',
                       'пл_оуп.НомПартии_ЗП',
                       'пл_оуп.ПКК',
                       'пл_оуп.№проекта',
                       'plan.Позиция'):
                row.set_editable("Значение",True)
            if name=='plan.Направление_деятельности':
                widg = CQT.add_interactive_label(t_pl.tbl, row.i, t_pl.nf["Значение"], '',
                                                 parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать', on_clicked=fnc_select_nd,
                                cell_val=(t,row), img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                          'icons', 'btn_select']))

            if name == 'знпр.№ERP':
                int_lbl = widg = CQT.add_interactive_label(t_pl.tbl, row.i, t_pl.nf["Значение"], row.value('Значение'),
                                                 parent_self=self)
                widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать ЗП', select_py,
                                cell_val=None, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                                      'icons', 'btn_select']))

                if row.value("Значение"):
                    int_lbl.set_text(row.value("Значение"))


            if name == 'plan.Статус':
                CQT.add_combobox(self, t_pl.tbl, row.i, t_pl.nf["Значение"],
                                 [_ for _ in list(self.Data_plan.DICT_STATUS_POZ_NAME.keys()) if
                                  _ in ('Резерв', 'Подготовка', "Долгосрочный")],
                                 first_void=True,
                                 conn_func=select_status)
            if name == 'пл_оуп.ПКК':
                add_widget_pkk(t_pl,row)

        CMS.load_column_widths(self,t_pl.tbl)
        t_pl.hide_if_not_dev(CFG)
    return True


def check_add_poz(list_add:dict)->bool:

    rez = CSQ.custom_request_c(DTCLS.db_kplan, f"""SELECT plan.Позиция, пл_оуп.№проекта, пл_оуп.№ERP
                FROM plan 
              INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер 
             WHERE plan.Позиция = "{list_add['plan.Позиция']}" AND 
              пл_оуп.№проекта = "{list_add['знпр.№проекта']}" AND 
               пл_оуп.№ERP = "{list_add['знпр.№ERP']}" """, one=True)
    if rez and len(rez) > 1:
        CQT.msgbox(
            f"Уже существует в базе {list_add['знпр.№проекта']} {list_add['знпр.№ERP']} {list_add['plan.Позиция']}")
        return False

    DICT_FIELDS = DTCLS.FIELDS_DB_INFO.dict_fields


    checker_o = CMS.Checker_val_fields(None,DTCLS.DICT_ITERS_FOR_CHECK_FIELDS)
    for key in list_add.keys():
        val = list_add[key]
        if key not in ('знпр.№ERP'):
            if val:
                if '*' == str(val)[0]:
                    CQT.msgbox(f'{key} не указан')
                    return False
        field_o = DICT_FIELDS[key]
        val = checker_o.fix_value_field(val, field_o)
        if  field_o.name_mes not in ('plan.Статус'):
            succ = checker_o.check_value_field(val, field_o)

    dict_checked = checker_o.get_results()

    list_errors = [{'Поле': DICT_FIELDS[nf], 'Содержимое': _.msg} for nf, _ in dict_checked.items() if not _.success]

    if list_errors:
        CQT.msgboxg_get_table_ok_inf(DTCLS.app_self, 'Результаты проверки:', list_errors,
                                     WindowTitle=f'{CEMOJ.EmojiMain.Эмоции.confused} Ошибки при проверке',
                                     styleSheet=CQT.MES_CSS)
        return False

    return True




def ______________OK_________________________________():pass


@CQT.onerror
def fill_oup_fields_from_znpr(self: mywindow, num_kpl):
    req = f"""SELECT  знпр.s_num, 
            знпр.Год, 
            знпр.Дата_заявки_на_произв, 
            знпр.№ERP, 
            знпр.№проекта, 
            знпр.Статус_поз_ЕРП, 
            знпр.Заказ_клиента, 
            знпр.Дата_отгрузки_ПУ, 
            знпр.ЗП_келаст_КЭ, 
            знпр.Этапы_ЕРП, 

            знпр.Ref_Key_py
            FROM знпр WHERE s_num IN (SELECT Пномер_ЗП FROM пл_оуп WHERE НомПл = {int(num_kpl)})"""
    row_znpr = CSQ.custom_request_c(self.db_kplan, req, rez_dict=True)
    row_znpr = row_znpr[0]
    list_data = [row_znpr['Дата_заявки_на_произв'],
                 row_znpr['№ERP'],
                 row_znpr['№проекта'],
                 row_znpr['Дата_отгрузки_ПУ']
                 ]
    CSQ.custom_request_c(self.db_kplan, f"""UPDATE пл_оуп SET (Дата_заявки_на_произв,№ERP,№проекта,Дата_отгрузки_ПУ)
         = ({CSQ.questions_for_mask(list_data)}
         ) WHERE НомПл = {int(num_kpl)}""", list_of_lists_c=[list_data])


def post_edit_handling(delta_dict:dict, old_val_dict:dict, new_val_dict:dict,pnom:int):
    podr = DTCLS.current_podr_for_edit
    if podr is None:
        raise ValueError(f'podr == None')
    if podr == 'plan' and 'plan.Фдата_получения_КД' in delta_dict:
        if old_val_dict['plan.Фдата_получения_КД'] != new_val_dict['plan.Фдата_получения_КД']:
            obj_msg = CMS.Msg_b24(DTCLS.db_kplan, DTCLS.bd_naryad, DTCLS.db_resxml, DTCLS.db_users, pnom)
            obj_msg.send_msg('obtained_kd')

    if podr == 'пл_топ' and 'пл_топ.Вид' in delta_dict:
        if old_val_dict['пл_топ.Вид'] != new_val_dict['пл_топ.Вид']:
            obj_msg = CMS.Msg_b24(DTCLS.db_kplan, DTCLS.bd_naryad, DTCLS.db_resxml, DTCLS.db_users, pnom)
            obj_msg.send_msg('recalc_time_technolog')

    if podr == 'пл_топ' and 'пл_топ.Спецификация_код_ЕРП' in delta_dict:
        if old_val_dict['пл_топ.Спецификация_код_ЕРП'] != new_val_dict['пл_топ.Спецификация_код_ЕРП']:
            obj_msg = CMS.Msg_b24(DTCLS.db_kplan, DTCLS.bd_naryad, DTCLS.db_resxml, DTCLS.db_users, pnom)
            obj_msg.send_msg('obtained_kod_res')

    if podr == 'пл_оуп':
        if 'пл_оуп.Пномер_ЗП' in delta_dict:
            if str(new_val_dict['пл_оуп.Пномер_ЗП']) != '0':
                fill_oup_fields_from_znpr(DTCLS.app_self, pnom)

        if 'пл_оуп.№ERP' in delta_dict:
            if old_val_dict['пл_оуп.№ERP'] != new_val_dict['пл_оуп.№ERP']:
                py = new_val_dict['пл_оуп.№ERP']
                obj_msg = CMS.Msg_b24(DTCLS.db_kplan, DTCLS.bd_naryad, DTCLS.db_resxml, DTCLS.db_users, pnom)
                obj_msg.send_msg('reset_py', additional_str=py)

        if 'пл_оуп.ПКК' in delta_dict:
            if not new_val_dict['пл_оуп.ПКК']:
                old_pkk = old_val_dict['пл_оуп.ПКК']
                if F.is_numeric(old_pkk):
                    del_file_pkk(int(old_pkk))
def load_client_order_num(ref:str)->str|None:
    text = f"""
                    ВЫБРАТЬ
            ЗаказКлиента.Номер КАК Номер,
            ЗаказКлиента.Дата КАК Дата
        ИЗ
            Документ.ЗаказКлиента КАК ЗаказКлиента
        ГДЕ
            ЗаказКлиента.Ссылка = &Ссылка
                    """

    refs = APIERP.Refs_wet(text)
    ref_obj = APIERP.Ref_wet('Ссылка', 'Документы.ЗаказКлиента', ref)
    refs.add_ref(ref_obj)
    key, res = APIERP.get_wet_request(text=text, refs=refs)
    if key != 200:
        CQT.msgbox(f'Ошибка получения данных ЗаказКлиента из ЕРП ')
        return
    data = res['data'][0]
    year = F.dateStrToStr(data["Дата"],"%Y-%m-%dT%H:%M:%S","%Y")
    num = f'{year} {data["Номер"]}'
    update_client_order_num(num,ref)
    return num
def update_client_order_num(num,ref):
    CSQ.custom_request_c(DTCLS.db_kplan,f"""UPDATE знпр SET client_order_num = '{num}' 
            where client_order_Key='{ref}';""")
    print(f'update_client_order_num: {num}, {ref}')

def btn_pl_ok_add_poz_click(self, *args):
    def add_py_from_erp(Ref_Key_py, nom_proj):
        m = CODAT.OrdersComposit()
        code, list_data = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                                         wet_filtr=f"?$filter= Ref_Key eq guid'{Ref_Key_py}'"
                                                   f" &$select=Date,Number,Комментарий,Статус,ДатаПотребности,ДокументОснование,ДокументОснование_Type",
                                         with_cod=True)
        if code != 200:
            CQT.msgbox(f'Ошибка связи с ЕРП  Document_ЗаказНаПроизводство2_2  код {code}')
            return False
        if len(list_data) == 0:
            CQT.msgbox(f"Не найден в ЕРП ЗП с Ref_Key_py {Ref_Key_py}")
            return False

        if list_data[0]['ДокументОснование_Type'] not in (
                'StandardODATA.Document_ЗаказКлиента', 'StandardODATA.Document_ЗаказНаСборку',
                'StandardODATA.Document_ЗаказНаВнутреннееПотребление', 'StandardODATA.Document_ЗаказДавальца2_5'):
            CQT.msgbox(
                f"Основание для {self.place.doc_prefix}:\n{list_data[0]['ДокументОснование_Type']}.\n Нужен Заказа клиента/Заказ на сборку/ЗНВП")
            return

        client_order = list_data[0]['ДокументОснование']
        sb_order = ''
        znvp_order = ''
        zDav_order = ''

        if list_data[0]['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказНаСборку':
            sb_order = list_data[0]['ДокументОснование']
            code, data_sb = m.get_response(doc_name=f"Document_ЗаказНаСборку(guid'{sb_order}')",
                                           wet_filtr=f"?$select=ДокументОснование_Key,Номенклатура_Key", with_cod=True)
            if code != 200:
                CQT.msgbox(f'Ошибка связи с ЕРП Document_ЗаказНаСборку код {code}')
                return False
            client_order = data_sb['ДокументОснование_Key']

        if list_data[0]['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказНаВнутреннееПотребление':
            znvp_order = list_data[0]['ДокументОснование']
            client_order = ''

        if list_data[0]['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказДавальца2_5':
            zDav_order = list_data[0]['ДокументОснование']
            client_order = ''

        year = F.datetostr(F.strtodate(list_data[0]['Date'], "%Y-%m-%dT%H:%M:%S"), "%Y")
        date = F.datetostr(F.strtodate(list_data[0]['Date'], "%Y-%m-%dT%H:%M:%S"), "%Y-%m-%d")
        date_otgr = F.datetostr(F.strtodate(list_data[0]['ДатаПотребности'], "%Y-%m-%dT%H:%M:%S"), "%Y-%m-%d")
        list_to_add = [int(year), date, list_data[0]['Number'], nom_proj, list_data[0]['Статус'],
                       '', date_otgr, '', 1, Ref_Key_py, list_data[0]['Комментарий'], sb_order, client_order,
                       znvp_order, zDav_order]

        CSQ.custom_request_c(self.db_kplan, f"""INSERT INTO знпр (Год, 
                        Дата_заявки_на_произв, 
                        №ERP, 
                        №проекта, 
                        Статус_поз_ЕРП, 
                        Заказ_клиента, 
                        Дата_отгрузки_ПУ, 
                        ЗП_келаст_КЭ, 
                        Этапы_ЕРП,
                        Ref_Key_py,
                        Комментарий,
                        sb_order_Key,
                        client_order_Key,
                        znvp_order_Key,
                        zDav_order_Key
                        ) VALUES ({CSQ.questions_for_mask(list_to_add)})""", list_of_lists_c=[list_to_add])

        if client_order:
            load_client_order_num(client_order)

    def apply_edit_tabel(self, list_sql):
        for custom_request_c in list_sql:
            CSQ.custom_request_c(self.db_kplan, custom_request_c)
        CMS.agregate_m_cld()
        CQT.msgbox(f'Успешно.')

    @CQT.onerror
    def add_new_poz(self: mywindow)->tuple(bool,int|None):
        tbl = self.ui.tbl_pl_add_poz
        list_wet = CQT.list_from_wtabl_c(tbl, rez_dict=True)
        list_add = {_['_Name']: _['Значение'] for _ in list_wet}
        list_add = F.trim_collection(list_add)  # 05.06.2025

        link = None
        if not F.is_numeric(list_add['пл_оуп.ПКК']):
            link = copy.copy(list_add['пл_оуп.ПКК'])
            pkk_id = ""
            list_add['пл_оуп.ПКК'] = pkk_id

        if not check_add_poz(list_add):
            return False, None

        if link:
            pkk_id = upload_pkk(link)
            if not pkk_id:
                CQT.msgbox(f'Ошибка добавления ПКК')
                return False, None
            list_add['пл_оуп.ПКК'] = pkk_id

        s_num_py = 0
        if F.is_unique_identifier(list_add['знпр.Ref_Key_py']):
            list_py_from_mes = CSQ.custom_request_c(self.db_kplan, f"""SELECT Ref_Key_py FROM знпр WHERE 
             Ref_Key_py = "{list_add['знпр.Ref_Key_py']}";""", rez_dict=True)
            if len(list_py_from_mes) == 0:
                add_py_from_erp(list_add['знпр.Ref_Key_py'], list_add['знпр.№проекта'])

            list_py_from_mes = CSQ.custom_request_c(self.db_kplan,
                                                    f"""SELECT s_num FROM знпр WHERE Ref_Key_py 
                                                         = "{list_add['знпр.Ref_Key_py']}";""",
                                                    rez_dict=True)
            if len(list_py_from_mes) == 0:
                CQT.msgbox(f"Не найден в МЕС ЗП с Ref_Key_py {list_add['знпр.Ref_Key_py']}")
                return False, None
            s_num_py = list_py_from_mes[0]['s_num']

        pnom = CSQ.custom_request_c(self.db_kplan, f"""INSERT INTO plan(Дата_внесения,
                    Позиция,
                    Направление_деятельности,
                    Статус,
                    poki
                    )
                    VALUES (?,?,?,?,?) RETURNING Пномер;""",
                                list_of_lists_c=[F.now("%Y-%m-%d"), list_add['знпр.№проекта'],
                                                list_add['plan.Направление_деятельности'],
                                                int(list_add['plan.Статус']), self.place.poki],
                                            returning=True, one=True,one_column=True,hat_c=False)

        list_podr = [_ for _ in CSQ.get_list_of_tables_c(self.db_kplan) if _.startswith('пл_')]
        for podr in list_podr:
            CSQ.custom_request_c(self.db_kplan, f"""INSERT INTO {podr}(
                        НомПл
                        )
                        VALUES (?);""", list_of_lists_c=[[pnom]])

        vals = [

            list_add['знпр.№проекта'],
            s_num_py,
            list_add['пл_оуп.Количество'],
            list_add['пл_оуп.ПКК'],
            list_add['пл_оуп.Номенклатура_ЕРП'],
            list_add['пл_оуп.Вес_кг'].replace(',', '.'),
            list_add['пл_оуп.НомПартии_ЗП'], ]

        CSQ.custom_request_c(self.db_kplan, f"""UPDATE пл_оуп SET(
               №проекта,
               Пномер_ЗП,
               Количество,
               ПКК,
               Номенклатура_ЕРП, 
               Вес_кг,
               НомПартии_ЗП  
               ) =
                ({"?, ".join([""] * len(vals)) + "?"}) WHERE НомПл == {pnom};""", list_of_lists_c=vals)
        if s_num_py != 0:
            fill_oup_fields_from_znpr(self, pnom)

        vals = [list_add['пл_ко.Вес_ВО'].replace(',', '.'),
                ]

        CSQ.custom_request_c(self.db_kplan, f"""UPDATE пл_ко SET(
                       Вес_ВО
                       ) =
                        (?) WHERE НомПл == {pnom};""", list_of_lists_c=vals)


        obj_msg = CMS.Msg_b24(self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, pnom)
        obj_msg.send_msg('add_new_poz')

        return True,pnom

    @CQT.onerror
    def edit_poz(self: mywindow):
        @CQT.onerror
        def fill_changes_into_user_tbl(delta_dict, pnom):
            DICT_FIELDS=DTCLS.FIELDS_DB_INFO.dict_fields
            tbl = self.ui.tbl_kal_pl
            with CQT.table_updating(tbl):
                t = CQT.TableContext(tbl)
                row = t.find_row({'plan.Пномер':pnom},True)
                if row is None:
                    return
                for field in delta_dict.keys():
                    if field in DICT_FIELDS:
                        indx = DICT_FIELDS[field].tbl_idx
                        if indx:
                            row.set_value(field,str(delta_dict[field]))
                oforml_row_plan_tbl(row)

        def get_val(t,name)->str:
            row = t.find_row({'_Name': name}, True)
            return row.value('Значение')

        def add_ref_zp(num_pr: str, ref_zp: str) -> int:
            def get_zp(ref_zp) -> dict | None | False:
                py_from_mes = CSQ.custom_request_c(self.db_kplan,
                f"""SELECT Ref_Key_py, s_num FROM знпр WHERE Ref_Key_py = "{ref_zp}";""",
                                                   rez_dict=True, one=True)
                return py_from_mes

            zp_from_db = get_zp(ref_zp)
            if not zp_from_db:
                add_py_from_erp(ref_zp, num_pr)
                zp_from_db = get_zp(ref_zp)

            return zp_from_db['s_num']

        tbl = self.ui.tbl_pl_add_poz
        podr = DTCLS.current_podr_for_edit
        if podr is None or podr == '':
            return
        table_o = DTCLS.FIELDS_DB_INFO.tables_db.get_table(podr)
        if table_o is None:
            return
        name_field = table_o.table_primary_full_name
        t = CQT.TableContext(tbl)
        pnom = int(get_val(t,name_field))

        old_val_dict = get_line_to_edit_podr(self, pnom,table_o)
        if not old_val_dict:
            return
        old_val_dict = {f'{table_o.name}.{k}':str(_) for k, _ in old_val_dict[0].items()}
        new_val_dict = {_['_Name']: _['Значение'] for _ in CQT.list_from_wtabl_c(tbl, hat_c=True, rez_dict=True)}
        poz = CMS.Pozition(pnom,DTCLS.db_kplan,DTCLS.bd_naryad,DTCLS.db_resxml,DTCLS.db_users,DTCLS.app_self)

        if podr == 'пл_оуп':
            if F.is_unique_identifier(new_val_dict['пл_оуп.Пномер_ЗП']):
                ref_zp = new_val_dict['пл_оуп.Пномер_ЗП']
                s_num_zp = add_ref_zp(new_val_dict['пл_оуп.№проекта'], ref_zp)
                if not s_num_zp:
                    CQT.msgbox(f"Не найден в МЕС ЗП с Ref_Key_py {ref_zp}")
                    return False
                new_val_dict['пл_оуп.Пномер_ЗП'] = str(s_num_zp)

            link = None
            if not F.is_numeric(new_val_dict['пл_оуп.ПКК']):
                link = copy.copy(new_val_dict['пл_оуп.ПКК'])
                pkk_id = 0
                new_val_dict['пл_оуп.ПКК'] = pkk_id


        if not check_edit_poz(old_val_dict,new_val_dict,poz):
            return

        if podr == 'пл_оуп':
            if link:
                pkk_id = upload_pkk(link)
                if not pkk_id:
                    CQT.msgbox(f'Ошибка добавления ПКК')
                    return False
                new_val_dict['пл_оуп.ПКК'] = pkk_id

        old_val_dict.pop(name_field)
        new_val_dict.pop(name_field)
        delta_dict = dict()

        obj_jur = CMS.Logs(self.bd_files)
        for key in new_val_dict.keys():
            if str(new_val_dict[key]) != str(old_val_dict[key]):
                delta_dict[key] = new_val_dict[key]
                obj_jur.add_note(pnom, key, new_val_dict[key], 'tbl_kal_pl')

        list_fields = list(delta_dict.keys())
        list_vals = list(delta_dict.values())
        if not delta_dict:
            return True

        if list_fields == []:
            return


        CSQ.custom_request_c(self.db_kplan, f"""UPDATE {podr} SET({','.join(list_fields)}) =
         ({'?,'.join(['' for _ in list_fields]) + '?'}) WHERE {name_field} = {pnom};""", list_of_lists_c=list_vals)

        fill_changes_into_user_tbl(delta_dict, pnom)

        post_edit_handling(delta_dict,old_val_dict,new_val_dict,pnom)


        CQT.msgbox(f'Успешно')
        return True

    if DTCLS.EDIT_TABEL_MODE:
        list_sql = check_edit_tabel(self)
        if list_sql:
            apply_edit_tabel(self, list_sql)
        gui_mode_off()
        return

    if DTCLS.ADD_POZ_MODE:
        succ, pnom = add_new_poz(self)
        if succ:
            update_local_graf(True,pnom,not is_local_gant_hidden(self) )
            load_table_db(self)
            CQT.msgbox(f'Успешно')
            gui_mode_off()

    if DTCLS.EDIT_POZ_MODE:
        rez = edit_poz(self)
        if rez != None:
            update_local_graf( True,DTCLS.current_id_poz_kpl,not is_local_gant_hidden(self))
            gui_mode_off()

    if DTCLS.SETTINGS_PL_MODE:
        gui_mode_off()

def ______________TABEL________________________________():pass
def check_edit_tabel(self)->list|None:
    month = DTCLS.edit_tabel_current_month
    if month == '':
        return
    list_month = CSQ.custom_request_c(self.db_kplan,
                    f"""SELECT * FROM {month}""",rez_dict=True)
    list_new = CQT.list_from_wtabl_c(self.ui.tbl_pl_add_poz, '', True,rez_dict=True)
    if len(list_month) != len(list_new):
        CQT.msgbox(f'Данные таблицы не совпадают с БД')
        return

    list_changes = []
    list_sql = []
    dict_compare_new = dict()
    dict_compare_old = dict()
    DICT_TABELS = DTCLS.FIELDS_DB_INFO.tables_db.dict_tabels_by_names
    for it in list_new:
        podr = it['Подразделение']
        if podr not in DICT_TABELS:
            continue
        for k,v in it.items():
            if F.is_date(k,"d_%Y_%m_%d"):
                dict_compare_new[(podr,k)] = v

    for it in list_month:
        podr = it['Подразделение']
        if podr not in DICT_TABELS:
            continue
        for k,v in it.items():
            if F.is_date(k,"d_%Y_%m_%d"):
                dict_compare_old[(podr,k)] = v

    for k,v in dict_compare_new.items():
        if k in dict_compare_old:
            old_val = dict_compare_old[k]
            if v != old_val:
                podr = k[0]
                podr_alias = DICT_TABELS[podr].alias
                date = k[1]
                date_gui = F.dateStrToStr(date,
                                          "d_%Y_%m_%d","%d.%m.%Y",'err')
                list_changes.append(
                    f'Для "{podr_alias}" от {date_gui} '
                    f'      было: {old_val}, стало: {v}')
                list_sql.append(
                    f"""UPDATE {month} SET {date} = {v} 
                            WHERE Подразделение = '{podr}'""")

    if list_changes == []:
        CQT.msgbox(f'Изменений не найдено')
        return
    list_changes.insert(0,'Изменения')
    rez = CQT.msgboxg_get_table(DTCLS.app_self,'Внести изменения?',list_changes,
                                'Да','Нет',styleSheet=CQT.MES_CSS,
                                selectRows=True,yesNoMode=True)
    if not rez:
        return
    return list_sql

def show_tabel(self):
    def gui_edit_tabel_on():
        self.ui.fr_pl_etap.setHidden(True)
        self.ui.fr_pl_add_poz.setHidden(False)
        self.ui.fr_gant_local.setHidden(True)
        CQT.clear_tbl(self.ui.tbl_select_etap_edit_poz)
        self.ui.tbl_pl_add_poz.clear()
        self.ui.tbl_pl_add_poz.setHidden(False)
        self.ui.btn_pull_poz_show.setHidden(True)
        self.ui.btn_pl_mode.setHidden(True)
        DTCLS.EDIT_TABEL_MODE = True
    @CQT.onerror
    def edit_tabel(self,*args):
        month =DTCLS.edit_tabel_current_month
        list_month = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM {month}""")
        set_editeble_columns = set()
        aliases = dict()
        for i in range(len(list_month[0])):
            if F.is_date(list_month[0][i], "d_%Y_%m_%d"):
                set_editeble_columns.add(list_month[0][i])
                date = F.strtodate(list_month[0][i], "d_%Y_%m_%d")
                aliases[list_month[0][i]] = F.datetostr(date,"%d.%m.%Y")
        list_dict_month = F.list_of_lists_to_list_of_dicts(list_month)
        list_dict_month = F.insert_key_to_dicts(list_dict_month,1,'Этап','')
        tabels = DTCLS.FIELDS_DB_INFO.tables_db
        for it in list_dict_month:
            podr = it['Подразделение']
            podr_o = tabels.get_table(podr)
            if podr_o:
                it['Этап'] = podr_o.alias
            else:
                it['Этап'] = ''

        CQT.fill_wtabl(list_dict_month, self.ui.tbl_pl_add_poz, set_editeble_col_nomera=set_editeble_columns,
                       colorful_edit=True,styleSheet=CQT.MES_EDIT_CSS,aliases_header=aliases)
        t = CQT.TableContext(self.ui.tbl_pl_add_poz)
        t.hide('Подразделение')
        t.hide('Пномер')
        for row in t.rows():
            if row.value('Примечание') == 'Выходные':
                row.set_editable(value=False)
                row_dayweek = t.find_row({'Примечание':'День недели'},first=True)
                for k in row.nf.keys():
                    if F.is_date(k, "d_%Y_%m_%d"):
                        val_vih = row.value(k)
                        if F.is_numeric(val_vih):
                            if val_vih == '0':
                                row.set_value(k,CEMOJ.ПерсоналРоли.workday.symbol)
                            else:
                                if row_dayweek:
                                    if row_dayweek.value(k) in ('6','7'):
                                        row.set_value(k, CEMOJ.ПерсоналРоли.weekend.symbol)
                                    else:
                                        row.set_value(k, CEMOJ.ПерсоналРоли.holiday.symbol)
                                else:
                                    row.set_value(k, CEMOJ.ПерсоналРоли.weekend.symbol)

            if row.value('Примечание') == 'День недели':
                row.set_editable(value=False)
                for k in row.nf.keys():
                    if F.is_date(k, "d_%Y_%m_%d"):
                        num_day = row.value(k)
                        if F.is_numeric(num_day):
                            row.set_value(k, F.get_day_name(num_day))
                            if num_day in ('6', '7'):
                                row.set_color_font(222,22,22,col_name=k)
                                row.set_font_format(bold=True,col_name=k)
            podr = row.value('Подразделение')
            etap_o = tabels.get_table(podr)
            if etap_o:
                clr = etap_o.color
                fix_col = clr.align_colors(level_percent=-20, saturation_percent=-10,copy=True)
                row.set_color_font(*fix_col.rgb, col_name='Этап')
                row.set_font_format(bold=True, col_name='Этап')

    if not DTCLS.EDIT_TABEL_MODE:
        def fnc_oform(tbl:QtWidgets.QTableWidget):
            t = CQT.TableContext(tbl)
            t.hide_if_not_dev(CFG)

        list_month = [{'cld':_, 'dt': F.strtodate(_.replace('m_cld_',''),"%Y_%m_%d")} for _
                      in CSQ.get_list_of_tables_c(self.db_kplan) if 'm_cld_' in _]
        template = [{'_cld':_['cld'], 'Год':_['dt'].year, 'Месяц': F.month_rus_from_date(_['dt'],rodit_padej=False)}
                    for _ in list_month]
        rez = CQT.msgboxg_get_table(self,'Выбор месяца',template,styleSheet=CQT.MES_CSS,selectRows=True,
                                    ExtendedSelection=False,
                                    selection_from_tbl=True,func_oform_tbl=fnc_oform)
        if not rez:
            return
        DTCLS.edit_tabel_current_month = rez['_cld']
        gui_edit_tabel_on()
        edit_tabel(self)

    else:
        gui_mode_off()

def gui_mode_off():
    self = DTCLS.app_self
    self.ui.fr_settings_pl.setHidden(True)
    self.ui.btn_pull_poz_show.setHidden(False)
    self.ui.btn_pl_mode.setHidden(False)
    CQT.clear_tbl(self.ui.tbl_pl_add_poz)
    self.ui.tbl_pl_add_poz.setHidden(True)
    self.ui.tbl_select_etap_edit_poz.setHidden(True)
    self.ui.fr_pull_poz.setHidden(True)
    self.ui.fr_pl_graf.setHidden(True)
    self.ui.fr_pl_tables.setHidden(False)
    self.ui.fr_pl_add_poz.setHidden(True)
    self.ui.fr_pl_etap.setHidden(True)
    self.ui.fr_gant_local.setHidden(False)
    DTCLS.SETTINGS_PL_MODE = False
    DTCLS.EDIT_TABEL_MODE = False
    DTCLS.edit_tabel_current_month = None
    DTCLS.ADD_POZ_MODE = False
    DTCLS.EDIT_POZ_MODE = False

def _____________________LOAD_DB____________________():pass
@CQT.onerror
def load_db(self: mywindow, pnom: bool | int = False, only_hat=False) -> None | dict:
    def check_tabels(self: mywindow):
        list_pnoms = CSQ.custom_request_c(self.db_kplan, f"""SELECT Пномер FROM plan""", one_column=True, hat_c=False)
        list_tbls = CSQ.get_list_of_tables_c(self.db_kplan)
        for tbl in list_tbls:
            if 'пл_' == tbl[:3]:
                list_nompl = CSQ.custom_request_c(self.db_kplan, f"""SELECT НомПл  FROM {tbl}""", one_column=True,
                                                  hat_c=False)
                differ_list = [[_] for _ in list_pnoms if _ not in list_nompl]
                if len(differ_list) > 0:
                    count_fields = len(CSQ.custom_request_c(self.db_kplan, f'select * from {tbl} Limit 1')[0])
                    for i in range(len(differ_list)):
                        for _ in range(count_fields - 1):
                            differ_list[i].append('')
                    CSQ.custom_request_c(self.db_kplan,
                                         f"""INSERT INTO  {tbl} VALUES({','.join(["?" for _ in range(count_fields)])})""",
                                         list_of_lists_c=differ_list)

    name_gr_field = 'plan.Группа'
    sort_by = ''
    if DTCLS.FIELDS_DB_INFO.use_groups:
        sort_by = f' ORDER BY plan.Пномер, {name_gr_field}'

    limit = ''
    if only_hat:
        limit = ' Limit 1'

    # check_tabels(self)

    poki = f'plan.poki == {self.place.poki}'
    addit_kpls_where = ''
    addit_kpls = []
    if DTCLS.USER_CONFIG.is_developer:
        addit_kpls = [5596,4337]
    if addit_kpls:
        addit_kpls_where = f' OR plan.Пномер in ({CSQ.prepare_list_to_tuple(addit_kpls)}) '
    postfix = f'WHERE {poki} and status_poz.Имя NOT IN  ("Завершена","Приостановлена","На удаление")'
    if self.ui.chk_kpl_zaversch.isChecked():
        postfix = f'WHERE {poki}'
    if pnom:
        postfix = f'WHERE {poki} and plan.Пномер == {int(pnom)}'
    fl_one_row = False
    if pnom:
        fl_one_row = True
    postfix = postfix + addit_kpls_where

    update_list_fields(fl_one_row)
    rez_list_tabels = [f'{_.select_db} AS "{_.name_mes}"' for _ in
                       DTCLS.FIELDS_DB_INFO.dict_fields.values() if _.is_loaded]
    list_join = sorted([ (v.join_order, f'{k} ON {k}.{v.table_primary_name} '
                                 f'= {v.source_table_for_join.name_mes}')
       for k,v in DTCLS.FIELDS_DB_INFO.tables_db.dict_tables.items() if v.source_table_for_join
                   ] ,key= lambda x:x[0])


    list_join = [_[1] for _ in list_join]
    str_join = ', \n'.join(list_join)
    str_field = ', \n'.join(rez_list_tabels)


    text_req = f"""SELECT
    {str_field}
    FROM plan
    LEFT JOIN 
    {str_join}
    {postfix} {limit} {sort_by};
    """

    list_db = CSQ.custom_request_c(self.db_kplan, text_req, attach_dbs=(self.bd_naryad), rez_dict=True)  # 18.07.25
    if not list_db:
        CQT.msgbox(f'Ошибка в динамическом запросе')
        return

    for item in list_db:
        if item['пл_оуп.ИмяПартии_ЗП'] != '':
            item['пл_оуп.Количество'] = ''
            item['пл_оуп.Номенклатура_ЕРП'] = f'*' + item['пл_оуп.ИмяПартии_ЗП']

    if DTCLS.FIELDS_DB_INFO.use_groups:
        shabl_row = {k: "" for k in list_db[0].keys()}
        list_groups = sorted(
            set([item[name_gr_field].strip() for item in list_db if item[name_gr_field].strip() != '']))
        for gr in list_groups:
            tmp_row = copy.deepcopy(shabl_row)
            tmp_row[name_gr_field] = gr
            tmp_row['plan.ТипГр'] = ''
            tmp_row['plan.Статус'] = 'Группа'
            tmp_row['plan.Пномер'] = '-1'
            list_db.append(tmp_row)

        list_db.sort(key=lambda x: (x[name_gr_field] in ('', None), x[name_gr_field] or '', int(x['plan.Пномер'])))
        for item in list_db:
            state_gr = item['plan.Статус']
            if state_gr == 'Группа':
                item['plan.ТипГр'] = FOLDER_CLOSED
            else:
                item_group = item[name_gr_field].strip()
                if item_group:
                    item['plan.ТипГр'] = DOC_EMOJI
    if fl_one_row and pnom:
        return list_db[0]

    DTCLS.list_dict_from_db = list_db
    DTCLS.dict_dict_from_db = F.deploy_dict_c(DTCLS.list_dict_from_db, 'plan.Пномер', True)


@CQT.onerror
def oforml_row_plan_tbl(row: CQT.TableRow, *args):
    if 'cust.client_order' in row.nf:
        ref_zk = row.value("cust.client_order")
        if ref_zk:
            ref, num = ref_zk.split('|')
            row.set_data("cust.client_order",ref)
            row.set_value('cust.client_order',num)

    if 'пл_оуп.№проекта' in row.nf:
        CQT.font_cell_size_format(row.tbl, row.i, row.nf['пл_оуп.№проекта'], underline=True)
    if 'napravlenie.Направление' in row.nf:
        r, g, b = 240, 240, 240
        try:
            napr_name = row.value('plan.Направление_деятельности')
            if napr_name in DTCLS.DICT_NAPR_DEYAT_NAME:
                napr_val = DTCLS.DICT_NAPR_DEYAT_NAME[napr_name]['Направление']
                if napr_val in DTCLS.DICT_NAPRAVLENIE:
                    clr_str = DTCLS.DICT_NAPRAVLENIE[napr_val]['Цвет']
                    if clr_str:
                        clr = CMS.Color(clr_str)
                        r,g,b = clr.rgb
        except:
            pass
        row.set_color_font(r, g, b,'napravlenie.Направление')

    if 'napravl_deyat.Псевдоним' in row.nf:
        r, g, b = 240, 240, 240
        try:
            napr_name = row.value('plan.Направление_деятельности')
            r, g, b = DTCLS.DICT_NAPR_DEYAT_NAME[napr_name]['Цвет'].split(';')
        except:
            pass
        CQT.set_color_wtab_c(row.tbl, row.i, row.nf['napravl_deyat.Псевдоним'], r, g, b)

    if 'пл_оуп.ПКК' in row.nf:
        pkk_val = row.value('пл_оуп.ПКК')
        if F.is_numeric(pkk_val) and pkk_val != '0':
            row.ctx.add_column_events('пл_оуп.ПКК', on_double_click=open_pkk)
            row.set_data('пл_оуп.ПКК', pkk_val)
            row.set_value('пл_оуп.ПКК', CEMOJ.ДокументыДанные.document.symbol)
        else:
            row.set_value('пл_оуп.ПКК', '')
    if 'plan.Статус_норм' in row.nf:
        state = row.value('plan.Статус_норм')
        if state in DTCLS.DICT_STATUS_NORM_NAME:
            r, g, b = DTCLS.DICT_STATUS_NORM_NAME[state]['color'].split(';')
            CQT.set_color_wtab_c(row.tbl, row.i, row.nf['plan.Статус_норм'], r, g, b)
    if 'plan.Статус' in row.nf:
        state = row.value('plan.Статус')
        if state in DTCLS.DICT_STATUS_POZ_NAME:
            r, g, b = DTCLS.DICT_STATUS_POZ_NAME[state]['color'].split(';')
            CQT.set_color_wtab_c(row.tbl, row.i, row.nf['plan.Статус'], r, g, b)
            part_emo = DTCLS.DICT_STATUS_POZ_NAME[state]['emoj']
            emoj = eval(f'CEMOJ.EmojiMain.{part_emo}')
            row.set_value('plan.Статус', f'{emoj} {state}')
    if 'plan.МК' in row.nf:
        mk = row.value('plan.МК')
        if mk == '0':
            CQT.set_color_wtab_c(row.tbl, row.i, row.nf['plan.МК'], 206, 128, 128)
    DICT_FIELDS = DTCLS.FIELDS_DB_INFO.dict_fields
    for clmn in row.nf.keys():
        if clmn in DICT_FIELDS:
            if DICT_FIELDS[clmn].is_bool:
                max_val = str(DICT_FIELDS[clmn].is_bool)
                val = row.value(clmn)
                row.set_font_format(bold=True,col_name=clmn )
                if val == max_val:
                    row.set_value(clmn, CEMOJ.СтатусыПроизводства.success)
                else:
                    row.set_value(clmn, '')




@CQT.progress_decorator
def load_table_db(self, hook_prog_bar=None):
    if 'shift' in CQT.get_key_modifiers(self):
        DTCLS.FIELDS_DB_INFO = CMS.Fields_db_info(DTCLS.CHECK_FIELD_RULES)

    def fill_client_order(data: list[dict]) -> list[dict] | None:
        list_kpls = [_['plan.Пномер'] for _ in data]
        list_refs_zc = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""
                SELECT DISTINCT пл_оуп.НомПл, знпр.client_order_Key,  знпр.client_order_num
                  FROM знпр
                       INNER JOIN
                       пл_оуп ON пл_оуп.Пномер_ЗП == знпр.s_num
                 WHERE client_order_Key != "" and пл_оуп.НомПл IN ({CSQ.prepare_list_to_tuple(list_kpls)});
        """, rez_dict=True)
        dict_refs_zp = F.deploy_dict_c(list_refs_zc,'НомПл')
        for it in data:
            if it["plan.Пномер"] not in dict_refs_zp:
                continue
            data_zk = dict_refs_zp[it["plan.Пномер"]]
            if not data_zk['client_order_num']:
                data_zk['client_order_num'] = load_client_order_num(data_zk['client_order_Key'])
            it['cust.client_order'] = data_zk['client_order_Key'] + '|' + data_zk['client_order_num']
        return data

    def fill_Дата_прих_ордера_гп(data: list[dict]) -> list[dict] | None:
        list_kpls = [_['plan.Пномер'] for _ in data]
        list_refs_zp = CSQ.custom_request_c(CFG.Config.project.db_kplan, f"""
                SELECT DISTINCT пл_оуп.НомПл, знпр.Ref_Key_py
                  FROM знпр
                       INNER JOIN
                       пл_оуп ON пл_оуп.Пномер_ЗП == знпр.s_num
                 WHERE Ref_Key_py != "" and пл_оуп.НомПл IN ({CSQ.prepare_list_to_tuple(list_kpls)});
        """, rez_dict=True,lazy_method_hours= 0.1)
        dict_refs_zp = F.deploy_dict_c(list_refs_zp, 'НомПл')
        unic_set_refs = set([_['Ref_Key_py'] for _ in list_refs_zp])
        dict_ref_alias = {k: f'lnk{i}' for i, k in enumerate(unic_set_refs)}
        list_lnks = ', '.join(['&' + _ for _ in dict_ref_alias.values()])

        text = f"""
            ВЫБРАТЬ
            ЭтапПроизводства2_2.Распоряжение.Ссылка КАК ЗП,
            ПриходныйОрдерНаТоварыТовары.Номенклатура.Представление КАК Номенклатура,
            МАКСИМУМ(ПриходныйОрдерНаТоварыТовары.Ссылка.Дата) КАК Дата,
            СУММА(ПриходныйОрдерНаТоварыТовары.КоличествоУпаковок) КАК КоличествоУпаковок1
        ПОМЕСТИТЬ ВТ
        ИЗ
            Документ.ЭтапПроизводства2_2 КАК ЭтапПроизводства2_2
                ВНУТРЕННЕЕ СОЕДИНЕНИЕ Документ.ДвижениеПродукцииИМатериалов КАК ДвижениеПродукцииИМатериалов
                    ВНУТРЕННЕЕ СОЕДИНЕНИЕ Документ.ПриходныйОрдерНаТовары.Товары КАК ПриходныйОрдерНаТоварыТовары
                    ПО (ПриходныйОрдерНаТоварыТовары.Ссылка.Распоряжение = ДвижениеПродукцииИМатериалов.Ссылка)
                ПО (ДвижениеПродукцииИМатериалов.Распоряжение = ЭтапПроизводства2_2.Ссылка)
        ГДЕ
            ПриходныйОрдерНаТоварыТовары.Ссылка.ПометкаУдаления = ЛОЖЬ
            И ПриходныйОрдерНаТоварыТовары.Ссылка.Проведен = ИСТИНА
            И ДвижениеПродукцииИМатериалов.ПометкаУдаления = ЛОЖЬ
            И ДвижениеПродукцииИМатериалов.Проведен = ИСТИНА
            И ЭтапПроизводства2_2.Распоряжение.Ссылка В ({list_lnks})

        СГРУППИРОВАТЬ ПО
            ЭтапПроизводства2_2.Распоряжение.Ссылка,
            ПриходныйОрдерНаТоварыТовары.Номенклатура,
            ПриходныйОрдерНаТоварыТовары.Номенклатура.Представление
        ;

        ////////////////////////////////////////////////////////////////////////////////
        ВЫБРАТЬ
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВТ.ЗП)) КАК Ref_Key,
            ВТ.Номенклатура КАК Номенклатура,
            ВТ.Дата КАК Дата,
            ВТ.КоличествоУпаковок1 КАК Количество
        ИЗ
            ВТ КАК ВТ
        """
        refs = APIERP.Refs_wet(text)
        for k, link in dict_ref_alias.items():
            ref_obj = APIERP.Ref_wet(link, 'Документы.ЗаказНаПроизводство2_2', k)
            refs.add_ref(ref_obj)
        key, res = APIERP.get_wet_request(text=text, refs=refs, lazy_method_huours=0.25)
        if key != 200:
            CQT.msgbox(f'Ошибка получения данных ЗаказНаПроизводство2_2 из ЕРП ')
            return
        erp_list_zp = res['data']
        erp_dict_zp = {(_['Ref_Key'], _['Номенклатура']): _ for _ in erp_list_zp}
        for item in data:
            nomen = item['пл_оуп.Номенклатура_ЕРП']
            kpl = item['plan.Пномер']
            count_poz = item['пл_оуп.Количество']
            if kpl in dict_refs_zp:
                ref = dict_refs_zp[kpl]
                k_item = (ref, nomen)
                if k_item in erp_dict_zp:
                    data_erp_poz = erp_dict_zp[k_item]
                    count_erp = data_erp_poz['Количество']
                    date_erp = F.dateStrToStr(data_erp_poz['Дата'], "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", '')
                    if count_erp == count_poz:
                        item['cust.Дата_прих_ордера_гп'] = date_erp
                    else:
                        item['cust.Дата_прих_ордера_гп'] = f'{date_erp}-{count_erp} шт.'

        return data

    def oforml_groups(self):
        tbl: QtWidgets.QTableWidget = self.ui.tbl_kal_pl
        t = CQT.TableContext(tbl)
        with CQT.table_updating(t):
            if not DTCLS.FIELDS_DB_INFO.use_groups:
                t.hide('plan.ТипГр')

            else:
                t.hide('plan.ТипГр', False)
                t.set_width('plan.ТипГр', 100)

            if DTCLS.FIELDS_DB_INFO.use_groups:
                for row in t.rows():
                    state = row.value('plan.Статус')
                    if state == 'Группа':
                        row.set_font_format(bold=True, col_name='plan.Группа')
                        row.set_font_format(bold=True, col_name='plan.Статус')
                        row.set_font_format(bold=True, col_name='plan.ТипГр', size=14)

    def oforml_table(self):

        def fncContextMenu_predv_res(t: CQT.TableContext, i: int, j: int, builder: CQT.ContextMenuBuilder):
            builder.add_menu(f'{CEMOJ.EmojiMain.ОборудованиеИнструменты.link} Выбрать РС',
                             partial(fcn_pred_spec_erp, i, j))
            builder.add_menu(f'{CEMOJ.EmojiMain.СтатусыПроизводства.error} Очистить РС',
                             partial(fcn_pred_spec_erp, i, j, True))
            pass

        @CQT.onerror
        def fnc_dblclick_link(t: CQT.TableContext, i, name_clmn: str, *args):
            def open_link(ref, doc_name) -> bool:
                succ, link = APIERP.open_in_1c(ref, doc_name)
                if not succ:
                    CQT.msgbox(f'Ошибка открытия ссылки, скопирована в буфер обмена')
                return succ

            row = t.get_row(i)
            if row.no_selection:
                return

            val = row.value(name_clmn).strip()
            if not val:
                return

            if name_clmn == 'cust.client_order':
                ref_zk = row.value(name_clmn, get_cust_content=True)
                open_link(ref_zk, 'Документ.ЗаказКлиента')
                return

            text = None
            doc_name = None

            poz = CMS.Pozition(int(row.value('plan.Пномер')), DTCLS.db_kplan, DTCLS.bd_naryad, DTCLS.db_resxml,
                               DTCLS.db_users, DTCLS.app_self)

            poz.load_kpl_table('пл_оуп')
            checker = CMS.Checker_val_fields(poz,DTCLS.DICT_ITERS_FOR_CHECK_FIELDS)
            field_o = DTCLS.FIELDS_DB_INFO.dict_fields[name_clmn]
            if not checker.check_value_field(val, field_o):
                return

            if name_clmn == 'знпр.№ERP':
                ref_zp = poz.dict_tables['пл_оуп']['Ref_Key_py']
                open_link(ref_zp, 'Документ.ЗаказНаПроизводство2_2')
                return

            if name_clmn == 'пл_топ.Предв_спецификация_ЕРП':
                text = f"""
                    ВЫБРАТЬ
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.Ссылка)) КАК Ref
                    ИЗ
                        Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                    ГДЕ
                        РесурсныеСпецификации.Код = "{val}"
                        ИЛИ РесурсныеСпецификации.Наименование = "{val}"
                    """
                doc_name = 'Справочник.РесурсныеСпецификации'

            if name_clmn == 'пл_топ.Спецификация_ЕРП':
                text = f"""
                    ВЫБРАТЬ
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.Ссылка)) КАК Ref
                    ИЗ
                        Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                    ГДЕ
                         РесурсныеСпецификации.Наименование = "{val}"
                    """
                doc_name = 'Справочник.РесурсныеСпецификации'

            if name_clmn == 'пл_топ.Спецификация_код_ЕРП':
                text = f"""
                    ВЫБРАТЬ
                        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(РесурсныеСпецификации.Ссылка)) КАК Ref
                    ИЗ
                        Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                    ГДЕ
                         РесурсныеСпецификации.Код = "{val}"
                    """
                doc_name = 'Справочник.РесурсныеСпецификации'

            if name_clmn == 'пл_оуп.Номенклатура_ЕРП':
                text = f"""
                        ВЫБРАТЬ
                            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.Ссылка)) КАК Ref
                        ИЗ
                            Справочник.Номенклатура КАК Номенклатура
                        ГДЕ
                            Номенклатура.Наименование = "{val}"
                        """
                doc_name = 'Справочник.Номенклатура'
            if text:
                succ, rez = APIERP.get_wet_request(text)
                if succ != 200:
                    CQT.msgbox(f'{CEMOJ.EmojiMain.Эмоции.confused} Ошибка связи с ЕРП, Код: {succ}', app_self=self)
                    return
                if not rez['data']:
                    CQT.msgbox(f'{CEMOJ.EmojiMain.Эмоции.confused} Не найдено в ЕРП', app_self=self)
                    return
                ref = rez['data'][0]['Ref']
                open_link(ref, doc_name)
                return
            else:
                if CQT.is_link_like(val):
                    CQT.lbl_linkActivated(val)

        @CQT.onerror
        def fncContextMenuZnprNpr(t: CQT.TableContext, row: int, col: int,
                                  menu_builder: CQT.ContextMenuBuilder):

            def fnc_edit_num_pr(self: mywindow, s_num_poz: int, change: bool = True):
                poz = CMS.Pozition(s_num_poz)
                poz.load_kpl_table('пл_оуп')
                start_text = None
                if change:
                    start_text = poz.dict_tables['пл_оуп']['№проекта']
                succ, text = CQT.get_dialog_choose_text(self, f'Новый номер проекта:', placeholderText='...',
                                                        start_text=start_text)
                if not succ:
                    return
                new_np = text["text"].strip()
                if len(new_np) < 4:
                    CQT.msgbox(f'Не корректное значение')
                    return

                if poz.dict_tables['пл_оуп']['№проекта'] == new_np:
                    CQT.msgbox(f'Номер проекта не изменился')
                    return
                poz.dict_tables['пл_оуп']['№проекта'] = new_np
                if not poz.update_znpr():
                    CQT.msgbox(f'Ошибка изменения ЗНПР')
                    return
                update_plan_main_tbl(self)

            row_o = t.get_row(row)

            s_num_poz = row_o.value('plan.Пномер')

            if t.tbl.item(row, col).text() == '' or t.tbl.item(row, t.nf['знпр.№ERP']).text() == '':
                return
            field_o = DTCLS.FIELDS_DB_INFO.dict_fields['знпр.№проекта']
            if field_o.accessed:
                emoji: CEMOJ.EmojiItem = CEMOJ.EmojiMain.ДокументыДанные.pencil2

                fnc = partial(fnc_edit_num_pr, self, int(s_num_poz), change=True)
                menu_builder.add_menu(f'{emoji.symbol} {"Изменить"}',
                                      fnc)

                emoji: CEMOJ.EmojiItem = CEMOJ.EmojiMain.ДокументыДанные.document
                fnc = partial(fnc_edit_num_pr, self, int(s_num_poz), change=False)
                menu_builder.add_menu(f'{emoji.symbol} {"Ввести новый"}',
                                      fnc)

        tbl = self.ui.tbl_kal_pl
        it = 0
        t = CQT.TableContext(self.ui.tbl_kal_pl)


        #------------ROWS-----------------------------
        for row in t.rows():
            oforml_row_plan_tbl(row)
        # ------------ROWS-----------------------------

        for name, field_o in dict_fields_o.items():
            if not field_o.is_loaded:
                continue
            if name in t.nf:
                if field_o.is_hidden:
                    t.hide(name)
                if field_o.tbl_idx is not None:
                    CQT.set_color_text_header_wtab_horisontal_c(self.ui.tbl_kal_pl, field_o.tbl_idx,
                                                                *field_o.table_color.rgb,
                                                                blod=True)
                    if name == 'plan.ТипГр':
                        t.add_column_events(name, on_context_menu=fncContextMenuGr)

                    if name == 'знпр.№проекта' and field_o.accessed:

                        t.add_column_events(name,
                                            on_context_menu=fncContextMenuZnprNpr)

                    if field_o.is_linklike:
                        on_context_menu = None
                        if name == 'пл_топ.Предв_спецификация_ЕРП' and field_o.accessed and field_o.hand_editable:
                            on_context_menu = fncContextMenu_predv_res


                        t.add_column_events(field_o.name_mes, on_double_click=fnc_dblclick_link,
                                            on_context_menu=on_context_menu)
                        t.set_color_font(*CMS.Colors.link_blue.rgb, name)

            hook_prog_bar.set(40 + round(it / t.tbl.rowCount() * 30))
            it += 1


        if self.ui.chk_paint_dates.isChecked():
            fl_paint_npr = False
            if 'пл_оуп.№проекта' in t.nf:
                fl_paint_npr = True

            dict_nkpl_for_paint = dict()
            dict_pairs_fields = {
                name + '.' + _['Имя_начала_этапа']: name + '.' + _['Имя_начала_этапа'].replace('Пдата',
                                                                                               'Фдата').replace(
                    'ПДата', 'ФДата') for name, _ in
                self.Data_plan.DICT_PODR.items() if _['Имя_начала_этапа']}

            for i, item in enumerate(DTCLS.list_dict_from_db):
                for field, val in item.items():
                    if field in dict_pairs_fields:
                        if F.is_date(val, "%Y-%m-%d") and F.strtodate(val, "%Y-%m-%d") <= F.now(''):
                            if i not in dict_nkpl_for_paint:
                                dict_nkpl_for_paint[i] = set()
                            dict_nkpl_for_paint[i].add(field)
            clr_bad = CMS.Color_tbl(0)
            for i_row, set_fields in dict_nkpl_for_paint.items():
                if fl_paint_npr:
                    CQT.set_color_wtab_c(tbl, i_row, t.nf['пл_оуп.№проекта'], clr_bad.r, clr_bad.g, clr_bad.b)
                CQT.set_color_wtab_c(tbl, i_row, t.nf['plan.Пномер'], clr_bad.r, clr_bad.g, clr_bad.b)
                for field in set_fields:
                    CQT.set_color_wtab_c(tbl, i_row, t.nf[field], clr_bad.r, clr_bad.g, clr_bad.b)

    def fcn_pred_spec_erp(i, j, clear=False, *args):
        def fnc_oform_tbl_res(tbl):
            pass

        def fnc_select_tbl_res(tbl):
            pass

        tbl = DTCLS.app_self.ui.tbl_kal_pl
        t = CQT.TableContext(tbl)
        res_code = ''

        if not clear:
            nom_pr = tbl.item(i, t.nf['пл_оуп.№проекта']).text()
            wet_req_text = f"""
                     ВЫБРАТЬ
                         РесурсныеСпецификации.Наименование КАК Наименование,
                         РесурсныеСпецификации.Код КАК Код,
                         РесурсныеСпецификации.Статус КАК Статус,
                         РесурсныеСпецификации.Описание КАК Описание
                     ИЗ
                         Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                     ГДЕ
                         РесурсныеСпецификации.ПометкаУдаления = ЛОЖЬ
                         И РесурсныеСпецификации.ЭтоГруппа = ЛОЖЬ
                         И РесурсныеСпецификации.Наименование ПОДОБНО "%ТКПА_%"
                         И РесурсныеСпецификации.Наименование ПОДОБНО "%{nom_pr}%"
                     """
            key, data_rez = APIERP.get_wet_request(wet_req_text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных из ERP. Код: {key}')
                return
            if not data_rez['data']:
                CQT.msgbox(f'Не найдены подходящие РС для проекта "{nom_pr}"')
                return
            if data_rez['data']:
                data_rez['data'].insert(0, {k: '' for k in data_rez['data'][0].keys()})
            result = CQT.msgboxg_get_table(DTCLS.app_self, f'Выбор ресурсной', data_rez['data'], 'Выбор',
                                           func_oform_tbl=fnc_oform_tbl_res,
                                           func_btn0=fnc_select_tbl_res,
                                           ExtendedSelection=False, selectRows=True, styleSheet=CQT.ERP_CSS,
                                           sortingEnabled=True)
            if result:
                res_code = result['Код']
            else:
                return

        tbl.blockSignals(True)
        tbl.item(i, j).setText(res_code)
        tbl_kal_pl_cellChanged(DTCLS.app_self)
        tbl.blockSignals(False)

    debug = False
    hook_prog_bar.open()
    if CFG.Config.user_config.is_developer and debug:
        self.setHidden(False)
    hook_prog_bar.set(0)
    hook_prog_bar.text("Загрузка данных")
    DTCLS.FIELDS_DB_INFO.use_groups = self.ui.chk_kpl_groups.isChecked()

    load_db(self)

    if DTCLS.list_dict_from_db is None:
        CQT.msgbox(f'Ошибка получения данных')
        return
    list_dict_from_db = DTCLS.list_dict_from_db
    if list_dict_from_db == False:
        CQT.msgbox(f'Ошибка загрузки таблиц')
        return
    fields_from_db = list(list_dict_from_db[0].keys())


    if 'cust.Дата_прих_ордера_гп' in fields_from_db:
        rez = fill_Дата_прих_ордера_гп(list_dict_from_db)
        if rez is not None:
            list_dict_from_db = rez
    if 'cust.client_order' in fields_from_db:
        rez = fill_client_order(list_dict_from_db)
        if rez is not None:
            list_dict_from_db = rez


    dict_fields_o = DTCLS.FIELDS_DB_INFO.dict_fields
    editeble_col_nomera = []
    hook_prog_bar.set(20)
    hook_prog_bar.text("Применение прав")
    for i, name_field in enumerate(fields_from_db):
        field_o = dict_fields_o[name_field]
        if field_o.hand_editable:
            if field_o.accessed or DTCLS.USER_CONFIG.is_developer:
                editeble_col_nomera.append(name_field)
        hook_prog_bar.set(20 + round(i / len(list_dict_from_db[0]) * 10))
    hook_prog_bar.text("Заполнение данными")

    @CQT.onerror
    def fncContextMenuGr( t: CQT.TableContext, row: int, col: int,
                         menu_builder: CQT.ContextMenuBuilder):

        cfg = CFG.Config.project

        row_o = t.get_row(row)

        s_num_poz = row_o.value('plan.Пномер')
        col_name = t.name_by_idx(col)
        def fnc_set_state(self: mywindow, s_num_state: int, list_s_num: tuple[int]):
            r, g, b = self.Data_plan.DICT_STATUS_POZ[s_num_state]['color'].split(';')
            state_name = self.Data_plan.DICT_STATUS_POZ[s_num_state]['Имя']
            CSQ.custom_request_c(cfg.db_kplan,
                                 f"""UPDATE plan SET (Статус) = ({s_num_state}) 
                                 WHERE Пномер in ({CSQ.prepare_list_to_tuple(list_s_num)})""")
            with CQT.table_updating(t.tbl):
                for row_tbl in range(t.tbl.rowCount()):
                    if int(t.tbl.item(row_tbl, t.nf['plan.Пномер']).text()) in list_s_num:
                        t.tbl.item(row_tbl, t.nf['plan.Статус']).setText(state_name)
                        CQT.set_color_wtab_c(t.tbl, row_tbl, t.nf['plan.Статус'], r, g, b)

        def chek_state_poz(self: mywindow, num_state: int, s_num_poz: int, poz: CMS.Pozition = None, msg=True) -> bool:

            val_str = self.Data_plan.DICT_STATUS_POZ[int(num_state)]['Имя']
            if val_str in ('К производству', 'Завершена', 'Изготовление'):
                if poz is None:
                    poz = CMS.Pozition(s_num_poz, self.db_kplan, self.bd_naryad, self.db_resxml,
                                       self.db_users, '')
                if 'пл_оуп' not in poz.dict_tables:
                    poz.load_kpl_table('пл_оуп')
                if poz.dict_tables['пл_оуп']['№ERP'] in ('', 0, '-'):
                    if msg:
                        CQT.msgbox(f'Статус без №ERP не может быть {val_str}')
                    return False
            return True

        field_o = DTCLS.FIELDS_DB_INFO.dict_fields['plan.Статус']
        if field_o.accessed:
            gr = row_o.value('plan.Группа')
            if t.tbl.item(row, col).text() == CMS.DOC_EMOJI:
                s_num_pozs = [s_num_poz]

            else:
                s_num_pozs = CSQ.custom_request_c(cfg.db_kplan,
                                                  f"""SELECT Пномер FROM plan WHERE Группа == "{gr}";""",
                                                  hat_c=False, one_column=True
                                                  )
            pozitions = CMS.Pozitions(s_num_pozs, cfg.db_kplan, cfg.db_naryad,
                                      cfg.db_resxml, cfg.db_users, self
                                      )
            pozitions.load_kpl_table('пл_оуп')
            list_states = [data_state['Пномер'] for data_state in self.Data_plan.DICT_STATUS_POZ_NAME.values()]

            for poz in pozitions.dict_pozs.values():
                for state, data_state in self.Data_plan.DICT_STATUS_POZ_NAME.items():
                    s_num_state = data_state['Пномер']
                    if not chek_state_poz(self, s_num_state, poz.Пномер, poz, msg=False):
                        if s_num_state in list_states:
                            list_states.remove(s_num_state)
            if list_states:
                menu_builder.add_submenu(f"Сменить статус    ")
            for state_num in list_states:
                data_state = self.Data_plan.DICT_STATUS_POZ[state_num]

                emoji: CEMOJ.EmojiItem = eval(f'CEMOJ.EmojiMain.{data_state["emoj"]}')
                fnc = partial(fnc_set_state, self, state_num, tuple(pozitions.dict_pozs.keys()))
                menu_builder.add_menu(f'{emoji.symbol} {data_state["Имя"]}',
                                      fnc)

    @CQT.onerror
    def fncContextMenuHeader(t: CQT.TableContext, i: int, j: int, menu_builder: CQT.ContextMenuBuilder) -> None:
        menu_builder.add_menu(f'{CEMOJ.ОборудованиеИнструменты.machine.symbol} Настройка полей',
                              btn_config_fields)

    # self.show()
    CQT.fill_wtabl(list_dict_from_db, self.ui.tbl_kal_pl, auto_type=False, set_editeble_col_nomera=editeble_col_nomera,
                   height_row=20, sortingEnabled=not self.ui.chk_kpl_groups.isChecked(), load_links=False,
                    parent_self=self, aliases_header=DTCLS.FIELDS_DB_INFO.get_aliases(),
                   styleSheet=CQT.MES_EDIT_CSS)
    t = CQT.TableContext(self.ui.tbl_kal_pl)

    DTCLS.FIELDS_DB_INFO.fill_tbl_idx(t)


    with CQT.table_updating(self.ui.tbl_kal_pl):
        hook_prog_bar.text("Свертка полей")


        if self.ui.tbl_filtr_kal_pl.columnCount() < 1:
            btn_clear_filtr(self, False)

        hook_prog_bar.set(40)
        hook_prog_bar.text("Применение цветовой темы")

        oforml_table(self)

        CMS.load_column_widths(self, self.ui.tbl_kal_pl)
        hook_prog_bar.set(90)
        hook_prog_bar.text("Заполнение фильтров")
        oforml_groups(self)

    t.add_header_events(fncContextMenuHeader)

    def fncDrdrop(t: CQT.TableContext, new_nf):
        edited_field = {k: new_nf[k] for k, v in t.nf.items() if new_nf[k] != v}
        if not edited_field:
            return

        dict_fields = DTCLS.FIELDS_DB_INFO.dict_fields
        for name, idx in edited_field.items():
            f = dict_fields[name]
            f.usr_idx = idx

        DTCLS.FIELDS_DB_INFO.fix_indx()
        DTCLS.FIELDS_DB_INFO.save_user_data()
        load_table_db(DTCLS.app_self)

    t.add_header_drdrop(fncDrdrop)
    dict_cmb_filter = {k.name_mes:None for k in DTCLS.FIELDS_DB_INFO.list_fields if k.is_bool}
    dict_chck_filter = {k.name_mes:None for k in DTCLS.FIELDS_DB_INFO.list_fields if k.is_state}

    CQT.fill_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl,
                     USER_CONFIG_reset_tbl_filtrs_forsed_off=self.ui.chk_kpl_groups.isChecked(),
                     check_box_dict = dict_chck_filter, # таблица для нескольких значений
                     combo_dict=dict_cmb_filter,show_header=False)
    CMS.update_width_filtr(self.ui.tbl_kal_pl, self.ui.tbl_filtr_kal_pl)
    CMS.apply_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl, False)
    KPLUF.apply_select_filtr(self)

    close_all_groups(self)
    hook_prog_bar.close()
    self.ui.tbl_kal_pl.setVisible(True)

    print(f'reload ok')



def _____________________gant_manage_________________________():pass

class Gant_handler():
    def __init__(self,local_mode:bool=True, by_hover:CQT.QtGui.QMouseEvent|None=None,forced_row:CQT.TableRow|None=None):# :CMS.Gant

        self.local_mode:bool=local_mode
        if self.local_mode:
            self.gant: CMS.Gant = DTCLS.current_gant
        else:
            self.gant: CMS.Gant = DTCLS.current_vol_gant

        self._mouse_moving_block_gant_mode: GPL.Mouse_moving_block_gant_modes | None = None
        self._by_hover:CQT.QtGui.QMouseEvent|None = by_hover
        if self.local_mode:
            self.t:CQT.TableContext = CQT.TableContext(DTCLS.app_self.ui.tbl_preview)
        else:
            self.t: CQT.TableContext = CQT.TableContext(DTCLS.app_self.ui.tbl_pl_gaf)
        self.current_row: CQT.TableRow | None = None
        self.cld_day: CMS.Month_cld_day | None = None
        self.poz_gant: CMS.Poz_gant | None = None
        self.type_day: CMS.Type_day_gant | None = None
        self.tbl_db: CMS.Table_db_info | None = None
        self.min_date_block:datetime.datetime|None = None
        self.max_date_block:datetime.datetime|None = None
        self.left_idx_net:int|None = None
        self.right_idx_net:int|None = None
        self.link_blocks_moving:bool|None
        if self.gant is None:
            return
        if self._by_hover:
            i,j = self._get_hover_coords()
            if i is None:
                return
            curr_clmn = self.t.name_by_idx(j)
            self.current_row = self.t.get_row(i)
        else:

            curr_clmn = self.t.current_column_name()
            if forced_row:
                self.current_row: CQT.TableRow = forced_row
            else:
                self.current_row: CQT.TableRow = self.t.current_row()
                if self.current_row.no_selection:
                    return

        if isinstance(curr_clmn, CMS.Month_cld_day):
            self.cld_day = curr_clmn
        try:
            id_poz = int(self.current_row.value('_id_poz'))
        except:
            return
        if id_poz == -1:
            return
        if id_poz not in self.gant.dict_pozitions:
            return
        self.poz_gant:CMS.Poz_gant = self.gant.dict_pozitions[id_poz]
        self.type_day = CMS.Types_day_gant.find(self.current_row.value('_type_day'))
        self.tbl_db = DTCLS.FIELDS_DB_INFO.tables_db.get_table(
            self.current_row.value("_tbl_name"))
        self.min_date_block, self.max_date_block = self.poz_gant.dict_agregate_etaps[
                        self.tbl_db.name][self.type_day]
        self.left_idx_net = 0
        self.right_idx_net = len(self.t.nf)-1
        for k,v in self.t.nf.items():
            if not isinstance(k,str):
                self.left_idx_net = v
                break
        self.link_blocks_moving = DTCLS.app_self.ui.chk_link_gant_blocks.isChecked()

    def __repr__(self):
        mode = "hover" if self._by_hover else "click"
        poz = self.poz_gant.poz_id if self.poz_gant else None
        day = self.cld_day.dt_datetime.strftime("%Y-%m-%d") if self.cld_day else None
        type_name = self.type_day.name if self.type_day else None
        tbl = self.tbl_db.name if self.tbl_db else None
        return f"Gant_handler(mode={mode}, poz={poz}, day={day}, type={type_name}, tbl={tbl})"
    def _get_hover_coords(self):
        pos = self._by_hover.pos()

        row_h = self.t.tbl.rowAt(pos.y())
        column_h = self.t.tbl.columnAt(pos.x())

        # если курсор вне ячеек
        if row_h < 0 or column_h < 0:
            return None, None
        return row_h,column_h

    @property
    def list_selected_rows(self)->list[CQT.TableRow]:
        selected_ranges = self.t.tbl.selectedRanges()  # список QTableWidgetSelectionRange
        unique_rows = set()
        [[unique_rows.add(r) for r in range(_.topRow(), _.bottomRow() + 1)] for _ in selected_ranges ]
        return sorted([self.t.get_row(_) for _ in unique_rows], key=lambda x:x.i)
    @property
    def count_selected_rows(self)->int:
        return len(self.list_selected_rows)
    @property
    def get_power_hour_current_etap(self)->float|int:
        if self.tbl_db.name not in self.cld_day.dict_podrs:
            return 0
        return self.cld_day.dict_podrs[self.tbl_db.name]

    @property
    def is_block_replaced_dates(self)->bool:
        for dt_day , day_gant in self.poz_gant.dict_days.items():
            if self.min_date_block <=  dt_day <= self.max_date_block:
                if day_gant.is_replaced(self.tbl_db.name,self.type_day):
                    return True
        return False

    @property
    def block_count_hours(self)->float|int:
        return self.poz_gant.get_etap_gant_summ_minutes(
            self.tbl_db, self.type_day
        ) / 60

    @property
    def selected_cell(self)->CMS.Cell_etap_gant|None:
        cell = self.gant.get_value(self.poz_gant,
                            self.cld_day,
                            self.tbl_db,
                            self.type_day,
                            as_cell_o=True)
        return cell
    @property
    def block_selected(self)->bool:
        return  self.min_date_block <= self.cld_day.dt_datetime <= self.max_date_block
    @property
    def left_block_idx(self)->int:
        for k,i in self.t.nf.items():
            if isinstance(k,CMS.Month_cld_day) and k.dt_datetime == self.min_date_block:
                return i

    @property
    def right_block_idx(self) -> int:
        for k, i in self.t.nf.items():
            if isinstance(k,CMS.Month_cld_day) and k.dt_datetime == self.max_date_block:
                return i
    def set_new_date(self,start:bool,dt_new_date:datetime.datetime)->bool:
        new_date = F.datetostr(dt_new_date,"%Y-%m-%d")
        if start:
            name_field = self.tbl_db.start_plan_name_field
        else:
            name_field = self.tbl_db.end_plan_name_field
        table = self.tbl_db.name
        name_field_snom = self.tbl_db.table_primary_name
        return CSQ.custom_request_c(DTCLS.db_kplan,
                             f"""UPDATE {table} SET {name_field} = "{new_date}" 
                    WHERE {name_field_snom} == {self.poz_gant.poz_id};""")

    def select_block_range(self):
        self.current_row.tbl.setRangeSelected(
            CQT.QtWidgets.QTableWidgetSelectionRange(self.current_row.i, self.left_block_idx,
                                                     self.current_row.i, self.right_block_idx),
            True
        )

    def get_list_cld_days_selected(self)->list[CMS.Month_cld_day]:
        selection_cells = CQT.get_selected_cells_coordinates(self.t.tbl)
        return [d for d in  [self.t.name_by_idx(_[1]) for _ in selection_cells] if isinstance(d,CMS.Month_cld_day)]

    def load_poz(self, load_loacal_graf=False,row_dates_etaps=None,load_day_plan=False)->CMS.Pozition:
        return CMS.Pozition(self.poz_gant.poz_id, parent_self= DTCLS.app_self ,
                            load_loacal_graf=load_loacal_graf,
                            row_dates_etaps=row_dates_etaps,load_day_plan=load_day_plan)

@CQT.onerror
def select_block():
    g_handler = Gant_handler()
    if g_handler is None or g_handler.cld_day is None:
        return
    if g_handler.block_selected:
        g_handler.select_block_range()


@CQT.onerror
def clck_tbl_preview(self, tbl):
    self.current_kpl_table = 'tbl_preview'
    CQT.summ_selct_tbl(self, tbl)
    if DTCLS.MOUSE_MOVING_BLOCK_GANT:
        GPL.mouse_moving_stop()
    else:
        select_block()

@CQT.onerror
def show_fact_etap_by_current_day(self):
    self.current_kpl_table = 'tbl_preview'
    g_handler:Gant_handler=Gant_handler()

    if g_handler.cld_day is None:
        return
    if g_handler.type_day is not CMS.Types_day_gant.fact:
        return
    row_name = f'{g_handler.type_day.full_text}_{g_handler.tbl_db.name}'.lower()

    result = CMS.recalc_fact_by_date(
        self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN,
        self.DICT_VID_RABOT,
        self.Data_plan.DICT_NAPR_DEYAT,
        self.Data_plan.DICT_VID_PO_NAPR,
        self.Data_plan.DICT_NAPRAVLENIE,
        self.Data_plan.DICT_NAPR_DEYAT_NAME,
        self.Data_plan.DICT_DOLGN_ETAP,
        self.Data_plan.DICT_EMPLOEE_FULL_WITH_DEL,
        self.DICT_OP_NAME,
        g_handler.poz_gant.poz_id,
        date_calc=g_handler.cld_day.dt_datetime)
    if result is None:
        return
    poz, dict_fact_jur, dict_summ_time, dict_jur_data = result

    if row_name in dict_jur_data:
        CQT.msgboxg_get_table_ok_inf(self, 'Расшифровка дня', dict_jur_data[row_name], load_summ=True)



@CQT.onerror
def plan_day_edit_recalc(self: mywindow, *args):

    g_handler = Gant_handler()
    if g_handler is None:
        return
    if g_handler.cld_day is None:
        CQT.msgbox(f'Не выбран этап в ганте')
        return
    if g_handler.count_selected_rows > 1:
        CQT.msgbox(f'Нужно выбрать одну строку')
        return
    poz = g_handler.load_poz(False, None, True)
    dict_fact_jur = poz.recalc_get_day_plan_as_fact(g_handler.tbl_db.name)
    if dict_fact_jur == None or not dict_fact_jur:
        CQT.msgbox(f'Работ пока нет')
        return
    update_local_graf( True, self.pnom_kplan_select, True)
    CQT.msgbox(f'Успешно')

@CQT.onerror
def save_val_chk_link_gant_blocks(*args):
    chk_link_blocks: CQT.QtWidgets.QCheckBox = DTCLS.app_self.ui.chk_link_gant_blocks
    CMS.save_tmp_stukt(chk_link_blocks.isChecked() ,'_chk_link_gant_blocks')

@CQT.onerror
def oforml_gant_manage():
    chk_link_blocks:CQT.QtWidgets.QCheckBox = DTCLS.app_self.ui.chk_link_gant_blocks
    chk_link_blocks.setText(CEMOJ.EmojiMain.ОборудованиеИнструменты.link.symbol)
    chk_link_blocks.blockSignals(True)
    chk_link_blocks.setChecked(CMS.load_tmp_stukt('_chk_link_gant_blocks',False))
    chk_link_blocks.blockSignals(False)



@CQT.onerror
def update_local_graf(update=False,pnom:int = 0,fill_gant=True,
                      DICT_CLD:dict[datetime.datetime,CMS.Month_cld_day]=None, *args):
    self = DTCLS.app_self
    if DICT_CLD is None :
        DICT_CLD = DTCLS.DICT_CLD
    min_day =  self.ui.de_vol_pl.dateTime().toPyDateTime()
    max_day =  self.ui.de_vol_pl_end.dateTime().toPyDateTime()
    gant_o = CMS.Gant(DICT_CLD,DTCLS.FIELDS_DB_INFO,min_day,max_day)
    if pnom == 0 and self is None:
        raise ValueError(f'update_local_graf: not pnom and self is None')
    if self.is_main_mode():
        t = CQT.TableContext(self.ui.tbl_kal_pl)
        cur_row = t.current_row()
        if cur_row.no_selection:
            raise ValueError(f'update_local_graf: not pnom and no_selection')
        pnom = int(cur_row.value('plan.Пномер'))

    gant_o.load([pnom])


    if (self.is_main_mode() and 'shift' in CQT.get_key_modifiers(self)) or update:
        gant_o.recalc([pnom])

    if gant_o.recalced_naprs_id:
        set_naprs_d = set([DTCLS.DICT_NAPR_DEYAT[_]['Направление'] for _ in gant_o.recalced_naprs_id.keys()])
        for napr_d in set_naprs_d:
            napr_d_name = DTCLS.DICT_NAPRAVLENIE[napr_d]['name']
            update_graf_pad_moshn(DTCLS.app_self,selected_napr=napr_d_name)


    DTCLS.current_gant = gant_o

    def connect_context_blocks():
        t_preview = CQT.TableContext(self.ui.tbl_preview)
        CQT.add_context_menu(t_preview.tbl, DTCLS.app_self, partial(GPL.fnc_context_menu_gant))


    if self and fill_gant:

        gant_o.oforml_table(self,self.ui.tbl_preview)
        oforml_gant_manage()
        connect_context_blocks()

def _____________________etc_________________________():pass


def select_row(self: mywindow):
    if DTCLS.EDIT_POZ_MODE:
        CQT.clear_tbl(self.ui.tbl_pl_add_poz)
    if is_local_gant_hidden(self):
        return
    prepare_local_gant_and_poz_info(self)

def prepare_local_gant_and_poz_info(self,forced_kpl_id:int|None = None):
    set_current_id_poz_kpl(forced_kpl_id)
    update_local_graf(pnom=DTCLS.current_id_poz_kpl)
    GPL.fill_select_poz_kpl(self,forced_kpl_id)
    self.ui.btn_pl_send_dates_into_ERP.setEnabled(False)
    self.ui.tab_addit_info_poz_gant.blockSignals(True)
    self.ui.tab_addit_info_poz_gant.setCurrentIndex(0)
    self.ui.tab_addit_info_poz_gant.blockSignals(False)

def set_current_id_poz_kpl(forced_kpl_id:int|None = None):
    DTCLS.current_id_poz_kpl = None
    DTCLS.current_gant = None
    if forced_kpl_id:
        DTCLS.current_id_poz_kpl = forced_kpl_id
        return
    tbl = DTCLS.app_self.ui.tbl_kal_pl
    nf_kpl = CQT.num_col_by_name_c(tbl,'plan.Пномер',False)
    if nf_kpl:
        id_poz = int(tbl.item(tbl.currentRow(),nf_kpl).text())
        if id_poz>0:
            DTCLS.current_id_poz_kpl = id_poz
@CQT.onerror
def open_pkk(t:CQT.TableContext,i:int,name_clmn:str):
    DTCLS.app_self.current_kpl_table = 'tbl_preview'
    row = t.current_row()
    if row.no_selection:
        return
    val = row.value(name_clmn,get_cust_content=True)
    if not F.is_numeric(val):
        return
    nom_file = int(val)
    tmp_name = download_pkk(nom_file)
    if tmp_name:
        F.run_file_os_c(tmp_name)
def _____________________refactored_________________________():pass#^^^^^^
@CQT.onerror
def test_fnc(*args):
    recalc_kpl()

@CQT.onerror
def fill_id_kpl_into_new_tbls_plan(*args):
    list_ids = CSQ.custom_request_c(DTCLS.db_kplan,f"""SELECT Пномер FROM plan""",one_column=True,hat_c=False)
    for name, tbl in DTCLS.FIELDS_DB_INFO.tables_db.dict_tabels_by_names.items():
        if tbl.poki != DTCLS.PLACE.poki:
            continue
        CSQ.custom_request_c(DTCLS.db_kplan,
                             f"""INSERT INTO {tbl.name}
         ({tbl.table_primary_name}) VALUES (?);""",list_of_lists_c=[[_] for _ in list_ids])






@CQT.onerror
def recalc_kpl(*args):
    list_not_filled_nums = CSQ.custom_request_c(DTCLS.db_kplan,
                        f"""SELECT plan.Пномер
            FROM plan
            WHERE plan.poki = 0;""",one_column=True,hat_c=False)
    gant_o = CMS.Gant(DTCLS.DICT_CLD, DTCLS.FIELDS_DB_INFO, None, None)
    gant_o.load(list_not_filled_nums, forced_recalc=True)


@CQT.onerror
def update_db_info_fields_kpl(*args):
    self: mywindow = DTCLS.app_self
    result = []
    list_err = []
    list_db = []
    for name, data_podr in self.Data_plan.DICT_PODR_POKI.items():

        dict_fields = CSQ.dict_types_tbl(self.db_kplan,name)
        for field in dict_fields.keys():
            field_name = f'{name}.{field}'
            if field_name not in list_db:
                list_db.append(field_name)

    for str_name in list_db:
        if str_name not in DTCLS.FIELDS_DB_INFO.dict_fields:
            if '.' in str_name:
                tbl, field = str_name.split('.')
            else:
                tbl = ''
                field = str_name
            if CSQ.custom_request_c(self.db_kplan,
                                 f"""INSERT INTO info_fields_kpl (table_kpl,name,nickname,alias_db,alias_usr) 
                                 VALUES ("{tbl}","{field}","{str_name}","{str_name}","{field}");"""):
                result.append(str_name)
            else:
                list_err.append(str_name)
    if len(result):
        CQT.msgbox(f'Успешно {pprint.pformat(result)}')
    else:
        CQT.msgbox(f'Новых полей не найдено')
    if list_err:
        CQT.msgbox(f'Ошибки в {pprint.pformat(list_err)}')

@CQT.onerror
def recalc_and_fil_fact(self: mywindow, *args):
    def calc_pozition_fact_kpl_ws_msg(self, pozition_num, msg=True, repaint_graf=True, infotable=False):
        result = CMS.calc_pozition_fact_kpl(self, pozition_num,
                            DTCLS.DICT_GROUP_PODR_VID_RAB_FOR_PLAN,
                            self.DICT_VID_RABOT,
                            DTCLS.DICT_NAPR_DEYAT,
                            DTCLS.DICT_VID_PO_NAPR,
                            DTCLS.DICT_NAPRAVLENIE,
                            DTCLS.DICT_NAPR_DEYAT_NAME,
                            DTCLS.DICT_DOLGN_ETAP,
                            DTCLS.DICT_EMPLOEE_FULL_WITH_DEL,
                            self.DICT_OP_NAME,
                            DTCLS.DICT_CLD,
                            DTCLS.DICT_PODR,
                            DTCLS.FIELDS_DB_INFO
                            )
        if result is None:
            return
        dict_jur_data, rez_update_row_etaps = result
        if infotable:
            list_compare = []
            for etap, val_etap in dict_jur_data.items():
                for item in val_etap:
                    dse = item['ДСЕ'].replace('$', ' ')
                    oper = item['Операция']
                    s_nar = item['Номер_наряда']
                    time = item['Подытог_нормы_для_плана_минут']
                    summ_teor_time = item['summ_teor_time']
                    list_compare.append(
                        {'dse': dse, 'etap': etap, 'Номер_наряда': s_nar, 'summ_teor_time': summ_teor_time,
                         'Подытог_нормы': item['Подытог_нормы'], 'minutes_fact': item['minutes_fact'],
                         'koef_posta': item['koef_posta'],
                         'minutes_fact_k': item['minutes_fact_k'],

                         'oper': oper, 'Подытог_нормы_для_плана_минут': time})
            if not CQT.msgboxg_get_table(self, 'info', list_compare, load_summ=True, yesNoMode=True):
                return

        if msg:
            if rez_update_row_etaps:

                CQT.msgbox(f'Успешно')
            else:
                CQT.msgbox(f'Новых работ не обнаружено')
                
        
    tbl = self.ui.tbl_kal_pl
    if 'shift' in CQT.get_key_modifiers(self):
        row = CQT.get_dict_line_form_tbl(tbl)
        if 'plan.Пномер' not in row:
            return
        nf_pnum = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
        nf_stat = CQT.num_col_by_name_c(tbl, 'plan.Статус')
        list_pnums = []
        for i in range(tbl.rowCount()):
            if not tbl.isRowHidden(i):
                if tbl.item(i, nf_stat).text() in (
                        'Долгосрочный',
                        'Резерв',
                        'Завершена',
                        'Приостановлена',
                        'На удаление',
                        'Перепроверка',):
                    continue
                list_pnums.append(int(tbl.item(i, nf_pnum).text()))
        if not CQT.msgboxgYN(f'Учитываются только статусы (Подготовка, Изготовление, К производству)\n\n'
                             f'Это займет около {round(len(list_pnums) * 4 / 60, 1)} минут\n\nпродолжить?'):
            return
        for pozition_num in list_pnums:
            calc_pozition_fact_kpl_ws_msg(self, pozition_num, False, False,infotable=False)
            print(f'{pozition_num} recalced success')
        CQT.msgbox(f'Звершено')

    else:
        row = CQT.get_dict_line_form_tbl(tbl)
        if 'plan.Пномер' not in row:
            return
        pozition_num = int(row['plan.Пномер'])
        calc_pozition_fact_kpl_ws_msg(self, pozition_num,infotable=True)


@CQT.onerror
def fill_napr_into_cmb_select_napr(self: mywindow):
    dict_napr = dict()
    dict_napr['none'] = ''
    dict_napr[None] = 'Все'
    dict_napr_add = {_['name']: _['alias'] for _ in self.Data_plan.DICT_NAPRAVLENIE.values()
                                            if _['poki'] == CFG.Config.place.poki}
    dict_napr.update(dict_napr_add)

    CQT.fill_list_combobx(self,self.ui.cmb_select_napr,list(dict_napr.values()),
                          list_data=list(dict_napr.keys()),current_text='')


@CQT.onerror
def pl_graf_context_as_tbl(*args):
    self = DTCLS.app_self
    selected_napr = self.ui.cmb_select_napr.currentData(CQT.Qt.UserRole)
    if selected_napr == 'none':
        return
    update_graf_pad_moshn(self, selected_napr,as_table=True)

@CQT.onerror
def update_graf_site_and_get_local(self: mywindow):
    selected_napr = self.ui.cmb_select_napr.currentData(CQT.Qt.UserRole)
    if selected_napr == 'none':
        return
    update_graf_pad_moshn(self, selected_napr)
    GEN_PLG(self, selected_napr)



@CQT.onerror
def update_graf_pad_moshn(self: mywindow, selected_napr=None, as_table=False,  *args):

    @CQT.onerror
    def save_graf_pad_moshn(self: mywindow, napr, percent, name_for_file, resp, max_date,data_norms, *args):
        def calc_vol_by_date(date_nach, date_end, mosh, curr_date):
            if not F.is_date(date_nach, "%Y-%m-%d"):
                return 0
            if not F.is_date(date_end, "%Y-%m-%d"):
                return 0
            date_nach = F.strtodate(date_nach)
            date_end = F.strtodate(date_end)
            if curr_date >= date_nach and curr_date <= date_end:
                delta = (date_end - date_nach).days + 1
                day_mosh = mosh
                if delta > 0:
                    day_mosh = mosh / delta
                return day_mosh
            else:
                return 0

        def calc_graf_pad_moshn(self: mywindow, napr, percent, resp, max_date, dict_data_norms, *args):
            list_err = []
            """
            O:\Журналы и графики\Ведомости для передачи

                      arr_kl(1, UBound(arr_kl, 2)) = Data
                      arr_kl(2, UBound(arr_kl, 2)) = summ_kl
                      arr_kl(3, UBound(arr_kl, 2)) = max_kl
                      arr_kl(4, UBound(arr_kl, 2)) = summ_kl_skd
                      arr_kl(5, UBound(arr_kl, 2)) = summ_kl_std
                      arr_kl(6, UBound(arr_kl, 2)) = summ_kl_autsors
                      arr_kl(7, UBound(arr_kl, 2)) = summ_kl_rezerv
            :param self:
            :param args:
            :return:
            """
            list_wo_kd_td = []

            res = {'date': [],
                   "summ_napr": [],
                   "max_napr": [],
                   "summ_napr_skd": [],
                   "summ_napr_std": [],
                   "summ_napr_autsors": [],
                   "summ_napr_rezerv": [],
                   "summ_napr_rezerv_d": [],
                   }
            # max_date = F.add_months(F.strtodate(F.start_end_dates_c(vid='m')[1]),15)

            start_date = F.add_months(F.strtodate(F.now("%Y-%m-%d")), -1)
            max_date = F.strtodate(max_date,"%Y-%m-%d")
            list_dates = [_ for _ in DTCLS.DICT_CLD.keys() if  start_date <= _ <= max_date]
            podr_eval_name = 'план_' + self.place.evaluation_department.Имя
            dict_moshn = dict()
            for item in resp:
                data_norms = []
                kpl = item['Пномер']
                if kpl in dict_data_norms:
                    data_norms = dict_data_norms[kpl]
                for it in data_norms:
                    date_data = F.strtodate(it['day_dt'],"%Y-%m-%d")
                    norma = it['val_minutes']
                    if date_data not in dict_moshn:
                        dict_moshn[date_data]=dict()
                    if kpl not in dict_moshn[date_data]:
                        dict_moshn[date_data][kpl] = 0
                    dict_moshn[date_data][kpl] += norma

            for date_dt, val_date in dict_moshn.items():
                for kpl, norm in val_date.items():
                    dict_moshn[date_dt][kpl] = round(norm/60,2)

            if list_err and selected_napr: #07.11.25
                CQT.msgboxg_get_table_ok_inf(self,'Ошибки',list_err)
                return
            for date in list_dates:
                summ_napr = 0
                max_napr = 0

                #for podr in [k for k, _ in self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN.items() if _['estimated']]
                for podr in list({v['Имя'] for k,v in self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items() if v['poki'] == self.place.poki and v['estimated']}):
                    max_napr += round(DTCLS.DICT_CLD[date].dict_podrs[podr] * percent / 100, 2)
                summ_napr_skd = 0
                summ_napr_std = 0
                summ_napr_autsors = 0
                summ_napr_rezerv = 0
                summ_napr_rezerv_d = 0
                for item in resp:

                    #vol = calc_vol_by_date(item['Пдата_нач_сб'], item['Пдата_зав_сб'], item['Нчас_сб'], date)
                    vol = 0
                    if date in dict_moshn:
                        if item['Пномер'] in dict_moshn[date]:
                            vol = dict_moshn[date][item['Пномер']]
                    if vol == 0:
                        continue
                    if item['Имя'] in ('Резерв','Долгосрочный'):
                        if item['Имя'] == 'Резерв':
                            summ_napr_rezerv += vol
                            list_wo_kd_td.append(
                                ['Резерв', date, item['№проекта'], item['№ERP'], item['Пдата_нач'], item['Пдата_зав'], item['Пномер'],vol])
                        if item['Имя'] == 'Долгосрочный':
                            summ_napr_rezerv_d += vol
                            list_wo_kd_td.append(
                                ['Долгосрочный', date, item['№проекта'], item['№ERP'],  item['Пдата_нач'], item['Пдата_зав'], item['Пномер'],vol])
                    else:
                        summ_napr += vol
                        if item['Фдата_получения_КД'] != '':
                            summ_napr_skd += vol
                            list_wo_kd_td.append(
                                ['с КД', date, item['№проекта'], item['№ERP'], item['Пдата_нач'], item['Пдата_зав'], item['Пномер'],vol])
                        if item['МК'] != 0:
                            summ_napr_std += vol
                            list_wo_kd_td.append(
                                ['с ТД', date, item['№проекта'], item['№ERP'], item['Пдата_нач'], item['Пдата_зав'], item['Пномер'],vol])
                        if item['МК'] == 0 and item['Фдата_получения_КД'] == '':
                            list_wo_kd_td.append(
                                ['Без КД и Без ТД', date, item['№проекта'], item['№ERP'], item['Пдата_нач'], item['Пдата_зав'], item['Пномер']])

                res['date'].append(F.datetostr(date, '%d.%m.%Y'))
                res["summ_napr"].append(round(summ_napr, 2))
                res["max_napr"].append(round(max_napr, 2))
                res["summ_napr_skd"].append(round(summ_napr_skd, 2))
                res["summ_napr_std"].append(round(summ_napr_std, 2))
                res["summ_napr_autsors"].append(round(summ_napr_autsors, 2))
                res["summ_napr_rezerv"].append(round(summ_napr_rezerv, 2))
                res["summ_napr_rezerv_d"].append(round(summ_napr_rezerv_d, 2))

            list_of_lists = [
                res['date'],
                res["summ_napr"],
                res["max_napr"],
                res["summ_napr_skd"],
                res["summ_napr_std"],
                res["summ_napr_autsors"],
                res["summ_napr_rezerv"],
                res["summ_napr_rezerv_d"],
            ]
            if 'alt' in CQT.get_key_modifiers(self):
                F.save_file(F.dir_workdesc_c() + F.sep() + f'{napr}_{F.now("%Y_%m_%d")}.txt', list_wo_kd_td)
            return list_of_lists

        dict_data_norms = dict()
        for it in data_norms:
            id = it['id_poz']
            if id not in dict_data_norms:
                dict_data_norms[id] = []
            dict_data_norms[id].append(it)
        data = calc_graf_pad_moshn(self, napr, percent, resp, max_date,dict_data_norms)
        name_file = f'gr_pad_mosh_{name_for_file}.txt'
        F.save_file(F.scfg('BD_selector') + F.sep() + name_file, data)

    #TODO add tatkuz
    SET_estimated_podr = {v['Имя'] for k,v in self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items() if v['estimated']}
    dict_estimated_podr_filtr = {k:v for k,v in self.Data_plan.DICT_PODR_POKI.items() if k in SET_estimated_podr}
    list_fields_and_tabels =  [[', '.join([f"{k}.{_['Имя_начала_этапа']} AS Пдата_нач" ,
                        f"{k}.{_['Имя_конца_этапа']} AS Пдата_зав", f"{k}.{_['Имя_поля'].split(';')[0]} AS Нчас"]),
                            f'{k} ON {k}.НомПл == пл_оуп.НомПл,' ] for k, _ in dict_estimated_podr_filtr.items()]

    prefix = """SELECT plan.Пномер, napravlenie.name, 
                status_poz.Имя, plan.Фдата_получения_КД, 
                    plan.МК, """
    middle  = """,
    пл_оуп.№проекта, пл_оуп.№ERP
                     FROM пл_оуп 
                    INNER JOIN plan ON plan.Пномер == пл_оуп.НомПл,"""
    fostfix = f"""
                     status_poz ON status_poz.Пномер == plan.Статус,
                     napravlenie ON napravlenie.Пномер == napravl_deyat.Направление,
                     napravl_deyat ON napravl_deyat.Пномер == plan.Направление_деятельности

                    WHERE plan.poki = {self.place.poki} and status_poz.Пномер IN (
    {', '.join([str(i) for i, _ in self.Data_plan.DICT_STATUS_POZ.items() if _['for_reports']])})"""
    reqs = [f"""{prefix}
                    {item[0]}
                    {middle}
                    {item[1]}
                    {fostfix}""" for item in list_fields_and_tabels]

    req_str = ' UNION ALL '.join(reqs)

    resp = CSQ.custom_request_c(self.db_kplan,  req_str ,
                                rez_dict=True)
    max_date = F.now("%Y-%m-%d")

    dict_pozs = dict()
    for item in resp:
        if (F.is_date(item['Пдата_зав'],"%Y-%m-%d") and
                F.strtodate(item['Пдата_зав'],"%Y-%m-%d") > F.strtodate(max_date,"%Y-%m-%d" )):
            max_date = item['Пдата_зав']

        if item['Пномер'] not in dict_pozs:
            dict_pozs[item['Пномер']] = {
                'Пдата_нач':None,
                'Пдата_зав':None,
                'Нчас':0,
                'Фдата_получения_КД':F.now("%Y-%m-%d"),
            }
        if F.is_date(item['Пдата_нач'], "%Y-%m-%d"):
            if (dict_pozs[item['Пномер']]['Пдата_нач'] == None or
                    F.strtodate(item['Пдата_нач'],"%Y-%m-%d") <
                    F.strtodate(dict_pozs[item['Пномер']]['Пдата_нач'],"%Y-%m-%d")):
                dict_pozs[item['Пномер']]['Пдата_нач'] = item['Пдата_нач']

        if F.is_date(item['Пдата_зав'], "%Y-%m-%d"):
            if (dict_pozs[item['Пномер']]['Пдата_зав'] == None or
                    F.strtodate(item['Пдата_зав'],"%Y-%m-%d") >
                    F.strtodate(dict_pozs[item['Пномер']]['Пдата_зав'],"%Y-%m-%d")):
                dict_pozs[item['Пномер']]['Пдата_зав'] = item['Пдата_зав']

        if F.is_date(item['Фдата_получения_КД'], "%Y-%m-%d"):
            if (F.strtodate(item['Фдата_получения_КД'],"%Y-%m-%d") >
                    F.strtodate(dict_pozs[item['Пномер']]['Фдата_получения_КД'],"%Y-%m-%d")):
                dict_pozs[item['Пномер']]['Фдата_получения_КД'] = item['Фдата_получения_КД']

        if F.is_numeric(item['Нчас']):
            dict_pozs[item['Пномер']]['Нчас'] += F.valm(item['Нчас'])

    start_date = F.add_months(F.strtodate(F.now("%Y-%m-%d")), -1)
    agr = CMS.Gant_agregator()
    list_main_etaps = [_.id for _ in DTCLS.FIELDS_DB_INFO.tables_db.tabels if
                       _.name == self.place.evaluation_department.Имя and _.poki in (None,CFG.Config.place.poki)]

    data_norms = agr.load(start_date,F.strtodate(max_date,"%Y-%m-%d"),list(dict_pozs.keys()),list_main_etaps)

    if as_table:
        def fnc_oform_filter(tbl:CQT.QtWidgets.QTableWidget,tblf:CQT.QtWidgets.QTableWidget):
            CMS.fill_filtr_c(DTCLS.app_self,tblf,tbl, combo_dict={'Этап':None})
            pass

        CQT.msgboxg_get_table_ok_inf(self,'Таблица графика загрузки плана',[{
                                        'Дата':_['day_dt'],
                                        'Этап': DTCLS.DICT_PODR_BY_ID[
                                                    _['etap_podrazdel']]['Имя'],
                                        'КПЛ':_['id_poz'],
                                        'Статус':_['state'],
                                        'Напр.д.':_['napr_d'],
                                        'Позиция':_['poz'],
                                        'Колич.':_['count'],
                                        'Проект':_['np'],
                                        'ЗП':_['zp'],
                                        'Время,час.':round(_['val_minutes']/60 ,2),
                                        'Предел,час.':round(
                                            DTCLS.DICT_CLD[F.strtodate(_['day_dt'],"%Y-%m-%d")].dict_podrs[
                                                DTCLS.DICT_PODR_BY_ID[
                                                    _['etap_podrazdel']]['Имя']] ,2),
                                             } for _ in data_norms],
                            styleSheet=CQT.MES_CSS,load_summ=True,
                                     func_oform_filtr=fnc_oform_filter,showFullScreen=True)
        return

    cnter = 0
    for napr, percent, name_for_file in [[_['name'], _['val'], _['name_for_file_graf_pad_mosh']] for _ in
                                         self.Data_plan.DICT_NAPRAVLENIE.values() if _['poki'] == self.place.poki]:
        cnter += 1
        if selected_napr == None or selected_napr == napr:

            save_graf_pad_moshn(self, napr, percent, name_for_file, [_ for _ in resp if _['name'] == napr], max_date,data_norms)



@CQT.onerror
def calc_current_ifo_tbl_name(self):
    return self.current_kpl_table

@CQT.progress_decorator
@CQT.onerror
def check_kpl_by_erp(self: mywindow, hook_prog_bar=None):
    USE_TMP = True
    _LOAD_FROM_BASES = True

    # TODO get all nomen and all res
    def get_list_nomen(data):
        for i, product in enumerate(data['Продукция']):
            data['Продукция'][i]['Description_Номенклатура'] = 'err'
            if product['Номенклатура_Key'] in dict_all_nomen:
                data['Продукция'][i]['Description_Номенклатура'] = dict_all_nomen[product['Номенклатура_Key']]
            else:
                list_err.append({'КПЛ':'ЕРП','Содержание':f"Для {data['Number']} {data['Date']} нет номера номенклатуры в ЕРП"})

            data['Продукция'][i]['Description_РесурсныеСпецификации'] = 'err'
            if product['Спецификация_Key'] == '00000000-0000-0000-0000-000000000000':
                list_err.append({'КПЛ':'ЕРП','Содержание':
                    f"Для {data['Number']} {data['Date']} в номенклатуре {data['Продукция'][i]['Description_Номенклатура']} ресурсная не назначена. (см в ЕРП)"})
            else:
                if product['Спецификация_Key'] in dict_all_res:
                    data['Продукция'][i]['Description_РесурсныеСпецификации'] = dict_all_res[
                        product['Спецификация_Key']]
                else:
                    list_err.append({'КПЛ':'ЕРП','Содержание':
                        f"Для {data['Number']} {data['Date']}  {data['Продукция'][i]['Description_Номенклатура']} ресурсная помечена на удаление в ЕРП"})
        return F.deploy_dict_c(data['Продукция'], 'Description_Номенклатура')

    if not CQT.msgboxgYN(f'Займет пару минут, продолжить?'):
        return


    hook_prog_bar.open()
    hook_prog_bar.set(0)
    hook_prog_bar.text('Получение данных')

    begin_year = F.start_end_dates_c(F.date_add_days(F.now(), -365), format_out="%Y-%m-%d 00:00:01")[0]
    last_year = F.datetostr(F.strtodate(begin_year), "%Y")
    this_year = F.now("%Y")

    days = (F.now('') - F.strtodate(begin_year)).days

    list_poz = CSQ.custom_request_c(self.db_kplan, f"""SELECT plan.Пномер, знпр.Ref_Key_py, знпр.Год, пл_оуп.НомПл, 
    пл_оуп.№ERP, пл_оуп.Номенклатура_ЕРП, пл_оуп.Количество, пл_оуп.НомПартии_ЗП, пл_топ.Спецификация_ЕРП, пл_оуп.Дата_отгрузки_ПУ, 
       пл_оуп.№проекта, status_poz.Имя as status, пл_оуп.Дата_заявки_на_произв FROM пл_оуп 
        INNER JOIN plan ON plan.Пномер == пл_оуп.НомПл
        INNER JOIN пл_топ ON пл_топ.НомПл == пл_оуп.НомПл
        INNER JOIN знпр ON знпр.s_num == пл_оуп.Пномер_ЗП
        INNER JOIN status_poz ON status_poz.Пномер == plan.Статус
         WHERE  plan.poki = {self.place.poki} and 
            datetime(пл_оуп.Дата_заявки_на_произв || '00:00:01') > datetime('{begin_year}')""", rez_dict=True)





    set_py = set()
    for poz in list_poz:
        #year = F.datetostr(F.strtodate(poz['Дата_заявки_на_произв']), "%Y")
        #py = poz['№ERP'].split('\\')[-1]
        set_py.add(poz['Ref_Key_py'])
        # list_py_sort = sorted(list(set_py))
    list_err = []
    dir = rf'{CMS.tmp_dir()}'
    puthname = rf'{dir}\dataERP_{F.now("%Y%m%d")}.pickle'
    if not F.existence_file_c(dir):
        CQT.msgbox(f'Не доступен каталог {dir}')
        return
    dict_all_nomen= dict_all_res= DICT_STATUS = ref_key_pdo = data_all_last = data_all_this = []
    if USE_TMP:
        if F.existence_file_c(puthname):
            dict_all_nomen, dict_all_res, DICT_STATUS, ref_key_pdo, data_all_last, data_all_this = F.load_file_pickle(
                puthname)
            _LOAD_FROM_BASES = False

    m = None
    if _LOAD_FROM_BASES:
        m = ERP.OrdersComposit()
        dict_all_nomen = F.deploy_dict_c(m.get_response(doc_name='Catalog_Номенклатура',
                                                        wet_filtr=f"?$filter=DeletionMark eq false&$select= Ref_Key, Description"),
                                         'Ref_Key')
        if dict_all_nomen == False:
            CQT.msgbox(f'Соединение с сервером 1С не установлено')
            return
        dict_all_res = F.deploy_dict_c(m.get_response(doc_name='Catalog_РесурсныеСпецификации',
                                                      wet_filtr=f"?$filter=DeletionMark eq false&$select= Ref_Key, Description"),
                                       'Ref_Key')
        DICT_STATUS = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM status_poz""", rez_dict=True),
            "Имя")

        # m.get_orders(last_days=2)  # find_me="Статус eq 'КПроизводству'"

        ref_key_pdo = m.get_response(doc_name='Catalog_СтруктураПредприятия',
                                     wet_filtr=f"?$filter=Description eq "
                                               f"'Планово-диспетчерский отдел Производства (Пауэрз)' &$select= Ref_Key")[
            0]['Ref_Key']
        data_all_last = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                                       wet_filtr=f"""?$filter=year(Date) eq {last_year} and 
                                   Подразделение_Key eq guid'{ref_key_pdo}'&$select= Ref_Key, Number,
                                    Date, Статус, Комментарий, Продукция/Номенклатура_Key, Продукция/Количество,
                                     Продукция/Спецификация_Key, Продукция/ДатаОтгрузки,Продукция/LineNumber""")
        # data_all_last = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
        #                          wet_filtr=f"""?$filter=year(Date) eq {last_year}&$top=10&$select=*""")
        data_all_this = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                                       wet_filtr=f"""?$filter=year(Date) eq {this_year} and 
                                       Подразделение_Key eq guid'{ref_key_pdo}'&$select= Ref_Key, Number,
                                        Date, Статус, Комментарий, Продукция/Номенклатура_Key, Продукция/Количество,
                                         Продукция/Спецификация_Key, Продукция/ДатаОтгрузки,Продукция/LineNumber""")
        F.save_file_pickle(puthname,
                           [dict_all_nomen, dict_all_res, DICT_STATUS, ref_key_pdo, data_all_last, data_all_this])

    hook_prog_bar.set(10)
    hook_prog_bar.text('Обработка данных')


    dict_data_all = dict()
    i = 1
    for item in data_all_last:
        print(f'data_all_last {i}/{len(data_all_last)}')
        #year = F.datetostr(F.strtodate(item['Date'], "%Y-%m-%dT%H:%M:%S"), "%Y")
        #pyear = f"{item['Number']}${year}"
        ref = item['Ref_Key']
        dict_data_all[ref] = item
        dict_data_all[ref]['dict_nomen'] = get_list_nomen(dict_data_all[ref])
        i += 1
    i = 1
    for item in data_all_this:
        print(f'data_all_this {i}/{len(data_all_this)}')
        #year = F.datetostr(F.strtodate(item['Date'], "%Y-%m-%dT%H:%M:%S"), "%Y")
        #pyear = f"{item['Number']}${year}"
        ref = item['Ref_Key']
        dict_data_all[ref] = item
        dict_data_all[ref]['dict_nomen'] = get_list_nomen(dict_data_all[ref])
        i += 1

    i = 0
    for ref, zp_erp_data in dict_data_all.items():
        print(f'{i} / {len(dict_data_all)}')
        i += 1
        if ref not in set_py:
            list_err.append({'КПЛ':'ЕРП','Содержание':f"Заказ {zp_erp_data['Number']} "
                            f"({';'.join(list(zp_erp_data['dict_nomen']))})"
                            f"от {zp_erp_data['Date'].replace('T', ' ')} отсутствует в МЕС"})

    i = 1

    list_years = list({_['Год'] for _ in  list_poz if _['Год'] > 0})


    min_year = min(list_years)
    max_year = max(list_years)
    wet_req_text = f"""
        ВЫБРАТЬ РАЗЛИЧНЫЕ
            ЭтапПроизводства2_2.НомерПартииЗапуска КАК НомерПартииЗапуска,
            УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЭтапПроизводства2_2.Распоряжение.Ссылка) КАК Ref_Key_py
            
        ИЗ
            Документ.ЭтапПроизводства2_2 КАК ЭтапПроизводства2_2
                
        ГДЕ
            ЭтапПроизводства2_2.Дата МЕЖДУ ДАТАВРЕМЯ({min_year}, 1, 1, 0, 0, 0) И ДАТАВРЕМЯ({max_year+1}, 1, 1, 0, 0, 0)
            И ЭтапПроизводства2_2.НЭ_НулевойЭтап = ИСТИНА
    """
    key, data_rez = APIERP.get_wet_request(wet_req_text)
    if key != 200:
        CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
        return
    DICT_NULL_ETAPS = F.deploy_dict_c( data_rez['data'],'Ref_Key_py')

    for item in list_poz:

        hook_prog_bar.set(20 + round((i/len(list_poz))*80))

        CQT.statusbar_text(self, f'{i} / {len(list_poz)}')
        print(f'{i} / {len(list_poz)}')
        i += 1

        poz = item

        s_num = poz['Пномер']
        py = poz['№ERP']
        ref = poz['Ref_Key_py']
        nomen = poz['Номенклатура_ЕРП']
        count_poz = poz['Количество']
        num_line_py = poz['НомПартии_ЗП']
        spec_erp = poz['Спецификация_ЕРП']
        date_otgruz = poz['Дата_отгрузки_ПУ']

        if py == '-':
            list_err.append({'КПЛ':s_num,'Содержание':f"{item['№проекта']} не присвоен {self.place.doc_prefix} "})
            continue

        #pyear_mes = f"{py}${year}"
        if ref not in dict_data_all:
            list_err.append({'КПЛ':s_num,'Содержание':f"{py} не найден в ЕРП"})
            continue
        data = dict_data_all[ref]
        date_poz_erp = data['Date'].replace('T', ' ')

        stat_prim = DICT_STATUS[item['status']]['Примечание']
        if stat_prim != '':
            if stat_prim != data['Статус']:
                list_err.append({'КПЛ':s_num,'Содержание':f"{py} {date_poz_erp} \n  статус '{stat_prim}' не соответсвует статусу ЕРП '{data['Статус']}'"})


        dict_poz_erp = data['dict_nomen']

        if nomen not in dict_poz_erp:
            list_err.append({'КПЛ':s_num,'Содержание':f"{nomen}\n     отсутствует в ЕРП в \n{py} {date_poz_erp}"})
        else:
            if dict_poz_erp[nomen]['Количество'] != count_poz:
                list_err.append({'КПЛ':s_num,'Содержание':
                    f"{nomen}\n     количество не совпадает с ЕРП в {self.place.doc_prefix} \n{py} {date_poz_erp}\n      "
                    f"ЕРП: \n{dict_poz_erp[nomen]['Количество']}\n        и MES: \n{count_poz}"})

            tmp_num_line_py = int(dict_poz_erp[nomen]['LineNumber'])

            if ref in DICT_NULL_ETAPS:

                num_first_etap = DICT_NULL_ETAPS[ref]
                if  int(dict_poz_erp[nomen]['LineNumber']) >= num_first_etap:
                    tmp_num_line_py = 1 + int(dict_poz_erp[nomen]['LineNumber'])

            if tmp_num_line_py != num_line_py:
                CSQ.custom_request_c(self.db_kplan, f"""UPDATE пл_оуп SET НомПартии_ЗП = ? WHERE НомПл = ?""",
                                         list_of_lists_c=[[tmp_num_line_py, item['НомПл']]])

            if dict_poz_erp[nomen]['Description_РесурсныеСпецификации'] != spec_erp:
                list_err.append({'КПЛ':s_num,'Содержание':
                    f"{nomen} (Номер КПЛ {item['НомПл']})\n     ресурсная спецификация НАИМЕНОВАНИЕ не совпадает с ЕРП в {self.place.doc_prefix} \n{py} {date_poz_erp} "
                    f"      ЕРП: \n{dict_poz_erp[nomen]['Description_РесурсныеСпецификации']}\n     и MES: \n{spec_erp}"})
            date_otgruz_poz_erp = F.datetostr(F.strtodate(dict_poz_erp[nomen]['ДатаОтгрузки'], "%Y-%m-%dT%H:%M:%S"),
                                              '%Y-%m-%d')
            if date_otgruz  != date_otgruz_poz_erp:
                list_err.append({'КПЛ':s_num,'Содержание':
                    f"{nomen}\n     дата отгрузки не совпадает с ЕРП в {self.place.doc_prefix}\n{py} {date_poz_erp}\n"
                    f"  ЕРП: \n{date_otgruz_poz_erp}\n   и MES: \n{date_otgruz}"})

            # list_err.append(f"{py} обновлено примечание ЕРП: {komment}")
    CQT.statusbar_text(self)
    #path = F.put_po_umolch()
    #F.save_file(fr'{path}\list_err.txt', list_err)
    #F.run_file_os_c(fr'{path}\list_err.txt')
    CMS.save_tmp_val('count_exeptions_compare_erp_mes',str(len(list_err)),self.db_kplan)
    hook_prog_bar.close()
    list_err = [ {k:str(v).replace('\n',' ') for k,v in _.items()}  for _ in list_err]
    CQT.msgboxg_get_table(self,'Неосоответствия',list_err,btn0_name='ОК', disable_btn1=True,)


def update_date_kplmk_from_narmk(self: mywindow):
    query = f"""SELECT plan.МК,  пл_топ.НомПл , пл_топ.Дата_МК FROM пл_топ INNER JOIN 
     plan ON plan.Пномер ==  пл_топ.НомПл 
     WHERE пл_топ.Дата_МК != "" and plan.МК <> 0 and plan.poki = {self.place.poki};"""
    res = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, query, rez_dict=True), 'МК')
    list_mk = [str(_) for _ in res.keys()]
    str_list_mk = ','.join(list_mk)
    query2 = f"""SELECT Дата,Пномер FROM mk WHERE Пномер IN ({str_list_mk}) AND Статус != 'НаУдаление'"""
    res_2 = CSQ.custom_request_c(self.bd_naryad, query2, rez_dict=True)
    for item in res_2:
        res[item['Пномер']]['Дата_МК'] = F.datetostr(F.strtodate(item['Дата'], "%y-%m-%d"), "%Y-%m-%d")
    for mk in res.keys():
        CSQ.custom_request_c(self.db_kplan,
                             f"""UPDATE пл_топ SET Дата_МК = "{res[mk]['Дата_МК']}" WHERE НомПл = {res[mk]['НомПл']}""")


@CQT.onerror
def apply_recalc_dates_etaps(self: mywindow, *args):
    tbl = self.ui.tbl_kal_pl
    t = CQT.TableContext(tbl)
    cur_row = t.current_row()
    if cur_row.no_selection:
        CQT.msgbox(f'Не выбрана строка КПЛ')
        return

    num_kpl = int(cur_row.value('plan.Пномер'))
    CMS.Pozition.set_flag_recalc_dates(self.db_kplan, num_kpl, 0)
    if 'plan.Потребность_пересч_сроков' not in t.nf:
        return
    cur_row.set_value('plan.Потребность_пересч_сроков','0')
    oforml_row_plan_tbl(cur_row)


@CQT.onerror
def pl_cr_dir_poz(self: mywindow, *args):
    tbl = self.ui.tbl_kal_pl
    row = tbl.currentRow()
    if row == -1:
        return
    row = CQT.get_dict_line_form_tbl(tbl)
    num_kpl = row['plan.Пномер']
    poz = CMS.Pozition(int(num_kpl), self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
    poz.load_kpl_table('пл_оуп')
    np = poz.dict_tables['пл_оуп']['№проекта'].strip()
    if np == '':
        CQT.msgbox(f'Не указан №проекта')
        return
    py = poz.dict_tables['пл_оуп']['№ERP'].strip()
    if py == '':
        CQT.msgbox(f'Не указан №ERP')
        return
    year_py = poz.dict_tables['пл_оуп']['Год']
    if py == '-' or py == f'{self.place.doc_prefix}00-000000' :
        CQT.msgbox(f'номер {self.place.doc_prefix} не корректный')
        return
    napr = poz.get_napravl() #27.10.25 по задаче 100058608
    struct_dirs = napr.get('projects_localnet_struct', '')

    dir_proj = CMS.get_path_to_proj_NPPY_c(np, py,year_py,napr['projects_localnet_path'])
    if F.existence_file_c(dir_proj):
        CQT.msgbox(f'Директория {dir_proj} уже создана')
        return
    if not F.create_dir_c(dir_proj):
        CQT.msgbox(f'Отказано в доступе: {dir_proj}')
        return
    base_path = pathlib.Path(dir_proj) #27.10.25 по задаче 100058608
    for folder in struct_dirs.split(';'):
        (base_path / folder).mkdir(exist_ok=True, parents=True)
    F.open_dir_c(dir_proj)



@CQT.onerror
def pl_cr_mk(self: mywindow, *args):
    tbl = self.ui.tbl_kal_pl
    row = tbl.currentRow()
    if row == -1:
        return
    nf_pnom = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
    if nf_pnom == None:
        CQT.msgbox(f'ОШибка подбора поля plan.Пномер')
        return
    pnom = int(tbl.item(row, nf_pnom).text())

    self.dict_cur_poz_cr_mk = CSQ.custom_request_c(self.db_kplan, f"""SELECT    пл_оуп.№проекта as "Проект", 
    пл_оуп.№ERP as "№ERP",  napravl_deyat.Псевдоним as "Вид",
                 napravlenie.name as "Направление",  пл_оуп.Количество as "Количество", plan.Позиция, 
                 plan.Пномер as "Пномер", пл_оуп.Номенклатура_ЕРП as "Номен. ЕРП"  FROM пл_оуп  INNER JOIN plan ON пл_оуп.НомПл = plan.Пномер,
        napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
        napravlenie ON napravlenie.Пномер = napravl_deyat.Направление WHERE plan.Статус in (2,3,1,7) and plan.Пномер = {pnom} and plan.poki = {self.place.poki};""",
                                                   rez_dict=True)

    if len(self.dict_cur_poz_cr_mk) == 1:
        self.dict_cur_poz_cr_mk = self.dict_cur_poz_cr_mk[0]
    else:
        CQT.msgbox(f'ОШибка загрузки БД')
        return
    self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget, 'Создание МК'))
    # self.tkp_current_schema = None
    self.tkp_current_schema.clear()
    name_tab = CQT.msgboxg_get_table(self, 'Режим создания МК', ['Режим', 'Создание МК из *.XML', 'Разработка МК'],
                                     show_filtr=False)
    if name_tab == False:
        return
    self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, name_tab[0]['Режим']))
    self.fill_select_poz_for_mk()

#++ 29.10.25
def checking_positions_for_closed_mk(window: QtWidgets.QWidget, poz_nums: list[int | str]) -> bool:
    def list_unclosed_mk(list_joined_poz_pk: str):
        list_if_status = CSQ.custom_request_c(
            CFG.Config.project.db_naryad,
            f"""SELECT Дата_завершения, Пномер, НомКплан as "КПЛ", Статус FROM mk
         WHERE НомКплан IN ({list_joined_poz_pk}) AND Статус == 'Открыта';""", rez_dict=True) #28.11.2025
        list_open_mk = []
        for item in list_if_status:
            if item['Дата_завершения'] == "":
                list_open_mk.append(item)
        return list_open_mk

    pk_params = ','.join(str(poz) for poz in poz_nums)

    znpr_keys = CSQ.custom_request_c(CFG.Config.project.db_kplan,
                                     f'''SELECT Пномер_ЗП FROM пл_оуп WHERE НомПл IN ({pk_params})''',
                                     one_column=True,
                                     hat_c=False)
    if znpr_keys == False:
        print('Ошибка запроса kal_plan.set_stat_closed')
        return
    if len(set(znpr_keys)) > 1:
        return CQT.msgbox('Нельзя закрывать больше чем 1 заказ')

    if list_mk := list_unclosed_mk(pk_params):
        CQT.msgboxg_get_table(window, 'Не закрыты следующие МК', list_mk, show_filtr=False)
        return False
    return True
#-- 29.10.25

@CQT.onerror
def set_stat_closed(self: mywindow, *args): #22.10.25
    def check_fields(tbl):
        list_necessarily_fields = ('plan.Пномер',)
        for field in list_necessarily_fields:
            if CQT.num_col_by_name_c(tbl, field) == None:
                CQT.msgbox(f'Поле {field} не найдено')
                return False
        return True

    tbl = self.ui.tbl_kal_pl

    if not check_fields(tbl):
        return
    if 'shift' in CQT.get_key_modifiers(self):
        list_of_poz = CQT.list_from_wtabl_c(tbl,rez_dict=True)
        if not list_of_poz: return
    else:
        if tbl.currentRow() == -1: return
        list_of_poz = [CQT.get_dict_line_form_tbl(tbl)]

    list_poz_nums = [_['plan.Пномер'] for _ in list_of_poz]
    if not checking_positions_for_closed_mk(window=self, poz_nums=list_poz_nums): #29.10.25
        return
    for pnum in list_poz_nums:
        CSQ.custom_request_c(self.db_kplan, f"""UPDATE plan SET Статус = 4 WHERE Пномер = {pnum}""")

    CQT.msgbox(f'Успешно')
    load_table_db(self)


@CQT.onerror
def find_field_reset(self):
    self.find_field_counter = 0


@CQT.onerror
def find_field(self: mywindow):

    def find_in_tbl(tbl):
        def select():
            CQT.select_cell(tbl, 0, f.tbl_idx)
            if self.ui.tbl_kal_pl.rowCount() > 0:
                CQT.select_cell(self.ui.tbl_kal_pl, 0, f.tbl_idx)

        fl = False
        val = self.ui.le_pl_find_field.text().lower().strip()
        FIELDS = DTCLS.FIELDS_DB_INFO.list_fields
        for f in FIELDS:
            if f.tbl_idx is None or not f.tbl_idx:
                continue
            if val in f.field_alias.lower():
                fl = True
                select()
                self.find_field_counter = f.tbl_idx + 1
        if fl==False:
            for f in FIELDS:
                if f.tbl_idx is None or not f.tbl_idx:
                    continue
                if val in f.description.lower():
                    fl = True
                    select()
                    self.find_field_counter = f.tbl_idx + 1
        if fl==False:
            for f in FIELDS:
                if val in f.field_alias.lower():
                    fl = True
                    CQT.msgbox(f'Поле "{f.field_alias} ({f.description})" скрыто')
        if fl == False:
            self.find_field_counter = 0

    if self.ui.le_pl_find_field.text() == '':
        return
    self.find_field_counter = getattr(self,"find_field_counter",0)
    find_in_tbl(self.ui.tbl_filtr_kal_pl)




@CQT.onerror
def btn_pl_open_dir(self: mywindow):
    tbl = self.ui.tbl_kal_pl
    if tbl.currentRow() == -1:
        return
    row = CQT.get_dict_line_form_tbl(tbl)
    num_kpl = row['plan.Пномер']
    poz = CMS.Pozition(int(num_kpl), self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
    poz.load_kpl_table('пл_оуп')
    np = poz.dict_tables['пл_оуп']['№проекта']
    py = poz.dict_tables['пл_оуп']['№ERP']
    year_py = poz.dict_tables['пл_оуп']['Год']
    path = CMS.get_path_to_proj_NPPY_c(np, py, year_py, poz.get_napravl()['projects_localnet_path']) #08.08.25
    F.open_dir_c(path)


def btn_pl_add_trbl(self: mywindow):
    tbl = self.ui.tbl_kal_pl
    if tbl.currentRow() == -1:
        return
    nk_mk = CQT.num_col_by_name_c(tbl, 'plan.МК')
    if nk_mk == None:
        CQT.msgbox(f'Отсутствует поле plan.МК')
        return
    mk = tbl.item(tbl.currentRow(), nk_mk).text()
    if mk == '0':
        CQT.msgbox(f'МК не создана')
        return
    self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget, 'Замечания по МК'))
    tbl_zam = self.ui.tbl_zamech_add_field
    nk_mk_zam = CQT.num_col_by_name_c(tbl_zam, 'МК')
    tbl_zam.item(0, nk_mk_zam).setText(mk)


@CQT.onerror
def setting_into_plan(self: mywindow, list_p_nom_row):
    CSQ.custom_request_c(self.db_kplan, f"""UPDATE plan SET Постановка_в_план = 1 WHERE 
    Пномер in ({','.join([str(_) for _ in list_p_nom_row])});""")


@CQT.onerror
def get_stat_proiv(self: mywindow, vid):
    if vid == 1:
        CQT.msgbox(f'Не выбран Вид изделия')
        return
    if vid not in self.Data_plan.DICT_VID_PO_NAPR_NAME:
        CQT.msgbox(f'Вид изделия не найден в базе')
        return
    if self.Data_plan.DICT_VID_PO_NAPR_NAME[vid]['Выборка'] <= 1:
        return 121
    return self.Data_plan.DICT_VID_PO_NAPR_NAME[vid]['кг_на_пост_см']


@CQT.onerror
def btn_pl_kopy_norm_etap_buff(self: mywindow):
    tbl = self.ui.tbl_kal_pl
    row_o = CQT.TableContext(tbl).current_row()
    DICT_SOPOST_ETAPOV_VO = {
        'Лазерная резка': 'пл_заг.Нчас_заг',
        'Токарка+фрезеровка': 'пл_мех.Нчас_мехобр',
        'Сборка': 'пл_сб.Нчас_слсб',
        'Сварка': 'пл_сб.Нчас_св',
        'Зачистка': 'пл_сб.Нчас_зач',
        'Вспомогательная': 'plan.Нчас_вспом',
        'Покраска': 'пл_покр.Нчас_покр',
        'Упаковка и комплектование ЗИП': 'пл_компл.Нчас_упаковки'
    }
    DICT_SOPOST_ETAPOV_VO = {_['name']: _['sopost_etapov_vo'].split('|') for _ in self.Data_plan.ETAPS_NAME if
                             _['sopost_etapov_vo'] != None}
    rez_dict = {'Вес': 0, 'ДатаМК': F.now("%y-%m-%d")}
    nk_field_pnom = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
    if nk_field_pnom == None:
        CQT.msgbox(f'plan.Пномер поле не найдено')
        return

    f_intoplan = CQT.num_col_by_name_c(tbl, 'plan.Постановка_в_план')
    nk_field_stat_norm = CQT.num_col_by_name_c(tbl, 'plan.Статус_норм')
    nk_field_proj = CQT.num_col_by_name_c(tbl, "знпр.№проекта")
    nk_field_erp = CQT.num_col_by_name_c(tbl, "знпр.№ERP")
    nk_field_vid = CQT.num_col_by_name_c(tbl, "пл_топ.Вид")
    nk_field_ves_vo = CQT.num_col_by_name_c(tbl, "пл_топ.Уд_вес_ВО")
    set_py = set()
    for i in range(tbl.rowCount()):
        if not tbl.isRowHidden(i):
            set_py.add(tbl.item(i, nk_field_erp).text() + tbl.item(i, nk_field_proj).text())
    if len(set_py) != 1:
        CQT.msgbox(f'В табличной части более одного проекта')
        return

    if nk_field_stat_norm == None:
        CQT.msgbox(f'plan.Статус_норм поле не найдено')
        return
    nk_mk = CQT.num_col_by_name_c(tbl, 'plan.МК')
    if nk_mk == None:
        CQT.msgbox(f'plan.МК поле не найдено')
        return
    if nk_field_ves_vo == None:
        CQT.msgbox(f'пл_топ.Уд_вес_ВО поле не найдено')
        return
    set_etaps_sb = set()
    def is_sb(field_name):
        tbl, field = field_name.split('.')
        for k, item in self.Data_plan.DICT_PODR_POKI.items():
            if tbl == k and item['Имя_поля'] == field:
                if item['Это_группа_сборки']:
                    return True
                else:
                    continue
        return False



    for etap in DICT_SOPOST_ETAPOV_VO:

        field_names = DICT_SOPOST_ETAPOV_VO[etap]
        for field_name in field_names:

            if is_sb(field_name):
                set_etaps_sb.add(etap)

            nk_field_name = CQT.num_col_by_name_c(tbl, field_name)
            if nk_field_name == None:
                CQT.msgbox(f'Не найдено поле {field_name}')
                return
            rez_dict[etap] = 0

            for i in range(tbl.rowCount()):
                if not tbl.isRowHidden(i):
                    if tbl.item(i, nk_field_stat_norm).text() == 'Нет':
                        CQT.msgbox(f'Нормы не прогружены по строке {i + 1} статус -=Нет=-')
                        return
                    rez_dict[etap] += F.valm(tbl.item(i, nk_field_name).text())

    list_pnoms = []
    set_nom_erp = set()
    vid = ''
    ves = ''

    fl_po_tk_all = True
    fl_naid = False
    for i in range(tbl.rowCount()):
        if not tbl.isRowHidden(i):
            if vid == '':
                vid = tbl.item(i, nk_field_vid).text()
            set_nom_erp.add(tbl.item(i, nk_field_erp).text())
            if tbl.item(i, nk_field_stat_norm).text() == 'По ТК':
                list_pnoms.append(str(tbl.item(i, nk_field_pnom).text()))
                mk = int(tbl.item(i, nk_field_pnom).text())
                resp = CSQ.custom_request_c(self.bd_naryad,
                                            f"""SELECT SUM(Вес) FROM mk WHERE mk.НомКплан = {tbl.item(i, nk_field_pnom).text()} AND Статус != 'НаУдаление';""")
                if resp == None or resp == False or len(resp) != 2:
                    CQT.msgbox(f'В МК {mk} ошикба загрузки веса')
                    return
                if f_intoplan != None:
                    tbl.item(i, f_intoplan).setText('1')
                ves = resp[-1][0]
                rez_dict['Вес'] += ves
                fl_naid = True


            elif tbl.item(i, nk_field_stat_norm).text() == 'По Весу' or tbl.item(i,
                                                                                 nk_field_stat_norm).text() == 'По предв_рес':
                fl_po_tk_all = False
                list_pnoms.append(str(tbl.item(i, nk_field_pnom).text()))
                ves_str = tbl.item(i, nk_field_ves_vo).text()
                if ves_str == None or ves_str == False or F.valm(ves_str) == False:
                    CQT.msgbox(f'В Пномер {str(tbl.item(i, nk_field_pnom).text())} ошикба загрузки веса')
                    return

                ves = F.valm(ves_str)
                rez_dict['Вес'] += ves
                fl_naid = True
            else:
                CQT.msgbox(f'Со статусом {tbl.item(i, nk_field_stat_norm).text()} выгрузка не предусмотрена')
                return
    ves = round(rez_dict['Вес'], 2)
    if fl_naid == False:
        CQT.msgbox(f'Не найдено ни одной строки со статусом По ТК/По Весу/По предв_рес')
        return
    if len(set_nom_erp) > 1:
        CQT.msgbox(f'номер ЕРП в таблице должен быть один для выгрузки в план(фильтр)')
        return
    if ves == '':
        CQT.msgbox(f'Не расчитан вес')
        return

    rez_list = []
    sb_sv= 0
    #sb_sv = rez_dict['Сборка'] + rez_dict['Сварка']
    #rez_dict['Сборка+сварка'] = sb_sv
    #rez_dict.pop('Сборка')
    #rez_dict.pop('Сварка')
    for etap in rez_dict:
        if F.is_numeric(rez_dict[etap]):
            etap_val = f'{etap} - {round(rez_dict[etap], 2)}'
        else:
            etap_val = f'{etap} - {rez_dict[etap]}'
        rez_list.append(etap_val)
        if etap in set_etaps_sb:
            sb_sv+= rez_dict[etap]
    row = '\n'.join(rez_list)
    if sb_sv == 0:
        CQT.msgbox(f'Сборка сварка 0 час.')
        return
    proizv = round(ves * 8 / (sb_sv / 2))
    otkl = 100
    stat_proizv = get_stat_proiv(self, vid)
    if stat_proizv != 0 and proizv != 0:
        if proizv > stat_proizv:
            otkl = round(abs(proizv / stat_proizv) * 100, 1)
        else:
            otkl = round(abs(stat_proizv / proizv) * 100, 1)
    oforml_row_plan_tbl(row_o)
    CQT.msgbox(
        f'По {vid}:\n\nСредняя производительность {round(stat_proizv)} кг/п-см\n\nВ текущей выборке производительность {proizv} при весе {ves} кг.'
        f' \n кг/п-см отклонение {round(otkl - 100)}%.\n\n Поэтапно(н-час) :\n{row}')
    return


@CQT.onerror
def check_set_fininsh_py(self: mywindow):
    query = f"""SELECT plan.Пномер, пл_оуп.№ERP || "$" || пл_оуп.№проекта as ERP, plan.Статус, plan.Статус_норм,
      plan.Готовность_ПУ, пл_топ.Дата_МК  
      FROM plan INNER JOIN 
    пл_оуп ON пл_оуп.НомПл = plan.Пномер,
     пл_топ ON пл_топ.НомПл = plan.Пномер 
     WHERE plan.Статус IN (2,7) and plan.poki = {self.place.poki};"""
    res = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, query, rez_dict=True), 'Пномер')
    dict_proj = dict()
    for key in res.keys():
        item = res[key]
        if item['ERP'] not in dict_proj:
            dict_proj[item['ERP']] = {'ready': [], 'notready': []}
        if item['Дата_МК'] != '':
            dict_proj[item['ERP']]['ready'].append(key)
        else:
            dict_proj[item['ERP']]['notready'].append(key)

    list_ready_py = []
    list_not_ready_py = []

    for proj in dict_proj.keys():
        if len(dict_proj[proj]['notready']) == 0:
            for num in dict_proj[proj]['ready']:
                if res[num]['Статус'] != 7 or res[num]['Статус_норм'] != 2 or res[num]['Готовность_ПУ'] != 1:
                    list_ready_py.append(str(num))
        else:
            for num in dict_proj[proj]['ready']:
                if res[num]['Готовность_ПУ'] != 0:
                    list_not_ready_py.append(str(num))
            for num in dict_proj[proj]['notready']:
                if res[num]['Готовность_ПУ'] != 0:
                    list_not_ready_py.append(str(num))

    query = f"""UPDATE plan SET Готовность_ПУ = 1 WHERE Пномер IN ({','.join(list_ready_py)})"""
    CSQ.custom_request_c(self.db_kplan, query)
    query = f"""UPDATE plan SET Готовность_ПУ = 0 WHERE Пномер IN ({','.join(list_not_ready_py)})"""
    CSQ.custom_request_c(self.db_kplan, query)


@CQT.onerror
def generate_dict_norm(self: mywindow):
    tmp_list = [['str', 'poz']]
    for name_tbl, item in self.Data_plan.DICT_PODR.items():
        if item['Имя_поля']:
            order = item['Порядок'] or 0
            for name_field in item['Имя_поля'].split(';'):
                str_full_name = '.'.join([name_tbl, name_field])
                tmp_list.append([str_full_name, order])
    dict_norm = {_[0]: 0 for _ in F.sort_by_column_c(tmp_list, 'poz')[1:]}
    return dict_norm


@CQT.onerror
def dict_norm_from_res(self:mywindow, res, dict_norm='', koef_vneplana=1, koef_pogr_norm=1, count_izd=None, list_log=None,
                       s_num_mk: int = 0):
    def prepare_fact_as_list_opers(s_num_mk):

        dict_fact = dict()
        if s_num_mk == 0:
            return dict_fact

        list_fact = CSQ.custom_request_c(self.bd_naryad,
                                         f"""SELECT Пномер, Твремя,
                                          ФИО,  ФИО2, (Фвремя + Фвремя2) as Фвремя, ДСЕ_ID, Операции,
                                           Опер_время, Опер_колво, Подтвержд_вып FROM 
                                            naryad WHERE naryad.Номер_мк == {s_num_mk} and (ФИО != '' or ФИО2 != '') and Аутсорсинг == 0""",
                                         rez_dict=True)

        for nar in list_fact:
            nar_norma = nar['Твремя']
            kr = 1
            if nar['ФИО'] != '' and nar['ФИО2'] != '':
                nar_norma *=2
                kr =2
            nar_fact = nar['Фвремя']


            list_dse = nar['ДСЕ_ID'].split('|')
            list_oper = nar['Операции'].split('|')
            list_time = nar['Опер_время'].split('|')
            list_count = nar['Опер_колво'].split('|')
            for i, dse in enumerate(list_dse):
                dse = int(dse)
                oper  = list_oper[i]
                time = F.valm(list_time[i])
                count =F.valm(list_count[i])

                time_fact =round(time,2)

                koef_posta = 1
                if kr == 2:
                    koef_posta = 1 / 0.7

                if dse not in dict_fact:
                    dict_fact[dse] = dict()
                if oper not in dict_fact[dse]:
                    dict_fact[dse][oper] = {'Наряды':[],'Всего_мин.':0, 'Всего_шт.':0,'Нарядов':0}
                dict_fact[dse][oper]['Наряды'].append({'№ Наряда':nar['Пномер'],
                                                       'Подтвержден':nar['Подтвержд_вып'],
                                                       'мин.':round(time_fact,3)})
                dict_fact[dse][oper]['Всего_мин.'] += time_fact
                dict_fact[dse][oper]['Всего_шт.'] += count
                dict_fact[dse][oper]['Нарядов'] += 1
        return dict_fact



    if dict_norm == '':
        dict_norm = generate_dict_norm(self)
    if list_log == None:
        list_log = []
    pozition = res[0]['Номенклатурный_номер']
    if count_izd == None:
        CQT.msgbox(f'kal_plan row err количество изделий не указано')
        return None, None
    dict_fact = prepare_fact_as_list_opers(s_num_mk)
    for dse in res:
        fl_mat = True
        for oper in dse['Операции']:
            if oper['Опер_РЦ_код'] not in self.DICT_RC:
                CQT.msgbox(
                    f"По МК№ {s_num_mk} в {dse['Наименование']} {dse['Номенклатурный_номер']} РЦ {oper['Опер_РЦ_код']} не найден в БД")
                return None, None
            if not self.DICT_RC[oper['Опер_РЦ_код']]['use_in_estimate_plan']:
                continue
            if oper['Опер_наименование'] == '' and oper['Этап'] in self.Data_plan.DICT_ETAPS_NAME:
                kod_oper =self.Data_plan.DICT_ETAPS_NAME[oper['Этап']]['Опер_код_для_ткп_стат']
                oper['Опер_код'] = kod_oper
                if kod_oper in self.DICT_OP:
                    oper['Опер_наименование'] = self.DICT_OP[kod_oper]['name']
            if oper['Опер_наименование'] == '':
                CQT.msgbox(
                    f"По МК№ {s_num_mk} в {dse['Наименование']} {dse['Номенклатурный_номер']} не определено имя операции")
                return None, None
            if oper['Опер_наименование'] in self.DICT_VAR_OPER:
                count_dse = dse['Количество'] / res[0]['Количество'] * count_izd
                tsht_kol_zayvk = oper['Опер_Тшт_ед'] * count_dse
                if self.DICT_VAR_OPER[oper['Опер_наименование']][0]['kal_pl_podr'] == None:
                    CQT.msgbox(f"По МК№ {s_num_mk} в {dse['Наименование']} {dse['Номенклатурный_номер']} для операции№ {oper['Опер_номер']} "
                               f"{oper['Опер_код']} {oper['Опер_наименование']} не определено подразделение для планирования kal_pl_podr для {self.place.Имя}")
                    return None, None

                list_naryads = ''
                summ_time_fact_naryads = ''
                summ_time_fact_koef_naryads = ''
                summ_count_fact_naryads = ''
                count_nar = 0
                if dse['Номерпп'] in dict_fact:
                    oper_str= '$'.join([oper['Опер_номер'], oper['Опер_наименование']])
                    if oper_str in dict_fact[dse['Номерпп']]:
                        list_naryads = dict_fact[dse['Номерпп']][oper_str]['Наряды']
                        summ_time_fact_naryads = round(dict_fact[dse['Номерпп']][oper_str]['Всего_мин.'],2)
                        summ_count_fact_naryads = dict_fact[dse['Номерпп']][oper_str]['Всего_шт.']
                        summ_time_fact_koef_naryads = copy.deepcopy(summ_time_fact_naryads)
                        count_nar = dict_fact[dse['Номерпп']][oper_str]['Нарядов']

                Тпз_мин = oper['Опер_Тпз']
                kal_pl_podr = self.DICT_VAR_OPER[oper['Опер_наименование']][0]['kal_pl_podr'].split("|")
                for podr_per in kal_pl_podr:
                    podr, per = podr_per.split("%")
                    if podr not in dict_norm:
                        CQT.msgbox(
                            f"По МК№ {s_num_mk}  В бд не соответствует этап {podr} базовому dict_norm")
                        return None, None
                    else:
                        if oper['Опер_код'] not in self.DICT_OP:
                            CQT.msgbox(f"По МК№ {s_num_mk} в {dse['Наименование']} {dse['Номенклатурный_номер']} для операции№ {oper['Опер_номер']} "
                               f"``{oper['Опер_код']} {oper['Опер_наименование']}`` не найдена в справочнике операций для {self.place.Имя}")
                            return None, None
                        kr = self.DICT_OP[oper['Опер_код']]['kr_default']
                        koef_posta = 1
                        if kr == 2:
                            koef_posta = 1 / 0.7
                        time = tsht_kol_zayvk * koef_posta
                        time_paral = (oper['Опер_Тпз'] + time) * F.valm(per) / 100
                        koef_vneplana_tmp = 1
                        estimated_vid_rab_names = [k for k,v in  self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items() if v['estimated'] and v['poki'] == self.place.poki]
                        if podr in estimated_vid_rab_names:
                            koef_vneplana_tmp = koef_vneplana

                        koef_smen = (F.round_up(tsht_kol_zayvk / 480) - 1) * Тпз_мин

                        itog_time = time_paral * koef_vneplana_tmp * koef_pogr_norm + koef_smen
                        summ_time_fact_koef_naryads_tmp= ''
                        if F.is_numeric(summ_time_fact_koef_naryads):
                            summ_time_fact_koef_naryads_tmp = round(summ_time_fact_koef_naryads* koef_posta * F.valm(per) / 100 * koef_vneplana_tmp * koef_pogr_norm,2)
                        if self.place.apply_ratio_on_calc_plan_norm: #27.01.2026 по задаче 100065475
                            dict_norm[podr] += itog_time
                        else:

                            dict_norm[podr] += round(time_paral + koef_smen, 2)
                        mat_znch = 0
                        mat_name = ''
                        link_docs = ''
                        if fl_mat:
                            mat_znch = F.valm(dse['Мат_кд'].split("/")[0])
                            mat_name = dse['Мат_кд']
                            link_docs = dse['Ссылка']
                            fl_mat = False

                        delta_count = dse['Количество']
                        if F.is_numeric(summ_count_fact_naryads):
                            delta_count = dse['Количество']-summ_count_fact_naryads

                        if oper['Опер_профессия_код'] not in self.DICT_PROFESSIONS: #08.09.25
                            nn = f"{dse['Наименование']} {dse['Номенклатурный_номер']}"
                            oper_name = oper['Опер_профессия_наименование']
                            CQT.msgbox(f'МК: {s_num_mk} ДСЕ: {nn}\nНе найдена профессия: {oper_name} в БД МЕС')
                            return None, None
                        tmp_row = {'Позиция': pozition,
                                   'МК': s_num_mk,
                                   'Номерпп': dse['Номерпп'],
                                   'ДСЕ': f"{dse['Наименование']} {dse['Номенклатурный_номер']}",
                                   'Колво_в_узел': dse['Количество'], 'Изделий': count_izd,
                                   'Колво_всего': dse['Количество'], 'Опер_номер': oper['Опер_номер'],
                                   'Опер_имя': oper['Опер_наименование'], 'Мат_кд_знч': mat_znch, 'Мат_кд': mat_name,
                                   'Ссылка': link_docs, 'Этап': oper['Этап'],
                                   'Вид_работ': self.DICT_PROFESSIONS[oper['Опер_профессия_код']]['Вид_работ'], #08.09.25
                                   'КР': kr, 'КОИД': oper['Опер_КОИД'], 'koef_posta': round(koef_posta,2),
                                   'Номер': oper['Опер_номер'], 'Подразд': podr,
                                   'РЦ': oper['Опер_РЦ_код'],
                                   'Тпз_мин': Тпз_мин,
                                   'Тшт_1дет_мин': oper['Опер_Тшт_ед'],
                                   'Тшт*Кол*Заяв_мин': round(tsht_kol_zayvk * F.valm(per) / 100,3),
                                   'Тпз_мин + Тшт*Кол*Заяв_мин': round(Тпз_мин+ tsht_kol_zayvk * F.valm(per) / 100, 3),
                                   'Тшт*Кол*Заяв*k_post_мин_мин': round(time * F.valm(per) / 100,2),
                                   'Закрыто по нарядам': list_naryads, 'Итого по нарядам факт.мин.': summ_time_fact_naryads,
                                   'Итого по нарядам факт.мин.*k_post*k_pl*k_pot': summ_time_fact_koef_naryads_tmp,
                                   'Итого по нарядам факт.шт.': summ_count_fact_naryads,
                                   'Нарядов_шт.':count_nar,
                                   'Профессия': oper['Опер_профессия_наименование'], 'Доля_н': F.valm(per),
                                   '(Тпз+Тшт*Кол*Заяв*k_post)*Доля_нар_мин': round(time_paral,2),
                                   'Коэфф_потерь_для_плана': koef_vneplana_tmp, 'Коэфф_норм_для_плана': koef_pogr_norm,
                                   'Коэфф_смены((Т/480-1)*Тшт)': round(koef_smen,2),
                                   'Итог_мин': round(itog_time,2),
                                   'Не закрыто шт.':delta_count}

                        list_log.append(tmp_row)
                        Тпз_мин = 0
                        list_naryads = ''
                        summ_time_fact_naryads = ''
                        count_nar = ''
    return dict_norm, list_log





@CQT.onerror
def btn_edit_zp_kpl(self: mywindow):
    if 'shift' in CQT.get_key_modifiers(self):
        show_del_zp_kpl(self)
    else:
        add_zp_kpl(self)

@CQT.onerror
def show_del_zp_kpl(self: mywindow):
    tbl = self.ui.tbl_kal_pl
    num_row = tbl.currentRow()
    if num_row == -1:
        return
    row = CQT.get_dict_line_form_tbl(tbl, num_row)
    num_kpl = int(row['plan.Пномер'])

    sootv = CMS.Zp_kpl(self)
    list_sootv = sootv.get_by_kpl(num_kpl)
    list_dict_sootv = F.list_of_lists_to_list_of_dicts(list_sootv)

    def hide_clmn(tbl:QtWidgets.QTableWidget):
        tbl.setStyleSheet(CQT.ERP_CSS)
        if CQT.num_col_by_name_c(tbl, 's_num') != None:
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 's_num'), True)
        if CQT.num_col_by_name_c(tbl,'Ref_Key') != None:
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl,'Ref_Key_зп_абстракт'),True)
        nf_del_mark = CQT.num_col_by_name_c(tbl, 'На удаление')
        for i in range(tbl.rowCount()):
            if tbl.item(i, nf_del_mark).text() == 'X':
                CQT.set_font_color_wtab_c(tbl, i, nf_del_mark, 254, 20, 20)
                CQT.font_cell_size_format(tbl, i, nf_del_mark, bold=True)

    def apply_num_kpl(tbl, tblf:QtWidgets.QTableWidget):
        nf_kpl = CQT.num_col_by_name_c(tblf,'КПЛ')
        tblf.item(0,nf_kpl).setText(str(num_kpl))
        CQT.apply_filtr_c(self,tblf,tbl)
    m = CODAT.OrdersComposit()
    list_refs = list({_['Ref_Key_зп_абстракт'] for _ in list_dict_sootv})
    list_refs_str = ' or '.join([f"(Ref_Key eq guid'{_}')" for  _ in list_refs])
    code, list_data = m.get_response(doc_name='Document_ЗаказПоставщику?$expand=Партнер,Автор',
                                     wet_filtr=f"&$filter= {list_refs_str}"
                                               f"&$select=Ref_Key, Партнер/Description, Date, Статус, "
                                               f"Партнер/Description,Автор/Description, Комментарий, "
                                               f"ДополнительнаяИнформация, ЖелаемаяДатаПоступления, DeletionMark",#
                                     with_cod=True,
                                     dict_aliases={
                                                   "ДополнительнаяИнформация":"Доп. информация",
                                                   "Date":"Дата",
                                                   "DeletionMark":"На удаление",
                                                   "ЖелаемаяДатаПоступления":"Желаемая дата поступления"})
    if code != 200:
        CQT.msgbox(f'Ошибка связи с ЕРП  Document_ЗаказПоставщику код {code}')
        return False

    shabl = {k:'' for k in list_data[0].keys()}
    for item in list_dict_sootv:
        fl_naid = False
        for row_1c in list_data:
            if row_1c['Ref_Key'] == item['Ref_Key_зп_абстракт']:
                for k,v in row_1c.items():
                    if isinstance(v,dict):
                        v = v['Description']
                    item[k] = v

                fl_naid = True
        if not fl_naid:
            for k,v in shabl.items():
                item[k] = v
        item['Дата'] = F.datetostr(F.strtodate(item['Дата'], "%Y-%m-%dT%H:%M:%S"), "%d.%m.%Y %H:%M:%S")
        item["Желаемая дата поступления"] = F.datetostr(
            F.strtodate(item["Желаемая дата поступления"], "%Y-%m-%dT%H:%M:%S"), "%d.%m.%Y")
        if item["На удаление"]:
            item["На удаление"] = 'X'
        else:
            item["На удаление"] = ''
            
    rez = CQT.msgboxg_get_table(self, 'Выбор ЗП для удаления', list_dict_sootv, 'Удалить соответствия ЗП',
                                'Отмена', WindowTitle='Просмотр всех ЗП для КПЛ',
                                selectRows=True, func_oform_tbl=hide_clmn,func_oform_filtr=apply_num_kpl)
    if rez == False:
        return
    msg_list = [_["Номер ЗП"] for _ in rez]
    if not CQT.msgboxgYN(f'Будут удалены соответствия {msg_list}'):
        return
    for item in rez:
        s_num = int(item['s_num'])
        sootv.del_compliance(s_num)
    CQT.msgbox(f'Успешно',time_life=0.5)


@CQT.onerror
def add_zp_kpl(self: mywindow):

    def generate_msg(poz):
        poz.load_kpl_table('пл_оуп')
        proj = poz.dict_tables['пл_оуп']['№проекта']
        py = poz.dict_tables['пл_оуп']['№ERP']
        poz_num = poz.Позиция
        fio_technolog = poz.dict_tables['пл_топ']['Отв_технолог']
        str_fio_technolog = CMS.b24_notation_user_fio(fio_technolog)
        msg = f'{str_fio_technolog}!\nДля закупа материалов по\n{proj} {py} поз. {poz_num} (КПЛ№ {num_kpl})\nнеобходимо указать пл_топ.Предв_спецификация_ЕРП\nв Объемно-календарном планировании'
        return msg
    tbl = self.ui.tbl_kal_pl
    num_row = tbl.currentRow()
    if num_row == -1:
        return
    row = CQT.get_dict_line_form_tbl(tbl,num_row)
    num_kpl = int(row['plan.Пномер'])
    m = CODAT.OrdersComposit()

    code, list_data = m.get_response(doc_name='Document_ЗаказПоставщику?$expand=Партнер,Автор',
                                     wet_filtr=f"&$filter= (Posted eq true or DeletionMark eq true) and Статус ne 'Закрыт'"
                                               f" and Партнер_Key eq guid'{self.place.УИД_ЕРП_Отдел_снабжения}'"
                                               f"&$select=Ref_Key, Партнер/Description, Number, Date, Статус, "
                                               f"Партнер/Description,Автор/Description, Комментарий, "
                                               f"ДополнительнаяИнформация, ЖелаемаяДатаПоступления, DeletionMark",#
                                     with_cod=True,
                                     dict_aliases={'Number':"Номер",
                                                   "ДополнительнаяИнформация":"Доп. информация",
                                                   "Date":"Дата",
                                                   "DeletionMark":"На удаление",
                                                   "ЖелаемаяДатаПоступления":"Желаемая дата поступления"})

    if code != 200:
        CQT.msgbox(f'Ошибка связи с ЕРП  Document_ЗаказПоставщику код {code}')
        return False

    sootv = CMS.Zp_kpl(self)
    list_refs = sootv.get_list_refs(num_kpl)
    list_filtr = []
    for item in list_data:
        item['Партнер'] = item['Партнер']['Description']
        item['Автор'] = item['Автор']['Description']
        item['Дата'] = F.datetostr(F.strtodate(item['Дата'],"%Y-%m-%dT%H:%M:%S"),"%d.%m.%Y %H:%M:%S")
        item["Желаемая дата поступления"] = F.datetostr(F.strtodate(item["Желаемая дата поступления"],"%Y-%m-%dT%H:%M:%S"), "%d.%m.%Y")
        if item["На удаление"]:
            item["На удаление"] = 'X'
        else:
            item["На удаление"] = ''
        if item['Ref_Key'] not in list_refs:
            list_filtr.append(item)
        
        
    def hide_clmn(tbl:QtWidgets.QTableWidget):
        tbl.setStyleSheet(CQT.ERP_CSS)
        num_hide = CQT.num_col_by_name_c(tbl,'Ref_Key')
        if num_hide != None:
            tbl.setColumnHidden(num_hide,True)
        nf_del_mark = CQT.num_col_by_name_c(tbl,'На удаление')
        for i in range(tbl.rowCount()):
            if tbl.item(i,nf_del_mark).text() == 'X':
                CQT.set_font_color_wtab_c(tbl,i,nf_del_mark,254,20,20)
                CQT.font_cell_size_format(tbl,i,nf_del_mark,bold=True)

    rez = CQT.msgboxg_get_table(self,'Выбор ЗП',list_filtr,'Выбрать ЗП','Отмена',
                                WindowTitle='Выбор ЗП для КПЛ',selectRows=True,func_oform_tbl=hide_clmn,sortingEnabled=True)
    if rez == False:
        return
    list_zp_obj = []
    for item in rez:
        num_erp = item['Номер']
        date = F.strtodate(item['Дата'],"%d.%m.%Y %H:%M:%S")
        Ref_Key = item['Ref_Key']
        zp_obj = CMS.Zakaz_postavshiky.add_new_zp(Ref_Key, num_erp,date)
        list_zp_obj.append(zp_obj)


    sootv.add_compliance(num_kpl,list_zp_obj)
    if len(list_zp_obj):
        poz = CMS.Pozition(num_kpl, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
        poz.load_kpl_table('пл_топ')
        if not poz.dict_tables['пл_топ']['Предв_спецификация_ЕРП'].strip():
            msg = generate_msg(poz)
            result = CB24.B24Sender().send_msg_by_chat_id('chat48346', msg)
            if not result:
                CQT.msgbox('Ошибка отправки сообщения в б24')
        CQT.msgbox(f'Успешно',time_life=0.5)
    return





@CQT.onerror
def btn_norm_fact_by_opers(self: mywindow):
    def calc_top(self, dict_norm, data_top):
        # t(в часах)=колво ДСЕ*0,4+2
        dict_norm['пл_топ.Нчас_ТД'] = (data_top['Число_ДСЕ'] * 0.4 + 2) * 60
        return dict_norm
    list_log = False
    tbl = self.ui.tbl_kal_pl
    t = CQT.TableContext(tbl)
    cur_row = t.current_row()
    if cur_row.no_selection:
        CQT.msgbox(f'Не выбрана позиция')
        return
    p_nom = cur_row.value('plan.Пномер')
    poz = CMS.Pozition(p_nom, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
    poz.load_kpl_table('пл_топ')
    poz.load_kpl_table('пл_оуп')
    vid_po_napr = poz.dict_tables['пл_топ']['Вид']
    num_napr_deyat = poz.Направление_деятельности
    napr_deyat = self.Data_plan.DICT_NAPR_DEYAT[num_napr_deyat]['Имя']
    try:
        koef_vneplana, koef_pogr_norm = CMS.calc_koefs_pogr(self.Data_plan.DICT_VID_PO_NAPR,
                                                            self.Data_plan.DICT_NAPRAVLENIE,
                                                            self.Data_plan.DICT_NAPR_DEYAT_NAME, vid_po_napr, napr_deyat)
    except:
        CQT.msgbox(f'Не корректно занесен направление')
        return

    list_mk = CSQ.custom_request_c(self.bd_naryad, f"""SELECT Пномер,Количество,Дата_завершения,Вес,Тип FROM mk WHERE 
        НомКплан == {poz.Пномер} AND На_удал == 0;""", rez_dict=True)

    if len(list_mk) == 0:
        CQT.msgbox(f'Не найдены МК')
        return

    dict_norm = generate_dict_norm(self)
    nk_pnom = CQT.num_col_by_name_c(tbl, 'plan.Пномер')

    nk_stat_norm = CQT.num_col_by_name_c(tbl, 'plan.Статус_норм')
    if nk_stat_norm == None:
        CQT.msgbox(f'Отсутствует поле plan.Статус_норм')
        return

    dict_norm = calc_top(self, dict_norm, poz.dict_tables['пл_топ'])




    aliases = {
    'Пномер' : 'Пномер',
    'Количество' : 'Количество изделий',
    'Дата_завершения' : 'Дата завершения',
    'Вес' : 'Вес',
    'Тип' : 'Тип'
    }
    template = []
    if len(list_mk)>1:
        def calc_type_mk_name(num:int)->str :
            for name, dict_data in self.DICT_TIP_MK.items():
                if dict_data['Пномер']==num:
                    return name
            return  f'Не найден в БД'
        for it in list_mk:
            template.append({   '':CEMOJ.ДокументыДанные.document,
                                'Пномер' : it['Пномер'],
                                'Количество' : it['Количество'],
                                'Дата_завершения' : it['Дата_завершения'],
                                'Вес' : it['Вес'],
                                'Тип' : calc_type_mk_name(it['Тип'])
            }
            )
        rez = CQT.msgboxg_get_table(DTCLS.app_self,'МК для просмотра',template,
                                    'Выбор',styleSheet=CQT.MES_CSS,aliases_header =aliases,selectRows=True,
                                    selection_from_tbl=True)
        if not rez:
            return
        mk_item = [_ for _ in list_mk if str(_['Пномер']) == rez[0]['Пномер']][0]
    else:
        mk_item = list_mk[0]
    show_mk_norm_fact_by_opers(mk_item,koef_vneplana,koef_pogr_norm,dict_norm)

def show_mk_norm_fact_by_opers(mk_item,koef_vneplana,koef_pogr_norm,dict_norm):
    tmp_log = []
    list_log = []
    def tmp_log_calc(res, tmp_log):
        for dse in res:
            for oper in dse['Операции']:
                pass
                kal_pl_podr = DTCLS.app_self.DICT_VAR_OPER[oper['Опер_наименование']][0]['kal_pl_podr'].split("|")
                tpz = oper['Опер_Тпз']
                tsht = oper['Опер_Тшт_ед']
                for podr_per in kal_pl_podr:
                    podr, per = podr_per.split("%")
                    if 'пл_сб' in podr:
                        tsht_per = round(oper['Опер_Тшт'] * int(per) / 100, 3)
                        tmp_log.append({"МК": mk,
                                        "dse": f"{dse['Наименование']} {dse['Номенклатурный_номер']}",
                                        "кол_во_заказ_по_структуре": dse['кол_во_инф']['кол_во_заказ_по_структуре'],
                                        "Опер_Тпз": tpz,
                                        "Опер_Тшт": tsht_per,
                                        "Опер_Тшт_ед": tsht,
                                        "Опер_Тпз+Опер_Тшт*N": tsht_per + tpz
                                        })
                    tpz = 0
                    tsht = 0
        return tmp_log

    mk = mk_item['Пномер']
    count_izd = mk_item['Количество']
    res = CMS.load_res(int(mk))
    # count_izd = poz.dict_tables['пл_оуп']['Количество']
    tmp_log = tmp_log_calc(res, tmp_log)

    koef_vneplana_tmp = copy.deepcopy(koef_vneplana)  # 19.08.2025 Задача № 100058908
    if mk_item['Тип'] in (2, 3, 5):
        if koef_vneplana_tmp > 1.27:
            koef_vneplana_tmp = 1.27

    ves, ves_res_list = DTCLS.app_self.raschet_vesa_dse(res, False)
    if ves != mk_item['Вес']:
        CSQ.custom_request_c(DTCLS.bd_naryad, f"""UPDATE mk SET Вес = {ves} WHERE Пномер = {int(mk)};""")
        CQT.msgbox(f'В МК {mk} обновлен вес, было {mk_item["Вес"]} кг., стало {ves} кг.')
    if count_izd == None or count_izd == '' or not F.is_numeric(count_izd):
        CQT.msgbox(f'{"пл_оуп.Количество"} не число')
    dict_norm, list_log = dict_norm_from_res(DTCLS.app_self, res, dict_norm, koef_vneplana_tmp, koef_pogr_norm, count_izd,
                                             list_log, mk)
    if list_log:
        CQT.msgboxg_get_table(DTCLS.app_self, 'Расчет веса для сравнения', list_log,
                              'OK', disable_btn1=True, load_summ=True, WindowTitle=f'МК {mk}')

@CQT.onerror
def btn_pl_load_norm(self: mywindow):
    if 'shift' in CQT.get_key_modifiers(self):
        btn_norm_fact_by_opers(self)
        return
    # group_vid_rab_for_plan average_efficiency это МИНУТ НА 1 КГ.


    def fill_norm_db(self, dict_norm, pnom, dict_form_db, row_time_add_etap):
        list_change = []
        for key in dict_norm:
            norma = round(dict_norm[key] / 60, 2)
            tbl, field = key.split('.')
            if tbl == 'plan':
                ind_field = 'Пномер'
            else:
                ind_field = 'НомПл'
            fl_fill = True
            old_time = 0.0
            if key in dict_form_db:
                old_time = dict_form_db[key]
                if norma == dict_form_db[key]:
                    fl_fill = False
            if key in row_time_add_etap:
                old_time = row_time_add_etap[key]
                if norma == row_time_add_etap[key]:
                    fl_fill = False
            if old_time == norma and norma == 0.0: #28.07.25 по задаче 100057452
                fl_fill = False
            if fl_fill:
                CSQ.custom_request_c(self.db_kplan,
                                     f"""UPDATE {tbl} SET {field} = {norma} WHERE {ind_field} = {pnom} """)
                list_change.append({'Этап' : field, 'Было' :str(round(old_time, 2)), 'Cтало': str(round(norma, 2))})
                    #f'{field} было {str(round(old_time, 2))}, '
                    #f'cтало  {str(round(norma, 2))}'])
        return list_change

    def calc_norm_by_weight(dict_norm, ves):
        for item_etap, data_etap in self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items():
            if item_etap in dict_norm and data_etap['poki'] == CFG.Config.place.poki:
                dict_norm[item_etap] += round(
                    F.valm(data_etap['average_efficiency']) * 1.32 * ves, 6)
        return dict_norm

    def load_norm_vo(self, pnom: int, dict_norm: dict):
        item = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM пл_топ WHERE НомПл == {pnom}""", one=True,
                                    rez_dict=True)
        if item['Уд_вес_ВО'] == '' or item['Уд_вес_ВО'] == 0:
            CQT.msgbox(f'Не указан Уд_вес_ВО')
            return
        ves = F.valm(item['Уд_вес_ВО'])
        if item['Вид'] == 1:
            CQT.msgbox(f'Не выбран Вид изделия')
            return
        if item['Вид'] not in self.Data_plan.DICT_VID_PO_NAPR:
            CQT.msgbox(f'Вид изделия не найден в базе')
            return

        if self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]['Выборка'] <= 3:
            CQT.msgbox(f'Выборка слишком мала, используем 121 кг/п/см.')
            dict_norm = calc_norm_by_weight(dict_norm,ves)
            return dict_norm

        CQT.msgbox(f"Принято для расчета {self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]['Имя']} "
                   f" {self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]['кг_на_пост_см']}"
                   f" кг/пост/смену (выборка {self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]['Выборка']} изд.)"
                   f"koef_vneplana {koef_vneplana}, "
                   f"koef_pogr_norm {koef_pogr_norm}")

        for etap_name in self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]:
            for item_sootv in self.Data_plan.LIST_GROUP_VID_RAB_FOR_PLAN_VS_ETAP:
                if item_sootv['pep_notation'] == etap_name:
                    kpl_etap = item_sootv['group_vid_rab']
                    koef = item_sootv['koef']
                    if kpl_etap in self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN:
                        if kpl_etap in dict_norm and etap_name in self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]:
                            dict_norm[kpl_etap] += \
                            round(F.valm(self.Data_plan.DICT_VID_PO_NAPR[item['Вид']][etap_name]) *
                                  koef_vneplana * ves  *koef / 100, 6)
        return dict_norm

    def calc_by_tkp(resp, poz, dict_norm, koef_vneplana, koef_pogr_norm, pnom, nk_stat_norm):
        res = CMS.load_res(resp, self=self, tkp=True)
        count_izd = poz.dict_tables['пл_оуп']['Количество']
        if count_izd == None or count_izd == '' or not F.is_numeric(count_izd):
            CQT.msgbox(f'{"пл_оуп.Количество"} не число')

        dict_norm, list_opers = dict_norm_from_res(self, res, dict_norm, koef_vneplana, koef_pogr_norm, count_izd)
        if dict_norm == None:
            return None,None
        return dict_norm, list_opers

    def calc_by_weight(self, ves, dict_norm, nk_stat_norm):
        calc_norm_by_weight(dict_norm,ves)
        if dict_norm == None:
            return
        return dict_norm


    def calc_by_vo(self, pnom, dict_norm, nk_stat_norm):
        # ==============ПО ВО===================
        dict_norm = load_norm_vo(self, pnom, dict_norm)
        if dict_norm == None:
            return

        return dict_norm

    def calc_top(self, dict_norm, data_top):
        # t(в часах)=колво ДСЕ*0,4+2
        dict_norm['пл_топ.Нчас_ТД'] = (data_top['Число_ДСЕ'] * 0.4 + 2) * 60
        return dict_norm

    @CQT.onerror
    def tmp_log_calc(res,tmp_log):
        for dse in res:
            for oper in dse['Операции']:
                pass
                kal_pl_podr = self.DICT_VAR_OPER[oper['Опер_наименование']][0]['kal_pl_podr'].split("|")
                tpz = oper['Опер_Тпз']
                tsht = oper['Опер_Тшт_ед']
                for podr_per in kal_pl_podr:
                    podr, per = podr_per.split("%")
                    if 'пл_сб' in podr:
                        tsht_per = round(oper['Опер_Тшт']*int(per)/100,3)
                        tmp_log.append({"МК": mk,
                            "dse":f"{dse['Наименование']} {dse['Номенклатурный_номер']}",
                            "кол_во_заказ_по_структуре":dse['кол_во_инф']['кол_во_заказ_по_структуре'],
                                        "Опер_Тпз":tpz,
                                        "Опер_Тшт": tsht_per,
                                        "Опер_Тшт_ед": tsht,
                                        "Опер_Тпз+Опер_Тшт*N": tsht_per+tpz
                                        })
                    tpz = 0
                    tsht = 0
        return tmp_log

    list_log = False
    tbl = self.ui.tbl_kal_pl
    if tbl.currentRow() == -1:
        CQT.msgbox(f'Не выбрана позиция')
        return
    row = CQT.get_dict_line_form_tbl(tbl)
    p_nom = row['plan.Пномер']
    poz = CMS.Pozition(p_nom, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
    poz.load_kpl_table('пл_топ')
    poz.load_kpl_table('пл_оуп')
    vid_po_napr = poz.dict_tables['пл_топ']['Вид']
    ud_ves_vo = poz.dict_tables['пл_топ']['Уд_вес_ВО']
    count_izd = poz.dict_tables['пл_оуп']['Количество']
    if count_izd == None or count_izd == '' or not F.is_numeric(count_izd):
        CQT.msgbox(f'{"пл_оуп.Количество"} не число')
        return
    nk_napr = CQT.num_col_by_name_c(tbl, 'plan.Направление_деятельности')
    if nk_napr == None:
        CQT.msgbox(f'Отсутствует поле plan.Направление_деятельности')
        return
    napr_deyat = tbl.item(tbl.currentRow(), nk_napr).text()

    try:
        koef_vneplana, koef_pogr_norm = CMS.calc_koefs_pogr(self.Data_plan.DICT_VID_PO_NAPR,
                                                            self.Data_plan.DICT_NAPRAVLENIE,
                                                            self.Data_plan.DICT_NAPR_DEYAT_NAME, vid_po_napr, napr_deyat)
    except:
        CQT.msgbox(f'Не корректно занесен направление')
        return

    list_mk = CSQ.custom_request_c(self.bd_naryad, f"""SELECT Пномер,Количество,Дата_завершения,Вес,Тип FROM mk WHERE 
    НомКплан == {poz.Пномер} AND На_удал == 0;""", rez_dict=True)
    descr_predv_res = poz.dict_tables['пл_топ']['Предв_спецификация_ЕРП'].strip() #00-065171

    DICT_NAMES_ETAP_FROM_ERP = dict()
    for k, it in self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN.items():
        if 'etap_name_from_erp_1c' in  it and it['etap_name_from_erp_1c']:
            for et in it['etap_name_from_erp_1c'].split(';'):
                DICT_NAMES_ETAP_FROM_ERP[et] = k

    dict_norm = generate_dict_norm(self)
    nk_pnom = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
    pnom = int(tbl.item(tbl.currentRow(), nk_pnom).text())
    nk_stat_norm = CQT.num_col_by_name_c(tbl, 'plan.Статус_норм')
    if nk_stat_norm == None:
        CQT.msgbox(f'Отсутствует поле plan.Статус_норм')
        return

    dict_norm = calc_top(self, dict_norm, poz.dict_tables['пл_топ'])

    def calc_prefix_tkpa(name_predv_res: str) -> int | None:
        if name_predv_res.startswith('ТКПА_'):
            list_name_predv_res = name_predv_res.split('_')
            if len(list_name_predv_res) > 1 and F.is_numeric(list_name_predv_res[1]):
                s_num_tkp = list_name_predv_res[1]
                return int(s_num_tkp)

    emo_off = CEMOJ.СтатусыПроизводства.stopped.symbol
    emo_on = CEMOJ.СтатусыПроизводства.normal.symbol




    def set_val_into_summary_info(sort:str,field:str,val):
        for item in summary_info:
            if item['Вид расчета'] == sort:
                item[field] = val

    def calc_code_name_predv_res(descr_predv_res)->tuple[str|None,str|None]:
        def is_name_predv_res_as_code(descr_predv_res):
            return descr_predv_res.startswith('00-')


        code_predv_res = None
        name_predv_res = None
        if not is_name_predv_res_as_code(descr_predv_res):
            name_predv_res = descr_predv_res
            s_num_tkp = calc_prefix_tkpa(descr_predv_res)
            postfix = ")"
            if s_num_tkp:
                postfix = f' ИЛИ РесурсныеСпецификации.Наименование ПОДОБНО "ТКПА_{s_num_tkp}%")'
            wet_req_text = f"""ВЫБРАТЬ  РесурсныеСпецификации.Код КАК Код,
                                                    РесурсныеСпецификации.Наименование КАК Наименование
                                            ИЗ
                                                Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                                            ГДЕ
                                                 РесурсныеСпецификации.ЭтоГруппа = ЛОЖЬ
                                                И (РесурсныеСпецификации.Наименование = "{descr_predv_res}"{postfix}
                                            """
            res_get_wet = APIERP.get_wet_request_result(wet_req_text,
                                                        msg_err=f'Не найдена ресурсная с названием "{descr_predv_res}"')
            if res_get_wet is not None:
                code_predv_res = res_get_wet[0]['Код'].strip()
                name_predv_res = res_get_wet[0]['Наименование'].strip()
                CSQ.custom_request_c(self.db_kplan,
                                     f'''UPDATE пл_топ SET Предв_спецификация_ЕРП = "{code_predv_res}" WHERE НомПл == {pnom};''')

        else:
            code_predv_res = descr_predv_res
            wet_req_text = f"""ВЫБРАТЬ
                                                                    РесурсныеСпецификации.Наименование КАК Наименование
                                                                ИЗ
                                                                    Справочник.РесурсныеСпецификации КАК РесурсныеСпецификации
                                                                ГДЕ
                                                                     РесурсныеСпецификации.ЭтоГруппа = ЛОЖЬ
                                                                    И РесурсныеСпецификации.Код = "{code_predv_res}"
                                                                """
            key, data_rez = APIERP.get_wet_request(wet_req_text)
            if key != 200:
                CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
                return code_predv_res,name_predv_res

            if data_rez['data']:
                name_predv_res = data_rez['data'][0]['Наименование']

        return code_predv_res, name_predv_res

    def calc_res_data(name_predv_res) -> bool | None | list:
        s_num_tkp = calc_prefix_tkpa(name_predv_res)

        if s_num_tkp:
            resp = CSQ.custom_request_c(self.db_resxml,
                                        f"""SELECT data FROM predv_res WHERE Имя LIKE "ТКПА_{s_num_tkp}%";""")
        else:
            resp = CSQ.custom_request_c(self.db_resxml, f"""SELECT data FROM predv_res WHERE Имя = ?;""",
                                        list_of_lists_c=(name_predv_res,))
        return resp

    @CQT.onerror
    def calc_res_data_1c(code_predv_res,err_view = False):
        wet_req_text = f"""ВЫБРАТЬ
                                РесурсныеСпецификацииТрудозатраты.Количество КАК Количество,
                                РесурсныеСпецификацииТрудозатраты.Этап.Наименование КАК ЭтапНаименование,
                                РесурсныеСпецификацииТрудозатраты.Ссылка.ОсновноеИзделиеНоменклатура.Наименование КАК ОсновноеИзделиеНоменклатураНаименование,
                                РесурсныеСпецификацииТрудозатраты.Ссылка.Код КАК Код
                            ИЗ
                                Справочник.РесурсныеСпецификации.Трудозатраты КАК РесурсныеСпецификацииТрудозатраты
                            ГДЕ
                                РесурсныеСпецификацииТрудозатраты.Ссылка.Код = "{code_predv_res}";"""
        key, data_rez = APIERP.get_wet_request(wet_req_text)
        if key != 200:
            if err_view:
                CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
            return
        if not data_rez['data']:
            if err_view:
                CQT.msgbox(f'ТЧ в ресурсной {name_predv_res} пустая')
            return
        return data_rez

    summary_info = [
        {'':emo_off,'Вид расчета':'По МК',       'Основа':'','Новый статус':''},
        {'':emo_off,'Вид расчета':'Ресурсная 1С','Основа':'','Новый статус':''},
        {'':emo_off,'Вид расчета':'ТКПА',        'Основа':'','Новый статус':''},
        {'':emo_off,'Вид расчета':'По виду',     'Основа':'','Новый статус':''},
        {'':emo_on, 'Вид расчета':'По весу',     'Основа':'','Новый статус':''},
    ]

    if len(list_mk):
        set_val_into_summary_info('По МК','',emo_on)
        set_val_into_summary_info('По МК','Основа',f'{len(list_mk)} шт. МК')
        set_val_into_summary_info('По МК','Новый статус',2)

    if descr_predv_res:
        code_predv_res, name_predv_res = calc_code_name_predv_res(descr_predv_res)
        # нормы Предв_спецификация_ЕРП по MES
        resp = calc_res_data(name_predv_res)
        if resp != False and resp != None and len(resp) == 2:
            set_val_into_summary_info('ТКПА','',emo_on)
            set_val_into_summary_info('ТКПА','Основа',descr_predv_res)
            set_val_into_summary_info('ТКПА','Новый статус',3)

        data_rez = calc_res_data_1c(code_predv_res) # нормы Предв_спецификация_ЕРП по 1C
        if data_rez:
            set_val_into_summary_info('Ресурсная 1С', '', emo_on)
            set_val_into_summary_info('Ресурсная 1С', 'Основа', code_predv_res)
            set_val_into_summary_info('Ресурсная 1С', 'Новый статус', 3)

    if True:# нормы по ВО
        ves = 0
        fl_on = True
        if ud_ves_vo == '' or ud_ves_vo == 0:
            set_val_into_summary_info('По виду', 'Основа', f'Не указан Уд_вес_ВО')
            fl_on = False
        else:
            ves = F.valm(ud_ves_vo)
            if vid_po_napr == 1:
                set_val_into_summary_info('По виду', 'Основа', f'Не выбран Вид изделия')
                fl_on = False
            if vid_po_napr not in self.Data_plan.DICT_VID_PO_NAPR:
                set_val_into_summary_info('По виду', 'Основа', f'Вид изделия не найден в базе')
                fl_on = False

        if fl_on:
            set_val_into_summary_info('По виду', '', emo_on)
            set_val_into_summary_info('По виду', 'Основа', f'{ves} кг. ({vid_po_napr})')
            set_val_into_summary_info('По виду', 'Новый статус', 1)

    if True:  # нормы по весу
        ves = 0
        fl_on = True
        if ud_ves_vo == '' or ud_ves_vo == 0:
            set_val_into_summary_info('По виду', 'Основа', f'Не указан Уд_вес_ВО')
            fl_on = False
        else:
            ves = F.valm(ud_ves_vo)
        if fl_on:
            set_val_into_summary_info('По весу', '', emo_on)
            set_val_into_summary_info('По весу', 'Основа', f'{ves} кг.')
            set_val_into_summary_info('По весу', 'Новый статус', 1)

    @CQT.onerror
    def fnc_oform(tbl:CQT.QtWidgets.QTableWidget,parent_self:mywindow):
        nf = CQT.nums_col_by_name_dict(tbl)
        DICT_STATUS_NORM = parent_self.Data_plan.DICT_STATUS_NORM
        def fnc_set_val(self,val,i,j):
            val_str = val if val else ''
            tbl.item(i,j).setText(str(val_str))

        for i in range(tbl.rowCount()):
            CQT.add_combobox(self, tbl, i, nf['Новый статус'], [_['Имя'] for _ in DICT_STATUS_NORM.values()], True,
                             list_data=[_ for _ in DICT_STATUS_NORM.keys()], return_data=True, conn_func=fnc_set_val)
            state = tbl.item(i,nf['Новый статус']).text()

            if F.is_numeric(state):
                state = F.valm(state)
                state_name = DICT_STATUS_NORM[state]['Имя']
                cmb:CQT.QtWidgets.QComboBox = tbl.cellWidget(i,nf['Новый статус'])
                cmb.setCurrentText(state_name)


            enable = tbl.item(i,nf['']).text()
            if enable == emo_off:
                CQT.setRowDisabled(tbl,i)

    @CQT.onerror
    def fnc_check_select(btn, dialog, t, p):
        if btn.text() == 'Рассчитать':
            row = CQT.get_dict_line_form_tbl(t)
            if not  row:
                CQT.msgbox(f'Не выбран метод расчета')
                return
            if row[''] == emo_off:
                CQT.msgbox(f'Недоступно')
                return
            dialog.accept()
        else:
            dialog.reject()


    result = CQT.msgboxg_get_table(self,'Выбор метода расчета',summary_info,'Рассчитать',show_filtr=False,
                          func_oform_tbl=fnc_oform,selectRows=True,styleSheet=CQT.MES_CSS,parent_self=self,
                                   func_btn0=fnc_check_select,not_standart_close=True)
    if not result:
        return
    result = result[0]

    list_err = []

    if result['Вид расчета'] == 'По МК':
        tmp_log = []
        list_log = []
        for mk_item in list_mk:
            mk = mk_item['Пномер']
            count_izd = mk_item['Количество']
            res = CMS.load_res(int(mk))
            # count_izd = poz.dict_tables['пл_оуп']['Количество']

            tmp_log = tmp_log_calc(res, tmp_log)

            koef_vneplana_tmp = copy.deepcopy(koef_vneplana)  # 19.08.2025 Задача № 100058908
            if mk_item['Тип'] in (2, 3, 5):
                if koef_vneplana_tmp > 1.27:
                    koef_vneplana_tmp = 1.27

            ves, ves_res_list = self.raschet_vesa_dse(res, False)
            if ves != mk_item['Вес']:
                CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Вес = {ves} WHERE Пномер = {int(mk)};""")
                CQT.msgbox(f'В МК {mk} обновлен вес, было {mk_item["Вес"]} кг., стало {ves} кг.')
            if count_izd == None or count_izd == '' or not F.is_numeric(count_izd):
                CQT.msgbox(f'{"пл_оуп.Количество"} не число')
            dict_norm, list_log = dict_norm_from_res(self, res, dict_norm, koef_vneplana_tmp, koef_pogr_norm, count_izd,
                                                     list_log, mk)
        #CQT.msgboxg_get_table(self, 'Расчет веса для TEST', tmp_log, 'OK', disable_btn1=True, load_summ=True)


    elif result['Вид расчета'] == 'ТКПА':
        dict_norm, list_log = calc_by_tkp(resp, poz, dict_norm, koef_vneplana, koef_pogr_norm, pnom,
                                          nk_stat_norm)
    elif result['Вид расчета'] == 'Ресурсная 1С':
        for et in data_rez['data']:
            if et['ЭтапНаименование'] in DICT_NAMES_ETAP_FROM_ERP:
                name_gr = DICT_NAMES_ETAP_FROM_ERP[et['ЭтапНаименование']]
                if name_gr in dict_norm:
                    dict_norm[name_gr] += et['Количество']*count_izd
            else:
                list_err.append({'Ошибка':f"Этап 1c `{et['ЭтапНаименование']}` не имеет соответствия в настройках МЕС. Норма не учтена"})
    elif result['Вид расчета'] == 'По виду':
        dict_norm = calc_by_vo(self, pnom, dict_norm, nk_stat_norm)
    else:#result['Вид расчета'] == 'По весу':
        dict_norm = calc_by_weight(self,ves,dict_norm,nk_stat_norm)


    for compose in self.Data_plan.DICT_COMPOSITE_PODRAZD.values():
        name_compose = f"{compose['name']}.{compose['main_comp_field_name']}"
        summ_compose = 0
        for inp_field in compose['dict_input_fields'].keys():
            name_inp_field = f"{compose['name']}.{inp_field}"
            summ_compose += dict_norm[name_inp_field]
        dict_norm[name_compose] = round(summ_compose, 2)

    if list_err:
        CQT.msgboxg_get_table_ok_inf(self,f'Ошибки расчета',list_err)

    list_change = fill_norm_db(self, dict_norm, pnom, poz.row_time_etap, poz.row_time_add_etap)

    for field in dict_norm:
        nk_field = CQT.num_col_by_name_c(tbl, field)
        if nk_field != None:
            tbl.item(tbl.currentRow(), nk_field).setText(str(round(dict_norm[field] / 60, 2)))

    if list_change:
        update_local_graf( update=True, pnom=pnom,fill_gant=not is_local_gant_hidden(self))
        obj_msg = CMS.Msg_b24(self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, pnom)
        obj_msg.send_msg('recalc_dates_disp', tbl = list_change)
        CQT.msgboxg_get_table_ok_inf(self, 'Успешно пересчитано', list_change, show_filtr=False,
                                     WindowTitle=f'Изменения пересчета КПЛ {pnom}')
    else:
        CQT.msgbox('Изменений норм нет.')

    # ====================state===================
    def set_state(state: int,poz:CMS.Pozition|None=None):
        fl = True
        if poz:
            if poz.Статус_норм == state:
                fl = False
        if fl:
            CSQ.custom_request_c(self.db_kplan, f"""UPDATE plan SET Статус_норм = {state} WHERE Пномер = {pnom} """)
            if nk_stat_norm:
                tbl.item(tbl.currentRow(), nk_stat_norm).setText(self.Data_plan.DICT_STATUS_NORM[state]['Имя'])

    state = result['Новый статус']
    if not state == '':
        set_state(int(state),poz)
    # =====================================

    CMS.Pozition.set_flag_recalc_dates(self.db_kplan, pnom, 1)

    if CQT.num_col_by_name_c(tbl, 'plan.Потребность_пересч_сроков') != None:
        CQT.set_val_tbl_by_name(self.ui.tbl_kal_pl, self.ui.tbl_kal_pl.currentRow(), 'plan.Потребность_пересч_сроков',
                                '1')

    CQT.select_range(tbl, tbl.currentRow(), tbl.currentColumn())
    tbl.setFocus()
    oforml_row_plan_tbl(CQT.TableContext(tbl).current_row())
    if list_log:
        if CQT.msgboxgYN(f'Показать таблицу норм пооперационно?'):
            CQT.msgboxg_get_table(self, 'Расчет веса для сравнения', list_log, 'OK', disable_btn1=True, load_summ=True)


def get_zc_data_from_ERP(self,Ref_Key_py,nomen_name,m=None):
    is_order_sb = False
    if not m:
        m = CODAT.OrdersComposit(self.USER_CONFIG.ERP_base_name['Значение'])

    data_py = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                             wet_filtr=f"?$filter=Ref_Key eq guid'{Ref_Key_py}' &$select=ДокументОснование,ДокументОснование_Type")


    if data_py[0]['ДокументОснование_Type'] not in (
    'StandardODATA.Document_ЗаказКлиента', 'StandardODATA.Document_ЗаказНаСборку',
    'StandardODATA.Document_ЗаказНаВнутреннееПотребление'):
        CQT.msgbox(f"Основание для {self.place.doc_prefix}:\n{data_py['ДокументОснование_Type']}.\n Нужен Заказ клиента/Заказ на сборку")
        return
    client_order = data_py[0]['ДокументОснование']
    nomen_ref = None
    if data_py[0]['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказНаСборку':
        sb_order = data_py[0]['ДокументОснование']
        data_sb = m.get_response(doc_name=f"Document_ЗаказНаСборку(guid'{sb_order}')",
                                 wet_filtr=f"?$select=ДокументОснование_Key,Номенклатура_Key")
        client_order = data_sb['ДокументОснование_Key']
        is_order_sb = True
        nomen_ref = data_sb['Номенклатура_Key']

    else:
        nomen_ref = m.get_response(doc_name='Catalog_Номенклатура',
                                   wet_filtr=f"""?$filter=Description eq '{nomen_name}'&$select= Ref_Key""")
        if len(nomen_ref) == 0:
            CQT.msgbox(f'Номенклатура\n{nomen_name}\nНе обнаружена в ЕРП!')
            return
        nomen_ref = nomen_ref[0]['Ref_Key']


    if data_py[0]['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказНаВнутреннееПотребление':
        data_co_wet = m.get_response(doc_name=f"Document_ЗаказНаВнутреннееПотребление(guid'{client_order}')",
                                 wet_filtr=f"?$select=ДатаОтгрузки,НеОтгружатьЧастями,"
                                           f"Товары", get_response_val=False)
        data_co = data_co_wet
        data_co['doc_name'] = 'ЗаказНаВнутреннееПотребление'
    else:
        data_co_wet = m.get_response(doc_name='Document_ЗаказКлиента',
                                 wet_filtr=f"?$filter=Ref_Key eq guid'{client_order}' &$select=ДатаОтгрузки,НеОтгружатьЧастями,"
                                           f"Товары,ЭтапыГрафикаОплаты", get_response_val=False)
        data_co = data_co_wet['value'][0]
        data_co['doc_name'] = 'ЗаказКлиента'
    meta_co = data_co_wet['odata.metadata']
    return m, nomen_ref, data_py, data_co,meta_co,client_order,is_order_sb

@CQT.onerror
def select_exel_file(self:mywindow,*args):
    dir = CMS.load_tmp_path('exel_file_poz_for_erp')
    file_path = CQT.f_dialog_name(self,'Выбрать Эксель',dir,'*.xlsx')
    CMS.save_tmp_path('exel_file_poz_for_erp',file_path,True)
    data = CEX.read_file(file_path,'PLANVSE',4)
    tbl = self.ui.tbl_poz_from_exel
    CQT.fill_wtabl(data,tbl,height_row=24,auto_type=False,selectionBehavior='SelectRows')



@CQT.onerror
def pl_send_dates_into_ERP_from_exel(self:mywindow,*args):
    self.ui.btn_pl_send_dates_into_ERP.setEnabled(False)
    self.ui.tab_addit_info_poz_gant.blockSignals(True)
    self.ui.tab_addit_info_poz_gant.setCurrentIndex(0)
    self.ui.tab_addit_info_poz_gant.blockSignals(False)
    if self.ui.fr_poz_from_exel.isHidden():
        self.ui.fr_poz_from_exel.setHidden(False)
        self.ui.fr_gant_local_tbl.setHidden(True)
    else:
        self.ui.fr_poz_from_exel.setHidden(True)
        self.ui.fr_gant_local_tbl.setHidden(False)


@CQT.onerror
def send_into_ERP(self:mywindow):
    tab = self.ui.tab_addit_info_poz_gant
    ind = tab.currentIndex()
    if tab.tabText(ind) == 'Этапы':
        if self.glob_dict_etaps_from_erp == None:
            return
        line = CQT.get_dict_line_form_tbl(self.ui.tbl_kal_pl)
        if line== {}:
            return
        kpl_num = int(line['plan.Пномер'])
        znpr_num = CSQ.custom_request_c(self.db_kplan,f'''SELECT s_num FROM знпр INNER JOIN пл_оуп 
                ON знпр.s_num == пл_оуп.Пномер_ЗП WHERE пл_оуп.НомПл = {kpl_num};''',one_column=True,one=True,hat_c=False)
        rez = CMS.update_data_etaps_from_erp(self.db_kplan,self.glob_dict_etaps_from_erp,znpr_num) #11.11.25
        if rez:
            CQT.msgbox(f'Удачно',time_life=0.5)
            tab.setCurrentIndex(0)
        else:
            CQT.msgbox(f'Не выполнено!')

        return

    if tab.tabText(ind) == 'ЗК':
        send_date_kompl_into_ERP(self)
@CQT.onerror
def send_date_kompl_into_ERP(self:mywindow):
    exel_mode = False
    if not self.ui.fr_poz_from_exel.isHidden():
        exel_mode=True

    if self.glob_plan_addit_info_poz_gant_old_date == None:
        CQT.msgbox(f'Дата отгрузки `{self.glob_plan_addit_info_poz_gant_old_date}` не соотнесена с текущей позицией, ошибка разбора документа.\nНужно прогрузить вкладку ЗК')
        return


    m = CODAT.OrdersComposit(self.USER_CONFIG.ERP_base_name['Значение'])

    Ref_Key_py, nomen_poz, poz = GPL.get_ref_and_nomen_from_tbl_poz(self, m, exel_mode)

    m, nomen_ref, data_py, data_co, meta_co,client_order, is_order_sb = get_zc_data_from_ERP(self,Ref_Key_py,nomen_poz,m)

    parts = data_co['НеОтгружатьЧастями']
    postfix = ''
    if parts == True:
        if exel_mode:
            max_date = F.strtodate("1999-01-01")
            line = CQT.get_dict_line_form_tbl(self.ui.tbl_poz_from_exel)
            current_part_zp = line['номер\nкэ в 1С']
            current_part_zk = line['ЗК']
            list_from_tbl = CQT.list_from_wtabl_c(self.ui.tbl_poz_from_exel,rez_dict=True)
            for item in list_from_tbl:
                if item['номер\nкэ в 1С'] == current_part_zp and item['ЗК'] == current_part_zk:
                    if F.is_date(poz['ДАТА\nПЛАН\n\nготовн'],"%d.%m.%y"):
                        if F.strtodate(poz['ДАТА\nПЛАН\n\nготовн'],"%d.%m.%y") > max_date:
                            max_date = F.strtodate(poz['ДАТА\nПЛАН\n\nготовн'],"%d.%m.%y")

            date_kompl = F.datetostr(max_date,"%Y-%m-%d")
            postfix = f"\n(МАХ дата из всех поз. по кэ в 1С {current_part_zp})"
        else:
            date_kompl = CSQ.custom_request_c(self.db_kplan, f"""SELECT 
            MAX(пл_компл.ПДата_зав_комплект_упаковки) FROM пл_компл INNER JOIN  
             пл_оуп ON пл_оуп.НомПл = пл_компл.НомПл, 
            знпр ON пл_оуп.Пномер_ЗП = знпр.s_num WHERE знпр.Ref_Key_py = "{Ref_Key_py}";""", rez_dict=False, one_column=True,
                                                 hat_c=False)
            date_kompl= date_kompl[0]
            postfix = f"\n(МАХ дата из всех поз. по `{poz.dict_tables['пл_оуп']['№ERP']})`"

    else:
        if exel_mode:
            date_kompl = F.datetostr(F.strtodate(poz['ДАТА\nПЛАН\n\nготовн'],"%d.%m.%y"))
        else:
            date_kompl = poz.row_dates_etap['ПДата_зав_комплект_упаковки']

    date_fix_date = F.strtodate(date_kompl)
    if not exel_mode:
        date_fix_date = CMS.add_only_work_days(date_fix_date, datetime.timedelta(days=1), self)
    date_fix = F.datetostr(date_fix_date, "%Y-%m-%dT%H:%M:%S")
    date_fix_rus = F.datetostr(date_fix_date, "%d.%m.%Y")



    if F.strtodate(self.glob_plan_addit_info_poz_gant_old_date, "%d.%m.%Y %H:%M:%S") == date_fix_date:
        CQT.msgbox(f'Даты равны: {date_fix_rus}{postfix}')
        return

    if not CQT.msgboxgYN(
            f'Дата отгрузки {F.datetostr(F.strtodate(self.glob_plan_addit_info_poz_gant_old_date, "%d.%m.%Y %H:%M:%S"), "%d.%m.%Y")} '
            f'будет заменена на {date_fix_rus}{postfix}\n продолжить?'):
        return


    struct = []
    fl_edit = False
    min_data = None
    max_data = None
    for nomen in data_co['Товары']:
        if nomen['Номенклатура_Key'] == nomen_ref and nomen['ДатаОтгрузки'] != date_fix:
            fl_edit =True
            nomen['ДатаОтгрузки'] = date_fix
        if min_data == None or F.strtodate(min_data,"%Y-%m-%dT%H:%M:%S") > F.strtodate(nomen['ДатаОтгрузки'],"%Y-%m-%dT%H:%M:%S"):
            min_data = nomen['ДатаОтгрузки']
        if max_data == None or F.strtodate(max_data,"%Y-%m-%dT%H:%M:%S") < F.strtodate(nomen['ДатаОтгрузки'],"%Y-%m-%dT%H:%M:%S"):
            max_data = nomen['ДатаОтгрузки']
        struct.append(nomen)



    if parts:
        max_data = F.datetostr(date_fix_date,"%Y-%m-%dT%H:%M:%S")


    if max_data == None:
        CQT.msgbox(f'Не найдена максимальная дата')
        return

    if data_co['ДатаОтгрузки'] != max_data:
        fl_edit = True


    if not fl_edit:
        CQT.msgbox(f'Изменений не требуется, даты совпадают')
        return
    struct_etaps = []
    js_data = {'odata.metadata': meta_co,
               'НеОтгружатьЧастями': parts,
               'ДатаОтгрузки': max_data,
               'Товары': struct
               }

    if 'ЭтапыГрафикаОплаты' in data_co and data_co['doc_name'] == 'ЗаказКлиента':
        for line in data_co['ЭтапыГрафикаОплаты']:
            if line['ВариантОтсчета'] == 'ОтДатыОтгрузки':
                if not F.is_numeric(line['Сдвиг']):
                    CQT.msgbox(f'Сдвиг ЭтапыГрафикаОплаты не число "{line["Сдвиг"]}"')
                else:
                    line['ДатаПлатежа'] = F.datetostr(F.add_days(date_fix_date, datetime.timedelta(days=int(line['Сдвиг']))), "%Y-%m-%dT%H:%M:%S")

            if line['ВариантОтсчета'] == 'ДоДатыОтгрузки':
                if not F.is_numeric(line['Сдвиг']):
                    CQT.msgbox(f'Сдвиг ЭтапыГрафикаОплаты не число "{line["Сдвиг"]}"')
                else:
                    line['ДатаПлатежа'] = F.datetostr(F.add_days(date_fix_date, datetime.timedelta(days=-1* int(line['Сдвиг']))), "%Y-%m-%dT%H:%M:%S")
            struct_etaps.append(line)
        js_data['ЭтапыГрафикаОплаты'] = struct_etaps

    m.params = js_data
    cod, rez = m.patch_responce(doc_name=f"Document_{data_co['doc_name']}(guid'{client_order}')")
    if cod != 200:
        msg = ''
        if isinstance(rez, str):
            msg = rez
        CQT.msgbox(f'Ошибка при изменении {cod}\n{msg}')
        return

    cod, rez =    m.undertake_doc(f"Document_{data_co['doc_name']}",client_order)
    if cod != 200:
        msg = ''
        if isinstance(rez, str):
            msg = rez
        CQT.msgbox(f'Ошибка при проведении {cod}\n{msg}')
        return

    GPL.tab_addit_info_poz_gant_click(self, self.ui.tab_addit_info_poz_gant.currentIndex())
    CQT.msgbox(f'Успешно',time_life=0.5)




@CQT.onerror
def update_plan_main_tbl(self: mywindow):
    gui_mode_off()
    if DTCLS.FIELDS_DB_INFO.list_unchecked:
        def fnc_oform(tbl, *args):
            list_checks = CSQ.custom_request_c(DTCLS.db_kplan,f"""SELECT * FROM info_fields_kpl_check_rules""",rez_dict=True)

            t = CQT.TableContext(tbl)
            for row in t.rows():
                CQT.add_combobox(DTCLS.app_self,t.tbl,row.i,t.nf['Правило'],
                                 [f"{_['name']} ({_['descr']})" for _ in list_checks],
                                 list_data=[_['id'] for _ in list_checks],return_data=True)
        def fnc_btn(btn: QtWidgets.QPushButton, dialog:CQT.Dialog_tbl, tbl: QtWidgets.QTableWidget,*args):
            if btn.text() == "Ввод":
                t = CQT.TableContext(tbl)
                for row in t.rows():
                    cmb:CQT.QtWidgets.QComboBox = row.widget('Правило')
                    id_rule = cmb.currentData(QtCore.Qt.UserRole)
                    field_id = int(row.value('Номер'))
                    CSQ.custom_request_c(DTCLS.db_kplan,f"""INSERT INTO info_fields_kpl_check_rules_val 
                            (field, rule, comment) VALUES(?,?,?)""",list_of_lists_c=[[field_id,id_rule,F.now()]])
                CQT.msgbox(f'Успешно. Перезагрузка')
                dialog.accept()
            else:
                dialog.reject()
        if DTCLS.USER_CONFIG.is_developer:
            dict_tabels = {_['Таблица']: dict() for _ in DTCLS.FIELDS_DB_INFO.list_unchecked}
            for tbl_name in dict_tabels.keys():
                dict_tabels[tbl_name] = CSQ.dict_types_tbl(DTCLS.db_kplan, tbl_name,as_str=True)
            template = []
            for it in DTCLS.FIELDS_DB_INFO.list_unchecked:
                it["Правило"]=''
                it['Тип'] = dict_tabels[it['Таблица']][it['Поле']]
                template.append(it)


            rez = CQT.msgboxg_get_table(DTCLS.app_self, 'Не проверенные поля:', template,
                                         WindowTitle=f'{CEMOJ.EmojiMain.Эмоции.confused} Нет правил проверки',
                                         styleSheet=CQT.MES_CSS,func_oform_tbl=fnc_oform,func_btn0=fnc_btn,not_standart_close=True)
        else:
            CQT.msgbox(' Нет правил проверки для некоторых полей')

        sys.exit()
        raise Exception
    def load_month_for_apply_diap_dates_to_sb_in_tbl(self: mywindow):
        cmb = self.ui.cmb_apply_diap_dates_to_sb_in_tbl
        cmb.clear()
        cmb.addItem('')
        cmb.addItem('Не в плане')
        rez = CSQ.custom_request_c(self.db_kplan, f"""SELECT Дата  
         FROM mnts_plan WHERE file_poz_plan IS NOT NULL AND poki == {self.place.poki} ORDER BY Дата""",
                                   rez_dict=True)
        for month in rez:
            if month['Дата']:
                cmb.addItem(month['Дата'])

    def get_params_kpl(self: mywindow):
        kpl_bool_load_zav = 0
        try:
            kpl_bool_load_zav = F.valm(CMS.load_tmp_path('kpl_bool_load_zav'))
        except:
            pass
        self.ui.chk_kpl_zaversch.blockSignals(True)
        self.ui.chk_kpl_zaversch.setChecked(kpl_bool_load_zav)
        self.ui.chk_kpl_zaversch.blockSignals(False)

        kpl_bool_paint_dates = 0
        try:
            kpl_bool_paint_dates = F.valm(CMS.load_tmp_path('kpl_bool_paint_dates'))
        except:
            pass
        self.ui.chk_paint_dates.blockSignals(True)
        self.ui.chk_paint_dates.setChecked(kpl_bool_paint_dates)
        self.ui.chk_paint_dates.blockSignals(False)

    get_params_kpl(self)
    # update_date_kplmk_from_narmk(self)# отключено
    self.Data_plan.DICT_INFO_FIELDS_KPL = self.Data_plan.GET_DICT_INFO_FIELDS_KPL(self.Data_plan.db_kplan)
    #temporary_fix(self)
    self.ui.tbl_kal_pl.blockSignals(True)
    check_set_fininsh_py(self)
    self.kpl_mode = 0

    # self.LIST_ETAPS = [ _ for _ in CSQ.get_list_of_tables_c(self.db_kplan) if 'пл_' in _ ]

    self.dict_tbls_kpl_info = dict()

    if "val_masht" not in dir(self):
        self.val_masht = 12
        try:
            self.val_masht = int(CMS.load_tmp_path('mk_val_masht'))
        except:
            pass
    VPL.load_diapazon_month(self)


    #=======ЗАГРУЗКА ДАННЫХ==============
    load_gui(self)
    #===================================

    self.ui.splitter_pl.setSizes([400, 180])


    self.glob_kpl_summ_selct_tbl = ''
    self.dict_form_kpl = ''
    KPLUF.fill_pl_user_filtrs(self)
    load_month_for_apply_diap_dates_to_sb_in_tbl(self)

    m = CODAT.OrdersComposit(self.USER_CONFIG.ERP_base_name['Значение'])
    try:
        #self.DICT_plan_erp_nomen_refs = F.deploy_dict_c(m.get_response(doc_name='Catalog_Номенклатура',
        #                          wet_filtr=f"""?$select= Ref_Key, Description, Артикул""",lazy_method_huours = 2), 'Ref_Key')

        wet_req_text = f"""ВЫБРАТЬ
                Номенклатура.Наименование КАК Description,
                Номенклатура.Артикул КАК Артикул,
                УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Номенклатура.Ссылка) КАК Ref_Key
            ИЗ
                Справочник.Номенклатура КАК Номенклатура
            ГДЕ
                Номенклатура.ВидНоменклатуры В ИЕРАРХИИ
            (ВЫБРАТЬ ПЕРВЫЕ 1
                ВидыНоменклатуры.Ссылка КАК Ссылка
            ИЗ
                Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
            ГДЕ
                ВидыНоменклатуры.ЭтоГруппа = ИСТИНА
                И ВидыНоменклатуры.Наименование = "{CFG.Config.place.Имя}");"""
        key, data_rez = APIERP.get_wet_request(wet_req_text,lazy_method_huours=2)
        if key != 200:
            if not CFG.Config.user_config.is_developer:
                self.ui.tabWidget.setCurrentIndex(self.START_TAB_IND)
            CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
            return
        self.DICT_plan_erp_nomen_refs = F.deploy_dict_c(data_rez['data'] , 'Ref_Key')
        
        self.DICT_plan_erp_Пользователи = F.deploy_dict_c(m.get_response(doc_name=f"Catalog_Пользователи",
                                   wet_filtr=f"?$select=Ref_Key, Description",lazy_method_huours = 24), 'Ref_Key')

        self.DICT_plan_erp_ПричиныПриостановкиПроизводства = F.deploy_dict_c(m.get_response(doc_name=f"Catalog_ПричиныПриостановкиПроизводства",
                                   wet_filtr=f"?$select=*",lazy_method_huours = 24), 'Ref_Key')
    except:
        CQT.msgbox(f'Ошибка получения данных из 1С (сервер не отвечает) попробуй через минуту')
        self.ui.tabWidget.setCurrentIndex(self.START_TAB_IND)

    self.glob_kpl_pull_poz_dict = dict()
    self.ui.splitter_pl.setSizes([400, 0])

    self.ui.fr_tree_fields.setHidden(True)
    self.ui.tbl_kal_pl.blockSignals(False)
    self.ui.fr_plan_day_edit.setHidden(True)
    self.ui.fr_poz_from_exel.setHidden(True)
    self.ui.fr_gant_local_tbl.setHidden(False)

def is_local_gant_hidden(self:mywindow)->bool:
    if self.ui.splitter_pl.sizes()[1] == 0:
        return True
    return False



@CQT.onerror
def load_gui(self: mywindow, *args):
    show_fr(self)
    gui_mode_off()
    load_table_db(self)
    self.kpl_mode = 0  # объемный выключен
    self.kpl_mode_pull = 0  # компоновщик выключен






@CQT.onerror
def plan_day_edit_set_weekend(self: mywindow, *args):
    g_handler = Gant_handler()
    if g_handler is None:
        return
    weekends = CMS.Plan_custom_weekends(g_handler.poz_gant.poz_id)

    if 'shift' in CQT.get_key_modifiers(self):

        list_days_oform = weekends.get_list_weekends()
        list_del = CQT.msgboxg_get_table(self,'Дни к удалению',list_days_oform,'Удалить','Отмена',ExtendedSelection=True,sortingEnabled=True)
        if not list_del:
            return
        weekends.del_days({F.strtodate(_['Не рабочие дни'],"%Y-%m-%d" ) for _ in list_del})


    else:
        list_cld_days_selected = g_handler.get_list_cld_days_selected()
        list_days_oform = [{'Дата':f'{F.get_day_name(_.day_week)} - {F.datetostr(_.dt_datetime,"%d.%m.%Y")}'}
                           for _ in list_cld_days_selected]

        ans = CQT.msgboxg_get_table(self,'Дни к добавлению',list_days_oform,'Продолжить',yesNoMode=True)
        if not ans:
            return
        weekends.add_days(set([_.dt_datetime for _ in list_cld_days_selected]))
    update_local_graf(update=True,)
    #CQT.msgbox(f'Успешно. Теперь нужно пересчитать гант')




@CQT.onerror
def plan_on_of_day_edit_frame(self: mywindow, *args):
    if self.ui.fr_plan_day_edit.isHidden():
        self.ui.fr_plan_day_edit.setHidden(False)
        self.ui.le_plan_day_edit_recalc_hour_per_day.setText('16')
        self.ui.fr_setup_etaps.setHidden(True)
    else:
        self.ui.fr_plan_day_edit.setHidden(True)
        self.ui.fr_setup_etaps.setHidden(False)

@CQT.onerror
def btn_pull_poz_show(self: mywindow, *args):
    if self.kpl_mode_pull == 0:  # компоновщик выключен
        self.ui.fr_pull_poz.setHidden(False)
        self.ui.splitter_3.setSizes([168, 500])
        # компоновщик
        POZPL.fill_list_month_pozplan(self)
        self.ui.cmb_for_adapt.clear()
        self.ui.cmb_for_adapt.addItem('')
        dict_nicks = CMS.get_shablon_vidov(self.DICT_PROFESSIONS)
        CQT.fill_list_combobx(self,self.ui.cmb_for_adapt,[_.replace('_н_см','') for _ in dict_nicks],
                              list_data=dict_nicks)

        self.ui.btn_pl_mode.setHidden(True)
        self.kpl_mode_pull = 1  # объемный вылючен
        self.ui.lbl_srv_cld_plan_workforce.setText(CEMOJ.EmojiMain.ПерсоналРоли.server.symbol)
        self.ui.lbl_local_cld_plan_workforce.setText(CEMOJ.EmojiMain.ПерсоналРоли.local_machine.symbol)
    else:
        self.ui.fr_pull_poz.setHidden(True)
        self.ui.btn_pl_mode.setHidden(False)
        self.kpl_mode_pull = 0


@CQT.onerror
def btn_pl_mode(self:mywindow):

    def get_koef_selected_napr(self):
        for dic in self.Data_plan.DICT_NAPRAVLENIE.values():
            if dic['name'] == self.selected_napr:
                return dic['val'] / 100
        return 0

    if self.is_main_mode():  # объемный выключен :включаем

        if not VPL.load_tbl_gant(self):  # объемный загрузка
            return
        show_fr(self, graf=1)  # объемный включаем
        fill_napr_into_cmb_select_napr(self)
    else:
        load_gui(self)  # объемный выключить



@CQT.onerror
def clck_tbl_verticalHeader(self, row, *args):
    tbl = self.ui.tbl_pl_gaf
    tbl_filtr = self.ui.tbl_filtr_kal_pl
    c = tbl.currentColumn()
    etap = tbl.item(row, CQT.num_col_by_name_c(tbl, 'Этап')).text()

    self.ui.tbl_pl_gaf_filtr.item(0, CQT.num_col_by_name_c(tbl, 'Этап')).setText(etap)




def btn_pl_add_poz_click(self):
    def add_poz_mode_on():
        self.ui.fr_settings_pl.setHidden(True)
        self.ui.btn_pull_poz_show.setHidden(False)
        self.ui.btn_pl_mode.setHidden(False)
        CQT.clear_tbl(self.ui.tbl_pl_add_poz)
        self.ui.tbl_pl_add_poz.setHidden(False)

        self.ui.fr_pull_poz.setHidden(True)
        self.ui.fr_pl_graf.setHidden(True)
        self.ui.fr_pl_tables.setHidden(False)

        self.ui.fr_pl_add_poz.setHidden(False)
        self.ui.fr_pl_etap.setHidden(True)
        self.ui.btn_pl_mode.setHidden(True)
        self.ui.tbl_pl_add_poz.setHidden(False)
        DTCLS.ADD_POZ_MODE = True

    if not DTCLS.ADD_POZ_MODE:
        add_poz_mode_on()
        if not load_tbl_add_new_poz(self):
            gui_mode_off()
    else:
        gui_mode_off()

def btn_pl_settings(self:mywindow):
    def gui_settings_pl_mode_on():
        self.ui.fr_settings_pl.setHidden(False)
        self.ui.btn_pull_poz_show.setHidden(True)
        self.ui.btn_pl_mode.setHidden(True)
        CQT.clear_tbl(self.ui.tbl_pl_add_poz)
        self.ui.tbl_pl_add_poz.setHidden(True)
        self.ui.tbl_select_etap_edit_poz.setHidden(True)
        self.ui.fr_pull_poz.setHidden(True)
        self.ui.fr_pl_graf.setHidden(True)
        self.ui.fr_pl_tables.setHidden(False)
        self.ui.fr_pl_add_poz.setHidden(False)
        self.ui.fr_pl_etap.setHidden(True)

        DTCLS.SETTINGS_PL_MODE = True

    if not DTCLS.SETTINGS_PL_MODE:

        self.ui.chk_autorepeat_update_fact.blockSignals(True)
        if CMS.is_autorepeat_update_fact(CFG.Config.project.db_naryad,self.place.poki):
            self.ui.chk_autorepeat_update_fact.setChecked(True)
        else:
            self.ui.chk_autorepeat_update_fact.setChecked(False)
        self.ui.chk_autorepeat_update_fact.blockSignals(False)
        gui_settings_pl_mode_on()

    else:
        gui_mode_off()




def create_list_fields____(self):#TO DELETe
    list_tables = ['plan','mk.Дата_завершения','mk.Вес','mk.xml', 'знпр']
    custom_fields = ['Дата_прих_ордера_гп']
    filtr_poki = list(self.Data_plan.DICT_PODR_POKI.keys())

    tables = [_ for _ in CSQ.get_list_of_tables_c(self.db_kplan) if 'пл_' in _ and _ in filtr_poki]
    for i in range(len(self.Data_plan.DICT_PODR)):
        for table in tables:
            if table in self.Data_plan.DICT_PODR:
                if self.Data_plan.DICT_PODR[table]['Порядок'] == i:
                    list_tables.append(table)
    for table in tables:
        if table not in self.Data_plan.DICT_PODR:
            list_tables.append(table)

    dict_fields = dict()
    for cust_field in custom_fields:
        name_field = f'cust.{cust_field}'
        dict_fields[name_field] = {'view':1}
        descr = ''
        if name_field in self.Data_plan.DICT_INFO_FIELDS_KPL:
            descr = self.Data_plan.DICT_INFO_FIELDS_KPL[name_field]['nickname']
            if self.Data_plan.DICT_INFO_FIELDS_KPL[name_field]['hide'] == 1:
                dict_fields[name_field]['view'] = 0
        dict_fields[name_field]['descr'] = descr

    for table in list_tables:
        if '.' in table:
            table , fields = table.split('.')
            fields = [fields]
        else:
            fields = CSQ.list_of_columns_c(self.db_kplan, table)
        for field in fields:
            name_field = f'{table}.{field}'
            dict_fields[name_field] = {'view':1}
            descr = ''
            if name_field in self.Data_plan.DICT_INFO_FIELDS_KPL:
                descr = self.Data_plan.DICT_INFO_FIELDS_KPL[name_field]['nickname']
                if self.Data_plan.DICT_INFO_FIELDS_KPL[name_field]['hide'] == 1:
                    dict_fields[name_field]['view'] = 0
            dict_fields[name_field]['descr'] = descr
    return dict_fields




def update_list_fields(fl_one_row=False):
    DTCLS.FIELDS_DB_INFO.force_view = fl_one_row
    dict_fields_o = DTCLS.FIELDS_DB_INFO.dict_fields

    dict_cnf = DTCLS.FIELDS_DB_INFO.load_user_data(f"poki_{CFG.Config.place.poki}_")
    if not dict_cnf:
        dict_cnf =  DTCLS.FIELDS_DB_INFO.load_user_data()


    if dict_cnf is None:
        DTCLS.FIELDS_DB_INFO.first_load = True
    else:
        for f_cnf, data_cnf in dict_cnf.items():
            if f_cnf in dict_fields_o:
                dict_fields_o[f_cnf].usr_hide = not data_cnf['hidden']
                dict_fields_o[f_cnf].usr_idx = data_cnf['order']
        set_new_fields = set(dict_fields_o.keys()) - set(dict_cnf.keys())

        if set_new_fields:
            for field_o in dict_fields_o.values():
                if field_o.name_mes in set_new_fields:
                    field_o.usr_hide = True

    dict_fields_o['plan.ТипГр'].sys_hide = not DTCLS.FIELDS_DB_INFO.use_groups
    dict_fields_o['plan.Группа'].sys_hide = not DTCLS.FIELDS_DB_INFO.use_groups
    DTCLS.FIELDS_DB_INFO.fix_indx()




def btn_pl_edit_poz_click(self: mywindow):
    def gui_edit_poz_mode_on():
        self.ui.fr_settings_pl.setHidden(True)
        self.ui.btn_pull_poz_show.setHidden(False)
        self.ui.btn_pl_mode.setHidden(False)
        CQT.clear_tbl(self.ui.tbl_pl_add_poz)
        self.ui.tbl_pl_add_poz.setHidden(False)

        self.ui.fr_pull_poz.setHidden(True)
        self.ui.fr_pl_graf.setHidden(True)
        self.ui.fr_pl_tables.setHidden(False)

        self.ui.fr_pl_add_poz.setHidden(False)
        self.ui.fr_pl_etap.setHidden(False)
        self.ui.btn_pl_mode.setHidden(True)
        self.ui.tbl_pl_add_poz.setHidden(False)
        DTCLS.EDIT_POZ_MODE = True

    if not DTCLS.EDIT_POZ_MODE:
        load_tbl_edit_poz(self)
        gui_edit_poz_mode_on()
    else:
        gui_mode_off()



def check_permisions_on_fields(header: str, value: str, self) -> bool:
    if DTCLS.ADD_POZ_MODE:
        return True
    if CFG.Config.user_config.is_developer:
        return True
    db_kplan = CFG.Config.project.db_kplan
    current_login = F.user_name()
    access_users = CSQ.custom_request_c(
        db_kplan,
        f'SELECT users_rule FROM info_fields_kpl WHERE name = {header!r}', rez_dict=True, one=True
    )
    if isinstance(access_users, dict):
        users_rule = access_users.get('users_rule', '')
        if not current_login in users_rule.split(';'):
            return CQT.msgbox(f'У вас недостаточно прав для редактирования поля: {header!r}')
        return True
    return False

def attach_tbl_pl_add_poz_validator(self, tbl: QtWidgets.QTableWidget):
    validator = CQT.TableValidator(check_permisions_on_fields, tbl, self)
    if not hasattr(tbl, 'validator_is_set'):
        tbl.validator_is_set = True
        tbl.setItemDelegate(validator)


@CQT.onerror
def load_tbl_edit_poz(self: mywindow):
    podrs = DTCLS.FIELDS_DB_INFO.tables_db.tabels_ordered
    dict_podr = { i:_ for i, _ in enumerate(podrs)}
    tbl_select_podr = self.ui.tbl_select_etap_edit_poz
    columns = 25
    rows = F.round_up(len(dict_podr)/columns)
    templ = [[''] * columns for _ in range(rows)]


    templ.insert(0,  [str(_) for _ in range(columns)])
    CQT.fill_wtabl(templ,tbl_select_podr,auto_type=False,hide_head_column=True,hide_head_rows=True,
                   selectionMode='SingleSelection',styleSheet=CQT.MES_CSS,height_row=24)
    t = CQT.TableContext(tbl_select_podr)
    with CQT.table_updating(t.tbl):
        indx = 0
        fl_exit = False
        for row in t.rows():
            if fl_exit:
                break
            for j, key in enumerate(row.nf.keys()):
                it = dict_podr[indx]
                row.set_value(key, it.alias)
                row.set_data(key, it.name)
                row.setToolTip(key, it.descr)
                clr = it.color.rgb
                row.set_color_font(*clr,col_name=key)
                row.set_font_format(bold=True,col_name=key)
                indx += 1
                if indx == len(dict_podr):
                    fl_exit = True
                    break

        t.tbl.resizeColumnsToContents()
        row = t.get_row(0)
        for column,idx in t.nf.items():
            data = row.data(column)
            if data:
                wdth = t.tbl.columnWidth(idx)
                if wdth<50:
                    t.tbl.setColumnWidth(idx,50)
            else:
                t.tbl.setColumnWidth(idx,5)

        t.set_cursor(CQT.Cursors.pointinghand.get())
    t.resizeHeigtToContents()
    return



@CQT.onerror
def doubleclck_tbl_kal_pl(self: mywindow, row='', col=''):
    tbl = self.ui.tbl_kal_pl
    t = CQT.TableContext(tbl)
    field_name = t.current_column_name()
    cur_row = t.current_row()
    if cur_row.no_selection:
        return

    if field_name == 'plan.ТипГр':

        is_closed = cur_row.value('plan.ТипГр') == FOLDER_CLOSED

        dict_filtr = CMS.apply_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl, False,
                                       get_dict_by_fild='plan.Пномер')
        gr = cur_row.value('plan.Группа')
        with CQT.table_updating(t):
            set_group_close(self,gr_name=gr,close= not is_closed, dict_filtr=dict_filtr)

            if is_closed:
                cur_row.set_value('plan.ТипГр',FOLDER_OPEN)
            else:
                cur_row.set_value('plan.ТипГр',FOLDER_CLOSED)


    if field_name == 'пл_ко.Ссылка_КД':
        val = tbl.item(row,col).text()
        if ':' in val:
            try:
                os.startfile(val)
            except:
                CQT.msgbox(f'Ошибка открытия ссылки')




@CQT.onerror
def select_sort_c(self, text, row, col, *args):
    obj = CMS.TypesWorkingByDirections() #25.07.25
    if obj.COMBOBOX_KEY_FOR_NAME_COMPOSE == text:
        text = obj.get_table_for_name_composite(window=self)
        if not text:
            return

        nk_sort_c = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Вид')
        cell = self.ui.tbl_pl_add_poz.cellWidget(0, nk_sort_c)
        cmb_vals_generator = (cell.itemText(cr_cmb_idx) for cr_cmb_idx in range(cell.count()))
        if text not in cmb_vals_generator:
            cell.addItem(text)
        cell.setCurrentText(text)
        self.ui.tbl_pl_add_poz.resizeColumnToContents(nk_sort_c)

    nk_sort_c = col
    val = 0
    for key in self.Data_plan.DICT_VID_PO_NAPR.keys():
        if self.Data_plan.DICT_VID_PO_NAPR[key]['Имя'] == text:
            val = key
            break
    self.ui.tbl_pl_add_poz.item(row, nk_sort_c).setText(str(val))
    print(f'Выбран {val}')





def select_status_tara(self, text, row, col, *args):
    statys_nom = self.Data_plan.DICT_STATUS_TARA_NAME[text]['s_num']
    self.ui.tbl_pl_add_poz.item(row, col).setText(str(statys_nom))
    print(f'Выбран {text}')


def select_napr_deyat(self, text, row, col, *args):
    nk_napr_deyat = col
    val = 0
    for key in self.Data_plan.DICT_NAPR_DEYAT.keys():
        if self.Data_plan.DICT_NAPR_DEYAT[key]['Имя'] == text:
            val = key
            tooltip = f"{self.Data_plan.DICT_NAPR_DEYAT[key]['Примечание']} ({self.Data_plan.DICT_NAPR_DEYAT[key]['Псевдоним']})"
            break
    self.ui.tbl_pl_add_poz.item(row, nk_napr_deyat).setText(str(val))
    self.ui.tbl_pl_add_poz.cellWidget(row, nk_napr_deyat).setToolTip(tooltip)
    # fill_sort_c_top_combo(self, val)
    print(f'Выбран {val}')


def select_status(self, text, row, col, *args):
    nk_ = col
    val = 0
    for key in self.Data_plan.DICT_STATUS_POZ.keys():
        if self.Data_plan.DICT_STATUS_POZ[key]['Имя'] == text:
            val = key
            break
    self.ui.tbl_pl_add_poz.item(row, nk_).setText(str(val))



def select_status_norm(self, text, row, col, *args):
    nk_ = col
    val = 0
    for key in self.Data_plan.DICT_STATUS_NORM.keys():
        if self.Data_plan.DICT_STATUS_NORM[key]['Имя'] == text:
            val = key
            break
    self.ui.tbl_pl_add_poz.item(row, nk_).setText(str(val))
    print(f'Выбран {val}')


def select_etapi_erp(self, text, row, col, *args):
    nk_ = col
    val = 0
    for key in self.Data_plan.DICT_STATUS_ETAPI_ERP.keys():
        if self.Data_plan.DICT_STATUS_ETAPI_ERP[key]['Имя'] == text:
            val = key
            break
    self.ui.tbl_pl_add_poz.item(row, nk_).setText(str(val))
    print(f'Выбран {val}')


@CQT.onerror
def generate_list_py(self)->list[dict]:
    wet_req_text = f"""
            ВЫБРАТЬ
    ЗаказНаПроизводство2_2.Дата КАК Date,
    ЗаказНаПроизводство2_2.Номер КАК Number,
    ЗаказНаПроизводство2_2.Статус КАК Статус,
    ЗаказНаПроизводство2_2.Комментарий КАК Комментарий,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказНаПроизводство2_2.Ссылка)) КАК Ref_Key
ИЗ
    Документ.ЗаказНаПроизводство2_2 КАК ЗаказНаПроизводство2_2
ГДЕ
    ЗаказНаПроизводство2_2.Статус <> Значение(Перечисление.СтатусыЗаказовНаПроизводство2_2.Закрыт) И
     ЗаказНаПроизводство2_2.Номер ПОДОБНО "{self.place.doc_prefix}%"
            """
    key, data_rez = APIERP.get_wet_request(wet_req_text,lazy_method_huours=0.1)
    if key != 200:
        CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
        return
    if data_rez['data']:
        data = data_rez['data']
        for i in range(len(data)):
            data[i]['Date'] = F.dateStrToStr(data[i]['Date'],format_out="%Y-%m-%d")
        return data
    return
    postfix = f"and Статус ne 'Закрыт'"
    if state != None:
        postfix = f"and Статус eq '{state}'"
    if year != None:
        if year == 'all':
            pass
        else:
            postfix = f"{postfix} and  year(Date) eq {year}"

    m = ERP.OrdersComposit()
    list_data = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                               wet_filtr=f"?$filter= startswith(Number, '{self.place.doc_prefix}'){postfix} &$select=Date,Number,Комментарий,Ref_Key")
    if list_data == None:
        CQT.msgbox(f'Соединение с сервером 1С не установлено')
        return
    rez_list = ['Date|Number|Комментарий|Ref_Key']
    for item in list_data:
        year = F.datetostr(F.strtodate(item['Date'], "%Y-%m-%dT%H:%M:%S"), "%Y")

        rez_list.append(
            '|'.join([year, item['Number'], F.clear_str_ntrs(item['Комментарий']).replace("|", " "), item['Ref_Key']]))
    rez_list.insert(1, '|'.join(['Загрузить', '-', 'Все года', "Статус = 'Формируется'"]))
    rez_list.insert(2, '|'.join(['Загрузить', '-', 'Статус не закрыт', "Все Года"]))
    rez_list.insert(3, '|'.join(['1999', '-', f'Нет {self.place.doc_prefix}', ""]))
    return rez_list



def select_poz(self: mywindow, text, row, col, *args):
    num_line, count_poz, name = text.split('.| ')
    tbl = self.ui.tbl_pl_add_poz

    nf_poz_count = CQT.num_col_by_name_c(tbl, 'Количество')
    tbl.item(0, nf_poz_count).setText('')

    nf_poz_num = CQT.num_col_by_name_c(tbl, 'Позиция')
    if nf_poz_num:
        tbl.item(0, nf_poz_num).setText('')

    if text == '':
        return

    nf_poz_name = CQT.num_col_by_name_c(tbl, 'Номенклатура_ЕРП')
    nf_poz_line = CQT.num_col_by_name_c(tbl, 'НомПартии_ЗП')
    tbl.item(0, nf_poz_count).setText(count_poz.replace(" ед.", ''))
    tbl.item(0, nf_poz_name).setText(name)
    poz_num = '?'
    if nf_poz_num:
        tbl.item(0, nf_poz_num).setText(poz_num)
    tbl.item(0, nf_poz_line).setText(num_line.replace("№", ''))
    pass

def etaps_data_if_exists(m: ERP.OrdersComposit, num_py: str, year: int) -> tuple[dict, bool]:
    """
    Принимает:
    @m -> Объект ERP.OrderComposit
    @num_py Номер пу нпрм(ПУ00-000080)
    @year Год
    Действия:
    1. Запрашиваем по номеру_пу / год этапы связанные с выбранным заказом
    2. Формируем словарь из {ОсновноеИзделиеНоменклатура_Key: {НомерПартииЗапуска: ..., НЭ_НулевойЭтап: ...}}
    Возвращает:
    tuple(СловарьКлючейНоменклатур: dict, СодержитНулевойЭтап: bool)
    """
    etaps = m.get_response(doc_name='/Document_ЭтапПроизводства2_2',
                   wet_filtr=f"?$expand=Спецификация&$filter=Распоряжение/Number eq {num_py!r} and year(Date) eq {year} &$select=НЭ_НулевойЭтап,Спецификация/ОсновноеИзделиеНоменклатура_Key,НомерПартииЗапуска")
    have_nullable_etap = False
    result = {}
    for etap in etaps:
        if not etap['НЭ_НулевойЭтап']:
            if 'Спецификация' in etap and isinstance(etap['Спецификация'], dict):
                spec = etap['Спецификация']
                if 'ОсновноеИзделиеНоменклатура_Key' and spec['ОсновноеИзделиеНоменклатура_Key']:
                    result[spec['ОсновноеИзделиеНоменклатура_Key']] = {'НулевойЭтап': etap['НЭ_НулевойЭтап'], 'НомерПартииЗапуска': etap['НомерПартииЗапуска']}
        else:
            have_nullable_etap = True
    return result, have_nullable_etap
@CQT.onerror
def select_py(lblself:CQT.InteractiveLabelInstance, self: mywindow, row, col, *args):
    list_py = generate_list_py(self)
    def fn_oform(tbl:QtWidgets.QTableWidget, *args):
        nf = CQT.nums_col_by_name_dict(tbl)
        tbl.setColumnHidden(nf['Ref_Key'],True)

    row = CQT.msgboxg_get_table(self, 'Выбор проекта', list_py, 'Выбор',
                                selection_from_tbl=True, ExtendedSelection=False,
                                selectRows=True, sortingEnabled=True,styleSheet=CQT.ERP_CSS,func_oform_tbl=fn_oform,
                                aliases_header={'Date':'Дата','Number':'Номер ЗП'},)

    if row:
        year= row['Date']
        nom= row['Number']
        prim= row['Комментарий']
        Ref_Key_py = row['Ref_Key']
    else:
        return
    if self.place.doc_prefix not in nom:
        CQT.msgbox(f'Не выбран {self.place.doc_prefix}')
        return
    tbl = self.ui.tbl_pl_add_poz
    t = CQT.TableContext(tbl)
    for row in t.rows():
        name = row.value('_Name')
        #add
        if name == 'пл_оуп.Номенклатура_ЕРП':
            row.set_value('Значение','')
        if name == 'пл_оуп.Количество':
            row.set_value('Значение','')
        if name == 'plan.Позиция':
            row.set_value('Значение','')
        if name == 'знпр.Ref_Key_py':
            row.set_value('Значение',Ref_Key_py)
        if name == 'знпр.№ERP':
            row.set_value('Значение',nom)
        # edit
        if name == 'пл_оуп.№ERP':
            row.set_value('Значение',nom)
        if name == 'пл_оуп.Дата_заявки_на_произв':
            row.set_value('Значение' ,F.dateStrToStr(year))
        if name == 'пл_оуп.Пномер_ЗП':
            row.set_value('Значение', Ref_Key_py)

    lblself.set_text(nom)
    add_btns_select_poz_after_py(self, tbl, Ref_Key_py)

@CQT.onerror
def select_poz_after_py(lblself:CQT.InteractiveLabelInstance,self, row, col,ref:str):
    text = f"""
                ВЫБРАТЬ
    ЗаказНаПроизводство2_2Продукция.Номенклатура.Наименование КАК НоменклатураНаименование,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказНаПроизводство2_2Продукция.Номенклатура.Ссылка)) КАК Номенклатура_Key, 
    ЗаказНаПроизводство2_2Продукция.Номенклатура.ЕдиницаИзмерения.Наименование КАК ЕдиницаИзмерения,
    ЗаказНаПроизводство2_2Продукция.Количество КАК Количество,
    ЗаказНаПроизводство2_2Продукция.НомерСтроки КАК LineNumber,
    ЗаказНаПроизводство2_2Продукция.Ссылка.Номер КАК НомерЗП,
    ГОД(ЗаказНаПроизводство2_2Продукция.Ссылка.Дата) КАК year
ИЗ
    Документ.ЗаказНаПроизводство2_2.Продукция КАК ЗаказНаПроизводство2_2Продукция
ГДЕ
    ЗаказНаПроизводство2_2Продукция.Ссылка = &Ссылка
                """
    refs = APIERP.Refs_wet(text)
    ref_obj = APIERP.Ref_wet('Ссылка', 'Документы.ЗаказНаПроизводство2_2', ref)
    refs.add_ref(ref_obj)
    key, data_rez = APIERP.get_wet_request(text,refs,lazy_method_huours=0.1)
    if key != 200:
        CQT.msgbox(f'Ошибка получения данных код ({key}) из ERP')
        return
    if not data_rez['data']:
        CQT.msgbox(f'ТЧ пустая')
        return
    data = data_rez['data']
    year = data[0]['year']
    nom = data[0]['НомерЗП']
    m = ERP.OrdersComposit()
    nomen_pos, have_null_etap = etaps_data_if_exists(m, nom, year)
    list_name_poz = []
    for poz in data:
        name_poz = poz['НоменклатураНаименование']
        if part_py := nomen_pos.get(poz['Номенклатура_Key']):
            line_number = part_py.get('НомерПартииЗапуска')
        else:
            line_number = int(have_null_etap) + int(poz['LineNumber'])

        list_name_poz.append( {'№':line_number, 'НоменклатураНаименование': name_poz , 'Количество': poz['Количество'] ,
                               'ЕдиницаИзмерения': poz['ЕдиницаИзмерения'] })

    row = CQT.msgboxg_get_table(self, 'Выбор проекта', list_name_poz, 'Выбор',
                                selection_from_tbl=True, ExtendedSelection=False,
                                selectRows=True, sortingEnabled=True,styleSheet=CQT.ERP_CSS)
    if row:
        num_line = row['№']
        count_poz= row['Количество']
        name_nomen= row['НоменклатураНаименование']
    else:
        return

    tbl_pl = self.ui.tbl_pl_add_poz
    t = CQT.TableContext(tbl_pl)
    for row in t.rows():
        name = row.value("_Name")
        if name == 'пл_оуп.Номенклатура_ЕРП':
            row.set_value('Значение',name_nomen)
        if name == 'пл_оуп.Количество':
            row.set_value('Значение',str(count_poz))
        if name == 'пл_оуп.НомПартии_ЗП':
            row.set_value('Значение',str(num_line))
        if name == 'plan.Позиция':
            row.set_value('Значение', '')

    lblself.set_text(name_nomen)



@CQT.onerror
def add_btns_select_poz_after_py(self:mywindow,tbl_pl:QtWidgets.QTableWidget,ref_zp:str):
    t = CQT.TableContext(tbl_pl)
    for row in t.rows():
        name = row.value('_Name')
        if name == 'пл_оуп.Номенклатура_ЕРП':
            widg = CQT.add_interactive_label(tbl_pl, row.i, t.nf['Значение'],
                                             row.value('Значение'), parent_self=self)
            widg.add_button(CEMOJ.EmojiMain.Статусы.ellipsis.symbol, 'Выбрать Поз.', select_poz_after_py,
                            cell_val=ref_zp, img_path=  F.sep().join([F.path_to_execut_file_c(),
                                                                                      'icons','btn_select']))


def fnc_select_nd(lbl: CQT.InteractiveLabelInstance, app_self, i, j, add_data):
    row: CQT.TableRow = add_data[1]
    t: CQT.TableContext = add_data[0]
    def fnc_oform(tbl):
        t = CQT.TableContext(tbl)
        if not CFG.Config.user_config.is_developer:
            t.hide_startsunderscore()
        for row in t.rows():
            clr_o = CMS.Color(row.value('_clr'))
            clr_o.align_colors(level_percent=-30, saturation_percent=-20)
            row.set_color_font(*clr_o.rgb, col_name='Имя')
            row.set_font_format(bold=True, col_name='Имя')

    tmpl = [{'_Пномер': _['Пномер'], 'Имя': _['Имя'], 'Псевдоним': _['Псевдоним'], '_clr': _['Цвет']} for _ in
            app_self.Data_plan.NAPR_DEYAT if _['Псевдоним']]
    rez = CQT.msgboxg_get_table(DTCLS.app_self, 'Выбор НД', tmpl, styleSheet=CQT.MES_CSS,
                                selectRows=True, ExtendedSelection=False, func_oform_tbl=fnc_oform,
                                selection_from_tbl=True)
    if not rez:
        return
    row.set_value('Значение', rez['_Пномер'])
    lbl.set_text(rez['Псевдоним'])


def fill_sort_c_top_combo(self: mywindow, napr_d=0):
    list_sort_c_top = []
    for key in self.Data_plan.DICT_VID_PO_NAPR:
        if self.Data_plan.DICT_VID_PO_NAPR[key]['Направл'] == napr_d:
            list_sort_c_top.append(self.Data_plan.DICT_VID_PO_NAPR[key]['Имя'])
    nk_sort_c_top = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Вид')
    CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_sort_c_top, list_sort_c_top, first_void=False,
                     conn_func=select_sort_c)





@CQT.onerror
def del_poz(self: mywindow):
    tbl = self.ui.tbl_kal_pl
    row= CQT.get_dict_line_form_tbl(tbl)
    if not row:
        CQT.msgbox(f'Строка не выбрана')
        return

    if not CQT.msgboxg_get_table(self,f'Точно удалить',[{'Ключ':k,'Значение':v} for k,v in row.items()],yesNoMode=True):
        return
    pnom = int(row['plan.Пномер'])
    CSQ.custom_request_c(self.db_kplan, f"""DELETE FROM plan
      WHERE Пномер = {pnom};
                    """)
    list_podr = [_ for _ in CSQ.get_list_of_tables_c(self.db_kplan) if _.startswith('пл_') ]
    for podr in list_podr:
        CSQ.custom_request_c(self.db_kplan, f"""DELETE FROM {podr} WHERE НомПл = {pnom};""")
    load_table_db(self)
    CQT.msgbox(f'Успешно')
    return True



@CQT.onerror
def fix_crashed_poz(self: mywindow):
    list_pozs = CSQ.custom_request_c(self.db_kplan,f'''SELECT Пномер,
       Дата_внесения,
       Позиция,
       Направление_деятельности,
       Статус,
       Статус_норм,
       Фдата_получения_КД,
       МК,
       Нчас_заявка_мат,
       Пдата_нач_заявка_мат,
       Пдата_зав_заявка_мат,
       Фчас_заявка_мат,
       Фдата_нач_заявка_мат,
       Фдата_зав_заявка_мат,
       Нчас_заявка_аутсорс,
       Пдата_нач_заявка_аутсорс,
       Пдата_зав_заявка_аутсорс,
       Фчас_заявка_аутсорс,
       Фдата_нач_заявка_аутсорс,
       Фдата_зав_заявка_аутсорс,
       Нчас_вспом,
       Пдата_нач_вспом,
       Пдата_зав_вспом,
       Фчас_вспом,
       Фдата_нач_вспом,
       Фдата_зав_вспом,
       Фчас_доп_раб,
       Этапы_ЕРП,
       Готовность_ПУ,
       Постановка_в_план,
       Примечание,
       Приоритет,
       ЗП_келаст_КЭ,
       Заказ_клиента,
       Потребность_пересч_сроков,
       Статус_поз_ЕРП,
       poki
  FROM plan;
''',rez_dict=True)

    row = CQT.msgboxg_get_table(self,'Выбери поз',list_pozs,selectRows=True,ExtendedSelection=False,selection_from_tbl=True)

    if not row:
        CQT.msgbox(f'Строка не выбрана')
        return

    pnom = int(row['Пномер'])

    list_podr = [_ for _ in CSQ.get_list_of_tables_c(self.db_kplan) if _.startswith('пл_') ]

    for podr in list_podr:
        found = CSQ.custom_request_c(self.db_kplan, f"""SELECT НомПл
                  FROM {podr} 
                 WHERE НомПл = {pnom};""",rez_dict=True)
        if not found:
            CSQ.custom_request_c(self.db_kplan, f"""INSERT INTO {podr}(
                        НомПл
                        )
                        VALUES (?);""", list_of_lists_c=[[pnom]])
    load_table_db(self)
    CQT.msgbox(f'Успешно')
    return True

def get_line_to_edit_podr(self, pnom, podr:CMS.Table_db_info )->list[dict]:
    name_field =  podr.table_primary_full_name
    list_itog = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM 
                    {podr.name} WHERE {name_field} == {pnom}
                     """, one=True, rez_dict=True)
    return [list_itog]

def show_fr(self, graf=0):
    if graf: #объемный график включаем
        self.ui.fr_main_mode.setHidden(True)
        self.ui.fr_pl_graf.setHidden(False)
        self.ui.fr_for_tbl_gant_vol.setHidden(False)
    else:
        # объемный график выключеаем
        self.ui.fr_pl_graf.setHidden(True)
        self.ui.fr_main_mode.setHidden(False)
        self.ui.fr_for_tbl_gant_vol.setHidden(True)




def current_cell_is_data_type(tbl):
    try:
        t = CQT.TableContext(tbl)
        if 'дата' in t.current_column_name().lower():
            return True
        return False
    except:
        return False


def dbl_clk_tbl_add_poz(self):
    if current_cell_is_data_type(self.ui.tbl_pl_add_poz):
        CQT.msgbox('Нужно выбрать дату в календаре  [...]')






@CQT.onerror
def test_add_field_kpl():
    list_files_bin = CSQ.custom_request_c(CFG.Config.project.db_kplan,
                                          f"""SELECT file_poz_plan, Дата FROM mnts_plan 
                                            WHERE file_poz_plan IS NOT NULL""",rez_dict=True)


    list_znpr = CSQ.custom_request_c(CFG.Config.project.db_kplan,
                                          f"""SELECT пл_оуп.НомПл, знпр.Дата_занесения_в_план_месяца  FROM знпр 
                                          INNER JOIN пл_оуп ON пл_оуп.Пномер_ЗП = знпр.s_num 
                                            WHERE знпр.Дата_занесения_в_план_месяца != "";""",rez_dict=True)

    dict_znpr = F.deploy_dict_c(list_znpr,'НомПл')


    list_files_bin = F.sort_by_column_c(list_files_bin,'Дата')
    dict_date_add_poz = {}
    for item in list_files_bin:
        if not item:
            continue
        date = item['Дата']
        file = F.from_binary_pickle(item['file_poz_plan'])
        for num, data_poz in file.items():
            if num not in dict_date_add_poz:
                dict_date_add_poz[num] = date


    for num, date in dict_date_add_poz.items():

        date_mnts = date
        date_mnts_obj = F.strtodate(date_mnts)
        name_plan = f'{F.month_rus_from_date(date,"%Y-%m-%d",False)} {date_mnts_obj.year}'

        if num in dict_znpr:
            date_znpr = dict_znpr[num]
            date_znpr_obj = F.strtodate(date_znpr)
            month_znpr = date_znpr_obj.month

            month_mnts = date_mnts_obj.month
            if month_mnts == month_znpr:
                date = dict_znpr[num]
        rez = CSQ.custom_request_c(CFG.Config.project.db_kplan,f"""
            UPDATE plan SET (Дата_внесения_в_план_месяца, Имя_внесения_в_план_месяца ) = ("{date}","{name_plan}") WHERE Пномер = {num};
            """)
        print(rez)

class Сomparison_fields_vs_db_field():
    def __init__(self,name_column_plan:str,name_tbl_db:str,name_field_db:str):
        self.name_column_plan:str|None = name_column_plan
        self.name_tbl_db:str|None = name_tbl_db
        self.name_field_db:str|None = name_field_db
        if self.name_tbl_db == 'plan':
            ind_field = 'Пномер'
        else:
            ind_field = 'НомПл'
        self.ind_field:str = ind_field

class Сomparison_fields_vs_db():
    def __init__(self,list_fields:list[Сomparison_fields_vs_db_field]):
        tbl = DTCLS.app_self.ui.tbl_kal_pl
        t = CQT.TableContext(tbl)
        self.t: CQT.TableContext = t
        self.list_fields:list[Сomparison_fields_vs_db_field] = []
        self.dict_hierarchy_tbls_db = dict()
        self.db = CFG.Config.project.db_kplan
        self.kpls:dict[int,CQT.TableRow] = self._get_active_kpl_nums()
        for field in list_fields:
            if field.name_column_plan in t.nf:
                self.list_fields.append(field)
                if field.name_tbl_db not in self.dict_hierarchy_tbls_db:
                    self.dict_hierarchy_tbls_db[field.name_tbl_db]={'items_fields':[],
                                                                    'ind_field':field.ind_field}
                self.dict_hierarchy_tbls_db[field.name_tbl_db]['items_fields'].append(field)
        self._check_existance()


    def _check_existance(self):
        list_tbls = CSQ.get_list_of_tables_c(self.db)
        exist_tbls = dict()
        not_exist_tbls = set()
        for it in self.list_fields:
            tbl_name = it.name_tbl_db
            field_name = it.name_field_db
            if tbl_name in list_tbls:
                if tbl_name not in exist_tbls:
                    exist_tbls[tbl_name] = {'ind_field':it.ind_field,'field_name':[]}
                exist_tbls[tbl_name]['field_name'].append(field_name)
            else:
                not_exist_tbls.add(tbl_name)
        if not_exist_tbls:
            raise ValueError(f'reload_fields_from_db err: tbls "{not_exist_tbls}" not found in db "{self.db}"')

        not_exist_fields = set()
        for tbl_db, fields_inf in exist_tbls.items():
            fields = fields_inf['field_name']
            ind_field = fields_inf['ind_field']

            list_fields_db = CSQ.dict_types_tbl(self.db, tbl_db)
            if ind_field not in list_fields_db:
                raise ValueError(f'reload_fields_from_db err: ind_field "{ind_field}" not found in tbl: {tbl_db}, db: "{self.db}"')

            for field_name in fields:
                if field_name not in list_fields_db:
                    not_exist_fields.add(f'{tbl_db}.{field_name}')
        if not_exist_fields:
            raise ValueError(f'reload_fields_from_db err: fields "{not_exist_fields}" not found in db "{self.db}"')

    def _get_active_kpl_nums(self)->dict:
        kpls = dict()
        for it in self.t.rows():
            kpls[int(it.value('plan.Пномер'))]=it
        return kpls

    @CQT.onerror
    def reload_fields_from_db(self)->tuple[bool,dict]:
        def norm(v):
            return '' if v is None else str(v)


        rez = dict()
        suc_iter = False
        limit = 1000
        start = 0
        if not self.kpls:
            return suc_iter,rez
        list_kpls = list(self.kpls.keys())
        with CQT.table_updating(self.t.tbl):
            while start < len(self.kpls):
                chunk_kpl = list_kpls[start:start+limit]
                start = start+limit
                if not chunk_kpl: continue
                for tbl_db, fields_name in self.dict_hierarchy_tbls_db.items():
                    select_fields = [_.name_field_db for _ in fields_name['items_fields']]
                    text = f'''SELECT {", ".join(select_fields)}, {fields_name['ind_field']} as id_row from {tbl_db} 
                            WHERE {fields_name['ind_field']}
                        in ({", ".join([str(_) for _ in chunk_kpl])});'''
                    data = CSQ.custom_request_c(self.db,text,rez_dict=True)
                    dict_data = F.deploy_dict_c(data,'id_row')
                    for item in fields_name['items_fields']:
                        name_field_db = item.name_field_db
                        name_column_plan = item.name_column_plan
                        for kpl in chunk_kpl:
                            row = self.kpls.get(kpl)
                            if not row: continue
                            new_val = None
                            if kpl in dict_data:
                                new_val = dict_data[kpl][name_field_db]
                            if new_val is  None:
                                continue

                            suc_iter = True
                            old_val = row.value(name_column_plan)
                            if norm(new_val) != norm(old_val):
                                row.set_value(name_column_plan, new_val)
                                if kpl not in rez:
                                    rez[kpl] = []
                                rez[kpl].append({'Поле':name_column_plan,
                                          'Было':old_val,
                                          'Стало':new_val})
        return suc_iter,rez






@CQT.onerror
def get_history(self: mywindow):
    tbl = self.ui.tbl_kal_pl
    row_data = CQT.get_dict_line_form_tbl(tbl)
    row_num = int(row_data['plan.Пномер'])
    column = tbl.horizontalHeaderItem(tbl.currentColumn()).text()
    obj_jur = CMS.Logs(self.bd_files)
    history_list = obj_jur.get_history(row_num, column, obj_name='MKart$tbl_kal_pl')
    CQT.msgboxg_get_table(self, 'Журнал изменений', history_list, 'ясно', 'понятно')

@CQT.onerror
def set_group_close(self:mywindow, gr_name:str, close:bool=True, dict_filtr:dict=None):
    tbl = self.ui.tbl_kal_pl
    nf_type_gr = CQT.num_col_by_name_c(tbl, 'plan.ТипГр')
    nf_gr = CQT.num_col_by_name_c(tbl, 'plan.Группа')
    nf_s_num = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
    if dict_filtr is None:
        dict_filtr = CMS.apply_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl, False,
                                   get_dict_by_fild='plan.Пномер')

    tbl_hide = tbl.setRowHidden
    tbl_item = tbl.item
    tbl_rowcount = tbl.rowCount()

    for i in range(tbl_rowcount):
        gr_item = tbl_item(i, nf_gr)
        type_item = tbl_item(i, nf_type_gr)
        if not gr_item or not type_item:
            continue

        if gr_item.text() == gr_name and type_item.text() == DOC_EMOJI:
            s_num_item = tbl_item(i, nf_s_num)
            if not s_num_item:
                continue
            s_num = s_num_item.text()

            # вычисляем условие видимости
            if close:
                tbl_hide(i, True)
            else:
                if s_num in dict_filtr:
                    if dict_filtr[s_num]:
                        tbl_hide(i, False)
                    else:
                        tbl_hide(i, True)


@CQT.onerror
def close_all_groups(self:mywindow):
    tbl = self.ui.tbl_kal_pl

    with CQT.table_updating(tbl):
        nf = CQT.nums_col_by_name_dict(tbl)
        col_group = nf['plan.Группа']
        dict_filtr = CMS.apply_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl, False,
                                       get_dict_by_fild='plan.Пномер')
        groups = set()
        for i in range(tbl.rowCount()):
           gr = tbl.item(i, col_group).text()
           if gr:
               groups.add(gr)

        for gr in groups:
            set_group_close(self,gr,dict_filtr=dict_filtr)

        CMS.apply_gui_groups(self)


@CQT.onerror
def delete_from_cell(self:mywindow):
    tbl = self.ui.tbl_kal_pl
    full_name_field = tbl.horizontalHeaderItem(tbl.currentColumn()).text()
    fl_access = CMS.access_kpl_tbl(self.Data_plan.DICT_INFO_FIELDS_KPL, full_name_field)
    if fl_access == False:
        CQT.msgbox(f'Нет доступа')
        return
    row = tbl.currentRow()
    col = tbl.currentColumn()
    if not CQT.msgboxgYN(f'Удалить данные с ячейки?\n Строка: {row}\nКолонка: {col}\nЗначение: `{tbl.item(row,col).text()}`'):
        return
    cellw = tbl.cellWidget(row,col)
    if cellw:
        if isinstance(cellw, QtWidgets.QLabel):
            tbl.removeCellWidget(row,col)
    tbl.item(row,col).setText('')
    tbl_kal_pl_cellChanged(self)



@CQT.onerror
def btn_clear_filtr(self: mywindow, apply=True):
    row = CQT.get_dict_line_form_tbl(self.ui.tbl_kal_pl, 0)
    spis_znach = [['' for _ in range(len(row))]]
    nk_status = CQT.num_col_by_name_c(self.ui.tbl_kal_pl, 'plan.Статус')
    if nk_status != None:
        spis_znach[-1][nk_status] = 'Изготовление|Подготовка|К производству|Резерв|Долгосрочный|Группа'
    CMS.fill_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl, hidden_scroll=True, spis_znach=spis_znach)
    CMS.update_width_filtr(self.ui.tbl_kal_pl, self.ui.tbl_filtr_kal_pl)
    if 'shift' in CQT.get_key_modifiers(self) or apply:
        CMS.apply_filtr_c(self,self.ui.tbl_filtr_kal_pl,self.ui.tbl_kal_pl)

def set_groups_kpl(self: mywindow):
    kpl_bool_groups = self.ui.chk_kpl_groups.isChecked()
    if kpl_bool_groups:
        btn_clear_filtr(self, True)

    try:
        CMS.save_tmp_stukt(kpl_bool_groups, 'chk_kpl_groups')
        update_plan_main_tbl(self)

    except:
        pass
def set_params_kpl(self: mywindow):
    kpl_bool_load_zav = self.ui.chk_kpl_zaversch.isChecked()
    try:
        CMS.save_tmp_path('kpl_bool_load_zav', str(int(kpl_bool_load_zav)))
        update_plan_main_tbl(self)
    except:
        pass


def set_chk_paint_dates(self: mywindow):
    chk_paint_dates = self.ui.chk_paint_dates.isChecked()
    try:
        CMS.save_tmp_path('kpl_bool_paint_dates', str(int(chk_paint_dates)))
    except:
        pass



def chk_autorepeat_update_fact(self: mywindow):
    chk_autorepeat_update_fact = self.ui.chk_autorepeat_update_fact.isChecked()
    if chk_autorepeat_update_fact:
        if not CQT.msgboxgYN(f'Включить автообновление факта плана каждые 120 минут?' ):
            self.ui.chk_autorepeat_update_fact.blockSignals(True)
            self.ui.chk_autorepeat_update_fact.setChecked(False)
            self.ui.chk_autorepeat_update_fact.blockSignals(False)
            return
    CSQ.custom_request_c(CFG.Config.project.db_naryad, f"""UPDATE places 
    SET autoload_fact_kpl_onoff = {F.valm(chk_autorepeat_update_fact)} 
    where poki = {self.place.poki}""")


@CQT.onerror
def clck_tbl_kal_pl_tbl(self:mywindow, *args):
    self.current_kpl_table = 'tbl_preview'
    tbl = self.ui.tbl_kal_pl
    CQT.summ_selct_tbl(self, tbl)
    select_row(self)
    if not self.ui.fr_tree_fields.isHidden():
        GPL.load_fields_for_tree(self)
    if not self.ui.fr_pull_poz.isVisible():
        return
    POZPL.clck_tbl_kal_pl(self)


@CQT.onerror
def clck_tbl_pl_gaf(self:mywindow, tbl:QtWidgets.QTableWidget):
    CQT.summ_selct_tbl(self, tbl)
    if is_local_gant_hidden(self):
        return
    nf_id_kpl = CQT.num_col_by_name_c(tbl,'_id_poz')
    it = tbl.item(tbl.currentRow(),nf_id_kpl)
    if it:
        id_kpl = int(it.text())
        prepare_local_gant_and_poz_info(self,forced_kpl_id=id_kpl)






def add_excell(list):
    list_of_pr = F.open_file_c(r'O:\Производство Powerz\Отдел технолога\ТД\Учет табель\бд_проекты\BD_Proect.txt',
                               separ='|', utf8=False)
    for i, item in enumerate(list_of_pr):
        if i < 5:
            continue
        nompr = str(item[0])
        nompy = str(item[1])
        vid = item[2]
        status = item[3]
        datakd = item[4]
        sb = item[6].replace('&', '')
        kolvo = item[8]
        napravl_deyat = ''
        nomen_erp = ''
        dataotgr = item[9]
        ves = F.valm(item[10].replace('&', ''))
        prim = item[11]
        tehnolog = item[16]
        datazayavk = item[17]
        datakd_plan = item[19]
        pkk = item[20]
        datatd = item[21]
        napravl = item[22]
        prioritet = item[23]

        if F.is_numeric(sb):
            sb = F.valm(sb)
            udvestd = round(sb * 2 / 8 * 102)
        else:
            sb = 1
            udvestd = 1
        if item[7] == '?':
            etap = 0
        else:
            etap = 1
        list.append(
            ['', datazayavk, nompr, nompy, '00', vid, napravl_deyat, nomen_erp, kolvo, 1, dataotgr, '', '', 1, 1, pkk,
             tehnolog, status, datakd_plan, datakd, ves, napravl, "", datatd, "", udvestd, 1, 1, 1, "", 1, "",
             round(sb * 2, 2), "", 1, "", 1, "", "", etap, prim, prioritet, ''])
    return list


def load_table_add(self):
    pass


@CQT.onerror
def copy_excel_local(self: mywindow):
    row = CQT.get_dict_line_form_tbl(self.ui.tbl_kal_pl)
    putf = F.put_po_umolch()
    wb_name = f"КПЛ_{row['plan.Пномер']}_{F.now('%Y_%m_%d_%H_%M')}"
    ws_name = '1'
    tbl = self.ui.tbl_preview
    hat = F.list_of_dicts_to_list_of_lists([row])
    hat = F.transpose_list_of_lists(hat)
    file_path = CEX.save_table_colour(tbl, putf, wb_name, ws_name, hat=hat)
    F.run_file_os_c(file_path)


@CQT.onerror
def copy_exel_svod(self: mywindow):
    putf = F.put_po_umolch()
    wb_name = f'КПЛ_СВ_{F.now("%Y_%m_%d_%H_%M")}'
    ws_name = '1'
    tbl = self.ui.tbl_pl_gaf
    file_path = CEX.save_table_colour(tbl, putf, wb_name, ws_name)
    F.run_file_os_c(file_path)




