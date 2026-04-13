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

@CQT.onerror
def update_comp_files():
    tbl = DTCLS.app_self.ui.tbl_comp_files
    tblf = DTCLS.app_self.ui.tbl_comp_files_filtr
    comps = CMS.Compositions()
    DTCLS.compositions = comps
    templ = comps.template()

    CQT.fill_wtabl(templ,tbl,styleSheet=CQT.MES_CSS,selectionBehavior="SelectRows",sortingEnabled=True,
                   aliases_header=CMS.Composition.ALIASES)
    t = CQT.TableContext(tbl)
    with CQT.table_updating(tbl):
        if not CFG.Config.user_config.is_developer:
            t.hide_startsunderscore(True)

        CMS.load_column_widths(DTCLS.app_self,tbl)
        CMS.fill_filtr_c(DTCLS.app_self,tblf,tbl)


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
        comp = CMS.Compositions.add_new_comp()
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
            if not poz_comp.upload():
                return False

        return True


def ________TBLS_______________():
    pass
@CQT.onerror
def btn_comp_load_file(id_file:int|None = None,*args):
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
    comp = DTCLS.compositions.find(id)
    comp.load_pozs()
    comp.recalc_signed()
    comp.recalc_coupled()
    comp.recalc_finished()
    if comp.is_edited:
        btn_update_files(DTCLS.app_self)
        comp.set_not_edited()
    templ = comp.template_pozs()

    CQT.fill_wtabl(templ, tbl, styleSheet=CQT.MES_CSS, selectionBehavior="SelectRows", sortingEnabled=True,
                   aliases_header=CMS.Composition_poz.ALIASES)
    t = CQT.TableContext(tbl)
    with CQT.table_updating(tbl):
        if not CFG.Config.user_config.is_developer:
            t.hide_startsunderscore(True)
        CMS.load_column_widths(DTCLS.app_self, tbl)
        CMS.fill_filtr_c(DTCLS.app_self, tblf, tbl)


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
    if not CFG.Config.user_config.is_developer:
        t.hide_startsunderscore()

    set_lbl_count_composite_aviable(poz.calc_count_composite(DTCLS.app_self.DICT_DOLGN_ETAP,
                                                             DTCLS.app_self.DICT_EMPLOEE_FULL,
                                                             DTCLS.app_self.DICT_OPER_NAME
    ))
    set_lbl_count_composite_create_aviable(poz.calc_count_create())
    btn_create = DTCLS.app_self.ui.btn_comp_dse_cr_nar
    btn_comp = DTCLS.app_self.ui.btn_comp_dse
    fl_disable_create = False
    fl_disable_comp = False
    if poz.is_coupled:
        fl_disable_create = True
        fl_disable_comp = True
    if poz.count_left_couple <= poz.aviable_to_composite:
        fl_disable_create = True
    btn_create.setEnabled(not fl_disable_create)
    btn_comp.setEnabled(not fl_disable_comp)


    check_count()

def ________BTNS_______________():
    pass

@CQT.onerror
def btn_comp_add_file(app_self,*args):
    def is_composition(data)->bool:
        if '|__|__|__|__|__|__|__|__|__|__|__|__|__|__|__|__|' not in data[5][2]:
            return False
        return True
    default_path = load_last_dir()
    files = CQT.f_dialog_name(app_self,'Выбора карты раскроя',default_path, filtr='*.XLSX',one=False)
    if not files:
        return
    fl_save = False
    dict_comp = dict()
    list_used_names = []
    compositions = CMS.Compositions()
    for file in files:
        fileo = F.Cust_path(file)
        if not fl_save:
            save_last_dir(str(fileo.parent))
        data = CEX.read_file(fileo.path_str,c2=18)
        if not is_composition(data):
            CQT.msgbox(f'Файл {fileo.name} не корректный')
            return
        card_nesting = Card_nesting_powerz(data,fileo)

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
def btn_comp_dse_cr_nar(app_self,*args):
    poz = _get_current_poz_obj()
    if poz is None:
        return
    if poz.is_coupled:
        CQT.msgbox(f'Наряды уже связанны количеством {poz.count_aggregate}')
        return
    template = poz.calc_composite_create_templ()

    def fnc_check_select(btn, dialog, t):
        if btn.text() == 'Ввод':
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
            overrun = [str(_.i + 1) for _ in t.rows() if _.value('Выбрано шт.') > _.value('Доступно')]
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
    new_nar.save()
    for param_o in new_nar.params_o:
        snum_nar = param_o.parent.Пномер
        id_dse = param_o.ДСЕ_ID
        count_nar = param_o.Опер_колво
        n_oper = param_o.Операции_номер
        с_oper = param_o.code_oper
        if not poz.add_associated_dse(snum_nar, id_dse, count_nar, n_oper, с_oper):
            CQT.msgbox(f'Ошибка связывания с нарядом')
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

    template = poz.calc_composite_templ(DTCLS.app_self.DICT_DOLGN_ETAP,
                                                             DTCLS.app_self.DICT_EMPLOEE_FULL,
                                                             DTCLS.app_self.DICT_OPER_NAME)

    def fnc_check_select(btn, dialog, t):
        if btn.text() == 'Ввод':
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

            overrun = [str(_.i + 1) for _ in t.rows() if _.value('Выбрано шт.') > _.value('Кол_во')]
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

    if not  template:
        CQT.msgbox(f'Нарядов для связывания не найдено')
        return

    rez = CQT.msgboxg_get_table(DTCLS.app_self, f'Выбор нарядов для связи на {poz.count_left_couple} шт.', template,
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
        с_oper = item['Код опер.']
        if not poz.add_associated_dse(snum_nar, id_dse, count_nar,n_oper,с_oper):
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

def set_lbl_count_composite_aviable(count:int|str = '-'):
    lbl:CQT.QtWidgets.QLabel = DTCLS.app_self.ui.lbl_compos_count
    lbl.setText(f'Доступно: {count} шт.')

def set_lbl_count_composite_create_aviable(count:int|str = '-'):
    lbl:CQT.QtWidgets.QLabel = DTCLS.app_self.ui.lbl_compos_create_count
    lbl.setText(f'Доступно: {count} шт.')


def _get_current_poz_obj()-> CMS.Composition_poz | None:
    tbl = DTCLS.app_self.ui.tbl_comp_dse
    t = CQT.TableContext(tbl)
    row = t.current_row()
    if row.no_selection:
        return
    id_f = int(row.value('id_file'))
    comp = DTCLS.compositions.find(id_f)
    id_p = int(row.value('id'))
    poz = comp.find_poz(id_p)
    if poz is None:
        CQT.msgbox(f"ДСЕ не найдена в БД")
        return
    return poz
