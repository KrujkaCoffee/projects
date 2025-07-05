from __future__ import annotations

import datetime
import os
import copy
import pprint
import sys
import hashlib
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
from attr._make import fields
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
from typing import TYPE_CHECKING, TypeVar
import project_cust_38.api_erp_commands as APIERP
if TYPE_CHECKING:
    from MKart import mywindow

LIST_FREEZE_FIELDS = ['plan.Пномер', 'plan.Направление_деятельности', 'plan.local_graf', 'plan.Статус', ]
LIST_HIDE_FIELDS = ['plan.local_graf']


@CQT.onerror
def update_db_info_fields_kpl(self: mywindow):
    result = []
    list_db = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, f"""SELECT case when table_kpl = '' then name else  table_kpl 
     || "." || name end as name, nickname FROM info_fields_kpl;""", rez_dict=True), 'name')
    selected_tbls, list_conf = load_db(self, only_hat=True)
    if selected_tbls == False:
        CQT.msgbox(f'Ошибка загрузки таблиц')
        return
    for str_name in selected_tbls[0]:
        if str_name not in list_db:
            if '.' in str_name:
                tbl, field = str_name.split('.')
            else:
                tbl = ''
                field = str_name
            CSQ.custom_request_c(self.db_kplan,
                                 f"""INSERT INTO info_fields_kpl (table_kpl,name,nickname) VALUES ("{tbl}","{field}","{str_name}");""")
            result.append(str_name)
    if len(result):
        CQT.msgbox(f'Успешно {pprint.pformat(result)}')
    else:
        CQT.msgbox(f'Новых полей не найдено')

@CQT.onerror
def recalc_fact_by_date(self: mywindow,pozition_num:int, date_calc:datetime.datetime=None, *args):
    estimated_vid_rab_names_fact = {v['name_fact'] for k, v in self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items()
                                    if
                                    v['estimated'] and v['poki'] == self.place.poki}
    estimated_vid_rab_names = {v['Имя'] for k, v in self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items()
                                    if
                                    v['estimated'] and v['poki'] == self.place.poki}
    estimated_vid_rab_names_fact = estimated_vid_rab_names_fact.union(estimated_vid_rab_names)

    def vid_rab_into_name_plan(vid_rab: str):
        if vid_rab in self.DICT_VID_RABOT:
            return self.DICT_VID_RABOT[vid_rab]['group_for_plan_f'].split(';')
        return

    def vid_rab_into_name_etap(vid_rab: str):
        if vid_rab in self.DICT_VID_RABOT:
            return self.DICT_VID_RABOT[vid_rab]['name_tbl'].split(';')
        return

    def start_end_fakt_into_name_plan(vid_rab: str):
        if vid_rab in self.DICT_VID_RABOT:
            return self.DICT_VID_RABOT[vid_rab]['group_for_plan_start_f'].split(';'), self.DICT_VID_RABOT[vid_rab][
                'group_for_plan_end_f'].split(';')
        return None, None

    def calc_time(self, pozition_num, date_calc=None):
        poz = CMS.Pozition(pozition_num, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
        poz.load_kpl_table('пл_топ')

        vid_po_napr = poz.dict_tables['пл_топ']['Вид']
        napr_deyat = self.Data_plan.DICT_NAPR_DEYAT[poz.Направление_деятельности]['Имя']

        try:
            koef_vneplana, koef_pogr_norm = calc_koefs_pogr(self, vid_po_napr, napr_deyat)
        except:
            CQT.msgbox(f'Не корректно занесен направление')
            return
        postfix =''
        if date_calc:
            nach = F.datetostr(date_calc,"%Y-%m-%d 04:00:00")
            konec = F.datetostr( F.date_add_days(date_calc,1,format_out='') ,"%Y-%m-%d 03:59:59")
            postfix= f'datetime(jurnal.Дата) > datetime("{nach}") and datetime(jurnal.Дата) < datetime("{konec}") and'
        list_nars = CSQ.custom_request_c(self.bd_naryad, f"""SELECT DISTINCT
                    {', '.join(['naryad.' + _ for _ in CSQ.list_types_table(self.bd_naryad, 'naryad').keys()])}
         FROM naryad 
        INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
        INNER JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер 
        WHERE {postfix} mk.НомКплан = {pozition_num} and naryad.Подтвержд_вып_дата != "" and naryad.Аутсорсинг == 0;""",
                                         rez_dict=True)
        #mk.Пномер as "Номер МК", mk.Номенклатура, [_['Пномер'] for _ in list_nars]
        list_mk_nums = [_['Номер_мк'] for _ in list_nars]
        dict_mk_data = F.deploy_dict_c(CSQ.custom_request_c(self.bd_naryad,f"""SELECT mk.Пномер as "Номер МК", 
         mk.Номенклатура FROM mk 
         LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
        WHERE 
         mk.Пномер IN ({CSQ.prepare_list_to_tuple(list_mk_nums)}) and plan.poki = {self.place.poki};""", rez_dict=True,
                                            attach_dbs=(self.db_kplan)),"Номер МК")
        dict_summ_time = dict()
        dict_fact_jur = dict()
        dict_jur_data = dict()

        set_name_etaps = set()

        for row in list_nars:
            nar = CMS.Naryads(row, self.bd_naryad, self.Data_plan.DICT_DOLGN_ETAP, self.db_users,
                              self.Data_plan.DICT_EMPLOEE_FULL_WITH_DEL)

            nar.recalc_fact()
            nar.recalc_jur_n_time(nar.ФИО)
            nar.recalc_jur_n_time(nar.ФИО2)

            jur = nar.get_list_from_jurnal()
            start, end = jur.calc_start_end_dates()
            if start == None or end == None:
                continue

            def calc_dict_fact_jur_by_day(jur:CMS.Jurnal_nar):

                dict_fact_jur_by_day = dict()

                for item_jur in jur.rows:
                    if item_jur['Подытог_нормы'] == '':
                        continue
                    if F.is_numeric(item_jur['Подытог_нормы']) and item_jur['Подытог_нормы'] > 0 and item_jur['Статус'] == 'Начат':
                        date_jur = F.strtodate(item_jur['Дата'])
                        if date_calc:
                            if date_calc.date() != date_jur.date():
                                continue
                        day = F.datetostr(date_jur, "%d\n%m\n%y")

                        if day not in dict_fact_jur_by_day:
                            dict_fact_jur_by_day[day] = {'time':0,'data_jur':[]}
                        dict_fact_jur_by_day[day]['time'] += item_jur['Подытог_нормы']
                        dict_fact_jur_by_day[day]['data_jur'].append(item_jur)
                return dict_fact_jur_by_day

            dict_fact_jur_by_day = calc_dict_fact_jur_by_day(jur)

            for oper_param in nar.params:
                name_plan_list = vid_rab_into_name_plan(oper_param['Виды_работ'])

                list_name_start, list_name_end = start_end_fakt_into_name_plan(oper_param['Виды_работ'])
                if list_name_start == None or list_name_start == None:
                    continue
                for name_start in list_name_start:
                    if not start == None:
                        if name_start not in dict_summ_time or F.strtodate(start) < F.strtodate(
                                dict_summ_time[name_start]):
                            dict_summ_time[name_start] = start
                for name_end in list_name_end:
                    if not end == None:
                        if name_end not in dict_summ_time or F.strtodate(end) > F.strtodate(dict_summ_time[name_end]):
                            dict_summ_time[name_end] = end

                if name_plan_list == None:
                    continue

                kr = self.DICT_OP_NAME[oper_param['Операции_имя']]['kr_default']
                koef_posta = 1
                if kr == 2:
                    koef_posta = 1 / 0.7

                name_etap_list = vid_rab_into_name_etap(oper_param['Виды_работ'])
                for name_etap in name_etap_list:
                    set_name_etaps.add(name_etap)
                    koef_vneplana_tmp = 1
                    if name_etap in estimated_vid_rab_names_fact:
                        koef_vneplana_tmp = koef_vneplana

                    name_etap = 'факт_' + name_etap
                    if name_etap not in dict_jur_data:
                        dict_jur_data[name_etap] = []
                    if name_etap not in dict_fact_jur:
                        dict_fact_jur[name_etap] = dict()
                    for day, minutes_fact_data in dict_fact_jur_by_day.items():
                        minutes_fact= minutes_fact_data['time']

                        if day not in dict_fact_jur[name_etap]:
                            dict_fact_jur[name_etap][day] = 0
                        minutes_fact_k = minutes_fact * koef_vneplana_tmp * koef_posta * koef_pogr_norm
                        part_time =  minutes_fact_k / nar.get_summ_teor_time_by_empl() * oper_param['Опер_время']
                        dict_fact_jur[name_etap][day] +=part_time

                        for row_jur in minutes_fact_data['data_jur']:

                            row_jur = copy.deepcopy(row_jur)

                            minutes_fact_k_row = row_jur['Подытог_нормы'] * koef_vneplana_tmp * koef_posta * koef_pogr_norm
                            part_time_row = round(minutes_fact_k_row / nar.get_summ_teor_time_by_empl() * oper_param['Опер_время'],3)

                            row_jur["Номенклатура"] = ""
                            if nar.Номер_мк in dict_mk_data:
                                row_jur["Номенклатура"] =dict_mk_data[nar.Номер_мк]
                            row_jur['Этап плана'] = name_etap
                            row_jur['Дата плана'] = F.datetostr(F.strtodate(day,"%d\n%m\n%y"),'%Y-%m-%d')
                            row_jur['ДСЕ'] = oper_param['ДСЕ']
                            row_jur['Операция'] = " ".join((oper_param['Операции_номер'],oper_param['Операции_имя']))
                            row_jur['minutes_fact'] = row_jur['Подытог_нормы']
                            row_jur['Опер_время'] = oper_param['Опер_время']
                            row_jur['koef_posta'] = round(koef_posta,2)

                            row_jur['koef_pogr_norm'] = koef_pogr_norm

                            row_jur['koef_vneplana'] = koef_vneplana_tmp
                            row_jur['minutes_fact_k'] =round( minutes_fact_k_row,2)
                            row_jur['summ_teor_time'] = nar.get_summ_teor_time_by_empl()
                            row_jur['Подытог_нормы_для_плана_минут'] = copy.deepcopy(round(part_time_row,3))
                            row_jur['Подытог_нормы_для_плана_час'] = copy.deepcopy(round(part_time_row/60, 3))

                            if 'Подытог' in row_jur:
                                row_jur.pop('Подытог')
                            dict_jur_data[name_etap].append(row_jur)

                for name_plan in name_plan_list:
                    koef_vneplana_tmp = 1
                    set_name_etaps.add(name_etap)
                    if name_plan in estimated_vid_rab_names_fact:
                        koef_vneplana_tmp = koef_vneplana

                    if name_plan not in dict_summ_time:
                        dict_summ_time[name_plan] = 0
                    minutes_fact = sum(
                       [ _['time'] for _ in list(dict_fact_jur_by_day.values())]) * koef_vneplana_tmp * koef_posta * koef_pogr_norm
                    part_time = minutes_fact / nar.get_summ_teor_time_by_empl() * oper_param['Опер_время']
                    dict_summ_time[name_plan] += round(part_time,3)  # учитывается отдельно сумма пл_сб поэтому не надо делить на 2
        for k, v in dict_summ_time.items():
            if F.is_date(v):
                dict_summ_time[k] = F.datetostr(F.strtodate(v), "%Y-%m-%d")
            if F.is_numeric(v):
                dict_summ_time[k] = round(v / 60, 2)

        return poz, dict_fact_jur, dict_summ_time, dict_jur_data

    poz, dict_fact_jur, dict_summ_time, dict_jur_data= calc_time(self,pozition_num,date_calc)

    return poz, dict_fact_jur, dict_summ_time,dict_jur_data
@CQT.onerror
def recalc_and_fil_fact(self: mywindow, *args):
    def calc_pozition(self, pozition_num, msg=True, repaint_graf=True,infotable=False):
        poz, dict_fact_jur, dict_summ_time,dict_jur_data = recalc_fact_by_date(self,pozition_num)
        if infotable:
            list_compare = []
            for etap, val_etap in dict_jur_data.items():
                for item in val_etap:
                    dse = item['ДСЕ'].replace('$',' ')
                    oper= item['Операция']
                    s_nar = item['Номер_наряда']
                    time = item['Подытог_нормы_для_плана_минут']
                    summ_teor_time = item['summ_teor_time']
                    list_compare.append({'dse':dse,'etap':etap,'Номер_наряда':s_nar,'summ_teor_time':summ_teor_time,
                                         'Подытог_нормы':item['Подытог_нормы'],'minutes_fact':item['minutes_fact'] ,
                                'koef_posta': item['koef_posta'] ,
                                'minutes_fact_k': item['minutes_fact_k'] ,

                        'oper':oper,'Подытог_нормы_для_плана_минут':time})
            if not CQT.msgboxg_get_table(self,'info',list_compare, load_summ=True,yesNoMode=True):
                return


        poz.update_day_plan_etap_jurnal(dict_fact_jur)
        if poz.update_row_etaps(dict_summ_time):

            self.Data_plan.DICT_REPLACE_BY_DAYS = dict_fact_jur
            GPL.update_local_graf(self, True, pozition_num, repaint_graf)
            if msg:
                CQT.msgbox(f'Успешно')
        else:
            if msg:
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
            calc_pozition(self, pozition_num, False, False,infotable=False)
        CQT.msgbox(f'Звершено')

    else:
        row = CQT.get_dict_line_form_tbl(tbl)
        if 'plan.Пномер' not in row:
            return
        pozition_num = int(row['plan.Пномер'])
        calc_pozition(self, pozition_num,infotable=True)


@CQT.onerror
def update_graf_site_and_get_local(self: mywindow):
    if not self.selected_napr:
        CQT.msgbox(f'Выбрано не одно направление')
        return
    update_graf_pad_moshn(self, self.selected_napr)
    GEN_PLG(self, self.selected_napr)


@CQT.progress_decorator
@CQT.onerror
def update_graf_pad_moshn(self: mywindow, selected_napr=None, hook_prog_bar=None, *args):
    if 'KPLAN_max_mosh' not in self.__dict__:
        VPL.get_max_mosh_from_db(self)

    @CQT.onerror
    def save_graf_pad_moshn(self: mywindow, napr, percent, name_for_file, resp, max_date, *args):
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

        def calc_graf_pad_moshn(self: mywindow, napr, percent, resp, max_date, *args):

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
            list_dates = []
            start_date = F.add_months(F.strtodate(F.now("%Y-%m-%d")), -1)
            date = start_date
            max_date = F.strtodate(max_date,"%Y-%m-%d")
            while True:
                if date > max_date:
                    break
                list_dates.append(date)
                date = F.date_add_days(date, 1, format_out='')
            podr_eval_name = 'план_' + self.place.evaluation_department.Имя
            dict_moshn = dict()
            for item in resp:
                dict_form = F.from_binary_pickle(item['local_graf'])
                dict_replace_by_days = None
                if item['fact_jurnal_blolb_data']:
                    dict_replace_by_days = F.from_binary_pickle(item['fact_jurnal_blolb_data'])
                kpl = item['Пномер']
                for i in range(len(dict_form)):
                    for date_data, data in dict_form[i]['data'].items():
                        if date_data not in dict_moshn:
                            dict_moshn[date_data] = dict()
                        if kpl not in dict_moshn[date_data]:
                            dict_moshn[date_data][kpl] = 0
                        if podr_eval_name in data['podr']:
                            for elem in data['podr'][podr_eval_name]:
                                dict_moshn[date_data][kpl] += elem['Время_час']
                if dict_replace_by_days :
                    if podr_eval_name in dict_replace_by_days:
                        for date_repl, val_repl in dict_replace_by_days[podr_eval_name].items():
                            date_repl_obj = F.strtodate(date_repl,"%d\n%m\n%y")
                            if date_repl_obj not in dict_moshn:
                                dict_moshn[date_repl_obj] = dict()
                            dict_moshn[date_repl_obj][kpl] = round(val_repl/60,2)

            for date in list_dates:
                summ_napr = 0
                max_napr = 0
                if date in self.KPLAN_max_mosh: #self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN self.Data_plan.DICT_PODR_POKI
                    max_napr = 0
                    #for podr in [k for k, _ in self.Data_plan.DICT_GROUP_VID_RAB_FOR_PLAN.items() if _['estimated']]
                    for podr in list({v['Имя'] for k,v in self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items() if v['poki'] == self.place.poki and v['estimated']}):
                        max_napr += round(self.KPLAN_max_mosh[date][podr] * percent / 100, 2)
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

        data = calc_graf_pad_moshn(self, napr, percent, resp, max_date)
        name_file = f'gr_pad_mosh_{name_for_file}.txt'
        F.save_file(F.scfg('BD_selector') + F.sep() + name_file, data)

    hook_prog_bar.open()
    hook_prog_bar.set(0)
    hook_prog_bar.text('Получение дат')
    SET_estimated_podr = {v['Имя'] for k,v in self.Data_plan.DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items() if v['estimated']}
    dict_estimated_podr_filtr = {k:v for k,v in self.Data_plan.DICT_PODR_POKI.items() if k in SET_estimated_podr}
    list_fields_and_tabels =  [[', '.join([f"{k}.{_['Имя_начала_этапа']} AS Пдата_нач" , f"{k}.{_['Имя_конца_этапа']} AS Пдата_зав", f"{k}.{_['Имя_поля'].split(';')[0]} AS Нчас"]),
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

                    WHERE plan.poki = {self.place.poki} and status_poz.Имя IN (
                    "Долгосрочный",
                    "Резерв", 
                    "Подготовка", 
                    "Изготовление", 
                    "К производству", 
                    "Перепроверка")"""
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
        pass
        if F.is_date(item['Пдата_зав'],"%Y-%m-%d") and F.strtodate(item['Пдата_зав'],"%Y-%m-%d") > F.strtodate(max_date,"%Y-%m-%d" ):
            max_date = item['Пдата_зав']

        if item['Пномер'] not in dict_pozs:
            dict_pozs[item['Пномер']] = {
                'Пдата_нач':None,
                'Пдата_зав':None,
                'Нчас':0,
                'Фдата_получения_КД':F.now("%Y-%m-%d"),
            }
        if F.is_date(item['Пдата_нач'], "%Y-%m-%d"):
            if dict_pozs[item['Пномер']]['Пдата_нач'] == None or F.strtodate(item['Пдата_нач'],"%Y-%m-%d") <  F.strtodate(dict_pozs[item['Пномер']]['Пдата_нач'],"%Y-%m-%d"):
                dict_pozs[item['Пномер']]['Пдата_нач'] = item['Пдата_нач']
        if F.is_date(item['Пдата_зав'], "%Y-%m-%d"):
            if dict_pozs[item['Пномер']]['Пдата_зав'] == None or F.strtodate(item['Пдата_зав'],"%Y-%m-%d") >  F.strtodate(dict_pozs[item['Пномер']]['Пдата_зав'],"%Y-%m-%d"):
                dict_pozs[item['Пномер']]['Пдата_зав'] = item['Пдата_зав']
        if F.is_date(item['Фдата_получения_КД'], "%Y-%m-%d"):
            if F.strtodate(item['Фдата_получения_КД'],"%Y-%m-%d") > F.strtodate(dict_pozs[item['Пномер']]['Фдата_получения_КД'],"%Y-%m-%d"):
                dict_pozs[item['Пномер']]['Фдата_получения_КД'] = item['Фдата_получения_КД']
        if F.is_numeric(item['Нчас']):
            dict_pozs[item['Пномер']]['Нчас'] += F.valm(item['Нчас'])

    list_num_poz = list(dict_pozs.keys())
    list_num_poz_blolb_data = CSQ.custom_request_c(self.db_kplan, f"""SELECT plan.Пномер,
                        plan.local_graf, plan.fact_jurnal_blolb_data FROM plan  

                        WHERE plan.Пномер IN ({CSQ.prepare_list_to_tuple(list_num_poz)});""", rez_dict=True)
    dict_num_poz_blolb_data = F.deploy_dict_c(list_num_poz_blolb_data,'Пномер')
    for item in resp:
        item['local_graf'] =  dict_num_poz_blolb_data[item['Пномер']]['local_graf']
        item['fact_jurnal_blolb_data'] =  dict_num_poz_blolb_data[item['Пномер']]['fact_jurnal_blolb_data']

    cnter = 0
    for napr, percent, name_for_file in [[_['name'], _['val'], _['name_for_file_graf_pad_mosh']] for _ in
                                         self.Data_plan.DICT_NAPRAVLENIE.values() if _['poki'] == self.place.poki]:
        cnter += 1
        if selected_napr == None or selected_napr == napr:
            hook_prog_bar.set(10 + round((cnter / len(self.Data_plan.DICT_NAPRAVLENIE)) * 90))
            hook_prog_bar.text(f'Расчет по {napr}')
            save_graf_pad_moshn(self, napr, percent, name_for_file, [_ for _ in resp if _['name'] == napr], max_date)
    hook_prog_bar.close()


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
    nf_s_num = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
    row = tbl.currentRow()
    if row == -1:
        CQT.msgbox(f'Не выбрана строка')
        return
    CMS.Pozition.set_flag_recalc_dates(self.db_kplan, int(tbl.item(row, nf_s_num).text()), 0)
    if CQT.num_col_by_name_c(tbl, 'plan.Потребность_пересч_сроков') == None:
        return
    CQT.set_val_tbl_by_name(self.ui.tbl_kal_pl, self.ui.tbl_kal_pl.currentRow(), 'plan.Потребность_пересч_сроков', '0')


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
    np = poz.dict_tables['пл_оуп']['№проекта']
    py = poz.dict_tables['пл_оуп']['№ERP']
    year_py = poz.dict_tables['пл_оуп']['Год']
    if py == '-' or py == f'{self.place.doc_prefix}00-000000' :
        CQT.msgbox(f'номер {self.place.doc_prefix} не корректный')
        return
    dir_proj = CMS.get_path_to_proj_NPPY_c(np, py,year_py,poz.get_napravl()['projects_localnet_path'])
    if F.existence_file_c(dir_proj):
        CQT.msgbox(f'Директория {dir_proj} уже создана')
        return
    if not F.create_dir_c(dir_proj):
        CQT.msgbox(f'Отказано в доступе: {dir_proj}')
        return
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
    пл_оуп.№ERP as "№ERP", пл_оуп.№Пл_Пр as "ПлПр", napravl_deyat.Псевдоним as "Вид",
                 napravlenie.name as "Направление",  пл_оуп.Количество as "Количество", plan.Позиция, plan.Пномер as "Пномер" FROM пл_оуп  INNER JOIN plan ON пл_оуп.НомПл = plan.Пномер,
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


@CQT.onerror
def set_stat_closed(self: mywindow, *args):
    def list_unclosed_mk(self: mywindow, list_of_poz):
        list_of_mk = tuple([str(_['plan.МК']) for _ in list_of_poz])
        str_list_of_mk = ','.join(list_of_mk)
        list_if_status = CSQ.custom_request_c(self.bd_naryad, f"""SELECT Дата_завершения, Пномер FROM mk
         WHERE Пномер IN ({str_list_of_mk}) AND Статус != 'НаУдаление';""", rez_dict=True)
        if list_if_status == None or list_if_status == False:
            CQT.msgbox(f'Ошибка в генерации списка МК по перечню {list_of_mk}')
            return
        list_open_mk = []
        for item in list_if_status:
            if item['Дата_завершения'] == "":
                list_open_mk.append(item['Пномер'])
        return list_open_mk

    def check_fields(tbl):
        list_necessarily_fields = ['plan.МК', 'plan.Пномер']
        for field in list_necessarily_fields:
            if CQT.num_col_by_name_c(tbl, field) == None:
                CQT.msgbox(f'Поле {field} не найдено')
                return False
        return True

    tbl = self.ui.tbl_kal_pl

    list_of_poz = CQT.list_from_wtabl_c(tbl, '', True, True, True)
    if not check_fields(tbl):
        return

    list_open_mk = list_unclosed_mk(self, list_of_poz)
    if len(list_open_mk) != 0:
        CQT.msgbox(f'Ошибка, не закрыты МК:\n' + pprint.pformat(list_open_mk))
        return

    list_poz_nums = [_['plan.Пномер'] for _ in list_of_poz]
    for pnum in list_poz_nums:
        CSQ.custom_request_c(self.db_kplan, f"""UPDATE plan SET Статус = 4 WHERE Пномер = {pnum}""")
        pass

    CQT.msgbox(f'Успешно')
    load_table_db(self)


@CQT.onerror
def find_field_reset(self):
    self.find_field_counter = 0


@CQT.onerror
def find_field(self: mywindow):

    def find_in_tbl(tbl):
        fl = False
        for j in range(self.find_field_counter, tbl.columnCount()):
            if tbl.isColumnHidden(j):
                continue
            if self.ui.le_pl_find_field.text().lower() in tbl.horizontalHeaderItem(
                    j).text().lower():
                fl = True
                CQT.select_cell(tbl, 0, j)
                if self.ui.tbl_kal_pl.rowCount() > 0:
                    CQT.select_cell(self.ui.tbl_kal_pl, 0, j)
                self.find_field_counter = j + 1
                break
        if fl == False:
            self.find_field_counter = 0

    if self.ui.le_pl_find_field.text() == '':
        return
    if not "find_field_counter" in self.__dict__:
        self.find_field_counter = 0
    
    if self.regim == 'cnf':
        find_in_tbl(self.ui.tbl_pl_add_poz)
        return
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
    path = CMS.path_to_proj_NPPY_c(np, py, True,year_py)
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
        if item['Имя_поля'] != '':

            for name_field in item['Имя_поля'].split(';'):
                str_full_name = '.'.join([name_tbl, name_field])
                tmp_list.append([str_full_name, item['Порядок']])
    dict_norm = {_[0]: 0 for _ in F.sort_by_column_c(tmp_list, 'poz')[1:]}
    return dict_norm


@CQT.onerror
def dict_norm_from_res(self, res, dict_norm='', koef_vneplana=1, koef_pogr_norm=1, count_izd=None, list_log=None,
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
                            f"По МК№ {s_num_mk}  В бд не соотвествует этап {podr} базовому dict_norm")
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
                        dict_norm[podr] += itog_time
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


                        tmp_row = {'Позиция': pozition,
                                   'МК': s_num_mk,
                                   'Номерпп': dse['Номерпп'],
                                   'ДСЕ': f"{dse['Наименование']} {dse['Номенклатурный_номер']}",
                                   'Колво_в_узел': dse['Количество'], 'Изделий': count_izd,
                                   'Колво_всего': dse['Количество'], 'Опер_номер': oper['Опер_номер'],
                                   'Опер_имя': oper['Опер_наименование'], 'Мат_кд_знч': mat_znch, 'Мат_кд': mat_name,
                                   'Ссылка': link_docs, 'Этап': oper['Этап'],
                                   'Вид_работ': self.DICT_PROFESSIONS_NAME[oper['Опер_профессия_наименование']][
                                       'Вид_работ'],
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
def calc_koefs_pogr(self: mywindow, vid_po_napr, napr_deyat):
    # koef_vneplana = self.Data_plan.DICT_NAPRAVLENIE[self.Data_plan.DICT_NAPR_DEYAT_NAME[napr_deyat]['Направление']][
    # 'koef_vneplana']
    koef_vneplana = 1
    if vid_po_napr in self.Data_plan.DICT_VID_PO_NAPR:
        koef_vneplana = 1 + self.Data_plan.DICT_VID_PO_NAPR[vid_po_napr]['vneplan_percent']
    koef_pogr_norm = self.Data_plan.DICT_NAPRAVLENIE[self.Data_plan.DICT_NAPR_DEYAT_NAME[napr_deyat]['Направление']][
        'koef_pogr_norm']
    return koef_vneplana, koef_pogr_norm
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
        CQT.msgbox(f'Успешно',time_life=0.5)
    return

@CQT.onerror
def btn_pl_load_norm(self: mywindow):
    # МИНУТ НА 1 КГ.
    DICT_AVERAGE_EFFICIENCY = {"Лазерная резка": 0.632670759652881,
                               "Сборка": 3.57824246635921,
                               "Сварка": 3.57824246635921,
                               "Покраска": 0.308754357651951,
                               "Токарка_фрезеровка": 0.654724642342306,
                               "Зачистка": 0.777399364802233,
                               "Вспомогательная": 1.10964857367662346,
                               "Подготовка_монтажного_комплекта": 0.168,
                               }

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
            old_time = 0
            if key in dict_form_db:
                old_time = dict_form_db[key]
                if norma == dict_form_db[key]:
                    fl_fill = False
            if key in row_time_add_etap:
                old_time = row_time_add_etap[key]
                if norma == row_time_add_etap[key]:
                    fl_fill = False
            if fl_fill:
                CSQ.custom_request_c(self.db_kplan,
                                     f"""UPDATE {tbl} SET {field} = {norma} WHERE {ind_field} = {pnom} """)
                list_change.append([
                    f'{field} было {str(round(old_time, 2))}, '
                    f'cтало  {str(round(norma, 2))}'])
        return list_change

    def load_norm_vo(self, pnom: int, dict_norm: dict):
        DICT_SOPOST_ETAPOV_VO_SRED = {'Лазерная резка': 'пл_заг.Нчас_заг',
                                      'Сборка': 'пл_сб.Нчас_слсб',
                                      'Сварка': 'пл_сб.Нчас_св',
                                      'Покраска': 'пл_покр.Нчас_покр',
                                      'Токарка_фрезеровка': 'пл_мех.Нчас_мехобр',
                                      'Зачистка': 'пл_сб.Нчас_зач',
                                      'Вспомогательная': 'plan.Нчас_вспом',
                                      'Термическая': 'plan.Нчас_вспом',
                                      'Подготовка_монтажного_комплекта': 'пл_компл.Нчас_упаковки',
                                      'Упаковка_и_комплектование ЗИП': 'пл_компл.Нчас_упаковки'

                                      }
        DICT_SOPOST_ETAPOV_VO_VID = {'Лазерная_резка': {'пл_заг.Нчас_заг': 100, },
                                     'Сборка_сварка': {'пл_сб.Нчас_слсб': 59, 'пл_сб.Нчас_св': 59},
                                     'Покраска': {'пл_покр.Нчас_покр': 100, },
                                     'Токарка_фрезеровка': {'пл_мех.Нчас_мехобр': 100, },
                                     'Зачистка': {'пл_сб.Нчас_зач': 100, },
                                     'Вспомогательная': {'plan.Нчас_вспом': 100, },
                                     'Термическая': {'plan.Нчас_вспом': 100, },
                                     'Подготовка_монтажного_комплекта': {'пл_компл.Нчас_упаковки': 100, },
                                     'Упаковка_и_комплектование_ЗИП': {'пл_компл.Нчас_упаковки': 100, },
                                     }
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
            for etap in DICT_AVERAGE_EFFICIENCY:
                if etap in DICT_SOPOST_ETAPOV_VO_SRED and DICT_SOPOST_ETAPOV_VO_SRED[etap] in dict_norm:
                    dict_norm[DICT_SOPOST_ETAPOV_VO_SRED[etap]] += round(
                        F.valm(DICT_AVERAGE_EFFICIENCY[etap]) * 1.32 * ves, 6)
            return dict_norm

        CQT.msgbox(f"Принято для расчета {self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]['Имя']} "
                   f" {self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]['кг_на_пост_см']}"
                   f" кг/пост/смену (выборка {self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]['Выборка']} изд.)"
                   f"koef_vneplana {koef_vneplana}"
                   f"koef_pogr_norm {koef_pogr_norm}")

        for etap in self.Data_plan.DICT_VID_PO_NAPR[item['Вид']]:
            if etap in DICT_SOPOST_ETAPOV_VO_VID:
                for kpl_etap in DICT_SOPOST_ETAPOV_VO_VID[etap].keys():
                    if kpl_etap in dict_norm:
                        dict_norm[kpl_etap] += \
                            round(F.valm(self.Data_plan.DICT_VID_PO_NAPR[item['Вид']][etap]) *
                                  koef_vneplana * ves * DICT_SOPOST_ETAPOV_VO_VID[etap][kpl_etap] / 100, 6)
        return dict_norm

    def calc_by_tkp(resp, poz, dict_norm, koef_vneplana, koef_pogr_norm, pnom, nk_stat_norm):
        res = CMS.load_res(resp, self=self, tkp=True)
        count_izd = poz.dict_tables['пл_оуп']['Количество']
        if count_izd == None or count_izd == '' or not F.is_numeric(count_izd):
            CQT.msgbox(f'{"пл_оуп.Количество"} не число')

        dict_norm, list_opers = dict_norm_from_res(self, res, dict_norm, koef_vneplana, koef_pogr_norm, count_izd)
        if dict_norm == None:
            return
        CSQ.custom_request_c(self.db_kplan,
                             f"""UPDATE plan SET Статус_норм = 3 WHERE Пномер = {pnom} """)
        if nk_stat_norm:
            tbl.item(tbl.currentRow(), nk_stat_norm).setText(self.Data_plan.DICT_STATUS_NORM[3]['Имя'])
        return dict_norm, list_opers

    def calc_by_vo(self, pnom, dict_norm, nk_stat_norm):
        # ==============ПО ВО===================
        dict_norm = load_norm_vo(self, pnom, dict_norm)
        if dict_norm == None:
            return
        CSQ.custom_request_c(self.db_kplan, f"""UPDATE plan SET Статус_норм = 1 WHERE Пномер = {pnom} """)
        if nk_stat_norm:
            tbl.item(tbl.currentRow(), nk_stat_norm).setText(self.Data_plan.DICT_STATUS_NORM[1]['Имя'])
        return dict_norm

    def calc_top(self, dict_norm, data_top):
        # t(в часах)=колво ДСЕ*0,4+2
        dict_norm['пл_топ.Нчас_ТД'] = (data_top['Число_ДСЕ'] * 0.4 + 2) * 60
        return dict_norm

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
    nk_napr = CQT.num_col_by_name_c(tbl, 'plan.Направление_деятельности')
    if nk_napr == None:
        CQT.msgbox(f'Отсутствует поле plan.Направление_деятельности')
        return
    napr_deyat = tbl.item(tbl.currentRow(), nk_napr).text()

    try:
        koef_vneplana, koef_pogr_norm = calc_koefs_pogr(self, vid_po_napr, napr_deyat)
    except:
        CQT.msgbox(f'Не корректно занесен направление')
        return

    list_mk = CSQ.custom_request_c(self.bd_naryad, f"""SELECT Пномер,Количество,Дата_завершения,Вес FROM mk WHERE 
    НомКплан == {poz.Пномер} AND На_удал == 0;""", rez_dict=True)
    name_predv_res = poz.dict_tables['пл_топ']['Предв_спецификация_ЕРП']

    dict_norm = generate_dict_norm(self)
    nk_pnom = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
    pnom = int(tbl.item(tbl.currentRow(), nk_pnom).text())
    nk_stat_norm = CQT.num_col_by_name_c(tbl, 'plan.Статус_норм')
    if nk_stat_norm == None:
        CQT.msgbox(f'Отсутствует поле plan.Статус_норм')
        return

    dict_norm = calc_top(self, dict_norm, poz.dict_tables['пл_топ'])

    if len(list_mk) == 0:
        # ============================НЕТ МК==================
        fl_calc_vo = False

        if name_predv_res != '':
            # ================по ТКП================
            resp = CSQ.custom_request_c(self.db_resxml, f"""SELECT data FROM predv_res WHERE Имя = ?;""",
                                        list_of_lists_c=(name_predv_res,))
            if resp != False and resp != None and len(resp) == 2:
                if not CQT.msgboxgYN(f'МК не создана, загрузить нормы по аналогу/ТКП?'):
                    return
                dict_norm, list_log = calc_by_tkp(resp, poz, dict_norm, koef_vneplana, koef_pogr_norm, pnom,
                                                  nk_stat_norm)
            else:
                fl_calc_vo = True
            # ======================================
        else:
            if not CQT.msgboxgYN(f'МК не создана и Ресурсная на аналог не создана, загрузить нормы по ВО?'):
                return
            fl_calc_vo = True

        if fl_calc_vo:
            dict_norm = calc_by_vo(self, pnom, dict_norm, nk_stat_norm)
        if dict_norm == None:
            CQT.msgbox(f'Ошибка расчета норм')
            return
        for key in dict_norm.keys():
            dict_norm[key] *= koef_pogr_norm
        dict_norm['пл_сб.Нчас_сб'] = round((dict_norm['пл_сб.Нчас_слсб'] + dict_norm['пл_сб.Нчас_св'] +
                                            dict_norm['пл_сб.Нчас_зач']) * koef_vneplana, 2)
    # =====================================================
    else:  # ПО МК
        tmp_log = []
        list_log = []
        for mk_item in list_mk:
            mk = mk_item['Пномер']
            count_izd = mk_item['Количество']
            res = CMS.load_res(int(mk))
            # count_izd = poz.dict_tables['пл_оуп']['Количество']

            tmp_log = tmp_log_calc(res,tmp_log)


            ves, ves_res_list = self.raschet_vesa_dse(res,False)
            if ves != mk_item['Вес']:
                CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Вес = {ves} WHERE Пномер = {int(mk)};""")
                CQT.msgbox(f'В МК {mk} обновлен вес, было {mk_item["Вес"]} кг., стало {ves} кг.')
            if count_izd == None or count_izd == '' or not F.is_numeric(count_izd):
                CQT.msgbox(f'{"пл_оуп.Количество"} не число')
            dict_norm, list_log = dict_norm_from_res(self, res, dict_norm, koef_vneplana, koef_pogr_norm, count_izd,
                                                     list_log, mk)#TODO
            if dict_norm == None:
                return

        CQT.msgboxg_get_table(self, 'Расчет веса для TEST', tmp_log, 'OK', disable_btn1=True, load_summ=True)

        CSQ.custom_request_c(self.db_kplan, f"""UPDATE plan SET Статус_норм = 2 WHERE Пномер = {pnom} """)
        if nk_stat_norm:
            tbl.item(tbl.currentRow(), nk_stat_norm).setText(self.Data_plan.DICT_STATUS_NORM[2]['Имя'])
        for compose in self.Data_plan.DICT_COMPOSITE_PODRAZD.values():
            name_compose =f"{compose['name']}.{compose['main_comp_field_name']}"
            summ_compose = 0
            for inp_field in compose['dict_input_fields'].keys():
                name_inp_field = f"{compose['name']}.{inp_field}"
                summ_compose+= dict_norm[name_inp_field]
            dict_norm[name_compose] = round(summ_compose, 2)
    list_change = fill_norm_db(self, dict_norm, pnom, poz.row_time_etap, poz.row_time_add_etap)

    for field in dict_norm:
        nk_field = CQT.num_col_by_name_c(tbl, field)
        if nk_field != None:
            tbl.item(tbl.currentRow(), nk_field).setText(str(round(dict_norm[field] / 60, 2)))

    if list_change:
        GPL.update_local_graf(self, update=True, pnom=pnom)
        obj_msg = CMS.Msg_b24(self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, pnom)
        if not self.USER_CONFIG.is_developer:
            obj_msg.send_msg('recalc_dates_disp', pprint.pformat(list_change))

    CMS.Pozition.set_flag_recalc_dates(self.db_kplan, pnom, 1)
    if CQT.num_col_by_name_c(tbl, 'plan.Потребность_пересч_сроков') != None:
        CQT.set_val_tbl_by_name(self.ui.tbl_kal_pl, self.ui.tbl_kal_pl.currentRow(), 'plan.Потребность_пересч_сроков',
                                '1')
    CQT.select_range(tbl, tbl.currentRow(), tbl.currentColumn())
    tbl.setFocus()
    msg_change = ''
    if list_change:
        msg_change = f'Изменения:\n{ pprint.pformat(list_change)}\n'
    if list_log:
        if CQT.msgboxgYN(f'Успешно!\n {msg_change} Показать таблицу норм пооперационно?'):
            CQT.msgboxg_get_table(self, 'Расчет веса для сравнения', list_log, 'OK', disable_btn1=True, load_summ=True)
    else:
        CQT.msgbox(f'Успешно\n {msg_change}')



def get_zc_data_from_ERP(self,Ref_Key_py,nomen_name,m=None):
    is_order_sb = False
    if not m:
        m = CODAT.OrdersComposit(self.USER_CONFIG.ERP_base_name['Значение'])

    data_py = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                             wet_filtr=f"?$filter=Ref_Key eq guid'{Ref_Key_py}' &$select=ДокументОснование,ДокументОснование_Type")


    if data_py[0]['ДокументОснование_Type'] not in (
    'StandardODATA.Document_ЗаказКлиента', 'StandardODATA.Document_ЗаказНаСборку'):
        CQT.msgbox(f"Основание для {self.place.doc_prefix}:\n{data_py['ДокументОснование_Type']}.\n Нужен Заказа клиента/Заказ на сборку")
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


    data_co_wet = m.get_response(doc_name='Document_ЗаказКлиента',
                                 wet_filtr=f"?$filter=Ref_Key eq guid'{client_order}' &$select=ДатаОтгрузки,НеОтгружатьЧастями,"
                                           f"Товары,ЭтапыГрафикаОплаты", get_response_val=False)
    data_co = data_co_wet['value'][0]
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
        rez = CMS.update_data_etaps_from_erp(self.db_kplan,self.glob_dict_etaps_from_erp,znpr_num[0])
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
    js_data = {'odata.metadata':meta_co,
               'НеОтгружатьЧастями': parts,
                   'ДатаОтгрузки':max_data,
                   'Товары':struct,
               'ЭтапыГрафикаОплаты':struct_etaps}
    m.params = js_data
    cod, rez = m.patch_responce(doc_name=f"Document_ЗаказКлиента(guid'{client_order}')")
    if cod != 200:
        msg = ''
        if isinstance(rez, str):
            msg = rez
        CQT.msgbox(f'Ошибка при изменении {cod}\n{msg}')
        return

    cod, rez =    m.undertake_doc('Document_ЗаказКлиента',client_order)
    if cod != 200:
        msg = ''
        if isinstance(rez, str):
            msg = rez
        CQT.msgbox(f'Ошибка при проведении {cod}\n{msg}')
        return

    GPL.tab_addit_info_poz_gant_click(self, self.ui.tab_addit_info_poz_gant.currentIndex())
    CQT.msgbox(f'Успешно',time_life=0.5)



@CQT.onerror
def get_fill_dates_etap_DELETE(self: mywindow):
    path = r'O:\Журналы и графики\Ведомости для передачи\Sroki_etapov.txt'
    if not F.existence_file_c(path):
        CQT.msgbox(f'файл не найден')
        return
    list_proj = F.list_of_lists_to_list_of_dicts(F.open_file_c(path, False, "|", False))
    dict_names = {'Резка': ['пл_заг', 'ПДата_нач_заг', 'ПДата_зав_заг'],
                  'Мех_обработка': ['пл_мех', 'Пдата_нач_мехобр', 'Пдата_зав_мехобр'],
                  'Сборка+сварка': ['пл_сб', "Пдата_нач_сб", ''],
                  'Зачистка': ['пл_сб', "", 'Пдата_зав_сб'],
                  'Покрытие': ['пл_покр', "Пдата_нач_покр", 'Пдата_зав_покр'],
                  'Упаковка': ['пл_компл', "ПДата_нач_комплект_упаковки", 'ПДата_зав_комплект_упаковки'],
                  'Всп': ['пл_отк', "Пдата_нач_контр", 'Пдата_зав_контр']}
    set_proj = set(['"' + _['Номер проекта'] + '$' + _['Номер заявки'] + '"' for _ in list_proj])
    list_proj_str = ','.join(set_proj)

    query = f"""SELECT пл_оуп.НомПл, пл_оуп.№проекта || '$' || пл_оуп.№ERP as Проект, 
    пл_заг.ПДата_нач_заг, пл_заг.ПДата_зав_заг, пл_заг.ФДата_нач_заг, пл_заг.ФДата_зав_заг, 
    пл_мех.Пдата_нач_мехобр, пл_мех.Пдата_зав_мехобр, пл_мех.Фдата_нач_мехобр, пл_мех.Фдата_зав_мехобр, 
    пл_компл.Дата_комплект_под_сб, пл_компл.ПДата_нач_комплект_упаковки,  пл_компл.ПДата_зав_комплект_упаковки, 
    пл_компл.ФДата_нач_комплект_упаковки,  пл_компл.ФДата_зав_комплект_упаковки, 
    пл_сб.Пдата_нач_сб, пл_сб.Пдата_зав_сб, пл_сб.Фдата_нач_сб, пл_сб.Фдата_зав_сб, 
    пл_покр.Пдата_нач_покр, пл_покр.Пдата_зав_покр, пл_покр.Фдата_нач_покр, пл_покр.Фдата_зав_покр, 
    пл_отк.Пдата_нач_контр, пл_отк.Пдата_зав_контр, пл_отк.Фдата_нач_контр, пл_отк.Фдата_зав_контр 
    
    FROM пл_оуп
    INNER JOIN 
     
    пл_заг   ON пл_заг.НомПл    = пл_оуп.НомПл, 
    пл_мех   ON пл_мех.НомПл    = пл_оуп.НомПл, 
    пл_компл ON пл_компл.НомПл  = пл_оуп.НомПл, 
    пл_сб    ON пл_сб.НомПл     = пл_оуп.НомПл, 
    пл_покр  ON пл_покр.НомПл   = пл_оуп.НомПл, 
    пл_отк   ON пл_отк.НомПл    = пл_оуп.НомПл 
    
     WHERE пл_оуп.№проекта || '$' || пл_оуп.№ERP IN ({list_proj_str})"""
    res = CSQ.custom_request_c(self.db_kplan, query, rez_dict=True)
    set_rows = set()
    list_not_find_rows = []
    fl_fill = False
    for item in res:
        proj = item['Проект']
        for row in list_proj:
            if row['Номер проекта'] + '$' + row['Номер заявки'] == proj:
                fl_fill = True
                for key in dict_names:
                    if key in row:
                        nach, kon = row[key].split("/")
                        if nach != '':
                            nach = F.datetostr(F.strtodate(nach, '%d.%m.%Y'), "%Y-%m-%d")
                            if dict_names[key][1] in item:
                                if item[dict_names[key][1]] != nach:
                                    pass
                                    print(f'В {dict_names[key][0]} было {item[dict_names[key][1]]} стало {nach}')
                                    query = f"""UPDATE {dict_names[key][0]} SET {dict_names[key][1]} = "{nach}" WHERE НомПл = {item['НомПл']}"""
                                    CSQ.custom_request_c(self.db_kplan, query)
                                    set_rows.add(item['НомПл'])
                                    F.sleep(0.25)
                        if kon != "":
                            kon = F.datetostr(F.strtodate(kon, '%d.%m.%Y'), "%Y-%m-%d")
                            if dict_names[key][2] in item:
                                if item[dict_names[key][2]] != kon:
                                    pass
                                    print(f'В {dict_names[key][0]} было {item[dict_names[key][2]]} стало {kon}')
                                    query = f"""UPDATE {dict_names[key][0]} SET {dict_names[key][2]} = "{kon}" WHERE НомПл = {item['НомПл']}"""
                                    CSQ.custom_request_c(self.db_kplan, query)
                                    set_rows.add(item['НомПл'])
                                    F.sleep(0.25)
        if fl_fill == False:
            list_not_find_rows.append(item['НомПл'])
    for row in set_rows:
        GPL.update_local_graf(self, True, row, False)
    CQT.msgbox(f'Успешно')


@CQT.onerror
def update_tabels(self: mywindow):
    def load_month_for_apply_diap_dates_to_sb_in_tbl(self: mywindow):
        cmb = self.ui.cmb_apply_diap_dates_to_sb_in_tbl
        cmb.clear()
        cmb.addItem('')
        cmb.addItem('Не в плане')
        rez = CSQ.custom_request_c(self.db_kplan, f"""SELECT Дата   FROM mnts_plan WHERE file_poz_plan IS NOT NULL AND poki == {self.place.poki} ORDER BY Дата""",
                                   rez_dict=True)
        for month in rez:
            if month['Дата']:
                cmb.addItem(month['Дата'])

    def temporary_fix(self):
        pass
        for name, val in self.Data_plan.DICT_STATUS_POZ_NAME.items():
            CSQ.custom_request_c(self.db_kplan,
                                 f"""UPDATE plan SET (Статус) = ({val['Пномер']}) WHERE Статус = "{name}";""")
        for name, val in self.Data_plan.DICT_STATUS_NORM_NAME.items():
            CSQ.custom_request_c(self.db_kplan,
                                 f"""UPDATE plan SET (Статус_норм) = ({val['Код']}) WHERE Статус_норм = "{name}";""")

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
    self.edit_tabel_mode = False
    if "val_masht" not in dir(self):
        self.val_masht = 12
        try:
            self.val_masht = int(CMS.load_tmp_path('mk_val_masht'))
        except:
            pass
    VPL.load_diapazon_month(self)
    load_gui(self)
    self.ui.splitter_pl.setSizes([400, 180])

    VPL.get_max_mosh_from_db(self)
    self.glob_kpl_summ_selct_tbl = ''
    self.dict_form_kpl = ''
    KPLUF.fill_pl_user_filtrs(self)
    load_month_for_apply_diap_dates_to_sb_in_tbl(self)

    m = CODAT.OrdersComposit(self.USER_CONFIG.ERP_base_name['Значение'])

    self.DICT_plan_erp_nomen_refs = F.deploy_dict_c(m.get_response(doc_name='Catalog_Номенклатура',
                               wet_filtr=f"""?$select= Ref_Key, Description, Артикул""",lazy_method_huours = 2), 'Ref_Key')

    self.DICT_plan_erp_Пользователи = F.deploy_dict_c(m.get_response(doc_name=f"Catalog_Пользователи",
                               wet_filtr=f"?$select=Ref_Key, Description",lazy_method_huours = 24), 'Ref_Key')

    self.DICT_plan_erp_ПричиныПриостановкиПроизводства = F.deploy_dict_c(m.get_response(doc_name=f"Catalog_ПричиныПриостановкиПроизводства",
                               wet_filtr=f"?$select=*",lazy_method_huours = 24), 'Ref_Key')


    self.glob_kpl_pull_poz_dict = dict()
    self.ui.splitter_4.setSizes([400, 0])
    self.ui.splitter_pl.setSizes([400, 0])
    self.ui.splitter_gant_local.setSizes([1040, 871])
    self.ui.fr_tree_fields.setHidden(True)
    self.ui.tbl_kal_pl.blockSignals(False)
    self.ui.fr_plan_day_edit.setHidden(True)
    self.ui.fr_poz_from_exel.setHidden(True)
    self.ui.fr_gant_local_tbl.setHidden(False)


def select_row(self: mywindow):
    if self.ui.splitter_pl.sizes()[1] == 0:
        return
    GPL.update_local_graf(self)
    GPL.fill_select_poz_kpl(self)
    self.ui.btn_pl_send_dates_into_ERP.setEnabled(False)
    self.ui.tab_addit_info_poz_gant.blockSignals(True)
    self.ui.tab_addit_info_poz_gant.setCurrentIndex(0)
    self.ui.tab_addit_info_poz_gant.blockSignals(False)

@CQT.onerror
def load_gui(self: mywindow, *args):
    show_fr(self)

    load_table_db(self)

    self.kpl_mode = 0  # объемный выключен
    self.kpl_mode_pull = 0  # компоновщик выключен


def btn_pl_add_poz_click(self):
    if self.regim == '':
        show_fr(self, 'tbl_add')
        load_tbl_add_new_poz(self)
        self.regim = 'add'
    else:
        show_fr(self)
        self.regim = ''


@CQT.onerror
def plan_day_edit_set_weekend(self: mywindow, *args):
    tbl_gant = self.ui.tbl_preview
    weekends = CMS.Plan_custom_weekends(self.pnom_kplan_select)

    if 'shift' in CQT.get_key_modifiers(self):

        list_days_oform = weekends.get_list_weekends()
        list_del = CQT.msgboxg_get_table(self,'Дни к удалению',list_days_oform,'Удалить','Отмена',ExtendedSelection=True,sortingEnabled=True)
        if not list_del:
            return
        weekends.del_days({F.strtodate(_['Не рабочие дни'],"%Y-%m-%d" ) for _ in list_del})


    else:
        selection_cells = CQT.get_selected_cells_coordinates(tbl_gant)
        list_days_parts = [tbl_gant.horizontalHeaderItem(_[1]).text().split('\n') for _ in selection_cells]
        list_days_oform = [f'{_[3]} - {".".join(_[:3])}' for _ in list_days_parts]
        list_days_oform.insert(0,'Не рабочие дни')
        list_days = [F.strtodate('.'.join(_[:3]), "%d.%m.%y") for _ in list_days_parts]
        ans = CQT.msgboxg_get_table(self,'Дни к добавлению',list_days_oform,'Продолжить',yesNoMode=True)
        if not ans:
            return
        weekends.add_days(set(list_days))
    GPL.update_local_graf(self,update=True)
    #CQT.msgbox(f'Успешно. Теперь нужно пересчитать гант')



@CQT.onerror
def plan_day_edit_recalc(self: mywindow, *args):
    tbl_gant:QtWidgets.QTableWidget = self.ui.tbl_preview
    line = CQT.get_dict_line_form_tbl(tbl_gant)
    if len(tbl_gant.selectedIndexes()) > 1:
        CQT.msgbox(f'Нужно выбрать одну строку')
        return
    if len(line) == 0:
        CQT.msgbox(f'Не выбран этап в ганте')
        return
    curr_field = line['Этап']
    if curr_field[:4] in ('план', 'факт'):
        pl_name = 'план' + curr_field[4:]
        f_name = 'факт' + curr_field[4:]
    else:
        CQT.msgbox(f'Не подходящий этап')
        return

    poz = CMS.Pozition(self.pnom_kplan_select, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users,
                       self, False, None, True)
    dict_fact_jur = poz.recalc_get_day_plan_as_fact(pl_name, f_name)
    if dict_fact_jur == None:
        return
    self.Data_plan.DICT_REPLACE_BY_DAYS = dict_fact_jur
    GPL.update_local_graf(self, True, self.pnom_kplan_select, True)
    CQT.msgbox(f'Успешно')


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
        self.ui.cmb_for_adapt.addItems(CMS.get_shablon_vidov(self.DICT_PROFESSIONS))

        self.kpl_mode_pull = 1  # объемный вылючен
    else:
        self.ui.fr_pull_poz.setHidden(True)
        self.kpl_mode_pull = 0


@CQT.onerror
def btn_pl_mode(self):
    def check_one_napr_filtr(self):
        tbl = self.ui.tbl_kal_pl
        set_napr = set()
        nf_napr = CQT.num_col_by_name_c(tbl, 'Направление')
        for i in range(tbl.rowCount()):
            if not tbl.isRowHidden(i):
                set_napr.add(tbl.item(i, nf_napr).text())
        if len(set_napr) != 1:
            return False
        return list(set_napr)[0]

    def get_koef_selected_napr(self):
        for dic in self.Data_plan.DICT_NAPRAVLENIE.values():
            if dic['name'] == self.selected_napr:
                return dic['val'] / 100
        return 0

    def count_rows():
        tbl = self.ui.tbl_kal_pl

        cntr = 0
        for i in range(tbl.rowCount()):
            if not tbl.isRowHidden(i):
                cntr +=1
        return  cntr

    if 'kpl_mode' not in self.__dict__:
        self.kpl_mode = 1

    if self.kpl_mode == 0:  # объемный выключен
        self.selected_napr = None
        self.selected_napr_koef = 1
        selected_napr = check_one_napr_filtr(self)
        if not selected_napr:
            if not CQT.msgboxgYN(f'В фильтре таблицы должно быть не более 1 направления для генерации графика мощности.\n Продолжить?'):
                return
        else:
            self.selected_napr = selected_napr
            self.selected_napr_koef = get_koef_selected_napr(self)

        if count_rows() > 100:
            if not CQT.msgboxgYN(f'В таблице более 100 строк, выгрузка займет достаточно много времени.\n Продолжить?'):
                return

        show_fr(self, graf=1)  # объемный включаем
        self.kpl_mode = 1  # объемный включен
        self.ui.fr_svod.setHidden(True)
        VPL.load_tbl_gant(self)  # объемный загрузка
    else:
        load_gui(self)  # объемный выключить
        self.selected_napr_koef = 1
        self.kpl_mode = 0


@CQT.onerror
def clck_tbl_verticalHeader(self, row, *args):
    tbl = self.ui.tbl_pl_gaf
    tbl_filtr = self.ui.tbl_filtr_kal_pl
    c = tbl.currentColumn()
    etap = tbl.item(row, CQT.num_col_by_name_c(tbl, 'Этап')).text()

    self.ui.tbl_pl_gaf_filtr.item(0, CQT.num_col_by_name_c(tbl, 'Этап')).setText(etap)


def kal_pl_left(self):
    tbl = self.ui.tbl_pl_add_poz
    column = tbl.currentColumn()
    if column == None or column == -1 or column == 0:
        return
    spis = CQT.list_from_wtabl_c(tbl, hat_c=True)
    spis_new = copy.deepcopy(spis)
    spis_new[0].pop(column)
    spis_new[1].pop(column)
    spis_new[0].insert(column - 1, spis[0][column])
    spis_new[1].insert(column - 1, spis[1][column])
    fill_tbl_settings(self, spis_new)
    tbl.selectColumn(column - 1)


def kal_pl_right(self):
    tbl = self.ui.tbl_pl_add_poz
    column = tbl.currentColumn()
    spis = CQT.list_from_wtabl_c(tbl, hat_c=True)
    if column == None or column == -1 or column == len(spis[0]) - 1:
        return
    spis_new = copy.deepcopy(spis)
    spis_new[0].pop(column)
    spis_new[1].pop(column)
    spis_new[0].insert(column + 1, spis[0][column])
    spis_new[1].insert(column + 1, spis[1][column])
    fill_tbl_settings(self, spis_new)
    tbl.selectColumn(column + 1)


def fill_tbl_settings(self: mywindow, list_conf):
    def check_val(self: mywindow, checked, row, col):
        self.ui.tbl_pl_add_poz.item(row, col).setText(str(int(checked)))

    CQT.fill_wtabl(list_conf, self.ui.tbl_pl_add_poz)
    for j in range(self.ui.tbl_pl_add_poz.columnCount()):
        val = 1
        if list_conf[-1][j] != 1:
            val = 0
        CQT.add_check_box(self.ui.tbl_pl_add_poz, 0, j, val=val, conn_func_checked_row_col=check_val, self=self)
        if list_conf[0][j] in LIST_FREEZE_FIELDS:
            self.ui.tbl_pl_add_poz.cellWidget(0, j).setEnabled(False)


def btn_pl_settings(self):
    if self.regim == '':
        show_fr(self, 'tbl_add')
        self.ui.btn_kal_pl_left.setHidden(False)
        self.ui.btn_kal_pl_right.setHidden(False)
        db, list_conf = load_db(self)
        fill_tbl_settings(self, list_conf)
        self.regim = 'cnf'
    else:
        show_fr(self)
        self.regim = ''


def create_list_fields(self):
    'Загрузка всех полей с БД'
    list_tables = ['plan','mk.Дата_завершения','mk.Вес','mk.xml', 'знпр']
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
    for table in list_tables:
        if '.' in table:
            table , fields = table.split('.')
            fields = [fields]
        else:
            fields = CSQ.list_of_columns_c(self.db_kplan, table)
        for field in fields:
            name_field = f'{table}.{field}'
            dict_fields[name_field] = 1
            if name_field in self.Data_plan.DICT_INFO_FIELDS_KPL:
                if self.Data_plan.DICT_INFO_FIELDS_KPL[name_field]['hide'] == 1:
                    dict_fields[name_field] = 0
    return dict_fields


def fix_old_field_path(new_path: str):
    import shutil
    old_path = 'Config\\fields.pickle'
    if os.path.exists(old_path):
        shutil.move(old_path, new_path)


def load_list_fields(self, all=False):
    """Приостановка отключенных полей из конфига"""
    path = os.path.join(CMS.tmp_dir(), 'fields.pickle')
    fix_old_field_path(path)
    dict_fields_mes = create_list_fields(self)
    if F.existence_file_c(path) and all == False:
        dict_cnf = F.load_file_pickle(path)
        tmp_list = [['n', 'fied']]
        max_n = 0
        for field, val in dict_fields_mes.items():
            if field in dict_cnf and val == 1 and field not in LIST_HIDE_FIELDS:
                tmp_list.append([dict_cnf[field]['order'], field])
                if dict_cnf[field]['order'] > max_n:
                    max_n = dict_cnf[field]['order']

        for field, val in dict_fields_mes.items():
            if field in dict_cnf and val == 0 or field in LIST_HIDE_FIELDS:
                max_n+=1
                tmp_list.append([max_n, field])

        tmp_list = F.sort_by_column_c(tmp_list, 'n')
        for field, val in dict_fields_mes.items():
            if field not in dict_cnf:
                tmp_list.append([tmp_list[-1][0] + 1, field])
        dict_fields = [[], []]
        for i in range(1, len(tmp_list)):
            dict_fields[0].append(tmp_list[i][1])
            if tmp_list[i][1] in dict_cnf and dict_fields_mes[tmp_list[i][1]] == 1:
                dict_fields[1].append(dict_cnf[tmp_list[i][1]]['hidden'])
            else:
                dict_fields[1].append(dict_fields_mes[tmp_list[i][1]])
        return dict_fields
    else:
        tmp_list = [['n', 'fied']]
        max_n = 0
        for i, field in enumerate(dict_fields_mes.keys()):
            if dict_fields_mes[field] == 1 and field not in LIST_HIDE_FIELDS:
                tmp_list.append([i, field])
                max_n = i

        for i, field in enumerate(dict_fields_mes.keys()):
            if dict_fields_mes[field] == 0 or field in LIST_HIDE_FIELDS:
                max_n+=1
                tmp_list.append([max_n, field])
        dict_fields = [[], []]
        for i in range(1, len(tmp_list)):
            dict_fields[0].append(tmp_list[i][1])
            dict_fields[1].append(dict_fields_mes[tmp_list[i][1]])
    return dict_fields


def btn_pl_edit_poz_click(self):
    if self.regim == '':
        show_fr(self, 'tbl_edit')
        load_tbl_edit_poz(self)
        self.regim = 'edit'
    else:
        show_fr(self)
        self.regim = ''


def oform_table_editeble(self, tbl, name_field):
    for i in range(tbl.columnCount()):
        if 'дата' in tbl.horizontalHeaderItem(i).text().lower() or name_field.lower() == \
                self.ui.tbl_pl_add_poz.horizontalHeaderItem(i).text().lower().split('.')[-1]:
            CQT.set_cell_editable(tbl, 0, i, False)
            CQT.set_color_wtab_c(tbl, 0, i, 230, 230, 230)
        else:
            CQT.set_cell_editable(tbl, 0, i, True)

def check_permisions_on_fields(header: str, value: str, self) -> bool:
    if getattr(self, 'regim') == 'add':
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
    filtr_poki = list(self.Data_plan.DICT_PODR_POKI.keys())
    list_podr = [_ for _ in CSQ.get_list_of_tables_c(self.db_kplan) if 'пл_' in _ and _ in filtr_poki]
    list_podr.append('plan')
    list_podr.append('')
    list_podr.sort()

    list_colors = []
    list_tooltip = []
    for podr in list_podr:
        tooltip = ''
        color = ('255;55;0')
        if podr in self.Data_plan.DICT_PODR:
            color = self.Data_plan.DICT_PODR[podr]['Цвет']
            tooltip = self.Data_plan.DICT_PODR[podr]['Наименование']
        list_colors.append(F.align_colors(color,';'))
        list_tooltip.append(tooltip)
    # list_colors = [QtGui.QColor.setRgb(*self.Data_plan.DICT_PODR[_]['Цвет'].split(';'))  for _ in list_podr]
    # self.ui.cmb_etap.addItems(list_podr)
    # self.ui.cmb_etap.setMaxVisibleItems(len(list_podr))
    attach_tbl_pl_add_poz_validator(self, self.ui.tbl_pl_add_poz)
    CQT.fill_list_combobx(self, self.ui.cmb_etap, list_podr, list_colors, list_tooltip)
    CQT.clear_tbl(self.ui.tbl_pl_add_poz)

@CQT.onerror
def open_pkk(self: mywindow, row='', col=''):
    self.current_kpl_table = 'tbl_preview'
    row = CQT.get_dict_line_form_tbl(self.ui.tbl_kal_pl, row)

    if 'plan.Пномер' not in row:
        return
    pozition = CMS.Pozition(row['plan.Пномер'], self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
    pozition.load_kpl_table('пл_оуп')
    nom_file = pozition.dict_tables['пл_оуп']['ПКК']
    if not F.is_numeric(nom_file):
        return
    if not isinstance(F.valm(nom_file), int):
        return
    nom_file = int(nom_file)
    rez = CSQ.custom_request_c(self.bd_files,
                               f'''SELECT file_name, file FROM project_cards WHERE s_nom = {nom_file}''',
                               one=True)
    if len(rez) <= 1:
        CQT.msgbox(f'Файл s_num {nom_file} в project_cards не найден')
        return
    file_blob_compr = rez[-1][1]
    file_name = rez[-1][0]
    file_blob = F.unpack_byte_file(file_blob_compr)
    dir_tmp = F.put_po_umolch() + F.sep() + 'tmp_file_view'
    try:
        if F.existence_file_c(dir_tmp):
            F.delete_dir_c(dir_tmp)
        F.create_dir_c(dir_tmp)
    except:
        CQT.msgbox(f'ОШибка доступа {dir_tmp}')
        return
    path_file = dir_tmp + F.sep() + file_name
    if F.existence_file_c(path_file):
        return
    F.save_binary_convert_to_file(file_blob, path_file)
    F.run_file_os_c(path_file)
@CQT.onerror
def doubleclck_tbl_kal_pl(self: mywindow, row='', col=''):
    tbl = self.ui.tbl_kal_pl
    col = tbl.currentColumn()
    row = tbl.currentRow()
    field_name = tbl.horizontalHeaderItem(col).text()
    if field_name == 'пл_ко.Ссылка_КД':
        val = tbl.item(row,col).text()
        if ':' in val:
            try:
                os.startfile(val)
            except:
                CQT.msgbox(f'Ошибка открытия ссылки')



@CQT.onerror
def select_etap_edit(self: mywindow):
    def add_file_pkk(checked, row, col):

        num_poz = int(self.ui.tbl_pl_add_poz.item(0, CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'НомПл')).text())

        dir = CMS.load_tmp_path('kpl_pkk')
        file_path = CQT.f_dialog_name(self, 'Выбрать файл с карточкой проекта', dir, '*', True)
        if file_path == '.':
            return
        name = file_path.split(F.sep())[-1]
        CMS.save_tmp_path('kpl_pkk', file_path, True)
        print(file_path)

        file_founding = F.load_file_convert_to_binary(file_path)
        size = sys.getsizeof(file_founding)
        if size > 1048576 * 3:
            CQT.msgbox(f'Размер файла должен быть не более 3 мб')
            return
        hash = hashlib.sha1(file_founding).hexdigest()
        file_founding = F.pack_byte_file(file_founding)
        print(f'size {size}')

        rez = CSQ.custom_request_c(self.bd_files,
                                   f'''SELECT s_nom FROM project_cards WHERE size = {size} AND hash = "{hash}"''',
                                   one_column=True, one=True)
        if len(rez) > 1:
            rez = rez[-1]
        else:
            CSQ.custom_request_c(self.bd_files,
                                 """INSERT INTO  project_cards(file_name,size,hash,file) VALUES (?,?,?,?);""",
                                 list_of_lists_c=[[name, size, hash, file_founding]])
            rez = CSQ.custom_request_c(self.bd_files,
                                       f'''SELECT s_nom FROM project_cards WHERE size = {size} AND hash = "{hash}"''',
                                       one_column=True, one=True)[-1]
        CSQ.custom_request_c(self.db_kplan, f"""UPDATE пл_оуп SET ПКК = {rez} WHERE  НомПл = {num_poz};""")
        self.ui.tbl_pl_add_poz.item(0, CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'ПКК')).setText(str(rez))

    def edit_tabel(self):
        month = self.ui.cmb_etap.currentText()
        if month == '':
            return
        list_month = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM {month}""")
        set_editeble_columns = set()
        for i in range(len(list_month[0])):
            if F.is_date(list_month[0][i], "d_%Y_%m_%d"):
                set_editeble_columns.add(i)
        CQT.fill_wtabl(list_month, self.ui.tbl_pl_add_poz, set_editeble_col_nomera=set_editeble_columns,
                       colorful_edit=True)

    def edit_etap(self):


        podr = self.ui.cmb_etap.currentText()
        tbl_pl = self.ui.tbl_kal_pl
        row = tbl_pl.currentRow()
        if row == None or row == -1:
            return
        if podr == "":
            CQT.clear_tbl(self.ui.tbl_pl_add_poz)
            return
        name_field = 'НомПл'
        if podr == "plan":
            name_field = 'Пномер'
        nk_pnom = int(CQT.num_col_by_name_c(tbl_pl, 'plan.Пномер'))
        pnom = tbl_pl.item(row, nk_pnom).text()
        list_itog = get_line_to_edit_podr(self, pnom)
        CQT.fill_wtabl(list_itog, self.ui.tbl_pl_add_poz, auto_type=False)
        for field in LIST_HIDE_FIELDS:
            if field.split('.')[0] == podr:
                nk = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, field.split('.')[1])
                if nk != None:
                    self.ui.tbl_pl_add_poz.setColumnHidden(nk, True)
        oform_table_editeble(self, self.ui.tbl_pl_add_poz, name_field)
        if podr == 'plan':
            list_napr_deyat = dict()
            for key in self.Data_plan.DICT_NAPR_DEYAT.keys():
                list_napr_deyat[self.Data_plan.DICT_NAPR_DEYAT[key]['Имя']] = self.Data_plan.DICT_NAPR_DEYAT[key][
                    'Псевдоним']
            nk_napr_deyat = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Направление_деятельности')
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_napr_deyat, list_napr_deyat, first_void=False,
                             conn_func=select_napr_deyat)

            try:
                self.ui.tbl_pl_add_poz.cellWidget(0, nk_napr_deyat).setCurrentText(
                    self.Data_plan.DICT_NAPR_DEYAT[int(self.ui.tbl_pl_add_poz.item(0, nk_napr_deyat).text())]['Имя'])
            except:
                pass
            list_status = []
            for key in self.Data_plan.DICT_STATUS_POZ.keys():
                list_status.append(self.Data_plan.DICT_STATUS_POZ[key]['Имя'])
            nk_status = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Статус')
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_status, list_status, first_void=False,
                             conn_func=select_status)
            try:
                self.ui.tbl_pl_add_poz.cellWidget(0, nk_status).setCurrentText(
                    self.Data_plan.DICT_STATUS_POZ[int(self.ui.tbl_pl_add_poz.item(0, nk_status).text())]['Имя'])
            except:
                pass
            list_status_norm = []
            for key in self.Data_plan.DICT_STATUS_NORM.keys():
                list_status_norm.append(self.Data_plan.DICT_STATUS_NORM[key]['Имя'])
            nk_status_norm = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Статус_норм')
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_status_norm, list_status_norm, first_void=False,
                             conn_func=select_status_norm)
            try:
                self.ui.tbl_pl_add_poz.cellWidget(0, nk_status_norm).setCurrentText(
                    self.Data_plan.DICT_STATUS_NORM[int(self.ui.tbl_pl_add_poz.item(0, nk_status_norm).text())]['Имя'])
            except:
                pass

            list_etapi_erp = []
            for key in self.Data_plan.DICT_STATUS_ETAPI_ERP.keys():
                list_etapi_erp.append(self.Data_plan.DICT_STATUS_ETAPI_ERP[key]['Имя'])
            nk_etapi_erp = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Этапы_ЕРП')
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_etapi_erp, list_etapi_erp, first_void=False,
                             conn_func=select_etapi_erp)
            try:
                self.ui.tbl_pl_add_poz.cellWidget(0, nk_etapi_erp).setCurrentText(
                    self.Data_plan.DICT_STATUS_ETAPI_ERP[int(self.ui.tbl_pl_add_poz.item(0, nk_etapi_erp).text())][
                        'Имя'])
            except:
                pass
        if podr == 'пл_топ':
            list_sort_c = []
            for key in self.Data_plan.DICT_VID_PO_NAPR.keys():
                list_sort_c.append(self.Data_plan.DICT_VID_PO_NAPR[key]['Имя'])
            nk_sort_c = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Вид')
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_sort_c, list_sort_c, first_void=False,
                             conn_func=select_sort_c)
            list_tech = []
            for key in self.DICT_EMPLOEE_FULL.keys():
                if self.DICT_EMPLOEE_FULL[key]['Подразделение'] == 'Технологический отдел Производства':
                    list_tech.append(key)
            list_tech = sorted(list_tech)
            nk_otv_tech = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Отв_технолог')
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_otv_tech, list_tech, first_void=True,
                             conn_func=select_tech)
            nk_otv_tech_res = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Отв_по_ресурсной')
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_otv_tech_res, list_tech, first_void=True,
                             conn_func=select_tech)
            try:
                self.ui.tbl_pl_add_poz.cellWidget(0, nk_sort_c).setCurrentText(
                    self.Data_plan.DICT_VID_PO_NAPR[int(self.ui.tbl_pl_add_poz.item(0, nk_sort_c).text())]['Имя'])
            except:
                pass
        if podr == 'пл_оуп':
            nk_py = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, '№ERP')
            nk_poz = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Номенклатура_ЕРП')
            list_py = generate_list_py(self)
            if list_py == None:
                self.regim = ''
                show_fr(self)
                return
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_py, list_py, first_void=False,
                             conn_func=select_py)
            line_tbl = CQT.get_dict_line_form_tbl(self.ui.tbl_pl_add_poz, 0)
            if not F.is_date(line_tbl['Дата_заявки_на_произв'], "%Y-%m-%d"):
                CQT.msgbox(f'Дата_заявки_на_произв не указана')
            else:
                year = F.datetostr(F.strtodate(line_tbl['Дата_заявки_на_произв']), "%Y")
                self.ui.tbl_pl_add_poz.cellWidget(0, nk_py).setCurrentIndex(0)
                for py_str in list_py:
                    if line_tbl['№ERP'] == py_str.split('|')[1] and year == py_str.split('|')[0]:
                        self.ui.tbl_pl_add_poz.cellWidget(0, nk_py).setCurrentText(py_str)
                        select_py(self, py_str, 0, nk_py)
                        fl_poz = False
                        if self.ui.tbl_pl_add_poz.cellWidget(0, nk_poz):
                            for row_cmb_poz in CQT.list_from_cmb_c(self.ui.tbl_pl_add_poz.cellWidget(0, nk_poz)):
                                if line_tbl['Номенклатура_ЕРП'] in row_cmb_poz:
                                    self.ui.tbl_pl_add_poz.cellWidget(0, nk_poz).setCurrentText(row_cmb_poz)
                                    select_poz(self, row_cmb_poz, 0, nk_poz)
                                    fl_poz = True
                                    break
                        if not fl_poz:
                            CQT.set_val_tbl_by_name(self.ui.tbl_pl_add_poz, 0, 'Номенклатура_ЕРП', '')
                        break

            CQT.add_btn(self.ui.tbl_pl_add_poz, 0, CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'ПКК'), '...',
                        conn_func_checked_row_col=add_file_pkk, self=self)
        if podr == 'пл_компл':
            list_status_tara = dict()
            for key in self.Data_plan.DICT_STATUS_TARA_NAME.keys():
                list_status_tara[key] = self.Data_plan.DICT_STATUS_TARA_NAME[key]['prim']
            nk_status_tara = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Статус_тара')
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_status_tara, list_status_tara, first_void=False,
                             conn_func=select_status_tara)
            try:
                self.ui.tbl_pl_add_poz.cellWidget(0, nk_status_tara).setCurrentText(
                    self.Data_plan.DICT_STATUS_TARA_NUM[int(self.ui.tbl_pl_add_poz.item(0, nk_status_tara).text())][
                        'name'])
            except:
                pass

    if self.edit_tabel_mode:
        edit_tabel(self)
    else:
        edit_etap(self)


def clck_cld(self):
    tbl = self.ui.tbl_pl_add_poz
    if not current_cell_is_data_type(tbl):
        return
    date = self.ui.calendarWidget.selectedDate()
    new_str = F.datetostr(QDate.toPyDate(date), "%Y-%m-%d")
    col = tbl.currentColumn()
    old_str = tbl.item(0, col).text()
    header = tbl.horizontalHeaderItem(col).text()
    if not check_permisions_on_fields(header, new_str, self):
        return
    if CQT.msgboxgYN(f'Установить для {tbl.horizontalHeaderItem(col).text()} c \n {old_str} \n на \n {new_str} ?'):
        tbl.item(0, col).setText(new_str)


def select_sort_c(self, text, row, col, *args):
    nk_sort_c = col
    val = 0
    for key in self.Data_plan.DICT_VID_PO_NAPR.keys():
        if self.Data_plan.DICT_VID_PO_NAPR[key]['Имя'] == text:
            val = key
            break
    self.ui.tbl_pl_add_poz.item(row, nk_sort_c).setText(str(val))
    print(f'Выбран {val}')


def select_tech(self, text, row, col, *args):
    self.ui.tbl_pl_add_poz.item(row, col).setText(text)
    print(f'Выбран {text}')


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
    print(f'Выбран {val}')


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
def generate_list_py(self, year: str = None, state = 'Формируется'):
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
    tbl.item(0, nf_poz_count).setText(count_poz.replace("шт", ''))
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

def select_py(self: mywindow, text, row, col, *args):


    tbl = self.ui.tbl_pl_add_poz
    nf_poz_name = CQT.num_col_by_name_c(tbl, 'Номенклатура_ЕРП')
    nf_poz_count = CQT.num_col_by_name_c(tbl, 'Количество')
    nf_poz_num = CQT.num_col_by_name_c(tbl, 'Позиция')
    nf_ref = CQT.num_col_by_name_c(tbl, 'Ref_Key_py')
    if nf_ref == None:
        nf_ref = CQT.num_col_by_name_c(tbl, 'Пномер_ЗП')

    tbl.removeCellWidget(0, nf_poz_name)
    tbl.item(0, nf_poz_name).setText('')
    tbl.item(0, nf_poz_count).setText('')
    if nf_poz_num:
        tbl.item(0, nf_poz_num).setText('')
    if nf_ref:
        tbl.item(0, nf_ref).setText('0')
    nk_py = col
    tbl.item(row, nk_py).setText('-')
    year, nom, prim, Ref_Key_py = text.split('|')
    if nom == '-':
        if prim == 'Все года':
            list_py = generate_list_py(self, 'all')
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_py, list_py, first_void=False,
                             conn_func=select_py)
            return

        if prim == 'Статус не закрыт':
            list_py = generate_list_py(self, state= None)
            CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_py, list_py, first_void=False,
                             conn_func=select_py)
            return
        else:
            return
    if self.place.doc_prefix not in nom:
        CQT.msgbox(f'Не выбран {self.place.doc_prefix}')
        return
    tbl.item(row, nk_py).setText(nom)
    tbl.item(row, nf_ref).setText(Ref_Key_py)
    tbl.cellWidget(row, nk_py).setToolTip(text)
    # fill_sort_c_top_combo(self, val)
    print(f'Выбран {nom}')
    m = ERP.OrdersComposit()
    list_poz_erp = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                                  wet_filtr=f"?$filter=year(Date) eq {year} and Number eq '{nom}'"
                                            f" &$select=Продукция/Номенклатура_Key,Продукция/Количество,Продукция/LineNumber")
    nomen_pos, have_null_etap = etaps_data_if_exists(m, nom, year)
    list_name_poz = []
    for zp in list_poz_erp:
        for poz in zp['Продукция']:
            name_poz = m.get_response(doc_name='Catalog_Номенклатура',
                                      wet_filtr=f"?$filter=Ref_Key eq guid'{poz['Номенклатура_Key']}'&$select=Description")
            if part_py := nomen_pos.get(poz['Номенклатура_Key']):
                line_number = part_py.get('НомерПартииЗапуска')
            else:
                line_number = int(have_null_etap) + int(poz['LineNumber'])
            if len(name_poz) and 'Description' in name_poz[0]:
                list_name_poz.append(
                    f"№{str(line_number)}.| {str(poz['Количество'])}шт.| {name_poz[0]['Description']}")

    CQT.add_combobox(self, tbl, 0, nf_poz_name, list_name_poz, first_void=True,
                     conn_func=select_poz)


@CQT.onerror
def load_tbl_add_new_poz(self: mywindow, *args):


    tbl_poz = self.ui.tbl_kal_pl
    list_heads = CSQ.custom_request_c(self.db_kplan, """SELECT 

plan.Направление_деятельности, 
"" as Статус,
пл_оуп.№Пл_Пр,
знпр.№проекта, 
знпр.№ERP, 
пл_оуп.Номенклатура_ЕРП,  
plan.Позиция, 
пл_оуп.Количество, 
пл_оуп.НомПартии_ЗП, 
пл_оуп.ПКК, 
"" AS Ref_Key_py, 
пл_оуп.Вес_кг,
пл_ко.Вес_ВО
FROM plan 
INNER JOIN 
пл_оуп ON пл_оуп.НомПл = plan.Пномер, 
пл_ко ON пл_ко.НомПл = plan.Пномер, 
пл_топ ON пл_топ.НомПл = plan.Пномер,
знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
 LIMIT 1""", one=True, hat_c=True)
    if list_heads == False:
        CQT.msgbox(f'Ошибка')
        return

    list_py = generate_list_py(self, F.now("%Y"))
    if list_py == None:
        show_fr(self)
        self.regim = ''
        return

    list_heads = list_heads[0]
    list_itog = ['' for _ in list_heads]
    list_itog = [list_heads, list_itog]
    list_itog[-1][F.num_col_by_name_in_hat_c(list_itog, 'Вес_кг')] = '*резерв/пмс на сумм кол-во'
    list_itog[-1][F.num_col_by_name_in_hat_c(list_itog, 'Вес_ВО')] = '*на сумм-ное кол-во'
    list_itog[-1][F.num_col_by_name_in_hat_c(list_itog, '№ERP')] = ''
    list_itog[-1][F.num_col_by_name_in_hat_c(list_itog, '№Пл_Пр')] = f' 00 Если по {self.place.doc_prefix}'
    list_itog[-1][F.num_col_by_name_in_hat_c(list_itog, 'НомПартии_ЗП')] = ''
    # ===========================
    cur_row = tbl_poz.currentRow()
    if cur_row >= 0 and CQT.get_key_modifiers(self) == ['shift']:
        nk_np = CQT.num_col_by_name_c(tbl_poz, 'знпр.№проекта')
        nk_py = CQT.num_col_by_name_c(tbl_poz, 'знпр.№ERP')
        nk_pp = CQT.num_col_by_name_c(tbl_poz, 'пл_оуп.№Пл_Пр')
        if nk_py == None:
            CQT.msgbox(f'Поле знпр.№ERP не включено')
            return
        if nk_np == None:
            CQT.msgbox(f'Поле знпр.№проекта не включено')
            return
        nk_pkk = CQT.num_col_by_name_c(tbl_poz, 'пл_оуп.ПКК')
        if nk_pp != None:
            list_itog[-1][F.num_col_by_name_in_hat_c(list_itog, '№Пл_Пр')] = tbl_poz.item(cur_row, nk_pp).text()
        if nk_np != None:
            list_itog[-1][F.num_col_by_name_in_hat_c(list_itog, '№проекта')] = tbl_poz.item(cur_row, nk_np).text()
        if nk_py != None:
            list_itog[-1][F.num_col_by_name_in_hat_c(list_itog, '№ERP')] = tbl_poz.item(cur_row, nk_py).text()

        if nk_pkk != None:
            list_itog[-1][F.num_col_by_name_in_hat_c(list_itog, 'ПКК')] = tbl_poz.item(cur_row, nk_pkk).text()
    # ===========================

    CQT.fill_wtabl(list_itog, self.ui.tbl_pl_add_poz)
    self.ui.tbl_pl_add_poz.setColumnWidth(F.num_col_by_name_in_hat_c(list_itog, 'Направление_деятельности'), 300)
    self.ui.tbl_pl_add_poz.setColumnWidth(F.num_col_by_name_in_hat_c(list_itog, 'Статус'), 100)
    self.ui.tbl_pl_add_poz.setColumnWidth(F.num_col_by_name_in_hat_c(list_itog, '№ERP'), 400)
    self.ui.tbl_pl_add_poz.setColumnWidth(F.num_col_by_name_in_hat_c(list_itog, '№Пл_Пр'), 100)
    self.ui.tbl_pl_add_poz.setColumnWidth(F.num_col_by_name_in_hat_c(list_itog, 'Позиция'), 60)
    self.ui.tbl_pl_add_poz.setColumnWidth(F.num_col_by_name_in_hat_c(list_itog, '№проекта'), 100)
    self.ui.tbl_pl_add_poz.setColumnWidth(F.num_col_by_name_in_hat_c(list_itog, 'Номенклатура_ЕРП'), 400)
    self.ui.tbl_pl_add_poz.setColumnHidden(F.num_col_by_name_in_hat_c(list_itog, 'Ref_Key_py'), True)
    list_napr_deyat = []
    for key in self.Data_plan.DICT_NAPR_DEYAT.keys():
        list_napr_deyat.append(self.Data_plan.DICT_NAPR_DEYAT[key]['Имя'])
    nk_napr_deyat = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Направление_деятельности')
    nk_py = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, '№ERP')
    nk_state = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Статус')
    CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_napr_deyat, list_napr_deyat, first_void=False,
                     conn_func=select_napr_deyat)
    CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_py, list_py, first_void=False,
                     conn_func=select_py)
    CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_state,
                     [_ for _ in list(self.Data_plan.DICT_STATUS_POZ_NAME.keys()) if _ in ('Резерв', 'Подготовка',"Долгосрочный")],
                     first_void=True,
                     conn_func=select_status)

    # fill_sort_c_top_combo(self,0)
    name_field = 'Пномер'
    oform_table_editeble(self, self.ui.tbl_pl_add_poz, name_field)


def fill_sort_c_top_combo(self: mywindow, napr_d=0):
    list_sort_c_top = []
    for key in self.Data_plan.DICT_VID_PO_NAPR:
        if self.Data_plan.DICT_VID_PO_NAPR[key]['Направл'] == napr_d:
            list_sort_c_top.append(self.Data_plan.DICT_VID_PO_NAPR[key]['Имя'])
    nk_sort_c_top = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'Вид')
    CQT.add_combobox(self, self.ui.tbl_pl_add_poz, 0, nk_sort_c_top, list_sort_c_top, first_void=False,
                     conn_func=select_sort_c)


def check_add_poz(self):
    def check_number(self, val, key, tbl):
        if ',' in val:
            CQT.msgbox(f'{key} разделитель дробной части должна быть точка, а не запятая')
            return False
        if F.is_numeric(val) == False:
            CQT.msgbox(f'{key} должно быть число')
            CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
            return False
        return True

    def check_db(self, val, key, tbl, dict):
        if F.valm(val) not in dict:
            CQT.msgbox(f'{key} должно быть по БД')
            CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
            return False
        return True

    def check_choose(self, val, key, tbl):
        if val == '1':
            CQT.msgbox(f'{key} должно быть выбрано')
            CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
            return False
        return True

    tbl = self.ui.tbl_pl_add_poz
    list_add = CQT.list_from_wtabl_c(tbl, rez_dict=True)[0]
    list_add = F.trim_collection(list_add) #05.06.2025
    for key in list_add.keys():
        val = list_add[key]
        if str(val).strip() == '':
            CQT.msgbox(f'{key} не может быть пусто')
            return False
        if key not in ('№ERP', '№Пл_Пр'):
            if str(val) == "" or '*' == str(val)[0]:
                CQT.msgbox(f'{key} не указан')
                return False
        if key in [ 'Направление_деятельности', 'Количество', 'Вес_ВО', 'Вес_кг']:
            if not check_number(self, val, key, tbl):
                return False
        if key == 'Статус':
            if val == '':
                CQT.msgbox(f'Не выбран статус позиции')
                return False
        if key == 'Направление_деятельности':
            if not check_db(self, val, key, tbl, self.Data_plan.DICT_NAPR_DEYAT):
                return False
            if not check_choose(self, val, key, tbl):
                return False
        if key == '№ERP':
            if val == '-':
                return True

            if f'{self.place.doc_prefix}00-0' not in val:
                CQT.msgbox(f'{key} Не корректная запись')
                CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                return False
            if not F.is_numeric(val.split(f'{self.place.doc_prefix}00-0')[-1]):
                CQT.msgbox(f'{key} Не корректная запись')
                CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                return False
            if val == f'{self.place.doc_prefix}00-000000':
                CQT.msgbox(f'{key} Не корректная запись')
                CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                return False

        if key == '№Пл_Пр':
            if val == '00':
                return True
            if not F.is_numeric(val):
                CQT.msgbox(f'{key} Не корректная запись')
                CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                return False


    rez = CSQ.custom_request_c(self.db_kplan, f"""SELECT plan.Позиция, пл_оуп.№проекта, пл_оуп.№ERP FROM plan 
          INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер 
         WHERE plan.Позиция = "{list_add['Позиция']}" AND 
          пл_оуп.№проекта = "{list_add['№проекта']}" AND 
           пл_оуп.№ERP = "{list_add['№ERP']}" """, one=True)
    if rez and len(rez) > 1:
        CQT.msgbox(
            f"Уже существует в базе {list_add['№проекта']} {list_add['№ERP']} {list_add['Позиция']}")
        return False

    return True


def check_edit_poz(self, old_list):
    def check_number(self, val, key, tbl):
        if ',' in val:
            CQT.msgbox(f'{key} разделитель дробной части должна быть точка, а не запятая')
            return False
        if F.is_numeric(val) == False:
            CQT.msgbox(f'{key} должно быть число')
            CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
            return False
        return True

    def check_db(self, val, key, tbl, dict):
        if F.valm(val) not in dict:
            CQT.msgbox(f'{key} должно быть по БД')
            CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
            return False
        return True

    def check_choose(self, val, key, tbl):
        if val == '1':
            CQT.msgbox(f'{key} должно быть выбрано')
            CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
            return False
        return True

    def check_date(self, val, key, tbl, dateformat='%Y-%m-%d'):
        if not F.is_date(val, dateformat):
            CQT.msgbox(f'{key} Не корректный формат даты')
            CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
            return False
        return True

    list_edit = CQT.list_from_wtabl_c(self.ui.tbl_pl_add_poz, rez_dict=True)[0]
    tbl = self.ui.tbl_pl_add_poz
    podr = self.ui.cmb_etap.currentText()

    if podr == 'plan':
        for key in list_edit.keys():
            val = list_edit[key]
            if str(val) == str(old_list[key]):
                continue
            if key in [ 'Направление_деятельности', 'Статус', 'МК', 'Нчас_вспом',
                       'Фчас_вспом', 'Фчас_доп_раб', 'Приоритет']:
                if not check_number(self, val, key, tbl):
                    return False
            if key in ['Направление_деятельности']:
                if not check_choose(self, val, key, tbl):
                    return False
            if key == 'Направление_деятельности':
                if not check_db(self, val, key, tbl, self.Data_plan.DICT_NAPR_DEYAT):
                    return False
            if key == 'Статус':
                if not check_db(self, val, key, tbl, self.Data_plan.DICT_STATUS_POZ):
                    return False
                val_str = self.Data_plan.DICT_STATUS_POZ[int(val)]['Имя']
                if val_str in ('К производству', 'Завершена', 'Изготовление'):
                    poz = CMS.Pozition(list_edit['Пномер'], self.db_kplan, self.bd_naryad, self.db_resxml,
                                       self.db_users, '')
                    poz.load_kpl_table('пл_оуп')
                    if poz.dict_tables['пл_оуп']['№ERP'] in ('', 0, '-'):
                        CQT.msgbox(f'{key} без ПлПр не может быть {val_str}')
                        return False

            if key == 'Статус_норм':
                if not check_db(self, val, key, tbl, self.Data_plan.DICT_STATUS_NORM):
                    return False

    if podr == 'пл_заг':
        for key in list_edit.keys():
            val = list_edit[key]
            if str(val) == str(old_list[key]):
                continue
            if key in ['Нчас_заг', 'Фчас_заг']:
                if not check_number(self, val, key, tbl):
                    return False
            if key in ['ПДата_нач_заг', 'ПДата_зав_заг', 'ФДата_нач_заг', 'ФДата_зав_заг',
                       'ФДата_раскладки', 'ФДата_резки', 'ФДата_г_ш']:
                if not check_date(self, val, key, tbl):
                    return False
    if podr == 'пл_ко':
        for key in list_edit.keys():
            val = list_edit[key]
            if str(val) == str(old_list[key]):
                continue
            if key in ['Вес_ВО', 'Вес_КД']:
                if not check_number(self, val, key, tbl):
                    return False
            if key in ['Пдата_КД', 'Фдата_КД']:
                if not check_date(self, val, key, tbl):
                    return False
            if key == 'Ссылка_КД':
                if 'docs://' not in val and 'Отдел технолога\В работе' not in val:
                    CQT.msgbox(f'{key} не корректная ссылка')
                    CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                    return False

    if podr == 'пл_компл':
        for key in list_edit.keys():
            val = list_edit[key]
            if str(val) == str(old_list[key]):
                continue

            if key in ['Дата_комплект_после_заг', 'Дата_компл_под_мех', 'Дата_комплект_под_сб',
                       'Дата_комплект_под_покр', 'Дата_комплект_под_упак',
                       'ПДата_комплект_упаковки', 'ФДата_комплект_упаковки', ]:
                if not check_date(self, val, key, tbl):
                    return False

    if podr == 'пл_мех':
        for key in list_edit.keys():
            val = list_edit[key]
            if str(val) == str(old_list[key]):
                continue
            if key in ['Нчас_мехобр', 'Фчас_мехобр']:
                if not check_number(self, val, key, tbl):
                    return False
            if key in ['Пдата_нач_мехобр', 'Пдата_зав_мехобр',
                       'Фдата_нач_мехобр', 'Фдата_зав_мехобр']:
                if not check_date(self, val, key, tbl):
                    return False
    if podr == 'пл_оуп':
        for key in list_edit.keys():
            val = list_edit[key]
            if str(val) == str(old_list[key]):
                continue
            if key in ['Количество']:
                if not check_number(self, val, key, tbl):
                    return False
            if key in ['Дата_заявки_на_произв', 'Дата_отгрузки_ПУ']:
                if not check_date(self, val, key, tbl):
                    return False
            if key in ['№проекта', 'ПКК', 'Номенклатура_ЕРП']:
                if val == '':
                    CQT.msgbox(f'{key} Не может быть пусто')
                    CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                    return False
            if key == '№ERP':
                if val == '-':
                    return True
                if f'{self.place.doc_prefix}00-0' not in val:
                    CQT.msgbox(f'{key} Не корректная запись')
                    CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                    return False
                if f'{self.place.doc_prefix}00-000000' in val:
                    CQT.msgbox(f'{key} Не корректная запись')
                    CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                    return False
                if not F.is_numeric(val.split(f'{self.place.doc_prefix}00-0')[-1]):
                    CQT.msgbox(f'{key} Не корректная запись')
                    CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                    return False
            if key == '№Пл_Пр':
                if val == '00':
                    return True
                if not F.is_numeric(val):
                    CQT.msgbox(f'{key} Не корректная запись')
                    CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                    return False

    if podr == 'пл_покр':
        for key in list_edit.keys():
            val = list_edit[key]
            if str(val) == str(old_list[key]):
                continue
            if key in ['Нчас_покр', 'Фчас_покр']:
                if not check_number(self, val, key, tbl):
                    return False
            if key in ['Пдата_нач_покр', 'Пдата_зав_покр', 'Фдата_нач_покр',
                       'Фдата_зав_покр']:
                if not check_date(self, val, key, tbl):
                    return False
    if podr == 'пл_сб':
        for key in list_edit.keys():
            val = list_edit[key]
            if str(val) == str(old_list[key]):
                continue
            if key in ['Нчас_сб', 'Фчас_сб']:
                if not check_number(self, val, key, tbl):
                    return False
            if key in ['Пдата_нач_сб', 'Пдата_зав_сб', 'Фдата_нач_сб', 'Фдата_зав_сб']:
                if not check_date(self, val, key, tbl):
                    return False
    if podr == 'пл_топ':
        for key in list_edit.keys():
            val = list_edit[key]
            if str(val) == str(old_list[key]):
                continue
            if key in ['Нчас_ТД', 'Нчас_сб', 'Фчас_сб', 'Вид',
                       'Уд_вес_ВО', 'Нчас_сб_ВО', 'Число_ДСЕ']:
                if not check_number(self, val, key, tbl):
                    return False
            if key in ['Пдата_ТД', 'Фдата_ТД', 'Дата_МК',
                       'Спецификация_дата']:
                if not check_date(self, val, key, tbl):
                    return False
            if key == 'пл_топ.Вид':
                if not check_db(self, val, key, tbl, self.Data_plan.DICT_VID_PO_NAPR):
                    return False
            if key == 'пл_топ.Спецификация_ЕРП':
                nk_npoz = CQT.num_col_by_name_c(self.ui.tbl_pl_add_poz, 'НомПл')
                npoz = int(self.ui.tbl_pl_add_poz.item(0, nk_npoz).text())
                oyp_nomenkl = CSQ.custom_request_c(self.db_kplan,
                                                   f"""SELECT Номенклатура_ЕРП FROM пл_оуп WHERE НомПл == {npoz};""",
                                                   one_column=True)
                if len(oyp_nomenkl) != 2:
                    return False
                if val != oyp_nomenkl[-1]:
                    CQT.msgbox(f'{key} Наименование должно совпадать с номенклатурой: {oyp_nomenkl[-1]}')
                    CQT.migat(self, tbl, 0, CQT.num_col_by_name_c(tbl, key), 1)
                    return False
    return True


def btn_pl_ok_add_poz_click(self):
    def add_py_from_erp(Ref_Key_py, nom_proj):
        m = CODAT.OrdersComposit()
        code, list_data = m.get_response(doc_name='Document_ЗаказНаПроизводство2_2',
                                   wet_filtr=f"?$filter= Ref_Key eq guid'{Ref_Key_py}'"
                                             f" &$select=Date,Number,Комментарий,Статус,ДатаПотребности,ДокументОснование,ДокументОснование_Type",with_cod=True)
        if code != 200:
            CQT.msgbox(f'Ошибка связи с ЕРП  Document_ЗаказНаПроизводство2_2  код {code}')
            return False
        if len(list_data) == 0:
            CQT.msgbox(f"Не найден в ЕРП ЗП с Ref_Key_py {Ref_Key_py}")
            return False


        if list_data[0]['ДокументОснование_Type'] not in (
                'StandardODATA.Document_ЗаказКлиента', 'StandardODATA.Document_ЗаказНаСборку', 'StandardODATA.Document_ЗаказНаВнутреннееПотребление'):
            CQT.msgbox(
                f"Основание для {self.place.doc_prefix}:\n{list_data[0]['ДокументОснование_Type']}.\n Нужен Заказа клиента/Заказ на сборку/ЗНВП")
            return
        client_order = list_data[0]['ДокументОснование']

        sb_order = ''
        znvp_order = ''

        if list_data[0]['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказНаСборку':
            sb_order = list_data[0]['ДокументОснование']
            code, data_sb = m.get_response(doc_name=f"Document_ЗаказНаСборку(guid'{sb_order}')",
                                   wet_filtr=f"?$select=ДокументОснование_Key,Номенклатура_Key",with_cod=True)
            if code != 200:
                CQT.msgbox(f'Ошибка связи с ЕРП Document_ЗаказНаСборку код {code}')
                return False
            client_order = data_sb['ДокументОснование_Key']
        if list_data[0]['ДокументОснование_Type'] == 'StandardODATA.Document_ЗаказНаВнутреннееПотребление':
            znvp_order = list_data[0]['ДокументОснование']
            client_order = ''

        year = F.datetostr(F.strtodate(list_data[0]['Date'], "%Y-%m-%dT%H:%M:%S"), "%Y")
        date = F.datetostr(F.strtodate(list_data[0]['Date'], "%Y-%m-%dT%H:%M:%S"), "%Y-%m-%d")
        date_otgr = F.datetostr(F.strtodate(list_data[0]['ДатаПотребности'], "%Y-%m-%dT%H:%M:%S"), "%Y-%m-%d")
        list_to_add = [int(year), date, list_data[0]['Number'], nom_proj, list_data[0]['Статус'],
                       '', date_otgr, '', 1, Ref_Key_py,list_data[0]['Комментарий'],sb_order,client_order,znvp_order]

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
                        znvp_order_Key) VALUES ({CSQ.questions_for_mask(list_to_add)})""", list_of_lists_c=[list_to_add])

    def check_edit_tabel(self):
        month = self.ui.cmb_etap.currentText()
        if month == '':
            return
        list_month = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM {month}""")
        list_new = CQT.list_from_wtabl_c(self.ui.tbl_pl_add_poz, '', True)
        if len(list_month) != len(list_new):
            CQT.msgbox(f'Что то пошло не так')
            return
        if len(list_month[0]) != len(list_new[0]):
            CQT.msgbox(f'Что то пошло не так')
            return
        list_changes = []
        list_sql = []
        for i in range(3, len(list_new)):
            for j in range(3, len(list_new[0])):
                if list_month[i][j] != list_new[i][j]:
                    list_changes.append(
                        f'Для {list_month[i][1]} от {list_month[0][j]} было:{list_month[i][j]}, стало:{list_new[i][j]}')
                    list_sql.append(
                        f"""UPDATE {month} SET {list_month[0][j]} = {list_new[i][j]} WHERE Подразделение = '{list_month[i][1]}'""")
        if list_changes == []:
            CQT.msgbox(f'Изменений не найдено')
            return False

        msg_str = 'Внести изменения?\n\n' + "\n".join(list_changes)
        if CQT.msgboxgYN(msg=msg_str):
            return list_sql
        return False

    def apply_edit_tabel(self, list_sql):
        for custom_request_c in list_sql:
            CSQ.custom_request_c(self.db_kplan, custom_request_c)
        CQT.msgbox(f'Успешно')
        VPL.get_max_mosh_from_db(self)

    @CQT.onerror
    def fill_old_fields_from_znpr(self: mywindow, num_kpl):
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

    @CQT.onerror
    def add_new_poz(self: mywindow):
        if not check_add_poz(self):
            return
        show_fr(self)

        list_add = CQT.list_from_wtabl_c(self.ui.tbl_pl_add_poz, rez_dict=True)[0]
        s_num_py = 0
        if list_add['Ref_Key_py'] not in ('','0'):
            list_py_from_mes = CSQ.custom_request_c(self.db_kplan, f"""SELECT Ref_Key_py FROM знпр WHERE 
             Ref_Key_py = "{list_add['Ref_Key_py']}";""", rez_dict=True)
            if len(list_py_from_mes) == 0:
                add_py_from_erp(list_add['Ref_Key_py'], list_add['№проекта'])

            list_py_from_mes = CSQ.custom_request_c(self.db_kplan,
                                                    f"""SELECT s_num FROM знпр WHERE Ref_Key_py 
                                                         = "{list_add['Ref_Key_py']}";""",
                                                    rez_dict=True)
            if len(list_py_from_mes) == 0:
                CQT.msgbox(f"Не найден в МЕС ЗП с Ref_Key_py {list_add['Ref_Key_py']}")
                return False
            s_num_py = list_py_from_mes[0]['s_num']

        CSQ.custom_request_c(self.db_kplan, f"""INSERT INTO plan(Дата_внесения,
                    Позиция,
                    Направление_деятельности,
                    Статус,
                    poki
                    )
                    VALUES (?,?,?,?,?);""", list_of_lists_c=[[F.now("%Y-%m-%d"), list_add['Позиция'],
                                                            list_add['Направление_деятельности'],
                                                            int(list_add['Статус']),self.place.poki]])
        pnom = CSQ.last_row_db_c(self.db_kplan, 'plan', 'Пномер', ['Пномер'])[0]

        list_podr = [_ for _ in CSQ.get_list_of_tables_c(self.db_kplan) if 'пл_' in _]
        for podr in list_podr:
            CSQ.custom_request_c(self.db_kplan, f"""INSERT INTO {podr}(
                        НомПл
                        )
                        VALUES (?);""", list_of_lists_c=[[pnom]])

        vals = [
            list_add['№Пл_Пр'],
            list_add['№проекта'],
            s_num_py,
            list_add['Количество'],
            list_add['ПКК'],
            list_add['Номенклатура_ЕРП'],
            list_add['Вес_кг'].replace(',', '.'),
            list_add['НомПартии_ЗП'], ]

        CSQ.custom_request_c(self.db_kplan, f"""UPDATE пл_оуп SET(

               №Пл_Пр, 
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
            fill_old_fields_from_znpr(self, pnom)

        vals = [list_add['Вес_ВО'].replace(',', '.'),
                ]

        CSQ.custom_request_c(self.db_kplan, f"""UPDATE пл_ко SET(
                       Вес_ВО
                       ) =
                        (?) WHERE НомПл == {pnom};""", list_of_lists_c=vals)

        # vals = [list_add['Вид'],
        #        ]

        # CSQ.custom_request_c(self.db_kplan, f"""UPDATE пл_топ SET(
        #               Вид
        #               ) =
        #                (?) WHERE НомПл == {pnom};""", list_of_lists_c=vals)
        obj_msg = CMS.Msg_b24(self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, pnom)
        obj_msg.send_msg('add_new_poz')
        # msg = f"{F.user_full_namre()} Добавил в план {list_add['№проекта']} {list_add['№ERP']} " \
        #      f"(Пл_Пр №{list_add['№Пл_Пр']}) поз. {list_add['Позиция']}:\n " \
        #      f"Необходимо указать вид {list_add['Номенклатура_ЕРП']}\n" \
        #      f"и загрузить xml-аналог либо сделать МК по КД"
        # self.send_info_mk_b24(msg,'chat48346')
        CQT.msgbox(f'Успешно')
        return True

    @CQT.onerror
    def edit_poz(self: mywindow):
        @CQT.onerror
        def fill_changes_into_user_tbl(self: mywindow, podr, list_fields, list_vals, pnom, name_field):
            tbl = self.ui.tbl_kal_pl
            row = -1
            nk_nom = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
            for i in range(tbl.rowCount()):
                if tbl.item(i, nk_nom).text() == str(pnom):
                    row = i
                    break
            if row == -1:
                return False
            for j, field in enumerate(list_fields):
                nk_field = CQT.num_col_by_name_c(tbl, f'{podr}.{field}')
                if nk_field != None:
                    if tbl.item(row, nk_field).text() != str(list_vals[j]):
                        tbl.item(row, nk_field).setText(str(list_vals[j]))
            pass

        tbl = self.ui.tbl_pl_add_poz
        podr = self.ui.cmb_etap.currentText()
        if podr == '':
            return
        if podr == 'plan':
            nk_nom = CQT.num_col_by_name_c(tbl, 'Пномер')
            name_field = 'Пномер'
        else:
            nk_nom = CQT.num_col_by_name_c(tbl, 'НомПл')
            name_field = 'НомПл'
        pnom = int(tbl.item(0, nk_nom).text())
        old_list = get_line_to_edit_podr(self, pnom)
        old_list = F.list_to_dict(old_list)[0]
        if not check_edit_poz(self, old_list):
            return

        new_list = CQT.list_from_wtabl_c(tbl, hat_c=True, rez_dict=True)[0]
        if podr == 'пл_оуп':
            if not F.is_numeric(new_list['Пномер_ЗП']):
                list_py_from_mes = CSQ.custom_request_c(self.db_kplan,
                                                        f"""SELECT Ref_Key_py FROM знпр WHERE Ref_Key_py = "{new_list['Пномер_ЗП']}";""",
                                                        rez_dict=True)
                if len(list_py_from_mes) == 0:
                    add_py_from_erp(new_list['Пномер_ЗП'], new_list['№проекта'])

                list_py_from_mes = CSQ.custom_request_c(self.db_kplan,
                                                        f"""SELECT s_num FROM знпр WHERE Ref_Key_py = "{new_list['Пномер_ЗП']}";""",
                                                        rez_dict=True)
                if len(list_py_from_mes) == 0:
                    CQT.msgbox(f"Не найден в МЕС ЗП с Ref_Key_py {new_list['Пномер_ЗП']}")
                    return False
                new_list['Пномер_ЗП'] = list_py_from_mes[0]['s_num']
        old_list.pop(name_field)
        new_list.pop(name_field)
        delta_dict = dict()

        obj_jur = CMS.Logs(self.bd_files)
        for key in new_list.keys():
            if str(new_list[key]) != str(old_list[key]):
                delta_dict[key] = new_list[key]
                obj_jur.add_note(pnom, key, new_list[key], 'tbl_kal_pl')

        list_fields = list(delta_dict.keys())
        list_vals = list(delta_dict.values())
        if len(delta_dict) > 0:
            if list_fields == []:
                return
            CSQ.custom_request_c(self.db_kplan, f"""UPDATE {podr} SET({','.join(list_fields)}) =
             ({'?,'.join(['' for _ in list_fields]) + '?'}) WHERE {name_field} = {pnom};""", list_of_lists_c=list_vals)

            fill_changes_into_user_tbl(self, podr, list_fields, list_vals, pnom, name_field)

            if podr == 'plan' and 'Фдата_получения_КД' in list_fields:
                if old_list['Фдата_получения_КД'] != new_list['Фдата_получения_КД']:
                    obj_msg = CMS.Msg_b24(self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, pnom)
                    obj_msg.send_msg('obtained_kd')
            if podr == 'пл_топ' and 'Вид' in list_fields:
                if old_list['Вид'] != new_list['Вид']:
                    # poz = CSQ.custom_request_c(self.db_kplan, f"""SELECT пл_оуп.№проекта, пл_оуп.№ERP, plan.Позиция FROM пл_оуп INNER JOIN plan
                    #        ON пл_оуп.НомПл = plan.Пномер WHERE НомПл = {pnom}""", rez_dict=True)
                    # msg = f'{F.user_full_namre()} указал "вид" на {str(poz)}\n Необходимо проставить предварительные нормы'
                    # self.send_info_mk_b24(msg, 'chat48346')
                    obj_msg = CMS.Msg_b24(self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, pnom)
                    obj_msg.send_msg('recalc_time_technolog')

            if podr == 'пл_топ' and 'Спецификация_код_ЕРП' in list_fields:
                if old_list['Спецификация_код_ЕРП'] != new_list['Спецификация_код_ЕРП']:
                    obj_msg = CMS.Msg_b24(self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, pnom)
                    obj_msg.send_msg('obtained_kod_res')

            if podr == 'пл_оуп':
                if str(new_list['Пномер_ЗП']) != '0':
                    fill_old_fields_from_znpr(self, pnom)
                if '№ERP' in list_fields:
                    if old_list['№ERP'] != new_list['№ERP']:
                        py = new_list['№ERP']
                        poz = CSQ.custom_request_c(self.db_kplan, f"""SELECT пл_оуп.№проекта, пл_оуп.№ERP, пл_оуп.№Пл_Пр, plan.Позиция FROM пл_оуп INNER JOIN plan 
                                            ON пл_оуп.НомПл = plan.Пномер WHERE НомПл = {pnom}""", rez_dict=True)
                        CSQ.custom_request_c(self.bd_naryad,
                                             f"""UPDATE mk SET Номер_заказа = "{py}" WHERE НомКплан = {pnom};""")

                        try:
                            msg = f"{F.user_full_namre()} на {str(poz)}\n УСТАНОВИЛ {py} необходимо открыть МК и сделать раскладку"
                            CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
                            # self.send_info_mk_b24(msg, 'chat41228')
                        except:
                            print('Ошибка отправки в Б24')
        show_fr(self)
        self.regim = ''
        CQT.msgbox(f'Успешно')
        return True

    def save_cnf(self):
        if 'shift' in CQT.get_key_modifiers(self):
            path = os.path.join(CMS.tmp_dir(), 'fields.pickle')
            F.delete_file_c(path)
            return True
        spis = CQT.list_from_wtabl_c(self.ui.tbl_pl_add_poz, hat_c=True)
        rez_dict = dict()
        for j in range(0, len(spis[-1])):
            spis[1][j] = int(spis[1][j])
            hid = 1
            if spis[1][j] != 1:
                if spis[0][j] in LIST_FREEZE_FIELDS:
                    hid = 2
                else:
                    hid = 0
            rez_dict[spis[0][j]] = {'hidden': hid, 'order': j + 1}
        path = os.path.join(CMS.tmp_dir(), 'fields.pickle')
        F.save_file_pickle(path, rez_dict)
        return True

    if self.edit_tabel_mode:
        list_sql = check_edit_tabel(self)
        if list_sql:
            apply_edit_tabel(self, list_sql)
    else:
        rez = None
        if self.regim == 'add':
            rez = add_new_poz(self)
            if rez != None:
                GPL.update_local_graf(self, True)
            self.regim = ''
            load_table_db(self)
            show_fr(self)
        if self.regim == 'edit':
            rez = edit_poz(self)
            if rez != None:
                GPL.update_local_graf(self, True)
        if self.regim == 'cnf':
            rez = save_cnf(self)
            self.regim = ''
            list_conf = load_list_fields(self, False)
            self.list_conf_fields_kpl = list_conf
            load_table_db(self)
            show_fr(self)
        if rez == None:
            return


def get_line_to_edit_podr(self, pnom):
    podr = self.ui.cmb_etap.currentText()
    if podr == "":
        CQT.clear_tbl(self.ui.tbl_pl_add_poz)
        return
    name_field = podr + '.НомПл'
    if podr == "plan":
        name_field = 'plan.Пномер'

    list_itog = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM 
                    {podr} WHERE {name_field} == {pnom}
                     """, one=True, hat_c=True)
    return list_itog


def show_fr(self, fr='', graf=0):
    self.ui.btn_kal_pl_left.setHidden(True)
    self.ui.btn_kal_pl_right.setHidden(True)
    if graf == 0:  # объемный выключаем
        self.ui.fr_pull_poz.setHidden(True)
        self.ui.fr_pl_graf.setHidden(True)
        self.ui.fr_pl_tables.setHidden(False)
        if fr == '':
            self.ui.fr_pl_cal.setHidden(True)
            self.ui.fr_pl_add_poz.setHidden(True)
            self.ui.fr_pl_etap.setHidden(True)
        if fr == 'tbl_add':
            self.ui.fr_pl_cal.setHidden(False)
            self.ui.fr_pl_add_poz.setHidden(False)
            self.ui.fr_pl_etap.setHidden(True)
        if fr == 'tbl_edit':
            self.ui.fr_pl_cal.setHidden(False)
            self.ui.fr_pl_add_poz.setHidden(False)
            self.ui.fr_pl_etap.setHidden(False)
    if graf == 1:  # объемный включаем
        self.ui.fr_pull_poz.setHidden(True)
        self.ui.fr_pl_graf.setHidden(False)
        self.ui.fr_pl_tables.setHidden(True)
        self.ui.fr_pl_gaf.setHidden(False)


def check_db(self):
    if 'SRV' in self.db_kplan:
        return True
    else:
        return F.existence_file_c(self.db_kplan)


def current_cell_is_data_type(tbl):
    try:
        column = tbl.currentColumn()
        if 'дата' in tbl.horizontalHeaderItem(column).text().lower():
            return True
        return False
    except:
        return False


def dbl_clk_tbl_add_poz(self):
    if current_cell_is_data_type(self.ui.tbl_pl_add_poz):
        CQT.blink_obj_c(self, 2, self.ui.calendarWidget, 'Выбрать дату в календаре')


def select_field_from_kgui(self):
    self.current_kpl_table = 'tbl_preview'
    tbl:QtWidgets.QTableWidget = self.ui.tbl_preview
    r = tbl.currentRow()
    c = tbl.currentColumn()
    if self.dict_tbls_kpl_info['tbl_preview'][r + 1][c] == '':
        return
    dict_obj = copy.deepcopy(self.dict_tbls_kpl_info['tbl_preview'][r + 1][c])[0]
    try:
        if 'shift' in CQT.get_key_modifiers(self):
            name_field = dict_obj['Имя_нз'][1]
        else:
            name_field = dict_obj['Имя_нз'][0]
    except:
        return
    nk = CQT.num_col_by_name_c(self.ui.tbl_kal_pl, name_field)
    self.ui.tbl_kal_pl.setCurrentCell(self.ui.tbl_kal_pl.currentRow(), nk)
    try:
        if 'фдата_' in dict_obj['Этап']:
            date_str = '\n'.join(tbl.horizontalHeaderItem(c).text().split('\n')[:3])
            date = F.strtodate(date_str, "%d\n%m\n%y")
            row_name = tbl.verticalHeaderItem(r).text()
            poz, dict_fact_jur, dict_summ_time,dict_jur_data = recalc_fact_by_date(self, self.pnom_kplan_select, date_calc=date)
            if row_name in dict_jur_data:
                CQT.msgboxg_get_table_ok_inf(self,'Расшифровка дня', dict_jur_data[row_name],load_summ=True)
    except:
        pass


def create_db(self):
    frase_tmp = """
"""
    CSQ.create_db_sql_c(self.db_kplan, frase_tmp)


@CQT.onerror
def load_db(self: mywindow, pnom=False, only_hat=False):
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

    limit = ''
    if only_hat:
        limit = ' Limit 1'

    # check_tabels(self)
    dict_inner = {
        'plan.Направление_деятельности as "plan.Направление_деятельности"': 'napravl_deyat.Имя as "plan.Направление_деятельности"',
        'plan.Статус as "plan.Статус"': 'status_poz.Имя as "plan.Статус"',
        'знпр.Этапы_ЕРП as "знпр.Этапы_ЕРП"': 'status_etapi_erp.Имя as "знпр.Этапы_ЕРП"',
        'пл_топ.Вид as "пл_топ.Вид"': 'виды_по_напр.Имя as "пл_топ.Вид"',
        'plan.local_graf as "plan.local_graf"': '"" as "plan.local_graf"',
        'пл_компл.Статус_тара as "пл_компл.Статус_тара"': 'status_tara.name as "пл_компл.Статус_тара"',
        'plan.Статус_норм as "plan.Статус_норм"': 'status_norm.Имя as "plan.Статус_норм"',
        'mk.Дата_завершения as "mk.Дата_завершения"': 'mk.Дата_завершения as "plan.Дата_зав_МК"',
        'mk.Вес as "mk.Вес"': 'mk.Вес as "plan.Вес"',
        'mk.xml as "mk.xml"': 'mk.xml as "plan.Вес_xml"'
    }
    if check_db(self) == False:
        CQT.msgbox(f'db_kplan не найдена')

    rez_list_tabels = ['napravlenie.name as "Направление"', 'napravl_deyat.Псевдоним as "Псевдоним"']
    poki = f'plan.poki == {self.place.poki}'


    if not self.ui.chk_kpl_zaversch.isChecked():
        postfix = f'WHERE {poki} and status_poz.Имя NOT IN  ("Завершена","Приостановлена","На удаление")'
    else:
        postfix = f'WHERE {poki}'
    if pnom:
        postfix = f'WHERE {poki} and plan.Пномер == {int(pnom)}'
        if 'list_conf_fields_kpl_all' in self.__dict__:
            list_conf = self.list_conf_fields_kpl_all
        else:
            list_conf = load_list_fields(self, True)
            self.list_conf_fields_kpl_all = list_conf

        for i in range(len(list_conf[0])):
            rez_list_tabels.append(f'{list_conf[0][i]} as "{list_conf[0][i]}"')
    else:
        if 'list_conf_fields_kpl' in self.__dict__:
            list_conf = self.list_conf_fields_kpl
        else:
            list_conf = load_list_fields(self, only_hat)
            self.list_conf_fields_kpl = list_conf
        for i in range(len(list_conf[0])):
            if list_conf[1][i]:
                rez_list_tabels.append(f'{list_conf[0][i]} as "{list_conf[0][i]}"')
    str_field = ', \n'.join(rez_list_tabels)
    for key in dict_inner.keys():
        str_field = str_field.replace(key, dict_inner[key])

    list = CSQ.custom_request_c(self.db_kplan, f"""SELECT
    {str_field}
    FROM plan
    LEFT JOIN 
    пл_оуп ON пл_оуп.НомПл = plan.Пномер,
    пл_ко ON пл_ко.НомПл = plan.Пномер,
    пл_топ ON пл_топ.НомПл = plan.Пномер,
    пл_заг ON пл_заг.НомПл = plan.Пномер,
    пл_компл ON пл_компл.НомПл = plan.Пномер,
    пл_мех ON пл_мех.НомПл = plan.Пномер,
    пл_сб ON пл_сб.НомПл = plan.Пномер,
    пл_покр ON пл_покр.НомПл = plan.Пномер,
    пл_отк ON пл_отк.НомПл = plan.Пномер,
    пл_осил ON пл_осил.НомПл = plan.Пномер,
    
    пл_рскр ON пл_рскр.НомПл = plan.Пномер,
    пл_оснтк ON пл_оснтк.НомПл = plan.Пномер,
    пл_швк ON пл_швк.НомПл = plan.Пномер,
    пл_сбтк ON пл_сбтк.НомПл = plan.Пномер,
    пл_сбмл ON пл_сбмл.НомПл = plan.Пномер,
    пл_нбвк ON пл_нбвк.НомПл = plan.Пномер,
    пл_свг ON пл_свг.НомПл = plan.Пномер,
    пл_сббси ON пл_сббси.НомПл = plan.Пномер,
    пл_упквк ON пл_упквк.НомПл = plan.Пномер,
    пл_кмпл ON пл_кмпл.НомПл = plan.Пномер,
    пл_откк ON пл_откк.НомПл = plan.Пномер,

    napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
    status_poz ON status_poz.Пномер = plan.Статус,
    status_etapi_erp ON status_etapi_erp.Пномер = знпр.Этапы_ЕРП,
    виды_по_напр ON виды_по_напр.Пномер = пл_топ.Вид,
    napravlenie ON napravlenie.Пномер = napravl_deyat.Направление,
    status_norm ON status_norm.Код = plan.Статус_норм,
    status_tara ON status_tara.s_num = пл_компл.Статус_тара,
    знпр ON знпр.s_num = пл_оуп.Пномер_ЗП,
    mk ON mk.Пномер = plan.МК 
    {postfix} {limit};
    """,attach_dbs=(self.bd_naryad))

    return list, list_conf


@CQT.onerror
def tbl_kal_pl_cellChanged(self: mywindow, *args):
    def check_date(text):
        if F.is_date(text, "%Y-%m-%d"):
            return text
        if F.is_date(text, "%y-%m-%d"):
            return F.datetostr(F.strtodate(text, "%y-%m-%d"), "%Y-%m-%d")
        if F.is_date(text, "%d.%m.%Y"):
            return F.datetostr(F.strtodate(text, "%d.%m.%Y"), "%Y-%m-%d")
        if F.is_date(text, "%d.%m.%y"):
            return F.datetostr(F.strtodate(text, "%d.%m.%y"), "%Y-%m-%d")
        if F.is_date(text, "%d.%m.%y"):
            return F.datetostr(F.strtodate(text, "%d.%m.%y"), "%Y-%m-%d")
        if text == '':
            return text
        return False

    def check_str(text):
        new_val = text.replace('\t', '').replace('\n', '')
        return new_val

    def check_digit(text):
        if not F.is_numeric(text):
            return False
        return str(F.valm(text))

    tbl = self.ui.tbl_kal_pl
    row = tbl.currentRow()
    column = tbl.currentColumn()
    if '.' not in tbl.horizontalHeaderItem(column).text():
        return
    tbl.blockSignals(True)
    name_tbl, name_field = tbl.horizontalHeaderItem(column).text().split('.')
    full_name_field = tbl.horizontalHeaderItem(column).text()
    row_dict = CQT.get_dict_line_form_tbl(tbl, row)
    if name_tbl == 'знпр':
        s_num = CSQ.custom_request_c(self.db_kplan, f"""SELECT  s_num 
     FROM знпр WHERE s_num IN (SELECT Пномер_ЗП FROM пл_оуп WHERE НомПл = {int(row_dict['plan.Пномер'])})""",
                                     rez_dict=True)[0]['s_num']
        old_val = CSQ.custom_request_c(self.db_kplan, f"""SELECT {name_field} FROM {name_tbl} 
                WHERE s_num == {s_num};""", hat_c=False, one_column=True, one=True)[0]
        name_s_num = 's_num'
    else:
        name_s_num = 'НомПл'
        if name_tbl == 'plan':
            name_s_num = 'Пномер'
        try:
            s_num = int(row_dict['plan.Пномер'])
            old_val = CSQ.custom_request_c(self.db_kplan, f"""SELECT {name_field} FROM {name_tbl} 
            WHERE {name_s_num} == {s_num};""", hat_c=False, one_column=True, one=True)[0]
        except:
            CQT.msgbox(f'Ошибка загрузки данных')
            tbl.blockSignals(False)
            return

    fl_update_val = False
    fl_check_field = True
    msg_err = ''
    if not full_name_field in self.Data_plan.DICT_INFO_FIELDS_KPL:
        msg_err = f'Не найдено правило обслуживания поля'
        fl_check_field = False

    if self.Data_plan.DICT_INFO_FIELDS_KPL[full_name_field]['hand_editable'] != 1:
        msg_err = f'Корректировка поля запрещена'
        fl_check_field = False

    fl_access = CMS.access_kpl_tbl(self.Data_plan.DICT_INFO_FIELDS_KPL, full_name_field)

    if fl_access == False:
        msg_err = f'Нет доступа'
        fl_check_field = False

    new_val = tbl.item(row, column).text().strip()
    if fl_check_field:
        if self.Data_plan.DICT_INFO_FIELDS_KPL[full_name_field]['edit_rules_str_digit_date'] == 'date':
            msg_err = f'Не корректный формат даты'
            new_val = check_date(new_val)
            if not (isinstance(new_val, bool) and new_val == False):
                fl_update_val = True

        elif self.Data_plan.DICT_INFO_FIELDS_KPL[full_name_field]['edit_rules_str_digit_date'] == 'str':
            msg_err = f'Не корректный формат строки'
            new_val = check_str(new_val)
            if not (isinstance(new_val, bool) and new_val == False):
                fl_update_val = True
        elif self.Data_plan.DICT_INFO_FIELDS_KPL[full_name_field]['edit_rules_str_digit_date'] == 'digit':
            msg_err = f'Не корректный формат число'
            new_val = check_digit(new_val)
            if not (isinstance(new_val, bool) and new_val == False):
                fl_update_val = True

    if fl_check_field and fl_update_val:

        CSQ.custom_request_c(self.db_kplan, f"""UPDATE {name_tbl} SET ({name_field}) = (?) WHERE {name_s_num} 
          == {s_num};""", list_of_lists_c=[new_val])
        if name_tbl == "знпр":
            update_tabels(self)
        else:
            tbl.item(row, column).setText(new_val)

        obj_jur = CMS.Logs(self.bd_files)
        obj_jur.add_note(s_num, name_field, new_val, 'tbl_kal_pl')
        print()
    else:
        tbl.item(row, column).setText(str(old_val))
        CQT.msgbox(msg_err)
    tbl.blockSignals(False)
    return


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


@CQT.progress_decorator
def load_table_db(self, hook_prog_bar=None):
    def oforml_table(self):
        tbl = self.ui.tbl_kal_pl
        nk_s_num = CQT.num_col_by_name_c(tbl, 'plan.Пномер')
        nk_pseudo = CQT.num_col_by_name_c(tbl, 'Псевдоним')
        nk_napr = CQT.num_col_by_name_c(tbl, 'plan.Направление_деятельности')
        nk_nom_pr = CQT.num_col_by_name_c(tbl, 'пл_оуп.№проекта')
        nk_local_graf = CQT.num_col_by_name_c(tbl, 'plan.local_graf')
        nk_pkk = CQT.num_col_by_name_c(tbl, 'пл_оуп.ПКК')
        nk_state_norm = CQT.num_col_by_name_c(tbl, 'plan.Статус_норм')
        nk_state = CQT.num_col_by_name_c(tbl, 'plan.Статус')
        nk_mk = CQT.num_col_by_name_c(tbl, 'plan.МК')
        self.ui.tbl_kal_pl.setColumnHidden(nk_local_graf, True)
        if nk_nom_pr != None:
            for i in range(tbl.rowCount()):
                r, g, b = 240, 240, 240
                try:
                    r, g, b = self.Data_plan.DICT_NAPR_DEYAT_NAME[tbl.item(i, nk_napr).text()]['Цвет'].split(';')
                except:
                    pass
                CQT.set_color_wtab_c(tbl, i, nk_pseudo, r, g, b)
                CQT.font_cell_size_format(tbl, i, nk_nom_pr, underline=True)

        if nk_pkk != None:
            for i in range(tbl.rowCount()):
                if not tbl.item(i, nk_pkk) == None:
                    pkk_val = tbl.item(i, nk_pkk).text()
                    if F.is_numeric(pkk_val) and isinstance(F.valm(pkk_val), int):
                        CQT.add_btn(tbl, i, nk_pkk, '(*)', conn_func_checked_row_col=open_pkk, self=self)
        if nk_state_norm != None:
            for i in range(tbl.rowCount()):
                if tbl.item(i, nk_state_norm):
                    state = tbl.item(i, nk_state_norm).text()
                    if state in self.Data_plan.DICT_STATUS_NORM_NAME:
                        r, g, b = self.Data_plan.DICT_STATUS_NORM_NAME[state]['color'].split(';')
                        CQT.set_color_wtab_c(tbl, i, nk_state_norm, r, g, b)
        if nk_state != None:
            for i in range(tbl.rowCount()):
                if tbl.item(i, nk_state):
                    state = tbl.item(i, nk_state).text()
                    if state in self.Data_plan.DICT_STATUS_POZ_NAME:
                        r, g, b = self.Data_plan.DICT_STATUS_POZ_NAME[state]['color'].split(';')
                        CQT.set_color_wtab_c(tbl, i, nk_state, r, g, b)

        if nk_mk != None:
            for i in range(tbl.rowCount()):
                if tbl.item(i, nk_mk):
                    mk = tbl.item(i, nk_mk).text()
                    if mk == '0':
                        CQT.set_color_wtab_c(tbl, i, nk_mk, 206, 128, 128)

        if self.ui.chk_paint_dates.isChecked():
            dict_nkpl_for_paint = dict()
            dict_pairs_fields = {
                name + '.' + _['Имя_начала_этапа']: name + '.' + _['Имя_начала_этапа'].replace('Пдата',
                                                                                               'Фдата').replace(
                    'ПДата', 'ФДата') for name, _ in
                self.Data_plan.DICT_PODR.items() if _['Имя_начала_этапа'] != ''}
            list_dicts_tbl = CQT.list_from_wtabl_c(tbl, rez_dict=True)
            if list_dicts_tbl:
                for i, item in enumerate(list_dicts_tbl):
                    for j, field_val in list(enumerate(item.items())):
                        if tbl.isColumnHidden(j):
                            continue
                        field, val = field_val
                        if field in dict_pairs_fields:
                            if F.is_date(val, "%Y-%m-%d") and F.strtodate(val, "%Y-%m-%d") <= F.now(''):
                                if dict_pairs_fields[field] in item:
                                    if item[dict_pairs_fields[field]] == '':
                                        if i not in dict_nkpl_for_paint:
                                            dict_nkpl_for_paint[i] = []
                                        dict_nkpl_for_paint[i].append(j)
            clr_bad = CMS.Color_tbl(10)
            for i_row, list_fields in dict_nkpl_for_paint.items():
                if nk_nom_pr != None:
                    CQT.set_color_wtab_c(tbl, i_row, nk_nom_pr, clr_bad.r, clr_bad.g, clr_bad.b)
                CQT.set_color_wtab_c(tbl, i_row, nk_s_num, clr_bad.r, clr_bad.g, clr_bad.b)
                for field in list_fields:
                    CQT.set_color_wtab_c(tbl, i_row, field, clr_bad.r, clr_bad.g, clr_bad.b)


    hook_prog_bar.open()
    hook_prog_bar.set(0)
    hook_prog_bar.text("load_db")
    list_from_db, list_conf = load_db(self)
    if list_from_db == False:
        CQT.msgbox(f'Ошибка загрузки таблиц')
        return
    # if len(list) == 1:
    #    list = add_excell(list)
    # list = CSQ.fix_types_table(list)
    # editeble_col_nomera = [_ for _ in list_conf[0] if 'дата_' in _.lower()]
    editeble_col_nomera = []
    hook_prog_bar.set(20)
    hook_prog_bar.text("Применение прав")
    for i, name_field in enumerate(list_from_db[0]):
        if name_field not in self.Data_plan.DICT_INFO_FIELDS_KPL:
            CQT.msgbox(f'Необходимо сформировать правила редактирования поля в БД info_fields_kpl')
            return
        if self.Data_plan.DICT_INFO_FIELDS_KPL[name_field]['hand_editable'] == 1:
            if CMS.access_kpl_tbl(self.Data_plan.DICT_INFO_FIELDS_KPL, name_field):
                editeble_col_nomera.append(name_field)
        hook_prog_bar.set(20 + round(i / len(list_from_db[0]) * 10))
    hook_prog_bar.text("Заполнение данными")
    CQT.fill_wtabl(list_from_db, self.ui.tbl_kal_pl, auto_type=False, set_editeble_col_nomera=editeble_col_nomera,
                   height_row=20,load_links=True,sortingEnabled=True)
    hook_prog_bar.text("Свертка полей")
    for i in range(len(list_conf[0])):
        if CQT.num_col_by_name_c(self.ui.tbl_kal_pl, list_conf[0][i]) != None:
            if list_conf[1][i] == 2:
                self.ui.tbl_kal_pl.setColumnHidden(CQT.num_col_by_name_c(self.ui.tbl_kal_pl, list_conf[0][i]), True)
            else:
                self.ui.tbl_kal_pl.setColumnHidden(CQT.num_col_by_name_c(self.ui.tbl_kal_pl, list_conf[0][i]), False)
        hook_prog_bar.set(30 + round(i / len(list_conf[0]) * 30))
    self.ui.tbl_kal_pl.rowCount()
    hook_prog_bar.text("Оформление заголовков")
    for j in range(self.ui.tbl_kal_pl.columnCount()):
        hook_prog_bar.set(60 + round(j / self.ui.tbl_kal_pl.columnCount() * 20))
        podr = self.ui.tbl_kal_pl.horizontalHeaderItem(j).text().replace('факт_', '').replace(
            'план_', '').split('.')[0]
        r = 11
        g = 11
        b = 11
        if podr in self.Data_plan.DICT_PODR:
            r, g, b = self.Data_plan.DICT_PODR[podr]['Цвет'].split(";")
        CQT.set_color_text_header_wtab_horisontal_c(self.ui.tbl_kal_pl, j, r, g, b, blod=True)

    if self.ui.tbl_filtr_kal_pl.columnCount() < 1:
        btn_clear_filtr(self, False)


    hook_prog_bar.set(80)
    hook_prog_bar.text("Применение цветовой политики")
    CMS.load_column_widths(self, self.ui.tbl_kal_pl)
    oforml_table(self)

    hook_prog_bar.set(90)
    hook_prog_bar.text("Заполнение фильтров")
    hook_prog_bar.close()

    CMS.update_width_filtr(self.ui.tbl_kal_pl, self.ui.tbl_filtr_kal_pl)
    CMS.apply_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl,False)
    KPLUF.apply_select_filtr(self)



@CQT.onerror
def btn_clear_filtr(self: mywindow, apply=True):
    row = CQT.get_dict_line_form_tbl(self.ui.tbl_kal_pl, 0)
    spis_znach = [['' for _ in range(len(row))]]
    nk_status = CQT.num_col_by_name_c(self.ui.tbl_kal_pl, 'plan.Статус')
    if nk_status != None:
        spis_znach[-1][nk_status] = 'Изготовление|Подготовка|К производству|Резерв|Долгосрочный'
    CMS.fill_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl, hidden_scroll=True, spis_znach=spis_znach)
    CMS.update_width_filtr(self.ui.tbl_kal_pl, self.ui.tbl_filtr_kal_pl)


def set_params_kpl(self: mywindow):
    kpl_bool_load_zav = self.ui.chk_kpl_zaversch.isChecked()
    try:
        CMS.save_tmp_path('kpl_bool_load_zav', str(int(kpl_bool_load_zav)))
        update_tabels(self)
    except:
        pass


def set_chk_paint_dates(self: mywindow):
    chk_paint_dates = self.ui.chk_paint_dates.isChecked()
    try:
        CMS.save_tmp_path('kpl_bool_paint_dates', str(int(chk_paint_dates)))
    except:
        pass


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


def show_tabel(self):
    if self.ui.fr_pl_add_poz.isHidden():
        self.edit_tabel_mode = True
        self.ui.fr_pl_etap.setHidden(False)
        self.ui.fr_pl_add_poz.setHidden(False)
        self.ui.tbl_pl_add_poz.setMaximumHeight(370)
        self.ui.fr_pl_add_poz.setMaximumHeight(470)
        self.ui.fr_gant_local.setHidden(True)
        self.ui.cmb_etap.clear()
        self.ui.tbl_pl_add_poz.clear()
        list_month = [_ for _ in CSQ.get_list_of_tables_c(self.db_kplan) if 'm_cld_' in _]
        list_month.insert(0, '')
        self.ui.cmb_etap.addItems(list_month)
        self.ui.cmb_etap.setMaxCount(len(list_month))
    else:
        self.ui.fr_pl_add_poz.setHidden(True)
        self.ui.fr_gant_local.setHidden(False)
        self.edit_tabel_mode = False
        self.ui.tbl_pl_add_poz.setMaximumHeight(70)
        self.ui.fr_pl_add_poz.setMaximumHeight(170)
        self.ui.tbl_pl_add_poz.clear()


@CQT.onerror
def clck_tbl_pl_gaf(self, tbl):
    self.current_kpl_table = 'tbl_preview'
    list_tbl = CQT.list_from_wtabl_c(tbl, rez_dict=True)
    row = list_tbl[tbl.currentRow()]
    if 'Пномер' not in row or row['Пномер'] == '':
        return
    pnom = int(row['Пномер'])
    GPL.update_local_graf(self, pnom=pnom)
    pozition = CMS.Pozition(pnom, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, '')
    GPL.fill_select_poz_kpl(self, pozition.row)
    CMS.on_section_resized(self)
    CQT.summ_selct_tbl(self, tbl)


@CQT.onerror
def clck_tbl_preview(self, tbl):
    self.current_kpl_table = 'tbl_preview'
    CMS.on_section_resized(self)
    CQT.summ_selct_tbl(self, tbl)
    # GPL.load_info_select_block(self,tbl)


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
