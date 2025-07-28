from __future__ import annotations

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
from PyQt5 import QAxContainer
from PyQt5.QtCore import Qt
from pathlib import Path
from PyQt5.QtGui import QPainter, QBrush, QPen, QPixmap, QColor, QFont
import project_cust_38.Cust_QtGui as CGUI
from copy import deepcopy

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MKart import mywindow



def check_load_tabel_in_db(self):
    if self.ui.cmb_tabeli.currentText() == '':
        CQT.blink_obj_c(self,2,self.ui.cmb_tabeli,'Не выбран месяц')
        return False
    if self.ui.tbl_tabeli.columnCount() < 3:
        CQT.blink_obj_c(self,2,self.ui.tbl_tabeli,'Не корректно заполнена таблица')
        return
    try:
        name_tbl_db =F.datetostr(F.strtodate(self.ui.cmb_tabeli.currentText().split(' ')[0],'%d.%m.%Y'),'mtdz_%Y_%m_%d')
    except:
        CQT.blink_obj_c(self,2,self.ui.cmb_tabeli,'Не распознать месяц')
        return False
    return True


def add_list_of_months_to_cmb(self):
    cmb = self.ui.cmb_tabeli
    list_of_month = CSQ.custom_request_c(self.db_users, """SELECT name from sqlite_master where type = 'table';""")
    cmb.clear()
    cmb.addItem('')
    for item in list_of_month:
        if item[0][:5] == 'mtdz_':
            if F.now('').year == F.strtodate(item[0], "mtdz_%Y_%m_%d").year:
                date = F.strtodate(item[0], "mtdz_%Y_%m_%d")
                read_name = F.datetostr(date, f'%d.%m.%Y ({F.month_rus_from_date(date, "", False)})')
                cmb.addItem(read_name)
    CQT.clear_tbl(self.ui.tbl_tabeli_person)


def oform_tabel_to_table(self, dict_users: dict):
    set_days = set()
    for user in dict_users.keys():
        for day in dict_users[user].keys():
            set_days.add(day)
    list_of_days = sorted(list(set_days))
    rez = [['ФИО']]
    for day in list_of_days:
        rez[0].append(day)
    rez[0].append('ИТОГ')
    list_of_days.append('ИТОГ')
    for user in dict_users.keys():
        rez.append([user])
        summ = 0
        for day in list_of_days:
            if day == 'ИТОГ':
                rez[-1].append(round(summ, 2))
                break
            if day in dict_users[user]:
                rez[-1].append(dict_users[user][day])
                if F.is_numeric(dict_users[user][day]):
                    summ += F.valm(dict_users[user][day])
            else:
                rez[-1].append(0)

    CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_tabeli, separ='', isp_hat_c=True, ogr_maxshir_kol=600,min_shir_col=60,set_editeble_col_nomera={'*'})
    for i in range(self.ui.tbl_tabeli.rowCount()):
        for j in range(1, self.ui.tbl_tabeli.columnCount()):
            if not F.is_numeric(self.ui.tbl_tabeli.item(i, j).text()):
                if self.ui.tbl_tabeli.item(i, j).text() == 'В':
                    CQT.set_color_wtab_c(self.ui.tbl_tabeli, i, j, 250, 235, 215)
                else:
                    CQT.set_color_wtab_c(self.ui.tbl_tabeli, i, j, 255, 250, 205)
            else:
                if F.valm(self.ui.tbl_tabeli.item(i, j).text()) == 0:
                    CQT.set_color_wtab_c(self.ui.tbl_tabeli, i, j, 255, 250, 205)
                else:
                    if F.valm(self.ui.tbl_tabeli.item(i, j).text()) <8:
                        CQT.set_color_wtab_c(self.ui.tbl_tabeli, i, j, 255, 230, 235)


def check_time(txt):
    if F.is_date(txt,"%H:%M"):
        return True
    CQT.msgbox('Не верный формат времени')
    return False

def check_val(txt):
    if F.is_numeric(txt):
        return True
    CQT.msgbox('Не верный формат числа')
    return False

def cellChanged(self, row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return

    ima_col = self.ui.tbl_rc.horizontalHeaderItem(col).text()
    if ima_col == None:
        CQT.msgbox('Ошибка уточнения полей')
        return
    conn, cur = CSQ.connect_bd(self.db_users)
    znach = self.ui.tbl_rc.item(row, col).text()
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())

    if ima_col == 'Время_начала_1' or ima_col == 'Время_конца_1' or ima_col == 'Время_начала_2' or \
        ima_col == 'Время_конца_2' or ima_col == 'Время_начала_3' or ima_col == 'Время_конца_3':
        if check_time(znach) == False:
            old_znach = CSQ.custom_request_c(self.db_users,f"""SELECT {ima_col} FROM rab_mesta WHERE Пномер = {pnom}""",conn=conn)[-1][0]
            self.ui.tbl_rc.item(row,col).setText(str(old_znach))
            CSQ.close_bd(conn)
            return
    if ima_col == 'Нераб_мин1' or ima_col == 'Между_нар_мин1' or ima_col == 'Коэфф_производит1' or \
            ima_col == 'Нераб_мин2' or ima_col == 'Между_нар_мин2' or ima_col == 'Коэфф_производит2' or \
            ima_col == 'Нераб_мин3' or ima_col == 'Между_нар_мин3' or ima_col == 'Коэфф_производит3':
        if check_val(znach) == False:
            old_znach = CSQ.custom_request_c(self.db_users,f"""SELECT {ima_col} FROM rab_mesta WHERE Пномер = {pnom}""",conn=conn)[-1][0]
            self.ui.tbl_rc.item(row,col).setText(str(old_znach))
            CSQ.close_bd(conn)
            return
    CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET {ima_col} = "{znach}" WHERE Пномер = {pnom}""",conn=conn)
    CSQ.close_bd(conn)
    CMS.dict_rab_mesta(self, self.db_users)

def load_deficit_emploee(self):
    rez = [['Пномер_РМ','Расположение','Прозвище','Профессия','Смена']]
    dict_rez_itog = dict()
    dict_rez_all = dict()
    conn, cur = CSQ.connect_bd(self.db_users)
    custom_request_c = """SELECT rab_mesta.Пномер, places.adress as Расположение, rab_mesta.Прозвище, professions.имя , rab_mesta.ФИО_1, rab_mesta.ФИО_2, rab_mesta.ФИО_3
            FROM rab_mesta 
            INNER JOIN professions ON professions.код == rab_mesta.Код_профессии
            INNER JOIN places ON places.serial == rab_mesta.Расположение
             """
    spis_rm = CSQ.custom_request_c(self.db_users, custom_request_c, hat_c=True, conn=conn)
    nk_r_fio1 = F.num_col_by_name_in_hat_c(spis_rm, 'ФИО_1')
    nk_r_fio2 = F.num_col_by_name_in_hat_c(spis_rm, 'ФИО_2')
    nk_r_fio3 = F.num_col_by_name_in_hat_c(spis_rm, 'ФИО_3')
    nk_r_pnom = F.num_col_by_name_in_hat_c(spis_rm, 'Пномер')
    nk_r_rasp = F.num_col_by_name_in_hat_c(spis_rm, 'Расположение')
    nk_r_proz = F.num_col_by_name_in_hat_c(spis_rm, 'Прозвище')
    nk_r_profes = F.num_col_by_name_in_hat_c(spis_rm, 'имя')
    for item in spis_rm[1:]:
        if item[nk_r_fio1] == 1:
            deficit_cm = '1'
            rez.append([item[nk_r_pnom], item[nk_r_rasp], item[nk_r_proz], item[nk_r_profes], deficit_cm])
            if item[nk_r_profes] not in dict_rez_itog:
                dict_rez_itog[item[nk_r_profes]] = 1
            else:
                dict_rez_itog[item[nk_r_profes]] += 1
        if item[nk_r_fio2] == 1:
            deficit_cm = '2'
            rez.append([item[nk_r_pnom], item[nk_r_rasp], item[nk_r_proz], item[nk_r_profes], deficit_cm])
            if item[nk_r_profes] not in dict_rez_itog:
                dict_rez_itog[item[nk_r_profes]] = 1
            else:
                dict_rez_itog[item[nk_r_profes]] += 1
        if item[nk_r_fio3] == 1:
            deficit_cm = '3'
            rez.append([item[nk_r_pnom], item[nk_r_rasp], item[nk_r_proz], item[nk_r_profes], deficit_cm])
            if item[nk_r_profes] not in dict_rez_itog:
                dict_rez_itog[item[nk_r_profes]] = 1
            else:
                dict_rez_itog[item[nk_r_profes]] += 1
        if item[nk_r_fio1] != 1 and item[nk_r_fio1] != 2 and item[nk_r_fio1] != 838:
            if item[nk_r_profes] not in dict_rez_all:
                dict_rez_all[item[nk_r_profes]] = 1
            else:
                dict_rez_all[item[nk_r_profes]] += 1
        if item[nk_r_fio2] != 1 and item[nk_r_fio2] != 2 and item[nk_r_fio2] != 838:
            if item[nk_r_profes] not in dict_rez_all:
                dict_rez_all[item[nk_r_profes]] = 1
            else:
                dict_rez_all[item[nk_r_profes]] += 1
        if item[nk_r_fio3] != 1 and item[nk_r_fio3] != 2 and item[nk_r_fio3] != 838:
            if item[nk_r_profes] not in dict_rez_all:
                dict_rez_all[item[nk_r_profes]] = 1
            else:
                dict_rez_all[item[nk_r_profes]] += 1

    rez.append(["====" for _ in rez[0]])
    rez.append(['Профессия','Количество по РМ','Дефицит','Дефицит,%',''])
    for key in dict_rez_all.keys():
        deficit = 0
        procent = 0
        if key in dict_rez_itog:
            deficit = dict_rez_itog[key]
            procent = round(deficit*100/dict_rez_all[key])
        rez.append([key,dict_rez_all[key],deficit,procent,''])
    CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_vacant, isp_hat_c=True, separ='')
    CMS.fill_filtr_c(self, self.ui.tbl_vacant_filtr, self.ui.tbl_vacant)
    CSQ.close_bd(conn)


def load_emploee(self):
    conn, cur = CSQ.connect_bd(self.db_users)
    custom_request_c = """SELECT employee.Пномер, employee.ФИО, employee.Должность, employee.Статус
    , "" as Номер_РМ
        FROM employee 
        WHERE employee.ФИО != "" and employee.ФИО != "-" AND Статус != 'Увольнение' 
         """
    spis_empl = CSQ.custom_request_c(self.db_users, custom_request_c, hat_c=True, conn=conn)
    nk_e_pnom = F.num_col_by_name_in_hat_c(spis_empl, 'Пномер')
    nk_e_nrm = F.num_col_by_name_in_hat_c(spis_empl,'Номер_РМ')
    custom_request_c = """SELECT rab_mesta.Пномер, rab_mesta.ФИО_1, rab_mesta.ФИО_2, rab_mesta.ФИО_3
        FROM rab_mesta
         """
    spis_rm = CSQ.custom_request_c(self.db_users, custom_request_c, hat_c=True, conn=conn)
    nk_r_fio1 = F.num_col_by_name_in_hat_c(spis_rm,'ФИО_1')
    nk_r_fio2 = F.num_col_by_name_in_hat_c(spis_rm, 'ФИО_2')
    nk_r_fio3 = F.num_col_by_name_in_hat_c(spis_rm, 'ФИО_3')
    nk_r_pnom = F.num_col_by_name_in_hat_c(spis_rm,'Пномер')

    for i in range(1,len(spis_empl)):
        for rm in spis_rm:
            if spis_empl[i][nk_e_pnom] == rm[nk_r_fio1]:
                spis_empl[i][nk_e_nrm] += f' {str(rm[nk_r_pnom])};'
            if spis_empl[i][nk_e_pnom] == rm[nk_r_fio2]:
                spis_empl[i][nk_e_nrm] += f' {str(rm[nk_r_pnom])};'
            if spis_empl[i][nk_e_pnom] == rm[nk_r_fio3]:
                spis_empl[i][nk_e_nrm] += f' {str(rm[nk_r_pnom])};'

    CQT.fill_wtabl_old_c(self, spis_empl, self.ui.tbl_emploee, isp_hat_c=True, separ='')
    CMS.fill_filtr_c(self,self.ui.tbl_emploee_filtr,self.ui.tbl_emploee)
    CSQ.close_bd(conn)
    return

def zagruzka_rc(self):

    spis = CMS.DICT_RC_TBL(self.db_users)
    conn,cur = CSQ.connect_bd(self.db_users)
    spis_prof_fio_status_emploee = CSQ.custom_request_c(self.db_users,"""SELECT Должность, ФИО ,Статус, Пномер FROM employee""",hat_c=False,conn=conn, rez_dict=True)
    spis_prof_emploee = sorted(list(set([_['Должность'] for _ in spis_prof_fio_status_emploee])))
    spis_fio_uvol_emploee = [[_['ФИО'], _['Пномер']] for _ in spis_prof_fio_status_emploee if _['Статус']=="Увольнение"]


    for i in range(len(spis)):
        if [spis[i]['ФИО_1см'], spis[i]['Пномер_emp1']] in spis_fio_uvol_emploee:
            spis[i]['ФИО_1см'] += ' УВОЛЕН'
        if [spis[i]['ФИО_2см'], spis[i]['Пномер_emp2']] in spis_fio_uvol_emploee:
            spis[i]['ФИО_2см'] += ' УВОЛЕН'
        if [spis[i]['ФИО_3см'], spis[i]['Пномер_emp3']] in spis_fio_uvol_emploee:
            spis[i]['ФИО_3см'] += ' УВОЛЕН'

    spis_rc = CSQ.custom_request_c(self.db_users, """SELECT Имя FROM rab_c""", hat_c=False, conn=conn)
    spis_rc = sorted(list(set([_[0] for _ in spis_rc])))

    spis_oborud = CSQ.custom_request_c(self.db_users, """SELECT Наименование || ' ' || Инв_номер FROM equipment""", hat_c=False, conn=conn)
    spis_oborud = sorted(list(set([_[0] for _ in spis_oborud])))

    spis_prof = CSQ.custom_request_c(self.db_users, """SELECT имя FROM professions""", hat_c=False, conn=conn)
    spis_prof = sorted(list(set([_[0] for _ in spis_prof])))

    spis_places = CSQ.custom_request_c(self.db_users, """SELECT adress FROM places""", hat_c=False, conn=conn)
    spis_places = sorted(list(set([_[0] for _ in spis_places])))

    set_edit = {'Прозвище',
                'Примечание',
                'Время_начала_1',
                'Время_конца_1',
                'Нераб_мин1',
                'Между_нар_мин1',
                'Коэфф_производит1',

                 'Время_начала_2',
                 'Время_конца_2',
                 'Нераб_мин2',
                 'Между_нар_мин2',
                 'Коэфф_производит2',

                 'Время_начала_3',
                 'Время_конца_3',
                 'Нераб_мин3',
                 'Между_нар_мин3',
                 'Коэфф_производит3',

                'coord'
                }

    CQT.fill_wtabl_old_c(self,spis,self.ui.tbl_rc,isp_hat_c=True,separ='',set_editeble_col_nomera=set_edit)
    CQT.color_cell_wtable_c(self.ui.tbl_rc,'ФИО_1см','УВОЛЕН',r=110)
    CQT.color_cell_wtable_c(self.ui.tbl_rc, 'ФИО_2см', 'УВОЛЕН', r=110)
    CQT.color_cell_wtable_c(self.ui.tbl_rc, 'ФИО_3см', 'УВОЛЕН', r=110)
    nk_dolg1 = CQT.num_col_by_name_c(self.ui.tbl_rc,'Должность_1см')
    nk_dolg2 = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Должность_2см')
    nk_dolg3 = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Должность_3см')
    nk_raspolog = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Расположение')
    nk_rc = CQT.num_col_by_name_c(self.ui.tbl_rc, 'РЦ')
    nk_oborud = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Оборудование')
    nk_prof = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Профессия_рм')
    nk_boss = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Руководитель')
    for i in range(self.ui.tbl_rc.rowCount()):
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_dolg1, spis_prof_emploee, False, select_prof_emploee)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_dolg2, spis_prof_emploee, False, select_prof_emploee)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_dolg3, spis_prof_emploee, False, select_prof_emploee)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_raspolog, spis_places, False, select_rasp)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_rc, spis_rc, False, select_rc)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_oborud, spis_oborud, False, select_oborud)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_prof, spis_prof, False, select_prof)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_prof, spis_prof, False, select_prof)
    CMS.fill_filtr_c(self,self.ui.tbl_rc_filtr,self.ui.tbl_rc)
    CSQ.close_bd(conn)
    self.ui.tbl_rc.setToolTip(f'"|_|" вакант = нет     "-" не нужен = нет     "+" не нужен = есть')

    return

def add_rm(self):
    modifiers = CQT.get_key_modifiers(self)
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    rez = CQT.msgboxgYN('Добавить новое рабочее место?')
    if rez != True:
        return
    if modifiers == ['shift']:
        nom_rm = self.ui.tbl_rc.item(self.ui.tbl_rc.currentRow(),CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')).text()
        conn, cur = CSQ.connect_bd(self.db_users)
        custom_request_c = f"""SELECT rab_mesta.Расположение, rab_mesta.Код_РЦ as РЦ, rab_mesta.Прозвище, rab_mesta.Номер_осн_оборуд as Оборудование,
            rab_mesta.Код_профессии as Профессия_рм,
             Время_начала_1, Время_конца_1, Нераб_мин1, Между_нар_мин1, Коэфф_производит1,
             Время_начала_2, Время_конца_2, Нераб_мин2, Между_нар_мин2, Коэфф_производит2,
             Время_начала_3, Время_конца_3, Нераб_мин3, Между_нар_мин3, Коэфф_производит3, 
             rab_mesta.Примечание
             FROM rab_mesta WHERE rab_mesta.Пномер = {nom_rm}"""
        spis = CSQ.custom_request_c(self.db_users, custom_request_c, hat_c=True, conn=conn, rez_dict=True)[0]
        CSQ.close_bd(conn)
        rasp = spis['Расположение']
        kod_rc = spis['РЦ']
        Прозвище = spis['Прозвище']
        Номер_осн_оборуд =  spis['Оборудование']
        Код_профессии =   spis['Профессия_рм']
        Время_начала_1 =   spis['Время_начала_1']
        Время_конца_1 =  spis['Время_конца_1']
        Нераб_мин1 =  spis['Нераб_мин1']
        Между_нар_мин1 =    spis['Между_нар_мин1']
        Коэфф_производит1 =  spis['Коэфф_производит1']
        Время_начала_2 =   spis['Время_начала_2']
        Время_конца_2 =  spis['Время_конца_2']
        Нераб_мин2 =   spis['Нераб_мин2']
        Между_нар_мин2 =   spis['Между_нар_мин2']
        Коэфф_производит2 =  spis['Коэфф_производит2']
        Время_начала_3 =  spis['Время_начала_3']
        Время_конца_3 =    spis['Время_конца_3']
        Нераб_мин3 =  spis['Нераб_мин3']
        Между_нар_мин3 =   spis['Между_нар_мин3']
        Коэфф_производит3 =  spis['Коэфф_производит3']
        Примечание =  spis['Примечание']
        custom_request_c = f"""INSERT INTO rab_mesta
                                      (Расположение, Код_РЦ, Прозвище, Номер_осн_оборуд, Код_профессии,ФИО_1,Время_начала_1,
                                      Время_конца_1,Нераб_мин1,Между_нар_мин1,Коэфф_производит1,ФИО_2,Время_начала_2,
                                      Время_конца_2,Нераб_мин2,Между_нар_мин2,Коэфф_производит2,ФИО_3,Время_начала_3,
                                      Время_конца_3,Нераб_мин3,Между_нар_мин3,Коэфф_производит3,Примечание)
                                      VALUES ({rasp}, "{kod_rc}", "{Прозвище}", {Номер_осн_оборуд}, "{Код_профессии}",
                                      1, "{Время_начала_1}", "{Время_конца_1}",{Нераб_мин1},{Между_нар_мин1},{Коэфф_производит1},
                                      1, "{Время_начала_2}", "{Время_конца_2}",{Нераб_мин2},{Между_нар_мин2},{Коэфф_производит2},
                                      1, "{Время_начала_3}", "{Время_конца_3}",{Нераб_мин3},{Между_нар_мин3},{Коэфф_производит3},
                                      "{Примечание}");"""
    else:
        custom_request_c = """INSERT INTO rab_mesta
                              (Расположение, Код_РЦ, Прозвище, Номер_осн_оборуд, Код_профессии,ФИО_1,Время_начала_1,
                              Время_конца_1,Нераб_мин1,Между_нар_мин1,Коэфф_производит1,ФИО_2,Время_начала_2,
                              Время_конца_2,Нераб_мин2,Между_нар_мин2,Коэфф_производит2,ФИО_3,Время_начала_3,
                              Время_конца_3,Нераб_мин3,Между_нар_мин3,Коэфф_производит3,Примечание)
                              VALUES (0, "010101", "", 1, "10371",
                              1, "07:00","15:30",75,40,1,
                              1, "15:30","23:59",75,40,0.9,
                              1, "00:01","07:00",75,40,0.8,
                              "");"""
    if CSQ.custom_request_c(self.db_users, custom_request_c):
        CQT.msgbox('Успешно')
        zagruzka_rc(self)
    else:
        CQT.msgbox('Ошибка')


def select_prof(self, text,  row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())
    conn, cur = CSQ.connect_bd(self.db_users)
    rez = CSQ.custom_request_c(self.db_users,f"""SELECT код FROM professions WHERE имя == '{text}'""",conn=conn)
    kod_prof = rez[-1][0]
    CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET Код_профессии = "{kod_prof}" WHERE Пномер = {pnom}""", hat_c=False)
    CSQ.close_bd(conn)

def select_oborud(self, text,  row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())
    conn, cur = CSQ.connect_bd(self.db_users)
    rez = CSQ.custom_request_c(self.db_users,f"""SELECT Пномер FROM equipment WHERE Наименование || ' ' || Инв_номер == '{text}'""",conn=conn)
    kod_oborud = rez[-1][0]
    CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET Номер_осн_оборуд = "{kod_oborud}" WHERE Пномер = {pnom}""", hat_c=False)
    CSQ.close_bd(conn)

def select_rc(self, text,  row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())
    conn, cur = CSQ.connect_bd(self.db_users)
    rez = CSQ.custom_request_c(self.db_users,f"""SELECT Код FROM rab_c WHERE Имя == '{text}'""",conn=conn)
    kod_rc = rez[-1][0]
    CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET Код_РЦ = "{kod_rc}" WHERE Пномер = {pnom}""", hat_c=False)
    CSQ.close_bd(conn)

def select_rasp(self, text,  row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())
    conn, cur = CSQ.connect_bd(self.db_users)
    rez = CSQ.custom_request_c(self.db_users, f"""SELECT serial FROM places WHERE adress == '{text}'""", conn=conn)
    kod_place = rez[-1][0]
    CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET Расположение = {kod_place} WHERE Пномер = {pnom}""", hat_c=False)
    CSQ.close_bd(conn)


def clck_tbl_rc(self):
    #self.ui.lbl_info_rc.setText('')
    CQT.statusbar_text(self)
    tbl = self.ui.tbl_rc
    r = tbl.currentRow()
    col = tbl.currentColumn()
    if r == -1 or col == -1:
        return
    nk_fio = False
    if tbl.horizontalHeaderItem(col).text() == 'ФИО_1см':
        nk_fio = CQT.num_col_by_name_c(tbl,'ФИО_1см')
    if tbl.horizontalHeaderItem(col).text() == 'ФИО_2см':
        nk_fio = CQT.num_col_by_name_c(tbl,'ФИО_2см')
    if tbl.horizontalHeaderItem(col).text() == 'ФИО_3см':
        nk_fio = CQT.num_col_by_name_c(tbl,'ФИО_3см')
    if nk_fio:
        fio = tbl.item(r,col).text()
        for id in self.DICT_EMPLOEE_FULL.keys():
            if fio in self.DICT_EMPLOEE_FULL:
                strok = str(self.DICT_EMPLOEE_FULL[fio])
                #self.ui.lbl_info_rc.setText(strok)
                CQT.statusbar_text(self,strok)

def select_prof_emploee(self, text, row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_fio = None
    if self.ui.tbl_rc.horizontalHeaderItem(col).text() == 'Должность_1см':
        nk_fio = CQT.num_col_by_name_c(self.ui.tbl_rc,'ФИО_1см')
    if self.ui.tbl_rc.horizontalHeaderItem(col).text() == 'Должность_2см':
        nk_fio = CQT.num_col_by_name_c(self.ui.tbl_rc,'ФИО_2см')
    if self.ui.tbl_rc.horizontalHeaderItem(col).text() == 'Должность_3см':
        nk_fio = CQT.num_col_by_name_c(self.ui.tbl_rc,'ФИО_3см')
    if nk_fio == None:
        return
    #spis_fio = CSQ.custom_request_c(self.db_users, f"""SELECT ФИО || "$" || Должность || "$" || Режим  FROM employee WHERE Должность == '{text}' AND Статус != 'Увольнение' """, hat_c=False)
    #spis_fio = [_[0] for _ in spis_fio]
    spis_fio = []
    for fio in self.DICT_EMPLOEE_FULL.keys():
        if self.DICT_EMPLOEE_FULL[fio]['Должность'] == text:
            spis_fio.append('$'.join([fio,self.DICT_EMPLOEE_FULL[fio]['Подразделение'],self.DICT_EMPLOEE_FULL[fio]['Режим']]))
    spis_fio = sorted(spis_fio)
    CQT.add_combobox(self, self.ui.tbl_rc, row, nk_fio, spis_fio, True, select_fio)

def select_fio(self, text,  row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_fio = None
    if self.ui.tbl_rc.horizontalHeaderItem(col).text() == 'ФИО_1см':
        nk_fio = "ФИО_1"
    if self.ui.tbl_rc.horizontalHeaderItem(col).text() == 'ФИО_2см':
        nk_fio = "ФИО_2"
    if self.ui.tbl_rc.horizontalHeaderItem(col).text() == 'ФИО_3см':
        nk_fio = "ФИО_3"
    if nk_fio == None:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row,nk_pnom).text())
    conn,cur = CSQ.connect_bd(self.db_users)
    #rez = CSQ.custom_request_c(self.db_users,f"""SELECT Пномер FROM employee WHERE ФИО == '{text}' AND Статус != 'Увольнение' """,conn=conn)
    pnom_emploe = 2
    if len(text.split("$")) == 3:
        sel_fio, sel_podr, sel_rej = text.split("$")
        pnom_emploe = self.DICT_EMPLOEE_FULL[sel_fio]['Пномер']
    CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET {nk_fio} = {pnom_emploe} WHERE Пномер = {pnom}""", hat_c=False)
    CSQ.close_bd(conn)

def set_tooltip_val(self):
    r = self.ui.tbl_tabeli.currentRow()
    c = self.ui.tbl_tabeli.currentColumn()
    key = f'{r},{c}'
    if key not in self.dict_zamen_tabel_update:
        self.ui.tbl_tabeli.setToolTip('')
        return
    old = self.dict_zamen_tabel_update[key]['old']
    new = self.dict_zamen_tabel_update[key]['new']
    self.ui.tbl_tabeli.setToolTip(f'Было: {old}, Стало: {new}')
def set_old_val(self):
    r = self.ui.tbl_tabeli.currentRow()
    c = self.ui.tbl_tabeli.currentColumn()
    key = f'{r},{c}'
    if key not in self.dict_zamen_tabel_update:
        CQT.msgbox(f'Ошибка значений')
        return
    old = str(self.dict_zamen_tabel_update[key]['old'])
    new = str(self.dict_zamen_tabel_update[key]['new'])
    old_theme = self.dict_zamen_tabel_update[key]['old_theme']
    new_theme = self.dict_zamen_tabel_update[key]['new_theme']
    if self.ui.tbl_tabeli.item(r,c).text() == old:
        self.ui.tbl_tabeli.item(r, c).setText(new)
        self.ui.tbl_tabeli.item(r, c).setBackground(new_theme)
    else:
        self.ui.tbl_tabeli.item(r, c).setText(old)
        self.ui.tbl_tabeli.item(r, c).setBackground(old_theme)


@CQT.onerror
def select_schema_dbl_clk(self, *args):
    r = self.ui.tbl_rc.currentRow()
    column = self.ui.tbl_rc.currentColumn()
    if CQT.num_col_by_name_c(self.ui.tbl_rc,'Пномер') == column:
        nk_rasp = CQT.num_col_by_name_c(self.ui.tbl_rc,'Расположение')
        #CMS.dict_rab_mesta(self, self.db_users)
        img = self.DICT_PLACES[self.ui.tbl_rc.item(r,nk_rasp).text()]['img_name']
        path = F.scfg('mk_data') + F.sep() + 'schems' + F.sep()
        coords = self.DICT_RM[int(self.ui.tbl_rc.item(r,column).text())]['coord']
        x = y = ''
        add_prim = get_ccords_text_rc(self,self.DICT_PLACES[self.ui.tbl_rc.item(r,nk_rasp).text()]['serial'])
        if coords != None and coords.strip() != '':
            x , y = coords.split(";")
            x = F.valm(x) * self.ui.lbl_shema.width()
            y = F.valm(y) * self.ui.lbl_shema.height()
        load_schema_jpg(self, path + img,x,y,add_prim=add_prim)
        self.ui.tabW_rab_places.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabW_rab_places,'Схема')) # 25.07.25
@CQT.onerror
def get_ccords_text_rc(self:mywindow,cex:int,*args):
    add_prim = []
    set_prim = set()
    font_size = 12
    if self.ui.le_schema_font_height.text().strip() == '':
        return
    if F.is_numeric(self.ui.le_schema_font_height.text().strip()):
        font_size = int(F.round_up(self.ui.le_schema_font_height.text().strip()))
    else:
        self.ui.le_schema_font_height.blockSignals(True)
        self.ui.le_schema_font_height.setText(str(font_size))
        self.ui.le_schema_font_height.blockSignals(False)
        return
    if font_size < 6:
        font_size = 6
    low_font_size = font_size - 5


    for k, item in self.DICT_RM.items():
        alias = item['Прозвище'].strip()
        if not alias:
            continue
        if self.ui.chk_schemas_show_alias.isChecked():
            text = f'РМ {k} "{alias}"'
        else:
            text = f'РМ {k}'
        if ";" not in item['coord'] or item['Расположение'] != cex:
            continue
        x, y = item['coord'].split(';')


        def gen_fio_pos(fio_num):
            res = ''
            if fio_num in self.DICT_EMPLOEE_FULL_BY_SNUM:
                fio = ''
                pos = ''
                if self.ui.chk_schemas_show_fio.isChecked():
                    fio = self.DICT_EMPLOEE_FULL_BY_SNUM[fio_num]['ФИО']
                if self.ui.chk_schemas_show_position.isChecked():
                    pos = self.DICT_EMPLOEE_FULL_BY_SNUM[fio_num]['Должность']
                res = f"{fio} {pos}".strip()
            return res

        fio1 = gen_fio_pos(item['ФИО_1'])
        fio2 = gen_fio_pos(item['ФИО_2'])
        fio3 = gen_fio_pos(item['ФИО_3'])

        add_prim.append({'x': F.valm(x) * self.ui.lbl_shema.width(),
                         'y': (F.valm(y)-0.02) * self.ui.lbl_shema.height(),
                         'prim': text,
                         'font_size':font_size})
        if len(fio1) >5:
            add_prim.append({'x': F.valm(x) * self.ui.lbl_shema.width(),
                         'y': (F.valm(y)) * self.ui.lbl_shema.height(),
                         'prim': f'1 см.{fio1}' ,
                         'font_size': low_font_size})
        if len(fio2) >5:
            add_prim.append({'x': F.valm(x) * self.ui.lbl_shema.width(),
                             'y': (F.valm(y)+0.02) * self.ui.lbl_shema.height(),
                             'prim': f'2 см.{fio2}',
                             'font_size': low_font_size})
        if len(fio3) >5:
            add_prim.append({'x': F.valm(x) * self.ui.lbl_shema.width(),
                             'y': (F.valm(y)+0.04) * self.ui.lbl_shema.height(),
                             'prim': f'3 см.{fio3}',
                             'font_size': low_font_size})
        set_prim.add(text)
    return add_prim
def save_control_schema_output(self:mywindow):
    CMS.save_tmp_stukt({
        'font_height':self.ui.le_schema_font_height.text(),
        'chk_schemas_show_fio':self.ui.chk_schemas_show_fio.isChecked(),
        'chk_schemas_show_position':self.ui.chk_schemas_show_position.isChecked(),
        'chk_schemas_show_alias':self.ui.chk_schemas_show_alias.isChecked(),
    }, 'control_schema_output')

def load_control_schema_output(self:mywindow):
    data = CMS.load_tmp_stukt('control_schema_output',False)
    if not data:
        return
    self.ui.le_schema_font_height.blockSignals(True)
    self.ui.le_schema_font_height.setText(data['font_height'])
    self.ui.le_schema_font_height.blockSignals(False)
    self.ui.chk_schemas_show_fio.blockSignals(True)
    self.ui.chk_schemas_show_fio.setChecked(data['chk_schemas_show_fio'])
    self.ui.chk_schemas_show_fio.blockSignals(False)
    self.ui.chk_schemas_show_position.blockSignals(True)
    self.ui.chk_schemas_show_position.setChecked(data['chk_schemas_show_position'])
    self.ui.chk_schemas_show_position.blockSignals(False)
    self.ui.chk_schemas_show_alias.blockSignals(True)
    self.ui.chk_schemas_show_alias.setChecked(data['chk_schemas_show_alias'])
    self.ui.chk_schemas_show_alias.blockSignals(False)

def select_schema(self):


    if self.ui.cmb_schems.currentText() == '':
        return
    path = F.scfg('mk_data') + F.sep() + 'schems' + F.sep()
    cex =0
    if F.existence_file_c(path):
        list_files = F.list_of_files_c(path)
        for file in list_files[0][2]:
            if F.keep_extention_c(file) == '.jpg':
                if F.throw_out_extention_c(file) == self.ui.cmb_schems.currentText():
                    for place in self.DICT_PLACES.keys():
                        if F.throw_out_extention_c(self.DICT_PLACES[place]['img_name']) == self.ui.cmb_schems.currentText():
                            cex = self.DICT_PLACES[place]['serial']
                    add_prim = get_ccords_text_rc(self,cex)
                    load_schema_jpg(self,list_files[0][0] + file,add_prim=add_prim)
                    save_control_schema_output(self)
                    return
        CQT.msgbox(f'Не найден файл {self.ui.cmb_schems.text()}')
        return
    CQT.msgbox(f'Не найден путь {path}')
    return

def load_schema_jpg(self:mywindow, path, x_sel = '', y_sel = '', add_prim:list=()):
    lbl = self.ui.lbl_shema

    fon = QPixmap(path)
    #koef = fon.height()/lbl.height()
    #lbl.setFixedHeight(fon.width()/koef)
    old_w = fon.width()
    old_h = fon.height()
    #lbl.setFixedWidth(fon.height()/koef)
    lbl.clear()
    #self.ui.lbl_shema.setFixedSize(self.SIZE_SCHEMA_LBL)
    self.ui.lbl_shema.maximumSize()
    pixmap = fon.scaled(lbl.size(), Qt.KeepAspectRatio)
    wind_k_width = old_w / pixmap.width()
    wind_k_height = old_h / pixmap.height()
    pic_w = 400
    pic_h = 100
    painter = QPainter(pixmap)
    painter.setPen(QColor(168, 34, 3))

    if x_sel != '':
        path_pic = F.scfg('mk_data') + F.sep() + 'schems' + F.sep() + "Shape_1.png"
        #painter = QPainter(self)
        pic = QPixmap(path_pic)
        pic_h = pic.height()/wind_k_height
        pic_w = pic.width()/wind_k_width
        painter.drawPixmap(int(round(x_sel - pic_w / 2)), int(round(y_sel - pic_h / 2)), int(pic_w), int(pic_h), pic)
    if add_prim:
        for item in add_prim:
            painter.setFont(QFont('Decorative', item['font_size']))
            painter.drawText(int(round(item['x'] - pic_w / 2)), int(round(item['y'] - pic_h / 2)), int(pic_w),
                             int(pic_h),Qt.AlignCenter,
                         item['prim'])
    painter.end()

    self.ui.lbl_shema.setPixmap(pixmap)
