import pathlib
import re
import os

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWinExtras import QtWin
import project_cust_38.Cust_Qt as CQT
CQT.convert_UI_into_PY_c()
from mydesign import Ui_MainWindow  # импорт нашего сгенерированного файла
import config
import sys
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_QtGui as CGUI
from project_cust_38 import user_mange as userm

import groups_manage as GRM
from datetime import timedelta
from datetime import datetime as DT
from project_cust_38.report_ci import virabotka_sotr
import project_cust_38.Cust_b24 as B24
cfg = config.Config(r'Config\CFG.cfg')  # файл конфига, находится п папке конфиг
import copy

import project_cust_38.Cust_config as USRCNF
import classes as CLSS
from functools import partial
import  project_cust_38.Cust_emoji as CEMOJ
import  composition_vipoln as CMPM
from app_dataclasses import data_app as DTCLS




class mywindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(mywindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.versia =  '1.5.9'
        self.NAME_MODULE_BASE = 'Выполнение'
        self.name_module = f'{self.NAME_MODULE_BASE}'
        self.USER_CONFIG: USRCNF.User_config = None
        self.place: USRCNF.Place = None
        USRCNF.Config.user_config.load_user_config(self,DTCLS)

        CQT.load_icons(self, 24)
        DTCLS.app_self = self
        CQT.connect_to_resize(self, CMS.tmp_dir())
        CMS.add_action_config_save_tbl_filtrs(self, self.ui)
        dic = CMS.dict_emploee(USRCNF.Config.project.db_users)
        self.auth_manager = userm.UserManager(
            window=self,
            combo_fio=self.ui.cmb_fio,
            combo_prof=self.ui.cmb_dolgn,
            input_password=self.ui.le_parol,
            input_password_reset1=self.ui.le_Nparol,
            input_password_reset2=self.ui.le_Nparol2,
            employee_by_fio=dic,
            on_success_login=self.on_success_login,
            on_logout=self.clear_widgets,
            btn_login=self.ui.btn_login,
            btn_logout=self.ui.btn_logout,
        )
        # ===========================================connects
        # ==================BTN
        self.ui.btn_login.clicked.connect(self.log_in)

        self.ui.btn_logout.clicked.connect(lambda _, x=self: self.auth_manager.logout())
        self.ui.btn_nachat.clicked.connect(self.start_nar)
        self.ui.btn_pauza.clicked.connect(self.pauza_nar)
        self.ui.btn_zaconch.clicked.connect(self.zaversh_nar)
        self.ui.btn_otkr_kd.clicked.connect(self.otkrit_docs)
        self.ui.btn_obnov_sp_nar.clicked.connect(self.zapoln_tabl_naryadov)
        self.ui.btn_add_type_brak.clicked.connect(self.add_type_brak)
        self.ui.btn_del_type_brak.clicked.connect(self.del_type_brak)
        self.ui.btn_print_nar.clicked.connect(self.print_nar)
        self.ui.btn_print_nar_settings.clicked.connect(self.on_click_btn_print_nar_settings)
        self.ui.btn_group_manage.clicked.connect(partial(GRM.btn_group_manage,self))
        self.ui.btn_seletc_base_doc.clicked.connect(self.on_click_btn_seletc_base_doc)
        self.ui.btn_reset_gr.clicked.connect(partial(GRM.btn_reset_gr,self))
        self.ui.bnt_group_cancel.clicked.connect(partial(GRM.bnt_group_cancel,self))
        self.ui.bnt_group_ok.clicked.connect(partial(GRM.bnt_group_ok,self))
        self.ui.bnt_gr_group_remove.clicked.connect(partial(GRM.bnt_group_remove,self))
        self.ui.bnt_gr_nar_remove.clicked.connect(partial(GRM.bnt_nar_remove,self))
        self.ui.btn_crash_header.clicked.connect(partial(GRM.btn_crash_header,self))
        self.ui.btn_test_apply_gr.clicked.connect(partial(GRM.btn_test_apply_gr,self))
        if not DTCLS.USER_CONFIG.is_developer:
            self.ui.btn_test_apply_gr.setHidden(True)
        #===================CHECKBOX
        self.ui.chk_come_back.clicked[bool].connect(self.save_check_box_value_to_temp_file)
        self.load_chk_come_back_state()
        #===================COMBOBOX
        self.ui.cmb_dolgn.activated[int].connect(lambda _, x = self: self.auth_manager.load_po_dolg())
        self.ui.cmb_fio.activated[int].connect(self.check_selected_user)
        self.ui.cmb_zamechain.activated[int].connect(self.vibor_zamech)
        self.ui.cmb_abstract.activated[int].connect(self.vibor_fio_abstract)
        self.ui.cmb_brak_type1.activated[int].connect(self.fill_cmbs_type_brak_2lvl)
        self.ui.cmb_brak_type2.activated[int].connect(self.fill_cmbs_type_brak_3lvl)
        #==== GLOBALS
        self.glob_login = ''
        self.glob_fio = ''
        self.user_score = None
        self.superuser = False
        self.glob_summ_treb_chas_tabel = 0
        self.glob_otk_kontrol = None
        self.glob_list_otk_brak = [['Кат_1','Кат_2','Кат_3','Тип','Кол_во']]
        self.nar_info:CLSS.Naryad_info | None = None
        # =======tbls
        self.ui.tbl_naryadi.cellDoubleClicked[int,int].connect(self.load_naruad)
        self.ui.tbl_naryadi.clicked.connect(self.tbl_naryadi_click)
        self.ui.tbl_chert.cellDoubleClicked[int, int].connect(self.otkrit_kd)
        self.ui.tbl_td.cellDoubleClicked[int, int].connect(self.otkrit_td)
        self.ui.tbl_nar_in_groups.cellDoubleClicked[int, int].connect(partial(GRM.tbl_nar_in_groupsDoubleClicked))
        self.ui.tbl_naryadi_view_kompl.clicked.connect(self.tbl_komplektovka_view_click)
        self.ui.tbl_edit_gr_groups.clicked.connect(partial(GRM.tbl_edit_gr_groups_click))
        # =======tabs
        self.ui.tabWidget_2.currentChanged[int].connect(self.tab2_clcik)
        self.ui.tabWidget.currentChanged[int].connect(self.tab_clcik)
        self.ui.tabWidget_3.currentChanged[int].connect(self.tab_clcik3)
        self.ui.tabWidget_docs.currentChanged[int].connect(self.tbl_prosmotr_docs)
        self.ui.tabw_groups.currentChanged[int].connect(partial(GRM.tab_gr_click))
        # ========le
        self.ui.le_basa.textChanged.connect(self.calc_user_score)
        self.ui.le_premia.textChanged.connect(self.calc_user_score)
        self.ui.le_brak.textChanged.connect(self.calc_user_score)

        #======ACTIONS
        self.ui.action_noviy_user.triggered.connect(lambda _, x = self: self.auth_manager.reg_new_user())
        self.ui.action_change_pass.triggered.connect(lambda _, x = self: self.auth_manager.change_user_pass())
        self.ui.action_reset_parol.triggered.connect(lambda _, x=self: self.auth_manager.reset_user_pass())
        self.ui.peresilniy.triggered.connect(self.create_peresilniy)
        self.ui.ved_komplekt.triggered.connect(self.create_ved_komplekt)
        self.ui.zayav_pererabotchik.triggered.connect(self.create_zayav_pererab)
        # ============DB
        self.db_naryd = F.bdcfg('Naryad')
        self.bd_naryad = self.db_naryd
        self.bd_users = F.bdcfg('BD_users')
        self.db_resxml = F.bdcfg('db_resxml')
        self.db_dse = F.bdcfg('BD_dse')
        self.db_kplan = F.bdcfg('DB_kplan')
        #self.db_dse = F.bdcfg('BD_dse')
        self.db_nomen = F.bdcfg('nomenklatura_erp')
        self.db_act = F.scfg('BDact') + F.sep() + 'BDact.db'
        # =======loads
        conn,cur = CSQ.connect_bd(self.db_naryd,100)
        self.check_lock_db(CMS.dict_etapi(self, self.db_naryd,""),"","")
        CSQ.close_bd(conn,cur)
        conn,cur = CSQ.connect_bd(self.bd_users)
        self.load_users()
        self.check_lock_db(CMS.dict_professions(self, self.bd_users, conn=conn), conn,cur)
        CSQ.close_bd(conn,cur)
        self.DICT_EMPL_FULL = CMS.dict_emploee_full(self.bd_users,self=self)
        self.auth_manager.load_po_dolg()

        DICT_OPER = CSQ.custom_request_c(self.db_naryd, f"""SELECT * FROM operacii""", rez_dict=True)
        self.DICT_OPER = F.deploy_dict_c(DICT_OPER, 'kod')
        self.DICT_OPER_NAME = F.deploy_dict_c(DICT_OPER, 'name')
        self.DICT_NOMEN = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_nomen, f"""SELECT * FROM nomen;""", rez_dict=True), 'Код')
        list_nomens = CSQ.custom_request_c(self.db_nomen, f"""SELECT * FROM ВидыНоменклатуры""", rez_dict=True)
        self.DICT_VIDS_NOMEN = F.deploy_dict_c(list_nomens, 'name')
        self.DICT_VIDS_NOMEN_BY_REF = F.deploy_dict_c(list_nomens, 'Ref_Key')
        self.DICT_PRICE_BRAK = CMS.DICT_PRICE_BRAK(self.db_naryd)
        self.DICT_TYPE_PROSTOI =F.deploy_dict_c( CSQ.custom_request_c(self.db_naryd,f"""SELECT * FROM kategor_vnepl WHERE poki_{self.place.poki} = 1""", rez_dict=True),"value")
        self.DICT_DOLGN_ETAP = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_naryd, f"""SELECT * FROM dolgn_etap""", rez_dict=True), 'Должность')
        self.app_icons()

        self.ui.le_Nparol.setVisible(False)
        self.ui.le_Nparol2.setVisible(False)
        self.ui.fr_add_info_prost.setVisible(False)
        self.ui.tbl_chert.setSelectionBehavior(1)
        CQT.set_color_sort_cell_table_c(self.ui.tbl_chert, r=80, g=200, b=110)
        self.ui.tbl_td.setSelectionBehavior(1)
        CQT.set_color_sort_cell_table_c(self.ui.tbl_td, r=80, g=200, b=110)
        self.ui.lbl_instruction_docs.setText(f'Для ШГ и АО - srv-docs.powerz.ru:21361'
                                                f'  Для КТ и ЛК - srv-docs.powerz.ru'
                                                f'  Для КЛ и ТППР - srv-docs-pkb.powerz.ru')
        CQT.load_css(self)
        GRM.clear()
        self.start_up()
        # ====ВРЕМЕННО
        self.ui.cmb_dolgn.setCurrentIndex(4)
        #self.proverka_zakritiya_naryadov_po_jurnaly()
        #self.ui.cmb_fio.setCurrentIndex(3)
        #self.ui.le_parol.setText('2022')
        #userm.log_in(self)
        #self.ui.btn_nekomplect.setEnabled(False)
        #self.update_poditogs()

    def log_in(self):
        self.auth_manager.log_in()
        DTCLS.user_abstracts = CSQ.custom_request_c(USRCNF.Config.project.db_users,
                                                    f"""SELECT ФИО FROM employee 
            WHERE Режим == 'Абстракт' AND Подразделение 
            == "{USRCNF.Config.user_config.User.Подразделение.strip()}";""",
                                                    rez_dict=True)


    def on_success_login(self):
        DTCLS.production_shift = CMS.Production_shifts(DTCLS.USER_CONFIG.User.Пномер,
                                                       DTCLS.USER_CONFIG.common_config.db_users)
        self.zapoln_tabl_naryadov()
        self.lbl_tek_narayd(USRCNF.Config.user_config.User.ФИО)
        self.fill_cmb_abstract()
        self.toggle_visible_btn_group_manage()
    def toggle_visible_btn_group_manage(self,forced_hide=False):
        if not forced_hide and  (F.user_name() in ('a.belyakov' 's.kozyrkov', 'm.moyamsin', 'a.a.fedorov') or (
                USRCNF.Config.place.poki == 1 and USRCNF.Config.user_config.User and
                USRCNF.Config.user_config.User.Подразделение in ('Сборочный цех Производства',
                                                                 'Отдел комплектации',
                                                                 'Набивочный цех Производства',
                                                                 'Столярный цех Производства',
                                                                 'Швейный цех Производства',
                                                                 )
        ) or (
                USRCNF.Config.place.poki == 0 and USRCNF.Config.user_config.User and
                USRCNF.Config.user_config.User.Подразделение in ('Цех механической обработки Производства'
                                                                 )
        )
        ):
            self.ui.btn_group_manage.setHidden(False)
        else:
            self.ui.btn_group_manage.setHidden(True)

    def clear_widgets(self):
        self.ui.cmb_fio.setCurrentText('')
        self.glob_login = ''
        self.ui.le_Nparol.setVisible(False)
        self.ui.le_Nparol2.setVisible(False)
        CQT.clear_tbl(self.ui.tbl_naryadi)
        CQT.clear_tbl(self.ui.tbl_history)
        CQT.clear_tbl(self.ui.tbl_chert)
        CQT.clear_tbl(self.ui.tbl_naryadi_view_kompl)
        CQT.clear_tbl(self.ui.tbl_stat)
        CQT.clear_tbl(self.ui.tbl_stat_filtr)
        CQT.clear_tbl(self.ui.tbl_stat_filtr_last)
        CQT.clear_tbl(self.ui.tbl_stat_last)
        CQT.clear_tbl(self.ui.tbl_descr_nar)
        self.ui.textBrowser_zadanie.setText('')
        self.ui.te_zamechain.setText('')
        self.ui.label_12.setText('План работы')
        self.ui.le_basa.setText('')
        self.ui.le_premia.setText('')
        self.ui.le_brak.setText('')
        self.ui.le_nom_nar_prost.setText('')

        self.ui.lbl_ostalos.setText('')
        self.ui.lbl_tek_nar.setText('')
        self.ui.tabWidget_2.setCurrentIndex(0)
        self.ui.tabWidget.setCurrentIndex(0)
        self.setStatusTip('')
        DTCLS.table_nar = None
        GRM.clear()
        CQT.clear_tbl(self.ui.tbl_compositions)
        self.ui.tbl_compositions.setHidden(True)
        self.toggle_visible_btn_group_manage(forced_hide=True)
    def load_users(self, conn='', cur=''):
        """Загрузить список сотрудников в листбокс"""
        poki = USRCNF.Config.place.poki
        org_name = USRCNF.Config.place.Имя
        self.DICT_EMPLOEE = dict()
        self.SPIS_EMPLOEE = CSQ.custom_request_c(
            self.bd_users,
            f"""SELECT ФИО, Должность FROM employee WHERE Пномер > 2 AND Статус != 'Увольнение' AND Компания = {org_name!r};""",
            hat_c=False
        )
        if self.SPIS_EMPLOEE == False:
            return False
        spis_black_list = F.load_file(F.scfg('Riba') + F.sep() + 'black_list_itr.txt')
        if spis_black_list == False:
            spis_black_list = ['']
            F.save_file(F.scfg('Riba') + F.sep() + 'black_list_itr.txt', spis_black_list)
        spis_itr = CSQ.custom_request_c(self.bd_users, f'select имя from professions where poki = {poki} AND Вкл = 1',
                                        one_column=True, hat_c=True)
        self.ui.cmb_dolgn.addItem('')
        # self.ui.cmb_fio.addItem('')
        set_dolgn = set()
        for rab in self.SPIS_EMPLOEE:
            fio = rab[0]
            dolg = rab[1]
            self.DICT_EMPLOEE[fio] = dolg
            flag = True
            for frase in spis_black_list:
                if frase in fio:
                    flag = False
            if dolg in spis_itr and flag == True:
                set_dolgn.add(dolg)
        spis_dolgn = sorted(list(set_dolgn))
        for dolgn in spis_dolgn:
            self.ui.cmb_dolgn.addItem(dolgn)

        spis_pauz = CSQ.custom_request_c(USRCNF.Config.project.db_naryad, f''' 
                SELECT s_num,
                       name,
                       comment,
                       poki
                  FROM reason_pause_nar where poki = {USRCNF.Config.place.poki};
                ''', rez_dict=True)
        self.ui.cmb_zamechain.clear()
        self.ui.cmb_zamechain.addItem('')
        CQT.fill_list_combobx(self, self.ui.cmb_zamechain, [_['name'] for _ in spis_pauz],
                              list_tooltip=[_['comment'] for _ in spis_pauz], first_void=True)
        self.ui.cmb_zamechain.setCurrentIndex(0)
        self.auth_manager.toggle_btn_login()

    @CQT.onerror
    def fill_cmb_abstract(self,*args,**kwargs):
        ima = CMS.name_by_empl_c(self.ui.cmb_fio.currentText())
        if self.DICT_EMPL_FULL[ima]['Режим'] == 'Абстракт':
            list_fio = []
            for fio in self.DICT_EMPLOEE.keys():
                if self.DICT_EMPL_FULL[fio]['Режим'] != 'Абстракт' :
                    list_fio.append(fio)
            list_fio = sorted(list_fio)
            self.ui.cmb_abstract.addItem('')
            self.ui.cmb_abstract.addItems(list_fio)

            self.ui.gb_abstrakt.setVisible(True)
        else:

            self.ui.gb_abstrakt.setVisible(False)

    def start_up(self):
        # if USRCNF.Config.user_config.is_developer: # 07.04.2026
        #     self.auth_manager.log_in(autouser='Демичев Николай Юрьевич')
            ...

    @CQT.onerror
    def check_selected_user(self, *args):
        fio_dolgn = self.ui.cmb_fio.currentText()
        fio = ' '.join(fio_dolgn.split()[:3])
        if fio in self.DICT_EMPL_FULL:
            if self.DICT_EMPL_FULL[fio]['Режим'] == 'Абстракт':
                self.ui.cmb_fio.setCurrentText('')
                CQT.msgbox('Для выбора абстрактных нарядов зайдите под своим именем')
                return

    @CQT.onerror
    def update_poditogs(self):
        start = "2024-07-01 04:03:25"
        list_nar = []
        str_add = ''
        if list_nar:
            str_add = f' AND Номер_наряда IN ({", ".join([str(_) for _ in list_nar])})'
        list_users = CSQ.custom_request_c(self.db_naryd,f"""SELECT DISTINCT ФИО, Номер_наряда FROM jurnal
         WHERE datetime(Дата) > datetime("{start}") {str_add};""",rez_dict=True)
        for i, item in enumerate(list_users):
            print(f'{i}/{len(list_users)}')
            nar = CMS.Naryads(item['Номер_наряда'], self.db_naryd, self.DICT_DOLGN_ETAP, self.bd_users,
                              self.DICT_EMPLOEE_FULL_WITH_DEL)
            nar.recalc_jur_n_time(item['ФИО'])

    @CQT.onerror
    def check_lock_db(self,func, conn = '', cur = ''):
        rez = func
        if rez == False:
            CSQ.close_bd(conn,cur)
            CQT.msgbox(f'Нет доступа к БД попробуй позже')
            quit()

    def keyReleaseEvent(self, e):
        if e.key() == 16777237 and e.modifiers() == (QtCore.Qt.ControlModifier):
            if CQT.focus_is_QTableWidget():
                for i in range(QtWidgets.QApplication.focusWidget().rowCount()):
                    if QtWidgets.QApplication.focusWidget().rowHeight(i) > 0.5:
                        QtWidgets.QApplication.focusWidget().setRowHeight(i,QtWidgets.QApplication.focusWidget().rowHeight(i) - 1)
        if e.key() == 16777235 and e.modifiers() == (QtCore.Qt.ControlModifier):
            if CQT.focus_is_QTableWidget():
                for i in range(QtWidgets.QApplication.focusWidget().rowCount()):
                    QtWidgets.QApplication.focusWidget().setRowHeight(i,QtWidgets.QApplication.focusWidget().rowHeight(i) + 1)

        if e.key() == 67 and e.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.copy_bufer_table(QtWidgets.QApplication.focusWidget())
        if self.ui.tbl_stat_filtr.hasFocus():
            if e.key() == 16777220:
                CMS.apply_filtr_c(self,self.ui.tbl_stat_filtr,self.ui.tbl_stat)
        if self.ui.le_parol.hasFocus():
            if e.key() == 16777220:
                self.ui.btn_login.setFocus()
                self.auth_manager.log_in()

    def app_icons(self):
        self.ui.btn_login.setIcon(QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton)))
        self.ui.btn_login.setIconSize(QtCore.QSize(32, 32))
        self.ui.btn_obnov_sp_nar.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)))
        self.ui.btn_obnov_sp_nar.setIconSize(QtCore.QSize(32, 32))

        self.ui.btn_nachat.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)))
        self.ui.btn_nachat.setIconSize(QtCore.QSize(32, 32))

        self.ui.btn_pauza.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MediaPause)))
        self.ui.btn_pauza.setIconSize(QtCore.QSize(32, 32))

        self.ui.btn_zaconch.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MediaStop)))
        self.ui.btn_zaconch.setIconSize(QtCore.QSize(32, 32))

        self.ui.btn_logout.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton)))
        self.ui.btn_logout.setIconSize(QtCore.QSize(32, 32))
        self.ui.tabWidget_2.setTabIcon(0, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)))
        self.ui.tabWidget_2.setTabIcon(1, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileDialogListView)))
        self.ui.tabWidget_2.setTabIcon(2, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxQuestion)))
        self.ui.tabWidget.setTabIcon(0, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogOkButton)))
        self.ui.tabWidget.setTabIcon(1, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileDialogInfoView)))
        self.ui.tabWidget.setTabIcon(2, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileDialogStart)))


    @CQT.onerror
    def tab_clcik3(self,ind,*args):
        if self.glob_login == "":
            return
        name = self.ui.tabWidget_3.tabText(ind)
        CQT.statusbar_text(self)
        if name == 'Предыдущий месяц':
            dat = F.datetostr(F.add_months(DT.today(),-1))
            self.load_statistic(dat,self.ui.tbl_stat_last,self.ui.tbl_stat_filtr_last)
            tbl = self.ui.tbl_stat_last
            CMS.apply_summ_с(self, tbl)
            CQT.color_cell_wtable_c(tbl, 'Внеплан', '1', r=222, g=100, b=100)
            CQT.color_cell_wtable_c(tbl, 'Внеплан', '2', r=100, g=222, b=100)
            CQT.color_cell_wtable_c(tbl, 'Подтвержд_вып', '0', r=222, g=100, b=100)
            CQT.color_cell_wtable_c(tbl, 'Подтвержд_вып', '1', r=100, g=222, b=100)

    @CQT.onerror
    def tab_clcik(self,ind,*args):
        name = self.ui.tabWidget.tabText(ind)
        CQT.statusbar_text(self)
        if name == 'История наряда':
            self.history_nar_load()
        if name == 'Документация':
            self.tbl_prosmotr_docs()


    @CQT.onerror
    def tab2_clcik(self,ind,*args):
        if CMS.kontrol_ver(self.versia, "Выполнение2") == False:
            sys.exit()
        CQT.statusbar_text(self)
        name = self.ui.tabWidget_2.tabText(ind)
        self.ui.le_basa.clear()
        self.ui.le_premia.clear()
        self.ui.le_brak.clear()
        self.ui.lbl_itog_calc.clear()
        CQT.clear_tbl(self.ui.tbl_naryadi_view_kompl)
        self.ui.lbl_kompl_info.clear()
        self.ui.lbl_abstract.clear()
        self.ui.cmb_abstract.setCurrentText('')
        self.ui.lbl_fio_for_otk.clear()
        self.ui.lbl_fiomaster_for_otk.clear()

        if name == 'Доступные наряды':

            self.ui.lbl_ostalos.setText('')
        if name == 'Управление нарядом':
            self.load_naruad()
        if name == 'Статистика':
            if self.glob_login == "":
                pass
            else:
                if self.ui.tabWidget_3.tabText(self.ui.tabWidget_3.currentIndex()) == 'Предыдущий месяц':
                    dat = F.datetostr(F.add_months(DT.today(), -1))
                    self.load_statistic(dat, self.ui.tbl_stat_last, self.ui.tbl_stat_filtr_last)
                    tbl = self.ui.tbl_stat_last
                else:
                    dat = F.datetostr(DT.today())
                    self.load_statistic(dat,self.ui.tbl_stat,self.ui.tbl_stat_filtr)
                    tbl = self.ui.tbl_stat
                CMS.apply_summ_с(self, tbl)
                CQT.color_cell_wtable_c(tbl, 'Внеплан', '1', r=222, g=100, b=100)
                CQT.color_cell_wtable_c(tbl, 'Внеплан', '2', r=100, g=222, b=100)
                CQT.color_cell_wtable_c(tbl, 'Подтвержд_вып', '0', r=222, g=100, b=100)
                CQT.color_cell_wtable_c(tbl, 'Подтвержд_вып', '1', r=100, g=222, b=100)

    def load_chk_come_back_state(self):
        name_rule = 'chk_come_back'
        val = CMS.load_tmp_stukt(name_rule,True)
        chk:CQT.QtWidgets.QCheckBox = self.ui.chk_come_back
        chk.blockSignals(True)#запрет сигнала
        chk.setChecked(val)
        chk.blockSignals(False)#разрешить сигнал

    def save_check_box_value_to_temp_file(self):
        name_rule = 'chk_come_back'
        chk: CQT.QtWidgets.QCheckBox = self.ui.chk_come_back
        CMS.save_tmp_stukt(chk.isChecked(), name_rule)



    def load_statistic(self,dat:str,tbl,filtr):
        konec = F.start_end_dates_c(date=dat, vid='m')[1]
        nach = F.start_end_dates_c(date=dat, vid='m')[0]
        rez_spis = virabotka_sotr(self, nach, konec, CMS.name_by_empl_c(self.glob_login))
        if rez_spis == None:
            return
        #nk_effect = F.num_col_by_name_in_hat_c(rez_spis, 'Дата')
        #nk_potabel = F.num_col_by_name_in_hat_c(rez_spis, 'Примеч_журнал')
        #nk_prem = F.num_col_by_name_in_hat_c(rez_spis, 'Задание')
        #effect = rez_spis[-2][nk_effect].split()[1]
        #potabel = F.valm(rez_spis[-2][nk_potabel].split()[2])
        #prem = rez_spis[-2][nk_prem]

        CQT.fill_wtabl_old_c(self, rez_spis, tbl, separ='', isp_hat_c=True, max_vis_row=500)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl,'Коэфф_вых'),True)
        CMS.fill_filtr_c(self, filtr, tbl)
        self.ui.le_brak.setText(rez_spis[-2][F.num_col_by_name_in_hat_c(rez_spis,'Коэфф_сложности')].split()[-1].replace('%',""))
        self.ui.le_brak.setEnabled(False)
        #self.load_info_imge(effect, potabel, prem)


    @CQT.onerror
    def load_info_imge(self,effect,potabel,prem):
        imgg = self.ui.lbl_fon
        imgg.clear()
        putf = os.path.join("icons", "svitok.jpg")
        if F.existence_file_c(putf) == False:
            CQT.msgbox('Не найден файл фона')
            return
        pixmap, k_w, k_h = CGUI.sozdat_obj_pod_risovane(putf, imgg)
        pixmap, self.user_score = self.risovat_pixmap(pixmap, k_w, k_h,effect,potabel,prem)
        if pixmap == None:
            return
        CGUI.zagruzit_img_na_lbl(imgg, pixmap)

    @CQT.onerror
    def summ_chas_po_tabel_mes(self):
        fio = CMS.name_by_empl_c(self.glob_login)
        spis_prem = F.open_file_c(F.scfg('employee') + F.sep() + 'Virabotka_sbdn.txt', separ='|')
        if spis_prem == ['']:
            return
        nk_summ_chas = F.num_col_by_name_in_hat_c(spis_prem,'stavka_tab_chas')
        nk_fio = F.num_col_by_name_in_hat_c(spis_prem, 'fio')
        for i in range(len(spis_prem)):
            if spis_prem[i][nk_fio] == fio:
                self.glob_summ_treb_chas_tabel = spis_prem[i][nk_summ_chas]
                return
        return

    @CQT.onerror
    def raschet_stoimosti_naryada(self):
        tblk = self.ui.tbl_naryadi
        r = tblk.currentRow()
        nk_koef_slog = CQT.num_col_by_name_c(tblk, 'Коэфф_сложности')
        koef_slog = F.valm(tblk.item(r, nk_koef_slog).text())
        list_time_oper = tblk.item(r, CQT.num_col_by_name_c(tblk,'Опер_время')).text().split('|')
        list_sort_c_rab_name = tblk.item(r, CQT.num_col_by_name_c(tblk, 'Виды_работ')).text().split('|')
        summ = 0
        if len(list_time_oper) != len(list_sort_c_rab_name):
            return 0
        for i in range(len(list_sort_c_rab_name)):
            vid = list_sort_c_rab_name[i]
            time = F.valm(list_time_oper[i])
            if vid == '':
                continue
            if vid not in self.DICT_VID_RABOT:
                print(f'{vid} не в списке видов')
                continue
            stavka = self.DICT_VID_RABOT[vid]['Руб_мин']
            summ += stavka*time
        return round(summ*koef_slog)


    @CQT.onerror
    def check_dostupnosti_nar(self,nom_nar:int):
        user = self.transform_current_user_for_sql()
        custom_request_c = f'''SELECT Пномер FROM naryad WHERE Пномер == {nom_nar} AND (ФИО IN ({user}) AND Фвремя == "" 
                                OR ФИО2 IN ({user}) AND Фвремя2 == "")'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c)
        if rez == False:
            return False
        if rez == None:
            return False
        if len(rez)>1:
            return True
        return False


    def upload_work_productivity_3(self,conn='', cur = ''):
        spis_rez = []
        #if F.strtodate(F.now()) - timedelta(days=70) > F.strtodate('2022-11-01 00:00:01'):
        data_nach = F.datetostr(F.strtodate(F.now()) - timedelta(days=40))
        #else:
        #    data_nach = '2022-11-01 00:00:01'
        custom_request_c = f'SELECT jurnal.Дата, ' \
                 f'jurnal.Штамп, ' \
                 f'jurnal.Номер_наряда, ' \
                 f'jurnal.ФИО, ' \
                 f'mk.Номер_проекта || "$" || ' \
                 f'mk.Номер_заказа AS "НП$ПУ", ' \
                 f'naryad.Операции, ' \
                 f'naryad.Номер_мк, ' \
                 f'naryad.Виды_работ, ' \
                 f'jurnal.Статус, ' \
                 f'naryad.Твремя, ' \
                 f'jurnal.Подытог, ' \
                 f'jurnal.Примечание, ' \
                 f'naryad.Опер_время,' \
                 f'naryad.ДСЕ,' \
                 f'naryad.Виды_работ' \
                 f' FROM jurnal INNER JOIN naryad' \
                 f' ON jurnal.Номер_наряда = naryad.Пномер' \
                 f' INNER JOIN mk' \
                 f' ON naryad.Номер_мк = mk.Пномер' \
                 f' WHERE jurnal.Статус == "Начат" AND naryad.Операции NOT LIKE "%Резка(ЧПУ)%" AND jurnal.Подытог > 0 and date(jurnal.Дата) > date("{data_nach}")'

        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c,rez_dict=True,conn=conn, cur = cur)
        if rez == False or rez == None:
            return
        set_etapov = set()
        for i in range(1, len(rez)):
            dolgn = self.DICT_EMPLOEE[rez[i]['ФИО']]
            etap = self.DICT_PROFESSIONS_PSEUDONAME[dolgn]['этап']
            fiod = self.fiod(rez[i]['ФИО'])
            spis_dse =  rez[i]['ДСЕ'].split('|')[0]
            spis_rez.append([rez[i]['Дата'], rez[i]['Штамп'], rez[i]['Номер_наряда'], fiod, rez[i]['НП$ПУ'],
                             etap, spis_dse, rez[i]['Статус'],
                             rez[i]['Подытог'], "Основной ФОТ", F.clear_row_for_file_name_c(rez[i]['Примечание'])])
            set_etapov.add(etap)

        for etap in set_etapov:
            tmp = []
            for item in spis_rez:
                if etap == item[5]:
                    tmp.append(item)
            F.save_file(F.scfg('employee') + F.sep() + f'Trudozatrati_3_{etap}.txt', tmp,utf=False)
        #F.write_file_c(F.scfg('employee') + F.sep() + 'Trudozatrati.txt', spis_rez,separ='|',utf8=False)


    @CQT.onerror
    def fiod(self,fio_):
        dolgn = f'{fio_} должность'
        for item in self.SPIS_EMPLOEE:
            if fio_ == item[0]:
                return ' '.join(item)
        return dolgn

    @CQT.onerror
    def vibor_fio_abstract(self,nom,*args):
        fio = self.ui.cmb_abstract.itemText(nom)
        self.ui.lbl_abstract.setText(fio)

    @CQT.onerror
    def vibor_zamech(self,nom,*args):
        zam = self.ui.cmb_zamechain.itemText(nom)
        self.ui.te_zamechain.setPlainText(zam)

    @CQT.onerror
    def create_zayav_pererab(self,*args):
        if self.glob_login == "":
            CQT.msgbox('Необходимо войти')
            return
        if self.ui.tabWidget_2.currentIndex() != CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Доступные наряды'):
            self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Доступные наряды'))
        tbl = self.ui.tbl_naryadi
        tblv = self.ui.tbl_naryadi_view_kompl
        CMS.load_order_outsourcing_c(self,tbl,tblv)

    @CQT.onerror
    def create_ved_komplekt(self,*args):
        if self.glob_login == "":
            CQT.msgbox('Необходимо войти')
            return
        if self.ui.tabWidget_2.currentIndex() != CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Доступные наряды'):
            self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Доступные наряды'))
        tbl = self.ui.tbl_naryadi
        tblv = self.ui.tbl_naryadi_view_kompl
        CMS.load_ved_komplekt(self,tbl,tblv)

    @CQT.onerror
    def create_peresilniy(self,*args):
        if self.glob_login == "":
            CQT.msgbox('Необходимо войти')
            return
        if self.ui.tabWidget_2.currentIndex() != CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Доступные наряды'):
            self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Доступные наряды'))
        tbl = self.ui.tbl_naryadi
        tblv = self.ui.tbl_naryadi_view_kompl
        CMS.load_peresilniy(self,tbl,tblv)


    @CQT.onerror
    def calc_user_score(self,*args):
        basa = self.ui.le_basa.text()


        premia = self.ui.le_premia.text()
        brak = self.ui.le_brak.text()
        itog = self.ui.lbl_itog_calc

        itog.setText('-')
        if self.glob_login == "":
            return

        if F.is_numeric(basa) == False:
            return

        if F.is_numeric(premia) == False:
            return
        if F.is_numeric(brak) == False:
            return
        rez = round(F.valm(basa) +  (F.valm(basa) * (F.valm(premia)-abs(F.valm(brak))))/100)
        itog.setText(str(rez))

    @CQT.onerror
    def risovat_pixmap(self,pixmap,k_w,k_h,effect,potabel,prem):
        fio = CMS.name_by_empl_c(self.glob_login)
        prof = CMS.job_post_by_empl_c(self.glob_login)
        spis_prem = F.open_file_c(F.scfg('employee') + F.sep() + 'Virabotka_sbdn.txt', separ='|')
        spis_po_prof = []
        my_paramets =''
        for i in range(1,len(spis_prem)):
            if prof == spis_prem[i][1]:
                spis_po_prof.append(spis_prem[i])
                if spis_prem[i][0] in fio:
                    my_paramets = spis_prem[i]
        for i in range(len(spis_po_prof)):
            spis_po_prof[i].append(round(int(spis_po_prof[i][2])-int(spis_po_prof[i][3])*2))
        spis_po_prof.sort(key=lambda x:int(x[-1]), reverse = True)

        qpp = QtGui.QPainter(pixmap)
        nach = [round(205 * k_w), round(113 * k_h)]
        font1 = round(30 * k_h)
        font2 = round(36 * k_h)
        shag1 = font1 *1.6


        CGUI.ris_text(qpp,nach[0],nach[1],f'Топ 5 по профессии {prof},  баллов.:',10,10,10,font1,ima_font='Century')
        nach[1] += shag1*2
        top = 6
        if len(spis_po_prof) < top:
            top = len(spis_po_prof)
        try:
            for i in range(top):
                CGUI.ris_text(qpp, nach[0] , nach[1] + i * shag1, f'{spis_po_prof[i][0]} \n {spis_po_prof[i][-1]}' , 10, 10, 10, font2, ima_font='Bookman Old Style')
        except:
            return None, None
        if my_paramets == "":
            return None, None
        nach2 = [round(205 * k_w), round(559 * k_h)]
        nach3 = [round(1120 * k_w), round(113 * k_h)]
        CGUI.ris_text(qpp, nach2[0], nach2[1], f'Статистика, {fio}:', 10, 10, 10, font2,
                      ima_font='Bookman Old Style')
        nach2[1] += shag1 * 2
        CGUI.ris_text(qpp, nach2[0], nach2[1], f'{prem}', 10, 10, 10, font2,
                      ima_font='Bookman Old Style')
        nach2[1] += shag1 * 2
        qpp.drawText(int(nach3[0]), int(nach3[1]), int(900* k_w), int(999 * k_w), 0x1000,
                     f'Выполненые наряды, №-час.:  {my_paramets[4].replace(":","-").replace(";",";   ")}')
        nach2[1] += shag1 * 2
        CGUI.ris_text(qpp, nach2[0], nach2[1], f'Эффективность {effect}', 10, 10, 10, font2,
                      ima_font='Bookman Old Style')
        nach2[1] += shag1 * 2
        CGUI.ris_text(qpp, nach2[0], nach2[1], f'Акты о браке,№-вычет: {my_paramets[6]}', 10, 10, 10, font2,
                      ima_font='Bookman Old Style')
        nach2[1] += shag1 * 2
        CGUI.ris_text(qpp, nach2[0], nach2[1], f'Итого за брак:, {my_paramets[3]}', 10, 10, 10, font2,
                      ima_font='Bookman Old Style')
        nach2[1] += shag1 * 2
        CGUI.ris_text(qpp, nach2[0], nach2[1], f'Минут по табелю к работе: {potabel} ({round(potabel/480,1)} смен)', 10, 10, 10, font2,
                      ima_font='Bookman Old Style')
        nach2[1] += shag1 * 2
        CGUI.ris_text(qpp, nach2[0], nach2[1], f'Баллов по профессии: {my_paramets[8]}', 10, 10, 10, font2,
                      ima_font='Bookman Old Style')
        qpp.end()
        return pixmap, my_paramets

    @CQT.onerror
    def history_nar_load(self):
        if self.nar_info is None:
            return
        custom_request_c = f'''SELECT  Дата, ФИО, Статус, Подытог, Примечание 
                FROM jurnal WHERE Номер_наряда == {self.nar_info.nom_nar}'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c)
        CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_history, isp_hat_c=True, separ='',min_shir_col=200)


    @CQT.onerror
    def tbl_prosmotr_docs(self,*args):
        if self.ui.tabWidget_docs.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_docs,'КД'):
            self.prosmotr_kd_load()
        if self.ui.tabWidget_docs.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_docs,'ТД'):
            self.prosmotr_td_load()

    @CQT.onerror
    def prosmotr_td_load(self):
        tblp = self.ui.tbl_td
        if self.nar_info is None:
            return
        custom_request_c = f'''SELECT ДСЕ,Операции,Номер_мк FROM naryad WHERE Пномер == {self.nar_info.nom_nar}'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c)
        spis_kd = rez[-1][0].split('|')
        spis_oper = rez[-1][1].split('|')
        nom_mk = rez[-1][2]
        set_docs = set()

        res = CMS.load_res(nom_mk)
        data_for_table = []
        cache = {}
        for i in range(len(spis_kd)):
            naim , nn = spis_kd[i].split('$')
            nom_oper = spis_oper[i].split('$')[0]
            for dse in res:
                if dse['Номенклатурный_номер'] == nn and dse['Наименование'] == naim:
                    for oper in dse['Операции']:
                        if nom_oper == oper['Опер_номер']:
                            if dse['Номенклатурный_номер'] not in cache:
                                cache[dse['Номенклатурный_номер']] = CMS.Techkards(
                                    nn_or_snum=dse['Номенклатурный_номер'],
                                    db_dse=USRCNF.Config.project.db_dse,
                                    nom_mk=str(nom_mk),
                                    DICT_OP_NAME=self.DICT_OPER_NAME,
                                    DICT_PROFESSIONS=self.DICT_PROFESSIONS
                                )
                            tech = cache[dse['Номенклатурный_номер']]
                            attached_files = tech.get_attached_operation_files(nom_oper, allowed_ext=('.pdf', '.docx'))
                            for filename in attached_files:
                                data_for_table.append({'Документ': filename, 'Номер_техкарты': tech.dse['Номер_техкарты']})
                            for doc in oper['Опер_документы']:
                                if doc != '':
                                    set_docs.add(doc)
                            break
                    break
        for instruction in set_docs:
            data_for_table.insert(0, {'Документ': instruction, 'Номер_техкарты': ''})
        CQT.fill_wtabl_old_c(self, data_for_table, tblp, isp_hat_c=True, separ='', ogr_maxshir_kol=300)
        nk_num_tk = CQT.num_col_by_name_c(tblp, 'Номер_техкарты')
        if nk_num_tk:
            tblp.setColumnHidden(nk_num_tk, True)

    @CQT.onerror
    def prosmotr_kd_load(self):
        tblp = self.ui.tbl_chert
        if self.nar_info is None:
            return
        custom_request_c = f'''SELECT ДСЕ FROM naryad WHERE Пномер == {self.nar_info.nom_nar}'''
        rez = CSQ.custom_request_c(self.db_naryd,custom_request_c)

        list_dse = CSQ.custom_request_c(self.db_dse,"""SELECT Путь_docs,Номенклатурный_номер FROM dse""", rez_dict=True)

        dict_dse = F.deploy_dict_c(list_dse, 'Номенклатурный_номер')

        spis_kd = rez[-1][0].split('|')
        rez_shap = ['НН',"Наименование",'Путь']
        rez_set = set()

        for dse in spis_kd:
            tmp = dse.split('$')
            put_docs = dict_dse[tmp[1]]
            rez_set.add((tmp[0],tmp[1],put_docs))

        rez_spis = list(rez_set)
        rez_spis.insert(0,rez_shap)
        CQT.fill_wtabl_old_c(self,rez_spis,tblp,isp_hat_c=True,separ='',ogr_maxshir_kol=300)


    @CQT.onerror
    def otkrit_docs(self,*args):
        if self.ui.tabWidget_docs.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_docs,'КД'):
            self.otkrit_kd()
        if self.ui.tabWidget_docs.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_docs,'ТД'):
            self.otkrit_td()

    @CQT.onerror
    def otkrit_td(self,*args):
        tbl = self.ui.tbl_td
        if tbl.currentRow() == -1:
            return
        col_doc = CQT.num_col_by_name_c(tbl, 'Документ') #30.07.25
        col_tk = CQT.num_col_by_name_c(tbl, 'Номер_техкарты')
        if col_doc is None or col_tk is None:
            return
        tk = tbl.item(tbl.currentRow(), col_tk).text()
        name = tbl.item(tbl.currentRow(), col_doc).text()
        if tk:
            file = CSQ.custom_request_c(USRCNF.Config.project.db_files, f"""
               SELECT reestr.file
               FROM t_kards
                        LEFT JOIN names ON t_kards.file_name = names.name
                        LEFT JOIN reestr ON names.nom_data = reestr.Пномер
               WHERE t_kards.t_kard_name = {tk!r} and t_kards.file_name = {name!r}
            """, rez_dict=True, one=True)
            _, ext = os.path.splitext(name)
            if not file or not isinstance(file.get('file'), bytes):
                return CQT.msgbox(f'Файл {name!r} не найден')
            path = F.save_tmp_win_dir_file(file.get('file'), extention=ext)
            return os.startfile(path)

        else:
            path = F.find_file_by_name_without_extension(F.scfg('td'), name)
            if not path:
                return CQT.msgbox(f'Файл {name} не найден')
            F.run_file_c(path)

    @CQT.onerror
    def otkrit_kd(self,*args):
        tbl = self.ui.tbl_chert
        if tbl.currentRow() == -1:
            return
        nk_ssil = CQT.num_col_by_name_c(tbl,'Путь')
        ssil = tbl.item(tbl.currentRow(),nk_ssil).text()
        os.startfile(f"{ssil}")

    @CQT.onerror
    def clear_naryad_bar(self,conn ='',cur = ''):
        self.lbl_tek_narayd(CMS.name_by_empl_c(self.glob_login))
        self.nar_info.clear()
        self.nar_info = None
        tab = self.ui.tabWidget_2
        #tab.setCurrentIndex(CQT.number_table_by_name_c(tab, 'Доступные наряды'))

        self.ui.te_zamechain.clear()
        self.ui.le_id_peresil.clear()
        CQT.clear_tbl(self.ui.tbl_list_brak)
        self.ui.cmb_brak_type1.clear()
        self.ui.cmb_brak_type2.clear()
        self.ui.cmb_brak_type3.clear()
        self.ui.lbl_abstract.clear()
        self.ui.cmb_abstract.setCurrentText('')
        self.ui.le_brak.clear()

    @CQT.onerror
    def time_ostalos_po_nar(self):
        tblk = self.ui.tbl_naryadi
        tblv = self.ui.tbl_naryadi_view_kompl
        if tblk.currentRow() == -1:
            CQT.msgbox('Не выбран наряд')
            return
        r = tblk.currentRow()
        nk_nar = CQT.num_col_by_name_c(tblk, 'Пномер')

        nk_mk = CQT.num_col_by_name_c(tblk, 'Номер_мк')
        if tblk.item(r,nk_nar).text() == '-':
            return
        nom_nar = int(tblk.item(r,nk_nar).text())
        nar = CMS.Naryads(nom_nar,self.bd_naryad)
        n_vrema = nar.get_n_time()
        rub = self.raschet_stoimosti_naryada()
        if rub > 0:
            import locale
            locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))
            rub_format = locale.currency(rub, grouping=True)
            CQT.statusbar_text(self,f'Наряд №{nom_nar}, предварительно расценен на {rub_format}',18,text_color='red')
        else:
            CQT.statusbar_text(self)

        conn, cur = CSQ.connect_bd(self.db_naryd,2)
        CQT.clear_tbl(tblv)
        if int(tblk.item(r,nk_mk).text()) != 0:
            try:
                CMS.specification_task_c(self, tblk, tblv,conn='',cur='')
            except:
                pass
        # 03.02.2026
        custom_request_c = f'''SELECT sum(Подытог) AS "Total Salary" FROM jurnal WHERE Номер_наряда == {nom_nar} AND ФИО == "{CMS.name_by_empl_c(self.glob_login)}"'''
        rez = CSQ.custom_request_c(self.db_naryd,custom_request_c,conn=conn,cur=cur)
        custom_request_c = f'''SELECT Штамп, Статус FROM jurnal WHERE Номер_наряда == {nom_nar} AND ФИО == "{CMS.name_by_empl_c(self.glob_login)}" ORDER BY datetime(Дата) DESC LIMIT 1'''
        rez_last = CSQ.custom_request_c(self.db_naryd, custom_request_c,conn=conn,cur = cur)
        CSQ.close_bd(conn,cur)

        if rez == False or rez_last == False:
            CQT.msgbox(f'Не удалось получить подытог')
            return
        tfakt = 0
        if len(rez) > 1:
            if rez[-1][0] != None:
                tfakt = rez[-1][0]
        t_zadel = 0
        if len(rez_last) > 1:
            if rez_last[-1][1] == "Начат":
                t_zadel = (F.get_time_shtamp_c() - rez_last[-1][0])//60
        raznica = round(n_vrema-tfakt-t_zadel,2)
        raznica_tdz = round(nar.Твремя - tfakt-t_zadel,2)
        def set_lbl_font_size(size=14):
            font = self.ui.lbl_ostalos.font()
            font.setPointSize(size)
            self.ui.lbl_ostalos.setFont(font)
        if raznica < 0:
            self.ui.lbl_ostalos.setText(f'По №{str(nom_nar)} дефицит нормы {F.miutes_to_time(abs(raznica))} (Трудов {raznica_tdz} мин.)  НЕ ЗАКРЫВАЙ наряд, не доделав до конца работу. иначе за простой придется отчитываться.')
            set_lbl_font_size(12)
        else:
            self.ui.lbl_ostalos.setText(f'По №{str(nom_nar)} осталось {F.miutes_to_time(raznica)} (Трудов {raznica_tdz}  мин.)')
            set_lbl_font_size(14)



    @CQT.onerror
    def tbl_naryadi_click(self,*args):
        CQT.statusbar_text(self)
        self.time_ostalos_po_nar()
        self.ui.fr_add_info_prost.setVisible(False)
        #F.sleep(3)


    @CQT.onerror
    def tbl_komplektovka_view_click(self,*args):
        tblv = self.ui.tbl_naryadi_view_kompl
        r = tblv.currentRow()
        nk_dse = CQT.num_col_by_name_c(tblv, 'Операции')
        self.ui.lbl_kompl_info.setText(tblv.item(r,nk_dse).text())

    @CQT.onerror
    def open_dir_chpy(self, line:str):
        if line == '':
            return
        try:
            path = '_'.join(line.split('_')[2:])
            if F.existence_file_c(path):
                F.open_dir_c(path)
        except:
            CQT.msgbox(f'Ошибка обработки строки')
    def calc_nar_info(self,num_nar:int, composition:CMS.Composition|None=None):
        row_data = None
        for it in DTCLS.table_nar:
            if it['Пномер'] == num_nar:
                row_data = it
        self.nar_info = None
        if not row_data:
            return row_data
        row_data['composition'] = composition

        self.nar_info = CLSS.Naryad_info(self, row_data)
        self.nar_info.fill_tbl()
        return  row_data

    @CQT.onerror #03.03.2026
    def on_click_btn_print_nar_settings(self, *args, **kwargs):
        import task_printer as TSKPRNT
        TSKPRNT.configure_print_task_fields(self, mk=self.nar_info.mk)


    @CQT.onerror
    def print_nar(self, *args, **kwargs):  #03.03.2026
        import task_printer as TSKPRNT
        from Documents_manage import print_out_naryad
        cfg_path = TSKPRNT.default_fields_config_path()
        fields = TSKPRNT.load_selected_fields(cfg_path) or TSKPRNT.default_selected_field_ids()
        zadanie_for_print = TSKPRNT.compose_task_for_print(
            self.nar_info,
            selected_field_ids=fields,
            fallback_to_saved=True,
        )
        self.nar_info.zadanie = zadanie_for_print or ""
        print_out_naryad(self.nar_info)

    @CQT.onerror
    def del_type_brak(self,*args,**kwargs):
        row = self.ui.tbl_list_brak.currentRow()
        if row == -1:
            CQT.msgbox(f'Не выбрана строка брака')
            return
        self.list_otk_brak.pop(row+1)
        CQT.fill_wtabl(self.list_otk_brak, self.ui.tbl_list_brak, {}, auto_type=False)


    @CQT.onerror
    def add_type_brak(self,*args,**kwargs):
        count_dse = self.ui.le_count_dse_brak.text()
        lvl1 = self.ui.cmb_brak_type1.currentText()
        lvl2 = self.ui.cmb_brak_type2.currentText()
        lvl3 = self.ui.cmb_brak_type3.currentText()
        vid = self.ui.chk_neisprav.checkState()
        if vid == 1:
            CQT.blink_obj_c(self,2,self.ui.chk_neisprav,f'Не выбран вид')
            return
        if lvl3 == '':
            CQT.blink_obj_c(self, 2, self.ui.cmb_brak_type3, f'Не выбран тип')
            return
        if vid == 0:
            vid_str = 'Исправимый'
            vid_for_db = 0
        else:
            vid_str = 'Неисправимый'
            vid_for_db = 1
        if not F.is_numeric(count_dse) or count_dse.strip() == '':
            CQT.blink_obj_c(self, 2, self.ui.le_count_dse_brak, f'Кол-во не указано')
            return
        self.list_otk_brak.append([lvl1,lvl2,lvl3,vid_for_db,F.valm(count_dse)])
        CQT.fill_wtabl(self.list_otk_brak,self.ui.tbl_list_brak,{},auto_type=False)

    @CQT.onerror
    def fill_cmbs_type_brak_3lvl(self,*args,**kwargs):
        self.ui.cmb_brak_type3.clear()
        id = self.ui.cmb_brak_type2.currentData()
        if not id:
            return
        list_data =  CSQ.custom_request_c(USRCNF.Config.project.db_naryad,f"""SELECT * FROM brak_categories WHERE parent = {id}""",rez_dict=True)
        self.ui.cmb_brak_type3.addItem('', None)
        for item in list_data:
            self.ui.cmb_brak_type3.addItem(item['name'], item['s_num'])

    @CQT.onerror
    def fill_cmbs_type_brak_2lvl(self,*args,**kwargs):
        self.ui.cmb_brak_type2.clear()
        self.ui.cmb_brak_type3.clear()

        id = self.ui.cmb_brak_type1.currentData()
        if not id:
            return
        list_data = CSQ.custom_request_c(USRCNF.Config.project.db_naryad,
                                         f"""SELECT * FROM brak_categories WHERE parent = {id}""",rez_dict=True)
        self.ui.cmb_brak_type2.addItem('', None)
        for item in list_data:
            self.ui.cmb_brak_type2.addItem(item['name'], item['s_num'])



    def clck_check_box_dse_empl_brak(self, check='', i='', j='', *args):
        tbl = self.ui.tbl_empl_brak
        if check:
            tbl.item(i,j).setText('1')
        else:
            tbl.item(i, j).setText('')

    def unpack_links_to_documents(
            self,
            task_text: str,
            label: QtWidgets.QTextBrowser,
            font_family: str = 'Arial',
            font_weight: str = 'normal',
            font_size: str = '14pt',
            regex: str = r'Документы: (.*?)\n',
            folder_with_pointer_href: str = F.scfg('td'),
    ) -> str:
        """
        Принимает текст :task_text и по регулярному выражению :regex определяет какие элементы
            в тексте станут ссылками <a>, ведущими на элемент из директории :folder_with_pointer_href
        Мутирует объект QTextBrowser изменяя поведение:
        - Объект не распаковывает бинарное содержимое путем QTextBrowser.setText, а пытается открыть файл
        Если файл не существует ссылка не распаковывается

        :task_text Текст задания
        :label Объект QTextBrowser для распаковки текста
        :regex Регулярное выражение для поиска строки-ссылки
        :folder_with_pointer_href Папка в которой будет производится поиск имени файла для составления href=
        :font_size Размер шрифта после обработки
        :font_weight Жирность шрифта после обработки
        :font_family Семейство шрифтов
        """
        ul_form = '<ul>{text}</ul>'
        li_form = '<li>{text}</li>'
        a_form = '<li><a href="file:///{link}">{text}</a></li>'
        pre_form = (
            "<pre style="
            f"\"font-family: {font_family}; "
            f"font-weight: {font_weight}; "
            f"font-size: {font_size};\">"
            "{text}</pre>"
        )

        signal_posted = label.property('anchor_posted')
        if not signal_posted:
            def anchorClicked(url, *args):
                if url.scheme() == 'file':
                    os.startfile(url.toLocalFile())
                return False

            label.anchorClicked.connect(anchorClicked)
            label.setProperty('anchor_posted', True)

        result_parts = []
        last_pos = 0

        for m in re.finditer(regex, task_text):
            start, end = m.span()

            # текст до блока "Документы"
            result_parts.append(task_text[last_pos:start])

            docs_raw = m.group(1)
            if not docs_raw:
                result_parts.append(m.group(0))
                last_pos = end
                continue

            iter_state = []
            documents = docs_raw.split('; ')

            for doc in documents:
                cleaned_doc = doc.strip()
                if not cleaned_doc:
                    continue

                path = F.find_file_by_name_without_extension(
                    folder_with_pointer_href,
                    cleaned_doc
                )

                if not path:
                    iter_state.append(li_form.format(text=cleaned_doc))
                    continue

                resolve = path
                if F.keep_extention_c(path) == '.lnk':
                    resolve = F.resolve_lnk_target(path)

                if not resolve or not pathlib.Path(resolve).exists():
                    iter_state.append(li_form.format(text=cleaned_doc))
                    continue

                iter_state.append(
                    a_form.format(link=path, text=cleaned_doc)
                )

            if iter_state:
                block = 'Документы: ' + ul_form.format(
                    text=''.join(iter_state)
                ) + '\n'
            else:
                block = m.group(0)

            result_parts.append(block)
            last_pos = end

        # хвост текста
        result_parts.append(task_text[last_pos:])

        label.setOpenLinks(False)
        return pre_form.format(text=''.join(result_parts))

    @CQT.onerror
    def load_naruad(self,*args):
        def fill_cmbs_type_brak(self):
            self.ui.cmb_brak_type1.clear()
            self.ui.cmb_brak_type2.clear()
            self.ui.cmb_brak_type3.clear()
            self.ui.chk_neisprav.setCheckState(1)
            id_data = CSQ.custom_request_c(USRCNF.Config.project.db_naryad,
                                             f"""SELECT s_num FROM brak_categories WHERE name = "{USRCNF.Config.place.Имя}";""",rez_dict=True,one=True)
            if not id_data:
                CQT.msgbox(f'Для {USRCNF.Config.place.Имя} не определен перечень брака. Обратитесь к администратору')
                return
            id = id_data['s_num']
            list_data = CSQ.custom_request_c(USRCNF.Config.project.db_naryad,
                                             f"""SELECT * FROM brak_categories WHERE parent = {id}""",rez_dict=True)
            self.ui.cmb_brak_type1.addItem('',None)
            for item in list_data:
                self.ui.cmb_brak_type1.addItem(item['name'],item['s_num'])

        self.ui.fr_fio_for_otk.setHidden(True)
        tab = self.ui.tabWidget_2
        tbl_comp = self.ui.tbl_compositions
        tbl = self.ui.tbl_naryadi

        t_comp = CQT.TableContext(tbl_comp)
        row = t_comp.current_row()
        composition = None
        nom_nar = '-'
        if not row.no_selection:
            id_comp = int(row.value('id'))
            composition = DTCLS.user_compositions.find(id_comp)
            set_nar = composition.get_set_nars(set([_['Пномер'] for _ in DTCLS.table_nar]))
            if not set_nar:
                CQT.msgbox(f'Ошибка загрузки нарядов')
                return
            for nar in set_nar:
                nom_nar = nar
                break

        else:
            t = CQT.TableContext(tbl)
            row = t.current_row()
            if row.no_selection:
                CQT.msgbox('Не выбран наряд')
                return
            if t.current_column_name() == 'Статус_ЧПУ':
                dir = row.value('Статус_ЧПУ')
                self.open_dir_chpy(dir)
                return
            nom_nar = row.value('Пномер')
            if nom_nar == '-':
                #self.load_prostoy_nar() 05.03.2026 это зачем? если они создаются с номером через кнопку
                tab.setCurrentIndex(CQT.number_table_by_name_c(tab, 'Доступные наряды'))
                return
            nom_nar = int(nom_nar)

        nar_obj = CMS.Naryads(nom_nar,self.db_naryd,self.DICT_DOLGN_ETAP,self.bd_users,self.DICT_EMPLOEE_FULL_WITH_DEL)
        conn, cur = CSQ.connect_bd(self.db_naryd)
        if self.check_dostupnosti_nar(nom_nar) == False:
            self.zapoln_tabl_naryadov()
            CSQ.close_bd(conn,cur)
            tab.setCurrentIndex(CQT.number_table_by_name_c(tab, 'Доступные наряды'))
            CQT.msgbox('Наряд недоступен')
            return
        else:
            CSQ.close_bd(conn,cur)
            pass
        row_data = self.calc_nar_info(nar_obj.Пномер,composition)


        is_vnepl_otk = nar_obj.Категория_внепл == 18 #" 23.03.2026

        self.glob_otk_kontrol = CMS.is_otk_nar(row_data['Операции'],self.DICT_OPER_NAME) or is_vnepl_otk
        CQT.clear_tbl(self.ui.tbl_list_brak)
        self.list_otk_brak = copy.copy(self.glob_list_otk_brak)

        if self.glob_otk_kontrol:
            self.ui.tbl_empl_brak.setEnabled(True)
            CQT.clear_tbl(self.ui.tbl_empl_brak)
            if nar_obj.ФИО_для_ОТК_от_мастера != '':
                row_fio_or_nars = nar_obj.ФИО_для_ОТК_от_мастера.replace(";","|")
            else:
                row_fio_or_nars = CMS.get_list_fio_otk(self.db_naryd,row_data['ФИО_для_ОТК'])
            list_for_select = [['Чек',"ФИО"]]
            for user in row_fio_or_nars.split('|'):
                list_for_select.append(['',user])
            CQT.fill_wtabl(list_for_select,self.ui.tbl_empl_brak,{})
            if nar_obj.ФИО_для_ОТК_от_мастера != '':
                for i in range(self.ui.tbl_empl_brak.rowCount()):
                    CQT.add_check_box(self.ui.tbl_empl_brak, i, 0, conn_func_checked_row_col=self.clck_check_box_dse_empl_brak,val=True)
                    self.ui.tbl_empl_brak.item(i, 0).setText('1')
                self.ui.tbl_empl_brak.setEnabled(False)
            else:
                for i in range(self.ui.tbl_empl_brak.rowCount()):
                    CQT.add_check_box(self.ui.tbl_empl_brak, i, 0, conn_func_checked_row_col=self.clck_check_box_dse_empl_brak)


            self.ui.lbl_fio_for_otk.setText(row_fio_or_nars)
            self.ui.lbl_fiomaster_for_otk.setText(row_data['Распред_ФИО'])
            self.ui.fr_fio_for_otk.setHidden(False)
            self.ui.btn_pauza.setText('НЕ ПРИНЯТО (Shift-пауза)')
            self.ui.btn_zaconch.setText('ПРИНЯТО')
            self.ui.btn_nachat.setText('ПРЕДЪЯВЛЕНО(НАЧАТЬ)')
            fill_cmbs_type_brak(self)
        else:
            self.ui.fr_fio_for_otk.setHidden(True)
            self.ui.btn_pauza.setText('Пауза')
            self.ui.btn_zaconch.setText('Закончить')
            self.ui.btn_nachat.setText('Начать')

        self.ui.btn_nachat.setEnabled(self.nar_info.state is not CLSS.States_nar.started)
        tab.setCurrentIndex(CQT.number_table_by_name_c(tab, 'Управление нарядом'))

    @CQT.onerror
    def transform_current_user_for_sql(self):
        """
        Возвращает repr представление текущего имени
            Если профессия связана с абстрактом, то соедниняет псевдонимы с текущим именем через ,
        """
        cred = self.DICT_EMPL_FULL[self.glob_fio]
        department = cred['Подразделение']
        learn_user = CMS.name_by_empl_c(self.glob_login)
        user = repr(learn_user)
        users = {
            fio: cred
            for fio, cred in self.DICT_EMPL_FULL.items()
            if cred['Подразделение'].strip() == department.strip() and (cred['Режим'] == 'Абстракт' or learn_user == fio)
        }
        proffession_have_abstract = any(user for user in users.values() if user['Режим'] == 'Абстракт')

        if proffession_have_abstract:
            user = ', '.join(repr(u) for u in users)
        return user
    def upd_color_priority(self,cur_row:CQT.TableRow):
        prior = cur_row.value('Приоритет')
        clr = [240,240,240]
        if F.is_numeric(prior):
            prior = int(prior)
            clrprior = prior if prior < 11 else 10
            clr = CMS.Color_tbl(clrprior * 10, False).rgb

        cur_row.set_color_background(*clr,col_name='Приоритет')

    @CQT.onerror
    def zapoln_tabl_naryadov(self,*args):
        tbl = self.ui.tbl_naryadi
        if self.glob_login == "":
            CQT.msgbox('Необходимо войти')
            return

        user = self.transform_current_user_for_sql()
        ref_user = DTCLS.USER_CONFIG.User.ID_ФизЛица
        postfix = '((mk.Статус != "Закрыта" AND mk.Дата_завершения == "") OR (mk.Пномер = 0)) AND'
        if 'shift' in CQT.get_key_modifiers(self):
            postfix = ''
        custom_request_c = f'''
            SELECT 
                COALESCE( groups.name, "") as Группа,
                naryad.Пномер, 
                naryad.Дата, 
                naryad.Номер_мк, 
                naryad.Задание, 
                naryad.ФИО, 
                naryad.ФИО2, 
                naryad.Твремя, 
                naryad.Норма_времени AS "Норматив время", 
                "" AS "Время", 
                naryad.Компл_номер_тара,
                naryad.Компл_адрес, 
                naryad.Примечание, 
                naryad.Внеплан,
                CASE WHEN mk.Приоритет IS NOT NULL and mk.Приоритет != ""
                   THEN mk.Приоритет
                   ELSE plan.Приоритет 
                END AS Приоритет,
                
                naryad.Коэфф_сложности, 
                naryad.Виды_работ, 
                naryad.Опер_время, 
                mk.Статус_ЧПУ, 
                zagot.Прим_резка, 
                naryad.ФИО_для_ОТК , 
                naryad.Операции  , 
                naryad.Распред_ФИО , 
                naryad.Кол_повт_приемок AS "Кол_во повт. приёмок",
                plan.Позиция as "Позиция",
                пл_оуп.Номенклатура_ЕРП as "Номенклатура_ЕРП",
                CASE 
                    WHEN знпр.№ERP IS NOT NULL 
                    THEN знпр.№ERP 
                    ELSE пл_оуп.№ERP  
                END AS "Номер_заказа", 
                CASE WHEN знпр.№проекта IS NOT NULL 
                   THEN знпр.№проекта 
                   ELSE пл_оуп.№проекта 
                END AS Номер_проекта,
                COALESCE( groups.id, "") as _id,
                COALESCE( groups.summ, "") as _gr_summ
            FROM naryad 
            INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
            LEFT JOIN plan ON mk.НомКплан = plan.Пномер
            LEFT JOIN пл_оуп ON mk.НомКплан = пл_оуп.НомПл
            LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП
            INNER JOIN коды_веплана_для_наряда ON коды_веплана_для_наряда.code = naryad.Внеплан
            INNER JOIN zagot ON zagot.Ном_МК = naryad.Номер_мк 
            LEFT JOIN naryad_groups ON  (naryad_groups.id_nar = naryad.Пномер AND naryad_groups.fio IN ({user}))
            LEFT JOIN groups ON (groups.id == naryad_groups.id_group AND groups.user_ref == "{ref_user}")
            WHERE коды_веплана_для_наряда.poki = {self.place.poki} AND {postfix}  naryad.Подтвержд_вып_дата == "" AND
                         ((naryad.ФИО IN ({user}) AND naryad.Фвремя == "") 
                        OR (naryad.ФИО2 IN ({user}) AND naryad.Фвремя2 == ""));'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c, rez_dict=True, attach_dbs=USRCNF.Config.project.db_kplan) #04.09.25
        if rez == False or rez == None:
            CQT.msgbox(f'БД недоступна, пробуй еще')
            return
        for i in range(len(rez)):
            if rez[i]['ФИО'] != '' and  rez[i]['ФИО2'] !='':
                rez[i]['Норматив время'] = round(rez[i]['Норматив время']/2,2)
            rez[i]['Время'] = F.miutes_to_time(rez[i]['Норматив время'])
        self.ui.label_12.setText(f'План работ для на {F.now()}')
        if len(rez)>0:
            rez = F.sort_by_column_c(rez,'Приоритет',type_compare='numeric')

        DTCLS.user_compositions = CMPM.load_user_compositions([_['Пномер'] for _ in rez])
        DTCLS.table_nar = copy.deepcopy(rez)

        rez.insert(0,{
                        'Группа': '',
                      'Пномер':'-',
                      'Дата':'-',
                      'Номер_мк':'-',
                      'Задание':'ПРОСТОЙ',
                      'ФИО':CMS.name_by_empl_c(self.glob_login),
                      'ФИО2':'',
                      'Твремя':'1',
                      'Норматив время': '1',
                      'Время': '1',
                      'Компл_номер_тара':'',
                      'Компл_адрес':'',
                      'Примечание':'ПРОСТОЙ',
                      'Внеплан':'-',
                      'Номер_проекта':'-',
                      'Позиция': '-',
                      'Номер_заказа':'-',
                      'Номенклатура_ЕРП': '-', # 04.09.25 по задаче 100059700
                      'Приоритет':'',
                      'Коэфф_сложности':'0.01',
                      'Виды_работ':'-',
                      'Опер_время':'',
                      'Статус_ЧПУ':'',
                      'Прим_резка':'',
                      'ФИО_для_ОТК':'',
                      'Операции':'',
                      'Распред_ФИО':'',
                        '_id':'',
                        '_gr_summ':'',
        })
        t = CQT.TableContext(tbl)
        if t.count:
            t.save_coord()
        CQT.fill_wtabl(rez, tbl,auto_type=False,font_size=12,styleSheet=CQT.MES_EDIT_CSS,selectionBehavior='SelectRows')
        t = CQT.TableContext(tbl)
        clr = CMS.Color_tbl(10)
        gr_emoj = CEMOJ.EmojiMain.ДокументыДанные.folder.symbol
        with CQT.table_updating(t):
            hide_fields = {'Норматив время','Компл_номер_тара','Компл_адрес','Задание','Виды_работ',
                           'Опер_время','ФИО_для_ОТК','Операции','_id','_gr_summ'}
            for column_name in hide_fields:
                t.hide(column_name)

            CQT.add_btn(tbl, 0, t.nf['Дата'], 'СОЗДАТЬ', True, self.create_prostoi_nar, '')
            spis_prost = list(self.DICT_TYPE_PROSTOI.keys())

            CQT.add_combobox('',tbl, 0, t.nf['ФИО2'], spis_prost, False,self.select_type_prost)

            self.lbl_tek_narayd(CMS.name_by_empl_c(self.glob_login))
            self.ui.cmb_nom_nar_prost.clear()
            self.ui.cmb_nom_nar_prost.addItem('')
            self.ui.cmb_nom_nar_prost.addItems([ str(_['Пномер']) for _ in rez if _['Задание'] != 'ПРОСТОЙ'])
            fl_gr_found = False
            for row in t.rows():
                if 'Повт.Приёмка' in row.value('Примечание'):
                    row.set_color_font(*clr.rgb)
                if row.value('_id'):
                    row.set_value('Группа', f'{gr_emoj}({round(F.valm(row.value("_gr_summ")),2)}) {row.value("Группа")}' )
                    fl_gr_found = True
                self.upd_color_priority(row)
            if not fl_gr_found:
                t.hide('Группа')

            tbl.resizeColumnsToContents()
            CMS.load_column_widths(self,tbl)
        t.restore_selected_cell()
        CMPM.fill_table_compositions()



    def check_zav_nar(self,nom_nar,fio):
        query = f'''SELECT Дата FROM jurnal WHERE Номер_наряда == {nom_nar} and Статус == "Завершен" and ФИО == "{fio}"'''
        rez = CSQ.custom_request_c(self.db_naryd,query,one=True)
        if len(rez) == 1 or query == False:
            return False
        return True
    def select_type_prost(self, text, row, col):
        koef= 0.01
        if text in self.DICT_TYPE_PROSTOI:
            koef = self.DICT_TYPE_PROSTOI[text]['Коэффициент_наряда']
        self.ui.tbl_naryadi.item(0,CQT.num_col_by_name_c(self.ui.tbl_naryadi,'Коэфф_сложности')).setText(str(koef))
        self.ui.fr_add_info_prost.setVisible(True)

        view_nom_nar_lbl = self.DICT_TYPE_PROSTOI[text].get('kod') != 18

        self.ui.btn_seletc_base_doc.setHidden(False)
        self.ui.cmb_nom_nar_prost.setHidden(True)
        self.ui.le_base_nar.setHidden(not view_nom_nar_lbl)

        default_mk, default_nar = '№ МК', '№ Нар'
        self.ui.le_base_nk.setText(default_mk)
        self.ui.le_base_nk.setProperty('default', default_mk)
        self.ui.le_base_nar.setText(default_nar)
        self.ui.le_base_nar.setProperty('default', default_nar)


    def create_prostoi_nar(self,row,col):
        comment_column = CQT.num_col_by_name_c(self.ui.tbl_naryadi, 'ФИО2')
        primech = self.ui.tbl_naryadi.cellWidget(row,comment_column).currentText() #10.03.2026
        pk_nar = self.ui.le_base_nar.text()
        pk_mk = self.ui.le_base_nk.text()
        if primech not in self.DICT_TYPE_PROSTOI:
            CQT.blink_obj_c(self,2,self.ui.tbl_naryadi,'Не указана причина простоя')
            return False
        dop_prim_prost =''
        num_bad_bar = 0
        code_category = self.DICT_TYPE_PROSTOI[primech].get('kod')
        if code_category == 18:  # Финишный ОТК
            if pk_mk == self.ui.le_base_nk.property('default'):
                CQT.blink_obj_c(self, 2, self.ui.le_base_nk,
                                'Не указан номер МК')
                return False
        if primech == "Ошибка нормирования и технологии":
            if pk_nar == self.ui.le_base_nar.property('default'):
                CQT.blink_obj_c(self, 2, self.ui.le_base_nar,
                                'Не указан номер наряда, в котором не хватает времени/операции')
                return False
            if self.ui.le_nom_nar_prost.text().strip() == '':
                CQT.blink_obj_c(self, 2, self.ui.le_nom_nar_prost, 'Не указано примечание о том что не хватает времени/операции')
                return False
            dop_prim_prost = self.ui.le_nom_nar_prost.text().strip()
            # num_bad_bar = self.ui.cmb_nom_nar_prost.currentText()
            num_bad_bar = self.ui.le_base_nar.text()
        rez  = CMS.create_nar_prosoy(self.glob_login,
                                     primech,
                                     self.DICT_TYPE_PROSTOI[primech]['Коэффициент_наряда'],
                                     dop_prim_prost,
                                     num_bad_bar,
                                     pk_mk=pk_mk,
                                     code_category=self.DICT_TYPE_PROSTOI[primech]['kod'])
        if rez == False:
            CQT.msgbox(f'Неудачно!, попробуй еще.')
            return
        self.ui.le_nom_nar_prost.setText('')
        self.ui.le_base_nar.setText(self.ui.le_base_nar.property('default'))
        self.ui.le_base_nk.setText(self.ui.le_base_nk.property('default'))
        self.zapoln_tabl_naryadov()
        CQT.msgbox('Наряд успешно создан')

    def on_click_btn_seletc_base_doc(self, *args, **kwargs): #17.03.2026
        db_kplan = USRCNF.Config.project.db_naryad
        col = CQT.num_col_by_name_c(self.ui.tbl_naryadi, 'ФИО2')
        text = self.ui.tbl_naryadi.cellWidget(0, col).currentText()

        if self.DICT_TYPE_PROSTOI[text].get('kod') == 18:

            result = CSQ.custom_request_c(
                db_kplan,
                f"""
                    SELECT mk.Пномер AS "НомерМК", пл_отк.НомПл AS "НомерКПЛ",
                        CASE WHEN знпр.№ERP IS NOT NULL 
                           THEN знпр.№ERP 
                           ELSE mk.Номер_заказа 
                           END AS Номер_заказа, 

                            CASE WHEN знпр.№проекта IS NOT NULL 
                           THEN знпр.№проекта 
                           ELSE mk.Номер_проекта 
                           END AS Номер_проекта
                    FROM пл_отк 
                    INNER JOIN пл_оуп ON пл_оуп.НомПл = пл_отк.НомПл
                    INNER JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП
                    INNER JOIN mk ON пл_отк.НомПл = mk.НомКплан 
                    WHERE mk.Статус = "Открыта" AND пл_отк.Контр_покрытие_ФИО = ''
                """,
                rez_dict=True,
                attach_dbs=USRCNF.Config.project.db_kplan
            )
            result = CQT.msgboxg_get_table(self, 'Выберите МК-основание', result,
                                           ExtendedSelection=False, selectRows=True,
                                           btn0_name='Выбрать')
            if not result:
                return
            self.ui.le_base_nk.setText(result['НомерМК'])
        else:
            tbl = self.ui.tbl_naryadi
            data = CQT.list_from_wtabl_c(tbl, rez_dict=True) or []
            if not data:
                return
            result = CQT.msgboxg_get_table(self, 'Выберите наряд-основание', data[1:], ExtendedSelection=False,
                                           selectRows=True,
                                           btn0_name='Выбрать')
            if not result:
                return
            self.ui.le_base_nk.setText(result['Номер_мк'])
            self.ui.le_base_nar.setText(result['Пномер'])

    #+++ 15.07.25 по задаче 100056733
    def get_current_abstract_name(self, nom_nar: int | str):
        nar_obj = CMS.Naryads(db_naryad=self.db_naryd, p_nom_or_row=nom_nar,
                              dict_empl=self.DICT_EMPL_FULL,
                              dict_dolgn_etap=self.DICT_DOLGN_ETAP)
        nick = self.get_free_abstract_fio_place(nom_nar, self.glob_fio) # 15.07.25 Если имя уже числится в наряде отдаст имя
        return getattr(nar_obj, nick)                                   # 15.07.25 Иначе отдаст имя абстракта
    #--- 15.07.25

    def get_free_abstract_fio_place(self, nom_nar: int, fio: str) -> str | None:  # 21.04.25
        """
        @param fio Полное имя искомого работника
        @nom_nar Номер наряда
        """
        current_department = self.DICT_EMPL_FULL[self.glob_fio]['Подразделение']
        abstract_prof_names = [fio for fio, cred in self.DICT_EMPL_FULL.items() if cred['Режим'] == 'Абстракт' and cred['Подразделение'].strip() == current_department.strip()]
        query = f'SELECT ФИО, ФИО2 FROM naryad WHERE Пномер = {nom_nar}'
        naryad_item = CSQ.custom_request_c(self.db_naryd, query, rez_dict=True, one=True)
        if not isinstance(naryad_item, dict):
            return
        if self.glob_fio in naryad_item.values():
            abstract_prof_names = [self.glob_fio]
        for nick, val in naryad_item.items():
            if val in abstract_prof_names:
                return nick

    def replace_abstract_name(self, nom_nar: int, fio_executor: str) -> bool: #21.04.25
        """
        @nom_nar Номер наряда
        @fio_executor Полное имя пользователя, на которое заменяем имя абстракта
        """
        nick = self.get_free_abstract_fio_place(nom_nar, fio_executor)
        if nick is None:
            return False
        query = f"UPDATE naryad SET {nick} = {fio_executor!r} WHERE Пномер = {nom_nar}"
        return CSQ.custom_request_c(self.db_naryd, query)

    @CQT.onerror
    def pauza_nar(self,*args):
        self.stop_nar("Приостановлен")

    @CQT.onerror
    def zaversh_nar(self,*args):
        self.stop_nar("Завершен")

    @CQT.onerror
    def check_abstrakt(self,primech):
        if self.glob_fio not in self.DICT_EMPL_FULL:
            CQT.msgbox(f'{self.glob_fio} не в БД')
            return False
        if self.DICT_EMPL_FULL[self.glob_fio]['Режим'] == 'Абстракт':
            if self.ui.lbl_abstract.text() == '':
                CQT.msgbox(f'Не выбрано реальное ФИО (Блок Абстракт ФИО)')
                return False
            if self.ui.lbl_abstract.text() not in self.DICT_EMPL_FULL:
                CQT.msgbox(f'{primech} не в БД имен')
                return False
        return True
    @CQT.onerror
    def start_nar(self, *args):
        if not self.auth_manager.check_actual_password(self.glob_fio): #12.03.2026
            CQT.msgbox(f'Нужно обновить пароль через меню "Параметры"')
            return

        if self.nar_info is None:
            CQT.msgbox(f'Наряд не выбран')
            return
        nom_nar = self.nar_info.nom_nar
        if not CMS.check_execution_previous_operations(self,nom_nar):
            CQT.msgbox(f'по наряду {nom_nar} не выполнены требования маршрута, '
                       f'работа наряда ЗАБЛОКИРОВАНА\n\nОбратиться к мастеру.')
            return

        if self.nar_info.group_id:
            DTCLS.gr_groups_nar = CMS.Groups_nar(DTCLS.USER_CONFIG.common_config.db_naryad, DTCLS.app_self,
                                                     DTCLS.USER_CONFIG.User)
            gr = DTCLS.gr_groups_nar.find_gr(int(self.nar_info.group_id))
            list_not_zav_nar = [str(_) for _ in  gr.load_s_nums_nar()]
            if not CQT.msgboxgYN(f'Наряд состоит в группе "{gr.name}".\nВ обработку попадут'
                                 f' наряды №№:\n{", ".join(list_not_zav_nar)}',app_self=self,
                                 btn0_name='ОК',
                                 btn1_name='Отмена'):
                return
        if self.nar_info.composition:
            comp = self.nar_info.composition
            set_nar = comp.get_set_nars(set([_['Пномер'] for _ in DTCLS.table_nar]))
            if not CQT.msgboxgYN(f'Наряд состоит в раскрое "{comp.name}".\nВ обработку попадут'
                                 f' наряды №№:\n{", ".join([str(_) for _ in set_nar])}',app_self=self,
                                 btn0_name='ОК',
                                 btn1_name='Отмена'):
                return

        now = F.now()
        primech = self.ui.te_zamechain.toPlainText()
        if not self.check_abstrakt(primech):
            return
        jur_obj = CMS.Jurnal_nar(self.db_naryd, user=self.glob_fio) #23.04.25 Глобальный объект журнала
        tek = jur_obj.get_ontime_naruad()
        if tek == False or tek ==  (False,False,False):
            CQT.msgbox(f'БД занята попробуй позже')
            return
        if tek[0] != '':
            CQT.msgbox('Нельзя начать несколько нарядов одновременно')
            return
        if self.check_zav_nar(nom_nar, CMS.name_by_empl_c(self.glob_login)):
            CQT.msgbox(f'Наряд {nom_nar} уже завершен ранее')
            return
        tab = self.ui.tabWidget_2
        if self.check_dostupnosti_nar(nom_nar) == False:
            tab.setCurrentIndex(CQT.number_table_by_name_c(tab, 'Доступные наряды'))
            CQT.msgbox('Наряд недоступен')
            return
        # ++ 15.07.25 по задаче 100056733
        user = self.glob_fio
        if self.glob_otk_kontrol:
            user = self.get_current_abstract_name(nom_nar)
            jur_obj = CMS.Jurnal_nar(self.db_naryd, user=user, nom_nar=nom_nar)
            tek_abstract = jur_obj.get_ontime_naruad()
            if tek_abstract[0]:
                return CQT.msgbox(f'Наряд: {nom_nar} уже начат!')
            if self.check_zav_nar(nom_nar, user):
                return CQT.msgbox(f'Наряд {nom_nar} уже завершен ранее')

        jur_obj = CMS.Jurnal_nar(self.db_naryd, user=user, nom_nar=nom_nar) #23.04.25 Объект журнала по наряду
        # -- 15.07.25 по задаче 100056733
        rez = jur_obj.add_new_row(
            DICT_EMPL_FULL=self.DICT_EMPL_FULL,
            lbl_abstract_text='',
            date_time=now,
            primech=primech
        )  # 21.04.25
        if not rez:
            CQT.msgbox(f'Не удачно попробуй чуть позже')
            F.sleep(2)
            return
        if not self.glob_otk_kontrol:
            self.replace_abstract_name(nom_nar, self.glob_fio) # 15.07.25 по задаче 100056733
        CQT.msgbox('Наряд успешно запущен')

        self.clear_naryad_bar()
        tab = self.ui.tabWidget_2
        tab.setCurrentIndex(CQT.number_table_by_name_c(tab, 'Доступные наряды'))
        if not self.ui.chk_come_back.isChecked():  # если стоит галочка вернуться обратно то...
            self.load_naruad()


    @CQT.onerror
    def stop_nar(self, vid_stop):
        def apply_brak(self, nom_nar, msg_into_b24=True):
            usr_1 = ''
            usr_2 = ''
            list_empl_braks = CQT.list_from_wtabl_c(self.ui.tbl_empl_brak, rez_dict=True)
            coun_select_empl_brak = 0
            for item in list_empl_braks:
                if item['Чек'] == '1':
                    if usr_1 == '':
                        usr_1 = item['ФИО']
                    else:
                        if usr_2 == '':
                            usr_2 = item['ФИО']

                    coun_select_empl_brak += 1
            if coun_select_empl_brak > 2:
                CQT.msgbox(f'Можно выбрать не более двух ответственных за брак')
                return False
            if usr_1 == '' and usr_2 == '':
                CQT.msgbox(f'Не выбран ответственный за брак')
                return False
            # if self.ui.lbl_fio_for_otk.text() != '':
            #    usr_1, usr_2 = self.ui.lbl_fio_for_otk.text().split('|')

            prim = self.ui.te_zamechain.toPlainText().strip().replace('\n', 'LF')
            row = [F.now(), self.ui.lbl_abstract.text(), nom_nar, prim,
                   usr_1, usr_2]
            num_brak = CSQ.custom_request_c(self.bd_naryad,
                                            f"""INSERT INTO brak (date,empl,nom_nar,msg,usr_1,usr_2) VALUES ({CSQ.questions_for_mask(row)}) RETURNING s_num""",
                                            list_of_lists_c=row, one=True, rez_dict=True)['s_num']  # 10.11.25
            # num_brak = CSQ.custom_request_c(self.bd_naryad, f"""SELECT s_num FROM brak ORDER BY s_num DESC LIMIT 1""",
            rows_list_brak = []
            for item in self.list_otk_brak[1:]:
                item.append(num_brak)
                rows_list_brak.append(copy.copy(item))

            CSQ.custom_request_c(self.bd_naryad,
                                 f"""INSERT INTO list_brak (group_1,group_2,group_3,neisprav,count_dse,num_list_brak)
                                      VALUES ({CSQ.questions_for_mask(rows_list_brak[0])})""",
                                 list_of_lists_c=rows_list_brak)

            if msg_into_b24:
                try:
                    hat = copy.copy(self.list_otk_brak[0])
                    hat[3] = "Неисправимый"
                    hat[4] = "Кол-во ДСЕ"
                    hat.append("№ МЕС")
                    sender = B24.B24Sender()
                    msg_rows = [f'    {i + 1}.' + " | ".join([str(it) for it in _]) for i, _ in
                                enumerate(self.list_otk_brak[1:])]
                    msg_rows.insert(0, f'      ' + " | ".join(hat))
                    txt_rows = "\n".join(msg_rows)
                    result_msg = f'{F.now()} на {usr_1} {usr_2}\nпо наряду {nom_nar}, зарегистрирован брак ({prim.replace("LF", " ")}):\n' + txt_rows
                    sender.send_msg_by_action('Только брак', result_msg)
                except:
                    print(f'Не удалось вывести в Б24 сообщение')
                    pass

            return True

        # ===============================================================================
        if self.nar_info is None:
            CQT.msgbox(f'не выбран наряд')
            return

        db_nar = USRCNF.Config.project.db_naryad
        nom_nar = self.nar_info.nom_nar
        group_id = self.nar_info.group_id
        composition = self.nar_info.composition
        nar_obj = CMS.Naryads(nom_nar, db_nar,
                              self.DICT_DOLGN_ETAP, USRCNF.Config.project.db_users, self.DICT_EMPL_FULL)
        lbl_abstract = self.ui.lbl_abstract.text()
        zadanie = self.ui.textBrowser_zadanie.toPlainText().replace('\n', 'LF')
        primech = self.ui.te_zamechain.toPlainText().strip()
        nom_mk = self.nar_info.mk

        if vid_stop == 'Приостановлен':
            if primech == '' or len(primech) < 4:
                if self.glob_otk_kontrol:
                    self.ui.te_zamechain.setText('Несоответствие требованиям КД в результате контроля ОТК')
                    primech = self.ui.te_zamechain.toPlainText().strip()
                else:
                    CQT.blink_obj_c(self, 2, self.ui.te_zamechain, 'Не указана причина паузы')
                    return

            if self.glob_otk_kontrol:
                mods = CQT.get_key_modifiers(self)
                if mods == []:
                    if len(self.list_otk_brak) <= 1:
                        CQT.msgbox(f'Список браков пуст')
                        return
                    if not self.check_abstrakt(primech):
                        return
                    if not apply_brak(self, nom_nar):
                        return
                if 'shift' in mods:
                    if len(self.list_otk_brak) > 1:
                        CQT.msgbox(f'Список браков НЕ пуст')
                        return

        if vid_stop == 'Завершен':
            if not CMS.check_id_peresil(self, nom_nar, self.ui.le_id_peresil.text(), kod_oper=2):
                return
            if not self.check_abstrakt(primech):
                return
        # ++ 15.07.25 по задаче 100056733

        try:
            if self.glob_otk_kontrol:
                lbl_abstract = self.glob_fio
                abstract_name = self.get_current_abstract_name(nom_nar)
                # self.ui.lbl_nom_nar.setText(str(nom_nar)) ПРОВЕРИТЬ
                jur_obj = CMS.Jurnal_nar(db_nar, user=abstract_name, nom_nar=nom_nar)
            else:
                jur_obj = CMS.Jurnal_nar(db_nar, user=self.glob_fio)
            # -- 15.07.25 по задаче 100056733
            nomer_naryada, pnomer, data_nach = jur_obj.get_ontime_naruad(True)
            if nomer_naryada == False:
                return
            if str(nomer_naryada) != str(nom_nar):
                CQT.msgbox('Выбран не запущенный наряд')
                return False, False
            pnomer_nach = str(pnomer)

        except:
            CQT.msgbox(f'Не удалось проверить текущий наряд, попробуй еще')
            return
        if pnomer_nach == False:
            return

        # =======check==============

        if self.check_dostupnosti_nar(nom_nar) == False:
            tab = self.ui.tabWidget_2
            tab.setCurrentIndex(CQT.number_table_by_name_c(tab, 'Доступные наряды'))
            self.zapoln_tabl_naryadov()
            CQT.msgbox('Наряд недоступен')
            return
        last_status_nar = jur_obj.get_last_status_nar()
        if last_status_nar != 'Начат':
            CQT.msgbox('Статус наряда не позволяет выполнить действие')
            return

        #======================================

        is_idle = zadanie == 'ПРОСТОЙ'
        if not jur_obj.add_new_row(self.DICT_EMPL_FULL, lbl_abstract, F.now(), vid_stop, primech, is_idle):  # 15.05.25
            return

        # ======================================

        if vid_stop == 'Завершен':

            CMS.ending_oform_zav_nar(nar_obj, jur_obj, self.glob_otk_kontrol, self.glob_fio)

        #==============группировка=====================================
        if group_id:
            GRM.apply_group_event(int(group_id),int(nom_nar))
        if composition:
            GRM.apply_comp_event(composition,int(nom_nar))
        # ======================================
        self.zapoln_tabl_naryadov()

        self.clear_naryad_bar()

        CQT.msgbox(f'Наряд успешно {vid_stop}')


    @CQT.onerror
    def add_opoveshenie(self, vid_stop, nom_nar, nom_mk, fio, primech):#OFF
        custom_request_c = f'''SELECT Номер_заказа, Номер_проекта, Вид FROM mk WHERE Пномер == {nom_mk}'''
        rez = CSQ.custom_request_c(self.db_naryd,custom_request_c)
        np = rez[-1][1]
        nz = rez[-1][0]
        vid = rez[-1][2]
        spis_opov = [F.now('%d.%m.%Y %H:%M:%S'), str(nom_nar), np + ' ' + nz, vid, fio, vid_stop,primech]
        F.add_rec_into_file_c(F.scfg('Opoveshenie') + F.sep() + 'Opoveshenie_tgm.txt', spis_opov, True, sep='|')
        F.add_rec_into_file_c(F.scfg('Opoveshenie') + F.sep() + 'Opoveshenie_tgm_arh.txt', spis_opov, True, sep='|')
        if self.ui.tbl_naryadi.rowCount() == 0:
            F.add_rec_into_file_c(F.scfg('Opoveshenie') + F.sep() + 'Opoveshenie_tgm.txt',
                             f'{fio} остался без заданий. Уважаемые коллеги, пожалуйста примите меры!', True, sep='')
            F.add_rec_into_file_c(F.scfg('Opoveshenie') + F.sep() + 'Opoveshenie_tgm_arh.txt',
                             f'{fio} остался без заданий. Уважаемые коллеги, пожалуйста примите меры!', True, sep='')


    @CQT.onerror
    def lbl_tek_narayd(self,fio):
        lbl_tek_nar = ""

        jur_obj = CMS.Jurnal_nar(self.db_naryd, user=self.glob_fio)
        rez = jur_obj.get_ontime_naruad()
        if rez == False or rez == (False,False,False):
            lbl_tek_nar = "-"
        if rez == None:
            lbl_tek_nar = "-"
        if rez[0] == '':
            lbl_tek_nar = "-"
        else:
            lbl_tek_nar = str(rez[0])
        DTCLS.USER_CONFIG.cust_windowTitle = f'Текущий наряд: {lbl_tek_nar}'
        self.ui.lbl_tek_nar.setText(lbl_tek_nar)

    @CQT.onerror
    def tekush_naruad(self,fio):
        custom_request_c = f'''SELECT Номер_наряда, Пномер, Дата FROM jurnal WHERE ФИО == "{fio}" AND
                    Статус == "Начат" and  Подытог == 0'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c, hat_c=False)
        if rez == False:
            CQT.msgbox(f'Бд занята пробуй позже')
            return False, False, False
        if rez == None:
            CQT.msgbox(f'Данные не получены')
            return False, False, False
        if len(rez) == 0:
            return ['','','']
        return rez[0]


app = QtWidgets.QApplication(sys.argv)
args = sys.argv[1:]
myappid = 'Powerz.BAG.SustControlWork.20.07.2021'  # !!!
QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
app.setWindowIcon(QtGui.QIcon(os.path.join("icons", "tab.png")))

S = F.cfg['Stile'].split(",")
app.setStyle(S[0])
application = mywindow()
from project_cust_38.widget_spy import install_pyqt_event_hook
install_pyqt_event_hook(app)
# ======================================================
versia = application.versia
if CMS.kontrol_ver(versia,"Выполнение2") == False:
    sys.exit()
# =========================================================
application.showMaximized()
sys.exit(app.exec())
#pyinstaller.exe --onefile --icon=Apathae.ico --noconsole Module.py
