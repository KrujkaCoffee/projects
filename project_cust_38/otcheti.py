from __future__ import annotations

import project_cust_38.Cust_Functions as F

try:
    from PyQt5 import QtCore
except:
    pass

from PyQt5 import QtWebEngineWidgets

from PyQt5.QtWidgets import QVBoxLayout, QApplication

import project_cust_38.Cust_Qt as CQT
from datetime import datetime as DT, timedelta
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
from project_cust_38.Cust_virbotka import koeff_double_pay_holydays as koeff_holy, calc_month_rates_c
import project_cust_38.xml_v_drevo as XML

try:
    import plotly.graph_objects as go
    import pandas as pd
    import grafics as GR
    import plan as PL
    import gant_ploty as gp
    import plotly.express as px
except:
    pass
import copy

from dateutil.relativedelta import relativedelta

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Viewer import mywindow


KOEF_NEDEL_OTH = 1- 0.26
PROIZVODITELNOST = 102
KOEF_VNEPLANA = 0.7
minut_smen = 450
KOEF_RASKLADKI = 1/(2.32 * 0.4584)


@CQT.onerror
def vibor_sort_c_report_c(self, *args):
    vid = self.ui.cmb_sort_c_report_c.currentText()
    self.vid_report_c = vid
    self.ui.le_end_of_period_c.setEnabled(True)
    self.ui.le_nach_per.setEnabled(True)
    if vid == 'Выработка_ТОП':
        next_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        nach = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.le_nach_per.setText(nach)
        podrazdel_list(self,['По направлениям', 'По сотрудникам',
                             'По направлениям будни', 'По сотрудникам будни','По сотрудникам выходные','По сотрудникам выходные за год',
                             'По направлениям за год', 'По сотрудникам за год',
                             'По направлениям будни за год', 'По сотрудникам будни за год',])
    if vid == 'Усредненная удельная трудоемкость сборки по видам':
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = '2023-01-01 00:00:00'
        self.ui.le_nach_per.setText(nach)
        self.ui.le_end_of_period_c.setText(konec)
        podrazdel_none(self)
    if vid == 'Внеплановые работы по направлениям':
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = '2023-01-01 00:00:00'
        self.ui.le_nach_per.setText(nach)
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItems(list(self.DICT_NAPRAVL.keys()))
        self.ui.cmb_podrazdelenie.addItem('Все')
        self.ui.cmb_podrazdelenie.setDisabled(False)

    if vid == 'План-фактный график по месяцам':
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = '2023-01-01 00:00:00'
        self.ui.le_nach_per.setText(nach)
        self.ui.le_end_of_period_c.setText(konec)  
        podrazdel_none(self)

    if vid == 'График удельной производительности сборочного цеха':
        nach = '2023-01-01 00:00:00'
        dat = F.date_add_days(F.datetostr(DT.today()), -31)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        self.ui.le_nach_per.setText(nach)
        self.ui.le_end_of_period_c.setText(konec)
        podrazdel_none(self)

    if vid == 'Норматив материалов по завершенным нарядам':
        next_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        nach = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.le_nach_per.setText(nach)
        podrazdel_none(self)

    if vid == 'Неосвоенный_вес_по_созданным_нарядам':
        self.ui.le_end_of_period_c.setEnabled(False)
        self.ui.le_nach_per.setEnabled(False)
        podrazdel_kod(self)

    if vid == 'О выработке сотрудников за месяц':
        dat = F.date_add_days(F.datetostr(DT.today()), -1)
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = F.start_end_dates_c(date=dat, vid='m')[0]
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.le_nach_per.setText(nach)
        podrazdel_none(self)

    if vid == 'Трудозатраты':
        dat = F.date_add_days(F.datetostr(DT.today()), -1)
        konec = F.start_end_dates_c(date=dat, vid='d')[1]
        nach = F.start_end_dates_c(date=dat, vid='d')[0]
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.le_nach_per.setText(nach)
        podrazdel_kod(self)
    if vid == 'Статистика нормо-весовых харктеристик МК':
        podrazdel_kod(self)
    if vid == 'Выработка цеха по виду':
        podrazdel_kod(self)
    if vid == 'Выработка цеха по направлению':
        dat = F.date_add_days(F.datetostr(DT.today()), -3)
        konec = F.start_end_dates_c(date=dat, vid='n')[1]
        nach = F.start_end_dates_c(date=dat, vid='n')[0]
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.le_nach_per.setText(nach)
        podrazdel_kod(self)
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
        emploee(self)
    if vid == 'Выработка сотрудника по положению':
        nach_kon_mes(self, 'kon')
        emploee(self)
    if vid == 'Выработка сотрудников':
        nach_kon_mes(self)
        podrazdel_kod(self)
    if vid == 'Текущие работы':
        nach_kon_mes(self, 'kon')
        podrazdel_kod(self)
    if vid == 'Выработка сотрудников по положению':
        podrazdel_kod(self)
    if vid == 'Понедельный график выработки и отгрузок':
        nach = '2023-01-01 00:00:00'
        self.ui.le_nach_per.setText(nach)
        podrazdel_kod(self)
    if vid == 'План работ':
        next_month = F.now("")# + relativedelta(months=1)
        nach, konec = F.start_end_dates_c(next_month, '', 'm', "%Y-%m-%d %H:%M:%S")
        self.ui.le_nach_per.setText(nach)
        self.ui.le_end_of_period_c.setText(konec)
        podrazdel_none(self)
    if vid == 'Селекторное':
        self.ui.le_nach_per.setText(F.now("%Y-%m-%d %H:%M:%S"))
        self.ui.le_end_of_period_c.setText(F.now("%Y-%m-%d %H:%M:%S"))
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItems(
            ('Добавлено', 'Закрыто', 'Не закрыто', 'По плану закрыть', 'Просрочены', 'Все'))
        self.ui.cmb_podrazdelenie.setDisabled(False)
    if vid == 'План-фактный анализ по месяцам':
        self.ui.le_nach_per.setText("2022-09-01 00:00:00")
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItems(list(self.DICT_NAPRAVL.keys()))
        self.ui.cmb_podrazdelenie.addItem('Все')
        self.ui.cmb_podrazdelenie.setDisabled(False)
    if vid == 'Длина сварных швов к выработке':
        self.ui.le_nach_per.setText("2022-09-01 00:00:00")
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.cmb_podrazdelenie.clear()
        self.ui.cmb_podrazdelenie.addItems(list(self.DICT_NAPRAVL.keys()))
        self.ui.cmb_podrazdelenie.addItem('Все')
        self.ui.cmb_podrazdelenie.setDisabled(False)
    if vid == 'Журнал_техкарт':
        dat = F.date_add_days(F.datetostr(DT.today()), -1)
        konec = F.start_end_dates_c(date=dat, vid='d')[1]
        nach = F.start_end_dates_c(date=dat, vid='d')[0]
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.le_nach_per.setText(nach)
        podrazdel_none(self)
    if vid == 'Журнал_замечаний':
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        nach = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[0]
        self.ui.le_end_of_period_c.setText(konec)
        self.ui.le_nach_per.setText(nach)
        podrazdel_none(self)
    if vid == 'Сравнение норм времени по направлениям':
        last_month = F.now("") - relativedelta(months=1)
        konec = F.start_end_dates_c(last_month, '', 'm', "%Y-%m-%d %H:%M:%S")[1]
        self.ui.le_nach_per.setText("2023-01-01 00:00:00")
        self.ui.le_end_of_period_c.setText(konec)
        podrazdel_none(self)


@CQT.onerror
def nach_kon_mes(self, kon="today", *args):
    dat = F.datetostr(DT.today())
    konec = F.start_end_dates_c(date=dat, vid='m')[1]
    nach = F.start_end_dates_c(date=dat, vid='m')[0]
    if kon == "today":
        self.ui.le_end_of_period_c.setText(dat)
    else:
        self.ui.le_end_of_period_c.setText(konec)
    self.ui.le_nach_per.setText(nach)


@CQT.onerror
def report_c(self, *args):
    self.ui.tbl_report_c.setToolTip('')
    self.ui.btn_save_txt.setDisabled(True)
    nach = self.ui.le_nach_per.text()
    konec = self.ui.le_end_of_period_c.text()
    vid = self.ui.cmb_sort_c_report_c.currentText()
    podrazd = self.ui.cmb_podrazdelenie.currentText()


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
    tbl = self.ui.tbl_report_c
    CQT.clear_tbl(tbl)
    rez_spis = [[]]
    self.vid_report_c = vid
    self.permission = False
    clear_graf(self)
    if vid == 'Выработка_ТОП':
        rez_spis = virabotka_top(self, nach, konec, podrazd)
    if vid == 'Усредненная удельная трудоемкость сборки по видам':
        rez_spis = udel_trud_sort_c(self, nach, konec)
        self.ui.btn_save_txt.setDisabled(False)
    if vid  == 'Внеплановые работы по направлениям':
        rez_spis = vneplan_po_napravl(self, nach, konec,podrazd)
    if vid == 'План-фактный график по месяцам':
        rez_spis = plan_fact_grafic_mes(self, nach, konec)
    if vid == 'График удельной производительности сборочного цеха':
        rez_spis = gr_ud_proizv_cexa(self, nach, konec)
    if vid == 'Журнал_замечаний':
        rez_spis = jurnal_zamech(self, nach, konec)
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
    if vid == 'Трудозатраты':
        rez_spis = trudozatraty(self, nach, konec, podrazd)
        self.ui.btn_save_txt.setDisabled(False)
    if vid == 'Статистика нормо-весовых харктеристик МК':
        rez_spis = statistic_normoweight_MK_c(self, nach, konec, podrazd)
    if vid == 'Выработка цеха по виду':
        rez_spis = virabotka_ceha(self, nach, konec, podrazd)
    if vid == 'Выработка цеха по направлению':
        rez_spis = virabotka_ceha(self, nach, konec, podrazd, f_napravl=True)
    if vid == 'Выработка цеха понарядно':
        rez_spis = virabotka_ceha_ponaryadno(self, nach, konec, podrazd)
    if vid == 'Журнал работ':
        rez_spis = jurnal_rabot(self, nach, konec)
    if vid == 'Внеплановые работы':
        rez_spis = vneplan_rabot(self, nach, konec)
    if vid == 'Выработка сотрудника':
        rez_spis = virabotka_sotr(self, nach, konec, podrazd)
    if vid == 'Выработка сотрудника по положению':
        rez_spis = virabotka_sotr_po_pologeniy(self, nach, konec, podrazd)
    if vid == 'Выработка сотрудников':
        rez_spis = virabotka_sotrudnikov(self, nach, konec, podrazd)
    if vid == 'Текущие работы':
        rez_spis = tekush_raboty(self, podrazd)
    if vid == 'Выработка сотрудников по положению':
        rez_spis = virabotka_sotrudnikov_po_pologeniy(self, nach, konec, podrazd)
    if vid == 'Понедельный график выработки и отгрузок':
        rez_spis = ponedelniy_grafik_vir_otgr(self, nach, konec, podrazd)
    if vid == 'План работ':
        rez_spis = plan_rabot_preload(self, nach, konec, podrazd)
    if vid == 'Селекторное':
        rez_spis = report_c_selector(self, nach, konec, podrazd)
    if vid == 'Сравнение норм времени по направлениям':
        rez_spis = sravn_nv_napr(self, nach, konec)
    if vid == 'Длина сварных швов к выработке':
        rez_spis = svar_vir(self, nach, konec)
    # F.save_file('debug.txt',self.debug)
    if rez_spis == None:
        return

    CQT.fill_wtabl_old_c(self, rez_spis, tbl, separ='', isp_hat_c=True, max_vis_row=500)
    CMS.fill_filtr_c(self, self.ui.tbl_report_c_filtr, tbl)

    if vid == 'Трудозатраты':
        self.ui.tbl_report_c.setToolTip(f'Необходимо попасть в диапазон от {self.PROC_OTKL_TRUDOZATRAT[0]} до {self.PROC_OTKL_TRUDOZATRAT[1]}')
        nk_proc = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Соответствие_%')
        for i in range(self.ui.tbl_report_c.rowCount()):
            val_of_proc = F.valm(self.ui.tbl_report_c.item(i, nk_proc).text())
            if val_of_proc < 100 and val_of_proc >= self.PROC_OTKL_TRUDOZATRAT[0]:
                delta = (100 - val_of_proc) * 6
                CQT.set_color_wtab_c(self.ui.tbl_report_c, i, nk_proc, 255, 255 , 255 - delta)
            if val_of_proc > 100 and val_of_proc <= self.PROC_OTKL_TRUDOZATRAT[1]:
                delta = val_of_proc - 100
                CQT.set_color_wtab_c(self.ui.tbl_report_c, i, nk_proc, 255- delta, 255 , 255 -delta)
            if val_of_proc < self.PROC_OTKL_TRUDOZATRAT[0] or val_of_proc > self.PROC_OTKL_TRUDOZATRAT[1]:
                CQT.set_color_wtab_c(self.ui.tbl_report_c, i, nk_proc, 255, 55, 55)
            dir_path = CMS.load_tmp_path('tdz_dir')
            self.ui.le_path_save.setText(dir_path)


    if vid == 'Журнал работ':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl)
    if vid == 'Выработка цеха понарядно':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'Выработка сотрудника':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl)
        CQT.color_cell_wtable_c(tbl, 'Внеплан', '1', r=222, g=100, b=100)
        CQT.color_cell_wtable_c(tbl, 'Внеплан', '2', r=100, g=222, b=100)
        CQT.color_cell_wtable_c(tbl, 'Подтвержд_вып', '0', r=222, g=100, b=100)
        CQT.color_cell_wtable_c(tbl, 'Подтвержд_вып', '1', r=100, g=222, b=100)
    if vid == 'Выработка сотрудника по положению':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl)
        CQT.color_cell_wtable_c(tbl, 'Внеплан', '1', r=222, g=100, b=100)
        CQT.color_cell_wtable_c(tbl, 'Внеплан', '2', r=100, g=222, b=100)
        CQT.color_cell_wtable_c(tbl, 'Подтвержд_вып', '0', r=222, g=100, b=100)
        CQT.color_cell_wtable_c(tbl, 'Подтвержд_вып', '1', r=100, g=222, b=100)
    if vid == 'Понедельный график выработки и отгрузок':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'Статистика нормо-весовых харктеристик МК':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'План работ':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'План-фактный анализ по месяцам':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'О выработке сотрудников за месяц':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'Неосвоенный_вес_по_созданным_нарядам':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'Норматив материалов по завершенным нарядам':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'Журнал_техкарт':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'Журнал_замечаний':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
        self.permission = CMS.user_access(self.bd_naryad, 'просмотр_журнал_замечаний_корректировка_вн', 
                                          F.user_full_namre(), False)
    if vid == 'Сравнение норм времени по направлениям':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'График удельной производительности сборочного цеха':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'Выработка_ТОП':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)
    if vid == 'План-фактный график по месяцам':
        CMS.apply_apply_apply_apply_primenit_summ_с_c_c_c(self, tbl, sredn=True)

def rc_po_fio(self,fio):
    fio_rc = False
    if fio in self.DICT_EMPLOEE_FULL:
        fio_podrazd = self.DICT_EMPLOEE_FULL[fio]['Подразделение']
        for podr in self.DICT_RC.keys():
            if self.DICT_RC[podr]['empl_Подразделение'] == fio_podrazd:
                fio_rc = podr
    return fio_rc


def gr_ud_proizv_cexa(self:mywindow, nach, konec, *args):
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
        DICT_MAT = F.deploy_dict_c(CSQ.custom_request_c(self.bd_mat,f"""SELECT * FROM nomen""",rez_dict=True),'Код')
        DICT_FILTR = F.deploy_dict_c(CSQ.custom_request_c(self.bd_mat, f"""SELECT * FROM complex_filtr""", rez_dict=True), 'kod')
        custom_request_c = f"""SELECT mk.Пномер, mk.Дата_завершения, mk.Количество  FROM mk WHERE Дата_завершения != ""
                    and datetime(Дата_завершения) >= datetime("{nach}") and datetime(Дата_завершения) < datetime("{konec}")"""
        rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)
        set_razm = set()
        list_hz_mat = []
        for item in rez_mk:
            ves_xml = 0
            nom_mk = int(item['Пномер'])
            kol_vo_izd = int(item['Количество'])
            try:
                query = f'''SELECT data, Head FROM xml
                                   WHERE Номер_мк == {int(nom_mk)}
                                               '''
                rez_xml = CSQ.custom_request_c(self.db_resxml, query)
                xml = rez_xml[-1][0]
                xml_head = rez_xml[-1][1]
                if xml != '':
                    res_new = podgotovka_xml(self,XML.spisok_iz_xml(str_f=xml))
                    for item_xml in res_new:
                        mat = item_xml['data']['Масса/М1,М2,М3'].split('/')
                        if 'Тип' in item_xml['data']:
                            if mat[1] != '' and item_xml['data']['Тип'] ==  'Деталь':
                                ves_xml += F.valm(mat[0]) * F.valm(item_xml['data']['Количество на изделие'])*kol_vo_izd
                        else:
                            pass
                            if mat[1] != '' and item_xml['data']['Покупное изделие'] != '1':
                                ves_xml += F.valm(mat[0]) * F.valm(
                                    item_xml['data']['Количество на изделие']) * kol_vo_izd
                    CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET xml = {round(ves_xml,2)} WHERE Пномер = {nom_mk}""")
            except:
                print(f'Некорректные данные хмл {nom_mk}')
            
            ves_res = 0
            ves_res_list = 0
            #month = F.datetostr(F.strtodate(item['Дата_завершения']),"%Y-%m")
            
            res = CSQ.custom_request_c(self.db_resxml,f'''SELECT data FROM res WHERE Номер_мк == {nom_mk};''',hat_c=False,one=True)
            if res == False:
                CQT.msgbox(f'ОШибка')
                return
            try:
                res = F.from_binary_pickle(res[-1][0])
                for dse in res:
                    kol = dse['Количество']
                    for oper in dse['Операции']:
                        for mat in oper['Материалы']:
                            if mat['Мат_ед_изм'] not in self.LIST_ED_IZM_MAT and mat['Мат_код'] not in DICT_FILTR:
                                list_hz_mat.append(f"{F.valm(mat['Мат_норма'])} {mat['Мат_ед_изм']} "
                                                   f"{mat['Мат_наименование']} {mat['Мат_код']}     "
                                                   f"опер: {oper['Опер_наименовние']}     "
                                                   f"дет: {dse['Наименование']} {dse['Номенклатурный_номер']}")
                            set_razm.add(mat['Мат_ед_изм'])
                            if mat['Мат_ед_изм'] in self.LIST_ED_IZM_MAT:
                                ves_res += F.valm(mat['Мат_норма'])
                                #print(f"{F.valm(mat['Мат_норма'])} опер {oper['Опер_наименовние']} дет {dse['Наименование']}")
                                if mat['Мат_код'] in DICT_MAT and DICT_MAT[mat['Мат_код']]['П5']=='1':
                                    if DICT_MAT[mat['Мат_код']]['П6']!= '':
                                        ves_res_list += F.valm(mat['Мат_норма'])
                CSQ.custom_request_c(self.bd_naryad,f"""UPDATE zagot SET Вес_по_рес = {round(ves_res_list,2)} WHERE Ном_МК = {nom_mk}""")
                #CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Ресурсная = "" WHERE Пномер = {nom_mk}""")
                CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Вес = {round(ves_res, 2)} WHERE Пномер = {nom_mk}""")
            except:
                print(f'Некорректные данные рес {nom_mk}')
        #for item in set_razm:
        #    print(item)
        #F.save_file('unknown_mats.txt', list_hz_mat)
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
    #get_ves_from_res_and_xml() #ПЕРСЧЕТ норм По ресурсной включать раз месяц
    
    
    #====================Подсчет выработки =================
    

        
    custom_request_c = f"""SELECT mk.Вес, naryad.Твремя, naryad.ДСЕ_ID, naryad.Операции, naryad.Опер_время, naryad.Номер_мк, naryad.Внеплан, naryad.ФИО, naryad.ФИО2,  
            naryad.Фвремя, naryad.Фвремя2, naryad.Подтвержд_вып_дата, naryad.Виды_работ, naryad.Пномер FROM naryad INNER JOIN
             mk ON mk.Пномер = naryad.Номер_мк WHERE
        datetime(naryad.Подтвержд_вып_дата) > datetime("{nach}") and 
        datetime(naryad.Подтвержд_вып_дата) <= datetime("{konec}") AND naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1"""
    query = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)

    zzz = f"""
    SELECT jurnal.Пномер, jurnal.ФИО as ФИОЖ, jurnal.Подытог, jurnal.Номер_наряда, jurnal.Статус, naryad.Твремя, 
    naryad.Коэфф_сложности , naryad.Задание, naryad.ФИО, naryad.ФИО2, naryad.Фвремя, naryad.Фвремя2 FROM jurnal 
    INNER JOIN naryad ON naryad.Пномер = jurnal.Номер_наряда 
    WHERE jurnal.Статус == "Завершен" AND jurnal.Дата <= strftime("%Y-%m-%d %H:%M:00", datetime("2023-08-31 23:59:59")) AND 
    jurnal.Дата >= strftime("%Y-%m-%d %H:%M:00", datetime("2023-01-01 00:00:00")) AND naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1
    """
    query_j = CSQ.custom_request_c(self.bd_naryad, zzz, hat_c=True, rez_dict=True)

    tmp = []
    for i, item_j in enumerate(query_j):
        if item_j['ФИОЖ'] == 'Аксенов Александр Сергеевич':
            usr = item_j['ФИОЖ']
            nnar = item_j['Номер_наряда']
            time = '&'
            if usr == item_j['ФИО']:
                time = item_j['Фвремя']
            if usr == item_j['ФИО2']:
                time = item_j['Фвремя2']
            vid = 'Ж'
            tmp.append([usr,nnar,time,vid])

    for i, item_j in enumerate(query):
        if item_j['ФИО'] == 'Аксенов Александр Сергеевич':
            usr = item_j['ФИО']
            nnar = item_j['Пномер']
            time = item_j['Фвремя']
            vid = 'Н'
            tmp.append([usr,nnar,time,vid])
        if item_j['ФИО2'] == 'Аксенов Александр Сергеевич':
            usr = item_j['ФИО2']
            nnar = item_j['Пномер']
            time = item_j['Фвремя2']
            vid = 'Н'
            tmp.append([usr,nnar,time,vid])

    F.save_file('list_tmp_emp_min2.txt', tmp)



                    
    rez = dict()
    self.dict_tmp_emp_min = dict()
    for item in query:
        month = F.datetostr(F.strtodate(item['Подтвержд_вып_дата']),"%Y-%m")
        
        if month not in rez:
            rez[month] = {'minut':0, 'minut_fact':0, 'days' :dict(), 'ves':0, 'ves_list':0, 'ves_xml':0,'ves_kplan':0}
        minut = 0
        minut_f = 0
        
        minut = add_time(self, item, minut)
        minut_f = add_time_f(self, item, minut_f)
        

        rez[month]['minut'] += minut
        rez[month]['minut_fact'] += minut_f
        
            
    for item in query:
        month = F.datetostr(F.strtodate(item['Подтвержд_вып_дата']),"%Y-%m")
        if month not in self.dict_tmp_emp_min:
            self.dict_tmp_emp_min[month] = dict()

        teor = F.valm(item['Твремя'])
        if item['ФИО'] != '':
            add_time_tmp_empl(self, item['ФИО'],teor, F.valm(item['Фвремя']),month)
        if item['ФИО2'] != '':
            add_time_tmp_empl(self, item['ФИО2'],teor, F.valm(item['Фвремя2']),month)


    list_tmp_emp_min = F.dict_of_dicts_to_list_of_lists(self.dict_tmp_emp_min['2023-08'])
    F.save_file('list_tmp_emp_min.txt',list_tmp_emp_min)
    #===================подсчет постов   days ========================================
    custom_request_c = f"""SELECT jurnal.Дата, jurnal.ФИО FROM jurnal WHERE datetime(jurnal.Дата) > datetime("{nach}") 
            and datetime(jurnal.Дата) < datetime("{konec}")"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
    for item in rez_jur:
        data = F.datetostr(F.strtodate(item['Дата']),'%Y-%m-%d')
        month = F.datetostr(F.strtodate(item['Дата']),"%Y-%m")
        if month not in rez:
            rez[month] = {'minut':0, 'minut_fact':0, 'days' :dict(), 'ves':0, 'ves_list':0, 'ves_xml':0,'ves_kplan':0}
        if data not in rez[month]['days']:
            rez[month]['days'][data] = set()
        if item['ФИО'] in self.DICT_EMPLOEE_FULL:
            if self.DICT_EMPLOEE_FULL[item['ФИО']]['Подразделение'] == 'Сборочный цех Производства':
                rez[month]['days'][data].add(item['ФИО'])
    #=====================================================================================

    # ===================подсчет веса по МК,КД,РЕС   ========================================
    custom_request_c = f"""SELECT plan.МК, пл_ко.Вес_КД FROM plan INNER JOIN пл_ко ON пл_ко.НомПл = plan.Пномер WHERE plan.МК != 0"""
    rez_kplan_ves_kd = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, custom_request_c, rez_dict=True), 'МК')
    
    custom_request_c = f"""SELECT mk.Пномер, mk.Номер_заказа, mk.Номер_проекта, mk.Вес, mk.Дата_завершения, mk.Ресурсная, mk.xml, mk.Количество,
     zagot.Вес_по_рес FROM mk INNER JOIN zagot ON zagot.Ном_МК = mk.Пномер WHERE mk.Дата_завершения != ""
            and datetime(mk.Дата_завершения) >= datetime("{nach}") and datetime(mk.Дата_завершения) < datetime("{konec}")"""
    rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)
    viv =[]
    for item in rez_mk:
        viv.append([item["Пномер"],item["Номер_заказа"],item["Номер_проекта"],item["Вес"],item["Вес_по_рес"],item["xml"]])
        month = F.datetostr(F.strtodate(item['Дата_завершения']),"%Y-%m")
        if month not in rez:
            rez[month] = {'minut':0, 'minut_fact':0, 'days' :dict(), 'ves':0 , 'ves_list':0, 'ves_xml':0,'ves_kplan':0}
        
        ves_list_without_oth = item['Вес_по_рес'] * KOEF_NEDEL_OTH * KOEF_RASKLADKI
        delta = item['Вес_по_рес'] - ves_list_without_oth
        rez[month]['ves_list'] += ves_list_without_oth
        rez[month]['ves'] += (item['Вес'] - delta)
        rez[month]['ves_xml'] += F.valm(item['xml'])
        if item["Пномер"] in rez_kplan_ves_kd:
            rez[month]['ves_kplan'] += F.valm(rez_kplan_ves_kd[item['Пномер']])
        else:
            rez[month]['ves_kplan'] += F.valm(item['xml'])
    # =====================================================================================

    F.save_file('viv_ves.txt',viv)

    rez_tbl = [['Месяц','Постов','Выработка, н-недель','Присутствие, недель', 'Произв-ть % н-смен/пост',
                'Вес Рес.ИЗД, т. без скелета','Вес Рес.только лист без скелета, т.','Вес хмл КО, т.','Вес по черт.']]
    list_month = sorted(rez.keys())
    for month in list_month:
        name_table = F.datetostr(F.strtodate(month,"%Y-%m"),'m_%Y_%m_01')
        rab_dn_count = 0
        q_days = CSQ.custom_request_c(self.bd_users,f"""SELECT * FROM {name_table} WHERE Пномер = 1""")
        for j in range(3,len(q_days[0])):
            if q_days[1][j] == 0:
                rab_dn_count+=1
        list_count_days = []
        for day in rez[month]['days']:
            list_count_days.append(len(rez[month]['days'][day]))
        postov = sum(list_count_days)/rab_dn_count / 2
        virabotka = rez[month]['minut'] / 450/2
        prisutstvie  = rez[month]['minut_fact'] / 450/2
        proizv = virabotka / postov/rab_dn_count *100
        virabotka = virabotka/7
        prisutstvie = prisutstvie/7
        rez_tbl.append([month,round(postov,1), round(virabotka), round(prisutstvie), round(proizv,2), round(rez[month]['ves']/1000,2),
                        round(rez[month]['ves_list']/1000,2),
                        round(rez[month]['ves_xml']/1000,2),
                        round(rez[month]['ves_kplan'] / 1000, 2),
                        ])

    load_browser(self)
    create_gant(self,rez_tbl)
    rez_tbl.append(['' for _ in rez_tbl[0]])
    rez_tbl.append(['' for _ in rez_tbl[0]])
    return rez_tbl


def jurnal_zamech(self, nach, konec):
    custom_request_c = f"""SELECT zamech.Пномер,
zamech.Дата_создания,
mk.Номенклатура,
mk.Номер_заказа,
mk.Номер_проекта,
mk.Вид,
zamech.Инициатор,
zamech.Виновное_подразделение,
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
    rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True )
    nk_podr = F.num_col_by_name_in_hat_c(rez, 'Виновное_подразделение')
    for i in range(len(rez)):
        if rez[i][nk_podr] in self.DICT_RC:
            rez[i][nk_podr] = self.DICT_RC[rez[i][nk_podr]]['Сокр_наим_СТО']
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    load_browser(self)
    create_gant(self,rez)
    return rez

def load_browser(self):
    try:
        self.parent_for_grafic.removeWidget(self.browser)
    except:
        pass
    self.browser = QtWebEngineWidgets.QWebEngineView(self)
    self.parent_for_grafic.addWidget(self.browser)

def jurnal_tk(self, nach, konec):
    custom_request_c = f"""SELECT * FROM jurnal_td WHERE 
                           datetime(Дата) > datetime("{nach}") 
                           and datetime(Дата) < datetime("{konec}")"""
    rez = CSQ.custom_request_c(self.db_dse, custom_request_c, hat_c=True )
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez


def norm_mat_po_zav_nar(self,nach_data,kon_data):
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
    rez_res = F.deploy_dict_c(rez_res,'Номер_мк')
    rez_list = [['Номер_мк','Номенклатура','Номер_заказа','Пномер наряда','ДСЕ','Вид работ','Мат_код','Мат_наименование','Мат_ед_изм','Мат_норма']]
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
                                if oper['Опер_номер'] + '$' + oper['Опер_наименовние'] == oper_nom:
                                    for mat in oper['Материалы']:
                                        if 'Мат_норма_ед' in mat:
                                            nr = mat['Мат_норма_ед'] * kolvo / koef
                                        else:
                                            nr = mat['Мат_норма'] / max_kol * kolvo / koef
                                        rez_list.append([nar['Номер_мк'], nar['Номенклатура'], nar['Номер_заказа'],
                                                             nar['Пномер'], dse_str, vidrab, mat['Мат_код'], mat['Мат_наименование'],
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
            fio_rc = rc_po_fio(self,fio)
            if fio_rc == podrazd:
                
                nom_nar = rez[i]['Пномер']
                summ = CSQ.custom_request_c(self.bd_naryad, f"""SELECT sum(Подытог) FROM jurnal WHERE ФИО == "{fio}" and Номер_наряда == {nom_nar}""")
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
                summ = CSQ.custom_request_c(self.bd_naryad, f"""SELECT sum(Подытог) FROM jurnal WHERE ФИО == "{fio2}" and Номер_наряда == {nom_nar}""")
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
                        summ+= F.valm(list_vrem[i])
            if summ > 0:
                fl1 = True
                fl2 = True
            rez[i]['Освоено2'] == 0
            neosv1 = summ
            neosv2 = 0
        rez[i]['Неосв_кг_сумм'] = round((neosv1 + neosv2) * 102/ 480)
        if fl1 == True or fl2 == True:
            list_res.append(rez[i])
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez

def virabotka_sotr_za_mes(self:mywindow, nach_data, kon_data, *args):
    list_prich_pauz = F.load_file(f'{F.cfg["data_f"]}\Выполнение\Data\Prich_pauz.txt')
    list_prich_pauz.append('')
    list_prich_pauz.append(None)
    rez = [["п/п",	"Работник",	"Должность", "Подразделение","Наименование",	"Вид работ",	"Тариф",	"Единица измерения",	"Факт, мин.",
            "Норма, мин.",	"Фонд оплаты труда(План, руб.)",	"Фонд оплаты труда(Факт, руб.)",
            "Отклонение фактических показателей от предельных норм  мощностей, в мин.",	"Причина отклонения",
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
            if empl != False and len(empl)>=1:
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
        list_time_rabot =[F.valm(_) for _ in str_time_rabot.split("|")]
        list_dse = item['ДСЕ'].split("|")
        list_prim = CSQ.custom_request_c(self.bd_naryad,f"""SELECT Примечание FROM jurnal WHERE Номер_наряда == {nom_nar} AND ФИО == '{fio}';""",hat_c=False)

        try:
            str_prim ='; '.join([_[0] for _ in list_prim if [0] != None and _[0].strip() not in list_prich_pauz])
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
            fact_dse = round(norma_dse/koef,2)

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
    self.ui.cmb_gant_tochnost_dat.addItems(['Подетально', 'Помаршрутно','Отчет вспомогательных материалов'])


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
    if self.ui.cmb_gant_tochnost_dat.currentText() == 'Отчет вспомогательных материалов':
        name = f'plan_materials_{F.now("%Y-%m-%d")}.xlsx'
        nach = self.ui.le_nach_per.text()
        konec = self.ui.le_end_of_period_c.text()
        PL.save_excell_plan_materials(self,self.rez_plan,self.files_tmp,name,nach,konec)
    if  self.ui.cmb_gant_tochnost_dat.currentText() in ['Подетально', 'Помаршрутно']:
        create_gant(self)

@CQT.onerror
def create_gant(self, *args):
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

    def fig_gr_ud_prt_cex(self,spis):
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
        fig.add_trace(go.Scatter(x=month, y=ves, name= spis[0][5],
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

    def fig_gr_pf_gr_mes(self,spis):
        #[['Месяц', 'План, н-см.', 'Отгрузка, т.', 'Факт, н-см.', 'Внеплан, н-см.', 'Сумм. Факт, н-см.']]
        month = [_[0] for _ in spis[1:]]
        plan_ns = [_[1] for _ in spis[1:]]
        otgruzka = [_[2] for _ in spis[1:]]
        fact_ns = [_[3] for _ in spis[1:]]
        vnepalan = [_[4] for _ in spis[1:]]
        summ_fact = [_[5] for _ in spis[1:]]


        fig = go.Figure()
        color = 'firebrick'
        type_line = 'solid'
            # '''"solid", "dot", "dash",
            #            "longdash", "dashdot", or "longdashdot"'''
        fig.add_trace(go.Scatter(x=month, y=plan_ns, name=spis[0][1],
                                     line=dict(color='#1f77b4', width=4,
                                               dash=type_line), text=plan_ns ,
                                 textposition='top right',
                                  textfont=dict(color='#1f77b4',size = 16),
                                  mode='lines+text'))
        fig.add_trace(go.Scatter(x=month, y=otgruzka, name=spis[0][2],
                                 line=dict(color='#bfbf00', width=4,
                                           dash=type_line), text=otgruzka ,
                                 textposition='top right',
                                  textfont=dict(color='#bfbf00',size = 16),
                                  mode='lines+text'))

        fig.add_trace(go.Scatter(x=month, y=fact_ns, name=spis[0][3],
                                 line=dict(color='#007f00', width=4,
                                           dash=type_line), text=fact_ns ,
                                 textposition='top right',
                                  textfont=dict(color='#007f00',size = 16),
                                  mode='lines+text'))

        fig.add_trace(go.Scatter(x=month, y=vnepalan, name= spis[0][4],
                                 line=dict(color='#ff0000', width=4,
                                           dash=type_line), text=vnepalan ,
                                 textposition='top right',
                                  textfont=dict(color='#ff0000',size = 16),
                                  mode='lines+text'))

        fig.add_trace(go.Scatter(x=month, y=summ_fact, name=spis[0][5],
                                 line=dict(color='#c6580f', width=4,
                                           dash=type_line), text=summ_fact ,
                                 textposition='top right',
                                  textfont=dict(color='#c6580f',size = 16),
                                  mode='lines+text'))

        # Edit the layout
        fig.update_layout(
            title=f'{self.vid_report_c}',
            xaxis_title='Месяц',
            yaxis_title='')
        return fig

    def fig_gr_vnepl_rab(self,spis,napravl=''):
        #['Месяц', 'Внеплан, н-см.', 'Сумм св_швов, м.', 'Брак производственный', 'Ошибка нормирования и технологии', 'Доработка КД', 'Обучение', 'Работы на внешней площадке', 'Ошибка планирования нарядов', 'Отсутвие заказа на производство', 'Доработка оборудования(исправление чужого брака)', 'Цеховая оснастка', 'Простой']
        month = [_[0] for _ in spis[1:]]
        DICT_FORM = { 'Месяц':[""," "],
 'Внеплан, н-см.':["#ff0000","solid"],
 'Сумм св_швов, м.':["#bfbf00","longdashdot"],
 'Брак производственный':["#C15911","dash"],
 'Ошибка нормирования и технологии':["#599f21","dash"],
 'Доработка КД':["#5D14F0","dash"],
 'Обучение':["#BC4890","dash"],
 'Работы на внешней площадке':["#0DD6F7","dot"],
 'Ошибка планирования нарядов':["#766d0b","dot"],
 'Отсутвие заказа на производство':["#7BA85C","dot"],
 'Доработка оборудования(исправление чужого брака)':["#ff0000","dot"],
 'Цеховая оснастка':["#A06468","longdash"],
 'Простой':["#689B9C","longdash"],
}
        fig = go.Figure()
        color = 'firebrick'
        type_line = 'solid'
            # '''"solid", "dot", "dash",
            #            "longdash", "dashdot", or "longdashdot"'''
        for column in range(1,len(spis[0])):
            color = color = 'firebrick'
            type_line = 'solid'
            try:
                color = DICT_FORM[spis[0][column]][0]
                type_line = DICT_FORM[spis[0][column]][1]
            except:
                pass
            fig.add_trace(go.Scatter(x=month, y=[_[column] for _ in spis[1:]], name=spis[0][column],
                                             line=dict(color=color, width=4,
                                                       dash=type_line), text=[_[column] for _ in spis[1:]] ,
                                         textposition='top right',
                                          textfont=dict(color=color,size = 14),
                                          mode='lines+text'))

        # Edit the layout
        fig.update_layout(
            title=f'{self.vid_report_c}. {napravl}',
            xaxis_title='Месяц',
            yaxis_title='')
        return fig

    if self.vid_report_c == 'Внеплановые работы по направлениям':
        if args == None or len(args) == 0:
            return
        fig = fig_gr_vnepl_rab(self, args[0],args[-1])
        load_browser(self)
        vivod_gant(self, fig, self.browser)
        
        
        
    if self.vid_report_c == 'План-фактный график по месяцам':
        if args == None or len(args) == 0:
            return
        fig = fig_gr_pf_gr_mes(self, args[0])
        load_browser(self)
        vivod_gant(self, fig, self.browser)


    if self.vid_report_c == 'График удельной производительности сборочного цеха':
        if args == None or len(args) == 0:
            return
        fig = fig_gr_ud_prt_cex(self, args[0])
        load_browser(self)
        vivod_gant(self, fig, self.browser)

    if self.vid_report_c == 'Сравнение норм времени по направлениям':
        if args == None or len(args) == 0: 
            return 
        data_list = args[0]
        dict_color = CSQ.custom_request_c(self.db_kplan,f"""SELECT napravlenie.Цвет , napravlenie.name FROM napravlenie """,rez_dict=True)
        dict_color = F.deploy_dict_c(dict_color,'name')
        fig = fig_sravn_norm_vr_po_napr(self, data_list,dict_color)
        load_browser(self)
        vivod_gant(self, fig, self.browser)

    if self.vid_report_c == 'План работ':
        if self.plan_for_gant == '' or self.ui.cmb_gant_vert.currentText() == '' or self.ui.cmb_gant_colour == '':
            return
        fig = gp.fig_podetalno_narc_projects(self.plan_for_gant, self.ui.cmb_gant_vert.currentText(),
                                             self.ui.cmb_gant_vert_val.currentText(), self.ui.cmb_gant_colour.currentText(),
                                             self.ui.cmb_gant_tochnost_dat.currentText())
        vivod_gant(self, fig, self.browser)

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
                dict_tmp[zam['Виновное_подразделение']][zam['Код_замечания']][zam['Код_вп']] +=1
            except:
                print(f'ОШибка {zam}')
        
        list_kod_vp = []
        list_kod = []
        list_podr = []
        list_zam_count = []
        
        for podr in dict_tmp:
            for kod in dict_tmp[podr]:
                for kod_vp in dict_tmp[podr][kod]:
                    list_podr.append(podr)
                    list_kod_vp.append(kod_vp)
                    list_kod.append(kod)
                    list_zam_count.append(dict_tmp[podr][kod][kod_vp])

        for i in range(len(list_zam_count)):
            if list_zam_count[i] == 0:
                list_zam_count[i] = None

        #list_kod_vp = ["A", "B", "C", "D", None, "E", "F", "G", "H", None]
        #list_kod = ["Tech", "Tech", "Finance", "Finance", "Other",
        #           "Tech", "Tech", "Finance", "Finance", "Other"]
        #list_podr = ["North", "North", "North", "North", "North",
        #           "South", "South", "South", "South", "South"]
        #list_zam_count = [1, 3, 2, 4, 1, 2, 2, 1, 4, 1]
        df = pd.DataFrame(
            dict(podr=list_podr, kod=list_kod, kod_vp=list_kod_vp, число_замечаний=list_zam_count)
        )
        print(df)
        fig = px.sunburst(df, path=['podr','kod','kod_vp'], values='число_замечаний',title='Диаграмма замечаний за пероид')
        vivod_gant(self, fig, self.browser)
        


@CQT.onerror
def vivod_gant(self, fig, obj, *args):
    html = fig.to_html()
    print('2.1')
    putf = CMS.tmp_dir() + F.sep() + 'text.html'
    print(f'Saved: {putf}')
    print('2.2')
    with open(putf, 'w+', encoding="utf-8") as f:
        f.write(html)
    # rez = self.browser.setHtml(html)
    print('2.3')
    # self.ui.browser.setUrl(QtCore.QUrl(f"file://{putf.replace(F.sep(),'/')}"))
    obj.setUrl(QtCore.QUrl(f"file:///{putf.replace(F.sep(), '/')}"))
    print('2.4')
    # print(rez)


@CQT.onerror
def calendar_click(self, *args):
    data = self.ui.calendarWidget.selectedDate()
    if self.ui.rbut_nach_per.isChecked():
        self.ui.le_nach_per.setText(F.datetostr(QtCore.QDate.toPyDate(data), "%Y-%m-%d 00:00:00"))
        if self.ui.cmb_sort_c_report_c.currentText() == 'Трудозатраты':
            konec = F.start_end_dates_c(date=self.ui.le_nach_per.text(), vid='d')[1]
            self.ui.le_end_of_period_c.setText(konec)
        if self.ui.cmb_sort_c_report_c.currentText() == 'О выработке сотрудников за месяц':
            konec = F.start_end_dates_c(date=self.ui.le_nach_per.text(), vid='m')[1]
            self.ui.le_end_of_period_c.setText(konec)

    if self.ui.rbut_end_of_period_c.isChecked():
        self.ui.le_end_of_period_c.setText(F.datetostr(QtCore.QDate.toPyDate(data), "%Y-%m-%d 23:59:59"))
        if self.ui.cmb_sort_c_report_c.currentText() == 'Трудозатраты':
            nach = F.start_end_dates_c(date=self.ui.le_end_of_period_c.text(), vid='d')[0]
            self.ui.le_nach_per.setText(nach)
        if self.ui.cmb_sort_c_report_c.currentText() == 'О выработке сотрудников за месяц':
            nach = F.start_end_dates_c(date=self.ui.le_end_of_period_c.text(), vid='m')[0]
            self.ui.le_nach_per.setText(nach)


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
def podrazdel_none(self, *args):
    self.ui.cmb_podrazdelenie.clear()
    self.ui.cmb_podrazdelenie.addItem('-')
    self.ui.cmb_podrazdelenie.setDisabled(True)
    
@CQT.onerror
def podrazdel_list(self, list_vals:list, *args):
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
def plan_rabot(self, nach, konec, podrazd, *args):
    modifiers = QApplication.keyboardModifiers()
    delete_cash_plan = False
    if modifiers == QtCore.Qt.ShiftModifier:
        delete_cash_plan = True
        print('delete_cash_plan = True')
    plan_full_spis = PL.load_plan(self, delete_cash_plan)
    plan = self.generate_list_plan(plan_full_spis)
    if plan == None:
        return
    rez = [plan[0]]
    nk_nachalo = plan[0].index('Начало')
    for item in plan[1:]:
        # print(item)
        if F.strtodate(item[nk_nachalo][:19]) >= F.strtodate(nach) and F.strtodate(item[nk_nachalo][:19]) < F.strtodate(
                konec):
            rez.append(item)
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez

def svar_vir(self, data_nach, data_kon):
    return


def sravn_nv_napr(self, data_nach, data_kon):
    query = f"""SELECT DISTINCT naryad.Пномер, naryad.Дата, naryad.Твремя, naryad.Фвремя, naryad.Фвремя2, 
    naryad.ФИО, naryad.ФИО2, mk.Направление, naryad.Опер_время, naryad.Операции FROM naryad 
INNER JOIN mk ON mk.Пномер == naryad.Номер_мк
INNER JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер
WHERE naryad.Подтвержд_вып == 1 AND datetime(naryad.Дата) > datetime("{data_nach}") 
                and datetime(naryad.Дата) < datetime("{data_kon}") and mk.Направление != 'ПТ' and naryad.Внеплан = 0"""
    dict_rez = dict()
    responce = CSQ.custom_request_c(self.bd_naryad,query,rez_dict=True)
    set_napr = set()
    for item in responce:
        set_napr.add(item['Направление'])
    list_napr = sorted(list(set_napr))
    dict_shabl_napr = dict()

    for napr in list_napr:
        dict_shabl_napr[napr] = {'val_abs':0,'val':0,'count':0}
    for item in responce:
        fl_add = True
        list_oper =[_.split("$")[-1] for _ in item['Операции'].split("|")]
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
        delta_abs = abs(tvrem - fvrem)/tvrem*100
        delta = (tvrem - fvrem)/tvrem*100
        if delta_abs < 200:
            dict_rez[month][item['Направление']]['val_abs'] += delta_abs
            dict_rez[month][item['Направление']]['val'] += delta
            dict_rez[month][item['Направление']]['count'] += 1
        else:
            print(f"{item['Пномер']} - abs {delta_abs}" )
    rez = []
    for month in dict_rez.keys():
        tmp_line = {'Месяц':month}
        summ_napr = 0
        summ_napr_abs = 0
        count_summ_napr = 0
        for napr in dict_rez[month]:
            tmp_line[f'{napr}_абс'] = round(dict_rez[month][napr]['val_abs']/dict_rez[month][napr]['count'])
            tmp_line[f'{napr}'] = round(dict_rez[month][napr]['val'] / dict_rez[month][napr]['count'])
            summ_napr+=dict_rez[month][napr]['val']/dict_rez[month][napr]['count']
            summ_napr_abs += dict_rez[month][napr]['val_abs'] / dict_rez[month][napr]['count']
            count_summ_napr+=1
        summ_napr = round(summ_napr/count_summ_napr)
        summ_napr_abs = round(summ_napr_abs/count_summ_napr)
        tmp_line[f'Среднее'] = summ_napr
        tmp_line[f'Среднее_абс'] = summ_napr_abs
        rez.append(tmp_line)
    rez = F.list_of_dicts_to_list_of_lists(rez)
    create_gant(self, rez)
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
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
def jurnal_rabot(self, data_nach, data_kon, *args):
    custom_request_c = f"""SELECT mk.Номер_проекта, mk.Номер_заказа, jurnal.Дата, jurnal.ФИО AS "ФИО_журнал", jurnal.ФИО AS "Должность", jurnal.Статус, 
            jurnal.Подытог, jurnal.Номер_наряда, jurnal.Примечание AS "Примеч_журнал", 
            naryad.Твремя, naryad.Пномер as "Наряд_пномер", 
            naryad.ФИО, naryad.Фвремя, naryad.ФИО2, 
            naryad.Фвремя2, naryad.Задание, naryad.Примечание AS "Примеч_наряд", 
            naryad.Номер_мк, naryad.Внеплан FROM jurnal 
            INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
            INNER JOIN mk ON naryad.Номер_мк == mk.Пномер 
            WHERE datetime(jurnal.Дата) > datetime("{data_nach}") 
            and datetime(jurnal.Дата) < datetime("{data_kon}") """

    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True)
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
    list_tables = CSQ.get_list_of_tables_c(self.bd_users)
    max_date = 'm_2000_06_01'
    for table in list_tables:
        if F.is_date(table, "m_%Y_%m_%d"):
            if F.strtodate(table, "m_%Y_%m_%d") > F.strtodate(max_date, "m_%Y_%m_%d"):
                max_date = table
    max_date_dt = F.strtodate(max_date, "m_%Y_%m_%d")
    if F.strtodate(self.ui.le_end_of_period_c.text(), "%Y-%m-%d %H:%M:%S") > max_date_dt:
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
        vivod_gant(self, fig, self.browser)
    except:
        CQT.msgbox(f'Проблема с выводом графика')
    return rez_spis

@CQT.onerror
def ponedelniy_grafik_vir_otgr(self, data_nach, data_kon, etap, *args):
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
            poizvodit = round((vir / 5) / posesh,2)
        rez.append([tmp_data_nach, tmp_data_kon, vir, round(ves * KOEFF_TKANI), ves_tehn,
                    f'{round(100 * (ves_tehn + 1) / (vir + 1), 1)}%', posesh / 2, poizvodit])
        rez_gr.append([tmp_data_nach.split()[0], tmp_data_kon.split()[0], vir, round(ves /100,2), ves_tehn,
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
    GR.load_elements(self, rez_gr,'Понедельный график выработки и отгрузок')
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
        fio_rc = self.raschet_etapa(naryad['ФИО'])
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

    # PROIZVODITELNOST = 34
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
        fio_rc = self.raschet_etapa(naryad['ФИО'])
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
        #ves_tehn = ves_tehnolohicheskiy(self, mk[0], mk[1], mk[2], conn=conn, conn_mat=conn_mat)
        ves_tehn = 0
        summ_ves_tehn += ves_tehn

    return vir, ves, round(summ_ves_tehn)


@CQT.onerror
def virabotka_sotrudnikov_po_pologeniy(self, data_nach, data_kon, etap, *args):
    spis_vir_sotr, err = CMS.calc_productivity_cabotki(data_nach, F.bdcfg('BD_users'), F.bdcfg('Naryad'), F.bdcfg('BDact'),
                                               F.load_file(F.scfg('BDact') + F.sep() + 'employee.txt'))
    if spis_vir_sotr == '':
        print(err)
        return ''
    rez = [['ФИО', 'Профес.', 'Процент', "Вычет", "Список нарядов", "Сумм. часов", "Список актов", "Ставка, часов"]]
    for i in range(1, len(spis_vir_sotr)):
        fio_rc = self.raschet_etapa(spis_vir_sotr[i][0])
        if fio_rc == None:
            continue
        if fio_rc[:4] == self.ui.cmb_podrazdelenie.currentText()[:4]:
            dop_min = CMS.extra_time_unworked_between_task_c(self, spis_vir_sotr[i][0], data_nach, data_kon)
            rez_time = round((spis_vir_sotr[i][5] * 60 + dop_min) * 200 / (spis_vir_sotr[i][7] * 60))
            if rez_time == 0:
                print(f'!+++++++++++ Для {spis_vir_sotr[i][0]} доп время 0')
            else:
                print(f'Для {spis_vir_sotr[i][0]} доп время {rez_time}')
            spis_vir_sotr[i][2] = rez_time
            rez.append(spis_vir_sotr[i])
            rez = F.sort_by_column_c(rez, 'Процент')
    return rez


@CQT.onerror
def virabotka_sotrudnikov(self, data_nach, data_kon, etap, *args):
    spis_vir_sotr, err = CMS.calc_productivity_c(data_nach, F.bdcfg('BD_users'), F.bdcfg('Naryad'), F.bdcfg('BDact'),
                                         self.DICT_EMPLOEE)
    if spis_vir_sotr == '':
        print(err)
        return ''
    rez = [
        ['ФИО', 'Профес.', 'Процент', "Вычет", "Список нарядов", "Сумм. часов", "Список актов", "Ставка, часов", 'ves']
    ]
    for i in range(1, len(spis_vir_sotr)):
        fio_rc = self.raschet_etapa(spis_vir_sotr[i][0])
        if fio_rc == None:
            continue
        if fio_rc[:4] == self.ui.cmb_podrazdelenie.currentText()[:4]:
            dop_min = 0
            dop_min = CMS.extra_time_unworked_between_task_c(self, spis_vir_sotr[i][0], data_nach, data_kon)
            rez_time = round((spis_vir_sotr[i][5] * 60 + dop_min) * 200 / (spis_vir_sotr[i][7] * 60))
            if dop_min == 0:
                print(f'!+++++++++++ Для {spis_vir_sotr[i][0]} доп время 0')
            else:
                print(f'Для {spis_vir_sotr[i][0]} доп время {dop_min}')
            spis_vir_sotr[i][2] = rez_time
            rez.append(spis_vir_sotr[i])
            rez = F.sort_by_column_c(rez, 'Процент')
    return rez


@CQT.onerror
def virabotka_sotr_po_pologeniy(self, data_nach, data_kon, empl, *args):
    KOEF_SVERHNORMI = 2
    custom_request_c = f"""SELECT mk.Номер_проекта, mk.Номер_заказа, jurnal.Дата, jurnal.ФИО AS "ФИО_журнал", jurnal.Статус, 
                jurnal.Подытог, jurnal.Номер_наряда, jurnal.Примечание AS "Примеч_журнал", 
                naryad.Твремя, naryad.Твремя AS "Итог_Твремя", 
                naryad.ФИО, naryad.Фвремя, naryad.ФИО2, 
                naryad.Фвремя2, naryad.Задание, naryad.Примечание AS "Примеч_наряд", 
                naryad.Номер_мк, naryad.Внеплан, naryad.Коэфф_сложности, "" AS "Коэфф_вых", naryad.Подтвержд_вып FROM jurnal 
                INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
                INNER JOIN mk ON naryad.Номер_мк == mk.Пномер 
                WHERE jurnal.ФИО == "{CMS.name_by_empl_c(empl)}" AND datetime(jurnal.Дата) > datetime("{data_nach}") 
                and datetime(jurnal.Дата) < datetime("{data_kon}") AND jurnal.Номер_наряда in (SELECT jurnal.Номер_наряда FROM jurnal WHERE jurnal.ФИО == "{CMS.name_by_empl_c(empl)}" AND datetime(jurnal.Дата) > datetime("{data_nach}") 
                and datetime(jurnal.Дата) < datetime("{data_kon}") AND jurnal.Статус == "Завершен")"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True)
    if rez_jur == []:
        CQT.msgbox('Пусто')
        return
    table_name = data_nach.split()[0].replace('-', '_')
    custom_request_c = F'''SELECT * FROM m_{table_name}'''
    tabel = CSQ.custom_request_c(F.bdcfg('BD_users'), custom_request_c)
    if tabel == '':
        print('Не найден табель')
        raise ('Err')
    nk_fio2 = F.num_col_by_name_in_hat_c(rez_jur, 'ФИО2')
    nk_fact2 = F.num_col_by_name_in_hat_c(rez_jur, 'Фвремя2')
    nk_fio = F.num_col_by_name_in_hat_c(rez_jur, 'ФИО')
    nk_fact = F.num_col_by_name_in_hat_c(rez_jur, 'Фвремя')
    nk_status = F.num_col_by_name_in_hat_c(rez_jur, 'Статус')
    nk_tvrem = F.num_col_by_name_in_hat_c(rez_jur, 'Твремя')
    nk_nom_nar = F.num_col_by_name_in_hat_c(rez_jur, 'Номер_наряда')
    nk_prim_jur = F.num_col_by_name_in_hat_c(rez_jur, 'Примеч_журнал')
    nk_zadan = F.num_col_by_name_in_hat_c(rez_jur, 'Задание')
    nk_np = F.num_col_by_name_in_hat_c(rez_jur, 'Номер_проекта')
    nk_data = F.num_col_by_name_in_hat_c(rez_jur, 'Дата')
    nk_koef_slojn = F.num_col_by_name_in_hat_c(rez_jur, 'Коэфф_сложности')
    nk_koef_vih = F.num_col_by_name_in_hat_c(rez_jur, 'Коэфф_вых')
    nk_vneplan = F.num_col_by_name_in_hat_c(rez_jur, 'Внеплан')
    nk_podtv_m = F.num_col_by_name_in_hat_c(rez_jur, 'Подтвержд_вып')
    nk_itog_tvrema = F.num_col_by_name_in_hat_c(rez_jur, 'Итог_Твремя')
    set_nar = set()
    summ_tvr = 0
    summ_tvr_bez_koef = 0
    summ_tvr_bez_koef_max = 0
    summ_tvr_max = 0
    summ_fvr = 0
    mes_norma = calc_month_rates_c(tabel)
    for i in range(1, len(rez_jur)):

        if rez_jur[i][nk_fio2] == CMS.name_by_empl_c(empl):
            rez_jur[i][nk_fio] = rez_jur[i][nk_fio2]
            rez_jur[i][nk_fact] = rez_jur[i][nk_fact2]
        if rez_jur[i][nk_status] != 'Завершен' or rez_jur[i][nk_nom_nar] in set_nar:
            rez_jur[i][nk_tvrem] = 0
            rez_jur[i][nk_fact] = 0
            rez_jur[i][nk_itog_tvrema] = 0
            # rez_jur[i][nk_nom_nar] = ''
        else:
            set_nar.add(rez_jur[i][nk_nom_nar])
            rez_jur[i][nk_koef_vih] = 1

            koef_sverh_max = 1
            if rez_jur[i][nk_vneplan] != 1 and rez_jur[i][nk_podtv_m] == 1:
                summ_tvr_bez_koef += rez_jur[i][nk_tvrem]
                if summ_tvr_bez_koef > mes_norma:
                    rez_jur[i][nk_koef_vih] = KOEF_SVERHNORMI
                summ_tvr += rez_jur[i][nk_tvrem] * rez_jur[i][nk_koef_slojn] * rez_jur[i][nk_koef_vih]
                rez_jur[i][nk_itog_tvrema] = rez_jur[i][nk_tvrem] * rez_jur[i][nk_koef_slojn] * rez_jur[i][nk_koef_vih]

            summ_tvr_bez_koef_max += rez_jur[i][nk_tvrem]
            if summ_tvr_bez_koef_max > mes_norma:
                koef_sverh_max = KOEF_SVERHNORMI
            summ_tvr_max += rez_jur[i][nk_tvrem] * rez_jur[i][nk_koef_slojn] * koef_sverh_max

            summ_fvr += F.valm(rez_jur[i][nk_fact])

    rez_jur.append(['' for _ in rez_jur[0]])
    rez_jur[-1][nk_np] = f'ПОДЫТОГ:'
    if mes_norma == 0:
        eff = 0
        prem = 0
        prem_max = 0
    else:
        dop_min = CMS.extra_time_unworked_between_task_c(self, CMS.name_by_empl_c(empl), data_nach, data_kon)
        eff = round(summ_fvr / miutes * 100)
        prem = round((summ_tvr + dop_min) / miutes * 200)
        prem_max = round((summ_tvr_max + dop_min) / miutes * 200)
    rez_jur[-1][nk_data] = f'Эффективность {eff}%'
    rez_jur[-1][nk_prim_jur] = f'по табелю {mes_norma} мин.'
    if prem < 100:
        prem = 100
    rez_jur[-1][nk_zadan] = f'Премия({prem}%  без учета брака)'
    rez_jur[-1][nk_podtv_m] = f'Премия max {prem_max}% (внеплан+подтвержд)'
    rez_jur.append(['' for _ in rez_jur[0]])
    rez_jur = F.delete_column(rez_jur, ['ФИО_журнал', 'ФИО', 'ФИО2', 'Фвремя2'])
    return rez_jur


@CQT.onerror
def virabotka_sotr(self, data_nach, data_kon, empl, *args):
    custom_request_c = f"""SELECT mk.Номер_проекта, mk.Номер_заказа, jurnal.Дата, jurnal.ФИО AS "ФИО_журнал", jurnal.Статус, 
                jurnal.Подытог, jurnal.Номер_наряда, jurnal.Примечание AS "Примеч_журнал", 
                naryad.Твремя, 
                naryad.ФИО, naryad.Фвремя, naryad.ФИО2, 
                naryad.Фвремя2, naryad.Задание, naryad.Примечание AS "Примеч_наряд", 
                naryad.Номер_мк, naryad.Внеплан, naryad.Коэфф_сложности, "" AS "Коэфф_вых", naryad.Подтвержд_вып FROM jurnal 
                INNER JOIN naryad ON jurnal.Номер_наряда == naryad.Пномер 
                INNER JOIN mk ON naryad.Номер_мк == mk.Пномер 
                WHERE jurnal.ФИО == "{CMS.name_by_empl_c(empl)}" AND datetime(jurnal.Дата) >= datetime("{data_nach}") 
                and datetime(jurnal.Дата) <= datetime("{data_kon}") AND 
                jurnal.Номер_наряда in (SELECT jurnal.Номер_наряда FROM jurnal WHERE jurnal.ФИО == "{CMS.name_by_empl_c(empl)}" AND datetime(jurnal.Дата) >= datetime("{data_nach}") 
                and datetime(jurnal.Дата) <= datetime("{data_kon}") AND jurnal.Статус == "Завершен")"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True)
    if rez_jur == [] or rez_jur == False:
        CQT.msgbox('Пусто')
        return

    table_name = F.start_end_dates_c(data_nach, vid='m')[0].split()[0].replace('-', '_')
    custom_request_c = F'''SELECT * FROM m_{table_name}'''
    if custom_request_c == False:
        CQT.msgbox(f'Не найдена таблица {table_name}')
        return
    tabel = CSQ.custom_request_c(F.bdcfg('BD_users'), custom_request_c)
    if tabel == '':
        print('Не найден табель')
        raise ('Err')
    nk_fio2 = F.num_col_by_name_in_hat_c(rez_jur, 'ФИО2')
    nk_fact2 = F.num_col_by_name_in_hat_c(rez_jur, 'Фвремя2')
    nk_fio = F.num_col_by_name_in_hat_c(rez_jur, 'ФИО')
    nk_fact = F.num_col_by_name_in_hat_c(rez_jur, 'Фвремя')
    nk_tvrem = F.num_col_by_name_in_hat_c(rez_jur, 'Твремя')
    nk_nom_nar = F.num_col_by_name_in_hat_c(rez_jur, 'Номер_наряда')
    nk_prim_jur = F.num_col_by_name_in_hat_c(rez_jur, 'Примеч_журнал')
    nk_zadan = F.num_col_by_name_in_hat_c(rez_jur, 'Задание')
    nk_np = F.num_col_by_name_in_hat_c(rez_jur, 'Номер_проекта')
    nk_data = F.num_col_by_name_in_hat_c(rez_jur, 'Дата')
    nk_koef_slojn = F.num_col_by_name_in_hat_c(rez_jur, 'Коэфф_сложности')
    nk_koef_vih = F.num_col_by_name_in_hat_c(rez_jur, 'Коэфф_вых')
    nk_vneplan = F.num_col_by_name_in_hat_c(rez_jur, 'Внеплан')
    nk_podtv_m = F.num_col_by_name_in_hat_c(rez_jur, 'Подтвержд_вып')
    nk_prim_nar = F.num_col_by_name_in_hat_c(rez_jur, 'Примеч_наряд')
    set_nar = set()
    summ_tvr = 0
    summ_tvr_max = 0
    summ_fvr = 0
    for i in range(1, len(rez_jur)):
        if rez_jur[i][nk_fio2] == CMS.name_by_empl_c(empl):
            rez_jur[i][nk_fio] = rez_jur[i][nk_fio2]
            rez_jur[i][nk_fact] = rez_jur[i][nk_fact2]
        if rez_jur[i][nk_nom_nar] in set_nar:
            rez_jur[i][nk_tvrem] = 0
            rez_jur[i][nk_fact] = 0
            # rez_jur[i][nk_nom_nar] = ''
        else:
            if rez_jur[i][nk_tvrem] == '':
                CQT.msgbox(f'Наряд {rez_jur[i][nk_nom_nar]} не отнормирован./ ПРОСТОЙ по заврешении нормируется.')
                rez_jur[i][nk_tvrem] = 0
            set_nar.add(rez_jur[i][nk_nom_nar])
            rez_jur[i][nk_koef_vih] = koeff_holy(rez_jur, rez_jur[i][nk_nom_nar], tabel)
            if rez_jur[i][nk_vneplan] != 1 and rez_jur[i][nk_podtv_m] == 1:
                summ_tvr += rez_jur[i][nk_tvrem] * rez_jur[i][nk_koef_slojn] * rez_jur[i][nk_koef_vih]
                print(
                    f'{rez_jur[i][nk_tvrem]} == {rez_jur[i][nk_tvrem] * rez_jur[i][nk_koef_slojn] * rez_jur[i][nk_koef_vih]}')
            else:
                print(
                    f'не учтён {rez_jur[i][nk_tvrem]} == {rez_jur[i][nk_tvrem] * rez_jur[i][nk_koef_slojn] * rez_jur[i][nk_koef_vih]}')
            summ_tvr_max += rez_jur[i][nk_tvrem] * rez_jur[i][nk_koef_slojn] * rez_jur[i][nk_koef_vih]
            summ_fvr += F.valm(rez_jur[i][nk_fact])

    rez_jur.append(['' for _ in rez_jur[0]])
    miutes = CMS.time_by_repo_card_c(empl, data_kon)
    rez_jur[-1][nk_np] = f'ПОДЫТОГ:'
    dop_min = 0
    if miutes == 0:
        eff = 0
        prem = 0
        prem_max = 0
    else:
        dop_min = CMS.extra_time_unworked_between_task_c(self, CMS.name_by_empl_c(empl), data_nach, data_kon)
        eff = round(summ_fvr / miutes * 100)
        prem = round((summ_tvr + dop_min) / miutes * 200)
        prem_max = round((summ_tvr_max + dop_min) / miutes * 200)
    rez_jur[-1][nk_data] = f'Эффективность {eff}%'
    rez_jur[-1][nk_prim_jur] = f'По табелю {round(miutes / 60, 1)} час.'
    if prem < 100:
        prem = 100
    rez_jur[-1][nk_zadan] = f'Премия {prem}% (включая 100% оклад, без учета брака)'
    rez_jur[-1][nk_podtv_m] = f'Премия max {prem_max}% (внеплан+подтвержд)'
    rez_jur[-1][nk_prim_nar] = f'Доп. час. {round(dop_min / 60, 1)}'
    rez_jur[-1][nk_koef_vih] = f'Общ. итог {round((summ_tvr + dop_min) / 60, 1)} час.'
    rez_jur.append(['' for _ in rez_jur[0]])
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

    ponaryadno = [['Проект', 'Вeс_мк', 'Номер_наряда', 'Твремя_мин', f'кг_наряд({PROIZVODITELNOST} пр-ть)', 'Фвремя_мин', "Примечание", "Категория_внепл", "Вид",'Направление']]
    for oper in list_oper:
        ponaryadno[0].append(oper)
    set_weight_MK_c = set()
    for naryad in rez_jur:
        fio_rc = self.raschet_etapa(naryad['ФИО'])
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
            #custom_request_c = f"""SELECT Дата_завершения,Вес,Направление,Номер_проекта,Номер_заказа FROM mk WHERE Пномер == {naryad['Номер_мк']}"""
            #rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True, one=True)
            tmp = [nppy,ves, naryad['Номер_наряда'],
                   naryad['Твремя'], round(PROIZVODITELNOST * naryad['Твремя'] / minut_smen),
                   F.valm(vrem_fact), naryad['Примечание'], naryad['Категория_внепл'], naryad['Вид'], naryad['Направление']]
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
                    tmp[nk_oper] = round(tmp[nk_oper]+ F.valm(time_oper)/count_executors,2)
            
            ponaryadno.append(tmp)
    ponaryadno.append(['' for _ in ponaryadno[0]])
    ponaryadno.append(['' for _ in ponaryadno[0]])
    return ponaryadno


def plan_fact_grafic_mes(self, data_nach, data_kon, *args):
    def clac_fio_for_pfanal(self, fio, summ_ves_vir_vneplan, time):
        if fio != '' and fio in self.DICT_EMPLOEE:
            prof = self.DICT_EMPLOEE[fio]
            if prof in self.DICT_PROFESSIONS_NAME:
                if self.DICT_PROFESSIONS_NAME[prof]['этап'] == 'Сборка+сварка':
                    summ_ves_vir_vneplan += F.valm(time)
        return summ_ves_vir_vneplan

    self.DICT_NN_NTK = CMS.load_dict_dse(self.db_dse)

    list_month_plan = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM mnts_plan WHERE 
            datetime(Дата) >= datetime("{data_nach}") 
            and datetime(Дата) < datetime("{data_kon}")""", rez_dict=True)
    list_month_fact = CSQ.custom_request_c(self.bd_naryad, """SELECT * FROM mk WHERE Дата_завершения != '' """, rez_dict=True)

    dict_cat_vnepl = dict()
    list_kat_vnepl = CSQ.custom_request_c(self.bd_naryad, f"""SELECT value FROM kategor_vnepl WHERE kod > 0""", one_column=True,
                                hat_c=False)
    rez = [['Месяц', 'План, н-см.', 'Отгрузка, т.(со скелетами)', 'Факт, н-см.', 'Внеплан, %', 'Сумм. Факт, н-см.']]
    for item in list_month_plan:
        summ_ves = 0
        data = item['Дата']
        ves_pl = 0
        for vid_tmp in self.DICT_NAPRAVL.keys():
            if vid_tmp in item:
                ves_pl += item[vid_tmp]
        for mk in list_month_fact:
            dat_str = mk['Дата_завершения']
            dat_f = F.start_end_dates_c(F.strtodate(dat_str, "%Y-%m-%d %H:%M:%S"), '', vid='m', format_out="%Y-%m-%d")[
                    0]
            if dat_f == data:
                summ_ves += mk['Вес'] * KOEF_RASKLADKI
        nach_data, kon_data = F.start_end_dates_c(F.strtodate(data, "%Y-%m-%d"), '', vid='m',
                                              format_out="%Y-%m-%d %H:%M:%S")

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

        list_zav_nar_po = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)
        summ_ves_vir = 0
        summ_ves_vir_vneplan = 0

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
            if item['Внеплан'] == 2:
                if item['Виды_работ'] == "":
                    summ_ves_vir_vneplan = clac_fio_for_pfanal(self, item['ФИО'], summ_ves_vir_vneplan, item['Твремя'])
                    summ_ves_vir_vneplan = clac_fio_for_pfanal(self, item['ФИО2'], summ_ves_vir_vneplan, item['Твремя'])
                else:
                    if item['Виды_работ'] in self.DICT_VID_RABOT:
                        if self.DICT_VID_RABOT[item['Виды_работ']]['этап'] == 'Сборка+сварка':
                            summ_ves_vir_vneplan += F.valm(item['Твремя']) * bool(item['ФИО'])
                            summ_ves_vir_vneplan += F.valm(item['Твремя']) * bool(item['ФИО2'])

        summ_ves_vir = summ_ves_vir / 480
        summ_ves_vir_vneplan = summ_ves_vir_vneplan / 480
        summ_ves_fact = summ_ves_vir + summ_ves_vir_vneplan
        k = 0
        summ_ves_vir_vneplan_proc = round(100* summ_ves_vir_vneplan/summ_ves_fact)
        if summ_ves_vir > 0:
            k = summ_ves_fact / summ_ves_vir
     #rez = [['Месяц','План, н-см.',                    'Отгрузка, т.(со скелетами)', '     Факт, н-нед.',  'Внеплан, н-нед.', 'Сумм. Факт, н-нед.']]
        tmp = [data,   round(ves_pl / PROIZVODITELNOST), round(summ_ves / 1000, 2), round(summ_ves_vir * KOEF_VNEPLANA),
               summ_ves_vir_vneplan_proc, round(summ_ves_fact*KOEF_VNEPLANA)]

        rez.append(tmp)

    load_browser(self)
    create_gant(self,rez)

    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez


def calc_tehpodgotovka_per_month(bd_naryad,bd_users,db_resxml,db_dse, data_nach, data_kon,tip, *args):
    query = f"""SELECT * FROM jurnal_td WHERE Статус == 'Создание'"""
    DICT_DSE = F.deploy_dict_c(CSQ.custom_request_c(db_dse, query, rez_dict=True), 'ДСЕ')
    query = f"""SELECT mk.Пномер, mk.Дата, mk.Направление, mk.Вес, mk.Количество FROM mk 
        WHERE  date(strftime('%Y-%m-%d','20'||Дата)) > date("{data_nach}") 
                        and date(strftime('%Y-%m-%d','20'||Дата)) < date("{data_kon}")"""
    dict_rez_napr = dict()
    dict_rez_users = dict()
    responce = CSQ.custom_request_c(bd_naryad, query, rez_dict=True)
    tmp_dict_napr = {_['Направление'] :
                         {'операций':0,'переходов':0,'материалов':0,'документов':0,'инструмента':0,'оснастки':0, 'дсе': 0} for _ in responce }

    dict_zamech = CSQ.custom_request_c(bd_naryad,f"""SELECT МК, Код from zamech WHERE Код in (4,5,6,8) AND Виновное_подразделение = '030000' and Код_вп in (1,3,4)""",rez_dict=True)
    DICT_VES_ZAMECH = {4:20,5:20,6:20,8:20}#100 проц

    dict_date_vih = CMS.dict_calend_days(bd_users)



    for item in responce:
        date_month = F.datetostr(F.strtodate(item['Дата'], "%y-%m-%d"), "%Y-%m")
        
        if 'за год' in tip: 
            month = F.datetostr(F.strtodate(item['Дата'],"%y-%m-%d"),"%Y")
            mask = "%Y"
        else:
            month = date_month
            mask = "%Y-%m"


        if month not in dict_rez_napr:
            rab_dney = 0
            for day in dict_date_vih:
                day_dat =F.datetostr(F.strtodate(day, 'd_%Y_%m_%d'), mask)
                if day_dat == date_month:
                    if dict_date_vih[day] == 0:
                        rab_dney += 1

            dict_rez_napr[month] = {'rab_dn':rab_dney,'napr':copy.deepcopy(tmp_dict_napr)}
            dict_rez_users[month] = {'rab_dn':rab_dney,'users':dict()}
    dict_count_dse_per_napr = {'КЛ':{'дсе':0,'мк':0, 'вес_ед':0},'КТ':{'дсе':0,'мк':0, 'вес_ед':0},'ШГ':{'дсе':0,'мк':0, 'вес_ед':0},'ПР':{'дсе':0,'мк':0, 'вес_ед':0}}
    for item in responce:
        date_mk= F.strtodate(item['Дата'],"%y-%m-%d")
        month = F.datetostr(date_mk,"%Y-%m")
        if 'за год' in tip: 
            month = F.datetostr(date_mk,"%Y")
        nom_mk = int(item['Пномер'])
        count_zamech = 0
        for item_zamech in dict_zamech:
            if item_zamech['МК'] == nom_mk:
                count_zamech += DICT_VES_ZAMECH[item_zamech['Код']]
        if count_zamech > 80:
            count_zamech = 80
        koef_vichet_zam = 1- count_zamech/100
        print(f'МК {nom_mk} вычет на ТК {count_zamech}%')
        napr = item['Направление']
        dict_count_dse_per_napr[napr]['мк'] +=1
        #ves_ed = item['Вес']/item['Количество']
        dict_count_dse_per_napr[napr]['вес_ед'] += item['Вес']
        custom_request_c = f"""SELECT data FROM res WHERE Номер_мк == {nom_mk}"""
        rez = CSQ.custom_request_c(db_resxml, custom_request_c)
        if rez == None or rez == False:
            print(f'ресурсная для {nom_mk} не найдена')
            continue
        res = F.from_binary_pickle(rez[-1][0])
        if res == None:
            print(f'ресурсная для {nom_mk} не распознана')
            continue
        dict_users_from_mk = dict()
        dse_count = 0


        for dse in res:
            dict_count_dse_per_napr[napr]['дсе'] +=1
            oper_count = 0
            pereh_count = 0
            mat_count = 0
            docum_count = 0
            instr_count = 0
            osnast_count = 0
            name = dse['Номенклатурный_номер']
            if name not in DICT_DSE:
                print(
                    f"{name} не считается не найдена в журнале")
                continue
            koef_30d = 1
            if F.strtodate(DICT_DSE[name]['Дата']) < F.date_add_days(date_mk,-30, format_out=''):
                print(f"{name} koef = 0,05 сделана {F.strtodate(DICT_DSE[name]['Дата'])} ранее чем мк {F.date_add_days(date_mk,-30, format_out='')}")
                koef_30d = 0.05

            date_day = F.datetostr(F.strtodate(DICT_DSE[name]['Дата']), 'd_%Y_%m_%d')
            if date_day not in dict_date_vih:
                print(f'{date_day} не найден в табеле')
                raise 'err'
            if 'будни' in tip:
                if dict_date_vih[date_day]:
                    print(f" {name} не считается сделана {DICT_DSE[name]['Дата']} в выходной")
                    continue
            if 'выходные' in tip:
                if not dict_date_vih[date_day]:
                    print(f" {name} не считается сделана {DICT_DSE[name]['Дата']} в будни")
                    continue

            name_user = DICT_DSE[name]['ФИО']
            for oper in dse['Операции']:
                oper_count +=1*koef_30d*koef_vichet_zam
                pereh_count+= len(oper['Переходы'])*koef_30d*koef_vichet_zam
                mat_count += len(oper['Материалы'])*koef_30d*koef_vichet_zam
                docum_count += len(oper['Опер_документы'])*koef_30d*koef_vichet_zam
                instr_count += len(oper['Опер_инстумент'])*koef_30d*koef_vichet_zam
                osnast_count += len(oper['Опер_оснастка'])*koef_30d*koef_vichet_zam
            if name_user not in dict_users_from_mk:
                dict_users_from_mk[name_user] = {'операций':0,'переходов':0,'материалов':0,'документов':0,'инструмента':0,'оснастки':0, 'дсе': 0, 'days':dict()}
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
                dict_rez_users[month]['users'][user] = {'операций':0,'переходов':0,'материалов':0,'документов':0,'инструмента':0,'оснастки':0, 'дсе': 0, 'дсе_в_день': dict()}
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
            for day in  dict_rez_users[month]['users'][user]['дсе_в_день']:
                dse_per_day+= dict_rez_users[month]['users'][user]['дсе_в_день'][day]
            dse_per_day = round(dse_per_day/ len(dict_rez_users[month]['users'][user]['дсе_в_день']),1)
            dict_rez_users[month]['users'][user]['дсе_в_день'] = dse_per_day
    for napr in  dict_count_dse_per_napr:
        dict_count_dse_per_napr[napr]['aver'] = round(dict_count_dse_per_napr[napr]['дсе']/dict_count_dse_per_napr[napr]['мк'],2)
        dict_count_dse_per_napr[napr]['вес_ед']= round(dict_count_dse_per_napr[napr]['вес_ед']/dict_count_dse_per_napr[napr]['мк'],2)
    return dict_rez_users, dict_rez_napr

def virabotka_top(self:mywindow, data_nach, data_kon, tip ,*args):
    dict_users, dict_napr = calc_tehpodgotovka_per_month(self.bd_naryad, self.bd_users, self.db_resxml,self.db_dse,
                                                         data_nach, data_kon, tip, *args)
    if 'По направлениям' in tip:
        table_rez = [['Месяц','Направление']]
        set_keys = set()
        for month in dict_napr:
            for napr in dict_napr[month]['napr']:
                for key in dict_napr[month]['napr'][napr]:
                    set_keys.add(key)
        for key in sorted(list(set_keys)):
            table_rez[0].append(key)
        for month in dict_napr:
            for napr in dict_napr[month]['napr']:
                tmp_list = [month,napr]
                for field in table_rez[0][2:]:
                    if field in dict_napr[month]['napr'][napr]:
                        tmp_list.append(round(dict_napr[month]['napr'][napr][field],2))
                    else:
                        tmp_list.append(0)
                table_rez.append(tmp_list)
    if 'По сотрудникам'  in tip:
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
                        tmp_list.append(round(dict_users[month]['users'][user][field],2))
                    else:
                        tmp_list.append(0)
                table_rez.append(tmp_list)
    table_rez.append(['' for _ in table_rez[0]])
    table_rez.append(['' for _ in table_rez[0]])
    return table_rez
    
    
def udel_trud_sort_c(self:mywindow, data_nach, data_kon, *args):
    shablon_etaps = dict()
    rez = [['Код из бд','Выборка,шт.','Наименование (мин/кг)','кг_на_пост_см']]
    for oper in self.DICT_OPER_FULL.keys():
        etap  =self.DICT_OPER_FULL[oper]['etap']
        shablon_etaps[etap] = 0
    for etap in shablon_etaps:
        rez[0].append(etap)
    query = f"""SELECT DISTINCT naryad.Номер_мк, naryad.Пномер, naryad.Дата, naryad.Твремя, naryad.Фвремя, naryad.Фвремя2, 
        naryad.ФИО, naryad.ФИО2, mk.Направление, naryad.Опер_время, naryad.Операции, mk.Вес FROM naryad 
    INNER JOIN mk ON mk.Пномер == naryad.Номер_мк
    INNER JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер
    WHERE naryad.Подтвержд_вып == 1 AND datetime(naryad.Дата) > datetime("{data_nach}") 
                    and datetime(naryad.Дата) < datetime("{data_kon}") and mk.Направление != 'ПТ' and naryad.Внеплан = 0"""
    dict_rez = dict()
    responce = CSQ.custom_request_c(self.bd_naryad, query, rez_dict=True)

    query = f"""SELECT plan.МК, пл_топ.Вид FROM plan INNER JOIN пл_топ ON пл_топ.НомПл = plan.Пномер WHERE plan.МК != 0 AND пл_топ.Вид != 1"""
    dict_mk_sort_c = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, query, rez_dict=True),'МК')

    query = f"""SELECT Пномер, Имя FROM виды_по_напр"""
    dict_sort_c = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, query, rez_dict=True), 'Пномер')

    list_napr = sorted(list(dict_sort_c.keys()))
    dict_shabl_napr = dict()

    for napr in list_napr:
        dict_shabl_napr[napr] = copy.deepcopy(shablon_etaps)
        dict_shabl_napr[napr]['Вес'] = 0
        dict_shabl_napr[napr]['Кол'] = 0
    tmp_dict_mk = dict()
    for item in responce:
        if item['Номер_мк'] in dict_mk_sort_c:
            fvrem = F.valm(item['Фвремя']) + F.valm(item['Фвремя2'])
            tvrem = F.valm(item['Твремя']) * bool(item['ФИО']) + F.valm(item['Твремя']) * bool(item['ФИО2'])
            if fvrem == 0 or tvrem == 0:
                continue
            if item['Номер_мк'] not in tmp_dict_mk:
                tmp_dict_mk[item['Номер_мк']] = {'Вес':item['Вес'],'Вид': dict_mk_sort_c[item['Номер_мк']],'Этапы':copy.deepcopy(shablon_etaps)}
            koef = tvrem/fvrem
            list_oper = [_.split("$")[-1] for _ in item['Операции'].split("|")]
            list_time = [F.valm(_) for _ in item['Опер_время'].split("|")]
            for i in range(len(list_oper)):
                if list_oper[i] not in self.DICT_OPER_FULL:
                    continue
                etap = self.DICT_OPER_FULL[list_oper[i]]['etap']
                time_fact = list_time[i]/koef
                tmp_dict_mk[item['Номер_мк']]['Этапы'][etap]+=time_fact
    for mk in tmp_dict_mk.keys():
        ves = tmp_dict_mk[mk]['Вес']
        vid = tmp_dict_mk[mk]['Вид']
        dict_shabl_napr[vid]['Вес'] += ves
        dict_shabl_napr[vid]['Кол'] +=1
        for etap in tmp_dict_mk[mk]['Этапы'].keys():
            dict_shabl_napr[vid][etap] += tmp_dict_mk[mk]['Этапы'][etap]
    for vid in dict_shabl_napr.keys():
        ves = dict_shabl_napr[vid]['Вес']
        kol_vo = dict_shabl_napr[vid]['Кол']
        if ves == 0:
            continue
        tmp = [vid, kol_vo, dict_sort_c[vid], 0 ]
        for etap in dict_shabl_napr[vid].keys():
            if etap in ['Вес','Кол']:
                continue
            dict_shabl_napr[vid][etap] = round(dict_shabl_napr[vid][etap]/ ves,1)
            if etap == 'Сборка+сварка' and dict_shabl_napr[vid][etap] > 0:
                tmp[3] = round(960/ dict_shabl_napr[vid][etap])
        dict_shabl_napr[vid]['Вес'] = '*'
        
        for rez_etap in rez[0][4:]:
            tmp.append(dict_shabl_napr[vid][rez_etap])
        rez.append(tmp)
    #rez.append(['' for _ in rez[0]])
    #rez.append(['' for _ in rez[0]])
    return rez


def vneplan_po_napravl(self, data_nach, data_kon, vid, *args):
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

    list_month_plan = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM mnts_plan WHERE 
            datetime(Дата) >= datetime("{data_nach}") 
            and datetime(Дата) < datetime("{data_kon}")""", rez_dict=True)
    list_month_fact = CSQ.custom_request_c(self.bd_naryad, """SELECT * FROM mk WHERE Дата_завершения != '' """, rez_dict=True)
    rez = [['Месяц', 'Внеплан, н-см.']]
    dict_cat_vnepl = dict()
    list_kat_vnepl = CSQ.custom_request_c(self.bd_naryad, f"""SELECT value FROM kategor_vnepl WHERE kod > 0""", one_column=True,
                                hat_c=False)
    for kat in list_kat_vnepl:
        rez[0].append(kat)
        dict_cat_vnepl[kat] = 0
    for item in list_month_plan:

        for kat in dict_cat_vnepl.keys():
            dict_cat_vnepl[kat] = 0

        data = item['Дата']

        for mk in list_month_fact:

            if mk['Направление'] == vid or vid == 'Все':
                dat_str = mk['Дата_завершения']
                dat_f = F.start_end_dates_c(F.strtodate(dat_str, "%Y-%m-%d %H:%M:%S"), '', vid='m', format_out="%Y-%m-%d")[
                    0]

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
        tmp = [data, 
               round(summ_ves_vir_vneplan)]

        for kat in dict_cat_vnepl.keys():
            tmp.append(round(dict_cat_vnepl[kat] / 480))
        rez.append(tmp)

    # fig = GR.test()
   
    load_browser(self)
    create_gant(self,rez,vid)
    rez.append(['' for _ in rez[0]])
    rez.append(['' for _ in rez[0]])
    return rez



def plan_fact_mes(self, data_nach, data_kon, vid, *args):
    def clac_fio_for_pfanal(self, fio, summ_ves_vir_vneplan, time):
        if fio != '' and fio in self.DICT_EMPLOEE:
            prof = self.DICT_EMPLOEE[fio]
            if prof in self.DICT_PROFESSIONS_NAME:
                if self.DICT_PROFESSIONS_NAME[prof]['этап'] == 'Сборка+сварка':
                    summ_ves_vir_vneplan += F.valm(time)
        return summ_ves_vir_vneplan

    self.DICT_NN_NTK = CMS.load_dict_dse(self.db_dse)

    TUPLE_DOUBLE_SHOVOV = ('Т3', "Н2", "С7", "С12", "С14", "С15", "С16", "С43", "С21", "С45", "С23", "С25", "С26", "С27", "С39",
                           "С40","У5","У7","У8","У10","Т7","Т2","Т8","Т9","Т5",)

    list_month_plan = CSQ.custom_request_c(self.db_kplan,"""SELECT * FROM mnts_plan""",rez_dict=True)
    list_month_fact = CSQ.custom_request_c(self.bd_naryad, """SELECT * FROM mk WHERE Дата_завершения != '' """, rez_dict=True)
    rez = [['Месяц','План, н-см.','Отгрузка, кг.','Факт, н-см.','Внеплан, н-см.','Сумм. Факт, н-см.','Сумм св_швов, м.']]
    dict_cat_vnepl = dict()
    list_kat_vnepl = CSQ.custom_request_c(self.bd_naryad,f"""SELECT value FROM kategor_vnepl WHERE kod > 0""",one_column=True,hat_c=False)
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
                dat_f = F.start_end_dates_c(F.strtodate(dat_str,"%Y-%m-%d %H:%M:%S"),'', vid = 'm', format_out= "%Y-%m-%d")[0]
                if dat_f == data:
                    summ_ves += mk['Вес']
        nach_data, kon_data = F.start_end_dates_c(F.strtodate(data,"%Y-%m-%d"),'', vid = 'm', format_out= "%Y-%m-%d %H:%M:%S")
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
        list_zav_nar_po = CSQ.custom_request_c(self.bd_naryad,custom_request_c,rez_dict=True)
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
                                add_ = add_/2
                            summ_ves_vir += add_
                    if oper_name == 'Сварка':
                        dse_name, dse_nn = list_dse[i_o].split('$')
                        kol_vo_dse = F.valm(list_kolvo_dse[i_o])
                        name_file = self.DICT_NN_NTK[dse_nn]['Номер_техкарты'] + "_" + dse_nn + ".pickle"
                        path = F.sep().join([self.data_f,"MKart\data",str(item['Номер_мк']),name_file])
                        if F.existence_file_c(path):
                            tk = F.open_file_c(path,pickl=True)
                            for i_f in range(11,len(tk)):
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
                                                val_shva = F.valm(row_len[i_s])*2
                                            else:
                                                val_shva = F.valm(row_len[i_s])
                                            l_svar += val_shva * kol_vo_dse/1000
                                    else:
                                        print('Сварка' + str(values))
            if item['Внеплан'] == 2:
                if item['Виды_работ'] == "":
                    summ_ves_vir_vneplan = clac_fio_for_pfanal(self,item['ФИО'],summ_ves_vir_vneplan,item['Твремя'])
                    summ_ves_vir_vneplan = clac_fio_for_pfanal(self,item['ФИО2'], summ_ves_vir_vneplan, item['Твремя'])
                else:
                    if item['Виды_работ'] in self.DICT_VID_RABOT:
                        if self.DICT_VID_RABOT[item['Виды_работ']]['этап'] == 'Сборка+сварка':
                            summ_ves_vir_vneplan += F.valm(item['Твремя']) * bool(item['ФИО'])
                            summ_ves_vir_vneplan += F.valm(item['Твремя']) * bool(item['ФИО2'])
                            if item['Категория_внепл'] in dict_cat_vnepl:
                                dict_cat_vnepl[item['Категория_внепл']] += F.valm(item['Твремя']) * bool(item['ФИО'])
                                dict_cat_vnepl[item['Категория_внепл']] += F.valm(item['Твремя']) * bool(item['ФИО2'])
                

        summ_ves_vir = summ_ves_vir /480
        summ_ves_vir_vneplan = summ_ves_vir_vneplan/480
        summ_ves_fact = summ_ves_vir +summ_ves_vir_vneplan
        k = 0
        if summ_ves_vir> 0:
            k= summ_ves_fact/summ_ves_vir
        tmp = [data,round(ves_pl/PROIZVODITELNOST),round(summ_ves/100,3),round(summ_ves_vir),round(summ_ves_vir_vneplan),round(summ_ves_fact),round(l_svar*k)]
        for kat in dict_cat_vnepl.keys():
            tmp.append(round(dict_cat_vnepl[kat]/480))
        rez.append(tmp)
    GR.load_elements(self, rez,'План-фактный анализ по месяцам')
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
def trudozatraty(self, data_nach, data_kon, podrazd, *args):
    LIST_UNCHECK_PROF = ['Помощник оператора лазерных установок','Оператор лазерных установок', 'Инженер-технолог']
    @CQT.onerror
    def min_za_den_tabel(self, fiod, data, *args):
        name_table = F.datetostr(F.strtodate(data), 'mtdz_%Y_%m_01')
        day = F.datetostr(F.strtodate(data), 'd_%Y_%m_%d')
        if fiod not in self.DICT_EMPLOEE:
            return "Не найден"
        custom_request_c = f'''SELECT {day} FROM {name_table} WHERE ФИО == "{fiod} {self.DICT_EMPLOEE[fiod]}"; '''
        rez = CSQ.custom_request_c(F.bdcfg("BD_users"), custom_request_c)
        if rez == False or len(rez)==1:
            return "Не найден"
        return rez[-1][0] * 60

    self.PROC_OTKL_TRUDOZATRAT = [85, 110]

    custom_request_c = f"""SELECT ФИО,"" as Должность, "" as Подразделение, "" as Режим,  sum(Подытог) AS "Сумм_Минут"  
    FROM (SELECT * FROM jurnal WHERE Подытог <> 0 AND Статус = 'Начат' 
    and datetime(jurnal.Дата) > datetime("{data_nach}") 
    and datetime(jurnal.Дата) <= datetime("{data_kon}")) GROUP BY ФИО;"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
    for i in range(len(rez_jur)):
        minyt = min_za_den_tabel(self, rez_jur[i]['ФИО'], data_nach)
        rez_jur[i]["Табель_Минут"] = minyt
        if F.is_numeric(minyt) and minyt > 0:
            rez_jur[i]["МЕС_час"] = str(round(rez_jur[i]["Сумм_Минут"]/60,3)).replace('.',',')
            rez_jur[i]["Соответствие_%"] = round(rez_jur[i]["Сумм_Минут"] / rez_jur[i]["Табель_Минут"] * 100)
        else:
            rez_jur[i]["МЕС_час"] = '0'
            rez_jur[i]["Соответствие_%"] = 0
        if rez_jur[i]["ФИО"] in self.DICT_EMPLOEE_FULL:
            rez_jur[i]["Подразделение"] = self.DICT_EMPLOEE_FULL[rez_jur[i]["ФИО"]]["Подразделение"]
            rez_jur[i]["Режим"] = self.DICT_EMPLOEE_FULL[rez_jur[i]["ФИО"]]["Режим"]
            rez_jur[i]["Должность"] = self.DICT_EMPLOEE_FULL[rez_jur[i]["ФИО"]]["Должность"]
    rez_jur = F.list_of_dicts_to_list_of_lists(rez_jur)
    if rez_jur == [[]]:
        rez = [['ФИО','Должность','Подразделение','Режим','Сумм_Минут','Табель_Минут','МЕС_час','Соответствие_%']]
    else:
        rez = [rez_jur[0]]
    for item in rez_jur[1:]:
        if item[0] in self.DICT_EMPLOEE:
            fiod = f'{item[0]} {self.DICT_EMPLOEE[item[0]]}'
            if fiod not in self.DICT_EMPLOEE_RC:
                CQT.msgbox(f'{fiod} не назначен на рабочее место в Мкартах')
                continue
            if self.DICT_EMPLOEE_RC[f'{item[0]} {self.DICT_EMPLOEE[item[0]]}'][:4] == podrazd[:4]:
                rez.append(item)
    tmp_list_neycht = []
    for fiod in self.DICT_EMPLOEE_RC.keys():
        fio = ' '.join(fiod.split(' ')[:3])
        if fio not in self.DICT_EMPLOEE_FULL or str(self.DICT_EMPLOEE_FULL[fio]['Режим']) == 'Абстракт':
            continue
        if self.DICT_EMPLOEE_RC[fiod][:4] == podrazd[:4]:
            fl = True
            for i in range(1,len(rez)):
                if rez[i][0] == fio:
                    fl = False
                    break
            if fl == True:
                prof =  ''
                rejz = ''
                podr = ''
                if fio in self.DICT_EMPLOEE_FULL:
                    prof = self.DICT_EMPLOEE_FULL[fio]['Должность']
                    rejz = self.DICT_EMPLOEE_FULL[fio]['Режим']
                    podr = self.DICT_EMPLOEE_FULL[fio]['Подразделение']
                else:
                    prof = "Пномер в РМ: " + str(self.DICT_EMPLOEE_RM[fiod]['Пномер'])
                minyt = min_za_den_tabel(self, fio, data_nach)
                proc = 0
                if minyt == 0:
                    proc = 100
                if prof in LIST_UNCHECK_PROF:
                    proc = 100
                tmp_list_neycht.append([fio,prof,podr,rejz,0,minyt,0,proc])
        pass
    if len(rez[0]) >3:
        rez = F.sort_by_column_c(rez, rez[0][3])
    for item in tmp_list_neycht:
        rez.append(item)
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
        fio_rc = self.raschet_etapa(naryad['ФИО'])
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
def virabotka_ceha(self, data_nach, data_kon, etap, f_napravl=False, *args):
    minut_smen = 450

    # в ДБ с рейтин юсерз вписать рц чей работник, провести цикл на сравнение фамилий завершено с цехомю.
    custom_request_c = f"""SELECT jurnal.Дата, jurnal.ФИО as ФИОЖ, jurnal.Статус, jurnal.Номер_наряда, 
        naryad.Твремя, naryad.ДСЕ_ID, naryad.Операции, naryad.Опер_время, naryad.Номер_мк, naryad.Внеплан, naryad.ФИО as ФИО, naryad.ФИО2  as ФИО2,  
        naryad.Фвремя, naryad.Фвремя2, naryad.Примечание, naryad.Категория_внепл, mk.Вид FROM jurnal 
        INNER JOIN naryad ON jurnal.Номер_наряда = naryad.Пномер
        INNER JOIN mk ON mk.Пномер = naryad.Номер_мк
        WHERE jurnal.Статус == "Завершен"
    and datetime(jurnal.Дата) > datetime("{data_nach}") and datetime(jurnal.Дата) < datetime("{data_kon}") 
AND naryad.Внеплан != 1 AND naryad.Подтвержд_вып == 1"""
    rez_jur = CSQ.custom_request_c(self.bd_naryad, custom_request_c, hat_c=True, rez_dict=True)
    if rez_jur == []:
        CQT.msgbox('Пусто')
        return
    dict_napr_otgruz = dict()
    dict_napr_otgruz_proj = dict()
    dict_napr_zadel = dict()
    dict_napr_zadel_f = dict()
    dict_napr_zadel_proj = dict()
    dict_napr_vneplan = dict()
    dict_napr_vneplan_proj = dict()

    dict_napr_otgruz_mk = dict()
    dict_napr_zadel_mk = dict()
    dict_napr_vneplan_mk = dict()
    maska = ''
    vneplan = 0
    vneplan_set = set()
    set_napr = set()
    conn, cur = CSQ.connect_bd(self.bd_naryad)
    log_file = []
    for naryad in rez_jur:
        fio_rc = self.raschet_etapa(naryad['ФИО'])
        if fio_rc == None:
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
            custom_request_c = f"""SELECT Дата_завершения,Вид,Направление,Номер_проекта,Номер_заказа FROM mk WHERE Пномер == {naryad['Номер_мк']}"""
            rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, conn=conn, rez_dict=True, one=True)
            if f_napravl:
                try:
                    vid_izd = rez_mk['Направление']
                except:
                    continue
            else:
                vid_izd = rez_mk['Вид']
            set_napr.add(vid_izd)
            if naryad['Внеплан'] != 0:
                # ВНЕПЛАН
                if vid_izd not in dict_napr_vneplan_proj:
                    dict_napr_vneplan_proj[vid_izd] = {rez_mk['Номер_проекта'] + "$" + rez_mk['Номер_заказа']}
                if vid_izd not in dict_napr_vneplan_mk:
                    dict_napr_vneplan_mk[vid_izd] = {str(naryad['Номер_мк'])}
                dict_napr_vneplan_proj[vid_izd].add(rez_mk['Номер_проекта'] + "$" + rez_mk['Номер_заказа'])
                dict_napr_vneplan_mk[vid_izd].add(str(naryad['Номер_мк']))

                if vid_izd in dict_napr_vneplan:
                    dict_napr_vneplan[vid_izd] += naryad['Твремя']
                else:
                    dict_napr_vneplan[vid_izd] = naryad['Твремя']
            else:
                # ПО плану
                if vid_izd not in dict_napr_zadel_proj:
                    dict_napr_zadel_proj[vid_izd] = {rez_mk['Номер_проекта'] + "$" + rez_mk['Номер_заказа']}
                if vid_izd not in dict_napr_zadel_mk:
                    dict_napr_zadel_mk[vid_izd] = {str(naryad['Номер_мк'])}
                dict_napr_zadel_proj[vid_izd].add(rez_mk['Номер_проекта'] + "$" + rez_mk['Номер_заказа'])
                dict_napr_zadel_mk[vid_izd].add(str(naryad['Номер_мк']))

                if vid_izd in dict_napr_zadel:
                    dict_napr_zadel[vid_izd] += naryad['Твремя']
                    dict_napr_zadel_f[vid_izd] += F.valm(vrem_fact)
                else:
                    dict_napr_zadel[vid_izd] = naryad['Твремя']
                    dict_napr_zadel_f[vid_izd] = F.valm(vrem_fact)

            log_file.append([str(naryad)])

    custom_request_c = f"""SELECT Дата_завершения,Вид,Направление,Вес,Номер_проекта,Номер_заказа,Пномер FROM mk WHERE Статус == "Закрыта"
    and datetime(Дата_завершения) > datetime("{data_nach}") and datetime(Дата_завершения) < datetime("{data_kon}")"""
    rez_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, conn=conn, rez_dict=True)
    for mk in rez_mk:
        if f_napravl:
            vid_izd = mk['Направление']
        else:
            vid_izd = mk['Вид']
        set_napr.add(vid_izd)
        if vid_izd in dict_napr_otgruz:
            print(mk['Вес'])
            dict_napr_otgruz[vid_izd] += mk['Вес']
            dict_napr_otgruz_proj[vid_izd].add(mk['Номер_проекта'] + "$" + mk['Номер_заказа'])
            dict_napr_otgruz_mk[vid_izd].add(str(mk['Пномер']))
        else:
            dict_napr_otgruz[vid_izd] = mk['Вес']
            dict_napr_otgruz_proj[vid_izd] = {mk['Номер_проекта'] + "$" + mk['Номер_заказа']}
            dict_napr_otgruz_mk[vid_izd] = {str(mk['Пномер'])}
    CSQ.close_bd(conn)

    rez_spis = [
        ['Вид', "н.-см.", "кг.", 'Произв-ть, н.-см./см.', 'Проекты задел', 'МК задел', "Внеплан,н.-см.", "Внеплан, кг.",
         "Внеплан проекты", "МК внеплан", 'Сумма, кг.(Доля %)', "Завершено, кг.", 'Проекты завершено', 'МК завершено']]
    list_napr = sorted(list(set_napr))
    for key in list_napr:
        tmp = [key, 0, 0, 0, '', '', 0, 0, '', '', 0, 0, '', '']
        if key in dict_napr_zadel_proj and key in dict_napr_otgruz_proj:
            dict_napr_zadel_proj[key] = dict_napr_zadel_proj[key] - dict_napr_otgruz_proj[key]
        if key in dict_napr_vneplan_proj and key in dict_napr_otgruz_proj:
            dict_napr_vneplan_proj[key] = dict_napr_vneplan_proj[key] - dict_napr_otgruz_proj[key]
        if key in dict_napr_zadel_mk and key in dict_napr_otgruz_mk:
            dict_napr_zadel_mk[key] = dict_napr_zadel_mk[key] - dict_napr_otgruz_mk[key]
        if key in dict_napr_vneplan_mk and key in dict_napr_otgruz_mk:
            dict_napr_vneplan_mk[key] = dict_napr_vneplan_mk[key] - dict_napr_otgruz_mk[key]
        if key in dict_napr_zadel:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'н.-см.')] = round(dict_napr_zadel[key] / minut_smen, 1)
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'кг.')] = round(
                tmp[F.num_col_by_name_in_hat_c(rez_spis, 'н.-см.')] * PROIZVODITELNOST)
        if key in dict_napr_zadel_f:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'Произв-ть, н.-см./см.')] = round(
                tmp[F.num_col_by_name_in_hat_c(rez_spis, 'н.-см.')] / (dict_napr_zadel_f[key] / minut_smen), 2)
        if key in dict_napr_zadel_proj:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'Проекты задел')] = '; '.join(dict_napr_zadel_proj[key])
        if key in dict_napr_vneplan:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, "Внеплан,н.-см.")] = round(dict_napr_vneplan[key] / minut_smen, 1)
        if key in dict_napr_vneplan:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'Внеплан, кг.')] = round(
                dict_napr_vneplan[key] * PROIZVODITELNOST / minut_smen, 1)
        if key in dict_napr_vneplan_proj:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'Внеплан проекты')] = '; '.join(dict_napr_vneplan_proj[key])
        if key in dict_napr_otgruz:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'Завершено, кг.')] = round(dict_napr_otgruz[key])
        if key in dict_napr_otgruz_proj:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'Проекты завершено')] = '; '.join(dict_napr_otgruz_proj[key])
        if key in dict_napr_vneplan_mk:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'МК внеплан')] = '; '.join(dict_napr_vneplan_mk[key])
        if key in dict_napr_zadel_mk:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'МК задел')] = '; '.join(dict_napr_zadel_mk[key])
        if key in dict_napr_otgruz_mk:
            tmp[F.num_col_by_name_in_hat_c(rez_spis, 'МК завершено')] = '; '.join(dict_napr_otgruz_mk[key])
        rez_spis.append(tmp)
    summ_normpsmen = 0
    summ_kg = 0
    srednaya_proizvodit = 0
    summ_vneplan_normosmen = 0
    summ_vneplan_kg = 0
    summ_zaversheno = 0
    chet = 0
    summ_dolya = 0

    for i in range(1, len(rez_spis)):

        if rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Произв-ть, н.-см./см.')] > 0:
            chet += 1
            srednaya_proizvodit += rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Произв-ть, н.-см./см.')]
        summ_kg += rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'кг.')]
        summ_vneplan_normosmen += rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, "Внеплан,н.-см.")]
        summ_normpsmen += rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'н.-см.')]
        summ_vneplan_kg += rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Внеплан, кг.')]
        summ_zaversheno += rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Завершено, кг.')]
        rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Сумма, кг.(Доля %)')] = \
            rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'кг.')] + \
            rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Внеплан, кг.')]
        summ_dolya += rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Сумма, кг.(Доля %)')]
    if summ_dolya == 0:
        for i in range(1, len(rez_spis)):
            rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Сумма, кг.(Доля %)')] = \
                str(rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Сумма, кг.(Доля %)')])
    else:
        for i in range(1, len(rez_spis)):
            rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Сумма, кг.(Доля %)')] = \
                str(rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, 'Сумма, кг.(Доля %)')]) + \
                f'({round(rez_spis[i][F.num_col_by_name_in_hat_c(rez_spis, "Сумма, кг.(Доля %)")] / summ_dolya * 100)}%)'
    if chet == 0:
        srednaya_proizvodit = 0
    else:
        srednaya_proizvodit = round(srednaya_proizvodit / chet, 1)
    # rez_spis.append(['Внеплановых', round(vneplan), round(vneplan *118), "",'; '.join(list(vneplan_set)), "", ""])
    tmp_itog = ['Подытог', round(summ_normpsmen), round(summ_kg),
                round(srednaya_proizvodit, 2), '', '', round(summ_vneplan_normosmen), round(summ_vneplan_kg), '', '',
                round(summ_kg + summ_vneplan_kg), round(summ_zaversheno), '', '']
    rez_spis.append(tmp_itog)
    # tmp_itog2 = ['Итог(Задел+Внеплан):', round(summ_normpsmen + summ_vneplan_normosmen),'',
    #            '', '', "", '', '',
    #             round(summ_kg + summ_vneplan_kg),round(summ_zaversheno),'']
    # rez_spis.append(tmp_itog2)
    F.save_file(f'log_.txt', log_file)
    return rez_spis

def clck_otch(self:mywindow, *args):
    def change_kod_vp(self:mywindow,text, row, col, *args):
        print([text, row, col])
        nk_prim = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Пояснение_вп')
        nk_otv = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Ответственный')
        if self.ui.tbl_report_c.item(row,nk_prim).text() == '':
            CQT.msgbox(f'Пояснение не может быть пустым')
            self.ui.tbl_report_c.item(row, col).setText('')
            self.ui.tbl_report_c.cellWidget(row, col).setCurrentText('')
            return False
        pnom = int(CQT.valt(self.ui.tbl_report_c,'Пномер',row))
        CSQ.custom_request_c(self.bd_naryad,f"""UPDATE zamech SET  (Пояснение_вп,Код_вп,Ответственный)
        = ("{self.ui.tbl_report_c.item(row,nk_prim).text()}",{self.DICT_KOD_VP[text]},"{F.user_full_namre()}") WHERE Пномер = {pnom};""")
        self.ui.tbl_report_c.item(row,col).setText(text)
        self.ui.tbl_report_c.item(row, nk_otv).setText(F.user_full_namre())
        self.ui.tbl_report_c.removeCellWidget(row,col)
        return True
    
    def change_nk_fio_vin(self:mywindow,text, row, col, *args):
        print([text, row, col])
        if text == '':
            return 
  
        pnom = int(CQT.valt(self.ui.tbl_report_c,'Пномер',row))
        CSQ.custom_request_c(self.bd_naryad,f"""UPDATE zamech SET  (ФИО_виновный)
        = ("{text}") WHERE Пномер = {pnom};""")
        self.ui.tbl_report_c.item(row,col).setText(text)
        self.ui.tbl_report_c.removeCellWidget(row,col)
        return True
    
    if self.vid_report_c == 'Журнал_замечаний':
        if not self.permission:
            return 
        nk_kod_vp = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Код_вп')
        nk_prim = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Пояснение_вп')
        nk_fio_vin = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'ФИО_виновный')
        nk_podr_vin = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Виновное_подразделение')
        for i in range(self.ui.tbl_report_c.rowCount()):
            self.ui.tbl_report_c.removeCellWidget(i,nk_kod_vp)
            self.ui.tbl_report_c.item(i, nk_prim).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.ui.tbl_report_c.removeCellWidget(i,nk_fio_vin)
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
                list_empl = [_ for _ in self.DICT_EMPLOEE_FULL.keys() if self.DICT_EMPLOEE_FULL[_]['Подразделение'] == vp]
                list_empl.insert(0,'')
                CQT.add_combobox(self, self.ui.tbl_report_c, row, nk_fio_vin, list_empl, False, change_nk_fio_vin)
            return
        list_kod =list(self.DICT_KOD_VP.keys())
        CQT.add_combobox(self, self.ui.tbl_report_c, row, nk_kod_vp, list_kod, False, change_kod_vp)
        self.ui.tbl_report_c.item(row, nk_prim).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        CQT.set_cell_editable(self.ui.tbl_report_c,row,nk_prim,True)
        CQT.set_color_wtab_c(self.ui.tbl_report_c,row,nk_prim,245,245,245)


        

@CQT.onerror
def dbl_clck_otch(self, *args):
    if self.ui.cmb_sort_c_report_c.currentText() == 'Понедельный график выработки и отгрузок':
        column = self.ui.tbl_report_c.currentColumn()
        row = self.ui.tbl_report_c.currentRow()
        nk_nach = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Дата начала')
        nk_kon = CQT.num_col_by_name_c(self.ui.tbl_report_c, 'Дата конца')
        nach = self.ui.tbl_report_c.item(row, nk_nach).text()
        kon = self.ui.tbl_report_c.item(row, nk_kon).text()
        self.ui.le_nach_per.setText(nach)
        self.ui.le_end_of_period_c.setText(kon)
        current_ceh = self.ui.cmb_podrazdelenie.currentText()
        if column == 0:
            self.ui.cmb_sort_c_report_c.setCurrentText("Выработка цеха по виду")
        else:
            self.ui.cmb_sort_c_report_c.setCurrentText("Выработка цеха по направлению")
        self.ui.cmb_podrazdelenie.setCurrentText("current_ceh")
        report_c(self)


@CQT.onerror
def ves_tehnolohicheskiy(self, nom_mk: int, kolvo_izd, ves, conn, conn_mat, *args):
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
                    if mat['Мат_ед_изм'] in self.LIST_ED_IZM_MAT:
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
