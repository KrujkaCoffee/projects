from __future__ import annotations

import pprint
import copy
import project_cust_38.Cust_google_sheets_gspread as GS
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MKart import mywindow


@CQT.onerror
def load_tbl(self:mywindow):
    query = f"""SELECT * 
                            FROM koef_epml_per_ton"""
    self.LIST_STATE_KOEF = CSQ.custom_request_c(self.Data_plan.db_state, query, rez_dict=True)
    query = f"""SELECT * 
                            FROM napravlenie"""
    self.DICT_NAPR_KPLAN = F.deploy_dict_c(CSQ.custom_request_c(self.Data_plan.db_kplan, query, rez_dict=True),
                                           'name')
    base_weight = 55
    nomen_weigt = 55
    if self.ui.le_mosh_state.text() != '' and F.is_numeric(self.ui.le_mosh_state.text()):
        nomen_weigt= int(self.ui.le_mosh_state.text())

    query = f"""SELECT Пномер, 
        Древо, 
        Подразделение, 
        Должность, 
        Разряд, 
        Количество_штат, 
        "" AS Дефицит_штат, 
        "" AS Дефицит_штат_проц, 
        "" AS Количество_план, 
        "" AS Дефицит_план, 
        "" AS Дефицит_план_проц, 
        Примечание 
        FROM current_state"""
    list_proj = CSQ.custom_request_c(self.Data_plan.db_state,query,rez_dict=True)
    for i in range(len(list_proj)):
        dolgn_raz = list_proj[i]['Должность'].strip().lower()
        podr = list_proj[i]['Подразделение'].strip().lower()
        razr = list_proj[i]['Разряд']
        if razr != '':
            dolgn_raz = dolgn_raz + " " + str(razr) + " разряда"
        count_empl = 0
        for fio in self.DICT_EMPLOEE_FULL.keys():

            if self.DICT_EMPLOEE_FULL[fio]['Режим'] == "Абстракт":
                continue

            if self.DICT_EMPLOEE_FULL[fio]['Должность'].strip().lower() == dolgn_raz and\
                    self.DICT_EMPLOEE_FULL[fio]['Подразделение'].strip().lower() == podr :
                count_empl += 1

        list_proj[i]['Дефицит_штат'] = F.valm(list_proj[i]['Количество_штат']) - count_empl
        list_proj[i]['Дефицит_штат_проц'] =round((F.valm(list_proj[i]['Количество_штат']) - count_empl)/F.valm(list_proj[i]['Количество_штат'])*100,2)
        plan_state = 0
        for item in self.LIST_STATE_KOEF:
           if item['Подразделение'].strip().lower() == podr and item['Должность'].strip().lower() == dolgn_raz:
                koef_grow = item['koef_growing'] * (nomen_weigt-base_weight) + base_weight
                plan_state += self.DICT_NAPR_KPLAN['КЛ']['val'] / 100 * item[
                    'кл_ед_на_тонну'] * koef_grow
                plan_state += self.DICT_NAPR_KPLAN['КТ']['val'] / 100 * item[
                    'кт_ед_на_тонну']* koef_grow
                plan_state += self.DICT_NAPR_KPLAN['ШГ']['val'] / 100 * item[
                    'шг_ед_на_тонну']* koef_grow
                plan_state += self.DICT_NAPR_KPLAN['ПР']['val'] / 100 * item[
                    'пр_ед_на_тонну']* koef_grow
        if plan_state == 0:
            print(f"{list_proj[i]['Должность']}|{list_proj[i]['Подразделение']}|Подготовка"
                  f"|{F.valm(list_proj[i]['Количество_штат'])/0.5/base_weight}|{F.valm(list_proj[i]['Количество_штат'])/0.25/base_weight}|"
                  f"{F.valm(list_proj[i]['Количество_штат'])/0.125/base_weight}|{F.valm(list_proj[i]['Количество_штат'])/0.125/base_weight}")
        list_proj[i]['Количество_план'] = round(plan_state)
        list_proj[i]['Дефицит_план'] = list_proj[i]['Количество_план'] - count_empl
        if F.valm(list_proj[i]['Количество_план']) == 0:
            list_proj[i]['Дефицит_план_проц'] = 0
        else:
            list_proj[i]['Дефицит_план_проц'] = round(
            (F.valm(list_proj[i]['Количество_план']) - count_empl) / F.valm(list_proj[i]['Количество_план']) * 100, 2)


    CQT.fill_wtabl(list_proj,self.ui.tbl_state,auto_type=False)
    CMS.fill_filtr_c(self,self.ui.tbl_state_filtr,self.ui.tbl_state)
    CMS.update_width_filtr(self.ui.tbl_state,self.ui.tbl_state_filtr)
    nf_defic = CQT.num_col_by_name_c(self.ui.tbl_state,'Дефицит_штат')
    nf_defic_perc = CQT.num_col_by_name_c(self.ui.tbl_state,'Дефицит_штат_проц')
    nf_count = CQT.num_col_by_name_c(self.ui.tbl_state, 'Количество_штат')
    nf_defic_pl = CQT.num_col_by_name_c(self.ui.tbl_state, 'Дефицит_план')
    nf_defic_perc_pl = CQT.num_col_by_name_c(self.ui.tbl_state, 'Дефицит_план_проц')
    nf_count_pl = CQT.num_col_by_name_c(self.ui.tbl_state, 'Количество_план')
    for i in range(self.ui.tbl_state.rowCount()):
        defic = F.valm(self.ui.tbl_state.item(i,nf_defic).text())

        count = F.valm(self.ui.tbl_state.item(i,nf_count).text())
        delta = defic/count
        CQT.set_color_wtab_c(self.ui.tbl_state,i,nf_defic_perc,255,255- delta*255,255-delta*255)

        defic_pl = F.valm(self.ui.tbl_state.item(i, nf_defic_pl).text())
        count_pl = F.valm(self.ui.tbl_state.item(i, nf_count_pl).text())
        if count_pl==0:
            delta_pl = 0
        else:
            delta_pl = defic_pl / count_pl
        CQT.set_color_wtab_c(self.ui.tbl_state, i, nf_defic_perc_pl, 255, 255 - delta_pl * 255, 255 - delta_pl * 255)
    if nomen_weigt == base_weight:
        grow = 0
    else:
        grow = round((nomen_weigt - base_weight)/base_weight * 100 )
    self.ui.lbl_up_mosh.setText(f'Рост {grow}%')
    return


@CQT.onerror
def select_field_tbl_state(self:mywindow):
    def fill_empl(self:mywindow):
        tbl = self.ui.tbl_state
        row = tbl.currentRow()
        CQT.clear_tbl(self.ui.tbl_state_empl)
        if row == -1:
            return
        nf_podr = CQT.num_col_by_name_c(tbl,'Подразделение')
        nf_dolgn = CQT.num_col_by_name_c(tbl, 'Должность')
        nf_razr = CQT.num_col_by_name_c(tbl, 'Разряд')
        podr = tbl.item(row,nf_podr).text().strip().lower()
        dolgn = tbl.item(row, nf_dolgn).text().strip().lower()
        razr = tbl.item(row, nf_razr).text().strip().lower()
        if razr != '':
            dolgn = dolgn + " " + str(razr) + " разряда"
        list_empl = []
        for fio in self.DICT_EMPLOEE_FULL.keys():
            if self.DICT_EMPLOEE_FULL[fio]['Должность'].strip().lower() == dolgn and \
                    self.DICT_EMPLOEE_FULL[fio]['Подразделение'].strip().lower() == podr:
                tmp_item = copy.deepcopy(self.DICT_EMPLOEE_FULL[fio])
                tmp_item['ФИО'] = fio
                list_empl.append(tmp_item)
        if list_empl == []:
            return
        CQT.fill_wtabl(list_empl,self.ui.tbl_state_empl)

    def fill_empl_mat(self: mywindow):
        tbl = self.ui.tbl_state
        row = tbl.currentRow()
        CQT.clear_tbl(self.ui.tbl_state_empl_mat)
        list_empl = [['Код',"Материал","Ед.Изм.","Кол-во"]]
        CQT.fill_wtabl(list_empl, self.ui.tbl_state_empl_mat)


    fill_empl(self)
    fill_empl_mat(self)
    return
