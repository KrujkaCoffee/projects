from __future__ import annotations

import os
import pickle
import pprint
from collections import defaultdict

import project_cust_38.Cust_Functions as F
import project_cust_38.Zamechaniya as ZMCH
from PyQt5 import QtCore
from PyQt5.QtWidgets import QVBoxLayout, QApplication, QTableWidget

try:
    from PyQt5 import QtWebEngineWidgets
except:
    print(f'PyQt5 не подгружен QtWebEngineWidgets')
    pass

import project_cust_38.Cust_Excel as CEX
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
from datetime import datetime as DT, timedelta, time
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
# from project_cust_38.Cust_virbotka import koeff_double_pay_holydays as koeff_holy, calc_month_rates_c
import project_cust_38.xml_v_drevo as XML
import project_cust_38.Cust_odata_erp as ODAT
import project_cust_38.Cust_perko as SCUD
import project_cust_38.Cust_config as USRCNF
import project_cust_38.competence_matrix as MTXCMP
import project_cust_38.Cust_emoji as CEMOJ
from functools import partial
try:
    import reports_of_personal as RPTP
except:
    pass
try:
    import project_cust_38.Cust_b24 as СB24
except:
    print(f'!!! ERROR IMPORT  MODULE Cust_b24')
try:
    import plotly.graph_objects as go
except:
    print(f'!!! ERROR IMPORT  MODULE plotly')


    

try:
    from project_cust_38.Cust_virbotka import koeff_double_pay_holydays, calc_month_rates_c
except:
    pass
import copy
from dateutil.relativedelta import relativedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Viewer import mywindow

KOEF_NEDEL_OTH = 1 - 0.26
PROIZVODITELNOST_POST_SM = 121
KOEF_VNEPLANA = 1  # 0.7
minut_smen = 450
KOEF_RASKLADKI = 1  # 1/(2.32 * 0.4584)
KOEF_EFF_VREM = 0.8
KOEF_NORMIROVSCHICI = 1 / 1.15

DICT_VID_OTCH = {'': "",
                 'Исполнение плана месяца': '',
                 'Выполнение проектов находящихся в производстве без привязке к периоду':'Задача № 100046611 Моренко',
                 'Распределение работ по направлениям': 'Для МХ',
                 'Отклонения от плановых дат по проектам': "Для совещания",
                 'Усредненная удельная трудоемкость сборки по видам': "Для совещания",
                 'Внеплановые работы по направлениям': "Для совещания",
                 'План-фактный график по месяцам': "Для совещания",
                 'График удельной производительности сборочного цеха': "Для совещания",
                 '---------------------------------------------------':'',
                 'Не выгруженные в 1С наряды':"для сборочного к примеру, допустим оператор выгружает 25.12 а там есть работники с не подтвержденными нарядами (к примеру таких 10 нарядов), и чтоб это не сидеть и не переписывать, а так спустя там день другой, зайти и посмотреть и видеть что тому то тому не выгружены тз",
                 'Трудозатраты': "Сверка для выгрузки трудозатрат в ЕРП",
                'Отчет по отклонениям табеля и трудозатрат':'Для оператора производственного учета',
                '--------------------------------------------------':'',
                'Журнал работ': "",
                'Текущие работы': "",
                 'Выработка сотрудника': "",
                 'Выработка сотрудников': "",
                 'Отчетность персонала': "",
                 '-------------------------------------------------': '',
                 'Динамика производительности сотрудников': "Задача № 100045854 от  13.11.2024 13:06",
                 'Понедельный график выработки и отгрузок': "",
                 'Выработка цеха понарядно': "",
                 'Статистика нормо-весовых харктеристик МК': "",
                 'Селекторное': "",
                 'Отчет для селектора': "по ТЗ Моренко от 03.03.2025",
                 'Выработка цеха по направлению': "",
                 'Внеплановые работы': "",
                 'Матрицы компетенций': "по ТЗ  100060096 от 24.11.2025",
                 '-------------------------------------------------': '',
                 'Неосвоенный_вес_по_созданным_нарядам': "",
                 'Норматив материалов по завершенным нарядам': "",
                 'Сравнение норм времени по направлениям': "",
                 'Журнал_техкарт': "",
                 'Выработка_ТОП': "",
                 'Журнал_замечаний': "",
                 'Журнал замечаний динамика': "Для совещания",
                 'Реестр проектов в работе': "по ТЗ от ГД 25.01.2024",
                 'Анализ эффективности работ на минуту': 'по ТЗ от ГД 30.05.2024',
                 'Анализ внеплана по видам работ': 'по ТЗ от ГД 04.06.2024',
                 'ПланФакт наряды с внепланом': 'по ТЗ от Р 06.06.2024',
                 'О выработке сотрудников за месяц': "Отчет для ФЭО",
                 'Отчет по загрузке оборудования': 'по ТЗ от П 09.2024',
                 'Отчет по проекту': 'по ТЗ от CC 13.02.2025',
                 'Компоновщик': ''
                 }
@CQT.onerror
def get_list_month_fact(self: mywindow):
    self.list_month_fact = CSQ.custom_request_c(self.bd_naryad, f"""SELECT mk.Направление, 
    mk.Вес,mk.Дата_завершения,mk.xml, zagot.Вес_по_рес FROM mk 
    LEFT JOIN plan 
             ON plan.Пномер = mk.НомКплан 
    LEFT JOIN zagot ON zagot.Ном_МК == mk.Пномер          
             WHERE Дата_завершения != '' and plan.poki == {self.place.poki} """,
                                                rez_dict=True, attach_dbs=self.db_kplan)

def _______SELECT_SUB_TYPE_REPORT_____________():
    pass

@CQT.onerror
def vibor_additional_sort_report(self: mywindow, *args):
    def fill_cmb_addit_sort_c_report_by_podr(self,podr):
        set_users_empl_all = {_ for _ in self.DICT_EMPLOEE_FULL_WITH_DEL if
                     self.DICT_EMPLOEE_FULL_WITH_DEL[_]['Подразделение'] == podr and
                              self.DICT_EMPLOEE_FULL_WITH_DEL[_]['Компания'] == USRCNF.Config.place.Имя} #28.01.2026
        set_users_empl = {_ for _ in self.DICT_EMPLOEE_FULL if
                     self.DICT_EMPLOEE_FULL[_]['Подразделение'] == podr and
                              self.DICT_EMPLOEE_FULL_WITH_DEL[_]['Компания'] == USRCNF.Config.place.Имя}

        
        self.ui.cmb_addit_sort_c_report.clear()
        data_nach = self.ui.le_start_of_period.text()
        data_kon = self.ui.le_end_of_period.text()
        poki = USRCNF.Config.place.poki
        custom_request_c = f"""SELECT distinct jurnal.ФИО AS "ФИО_журнал" FROM jurnal 
                            INNER JOIN naryad ON naryad.Пномер = jurnal.Номер_наряда
                            INNER JOIN коды_веплана_для_наряда ON коды_веплана_для_наряда.code = naryad.Внеплан
                            WHERE datetime(jurnal.Дата) >= datetime("{data_nach}") 
                            and datetime(jurnal.Дата) <= datetime("{data_kon}") 
                            AND коды_веплана_для_наряда.poki = {poki} """ #28.01.2026 по задаче 100065789
        rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=False, one_column=True)
        set_users = {_ for _ in rez_jur if _ in set_users_empl_all}
        list_users = list(set_users.union(set_users_empl))
        
        list_users.sort()
        list_users.insert(0, '')
        self.ui.cmb_addit_sort_c_report.setEnabled(True)
        self.ui.cmb_addit_sort_c_report.clear()
        self.ui.cmb_addit_sort_c_report.addItems(list_users)

    vid = self.ui.cmb_sort_c_report.currentText()
    if vid == 'Выработка сотрудника':
        podr = self.ui.cmb_podrazdelenie.currentText()
        if podr == '':
            return
        fill_cmb_addit_sort_c_report_by_podr(self,podr)
        self.ui.cmb_addit_sort_c_report.setEnabled(True) #08.07.25
    if vid == 'Динамика производительности сотрудников':
        podr = self.ui.cmb_podrazdelenie.currentText()
        if podr == '':
            return
        fill_cmb_addit_sort_c_report_by_podr(self,podr)

    if vid == 'Отчетность персонала':
        type_rep = self.ui.cmb_podrazdelenie.currentText()
        if type_rep == '':
            return
        if 'Отчет' in type_rep:
            self.ui.cmb_addit_sort_c_report.setEnabled(True)
            RPTP.fill_cmb_users_with_rules(self.ui.cmb_addit_sort_c_report,filtr_by_owner_user=True)
        elif 'Документы' in type_rep:
            self.ui.cmb_addit_sort_c_report.setEnabled(True)
            RPTP.fill_cmb_users_with_rules(self.ui.cmb_addit_sort_c_report,filtr_by_current_user=True)
        else:
            self.ui.cmb_addit_sort_c_report.setDisabled(True)

    if vid == 'Матрицы компетенций':
        type_rep = self.ui.cmb_podrazdelenie.currentData(CQT.Qt.UserRole)
        self.ui.cmb_addit_sort_c_report.clear()
        if type_rep == '':
            return
        if type_rep == 'by_emploee' :
            self.ui.cmb_addit_sort_c_report.setEnabled(True)
            MTXCMP.fill_cmb_to_select_dep(self.ui.cmb_addit_sort_c_report,CFG.Config.place.poki)
        elif type_rep == 'by_depatment':
            self.ui.cmb_addit_sort_c_report.setEnabled(False)


def _______SELECT_REPORT_____________():
    pass

@CQT.onerror
def vibor_sort_c_report_c(self: mywindow, *args):
    vid = self.ui.cmb_sort_c_report.currentText()
    self.vid_report_c = vid
    self.ui.fr_params_plan.setHidden(True)
    self.ui.le_end_of_period.setEnabled(True)
    self.ui.le_start_of_period.setEnabled(True)
    self.ui.rbut_start_of_per.setEnabled(True)
    self.ui.rbut_end_of_period.setEnabled(True)
    self.ui.cmb_addit_sort_c_report.setEnabled(False)
    if vid == 'Матрицы компетенций':
        now = F.now("")
        dates = F.start_end_dates_c(now, '', 'd', "%Y-%m-%d %H:%M:%S")
        konec = dates[1]
        nach = dates[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        self.ui.cmb_podrazdelenie.clear()
        MTXCMP.fill_cmb_to_select_type_report(self.ui.cmb_podrazdelenie)
        self.ui.cmb_podrazdelenie.setEnabled(True)

        
    if vid == 'Отчетность персонала':
        now = F.now("")
        dates = F.start_end_dates_c(now, '', 'm', "%Y-%m-%d %H:%M:%S")
        konec = dates[1]
        nach = dates[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.setDisabled(False)
        RPTP.fill_cmb_to_select_regime()
        RPTP.init_rules()


    if vid == 'Не выгруженные в 1С наряды':
        next_month = F.now("")
        konec = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        nach = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        podrazdel_none(self)


    if vid == 'Отчет по отклонениям табеля и трудозатрат':
        next_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        nach = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        podrazdel_none(self)


    if vid == 'Выполнение проектов находящихся в производстве без привязке к периоду':
        self.ui.le_start_of_period.setText("2023-01-01 00:00:01")
        last_month = F.now("")
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.setDisabled(True)
        podrazdel_none(self)


    if vid == 'Исполнение плана месяца':
        self.ui.le_start_of_period.setText("2023-01-01 00:00:01")
        self.ui.le_end_of_period.setText("2023-01-01 00:00:01")
        self.ui.cmb_podrazdelenie.setEnabled(True)
        self.ui.rbut_start_of_per.setEnabled(False)
        self.ui.rbut_end_of_period.setEnabled(False)
        self.ui.le_end_of_period.setEnabled(False)
        self.ui.le_start_of_period.setEnabled(False)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItem('-')
        list_month = CSQ.custom_request_c(self.db_kplan,
                                          f"""SELECT Дата, Пномер FROM mnts_plan WHERE  file_poz_plan NOT NULL;""",
                                          rez_dict=True)
        list_month_str = [_['Дата'] for _ in list_month]
        self.ui.cmb_podrazdelenie.addItems(list_month_str)

    if vid == 'Распределение работ по направлениям':
        self.ui.le_start_of_period.setText("2023-01-01 00:00:01")
        last_month = F.now("")
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.setDisabled(True)
        podrazdel_none(self)
    if vid == 'Отклонения от плановых дат по проектам':
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = '2023-01-01 00:00:00'
        self.ui.le_start_of_period.setText(nach)
        self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)
    if vid == 'Выработка_ТОП':
        next_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        nach = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        podrazdel_list(self, ['По направлениям', 'По сотрудникам',
                              'По направлениям будни', 'По сотрудникам будни', 'По сотрудникам выходные',
                              'По сотрудникам выходные за год',
                              'По направлениям за год', 'По сотрудникам за год',
                              'По направлениям будни за год', 'По сотрудникам будни за год', ])
    if vid == 'Усредненная удельная трудоемкость сборки по видам':
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = F.start_end_dates_c(dat)[0]
        self.ui.le_start_of_period.setText(nach)
        self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)
    if vid == 'Внеплановые работы по направлениям':
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        nach, konec = F.start_end_dates_c(date=dat, vid='y') #07.07.25
        # nach = '2023-01-01 00:00:00'
        self.ui.le_start_of_period.setText(nach)
        self.ui.le_end_of_period.setText(konec)
        self.ui.fr_params_plan.setHidden(False)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItems(list(self.DICT_NAPRAVL.keys()))
        self.ui.cmb_podrazdelenie.addItem('Все')
        self.ui.cmb_podrazdelenie.setDisabled(False)
        list_etaps = sorted(list(set([_['этап'] for _ in self.Data.ETAP_BY_FIO.values() if _['этап'] != None])))
        self.ui.fr_params_plan.setHidden(False)
        self.ui.cmb_gant_tochnost_dat.setEnabled(True)
        self.ui.cmb_gant_tochnost_dat.clear()
        self.ui.cmb_gant_tochnost_dat.addItem('')
        self.ui.cmb_gant_tochnost_dat.addItems(list_etaps)

    if vid == 'План-фактный график по месяцам':
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = '2024-01-01 00:00:00'
        self.ui.le_start_of_period.setText(nach)
        self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)

    if vid == 'График удельной производительности сборочного цеха':
        nach = '2024-01-01 00:00:00'
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        self.ui.le_start_of_period.setText(nach)
        self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)

    if vid == 'Норматив материалов по завершенным нарядам':
        next_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        nach = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        podrazdel_none(self)

    if vid == 'Неосвоенный_вес_по_созданным_нарядам':
        self.ui.le_end_of_period.setEnabled(False)
        self.ui.le_start_of_period.setEnabled(False)
        podrazdel_kod(self)

    if vid == 'О выработке сотрудников за месяц':
        dat = F.date_add_days(F.datetostr(DT.today()), -1)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = F.start_end_dates_c(date=dat, vid='m')[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        podrazdel_none(self)

    if vid == 'Трудозатраты':
        dat = F.date_add_days(F.datetostr(DT.today()), -1)
        konec = F.start_end_dates_c(date=dat, vid='d')[1]
        nach = F.start_end_dates_c(date=dat, vid='d')[0]
        self.ui.fr_params_plan.setHidden(False)
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        list_podr = sorted(
            list(set([_['Подразделение'] for _ in self.Data.ETAP_BY_FIO.values() if _['этап'] not in (None, '') and  _['Компания'] == self.place.Имя])))
        self.ui.cmb_podrazdelenie.setDisabled(False)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItem('')

        for podr in list_podr:
            self.ui.cmb_podrazdelenie.addItem(podr)
        # podrazdel_kod(self)
    if vid == 'Статистика нормо-весовых харктеристик МК':
        podrazdel_kod(self)

    if vid == 'Выработка цеха по направлению':
        dat = F.date_add_days(F.datetostr(DT.today()), -30)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = F.start_end_dates_c(date=dat, vid='m')[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        list_etaps = sorted(list(set([_['этап'] for _ in self.Data.ETAP_BY_FIO.values() if _['этап'] != None])))
        self.ui.cmb_podrazdelenie.setEnabled(True)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItem('')
        self.ui.cmb_podrazdelenie.addItems(list_etaps)
    if vid == 'Выработка цеха понарядно':
        podrazdel_kod(self)
    if vid == 'Журнал работ':
        nach_kon_mes(self, 'kon')
        podrazdel_none(self)
    if vid == 'Внеплановые работы':
        nach_kon_mes(self, 'kon')
        podrazdel_none(self)
    if vid == 'Выработка сотрудника':
        nach_kon_mes(self, 'kon')
        fill_podrazd_by_empl_full(self)

    if vid == 'Динамика производительности сотрудников':
        nach_kon_mes(self, 'kon')
        fill_podrazd_by_empl_full(self)
        #emploee(self)
    if vid == 'Выработка сотрудников':
        nach_kon_mes(self, kon='end')
        podrazdel_from_dolgn_etap(self)
    if vid == 'Текущие работы':
        nach_kon_mes(self, 'kon')
        podrazdel_kod(self)

    if vid == 'Понедельный график выработки и отгрузок':
        nach = '2023-01-01 00:00:00'
        self.ui.le_start_of_period.setText(nach)
        podrazdel_kod(self)
    if vid == 'Селекторное':
        self.ui.le_start_of_period.setText(F.now("%Y-%m-%d %H:%M:%S"))
        self.ui.le_end_of_period.setText(F.now("%Y-%m-%d %H:%M:%S"))
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItems(
            ('Добавлено', 'Закрыто', 'Не закрыто', 'По плану закрыть', 'Просрочены', 'Все'))
        self.ui.cmb_podrazdelenie.setDisabled(False)
    if vid == 'План-фактный анализ по месяцам':
        self.ui.le_start_of_period.setText("2022-09-01 00:00:00")
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItems(list(self.DICT_NAPRAVL.keys()))
        self.ui.cmb_podrazdelenie.addItem('Все')
        self.ui.cmb_podrazdelenie.setDisabled(False)
    if vid == 'Длина сварных швов к выработке':
        self.ui.le_start_of_period.setText("2022-09-01 00:00:00")
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItems(list(self.DICT_NAPRAVL.keys()))
        self.ui.cmb_podrazdelenie.addItem('Все')
        self.ui.cmb_podrazdelenie.setDisabled(False)
    if vid == 'Журнал_техкарт':
        dat = F.date_add_days(F.datetostr(DT.today()), -1)
        konec = F.start_end_dates_c(date=dat, vid='d')[1]
        nach = F.start_end_dates_c(date=dat, vid='d')[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        podrazdel_none(self)
    if vid == 'Журнал_замечаний':
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        nach = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        podrazdel_none(self)
    if vid == 'Отчет для селектора':
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        nach = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period.setText(konec)
        self.ui.le_start_of_period.setText(nach)
        podrazdel_none(self)
    if vid == 'Журнал замечаний динамика':
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = '2023-01-01 00:00:00'
        self.ui.le_start_of_period.setText(nach)
        self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)
    if vid == 'Сравнение норм времени по направлениям':
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        self.ui.le_start_of_period.setText("2023-01-01 00:00:00")
        self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)
    # +++++++++++ отчет - Реестр проектов в работе
    if vid == 'Реестр проектов в работе':
        # last_month = F.now("") - relativedelta(months=1)
        # konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        # self.ui.le_start_of_period.setText("2023-01-01 00:00:00")
        # self.ui.le_end_of_period.setText(konec)
        podrazdel_kod(self)
    # +++++++++++ отчет - Реестр проектов в работе
    if vid == 'Анализ эффективности работ на минуту':
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        self.ui.le_start_of_period.setText("2024-04-01 00:00:00")
        self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)
    if vid == 'Анализ внеплана по видам работ':
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        self.ui.le_start_of_period.setText("2024-04-01 00:00:00")
        self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)
    if vid == 'ПланФакт наряды с внепланом':
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        self.ui.le_start_of_period.setText("2024-04-01 00:00:00")
        self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)
    if vid == 'Отчет по загрузке оборудования':
        # last_month = F.now("") - relativedelta(months=1)
        # konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        # self.ui.le_start_of_period.setText("2024-04-01 00:00:00")
        # self.ui.le_end_of_period.setText(konec)
        podrazdel_none(self)
    if vid == 'Отчет по проекту':
        self.ui.cmb_podrazdelenie.setDisabled(False)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItem('Выбрать год в календаре')
    if vid == 'Компоновщик':
        name_type_path = 'viewer_builder_excel_path'
        path = CMS.load_tmp_path(name_type_path)
        file_path = CQT.f_dialog_name(self, 'Выбрать файл', path,'*.xlsx')
        if file_path == '.':
            return
        CMS.save_tmp_path(name_type_path, file_path,True)
        self.excel_parser = CEX.ExcelParser(file_path)
        worksheets = self.excel_parser.worksheets
        self.ui.cmb_podrazdelenie.clear()
        worksheets_cmb_values = ['Выберите лист', *worksheets]
        self.ui.cmb_podrazdelenie.addItems(worksheets_cmb_values)
        nach_kon_mes(self, 'kon')
        CQT.msgbox('Книга успешно загружена. Выберите лист')
@CQT.onerror
def get_list_py_by_year(self:mywindow,years:list):
    
    list_py = CSQ.custom_request_c(self.db_kplan,f"""SELECT 
     знпр.№ERP || " | " || знпр.№проекта || " | " || napravl_deyat.Псевдоним || " | " || plan.Позиция || " | " || пл_оуп.НомПл || " | " || пл_оуп.Вес_кг
     FROM 
     знпр 
      INNER JOIN пл_оуп ON пл_оуп.Пномер_ЗП == знпр.s_num 
      INNER JOIN plan ON plan.Пномер == пл_оуп.НомПл 
      INNER JOIN napravl_deyat ON plan.Направление_деятельности = napravl_deyat.Пномер 
      
      WHERE знпр.Год IN({CSQ.prepare_list_to_tuple(list(years))}) and plan.poki = {USRCNF.Config.place.poki}""", hat_c=False,one_column=True)
    DICT_COLOR = {k:F.align_colors(v['Цвет'])  for k,v in F.deploy_dict_c(self.Data.NAPRAVL_D,'Псевдоним').items()}
    tbl =[row.split(' | ') for row in list_py]
    tbl = [ {'№ERP':_[0],
             '№проекта':_[1],
            'Псевдоним':_[2],
            'Позиция':_[3],
            'НомПл':_[4],
             'Вес_кг': _[5]
    } for _ in tbl]
    proj = CQT.msgboxg_get_table(self,f'Выбрать проект {years[0]} года',tbl,selection_from_tbl=True,ExtendedSelection=False)
    
    CQT.fill_list_combobx(self,self.ui.cmb_podrazdelenie,list_py,[DICT_COLOR[_.split(" | ")[2]]for _ in list_py])
    if proj:
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItem(' | '.join(list(proj.values())))


@CQT.onerror
def nach_kon_mes(self, kon="today", *args):
    # dat = F.datetostr(DT.today())
    dat = F.datetostr(QtCore.QDate.toPyDate(self.ui.calendarWidget.selectedDate()))
    konec = F.start_end_dates_c(date=dat, vid='m')[1]
    nach = F.start_end_dates_c(date=dat, vid='m')[0]
    if kon == "today":
        self.ui.le_end_of_period.setText(dat)
    else:
        self.ui.le_end_of_period.setText(konec)
    self.ui.le_start_of_period.setText(nach)

def check_interval(vid: str, start: str, end: str):
    if not F.is_date(start) or not F.is_date(end):
        return
    if vid == 'Анализ внеплана по видам работ':
        interval = F.strtodate(start) - F.strtodate(end)
        if interval.days > 190:
            CQT.msgbox('Интервал дат для данного отчета не должен превышать 6 месяца ')
            return False
    return True

def _______GENERATE_REPORT_____________():
    pass

@CQT.progress_decorator
@CQT.onerror
def report_c(self: mywindow,hook_prog_bar=None,  *args):
    def oform_tbl(vid):
        tbl = self.ui.tbl_report_c
        self.vid_report_c = vid

        if vid == 'Выработка сотрудника':
            col_bad = CMS.Color_tbl(0)
            col_good = CMS.Color_tbl(100)

            col_start = CMS.Color_tbl(30)
            col_pause = CMS.Color_tbl(60)
            col_end = CMS.Color_tbl(90)

            for i in range(tbl.rowCount()):
                row = CQT.get_dict_line_form_tbl(tbl, i)
                if row['Подтвержд_вып'] == '0':
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Подтвержд_вып'), *col_bad.rgb)
                else:
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Подтвержд_вып'), *col_good.rgb)

                if row['Внеплан'] in ('1', '3'):
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Внеплан'), *col_bad.rgb)
                if row['Учет'] == 'Учтен':
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Учет'), *col_good.rgb)
                elif row['Учет'] == 'Не учтен':
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Учет'), *col_bad.rgb)

                if row['Статус'] == 'Начат':
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Статус'), *col_start.rgb)
                elif row['Статус'] == 'Приостановлен':
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Статус'), *col_pause.rgb)
                elif row['Статус'] == 'Завершен':
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Статус'), *col_end.rgb)

                if F.is_numeric(row['Коэфф_сложности']) and F.valm(row['Коэфф_сложности']) > 1 and F.valm(
                        row['Коэфф_сложности']) <= 2:
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Коэфф_сложности'), *col_bad.rgb)
                if F.is_numeric(row['Коэфф_сложности']) and F.valm(row['Коэфф_сложности']) < 1:
                    CQT.set_color_wtab_c(tbl, i, CQT.num_col_by_name_c(tbl, 'Коэфф_сложности'), *col_good.rgb)


            for j in range(tbl.columnCount()):
                tbl.setColumnWidth(j, tbl.columnWidth(j) + 8)
                CQT.font_cell_size_format(tbl, tbl.rowCount() - 2, j, bold=True)
            CQT._load_tbl(tbl,self.ui.tbl_report_c_filtr,True)

        if vid == 'Трудозатраты':
            #self.ui.tbl_report_c.setToolTip(
            #    f'Необходимо попасть в диапазон от {self.PROC_OTKL_TRUDOZATRAT[0]} до {self.PROC_OTKL_TRUDOZATRAT[1]}')
            nk_proc = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Соответствие_%')
            nf_post_erp = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Минут_выгружено_ЕРП')
            nf_summ_min = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Сумм_Минут')
            for i in range(self.ui.tbl_report_c.rowCount()):
                val_of_proc = F.valm(self.ui.tbl_report_c.item(i, nk_proc).text())
                if val_of_proc < 100 and val_of_proc >= self.PROC_OTKL_TRUDOZATRAT[0]:
                    delta = (100 - val_of_proc) * 6
                    CQT.set_color_wtab_c(self.ui.tbl_report_c, i, nk_proc, 255, 255, 255 - delta)
                if val_of_proc > 100 and val_of_proc <= self.PROC_OTKL_TRUDOZATRAT[1]:
                    delta = val_of_proc - 100
                    CQT.set_color_wtab_c(self.ui.tbl_report_c, i, nk_proc, 255 - delta, 255, 255 - delta)
                if val_of_proc < self.PROC_OTKL_TRUDOZATRAT[0] or val_of_proc > self.PROC_OTKL_TRUDOZATRAT[1]:
                    CQT.set_color_wtab_c(self.ui.tbl_report_c, i, nk_proc, 255, 55, 55)
                dir_path = CMS.load_tmp_path('tdz_dir')
                self.ui.le_path_save.setText(dir_path)
                koef = 0
                val_summ_min = F.valm(self.ui.tbl_report_c.item(i, nf_summ_min).text())
                if val_summ_min > 0:
                    val_erp_min, koef = F.valm(self.ui.tbl_report_c.item(i, nf_post_erp).text().split('('))
                    koef = round(F.valm(koef.replace('%)','')))
                obj_col = CMS.Color_tbl(koef)
                CQT.set_color_wtab_c(self.ui.tbl_report_c, i, nf_post_erp, obj_col.r, obj_col.g, obj_col.b)

        if vid == 'Отчет по отклонениям табеля и трудозатрат':
            tbl = self.ui.tbl_report_c

            list_vals = []
            list_vals_scud = []
            nf_otkl_trdz = CQT.num_col_by_name_c(tbl, 'Отклонение трдз от таб,%')
            nf_state = CQT.num_col_by_name_c(tbl, 'Статус')
            nf_podr = CQT.num_col_by_name_c(tbl, 'Подразделение')
            nf_otkl_scud = CQT.num_col_by_name_c(tbl, 'Отклонение СКУД от таб,%')
            
            for i in range(tbl.rowCount()):
                list_vals_scud.append(F.valm(tbl.item(i,nf_otkl_trdz).text()))
            max_val_scud = max([abs(min(list_vals_scud)), max(list_vals_scud)])
            delta_scud = 100/max_val_scud
            
            for i in range(tbl.rowCount()):
                list_vals.append(F.valm(tbl.item(i,nf_otkl_scud).text()))
            max_val = max([abs(min(list_vals)), max(list_vals)])
            delta = 100/max_val
            
            clr_bad = CMS.Color_tbl(0)
            clr_good = CMS.Color_tbl(100)
            clr_middle = CMS.Color_tbl(50)
            for i in range(tbl.rowCount()):
                otkl = abs(F.valm(tbl.item(i,nf_otkl_trdz).text()))*delta
                clr = CMS.Color_tbl(otkl,True)
                CQT.set_color_wtab_c(tbl,i,nf_otkl_trdz,clr.r,clr.g,clr.b)
                
                otkl_scud = abs(F.valm(tbl.item(i,nf_otkl_scud).text()))*delta_scud
                clr = CMS.Color_tbl(otkl_scud,True)
                CQT.set_color_wtab_c(tbl,i,nf_otkl_scud,clr.r,clr.g,clr.b)
                
                if tbl.item(i,nf_state).text() == 'Работа':
                    CQT.set_color_wtab_c(tbl, i, nf_state, clr_good.r, clr_good.g, clr_good.b)
                elif tbl.item(i,nf_state).text() == 'Увольнение':
                    CQT.set_color_wtab_c(tbl, i, nf_state, clr_bad.r, clr_bad.g, clr_bad.b)
                else:
                    CQT.set_color_wtab_c(tbl, i, nf_state, clr_middle.r, clr_middle.g, clr_middle.b)
                
                if tbl.item(i,nf_podr).text() in self.DICT_PODR_RC:
                    clr_p_r,clr_p_g,clr_p_b = self.DICT_PODR_RC[tbl.item(i,nf_podr).text()]['Цвет'].split(',')
                    CQT.set_color_wtab_c(tbl, i, nf_podr, clr_p_r,clr_p_g,clr_p_b)
                
        if vid == 'Матрицы компетенций':
            tbl = self.ui.tbl_report_c
            t = CQT.TableContext(tbl)
            t.hide('id_user')
            t.hide('id_comp')
            t.hide('_color_dep')
            t.hide('id_depatment_mes')


    #self.ui.tbl_report_c.setToolTip('')
    self.ui.btn_save_txt.setDisabled(True)
    self.ui.fr_save_txt.setHidden(True)
    self.ui.fr_addition_tbl.setHidden(True)
    self.ui.fr_erp_handler.setHidden(True)
    self.ui.fr_params_plan.setHidden(True)
    self.ui.btn_save_txt.setText(f'Выгрузить')
    self.ui.le_path_save.setEnabled(True)
    nach = self.ui.le_start_of_period.text()
    konec = self.ui.le_end_of_period.text()
    vid = self.ui.cmb_sort_c_report.currentText()
    podrazd = self.ui.cmb_podrazdelenie.currentText()
    podrazd_data = self.ui.cmb_podrazdelenie.currentData(QtCore.Qt.UserRole)
    add_val = self.ui.cmb_addit_sort_c_report.currentText()
    self.ui.fr_mk_zamech.setHidden(True)
    self.ui.frame.setHidden(True)
    self.ui.fr_personal.setHidden(True)
    if not check_interval(vid, nach, konec):
        return

    if nach == '' or F.is_date(nach) == False:
        CQT.msgbox('Не корректная дата начала')
        return
    if konec == '' or F.is_date(konec) == False:
        CQT.msgbox('Не корректная дата конца')
        return
    if vid == '':
        CQT.msgbox('Не выбран вид отчета')
        return
    if podrazd == '':
        CQT.msgbox('Не выбрано подразделение')
        return
    hook_prog_bar.open()
    hook_prog_bar.set(0)
    hook_prog_bar.text('Очистка таблиц')
    tbl = self.ui.tbl_report_c
    CQT.clear_tbl(tbl)
    CQT.clear_tbl(self.ui.tbl_report_add)
    CQT.clear_tbl(self.ui.tbl_report_add_summ)
    CQT.clear_tbl(self.ui.tbl_report_add_filtr)
    CQT.clear_tbl(self.ui.tbl_viev_etaps_name)
    CQT.set_color_sort_cell_table_c(self.ui.tbl_report_c,SelectionRow=False)
    CQT.set_color_sort_cell_table_c(self.ui.tbl_report_add,SelectionRow=False)
    CQT.set_color_sort_cell_table_c(self.ui.tbl_viev_etaps_name, SelectionRow=False)
    CQT.set_color_sort_cell_table_c(self.ui.tbl_viev_etaps_erp, SelectionRow=False)
    rez_spis = [[]]
    
    self.permission = False
    self.global_arm_oper_user_fio = None
    clear_graf(self)
    CMS.save_tmp_path('last_used_report',vid)
    # self.fill_cmb_sorts_repot()
    hook_prog_bar.set(5)
    hook_prog_bar.text('Расчет данных')

    def report_excel_builder(self):
        cur_sheet = self.ui.cmb_podrazdelenie.currentText()
        if cur_sheet in self.excel_parser.worksheets:
            return self.excel_parser.data_by_worksheet(cur_sheet)
        return []

    if vid == 'Матрицы компетенций':
        if podrazd_data == 'by_depatment':
            rez_spis = report_matrix_competence_by_depatment(self,nach,konec)
        elif podrazd_data == 'by_emploee':
            rez_spis = report_matrix_competence(self,nach)

    if vid == 'Компоновщик':
        rez_spis = report_excel_builder(self)

    if vid == 'Не выгруженные в 1С наряды':
        rez_spis = not_upload_erp_nar(self, nach, konec)

    if vid == 'Динамика производительности сотрудников':
        rez_spis = dinam_proizv_sotr(self, nach, konec, add_val)
    if vid == 'Отчет по отклонениям табеля и трудозатрат':
        rez_spis = otkl_tabel_trdz(self, nach, konec, podrazd)
    if vid == 'Выполнение проектов находящихся в производстве без привязке к периоду':
        rez_spis = ispoln_pl_month_all(self, self.db_kplan, self.db_resxml, self.bd_naryad, self.bd_users, self.Data.DICT_PROFESSIONS,
                                   self.Data.DICT_VID_RABOT, podrazd)
    if vid == 'Исполнение плана месяца':
        rez_spis = ispoln_pl_month(self.db_kplan, self.db_resxml, self.bd_naryad, self.Data.DICT_PROFESSIONS,
                                   self.Data.DICT_VID_RABOT, podrazd)
    if vid == 'Распределение работ по направлениям':
        rez_spis = raspredelenie_po_naprfvleniam_proc(self, nach, konec)
    if vid == 'Отклонения от плановых дат по проектам':
        rez_spis = divergence_of_date_proj(self, nach, konec)
    if vid == 'Выработка_ТОП':
        rez_spis = virabotka_top(self, nach, konec, podrazd)
    if vid == 'Усредненная удельная трудоемкость сборки по видам':
        rez_spis = udel_trud_sort_c(self, nach, konec)
        self.ui.btn_save_txt.setDisabled(False)
        self.ui.fr_save_txt.setHidden(False)
    if vid == 'Внеплановые работы по направлениям':
        napr = podrazd
        podrazd = self.ui.cmb_gant_tochnost_dat.currentText()
        if podrazd == '':
            podrazd = 'Сборка+сварка'
        rez_spis = vneplan_po_napravl(self, nach, konec, napr, podrazd)
    if vid == 'План-фактный график по месяцам':
        rez_spis = plan_fact_grafic_mes(self, nach, konec)
    if vid == 'График удельной производительности сборочного цеха':
        rez_spis = gr_ud_proizv_cexa(self, nach, konec)
    if vid == 'Журнал_замечаний':
        rez_spis = jurnal_zamech(self, nach, konec)
        self.ui.fr_mk_zamech.setHidden(False)
        ZMCH.load_table_add(self)
        ZMCH.load_table_zamech(self)
    if vid == 'Журнал замечаний динамика':
        rez_spis = jurnal_zamech_dinamic(self, nach, konec)
    if vid == 'Журнал_техкарт':
        rez_spis = jurnal_tk(self, nach, konec)
    if vid == 'Норматив материалов по завершенным нарядам':
        rez_spis = norm_mat_po_zav_nar(self, nach, konec)
    if vid == 'Неосвоенный_вес_по_созданным_нарядам':
        rez_spis = neosv_ves_po_sozd_nar(self, podrazd)
    if vid == 'О выработке сотрудников за месяц':
        rez_spis = virabotka_sotr_za_mes(self, nach, konec)
    if vid == 'План-фактный анализ по месяцам':
        rez_spis = plan_fact_mes(self, nach, konec, podrazd)
    if vid == 'Отчетность персонала':
        rez_spis = None

        date_start = F.strtodate(self.ui.le_start_of_period.text())
        date_end = F.strtodate(self.ui.le_end_of_period.text())
        RPTP.init_dates_reports(date_start,date_end)
        self.ui.fr_addition_tbl.setHidden(False)
        if podrazd_data == 'events':
            RPTP.load_pers_events()
        if podrazd_data == 'settings':
            RPTP.load_pers_rules()
        if podrazd_data == 'report':
            RPTP.load_pers_report()
        self.ui.fr_personal.setHidden(False)

    if vid == 'Трудозатраты':
        self.ui.fr_params_plan.setHidden(False)
        rez_spis = trudozatraty(self, nach, konec, podrazd)
        self.ui.btn_save_txt.setDisabled(False)
        self.ui.fr_save_txt.setHidden(False)
        self.ui.frame.setHidden(False)
        self.ui.fr_erp_handler.setHidden(False)
        if self.ARM_oper_using:
            self.ui.fr_addition_tbl.setHidden(False)
            self.ui.fr_addition_tbl.setHidden(False)
        CQT.set_color_sort_cell_table_c(self.ui.tbl_report_c, SelectionRow=True)
        CQT.set_color_sort_cell_table_c(self.ui.tbl_report_add, SelectionRow=True)
        CQT.set_color_sort_cell_table_c(self.ui.tbl_viev_etaps_name, SelectionRow=True)
        CQT.set_color_sort_cell_table_c(self.ui.tbl_viev_etaps_erp, SelectionRow=True)

    if vid == 'Статистика нормо-весовых харктеристик МК':
        rez_spis = statistic_normoweight_MK_c(self, nach, konec, podrazd)
    if vid == 'Выработка цеха по направлению':
        rez_spis = virabotka_ceha(self, nach, konec, podrazd, f_napravl=True)
    if vid == 'Выработка цеха понарядно':
        rez_spis = virabotka_ceha_ponaryadno(self, nach, konec, podrazd)
    if vid == 'Журнал работ':
        rez_spis = jurnal_rabot(self, nach, konec)
    if vid == 'Внеплановые работы':
        rez_spis = vneplan_rabot(self, nach, konec)
    if vid == 'Выработка сотрудника':
        rez_spis = virabotka_sotr(self, nach, konec, add_val)
    if vid == 'Выработка сотрудников':
        rez_spis = virabotka_sotrudnikov(self, nach, konec, podrazd)
        self.ui.fr_save_txt.setHidden(False)
        self.ui.btn_save_txt.setText(f'Выгрузить в ЕРП')
        self.ui.le_path_save.setEnabled(False)
        self.ui.btn_save_txt.setDisabled(False)
    if vid == 'Текущие работы':
        rez_spis = tekush_raboty(self, podrazd)
    if vid == 'Понедельный график выработки и отгрузок':
        rez_spis = ponedelniy_grafik_vir_otgr(self, nach, konec, podrazd)
    if vid == 'План работ':
        self.ui.fr_params_plan.setHidden(False)
        rez_spis = plan_rabot_preload(self, nach, konec, podrazd)
    if vid == 'Селекторное':
        rez_spis = report_c_selector(self, nach, konec, podrazd)
    if vid == 'Отчет для селектора':
        rez_spis = report_c_selector_2(self, nach, konec, podrazd)
    if vid == 'Сравнение норм времени по направлениям':
        rez_spis = sravn_nv_napr(self, nach, konec)
    if vid == 'Длина сварных швов к выработке':
        rez_spis = svar_vir(self, nach, konec)
    # --------------------- 'Реестр проектов в работе'
    if vid == 'Реестр проектов в работе':
        rez_spis = ready_procent_ver2(self, nach, konec, podrazd)
    # --------------------- 'Реестр проектов в работе'
    # F.save_file('debug.txt',self.debug)
    if vid == 'Анализ эффективности работ на минуту':
        rez_spis = analysis_effectiv_work_per_minute(self, nach, konec, podrazd)
    if vid == 'Анализ внеплана по видам работ':

        rez_spis = analysis_vneplan_by_vid_rab(self, nach, konec, podrazd)
        self.ui.fr_save_txt.setHidden(False)
        self.ui.btn_save_txt.setText(f'Выгрузить коэфф. в БД')
        self.ui.le_path_save.setEnabled(False)
        self.ui.btn_save_txt.setDisabled(False)
    if vid == 'ПланФакт наряды с внепланом':
        rez_spis = planfact_nar_s_vneplan(self, nach, konec, podrazd)
    if vid == 'Отчет по загрузке оборудования':
        rez_spis = report_of_load_machine(self, nach,konec, podrazd)
    if vid == 'Отчет по проекту':
        rez_spis = report_by_proj(self, nach, konec, podrazd)


    if rez_spis == None:
        return

    hook_prog_bar.set(80)
    hook_prog_bar.text('Заполение таблиц')

    #CQT.fill_wtabl_old_c(self, rez_spis, tbl, separ='', isp_hat_c=True, max_vis_row=500)
    CQT.fill_wtabl(rez_spis,tbl,auto_type=False,height_row=24,sortingEnabled=True)


    hook_prog_bar.set(90)
    hook_prog_bar.text('Оформление таблиц')
    # --- только оформление таблицы
    if vid in (
            'Трудозатраты',
            'Отчет по отклонениям табеля и трудозатрат',
            'Выработка сотрудника',
            'Матрицы компетенций',
    ):
        oform_tbl(vid)

    # --- apply_summ_с со sredn=True
    if vid in (
            'Реестр проектов в работе',
            'Выработка цеха понарядно',
            'Понедельный график выработки и отгрузок',
            'Статистика нормо-весовых харктеристик МК',
            'План работ',
            'План-фактный анализ по месяцам',
            'О выработке сотрудников за месяц',
            'Неосвоенный_вес_по_созданным_нарядам',
            'Норматив материалов по завершенным нарядам',
            'Журнал_техкарт',
            'Журнал_замечаний',
            'Сравнение норм времени по направлениям',
            'График удельной производительности сборочного цеха',
            'Выработка_ТОП',
            'Отклонения от плановых дат по проектам',
            'План-фактный график по месяцам',
            'Динамика производительности сотрудников'
    ):
        CMS.apply_summ_с(self, tbl, sredn=True)

    # --- apply_summ_с со sredn=False
    if vid in ('Распределение работ по направлениям',
               'Выработка сотрудников',
               'Журнал работ',
               'Выработка сотрудника'
               ):
        CMS.apply_summ_с(self, tbl, sredn=False)

    # --- отдельное оформление плана
    if vid in (
            'Исполнение плана месяца',
            'Выполнение проектов находящихся в производстве без привязке к периоду'
    ):
        oform_tbl_execute_monh_plan(tbl)

    # --- особый случай с правами
    if vid == 'Журнал_замечаний':
        self.permission = CMS.user_access(
            self.bd_naryad,
            'просмотр_журнал_замечаний_корректировка_вн',
            F.user_full_namre(),
            False
        )

    CMS.fill_filtr_c(self, self.ui.tbl_report_c_filtr, tbl, hidden_scroll=True)
    CMS.update_width_filtr(tbl, self.ui.tbl_report_c_filtr)

    hook_prog_bar.set(100)
    hook_prog_bar.text('')

    if self.chk_autohide:
        self.up_down()


def report_by_proj(self, nach, konec, podrazd=None, *args):
    if podrazd == None or podrazd.count(' | ') != 5:
        return
    py,proj,napravl_deyat,poz, kpl, ves = podrazd.split(' | ')
    list = CSQ.custom_request_c(self.bd_naryad,fr"""
    SELECT mk.Пномер, mk.Номенклатура, mk.Вес, mk.Количество, mk.Статус, 
    дорезки_мк.Причина AS дорезки_мк_Причина, 

            тип_дорезок.Имя AS тип_дорезок_Имя, 
            тип_дорезок.Коэффициент_наряда AS тип_дорезок_Коэффициент_наряда, 

            тип_доработок.Имя AS тип_доработок_Имя, 
            тип_доработок.Коэффициент_наряда AS тип_доработок_Коэффициент_наряда, 

            Тип_мк.Имя AS Тип_мк_Имя, 
    
    naryad.Пномер as "Наряд Пномер", 
    naryad.Дата as "Наряд Дата", 
    naryad.Внеплан as "Наряд Внеплан", 
    naryad.Распред_дата as "Наряд Распред_дата",
    "" as  "Наряд Этап", 
    naryad.ФИО as "Наряд ФИО", 
    naryad.Фвремя as "Наряд Фвремя", 
    naryad.ФИО2 as "Наряд ФИО2", 
    naryad.Фвремя2 as "Наряд Фвремя2", 
    naryad.Твремя as "Наряд Твремя", 
    naryad.Норма_времени as "Наряд Норма_времени", 
    naryad.Подтвержд_вып_дата as "Наряд Подтвержд_вып_дата", 
    naryad.Подтвержд_вып_фио as "Наряд Подтвержд_вып_фио", 
    naryad.Кол_повт_приемок as "Наряд Кол_повт_приемок",
    naryad.Виды_работ as "Наряд Виды_работ",  

    
    jurnal.Пномер as "Журнал работ Пномер",
    jurnal.Дата as "Журнал работ Дата",
    jurnal.ФИО as "Журнал работ ФИО",
    jurnal.Подытог as "Журнал работ Подытог",
    jurnal.Подытог_нормы as "Журнал работ Подытог_нормы",
    jurnal.Дата_выгрузки_ЕРП as "Журнал работ Дата_выгрузки_ЕРП",
    jurnal.ФИО_выгрузки_ЕРП as "Журнал работ ФИО_выгрузки_ЕРП",
    jurnal.Минут_выгружено_ЕРП as "Журнал работ Минут_выгружено_ЕРП",
    jurnal.Статус as "Журнал работ Статус", 
    jurnal.Примечание as "Журнал работ Примечание" 
    FROM mk 
    INNER JOIN naryad on naryad.Номер_мк = mk.Пномер 
    INNER JOIN jurnal on jurnal.Номер_наряда = naryad.Пномер 
    LEFT JOIN дорезки_мк ON дорезки_мк.Номер_мк = mk.Пномер  
    LEFT JOIN тип_дорезок ON тип_дорезок.Пномер = дорезки_мк.Причина  
    LEFT JOIN тип_доработок ON тип_доработок.Пномер = mk.Тип_доработки 
    LEFT JOIN Тип_мк ON Тип_мк.Пномер = mk.Тип 

WHERE mk.НомКплан = {kpl}; 
""", rez_dict=True)
    for item in list:

        if item["Наряд Виды_работ"] != '':
            first_vid = item["Наряд Виды_работ"].split('|')[0]
            if first_vid in self.DICT_VID_RABOT:
                item["Наряд Этап"] = self.DICT_VID_RABOT[first_vid]['этап']

    return list

def report_of_load_machine(self, nach, konec, podrazd=None, *args):
    tbl = [['Станок', 'Твремя', 'Фвремя', 'Должности']]
    db_naryad = 'SRV:Naryad.db'
    db_resxml = 'SRV:BD_resxml.db'

    list_naryad = CSQ.custom_request_c(
        db_naryad,
        f"""
            SELECT * FROM jurnal j 
            INNER JOIN naryad n ON n.Пномер = j.Номер_наряда 
            WHERE datetime(j.Дата) > datetime("{nach}") and datetime(j.Дата) < datetime("{konec}")
                AND j.Статус = "Завершен"
                AND n.Номер_мк != 0
        """,
        rez_dict=True,
        hat_c=False
    )
    request = """
            SELECT 
            mk.Пномер,
            mk.Дата,
            mk.Статус,
            mk.Номенклатура,
            mk.Номер_заказа,
            mk.Номер_проекта,
            mk.Вид,
            mk.Примечание,
            mk.Основание,
            mk.Прогресс,
            mk.Приоритет,
            mk.Направление,
            mk.Вес,
            mk.xml,
            mk.Количество,
            mk.Статус_ЧПУ,
            mk.Ресурсная,
            mk.Дата_завершения,
            mk.Коэф_парал,
            mk.Обеспечение,
            mk.Место,
            mk.Искл_план_рм,
            mk.Тип,
            mk.Ресурсная_дата,
            mk.ФИО,
            mk.НомКплан,
            mk.check_execute_opers,
            mk.Тип_доработки,
            mk.На_удал,

            дорезки_мк.Причина AS дорезки_мк_Причина,

            тип_дорезок.Имя AS тип_дорезок_Имя,
            тип_дорезок.Коэффициент_наряда AS тип_дорезок_Коэффициент_наряда,

            тип_доработок.Имя AS тип_доработок_Имя,
            тип_доработок.Коэффициент_наряда AS тип_доработок_Коэффициент_наряда,

            Тип_мк.Имя AS Тип_мк_Имя,
            Тип_мк.rgb AS Тип_мк_rgb

             FROM mk LEFT JOIN дорезки_мк ON дорезки_мк.Номер_мк = mk.Пномер  
            LEFT JOIN тип_дорезок ON тип_дорезок.Пномер = дорезки_мк.Причина  
            LEFT JOIN тип_доработок ON тип_доработок.Пномер = mk.Тип_доработки 
                            LEFT JOIN Тип_мк ON Тип_мк.Пномер = mk.Тип
            WHERE mk.Пномер IN ({nums}) AND mk.Пномер != 0;"""

    res_xml_query = '''SELECT Номер_мк, data FROM res WHERE Номер_мк IN ({nums})'''

    nums_mk = {
        str(naryad['Номер_мк']): {'naryad': naryad}
        for naryad in list_naryad
    }

    response_mk = CSQ.custom_request_c(db_naryad, request.format(nums=', '.join(nums_mk.keys())), rez_dict=True,
                                       hat_c=False)
    response_res = CSQ.custom_request_c(db_resxml, res_xml_query.format(nums=', '.join(nums_mk.keys())), hat_c=False)
    dict_res = dict(response_res)
    machines = defaultdict(dict)
    mach = defaultdict(list)
    for mk in response_mk:
        mk_pk = mk['Пномер']
        operations_nar = nums_mk[str(mk_pk)]['naryad']['Операции'].split('|')
        operations_times = nums_mk[str(mk_pk)]['naryad']['Опер_время'].split('|')
        fact_time_1 = nums_mk[str(mk_pk)]['naryad']['Фвремя'] if nums_mk[str(mk_pk)]['naryad']['Фвремя'] else float()
        fact_time_2 = nums_mk[str(mk_pk)]['naryad']['Фвремя2'] if nums_mk[str(mk_pk)]['naryad']['Фвремя2'] else float()
        fact_time = float(fact_time_1) + float(fact_time_2)
        teo_time = nums_mk[str(mk_pk)]['naryad']['Твремя']
        instance = CMS.Marshrut_cards(mk_pk, db_naryad, db_resxml, row_from_db=mk,
                                      byte_data_res_from_db=dict_res.get(mk_pk))
        if instance.res:
            for res in instance.res:
                for operation_res in res.get('Операции', []):
                    oper_name = operation_res.get('Опер_наименование')
                    machine_name = operation_res.get('Опер_оборудование_наименование')
                    machines[oper_name]['Операция_instance'] = operation_res
                    mach[machine_name].append(machines[oper_name])
                    machines[oper_name]['name'] = operation_res.get('Опер_оборудование_наименование')
                    machines[oper_name].setdefault('Фвремя', float())
                    machines[oper_name].setdefault('Твремя', float())
                    machines[oper_name].setdefault('Должности', set()).add(
                        operation_res.get('Опер_профессия_наименование', ''))

        remains_time = (fact_time - teo_time) / len(operations_nar)
        for op_nar, op_time in zip(operations_nar, operations_times):
            _, name = op_nar.split('$')
            machines[name]['Твремя'] += float(op_time)
            machines[name]['Фвремя'] += (float(op_time) + float(remains_time))

    for k, v in mach.items():
        machine = {'Станок': k, 'Твремя': 0, 'Фвремя': 0}
        for oper in v:
            machine['Твремя'] += oper['Твремя']
            machine['Фвремя'] += oper['Фвремя']
        machine['Твремя'] = abs(round(machine['Твремя']))
        machine['Фвремя'] = abs(round(machine['Фвремя']))
        machine['Должности'] = v and ', '.join(d for d in v[0]['Должности'] if d)
        tbl.append(list(machine.values()))

    return tbl

def oform_tbl_execute_monh_plan(tbl):
    list_exclude_fields_oform = ['Примечание', 'Примечание_сб']
    tbl_color = []
    for i in range(tbl.rowCount()):
        tmp_row_color = []
        row = CQT.get_dict_line_form_tbl(tbl, i)
        for j, key in enumerate(row.keys()):
            str_color = f'rgb(255,255,255,0.7)'
            if key not in list_exclude_fields_oform:
                if '/' in row[key] and row[key].count('/')==1:
                    val, summ = row[key].split('/')
                    if F.valm(val) == 0 and F.valm(summ) == 0:
                        tmp_row_color.append(str_color)
                        continue
                    percent = 0
                    if F.valm(summ) > 0:
                        percent = F.valm(val) / F.valm(summ) * 100
                    else:
                        percent = 100
                    clr = CMS.Color_tbl(percent)
                    CQT.set_color_wtab_c(tbl, i, j, clr.r, clr.g, clr.b)
                    str_color = f'rgb({clr.r},{clr.g},{clr.b},0.7)'
                elif '%' in key and row[key] != '':
                    percent = F.valm(row[key])
                    clr = CMS.Color_tbl(percent)
                    CQT.set_color_wtab_c(tbl, i, j, clr.r, clr.g, clr.b)
                    str_color = f'rgba({clr.r},{clr.g},{clr.b},0.7)'
            tmp_row_color.append(str_color)
        tbl_color.append(tmp_row_color)
    return tbl_color


def rc_po_fio(self, fio):
    fio_rc = False
    if fio in self.DICT_EMPLOEE_FULL:
        fio_podrazd = self.DICT_EMPLOEE_FULL[fio]['Подразделение']
        for podr in self.DICT_RC.keys():
            if self.DICT_RC[podr]['empl_Подразделение'] == fio_podrazd:
                fio_rc = podr
    return fio_rc


def gr_ud_proizv_cexa(self: mywindow, nach, konec, *args):
    def get_ves_from_res_and_xml():
        def podgotovka_xml(self, spis_xml: list, xml_head='', show_negruz=False):
            if spis_xml == None:
                return
            rez = []
            if xml_head == '':

                self.xml_head = 0
            else:
                self.xml_head = xml_head

            for i in range(len(spis_xml)):
                if spis_xml[i]['data']['Покупное изделие'] == '1':
                    if spis_xml[i]['data']['Обозначение полное'].strip() == '':
                        spis_xml[i]['data']['Обозначение полное'] = F.shifr(spis_xml[i]['data']['Наименование'])[:13]
                else:
                    if spis_xml[i]['data']['Обозначение полное'].strip() == '':
                        CQT.msgbox(
                            f"Ошибка {spis_xml[i]['data']['Наименование']} {spis_xml[i]['data']['Обозначение полное']} не имеет Обозначение/не покупная")
                        return
                if 'Классификатор изделия' in spis_xml[i]['data']:
                    if spis_xml[i]['data']['Классификатор изделия'] == None:
                        spis_xml[i]['data']['Классификатор изделия'] = ''
                if 'Код ERP' in spis_xml[i]['data']:
                    if spis_xml[i]['data']['Код ERP'] == None:
                        spis_xml[i]['data']['Код ERP'] = ''

                mat = "/".join(
                    (str(spis_xml[i]['data']['Масса']).replace(',', '.'),
                     F.clear_row_for_file_name_c(str(spis_xml[i]['data']['Материал'])),
                     F.clear_row_for_file_name_c(str(spis_xml[i]['data']['Материал2'])),
                     F.clear_row_for_file_name_c(str(spis_xml[i]['data']['Материал3']))))
                spis_xml[i]['data']['Масса/М1,М2,М3'] = mat
                spis_xml[i]['data'].pop('Материал', None)
                spis_xml[i]['data'].pop('Материал2', None)
                spis_xml[i]['data'].pop('Материал3', None)
                spis_xml[i]['data']['Наименование'] = F.clear_row_for_file_name_c(spis_xml[i]['data']['Наименование'])
                spis_xml[i]['data']['Обозначение полное'] = F.clear_row_for_file_name_c(
                    spis_xml[i]['data']['Обозначение полное'])
                if 'Сводное наименование' in spis_xml[i]['data']:
                    spis_xml[i]['data']['Сводное наименование'] = F.clear_row_for_file_name_c(
                        spis_xml[i]['data']['Сводное наименование'])

                if 'Тип' in spis_xml[i]['data']:
                    if show_negruz:
                        rez.append(spis_xml[i])
                    else:
                        if spis_xml[i]['data']['Тип'] not in self.TIP_NEGRUZ_DSE:
                            rez.append(spis_xml[i])
                        else:
                            tek_ur = spis_xml[i]['level_c']
                            if i == 0:
                                pred_ur = -1
                            else:
                                pred_ur = spis_xml[i - 1]['level_c']
                            delta_ur = tek_ur - pred_ur
                            for j in range(i + 1, len(spis_xml)):
                                if spis_xml[j]['level_c'] <= tek_ur:
                                    break
                                spis_xml[j]['level_c'] -= delta_ur
                else:
                    rez.append(spis_xml[i])
            return rez

        self.TIP_NEGRUZ_DSE = ('Сборочный чертёж', 'Изделие проекта', 'Монтажный чертёж', 'Материал')
        DICT_MAT = F.deploy_dict_c(CSQ.custom_request_c(self.bd_mat, f"""SELECT * FROM nomen""", rez_dict=True), 'Код')
        DICT_FILTR = F.deploy_dict_c(
            CSQ.custom_request_c(self.bd_mat, f"""SELECT * FROM complex_filtr""", rez_dict=True), 'kod')
        custom_request_c = f"""SELECT mk.Пномер, mk.Дата_завершения, mk.Количество, mk.xml  FROM mk WHERE Дата_завершения != ""
                    and datetime(Дата_завершения) >= datetime("{nach}") and datetime(Дата_завершения) < datetime("{konec}")"""
        rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)

        list_hz_mat = []

        for item in rez_mk:
            nom_mk = int(item['Пномер'])
            kol_vo_izd = int(item['Количество'])

            CMS.calc_and_fill_weight_by_xml_and_res(self, self.db_resxml, self.bd_naryad, self.bd_mat, nom_mk,
                                                    kol_vo_izd, DICT_FILTR,
                                                    DICT_MAT)
            # try:
            #    CMS.calc_and_fill_weight_by_xml(self,self.db_resxml,nom_mk,kol_vo_izd,self.bd_naryad)
        # except:
        #    print(f'Некорректные данные хмл {nom_mk}')

        # list_hz_mat = CMS.calc_and_fill_weight_by_res(self,self.db_resxml, nom_mk, DICT_FILTR, list_hz_mat, DICT_MAT)

        # F.save_file('unknown_mats.txt', list_hz_mat)
        return

    def add_time_tmp_empl(self, fio, norma, fact, month):
        if fio in self.Data.VID_RABOT_PO_EMPL:
            if self.Data.VID_RABOT_PO_EMPL[fio]['Этап'] == 'Сборка+сварка':
                fiod = fio + "|" + "&"
                if fio in self.DICT_EMPLOEE_FULL:
                    fiod = fio + "|" + self.DICT_EMPLOEE_FULL[fio]['Должность']
                if fiod not in self.dict_tmp_emp_min[month]:
                    self.dict_tmp_emp_min[month][fiod] = {'Норм': 0, 'Факт': 0}
                self.dict_tmp_emp_min[month][fiod]['Норм'] += norma
                self.dict_tmp_emp_min[month][fiod]['Факт'] += fact

    def add_time(self, item, minut_old):
        def add__(self, fio, minut_old):
            if fio in self.Data.VID_RABOT_PO_EMPL:
                if self.Data.VID_RABOT_PO_EMPL[fio]['Этап'] == 'Сборка+сварка':
                    minut_old += F.valm(item['Твремя'])
            else:
                print(f"{fio} не найден в емплое")
            return minut_old

        if item['ФИО'] != '':
            minut_old = add__(self, item['ФИО'], minut_old)
        if item['ФИО2'] != '':
            minut_old = add__(self, item['ФИО2'], minut_old)
        return minut_old

    def add_time_f(self, item, minut_old):
        def add__(self, fio, minut_old, fact_time):
            if fio in self.Data.VID_RABOT_PO_EMPL:
                if self.Data.VID_RABOT_PO_EMPL[fio]['Этап'] == 'Сборка+сварка':
                    minut_old += F.valm(fact_time)
            else:
                print(f"{fio} не найден в емплое")
            return minut_old

        if item['ФИО'] != '':
            minut_old = add__(self, item['ФИО'], minut_old, item['Фвремя'])
        if item['ФИО2'] != '':
            minut_old = add__(self, item['ФИО2'], minut_old, item['Фвремя2'])
        return minut_old

    # get_ves_from_res_and_xml() #ПЕРСЧЕТ норм По ресурсной включать раз месяц
    if F.strtodate(nach) < F.strtodate('01.01.2024', "%d.%m.%Y"):
        CQT.msgbox(f'Дата начала слишком ранняя')
        return

        # ====================Подсчет выработки =================

    custom_request_c = f"""SELECT mk.Вес, naryad.Твремя, naryad.ДСЕ_ID, naryad.Операции, naryad.Опер_время, naryad.Номер_мк, naryad.Внеплан, naryad.ФИО, naryad.ФИО2,  
            naryad.Фвремя, naryad.Фвремя2, naryad.Подтвержд_вып_дата, naryad.Виды_работ, naryad.Пномер FROM naryad INNER JOIN
             mk ON mk.Пномер = naryad.Номер_мк WHERE
        datetime(naryad.Подтвержд_вып_дата) > datetime("{nach}") and 
        datetime(naryad.Подтвержд_вып_дата) <= datetime("{konec}") AND naryad.Внеплан = 0 AND naryad.Подтвержд_вып == 1"""
    query = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)

    rez = dict()
    self.dict_tmp_emp_min = dict()
    for item in query:
        month = F.datetostr(F.strtodate(item['Подтвержд_вып_дата']), "%Y-%m")

        if month not in rez:
            rez[month] = {'minut': 0, 'minut_fact': 0, 'days': dict(), 'ves': 0, 'ves_list': 0, 'ves_xml': 0,
                          'ves_kplan': 0}
        minut = 0
        minut_f = 0

        minut = add_time(self, item, minut)
        minut_f = add_time_f(self, item, minut_f)

        rez[month]['minut'] += minut
        rez[month]['minut_fact'] += minut_f

    for item in query:
        month = F.datetostr(F.strtodate(item['Подтвержд_вып_дата']), "%Y-%m")
        if month not in self.dict_tmp_emp_min:
            self.dict_tmp_emp_min[month] = dict()

        teor = F.valm(item['Твремя'])
        if item['ФИО'] != '':
            add_time_tmp_empl(self, item['ФИО'], teor, F.valm(item['Фвремя']), month)
        if item['ФИО2'] != '':
            add_time_tmp_empl(self, item['ФИО2'], teor, F.valm(item['Фвремя2']), month)

    # ===================подсчет постов   days ========================================
    custom_request_c = f"""SELECT jurnal.Дата, jurnal.ФИО FROM jurnal WHERE datetime(jurnal.Дата) > datetime("{nach}") 
            and datetime(jurnal.Дата) < datetime("{konec}")"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
    for item in rez_jur:
        data = F.datetostr(F.strtodate(item['Дата']), '%Y-%m-%d')
        month = F.datetostr(F.strtodate(item['Дата']), "%Y-%m")
        if month not in rez:
            rez[month] = {'minut': 0, 'minut_fact': 0, 'days': dict(), 'ves': 0, 'ves_list': 0, 'ves_xml': 0,
                          'ves_kplan': 0}
        if data not in rez[month]['days']:
            rez[month]['days'][data] = set()
        if item['ФИО'] in self.Data.VID_RABOT_PO_EMPL:
            if self.Data.VID_RABOT_PO_EMPL[item['ФИО']]['Этап'] == 'Сборка+сварка':
                rez[month]['days'][data].add(item['ФИО'])
        else:
            print(f"{item['ФИО']} не учтен в расчтете постов")
    # =====================================================================================

    # ===================подсчет веса по МК,КД,РЕС   ========================================
    custom_request_c = f"""SELECT plan.МК, пл_топ.Уд_вес_ВО as Вес_ВО, "" as used FROM plan INNER JOIN пл_топ ON пл_топ.НомПл = plan.Пномер WHERE plan.МК != 0"""
    rez_kplan_ves_kd = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, custom_request_c, rez_dict=True), 'МК')

    custom_request_c = f"""SELECT mk.Пномер, mk.Номер_заказа, mk.Номер_проекта, mk.Вес, mk.Дата_завершения, mk.Ресурсная, mk.xml, mk.Количество, mk.Тип,
     zagot.Вес_по_рес FROM mk INNER JOIN zagot ON zagot.Ном_МК = mk.Пномер WHERE mk.Дата_завершения != ""
            and datetime(mk.Дата_завершения) >= datetime("{nach}") and datetime(mk.Дата_завершения) < datetime("{konec}")"""
    rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)

    viv = []
    minus = 0
    list_err = []
    for item in rez_mk:
        # print(f'МК {item["Пномер"]}')
        viv.append(
            [item["Пномер"], item["Номер_заказа"], item["Номер_проекта"], item["Вес"], item["Вес_по_рес"], item["xml"]])
        month = F.datetostr(F.strtodate(item['Дата_завершения']), "%Y-%m")
        if month not in rez:
            rez[month] = {'minut': 0, 'minut_fact': 0, 'days': dict(), 'ves': 0, 'ves_list': 0, 'ves_xml': 0,
                          'ves_kplan': 0}

        rez[month]['ves_list'] += item['Вес_по_рес'] * KOEF_RASKLADKI
        rez[month]['ves'] += item['Вес']
        # print(f"вес по МК  {item['Вес']}| сумм:{rez[month]['ves']}")
        if item['xml'] == '' and item['Тип'] == 1:
            list_err.append([f'МК {item["Пномер"]} не загружен вес xml в МК'])

        rez[month]['ves_xml'] += F.valm(item['xml'])
        print(
            f"Номер_заказа {item['Номер_заказа']}   Номер_заказа {item['Номер_заказа']}   Пномер {item['Пномер']}  Вес: {item['Вес']} xml: {F.valm(item['xml'])}")
        print(f"вес ХМЛ  {F.valm(item['xml'])}| сумм:{rez[month]['ves_xml']}")
        if item["Пномер"] in rez_kplan_ves_kd:
            if rez_kplan_ves_kd[item["Пномер"]]['used'] == '':
                rez_kplan_ves_kd[item["Пномер"]]['used'] = '+'
                rez[month]['ves_kplan'] += F.valm(rez_kplan_ves_kd[item['Пномер']]['Вес_ВО'])
                print(f"вес ВО  {F.valm(rez_kplan_ves_kd[item['Пномер']]['Вес_ВО'])}| сумм:{rez[month]['ves_kplan']}")
            else:
                minus += F.valm(rez_kplan_ves_kd[item['Пномер']]['Вес_ВО'])
        else:
            #rez[month]['ves_kplan'] += F.valm(item['xml'])
            print(f"не найдент весВО , принято хМЛ {F.valm(item['xml'])}| сумм:{rez[month]['ves_kplan']}")

        print(f"")
    # =====================================================================================
    print(f'minus {minus}')
    if len(list_err) > 0:
        CQT.msgbox(pprint.pformat(list_err))
        return
    F.save_file('viv_ves.txt', viv)

    rez_tbl = [['Месяц', 'Постов', 'Выработка, н-недель', 'Присутствие, недель', 'Произв-ть % н-смен/пост',
                'Вес Рес.ИЗД, т. без скелета', 'Вес Рес.только лист без скелета, т.', 'Вес хмл КО, т.', 'Вес по черт.']]
    list_month = sorted(rez.keys())
    for month in list_month:
        name_table = F.datetostr(F.strtodate(month, "%Y-%m"), 'mtdz_%Y_%m_01')
        rab_dn_count = 0
        q_days = CSQ.custom_request_c(self.bd_users, f"""SELECT * FROM {name_table} WHERE Пномер = 1""")
        for j in range(3, len(q_days[0])):
            if q_days[1][j] == 0:
                rab_dn_count += 1
        list_count_days = []
        for day in rez[month]['days']:
            list_count_days.append(len(rez[month]['days'][day]))
        postov = sum(list_count_days) / rab_dn_count / 2
        virabotka = rez[month]['minut'] / 450 / 2 * KOEF_NORMIROVSCHICI
        prisutstvie = rez[month]['minut_fact'] / 450 / 2
        proizv = virabotka / postov / rab_dn_count * 100
        virabotka = virabotka / 7
        prisutstvie = prisutstvie / 7
        rez_tbl.append([month, round(postov, 1), round(virabotka), round(prisutstvie), round(proizv, 2),
                        round(rez[month]['ves'] / 1000, 2),
                        round(rez[month]['ves_list'] / 1000, 2),
                        round(rez[month]['ves_xml'] / 1000, 2),
                        round(rez[month]['ves_kplan'] / 1000, 2),
                        ])

    load_browser(self)
    create_gant(self, rez_tbl)
    rez_tbl.append(['' for _ in rez_tbl[0]])
    rez_tbl.append(['' for _ in rez_tbl[0]])
    return rez_tbl


def jurnal_zamech_dinamic(self, nach, konec, generate_chart=True):
    data = jurnal_zamech(self, nach, konec, False)
    data = F.list_of_lists_to_list_of_dicts(data[:-2])
    dict_month = dict()
    dict_podr = dict()
    for item in data:
        kod_vp = item['Рц_вп']
        if kod_vp in self.DICT_RC:
            kod_vp = self.DICT_RC[kod_vp]['empl_Подразделение']
        if kod_vp not in dict_podr:
            dict_podr[kod_vp] = 0
            dict_podr[kod_vp + "(принятые)"] = 0
    for item in data:
        if F.is_date(item['Дата_создания']):
            kod_vp = item['Рц_вп']
            if kod_vp in self.DICT_RC:
                kod_vp = self.DICT_RC[kod_vp]['empl_Подразделение']
            month = F.datetostr(F.strtodate(item['Дата_создания']), "%Y-%m")
            if month not in dict_month:
                dict_month[month] = copy.deepcopy(dict_podr)
            dict_month[month][kod_vp] += 1
            if not item['Код_вп'] == 'возражаю(см_пояснение)':
                dict_month[month][kod_vp + "(принятые)"] += 1

    list_dicts = []
    for month in dict_month.keys():
        tmp = {'month': month}
        for k, v in dict_month[month].items():
            tmp[k] = v
        list_dicts.append(tmp)
    
    if generate_chart:
        try:
            load_browser(self)
            create_gant(self, list_dicts)
        except:
            print(f'err create_gant')
            pass
    return F.list_of_dicts_to_list_of_lists(list_dicts)


def jurnal_zamech(self, nach, konec, generate_chart=True):
    custom_request_c = f"""SELECT zamech.Пномер,
zamech.Дата_создания,
mk.Номенклатура,
mk.Номер_заказа,
mk.Номер_проекта,
mk.Вид,
zamech.Инициатор,
zamech.Виновное_подразделение,
zamech.Виновное_подразделение as Рц_вп,
zamech.Фсмещение_дней,
zamech.Фпотери_времени_час,
zamech.Фпотери_материала_марка,
zamech.Фпотери_материала_вес,
zamech.Содержание,
kod_zamech.Имя as Код_замечания,
zamech.Примечание,
zamech.Пояснение_вп,
kod_zamech_vp.Имя as Код_вп,
zamech.Ответственный,
zamech.ФИО_виновный
FROM zamech 
INNER JOIN mk ON mk.Пномер = zamech.МК
INNER JOIN kod_zamech ON kod_zamech.Пномер = zamech.Код
INNER JOIN kod_zamech_vp ON kod_zamech_vp.Пномер = zamech.Код_вп
    WHERE 
                           datetime(zamech.Дата_создания) > datetime("{nach}") 
                           and datetime(zamech.Дата_создания) < datetime("{konec}")"""
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True)
    nk_podr = F.num_col_by_name_in_hat_c(rez, 'Виновное_подразделение')
    for i in range(len(rez)):
        if rez[i][nk_podr] in self.DICT_RC:
            rez[i][nk_podr] = self.DICT_RC[rez[i][nk_podr]]['Сокр_наим_СТО']
        else:
            print(f'podr не найден в бд')
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    if generate_chart:
        try:
            load_browser(self)
            create_gant(self, rez)
        except:
            print(f'err create_gant')
            pass
    return rez

def load_browser(self):
    try:
        self.parent_for_grafic.removeWidget(self.browser)
        self.browser.deleteLater()
    except Exception:
        pass

    self.browser = QtWebEngineWidgets.QWebEngineView(self)

    layout = self.parent_for_grafic
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    layout.addWidget(self.browser)

@CQT.onerror
def report_matrix_competence_by_depatment(self:mywindow, start:str, end:str)->list[dict]:
    tbl_data = MTXCMP.gen_report_data_by_department(start,end)

    def fnc_gen_grafic_departments(parent_self, data: list[dict]):


        from collections import defaultdict


        if not data:
            return

        # ----------------------------------
        # 1. Группировка по подразделению
        # ----------------------------------
        data_by_dep = defaultdict(list)
        for row in data:
            data_by_dep[row['id_depatment_mes']].append(row)

        fig = go.Figure()
        target_value = data[0]['Целевой балл']

        # ----------------------------------
        # 2. Строим линию для каждого подразделения
        # ----------------------------------
        for dep_id, dep_rows in data_by_dep.items():

            dep_name = dep_rows[0]['Подразделение']

            by_date_changes = defaultdict(list)
            value_by_date = {}

            for row in dep_rows:
                day = F.strtodate(row['Дата'], '%Y-%m-%d')

                by_date_changes[day].append(
                    f"<b>{row['ФИО']}</b><br>"
                    f"Было: {row['Было']} → Стало: {row['Стало']}<br>"
                    f"{row['Компетенция']}"
                )

                value_by_date[day] = max(
                    value_by_date.get(day, 0),
                    row['Балл по цеху']
                )

            dates_sorted = sorted(by_date_changes.keys())
            y_values = [value_by_date[d] for d in dates_sorted]

            # Ограничение размера тултипа
            hover_text = []
            for d in dates_sorted:
                changes = by_date_changes[d]

                max_rows = 10
                if len(changes) > max_rows:
                    visible = changes[:max_rows]
                    hidden_count = len(changes) - max_rows
                    visible.append(f"<br><i>... ещё {hidden_count} записей</i>")
                    hover_text.append("<br><br>".join(visible))
                else:
                    hover_text.append("<br><br>".join(changes))

            clr = 'rgba(55,55,55,0.57)'
            if data_by_dep[dep_id]:
                clr = f"rgba({data_by_dep[dep_id][0]['_color_dep']},1)"
            fig.add_trace(
                go.Scatter(
                    x=dates_sorted,
                    y=y_values,
                    mode='lines+markers',
                    name=dep_name,
                    customdata=hover_text,
                    line=dict(
                        color=clr,
                        width=2
                    ),
                    hovertemplate=
                    'Дата: %{x|%d.%m.%Y}<br><br>'
                    '%{customdata}'
                    '<extra></extra>'
                )
            )

        # ----------------------------------
        # 3. Линия целевого балла
        # ----------------------------------
        all_dates = sorted(
            set(
                F.strtodate(r['Дата'], '%Y-%m-%d')
                for r in data
            )
        )

        fig.add_trace(
            go.Scatter(
                x=all_dates,
                y=[target_value] * len(all_dates),
                mode='lines',
                name='Целевой балл',
                line=dict(color='red', width=2, dash='dash')
            )
        )

        # ----------------------------------
        # 4. Настройка отображения
        # ----------------------------------
        fig.update_layout(
            template='plotly_white',
            xaxis=dict(
                title='Дата',
                type='date',
                tickformat='%d.%m.%Y'
            ),
            yaxis=dict(
                title='Балл'
            ),
            hoverlabel=dict(
                align='left',
                font=dict(size=11,color='rgba(22,22,22,0.97)'),
                bgcolor='rgba(255,255,255,0.57)',
                bordercolor='rgba(120,120,120,0.5)'
            ),
            legend=dict(
                orientation='v',
                x=1.02,
                y=1,
                xanchor='left'
            ),
            margin=dict(l=60, r=180, t=40, b=40)
        )

        # ----------------------------------
        # 5. Вывод
        # ----------------------------------
        load_browser(parent_self)
        try:
            CQT.output_gant(
                parent_self,
                fig,
                parent_self.browser,
                'График_подразделений'
            )
        except PermissionError:
            import tempfile
            CQT.output_gant(
                parent_self,
                fig,
                parent_self.browser,
                'График_подразделений',
                dir=tempfile.gettempdir()
            )

        tab = parent_self.ui.tabw_otchet
        tab.setCurrentIndex(
            CQT.number_table_by_name_c(tab, 'График')
        )

    fnc_gen_grafic_departments(self, tbl_data)
    return tbl_data

@CQT.onerror
def  report_matrix_competence(self:mywindow, day:str):

    def fnc_gen_grafic_user_btn(self, parent_self: mywindow, row, column, user: MTXCMP.User):
        fnc_gen_grafic_user(parent_self,user)
    
    def fnc_gen_grafic_user(parent_self:mywindow, user:MTXCMP.User):

        users_map = CSQ.custom_request_c(CFG.Config.project.db_users,
                            f"""SELECT competence_vals.value, 
                            competence_vals.created_at, competence_vals.id_comp
                  FROM competence_vals
                       
                 WHERE 
                       competence_vals.id_user == "{user.ID_ФизЛица}"
                 ORDER BY competence_vals.created_at;
                """,rez_dict=True)


        def color_by_user(user_id: str) -> str:
            base = abs(hash(user_id)) % 360
            return f'hsl({base}, 65%, 45%)'

        

        def color_by_value(value: int) -> str:
            r, g, b = CMS.Color_tbl(value*25,dark_mode=True).rgb
            return f'rgb({r},{g},{b})'
        
        
        load_browser(parent_self)

        total_by_date = {}
        comp_count = len(user.base_competencies.COMPETENCE_SHABL)
        list_all_dates = sorted(list(set([r['created_at'] for r in users_map])))

        fig = go.Figure()
        for comp_data in user.base_competencies.COMPETENCE_SHABL:
            comp_id = comp_data['params_s_num']
            comp_name = comp_data['params_name_competence']
            user_points = [r for r in users_map if r['id_comp'] == comp_id]

            

            for r in user_points:
                day = r['created_at']
                if day not in total_by_date:
                    total_by_date[day] = 0
                total_by_date[day] += r['value']

            if not user_points:
                continue

            user_points.sort(key=lambda x: x['created_at'])

            x_dates = [r['created_at'] for r in user_points]
            y_fio = [comp_name] * len(user_points)
            values = [r['value'] for r in user_points]

            # ======расчет цветов линий======
            koef_color_line = 50
            if len(values) > 1:
                if values[-2] > values[-1]:
                    koef_color_line = 0
                if values[-2] < values[-1]:
                    koef_color_line = 100

            for all_date in list_all_dates:
                if all_date>x_dates[-1]:
                    x_dates.append(all_date)
                    y_fio.append(comp_name)
                    values.append(values[-1])

            weak_marks = set()
            for i, val in enumerate(values):
                if i>0 and values[i] == values[i-1]:
                    weak_marks.add(i)
                
            


            r, g, b = CMS.Color_tbl(koef_color_line, dark_mode=True).rgb
            color_line = f'rgb({r},{g},{b})'
            #==========================================
            line_width = 3
            fig.add_trace(
                go.Scatter(
                    x=x_dates,
                    y=y_fio,
                    mode='lines+markers',
                    name=comp_name,
                    line=dict(
                        color=color_line,
                        width=line_width
                    ),
                    marker=dict(
                        size=[6 + v * line_width if i not in weak_marks else line_width for i, v in enumerate(values)],
                        color=[color_by_value(v) for v in values] ,
                        line=dict(width=0.5, color='rgba(0,0,0,0.4)')
                    ),
                    hovertemplate=

                    'Дата: %{x|%d.%m.%Y}<br>' +
                    'Оценка: %{customdata}',
                    customdata=values
                )
            )

        if total_by_date:
            dates_sorted = sorted(total_by_date.keys())
            avg_values = [
                round(total_by_date[d] / comp_count, 2)
                for d in dates_sorted
            ]

            fig.add_trace(
                go.Scatter(
                    x=dates_sorted,
                    y=['Итоговый балл'] * len(dates_sorted),
                    mode='lines+markers',
                    name='Итоговый балл',
                    line=dict(
                        color='rgb(120,80,80)',
                        width=3
                    ),
                    marker=dict(
                        size=[6 + v * 3 for v in avg_values],
                        color=[color_by_value(int(round(v))) for v in avg_values],
                        line=dict(width=1, color='rgba(0,0,0,0.6)')
                    ),
                    hovertemplate=

                    'Дата: %{x|%d.%m.%Y}<br>'
                    'Средний балл: %{customdata}',
                    customdata=avg_values
                )
            )

        fig.update_layout(
             autosize=True,
            title=dict(
                text=
                f'Компетенции для {user.ФИО} ({user.Должность})<br>'
                '<span style="font-size:9px;color:rgb(80,80,80);line-height:50%;display:block;text-align:left">'
                '<b>Критерии оценки:</b><br>'
'1 — начальный уровень, теория | 2 — работает самостоятельно под наблюдением | 3 — выполняет самостоятельно, нужное качество и количество | 4 — эксперт, способен обучать',
                x=0.5,  # центр по графику
                xanchor='center'
            ),

            template='plotly_white',
            xaxis=dict(
                title='Дата',
                type='date',
                tickformat='%d.%m.%Y',
                showgrid=True
            ),
            yaxis=dict(
                domain=[0.02, 0.98]
            ),
            legend=dict(
                orientation='v',
                x=1.0,
                y=0.8,
                xanchor='left',
                yanchor='top'
            ),

            margin=dict(l=100,
                        r=160,
                        t=40,
                        b=40)
        )
        try:
            CQT.output_gant(parent_self, fig, parent_self.browser, parent_self.vid_report_c + '_' + parent_self.ui.cmb_podrazdelenie.currentText())
        except PermissionError: #05.02.2026
            import tempfile
            CQT.output_gant(parent_self, fig, parent_self.browser,
                            parent_self.vid_report_c + '_' + parent_self.ui.cmb_podrazdelenie.currentText(),
                            dir=tempfile.gettempdir()
                            )

        tab = parent_self.ui.tabw_otchet
        tab.setCurrentIndex(CQT.number_table_by_name_c(tab,'График'))
        return

    def fnc_gen_grafic_comp(self:mywindow, comp:MTXCMP.Competence):
        CQT.msgbox(f'В разработке')
        return
        users_map = CSQ.custom_request_c(CFG.Config.project.db_users,
                            f"""SELECT competence_vals.value, 
                            competence_vals.created_at, competence_vals.id_comp
                  FROM competence_vals
                       
                 WHERE 
                       competence_vals.id_user == "{user.ID_ФизЛица}"
                 ORDER BY competence_vals.created_at;
                """,rez_dict=True)


        def color_by_user(user_id: str) -> str:
            base = abs(hash(user_id)) % 360
            return f'hsl({base}, 65%, 45%)'

        

        def color_by_value(value: int) -> str:
            r, g, b = CMS.Color_tbl(value*25,dark_mode=True).rgb
            return f'rgb({r},{g},{b})'
        
        
        load_browser(parent_self)

        total_by_date = {}
        comp_count = len(user.base_competencies.COMPETENCE_SHABL)
        
        fig = go.Figure()
        for comp_data in user.base_competencies.COMPETENCE_SHABL:
            comp_id = comp_data['params_s_num']
            comp_name = comp_data['params_name_competence']
            user_points = [r for r in users_map if r['id_comp'] == comp_id]

            

            for r in user_points:
                day = r['created_at']
                if day not in total_by_date:
                    total_by_date[day] = 0
                total_by_date[day] += r['value']

            if not user_points:
                continue

            user_points.sort(key=lambda x: x['created_at'])

            x_dates = [r['created_at'] for r in user_points]
            y_fio = [comp_name] * len(user_points)
            values = [r['value'] for r in user_points]
            weak_marks = set()
            for i, val in enumerate(values):
                if i>0 and values[i] == values[i-1]:
                    weak_marks.add(i)
                
            
            #======расчет цветов линий======
            koef_color_line = 50
            if len(values) > 1:
                if values[-2] > values[-1]:
                    koef_color_line = 0
                if values[-2] < values[-1]:
                    koef_color_line = 100

            r, g, b = CMS.Color_tbl(koef_color_line, dark_mode=True).rgb
            color_line = f'rgb({r},{g},{b})'
            #==========================================
            line_width = 3
            fig.add_trace(
                go.Scatter(
                    x=x_dates,
                    y=y_fio,
                    mode='lines+markers',
                    name=comp_name,
                    line=dict(
                        color=color_line,
                        width=line_width
                    ),
                    marker=dict(
                        size=[6 + v * line_width if i not in weak_marks else line_width for i, v in enumerate(values)],
                        color=[color_by_value(v) for v in values] ,
                        line=dict(width=0.5, color='rgba(0,0,0,0.4)')
                    ),
                    hovertemplate=

                    'Дата: %{x|%d.%m.%Y}<br>' +
                    'Оценка: %{customdata}',
                    customdata=values
                )
            )

        if total_by_date:
            dates_sorted = sorted(total_by_date.keys())
            avg_values = [
                round(total_by_date[d] / comp_count, 2)
                for d in dates_sorted
            ]

            fig.add_trace(
                go.Scatter(
                    x=dates_sorted,
                    y=['Итоговый балл'] * len(dates_sorted),
                    mode='lines+markers',
                    name='Итоговый балл',
                    line=dict(
                        color='rgb(120,80,80)',
                        width=3
                    ),
                    marker=dict(
                        size=[6 + v * 3 for v in avg_values],
                        color=[color_by_value(int(round(v))) for v in avg_values],
                        line=dict(width=1, color='rgba(0,0,0,0.6)')
                    ),
                    hovertemplate=

                    'Дата: %{x|%d.%m.%Y}<br>'
                    'Средний балл: %{customdata}',
                    customdata=avg_values
                )
            )

        fig.update_layout(
             autosize=True,
            title=dict(
                text=
                f'Компетенции для {user.ФИО} ({user.Должность})<br>'
                '<span style="font-size:9px;color:rgb(80,80,80);line-height:50%;display:block;text-align:left">'
                '<b>Критерии оценки:</b><br>'
'1 — начальный уровень, теория | 2 — работает самостоятельно под наблюдением | 3 — выполняет самостоятельно, нужное качество и количество | 4 — эксперт, способен обучать',
                x=0.5,  # центр по графику
                xanchor='center'
            ),

            template='plotly_white',
            xaxis=dict(
                title='Дата',
                type='date',
                tickformat='%d.%m.%Y',
                showgrid=True
            ),
            yaxis=dict(
                domain=[0.02, 0.98]
            ),
            legend=dict(
                orientation='v',
                x=1.0,
                y=0.8,
                xanchor='left',
                yanchor='top'
            ),

            margin=dict(l=100,
                        r=160,
                        t=40,
                        b=40)
        )

        CQT.output_gant(parent_self, fig, parent_self.browser, parent_self.vid_report_c + '_' + parent_self.ui.cmb_podrazdelenie.currentText())
        tab = parent_self.ui.tabw_otchet
        tab.setCurrentIndex(CQT.number_table_by_name_c(tab,'График'))
        return

    @CQT.onerror
    def fncContextMenu(self: mywindow, tbl: QtWidgets.QTableWidget, row: int, col: int,
                       menu_builder: CQT.ContextMenuBuilder):
        EXCLUDE_COLUMNS_NAME = {
        'ФИО',
        'Должность',
        'Ответственный',
        'Итоговыйбалл',
        }
        def fnc_set_state(self: mywindow, s_num_state: int, list_s_num: tuple[int]):
            r, g, b = self.Data_plan.DICT_STATUS_POZ[s_num_state]['color'].split(';')
            state_name = self.Data_plan.DICT_STATUS_POZ[s_num_state]['Имя']
            CSQ.custom_request_c(cfg.db_kplan,
                                 f"""UPDATE plan SET (Статус) = ({s_num_state}) 
                                     WHERE Пномер in ({CSQ.prepare_list_to_tuple(list_s_num)})""")
            with CQT.table_updating(tbl):
                for row_tbl in range(tbl.rowCount()):
                    if int(tbl.item(row_tbl, nf['plan.Пномер']).text()) in list_s_num:
                        tbl.item(row_tbl, nf['plan.Статус']).setText(state_name)
                        CQT.set_color_wtab_c(tbl, row_tbl, nf['plan.Статус'], r, g, b)

        emoji: CEMOJ.EmojiItem = CEMOJ.EmojiMain.ДокументыДанные.analysis
        menu_builder.add_submenu(f"{emoji.symbol} График")
        
        nf = CQT.nums_col_by_name_dict(tbl)
        row_data = CQT.get_dict_line_form_tbl(tbl)
        col_name = tbl.horizontalHeaderItem(col).data(CQT.Qt.UserRole)

        emoji: CEMOJ.EmojiItem = CEMOJ.EmojiMain.ПерсоналРоли.operator
        user = comps.get_usr(tbl.item(row, nf['ID_ФизЛица']).text())
        fnc = partial(fnc_gen_grafic_user, self, user)
        menu_builder.add_menu(f'{emoji.symbol} По персоналу',
                              fnc)
        
        if col_name not in EXCLUDE_COLUMNS_NAME and F.is_numeric(col_name):
            comp_num = int(col_name)
            if comp_num  in comps.DICT_COMPETENCE_SHABL:
                comp = comps.DICT_COMPETENCE_SHABL[comp_num]
                emoji: CEMOJ.EmojiItem = CEMOJ.EmojiMain.ПерсоналРоли.training 
                fnc = partial(fnc_gen_grafic_comp, self, comp)
                menu_builder.add_menu(f'{emoji.symbol} По компетенции',
                                      fnc)


    cmb = self.ui.cmb_addit_sort_c_report
    depatment = cmb.currentData(CQT.Qt.UserRole)
    if depatment == '':
        CQT.msgbox(f'Не выбран цех')
        return

    tbl = MTXCMP.Tbl_comp(self.ui.tbl_report_c)
    comps = MTXCMP.Competencies(depatment, tbl,self.ui.tbl_report_c_filtr)
    from dataClass import data_app as DTCLS
    DTCLS.obj_Competencies = comps
    comps.refill()
    nf = CQT.nums_col_by_name_dict(tbl.tbl)

    CQT.add_context_menu(tbl.tbl, self, fncContextMenu)

    for i in range(tbl.tbl.rowCount()):
        val = tbl.tbl.item(i,nf['ФИО']).text()
        user = comps.get_usr(tbl.tbl.item(i,nf['ID_ФизЛица']).text())
        widg = CQT.add_interactive_label(tbl.tbl, i, nf['ФИО'], val,
                                         parent_self=self,grab_style_from_cell=True)

        widg.add_button('', 'График',
                        fnc_gen_grafic_user_btn,
                        cell_val=user, img_path=F.sep().join([F.path_to_execut_file_c(),
                                                              'icons', 'trending-up']))




@CQT.onerror
def not_upload_erp_nar(self:mywindow, nach_data, kon_data):
    mark_sudden_tasks = USRCNF.Config.place.КодыНарядов.Плановая #24.12.2025
    custom_request_c = f"""
        SELECT 
            strftime('%d.%m.%Y',jurnal.Дата) as Дата, 
            CASE WHEN знпр.№ERP IS NOT NULL 
                THEN знпр.№ERP 
                ELSE mk.Номер_заказа 
            END AS ПУ, 
            CASE WHEN знпр.№проекта IS NOT NULL 
                THEN знпр.№проекта 
                ELSE mk.Номер_проекта 
            END AS "Номер проекта", 
            jurnal.ФИО,
            "" as Должность, 
            "" as Подразделение,  
            naryad.Пномер as 'Номер наряда',
            naryad.Подтвержд_вып_дата as Подтвержден,
            jurnal.Подытог_нормы as "Труды в ЕРП",
            jurnal.Дата_выгрузки_ЕРП as "Выгружено в ЕРП"
        FROM jurnal
            INNER JOIN naryad ON naryad.Пномер == jurnal.Номер_наряда 
            INNER JOIN mk ON mk.Пномер == naryad.Номер_мк 
            LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
            LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
        WHERE  naryad.Внеплан == {mark_sudden_tasks} 
            and jurnal.Статус == 'Начат' 
            and datetime(jurnal.Дата) > datetime("{nach_data}") 
            and datetime(jurnal.Дата) < datetime("{kon_data}")
               """
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True,attach_dbs=(self.db_kplan))
    for item in rez:
        if item['ФИО'] in self.DICT_EMPLOEE_FULL_WITH_DEL:
            item['Должность'] = self.DICT_EMPLOEE_FULL_WITH_DEL[item['ФИО']]['Должность']
            item['Подразделение'] = self.DICT_EMPLOEE_FULL_WITH_DEL[item['ФИО']]['Подразделение']
            
    rez = F.sort_by_column_c(rez,'Номер наряда',)
    rez = F.sort_by_column_c(rez, 'ФИО', )
    rez = F.sort_by_column_c(rez, 'ПУ', )
    rez = F.sort_by_column_c(rez, 'Дата',date_time=True ,date_format='%d.%m.%Y')
    rez = F.sort_by_column_c(rez, "Подтвержден") 
    rez = F.sort_by_column_c(rez, "Выгружено в ЕРП" )
    
    rez = F.list_of_dicts_to_list_of_lists(rez)
    return rez

def dinam_proizv_sotr(self:mywindow, nach_data, kon_data, fio):
    nach_data_obj =  F.strtodate(nach_data)
    kon_data_obj = F.strtodate(kon_data)
    custom_request_c = f"""SELECT 
                            naryad.ФИО, 
                            naryad.Фвремя, 
                            naryad.ФИО2, 
                            naryad.Фвремя2, 
                            naryad.Твремя, 
                            naryad.Норма_времени,
                            naryad.Подтвержд_вып_дата
                          FROM naryad
                           WHERE (naryad.ФИО == "{fio}" OR naryad.ФИО2 == "{fio}") AND   naryad.Внеплан == 0 and naryad.Подтвержд_вып == 1 
                           and datetime(naryad.Подтвержд_вып_дата) > datetime("{nach_data}") 
                           and datetime(naryad.Подтвержд_вып_дата) < datetime("{kon_data}")
               """
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)

    dict_week = dict()
    for item in rez:
        count_user = 1
        if item['ФИО'] != '' and item['ФИО2'] != '':
            count_user = 2
        fact = None
        if item['ФИО'] == fio:
            fact = item['Фвремя']
        if item['ФИО2'] == fio:
            fact = item['Фвремя2']
        if fact == None:
            print(f'Не найден {fio} в наряде {item}')
            continue


        if item['Подтвержд_вып_дата'] == '' or not F.is_date(item['Подтвержд_вып_дата']):
            continue
        week = F.start_end_dates_c(item['Подтвержд_вып_дата'],vid='n',format_out= "%Y-%m-%d")[0]
        if week not in dict_week:
            dict_week[week] = {'Факт':0,
                               'Твремя':0,
                               'Норма':0}

        dict_week[week]['Факт'] += fact
        dict_week[week]['Твремя'] += item['Твремя']
        dict_week[week]['Норма'] += item['Норма_времени']

    list_week = [ {'week':k,'Факт':round(v['Факт']),'Твремя':round(v['Твремя']),'Норма':round(v['Норма']),} for k,v in dict_week.items()]
    list_week = F.sort_by_column_c(list_week,'week',False,True,"%Y-%m-%d",False)
    create_gant(self, list_week)
    list_week.append({k:'' for k,v in list_week[0].items()})
    list_week.append({k:'' for k,v in list_week[0].items()})

    return  list_week

def otkl_tabel_trdz(self:mywindow, nach_data, kon_data, podrazd):
    nach_data_obj =  F.strtodate(nach_data)
    kon_data_obj = F.strtodate(kon_data)
    
    SET_PODRAZD = {'Заготовительный',
'Механическая обработка',
'Слесарно-каркасные и сборочно-сварочые работы',
'Нанесение покрытия',
'Производство',
'Отдел комплектации',
'Ремонтный цех Производства',
}
    division_nums = ','.join([str(_['СКУД_id']) for _ in self.DICT_RC.values() if _['СКУД_id'] != None and _['Имя'] in SET_PODRAZD])
    client = SCUD.PerkoClient()
    params = SCUD.PerkoParams(
        dateBegin=F.datetostr(nach_data_obj,"%Y-%m-%d"),
        dateEnd=F.datetostr(kon_data_obj,"%Y-%m-%d"),
        division=division_nums
    )
    result = client.time_tracking(params)
    dict_perco = dict()
    for data in result:
        time_min = 0
        list_presence_time = data['presence_time'].split(':')
        if len(list_presence_time) == 2:
            time_min = F.valm(list_presence_time[0]) * 60  + F.valm(list_presence_time[1])
        elif len(list_presence_time) == 1:
            time_min = F.valm(list_presence_time[0]) * 60
        dict_perco[data['fio']] = time_min


    SET_USED_PODR = {
        'Заготовительный цех Производства',
        'Отдел комплектации',
        'Цех механической обработки Производства',
        'Цех выпуска готовой продукции Производства',
        'Сборочный цех Производства',
    }
    set_fields_hat = {'Должность','Статус','Подразделение','ДатаИзмененияДолжности'}
    'Отчет по отклонениям табеля и трудозатрат'
    str_date_start = F.datetostr(nach_data_obj,"%Y-%m-%dT%H:%M:%S")
    str_date_kon = F.datetostr(kon_data_obj,"%Y-%m-%dT%H:%M:%S")
    m = ODAT.OrdersComposit(self.ERP_base_name)
    data_trdz_regisr = m.get_response('AccumulationRegister_ТрудозатратыКОформлению/',
                                         f"""BalanceAndTurnovers(StartPeriod=datetime'{str_date_start}', 
                                          EndPeriod=datetime'{str_date_kon}', 
                                          Condition='Организация_Key eq guid'{self.place.Организация_Key}'')?$select=Исполнитель, КоличествоOpeningBalance, 
                                            КоличествоTurnover, 
                                            КоличествоReceipt, 
                                            КоличествоExpense
                                            """)
    if not isinstance(data_trdz_regisr,list):
        CQT.msgbox(f'Ошибка загрузки базы из "{self.ERP_base_name}" {data_trdz_regisr}')
        return 
    dict_data_trdz_regisr = dict()
    for item in data_trdz_regisr:
        if item['Исполнитель'] not in dict_data_trdz_regisr:
            dict_data_trdz_regisr[item['Исполнитель']] = 0
        dict_data_trdz_regisr[item['Исполнитель']] += item['КоличествоReceipt']



    tabels = CMS.Tabels_erp(self.ERP_base_name)
    tabels.get_list_tab_headers()
    
    dict_tabs_filtred = dict()
    for tab in tabels.list_tab_headers:
        if tab.ПериодРегистрации.year == nach_data_obj.year and tab.ПериодРегистрации.month == nach_data_obj.month and tab.Комментарий.lower() =='фактическая явка':
            tab.load_data()
            dict_tabs_filtred[tab.Подразделение] = tab
            
    set_err = set()
    rez = []
    SET_USED_TIME_VID = {'Явка(Я)','Праздники(РВ)','Ночные часы(Н)'} 
    for name, item in self.Data.DICT_EMPL_FULL.items():
        if item['Статус'] == "Увольнение" and (item['ДатаИзмененияДолжности'] == '' or F.strtodate(item['ДатаИзмененияДолжности']) < nach_data_obj):
            continue
        if item['Подразделение'] in SET_USED_PODR and item['Режим'] != 'Абстракт':
            tmp_dict= dict()
            tmp_dict['ФИО'] = name

            for k,v in item.items():
                if k in set_fields_hat:
                    tmp_dict[k] = v
            tmp_dict['Табель, час.'] = 0

            if item['Подразделение'] in dict_tabs_filtred:
                if name in  dict_tabs_filtred[item['Подразделение']].data:
                    for vid_time in SET_USED_TIME_VID:
                        tmp_dict['Табель, час.'] += dict_tabs_filtred[item['Подразделение']].data[name]['dict_summ'][vid_time]
                else:
                    set_err.add(f'{name} не найден в табеле {tab.Number} {tab.ПериодРегистрации}')
            else:
                set_err.add(f"{item['Подразделение']} не найдено в табелях от {nach_data}")

            tmp_dict['Трудозатрат в этапах, час.'] = 0
            if item['ID_ФизЛица'] in dict_data_trdz_regisr:
                tmp_dict['Трудозатрат в этапах, час.'] = round(dict_data_trdz_regisr[item['ID_ФизЛица']]/60,2)
                
            tmp_dict['Отклонение трдз от таб,%'] = 0
            if tmp_dict['Табель, час.'] > 0:
                tmp_dict['Отклонение трдз от таб,%'] =round((tmp_dict['Табель, час.']-tmp_dict['Трудозатрат в этапах, час.'])/tmp_dict['Табель, час.']*100,2)
            else:
                if tmp_dict['Трудозатрат в этапах, час.'] > 0:
                    tmp_dict['Отклонение трдз от таб,%'] = 100
                    
            tmp_dict['СКУД, час.'] = -1
            if name in dict_perco:
                tmp_dict['СКУД, час.'] = round(dict_perco[name]/60,2)

            tmp_dict['Отклонение СКУД от таб,%'] = 0
            if tmp_dict['СКУД, час.'] == -1:
                tmp_dict['Отклонение СКУД от таб,%'] = 100
            else:
                if tmp_dict['Табель, час.'] > 0:
                    tmp_dict['Отклонение СКУД от таб,%'] = round(
                        (tmp_dict['Табель, час.'] - tmp_dict['СКУД, час.']) /
                        tmp_dict['Табель, час.'] * 100, 2)
                else:
                    if tmp_dict['Трудозатрат в этапах, час.'] > 0:
                        tmp_dict['Отклонение СКУД от таб,%'] = 100
            
            rez.append(tmp_dict)
            
            
            

    rez = F.sort_by_column_c(rez,'Отклонение трдз от таб,%')
    rez = F.sort_by_column_c(rez, 'Подразделение')
    if set_err:
        CQT.msgbox(pprint.pformat(set_err))
        pprint.pprint(set_err)
    return rez

def jurnal_tk(self, nach, konec):
    custom_request_c = f"""SELECT * FROM jurnal_td WHERE 
                           datetime(Дата) > datetime("{nach}") 
                           and datetime(Дата) < datetime("{konec}")"""
    rez = CSQ.custom_request_c(self.db_dse, custom_request_c, hat_c=True)
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez


def norm_mat_po_zav_nar(self, nach_data, kon_data):
    custom_request_c = f"""SELECT DISTINCT
                           naryad.Пномер, naryad.Номер_мк, mk.Номенклатура, mk.Номер_заказа, naryad.Твремя, naryad.Внеплан, 
                           naryad.ФИО as ФИО , naryad.ФИО2 as ФИО2, 
                           naryad.Фвремя, naryad.Фвремя2 ,  jurnal.ФИО as ФИОЖ, naryad.Примечание, naryad.ДСЕ, 
                           naryad.Операции, naryad.Опер_время, naryad.ДСЕ_ID, naryad.Опер_колво, naryad.Виды_работ
                          FROM jurnal
                           INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер
                           INNER JOIN mk ON mk.Пномер = naryad.Номер_мк
                           WHERE  naryad.Внеплан == 0 and naryad.Подтвержд_вып == 1 and
                           jurnal.Статус == "Завершен" and datetime(jurnal.Дата) > datetime("{nach_data}") 
                           and datetime(jurnal.Дата) < datetime("{kon_data}")
               """
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)

    tuple_mk = tuple(set(_['Номер_мк'] for _ in rez))
    custom_request_c = f"""SELECT * FROM res WHERE Номер_мк in {tuple_mk};"""
    rez_res = CSQ.custom_request_c(self.db_resxml, custom_request_c, hat_c=True, rez_dict=True)
    rez_res = F.deploy_dict_c(rez_res, 'Номер_мк')
    rez_list = [
        ['Номер_мк', 'Номенклатура', 'Номер_заказа', 'Пномер наряда', 'ДСЕ', 'Вид работ', 'Мат_код', 'Мат_наименование',
         'Мат_ед_изм', 'Мат_норма']]
    for i, nar in enumerate(rez):
        if nar['Номер_мк'] in rez_res:
            koef = 1
            if nar['ФИО'] != '' and nar['ФИО2'] != '':
                koef = 2
            res = F.from_binary_pickle(rez_res[nar['Номер_мк']])
            list_dse = nar['ДСЕ_ID'].split('|')
            list_oper = nar['Операции'].split('|')
            list_kolvo = nar['Опер_колво'].split('|')
            list_sort_crab = nar['Виды_работ'].split('|')
            list_dse_str = nar['ДСЕ'].split('|')
            try:
                for j in range(len(list_dse)):
                    try:
                        vidrab = list_sort_crab[j]
                    except:
                        vidrab = 'none'
                    dse_id = list_dse[j]
                    oper_nom = list_oper[j]
                    kolvo = int(list_kolvo[j])
                    dse_str = list_dse_str[j]
                    for _ in res:
                        if _['Номерпп'] == int(dse_id):
                            max_kol = _['Количество']
                            for oper in _['Операции']:
                                if oper['Опер_номер'] + '$' + oper['Опер_наименование'] == oper_nom:
                                    for mat in oper['Материалы']:
                                        if 'Мат_норма_ед' in mat:
                                            nr = mat['Мат_норма_ед'] * kolvo / koef
                                        else:
                                            nr = mat['Мат_норма'] / max_kol * kolvo / koef
                                        rez_list.append([nar['Номер_мк'], nar['Номенклатура'], nar['Номер_заказа'],
                                                         nar['Пномер'], dse_str, vidrab, mat['Мат_код'],
                                                         mat['Мат_наименование'],
                                                         mat['Мат_ед_изм'],
                                                         '{:.6f}'.format(round(nr, 6))])
                                    break
                            break
            except:
                print(f"{nar['Номер_заказа']} ошибка разбора")
    rez_list.append(['' for _ in rez_list[0]])
    rez_list.append(['' for _ in rez_list[0]])
    return rez_list


def neosv_ves_po_sozd_nar(self, podrazd):
    podrazd = podrazd.split('|')[0]

    custom_request_c = """SELECT mk.Пномер, mk.Номер_заказа, mk.Номер_проекта, naryad.Пномер,naryad.Дата, naryad.ФИО, naryad.Фвремя, naryad.ФИО2, naryad.Фвремя2, naryad.Задание,
     naryad.Внеплан, naryad.Автор, naryad.Компл_ФИО, naryad.Компл_Дата, naryad.Операции, naryad.Опер_время, naryad.Твремя, 0 as Освоено, 0 as Освоено2, 0 as Неосв_кг_сумм FROM naryad 
INNER JOIN mk ON mk.Пномер = naryad.Номер_мк
 WHERE ((naryad.ФИО != '' and naryad.Фвремя == "") or (naryad.ФИО2 != '' and naryad.Фвремя2 == "") or (naryad.ФИО2 == '' and naryad.ФИО == "")) 
 and mk.Дата_завершения == ''"""
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
    list_res = []
    for i in range(len(rez)):
        fio = rez[i]['ФИО']
        fio2 = rez[i]['ФИО2']
        neosv1 = 0
        neosv2 = 0
        fl1 = True
        if fio != '':
            fio_rc = rc_po_fio(self, fio)
            if fio_rc == podrazd:

                nom_nar = rez[i]['Пномер']
                summ = CSQ.custom_request_c(self.bd_naryad,
                                            f"""SELECT sum(Подытог) FROM jurnal WHERE ФИО == "{fio}" and Номер_наряда == {nom_nar}""")
                rez[i]['Освоено'] == summ[-1][0]
                try:
                    if rez[i]['Освоено'] < rez[i]['Твремя']:
                        neosv1 = rez[i]['Твремя'] - rez[i]['Освоено']
                except:
                    print(f"nar{nom_nar}  {rez[i]['Освоено']} {rez[i]['Твремя']}")
                    neosv1 = 0
            else:
                fl1 = False
        fl2 = True
        if fio2 != '':
            fio2_rc = rc_po_fio(self, fio)
            if fio2_rc == podrazd:
                nom_nar = rez[i]['Пномер']
                summ = CSQ.custom_request_c(self.bd_naryad,
                                            f"""SELECT sum(Подытог) FROM jurnal WHERE ФИО == "{fio2}" and Номер_наряда == {nom_nar}""")
                rez[i]['Освоено2'] == summ[-1][0]
                try:
                    if rez[i]['Освоено2'] < rez[i]['Твремя']:
                        neosv2 = rez[i]['Твремя'] - rez[i]['Освоено2']
                except:
                    print(f"nar{nom_nar}  {rez[i]['Освоено']} {rez[i]['Твремя']}")
                    neosv2 = 0
            else:
                fl2 = False
        if fio2 == '' and fio == '':
            list_opers = rez[i]['Операции'].split("|")
            list_vrem = rez[i]['Опер_время'].split("|")
            summ = 0
            for i in range(len(list_opers)):
                num, name = list_opers[i].split('$')
                if name in self.DICT_OPER_FULL:
                    rc = self.DICT_OPER_FULL[name]['rc'][:4] + '00'
                    if rc == podrazd:
                        summ += F.valm(list_vrem[i])
            if summ > 0:
                fl1 = True
                fl2 = True
            rez[i]['Освоено2'] == 0
            neosv1 = summ
            neosv2 = 0
        rez[i]['Неосв_кг_сумм'] = round((neosv1 + neosv2) * 102 / 480)
        if fl1 == True or fl2 == True:
            list_res.append(rez[i])
    list_res.append({_:'' for _ in list_res[0].keys()})
    list_res.append({_:'' for _ in list_res[0].keys()})
    return list_res


def virabotka_sotr_za_mes(self: mywindow, nach_data, kon_data, *args):
    list_prich_pauz = F.load_file(rf'{F.cfg["data_f"]}\Выполнение\Data\Prich_pauz.txt')
    list_prich_pauz.append('')
    list_prich_pauz.append(None)
    rez = [["п/п", "Работник", "Должность", "Подразделение", "Наименование", "Вид работ", "Тариф", "Единица измерения",
            "Факт, мин.",
            "Норма, мин.", "Фонд оплаты труда(План, руб.)", "Фонд оплаты труда(Факт, руб.)",
            "Отклонение фактических показателей от предельных норм  мощностей, в мин.", "Причина отклонения",
            "Соблюдение норм/достижение результата, в %"]]
    pp = 1
    custom_request_c = f"""SELECT DISTINCT
                        naryad.Пномер, naryad.Твремя, naryad.Внеплан, 
                        naryad.ФИО as ФИО , naryad.ФИО2 as ФИО2, 
                        naryad.Фвремя, naryad.Фвремя2 ,  jurnal.ФИО as ФИОЖ, naryad.Примечание, naryad.ДСЕ, naryad.Операции, naryad.Опер_время,
                         naryad.Категория_внепл, naryad.Виды_работ FROM jurnal
                        INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер
                        WHERE naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1 and 
                        jurnal.Статус == "Завершен" and datetime(jurnal.Дата) > datetime("{nach_data}") 
                        and datetime(jurnal.Дата) < datetime("{kon_data}")
            """
    list_naryadov = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=False, rez_dict=True)
    for i, item in enumerate(list_naryadov):
        nom_nar = item['Пномер']
        fio = item['ФИОЖ']
        if fio not in self.DICT_EMPLOEE_FULL:
            query = f"""SELECT Должность, Подразделение FROM employee WHERE ФИО = '{fio}'"""
            empl = CSQ.custom_request_c(self.bd_users, query, rez_dict=True)
            if empl != False and len(empl) >= 1:
                dolgn = empl[0]['Должность']
                podrazdel = empl[0]['Подразделение']
            else:
                print(f"{item['ФИОЖ']} не найден в employee")
                continue
        else:
            dolgn = self.DICT_EMPLOEE_FULL[fio]['Должность']
            podrazdel = self.DICT_EMPLOEE_FULL[fio]['Подразделение']

        str_sort_c_rabot = item['Виды_работ']
        str_time_rabot = item['Опер_время']
        fact = item['Фвремя'] if fio == item['ФИО'] else item['Фвремя2']
        norma = item['Твремя']

        list_sort_c_rabot = str_sort_c_rabot.split("|")
        list_time_rabot = [F.valm(_) for _ in str_time_rabot.split("|")]
        list_dse = item['ДСЕ'].split("|")
        list_prim = CSQ.custom_request_c(self.bd_naryad,
                                         f"""SELECT Примечание FROM jurnal WHERE Номер_наряда == {nom_nar} AND ФИО == '{fio}';""",
                                         hat_c=False)

        try:
            str_prim = '; '.join([_[0] for _ in list_prim if [0] != None and _[0].strip() not in list_prich_pauz])
        except:
            str_prim = ''

        if item['ФИОЖ'] in self.Data.VID_RABOT_PO_EMPL:
            vid = self.Data.VID_RABOT_PO_EMPL[item['ФИОЖ']]['Вид_работ']
            tarif = self.Data.VID_RABOT_PO_EMPL[item['ФИОЖ']]['Руб_мин']
        else:

            continue

        koef = norma / fact

        for j in range(len(list_dse)):
            dse = list_dse[j].replace("$", ' ')
            norma_dse = list_time_rabot[j]
            fact_dse = round(norma_dse / koef, 2)

            fot_pl = round(tarif * norma_dse)
            fot_f = round(tarif * fact_dse
                          )
            if fact_dse <= 1:
                rez_precent = "-"
            else:
                rez_precent = round(norma_dse / fact_dse * 100)

            tmp = [pp, fio, dolgn, podrazdel, dse, vid, tarif, "мин.", fact_dse,
                   norma_dse, fot_pl, fot_f,
                   round(norma_dse - fact_dse, 2), str_prim,
                   rez_precent]
            rez.append(tmp)
            pp += 1
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez


@CQT.onerror
def load_parametrs_gant(self, *args):
    self.ui.cmb_gant_vert.clear()
    self.ui.cmb_gant_vert.addItems(self.plan_for_gant[0])
    self.ui.cmb_gant_colour.clear()
    self.ui.cmb_gant_colour.addItems(self.plan_for_gant[0])
    self.ui.cmb_gant_tochnost_dat.clear()
    self.ui.cmb_gant_tochnost_dat.addItems(['Подетально', 'Помаршрутно', 'Отчет вспомогательных материалов'])


@CQT.onerror
def vibor_pole_gant(self, *args):
    self.ui.cmb_gant_vert_val.clear()
    rez_set = set()
    pole = self.ui.cmb_gant_vert.currentText()
    nk = F.num_col_by_name_in_hat_c(self.plan_for_gant, pole)
    rez_set.add('')
    for i in range(1, len(self.plan_for_gant)):
        rez_set.add(self.plan_for_gant[i][nk])
    rez = sorted(list(rez_set))
    self.ui.cmb_gant_vert_val.addItems(rez)


@CQT.onerror
def create_podreport_c(self, *args):
    return 
    #if self.ui.cmb_gant_tochnost_dat.currentText() == 'Отчет вспомогательных материалов':
    #    name = f'plan_materials_{F.now("%Y-%m-%d")}.xlsx'
    #    nach = self.ui.le_start_of_period.text()
    #    konec = self.ui.le_end_of_period.text()
    #    PL.save_excell_plan_materials(self, self.rez_plan, self.files_tmp, name, nach, konec)
    #if self.ui.cmb_gant_tochnost_dat.currentText() in ['Подетально', 'Помаршрутно']:
    #    create_gant(self)


@CQT.onerror
def create_gant(self, *args):
    def fig_gr_dinam_proizv(self, spis):
        fig = go.Figure()
        if not spis:
            return fig
        weeks = [_['week'] for _ in spis]
        dict_fields = dict()
        info_dict = {'Факт': {
            'color': '#228B22',
            'type_line': 'solid'
        },
            'Твремя': {
                'color': '#E9967A',
                'type_line': 'solid'
            },
            'Норма': {
                'color': '#00FFFF',
                'type_line': 'dash'
            }
        }


        for field_name,val in spis[0].items():
            if field_name == 'week':
                continue
            # '''"solid", "dot", "dash",
            #            "longdash", "dashdot", or "longdashdot"'''

            fig.add_trace(go.Scatter(x=weeks, y=[_[field_name] for _ in spis], name=field_name,
                                     line=dict(color=info_dict[field_name]['color'], width=4,
                                               dash=info_dict[field_name]['type_line'])))

        # Edit the layout
        fig.update_layout(
            title=f'{self.vid_report_c}',
            xaxis_title='Группировка `Подтвержд. вып. дата` нарядов по неделям',
            yaxis_title='Минуты')
        return fig

    def fig_sravn_norm_vr_po_napr(self, spis, dict_color):
        month = [_[0] for _ in spis[1:]]
        dict_fields = dict()
        for j, field in enumerate(spis[0][1:]):
            dict_fields[field] = [_[j + 1] for _ in spis[1:]]

        fig = go.Figure()
        for field in dict_fields.keys():
            # Create and style traces
            napr = field.split("_")[0]
            color = 'firebrick'
            if napr in dict_color:
                list_color = [int(_) for _ in dict_color[napr].split(';')]
                color = F.rgb_to_hex(list_color)
            type_line = 'solid'
            # '''"solid", "dot", "dash",
            #            "longdash", "dashdot", or "longdashdot"'''
            if '_абс' in field:
                type_line = 'dot'
            fig.add_trace(go.Scatter(x=month, y=dict_fields[field], name=field,
                                     line=dict(color=color, width=4,
                                               dash=type_line)))

        # Edit the layout
        fig.update_layout(
            title=f'{self.vid_report_c}  "(Тп-Тф)*100/Тп" (абс - как абсолютное значение разницы план-факт)',
            xaxis_title='Месяц',
            yaxis_title='%')
        return fig

    def fig_gr_ud_prt_cex(self, spis):
        month = [_[0] for _ in spis[1:]]
        postov = [_[1] for _ in spis[1:]]
        virabotka = [_[2] for _ in spis[1:]]
        prisutstvie = [_[3] for _ in spis[1:]]
        proizv = [_[4] for _ in spis[1:]]
        ves = [_[5] for _ in spis[1:]]
        ves_list = [_[6] for _ in spis[1:]]
        ves_xml = [_[7] for _ in spis[1:]]
        ves_kplan = [_[8] for _ in spis[1:]]

        fig = go.Figure()
        color = 'firebrick'
        type_line = 'solid'
        # '''"solid", "dot", "dash",
        #            "longdash", "dashdot", or "longdashdot"'''
        fig.add_trace(go.Scatter(x=month, y=proizv, name=spis[0][4],
                                 line=dict(color='#E63A3E', width=4,
                                           dash=type_line), text=proizv,
                                 textposition='top right',
                                 textfont=dict(color='#E63A3E', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=postov, name=spis[0][1],
                                 line=dict(color='#069435', width=4,
                                           dash=type_line), text=postov,
                                 textposition='top right',
                                 textfont=dict(color='#069435', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=virabotka, name=spis[0][2],
                                 line=dict(color='#0070C0', width=4,
                                           dash=type_line), text=virabotka,
                                 textposition='top right',
                                 textfont=dict(color='#0070C0', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=prisutstvie, name=spis[0][3],
                                 line=dict(color='#0090C0', width=4,
                                           dash="longdash"), text=prisutstvie,
                                 textposition='top right',
                                 textfont=dict(color='#0070C0', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=ves, name=spis[0][5],
                                 line=dict(color='#FFD966', width=4,
                                           dash=type_line), text=ves,
                                 textposition='top right',
                                 textfont=dict(color='#FFD966', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=ves_list, name=spis[0][6],
                                 line=dict(color='#6600FF', width=4,
                                           dash=type_line), text=ves_list,
                                 textposition='top right',
                                 textfont=dict(color='#6600FF', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=ves_xml, name=spis[0][7],
                                 line=dict(color='#669900', width=4,
                                           dash=type_line), text=ves_xml,
                                 textposition='top right',
                                 textfont=dict(color='#669900', size=16),
                                 mode='lines+text'))

        fig.add_trace(go.Scatter(x=month, y=ves_kplan, name=spis[0][8],
                                 line=dict(color='#808000', width=4,
                                           dash=type_line), text=ves_kplan,
                                 textposition='top right',
                                 textfont=dict(color='#808000', size=16),
                                 mode='lines+text'))
        # Edit the layout
        fig.update_layout(
            title=f'{self.vid_report_c}',
            xaxis_title='Месяц',
            yaxis_title='')
        return fig

    def fig_gr_pf_gr_mes(self, spis):
        # [['Месяц', 'План, н-см.', 'Отгрузка, т.', 'Факт, н-см.', 'Внеплан, н-см.', 'Сумм. Факт, н-см.']]
        month = [_[0] for _ in spis[1:]]
        # plan_tonn = [_[1] for _ in spis[1:]]
        otgruzka = [_[1] for _ in spis[1:]]
        plan_nned = [_[2] for _ in spis[1:]]
        fact_ns = [_[3] for _ in spis[1:]]
        vnepalan = [_[4] for _ in spis[1:]]
        summ_fact = [_[5] for _ in spis[1:]]
        pl_tabel =  [_[6] for _ in spis[1:]]
        fact_plan_from_vir_sotr = [_[7] for _ in spis[1:]]
        fact_pl_time_n_sm = [_[8] for _ in spis[1:]]
        fig = go.Figure()
        color = 'firebrick'
        type_line = 'solid'
        # '''"solid", "dot", "dash",
        #            "longdash", "dashdot", or "longdashdot"'''
        # fig.add_trace(go.Scatter(x=month, y=plan_tonn, name=spis[0][1],
        #                             line=dict(color='#1f77b4', width=4,
        #                                       dash=type_line), text=plan_tonn ,
        #                         textposition='top right',
        #                          textfont=dict(color='#1f77b4',size = 16),
        #                          mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=otgruzka, name=spis[0][1],
                                 line=dict(color='#bfbf00', width=4,
                                           dash=type_line), text=otgruzka,
                                 textposition='top right',
                                 textfont=dict(color='#bfbf00', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=plan_nned, name=spis[0][2],
                                 line=dict(color='#E66761', width=4,
                                           dash=type_line), text=plan_nned,
                                 textposition='top right',
                                 textfont=dict(color='#bfbf00', size=16),
                                 mode='lines+text'))

        fig.add_trace(go.Scatter(x=month, y=fact_ns, name=spis[0][3],
                                 line=dict(color='#007f00', width=4,
                                           dash=type_line), text=fact_ns,
                                 textposition='top right',
                                 textfont=dict(color='#007f00', size=16),
                                 mode='lines+text'))

        fig.add_trace(go.Scatter(x=month, y=vnepalan, name=spis[0][4],
                                 line=dict(color='#ff0000', width=4,
                                           dash=type_line), text=vnepalan,
                                 textposition='top right',
                                 textfont=dict(color='#ff0000', size=16),
                                 mode='lines+text'))

        fig.add_trace(go.Scatter(x=month, y=summ_fact, name=spis[0][5],
                                 line=dict(color='#c6580f', width=4,
                                           dash=type_line), text=summ_fact,
                                 textposition='top right',
                                 textfont=dict(color='#c6580f', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=pl_tabel, name=spis[0][6],
                                 line=dict(color='#9999ff', width=4,
                                           dash=type_line), text=pl_tabel,
                                 textposition='top right',
                                 textfont=dict(color='#9999ff', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=fact_plan_from_vir_sotr, name=spis[0][7],
                                 line=dict(color='#b366ff', width=4,
                                           dash=type_line), text=fact_plan_from_vir_sotr,
                                 textposition='top right',
                                 textfont=dict(color='#b366ff', size=16),
                                 mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=fact_pl_time_n_sm, name=spis[0][8],
                                 line=dict(color='#45161C', width=4,
                                           dash=type_line), text=fact_pl_time_n_sm,
                                 textposition='top right',
                                 textfont=dict(color='#45161C', size=16),
                                 mode='lines+text'))
        # Edit the layout
        fig.update_layout(
            title=f'{self.vid_report_c}',
            xaxis_title='Месяц',
            yaxis_title='')
        return fig

    def fig_gr_vnepl_rab(self, spis, napravl=''):
        gp = check_import_modyle('gant_ploty')
        if gp is None:
            import gant_ploty as gp
        # ['Месяц', 'Внеплан, н-см.', 'Сумм св_швов, м.', 'Брак производственный', 'Ошибка нормирования и технологии', 'Доработка КД', 'Обучение', 'Работы на внешней площадке', 'Ошибка планирования нарядов', 'Отсутвие заказа на производство', 'Доработка оборудования(исправление чужого брака)', 'Цеховая оснастка', 'Простой']
        month = [_[0] for _ in spis[1:]]
        DICT_FORM = {'Месяц': ["", " "],
                     'Внеплан сумма, н-см./чел.': ["#C80E09", "solid"],
                     'Сумм св_швов, м.': ["#bfbf00", "longdashdot"],
                     'План, н-см./чел.': ["#3CB93D", "solid"],
                     'Брак производственный': ["#C15911", "solid"],
                     'Ошибка нормирования и технологии': ["#599f21", "dash"],
                     'Доработка КД': ["#5D14F0", "dash"],
                     'Обучение': ["#BC4890", "dash"],
                     'Работы на внешней площадке': ["#0DD6F7", "dot"],
                     'Ошибка планирования нарядов': ["#766d0b", "dot"],
                     'Отсутвие заказа на производство': ["#7BA85C", "dot"],
                     'Исправление чужого брака': ["#C8A2C8", "solid"],
                     'Цеховая оснастка(для нужд цеха)': ["#A06468", "dash"],
                     'Простой': ["#293133", "dot"],
                     'Некомплект': ["#766d0b", "dot"],
                     'Выход из строя оборудования': ["#002fa7", "dot"],
                     'Ожидание ОТК': ["#3EB489", "dot"],
                     'ПХД': ["#B0E0E6", "dot"],
                     '': ["#689B9C", "longdash"],
                     'Дорезка': ["#29AB87", "longdash"],
                     'Дорезка_брак(гибка)': ["#6E5160", "longdash"],
                     'Дорезка_брак(резка)': ["#FFB300", "longdash"],
                     'Дорезка_брак(сборка)': ["#FF8E0D", "longdash"],
                     'Дорезка_вырезали из другой толщины': ["#9F8200", "longdash"],
                     'Дорезка_вырезали по неактуальным чертежам': ["#2271B3", "longdash"],
                     'Дорезка_изменение кд': ["#EF98AA", "longdash"],
                     'Дорезка_неверная заявка на дорезку': ["#75151E", "longdash"],
                     'Дорезка_неверное csv': ["#308446", "longdash"],
                     'Дорезка_технологические доработки': ["#CA3767", "longdash"],
                     'Дорезка_утеря на заготовительном': ["#FBCEB1", "longdash"],
                     'Дорезка_утеря на сборке': ["#304B26", "longdash"],
                     'Дорезка_утеря на складе либо при перемещении': ["#42AAFF", "longdash"],
                     'Испытания': ["#141613", "solid"],
                     'Покрытие': ["#696969", "solid"],
                     'Доработка(без дорезки)': ["#689B9C", "dot"],
                     'Доработка_брак(гибка)': ['#5D9B9B', "dot"],
                     'Доработка_брак(резка)': ['#9370D8', "dot"],
                     'Доработка_брак(сборка)': ['#87CEEB', "dot"],
                     'Доработка_вырезали по неактуальным чертежам': ['#46394B', "dot"],
                     'Доработка_изменение кд': ['#C6DF90', 'dot'],
                     'Доработка_неверная заявка на дорезку': ['#6A5D4D', "dot"],
                     'Доработка_неверное csv': ['#252850', "dot"],
                     'Доработка_технологические доработки': ['#252850', "dot"],
                     'Доработка_обучение': ['#F984E5', "dot"],
                     'Доработка_работы на внешней площадке': ['#FF9966', "dot"],
                     'Доработка_цеховая оснастка(для нужд цеха)': ['#F9DFCF', "dot"],
                     'Доработка_выход из строя оборудования': ['#9E9764', "dot"],
                     }

        fig = go.Figure()
        color = 'firebrick'
        type_line = 'solid'
        # '''"solid", "dot", "dash",
        #            "longdash", "dashdot", or "longdashdot"'''
        for column in range(1, len(spis[0])):
            print(spis[0][column])
            color = color = 'firebrick'
            type_line = 'solid'
            try:
                color = DICT_FORM[spis[0][column]][0]
                type_line = DICT_FORM[spis[0][column]][1]
            except:
                pass
            fig.add_trace(go.Scatter(x=month, y=[_[column] for _ in spis[1:]], name=spis[0][column],
                                     line=dict(color=color, width=4,
                                               dash=type_line), text=[_[column] for _ in spis[1:]],
                                     textposition='top right',
                                     textfont=dict(color=color, size=14),
                                     mode='lines+text'))

        # Edit the layout
        fig.update_layout(
            title=f'{self.vid_report_c}. {napravl}',
            xaxis_title='Месяц',
            yaxis_title='')
        return fig

    if self.vid_report_c == 'Динамика производительности сотрудников':
        if args == None or len(args) == 0:
            return
        fig = fig_gr_dinam_proizv(self, args[0])
        load_browser(self)
        CQT.output_gant(self, fig, self.browser, self.vid_report_c + '_' + self.ui.cmb_addit_sort_c_report.currentText())

    if self.vid_report_c == 'Внеплановые работы по направлениям':
        if args == None or len(args) == 0:
            return
        fig = fig_gr_vnepl_rab(self, args[0], args[-1])
        load_browser(self)
        CQT.output_gant(self, fig, self.browser, self.vid_report_c + '_' + self.ui.cmb_podrazdelenie.currentText())

    if self.vid_report_c == 'План-фактный график по месяцам':
        if args == None or len(args) == 0:
            return
        fig = fig_gr_pf_gr_mes(self, args[0])
        load_browser(self)
        CQT.output_gant(self, fig, self.browser, self.vid_report_c + '_' + self.ui.cmb_podrazdelenie.currentText())

    if self.vid_report_c == 'График удельной производительности сборочного цеха':
        if args == None or len(args) == 0:
            return
        fig = fig_gr_ud_prt_cex(self, args[0])
        load_browser(self)
        CQT.output_gant(self, fig, self.browser, self.vid_report_c + '_' + self.ui.cmb_podrazdelenie.currentText())

    if self.vid_report_c == 'Сравнение норм времени по направлениям':
        if args == None or len(args) == 0:
            return
        data_list = args[0]
        dict_color = CSQ.custom_request_c(self.db_kplan,
                                          f"""SELECT napravlenie.Цвет , napravlenie.name FROM napravlenie """,
                                          rez_dict=True)
        dict_color = F.deploy_dict_c(dict_color, 'name')
        fig = fig_sravn_norm_vr_po_napr(self, data_list, dict_color)
        load_browser(self)
        CQT.output_gant(self, fig, self.browser, self.vid_report_c + '_' + self.ui.cmb_podrazdelenie.currentText())

    if self.vid_report_c == 'План работ':
        if self.plan_for_gant == '' or self.ui.cmb_gant_vert.currentText() == '' or self.ui.cmb_gant_colour == '':
            return
        fig = gp.fig_podetalno_narc_projects(self.plan_for_gant, self.ui.cmb_gant_vert.currentText(),
                                             self.ui.cmb_gant_vert_val.currentText(),
                                             self.ui.cmb_gant_colour.currentText(),
                                             self.ui.cmb_gant_tochnost_dat.currentText())
        CQT.output_gant(self, fig, self.browser, self.vid_report_c + '_' + self.ui.cmb_podrazdelenie.currentText())

    if self.vid_report_c == 'Журнал замечаний динамика':
        if args == None or len(args) == 0:
            return
        dict_podrs = F.deploy_dict_c(F.list_of_lists_to_list_of_dicts(F.dict_of_dicts_to_list_of_lists(self.DICT_RC)),'empl_Подразделение')
        title = self.vid_report_c
        labels_cod_wet = [_ for _ in args[0][0].keys() if _ != 'month']
        colors = ['rgb(67,67,67)', 'rgb(115,115,115)', 'rgb(49,130,189)', 'rgb(189,189,189)']
        colors = []
        for podr in args[0][0].keys():
            if podr != 'month':
                color = 'rgb(67,67,67)'
                podr_kod = podr
                if "(" in podr:
                    podr_kod = podr.split("(")[0]
                if podr_kod in dict_podrs: 
                    color = f'rgb({dict_podrs[podr_kod]["Цвет"]})'
                colors.append(color)

        x_data = [[_['month'] for _ in args[0]] for line in range(len(labels_cod_wet))]
        y_data_wet = [[line[pd] for line in args[0]] for pd in labels_cod_wet]

        filtr_rate = 5
        y_data = []
        labels_cod = []
        for i in range(len(y_data_wet)):
            fl_del = True
            for j in range(len(y_data_wet[i])):
                if y_data_wet[i][j] > filtr_rate:
                    fl_del = False
                    break
            if not fl_del:
                y_data.append(y_data_wet[i])
                labels_cod.append(labels_cod_wet[i])

        labels = labels_cod
        
        fig = go.Figure()

        # '''"solid", "dot", "dash",
        #            "longdash", "dashdot", or "longdashdot"'''

        for i in range(0, len(labels)):
            type_line = 'solid'
            if "_" in labels[i]:
                type_line = 'dot'
            fig.add_trace(go.Scatter(x=x_data[i], y=y_data[i], mode='lines+text',
                                     name=labels[i],
                                     line=dict(color=colors[i], width=3, dash=type_line),
                                     text=y_data[i], textposition='top right',
                                     textfont=dict(color=colors[i], size=12),
                                     connectgaps=True))
            """
            # endpoints
            fig.add_trace(go.Scatter(
                x=[x_data[i][0], x_data[i][-1]],
                y=[y_data[i][0], y_data[i][-1]],
                mode='markers',
                marker=dict(color=colors[i], size=mode_size[i])
            ))"""

            fig.update_layout(
                xaxis=dict(
                    showline=True,
                    showgrid=False,
                    showticklabels=True,
                    linecolor='rgb(204, 204, 204)',
                    linewidth=2,
                    ticks='outside',
                    tickfont=dict(
                        family='Arial',
                        size=12,
                        color='rgb(82, 82, 82)',
                    ),
                ),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showline=False,
                    showticklabels=False,
                ),
                autosize=True,

                showlegend=True,
                plot_bgcolor='white'
            )

        annotations = []
        i = 1
        # Adding labels
        for y_trace, label, color in zip(y_data, labels, colors):
            # labeling the left_side of the plot
            """if label != '':
                i +=1
                annotations.append(dict(xref='paper', x=0.05, y=y_trace[0] + (i*0.5),
                                        xanchor='right', yanchor='middle',
                                        text=label + ' {}%'.format(y_trace[0]),
                                        font=dict(family='Arial',
                                                  size=8),
                                        showarrow=False))
            # labeling the right_side of the plot
            annotations.append(dict(xref='paper', x=0.95, y=y_trace[-1],
                                    xanchor='left', yanchor='middle',
                                    text='{}%'.format(y_trace[-1]),
                                    font=dict(family='Arial',
                                              size=10),
                                    showarrow=False))"""
        # Title
        annotations.append(dict(xref='paper', yref='paper', x=0.5, y=1.05,
                                xanchor='center', yanchor='bottom',
                                text='Замечания в динамике',
                                font=dict(family='Arial',
                                          size=18,
                                          color='rgb(37,37,37)'),
                                showarrow=False))
        # Source
        annotations.append(dict(xref='paper', yref='paper', x=0.5, y=-0.1,
                                xanchor='center', yanchor='top',
                                text='Источник: журнал замечаний',
                                font=dict(family='Arial',
                                          size=12,
                                          color='rgb(150,150,150)'),
                                showarrow=False))

        fig.update_layout(annotations=annotations)
        CQT.output_gant(self, fig, self.browser, self.vid_report_c + '_' + self.ui.cmb_podrazdelenie.currentText())

    if self.vid_report_c == 'Журнал_замечаний':
        if args == None or len(args) == 0:
            return
        data_list = args[0]
        data_dict = F.list_to_dict(data_list[:-2])

        dict_tmp = dict()
        tmp_kod_sort_c_vp = copy.deepcopy(self.DICT_KOD_VP)
        for key in tmp_kod_sort_c_vp:
            tmp_kod_sort_c_vp[key] = 0
        tmp_kod_sort_c = copy.deepcopy(self.DICT_KOD_ZAM)
        for key in tmp_kod_sort_c:
            tmp_kod_sort_c[key] = copy.deepcopy(tmp_kod_sort_c_vp)

        for zam in data_dict:
            if zam['Виновное_подразделение'] not in dict_tmp:
                dict_tmp[zam['Виновное_подразделение']] = copy.deepcopy(tmp_kod_sort_c)

        for zam in data_dict:
            try:
                dict_tmp[zam['Виновное_подразделение']][zam['Код_замечания']][zam['Код_вп']] += 1
            except:
                print(f'ОШибка {zam}')
        # START(По задаче 100054795 ) 28.05.2025

        data = []
        for podr in dict_tmp:
            for kod in dict_tmp[podr]:
                for kod_vp in dict_tmp[podr][kod]:
                    data.append({
                        'podr': podr,
                        'kod_vp': kod_vp,
                        'kod': kod,
                        'list_zam_count': dict_tmp[podr][kod][kod_vp]
                    })
        # df = pd.DataFrame(
        #     dict(podr=list_podr, kod=list_kod, kod_vp=list_kod_vp, число_замечаний=list_zam_count)
        # )
        # print(df)
        # fig = px.sunburst(df, path=['podr', 'kod', 'kod_vp'], values='число_замечаний',
        #                   title='Диаграмма замечаний за пероид')
        labels = []
        parents = []
        values = []
        colors = []
        for entry in data:
            podr_color = '122,122,122'
            for item in self.DICT_PODR_RC.values():
                if item['Сокр_наим_СТО'] == entry["podr"]:
                    podr_color = item['Цвет']
                    break
            # 1 кольцо(подр)
            if entry["podr"] not in labels:
                labels.append(entry["podr"])
                parents.append("")
                values.append(sum(e["list_zam_count"] for e in data if e["podr"] == entry["podr"]))
                colors.append(f'rgb({podr_color})')
            # 2 кольцо(замечание)
            podr_kod = f"{entry['podr']}-{entry['kod']}"
            if podr_kod not in labels:
                labels.append(podr_kod)
                parents.append(entry["podr"])
                values.append(
                    sum(e["list_zam_count"] for e in data if e["podr"] == entry["podr"] and e["kod"] == entry["kod"]))
                colors.append(f'rgb({podr_color})')
            # 3 кольцо(код_вп)
            kod_kodvp = f"{podr_kod}-{entry['kod_vp']}"
            if kod_kodvp not in labels:
                labels.append(kod_kodvp)
                parents.append(podr_kod)
                values.append(entry["list_zam_count"])
                colors.append(f'rgb({podr_color})')
        fig = go.Figure(go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            marker=dict(colors=colors)

        ))

        fig.update_layout(
            title="Диаграмма замечаний за пероид",
            margin=dict(t=30, l=0, r=0, b=0),
        )
        # STOP(По задаче 100054795 ) 28.05.2025
        CQT.output_gant(self, fig, self.browser, self.vid_report_c + '_' + self.ui.cmb_podrazdelenie.currentText())


@CQT.onerror
def calendar_select(self, *args):
    if not len(args):
        return 
    type_date = args[0]
    data = F.datetostr(QtCore.QDate.toPyDate(self.ui.calendarWidget.selectedDate()))
    start, end = F.start_end_dates_c(data, "%Y-%m-%d %H:%M:%S", type_date, "%Y-%m-%d")
    self.ui.le_start_of_period.setText(start + " 00:00:00")
    self.ui.le_end_of_period.setText(end + " 23:59:59")


@CQT.onerror
def calendar_click(self, *args):
    data = self.ui.calendarWidget.selectedDate()
    if self.ui.rbut_start_of_per.isChecked():
        self.ui.le_start_of_period.setText(F.datetostr(QtCore.QDate.toPyDate(data), "%Y-%m-%d 00:00:00"))
        if self.ui.cmb_sort_c_report.currentText() == 'Матрицы компетенций':
            konec = F.start_end_dates_c(date=self.ui.le_start_of_period.text(), vid='d')[1]
            self.ui.le_end_of_period.setText(konec)
        if self.ui.cmb_sort_c_report.currentText() == 'Трудозатраты':
            konec = F.start_end_dates_c(date=self.ui.le_start_of_period.text(), vid='d')[1]
            self.ui.le_end_of_period.setText(konec)
        if self.ui.cmb_sort_c_report.currentText() == 'О выработке сотрудников за месяц':
            konec = F.start_end_dates_c(date=self.ui.le_start_of_period.text(), vid='m')[1]
            self.ui.le_end_of_period.setText(konec)

    if self.ui.rbut_end_of_period.isChecked():
        self.ui.le_end_of_period.setText(F.datetostr(QtCore.QDate.toPyDate(data), "%Y-%m-%d 23:59:59"))
        if self.ui.cmb_sort_c_report.currentText() == 'Матрицы компетенций':
            nach = F.start_end_dates_c(date=self.ui.le_end_of_period.text(), vid='d')[0]
            self.ui.le_start_of_period.setText(nach)
        if self.ui.cmb_sort_c_report.currentText() == 'Трудозатраты':
            nach = F.start_end_dates_c(date=self.ui.le_end_of_period.text(), vid='d')[0]
            self.ui.le_start_of_period.setText(nach)
        if self.ui.cmb_sort_c_report.currentText() == 'О выработке сотрудников за месяц':
            nach = F.start_end_dates_c(date=self.ui.le_end_of_period.text(), vid='m')[0]
            self.ui.le_start_of_period.setText(nach)

    if self.vid_report_c == 'Отчет по проекту' :
        self.ui.le_start_of_period.setText(F.datetostr(QtCore.QDate.toPyDate(data), "%Y-%m-%d 00:00:00"))
        self.ui.le_end_of_period.setText(F.datetostr(QtCore.QDate.toPyDate(data), "%Y-%m-%d 23:59:59"))
        years  = range(F.strtodate(self.ui.le_start_of_period.text()).year, F.strtodate(self.ui.le_end_of_period.text()).year+1)
        get_list_py_by_year(self,years)


@CQT.onerror
def podrazdel_etapi(self, *args):
    self.ui.cmb_podrazdelenie.clear()
    self.ui.cmb_podrazdelenie.addItem('')
    set_etapi = set()
    for key in self.DICT_ETAPI.keys():
        set_etapi.add(self.DICT_ETAPI[key])
    list_etapi = list(set_etapi)
    list_etapi.sort()
    for etap in list_etapi:
        self.ui.cmb_podrazdelenie.addItem(etap)


@CQT.onerror
def emploee(self, *args):
    self.ui.cmb_podrazdelenie.setDisabled(False)
    self.ui.cmb_podrazdelenie.clear()
    self.ui.cmb_podrazdelenie.addItem('')
    spis = set()
    for empl in self.DICT_EMPLOEE_RC.keys():
        spis.add(empl)
    spis = sorted(list(spis))
    for empl in spis:
        self.ui.cmb_podrazdelenie.addItem(empl)


@CQT.onerror
def fill_podrazd_by_empl_full(self):
    self.ui.cmb_podrazdelenie.setEnabled(True)
    self.ui.cmb_podrazdelenie.clear()
    company = self.place.Имя
    list_podr = list(set([_['Подразделение'] for _ in self.DICT_EMPLOEE_FULL_WITH_DEL.values() if
                          len(_['Подразделение']) > 2 and _['Компания'] == company and
                          _['Подразделение'] in self.DICT_PODR_RC]))
    list_podr.sort()
    list_colors = []
    list_tooltip = []
    for podr in list_podr:
        clr = ''
        tooltip = ''
        if podr in self.DICT_PODR_RC:
            clr = self.DICT_PODR_RC[podr]['Цвет']
            tooltip = self.DICT_PODR_RC[podr]['Код']
        list_colors.append(F.align_colors(clr,',',sep_out=','))
        list_tooltip.append(tooltip)
    CQT.fill_list_combobx(self, self.ui.cmb_podrazdelenie, list_podr, list_colors, list_tooltip, ',',
                          first_void=True)

@CQT.onerror
def podrazdel_none(self, *args):
    self.ui.cmb_podrazdelenie.clear()
    self.ui.cmb_podrazdelenie.addItem('-')
    self.ui.cmb_podrazdelenie.setDisabled(True)


@CQT.onerror
def podrazdel_list(self, list_vals: list, *args):
    self.ui.cmb_podrazdelenie.setDisabled(False)
    self.ui.cmb_podrazdelenie.clear()
    self.ui.cmb_podrazdelenie.addItem('')
    self.ui.cmb_podrazdelenie.addItems(list_vals)


@CQT.onerror
def podrazdel_kod(self, *args):
    self.ui.cmb_podrazdelenie.setDisabled(False)
    self.ui.cmb_podrazdelenie.clear()
    self.ui.cmb_podrazdelenie.addItem('')
    custom_request_c = f'''SELECT * FROM rab_c'''
    spis_cexov = CSQ.custom_request_c(self.bd_users, custom_request_c, hat_c=False)
    for cex in spis_cexov:
        if cex[0][-2:] == '00':
            self.ui.cmb_podrazdelenie.addItem(f'{cex[0]}|{cex[1]}({cex[2]})')

@CQT.onerror
def podrazdel_from_dolgn_etap(self, *args):
    self.ui.cmb_podrazdelenie.setDisabled(False)
    self.ui.cmb_podrazdelenie.clear()
    self.ui.cmb_podrazdelenie.addItem('')
    custom_request_c = f'''SELECT Distinct Подразделение FROM dolgn_etap WHERE Производство == "{self.USER_CONFIG.Organization['Значение']}" ORDER BY Подразделение;'''
    spis_cexov = CSQ.custom_request_c(self.bd_naryad, custom_request_c,one_column=True,hat_c=False)
    self.ui.cmb_podrazdelenie.addItems(spis_cexov)

@CQT.onerror
def plan_rabot(self, nach, konec, podrazd, *args):
    return []
    #modifiers = QApplication.keyboardModifiers()
    #delete_cash_plan = False
    #if modifiers == QtCore.Qt.ShiftModifier:
    #    delete_cash_plan = True
    #    print('delete_cash_plan = True')
    #plan_full_spis = PL.load_plan(self, delete_cash_plan)
    #plan = self.generate_list_plan(plan_full_spis)
    #if plan == None:
    #    return
    #rez = [plan[0]]
    #nk_nachalo = plan[0].index('Начало')
    #for item in plan[1:]:
    #    # print(item)
    #    if F.strtodate(item[nk_nachalo][:19]) >= F.strtodate(nach) and F.strtodate(item[nk_nachalo][:19]) < F.strtodate(
    #            konec):
    #        rez.append(item)
    #rez.append(['' for _ in rez[0]])
    #rez.append(['' for _ in rez[0]])
    #return rez


def svar_vir(self, data_nach, data_kon):
    return


@CQT.onerror
def ready_procent(self):
    ''' строки формируются списками, нулевая строка- заголовки
    '''

    def get_max_time_order(orders):
        # получить максимальное время по нарядам
        max_time_orders = {}
        for order in orders:
            current_order = max_time_orders.get(order[0])
            if current_order:
                if current_order < order[1]:
                    max_time_orders[order[0]] = order[1]
            else:
                max_time_orders[order[0]] = order[1]
        return max_time_orders

    def get_full_time(orders):
        res = 0
        for time in orders.values():
            res += time
        return round(res / 60, 1)  # перевод часы в минуты

    def get_order_project_time(pu, get_current_month=False):
        # получение времени работы по нарядам
        if get_current_month:
            query = f"""SELECT jurnal.Номер_наряда, jurnal.Подытог FROM jurnal 
                        INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
                        INNER JOIN mk ON naryad.Номер_мк == mk.Пномер WHERE mk.Номер_заказа = '{pu}' AND naryad.РЦ_наряд IN ('0101') """  # AND (MONTH(naryad.Дата) = MONTH(CURRENT_DATE()) AND YEAR(naryad.Дата) = YEAR(CURRENT_DATE()))
        else:
            query = f"""SELECT jurnal.Номер_наряда, jurnal.Подытог FROM jurnal 
                        INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
                        INNER JOIN mk ON naryad.Номер_мк == mk.Пномер WHERE mk.Номер_заказа = '{pu}' """

        summ_time = CSQ.custom_request_c(self.bd_naryad, query, hat_c=False, rez_dict=False)
        orders = get_max_time_order(summ_time)
        orders_time = get_full_time(orders)
        return orders_time

    res = []
    DB_PATH = r'Z:\Data\бд_проекты\plans'
    CURRENT_MONTH = str(DT.now().month).zfill(2)
    CURRENT_YEAR = str(DT.now().year).zfill(4)
    DEST = f'{DB_PATH}{F.sep()}{CURRENT_MONTH}.{CURRENT_YEAR}.pickle'
    if not os.path.exists(DEST):
        CQT.msgbox('Планы не загружены в MES начальником ПДО')
        return None
    with open(DEST, 'rb') as file:
        month_plan = pickle.load(file)
    headers = ['Номер проекта', 'План покраска(ч)', 'План Лазерная резка(ч)', 'План мех обработка(ч)',
               'План сборочно-сварочных работ(ч)', 'Фактически отработанное время по МК(ч)',
               'общий % выполнения сборочно-сварочных работ', 'Плановое время сборочно-сварочных работ за месяц(ч)',
               'работы выполненные в текущем месяце']  # , 'Выполнено в текущем месяце'] # проект, время итого на сборку сварку, потреблено времени Х, осталось времени Y
    res.append(headers)
    for pu, details in month_plan.items():
        row = []
        row.append(pu)
        w1 = details.get('Покраска, час')
        row.append(round(w1, 1) if w1 else '')

        w1 = details.get('Лазерная резка,час')
        row.append(round(w1, 1) if w1 else '')

        w1 = details.get('Мех обработка, час')
        row.append(round(w1, 1) if w1 else '')

        plan_sb_sv = details.get('Сборочно сварочные работы (слесарные+вспомогательные), час')
        row.append(round(plan_sb_sv, 1) if w1 else '')

        current_time = get_order_project_time(pu)  # общее фактически отработтаное вреямя по нарядам
        row.append(current_time)

        if plan_sb_sv and current_time:
            row.append(round(100 * current_time / plan_sb_sv, 1))
        else:
            row.append('')

        w2 = details.get('Нормо часы за текущий период')
        row.append(w2 if w2 else '')

        current_month = get_order_project_time(pu, get_current_month=True)  # работы выполненные в текущем месяце
        row.append(current_month)

        res.append(row)

    return res


@CQT.onerror
def planfact_nar_s_vneplan(self: mywindow, nach, konec, podrazd=None, *args):
    tbl = [['Заказ наряд на изделие ',
            'н/ч норматив',
            'н/ч факт',
            'Отклонение %',
            'Цех',
            'Тип',
            'Дата']]
    rez, list_vid_rab = get_plan_vneplan_data(self, nach, konec, vid='Все', etap='Все')
    for type_nar, etap_user, kat, time, item in list_vid_rab:  # etap_user, type_vneplan, add_time, item_zav_nar
        if time > 0:
            tbl.append([item['Пномер'], round(time / 60, 2),
                        round((F.valm(item['Фвремя']) + F.valm(item['Фвремя2'])) / 60, 2),
                        round(((F.valm(item['Фвремя']) + F.valm(item['Фвремя2'])) - time) / time * 100, 2),
                        "Сборочный цех Производства",
                        type_nar,
                        item['Подтвержд_вып_дата']])
    F.save_file(f'self.vid_report_c.txt', tbl)
    return tbl


@CQT.onerror
def analysis_vneplan_by_vid_rab(self: mywindow, nach, konec, podrazd=None, *args):
    DICT_REPLACE_VIDS = {
        '18549': 'Слесарно-сборочные работы 3 разряд',
        'Слесарно-сборочные работы': 'Слесарно-сборочные работы 3 разряд',
    }
    DICT_KAT_VNEPL = F.deploy_dict_c(
        CSQ.custom_request_c(self.bd_naryad, f"""SELECT * FROM kategor_vnepl WHERE kod > 0""",
                             rez_dict=True), 'value')
    RESP_PROF = CSQ.custom_request_c(self.bd_users,
                                     f'''SELECT * FROM professions INNER JOIN vid_rab_po_dolg 
                ON vid_rab_po_dolg.Вид_работ = professions.вид_работ,
                 group_vid_rab_for_plan ON group_vid_rab_for_plan.name=vid_rab_po_dolg.group_for_plan  WHERE group_vid_rab_for_plan.composite = 0'''
                                     , hat_c=False, rez_dict=True)
    DICT_PROF_ALL = F.deploy_dict_c(RESP_PROF, 'Вид_работ')
    DICT_PROF_ALL_BY_PROF_COD = F.deploy_dict_c(RESP_PROF, 'код')
    rez, list_vid_rab = get_plan_vneplan_data(self, nach, konec, vid='Все', etap='Все')

    list_group = list({_['Группы_для_отчетов'] for _ in DICT_PROF_ALL.values()})

    res_list = []
    set_mk = set()
    nar_pnoms = ', '.join(str(item['Пномер']) for _, _, _, _, item in list_vid_rab)
    response = CSQ.custom_request_c(self.bd_naryad, f'''SELECT 
       jurnal.Пномер,
       jurnal.Дата,
       jurnal.Штамп,
       jurnal.Номер_наряда,
       jurnal.ФИО,
       jurnal.Подытог,
       jurnal.Подытог_нормы,
       jurnal.Статус,
       jurnal.Примечание,
       jurnal.Ном_заверш,
       jurnal.Дата_выгрузки_ЕРП,
       jurnal.ФИО_выгрузки_ЕРП,
       jurnal.Файл_выгрузки_ЕРП,
       jurnal.Минут_выгружено_ЕРП,
       jurnal.base_ERP
     
     FROM jurnal 
                                                    INNER JOIN naryad ON naryad.Пномер = jurnal.Номер_наряда
                                                    INNER JOIN mk ON mk.Пномер = naryad.Номер_мк
                                                    INNER JOIN plan ON plan.Пномер = mk.НомКплан 
                                                    WHERE jurnal.Номер_наряда IN ({nar_pnoms}) 
                                                    and plan.poki == {self.place.poki}''' , rez_dict=True, attach_dbs=(self.db_kplan))
    journal_list = defaultdict(list)
    for item in response:
        journal_list[item['Номер_наряда']].append(item)
    
    dict_date_first_rabot = dict()
    
    for type_nar, etap, kat, time, item in list_vid_rab:
        if kat in DICT_KAT_VNEPL:
            if DICT_KAT_VNEPL[kat]['Коэффициент_наряда'] != 1:
                continue
        jurs = journal_list[item['Пномер']]
        jur_obj = CMS.Jurnal_nar(self.bd_naryad, item['Пномер'], list_dicts_jur=jurs)
        dict_prim = jur_obj.get_dict_primech()
        cex = ''
        if item['fio_jur_zav'] in self.DICT_EMPLOEE_FULL:
            cex = self.DICT_EMPLOEE_FULL[item['fio_jur_zav']]['Подразделение']
        vid_po_napr = ''
        if item['виды_по_напр'] in self.Data.DICT_VID_PO_NAPR:
            vid_po_napr = self.Data.DICT_VID_PO_NAPR[item['виды_по_напр']]['Имя']
            vid_po_napr_id = item['виды_по_напр']
        Фвремя = item['Фвремя']
        if item['fio_jur_zav'] == item['ФИО2']:
            Фвремя = item['Фвремя2']
        
        if int(item['Номер_мк']) not in dict_date_first_rabot:
            dict_date_first_rabot[int(item['Номер_мк'])] = item['Дата_журнал']
        
        tmp_dict = {'Дата_журнал_нач.\n/Дата нач.мк': item['Дата_журнал_нач.'],
                    'Дата_журнал_кон.\n/Дата зав.мк': item['Дата_журнал_кон.'],
                    'Этап': etap,
                    'Вид_по_напр': vid_po_napr,
                    'Вид_по_напр_id': vid_po_napr_id,
                    'Направление': item['Вид'],
                    'ПУ': item['Номер_заказа'],
                    'Номенклатура': item['Номенклатура'],
                    'Количество изд. в мк': item['Количество'],
                    'Тип': type_nar,
                    'Категория': kat,
                    'N кпл': item['НомКплан'],
                    'N Наряда': item['Пномер'],
                    'ФИО': item['fio_jur_zav'],
                    'N МК': item['Номер_мк'],
                    'Tвремя': time,
                    'Норма_времени': item['Норма_времени'],
                    'Фвремя': Фвремя,
                    'Дата_выгрузки_ЕРП':item['Дата_выгрузки_ЕРП'],
                    'ФИО_выгрузки_ЕРП':item['ФИО_выгрузки_ЕРП'],
                    'Минут_выгружено_ЕРП':item['Минут_выгружено_ЕРП'],
                    'base_ERP':item['base_ERP'],
                    'Примечание журнал': str(dict_prim),
                    'Примечание наряд': item['Примечание'],
                    'Подтвержд_вып_дата': item['Подтвержд_вып_дата'],
                    'Коэфф_сложности': item['Коэфф_сложности'],
                    'Цех': cex
                    }
        if item['Дата_завершения']:
            set_mk.add(item['Номер_мк'])
        for k in list_group:
            tmp_dict[k] = 0
        nar = CMS.Naryads(item)
        if kat in DICT_KAT_VNEPL:
            tmp_dict['Сборка+сварка'] += nar.Твремя

        for param in nar.params:
            vid_param = param['Виды_работ']
            if vid_param in DICT_REPLACE_VIDS:
                vid_param = DICT_REPLACE_VIDS[vid_param]
            if vid_param in DICT_PROF_ALL:
                group_tmp = DICT_PROF_ALL[vid_param]['Группы_для_отчетов']
                if group_tmp in tmp_dict:
                    if nar.count_users() > 0:
                        tmp_dict[group_tmp] += param['Опер_время'] / nar.count_users()
                else:
                    print(vid_param)
            else:
                print(f'if {vid_param} not in DICT_PROF_ALL')
        res_list.append(tmp_dict)
    self.analysis_vneplan_by_vid_rab_tmp_res_list = res_list


    for mk in set_mk:
        mk = CMS.Marshrut_cards(mk, self.bd_naryad, self.db_resxml, True)
        if mk.res == None:
            continue
        kat = ''
        if mk.Тип_мк_Имя != 'Плановая':
            if mk.дорезки_мк_Причина != None and mk.дорезки_мк_Причина != '':
                kat = mk.дорезки_мк_Причина
            elif mk.тип_доработок_Имя != None and mk.тип_доработок_Имя != '':
                kat = mk.тип_доработок_Имя
            elif mk.тип_дорезок_Имя != None and mk.тип_дорезок_Имя != '':
                kat = mk.тип_доработок_Имя
        date_nach_mk = ''
        if mk.Пномер in dict_date_first_rabot:
            date_nach_mk = dict_date_first_rabot[mk.Пномер]
        tmp_dict = {'Дата_журнал_нач.\n/Дата нач.мк': date_nach_mk,
                    'Дата_журнал_кон.\n/Дата зав.мк': mk.Дата_завершения,
                    'Этап': '',
                    'Направление': mk.Вид,
                    'ПУ': mk.Номер_заказа,
                    'Номенклатура': mk.Номенклатура,
                    'Количество изд. в мк': mk.Количество,
                    'ФИО': "Неосвоенные цехом работы",
                    'Тип': mk.Тип_мк_Имя,
                    'Категория': kat,
                    'N кпл': mk.НомКплан,
                    'N Наряда': 0,
                    'N МК': mk.Пномер,
                    'Tвремя': 0,
                    'Подтвержд_вып_дата':''
                    }
        for k in list_group:
            tmp_dict[k] = 0

        for dse in mk.res:
            for oper in dse['Операции']:
                neosv = dse['Количество']
                if 'Закрыто,шт.' in oper:
                    neosv = dse['Количество'] - oper['Закрыто,шт.']
                if neosv <= 0:
                    continue
                if oper['Опер_профессия_код'] in DICT_PROF_ALL_BY_PROF_COD:
                    group_tmp = DICT_PROF_ALL_BY_PROF_COD[oper['Опер_профессия_код']]['Группы_для_отчетов']
                    if group_tmp in tmp_dict:
                        tmp_dict[group_tmp] -= (oper['Опер_Тпз'] + oper['Опер_Тшт_ед'] * neosv)
                    else:
                        print(group_tmp)
        res_list.append(tmp_dict)
    return res_list


@CQT.onerror
def analysis_effectiv_work_per_minute(self: mywindow, nach, konec, podrazd=None, *args):
    """
    1 Вычислить все МК, закрытые в периоде, разнести по ПУ и по месяцам
    2 все МК представить в виде трудовпо видам(ресурсная)
        2.1 отразить труды плановые и освоенные плановые
        2.2 отразить внеплановые МК с осваяемыми трудами
    3 по кадому месяцу из табеля ЕРП получить факт. присутствие по видам работ
    3 по каждому виду работ посчитать среднюю по месяцу (  план, осваяемый план, внеплан, присутствие по ЕРП)
    4 вывести таблицу, в минутах среднюю за месяц
        строки- виды работ
        колонки -(  план, осваяемый план, внеплан, присутствие по ЕРП) в минутах
    """

    def summ_dict_vid_rab(base_dict, add_dict, koef_downgrade=1):
        if koef_downgrade == 0:
            return base_dict
        for k, v in add_dict.items():
            if k in base_dict:
                base_dict[k] += v / koef_downgrade
            else:
                base_dict[k] = v / koef_downgrade
        return base_dict

    def calc_deviation_dicts_vid_rab(plan_dict, vneplan_dict):
        dict_deviation = dict()

        for k, v in plan_dict.items():
            if k not in dict_deviation:
                dict_deviation[k] = dict()
                dict_deviation[k]['План'] = 0
                dict_deviation[k]['Внеплан'] = 0
            dict_deviation[k]['План'] += v

        for k, v in vneplan_dict.items():
            if k not in dict_deviation:
                dict_deviation[k] = dict()
                dict_deviation[k]['План'] = 0
                dict_deviation[k]['Внеплан'] = 0
            dict_deviation[k]['Внеплан'] += v

        for k, v in dict_deviation.items():
            dict_deviation[k]['План'] = round(dict_deviation[k]['План'])
            dict_deviation[k]['Внеплан'] = round(dict_deviation[k]['Внеплан'])
            dict_deviation[k]['deviation_%'] = 0
            if v['План'] == 0 and v['Внеплан'] != 0:
                dict_deviation[k]['deviation_%'] = 100
            elif v['План'] == 0 and v['Внеплан'] == 0:
                dict_deviation[k]['deviation_%'] = 0
            else:
                dict_deviation[k]['deviation_%'] = round(v['Внеплан'] / v['План'] * 100, 2)
        return {k: v['deviation_%'] for k, v in dict_deviation.items()}

    name_file = F.put_po_umolch() + F.sep() + F.now("analysis_effectiv_work_per_minute_list_mk_%Y%m%d.pickle")
    if F.existence_file_c(name_file):
        list_mk = F.load_file_pickle(name_file)
    else:
        list_mk = CSQ.custom_request_c(self.bd_naryad, f"""
                SELECT 
                mk.Пномер,
                mk.Дата,
                mk.Статус,
                mk.Номенклатура,
                mk.Номер_заказа,
                mk.Номер_проекта,
                mk.Вид,
                mk.Примечание,
                mk.Основание,
                mk.Прогресс,
                mk.Приоритет,
                mk.Направление,
                mk.Вес,
                mk.xml,
                mk.Количество,
                mk.Статус_ЧПУ,
                mk.Ресурсная,
                mk.Дата_завершения,
                mk.Коэф_парал,
                mk.Обеспечение,
                mk.Место,
                mk.Искл_план_рм,
                mk.Тип,
                mk.Ресурсная_дата,
                mk.ФИО,
                mk.НомКплан,
                mk.check_execute_opers,
                mk.Тип_доработки,
                mk.На_удал,
                
                дорезки_мк.Причина AS дорезки_мк_Причина,
                
                тип_дорезок.Имя AS тип_дорезок_Имя,
                тип_дорезок.Коэффициент_наряда AS тип_дорезок_Коэффициент_наряда,
                
                тип_доработок.Имя AS тип_доработок_Имя,
                тип_доработок.Коэффициент_наряда AS тип_доработок_Коэффициент_наряда,
                
                Тип_мк.Имя AS Тип_мк_Имя,
                Тип_мк.rgb AS Тип_мк_rgb

                 FROM mk LEFT JOIN дорезки_мк ON дорезки_мк.Номер_мк = mk.Пномер  
                LEFT JOIN тип_дорезок ON тип_дорезок.Пномер = дорезки_мк.Причина  
                LEFT JOIN тип_доработок ON тип_доработок.Пномер = mk.Тип_доработки 
                                LEFT JOIN Тип_мк ON Тип_мк.Пномер = mk.Тип            
                                WHERE mk.Дата_завершения != ""
            and datetime(mk.Дата_завершения) >= datetime("{nach}") and datetime(mk.Дата_завершения) < datetime("{konec}")
                   ;""", rez_dict=True)
        F.save_file_pickle(name_file, list_mk)

    DICT_PROF_ALL = F.deploy_dict_c(CSQ.custom_request_c(self.bd_users,
                                                         f'''SELECT * FROM professions INNER JOIN vid_rab_po_dolg 
            ON vid_rab_po_dolg.Вид_работ = professions.вид_работ,
             group_vid_rab_for_plan ON group_vid_rab_for_plan.name=vid_rab_po_dolg.group_for_plan WHERE group_vid_rab_for_plan.composite = 0'''
                                                         , hat_c=False, rez_dict=True), 'код')

    name_file = F.put_po_umolch() + F.sep() + F.now("analysis_effectiv_work_per_minute_dict_res_%Y%m%d.pickle")
    if F.existence_file_c(name_file):
        dict_res = F.load_file_pickle(name_file)
    else:
        list_nom_mk = [_['Пномер'] for _ in list_mk]
        list_res = CSQ.custom_request_c(self.db_resxml, f'''SELECT 
        Номер_мк, data FROM res WHERE Номер_мк in ({CSQ.prepare_list_to_tuple(list_nom_mk)});''', rez_dict=True)
        dict_res = F.deploy_dict_c(list_res, 'Номер_мк')
        F.save_file_pickle(name_file, dict_res)

    dict_moth = dict()
    dict_moth_calc_ed = dict()

    for item in list_mk:
        mk = CMS.Marshrut_cards(0, self.bd_naryad, self.db_resxml, True, item, dict_res[item['Пномер']])

        nom_kpl = mk.НомКплан
        if nom_kpl not in dict_moth:
            dict_moth[nom_kpl] = {'Кол_во_план': 0,
                                  'План_рес_ед(мин.)': dict(),
                                  'План_освоено_ед(мин.)': dict(),
                                  'Внеплан_кол': dict(),
                                  'month': ''
                                  }

        month = mk.get_month_zaversh()

        if month not in dict_moth_calc_ed:
            dict_moth_calc_ed[month] = dict()
            dict_moth_calc_ed[month]['План_рес_ед(мин.)'] = dict()
            dict_moth_calc_ed[month]['План_освоено_ед(мин.)'] = dict()
            dict_moth_calc_ed[month]['Внеплан_ед(мин.)'] = dict()

        if mk.Тип_мк_Имя == 'Плановая':
            dict_moth[nom_kpl]['Кол_во_план'] += mk.count_izdeliy()
            dict_moth[nom_kpl]['План_рес_ед(мин.)'] = summ_dict_vid_rab(dict_moth[nom_kpl]['План_рес_ед(мин.)'],
                                                                        mk.get_dict_vid_rab(DICT_PROF_ALL))
            dict_moth[nom_kpl]['План_освоено_ед(мин.)'] = summ_dict_vid_rab(dict_moth[nom_kpl]['План_освоено_ед(мин.)'],
                                                                            mk.get_dict_vid_rab(DICT_PROF_ALL, True))
            dict_moth[nom_kpl]['month'] = month
        else:
            dict_moth[nom_kpl]['Внеплан_кол'] = summ_dict_vid_rab(dict_moth[nom_kpl]['Внеплан_кол'],
                                                                  mk.get_dict_vid_rab(DICT_PROF_ALL, True,
                                                                                      by_one_izd=False))

    for num_kpl in dict_moth.keys():
        if dict_moth[num_kpl]['Кол_во_план'] == 0:
            continue
        month = dict_moth[num_kpl]['month']
        dict_moth_calc_ed[month]['План_рес_ед(мин.)'] = summ_dict_vid_rab(dict_moth_calc_ed[month]['План_рес_ед(мин.)'],
                                                                          dict_moth[num_kpl]['План_рес_ед(мин.)'])
        dict_moth_calc_ed[month]['План_освоено_ед(мин.)'] = summ_dict_vid_rab(
            dict_moth_calc_ed[month]['План_освоено_ед(мин.)'], dict_moth[num_kpl]['План_освоено_ед(мин.)'])
        dict_moth_calc_ed[month]['Внеплан_ед(мин.)'] = summ_dict_vid_rab(dict_moth_calc_ed[month]['Внеплан_ед(мин.)'],
                                                                         dict_moth[num_kpl]['Внеплан_кол'],
                                                                         dict_moth[num_kpl]['Кол_во_план'])

    for month in dict_moth_calc_ed.keys():
        dict_moth_calc_ed[month]['Отклонение_в_%'] = calc_deviation_dicts_vid_rab(
            dict_moth_calc_ed[month]['План_рес_ед(мин.)'], dict_moth_calc_ed[month]['Внеплан_ед(мин.)'])
        dict_moth_calc_ed[month]['План_рес_ед(мин.)'] = {k: round(v) for k, v in
                                                         dict_moth_calc_ed[month]['План_рес_ед(мин.)'].items()}
        dict_moth_calc_ed[month]['План_освоено_ед(мин.)'] = {k: round(v) for k, v in
                                                             dict_moth_calc_ed[month]['План_освоено_ед(мин.)'].items()}
        dict_moth_calc_ed[month]['Внеплан_ед(мин.)'] = {k: round(v) for k, v in
                                                        dict_moth_calc_ed[month]['Внеплан_ед(мин.)'].items()}

    name_file = F.put_po_umolch() + F.sep() + F.now("result_analysis_effectiv_work_per_minute_%Y%m%d.json")
    F.write_json_c(dict_moth_calc_ed, name_file, False)
    print()
    list_of_dicts = []
    for month in dict_moth_calc_ed.keys():
        for type_data in dict_moth_calc_ed[month].keys():
            tmp = copy.deepcopy(dict_moth_calc_ed[month][type_data])
            tmp['Тип'] = type_data
            tmp['Месяц'] = month
            list_of_dicts.append(tmp)
    res = F.list_of_dicts_to_list_of_lists(list_of_dicts)
    res.append(['' for _ in res[0]])
    res.append(['' for _ in res[0]])
    return res


@CQT.onerror
def ready_procent_ver2(self, nach, konec, podrazd='010301', *args):
    ''' строки формируются списками, нулевая строка- заголовки
    '''
    query = f'''SELECT naryad.Номер_мк, naryad.Подтвержд_вып_дата 
, mk.Номер_заказа 
, mk.Номер_проекта 
, mk.Вид 
, mk.Вес 
, mk.Номенклатура  
, Тип_мк.Имя  as Тип
, naryad.ФИО 
, naryad.Фвремя 
, naryad.ФИО2 
, naryad.Фвремя2 
, naryad.Твремя 
, naryad.Операции 
, naryad.Опер_время 
 FROM naryad INNER JOIN mk ON mk.Пномер = naryad.Номер_мк,
  Тип_мк ON Тип_мк.Пномер = mk.Тип WHERE mk.Статус == "Открыта" '''
    resp = CSQ.custom_request_c(self.bd_naryad, query, rez_dict=True)

    dict_mk = dict()
    for item in resp:
        list_opers = item['Операции'].split("|")
        list_time = item['Опер_время'].split("|")
        if item['Номер_мк'] not in dict_mk:
            dict_mk[item['Номер_мк']] = {
                'Номер_заказа': item['Номер_заказа'],
                'Номер_проекта': item['Номер_проекта'],
                'Вид': item['Вид'],
                'Вес': item['Вес'],
                'Номенклатура': item['Номенклатура'],
                'Тип': item['Тип'],
                'План': dict(),
                'Факт': dict(),
            }
        for i, oper in enumerate(list_opers):
            oper_name = oper.split("$")[-1]
            if oper_name not in self.DICT_OPER_FULL:
                continue
            etap = self.DICT_OPER_FULL[oper_name]['rc']
            time = list_time[i]
            if etap not in dict_mk[item['Номер_мк']]['План']:
                dict_mk[item['Номер_мк']]['План'][etap] = 0
                dict_mk[item['Номер_мк']]['Факт'][etap] = 0
            dict_mk[item['Номер_мк']]['Факт'][etap] += F.valm(time)

    for nom_mk in dict_mk:
        res = CMS.load_res(nom_mk)
        for dse in res:
            for oper in dse['Операции']:
                kod = oper['Опер_РЦ_код']
                time = oper['Опер_Тпз'] + oper['Опер_Тшт']
                if kod not in dict_mk[nom_mk]['План']:
                    dict_mk[nom_mk]['План'][kod] = 0
                    dict_mk[nom_mk]['Факт'][kod] = 0
                dict_mk[nom_mk]['План'][kod] += time

    res = [['Номер_МК', 'Номер_заказа', 'Номер_проекта', 'Вид', 'Номенклатура', 'Тип', 'Вес,кг*(с поправкой)',
            'Всего, н-см.', 'Освоено, н-см.', "Процент %", 'Вес_осталось,кг']]
    for nom_mk in dict_mk:
        plan = 0
        fact = 0
        for kod in dict_mk[nom_mk]['План']:
            if kod[:4] == podrazd[:4]:
                plan += dict_mk[nom_mk]['План'][kod]
        for kod in dict_mk[nom_mk]['Факт']:
            if kod[:4] == podrazd[:4]:
                fact += dict_mk[nom_mk]['Факт'][kod]
        if fact <= 0:
            continue
        proc = 0
        if plan > 0:
            proc = round(fact / plan * 100, 1)
        ves = round(F.valm(dict_mk[nom_mk]['Вес']) / 1.482, 1)
        ost = round((100 - proc) * ves / 100, 1)
        if ost < 0:
            ost = 0
        tmp = [nom_mk, dict_mk[nom_mk]['Номер_заказа'], dict_mk[nom_mk]['Номер_проекта'], dict_mk[nom_mk]['Вид']
            , dict_mk[nom_mk]['Номенклатура'], dict_mk[nom_mk]['Тип']
            , ves, round(plan / 480, 1), round(fact / 480, 1), proc, ost]
        res.append(tmp)

    res = F.sort_by_column_c(res, 'Процент %')
    res.append(['' for _ in res[0]])
    res.append(['' for _ in res[0]])
    return res


def sravn_nv_napr(self, data_nach, data_kon):
    query = f"""SELECT DISTINCT naryad.Пномер, naryad.Дата, naryad.Твремя, naryad.Фвремя, naryad.Фвремя2, 
    naryad.ФИО, naryad.ФИО2, mk.Направление, naryad.Опер_время, naryad.Операции FROM naryad 
INNER JOIN mk ON mk.Пномер == naryad.Номер_мк
INNER JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер
WHERE naryad.Подтвержд_вып == 1 AND datetime(naryad.Дата) > datetime("{data_nach}") 
                and datetime(naryad.Дата) < datetime("{data_kon}") and mk.Направление != 'ПТ' and naryad.Внеплан = 0"""
    dict_rez = dict()
    responce = CSQ.custom_request_c(self.bd_naryad, query, rez_dict=True)
    set_napr = set()
    for item in responce:
        set_napr.add(item['Направление'])
    list_napr = sorted(list(set_napr))
    dict_shabl_napr = dict()

    for napr in list_napr:
        dict_shabl_napr[napr] = {'val_abs': 0, 'val': 0, 'count': 0}
    for item in responce:
        fl_add = True
        list_oper = [_.split("$")[-1] for _ in item['Операции'].split("|")]
        for oper in list_oper:
            if oper in self.DICT_OPER_FULL:
                if self.DICT_OPER_FULL[oper]['Вспомогат']:
                    fl_add = False
                    break
        if fl_add == False:
            continue
        month = F.datetostr(F.strtodate(item['Дата']), "%Y-%m")
        if month not in dict_rez:
            dict_rez[month] = copy.deepcopy(dict_shabl_napr)
        fvrem = F.valm(item['Фвремя']) + F.valm(item['Фвремя2'])
        tvrem = F.valm(item['Твремя']) * bool(item['ФИО']) + F.valm(item['Твремя']) * bool(item['ФИО2'])
        if fvrem == 0 or tvrem == 0:
            continue
        delta_abs = abs(tvrem - fvrem) / tvrem * 100
        delta = (tvrem - fvrem) / tvrem * 100
        if delta_abs < 400:
            dict_rez[month][item['Направление']]['val_abs'] += delta_abs
            dict_rez[month][item['Направление']]['val'] += delta
            dict_rez[month][item['Направление']]['count'] += 1
        else:
            print(f"{item['Пномер']} - abs {delta_abs}")
    rez = []
    for month in dict_rez.keys():
        tmp_line = {'Месяц': month}
        summ_napr = 0
        summ_napr_abs = 0
        count_summ_napr = 0
        for napr in dict_rez[month]:
            tmp_line[f'{napr}_абс'] = round(dict_rez[month][napr]['val_abs'] / dict_rez[month][napr]['count'])
            tmp_line[f'{napr}'] = round(dict_rez[month][napr]['val'] / dict_rez[month][napr]['count'])
            summ_napr += dict_rez[month][napr]['val'] / dict_rez[month][napr]['count']
            summ_napr_abs += dict_rez[month][napr]['val_abs'] / dict_rez[month][napr]['count']
            count_summ_napr += 1
        summ_napr = round(summ_napr / count_summ_napr)
        summ_napr_abs = round(summ_napr_abs / count_summ_napr)
        tmp_line[f'Среднее'] = summ_napr
        tmp_line[f'Среднее_абс'] = summ_napr_abs
        rez.append(tmp_line)
    rez = F.list_of_dicts_to_list_of_lists(rez)
    rez = F.sort_by_column_c(rez, "Месяц", date_time=True, date_format="%Y-%m")
    create_gant(self, rez)
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez


@CQT.onerror
def report_c_selector_2(self, nach, konec, vid, *args):
    text = f""" SELECT napravlenie.name as Направление, napravl_deyat.Псевдоним as Псевдоним, пл_оуп.№проекта  as "№ проекта", 
     знпр.№проекта  as "Заказ на производство.№проекта", знпр.№ERP  as "Номер заказа на производство", 
    
    plan.Пномер as "Номер КПЛ",
    plan.Дата_внесения as "Дата внесения в МЕС",
    пл_заг.ПДата_нач_заг as "Плановая дата начала заготовительного участка",
    пл_компл.ПДата_зав_комплект_упаковки as "Плановая Дата завершения комплектации упаковки",
    пл_оуп.Дата_отгрузки_ПУ as "Плановая Дата отгрузки ПУ",
    plan.Фдата_получения_КД as "Фактическая дата получения КД",
    пл_сб.Прогноз_дата_зав_сб as "Прогнозируемая дата завершения производства",
    plan.Позиция as "Позиция",
    пл_оуп.Количество as "Количество",
    пл_оуп.Номенклатура_ЕРП as "Номенклатура ЕРП",
    пл_сб.Примечание_сб as "Примечание сборочный участок",
    plan.Примечание as "ПДО Примечание",
    пл_осил.Примечание as "ПДО Заявки на закуп",
    plan.Статус as "Статус",
    plan.Статус_норм as "Статус норм",
    plan.МК as "Плановая МК №"


    
    
    FROM plan 

    LEFT JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер 
    LEFT JOIN пл_заг ON пл_заг.НомПл = plan.Пномер 
    LEFT JOIN пл_компл ON пл_компл.НомПл = plan.Пномер 
    LEFT JOIN пл_сб ON пл_сб.НомПл = plan.Пномер 
    LEFT JOIN пл_осил ON пл_осил.НомПл = plan.Пномер 
    LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
    LEFT JOIN napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности 
    LEFT JOIN napravlenie ON napravlenie.Пномер = napravl_deyat.Направление   
    LEFT JOIN status_poz ON status_poz.Пномер = plan.Статус   
    
     WHERE status_poz.Имя IN ('Резерв','Подготовка','Изготовление','Приостановлена','К производству')"""
    
    rez = CSQ.custom_request_c(self.db_kplan,text,rez_dict=True)
    return rez

@CQT.onerror
def report_c_selector(self, nach, konec, vid, *args):
    list_zamech = CSQ.custom_request_c(self.bd_selector, '''SELECT * FROM zamech''', hat_c=True, rez_dict=True)
    hat_c = list(list_zamech[0].keys())
    block_add = []
    block_zakr = []
    block_nezakr = []
    block_plan = []
    block_prosrochka = []
    rez = []
    nach = F.strtodate(nach)
    konec = F.strtodate(konec)

    for item in list_zamech:
        d_vopr = F.strtodate(item['Дата_вопроса'], "%Y-%m-%d")
        d_plan = F.date_add_days(d_vopr, item['Дней_на_решение'], '', '')
        if item['Дата_решения'] == '':
            d_zaversh = ''
        else:
            d_zaversh = F.strtodate(item['Дата_решения'], "%Y-%m-%d")
        if d_vopr >= nach and d_vopr <= konec:
            block_add.append(item)
        if d_zaversh != '':
            if d_zaversh >= nach and d_zaversh <= konec:
                block_zakr.append(item)
        else:
            block_nezakr.append(item)
        if d_plan >= nach and d_plan <= konec:
            block_plan.append(item)

        if d_vopr >= nach and d_vopr <= konec:
            if item['Дата_решения'] == '':
                if d_plan < F.now(''):
                    block_prosrochka.append(item)
            else:
                if d_plan < d_zaversh:
                    block_prosrochka.append(item)

    if vid == 'Добавлено':
        block_add = F.list_of_dicts_to_list_of_lists(block_add)
        return block_add
    if vid == 'Закрыто':
        block_zakr = F.list_of_dicts_to_list_of_lists(block_zakr)
        return block_zakr
    if vid == 'Не закрыто':
        block_nezakr = F.list_of_dicts_to_list_of_lists(block_nezakr)
        return block_nezakr
    if vid == 'Все':
        list_zamech = F.list_of_dicts_to_list_of_lists(list_zamech)
        return list_zamech
    if vid == 'По плану закрыть':
        block_plan = F.list_of_dicts_to_list_of_lists(block_plan)
        return block_plan
    if vid == 'Просрочены':
        block_prosrochka = F.list_of_dicts_to_list_of_lists(block_prosrochka)
        return block_prosrochka
    return


@CQT.onerror
def tekush_raboty(self, podrazd, *args):
    # custom_request_c = f'''SELECT * FROM user_rc'''
    # rez = CSQ.custom_request_c(self.bd_users,custom_request_c,rez_dict=True)
    itog = [['ФИО', 'Раб.место', 'Смена', "Номер_проекта", "Номер_заказа", "Направление", "Номер_наряда",
             "Дата", "Примечание наярда", "Задание"]]
    con, cur = CSQ.connect_bd(self.bd_naryad)
    for user in self.DICT_EMPLOEE_RC.keys():
        fio = ' '.join(user.split()[:3])
        if self.DICT_EMPLOEE_RC[user][:4] == podrazd[:4]:
            custom_request_c = f'''SELECT "" as "ФИО","" as "РМ", "" as "Смена", mk.Номер_проекта, mk.Номер_заказа, mk.Направление, jurnal.Номер_наряда,
                    jurnal.Дата, naryad.Примечание, naryad.Задание FROM jurnal 
                    INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
                    INNER JOIN mk ON naryad.Номер_мк == mk.Пномер WHERE jurnal.ФИО == "{fio}" AND
            jurnal.Статус == "Начат" and jurnal.Подытог == 0'''
            rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=False, conn=con)
            if len(rez) != 0:
                rez[0][0] = fio
                rez[0][1] = f"{self.DICT_EMPLOEE_RM[user]['Пномер']}({self.DICT_EMPLOEE_RM[user]['Прозвище']})"
                rez[0][2] = f"{self.DICT_EMPLOEE_RM[user]['Смена']}"
                itog.append(rez[0])
            else:
                itog.append([fio, f"{self.DICT_EMPLOEE_RM[user]['Пномер']}({self.DICT_EMPLOEE_RM[user]['Прозвище']})",
                             f"{self.DICT_EMPLOEE_RM[user]['Смена']}", "", "", "", "", "", "",
                             ""])
    CSQ.close_bd(con)
    return itog


@CQT.onerror
def vneplan_rabot(self, data_nach, data_kon, *args):
    custom_request_c = f"""SELECT mk.Номер_проекта, mk.Номер_заказа, mk.Направление,
                naryad.Твремя, jurnal.ФИО AS "ФИО_журнал", jurnal.Примечание AS "Примеч_журнал",  
                naryad.ФИО, naryad.Фвремя, naryad.ФИО2, 
                naryad.Фвремя2, naryad.Задание,naryad.Пномер as "Наряд_пномер",  naryad.Примечание AS "Примеч_наряд", 
                naryad.Номер_мк, naryad.Внеплан , kategor_vnepl.value FROM jurnal 
                INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
                INNER JOIN mk ON naryad.Номер_мк == mk.Пномер 
                INNER JOIN kategor_vnepl ON kategor_vnepl.kod == naryad.Категория_внепл  
                WHERE jurnal.Статус == "Завершен" AND naryad.Внеплан != 0 AND datetime(jurnal.Дата) > datetime("{data_nach}") 
                and datetime(jurnal.Дата) < datetime("{data_kon}") """
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True)
    if rez_jur == []:
        CQT.msgbox('Пусто')
        return
    return rez_jur


@CQT.onerror
def jurnal_rabot(self, data_nach, data_kon, *args): #28.01.2026
    custom_request_c = f"""
        SELECT                                  
            CASE WHEN знпр.№проекта 
                IS NOT NULL 
                THEN знпр.№проекта 
                ELSE mk.Номер_проекта 
            END AS "Номер_проекта", 
            CASE WHEN знпр.№ERP IS NOT NULL 
                THEN знпр.№ERP 
                ELSE mk.Номер_заказа 
            END AS Номер_заказа, 
            jurnal.Дата as "Дата_журнал", 
            jurnal.ФИО AS "ФИО_журнал", 
            jurnal.ФИО AS "Должность", 
            jurnal.Статус, 
            jurnal.Подытог, 
            jurnal.Подытог_нормы as "Для трудозатрат",
            jurnal.Дата_выгрузки_ЕРП,
            jurnal.ФИО_выгрузки_ЕРП,
            jurnal.Минут_выгружено_ЕРП, 
            jurnal.Примечание AS "Примеч_журнал", 
            naryad.Твремя, naryad.Пномер as "Наряд_пномер", 
            naryad.ФИО, naryad.Фвремя, naryad.ФИО2, 
            naryad.Фвремя2, naryad.Задание, naryad.Примечание AS "Примеч_наряд", 
            naryad.Номер_мк, 
            коды_веплана_для_наряда.name AS "Внеплан"
        FROM jurnal 
        INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
        LEFT JOIN коды_веплана_для_наряда ON коды_веплана_для_наряда.code = naryad.Внеплан 
        INNER JOIN mk ON naryad.Номер_мк == mk.Пномер
        LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
        LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан
        LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
        WHERE коды_веплана_для_наряда.poki == {self.place.poki} and datetime(jurnal.Дата) > datetime("{data_nach}") 
            and datetime(jurnal.Дата) < datetime("{data_kon}") """

    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True,attach_dbs=(self.db_kplan))
    if rez_jur == False:
        CQT.msgbox(f'Не удалось загрузить данные из БД, занята попробуй позже.')
        return
    nk_dolgn = F.num_col_by_name_in_hat_c(rez_jur, 'Должность')
    for i in range(1, len(rez_jur)):
        if rez_jur[i][nk_dolgn] in self.DICT_EMPLOEE:
            rez_jur[i][nk_dolgn] = self.DICT_EMPLOEE[rez_jur[i][nk_dolgn]]
        else:
            rez_jur[i][nk_dolgn] = 'Не найдено в БД'
    rez_summ = ['' for _ in rez_jur[0]]
    rez_jur.append(rez_summ)
    if rez_jur == []:
        CQT.msgbox('Пусто')
        return
    return rez_jur


@CQT.onerror
def plan_rabot_preload(self, nach, konec, podrazd):
    gp = check_import_modyle('gant_ploty')
    if gp is None:
        import gant_ploty as gp
    list_tables = CSQ.get_list_of_tables_c(self.bd_users)
    max_date = 'mtdz_2000_06_01'
    for table in list_tables:
        if F.is_date(table, "mtdz_%Y_%m_%d"):
            if F.strtodate(table, "mtdz_%Y_%m_%d") > F.strtodate(max_date, "mtdz_%Y_%m_%d"):
                max_date = table
    max_date_dt = F.strtodate(max_date, "mtdz_%Y_%m_%d")
    if F.strtodate(self.ui.le_end_of_period.text(), "%Y-%m-%d %H:%M:%S") > max_date_dt:
        CQT.msgbox(f'Конец периода не может быть больше {max_date}')
        return
    rez_spis = plan_rabot(self, nach, konec, podrazd)
    if rez_spis == None:
        return
    self.plan_for_gant = rez_spis
    load_parametrs_gant(self)
    try:
        load_browser(self)
        fig = gp.fig_podetalno_narc_projects(self.plan_for_gant, 'РЦ',
                                             "01030",
                                             "ДСЕ", self.ui.cmb_gant_tochnost_dat.currentText())
        CQT.output_gant(self, fig, self.browser, self.vid_report_c + '_' + self.ui.cmb_podrazdelenie.currentText())
    except:
        CQT.msgbox(f'Проблема с выводом графика')
    return rez_spis


def check_import_modyle(name: str) -> object:
    import sys
    return next((mod for mod_name, mod in sys.modules.items() if name == mod_name.split('.')[-1]), None)



@CQT.onerror
def ponedelniy_grafik_vir_otgr(self, data_nach, data_kon, etap, *args):
    GR = check_import_modyle('grafics')
    if GR is None:
        import grafics as GR
    KOEFF_TKANI = 1
    self.debug = []
    tmp_data = F.strtodate(data_nach)
    conn, cur = CSQ.connect_bd(self.bd_naryad)
    conn_mat, cur_mat = CSQ.connect_bd(self.bd_mat)
    rez = [['Дата начала', "Дата конца", "Выработка, н-см.", "Заверш. вес, кг.", "Чист. вес, кг.", "%Техн. от выработ.",
            "Постов", "Произв-ть,н-см./см."]]
    rez_gr = [['Дата начала', "Дата конца", "Выработка, н-см.", "Заверш. вес, кг.", "Чист. вес, кг.", "Постов",
               "Произв-ть,н-см./см."]]
    while tmp_data < F.strtodate(data_kon):
        tmp_data_nach, tmp_data_kon = F.start_end_dates_c(F.datetostr(tmp_data), vid='n')
        self.debug.append(f'{tmp_data_nach} - {tmp_data_kon}')
        vir, ves, ves_tehn = vir_otgr(self, tmp_data_nach, tmp_data_kon, etap, conn, conn_mat)
        posesh = rasch_posesh(self, tmp_data_nach, tmp_data_kon, etap, conn)
        poizvodit = 0
        if posesh > 0:
            poizvodit = round((vir / 5) / posesh, 2)
        rez.append([tmp_data_nach, tmp_data_kon, vir, round(ves * KOEFF_TKANI), ves_tehn,
                    f'{round(100 * (ves_tehn + 1) / (vir + 1), 1)}%', posesh / 2, poizvodit])
        rez_gr.append([tmp_data_nach.split()[0], tmp_data_kon.split()[0], vir, round(ves / 100, 2), ves_tehn,
                       posesh / 2 * 10, int(poizvodit * 100)])
        tmp_data = tmp_data + timedelta(days=7)
    CSQ.close_bd(conn)
    CSQ.close_bd(conn_mat)
    # fig = GR.test()
    try:
        self.parent_for_grafic.removeWidget(self.toolbar)
        self.parent_for_grafic.removeWidget(self.canvas)
    except:
        pass
    GR.load_elements(self, rez_gr, 'Понедельный график выработки и отгрузок')
    self.parent_for_grafic.addWidget(self.toolbar)
    self.parent_for_grafic.addWidget(self.canvas)
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez


@CQT.onerror
def rasch_posesh(self, data_nach, data_kon, etap, conn, *args):
    custom_request_c = f"""SELECT jurnal.Дата, jurnal.ФИО  FROM jurnal INNER JOIN naryad
            ON jurnal.Номер_наряда = naryad.Пномер WHERE datetime(jurnal.Дата) > datetime("{data_nach}") 
        and datetime(jurnal.Дата) < datetime("{data_kon}")"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True, conn=conn)
    dict_poseshenie = dict()
    list_full_empl = [key for key in self.DICT_EMPLOEE_RC.keys() if self.DICT_EMPLOEE_RC[key][:4] == '0103']
    for naryad in rez_jur:
        fio_rc = self.calc_stage(naryad['ФИО'])
        if fio_rc == None:
            print(f'Не найден этап для {naryad["ФИО"]}')
            self.debug.append(f'Не найден этап для {naryad["ФИО"]}')
            continue
        if fio_rc[:4] == self.ui.cmb_podrazdelenie.currentText()[:4]:
            day = F.start_end_dates_c(naryad['Дата'], vid="d", format_out="%Y-%m-%d")[0]
            if day in dict_poseshenie:
                dict_poseshenie[day][naryad['ФИО']] = 1
            else:
                dict_poseshenie[day] = dict()
                dict_poseshenie[day][naryad['ФИО']] = 1

    posesh_count = 0
    for day in dict_poseshenie.keys():
        print(f'{day} : {len(dict_poseshenie[day].keys()) / 2}')
        # list_full_empl_tmp = copy.deepcopy(list_full_empl)
        for fio in dict_poseshenie[day].keys():
            if fio not in self.DICT_EMPLOEE:
                print(f'Надо занести в ЕМПЛ {fio}')
            else:
                fiod = f'{fio} {self.DICT_EMPLOEE[fio]}'
                # print(fiod)
                if fiod in list_full_empl:
                    pass
                #    list_full_empl_tmp.remove(fiod)
                else:
                    print(f'Надо занести в РЦ {fiod}')
        posesh_count += len(dict_poseshenie[day].keys())
        # print(f'Не было {list_full_empl_tmp}')
    posesh = posesh_count / 5
    return posesh


@CQT.onerror
def vir_otgr(self, data_nach, data_kon, etap, conn, conn_mat, *args):
    minut_smen = 480

    # PROIZVODITELNOST_POST_SM = 34
    # в ДБ с рейтин юсерз вписать рц чей работник, провести цикл на сравнение фамилий завершено с цехомю.
    custom_request_c = f"""SELECT jurnal.Дата, jurnal.ФИО, jurnal.Статус, jurnal.Номер_наряда, 
        naryad.Твремя, naryad.ДСЕ_ID, naryad.Операции,naryad.Опер_время, naryad.Номер_мк, naryad.Внеплан, naryad.ФИО, naryad.ФИО2,  
        naryad.Фвремя, naryad.Фвремя2 FROM jurnal INNER JOIN naryad
        ON jurnal.Номер_наряда = naryad.Пномер WHERE jurnal.Статус == "Завершен"
    and datetime(jurnal.Дата) > datetime("{data_nach}") and datetime(jurnal.Дата) < datetime("{data_kon}") AND naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True, conn=conn)
    summ = 0
    list_full_empl = [key for key in self.DICT_EMPLOEE_RC.keys() if self.DICT_EMPLOEE_RC[key][:4] == '0103']
    for naryad in rez_jur:
        fio_rc = self.calc_stage(naryad['ФИО'])
        if fio_rc == None:
            continue
        if fio_rc[:4] == self.ui.cmb_podrazdelenie.currentText()[:4]:

            if naryad['Внеплан'] == 0:
                bilo = naryad['Твремя']
                if self.ui.cmb_podrazdelenie.currentText()[:4] == '0103':
                    naryad['Твремя'] = ochistka_normi(self, naryad)
                print(f'уменьшилось на {round((bilo - naryad["Твремя"]) * 100 / bilo)}')
            summ += naryad['Твремя']

    vir = round(summ / minut_smen)
    self.debug.append(f'Выработка за {data_nach} {data_kon} - {vir} кг.')
    custom_request_c = f"""SELECT SUM(Вес) as ВЕС FROM mk WHERE Дата_завершения != ""
        and datetime(Дата_завершения) > datetime("{data_nach}") and datetime(Дата_завершения) < datetime("{data_kon}")"""
    rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, conn=conn, rez_dict=True)
    ves = 0
    if rez_mk[0]['ВЕС'] != None:
        ves = round(rez_mk[0]['ВЕС'])
    self.debug.append(f'Вес {ves}')
    summ_ves_tehn = 0

    custom_request_c = f"""SELECT Пномер, Количество, Вес FROM mk WHERE Дата_завершения != ""
        and datetime(Дата_завершения) > datetime("{data_nach}") and datetime(Дата_завершения) < datetime("{data_kon}")"""
    spis_nom_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, conn=conn, hat_c=False)
    for mk in spis_nom_mk:
        # ves_tehn = ves_tehnolohicheskiy(self, mk[0], mk[1], mk[2], conn=conn, conn_mat=conn_mat)
        ves_tehn = 0
        summ_ves_tehn += ves_tehn

    return vir, ves, round(summ_ves_tehn)


@CQT.onerror
def virabotka_sotrudnikov(self, data_nach, data_kon, etap, *args):
    nach_tmp , kon_tmp = F.start_end_dates_c(data_nach, vid='m',format_out="%Y-%m-%d")
    if nach_tmp != F.datetostr(F.strtodate(data_nach),"%Y-%m-%d") or kon_tmp != F.datetostr(F.strtodate(kon_tmp),"%Y-%m-%d"):
        CQT.msgbox(f'В  этом отчете, диапазон дат может быть только первым и последним числом месяца')
        return
    if F.strtodate(data_nach) >= F.strtodate('2024-07-01 00:00:00'):
        CALC_BASE_ONLY_PREM = True
    else:
        CALC_BASE_ONLY_PREM = False
        if 'shift' in CQT.get_key_modifiers(self):
            CALC_BASE_ONLY_PREM = True
    spis_vir_sotr, err, DICT_MASTERS = CMS.calc_productivity_c(data_nach, F.bdcfg('BD_users'), F.bdcfg('Naryad'),
                                                               F.bdcfg('BDact'), self.db_kplan,
                                                               self.DICT_EMPLOEE_FULL_WITH_DEL, self.DICT_PRICE_BRAK,
                                                               CALC_BASE_ONLY_PREM=CALC_BASE_ONLY_PREM,podrazdelenie =etap,organization=self.USER_CONFIG.Organization['Значение'])
    date_month = F.datetostr(F.strtodate(data_nach), "%Y-%m")
    if spis_vir_sotr == '':
        print(err)
        return ''
    rez = [
        ['Месяц', 'ФИО', 'Профес.', 'Выработка включая вычет,%', 'Выработка чистая,%', "Вычет,%", "КТУ%",
         "Закр. труд-т, час. с коэфф.(сложность+выходные)", "Закр. труд-т, час. без коэфф.",'Норма времени(Астр-кая),час.', "Ставка(табель), час.", "Список нарядов", 'Режим работы',
         'Подытог норм(труды в ЕРП), час.','Номер Док ЕРП','Час. ЕРП']
    ]
    spis_vir_sotr = F.sort_by_column_c(spis_vir_sotr, 'Итог') 
    # dict_vir_sotr = F.list_of_lists_to_list_of_dicts(spis_vir_sotr)
    set_nar_for_block = set()
    for item in spis_vir_sotr:
        fio_rc = self.calc_stage(item['ФИО'])
        nom_doc_erp = ''
        hour_from_erp = 0
        if fio_rc == None:
            continue

        vir = 0

        if CALC_BASE_ONLY_PREM:
            if item['сумма_часов_по_табелю'] > 0:
                vir = round((item['Сумма_теор_часов_с_коэфф'] / item['сумма_часов_по_табелю'] * 100))
            kpi = round(item['Итог'], 2)
        else:
            if item['сумма_часов_по_табелю'] > 0:
                vir = round((item['Сумма_теор_часов_с_коэфф'] / item['сумма_часов_по_табелю'] * 100 - 50) * 2) + 100
            kpi = round(item['Итог'] - 100, 2)
        rez.append([date_month,
                    item['ФИО'],
                    item['Должность'],
                    item['Итог'],
                    vir,
                    item['Брак'],
                    kpi,
                    item['Сумма_теор_часов_с_коэфф'],
                    item['Сумма_теор_часов_без_коэфф'],
                    item['Норма времени(Астр)'],
                    item['сумма_часов_по_табелю'],
                    item['Наряды'],
                    item['Режим'],
                    item['Подытог_по_нормам'],
                    nom_doc_erp,
                    hour_from_erp]
                   )

        set_nar_for_block = set_nar_for_block.union(item['Сет_нарядов'])


    rez.append(['' for _ in rez[0]])
    return rez


@CQT.onerror
def get_summ_brak_fio(DICT_PRICE_BRAK, fio, rez_jur_brak):
    # =========braki
    summ_brak = 0
    count_ispr = 0
    count_neispr = 0
    for item in rez_jur_brak:
        if fio in item['usrs']:
            if item['name'] in DICT_PRICE_BRAK:
                count_tmp = copy.copy(item['count_dse'])
                if count_tmp > 158:
                    count_tmp = 158
                count = count_tmp - (
                        0.0001 * count_tmp * (count_tmp * (210 - count_tmp)))
                if item['neisprav'] == 1:
                    type_brak_str = 'Неисправимый'
                    count_neispr += count
                else:
                    type_brak_str = 'Исправимый'
                    count_ispr += count

                summ_brak += DICT_PRICE_BRAK[item['name']][type_brak_str] * count

    # =========
    return {"Испр_число": count_ispr, "Неиспр_число": count_neispr, 'Сумма': summ_brak}


@CQT.onerror
def get_jur_brak(bd_naryad, data_nach, data_kon):
    request_brak = f"""SELECT  brak.s_num , list_brak.group_1 || "$" || list_brak.group_2 || "$" || list_brak.group_3 as name, 
        list_brak.neisprav, list_brak.count_dse, brak.usr_1  || "$" ||  brak.usr_2 as usrs, brak.date FROM brak INNER JOIN 
        list_brak ON list_brak.num_list_brak = brak.s_num WHERE datetime(brak.date) > datetime("{data_nach}") 
                    AND datetime(brak.date) < datetime("{data_kon}") """
    rez_jur_brak = CSQ.custom_request_c(bd_naryad, request_brak, hat_c=True, rez_dict=True)

    # =========
    return rez_jur_brak


@CQT.onerror
def virabotka_sotr(self, data_nach, data_kon, empl, *args, CALC_BASE_ONLY_PREM=True):
    if F.strtodate(data_nach) >= F.strtodate('2024-07-01 00:00:00'):
        CALC_BASE_ONLY_PREM = True
    else:
        CALC_BASE_ONLY_PREM = False
    custom_request_c = f"""SELECT mk.Номер_проекта, mk.Номер_заказа, jurnal.Дата, jurnal.ФИО AS "ФИО_журнал", jurnal.Статус, 
                jurnal.Подытог, jurnal.Номер_наряда, jurnal.Примечание AS "Примеч_журнал", 
                naryad.Твремя, 
                naryad.ФИО, naryad.Фвремя, naryad.ФИО2, 
                naryad.Фвремя2, "Учтен" AS Учет, naryad.Примечание AS "Примеч_наряд", 
                "" AS "Подытог Норм", naryad.Внеплан, naryad.Коэфф_сложности, "" AS "Коэфф_вых", "" AS "Коэфф_вых_ставка", naryad.Подтвержд_вып FROM jurnal 
                INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
                INNER JOIN mk ON naryad.Номер_мк == mk.Пномер 
                WHERE jurnal.ФИО == "{empl}" AND datetime(jurnal.Дата) >= datetime("{data_nach}") 
                and datetime(jurnal.Дата) <= datetime("{data_kon}") AND 
                jurnal.Номер_наряда in (SELECT jurnal.Номер_наряда FROM jurnal WHERE jurnal.ФИО == "{empl}" AND datetime(jurnal.Дата) >= datetime("{data_nach}") 
                and datetime(jurnal.Дата) <= datetime("{data_kon}") AND jurnal.Статус == "Завершен")"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)

    custom_request_c = f"""
SELECT mk.Номер_проекта, mk.Номер_заказа, jurnal.Дата, jurnal.ФИО AS "ФИО_журнал", jurnal.Статус, 
                jurnal.Подытог, jurnal.Номер_наряда, jurnal.Примечание AS "Примеч_журнал", 
                naryad.Твремя, 
                naryad.ФИО, naryad.Фвремя, naryad.ФИО2, 
                naryad.Фвремя2, "Не учтен" AS Учет, naryad.Примечание AS "Примеч_наряд", 
                jurnal.Подытог_нормы AS "Подытог Норм", naryad.Внеплан, naryad.Коэфф_сложности, "" AS "Коэфф_вых", "" AS "Коэфф_вых_ставка",
                 naryad.Подтвержд_вып FROM jurnal 
INNER JOIN naryad ON naryad.Пномер = jurnal.Номер_наряда 
INNER JOIN mk ON naryad.Номер_мк == mk.Пномер  
WHERE jurnal.Номер_наряда not in (SELECT jurnal.Номер_наряда  FROM jurnal WHERE 
jurnal.Статус = "Завершен" AND jurnal.ФИО = "{empl}") AND 
 datetime(jurnal.Дата) <= datetime("{data_kon}") AND 
datetime(jurnal.Дата) >= datetime("{data_nach}") AND jurnal.ФИО == "{empl}"
"""
    rez_jur_nezav = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
    if rez_jur == [] or rez_jur == False:
        CQT.msgbox('Внимание! завершенных нарядов у него нет, одни недоделки',icon_str='Warning')
        

    for item in rez_jur_nezav:
        rez_jur.append(item)

    rez_jur = F.sort_by_column_c(rez_jur, 'Дата', date_time=True)

    dict_user_brak = get_summ_brak_fio(self.DICT_PRICE_BRAK, empl,
                                       get_jur_brak(self.bd_naryad, data_nach, data_kon))

    table_name = F.start_end_dates_c(data_nach, vid='m')[0].split()[0].replace('-', '_')
    custom_request_c = F'''SELECT * FROM mtdz_{table_name}'''
    if custom_request_c == False:
        CQT.msgbox(f'Не найдена таблица {table_name}')
        return
    tabel = CSQ.custom_request_c(F.bdcfg('BD_users'), custom_request_c)
    if tabel == '':
        print('Не найден табель')
        raise ('Err')

    set_nar = set()
    summ_tvr = 0
    summ_tvr_koef = 0
    summ_tvr_max = 0
    summ_fvr = 0
    summ_poditog = 0
    for i, item in enumerate(rez_jur):
        if rez_jur[i]['ФИО2'] ==empl:
            rez_jur[i]['ФИО'] = rez_jur[i]['ФИО2']
            rez_jur[i]['Фвремя'] = rez_jur[i]['Фвремя2']
        if rez_jur[i]['Номер_наряда'] in set_nar:
            rez_jur[i]['Твремя'] = 0
            rez_jur[i]['Фвремя'] = 0
            # rez_jur[i]['Номер_наряда'] = ''
        else:
            if rez_jur[i]['Твремя'] == '':
                CQT.msgbox(f"Наряд {rez_jur[i]['Номер_наряда']} не отнормирован./ ПРОСТОЙ по заврешении нормируется.")
                rez_jur[i]['Твремя'] = 0
            set_nar.add(rez_jur[i]['Номер_наряда'])
            if F.strtodate(data_nach) >= F.strtodate('2024-08-01 00:00:00'):
                rez_jur[i]['Коэфф_вых'] = 1
                rez_jur[i]['Коэфф_вых_ставка'] = "С 08.2024 учет в ЕРП"
            else:
                rez_jur[i]['Коэфф_вых'] = koeff_double_pay_holydays(rez_jur, rez_jur[i]['Номер_наряда'], tabel)
                if rez_jur[i]['Коэфф_вых'] > 1:
                    rez_jur[i]['Коэфф_вых_ставка'] = "1.5"
                else:
                    rez_jur[i]['Коэфф_вых_ставка'] = "1"
            if rez_jur[i]['Внеплан'] != 1 and rez_jur[i]['Подтвержд_вып'] == 1 and rez_jur[i]['Учет'] == 'Учтен':
                summ_tvr += rez_jur[i]['Твремя']
                summ_tvr_koef += rez_jur[i]['Твремя'] * rez_jur[i]['Коэфф_сложности'] * rez_jur[i]['Коэфф_вых']
                print(
                    f"{rez_jur[i]['Твремя']} == {rez_jur[i]['Твремя'] * rez_jur[i]['Коэфф_сложности'] * rez_jur[i]['Коэфф_вых']}")
            else:
                print(
                    f"не учтён {rez_jur[i]['Твремя']} == {rez_jur[i]['Твремя'] * rez_jur[i]['Коэфф_сложности'] * rez_jur[i]['Коэфф_вых']}")
            summ_tvr_max += rez_jur[i]['Твремя'] * rez_jur[i]['Коэфф_сложности'] * rez_jur[i]['Коэфф_вых']
            summ_fvr += F.valm(rez_jur[i]['Фвремя'])
        summ_poditog += F.valm(rez_jur[i]["Подытог Норм"])

    rez_jur.append({_: '' for _ in rez_jur[0].keys()})

    name_table = F.datetostr(F.strtodate(data_kon), 'mtdz_%Y_%m_01')
    custom_request_c = f'''SELECT * FROM {name_table} '''
    data_tabel = CSQ.custom_request_c(self.bd_users, custom_request_c,rez_dict=True)

    miutes = CMS.time_by_repo_card(empl, data_tabel)
    rez_jur[-1]['Номер_проекта'] = f'ПОДЫТОГ:'
    if miutes == 0:
        eff = 0
        prem = 0
        prem_max = 0
    else:
        eff = round(summ_fvr / miutes * 100)
        if CALC_BASE_ONLY_PREM:
            prem = round((summ_tvr_koef) / miutes * 100,2)
            prem_max = round((summ_tvr_max) / miutes * 100,2)
        else:
            prem = round((summ_tvr_koef) / miutes * 200,2) - 100
            prem_max = round((summ_tvr_max) / miutes * 200,2) - 100
    rez_jur[-1]['Дата'] = f'Эффективность {eff}%'
    rez_jur[-1]['Примеч_журнал'] = f'По табелю {round(miutes / 60, 2)} час.'
    brak = round(dict_user_brak['Сумма'], 2)
    prem -= brak
    if prem < 0:
        prem = 0

    rez_jur[-1]['Примеч_наряд'] = f'Премия {prem}% (без учета брака)'
    rez_jur[-1]['Подтвержд_вып'] = f'Премия max {prem_max - brak}% (брак+внеплан+подтвержд+неучтен)'
    rez_jur[-1]['Твремя'] = f'{round((summ_tvr) / 60, 2)} час.'
    rez_jur[-1]["Подытог Норм"] = f'{round((summ_poditog) / 60, 2)} час.'
    rez_jur[-1]['Коэфф_сложности'] = f'Вычет БРАК {brak}%'
    rez_jur[-1]['Коэфф_вых'] = f'Общ. итог {round((summ_tvr_koef) / 60, 2)} час.'
    rez_jur[-1]['Коэфф_вых_ставка'] = f'Премия {prem - brak}% (включая брак)'
    rez_jur.append({_: '' for _ in rez_jur[0].keys()})
    rez_jur = F.list_of_dicts_to_list_of_lists(rez_jur)
    rez_jur = F.delete_column(rez_jur, ['ФИО_журнал', 'ФИО', 'ФИО2', 'Фвремя2'])
    return rez_jur


@CQT.onerror
def virabotka_ceha_ponaryadno(self, data_nach, data_kon, etap, *args):
    # в ДБ с рейтин юсерз вписать рц чей работник, провести цикл на сравнение фамилий завершено с цехомю.
    custom_request_c = f"""SELECT jurnal.Дата, jurnal.ФИО, jurnal.Статус, jurnal.Номер_наряда, 
            naryad.Твремя, naryad.ДСЕ_ID, naryad.Операции, naryad.Номер_мк, naryad.Внеплан, naryad.ФИО, naryad.ФИО2,  
            naryad.Фвремя, naryad.Фвремя2, naryad.Примечание, naryad.Категория_внепл,
            naryad.Опер_время, mk.Вид, mk.Вес, mk.Направление, mk.Номер_проекта, mk.Номер_заказа FROM jurnal 
            INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер
            INNER JOIN mk ON mk.Пномер = naryad.Номер_мк
            WHERE jurnal.Статус == "Завершен"
        and datetime(jurnal.Дата) > datetime("{data_nach}") and datetime(jurnal.Дата) < datetime("{data_kon}") 
    AND naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
    if rez_jur == []:
        CQT.msgbox('Пусто')
        return
    set_oper = set()
    for naryad in rez_jur:
        name_oper = naryad['Операции'].split('|')
        for oper in name_oper:
            set_oper.add(oper.split('$')[1])
    list_oper = sorted(list(set_oper))

    ponaryadno = [
        ['Проект', 'Вeс_мк', 'Номер_наряда', 'Твремя_мин', f'кг_наряд({PROIZVODITELNOST_POST_SM} пр-ть)', 'Фвремя_мин',
         "Примечание", "Категория_внепл", "Вид", 'Направление']]
    for oper in list_oper:
        ponaryadno[0].append(oper)
    set_weight_MK_c = set()
    for naryad in rez_jur:
        fio_rc = self.calc_stage(naryad['ФИО'])
        if fio_rc == None:
            continue
        if fio_rc[:4] == self.ui.cmb_podrazdelenie.currentText()[:4]:
            vrem_fact = naryad['Твремя']
            if naryad['ФИО'] == naryad['9_ФИО']:
                vrem_fact = naryad['Фвремя']
            if naryad['ФИО'] == naryad['ФИО2']:
                vrem_fact = naryad['Фвремя2']
            count_executors = 1
            if naryad['9_ФИО'] != '' and naryad['ФИО2'] != '':
                count_executors = 2
            ves = naryad['Вес']
            nppy = naryad['Номер_проекта'] + "$" + naryad['Номер_заказа']
            if nppy in set_weight_MK_c:
                ves = 0
            set_weight_MK_c.add(nppy)
            # custom_request_c = f"""SELECT Дата_завершения,Вес,Направление,Номер_проекта,Номер_заказа FROM mk WHERE Пномер == {naryad['Номер_мк']}"""
            # rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True, one=True)
            tmp = [nppy, ves, naryad['Номер_наряда'],
                   naryad['Твремя'], round(PROIZVODITELNOST_POST_SM * naryad['Твремя'] / minut_smen),
                   F.valm(vrem_fact), naryad['Примечание'], naryad['Категория_внепл'], naryad['Вид'],
                   naryad['Направление']]
            for oper in list_oper:
                tmp.append('')

            list_name_oper = naryad['Операции'].split('|')
            list_time_oper = naryad['Опер_время'].split('|')
            if len(list_name_oper) != len(list_time_oper):
                print(f'{nppy} {naryad["Номер_наряда"]} не сходятся операции и время опреаций')
            else:
                for i in range(len(list_name_oper)):
                    name_oper = list_name_oper[i].split('$')[1]
                    time_oper = list_time_oper[i]
                    nk_oper = F.num_col_by_name_in_hat_c(ponaryadno, name_oper)
                    if tmp[nk_oper] == '':
                        tmp[nk_oper] = 0
                    tmp[nk_oper] = round(tmp[nk_oper] + F.valm(time_oper) / count_executors, 2)

            ponaryadno.append(tmp)
    ponaryadno.append(['' for _ in ponaryadno[0]])
    ponaryadno.append(['' for _ in ponaryadno[0]])
    return ponaryadno


def plan_fact_grafic_mes(self, data_nach, data_kon, *args):
    if F.strtodate(data_nach) < F.strtodate('01.01.2024', "%d.%m.%Y"):
        CQT.msgbox(f'Дата начала слишком ранняя')
        return

    self.DICT_NN_NTK = CMS.load_dict_dse(self.db_dse)
    self.list_month_plan = list_month_plan = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM mnts_plan WHERE 
            datetime(Дата) >= datetime("{data_nach}") 
            and datetime(Дата) < datetime("{data_kon}") and poki = {USRCNF.Config.place.poki}""", rez_dict=True)
    get_list_month_fact(self)


    self.dict_dorezok = F.deploy_dict_c(CSQ.custom_request_c(self.bd_naryad, f"""SELECT дорезки_мк.Номер_мк,  тип_дорезок.Имя 
         FROM дорезки_мк INNER JOIN тип_дорезок ON тип_дорезок.Пномер == дорезки_мк.Причина""", rez_dict=True),
                                   "Номер_мк")

    table_vnepan = F.list_of_lists_to_dict_of_dicts(
        vneplan_po_napravl(self, data_nach, data_kon, 'Все', generate_graf=False,), 'Месяц')

    
    plan_tab_time_req = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan,f"""SELECT month, sum(normo_smen)  FROM plan_tabel_workforce 
     WHERE depatment == "сборочный цех производства" and poki == {USRCNF.Config.place.poki} GROUP BY month ;""",rez_dict=True),'month')
        

    dict_cat_vnepl = dict()
    list_kat_vnepl = CSQ.custom_request_c(self.bd_naryad, f"""SELECT value FROM kategor_vnepl WHERE kod > 0""",
                                          one_column=True,
                                          hat_c=False)
    rez = [['Месяц', 'Факт, уд.т.','По xml,т.', 'План(ПДО), н-см.', 'Освоено (МК Тип = Плановая), н-см.', 'Внеплан, %',
            'Освоено(план+внеплан работы), н-см.','Плановое табельное время, н-см.','Сумм. осв. время по журналу, н-см.(Подытог норм)']]
    for item in list_month_plan:
        summ_ves = 0
        data = item['Дата']
        month = F.datetostr(F.strtodate(data), "%Y-%m-%d")
        ves_pl = 0
        fact_tab_time = 0
        plan_tab_time = 0
        ves_xml_met = 0
        spis_vir_sotr, err, DICT_MASTERS = CMS.calc_productivity_c(data, F.bdcfg('BD_users'), F.bdcfg('Naryad'),
                                                                   F.bdcfg('BDact'), self.db_kplan,
                                                                   self.DICT_EMPLOEE_FULL_WITH_DEL,
                                                                   self.DICT_PRICE_BRAK,
                                                                   
                                                                   podrazdelenie='Сборочный цех Производства',
                                                                   organization=self.USER_CONFIG.Organization[
                                                                       'Значение'],additional_fix=False)

        fact_tab_time = round(sum([_['Подытог_по_нормам'] for _ in spis_vir_sotr])/8,2)
        #CQT.msgboxg_get_table(self,'',spis_vir_sotr)

        if plan_tab_time_req != None and len(plan_tab_time_req):
            if month in plan_tab_time_req:
                plan_tab_time = round(plan_tab_time_req[month], 2)
            
            
        for vid_tmp in self.DICT_NAPRAVL.keys():
            if vid_tmp in item:
                ves_pl += item[vid_tmp]
        for mk in self.list_month_fact:
           
            dat_str = mk['Дата_завершения']
            dat_f = F.start_end_dates_c(F.strtodate(dat_str, "%Y-%m-%d %H:%M:%S"), '', vid='m', format_out="%Y-%m-%d")[
                0]
            if dat_f == data:
                summ_ves += mk['Вес'] * KOEF_RASKLADKI
                if F.valm(mk['xml']) == 0:
                    if F.valm(mk['Вес_по_рес']) == 0:
                        ves_xml_met += F.valm(mk['Вес'])
                    else:
                        ves_xml_met += F.valm(mk['Вес_по_рес'])
                else:
                    ves_xml_met += F.valm(mk['xml'])
        nach_data, kon_data = F.start_end_dates_c(F.strtodate(data, "%Y-%m-%d"), '', vid='m',
                                                  format_out="%Y-%m-%d %H:%M:%S")

        dxict_moth = table_vnepan[data]
        # rez = [['Месяц', 'План, т.', 'Факт, т.', 'План(ПДО), н-нед.', 'Освоено плановых, н-нед.', 'Внеплан, %','Освоено(план+внеплан работы), н-нед.']]
        summ_vrem_osvoeno = dxict_moth['План, н-см./чел.']
        summ_vrem_osv_vneplan = dxict_moth['Внеплан сумма, н-см./чел.']
        summ_ves_fact = summ_vrem_osvoeno + summ_vrem_osv_vneplan
        k = 0
        try:
            summ_ves_vir_vneplan_proc = round(100 * summ_vrem_osv_vneplan / summ_ves_fact, 2)
        except ZeroDivisionError as e: #27.11.2025
            summ_ves_vir_vneplan_proc = 'Проигнорировано т.к. "План, н-см./чел." и "Внеплан сумма, н-см./чел." равны нулю'
        if summ_vrem_osvoeno > 0:
            k = summ_ves_fact / summ_vrem_osvoeno
        plan_normo_sm = round((item['Нормо_смены_сб'] + item['Нормо_смены_св'] + item['Нормо_смены_зачист']), 2)
        # rez = [['Месяц',    'План, т.',              'Отгрузка, т.', '           Факт, н-нед.'
        tmp = [data, round(summ_ves / 1000, 2),round(ves_xml_met / 1000, 2), plan_normo_sm, round(summ_vrem_osvoeno * KOEF_VNEPLANA, 2),
               summ_ves_vir_vneplan_proc, round(summ_ves_fact * KOEF_VNEPLANA, 2), plan_tab_time, fact_tab_time]
        # ,  'Внеплан, н-нед.',                      'Сумм. Факт, н-нед.']]
        rez.append(tmp)

    rez = F.sort_by_column_c(rez,'Месяц',False,True,date_format="%Y-%m-%d")

    load_browser(self)
    create_gant(self, rez)

    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez


def calc_tehpodgotovka_per_month(bd_naryad, bd_users, db_resxml, db_dse, data_nach, data_kon, tip, *args):
    query = f"""SELECT * FROM jurnal_td WHERE Статус == 'Создание'"""
    DICT_DSE = F.deploy_dict_c(CSQ.custom_request_c(db_dse, query, rez_dict=True), 'ДСЕ')
    query = f"""SELECT mk.Пномер, mk.Дата, mk.Направление, mk.Вес, mk.Количество FROM mk 
        WHERE  date(strftime('%Y-%m-%d','20'||Дата)) > date("{data_nach}") 
                        and date(strftime('%Y-%m-%d','20'||Дата)) < date("{data_kon}")"""
    dict_rez_napr = dict()
    dict_rez_users = dict()
    responce = CSQ.custom_request_c(bd_naryad, query, rez_dict=True)
    tmp_dict_napr = {_['Направление']:
                         {'операций': 0, 'переходов': 0, 'материалов': 0, 'документов': 0, 'инструмента': 0,
                          'оснастки': 0, 'дсе': 0} for _ in responce}

    dict_zamech = CSQ.custom_request_c(bd_naryad,
                                       f"""SELECT МК, Код from zamech WHERE Код in (4,5,6,8) AND Виновное_подразделение = '030000' and Код_вп in (1,3,4)""",
                                       rez_dict=True)
    DICT_VES_ZAMECH = {4: 20, 5: 20, 6: 20, 8: 20}  # 100 проц

    dict_date_vih = CMS.DICT_CLD_KPLAN(None)

    for item in responce:
        date_month = F.datetostr(F.strtodate(item['Дата'], "%y-%m-%d"), "%Y-%m")

        if 'за год' in tip:
            month = F.datetostr(F.strtodate(item['Дата'], "%y-%m-%d"), "%Y")
            mask = "%Y"
        else:
            month = date_month
            mask = "%Y-%m"

        if month not in dict_rez_napr:
            rab_dney = 0
            for day in dict_date_vih.keys():
                day_dat = F.datetostr(F.strtodate(day, 'd_%Y_%m_%d'), mask)
                if day_dat == date_month:
                    if not dict_date_vih[day].is_holyday:
                        rab_dney += 1

            dict_rez_napr[month] = {'rab_dn': rab_dney, 'napr': copy.deepcopy(tmp_dict_napr)}
            dict_rez_users[month] = {'rab_dn': rab_dney, 'users': dict()}
    dict_count_dse_per_napr = {'КЛ': {'дсе': 0, 'мк': 0, 'вес_ед': 0}, 'КТ': {'дсе': 0, 'мк': 0, 'вес_ед': 0},
                               'ШГ': {'дсе': 0, 'мк': 0, 'вес_ед': 0}, 'ПР': {'дсе': 0, 'мк': 0, 'вес_ед': 0}}
    for item in responce:
        date_mk = F.strtodate(item['Дата'], "%y-%m-%d")
        month = F.datetostr(date_mk, "%Y-%m")
        if 'за год' in tip:
            month = F.datetostr(date_mk, "%Y")
        nom_mk = int(item['Пномер'])
        count_zamech = 0
        for item_zamech in dict_zamech:
            if item_zamech['МК'] == nom_mk:
                count_zamech += DICT_VES_ZAMECH[item_zamech['Код']]
        if count_zamech > 80:
            count_zamech = 80
        koef_vichet_zam = 1 - count_zamech / 100
        # print(f'МК {nom_mk} вычет на ТК {count_zamech}%')
        napr = item['Направление']
        dict_count_dse_per_napr[napr]['мк'] += 1
        # ves_ed = item['Вес']/item['Количество']
        dict_count_dse_per_napr[napr]['вес_ед'] += item['Вес']
        custom_request_c = f"""SELECT data FROM res WHERE Номер_мк == {nom_mk}"""
        rez = CSQ.custom_request_c(db_resxml, custom_request_c)
        if rez == None or rez == False:
            # print(f'ресурсная для {nom_mk} не найдена')
            continue
        res = F.from_binary_pickle(rez[-1][0])
        if res == None:
            # print(f'ресурсная для {nom_mk} не распознана')
            continue
        dict_users_from_mk = dict()
        dse_count = 0

        for dse in res:
            dict_count_dse_per_napr[napr]['дсе'] += 1
            oper_count = 0
            pereh_count = 0
            mat_count = 0
            docum_count = 0
            instr_count = 0
            osnast_count = 0
            name = dse['Номенклатурный_номер']
            if name not in DICT_DSE:
                # print(f"{name} не считается не найдена в журнале")
                continue
            koef_30d = 1
            if F.strtodate(DICT_DSE[name]['Дата']) < F.date_add_days(date_mk, -30, format_out=''):
                # print(f"{name} koef = 0,05 сделана {F.strtodate(DICT_DSE[name]['Дата'])} ранее чем мк {F.date_add_days(date_mk,-30, format_out='')}")
                koef_30d = 0.05

            date_day = F.datetostr(F.strtodate(DICT_DSE[name]['Дата']), 'd_%Y_%m_%d')
            if date_day not in dict_date_vih:
                # print(f'{date_day} не найден в табеле')
                raise 'err'
            if 'будни' in tip:
                if dict_date_vih[date_day]:
                    # print(f" {name} не считается сделана {DICT_DSE[name]['Дата']} в выходной")
                    continue
            if 'выходные' in tip:
                if not dict_date_vih[date_day]:
                    # print(f" {name} не считается сделана {DICT_DSE[name]['Дата']} в будни")
                    continue

            name_user = DICT_DSE[name]['ФИО']
            for oper in dse['Операции']:
                oper_count += 1 * koef_30d * koef_vichet_zam
                pereh_count += len(oper['Переходы']) * koef_30d * koef_vichet_zam
                mat_count += len(oper['Материалы']) * koef_30d * koef_vichet_zam
                docum_count += len(oper['Опер_документы']) * koef_30d * koef_vichet_zam
                instr_count += len(oper['Опер_инстумент']) * koef_30d * koef_vichet_zam
                osnast_count += len(oper['Опер_оснастка']) * koef_30d * koef_vichet_zam
            if name_user not in dict_users_from_mk:
                dict_users_from_mk[name_user] = {'операций': 0, 'переходов': 0, 'материалов': 0, 'документов': 0,
                                                 'инструмента': 0, 'оснастки': 0, 'дсе': 0, 'days': dict()}
            dict_users_from_mk[name_user]['операций'] += oper_count
            dict_users_from_mk[name_user]['переходов'] += pereh_count
            dict_users_from_mk[name_user]['материалов'] += mat_count
            dict_users_from_mk[name_user]['документов'] += docum_count
            dict_users_from_mk[name_user]['инструмента'] += instr_count
            dict_users_from_mk[name_user]['оснастки'] += osnast_count
            dict_users_from_mk[name_user]['дсе'] += 1
            if date_day not in dict_users_from_mk[name_user]['days']:
                dict_users_from_mk[name_user]['days'][date_day] = 0
            dict_users_from_mk[name_user]['days'][date_day] += 1

            dict_rez_napr[month]['napr'][napr]['операций'] += oper_count
            dict_rez_napr[month]['napr'][napr]['переходов'] += pereh_count
            dict_rez_napr[month]['napr'][napr]['материалов'] += mat_count
            dict_rez_napr[month]['napr'][napr]['документов'] += docum_count
            dict_rez_napr[month]['napr'][napr]['инструмента'] += instr_count
            dict_rez_napr[month]['napr'][napr]['оснастки'] += osnast_count
            dict_rez_napr[month]['napr'][napr]['дсе'] += 1

        for user in dict_users_from_mk:
            if user not in dict_rez_users[month]['users']:
                dict_rez_users[month]['users'][user] = {'операций': 0, 'переходов': 0, 'материалов': 0, 'документов': 0,
                                                        'инструмента': 0, 'оснастки': 0, 'дсе': 0, 'дсе_в_день': dict()}
            dict_rez_users[month]['users'][user]['операций'] += dict_users_from_mk[user]['операций']
            dict_rez_users[month]['users'][user]['переходов'] += dict_users_from_mk[user]['переходов']
            dict_rez_users[month]['users'][user]['материалов'] += dict_users_from_mk[user]['материалов']
            dict_rez_users[month]['users'][user]['документов'] += dict_users_from_mk[user]['документов']
            dict_rez_users[month]['users'][user]['инструмента'] += dict_users_from_mk[user]['инструмента']
            dict_rez_users[month]['users'][user]['оснастки'] += dict_users_from_mk[user]['оснастки']
            dict_rez_users[month]['users'][user]['дсе'] += dict_users_from_mk[user]['дсе']
            for day in dict_users_from_mk[name_user]['days']:
                if day not in dict_rez_users[month]['users'][user]['дсе_в_день']:
                    dict_rez_users[month]['users'][user]['дсе_в_день'][day] = 0
                dict_rez_users[month]['users'][user]['дсе_в_день'][day] += dict_users_from_mk[name_user]['days'][day]

    for month in dict_rez_users:
        for user in dict_rez_users[month]['users']:
            dse_per_day = 0
            for day in dict_rez_users[month]['users'][user]['дсе_в_день']:
                dse_per_day += dict_rez_users[month]['users'][user]['дсе_в_день'][day]
            dse_per_day = round(dse_per_day / len(dict_rez_users[month]['users'][user]['дсе_в_день']), 1)
            dict_rez_users[month]['users'][user]['дсе_в_день'] = dse_per_day
    for napr in dict_count_dse_per_napr:
        if dict_count_dse_per_napr[napr]['мк'] == 0:
            dict_count_dse_per_napr[napr]['aver'] = 0
            dict_count_dse_per_napr[napr]['вес_ед'] = 0
        else:
            dict_count_dse_per_napr[napr]['aver'] = round(
                dict_count_dse_per_napr[napr]['дсе'] / dict_count_dse_per_napr[napr]['мк'], 2)
            dict_count_dse_per_napr[napr]['вес_ед'] = round(
                dict_count_dse_per_napr[napr]['вес_ед'] / dict_count_dse_per_napr[napr]['мк'], 2)
    return dict_rez_users, dict_rez_napr


def virabotka_top(self: mywindow, data_nach, data_kon, tip, *args):
    dict_users, dict_napr = calc_tehpodgotovka_per_month(self.bd_naryad, self.bd_users, self.db_resxml, self.db_dse,
                                                         data_nach, data_kon, tip, *args)
    if 'По направлениям' in tip:
        table_rez = [['Месяц', 'Направление']]
        set_keys = set()
        for month in dict_napr:
            for napr in dict_napr[month]['napr']:
                for key in dict_napr[month]['napr'][napr]:
                    set_keys.add(key)
        for key in sorted(list(set_keys)):
            table_rez[0].append(key)
        for month in dict_napr:
            for napr in dict_napr[month]['napr']:
                tmp_list = [month, napr]
                for field in table_rez[0][2:]:
                    if field in dict_napr[month]['napr'][napr]:
                        tmp_list.append(round(dict_napr[month]['napr'][napr][field], 2))
                    else:
                        tmp_list.append(0)
                table_rez.append(tmp_list)
    if 'По сотрудникам' in tip:
        table_rez = [['Месяц', 'Сотрудник']]
        set_keys = set()
        for month in dict_users:
            for user in dict_users[month]['users']:
                for key in dict_users[month]['users'][user]:
                    set_keys.add(key)
        for key in sorted(list(set_keys)):
            table_rez[0].append(key)
        for month in dict_users:
            for user in dict_users[month]['users']:
                tmp_list = [month, user]
                for field in table_rez[0][2:]:
                    if field in dict_users[month]['users'][user]:
                        tmp_list.append(round(dict_users[month]['users'][user][field], 2))
                    else:
                        tmp_list.append(0)
                table_rez.append(tmp_list)
    table_rez.append(['' for _ in table_rez[0]])
    table_rez.append(['' for _ in table_rez[0]])
    return table_rez


def divergence_of_date_proj(self: mywindow, data_nach, data_kon, *args):
    def check_date_zp(item, tmp_dict):
        if F.is_date(item['Дата_ЗП'], "%Y-%m-%d"):
            tmp_dict['Дата_ЗП'] = item['Дата_ЗП']
            return True
        if F.is_date(item['Дата_ЗП_2'], "%Y-%m-%d"):
            tmp_dict['Дата_ЗП'] = item['Дата_ЗП_2']
            return True
        return False

    def check_date_kd(item, tmp_dict):
        if F.is_date(item['Дата_КД'], "%Y-%m-%d"):
            tmp_dict['Дата_КД'] = item['Дата_КД']
            return True
        if F.is_date(item['Дата_КД_2'], "%Y-%m-%d"):
            tmp_dict['Дата_КД'] = item['Дата_КД_2']
            return True
        return False

    def check_date_td(item, tmp_dict):
        if F.is_date(item['Дата_ТД'], "%Y-%m-%d"):
            tmp_dict['Дата_ТД'] = item['Дата_ТД']
            return True
        if F.is_date(item['Дата_ТД'], "%Y-%m-%d"):
            tmp_dict['Дата_ТД'] = item['Дата_ТД_2']
            return True
        if F.is_date(item['Дата_ТД_3'], "%Y-%m-%d"):
            tmp_dict['Дата_ТД'] = item['Дата_ТД_3']
            return True
        return False

    def check_date_otgr(item, tmp_dict):
        if F.is_date(item['Дата_отгрузки'], "%Y-%m-%d"):
            tmp_dict['Дата_отгрузки'] = item['Дата_отгрузки']
            return True
        return False

    def check_norm(item, tmp_dict):
        summ = 0
        summ += F.valm(item['Нчас_заг'])
        summ += F.valm(item['Нчас_мехобр'])
        summ += F.valm(item['Нчас_покр'])

        summ += F.valm(item['Нчас_контр'])
        summ += F.valm(item['Нчас_упаковки'])
        summ += F.valm(item['Нчас_вспом'])
        summ += (1 + F.valm(item['Нчас_сб']) * 0.27) / 2  # простои
        summ += F.valm(item['Нчас_сб']) / 2
        summ = round(summ / 8, 1)

        tmp_dict['Смен'] = summ

        tmp_dict['Направление'] = item['Имя']
        tmp_dict['№ERP'] = item['№ERP'] + "_"
        tmp_dict['№проекта'] = item['№проекта'] + "_"
        tmp_dict['Пномер'] = str(item['Пномер']) + "_"
        tmp_dict['Уд.кг.'] = round(F.valm(item['Нчас_сб']) / 16 * PROIZVODITELNOST_POST_SM, 1)
        if summ == 0:
            return False
        return True

    query = f"""SELECT plan.Пномер, пл_оуп.№проекта , пл_оуп.№ERP, napravl_deyat.Имя, 
    пл_заг.Нчас_заг  , 
пл_мех.Нчас_мехобр , 
пл_покр.Нчас_покр, 
пл_сб.Нчас_сб , 
пл_отк.Нчас_контр , 
пл_компл.Нчас_упаковки, 
plan.Нчас_вспом, 
    plan.Фдата_получения_КД as Дата_КД, пл_ко.Фдата_зав_КДрев2 as Дата_КД_2, 
    
     пл_топ.Фдата_зав_спецЕРП as Дата_ТД ,пл_топ.Дата_МК as Дата_ТД_2 ,пл_топ.Фдата_зав_ТД  as Дата_ТД_3,
      
      пл_оуп.Дата_заявки_на_произв as Дата_ЗП, plan.Дата_внесения as Дата_ЗП_2,
      
       пл_оуп.Дата_отгрузки_ПУ  as Дата_отгрузки 
       
       FROM plan INNER JOIN 
       пл_ко ON пл_ко.НомПл = plan.Пномер,
        пл_топ ON пл_топ.НомПл = plan.Пномер,
        пл_оуп ON пл_оуп.НомПл = plan.Пномер,
        napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
        пл_заг  ON пл_заг.НомПл = plan.Пномер,  
        пл_мех  ON пл_мех.НомПл = plan.Пномер,  
        пл_покр ON пл_покр.НомПл = plan.Пномер,  
        пл_сб   ON пл_сб.НомПл = plan.Пномер,  
        пл_отк  ON пл_отк.НомПл = plan.Пномер, 
        пл_компл ON пл_компл.НомПл = plan.Пномер
        WHERE plan.Статус IN (2,3,4,7)
"""
    responce = CSQ.custom_request_c(self.db_kplan, query, rez_dict=True)
    all_poz_dict = dict()
    for item in responce:
        tmp_dict = dict()
        if not check_date_zp(item, tmp_dict):
            continue
        if not check_date_kd(item, tmp_dict):
            continue
        if not check_date_td(item, tmp_dict):
            continue
        if not check_date_otgr(item, tmp_dict):
            continue
        if not check_norm(item, tmp_dict):
            continue
        tmp_dict['Время_на_проект_факт_дн'] = (
                    F.strtodate(tmp_dict['Дата_отгрузки']) - F.strtodate(tmp_dict['Дата_ЗП'])).days
        tmp_dict['Время_на_КД_факт_дн'] = (F.strtodate(tmp_dict['Дата_КД']) - F.strtodate(tmp_dict['Дата_ЗП'])).days
        tmp_dict['Время_на_ТД_факт_дн'] = (F.strtodate(tmp_dict['Дата_ТД']) - F.strtodate(tmp_dict['Дата_КД'])).days

        zak_days = 1
        if tmp_dict['Направление'] in self.Data.NAPRAVL_DEYAT:
            if self.Data.NAPRAVL_DEYAT[tmp_dict['Направление']]['Направление'] == 3:
                zak_days = 14
            if self.Data.NAPRAVL_DEYAT[tmp_dict['Направление']]['Направление'] == 1:
                zak_days = 14
            if self.Data.NAPRAVL_DEYAT[tmp_dict['Направление']]['Направление'] == 2:
                zak_days = 2
            tmp_dict['Время_на_материал_факт_дн'] = zak_days

        tmp_dict['Время_на_изгот_остаток'] = (F.strtodate(tmp_dict['Дата_отгрузки']) - F.strtodate(
            tmp_dict['Дата_ТД'])).days - zak_days
        tmp_dict['Дефицит_смен'] = round(tmp_dict['Смен'] - tmp_dict['Время_на_изгот_остаток'])
        tmp_dict['Уд. Дефицит_смен'] = round(tmp_dict['Уд.кг.'] / 1000 * tmp_dict['Дефицит_смен'], 1)
        if tmp_dict['Направление'] not in all_poz_dict:
            all_poz_dict[tmp_dict['Направление']] = [tmp_dict]
        all_poz_dict[tmp_dict['Направление']].append(tmp_dict)
        for key in tmp_dict:
            if F.is_numeric(tmp_dict[key]):
                all_poz_dict[tmp_dict['Направление']][0][key] += tmp_dict[key]
    rez = []
    list_to_del = ["Дата_ЗП",
                   "Дата_КД",
                   "Дата_ТД",
                   "Дата_отгрузки",
                   "№ERP",
                   "№проекта",
                   "Пномер"]
    for key in all_poz_dict:
        for key2 in all_poz_dict[key][0].keys():
            if F.is_numeric(all_poz_dict[key][0][key2]):
                all_poz_dict[key][0][key2] = round(all_poz_dict[key][0][key2] / len(all_poz_dict[key]) - 1, 1)
        rez.append(all_poz_dict[key][0])
        for item in list_to_del:
            rez[-1].pop(item)

    #rez.append(['' for _ in rez[0]])
    #rez.append(['' for _ in rez[0]])
    return rez


def udel_trud_sort_c(self: mywindow, data_nach, data_kon, *args):
    shablon_etaps = dict()
    rez = [
        ['Код из бд', 'Выборка,шт.', "Направление", 'Наименование (мин/кг)', 'кг/чел/см_факт', 'кг/чел/см_норм',
         'кг/чел/см_средн', 'кг/чел/см_кпл']]
    for oper in self.DICT_OPER_FULL.keys():
        etap = self.DICT_OPER_FULL[oper]['etap']
        if etap is not  None:
            shablon_etaps[etap] = 0
    for etap in shablon_etaps:
        rez[0].append(etap)

    list_tbls = CSQ.get_list_of_tables_c(self.db_kplan)


    
    podrs = CSQ.custom_request_c(self.db_kplan,f"""
SELECT Пномер,
       Имя,
       Имя_поля,
       Это_группа_сборки,
       poki
  FROM podrazdel WHERE poki = {CFG.Config.place.poki};
""",rez_dict= True)

    inner = "\n".join([f'{_["Имя"]} ON {_["Имя"]}.НомПл    = пл_оуп.НомПл,' for _ in podrs ])[:-1]
    select = []
    dinamic_names_fields = []
    group_names_fields = []
    for item in podrs:
        list_names = item["Имя_поля"].split(';')
        for i, name in enumerate(list_names):
            if len(list_names) == 1 or i>0:
                select.append(f'{item["Имя"]}.{name}')
                dinamic_names_fields.append(name)
            if i>0:
                group_names_fields.append(name)
    select = ", ".join(select)
    
    query = f"""SELECT пл_оуп.№проекта || '$' || пл_оуп.№ERP as Проект, пл_оуп.Количество, plan.Пномер, пл_топ.Вид, пл_ко.Вес_ВО,
     plan.Нчас_вспом, {select}
     FROM пл_оуп
    INNER JOIN
    plan ON plan.Пномер    = пл_оуп.НомПл,
    пл_топ ON пл_топ.НомПл = пл_оуп.НомПл,
    пл_ко  ON пл_ко.НомПл = пл_оуп.НомПл,
    {inner}
    """
    responce = CSQ.custom_request_c(self.db_kplan, query, rez_dict=True)
    dict_kpl = dict()

    template = {'Нчпс': 0, 'Вес': 0, 'Кол_во': 0}
    for field in dinamic_names_fields:
        template[field] = 0
    for item in responce:
        if item['Вид'] not in dict_kpl:

            dict_kpl[item['Вид']] = copy.deepcopy(template)


        kol = F.valm(item['Количество'])
        if kol == 0:
            continue
        dict_kpl[item['Вид']]['Вес'] += F.valm(item['Вес_ВО']) / kol
        for name in dinamic_names_fields:
            dict_kpl[item['Вид']][name] += item[name] / kol

        summ_val = 0
        for name in group_names_fields:
            summ_val += item[name]
        if summ_val == 0:
            continue

        npsm = (F.valm(item['Вес_ВО']) / kol) / (
                    (summ_val / kol) / 8)

        if npsm < 10 or npsm > 300:
            continue
        dict_kpl[item['Вид']]['Нчпс'] += npsm
        dict_kpl[item['Вид']]['Кол_во'] += 1


    for item in dict_kpl:

        if dict_kpl[item]['Кол_во']:
            count_izd = dict_kpl[item]['Кол_во']

            dict_kpl[item]['Вес'] = round(dict_kpl[item]['Вес'] / dict_kpl[item]['Кол_во'], 1)
            dict_kpl[item]['Нчпс'] = round(dict_kpl[item]['Нчпс'] / dict_kpl[item]['Кол_во'], 2)
            for name in dinamic_names_fields:
                dict_kpl[item][name] = round(dict_kpl[item][name] / count_izd, 2)


        else:
            dict_kpl[item]['Вес'] = 0
            for name in dinamic_names_fields:
                dict_kpl[item][name] = 0


    query = f"""SELECT DISTINCT naryad.Номер_мк, naryad.Пномер, naryad.Дата, naryad.Твремя, naryad.Фвремя, naryad.Фвремя2, 
        naryad.ФИО, naryad.ФИО2, napravlenie.name as Направление, naryad.Опер_время, naryad.Операции, mk.Вес, 
         пл_топ.Вид FROM naryad 
    INNER JOIN mk ON mk.Пномер == naryad.Номер_мк 
    INNER JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер 
    INNER JOIN plan ON plan.Пномер = mk.НомКплан 
    INNER JOIN пл_топ ON пл_топ.НомПл = plan.Пномер 
    INNER JOIN napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности 
    INNER JOIN napravlenie ON napravlenie.Пномер = napravl_deyat.Направление  
    WHERE naryad.Подтвержд_вып == 1 AND datetime(naryad.Дата) > datetime("{data_nach}") 
                    and datetime(naryad.Дата) < datetime("{data_kon}") and mk.Направление != 'ПТ' 
                     and naryad.Внеплан in(10, 0) AND пл_топ.Вид != 1 and plan.poki == {self.place.poki} """
    dict_rez = dict()
    responce = CSQ.custom_request_c(self.bd_naryad, query, rez_dict=True,attach_dbs=(self.db_kplan))

    #query = f"""SELECT plan.МК, пл_топ.Вид FROM plan INNER JOIN пл_топ ON пл_топ.НомПл = plan.Пномер WHERE plan.МК != 0 AND пл_топ.Вид != 1"""
    #dict_mk_sort_c = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, query, rez_dict=True), 'МК')
    dict_sort_c = self.Data.DICT_VID_PO_NAPR #18.07.25

    list_napr = sorted(list(dict_sort_c.keys()))
    dict_shabl_napr = dict()

    for napr in list_napr:
        dict_shabl_napr[napr] = dict()
        dict_shabl_napr[napr]['etap_fakt'] = copy.deepcopy(shablon_etaps)
        dict_shabl_napr[napr]['etap_norm'] = copy.deepcopy(shablon_etaps)
        dict_shabl_napr[napr]['Вес'] = 0
        dict_shabl_napr[napr]['Кол'] = 0
    tmp_dict_mk = dict()
    for item in responce:
        napr_deyat = item['Направление']
        koef_vneplana = 1
        koef_pogr_norm = 1
        try:
            koef_vneplana = \
                self.Data.DICT_NAPRAVL[napr_deyat]['koef_vneplana']
            koef_pogr_norm = \
                self.Data.DICT_NAPRAVL[napr_deyat]['koef_pogr_norm']
        except:
            CQT.msgbox(f'Не корректно занесен направление')
            return
        fvrem = F.valm(item['Фвремя']) + F.valm(item['Фвремя2'])
        tvrem = F.valm(item['Твремя']) * bool(item['ФИО']) + F.valm(item['Твремя']) * bool(item['ФИО2'])
        if fvrem == 0 or tvrem == 0:
            continue
        if item['Номер_мк'] not in tmp_dict_mk:
            tmp_dict_mk[item['Номер_мк']] = {'Вес': item['Вес'],
                                             'Вид': item['Вид'],
                                             'Этапы': copy.deepcopy(shablon_etaps),
                                             'Этапы_нома': copy.deepcopy(shablon_etaps),
                                             'koef_vneplana': koef_vneplana,
                                             'koef_pogr_norm': koef_pogr_norm}
        koef = tvrem / fvrem
        list_oper = [_.split("$")[-1] for _ in item['Операции'].split("|")]
        list_time = [F.valm(_) for _ in item['Опер_время'].split("|")]
        for i in range(len(list_oper)):
            if list_oper[i] not in self.DICT_OPER_FULL:
                continue
            if len(list_oper) > len(list_time):
                continue
            etap = self.DICT_OPER_FULL[list_oper[i]]['etap']
            if etap is None:
                continue
            time_fact = list_time[i] / koef
            tmp_dict_mk[item['Номер_мк']]['Этапы'][etap] += time_fact
            tmp_dict_mk[item['Номер_мк']]['Этапы_нома'][etap] += list_time[i]


    estimated_vid_rab_names_fact = {v['Имя'] for k, v in self.Data.DICT_GROUP_PODR_VID_RAB_FOR_PLAN.items()
                                    if
                                    v['estimated'] and v['poki'] == CFG.Config.place.poki}
    def calc_estimated_etap(etap):
        estimated = False
        if etap in self.Data.DICT_ETAPI_FULL:
            etap_data = self.Data.DICT_ETAPI_FULL[etap]
            if etap_data['sopost_etapov_vo'] is not None:
                sopost_etapov_vo = etap_data['sopost_etapov_vo'].split("|")
                for elem in sopost_etapov_vo:
                    if elem.split('.')[0] in estimated_vid_rab_names_fact:
                        estimated = True
                        break
        return estimated

    for mk in tmp_dict_mk.keys():
        ves = tmp_dict_mk[mk]['Вес'] * KOEF_RASKLADKI
        vid = tmp_dict_mk[mk]['Вид']
        try:
            dict_shabl_napr[vid]['Вес'] += ves                
        except:
            pass
        dict_shabl_napr[vid]['Кол'] += 1
        for etap in tmp_dict_mk[mk]['Этапы'].keys():
            if calc_estimated_etap(etap):
                dict_shabl_napr[vid]['etap_fakt'][etap] += tmp_dict_mk[mk]['Этапы'][etap] * tmp_dict_mk[mk][
                    'koef_pogr_norm'] * tmp_dict_mk[mk]['koef_vneplana']
                dict_shabl_napr[vid]['etap_norm'][etap] += tmp_dict_mk[mk]['Этапы_нома'][etap] * tmp_dict_mk[mk][
                    'koef_pogr_norm'] * tmp_dict_mk[mk]['koef_vneplana']
            else:
                dict_shabl_napr[vid]['etap_fakt'][etap] += tmp_dict_mk[mk]['Этапы'][etap] * tmp_dict_mk[mk][
                    'koef_pogr_norm']
                dict_shabl_napr[vid]['etap_norm'][etap] += tmp_dict_mk[mk]['Этапы_нома'][etap] * tmp_dict_mk[mk][
                    'koef_pogr_norm']
    for vid in dict_shabl_napr.keys():
        ves = dict_shabl_napr[vid]['Вес']
        kol_vo = dict_shabl_napr[vid]['Кол']
        if ves == 0:
            continue
        tmp = [vid, kol_vo, self.Data.NAPRAVL_DEYAT_KOD[dict_sort_c[vid]['Направл']]['Направление'],
               dict_sort_c[vid]['Имя'], 0, 0, 0, 0]
        for etap in dict_shabl_napr[vid]['etap_fakt'].keys():
            if etap in ['Вес', 'Кол']:
                continue
            dict_shabl_napr[vid]['etap_fakt'][etap] = round(dict_shabl_napr[vid]['etap_fakt'][etap] / ves, 1)
            dict_shabl_napr[vid]['etap_norm'][etap] = round(dict_shabl_napr[vid]['etap_norm'][etap] / ves, 1)

        summ_estimated_fakt = 0
        for etap,val in dict_shabl_napr[vid]['etap_fakt'].items():
             if calc_estimated_etap(etap):
                 summ_estimated_fakt += val
        summ_estimated_norm  = 0
        for etap,val in dict_shabl_napr[vid]['etap_norm'].items():
             if calc_estimated_etap(etap):
                 summ_estimated_norm += val


        if summ_estimated_fakt:
            tmp[4] = 0
            tmp[5] = 0
            tmp[6] = 0
            tmp[7] = 0
            if vid in dict_kpl:
                tmp[7] = dict_kpl[vid]['Нчпс']
            if summ_estimated_fakt > 0:
                tmp[4] = round(480 / summ_estimated_fakt)
            if summ_estimated_norm > 0:
                tmp[5] = round(480 / summ_estimated_norm)

            if tmp[4] != 0 and tmp[7] != 0:
                tmp[6] = round((tmp[4] + tmp[7]) / 2, 1)

            if tmp[4] == 0:
                tmp[6] = tmp[7]
            if tmp[7] == 0:
                tmp[6] = tmp[4]

        dict_shabl_napr[vid]['Вес'] = '*'

        for rez_etap in rez[0][8:]:
            if dict_shabl_napr[vid]['etap_fakt'][rez_etap] == 0 and dict_shabl_napr[vid]['etap_norm'][rez_etap] != 0:
                tmp.append(
                    (dict_shabl_napr[vid]['etap_norm'][rez_etap]))
            if dict_shabl_napr[vid]['etap_fakt'][rez_etap] != 0 and dict_shabl_napr[vid]['etap_norm'][rez_etap] == 0:
                tmp.append(
                    (dict_shabl_napr[vid]['etap_fakt'][rez_etap]))
            if dict_shabl_napr[vid]['etap_fakt'][rez_etap] != 0 and dict_shabl_napr[vid]['etap_norm'][rez_etap] != 0:
                tmp.append(round(
                    (dict_shabl_napr[vid]['etap_fakt'][rez_etap] + dict_shabl_napr[vid]['etap_norm'][rez_etap]) / 2, 3))
        rez.append(tmp)
    # rez.append(['' for _ in rez[0]])
    # rez.append(['' for _ in rez[0]])

    max_lenght = max([len(_) for _ in rez])
    for item in rez:
        delta = max_lenght - len(item)
        for i in range(delta):
            item.append('')
    for j in range(len(rez[0])):
        if rez[0][j] in shablon_etaps:
            rez[0][j] = rez[0][j] + "_мин/кг"
    return rez


@CQT.onerror
def get_plan_vneplan_data(self, data_nach, data_kon, vid='Все', etap='Сборка+сварка'):
    if vid == '-':
        vid = 'Все'
    if etap == '':
        CQT.msgbox(f'Подразделение не выбрано')
        return [[]]

    def clac_fio_for_pfanal(self, fio):
        if fio != '' and fio in self.Data.ETAP_BY_FIO:
            return True
        return False

    def calc_sb_sv_time_minutes(item, fio_zav):
        summ = 0
        if item['ФИО'] == fio_zav:
            summ += F.valm(item['Твремя']) * clac_fio_for_pfanal(self, item['ФИО'])
        if item['ФИО2'] == fio_zav:
            summ += F.valm(item['Твремя']) * clac_fio_for_pfanal(self, item['ФИО2'])
        return summ

    if "DICT_NN_NTK" not in self.__dict__ or self.DICT_NN_NTK == None:
        self.DICT_NN_NTK = CMS.load_dict_dse(self.db_dse)

    TUPLE_DOUBLE_SHOVOV = (
        'Т3', "Н2", "С7", "С12", "С14", "С15", "С16", "С43", "С21", "С45", "С23", "С25", "С26", "С27", "С39",
        "С40", "У5", "У7", "У8", "У10", "Т7", "Т2", "Т8", "Т9", "Т5",)



    
    self.list_month_plan  = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM mnts_plan WHERE 
                    datetime(Дата) >= datetime("{data_nach}") 
                    and datetime(Дата) < datetime("{data_kon}") and poki == {self.place.poki}""", rez_dict=True)
    list_month_plan = self.list_month_plan

    if 'list_month_fact' not in self.__dict__ or self.list_month_fact == None:
        get_list_month_fact(self)
    list_month_fact = self.list_month_fact


    rez = [['Месяц', 'Этап', 'Внеплан сумма, н-см./чел.', 'План, н-см./чел.']]
    dict_cat_vnepl = dict()
    list_by_vid_rab = []

    list_kat_vnepl = [ _['value'] for _ in self.Data.KAT_VNEPL if _['kod'] > 0]
    #CSQ.custom_request_c(self.bd_naryad, f"""SELECT value FROM kategor_vnepl WHERE kod > 0""",
    #                                      one_column=True,
    #                                      hat_c=False)
    dict_type_mk_names = self.Data.DICT_TYPE_MK_NAMES

    dict_type_dorez = self.Data.DICT_TYPE_DOREZ

    dict_type_dorez_names = F.deploy_dict_c(dict_type_dorez, 'Имя')
    dict_type_dorez_nums = F.deploy_dict_c(dict_type_dorez, 'Пномер')

    dict_type_dorab_ = self.Data.DICT_TYPE_DORAB

    dict_type_dorab_names = F.deploy_dict_c(dict_type_dorab_
                                            , 'Имя')
    dict_type_dorab_nums = F.deploy_dict_c(dict_type_dorab_
                                           , 'Пномер')
    if 'dict_dorezok' not in self.__dict__ or self.dict_dorezok == None:
        self.dict_dorezok = F.deploy_dict_c(CSQ.custom_request_c(self.bd_naryad, f"""SELECT дорезки_мк.Номер_мк,  тип_дорезок.Имя 
         FROM дорезки_мк INNER JOIN тип_дорезок ON тип_дорезок.Пномер == дорезки_мк.Причина""", rez_dict=True),
                                   "Номер_мк")
    dict_dorezok = self.dict_dorezok
    # TODO ПРИВЯЗАТЬ КАТЕГОРИИ ДОРЕЗОК И ДОРАБОТОК В ОТЧЕТ ЧЕРЕЗ ОБЩИЙ ВИД
    for kat in list_kat_vnepl:
        if 'не использовать' in kat.lower():
            continue
        rez[0].append(kat)
        dict_cat_vnepl[kat] = 0

    for name in dict_type_dorez_names:
        name_full = 'Дорезка_' + name
        rez[0].append(name_full)
        dict_cat_vnepl[name_full] = 0
    rez[0].append('Дорезка')
    dict_cat_vnepl['Дорезка'] = 0
    for name in dict_type_dorab_names:
        if name == '':
            name_full = 'Доработка(без дорезки)'
        else:
            name_full = 'Доработка_' + name
        rez[0].append(name_full)
        dict_cat_vnepl[name_full] = 0
    rez[0].append('Испытания')
    dict_cat_vnepl['Испытания'] = 0
    rez[0].append('Покрытие')
    dict_cat_vnepl['Покрытие'] = 0
    # не работал тип
    # dict_cat_vnepl["Доработка(без дорезки)"] = 0
    # rez[0].append("Доработка(без дорезки)")
    # ===============================
    for item in list_month_plan:
        for kat in dict_cat_vnepl.keys():
            dict_cat_vnepl[kat] = 0

        data = item['Дата']
        for mk in list_month_fact:
            if mk['Направление'] == vid or vid == 'Все':
                dat_str = mk['Дата_завершения']
                dat_f = \
                F.start_end_dates_c(F.strtodate(dat_str, "%Y-%m-%d %H:%M:%S"), '', vid='m', format_out="%Y-%m-%d")[
                    0]

        nach_data, kon_data = F.start_end_dates_c(F.strtodate(data, "%Y-%m-%d"), '', vid='m',
                                                  format_out="%Y-%m-%d %H:%M:%S")
        postfix = ''
        if vid != 'Все':
            postfix = f'mk.Вид = "{vid}" AND '

        DICT_VID_NAPR = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_kplan, f"""SELECT НомПл, Вид  FROM пл_топ;""", rez_dict=True), 'НомПл')

        custom_request_c = f"""SELECT DISTINCT
                                    naryad.Пномер, naryad.Твремя, naryad.Норма_времени,  naryad.Номер_мк, naryad.Внеплан, 
                        naryad.ФИО  as ФИО , naryad.ФИО2  as ФИО2, 
                                    naryad.Фвремя, naryad.Фвремя2, naryad.Примечание,naryad.ДСЕ,naryad.ДСЕ_ID,naryad.Опер_колво,
                                    naryad.Профессии, naryad.Операции, naryad.Опер_время, naryad.Виды_работ, mk.Вид, mk.Направление, 
                                     Тип_мк.Имя as Тип, тип_доработок.Имя as Доработка, naryad.Коэфф_сложности,
                        mk.Вес, 
                                CASE WHEN знпр.№ERP IS NOT NULL 
                       THEN знпр.№ERP 
                       ELSE mk.Номер_заказа 
                       END AS Номер_заказа,  
                       
                         CASE WHEN знпр.№проекта IS NOT NULL 
                       THEN знпр.№проекта 
                       ELSE mk.Номер_проекта 
                       END AS Номер_проекта,  
                       
                        mk.Дата_завершения, mk.Количество, 
                        mk.Номенклатура, mk.НомКплан, jurnal.Пномер as ПномерЖ, jurnal.Дата as Дата_журнал , jurnal.ФИО as fio_jur_zav, 
                        "" as Дата_выгрузки_ЕРП, "" as ФИО_выгрузки_ЕРП, 0 as Минут_выгружено_ЕРП, "" as base_ERP, 
                        kategor_vnepl.value as Категория_внепл , 
                        naryad.Подтвержд_вып_дата as Подтвержд_вып_дата ,
                        mk.Дата as Дата_мк
                        FROM jurnal 
                                    INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер  
                                    INNER JOIN mk ON mk.Пномер = naryad.Номер_мк  
                                    INNER JOIN kategor_vnepl ON kategor_vnepl.kod = naryad.Категория_внепл   
                                    INNER JOIN Тип_мк ON Тип_мк.Пномер = mk.Тип 
                                    INNER JOIN тип_доработок ON тип_доработок.Пномер = mk.Тип_доработки  
                                    LEFT JOIN plan ON plan.Пномер = mk.НомКплан  
                                    LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
                                    LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
                        WHERE {postfix} naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1 AND naryad.Аутсорсинг == 0 and 
                        jurnal.Статус == "Завершен" and plan.poki == {self.place.poki} and datetime(jurnal.Дата) >= datetime("{nach_data}") 
                        and datetime(jurnal.Дата) <= datetime("{kon_data}")
            """
        list_zav_nar_po = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True, attach_dbs=(self.db_kplan))
        s_num_nars = list({_['Пномер'] for _ in list_zav_nar_po})
        starts_with_params_erp_upload = CSQ.custom_request_c(self.bd_naryad,f"""SELECT 
        jurnal.Пномер as ПномерЖ, jurnal.Дата, jurnal.Номер_наряда, jurnal.ФИО as fio_jur_zav, 
        jurnal.Дата_выгрузки_ЕРП, jurnal.ФИО_выгрузки_ЕРП, jurnal.Минут_выгружено_ЕРП, jurnal.base_ERP
        FROM jurnal 
         WHERE jurnal.Номер_наряда IN ({CSQ.prepare_list_to_tuple(s_num_nars)})
         AND jurnal.Статус == "Начат" ORDER BY jurnal.Пномер DESC""",rez_dict=True)

        summ_ves_plan = 0
        summ_ves_vir_vneplan = 0

        l_svar = 0
        set_errors = set()
        etap_user = type_vneplan = 'Неопределено'
        for item_zav_nar in list_zav_nar_po:
            item_zav_nar['Дата_журнал_нач.'] = ''
            item_zav_nar['Дата_журнал_кон.'] = item_zav_nar['Дата_журнал']
            item_zav_nar['Дата_выгрузки_ЕРП'] = ''
            for item_params_erp in starts_with_params_erp_upload:
                if item_params_erp['fio_jur_zav'] == item_zav_nar['fio_jur_zav']:
                    if item_params_erp['Номер_наряда'] == item_zav_nar['Пномер']:
                        if item_params_erp['ПномерЖ'] < item_zav_nar['ПномерЖ']:
                            if item_zav_nar['Дата_журнал_нач.'] == '' or F.strtodate(item_zav_nar['Дата_журнал_нач.']) >  F.strtodate(item_params_erp['Дата']):
                                item_zav_nar['Дата_журнал_нач.'] = item_params_erp['Дата']
                            if item_zav_nar['Дата_журнал_кон.'] == '' or F.strtodate(item_zav_nar['Дата_журнал_кон.']) <  F.strtodate(item_params_erp['Дата']):
                                item_zav_nar['Дата_журнал_кон.'] = item_params_erp['Дата']
                            item_zav_nar['Дата_выгрузки_ЕРП'] = item_zav_nar['Дата_выгрузки_ЕРП'] + ";" + item_params_erp['Дата_выгрузки_ЕРП']
                            item_zav_nar['ФИО_выгрузки_ЕРП'] = item_params_erp['ФИО_выгрузки_ЕРП']
                            item_zav_nar['Минут_выгружено_ЕРП'] += item_params_erp['Минут_выгружено_ЕРП']
                            item_zav_nar['base_ERP'] = item_params_erp['base_ERP']
            item_zav_nar['Дата_выгрузки_ЕРП'] = item_zav_nar['Дата_выгрузки_ЕРП'][1:]

            item_zav_nar['виды_по_напр'] = 1
            if item_zav_nar['НомКплан'] in DICT_VID_NAPR:
                item_zav_nar['виды_по_напр'] = DICT_VID_NAPR[item_zav_nar['НомКплан']]
            fio_zav = item_zav_nar['fio_jur_zav']
            add_time = calc_sb_sv_time_minutes(item_zav_nar, fio_zav)
            if fio_zav not in self.Data.ETAP_BY_FIO:
                CQT.msgbox(f'{fio_zav} не найден в ETAP_BY_FIO')
                return None, None
            etap_user = self.Data.ETAP_BY_FIO[fio_zav]['этап']
            if etap_user == None:
                CQT.msgbox(f'Для {fio_zav} не указан этап в DB dolgn_etap')
                return None, None
            if vid != 'Все':
                if etap_user != etap:
                    continue
            try:
                if item_zav_nar['Тип'] == 'Плановая':  # Плановая
                    if item_zav_nar['Внеплан'] in (0,10):
                        summ_ves_plan += add_time
                        list_by_vid_rab.append(['план', etap_user, '', add_time, item_zav_nar])

                    else:  # ===item['Внеплан'] == 2 ===Внеплановый наряд по плановой МК
                        if item_zav_nar['Категория_внепл'] in dict_cat_vnepl:
                            summ_ves_vir_vneplan += add_time
                            list_by_vid_rab.append(
                                ['внеплан', etap_user, item_zav_nar['Категория_внепл'], add_time, item_zav_nar])
                            dict_cat_vnepl[item_zav_nar['Категория_внепл']] += add_time

                else:
                    if item_zav_nar['Тип'] == 'Дорезка':
                        if item_zav_nar['Номер_мк'] not in dict_dorezok:
                            type_vneplan = "Дорезка"
                        else:
                            type_vneplan = 'Дорезка_' + dict_dorezok[item_zav_nar['Номер_мк']]

                            if type_vneplan not in dict_cat_vnepl:
                                type_vneplan = "Дорезка"

                        summ_ves_vir_vneplan += add_time
                        dict_cat_vnepl[type_vneplan] += add_time

                    if item_zav_nar['Тип'] == 'Испытание':
                        type_vneplan = 'Испытания'
                        summ_ves_vir_vneplan += add_time
                        dict_cat_vnepl[type_vneplan] += add_time
                    if item_zav_nar['Тип'] == 'Покрытие':
                        type_vneplan = 'Покрытие'
                        summ_ves_vir_vneplan += add_time
                        dict_cat_vnepl[type_vneplan] += add_time
                    if item_zav_nar['Тип'] == 'Доработка(без дорезки)':
                        type_vneplan = 'Доработка(без дорезки)'
                        if 'Доработка_' + item_zav_nar['Доработка'] in dict_cat_vnepl:
                            type_vneplan = 'Доработка_' + item_zav_nar['Доработка']
                        summ_ves_vir_vneplan += add_time
                        dict_cat_vnepl[type_vneplan] += add_time
                    list_by_vid_rab.append(['внеплан', etap_user, type_vneplan, add_time, item_zav_nar])
            except:
                print(f'err {item_zav_nar}')

        summ_ves_plan = summ_ves_plan / 480
        summ_ves_vir_vneplan = summ_ves_vir_vneplan / 480
        summ_ves_fact = summ_ves_plan + summ_ves_vir_vneplan
        k = 0
        if summ_ves_plan > 0:
            k = summ_ves_fact / summ_ves_plan
        tmp = [data, etap_user,
               round(summ_ves_vir_vneplan, 2), round(summ_ves_plan, 2)]

        for kat in dict_cat_vnepl.keys():
            tmp.append(round(dict_cat_vnepl[kat] / 480, 2))

        rez.append(tmp)
    rez = F.sort_by_column_c(rez,'Месяц',date_time=True,date_format="%Y-%m-%d")
    return rez, list_by_vid_rab
    CQT.msgboxg_get_table_ok_inf(self,'Отладка',
                                 [{'_Тип':_[0],
                                   '_Этап':_[1],
                                   '_Категория_внепл':_[2],
                                   '_add_time': _[3],
                                   **{k:v for k,v in _[4].items()}
                                   } for _ in list_by_vid_rab]
                                 )

def vneplan_po_napravl(self, data_nach, data_kon, vid, etap='Сборка+сварка', generate_graf=True, *args):
    results = get_plan_vneplan_data(self, data_nach, data_kon, vid, etap)
    if results == None:
        return 
    rez, *args = results
    if rez == None:
        return
        # F.save_file('vneplan_data.txt',summ_list_vneplan)
    if generate_graf:

        list_delete = []
        for column in range(1, len(rez[0])):
            delete_ = True
            for row in range(len(rez)):
                if F.valm(rez[row][column]) > 0:
                    delete_ = False
                    break
            if delete_:
                list_delete.append(column)
        rez = F.delete_column(rez, numbers_del=list_delete)
        load_browser(self)
        create_gant(self, rez, vid)
        rez.append(['' for _ in rez[0]])
        rez.append(['' for _ in rez[0]])
    return rez


def plan_fact_mes(self, data_nach, data_kon, vid, *args):
    GR = check_import_modyle('grafics')
    if GR is None:
        import grafics as GR
    def clac_fio_for_pfanal(self, fio, summ_ves_vir_vneplan, time):
        if fio != '' and fio in self.DICT_EMPLOEE:
            prof = self.DICT_EMPLOEE[fio]
            if prof in self.DICT_PROFESSIONS_NAME:
                if self.DICT_PROFESSIONS_NAME[prof]['этап'] == 'Сборка+сварка':
                    summ_ves_vir_vneplan += F.valm(time)
        return summ_ves_vir_vneplan

    self.DICT_NN_NTK = CMS.load_dict_dse(self.db_dse)

    TUPLE_DOUBLE_SHOVOV = (
    'Т3', "Н2", "С7", "С12", "С14", "С15", "С16", "С43", "С21", "С45", "С23", "С25", "С26", "С27", "С39",
    "С40", "У5", "У7", "У8", "У10", "Т7", "Т2", "Т8", "Т9", "Т5",)

    list_month_plan = CSQ.custom_request_c(self.db_kplan, """SELECT * FROM mnts_plan""", rez_dict=True)
    list_month_fact = CSQ.custom_request_c(self.bd_naryad, """SELECT * FROM mk WHERE Дата_завершения != '' """,
                                           rez_dict=True)
    rez = [['Месяц', 'План, н-см.', 'Отгрузка, кг.', 'Факт, н-см.', 'Внеплан, н-см.', 'Сумм. Факт, н-см.',
            'Сумм св_швов, м.']]
    dict_cat_vnepl = dict()
    list_kat_vnepl = CSQ.custom_request_c(self.bd_naryad, f"""SELECT value FROM kategor_vnepl WHERE kod > 0""",
                                          one_column=True, hat_c=False)
    for kat in list_kat_vnepl:
        rez[0].append(kat)
        dict_cat_vnepl[kat] = 0
    for item in list_month_plan:
        summ_ves = 0
        for kat in dict_cat_vnepl.keys():
            dict_cat_vnepl[kat] = 0

        data = item['Дата']
        if vid == 'Все':
            ves_pl = 0
            for vid_tmp in self.DICT_NAPRAVL.keys():
                if vid_tmp in item:
                    ves_pl += item[vid_tmp]
        else:
            ves_pl = item[vid]
        for mk in list_month_fact:

            if mk['Направление'] == vid or vid == 'Все':
                dat_str = mk['Дата_завершения']
                dat_f = \
                F.start_end_dates_c(F.strtodate(dat_str, "%Y-%m-%d %H:%M:%S"), '', vid='m', format_out="%Y-%m-%d")[0]
                if dat_f == data:
                    summ_ves += mk['Вес']
        nach_data, kon_data = F.start_end_dates_c(F.strtodate(data, "%Y-%m-%d"), '', vid='m',
                                                  format_out="%Y-%m-%d %H:%M:%S")
        if vid == 'Все':
            custom_request_c = f"""SELECT DISTINCT
            naryad.Пномер, naryad.Твремя, naryad.Номер_мк, naryad.Внеплан, 
naryad.ФИО  as ФИО , naryad.ФИО2  as ФИО2, 
            naryad.Фвремя, naryad.Фвремя2, naryad.Примечание,naryad.ДСЕ,naryad.Опер_колво, naryad.Операции, naryad.Опер_время, naryad.Виды_работ, mk.Вид, 
mk.Вес, mk.Номер_заказа, mk.Номер_проекта, mk.Дата_завершения, mk.Количество, kategor_vnepl.value as Категория_внепл FROM jurnal
            INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер
            INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
            INNER JOIN kategor_vnepl ON kategor_vnepl.kod = naryad.Категория_внепл 
            WHERE naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1 and 
            jurnal.Статус == "Завершен" and datetime(jurnal.Дата) > datetime("{nach_data}") 
            and datetime(jurnal.Дата) < datetime("{kon_data}")
"""
        else:
            custom_request_c = f"""SELECT DISTINCT
                        naryad.Пномер, naryad.Твремя, naryad.Номер_мк, naryad.Внеплан, 
            naryad.ФИО  as ФИО , naryad.ФИО2  as ФИО2, 
                        naryad.Фвремя, naryad.Фвремя2, naryad.Примечание,naryad.ДСЕ,naryad.Опер_колво, naryad.Операции, naryad.Опер_время, naryad.Виды_работ, mk.Вид, 
            mk.Вес, mk.Номер_заказа, mk.Номер_проекта, mk.Дата_завершения, mk.Количество,kategor_vnepl.value as Категория_внепл FROM jurnal
                        INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер
                        INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
                        INNER JOIN kategor_vnepl ON kategor_vnepl.kod = naryad.Категория_внепл 
                        WHERE mk.Вид = "{vid}" AND naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1 and 
                        jurnal.Статус == "Завершен" and datetime(jurnal.Дата) > datetime("{nach_data}") 
                        and datetime(jurnal.Дата) < datetime("{kon_data}")
            """
        list_zav_nar_po = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)
        summ_ves_vir = 0
        summ_ves_vir_vneplan = 0
        l_svar = 0
        for item in list_zav_nar_po:
            if item['Внеплан'] == 0:
                list_oper = item['Операции'].split('|')
                list_oper_time = item['Опер_время'].split('|')
                list_dse = item['ДСЕ'].split('|')
                list_kolvo_dse = item['Опер_колво'].split("|")
                for i_o, oper in enumerate(list_oper):
                    oper_nom, oper_name = oper.split('$')
                    if oper_name in self.DICT_ETAPI:
                        if self.DICT_ETAPI[oper_name] == 'Сборка+сварка':
                            add_ = F.valm(list_oper_time[i_o])
                            if item['ФИО'] != '' and item['ФИО2'] != '':
                                add_ = add_ / 2
                            summ_ves_vir += add_
                    if oper_name == 'Сварка':
                        dse_name, dse_nn = list_dse[i_o].split('$')
                        kol_vo_dse = F.valm(list_kolvo_dse[i_o])
                        name_file = self.DICT_NN_NTK[dse_nn]['Номер_техкарты'] + "_" + dse_nn + ".pickle"
                        path = F.sep().join([self.data_f, r"MKart\data", str(item['Номер_мк']), name_file])
                        if F.existence_file_c(path):
                            tk = F.open_file_c(path, pickl=True)
                            for i_f in range(11, len(tk)):
                                list_item_f = tk[i_f].split('|')
                                if list_item_f[20] == '0':
                                    break
                                if list_item_f[0] == oper_name and list_item_f[2] == oper_nom:
                                    values = list_item_f[14].split("$")
                                    if len(values) > 1:
                                        row_len = values[2].split(';')
                                        row_sort_c = values[1].split(';')
                                        for i_s in range(len(row_len)):
                                            if row_sort_c[i_s].upper() in TUPLE_DOUBLE_SHOVOV:
                                                val_shva = F.valm(row_len[i_s]) * 2
                                            else:
                                                val_shva = F.valm(row_len[i_s])
                                            l_svar += val_shva * kol_vo_dse / 1000
                                    else:
                                        print('Сварка' + str(values))
            if item['Внеплан'] == 2:
                if item['Виды_работ'] == "":
                    summ_ves_vir_vneplan = clac_fio_for_pfanal(self, item['ФИО'], summ_ves_vir_vneplan, item['Твремя'])
                    summ_ves_vir_vneplan = clac_fio_for_pfanal(self, item['ФИО2'], summ_ves_vir_vneplan, item['Твремя'])
                else:
                    if item['Виды_работ'] in self.DICT_VID_RABOT:
                        if self.DICT_VID_RABOT[item['Виды_работ']]['этап'] == 'Сборка+сварка':
                            summ_ves_vir_vneplan += F.valm(item['Твремя']) * bool(item['ФИО'])
                            summ_ves_vir_vneplan += F.valm(item['Твремя']) * bool(item['ФИО2'])
                            if item['Категория_внепл'] in dict_cat_vnepl:
                                dict_cat_vnepl[item['Категория_внепл']] += F.valm(item['Твремя']) * bool(item['ФИО'])
                                dict_cat_vnepl[item['Категория_внепл']] += F.valm(item['Твремя']) * bool(item['ФИО2'])

        summ_ves_vir = summ_ves_vir / 480
        summ_ves_vir_vneplan = summ_ves_vir_vneplan / 480
        summ_ves_fact = summ_ves_vir + summ_ves_vir_vneplan
        k = 0
        if summ_ves_vir > 0:
            k = summ_ves_fact / summ_ves_vir
        tmp = [data, round(ves_pl / PROIZVODITELNOST_POST_SM), round(summ_ves / 100, 3), round(summ_ves_vir),
               round(summ_ves_vir_vneplan), round(summ_ves_fact), round(l_svar * k)]
        for kat in dict_cat_vnepl.keys():
            tmp.append(round(dict_cat_vnepl[kat] / 480))
        rez.append(tmp)
    GR.load_elements(self, rez, 'План-фактный анализ по месяцам')
    self.parent_for_grafic.addWidget(self.toolbar)
    self.parent_for_grafic.addWidget(self.canvas)
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez


def clear_graf(self):
    try:
        self.parent_for_grafic.removeWidget(self.toolbar)
        self.parent_for_grafic.removeWidget(self.canvas)
    except:
        pass
    try:
        self.parent_for_grafic.removeWidget(self.browser)
    except:
        pass


@CQT.onerror
def trudozatraty(self, data_nach, data_kon, podrazd='-', *args):
    LIST_UNCHECK_PROF = ['Оператор лазерных установок', 'Инженер-технолог']
    LIST_DELETE_PROF = ['Мастер цеха', 'Старший мастер цеха']

    @CQT.onerror
    def check_master(self, dolg, fio, *args):
        fiod = fio + " " + dolg
        if dolg in LIST_DELETE_PROF:
            return True
        fl_master = False
        for rc in self.DICT_RC_FULL.keys():
            if self.DICT_RC_FULL[rc]['ФИО_1см'] == fiod or self.DICT_RC_FULL[rc]['ФИО_2см'] == fiod or \
                    self.DICT_RC_FULL[rc]['ФИО_3см'] == fiod:
                if 'мастер' in self.DICT_RC_FULL[rc]['Прозвище'].lower():
                    fl_master = True
                    break
        if fl_master:
            return True
        return False

    @CQT.onerror
    def min_za_den_tabel(self, fiod, data, *args):
        name_table = F.datetostr(F.strtodate(data), 'mtdz_%Y_%m_01')
        day = F.datetostr(F.strtodate(data), 'd_%Y_%m_%d')
        custom_request_c = f'''SELECT {day} FROM {name_table} WHERE ФИО LIKE "{fiod}%"; '''
        rez = CSQ.custom_request_c(F.bdcfg("BD_users"), custom_request_c)
        if rez == False or len(rez) == 1:
            return "Не найден"
        summ = 0
        for i in range(1, len(rez)):
            summ += rez[i][0]
        return summ * 60

    @CQT.onerror
    def den_tabel(self, data, *args):
        name_table = F.datetostr(F.strtodate(data), 'mtdz_%Y_%m_01')
        custom_request_c = f'''SELECT Пномер, ФИО FROM {name_table} WHERE Пномер > 2 AND Примечание != "Увольнение"; '''
        rez = CSQ.custom_request_c(F.bdcfg("BD_users"), custom_request_c, rez_dict=True)
        if rez == False or len(rez) == 1:
            return "Не найден"
        return rez

    self.PROC_OTKL_TRUDOZATRAT = [85, 110]
    custom_request_c = f"""SELECT ФИО, "" as Должность, "" as Подразделение, "" as Режим,  sum(Подытог) AS "Сумм_Минут" ,  sum(Подытог_нормы) AS "Сумм_Минут_нормы" ,  sum(Минут_выгружено_ЕРП) AS "Минут_выгружено_ЕРП", 
     Пномер, Номенклатура, Номер_заказа, Номер_проекта 
    FROM (SELECT jurnal.ФИО, jurnal.Подытог, jurnal.Подытог_нормы, jurnal.Минут_выгружено_ЕРП, mk.Пномер, mk.Номенклатура, mk.Номер_заказа, mk.Номер_проекта 
     FROM jurnal INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер 
     INNER JOIN mk ON mk.Пномер = naryad.Номер_мк
     LEFT JOIN plan ON plan.Пномер = mk.НомКплан AND plan.poki = {self.place.poki}
    WHERE jurnal.Подытог <> 0 AND jurnal.Статус = 'Начат' 
    and datetime(jurnal.Дата) > datetime("{data_nach}") 
    and datetime(jurnal.Дата) <= datetime("{data_kon}")) GROUP BY ФИО;"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True, attach_dbs=(self.db_kplan))
    set_mk = set()

    cmb = self.ui.cmb_gant_tochnost_dat
    cmb.setEnabled(True)
    cmb.clear()
    cmb.addItem('')
    rez = []  # set([self.Data.ETAP_BY_FIO[_['ФИО']]['Подразделение'] for _ in rez_jur])

    list_users = den_tabel(self, data_nach)
    
    for item_mtdz in list_users:
        fiod_mtdz = item_mtdz['ФИО']
        fio_mtdz = ' '.join(fiod_mtdz.split(" ")[:3])
        dolgn_mtdz = ' '.join(fiod_mtdz.split(" ")[3:])
        if fio_mtdz not in self.DICT_EMPLOEE_FULL_WITH_DEL:
            continue
        # obj_user = CMS.Emploee_usr(fio_mtdz,self.bd_users)
        # fl_dissmissed = obj_user.is_dismissed_now(dolgn_mtdz,data_nach)
        # if fl_dissmissed:
        #    continue
        if fio_mtdz in self.Data.ETAP_BY_FIO:
            if self.Data.ETAP_BY_FIO[fio_mtdz]['Компания'] != self.place.Имя:
                continue
            if self.Data.ETAP_BY_FIO[fio_mtdz]['Подразделение'] != podrazd:
                continue
        else:
            continue
        minyt = min_za_den_tabel(self, fio_mtdz, data_nach)

        fl = False
        for i in range(len(rez_jur)):
            fio = rez_jur[i]['ФИО']
            if fio == fio_mtdz:
                fl = True
                rez_jur[i]["Табель_Минут"] = minyt
                if F.is_numeric(minyt) and minyt > 0:
                    rez_jur[i]["МЕС_час"] = str(round(rez_jur[i]["Сумм_Минут"] / 60, 3)).replace('.', ',')
                    rez_jur[i]["Соответствие_%"] = round(rez_jur[i]["Сумм_Минут"] / rez_jur[i]["Табель_Минут"] * 100)
                else:
                    rez_jur[i]["МЕС_час"] = '0'
                    rez_jur[i]["Соответствие_%"] = 0
                if rez_jur[i]["ФИО"] in self.DICT_EMPLOEE_FULL_WITH_DEL:
                    rez_jur[i]["Подразделение"] = self.DICT_EMPLOEE_FULL_WITH_DEL[rez_jur[i]["ФИО"]]["Подразделение"]
                    rez_jur[i]["Режим"] = self.DICT_EMPLOEE_FULL_WITH_DEL[rez_jur[i]["ФИО"]]["Режим"]
                    rez_jur[i]["Должность"] = self.DICT_EMPLOEE_FULL_WITH_DEL[rez_jur[i]["ФИО"]]["Должность"]
                if rez_jur[i]["Должность"] in LIST_UNCHECK_PROF:
                    rez_jur[i]["Соответствие_%"] = 100
                set_mk.add("|".join([str(rez_jur[i]["Пномер"]), rez_jur[i]["Номенклатура"], rez_jur[i]["Номер_заказа"],
                                     rez_jur[i]["Номер_проекта"]]))
                if rez_jur[i]["Сумм_Минут_нормы"] >0:
                    rez_jur[i]["Минут_выгружено_ЕРП"] = f'{rez_jur[i]["Минут_выгружено_ЕРП"]}({round(rez_jur[i]["Минут_выгружено_ЕРП"]/rez_jur[i]["Сумм_Минут_нормы"]*100)}%)'
                else:
                    rez_jur[i]["Минут_выгружено_ЕРП"] = f'0(0%)'
                rez.append({'ФИО': fio,
                            'Должность': rez_jur[i]["Должность"],
                            'Подразделение': rez_jur[i]["Подразделение"],
                            'Режим': rez_jur[i]["Режим"],
                            'Сумм_Минут': rez_jur[i]["Сумм_Минут"],
                            'Табель_Минут': rez_jur[i]["Табель_Минут"],
                            'МЕС_час': rez_jur[i]["МЕС_час"],
                            'Соответствие_%': rez_jur[i]["Соответствие_%"],
                            'Минут_выгружено_ЕРП': rez_jur[i]["Минут_выгружено_ЕРП"]}
                           )
                break
        if fl == False:
            rez.append({'ФИО': fio_mtdz,
                        'Должность': dolgn_mtdz,
                        'Подразделение': "",
                        'Режим': "",
                        'Сумм_Минут': 0,
                        'Табель_Минут': minyt,
                        'МЕС_час': 0,
                        'Соответствие_%': 0,
                        'Минут_выгружено_ЕРП':'0(0%)'}
                       )

    rez = F.list_of_dicts_to_list_of_lists(rez)

    if len(rez[0]) > 3:
        rez = F.sort_by_column_c(rez, rez[0][7])
    cmb.addItems(list(set_mk))
    return rez


@CQT.onerror
def statistic_normoweight_MK_c(self, data_nach, data_kon, etap, *args):
    minut_smen = 450

    custom_request_c = f"""SELECT jurnal.Дата, jurnal.ФИО as ФИОЖ, jurnal.Статус, jurnal.Номер_наряда, 
            naryad.Твремя, naryad.ДСЕ_ID, naryad.Операции,naryad.Опер_время, naryad.Номер_мк, naryad.Внеплан, 
naryad.ФИО  as ФИО , naryad.ФИО2  as ФИО2,  
            naryad.Фвремя, naryad.Фвремя2, naryad.Примечание, naryad.Категория_внепл, naryad.Автор, mk.Вид, 
mk.Вес, mk.Номер_заказа, mk.Номер_проекта, mk.Дата_завершения, mk.Количество FROM jurnal 
            INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер
            INNER JOIN mk ON mk.Пномер = naryad.Номер_мк
            WHERE jurnal.Статус == "Завершен"
        and datetime(mk.Дата_завершения) > datetime("{data_nach}") and datetime(mk.Дата_завершения) < datetime("{data_kon}") 
    AND naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
    if rez_jur == []:
        CQT.msgbox('Пусто')
        return
    maska = ''
    spis_mk = [['Дата_завершения', 'Номер_заказа', 'Номер_проекта', 'Номер_мк', 'Вид', 'Вес', 'Твремя', 'Факт',
                'Эффективность', 'Производительность_теор', 'Производительность_факт', 'Количество']]
    for naryad in rez_jur:
        fio_rc = self.calc_stage(naryad['ФИО'])
        if fio_rc == None:
            print(f"{naryad['ФИО']} не учтен в нарядах, не найден его РЦ")
            continue
        if fio_rc[:4] == self.ui.cmb_podrazdelenie.currentText()[:4]:
            if naryad['Внеплан'] == 0:
                bilo = naryad['Твремя']
                if self.ui.cmb_podrazdelenie.currentText()[:4] == '0103':
                    naryad['Твремя'] = ochistka_normi(self, naryad)
                print(f'уменьшилось на {round((bilo - naryad["Твремя"]) * 100 / bilo)}')

            vrem_fact = naryad['Твремя']
            if naryad['ФИОЖ'] == naryad['ФИО']:
                vrem_fact = naryad['Фвремя']
            if naryad['ФИОЖ'] == naryad['ФИО2']:
                vrem_fact = naryad['Фвремя2']
            spis_mk.append(
                [naryad['Дата_завершения'], naryad['Номер_заказа'], naryad['Номер_проекта'], naryad['Номер_мк'],
                 naryad['Вид'], naryad['Вес'],
                 naryad['Твремя'], vrem_fact,
                 '', '', '', naryad['Количество']])
    spis_mk_sort = F.sort_by_column_c(spis_mk, 'Номер_мк')
    nom_mk = ''
    nk_ves = F.num_col_by_name_in_hat_c(spis_mk_sort, 'Вес')
    nk_nom_mk = F.num_col_by_name_in_hat_c(spis_mk_sort, 'Номер_мк')
    nk_teor = F.num_col_by_name_in_hat_c(spis_mk_sort, 'Твремя')
    nk_fact = F.num_col_by_name_in_hat_c(spis_mk_sort, 'Факт')
    nk_eff = F.num_col_by_name_in_hat_c(spis_mk_sort, 'Эффективность')
    nk_prteor = F.num_col_by_name_in_hat_c(spis_mk_sort, 'Производительность_теор')
    nk_prfact = F.num_col_by_name_in_hat_c(spis_mk_sort, 'Производительность_факт')
    rez = [['Дата_завершения', 'Номер_заказа', 'Номер_проекта', 'Номер_мк', 'Вид', 'Вес', 'Твремя смен', 'Факт смен',
            'Эффективность', 'Производительность_теор кг/пост/смену', 'Производительность_факт кг/пост/смену',
            'Количество']]
    for i in range(1, len(spis_mk_sort)):
        fl_naid = False
        if spis_mk_sort[i][nk_nom_mk] != nom_mk:
            if nom_mk != '':
                tmp[nk_teor] = round(tmp[nk_teor] / 480, 3)
                tmp[nk_fact] = round(tmp[nk_fact] / 480, 3)
                tmp[nk_eff] = round(tmp[nk_teor] / tmp[nk_fact] * 100)
                if tmp[nk_teor] == 0:
                    tmp[nk_prteor] = 0
                else:
                    tmp[nk_prteor] = round(tmp[nk_ves] / tmp[nk_teor], 2) * 2
                tmp[nk_prfact] = round(tmp[nk_ves] / tmp[nk_fact], 2) * 2
                rez.append(tmp)
            nom_mk = spis_mk_sort[i][nk_nom_mk]
            tmp = spis_mk_sort[i]
        else:
            spis_mk_sort[i][nk_ves] = 0
            tmp[nk_ves] += spis_mk_sort[i][nk_ves]
            tmp[nk_teor] += spis_mk_sort[i][nk_teor]
            tmp[nk_fact] += spis_mk_sort[i][nk_fact]
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez


@CQT.onerror
def ochistka_normi(self, naryad, *args):
    name_oper = naryad['Операции'].split('|')
    time_oper = naryad['Опер_время'].split('|')
    rez = 0
    for i in range(len(name_oper)):
        if name_oper[i].split('$')[1] in self.DICT_ETAPI:
            if self.DICT_ETAPI[name_oper[i].split('$')[1]] == 'Сборка+сварка':
                rez += F.valm(time_oper[i])
        else:
            rez += F.valm(time_oper[i])
    if naryad['ФИО'] != '' and naryad['ФИО2'] != '':
        rez /= 2
    return rez


@CQT.onerror
def ispoln_pl_month_all(self, db_kplan, db_resxml, bd_naryad,db_users, DICT_PROFESSIONS, DICT_VID_RABOT,
                    from_reiting_py=False):
    def calc_count_vipusk_erp(name_poz, num_py, zp_date, num_kpl):
        if not F.is_date(zp_date, "%Y-%m-%d"):
            msg = f'!!! КПЛ№ {num_kpl}, в позиции {name_poz} Дата_заявки_на_произв не указана корректно - "{zp_date}" выпуск не учтен!!!'
            print(msg)
            if from_reiting_py:
                try:
                    bitrix = СB24.B24('chat48346')
                    bitrix.msg(msg)
                except:
                    pass
            return 0
        key = '$'.join([num_py, F.datetostr(F.strtodate(zp_date), "%Y"), name_poz])
        if key not in DICT_VIPUSK_ERP:
            return 0
        else:
            return DICT_VIPUSK_ERP[key]

    
    count_vipusk_erp = 0
    DICT_VIPUSK_ERP = dict()
    list_releases = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM releases_from_erp""", rez_dict=True)
    for item in list_releases:
        key = '$'.join([item['py_zp'], F.datetostr(F.strtodate(item['zp_date']), "%Y"), item['nomen_name']])
        if key not in DICT_VIPUSK_ERP:
            DICT_VIPUSK_ERP[key] = 0
        DICT_VIPUSK_ERP[key] += item['nomen_count']


    req = f"""SELECT plan.Пномер, '' as "Статус в тек. периоде", napravl_deyat.Псевдоним as "Направление", пл_оуп.Дата_заявки_на_произв, пл_оуп.№ERP, пл_оуп.№проекта, plan.Позиция, 
        пл_оуп.Номенклатура_ЕРП, 
        пл_оуп.Количество as "Количество_заказ",  знпр.client_order_Key as "Дата по ЗК", 
        status_poz.Имя as "Статус позиции", "" as "Примечание", 
          
          CASE WHEN пл_сб.Прогноз_дата_зав_сб != '' 
       THEN strftime('%d.%m.%Y', пл_сб.Прогноз_дата_зав_сб) 
       ELSE пл_сб.Прогноз_дата_зав_сб 
       END AS "Прогноз. дата зав.сб.", 
          
          пл_сб.Примечание_сб, 
        "" as "Всего н-смен на поз.",
        "" as "Зав_мк из" 
        FROM plan 
        INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер, пл_топ ON пл_топ.НомПл = plan.Пномер,  знпр ON знпр.s_num = пл_оуп.Пномер_ЗП ,
        napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
        status_poz ON status_poz.Пномер = plan.Статус, 
        пл_сб on пл_сб.НомПл = plan.Пномер,
        napravlenie ON napravlenie.Пномер = napravl_deyat.Направление WHERE plan.Статус IN (2,3,7)"""
    rez = CSQ.custom_request_c(db_kplan, req, rez_dict=True)


    pozs_obj = CMS.Pozitions([_['Пномер'] for _ in rez],db_kplan,bd_naryad,db_resxml,db_users)
    dict_poz_obj = pozs_obj.dict_pozs

    req_mk = f"""SELECT Пномер, Дата_завершения, НомКплан FROM mk WHERE НомКплан IN ({CSQ.prepare_list_to_tuple([_['Пномер'] for _ in rez])});"""
    list_mk_from_plan = CSQ.custom_request_c(bd_naryad, req_mk, rez_dict=True)
    list_vid_rab = CMS.get_shablon_vidov(DICT_PROFESSIONS)

    list_all_nar_by_month = CSQ.custom_request_c(bd_naryad, f"""SELECT * FROM naryad WHERE 
        naryad.Номер_мк IN ({CSQ.prepare_list_to_tuple([_['Пномер'] for _ in list_mk_from_plan])}) """,
                                                 rez_dict=True)

    if rez == []:
        print('Таблица пустая некорректная загрузка из БД')
        return rez

    set_mk_for_zam = {_['Пномер'] for _ in list_mk_from_plan}
    list_zam = CSQ.custom_request_c(bd_naryad, f"""SELECT zamech.Пномер, kod_zamech.Имя as Код, mk.НомКплан 
     FROM zamech 
     INNer join mk on mk.Пномер = zamech.МК,
     kod_zamech ON kod_zamech.Пномер = zamech.Код 
     WHERE МК IN ({CSQ.prepare_list_to_tuple(set_mk_for_zam)}); """, rez_dict=True)

    dict_napravl = dict()
    dict_res = dict()
    list_fields_for_summ = copy.deepcopy(list_vid_rab)
    
    m = ODAT.OrdersComposit(USRCNF.Config.user_config.ERP_base_name['Значение'])
    cod, data_client_order = m.get_response(doc_name='Document_ЗаказКлиента',
                               wet_filtr=f"?$filter=Статус ne 'Закрыт'&$select=Ref_Key,ДатаОтгрузки",with_cod=True)
    if cod != 200:
        CQT.msgbox('Досуп к датам 1с не обеспечен')
        data_client_order = dict()
    else:
        data_client_order = F.deploy_dict_c(data_client_order,'Ref_Key')
    month_str = F.now("%Y-%m-%d")
    data_nach, data_kon = F.start_end_dates_c(month_str, "%Y-%m-%d", 'm',format_out="%Y-%m-%d")
    plan = CMS.Month_plan(data_nach, db_kplan)
    list_pnums_plan = {}
    if plan.data != None:
        list_pnums_plan = {_ for _ in plan.data.keys()}




    for i in range(len(rez)):
        dict_vip_rab = {_: 0 for _ in list_vid_rab}
        count_mk = 0
        count_zakr_mk = 0
        count_control_oper_mk = 0
        zav_control_oper_mk = 0
        poz = dict_poz_obj[rez[i]['Пномер']]
        if rez[i]["Пномер"] in list_pnums_plan:
            rez[i]["Статус в тек. периоде"] = 'В палне'


        if rez[i]["Дата по ЗК"] != '':
            if rez[i]["Дата по ЗК"] in data_client_order:
                rez[i]["Дата по ЗК"] = data_client_order[rez[i]["Дата по ЗК"]]
                if F.is_date(rez[i]["Дата по ЗК"],"%Y-%m-%dT%H:%M:%S"):
                    rez[i]["Дата по ЗК"] = F.datetostr(F.strtodate(rez[i]["Дата по ЗК"],"%Y-%m-%dT%H:%M:%S"), "%d.%m.%Y" )
        
        
        for mk_from_plan in list_mk_from_plan:
            if mk_from_plan['НомКплан'] == rez[i]['Пномер']:
                if mk_from_plan['Пномер'] not in dict_res:
                    mk_obj = CMS.Marshrut_cards(mk_from_plan['Пномер'], bd_naryad, db_resxml, True)
                    dict_res[mk_from_plan['Пномер']] = mk_obj.res
                res = dict_res[mk_from_plan['Пномер']]
                for dse_res in res:
                    for oper in dse_res['Операции']:
                        if oper['Опер_код'] in ("0220", "0250", "0386", "0230", "0251"):
                            count_control_oper_mk += 1
                            if 'Закрыто,шт.' in oper:
                                if oper['Закрыто,шт.'] >= dse_res['Количество']:
                                    zav_control_oper_mk += 1

                count_mk += 1
                if mk_from_plan['Дата_завершения'] != '':
                    count_zakr_mk += 1
                for nar in list_all_nar_by_month:
                    if nar['Номер_мк'] == mk_from_plan['Пномер']:
                        nar_obj = CMS.Naryads(nar, bd_naryad)
                        if nar_obj.row == []:
                            continue
                        for dse in nar_obj.params:
                            vid_r = dse['Виды_работ']

                            if vid_r == '':
                                for dse_res in res:
                                    if dse_res['Номерпп'] == dse['ДСЕ_ID']:
                                        for oper in dse_res['Операции']:
                                            if oper['Опер_номер'] == dse['Операции_номер']:
                                                prof = oper['Опер_профессия_код']
                                                if prof in DICT_PROFESSIONS:
                                                    nick = DICT_PROFESSIONS[prof]['nick_name']
                                                    dict_vip_rab[nick] += dse[
                                                        'Норма_времени_пооперационно']  # nar_obj.Твремя * nar_obj.count_users()
                                                break
                                        break
                            else:
                                if vid_r in DICT_VID_RABOT:
                                    nick = DICT_VID_RABOT[vid_r]['nick_name']
                                    dict_vip_rab[nick] += dse[
                                        'Норма_времени_пооперационно']  # nar_obj.Твремя * nar_obj.count_users()

        rez[i]["Зав_мк из"] = f'{count_zakr_mk}/{count_mk}'
        min_count = rez[i]['Количество_заказ']

        dict_napravl[rez[i]['Пномер']] = rez[i]['Направление']
        rez[i]["Подытог(по МК)%"] = '0'

        for vid_r in list_vid_rab:
            ostatok_n_sm = 0
            name_etap = self.Data.DICT_GROUP_VID_RAB_FOR_PLAN_NICKNAME[vid_r]['name']
            if name_etap in poz.row_time_etap:
                plan_hour = poz.row_time_etap[name_etap]
            else:
                plan_hour = poz.row_time_add_etap[name_etap]
            
            rez[i][vid_r] = f"""{round(dict_vip_rab[vid_r] / 480, 2)}/{round(plan_hour/8, 2)}"""

        rez[i]["Итог(н_см)%"] = '0'
        rez[i]["Зав_ОТК"] = f'{zav_control_oper_mk}/{count_control_oper_mk}'



        SET_USED_ETAPS = {
                        'Нчас_заг',
                        'Нчас_упаковки',
                        'Нчас_мехобр',
                        'Нчас_покр',
                        'Нчас_сб',
                        'Нчас_св',
                        'Нчас_слсб',
                        'Нчас_зач',}
        rez[i]["Всего н-смен на поз."] = round(sum([v/8 for k,v in  poz.row_time_etap.items() if  k.split('.')[-1] in SET_USED_ETAPS]), 2)
        


        count_vipusk_erp = calc_count_vipusk_erp(rez[i]['Номенклатура_ЕРП'], rez[i]['№ERP'],
                                                 rez[i]['Дата_заявки_на_произв'], rez[i]['Пномер'])
        rez[i]["Выпуски"] = f"{count_vipusk_erp}/{rez[i]['Количество_заказ']}"

    count_poz = 0
    zav_poz = 0
    for i in range(len(rez)):
        itog = 0
        isp_summ = 0
        count_summ = 0
        itog_ed = 0
        for field in list_fields_for_summ:
            if '_н_см' in field:
                if '/' in rez[i][field]:
                    isp, count = rez[i][field].split("/")
                    isp_summ += F.valm(isp)
                    count_summ += F.valm(count)
        itog = 0
        if count_summ > 0:
            itog = round(isp_summ / count_summ * 100)
        if itog > 0:
            rez[i]["Итог(н_см)%"] = str(itog)
        if '/' in rez[i]["Зав_мк из"]:
            isp, count = rez[i]["Зав_мк из"].split("/")
            if F.valm(count) > 0:
                rez[i]["Подытог(по МК)%"] = round(F.valm(isp) / F.valm(count) * 100)
        if rez[i]['Статус позиции'] != '':
            if rez[i]['Статус позиции'] == 'Завершена':
                zav_poz += F.valm(rez[i]['Количество_заказ'])
            count_poz += F.valm(rez[i]['Количество_заказ'])
    percent = 0
    if F.is_numeric(count_poz) and F.valm(count_poz) > 0:
        percent = round(zav_poz / count_poz * 100)
    rez[-1]['Статус позиции'] = str(percent) + " %"

    for i in range(len(rez)):
        dict_zam = dict()
        rez[i]['Замечания'] = ''
        if rez[i]['Пномер'] != '':
            nom_kpl = int(rez[i]['Пномер'])
            for zam in list_zam:
                if zam['НомКплан'] == nom_kpl:
                    if zam['Код'] not in dict_zam:
                        dict_zam[zam['Код']] = 0
                    dict_zam[zam['Код']] += 1
            rez[i]['Замечания'] = pprint.pformat(dict_zam)

    rez.append({_: '' for _ in rez[0]})
    rez[-1]["Всего н-смен на поз."] = "ИТОГ:"

    itog_percent = 0
    list_fields_for_summ.append('Зав_мк из')
    list_fields_for_summ.append('Зав_ОТК')
    list_fields_for_summ.append('Выпуски')
    for field in list_fields_for_summ:
        isp_summ = 0
        count_summ = 0
        for i in range(0, len(rez) - 1):
            if field in rez[i] and isinstance(rez[i][field], str) and '/' in rez[i][field]:
                isp, count = rez[i][field].split("/")
                isp_summ += F.valm(isp)
                count_summ += F.valm(count)
        rez[-1][field] = f"{round(isp_summ, 2)}/{round(count_summ, 2)}"
    return rez


@CQT.onerror
def ispoln_pl_month(db_kplan, db_resxml, bd_naryad, DICT_PROFESSIONS, DICT_VID_RABOT, month_str: str,from_reiting_py=False):
    def calc_count_vipusk_erp(name_poz, num_py, zp_date,num_kpl):
        if not F.is_date(zp_date,"%Y-%m-%d"):
            msg = f'!!! КПЛ№ {num_kpl}, в позиции {name_poz} Дата_заявки_на_произв не указана корректно - "{zp_date}" выпуск не учтен!!!'
            print(msg)
            if from_reiting_py:
                try:
                    bitrix = СB24.B24('chat48346')
                    bitrix.msg(msg)
                except:
                    pass
            return 0
        key = '$'.join([num_py, F.datetostr(F.strtodate(zp_date), "%Y"), name_poz])
        if key not in DICT_VIPUSK_ERP:
            return 0
        else:
            return DICT_VIPUSK_ERP[key]

    if not F.is_date(month_str, "%Y-%m-%d"):
        print(f'{month_str} не дата %Y-%m-%d')
        return
    data_nach, data_kon = F.start_end_dates_c(month_str, "%Y-%m-%d", 'm')

    count_vipusk_erp = 0
    DICT_VIPUSK_ERP = dict()
    list_releases = CSQ.custom_request_c(db_kplan, f"""SELECT * FROM releases_from_erp WHERE 
     datetime(date_rel) >= datetime("{data_nach}") and datetime(date_rel) < datetime("{data_kon}")""", rez_dict=True)
    for item in list_releases:
        key = '$'.join([item['py_zp'], F.datetostr(F.strtodate(item['zp_date']), "%Y"), item['nomen_name']])
        if key not in DICT_VIPUSK_ERP:
            DICT_VIPUSK_ERP[key] = 0
        DICT_VIPUSK_ERP[key] += item['nomen_count']
    list_pnums = []
    plan = CMS.Month_plan(month_str, db_kplan)
    if  plan.data == None:
        print(f'!!!!!! План за {month_str} не обнаружен')
        return []
    list_pnums = [_ for _ in plan.data.keys() if
                  'Тип' not in plan.data[_] or ('Тип' in plan.data[_] and plan.data[_]['Тип'] != 'Внеплан')]
    list_pnums_vnepl_pl = [_ for _ in plan.data.keys() if 'Тип' in plan.data[_] and plan.data[_]['Тип'] == 'Внеплан']
    req = f"""SELECT plan.Пномер,  "План" as Статус, napravl_deyat.Псевдоним as "Направление", пл_оуп.Дата_заявки_на_произв, пл_оуп.№ERP, пл_оуп.№проекта, plan.Позиция, 
        пл_оуп.Номенклатура_ЕРП, 
        пл_топ.Спецификация_ЕРП, пл_топ.Спецификация_код_ЕРП, "Штука" as "Ед. изм.",
        пл_оуп.Количество as "Количество_заказ", "" as "Количество", "" as "Дата", "" as "Статус РС" , 
        status_poz.Имя as "Статус позиции", "" as "Примечание", пл_сб.Прогноз_дата_зав_сб, пл_сб.Примечание_сб, "" as "Всего н-смен на поз.","" as "Зав_мк из" FROM plan 
        INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер, пл_топ ON пл_топ.НомПл = plan.Пномер,  
        napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
        status_poz ON status_poz.Пномер = plan.Статус, 
        пл_сб on пл_сб.НомПл = plan.Пномер,
        napravlenie ON napravlenie.Пномер = napravl_deyat.Направление WHERE plan.Пномер IN 
             ({CSQ.prepare_list_to_tuple(list_pnums)})"""
    rez = CSQ.custom_request_c(db_kplan, req, rez_dict=True)
    if len(list_pnums_vnepl_pl):
        req = f"""SELECT plan.Пномер,  "Внеплан" as Статус, napravl_deyat.Псевдоним as "Направление", пл_оуп.Дата_заявки_на_произв, пл_оуп.№ERP, пл_оуп.№проекта, plan.Позиция, 
            пл_оуп.Номенклатура_ЕРП, 
            пл_топ.Спецификация_ЕРП, пл_топ.Спецификация_код_ЕРП, "Штука" as "Ед. изм.",
            пл_оуп.Количество as "Количество_заказ", "" as "Количество", "" as "Дата", "" as "Статус РС" , 
            status_poz.Имя as "Статус позиции", "" as "Примечание", пл_сб.Прогноз_дата_зав_сб, пл_сб.Примечание_сб, "" as "Всего н-смен на поз.","" as "Зав_мк из" FROM plan 
            INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер, пл_топ ON пл_топ.НомПл = plan.Пномер,  
            napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
            status_poz ON status_poz.Пномер = plan.Статус, 
            пл_сб on пл_сб.НомПл = plan.Пномер,
            napravlenie ON napravlenie.Пномер = napravl_deyat.Направление WHERE plan.Пномер IN 
                 ({CSQ.prepare_list_to_tuple(list_pnums_vnepl_pl)})"""
        rez_vnepl_pl = CSQ.custom_request_c(db_kplan, req, rez_dict=True)
        for item in rez_vnepl_pl:
            rez.append(item)

    req_mk = f"""SELECT Пномер, Дата_завершения, НомКплан FROM mk WHERE НомКплан IN ({CSQ.prepare_list_to_tuple(list_pnums)});"""
    list_mk_from_plan = CSQ.custom_request_c(bd_naryad, req_mk, rez_dict=True)
    list_vid_rab = CMS.get_shablon_vidov(DICT_PROFESSIONS)

    list_all_nar_by_month = CSQ.custom_request_c(bd_naryad, f"""SELECT * FROM naryad WHERE 
        date(Подтвержд_вып_дата) >= datetime("{data_nach}") and date(Подтвержд_вып_дата) < datetime("{data_kon}")""",
                                                 rez_dict=True)

    if rez == []:
        print('Таблица пустая некорректная загрузка из БД')
        return rez

    set_all_mk_by_month = {_['Номер_мк'] for _ in list_all_nar_by_month}
    set_mk_fom_plan = {_['Пномер'] for _ in list_mk_from_plan}
    set_mk_wo_plan = set_all_mk_by_month - set_mk_fom_plan

    req = f"""SELECT НомКплан FROM mk WHERE mk.Пномер IN 
     ({CSQ.prepare_list_to_tuple(set_mk_wo_plan)});"""
    list_vnepl_kpl = CSQ.custom_request_c(bd_naryad, req, hat_c=False, one_column=True)
    set_vnepl_kpl = set(list_vnepl_kpl)
    req = f"""SELECT plan.Пномер, "Внеплан" as Статус, napravl_deyat.Псевдоним as "Направление", пл_оуп.Дата_заявки_на_произв, пл_оуп.№ERP, пл_оуп.№проекта, plan.Позиция, 
            пл_оуп.Номенклатура_ЕРП, 
            пл_топ.Спецификация_ЕРП, пл_топ.Спецификация_код_ЕРП, "Штука" as "Ед. изм.",
            пл_оуп.Количество as "Количество_заказ", "" as "Количество", "" as "Дата", "" as "Статус РС" , 
            status_poz.Имя as "Статус позиции", "" as "Примечание", пл_сб.Прогноз_дата_зав_сб, пл_сб.Примечание_сб, "" as "Всего н-смен на поз.","" as "Зав_мк из" FROM plan 
            INNER JOIN пл_оуп ON пл_оуп.НомПл = plan.Пномер, пл_топ ON пл_топ.НомПл = plan.Пномер,  
            napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
            status_poz ON status_poz.Пномер = plan.Статус, 
            пл_сб on пл_сб.НомПл = plan.Пномер,
            napravlenie ON napravlenie.Пномер = napravl_deyat.Направление WHERE plan.Пномер IN 
                 ({CSQ.prepare_list_to_tuple(set_vnepl_kpl)})"""
    rez_vnepl = CSQ.custom_request_c(db_kplan, req, rez_dict=True)
    for item in rez_vnepl:
        rez.append(item)

    req_mk = f"""SELECT Пномер, Дата_завершения, НомКплан FROM mk WHERE НомКплан IN ({CSQ.prepare_list_to_tuple([_['Пномер'] for _ in rez])});"""
    list_mk_from_plan = CSQ.custom_request_c(bd_naryad, req_mk, rez_dict=True)

    set_mk_for_zam = {_['Пномер'] for _ in list_mk_from_plan}
    list_zam = CSQ.custom_request_c(bd_naryad, f"""SELECT zamech.Пномер, kod_zamech.Имя as Код, mk.НомКплан 
     FROM zamech 
     INNer join mk on mk.Пномер = zamech.МК,
     kod_zamech ON kod_zamech.Пномер = zamech.Код 
     WHERE МК IN ({CSQ.prepare_list_to_tuple(set_mk_for_zam)}); """, rez_dict=True)

    dict_napravl = dict()
    dict_res = dict()
    list_fields_for_summ = copy.deepcopy(list_vid_rab)

    for i in range(len(rez)):
        dict_vip_rab = {_: 0 for _ in list_vid_rab}
        count_mk = 0
        count_zakr_mk = 0
        count_control_oper_mk = 0
        zav_control_oper_mk = 0

        for mk_from_plan in list_mk_from_plan:
            if mk_from_plan['НомКплан'] == rez[i]['Пномер']:
                if mk_from_plan['Пномер'] not in dict_res:
                    mk_obj = CMS.Marshrut_cards(mk_from_plan['Пномер'], bd_naryad, db_resxml, True)
                    dict_res[mk_from_plan['Пномер']] = mk_obj.res
                res = dict_res[mk_from_plan['Пномер']]
                for dse_res in res:
                    for oper in dse_res['Операции']:
                        if oper['Опер_код'] in ("0220", "0250", "0386", "0230", "0251"):
                            count_control_oper_mk += 1
                            if 'Закрыто,шт.' in oper:
                                if oper['Закрыто,шт.'] >= dse_res['Количество']:
                                    zav_control_oper_mk += 1

                count_mk += 1
                if mk_from_plan['Дата_завершения'] != '':
                    count_zakr_mk += 1
                for nar in list_all_nar_by_month:
                    if nar['Номер_мк'] == mk_from_plan['Пномер']:
                        nar_obj = CMS.Naryads(nar, bd_naryad)
                        if nar_obj.row == []:
                            continue
                        for dse in nar_obj.params:
                            vid_r = dse['Виды_работ']

                            if vid_r == '':
                                for dse_res in res:
                                    if dse_res['Номерпп'] == dse['ДСЕ_ID']:
                                        for oper in dse_res['Операции']:
                                            if oper['Опер_номер'] == dse['Операции_номер']:
                                                prof = oper['Опер_профессия_код']
                                                if prof in DICT_PROFESSIONS:
                                                    nick = DICT_PROFESSIONS[prof]['nick_name']
                                                    dict_vip_rab[nick] += dse[
                                                        'Норма_времени_пооперационно']  # nar_obj.Твремя * nar_obj.count_users()
                                                break
                                        break
                            else:
                                if vid_r in DICT_VID_RABOT:
                                    nick = DICT_VID_RABOT[vid_r]['nick_name']
                                    dict_vip_rab[nick] += dse[
                                        'Норма_времени_пооперационно']  # nar_obj.Твремя * nar_obj.count_users()

        rez[i]["Зав_мк из"] = f'{count_zakr_mk}/{count_mk}'
        min_count = rez[i]['Количество_заказ']
        norma_poz = 0
        dict_napravl[rez[i]['Пномер']] = rez[i]['Направление']
        rez[i]["Подытог(по МК)%"] = '0'

        for vid_r in list_vid_rab:
            if rez[i]['Пномер'] not in plan.data:
                rez[i][vid_r] = f"""{round(dict_vip_rab[vid_r] / 480, 2)}/0"""
            else:
                ostatok_n_sm = 0
                if vid_r  in plan.data[rez[i]['Пномер']]['Группы_работ']:
                    
                    if rez[i]['Пномер'] in plan.data and plan.data[rez[i]['Пномер']]['Группы_работ'][vid_r][
                        'Норма_н_см'] > 0:
                        if plan.data[rez[i]['Пномер']]['Группы_работ'][vid_r]['Остаток_шт'] < min_count:
                            min_count = plan.data[rez[i]['Пномер']]['Группы_работ'][vid_r]['Остаток_шт']
                        norma_poz += plan.data[rez[i]['Пномер']]['Группы_работ'][vid_r]['Норма_н_см']
                        ostatok_n_sm = plan.data[rez[i]['Пномер']]['Группы_работ'][vid_r]['Остаток_н_см']
                rez[i][vid_r] = f"""{round(dict_vip_rab[vid_r] / 480, 2)}/{round(ostatok_n_sm, 2)}"""

        rez[i]["Итог(н_см)%"] = '0'
        rez[i]["Зав_ОТК"] = f'{zav_control_oper_mk}/{count_control_oper_mk}'

        if rez[i]["Спецификация_код_ЕРП"] != '':
            rez[i]["Статус РС"] = "Создана"
        rez[i]["Дата"] = ''
        if rez[i]['Пномер'] in plan.data:
            rez[i]["Дата"] = plan.data[rez[i]['Пномер']]['max_date']
        rez[i]["Всего н-смен на поз."] = round(norma_poz, 2)

        rez[i]['Количество'] = 0
        if rez[i]['Пномер'] in plan.data:
            if 'Количество' not in plan.data[rez[i]['Пномер']] or plan.data[rez[i]['Пномер']]['Количество'] == -1:
                plan.data[rez[i]['Пномер']]['Количество'] = F.round_up(min_count)
            rez[i]['Количество'] = plan.data[rez[i]['Пномер']]['Количество']
            if 'Примечание' in plan.data[rez[i]['Пномер']]:
                rez[i]['Примечание'] = plan.data[rez[i]['Пномер']]['Примечание']
        count_vipusk_erp = calc_count_vipusk_erp(rez[i]['Номенклатура_ЕРП'], rez[i]['№ERP'],
                                                 rez[i]['Дата_заявки_на_произв'],rez[i]['Пномер'])
        rez[i]["Выпуски"] = f'{count_vipusk_erp}/{rez[i]["Количество"]}'

    count_poz = 0
    zav_poz = 0
    for i in range(len(rez)):
        itog = 0
        isp_summ = 0
        count_summ = 0
        itog_ed = 0
        for field in list_fields_for_summ:
            if '_н_см' in field:
                if '/' in rez[i][field]:
                    isp, count = rez[i][field].split("/")
                    isp_summ += F.valm(isp)
                    count_summ += F.valm(count)
        itog = 0
        if count_summ > 0:
            itog = round(isp_summ / count_summ * 100)
        if itog > 0:
            rez[i]["Итог(н_см)%"] = str(itog)
        if '/' in rez[i]["Зав_мк из"]:
            isp, count = rez[i]["Зав_мк из"].split("/")
            if F.valm(count) > 0:
                rez[i]["Подытог(по МК)%"] = round(F.valm(isp) / F.valm(count) * 100)
        if rez[i]['Статус позиции'] != '':
            if rez[i]['Статус позиции'] == 'Завершена':
                zav_poz += F.valm(rez[i]['Количество'])
            count_poz += F.valm(rez[i]['Количество'])
    percent = 0
    if F.is_numeric(count_poz) and F.valm(count_poz) > 0:
        percent = round(zav_poz / count_poz * 100)
    rez[-1]['Статус позиции'] = str(percent) + " %"

    for i in range(len(rez)):
        dict_zam = dict()
        rez[i]['Замечания'] = ''
        if rez[i]['Пномер'] != '':
            nom_kpl = int(rez[i]['Пномер'])
            for zam in list_zam:
                if zam['НомКплан'] == nom_kpl:
                    if zam['Код'] not in dict_zam:
                        dict_zam[zam['Код']] = 0
                    dict_zam[zam['Код']] += 1
            rez[i]['Замечания'] = pprint.pformat(dict_zam)

    rez.append({_: '' for _ in rez[0]})
    rez[-1]["Всего н-смен на поз."] = "ПЛАН:"
    rez.append({_: '' for _ in rez[0]})
    list_fields_for_summ = copy.deepcopy(list_fields_for_summ)
    list_fields_for_summ.append("Зав_мк из")
    list_fields_for_summ.append("Зав_ОТК")
    list_fields_for_summ.append("Выпуски")
    itog_percent = 0
    # list_fields_for_summ_int = ["Итог(н_см)%"]
    for field in list_fields_for_summ:
        isp_summ = 0
        count_summ = 0
        for i in range(0, len(rez) - 1):
            if rez[i]['Статус'] != 'План':
                continue
            if field in rez[i] and isinstance(rez[i][field], str) and '/' in rez[i][field]:
                isp, count = rez[i][field].split("/")
                isp_summ += F.valm(isp)
                count_summ += F.valm(count)
        rez[-1][field] = f"{round(isp_summ, 2)}/{round(count_summ, 2)}"

    rez.append({_: '' for _ in rez[0]})
    rez[-1]["Всего н-смен на поз."] = "ВНЕПЛАН:"
    rez.append({_: '' for _ in rez[0]})
    itog_percent = 0

    for field in list_fields_for_summ:
        isp_summ = 0
        count_summ = 0
        for i in range(0, len(rez) - 1):
            if rez[i]['Статус'] != 'Внеплан':
                continue
            if field in rez[i] and isinstance(rez[i][field], str) and '/' in rez[i][field]:
                isp, count = rez[i][field].split("/")
                isp_summ += F.valm(isp)
                # count_summ += F.valm(count)
        rez[-1][field] = f"{round(isp_summ, 2)}/{round(count_summ, 2)}"

    rez.append({_: '' for _ in rez[0]})
    rez[-1]["Всего н-смен на поз."] = "ИТОГ:"
    rez.append({_: '' for _ in rez[0]})
    itog_percent = 0

    for field in list_fields_for_summ:
        isp_summ = 0
        count_summ = 0
        for i in range(0, len(rez) - 1):
            if rez[i]['Статус'] == '':
                continue
            if field in rez[i] and isinstance(rez[i][field], str) and '/' in rez[i][field]:
                isp, count = rez[i][field].split("/")
                isp_summ += F.valm(isp)
                if rez[i]['Статус'] == 'План':
                    count_summ += F.valm(count)
        rez[-1][field] = f"{round(isp_summ, 2)}/{round(count_summ, 2)}"

    return rez


def raspredelenie_po_naprfvleniam_proc(self, data_nach, data_kon):
    custom_request_c = f'''SELECT naryad.Пномер
, naryad.Дата       
, naryad.Автор      
, naryad.Номер_мк   
, naryad.Внеплан    
, naryad.Задание    
, naryad.Компл_ФИО  
, naryad.Компл_Дата 
, naryad.Компл_номер_тара
, naryad.Компл_адрес
, naryad.ФИО        
, naryad.Фвремя     
, naryad.ФИО2       
, naryad.Фвремя2    
, naryad.Твремя     
, naryad.ДСЕ        
, naryad.ДСЕ_ID     
, naryad.Операции   
, naryad.Опер_время 
, naryad.Опер_колво 
, naryad.Примечание 
, naryad.Коэфф_сложности
, naryad.Подтвержд_вып
, naryad.Категория_внепл
, naryad.Виды_работ 
, naryad.Номер_замечания_журнал
, naryad.Подтвержд_вып_дата
, naryad.Подтвержд_вып_фио
, naryad.Профессии  
, naryad.РЦ_наряд   

, mk.Дата as mk_data
, mk.Статус
, mk.Номенклатура
, mk.Номер_заказа
, mk.Номер_проекта
, mk.Вид
, mk.Примечание as mk_primech
, mk.Основание
, mk.Прогресс
, mk.Приоритет
, mk.Направление
, mk.Вес
, mk.xml
, mk.Количество
, mk.Статус_ЧПУ
, mk.Ресурсная
, mk.Дата_завершения
, mk.Коэф_парал
, mk.Обеспечение
, mk.Место
, mk.Искл_план_рм
, mk.Тип
, mk.Ресурсная_дата
, mk.ФИО as mk_fio
, mk.НомКплан
, mk.check_execute_opers 
, '' as Направление_деятельности 
, '' as dolya  
, zagot.Вес_по_рес 
 FROM naryad INNER JOIN mk 
    ON mk.Пномер = naryad.Номер_мк, 
   zagot ON mk.Пномер = zagot.Ном_МК
     WHERE datetime(Подтвержд_вып_дата) > datetime("{data_nach}") 
    and datetime(Подтвержд_вып_дата) < datetime("{data_kon}") 
        AND Внеплан != 1 AND Подтвержд_вып == 1'''
    if F.existence_file_c('rez_jur_raspredelenie_po_naprfvleniam_proc'):
        rez_jur = F.load_file_pickle('rez_jur_raspredelenie_po_naprfvleniam_proc')
    else:
        rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
        F.save_file_pickle('rez_jur_raspredelenie_po_naprfvleniam_proc', rez_jur)

    query_kplan = f"""SELECT plan.МК, napravl_deyat.Имя, пл_ко.Вес_КД FROM plan INNER JOIN 
napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности, 
пл_ко ON пл_ко.НомПл = plan.Пномер
"""

    if F.existence_file_c('rez_kplan_raspredelenie_po_naprfvleniam_proc'):
        rez_kplan = F.load_file_pickle('rez_kplan_raspredelenie_po_naprfvleniam_proc')
    else:
        rez_kplan = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, query_kplan, hat_c=True, rez_dict=True), 'МК')
        F.save_file_pickle('rez_kplan_raspredelenie_po_naprfvleniam_proc', rez_kplan)

    rez_jur_2 = []
    dict_mk_summ_tdz = dict()
    for i in range(len(rez_jur)):
        napr_d = '?'
        rez_jur[i]['Вес'] = rez_jur[i]['Вес_по_рес']
        if rez_jur[i]['Номер_мк'] in rez_kplan:
            napr_d = rez_kplan[rez_jur[i]['Номер_мк']]['Имя']
            ves_kd = F.valm(rez_kplan[rez_jur[i]['Номер_мк']]['Вес_КД'])
            ves_xml = F.valm(rez_jur[i]['xml'])
            if ves_xml > ves_kd:
                ves_kd = ves_xml
            rez_jur[i]['Вес'] = ves_kd
        else:

            rez_jur[i]['Вес'] = F.valm(rez_jur[i]['xml'])
        rez_jur[i]['Направление_деятельности'] = napr_d

        rc = None
        if rez_jur[i]['ФИО'] != '':
            rc = self.calc_stage(rez_jur[i]['ФИО'])
        else:
            if rez_jur[i]['ФИО2'] != '':
                rc = self.calc_stage(rez_jur[i]['ФИО2'])
        if rc != None:
            if rc[:4] == '0103':
                rez_jur_2.append(rez_jur[i])

                if rez_jur[i]['Номер_мк'] not in dict_mk_summ_tdz:
                    dict_mk_summ_tdz[rez_jur[i]['Номер_мк']] = 0
                dict_mk_summ_tdz[rez_jur[i]['Номер_мк']] += F.valm(rez_jur[i]['Фвремя'])
                dict_mk_summ_tdz[rez_jur[i]['Номер_мк']] += F.valm(rez_jur[i]['Фвремя2'])

    for i in range(len(rez_jur_2)):
        rez_jur_2[i]['dolya'] = (F.valm(rez_jur_2[i]['Фвремя']) + F.valm(rez_jur_2[i]['Фвремя2'])) / \
                                dict_mk_summ_tdz[rez_jur_2[i]['Номер_мк']] * rez_jur_2[i]['Вес']

    rez_dict = {'План': dict(), 'Внеплан': dict(), }

    set_month = set()

    for item in rez_jur_2:
        month = F.datetostr(F.strtodate(item['Подтвержд_вып_дата']), '%m.%Y') + "(" + \
                F.month_rus_from_date(F.strtodate(item['Подтвержд_вып_дата']), rodit_padej=False) + ")"

        set_month.add(month)
        napr = item['Направление']
        napr_d = item['Направление_деятельности']
        if napr_d == '?':
            napr_d = napr
        napr_d = napr_d + "$" + napr
        ves = item['dolya']
        nchas = F.valm(item['Фвремя']) + F.valm(item['Фвремя2'])
        vneplan = item['Внеплан']

        if vneplan == 0:
            pl_vnpl = 'План'

        else:
            pl_vnpl = 'Внеплан'

        if napr_d not in rez_dict[pl_vnpl]:
            rez_dict[pl_vnpl][napr_d] = dict()

        if month not in rez_dict[pl_vnpl][napr_d]:
            rez_dict[pl_vnpl][napr_d][month] = dict()

        if 'Вес' not in rez_dict[pl_vnpl][napr_d][month]:
            rez_dict[pl_vnpl][napr_d][month]['Вес'] = 0
            rez_dict[pl_vnpl][napr_d][month]['Нчас'] = 0

        rez_dict[pl_vnpl][napr_d][month]['Вес'] += ves
        rez_dict[pl_vnpl][napr_d][month]['Нчас'] += nchas

    list_vid = ['План', 'Внеплан']
    rez_list_plan = [['Направление_д', 'Вид', 'План']]
    for month in sorted(list(set_month)):
        rez_list_plan[0].append(month + '_Нчас')
        rez_list_plan[0].append(month + '_кг')

    for vid in list_vid:
        for napr in rez_dict[vid]:
            tmp = [napr.split('$')[0], napr.split('$')[1], vid]
            for month in rez_list_plan[0][3:]:
                if '_кг' in month:
                    continue
                month_str = month.split('_')[0]
                if month_str in rez_dict[vid][napr]:
                    tmp.append(round(rez_dict[vid][napr][month_str]['Нчас'] / 60, 2))
                    tmp.append(round(rez_dict[vid][napr][month_str]['Вес'], 2))
                else:
                    tmp.append(0)
                    tmp.append(0)
            rez_list_plan.append(tmp)
    rez_list_plan.append(['' for _ in rez_list_plan[0]])
    return rez_list_plan


@CQT.onerror
def virabotka_ceha(self, data_nach, data_kon, etap, f_napravl=False, *args):
    # dict_napr[napr] = F.list_of_lists_to_dict_of_dicts(vneplan_po_napravl(self, data_nach, data_kon, napr, generate_graf= False),
    #                                                'Месяц')
    # dict_napr["ПТ"] = F.list_of_lists_to_dict_of_dicts(vneplan_po_napravl(self, data_nach, data_kon, napr, generate_graf= False ),
    #                                                   'Месяц')
    vid = 'Все'

    rez, list_vneplan_po_napravl = get_plan_vneplan_data(self, data_nach, data_kon, vid, etap)
    if list_vneplan_po_napravl == None:
        return
    rez_dict = dict()
    shablon_line = {'Вид': '',
                    "План, н.-см.": 0,
                    "Внеплан,н. -см.": 0,
                    'Н.-см.(Доля %)': '',
                    "Завершено, кг.": 0,
                    'Проекты в работе': set(),
                    'МК завершено': set()
                    }
    for item in list_vneplan_po_napravl:
        nar = item[4]
        napr = nar['Направление']
        if napr not in rez_dict:
            rez_dict[napr] = copy.deepcopy(shablon_line)
            rez_dict[napr]['Вид'] = napr
        if item[0] == 'план':
            rez_dict[napr]["План, н.-см."] += item[3]
        else:
            rez_dict[napr]["Внеплан,н. -см."] += item[3]

    # =======================================================================================================================
    custom_request_c = f"""SELECT Дата_завершения,Вид,Направление,Вес,Номер_проекта,Номер_заказа,Пномер FROM mk WHERE Статус == "Закрыта"
    and datetime(Дата_завершения) > datetime("{data_nach}") and datetime(Дата_завершения) < datetime("{data_kon}")"""
    rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)
    for mk in rez_mk:
        napr = mk['Направление']
        if napr not in rez_dict:
            rez_dict[napr] = copy.deepcopy(shablon_line)
        rez_dict[napr]["Завершено, кг."] += mk['Вес']
        rez_dict[napr]['Проекты в работе'].add(mk['Номер_проекта'] + "$" + mk['Номер_заказа'])
        rez_dict[napr]['МК завершено'].add(str(mk['Пномер']) + f'({round(mk["Вес"])})')
    # =======================================================================================================================

    # ====ПОДЫТОГ===================================================================================================================

    summ_normpsmen = 0
    summ_kg = 0
    srednaya_proizvodit = 0
    summ_vneplan_normosmen = 0
    summ_vneplan_kg = 0
    summ_zaversheno = 0
    chet = 0
    summ_dolya = 0

    for napr in rez_dict.keys():
        rez_dict[napr]["План, н.-см."] = round(rez_dict[napr]["План, н.-см."] / 480, 2)
        summ_normpsmen += rez_dict[napr]["План, н.-см."]
        rez_dict[napr]["Внеплан,н. -см."] = round(rez_dict[napr]["Внеплан,н. -см."] / 480, 2)
        summ_vneplan_normosmen += rez_dict[napr]["Внеплан,н. -см."]
        rez_dict[napr]['Завершено, кг.'] = round(rez_dict[napr]['Завершено, кг.'])
        summ_zaversheno += rez_dict[napr]['Завершено, кг.']

        rez_dict[napr]['Н.-см.(Доля %)'] = \
            rez_dict[napr]["План, н.-см."] + \
            rez_dict[napr]["Внеплан,н. -см."]
        summ_dolya += rez_dict[napr]['Н.-см.(Доля %)']

        rez_dict[napr]['Проекты в работе'] = '; '.join(rez_dict[napr]['Проекты в работе'])
        rez_dict[napr]['МК завершено'] = '; '.join(rez_dict[napr]['МК завершено'])

    rez_spis = F.list_of_dicts_to_list_of_lists([j for i, j in F.dict_to_list(rez_dict)])
    if summ_dolya == 0:
        for i in range(1, len(rez_spis)):
            rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Н.-см.(Доля %)')] = \
                str(rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Н.-см.(Доля %)')])
    else:
        for i in range(1, len(rez_spis)):
            rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Н.-см.(Доля %)')] = \
                str(round(rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Н.-см.(Доля %)')], 2)) + \
                f'({round(rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, "Н.-см.(Доля %)")] / summ_dolya * 100)}%)'

    tmp_itog = ['Подытог', round(summ_normpsmen), round(summ_vneplan_normosmen),
                round(summ_normpsmen + summ_vneplan_normosmen), round(summ_zaversheno), '', '']
    rez_spis.append(tmp_itog)
    rez_spi = F.delete_column(rez_spis, ['Завершено, кг.'])
    return rez_spis


def clck_otch(self: mywindow, *args):
    def change_kod_vp(self: mywindow, text, row, col, *args):
        print([text, row, col])
        nk_prim = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Пояснение_вп')
        nk_otv = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Ответственный')
        if self.ui.tbl_report_c.item(row, nk_prim).text() == '':
            CQT.msgbox(f'Пояснение не может быть пустым')
            self.ui.tbl_report_c.item(row, col).setText('')
            self.ui.tbl_report_c.cellWidget(row, col).setCurrentText('')
            return False
        pnom = int(CQT.valt(self.ui.tbl_report_c, 'Пномер', row))
        CSQ.custom_request_c(self.bd_naryad, f"""UPDATE zamech SET  (Пояснение_вп,Код_вп,Ответственный)
        = ("{self.ui.tbl_report_c.item(row, nk_prim).text()}",{self.DICT_KOD_VP[text]},"{F.user_full_namre()}") WHERE Пномер = {pnom};""")
        self.ui.tbl_report_c.item(row, col).setText(text)
        self.ui.tbl_report_c.item(row, nk_otv).setText(F.user_full_namre())
        self.ui.tbl_report_c.removeCellWidget(row, col)
        return True

    def change_nk_fio_vin(self: mywindow, text, row, col, *args):
        print([text, row, col])
        if text == '':
            return

        pnom = int(CQT.valt(self.ui.tbl_report_c, 'Пномер', row))
        CSQ.custom_request_c(self.bd_naryad, f"""UPDATE zamech SET  (ФИО_виновный)
        = ("{text}") WHERE Пномер = {pnom};""")
        self.ui.tbl_report_c.item(row, col).setText(text)
        self.ui.tbl_report_c.removeCellWidget(row, col)
        return True

    if self.vid_report_c == 'Журнал_замечаний':
        if not self.permission:
            return
        nk_kod_vp = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Код_вп')
        nk_prim = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Пояснение_вп')
        nk_fio_vin = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'ФИО_виновный')
        nk_podr_vin = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Виновное_подразделение')
        for i in range(self.ui.tbl_report_c.rowCount()):
            self.ui.tbl_report_c.removeCellWidget(i, nk_kod_vp)
            self.ui.tbl_report_c.item(i, nk_prim).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.tbl_report_c.removeCellWidget(i, nk_fio_vin)
            CQT.set_color_wtab_c(self.ui.tbl_report_c, i, nk_prim, 225, 225, 225)
        row = self.ui.tbl_report_c.currentRow()
        if self.ui.tbl_report_c.item(row, nk_kod_vp).text() not in self.DICT_KOD_VP:
            return

        if self.DICT_KOD_VP[self.ui.tbl_report_c.item(row, nk_kod_vp).text()] != 1:
            if self.DICT_KOD_VP[self.ui.tbl_report_c.item(row, nk_kod_vp).text()] == 4:
                if self.ui.tbl_report_c.item(row, nk_fio_vin).text() != '':
                    return
                vp = ''
                for kod_rc in self.DICT_RC.keys():
                    if self.DICT_RC[kod_rc]['Сокр_наим_СТО'] == self.ui.tbl_report_c.item(row, nk_podr_vin).text():
                        vp = self.DICT_RC[kod_rc]['empl_Подразделение']
                if vp == '':
                    CQT.msgbox(f'Не найден БД {self.ui.tbl_report_c.item(row, nk_podr_vin).text()}')
                    return
                list_empl = [_ for _ in self.DICT_EMPLOEE_FULL.keys() if
                             self.DICT_EMPLOEE_FULL[_]['Подразделение'] == vp]
                list_empl.insert(0, '')
                CQT.add_combobox(self, self.ui.tbl_report_c, row, nk_fio_vin, list_empl, False, change_nk_fio_vin)
            return
        list_kod = list(self.DICT_KOD_VP.keys())
        CQT.add_combobox(self, self.ui.tbl_report_c, row, nk_kod_vp, list_kod, False, change_kod_vp)
        self.ui.tbl_report_c.item(row, nk_prim).setFlags(
            QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        CQT.set_cell_editable(self.ui.tbl_report_c, row, nk_prim, True)
        CQT.set_color_wtab_c(self.ui.tbl_report_c, row, nk_prim, 245, 245, 245)

    if self.vid_report_c == "Трудозатраты":
        arm_pr_oper = check_import_modyle('arm_pr_oper')
        if arm_pr_oper is None:
            import arm_pr_oper
        arm_pr_oper.fill_tbl_report_add(self)

    if self.vid_report_c == "Отчетность персонала":
        RPTP.clck_user()

@CQT.onerror
def dbl_clck_otch(self, *args):
    if self.ui.cmb_sort_c_report.currentText() == 'Понедельный график выработки и отгрузок':
        column = self.ui.tbl_report_c.currentColumn()
        row = self.ui.tbl_report_c.currentRow()
        nk_nach = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Дата начала')
        nk_kon = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Дата конца')
        nach = self.ui.tbl_report_c.item(row, nk_nach).text()
        kon = self.ui.tbl_report_c.item(row, nk_kon).text()
        self.ui.le_start_of_period.setText(nach)
        self.ui.le_end_of_period.setText(kon)
        current_ceh = self.ui.cmb_podrazdelenie.currentText()
        if column == 0:
            self.ui.cmb_sort_c_report.setCurrentText("Выработка цеха по виду")
        else:
            self.ui.cmb_sort_c_report.setCurrentText("Выработка цеха по направлению")
        self.ui.cmb_podrazdelenie.setCurrentText("current_ceh")
        report_c(self)
    if self.vid_report_c == "Отчетность персонала":
        RPTP.dbl_clck_user()

@CQT.onerror
def ves_tehnolohicheskiy(self, nom_mk: int, kolvo_izd, ves, conn, conn_mat, *args):
    LIST_ED_IZM_MAT = ['Килограмм', 'кг']
    custom_request_c = f"""SELECT data FROM res WHERE Номер_мк == {nom_mk}"""
    rez = CSQ.custom_request_c(self.db_resxml, custom_request_c)

    if rez == None or rez == False:
        self.debug.append(f'{nom_mk} nom_mk')
        custom_request_c = f"""SELECT Вес FROM mk WHERE Пномер == {nom_mk}"""
        rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, conn=conn, one=True, rez_dict=True)
        return rez['Вес']
    else:
        res = F.from_binary_pickle(rez[-1][0])
    kd_ves = 0
    summ_ves = 0
    try:
        for dse in res:
            self.debug.append(f"{dse['Номенклатурный_номер']}")
            list_ves_kd = dse['Мат_кд'].split('/')
            if list_ves_kd[1] != '' and list_ves_kd[2] != '':
                kd_ves += F.valm(list_ves_kd[0]) * dse['Количество']
                self.debug.append(
                    f"$по кд {F.valm(list_ves_kd[0]) * dse['Количество']} кг. {list_ves_kd[1]} {list_ves_kd[2]}")
            for oper in dse['Операции']:
                for mat in oper['Материалы']:
                    if mat['Мат_ед_изм'] in LIST_ED_IZM_MAT:
                        resp_mat = CSQ.custom_request_c(self.bd_mat,
                                                        f"""SELECT Вид FROM nomen WHERE Код == '{mat['Мат_код']}' """,
                                                        conn=conn_mat)
                        if len(resp_mat) == 1:
                            self.debug.append(f'!Не найден материал {mat}')
                            continue
                        vid_mat = resp_mat[-1][0]
                        if vid_mat in self.LIST_VID_MAT:
                            summ_ves += mat['Мат_норма']
                            self.debug.append(f"+по тк {mat['Мат_норма']} кг. {mat['Мат_наименование']}")
                        else:
                            self.debug.append(f'-Не учтен материал {mat} как основной')
    except:
        print(f'Ошибка в рес {nom_mk}')
        pass
    self.debug.append("Итог:")
    self.debug.append(
        f'*мк№ {nom_mk}: вес по бд(мес) {ves}, по техкартам {round(kd_ves)}, кол-во {kolvo_izd} изд. разница {round(kd_ves - ves)}')
    self.debug.append('')
    self.debug.append('')
    return summ_ves
