from __future__ import annotations

import datetime
import collections
from pathlib import Path
from copy import deepcopy
import re
from typing import TYPE_CHECKING

from PyQt5 import QAxContainer, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QPen, QPixmap, QColor, QFont

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_QtGui as CGUI
from project_cust_38 import Cust_config as CFG

if TYPE_CHECKING:
    from MKart import mywindow


DEFAULT_SHIFT_SETTINGS = {
    1: {"time_start": "07:00", "time_end": "15:30", "Нераб_мин": 75, "Между_нар_мин": 40, "Коэфф_производит": 1},
    2: {"time_start": "15:30", "time_end": "23:59", "Нераб_мин": 75, "Между_нар_мин": 40, "Коэфф_производит": 0.9},
    3: {"time_start": "00:01", "time_end": "07:00", "Нераб_мин": 75, "Между_нар_мин": 40, "Коэфф_производит": 0.8},
}

def ensure_workplace_shifts(self, workplace_id: int, conn=None):
    """Создаёт отсутствующие строки смен 1..3 для рабочего места."""
    existing = CSQ.custom_request_c(
        self.db_users,
        f"""SELECT shift_no FROM schedule_work_places
              WHERE workplace_id = {int(workplace_id)}""",
        hat_c=False
    )
    existing = {int(r[0]) for r in existing} if existing else set()
    for shift_no, d in DEFAULT_SHIFT_SETTINGS.items():
        if shift_no in existing:
            continue
        CSQ.custom_request_c(
            self.db_users,
            f"""INSERT INTO schedule_work_places
                  (workplace_id, employee_id, shift_no, time_start, time_end, Нераб_мин, Между_нар_мин, Коэфф_производит)
                  VALUES ({int(workplace_id)}, 1, {int(shift_no)},
                          '{d['time_start']}', '{d['time_end']}', {int(d['Нераб_мин'])}, {int(d['Между_нар_мин'])}, {float(d['Коэфф_производит'])});""",
        )


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

def cellChanged(self, row, col): #26.01.2026
    if CQT.is_table_updating(self.ui.tbl_rc):
        return
    if CMS.user_access(self.bd_naryad, 'rab_mesta_edit', F.user_name()) == False:
        return

    ima_col = self.ui.tbl_rc.horizontalHeaderItem(col).text()
    if ima_col is None:
        CQT.msgbox('Ошибка уточнения полей')
        return

    znach = self.ui.tbl_rc.item(row, col).text()
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())

    shift_no = None
    swp_col = None
    is_time = False

    if ima_col.startswith('Время_начала_') or ima_col.startswith('Время_конца_'):
        is_time = True
        try:
            shift_no = int(ima_col.split('_')[-1])
        except Exception as e:
            shift_no = None
        swp_col = 'time_start' if 'Время_начала_' in ima_col else 'time_end'
        if shift_no in (1, 2, 3):
            if check_time(znach) == False:
                ensure_workplace_shifts(self, pnom)
                old_znach = CSQ.custom_request_c(
                    self.db_users,
                    f"""SELECT {swp_col} FROM schedule_work_places
                          WHERE workplace_id = {pnom} AND shift_no = {shift_no}""",
                )[-1][0]
                self.ui.tbl_rc.item(row, col).setText(str(old_znach))
                return

    if ima_col.startswith('Нераб_мин') or ima_col.startswith('Между_нар_мин') or ima_col.startswith('Коэфф_производит'):
        m = re.search(r'(\d+)$', ima_col)
        if m:
            shift_no = int(m.group(1))
        if ima_col.startswith('Нераб_мин'):
            swp_col = 'Нераб_мин'
        elif ima_col.startswith('Между_нар_мин'):
            swp_col = 'Между_нар_мин'
        else:
            swp_col = 'Коэфф_производит'
        if shift_no in (1, 2, 3):
            if check_val(znach) == False:
                ensure_workplace_shifts(self, pnom)
                old_znach = CSQ.custom_request_c(
                    self.db_users,
                    f"""SELECT {swp_col} FROM schedule_work_places
                          WHERE workplace_id = {pnom} AND shift_no = {shift_no}""",
                )[-1][0]
                self.ui.tbl_rc.item(row, col).setText(str(old_znach))
                return

    if shift_no in (1, 2, 3) and swp_col:
        ensure_workplace_shifts(self, pnom)
        if swp_col in ('Нераб_мин', 'Между_нар_мин'):
            val_sql = int(F.valm(znach)) if F.is_numeric(znach) else 0
            CSQ.custom_request_c(
                self.db_users,
                f"""UPDATE schedule_work_places SET {swp_col} = {val_sql}
                      WHERE workplace_id = {pnom} AND shift_no = {shift_no}""",
            )
        elif swp_col == 'Коэфф_производит':
            val_sql = float(F.valm(znach)) if F.is_numeric(znach) else 0
            CSQ.custom_request_c(
                self.db_users,
                f"""UPDATE schedule_work_places SET {swp_col} = {val_sql}
                      WHERE workplace_id = {pnom} AND shift_no = {shift_no}""",
            )
        else:
            CSQ.custom_request_c(
                self.db_users,
                f"""UPDATE schedule_work_places SET {swp_col} = '{znach}'
                      WHERE workplace_id = {pnom} AND shift_no = {shift_no}""",
            )
        CMS.dict_rab_mesta(self, self.db_users)
        return

    CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET {ima_col} = "{znach}" WHERE Пномер = {pnom}""")
    CMS.dict_rab_mesta(self, self.db_users)

def load_deficit_emploee(self):
    rez = [['Пномер_РМ', 'Расположение', 'Прозвище', 'Профессия', 'Смена']]
    dict_rez_itog = dict()
    dict_rez_all = dict()

    custom_request_c = """SELECT rm.Пномер,
                                   pc.adress as Расположение,
                                   rm.Прозвище,
                                   pr.имя as Профессия,
                                   swp.shift_no as Смена,
                                   swp.employee_id as employee_id
                            FROM rab_mesta rm
                            LEFT JOIN professions pr ON pr.код == rm.Код_профессии
                            LEFT JOIN places_capacity pc ON pc.serial == rm.Расположение
                            LEFT JOIN schedule_work_places swp ON swp.workplace_id == rm.Пномер
                         """
    spis = CSQ.custom_request_c(self.db_users, custom_request_c, rez_dict=True, hat_c=False) or []

    for item in spis:
        prof = item.get('Профессия') or ''
        emp = item.get('employee_id')
        shift = item.get('Смена')
        if shift is None:
            continue

        if emp == 1:
            rez.append([item.get('Пномер'), item.get('Расположение'), item.get('Прозвище'), prof, str(shift)])
            dict_rez_itog[prof] = dict_rez_itog.get(prof, 0) + 1

        if emp not in (None, 1, 2, 838):
            dict_rez_all[prof] = dict_rez_all.get(prof, 0) + 1

    rez.append(['====' for _ in rez[0]])
    rez.append(['====' for _ in rez[0]])

    for key in dict_rez_itog.keys():
        rez.append([key, dict_rez_itog[key], dict_rez_all.get(key, 0)])
    CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_vacant, isp_hat_c=True, separ='')
    CMS.fill_filtr_c(self, self.ui.tbl_vacant_filtr, self.ui.tbl_vacant)

def load_emploee(self, *args):
    custom_request_c = """SELECT Пномер, ФИО, Статус,Подразделение, Должность, Режим
                            FROM employee WHERE Статус != 'Увольнение' ORDER BY ФИО"""
    spis_empl = CSQ.custom_request_c(self.db_users, custom_request_c, hat_c=True)

    req_rm = """SELECT workplace_id, employee_id
                  FROM schedule_work_places
                  WHERE employee_id IS NOT NULL AND employee_id NOT IN (1,2,838)"""
    spis_rm = CSQ.custom_request_c(self.db_users, req_rm, hat_c=False)
    map_emp_rm = {}
    for w_id, e_id in spis_rm:
        map_emp_rm.setdefault(int(e_id), set()).add(int(w_id))

    nk_pnom = F.num_col_by_name_in_hat_c(spis_empl, 'Пномер')
    spis_empl[0].append('Номер_РМ')

    for r in range(1, len(spis_empl)):
        pnom_emp = int(spis_empl[r][nk_pnom])
        rms = sorted(list(map_emp_rm.get(pnom_emp, set())))
        spis_empl[r].append(','.join([str(x) for x in rms]))

    CQT.fill_wtabl_old_c(self, spis_empl, self.ui.tbl_emploee, isp_hat_c=True, separ='')
    CMS.fill_filtr_c(self,self.ui.tbl_emploee_filtr,self.ui.tbl_emploee)
    return

def zagruzka_rc(self, *args):
    sp_pnom = CSQ.custom_request_c(self.db_users, """SELECT Пномер FROM rab_mesta""") or []
    for (pnom,) in sp_pnom:
        try:
            ensure_workplace_shifts(self, int(pnom))
        except:
            pass

    custom_request_c = """SELECT rm.Пномер,
                                   pc.adress AS Расположение,
                                   rc.Имя AS РЦ,
                                   rm.Прозвище,
                                   eq.Наименование || ' ' || eq.Инв_номер AS Оборудование,
                                   pr.имя AS Профессия_рм,
                                   rc.Отв_мастер_тдз AS Руководитель,

                                   COALESCE(e1.Должность, '') AS Должность_1см,
                                   COALESCE(e1.ФИО, '') AS ФИО_1см,
                                   COALESCE(sw1.employee_id, 1) AS Пномер_emp1,
                                   COALESCE(sw1.time_start, '07:00') AS Время_начала_1,
                                   COALESCE(sw1.time_end,   '15:30') AS Время_конца_1,
                                   COALESCE(sw1.Нераб_мин, 75) AS Нераб_мин1,
                                   COALESCE(sw1.Между_нар_мин, 40) AS Между_нар_мин1,
                                   COALESCE(sw1.Коэфф_производит, 1) AS Коэфф_производит1,

                                   COALESCE(e2.Должность, '') AS Должность_2см,
                                   COALESCE(e2.ФИО, '') AS ФИО_2см,
                                   COALESCE(sw2.employee_id, 1) AS Пномер_emp2,
                                   COALESCE(sw2.time_start, '15:30') AS Время_начала_2,
                                   COALESCE(sw2.time_end,   '23:59') AS Время_конца_2,
                                   COALESCE(sw2.Нераб_мин, 75) AS Нераб_мин2,
                                   COALESCE(sw2.Между_нар_мин, 40) AS Между_нар_мин2,
                                   COALESCE(sw2.Коэфф_производит, 0.9) AS Коэфф_производит2,

                                   COALESCE(e3.Должность, '') AS Должность_3см,
                                   COALESCE(e3.ФИО, '') AS ФИО_3см,
                                   COALESCE(sw3.employee_id, 1) AS Пномер_emp3,
                                   COALESCE(sw3.time_start, '00:01') AS Время_начала_3,
                                   COALESCE(sw3.time_end,   '07:00') AS Время_конца_3,
                                   COALESCE(sw3.Нераб_мин, 75) AS Нераб_мин3,
                                   COALESCE(sw3.Между_нар_мин, 40) AS Между_нар_мин3,
                                   COALESCE(sw3.Коэфф_производит, 0.8) AS Коэфф_производит3,

                                   rm.Примечание,
                                   rm.coord
                            FROM rab_mesta rm
                            LEFT JOIN places_capacity pc ON pc.serial == rm.Расположение
                            LEFT JOIN rab_c rc ON rc.Код == rm.Код_РЦ
                            LEFT JOIN equipment eq ON eq.Пномер == rm.Номер_осн_оборуд
                            LEFT JOIN professions pr ON pr.код == rm.Код_профессии

                            LEFT JOIN schedule_work_places sw1 ON sw1.workplace_id == rm.Пномер AND sw1.shift_no == 1
                            LEFT JOIN schedule_work_places sw2 ON sw2.workplace_id == rm.Пномер AND sw2.shift_no == 2
                            LEFT JOIN schedule_work_places sw3 ON sw3.workplace_id == rm.Пномер AND sw3.shift_no == 3
                            LEFT JOIN employee e1 ON e1.Пномер == sw1.employee_id
                            LEFT JOIN employee e2 ON e2.Пномер == sw2.employee_id
                            LEFT JOIN employee e3 ON e3.Пномер == sw3.employee_id
                            ORDER BY rm.Пномер"""

    spis = CSQ.custom_request_c(self.db_users, custom_request_c, hat_c=False, rez_dict=True) or []
    spis_fio_uvol_emploee = CSQ.custom_request_c(self.db_users, """SELECT ФИО, Пномер FROM employee WHERE Статус == 'Увольнение' """)
    for i in range(len(spis)):
        if [spis[i].get('ФИО_1см', ''), spis[i].get('Пномер_emp1', '')] in spis_fio_uvol_emploee:
            spis[i]['ФИО_1см'] = (spis[i].get('ФИО_1см', '') + ' УВОЛЕН').strip()
        if [spis[i].get('ФИО_2см', ''), spis[i].get('Пномер_emp2', '')] in spis_fio_uvol_emploee:
            spis[i]['ФИО_2см'] = (spis[i].get('ФИО_2см', '') + ' УВОЛЕН').strip()
        if [spis[i].get('ФИО_3см', ''), spis[i].get('Пномер_emp3', '')] in spis_fio_uvol_emploee:
            spis[i]['ФИО_3см'] = (spis[i].get('ФИО_3см', '') + ' УВОЛЕН').strip()

    for row in spis:
        for k, v in list(row.items()):
            if v is None:
                row[k] = ''
        set_edit = {
            'Прозвище',
            'Примечание',
            'Время_начала_1', 'Время_конца_1', 'Нераб_мин1', 'Между_нар_мин1', 'Коэфф_производит1',
            'Время_начала_2', 'Время_конца_2', 'Нераб_мин2', 'Между_нар_мин2', 'Коэфф_производит2',
            'Время_начала_3', 'Время_конца_3', 'Нераб_мин3', 'Между_нар_мин3', 'Коэфф_производит3',
            'coord'
        }

    CQT.fill_wtabl_old_c(self, spis, self.ui.tbl_rc, separ='', isp_hat_c=True, set_editeble_col_nomera=set_edit)
    self.ui.tbl_rc.setToolTip('"|_|" вакант = нет     "-" не нужен = нет     "+" не нужен = есть')

    spis_rasp = CSQ.custom_request_c(self.db_users, """SELECT adress FROM places_capacity""", hat_c=False, one_column=True)
    spis_rc = CSQ.custom_request_c(self.db_users, """SELECT Имя FROM rab_c""", hat_c=False, one_column=True)
    spis_oborud = CSQ.custom_request_c(self.db_users, """SELECT Наименование || ' ' || Инв_номер FROM equipment""", hat_c=False, one_column=True)
    spis_prof = CSQ.custom_request_c(self.db_users, """SELECT имя FROM professions""", hat_c=False, one_column=True)
    spis_dolgn = CSQ.custom_request_c(self.db_users, """SELECT DISTINCT Должность FROM employee WHERE Статус != 'Увольнение' """, hat_c=False, one_column=True)
    spis_dolgn = sorted(spis_dolgn)

    self.ui.tbl_rc.blockSignals(True)

    nk_dolg1 = CQT.num_col_by_name_c(self.ui.tbl_rc,'Должность_1см')
    nk_dolg2 = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Должность_2см')
    nk_dolg3 = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Должность_3см')
    nk_raspolog = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Расположение')
    nk_rc = CQT.num_col_by_name_c(self.ui.tbl_rc, 'РЦ')
    nk_oborud = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Оборудование')
    nk_prof = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Профессия_рм')
    # nk_boss = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Руководитель')

    for i in range(self.ui.tbl_rc.rowCount()):

        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_raspolog, spis_rasp, False, select_rasp)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_rc, spis_rc, False, select_rc)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_oborud, spis_oborud, False, select_oborud)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_prof, spis_prof, False, select_prof)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_dolg1, spis_dolgn, False, select_prof_emploee)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_dolg2, spis_dolgn, False, select_prof_emploee)
        CQT.add_combobox(self, self.ui.tbl_rc, i, nk_dolg3, spis_dolgn, False, select_prof_emploee)
    self.ui.tbl_rc.blockSignals(False)


    CQT.color_cell_wtable_c(self.ui.tbl_rc, 'ФИО_1см', 'УВОЛЕН', r=110)
    CQT.color_cell_wtable_c(self.ui.tbl_rc, 'ФИО_2см', 'УВОЛЕН', r=110)
    CQT.color_cell_wtable_c(self.ui.tbl_rc, 'ФИО_3см', 'УВОЛЕН', r=110)

    CMS.fill_filtr_c(self, self.ui.tbl_rc_filtr, self.ui.tbl_rc)

def add_rm(self):
    if CMS.user_access(self.bd_naryad, 'rab_mesta_edit', F.user_name()) == False:
        return

    raspol = 0
    kod_rc = "010101"
    prozv = ""
    oborud = 1
    prof = "10371"
    note = ''

    shifts = deepcopy(DEFAULT_SHIFT_SETTINGS)

    mods = QtWidgets.QApplication.keyboardModifiers()
    if (mods & Qt.ShiftModifier) == Qt.ShiftModifier:
        if self.ui.tbl_rc.rowCount() == 0:
            CQT.msgbox('Нет данных для копирования')
            return
        nom_rm = self.ui.tbl_rc.item(self.ui.tbl_rc.currentRow(), CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')).text()
        if nom_rm == '':
            return


        spis = CSQ.custom_request_c(
            self.db_users,
            f"""SELECT Расположение,
                        Код_РЦ as РЦ_код,
                        Прозвище,
                        Номер_осн_оборуд as Оборудование,
                        Код_профессии as Профессия_рм,
                        Примечание
                 FROM rab_mesta WHERE Пномер = {int(nom_rm)}""",
            hat_c=True,
            rez_dict=True
        )[0]
        raspol = spis.get('Расположение', raspol)
        kod_rc = spis.get('РЦ_код', kod_rc)
        prozv = spis.get('Прозвище', prozv)
        oborud = spis.get('Оборудование', oborud)
        prof = spis.get('Профессия_рм', prof)
        note = spis.get('Примечание', note)

        ensure_workplace_shifts(self, int(nom_rm))
        for s in (1, 2, 3):
            row = CSQ.custom_request_c(
                self.db_users,
                f"""SELECT time_start, time_end, Нераб_мин, Между_нар_мин, Коэфф_производит
                      FROM schedule_work_places
                      WHERE workplace_id = {int(nom_rm)} AND shift_no = {s}""",
            )
            if row:
                shifts[s] = {
                    'time_start': row[-1][0] or shifts[s]['time_start'],
                    'time_end': row[-1][1] or shifts[s]['time_end'],
                    'Нераб_мин': row[-1][2] if row[-1][2] is not None else shifts[s]['Нераб_мин'],
                    'Между_нар_мин': row[-1][3] if row[-1][3] is not None else shifts[s]['Между_нар_мин'],
                    'Коэфф_производит': row[-1][4] if row[-1][4] is not None else shifts[s]['Коэфф_производит'],
                }

        CSQ.custom_request_c(
            self.db_users,
            f"""INSERT INTO rab_mesta (Расположение, Код_РЦ, Прозвище, Номер_осн_оборуд, Код_профессии, Примечание)
                  VALUES ({int(raspol)}, '{kod_rc}', '{prozv}', {int(oborud)}, '{prof}', '{note}');""",
        )
        new_rm = CSQ.custom_request_c(self.db_users, """SELECT MAX(Пномер) FROM rab_mesta""")[-1][0]

        for s in (1, 2, 3):
            d = shifts[s]
            CSQ.custom_request_c(
                self.db_users,
                f"""INSERT INTO schedule_work_places
                      (workplace_id, employee_id, shift_no, time_start, time_end, Нераб_мин, Между_нар_мин, Коэфф_производит)
                      VALUES ({int(new_rm)}, 1, {s}, '{d['time_start']}', '{d['time_end']}', {int(d['Нераб_мин'])},
                              {int(d['Между_нар_мин'])}, {float(d['Коэфф_производит'])});""",
            )

        CQT.msgbox('Создано новое РМ (скопированы базовые поля и настройки смен, сотрудники не копировались)')
        zagruzka_rc(self)
        CMS.dict_rab_mesta(self, self.db_users)
        return

    CSQ.custom_request_c(
        self.db_users,
        f"""INSERT INTO rab_mesta (Расположение, Код_РЦ, Прозвище, Номер_осн_оборуд, Код_профессии, Примечание)
              VALUES ({int(raspol)}, '{kod_rc}', '{prozv}', {int(oborud)}, '{prof}', '{note}');""",
    )
    new_rm = CSQ.custom_request_c(self.db_users, """SELECT MAX(Пномер) FROM rab_mesta""")[-1][0]

    for s in (1, 2, 3):
        d = shifts[s]
        CSQ.custom_request_c(
            self.db_users,
            f"""INSERT INTO schedule_work_places
                  (workplace_id, employee_id, shift_no, time_start, time_end, Нераб_мин, Между_нар_мин, Коэфф_производит)
                  VALUES ({int(new_rm)}, 1, {s}, '{d['time_start']}', '{d['time_end']}', {int(d['Нераб_мин'])},
                          {int(d['Между_нар_мин'])}, {float(d['Коэфф_производит'])});""",
        )
    CQT.msgbox('Создано новое РМ')
    zagruzka_rc(self)
    CMS.dict_rab_mesta(self, self.db_users)

def select_prof(self, text,  row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())
    rez = CSQ.custom_request_c(self.db_users,f"""SELECT код FROM professions WHERE имя == '{text}'""")
    kod_prof = rez[-1][0]
    response = CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET Код_профессии = "{kod_prof}" WHERE Пномер = {pnom}""", hat_c=False)
    CQT.msgbox('Успешно') if response else CQT.msgbox('Не удалось обновить профессию на рм')

def select_oborud(self, text,  row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())
    rez = CSQ.custom_request_c(self.db_users,f"""SELECT Пномер FROM equipment WHERE Наименование || ' ' || Инв_номер == '{text}'""")
    kod_oborud = rez[-1][0]
    response = CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET Номер_осн_оборуд = "{kod_oborud}" WHERE Пномер = {pnom}""", hat_c=False)
    CQT.msgbox('Успешно') if response else CQT.msgbox('Не удалось обновить оборудование на рм')


def select_rc(self, text,  row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())
    rez = CSQ.custom_request_c(self.db_users,f"""SELECT Код FROM rab_c WHERE Имя == '{text}'""")
    kod_rc = rez[-1][0]
    response = CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET Код_РЦ = "{kod_rc}" WHERE Пномер = {pnom}""", hat_c=False)
    CQT.msgbox('Успешно') if response else CQT.msgbox('Не удалось обновить РЦ на рм')

def select_rasp(self, text,  row, col):
    if CMS.user_access(self.bd_naryad,'rab_mesta_edit',F.user_name()) == False:
        return
    nk_pnom = CQT.num_col_by_name_c(self.ui.tbl_rc, 'Пномер')
    pnom = int(self.ui.tbl_rc.item(row, nk_pnom).text())
    rez = CSQ.custom_request_c(self.db_users, f"""SELECT serial FROM places_capacity WHERE adress == '{text}'""")
    kod_place = rez[-1][0]
    response = CSQ.custom_request_c(self.db_users, f"""UPDATE rab_mesta SET Расположение = {kod_place} WHERE Пномер = {pnom}""", hat_c=False)
    CQT.msgbox('Успешно') if response else CQT.msgbox('Не удалось обновить Расположение на рм')


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


def select_fio(self, txt_cmb,  row, col):
    if CMS.user_access(self.bd_naryad, 'rab_mesta_edit', F.user_name()) == False:
        return
    tbl = self.ui.tbl_rc
    header = tbl.horizontalHeaderItem(col).text()
    if header == 'ФИО_1см':
        shift_no = 1
    elif header == 'ФИО_2см':
        shift_no = 2
    elif header == 'ФИО_3см':
        shift_no = 3
    else:
        return

    nk_pnom = CQT.num_col_by_name_c(tbl, 'Пномер')
    pnom_rm = int(tbl.item(row, nk_pnom).text())
    fio, podr, rej = txt_cmb.split('$')

    if fio in self.DICT_EMPLOEE_FULL:
        pk_employee = self.DICT_EMPLOEE_FULL[fio]['Пномер']
    else:
        return CQT.msgbox(f'Ошибка! {fio} не найден')
    ensure_workplace_shifts(self, pnom_rm)
    result = CSQ.custom_request_c(
        self.db_users,
        f"""UPDATE schedule_work_places
              SET employee_id = ?
              WHERE workplace_id = ? AND shift_no = ?""",
        list_of_lists_c=[[pk_employee, pnom_rm, shift_no]]
    )
    CQT.msgbox('Успешно') if result else CQT.msgbox('Не удалось установить пользователя на рм')
    CMS.dict_rab_mesta(self, self.db_users)

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


def get_workers(default_val = None): #27.01.2026
    company = CFG.Config.place.Имя
    return CSQ.custom_request_c(
        CFG.Config.project.db_users,
        f"""
        SELECT 
            employee.gender AS Пол,
            employee.ФИО,
            employee.ID_ФизЛица AS sys_employee_phys_ref,
            employee.Должность,
            employee.Подразделение,
            GROUP_CONCAT(sb.schedule, ', ') AS "Текущее расписание перерывов"
        FROM employee
             LEFT JOIN schedule_break sb ON sb.employee_phys_ref = employee.ID_ФизЛица
        WHERE employee.Статус = 'Работа'
            AND employee.Компания = {company!r}
            AND employee.Должность IN (SELECT DISTINCT имя FROM professions)
        GROUP BY employee.ID_ФизЛица""",
        rez_dict=True,
        attach_dbs=CFG.Config.project.db_naryad
    ) or default_val

def gen_hour_breaks(start_hour: int, phys_refs):
    result = []
    str_refs = ','.join(repr(ref) for ref in phys_refs)
    schedules = CSQ.custom_request_c(
        CFG.Config.project.db_users,
        f"""
        SELECT 
            period,
            GROUP_CONCAT(DISTINCT schedule ORDER BY schedule) AS schedule,
            GROUP_CONCAT(DISTINCT error_margin) AS error_margin,
            GROUP_CONCAT(DISTINCT comment) AS comment
        FROM schedule_break
        WHERE employee_phys_ref IN ({str_refs})
        GROUP BY period
""",
        rez_dict=True,
        attach_dbs=CFG.Config.project.db_naryad
    ) or {}
    schedule_by_period = F.deploy_dict_c(schedules, 'period')

    for i in range(24):
        h1 = (start_hour + i) % 24
        h2 = (h1 + 1) % 24
        interval = f"{h1:02d}:00-{h2:02d}:00"
        item = schedule_by_period.get(interval, {})
        schedule = item.get('schedule', "")
        error_margin = item.get('error_margin', "")
        comment = item.get('comment', "")
        result.append({"Перерыв\nв промежутке": interval, "Время перерыва": schedule, "Погрешность(мин)": error_margin, "Примечание": comment})
    return result

def apply_autoschedule_filter(self):
    tbl = self.ui.tbl_rc_autopause
    tblf = self.ui.tbl_rc_autopause_filtr
    CMS.apply_filtr_c(self, tblf, tbl)
    label_counter: QtWidgets.QLabel = self.ui.label_11
    label_info: QtWidgets.QLabel = self.ui.label_12
    count = sum(1 for num in range(tbl.rowCount()) if not tbl.isRowHidden(num))
    label_counter.setText(f'Выбрано: {count} строк по фильтру')
    label_info.setText(f'Применить расписание для выбранных строк')

def validate_time(start, finish, target):
    try:
        start_date = datetime.datetime.strptime(start, '%H:%M')
        finish_date = datetime.datetime.strptime(finish, '%H:%M')
        from_date = datetime.datetime.strptime(target['time_from'], '%H:%M')
        to_date = datetime.datetime.strptime(target['time_to'], '%H:%M')
        if from_date == to_date:
            CQT.msgbox('Дата начала и финиша не могут совпадать')
            return False, False
        if (from_date < start_date or from_date > finish_date) or (to_date < start_date or to_date > finish_date):
            CQT.msgbox(f'Дата выходит за рамки периода "{start}-{finish}"')
            return False, False
        return target, True
    except Exception as e:
        print(e)
    return False, False

def clear_break_line(self, row, col, window, *args):
    tbl_emp = window.ui.tbl_rc_autopause
    tbl_time = window.ui.tbl_rc_autopause_2
    col_base_time = CQT.num_col_by_name_c(tbl_time, "Перерыв\nв промежутке")
    if col_base_time is None: return
    lst = CQT.list_from_wtabl_c(tbl_emp, rez_dict=True, only_visible=True)
    item = tbl_time.item(row, col_base_time)
    result = set()
    if item is None:
        return
    period = item.text()
    if CQT.msgboxgYN(f'Перерывы в периоде: {period!r} будут очищены у {len(lst)} сотрудников. Продолжить?'):
        self.set_text("")
        for emp in lst:
            ref = emp['sys_employee_phys_ref']
            result.add(CSQ.custom_request_c(
                CFG.Config.project.db_users,
                'DELETE FROM schedule_break WHERE employee_phys_ref = ? AND period = ?',
                list_of_lists_c=[ref, period]
            ))
    if len(result) and all(result):
        return CQT.msgbox('Успешно')
    load_breaks_tab(window)


def autopause_change_hour(self: CQT.InteractiveLabelInstance, row, column, window, *args, **kwargs):
    try:
        table_widget: QtWidgets.QTableWidget = window.ui.tbl_rc_autopause_2
        old_schedule = self.full_text
        col_base_time = CQT.num_col_by_name_c(table_widget, "Перерыв\nв промежутке")
        col_comment = CQT.num_col_by_name_c(table_widget, "Примечание")
        item = table_widget.item(row, col_base_time)
        comment = table_widget.item(row, col_comment).text()
        if not item:
            return
        period = item.text()
        start, finish = period.split('-')
        if not old_schedule:
            old_schedule = start
        ok, new_schedule = CQT.get_time_dialog_choose(
            self.parent(),
            "Выберите время",
            func_validate=lambda result: validate_time(start, finish, result),
            start_time=start, finish_time=start.replace('00', '15'), format_time="%H:%M",
            range_times=True
        )
        if ok:
            new_lbl = '%s-%s' % (new_schedule['time_from'], new_schedule['time_to'])
            self.set_text(new_lbl)
            is_done = apply_break_changes(self, window, old_schedule, new_lbl, period, comment)
            is_done and CQT.msgbox('Успешно применено')
    except Exception as e:
        print(e)
    load_breaks_tab(window)

def on_autopause_table_changed(self, row, col, *args):
    tbl = self.sender()
    insert_body = []

    margin_column = CQT.num_col_by_name_c(tbl, "Погрешность(мин)")
    comment_column = CQT.num_col_by_name_c(tbl, "Примечание")
    period_column = CQT.num_col_by_name_c(tbl, "Перерыв\nв промежутке")
    if margin_column is None: return
    margin_item_cell = tbl.item(row, margin_column)
    period_item_cell = tbl.item(row, period_column)
    comment_item_cell = tbl.item(row, comment_column)
    if margin_item_cell is None or period_item_cell is None: return

    current_margin = margin_item_cell.text()
    current_period = period_item_cell.text()
    current_comment = comment_item_cell.text()
    worker_table_widget = self.ui.tbl_rc_autopause
    workers = CQT.list_from_wtabl_c(worker_table_widget, rez_dict=True, only_visible=True)
    if col == margin_column:

        is_confirm = CQT.msgboxg_get_table(
            self,
            f"Для данных работников будет разрешена {current_margin} мин\nпогрешность выхода на перерыв. Подтвердить?",
            [{'ФИО': worker['ФИО'], 'Должность': worker['Должность'], 'Подразделение': worker['Подразделение']} for worker in workers],
            btn0_name='Подтвердить',
            btn1_name='Отмена',
            yesNoMode=True,
        )
        if not is_confirm:
            load_breaks_tab(self)
            return
        for worker in workers:
            insert_body.append([current_margin, worker['sys_employee_phys_ref'], current_period])
        CSQ.custom_request_c(
            CFG.Config.project.db_users,
            'UPDATE schedule_break SET error_margin = ? WHERE employee_phys_ref = ? AND period = ?',
            list_of_lists_c=insert_body
        )
    if col == comment_column:
        for worker in workers:
            insert_body.append([current_comment, worker['sys_employee_phys_ref'], current_period])
        CSQ.custom_request_c(
            CFG.Config.project.db_users,
            'UPDATE schedule_break SET comment = ? WHERE employee_phys_ref = ? AND period = ?',
            list_of_lists_c=insert_body
        )
    load_breaks_tab(self)


def apply_break_changes(int_label, window, old_schedule, new_schedule, period, comment):
    worker_table_widget = window.ui.tbl_rc_autopause
    workers = CQT.list_from_wtabl_c(worker_table_widget, rez_dict=True, only_visible=True)

    if not workers:
        return
    refs = ','.join(repr(worker['sys_employee_phys_ref']) for worker in workers if isinstance(worker['sys_employee_phys_ref'], str))
    res = CSQ.custom_request_c(
        CFG.Config.project.db_users,
        f"""
        SELECT 
            employee.ID_ФизЛица,
            employee.ФИО,
            employee.Должность,
            employee.Подразделение,
            sb.period,
            sb.schedule
        FROM employee
             LEFT JOIN schedule_break sb ON sb.employee_phys_ref = employee.ID_ФизЛица
        WHERE employee.Статус = 'Работа'
          AND sb.period = {period!r}
          AND employee.ID_ФизЛица IN ({refs})""",
        rez_dict=True
    )
    if not isinstance(res, list):
        return
    existing = []
    for item in res:
        period = item['period']
        old_user_val = item['schedule']
        if None in (period, old_user_val):
            continue
        if old_user_val != new_schedule:
            existing.append({
                    'Период': period,
                    'ФИО': item['ФИО'],
                    'Должность': item['Должность'],
                    'Подразделение': item['Подразделение'],
                    'Было': old_user_val,
                    'Стало': new_schedule
                }
            )
    if existing:
        is_confirm = CQT.msgboxg_get_table(
            window,
            'У данных работников уже заданно расписание. Вы уверены что хотите заменить?',
            existing,
            btn0_name='Подтвердить',
            btn1_name='Отмена',
            show_filtr=False,
            yesNoMode=True
        )
    else:
        is_confirm = True
    if not is_confirm:
        int_label.set_text("")
        return
    is_done = set()
    for worker in workers:
        ref = worker['sys_employee_phys_ref']
        is_done.add(CSQ.custom_request_c(
            CFG.Config.project.db_users,
            """
                INSERT OR REPLACE INTO schedule_break(period, schedule, employee_phys_ref, comment)
                VALUES (?, ?, ?, ?)
            """,
            list_of_lists_c=[[period, new_schedule, ref, comment]]
        ))
    return all(is_done)


def load_breaks_tab(self):
    tbl_workers = self.ui.tbl_rc_autopause # type: QtWidgets.QTableWidget
    tblf_workers = self.ui.tbl_rc_autopause_filtr
    tbl_schedule = self.ui.tbl_rc_autopause_2
    tblf_schedule = self.ui.tbl_rc_autopause_filtr_2

    workers = get_workers([])
    CQT.fill_wtabl(workers, tbl_workers, auto_type=False)
    for col in range(tbl_workers.columnCount()):
        header = tbl_workers.horizontalHeaderItem(col).text()
        if header.startswith('sys_'):
            tbl_workers.hideColumn(col)

    CMS.fill_filtr_c(self, tblf_workers, tbl_workers)
    current_workers = CQT.list_from_wtabl_c(tbl_workers, only_visible=True, rez_dict=True, only_visible_columns=False)
    worker_refs = [worker['sys_employee_phys_ref'] for worker in current_workers]

    apply_autoschedule_filter(self)

    lst_hours = gen_hour_breaks(start_hour=6, phys_refs=worker_refs)

    CQT.fill_wtabl(lst_hours, tbl_schedule, set_editeble_col_nomera={'Погрешность(мин)', 'Примечание'})
    col_schedule: QtWidgets.QTableWidget = CQT.num_col_by_name_c(tbl_schedule, "Время перерыва")
    tbl_schedule.blockSignals(True)
    for row_index in range(tbl_schedule.rowCount()):
        label_schedule = CQT.add_interactive_label(tbl_schedule, row_index, col_schedule, min_label_px=200)
        label_schedule.add_button('🕒', on_clicked=autopause_change_hour, cell_val=self)
        label_schedule.add_button('❌', on_clicked=clear_break_line, cell_val=self)
    tbl_schedule.blockSignals(False)
    CMS.fill_filtr_c(self, tblf_schedule, tbl_schedule)
    return
