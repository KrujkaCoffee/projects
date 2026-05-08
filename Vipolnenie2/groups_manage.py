from __future__ import annotations

import copy

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
import  project_cust_38.Cust_emoji as CEMOJ
from app_dataclasses import data_app as DTCLS
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vipoln import mywindow
@CQT.onerror
def tbl_edit_gr_groups_click(*args):
    tbl = DTCLS.app_self.ui.tbl_edit_gr_groups
    tbln = DTCLS.app_self.ui.tbl_edit_gr_nars
    t = CQT.TableContext(tbl)
    row = t.current_row()
    id = row.value('id')
    gr = DTCLS.gr_groups_nar.find_gr(int(id))
    if gr is None:
        CQT.msgbox(f'Группа не найдена',app_self=DTCLS.app_self)
        return
    list_nar = gr.load_nars()
    CQT.fill_wtabl(list_nar,tbln,styleSheet=CQT.MES_CSS,selectionBehavior='SelectRows',font_size=12)

@CQT.onerror
def tab_gr_click(*args):
    ind = DTCLS.app_self.ui.tabw_groups.currentIndex()
    name = CQT.object_name_by_index_tab(DTCLS.app_self.ui.tabw_groups,ind)
    if name == 'tab_create':
        DTCLS.app_self.zapoln_tabl_naryadov()
        load_tbl_filter()
    if name == 'tab_edit':
        fill_tab_edit_gr()

def fill_tab_edit_gr():
    tbl = DTCLS.app_self.ui.tbl_edit_gr_groups
    CQT.clear_tbl(tbl)
    grps = CMS.Groups_nar(DTCLS.USER_CONFIG.common_config.db_naryad,DTCLS.app_self, DTCLS.USER_CONFIG.User)
    DTCLS.gr_groups_nar = grps
    list_templ = grps.gen_template()
    CQT.fill_wtabl(list_templ,tbl,styleSheet=CQT.MES_CSS,aliases_header = CMS.Group_nar.ALIASES,
                   selectionBehavior='SelectRows',font_size=12)
    CQT.clear_tbl(DTCLS.app_self.ui.tbl_edit_gr_nars)

def clear():
    DTCLS.app_self.ui.fr_groups.setVisible(False)
    DTCLS.app_self.ui.fr_naryads.setVisible(True)

def toggle_filtr_group_mode(val:bool):
    ui = DTCLS.app_self.ui
    ui.fr_groups.setVisible(val)
    ui.tabWidget_2.setVisible(not val)
    ui.fr_login.setVisible(not val)


def tbl_nar_in_groupsDoubleClicked(i,j,*args):
    t = CQT.TableContext(DTCLS.app_self.ui.tbl_nar_in_groups)
    row = t.get_row(i)
    s_num = row.value('Пномер')
    tg = CQT.TableContext(DTCLS.app_self.ui.tbl_filter_in_groups)
    for row_c in tg.rows():
        gr:Group_filtr = row_c.value('Пномер',get_cust_content=True)
        if int(s_num) in  gr.nnar:
            btn:CQT.QtWidgets.QPushButton = row_c.widget('Пномер')
            btn.setChecked(not btn.isChecked())
            toggle_filtr_btn()
            return
def _detect_gr()-> CMS.Group_nar|None:
    tbl = DTCLS.app_self.ui.tbl_edit_gr_groups
    tbln = DTCLS.app_self.ui.tbl_edit_gr_nars
    t = CQT.TableContext(tbl)
    row = t.current_row()
    id = row.value('id')
    gr = DTCLS.gr_groups_nar.find_gr(int(id))
    if gr is None:
        CQT.msgbox(f'Группа не найдена', app_self=DTCLS.app_self)
        return
    return gr

def _detect_s_num_nar()->[int]:
    tbln = DTCLS.app_self.ui.tbl_edit_gr_nars
    t = CQT.TableContext(tbln)
    selected_rows = t.get_selected_rows()
    if not selected_rows:
        CQT.msgbox(f'Не выбрана строка наряда',app_self=DTCLS.app_self)
        return []
    s_nums = [int(row.value('Пномер')) for row in selected_rows]
    return s_nums
def bnt_group_remove(self:mywindow):#Расформировать группу
    gr = _detect_gr()
    if gr is None:
        return
    if not CQT.msgboxgYN(f'Будет полностью расформирована группа "{gr.name}";',app_self=DTCLS.app_self):
        return
    if not DTCLS.gr_groups_nar.delete_gr([gr.id]):
        CQT.msgbox(f'Ошибка обработки группы',app_self=DTCLS.app_self)
        return
    fill_tab_edit_gr()
    CQT.msgbox(f'Успешно',app_self=DTCLS.app_self)




def bnt_nar_remove(self:mywindow):#Убрать наряд
    s_nums = _detect_s_num_nar()
    if not  s_nums:
        return
    gr = _detect_gr()
    if gr is None:
        return
    warn_remove_gr = ''
    if len(gr.load_s_nums_nar()) - len(s_nums) < 2:
        warn_remove_gr = f'\nИ группа будет расформирована'
    if not CQT.msgboxgYN(f'Будут убраны наряды №№ {", ".join([str(_) for _ in s_nums])} из группы "{gr.name}"{warn_remove_gr}',
                         app_self=DTCLS.app_self):
        return
    gr.remove_nar(s_nums)
    fill_tab_edit_gr()
    t = CQT.TableContext(DTCLS.app_self.ui.tbl_edit_gr_groups)
    if t.tbl.rowCount() == 0:
        return
    for row in t.rows():
        if int(row.value('id')) == gr.id:
            row.set_current('id')
            tbl_edit_gr_groups_click()
@CQT.onerror
def btn_test_apply_gr(self:mywindow,*args):# для теста при разработке
    tbl_nar = DTCLS.app_self.ui.tbl_naryadi
    t = CQT.TableContext(tbl_nar)
    row = t.current_row()
    s_num_gr = row.value('_id')
    if not s_num_gr:
        return
    s_num_nar = row.value('Пномер')
    s_num_nar = 201
    apply_group_event(int(s_num_gr),int(s_num_nar))
    pass

def apply_comp_event(composition:CMS.Composition,s_num_main_nar:int)->bool:
    jur = CMS.Jurnal_nar(DTCLS.USER_CONFIG.common_config.db_naryad, s_num_main_nar, DTCLS.USER_CONFIG.User.ФИО,
                         blob_pass=True)
    if not jur.rows:
        CQT.msgbox(f'Ошибка чтения журнала')
        return False
    jur.select_last_fragment()
    set_nar = composition.get_set_nars(set([_['Пномер'] for _ in DTCLS.table_nar]))
    if not CMS.Group_nar.split_by_group(set_nar, composition.name,
                                        f'Автовставка по раскрою.id {composition.id}', jur.fragment):
        return False
    return True
def apply_group_event(s_num_gr:int,s_num_main_nar:int)->bool:
    DTCLS.gr_groups_nar = CMS.Groups_nar(DTCLS.USER_CONFIG.common_config.db_naryad,DTCLS.app_self,DTCLS.USER_CONFIG.User)
    gr = DTCLS.gr_groups_nar.find_gr(s_num_gr)
    if gr is None:
        CQT.msgbox(f'Ошибка чтения группы')
        return False
    jur = CMS.Jurnal_nar(DTCLS.USER_CONFIG.common_config.db_naryad, s_num_main_nar, DTCLS.USER_CONFIG.User.ФИО,
                         blob_pass=True)
    if not jur.rows:
        CQT.msgbox(f'Ошибка чтения журнала')
        return False
    jur.select_last_fragment()
    not_finished_nars = gr.load_s_nums_nar()
    if s_num_main_nar not in not_finished_nars:
        not_finished_nars.add(s_num_main_nar)
    if not CMS.Group_nar.split_by_group(not_finished_nars,gr.name,
                                        f'Автовставка по гр.id {gr.id}', jur.fragment):
        return False
    return True


@CQT.onerror
def btn_reset_gr(self:mywindow,*args):
    DTCLS.gr_filter_nar.clear_select_headers()
    fill_table_nar({})
@CQT.onerror
def btn_crash_header(self:mywindow,*args):
    set_nnar = DTCLS.gr_filter_nar.calc_selectd_nars()
    DTCLS.gr_filter_nar.clear_select_headers()
    DTCLS.gr_filter_nar.set_select_nnar('Пномер',set_nnar)


@CQT.onerror
def bnt_group_ok(self:mywindow,*args):
    grps = CMS.Groups_nar(DTCLS.USER_CONFIG.common_config.db_naryad,DTCLS.app_self,DTCLS.USER_CONFIG.User)
    set_nnar = DTCLS.gr_filter_nar.calc_selectd_nars()
    gr_name = DTCLS.app_self.ui.le_name_gr.text()
    if len(gr_name)<=5:
        CQT.msgbox(f'Длина имени группы не менее 5 символов',app_self=DTCLS.app_self)
        return
    list_nnar = list(set_nnar)
    if len(list_nnar) < 2:
        CQT.msgbox('Для группировки должно быть выбрано не менее 2 нарядов',app_self=DTCLS.app_self)
        return
    gr = grps.create_new_gr(gr_name)
    if gr is None:
        return
    if not gr.add_nars(list_nnar):
        return

    DTCLS.app_self.zapoln_tabl_naryadov()
    CQT.msgbox(f'Успешно создана группа "{gr.name}"',app_self=DTCLS.app_self)
    toggle_filtr_group_mode(False)


def bnt_group_cancel(self:mywindow):
    toggle_filtr_group_mode(False)


def btn_group_manage(self:mywindow):
    if self.glob_login == "":
        return
    if DTCLS.table_nar is None:
        CQT.msgbox(f'Не сформирована таблица нарядов',app_self=DTCLS.app_self)
        return
    if not DTCLS.USER_CONFIG.is_developer:
        jur_obj = CMS.Jurnal_nar(DTCLS.USER_CONFIG.common_config.db_naryad, user=DTCLS.app_self.glob_fio)
        Номер_наряда, Пномер, Дата = jur_obj.get_ontime_naruad()
        if Номер_наряда:
            CQT.msgbox(f'Для управления группами, необходимо выйти из текущего наряда № {Номер_наряда}',app_self=DTCLS.app_self)
            return
    toggle_filtr_group_mode(True)
    load_tbl_filter()

class Group_filtr():
    def __init__(self,name,parent):
        self.parent:Header_gr_filtr = parent
        self.name:str = name
        self.nnar:set = set()
        self.data_nar:list = []
        self.time:float = 0
        self.btn:CQT.QtWidgets.QPushButton|None = None

    def clear_selected(self):
        self.btn.setChecked(False)

    def add(self,time:float,nnar:int,data_nar:dict):
        self.time+=time
        self.nnar.add(nnar)
        self.data_nar.append(data_nar)
    def str_for_tbl(self):
        cnt = len(self.nnar)
        cnt_str = ''
        if cnt > 1:
            cnt_str = f' - {cnt} шт.'
        return f'{self.name} ({round(self.time,2)} мин.){cnt_str}'
    def __str__(self):
        return f'name:{self.name}, time:{round(self.time,2)}, {len(self.nnar)} nnars'

class Header_gr_filtr():
    def __init__(self, name:str,parent):
        self.parent:Filtr_nar = parent
        self.name: str = name
        self.grs:list[Group_filtr] = list()

    def set_select_nnar(self,set_nnar:set[int]):
        for nnar in set_nnar:
            for gr in self.grs:
                if nnar in gr.nnar:
                    gr.btn.setChecked(True)

    def clear_selected_gr(self):
        for gr in self.grs:
            gr.clear_selected()
    def sort_by_time(self):
        self.grs = sorted(self.grs,key=lambda gr: gr.time)
    def get_gr_num(self,num:int)->str:
        if num >= len(self.grs):
            return ''
        return self.grs[num].str_for_tbl()
    def get_gr_data_num(self,num:int)->Group_filtr|None:
        if num >= len(self.grs):
            return None
        return self.grs[num]

    def add(self,name:str,time:float,nnar:int,data_nar:dict):
        gr = self.find(name)
        if gr is None:
            gr = Group_filtr(name,self)
            self.grs.append(gr)
            self.parent.check_count(self)
        gr.add(time,nnar,data_nar)

    def find(self,name:str)->Group_filtr:
        for it in self.grs:
            if it.name == name:
                return it

    def __str__(self):
        return f'name: {self.name}, grs: {[str(_) for _ in self.grs]}'

class Filtr_nar():
    list_rangire = (
                    'Группа',
                    'Номер_проекта',
                    'Номер_заказа',
                    'Позиция',
                    'Примечание',
                    'Распред_ФИО',
                    'Дата',
                    'Норматив время',
                    'Пномер'
                    )
    def __init__(self):
        self.headers:list[Header_gr_filtr] = [Header_gr_filtr(_,self) for _ in self.list_rangire]
        self._max_count_gr = 0

    def calc_selectd_nars(self)->set:
        list_sets = []
        for h in self.headers:
            tmp_set = set()
            for g in h.grs:
                if g.btn.isChecked():
                    tmp_set |= g.nnar
            if tmp_set:
                list_sets.append(tmp_set)
        if not  list_sets:
            return set()
        return set.intersection(*list_sets)

    def clear_select_headers(self):
        for h in self.headers:
            h.clear_selected_gr()
    def set_select_nnar(self,name_header:str,set_nnar:set[int]):
        h = self.find(name_header)
        h.set_select_nnar(set_nnar)

    def check_count(self,header:Header_gr_filtr):
        if self._max_count_gr < len(header.grs):
            self._max_count_gr = len(header.grs)
    def find(self,name)->Header_gr_filtr:
        for h in self.headers:
            if h.name == name:
                return h

    def add_item(self,item:dict):
        time = item['Норматив время']
        s_num = item['Пномер']
        for k, v in item.items():
            if k == 'Дата':
                v = F.dateStrToStr(v, format="%Y-%m-%d %H:%M:%S", format_out="%d.%m.%Y")
            if v is None:
                v = ''
            if F.is_numeric(v):
                v = str(v)
            h = self.find(k)
            if h is not None:
                h.add(v,time,s_num,item)

    def gen_tbl(self)->list[dict]:
        for header in self.headers:
            header.sort_by_time()
        result = []
        for i in range(self._max_count_gr):
            tmp_row = dict()
            for header in self.headers:
                cell_data = header.get_gr_num(i)
                tmp_row[header.name] = cell_data
            result.append(tmp_row)
        return result

    def gen_data_tbl(self)->list[dict]:
        for header in self.headers:
            header.sort_by_time()
        result = []
        for i in range(self._max_count_gr):
            tmp_row = dict()
            for header in self.headers:
                cell_data = header.get_gr_data_num(i)
                tmp_row[header.name] = cell_data
            result.append(tmp_row)
        return result



def fill_table_nar(set_nars=None):
    tbl_nar_in_groups = DTCLS.app_self.ui.tbl_nar_in_groups
    if set_nars is None:
        set_nars = set()
    nars_tbl = [_ for _ in DTCLS.table_nar if _['Пномер'] in set_nars]
    summ_time = round(sum([_['Норматив время'] for _ in nars_tbl]), 2)

    minutes_remained = DTCLS.production_shift.minutes_till_end()

    DTCLS.app_self.ui.lbl_info_group.setText(f'Выбрано нарядов на {summ_time} мин. из {minutes_remained} мин.')
    percent_covered = 0
    if minutes_remained:
        percent_covered = round(summ_time / minutes_remained, 2) * 100
    if percent_covered > 100:
        percent_covered = 100
    clr = CMS.Color_tbl(percent_covered)
    DTCLS.gr_prgs_bar.set_value(percent_covered)
    DTCLS.gr_prgs_bar.set_color(*clr.rgb)

    tmp_table_nar = copy.deepcopy(DTCLS.table_nar)
    tmp_table_nar = F.insert_key_to_dicts(tmp_table_nar, 0, '', '')
    with CQT.table_updating(tbl_nar_in_groups):
        CQT.fill_wtabl(tmp_table_nar,
                       tbl_nar_in_groups,
                       styleSheet=CQT.MES_CSS,
                       auto_type=False, hide_head_rows=False,font_size=12)
        tn = CQT.TableContext(tbl_nar_in_groups)
        for row in tn.rows():
            s_num = int(row.value('Пномер'))
            if s_num not in set_nars:
                row.set_color_font(200, 200, 200)
            else:
                row.set_value('', CEMOJ.СтатусыПроизводства.success_tin.symbol)
def toggle_filtr_btn():
    filtr = DTCLS.gr_filter_nar
    set_nars = filtr.calc_selectd_nars()
    DTCLS.app_self.ui.le_name_gr.setText(recalc_name_group())
    fill_table_nar(set_nars)

def recalc_name_group()->str:
    EXCLUDE_FIELDS = ('','Группа','Пномер','ФИО','ФИО2','Твремя',
                      'Норматив время',
                      'Время',
                      'Компл_номер_тара',
                      'Компл_адрес',
                      'Внеплан',
                      'Приоритет',
                      'Коэфф_сложности',
                      'Виды_работ',
                      'Опер_время',
                      'Статус_ЧПУ',
                      'Прим_резка',
                      'ФИО_для_ОТК',
                      'Операции',
                      'Распред_ФИО',
                      'Кол_во повт. приёмок',
                      )
    str = ''
    dict_overlap = dict()
    grps = DTCLS.gr_filter_nar
    for h in grps.headers:
        if h.name in EXCLUDE_FIELDS:
            continue
        set_checked = set()
        for g in h.grs:
            if g.btn.isChecked():
                set_checked.add(g.name)
        if len(set_checked) == 1:
            fix_v = list(set_checked)[0]
            fix_k = h.name
            if len(fix_k) >= 7:
                fix_k = f'{fix_k[:7]}.'

            if len(fix_v) >= 40:
                fix_v = f'{fix_v[:40]}.'
            dict_overlap[fix_k] = fix_v

    str = ', '.join([f'{k}:{_}'  for k, _ in dict_overlap.items()])
    if len(str)<=12:
        return  f'Группа № {F.now("%d.%m %H:%M")}'
    return str

@CQT.onerror
def load_tbl_filter():
    ui = DTCLS.app_self.ui
    tbl_filter_in_groups = ui.tbl_filter_in_groups

    DTCLS.gr_prgs_bar = CQT.Cust_progress_bar(DTCLS.app_self.ui.prgb_filtr)
    DTCLS.gr_prgs_bar.set_text_style(14, True)

    gr = Filtr_nar()
    DTCLS.gr_filter_nar = gr
    for item in DTCLS.table_nar:
        gr.add_item(item)
    rez_tbl  = gr.gen_tbl()
    rez_data_tbl  = gr.gen_data_tbl()

    def fnc_checked(row: int, column: int, gr: Group_filtr, *args):
        toggle_filtr_btn()
        DTCLS.app_self.ui.le_name_gr.setText(recalc_name_group())

    with CQT.table_updating(tbl_filter_in_groups):
        CQT.fill_wtabl(rez_tbl,
                       tbl_filter_in_groups,
                       styleSheet=CQT.MES_CSS,
                       auto_type=False,hide_head_rows=True,dict_or_list_user_data=rez_data_tbl,font_size=12)

        t_filter_in_groups = CQT.TableContext(tbl_filter_in_groups)

        #with CQT.table_updating(t_filter_in_groups):
        for k, ki in t_filter_in_groups.nf.items():
            for row in t_filter_in_groups.rows():
                val = row.value(k)
                if val == '':
                    continue
                grop:Group_filtr = CQT.getCustData(row.item(k))
                btn = CQT.add_btn(row.tbl,row.i,ki,val,checkable=True,
                                  conn_func_checked_row_col=fnc_checked,cell_val=grop)
                grop.btn = btn

    CQT.load_column_widths(DTCLS.app_self, tbl_filter_in_groups, CMS.tmp_dir())
    fill_table_nar()
    #t_filter_in_groups.tbl.resizeRowsToContents()
    #t_filter_in_groups.tbl.setFixedHeight(t_filter_in_groups.tbl.rowHeight(0))



    def height_changed(ctx, new_h):
        pass

    t_filter_in_groups.add_geometry_events(on_height_change=height_changed)
    pass





