from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING
import copy

from project_cust_38 import b24_html_content_deployer
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_b24 as CB24
import project_cust_38.Cust_emoji as CEMOJ
import project_cust_38.Cust_Excel as CEX
import datetime as DT
import re
try:
    from dataClass import data_app as DTCLS
except:
    pass

if TYPE_CHECKING:
    from Sozdanie import mywindow


def _______INITS__________():
    pass

def init_data():
    update_comp_files()
    DTCLS.registred_partials = CMS.RegistredPartials()
    DTCLS.registred_partials.load_data()

@CQT.onerror
def update_comp_files():
    tbl = DTCLS.app_self.ui.tbl_comp_files
    tblf = DTCLS.app_self.ui.tbl_comp_files_filtr
    t = CQT.TableContext(tbl)
    if t.count:
        t.save_coord()
    comps = CMS.Compositions(DTCLS.PLACE.poki)
    DTCLS.compositions = comps
    templ = comps.template()

    CQT.fill_wtabl(templ,tbl,styleSheet=CQT.MES_CSS,selectionBehavior="SelectRows",sortingEnabled=True,
                   aliases_header=CMS.Composition.ALIASES)
    t = CQT.TableContext(tbl)
    with CQT.table_updating(tbl):
        if not CFG.Config.user_config.is_developer:
            t.hide_startsunderscore(True)

        CMS.load_column_widths(DTCLS.app_self,tbl)
        CMS.fill_filtr_c(DTCLS.app_self,tblf,tbl,hidden_scroll=True,show_header=False)
    t.restore_selected_cell()


@CQT.onerror
def load_last_dir()->str:
    return CMS.load_tmp_path('comp_add_file')

@CQT.onerror
def save_last_dir(path:str):
    CMS.save_tmp_path('comp_add_file',path,)

class Card_nesting_powerz_dse():
    def __init__(self,item:dict):
        self.poz:int = item['Позиция №']
        self.project :str = item['проект']
        self.dse_dft: str =  item['Список деталей']
        self.time: DT.timedelta = item['время шт.']
        self.count: int = item['шт. на лист.']

    def __repr__(self):
        return f'{self.dse_dft} - {self.count} шт.'


class Card_nesting_kelast():
    DIR_FILES_COMP = r'Z:\Data\Создание\compositions'
    OPER_CODE = "ТОК.1"
    RC = {"10101","10102"}
    def __init__(self,data:list[list[str]],fileo:F.Cust_path):

        num = F.Cust_path(data[1][0])
        num.clean_and_normalize_path_part()
        self.fileo:F.Cust_path = fileo
        self.num:str = num.path_str
        self.comment:str = data[1][1].replace('примечание:','').strip()
        self.given_out:str = data[3][17].replace('Выдан:','').strip()
        self.material_name:str = data[4][3].strip()
        self.material_thickness:str = data[4][6].replace('≠','').strip()
        self.count:int = int(data[5][2].replace('Количество повторений: ','').split('|')[0])
        local_data = data[5][0].replace('Раскрой: ','').split(' из ')
        self.local_num:int = int(local_data[0])
        self.local_count:int = int(local_data[1])

        if F.is_numeric(self.count):
            self.count = int(self.count)
        else:
            self.count = 1
        self.dse:list[Card_nesting_powerz_dse] = []
        start_table_row = 8
        end_table_row = 8
        for ind in range(start_table_row,len(data)-1):
            if data[ind][0] == '':
                end_table_row = ind-1
                break
        tbl = F.list_of_lists_to_list_of_dicts(data[start_table_row:end_table_row+1])
        for item in tbl:
            dse_comp = Card_nesting_powerz_dse(item)
            if 'ТОП.ПР.008' in dse_comp.dse_dft:
                continue
            self.dse.append(dse_comp)
    @property
    def store_name(self)->str:
        return f'{self.num} N{self.local_num} из {self.local_count}{self.fileo.extension}'
    @property
    def store_path(self)->str:
        return F.sep().join([self.DIR_FILES_COMP, self.store_name])

    def __repr__(self):
        return f'{self.given_out} {self.material_name}{self.material_thickness} - {len(self.dse)} поз.'

    def add_to_db(self,new_path)->bool:
        comp = CMS.Compositions.add_new_comp(DTCLS.PLACE.poki)
        comp.name = self.num

        comp.path = new_path
        comp.count = self.count
        comp.comment = self.comment
        comp.given_out = self.given_out
        comp.material_name = self.material_name
        comp.material_thickness = self.material_thickness
        comp.local_num = self.local_num
        comp.local_count = self.local_count
        comp.oper_code = self.OPER_CODE
        comp.rc = self.RC


        if not comp.upload():
            return False
        for poz in self.dse:
            poz_comp = comp.add_poz()
            poz_comp.id_file = comp.id
            poz_comp.dse = '_'.join(poz.dse_dft.split('_')[1:]).replace('.dft','')
            poz_comp.count = poz.count
            poz_comp.proj = ''
            poz_comp.py = ''
            if '-' in poz.project:
                poz_comp.proj, poz_comp.py = poz.project.split('-')

            poz_comp.mk = int(poz.dse_dft.split('_')[0])
            if poz_comp.proj == '' and poz_comp.py == '':
                poz_comp.proj, poz_comp.py, poz.project = self.load_pr_py_by_mk(poz_comp.mk,poz.project)
            if not poz_comp.upload():
                return False

        return True

    def load_pr_py_by_mk(self,mk:int,project:str)->tuple[str,str,str]:
        data = CSQ.custom_request_c(DTCLS.PROJECT.db_kplan,f"""SELECT  знпр.№проекта, знпр.№ERP FROM mk
            INNER JOIN пл_оуп ON пл_оуп.НомПл == mk.НомКплан 
            INNER JOIN знпр ON знпр.s_num == пл_оуп.Пномер_ЗП WHERE mk.Пномер = {mk} """, rez_dict=True,one=True,attach_dbs=DTCLS.PROJECT.db_naryad)
        if data:
            erp = data['№ERP'].split('-')[-1].lstrip('0')
            np = data['№проекта']
            limit = 3
            if len(np) > limit:
                np = np[-limit:]
            return np , erp, f"{np}-{'0'*(4-len(str(erp)))}{erp}"
        return '','', project



class Card_nesting_powerz():
    DIR_FILES_COMP = r'Z:\Data\Создание\compositions'
    OPER_CODE = "9171"
    RC = "01010"
    def __init__(self,data:list[list[str]],fileo:F.Cust_path):
        data = [['' if v is None else v for v in _] for _ in data]
        num = F.Cust_path(data[0][0])
        num.clean_and_normalize_path_part()
        self.fileo:F.Cust_path = fileo
        self.num:str = num.path_str
        self.comment:str = data[1][1].replace('примечание:','').strip()
        self.given_out:str = data[3][17].replace('Выдан:','').strip()
        self.material_name:str = data[4][3].strip()
        self.material_thickness:str = data[4][6].replace('≠','').strip()
        self.count:int = int(data[5][2].replace('Количество повторений: ','').split('|')[0])
        local_data = data[5][0].replace('Раскрой: ','').split(' из ')
        self.local_num:int = int(local_data[0])
        self.local_count:int = int(local_data[1])

        if F.is_numeric(self.count):
            self.count = int(self.count)
        else:
            self.count = 1
        self.dse:list[Card_nesting_powerz_dse] = []
        start_table_row = 8
        end_table_row = 8
        for ind in range(start_table_row,len(data)-1):
            if data[ind][0] == '':
                end_table_row = ind-1
                break
        tbl = F.list_of_lists_to_list_of_dicts(data[start_table_row:end_table_row+1])
        for item in tbl:
            dse_comp = Card_nesting_powerz_dse(item)
            if 'ТОП.ПР.008' in dse_comp.dse_dft:
                continue
            self.dse.append(dse_comp)
    @property
    def store_name(self)->str:
        return f'{self.num} N{self.local_num} из {self.local_count}{self.fileo.extension}'
    @property
    def store_path(self)->str:
        return F.sep().join([self.DIR_FILES_COMP, self.store_name])

    def __repr__(self):
        return f'{self.given_out} {self.material_name}{self.material_thickness} - {len(self.dse)} поз.'

    def add_to_db(self,new_path)->bool:
        comp = CMS.Compositions.add_new_comp(DTCLS.PLACE.poki)
        comp.name = self.num

        comp.path = new_path
        comp.count = self.count
        comp.comment = self.comment
        comp.given_out = self.given_out
        comp.material_name = self.material_name
        comp.material_thickness = self.material_thickness
        comp.local_num = self.local_num
        comp.local_count = self.local_count
        comp.oper_code = self.OPER_CODE
        comp.rc = self.RC


        if not comp.upload():
            return False
        if not self._add_to_db_dse(comp):
            return False
        return True

    def _add_to_db_dse(self,comp:CMS.Composition):
        for poz in self.dse:
            poz_comp = comp.add_poz()
            poz_comp.id_file = comp.id
            poz_comp.dse = '_'.join(poz.dse_dft.split('_')[1:]).replace('.dft','')
            poz_comp.count = poz.count
            poz_comp.proj = ''
            poz_comp.py = ''
            if '-' in poz.project:
                poz_comp.proj, poz_comp.py = poz.project.split('-')

            poz_comp.mk = int(poz.dse_dft.split('_')[0])
            if poz_comp.proj == '' and poz_comp.py == '':
                poz_comp.proj, poz_comp.py, poz.project = self.load_pr_py_by_mk(poz_comp.mk,poz.project)
            if not poz_comp.upload():
                return False
        return True

    def load_pr_py_by_mk(self,mk:int,project:str)->tuple[str,str,str]:
        data = CSQ.custom_request_c(DTCLS.PROJECT.db_kplan,f"""SELECT  знпр.№проекта, знпр.№ERP FROM mk
            INNER JOIN пл_оуп ON пл_оуп.НомПл == mk.НомКплан 
            INNER JOIN знпр ON знпр.s_num == пл_оуп.Пномер_ЗП WHERE mk.Пномер = {mk} """, rez_dict=True,one=True,attach_dbs=DTCLS.PROJECT.db_naryad)
        if data:
            erp = data['№ERP'].split('-')[-1].lstrip('0')
            np = data['№проекта']
            limit = 3
            if len(np) > limit:
                np = np[-limit:]
            return np , erp, f"{np}-{'0'*(4-len(str(erp)))}{erp}"
        return '','', project




def ________TBLS_______________():
    pass

def reload_dse_from_comp(comp:CMS.Composition):
    fileo = F.Cust_path(comp.path)
    data = None
    if CFG.Config.place.poki == 0:
        data = CEX.read_file(fileo.path_str, c2=18)
        if not is_composition(data):
            CQT.msgbox(f'Файл {fileo.name} не корректный')
            return
        card_nesting = Card_nesting_powerz(data, fileo)
        card_nesting._add_to_db_dse(comp)

@CQT.onerror
def btn_comp_load_file(id_file:int|None = None,*args):

    def fnc_clear_new_name(lbl:CQT.InteractiveLabelInstance,app_self,i,j,row_o:CQT.TableRow,*args):
        poz = _get_poz_obj(row_o)
        if poz is None:
            return
        poz.nn_hand_compare = None
        poz.id_dse_mk_hand_compare = None
        poz.upload()
        row_o.set_value('nn_hand_compare', '')
        lbl.set_text('')
        tbl_comp_dse()
    def fnc_select_new_name(lbl:CQT.InteractiveLabelInstance,app_self,i,j,row_o:CQT.TableRow,*args):
        poz = _get_poz_obj(row_o)

        template = []  # Naryads(165205,CFG.Config.project.db_naryad,None,CFG.Config.project.db_users)
        res = poz.res
        for dse in res.data:
            for oper in dse.Операции:
                if not oper.Опер_код == poz.parent.oper_code:
                    continue
                available = dse.Количество - oper.Освоено  # available = 2
                excess_count_dse = dse.Количество - poz.count_aggregate
                if excess_count_dse >=0:
                    template.append({
                        'МК': res.mk.Пномер,
                        '_ДСЕ ID': dse.Номерпп,
                        'ДСЕ Наим.': dse.Наименование,
                        'ДСЕ НН': dse.Номенклатурный_номер,
                        'Опер. Код': oper.Опер_код,
                        'Опер. Наименование': oper.Опер_наименование,
                        'Опер. Номер': oper.Опер_номер,
                        'Опер. Tпз': oper.Опер_Тпз,
                        'Опер. Tшт': oper.Опер_Тшт_ед,
                        'КОИД': oper.Опер_КОИД,
                        '_Опер. Проф.Код': oper.Опер_профессия_код,
                        '_Опер. Проф.': oper.Опер_профессия_наименование,
                        'Кол-во ДСЕ': dse.Количество,
                        'Доступно': available
                    })
        if not template:
            CQT.msgbox('Нет подходящих ДСЕ')
            return
        rez = CQT.msgboxg_get_table(DTCLS.app_self,'Выбор имени',template,selectRows=True,styleSheet=CQT.MES_CSS,selection_from_tbl=True,ExtendedSelection=False)
        if not rez:
            return
        poz.nn_hand_compare = rez['ДСЕ НН']
        poz.id_dse_mk_hand_compare = int(rez['_ДСЕ ID'])
        poz.upload()
        row_o.set_value('nn_hand_compare', poz.nn_hand_compare)
        lbl.set_text(poz.nn_hand_compare)
        tbl_comp_dse()
        return
    def fnc_dbl_click_dse(t:CQT.TableContext,i,name_clmn:str, *args):
        def fnc_oform_tbl_parts(tbl,*args):
            t = CQT.TableContext(tbl)
            count_parts = 0
            for row in t.rows():
                count_parts = int(row.value('Частей\nв раскроях'))
            step = round(100/count_parts)
            for row in t.rows():
                part = int(row.value('Часть'))
                clr = CMS.Color_tbl(part*step)
                row.set_color_background(*clr.rgb)
            pass

        poz = _get_poz_obj(t.get_row(i))
        if not poz:
            return CQT.msgbox('Позиция не найдено')
        parts = DTCLS.part_manager.get_dict_parts(poz.id)
        if not parts:
            return CQT.msgbox('Частей ДСЕ не найдено')

        template = []
        dict_pozs = dict()
        dict_mks = dict()
        dict_files = dict()
        for _ in parts.values():
            if _.id_f not in dict_files:
                file_for_part = DTCLS.compositions.find(_.id_f)
                file_for_part.load_pozs(DTCLS.part_manager)
                file_for_part.load_dict_res_o()
                file_for_part.recalc_registred_partial(DTCLS.registred_partials)
                dict_files[_.id_f] = file_for_part
            else:
                file_for_part = dict_files[_.id_f]



            poz_for_part = file_for_part.find_poz(_.id_dse)
            if (poz_for_part.id_kpl,poz_for_part.mk,_.nn_raw) not in dict_mks:

                poz_for_part.calc_count_by_mk()

                dict_mks[(poz_for_part.id_kpl,poz_for_part.mk,_.nn_raw)] = poz_for_part
            else:
                poz_for_part = dict_mks[(poz_for_part.id_kpl,poz_for_part.mk,_.nn_raw)]

            dict_pozs[(_.id_f, _.id_dse)] = poz_for_part

        for _ in parts.values():

            registered_count_per_dse_val = poz.registered_count_per_dse(_)
            registered_count_per_project_val = poz.registered_count_per_project(_)
            poz_for_part = dict_pozs[(_.id_f,_.id_dse)]
            templ_row ={
            'КПЛ №': poz_for_part.id_kpl,
            'Кол-во изд.\nпо КПЛ': poz_for_part.count_kpl,

            'МК №': poz_for_part.mk,
            'Кол-во изд.\nв МК': poz_for_part.count_izd,
            'Общee\nкол-во ДСЕ': poz_for_part.count_count_aggregate_dse,

            'Раскрой\n№': _.id_f,
            '№\nсегмента': _.id_dse,
            'Сегмент\nв раскрое': _.nn_raw,
            'Часть': _.part,
            'Частей\nв раскроях': _.total_parts,
            'Кол-во\nв раскрое': _.total_count_dse,
            'Сегмент\nзарег-ан':_.is_exists_registered_parts(poz.registred),
            'Плановая\nДСЕ':_.registered_dse(poz.registred,DTCLS.registred_partials),
            'Рег.кол-во\nна изд.':registered_count_per_project_val if registered_count_per_project_val else '',
            'Рег.кол-во\nна ДСЕ':registered_count_per_dse_val if registered_count_per_dse_val else '',
            'Связано': _.calc_summ_coupled(poz.parts_couples,poz.registred,poz.parts)
          }
            template.append(templ_row)
        template.sort(key=lambda _: _['Часть'])
        template.sort(key=lambda _: _['Сегмент\nв раскрое'])
        rez = CQT.msgboxg_get_table_ok_inf(DTCLS.app_self,'Загруженные части',template,styleSheet=CQT.MES_EDIT_CSS,func_oform_tbl=fnc_oform_tbl_parts)
        return
    def fnc_dbl_click_mk(t:CQT.TableContext,i,name_clmn:str, *args):
        poz = _get_poz_obj(t.get_row(i))
        template = []  # Naryads(165205,CFG.Config.project.db_naryad,None,CFG.Config.project.db_users)
        res = poz.res
        for dse in res.data:
            for oper in dse.Операции:
                if not oper.Опер_код == poz.parent.oper_code:
                    continue
                available = dse.Количество - oper.Освоено  # available = 2
                template.append({
                    'МК': res.mk.Пномер,
                    'Кол-во изд.\nв МК': poz.count_izd,
                    'КПЛ №': poz.id_kpl,
                    'Кол-во изд.\nпо КПЛ': poz.count_kpl,
                    '_ДСЕ ID': dse.Номерпп,
                    'ДСЕ Наим.': dse.Наименование,
                    'ДСЕ НН': dse.Номенклатурный_номер,
                    'Опер.\nКод': oper.Опер_код,
                    'Опер.\nНаименование': oper.Опер_наименование,
                    'Опер.\nНомер': oper.Опер_номер,
                    'Опер.\nTпз': oper.Опер_Тпз,
                    'Опер.\nTшт': oper.Опер_Тшт_ед,
                    'КОИД': oper.Опер_КОИД,
                    '_Опер.\nПроф.Код': oper.Опер_профессия_код,
                    '_Опер.\nПроф.': oper.Опер_профессия_наименование,
                    'Кол-во\nДСЕ': dse.Количество,
                    'Доступно': available
                })
        if not template:
            CQT.msgbox('Нет подходящих ДСЕ')
            return
        def fnc_oform(tbl):
            t  = CQT.TableContext(tbl)
            t.hide_if_not_dev(CFG,forced_text=True)
        rez = CQT.msgboxg_get_table_ok_inf(DTCLS.app_self, 'МК', template,  styleSheet=CQT.MES_CSS,
                                    func_oform_tbl=fnc_oform)


    tbl_comp_f = DTCLS.app_self.ui.tbl_comp_files
    tbl = DTCLS.app_self.ui.tbl_comp_dse
    CQT.clear_tbl(tbl)
    CQT.clear_tbl(DTCLS.app_self.ui.tbl_comp_dse_chose_nar)
    set_lbl_count_composite_aviable()
    set_lbl_count_composite_create_aviable()
    tblf = DTCLS.app_self.ui.tbl_comp_dse_filtr
    t = CQT.TableContext(tbl_comp_f)
    if id_file is None:
        row = t.current_row()
        if row.no_selection:
            return
        id = int(row.value('id'))
    else:
        id = id_file
    comp:CMS.Composition = DTCLS.compositions.find(id)
    load_partial_poz(comp.name)
    comp.load_pozs(DTCLS.part_manager)
    # ========= для перезагрузки дсе из раскроя если была ошибка =============
    #if not comp.pozs and CFG.Config.user_config.is_developer:
    #    reload_dse_from_comp(comp)
    #    return
    # =========================================================================
    comp.load_dict_res_o()

    comp.recalc_signed()
    comp.recalc_coupled()
    comp.recalc_finished()
    comp.recalc_errors()
    comp.recalc_registred_partial(DTCLS.registred_partials)

    comp.load_count_by_mk()
    if comp.is_edited:
        btn_update_files(DTCLS.app_self)
        comp.set_not_edited()
    templ,templ_data = comp.template_pozs()



    CQT.fill_wtabl(templ, tbl, styleSheet=CQT.MES_CSS, selectionBehavior="SelectRows", sortingEnabled=True,
                   aliases_header=CMS.Composition_poz.ALIASES,dict_or_list_user_data=templ_data)

    t = CQT.TableContext(tbl)
    with CQT.table_updating(tbl):
        t.hide_if_not_dev(CFG,True)

        for row_o in t.rows():
            poz = _get_poz_obj(row_o)

            if poz.count_left_couple != poz.count_aggregate:#Начато связывание - менять ДСЕ для связывания поздно
                continue

            if poz.registred:
                continue
            else:
                continue

            widg = CQT.add_interactive_label(t.tbl, row_o.i, t.nf['nn_hand_compare'], row_o.value('nn_hand_compare'),
                                             parent_self=DTCLS.app_self, grab_style_from_cell=True,
                                             autoupdate_column_size=False)
            widg.add_button('...', 'Выбор',
                            fnc_select_new_name,
                            cell_val=row_o, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                     'icons', 'select_from']))
            widg.add_button('...', 'Очистить',
                            fnc_clear_new_name,
                            cell_val=row_o, img_path=F.sep().join([F.path_to_caller_file_c(),
                                                                   'icons', 'comp_tbl_dse_clear_name']))

        t.add_column_events('mk',on_double_click=fnc_dbl_click_mk)
        t.add_column_events('dse_ui',on_double_click=fnc_dbl_click_dse)
        CMS.load_column_widths(DTCLS.app_self, tbl)
        CMS.fill_filtr_c(DTCLS.app_self, tblf, tbl,hidden_scroll=True,show_header=False)


@CQT.onerror
def tbl_comp_dse(id_poz:int|None =None,*args):
    tbl_ch = DTCLS.app_self.ui.tbl_comp_dse_chose_nar
    poz = _get_current_poz_obj()
    if poz is None:
        return
    templ = poz.load_template_chose_nar()
    CQT.fill_wtabl(templ, tbl_ch, styleSheet=CQT.MES_CSS, selectionBehavior="SelectRows"
                   )
    t = CQT.TableContext(tbl_ch)
    t.hide_if_not_dev(CFG)

    DTCLS.poz_aviable_count_composite = (poz.calc_count_composite(DTCLS.app_self.DICT_DOLGN_ETAP,
                                                             DTCLS.app_self.DICT_EMPLOEE_FULL,
                                                             DTCLS.app_self.DICT_OPER_NAME
    ))
    poz.calc_count_create()

    poz.calc_count_by_mk()


    set_lbl_count_composite_aviable(poz.aviable_to_composite,False)
    set_lbl_count_composite_create_aviable(poz.aviable_to_create,False)
    btn_create = DTCLS.app_self.ui.btn_comp_dse_cr_nar
    btn_comp = DTCLS.app_self.ui.btn_comp_dse
    fl_disable_create = False
    fl_disable_comp = False
    if poz.is_coupled:
        fl_disable_create = True
        fl_disable_comp = True
    if not poz.aviable_to_composite:
        fl_disable_comp = True
    if not poz.aviable_to_create:
        fl_disable_create = True

    btn_create.setEnabled(not fl_disable_create)
    btn_comp.setEnabled(not fl_disable_comp)
    check_count()

def ________BTNS_______________():
    pass


def is_composition(data)->bool:
    def is_empty_row(row):
        row_list = [_.strip() for _ in row]
        if  len(set(row_list))==1 and row_list[0] == '':
            return True
        return False

    if not data:
        return False
    if DTCLS.PLACE.poki == 0:
        if '|__|__|__|__|__|__|__|__|__|__|__|__|__|__|__|__|' not in data[5][2]:
            return False
        return True
    elif DTCLS.PLACE.poki==1:
        if len(data[0]) != 13:
            return False
        if is_empty_row(data[0]) and is_empty_row(data[2]):
            return True
    return False



@CQT.onerror
def btn_comp_add_file(app_self,*args):
    POKI = DTCLS.PLACE.poki

    default_path = load_last_dir()
    if POKI == 0:
        str_filter = '*.XLSX'
    elif POKI==1:
        str_filter = '*.CSV'
    else:
        raise TypeError(f'fnc btn_comp_add_file')

    files = CQT.f_dialog_name(app_self,'Выбора карты раскроя',default_path, filtr=str_filter,one=False)
    if not files:
        return
    fl_save = False
    dict_comp = dict()
    list_used_names = []
    compositions = CMS.Compositions(DTCLS.PLACE.poki)
    for file in files:
        fileo = F.Cust_path(file)
        if not fl_save:
            save_last_dir(str(fileo.parent))
        if fileo.extension.lower() == ".XLSX".lower():
            data = CEX.read_file(fileo.path_str,c2=18)
        elif fileo.extension.lower() == ".CSV".lower():
            data = F.load_file(fileo.path_str,';')
        else:
            raise TypeError(f'fnc btn_comp_add_file')

        if not is_composition(data):
            CQT.msgbox(f'Файл {fileo.name} не корректный')
            return
        if POKI == 0:
            card_nesting = Card_nesting_powerz(data,fileo)
        elif POKI==1:
            card_nesting = Card_nesting_kelast(data, fileo)
        else:
            raise TypeError(f'fnc btn_comp_add_file')

        composition = compositions.find_by_name(card_nesting.store_name)
        if composition:
            list_used_names.append(card_nesting.store_name)
        dict_comp[fileo] = card_nesting


    if list_used_names:
        CQT.msgbox(f'Уже загружены ранее файлы:\n{str(list_used_names)}')
        return

    for patho, card_nesting in dict_comp.items():
        new_path = card_nesting.store_path
        if F.existence_file_c(new_path):
            CQT.msgbox(f'Файл ранее был скопирован {card_nesting.num}')
            return

    for patho, card_nesting in dict_comp.items():
        new_path = card_nesting.store_path
        try:
            F.copy_file_c(patho.path_str,new_path)
        except:
            CQT.msgbox(f'Ошибка копирования файла {card_nesting.num}')
            return
        if not F.existence_file_c(new_path):
            CQT.msgbox(f'Файл не скопирован {card_nesting.num}')
            return

        if not card_nesting.add_to_db(new_path):
            CQT.msgbox(f'Файл не может быть добавлен а БД')

    update_comp_files()

@CQT.onerror
def btn_comp_delete_file(app_self,*args):

    tbl_comp_f = DTCLS.app_self.ui.tbl_comp_files
    tbl = DTCLS.app_self.ui.tbl_comp_dse
    tblf = DTCLS.app_self.ui.tbl_comp_dse_filtr
    t = CQT.TableContext(tbl_comp_f)
    row = t.current_row()
    if row.no_selection:
        return
    id = int(row.value('id'))
    comp = DTCLS.compositions.find(id)

    if not CQT.msgboxgYN(f'Будет полностью удален раскрой {comp.name} и все его связи'):
        return
    if not CFG.Config.user_config.is_developer:
        if comp.is_coupled:
            CQT.msgbox(f'Связанный раскрой удалить нельзя')
            return
        if comp.signed:
            CQT.msgbox(f'Проведенный раскрой удалить нельзя')
            return
    if not comp.delete(CFG.Config.user_config.is_developer):
        return
    if F.existence_file_c(comp.path):
        F.delete_file_c(comp.path)
    CQT.msgbox(f'Успешно')
    update_comp_files()
    btn_comp_load_file()

@CQT.onerror
def btn_fr_comp_dse_nars_delete(app_self,*args):
    tbl_ch = DTCLS.app_self.ui.tbl_comp_dse_chose_nar
    t = CQT.TableContext(tbl_ch)
    cur_nar = t.current_row()
    if cur_nar.no_selection:
        CQT.msgbox('Не выбрана строка')
        return

    couple_o = CMS.Couple_nar_poz.get(int(cur_nar.value('_snum_couple')))

    nar = CMS.Naryads(couple_o.snum_nar,CFG.Config.project.db_naryad,DTCLS.app_self.DICT_DOLGN_ETAP,
                          CFG.Config.project.db_users,DTCLS.app_self.DICT_EMPLOEE_FULL,DTCLS.app_self.DICT_OPER,
                          DTCLS.app_self.DICT_DOLGN_ETAP)
    if nar.Пномер is not None: #не удален ранее
        if nar.get_list_from_jurnal().rows:
            CQT.msgbox('Наряд взят в работу- удаление невозможно')
            return
        if not CQT.msgboxgYN(f'Удалить наряд {nar.Пномер} и очисть связанные данные по раскрою?',
                             app_self=DTCLS.app_self):
            return
    else:
        if not CQT.msgboxgYN(f'Наряд {nar.Пномер} был удален ранее, очисть связанные данные по раскрою?',
                             app_self=DTCLS.app_self):
            return

    if nar.Пномер is not None: #не удален ранее
        if not nar.delete():
            CQT.msgbox('Ошибка удаления')

    composition_poz = couple_o.get_composition_poz()
    load_partial_poz(composition_poz.name)
    composition_poz.del_associated_dse(couple_o.snum_nar,DTCLS.part_manager)
    btn_comp_load_file(composition_poz.parent.id)
    tbl_comp_dse(composition_poz.id)


@CQT.onerror
def is_full_set_upload(cmp:CMS.Composition)->bool:
    cmps_set_locals = set([_.local_num for _ in DTCLS.compositions.comps if _.name == cmp.name])
    suggestion_locals = set(range(1,cmp.local_count+1))
    delta = suggestion_locals - cmps_set_locals
    if delta:
        return False
    return True



@CQT.onerror
def check_poz_parts(poz,*args)->bool:
    if not poz.registred:
        CQT.msgbox(
            f'{CEMOJ.EmojiMain.Эмоции.confused.symbol} составные части не зарегистрированы')
        return False

    if not CFG.Config.user_config.is_developer:
        if not is_full_set_upload(poz.parent):
            CQT.msgbox(
                f'{CEMOJ.EmojiMain.Эмоции.confused.symbol} Есть составные части, но не загружен полный комплект раскроев.')
            return False

    if not DTCLS.part_manager.check_proportions(poz.id):
        CQT.msgbox(f'Пропорции в составных частях не равны')
        return False



    return True

@CQT.onerror
def btn_comp_dse_cr_nar(app_self,*args):
    poz = _get_current_poz_obj()
    if poz is None:
        return
    if poz.is_coupled:
        CQT.msgbox(f'Наряды уже связанны количеством {poz.count_aggregate}')
        return
    if poz.parts:
       if not check_poz_parts(poz):
           return
    part = poz.my_part()
    id_reg_part = None
    if part:
        reg_part = part.registred_part(poz.registred)
        if reg_part:
            id_reg_part = reg_part.segment_id
        if id_reg_part is None:
            CQT.msgbox(f'Не найдена зарегистрированная часть для  {poz.dse}')
            return
    template = poz.calc_composite_create_templ()

    def fnc_check_select(btn, dialog, t):
        if dialog.is_btn_yes_role(btn):
            t = CQT.TableContext(t)
            not_nums = [str(_.i + 1) for _ in t.rows() if not F.is_numeric(_.value('Выбрано шт.'))
                        and _.value('Выбрано шт.') != '']
            if not_nums:
                str_nums = ', '.join(not_nums)
                CQT.msgbox(
                    f'Не числа в графе "Выбрано шт."\n в строках "{str_nums}"')
                return

            summ = sum([F.valm(_.value('Выбрано шт.')) for _ in t.rows()])
            if summ == 0:
                CQT.msgbox(
                    f'не указано количество в графе "Выбрано шт."')
                return
            overrun = [str(_.i + 1) for _ in t.rows() if int(_.value('Выбрано шт.')) > int(_.value('Доступно'))]
            if overrun:
                CQT.msgbox(
                    f'Превышение доступности в графе "Выбрано шт."\n в строках "{overrun}"')
                return

            if summ <= poz.count_aggregate:
                dialog.accept()
            else:
                CQT.msgbox(
                    f'превышение суммарного количества в графе "Выбрано шт."\nВведено {summ}, должно '
                    f'быть не более {poz.count_aggregate}')


        else:
            dialog.reject()

    def fnc_get_table(data, *args):
        return [_ for _ in data if _['Выбрано шт.'] != '']

    def func_oform_tbl(tbl, *args):
        def fnc_dblclick_copy_count(t:CQT.TableContext,i:int,name_clmn:str,*args):
            row = t.get_row(i)
            row.set_value('Выбрано шт.',row.value('Доступно'))

        t = CQT.TableContext(tbl)
        t.set_editable('Выбрано шт.')
        print(t.tbl.property('_drdr'))
        t.add_column_events('Доступно',on_double_click=fnc_dblclick_copy_count)

    if not template:
        CQT.msgbox(f'ДСЕ для создания не найдено')
        return

    rez = CQT.msgboxg_get_table(DTCLS.app_self, f"Создание наряда на {poz.count_left_couple} шт.", template,
                                styleSheet=CQT.MES_EDIT_CSS, selectRows=True, ExtendedSelection=False,
                                not_standart_close=True, func_btn0=fnc_check_select, func_validate=fnc_get_table,
                                func_oform_tbl=func_oform_tbl, showMaximized=True
                                )
    if rez == False:
        return

    nar_norma = 0
    list_params_o = []
    for item in rez:
        time_tmp = (F.valm(item['Опер. Tпз']) + F.valm(item['Опер. Tшт']) *
                    F.valm(item['Выбрано шт.']) / F.valm(item['КОИД']))
        nar_norma += time_tmp
        oper_sort_rab = item['_Опер. Проф.Код']
        if oper_sort_rab in DTCLS.app_self.DICT_PROFESSIONS:
            oper_sort_rab = DTCLS.app_self.DICT_PROFESSIONS[oper_sort_rab]['вид_работ']
        list_params_o.append(CMS.Naryad_param(None,
                                              "$".join([item['ДСЕ Наим.'],item['ДСЕ НН']]),
                                              int(item['_ДСЕ ID']),
                                              item['Опер. Номер'],
                                              item['Опер. Наименование'],
                                              int(item['Выбрано шт.']),
                                              F.valm(time_tmp),
                                              item['_Опер. Проф.'],
                                              oper_sort_rab
        ))
    new_nar = CMS.Naryads.add_new_nar(CFG.Config.project.db_naryad, CFG.Config.project.db_users, poz.mk,
                                      CMS.name_by_empl_c(CFG.Config.user_config.User.ФИО),
                                      f'Произвести работы в соответствии с документом {poz.parent.name}',
                                      nar_norma,
                                      f'Компоновщик нарядов',
                                      poz.parent.rc,
                                      auto_confirm= True,
                                       )
    for param_o in list_params_o:
        new_nar.add_param(param_o)
    new_nar.ФИО = 'Работник Заготовительного Цеха'
    new_nar.save()
    for param_o in new_nar.params_o:
        snum_nar = param_o.parent.Пномер
        id_dse = int(param_o.ДСЕ_ID)
        count_nar = int(param_o.Опер_колво)
        n_oper = param_o.Операции_номер
        c_oper = param_o.code_oper


        if not poz.add_associated_dse(snum_nar, id_dse, count_nar,n_oper,c_oper,id_reg_part):
            CQT.msgbox(f'Ошибка связывания при создании наряда')
            continue

    btn_comp_load_file( poz.parent.id)
    tbl_comp_dse(poz.id)

@CQT.onerror
def btn_comp_dse(app_self,*args):
    poz = _get_current_poz_obj()

    if poz is None:
        return
    if poz.is_coupled:
        CQT.msgbox(f'Наряды уже связанны количеством {poz.count_aggregate}')
        return
    if poz.parts:
       if not check_poz_parts(poz):
           return
    part = poz.my_part()
    id_reg_part = None
    if part:
        reg_part = part.registred_part(poz.registred)
        if reg_part:
            id_reg_part = reg_part.segment_id

        if id_reg_part is None:
            CQT.msgbox(f'Не найдена зарегистрированная часть для  {poz.dse}')
            return
    registered_count_per_dse = None
    if part:
        registered_count_per_dse =poz.registered_count_per_dse(part)
    template = poz.calc_composite_templ(DTCLS.app_self.DICT_DOLGN_ETAP,
                                                             DTCLS.app_self.DICT_EMPLOEE_FULL,
                                                             DTCLS.app_self.DICT_OPER_NAME,
                                        registered_count_per_dse)

    def fnc_check_select(btn, dialog, t):
        if dialog.is_btn_yes_role(btn):
            t = CQT.TableContext(t)
            not_nums = [str(_.i + 1) for _ in t.rows() if not F.is_numeric(_.value('Выбрано шт.'))
                        and _.value('Выбрано шт.') != '']
            if not_nums:
                str_nums = ', '.join(not_nums)
                CQT.msgbox(
                    f'Не числа в графе "Выбрано шт."\n в строках "{str_nums}"')
                return

            summ = sum([F.valm(_.value('Выбрано шт.')) for _ in t.rows()])
            if summ == 0:
                CQT.msgbox(
                    f'не указано количество в графе "Выбрано шт."')
                return

            # нельзя выбрать разные операции( 1 дет =  1 опер)
            tmp_strukt = {}
            for row in t.rows():
                nnar = row.value('Наряд')
                noper = row.value('Имя опер.')
                if row.value('Выбрано шт.'):
                    if nnar not  in tmp_strukt:
                        tmp_strukt[nnar] = []
                    tmp_strukt[nnar].append(noper)

            ower_select = {k: v for k, v in tmp_strukt.items() if len(v)>1}
            if ower_select:
                CQT.msgbox(
                    f'Нельзя выбрать разные операции,(1 наряд - 1 опер):\n{str(ower_select)}')
                return

            overrun = [str(_.i + 1) for _ in t.rows() if int(_.value('Выбрано шт.')) > int(_.value('Кол-во'))]
            if overrun:
                CQT.msgbox(
                    f'Превышение доступности в графе "Выбрано шт."\n в строках "{overrun}"')
                return

            if summ <= poz.count_aggregate:
                dialog.accept()
            else:
                CQT.msgbox(
                    f'превышение суммарного количества в графе "Выбрано шт."\nВведено {summ}, должно '
                    f'быть не более {poz.count_aggregate}')


        else:
            dialog.reject()

    def fnc_get_table(data, *args):
        return [_ for _ in data if _['Выбрано шт.'] != '']

    def func_oform_tbl(tbl, *args):
        t = CQT.TableContext(tbl)
        t.set_editable('Выбрано шт.')
        if not part:
            t.hide('Частей')
        def fnc_dblclick_copy_count(t:CQT.TableContext,i:int,name_clmn:str,*args):
            row = t.get_row(i)
            row.set_value('Выбрано шт.',row.value('Кол-во'))

        t.add_column_events('Кол-во',on_double_click=fnc_dblclick_copy_count)
    if not  template:
        CQT.msgbox(f'Нарядов для связывания не найдено')
        return
    msg = f'Выбор нарядов для связи на {poz.count_left_couple} ДСЕ.'
    if poz.parts:
        msg = f'Выбор нарядов для связи на {poz.count_left_couple_parts} частей.'
    rez = CQT.msgboxg_get_table(DTCLS.app_self, msg, template,
                                styleSheet=CQT.MES_EDIT_CSS, selectRows=True, ExtendedSelection=False,
                                not_standart_close=True, func_btn0=fnc_check_select, func_validate=fnc_get_table,
                                func_oform_tbl=func_oform_tbl,showMaximized=True
                                )
    if rez == False:
        return



    for item in rez:
        snum_nar = int(item['Наряд'])
        id_dse = int(item['N ДСЕ'])
        count_nar = int(item['Выбрано шт.'])
        n_oper = item['№ Опер.']
        c_oper = item['Код опер.']

        if not poz.add_associated_dse(snum_nar, id_dse, count_nar,n_oper,c_oper,id_reg_part):
            CQT.msgbox(f'Ошибка связывания с нарядом')
            return

    btn_comp_load_file(poz.parent.id)
    tbl_comp_dse(poz.id)
    return


@CQT.onerror
def btn_update_files(app_self,*args):
    update_comp_files()


@CQT.onerror
def btn_show_comp_file(app_self,*args):
    t = CQT.TableContext(DTCLS.app_self.ui.tbl_comp_files)
    row = t.current_row()
    if row.i == -1:
        return
    link = row.value('path')
    ext = F.keep_extention_c(link)
    if not F.existence_file_c(link):
        CQT.msgbox(f'Исходник не найден')
        return
    name = row.value('name')
    new_path = F.sep().join([F.tmp_dir_win(),f'{name}{ext}'])
    F.copy_file_c(link,new_path)
    if not F.existence_file_c(new_path):
        CQT.msgbox(f'Недоступно локальное пространство')
        return
    F.run_file_os_c(new_path)


def ________SUBS_______________():
    pass


@CQT.onerror
def check_count(*args):
    pass

def set_lbl_count_composite_aviable(count:int|str|None = '-',parts:dict|None=None):
    lbl:CQT.QtWidgets.QLabel = DTCLS.app_self.ui.lbl_compos_count
    str_alias = 'ДСЕ'
    if parts:
        str_alias = 'частей'
    if count:
        lbl.setText(f'Доступно к связыванию: {count} {str_alias}.')
        return
    lbl.setText(f'Не доступно к связыванию')

def set_lbl_count_composite_create_aviable(count:int|str|None = '-',parts:dict|None=None):
    lbl:CQT.QtWidgets.QLabel = DTCLS.app_self.ui.lbl_compos_create_count
    str_alias = 'ДСЕ'
    if parts:
        str_alias = 'частей'
    if count:
        lbl.setText(f'Доступно к созданию: {count} {str_alias}.')
        return
    lbl.setText(f'Не доступно к созданию')

def _get_poz_obj(row_o:CQT.TableRow)-> CMS.Composition_poz | None:
    id_f = int(row_o.value('id_file'))
    comp = DTCLS.compositions.find(id_f)
    id_p = int(row_o.value('id'))
    if comp.pozs is None:
        comp.load_pozs(DTCLS.part_manager)
    poz = comp.find_poz(id_p)
    if poz is None:
        CQT.msgbox(f"ДСЕ не найдена в БД")
        return
    return poz

def _get_current_poz_obj()-> CMS.Composition_poz | None:
    tbl = DTCLS.app_self.ui.tbl_comp_dse
    t = CQT.TableContext(tbl)
    row = t.current_row()
    if row.no_selection:
        return
    return _get_poz_obj(row)



def load_partial_poz(name_dsp):
    mng = CMS.ManagePartialDse(name_dsp)
    DTCLS.part_manager= mng

