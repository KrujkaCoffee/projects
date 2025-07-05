import colorsys
import copy
import collections

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWinExtras import QtWin
import os
import user_mange as userm
# import subprocess
import project_cust_38.Cust_Qt as CQT
import copy as CPY

CQT.convert_UI_into_PY_c()
from mydesign import Ui_MainWindow  # импорт нашего сгенерированного файла
# import config
import sys
import project_cust_38.Cust_Functions as F
import pprint
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Excel as CEX
import compare_files as compare
import table_marsh as MARSH
import outplan
import project_cust_38.Cust_b24 as B24
import project_cust_38.Cust_config as CFG

# import traceback


cfg = F.load_cfg(False)  # файл конфига, находится п папке конфиг


# F.test_path()


class mywindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(mywindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.versia = '1.6.0.7'
        self.NAME_MODULE_BASE = f"Создание"
        self.name_module = f'{self.NAME_MODULE_BASE}'
        self.USER_CONFIG: CFG.User_config = None
        self.place: CFG.Place = None

        CFG.Config.user_config.load_user_config(self)
        self.app_icons()
        CQT.load_icons(self, 24)
        CQT.connect_to_resize(self, CMS.tmp_dir())
        CMS.add_action_config_save_tbl_filtrs(self, self.ui)

        # ===========================================connects
        # ==================BTN
        self.ui.btn_login.clicked.connect(lambda _, x=self: userm.log_in(x))
        self.ui.btn_logout.clicked.connect(lambda _, x=self: userm.logout(x))
        self.ui.btn_create_nar.clicked.connect(self.create_naryd)
        self.ui.btn_select_all.clicked.connect(self.select_all_dse)
        self.ui.btn_invers.clicked.connect(self.select_invers_dse)
        self.ui.btn_unselect_all.clicked.connect(self.unselect_all_dse)
        self.ui.btn_komplect.clicked.connect(self.otmeka_komplekt)
        self.ui.btn_primen_imena.clicked.connect(self.primen_imena)
        self.ui.btn_poz_kol_add.clicked.connect(self.poz_kol_add)
        self.ui.btn_poz_kol_minus.clicked.connect(self.poz_kol_minus)
        self.ui.btn_edit_clear_fio.clicked.connect(self.edit_clear_fio)
        self.ui.btn_edit_clear_fio_and_jur.clicked.connect(self.edit_clear_fio_and_jur)
        self.ui.btn_edit_add_addition_fio.clicked.connect(self.edit_add_addition_fio)
        self.ui.btn_edit_delete_naruad.clicked.connect(self.edit_delete_naruad)
        self.ui.btn_edit_check_naruad.clicked.connect(self.edit_check_naruad)
        self.ui.btn_edit_check_vneplan.clicked.connect(self.edit_check_vneplan)
        self.ui.btn_anal_load_txt_erp.clicked.connect(lambda _, x=self: compare.load_txt(x))
        self.ui.btn_anal_load_txt_mes.clicked.connect(lambda _, x=self: compare.load_txt_mes(x))
        self.ui.btn_anal_start.clicked.connect(lambda _, x=self: compare.anal_start(x))

        self.ui.btn_edit_time_jur.clicked.connect(self.edit_time_jur_btn)
        self.ui.btn_set_edit_time_jur.clicked.connect(self.set_edit_time_jur)
        self.ui.btn_add_row_jur.clicked.connect(self.add_row_jur)
        self.ui.btn_del_row_jur.clicked.connect(self.del_row_jur)
        self.ui.btn_apply_deladd_row_jur.clicked.connect(self.apply_deladd_row_jur)
        self.ui.btn_prosm_edit_time_clear_fio.clicked.connect(lambda _, x='ФИО': self.btn_prosm_edit_time_clear_fio(x))
        self.ui.btn_prosm_edit_time_clear_fio2.clicked.connect(
            lambda _, x='ФИО2': self.btn_prosm_edit_time_clear_fio(x))
        self.ui.btn_reload_list_mk.clicked.connect(self.reload_list_mk)
        self.ui.btn_dse_sh_tree.clicked.connect(self.btn_dse_sh_tree)
        self.ui.btn_dse_sh_filtr.clicked.connect(self.btn_dse_sh_filtr)
        self.ui.btn_dse_sh_elems.clicked.connect(self.btn_dse_sh_elems)
        self.ui.btn_dse_info.clicked.connect(self.btn_dse_info)
        self.ui.btn_outplan.clicked.connect(lambda: outplan.start_form(self))
        self.ui.btn_outplan_ok.clicked.connect(lambda: outplan.outplan_ok(self))
        self.ui.btn_outplan_apply.clicked.connect(lambda: outplan.apply_row_technolog(self))
        self.ui.btn_open_vibor_assoc_prost.clicked.connect(lambda: self.open_vibor_assoc_proste_info('prost'))
        self.ui.btn_open_vibor_assoc_plan.clicked.connect(lambda: self.open_vibor_assoc_proste_info('plan'))
        self.ui.btn_vibor_assoc_prost.clicked.connect(self.vibor_assoc_prost_plan)
        self.ui.btn_outplan_confirm.clicked.connect(lambda: outplan.confirm_row(self))
        self.ui.btn_outplan_ansver.clicked.connect(lambda: outplan.ansver_row(self))
        self.ui.btn_save_custom_list_marsh.clicked.connect(lambda: MARSH.save_custom_list_marsh(self))
        self.ui.btn_add_rc_custom.clicked.connect(lambda: MARSH.add_rc_custom(self))
        self.ui.btn_del_rc_custom.clicked.connect(lambda: MARSH.del_rc_custom(self))
        self.ui.btn_order_recheck_otk.clicked.connect(self.order_recheck_otk)
        self.ui.btn_peresilniy.clicked.connect(self.create_peresilniy)
        # ==================lines
        self.ui.le_Nparol.setVisible(False)
        self.ui.le_Nparol2.setVisible(False)
        # ==================TABLES
        self.ui.tbl_projs_raspred.itemSelectionChanged.connect(self.select_tbl_projs_raspred)
        self.ui.tableWidget_vibor_mk.doubleClicked.connect(self.open_papka_chpy)
        self.ui.tableWidget_vibor_mk.clicked.connect(self.tbl_mk_click)
        self.ui.tableWidget_vibor_mk.setSelectionBehavior(0)
        self.ui.tbl_dse.clicked.connect(self.tbl_dse_click)
        self.ui.tbl_dse.itemSelectionChanged.connect(self.tbl_dse_select)
        self.ui.tbl_dse.currentItemChanged.connect(self.raschet_naruada_time_tmp)
        self.ui.tbl_prosmotr_nar.cellChanged[int, int].connect(self.edit_koeff_nar_tbl)
        self.ui.tbl_red_zhur.cellChanged[int, int].connect(self.edit_red_zhur_koef_sl)
        self.ui.tbl_red_zhur.clicked.connect(self.tbl_red_zhur_click)
        self.ui.tbl_dse.doubleClicked.connect(self.tbl_dse_dblclick)
        self.ui.tbl_vibor_nar_rasp.clicked.connect(self.tbl_nar_raspr_click)
        self.ui.tbl_vibor_rabotn_rasp.clicked.connect(self.tbl_rabotn_raspr_click)
        self.ui.tbl_komplektovka.itemSelectionChanged.connect(self.tbl_komplektovka_click)
        self.ui.tbl_komplektovka_view.clicked.connect(self.tbl_komplektovka_view_click)
        self.ui.tbl_prosmotr_nar.clicked.connect(self.tbl_prosmotr_nar_click)
        self.ui.tbl_brak.doubleClicked.connect(self.dblclick_brak)
        self.ui.tbl_prosmotr_nar.doubleClicked.connect(self.dblclick_tbl_prosmotr_nar)
        self.ui.tbl_prosmotr_nar_jurnal.clicked.connect(self.tbl_prosmotr_nar_jurnal_clk)
        self.ui.tbl_prosmotr_nar.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_filtr_prosmotr_nar.horizontalScrollBar().setValue)
        self.ui.tbl_komplektovka.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_filtr_komplektovka.horizontalScrollBar().setValue)
        self.ui.tableWidget_vibor_mk.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_filtr_mk.horizontalScrollBar().setValue)
        self.ui.tbl_dse.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_filtr_dse.horizontalScrollBar().setValue)
        self.ui.tbl_select_marsh.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_select_marsh_filtr.horizontalScrollBar().setValue)
        self.ui.tbl_vibor_nar_rasp.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_filtr_vibor_nar_rasp.horizontalScrollBar().setValue)
        self.ui.tbl_red_zhur.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_red_zhur_filtr.horizontalScrollBar().setValue)
        self.ui.tbl_select_marsh.clicked.connect(lambda: MARSH.tbl_select_marsh_clk(self))
        self.ui.tbl_select_marsh.doubleClicked.connect(lambda: MARSH.tbl_select_marsh_dblclk(self))
        self.ui.tbl_vibor_assoc_prost.clicked.connect(self.tbl_out_select_row)
        self.ui.tbl_outplan.clicked.connect(lambda: outplan.tbl_out_select_row(self))
        self.ui.tbl_outplan.itemSelectionChanged.connect(lambda: outplan.tbl_out_select_row(self))
        self.ui.tbl_outplan.cellChanged[int, int].connect(lambda: outplan.tbl_outplan_change_cell(self))
        self.ui.tbl_prosmotr_nar_jurnal.cellChanged[int, int].connect(
            lambda row, column: self.tbl_prosmotr_nar_jurnal_cellChanged(row, column))
        self.ui.tbl_brak.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_brak_filtr.horizontalScrollBar().setValue)
        # ==================TABS
        self.ui.tabWidget_2.currentChanged[int].connect(self.tab2_clcik)
        self.ui.tabWidget.currentChanged[int].connect(self.tab_clcik)
        self.ui.tab_prosm_nar.currentChanged[int].connect(self.tab_prosm_nar)
        self.ui.tabWidget.setTabEnabled(CQT.number_table_by_name_c(self.ui.tabWidget,'Контроль проектов'),False)
        # ===================CHECKBOX
        self.ui.checkBox_min_rezhjim.stateChanged[int].connect(self.min_rejim)
        self.ui.checkBox_vneplan_rab.stateChanged[int].connect(self.click_vneplan)
        self.ui.checkBox_full_dse.stateChanged.connect(self.check_box_load_full)
        self.ui.chk_progress.stateChanged.connect(self.zapoln_tabl_mk)
        # self.ui.chkb_autcourse.stateChanged.connect(self.click_chkb_autcourse)
        # ===================COMBOBOX
        self.ui.cmb_prof_rasp.activated[int].connect(self.select_prof_raspr)
        self.ui.cmb_etapi.activated[int].connect(self.select_etap_dse)
        self.ui.cmb_mat.activated[int].connect(self.select_etap_mat)
        self.ui.cmb_prof.activated[int].connect(self.select_prof)
        self.ui.cmb_current_rc.activated[int].connect(self.select_current_rc)
        self.ui.cmb_list_marsh.activated[int].connect(lambda: MARSH.select_dse_po_marsh(self))
        self.ui.cmb_vid_inf_marsh.activated[int].connect(lambda: MARSH.fill_tbl_select_marsh(self))
        self.ui.cmb_outplan.activated[int].connect(lambda: outplan.select_mk(self))
        self.ui.cmb_custom_marsh.activated[int].connect(lambda: MARSH.apply_custom_mar(self))
        # ===================RADIOBOX
        self.ui.radioButton_ispoln1.clicked.connect(self.clear_radio_isp)
        self.ui.radioButton_ispoln2.clicked.connect(self.clear_radio_isp)
        # ===================QSlider
        self.ui.hs_edit_time_jur.valueChanged.connect(self.edit_time_jur_time_change)
        # ==================== CALENDAR
        self.ui.cal_edit_time_jur.selectionChanged.connect(self.edit_date_jur_time_change)
        # ++++++++++++++++++++++++++++++++++++++++++++
        self.db_naryd = F.bdcfg('Naryad')
        self.db_act = F.scfg('BDact') + F.sep() + 'BDact.db'
        self.bd_users = F.bdcfg('BD_users')
        self.db_resxml = F.bdcfg('db_resxml')
        self.db_dse = F.bdcfg('BD_dse')
        self.db_nomen = F.bdcfg('nomenklatura_erp')
        self.db_files = F.bdcfg('BD_files')
        self.db_kplan = F.bdcfg('DB_kplan')
        # ==== GLOBALS
        self.MAX_TIME_NARUAD = 1920
        self.superuser = False
        self.SPIS_EMPLOEE = []
        self.glob_login = ''
        self.glob_ima = ''
        self.glob_nom_mk = 0
        self.glob_res = []
        self.glob_etap = set()
        self.set_rc_check_dse = set()
        self.metka_resize = ''
        self.CHECK_KOMPLEKT_TAB = False
        self.tab2_clcik_old_index = 0

        # self.ui.tabWidget.setTabEnabled(CQT.number_table_by_name_c(self.ui.tabWidget,'Комплектование'),self.CHECK_KOMPLEKT_TAB)
        self.TIME_DEAL = 5
        self.CORT_DOP_ZN_PRIM_REZKA_MK = ('вырезан', 'разложен', 'режется')
        self.SET_RUS_WORDS = F.load_file_pickle('summary.pickle')
        dict_tip = CSQ.custom_request_c(self.db_naryd, """SELECT * FROM тип_дорезок""", rez_dict=True)
        self.DICT_TIP_DOREZ = F.deploy_dict_c(dict_tip, 'Пномер')
        dict_tip_dorab = CSQ.custom_request_c(self.db_naryd, """SELECT * FROM тип_доработок""", rez_dict=True)
        self.DICT_TIP_DORAB = F.deploy_dict_c(dict_tip_dorab, 'Пномер')
        self.PRICES_BY_VID_RABOT = CMS.PRICES_BY_VID_RABOT(self.bd_users)
        self.LIST_DOLGN_ETAP = CSQ.custom_request_c(self.db_naryd, f"""SELECT * FROM dolgn_etap WHERE Производство == '{self.place.Имя}';""", rez_dict=True)
        self.DICT_DOLGN_ETAP = F.deploy_dict_c(
            self.LIST_DOLGN_ETAP, 'Должность')
        self.DICT_NOMEN = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_nomen, f"""SELECT * FROM nomen;""", rez_dict=True), 'Код')
        self.DICT_VIDS_NOMEN = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_nomen, f"""SELECT * FROM ВидыНоменклатуры""", rez_dict=True), 'name')
        self.DICT_PLACES = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_naryd, f"""SELECT * FROM places""", rez_dict=True), 'Имя')

        self.NAPR_DEYAT = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM napravl_deyat WHERE state_on_off = 1 and poki = {self.place.poki}""",
                                               rez_dict=True)
        self.DICT_NAPR_DEYAT = F.deploy_dict_c(self.NAPR_DEYAT, 'Пномер')
        self.DICT_NAPR_DEYAT_NAME = F.deploy_dict_c(self.NAPR_DEYAT, 'Имя')
        self.DICT_NAPR_DEYAT_PSDNAME = F.deploy_dict_c(self.NAPR_DEYAT, 'Псевдоним')
        # ======ACTIONS
        self.ui.action_noviy_user.triggered.connect(lambda _, x=self: userm.reg_new_user(x))
        self.ui.action_change_pass.triggered.connect(lambda _, x=self: userm.change_user_pass(x))
        self.ui.action_load_csv.triggered.connect(self.load_csv)
        # self.ui.action_peresilniy.triggered.connect(self.create_peresilniy)
        self.ui.action_open_zayavky.triggered.connect(self.open_zayavk)
        self.ui.action_reset_pass.triggered.connect(lambda _, x=self: userm.reset_user_pass(x))

        # =======loads

        self.DICT_EMPLOEE_FULL = dict()
        self.DICT_EMPLOEE_FULL_WITH_DEL = dict()
        CMS.dict_emploee_full(self.bd_users, self=self)


        userm.load_users(self, self.DICT_EMPLOEE_FULL, self.LIST_DOLGN_ETAP)


        self.ui.fr_vibor_assoc_prost.setHidden(True)
        self.ui.tbl_vibor_rabotn_rasp.setHidden(False)
        # ====== фильтр операций по должностям формирование списка
        self.SPIS_OPER = []
        if F.existence_file_c(F.scfg('Filtr_rab') + F.sep() + 'filtr_oper.txt'):
            spis_dost_oper_tmp = F.load_file(F.scfg('Filtr_rab') + F.sep() + 'filtr_oper.txt')
            for i in range(len(spis_dost_oper_tmp)):
                users = spis_dost_oper_tmp[i][1].split(';')
                users_fio = []
                for user in users:
                    users_fio.append(' '.join(user.split(',')[:3]))
                self.SPIS_OPER.append([spis_dost_oper_tmp[i][0], users_fio])
            del spis_dost_oper_tmp
        else:
            CQT.msgbox('Не найден список операций')
            # quit()
            # ================================
        DICT_OPER = CSQ.custom_request_c(self.db_naryd, f"""SELECT * FROM operacii WHERE poki == {self.place.poki}""",
                                         rez_dict=True)
        self.DICT_OPER = F.deploy_dict_c(DICT_OPER, 'kod')
        self.DICT_OPER_NAME = F.deploy_dict_c(DICT_OPER, 'name')
        # ===================== словарь этапов ===================
        self.DICT_ETAPI = dict()
        for item in DICT_OPER:
            self.DICT_ETAPI[item['name']] = item['dopust_prof'].split(',')
        self.DICT_ETAPS = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_naryd, f"""SELECT * FROM etaps""", rez_dict=True), 'name')
        # =========================================================
        spis_rc = CSQ.custom_request_c(self.bd_users, f'SELECT * FROM rab_c', rez_dict=True)
        # self.DICT_RC = dict()
        # for i in range(len(spis_rc)):
        #     if spis_rc[i]['Примечание'] == "":
        #         self.DICT_RC[spis_rc[i]['Код']] = spis_rc[i]['Имя']
        #     else:
        #         self.DICT_RC[spis_rc[i]['Код']] = f'{spis_rc[i]["Имя"]}({spis_rc[i]["Примечание"]})'
        CMS.dict_rc(self, self.bd_users)
        self.DICT_RC_FULL = F.deploy_dict_c(spis_rc, 'Код')

        dict_tip = CSQ.custom_request_c(self.db_naryd, """SELECT * FROM Тип_мк""", rez_dict=True)
        self.DICT_TIP_MK = F.deploy_dict_c(dict_tip, 'Имя')

        spis_status = CSQ.custom_request_c(self.db_naryd, f'SELECT DISTINCT jurnal.Статус FROM jurnal', hat_c=False)
        self.ui.cmb_edit_time_jur.addItems([i[0] for i in spis_status])

        MARSH.fill_filtr_rc(self)
        # ============DB
        # ====ВРЕМЕННО
        # self.ui.lbx_spis_sotr.setCurrentIndex(8)
        # self.ui.le_parol.setText('2022')
        # userm.log_in(self)
        # self.zaversh_naruad()
        self.ui.tab_4.setEnabled(False)
        self.ui.tab_11.setEnabled(True)
        self.DICT_KATEG_VNEPLAN = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_naryd, 'SELECT * FROM kategor_vnepl', rez_dict=True), 'value')
        self.DICT_PROFESSIONS = dict()
        CMS.dict_professions(self, self.bd_users)

        self.ui.cmb_kat_vnepl.addItems(list(self.DICT_KATEG_VNEPLAN.keys()))
        self.ui.cmb_prof_vnepl.addItem('')
        self.ui.cmb_prof_vnepl.addItems(list(self.DICT_PROFESSIONS_NAME.keys()))

        self.ui.cmb_rc_vnepl.addItem('')
        self.ui.cmb_rc_vnepl.addItems(list(self.DICT_RC.keys()))

        self.ui.tbl_prosmotr_nar_jurnal.setSelectionBehavior(1)
        self.ui.tbl_prosmotr_nar_jurnal.setSelectionMode(1)

        CQT.set_color_sort_cell_table_c(self.ui.tbl_prosmotr_nar_jurnal)
        # CQT.set_color_sort_cell_table_c(self.ui.tbl_dse)
        self.ui.fr_dse_filtrs.setHidden(True)

        # =====================временно
        # OFFself.write_date_podtv()
        # self.fix_error()
        # +++ 16.06.25

        self.ui.tbl_dse_check_counts.setHidden(True)
        self.ui.lbl_dse_check_counts.setHidden(True)
        # Создание наряда tooltips
        self.ui.btn_select_all.setToolTip('Поставить метку "Чек" для операций(По фильтру) \n<Shift + Click> Поставить метку "Чек" для всех операций(включая скрытые фильтром)')
        self.ui.btn_unselect_all.setToolTip('Снять метку "Чек" с операций(По фильтру) \n<Shift + Click> Снять метку "Чек" с всех операций(включая скрытые фильтром)')

        # Распределение наряда
        self.ui.chk_outsource_nar.stateChanged.connect(self.raspr_nar_on_chk_outsource)
        self.ui.chk_outsource_nar.setToolTip('При данной отметке наряд отмечается как исполняемый переработчиком')
        # --- 16.06.25
        self.ui.sp_select_opers.setSizes([30,600])


    # +++ 16.06.25
    @CQT.onerror
    def raspr_nar_on_chk_outsource(self, chk_state: int, *args):
        if not CMS.user_access(self.db_naryd, 'создание_создание_наряда_аутсорс', F.user_full_namre()):
            return
        tbl = self.ui.tbl_vibor_nar_rasp
        checkbox = self.ui.chk_outsource_nar

        nk_outsource = CQT.num_col_by_name_c(tbl, 'Аутсорсинг')
        current_row = tbl.currentRow()

        set_state = lambda state, chk: chk.blockSignals(True) or chk.setCheckState(state) or chk.blockSignals(False)
        current_row_data = CQT.get_dict_line_form_tbl(tbl, current_row)

        if current_row == -1 :
            return set_state(0, checkbox)
        pnom = current_row_data['Пномер']
        prev_state = 2 if tbl.item(current_row, nk_outsource).text() == '1' else 0
        new_state = chk_state == 2
        msg = "Вы уверены что хотите снять отметку аутсорсинга?"
        msg_for_b24 = f'{F.user_full_namre()} снял(а) пометку "Аутсорсинг" с наряда: {pnom!r}\n'
        if new_state:
            msg_for_b24 = f'{F.user_full_namre()} пометил(а) наряд: {pnom!r} как аутсорсинговый специалисту ПДО необходимо обработать наряд в программе "Аутсорсинг"\n'
            msg = "Вы уверены что хотите отметить данный наряд как аутсорснговый? При подтверждении Вы несете ответственность за данную отметку. Информация о распределении с данной отметкой будет направлена для последующей обработки"
        if not CQT.msgboxgYN(msg):
            return set_state(prev_state, checkbox)
        response = CSQ.custom_request_c(self.db_naryd,f'UPDATE naryad SET Аутсорсинг = {new_state} WHERE Пномер = {pnom}')
        if response:
            query = f"""SELECT пл_оуп.НомПл as "Номер КПЛ", знпр.№ERP, знпр.№проекта, mk.Пномер as "Номер МК" FROM naryad
                        JOIN mk ON mk.Пномер = naryad.Номер_мк
                        join пл_оуп ON пл_оуп.НомПл = mk.НомКплан
                        JOIN знпр ON пл_оуп.Пномер_ЗП = знпр.s_num
                        where naryad.Пномер = {pnom}
                    """
            credentials = CSQ.custom_request_c(self.db_naryd, query, rez_dict=True, one=True, attach_dbs=self.db_kplan)
            msg = msg_for_b24 + '\n'.join(f'{key}: {val!r}' for key, val in credentials.items())
            CMS.send_info_mk_b24_by_action(msg, 'Атсорсинг')
            tbl.item(current_row, nk_outsource).setText(str(int(new_state)))
            return self.tbl_nar_raspr_click()
        set_state(0, checkbox)
        # --- 16.06.25

    def fix_error(self):
        # list_nar = CSQ.custom_request_c(self.db_naryd,f"""SELECT Пномер FROM naryad WHERE datetime(Дата) >= datetime('2024-08-01 07:12:41')""",hat_c=False)
        list_nar = [[48176]]
        for num in list_nar:
            num = num[0]
            nar = CMS.Naryads(num, self.db_naryd)
            # if len(nar.params) == 1 and nar.params[0]['Опер_колво'] == 1:
            nar.recalc_tvrem()
            nar.recalc_astronom_time(self.DICT_OPER_NAME)
        return
        pass
        # list_jur = CSQ.custom_request_c(self.db_naryd, f"""SELECT Пномер, Дата FROM jurnal;""",rez_dict=True)
        for item in list_jur:
            date = item['Дата']
            if F.is_date(date, "%Y-%m-%d %H:%M:%S"):
                date_obj = F.strtodate(date, "%Y-%m-%d %H:%M:%S")
                if date_obj.hour < 10:
                    if date == F.datetostr(date_obj, "%Y-%m-%d %#H:%M:%S"):
                        str_Date = F.datetostr(date_obj, "%Y-%m-%d %H:%M:%S")
                        CSQ.custom_request_c(self.db_naryd,
                                             f"""UPDATE jurnal SET (Дата) = ("{str_Date}") WHERE Пномер = {item['Пномер']};""")
            else:
                print(item)

    def write_date_podtv(self):
        query = f"""SELECT jurnal.Дата, jurnal.ФИО, jurnal.Статус, 
        naryad.ФИО as Нар_ф, naryad.ФИО2  as Нар_ф2,
        naryad.Фвремя as Нар_фв, naryad.Фвремя2  as Нар_фв2,
        naryad.Пномер  from jurnal INNER JOIN naryad
         ON naryad.Пномер == jurnal.Номер_наряда WHERE Статус == 'Завершен'"""
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c=query, rez_dict=True)
        set_double = set()
        list_dates = []
        for nar in rez:
            if nar['Нар_ф'] != '' and nar['Нар_ф2'] != '' and nar['Нар_фв'] != '' and nar['Нар_фв2'] != '':
                set_double.add((nar['Пномер'], nar['Нар_ф'], nar['Нар_ф2']))
            if nar['Нар_ф'] != '' and nar['Нар_ф2'] == '':
                list_dates.append([nar['Дата'], nar['Пномер']])
            if nar['Нар_ф'] == '' and nar['Нар_ф2'] != '':
                list_dates.append([nar['Дата'], nar['Пномер']])
        list_double = list(set_double)

        for nar_nom, fio1, fio2 in list_double:
            data = ''
            flag = {fio1: 1, fio2: 1}
            for nar in rez:
                if flag[fio1] == 0 and flag[fio2] == 0:
                    break
                if nar['Пномер'] == nar_nom:
                    flag[nar['ФИО']] = 0
                    if data == '':
                        data = F.strtodate(nar['Дата'])
                    else:
                        if F.strtodate(nar['Дата']) > data:
                            data = F.strtodate(nar['Дата'])
            list_dates.append([F.datetostr(data), nar_nom])
        CSQ.custom_request_c(self.db_naryd, f"""UPDATE naryad SET Подтвержд_вып_дата = ? WHERE Пномер = ?""",
                             list_of_lists_c=list_dates)

    @CQT.onerror
    def zamena_filtr(self):
        tbl = self.ui.tbl_filtr_dse
        r = tbl.currentRow()
        c = tbl.currentColumn()
        if r == -1 or c == -1:
            return
        text = tbl.item(r, c).text()
        text = text.replace('/', '|')
        text = text.replace('?', '&')
        tbl.item(r, c).setText(text)
        CMS.apply_filtr_c(self, self.ui.tbl_filtr_dse, self.ui.tbl_dse)

    @CQT.onerror
    def key_handler(self, key_val: int, set_modifiers: set = ()):
        if self.ui.tbl_filtr_projs_raspred.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_projs_raspred, self.ui.tbl_projs_raspred)
        if self.ui.cmb_custom_marsh.hasFocus():
            if key_val == 16777223:
                MARSH.delete_selected_custom_mar(self)
        if self.ui.tbl_outplan.hasFocus():
            if key_val == 16777220:
                outplan.tbl_outplan_change_cell(self)
        if key_val == 67 and set_modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.copy_bufer_table(QtWidgets.QApplication.focusWidget())
        tabl_sp_mk = self.ui.tableWidget_vibor_mk
        if self.ui.tbl_outplan_naruad_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_outplan_naruad_filtr, self.ui.tbl_outplan_naruad)
        if self.ui.tbl_filtr_vibor_assoc_prost.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_vibor_assoc_prost, self.ui.tbl_vibor_assoc_prost)
        if self.ui.tbl_brak_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_brak_filtr, self.ui.tbl_brak)
        if self.ui.tbl_select_marsh_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_select_marsh_filtr, self.ui.tbl_select_marsh)
        if self.ui.tbl_red_zhur.hasFocus():
            if key_val == 16777220:
                if self.ui.tbl_red_zhur.currentColumn() == CQT.num_col_by_name_c(self.ui.tbl_red_zhur,
                                                                                 'Коэфф_сложности'):
                    self.edit_red_zhur_koef_sl(self.ui.tbl_red_zhur.currentRow(), self.ui.tbl_red_zhur.currentColumn())
                if self.ui.tbl_red_zhur.currentColumn() == CQT.num_col_by_name_c(self.ui.tbl_red_zhur, 'Твремя'):
                    self.edit_red_zhur_koef_sl(self.ui.tbl_red_zhur.currentRow(), self.ui.tbl_red_zhur.currentColumn())
                if self.ui.tbl_red_zhur.currentColumn() == CQT.num_col_by_name_c(self.ui.tbl_red_zhur, 'Примечание'):
                    self.edit_red_zhur_koef_sl(self.ui.tbl_red_zhur.currentRow(), self.ui.tbl_red_zhur.currentColumn())
            if key_val == 16777268:  # F5
                self.ui.tbl_red_zhur_filtr.setFocus()
                self.load_table_korr_naruad(False)
        if key_val == 80 and set_modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.refill_tbl_into_msgbox_get_table(self, QtWidgets.QApplication.focusWidget())
        if key_val == 67 and set_modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.copy_bufer_table(QtWidgets.QApplication.focusWidget())

        if key_val == QtCore.Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

        if key_val == 16777223 and set_modifiers == (QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                if QtWidgets.QApplication.focusWidget().rowCount() == 1:
                    for j in range(QtWidgets.QApplication.focusWidget().columnCount()):
                        QtWidgets.QApplication.focusWidget().item(0, j).setText('')
                    self.key_handler(16777220)

        if self.ui.tbl_prosmotr_nar.hasFocus():
            if key_val == 16777268:  # F5
                self.get_plan_proj()
                self.load_table_prosm_nar_by_year()
            if key_val == 16777220:
                tbl = self.ui.tbl_prosmotr_nar
                row = tbl.currentRow()
                column = tbl.currentColumn()
                self.edit_koeff_nar_tbl(row, column)
        if self.ui.tbl_outplan_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_outplan_filtr, self.ui.tbl_outplan)
        if self.ui.tbl_anal_rez_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_anal_rez_filtr, self.ui.tbl_anal_rez)
        if self.ui.tbl_anal_mk_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_anal_mk_filtr, self.ui.tbl_anal_mk)
        if self.ui.tbl_prosm_nar_oper_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_prosm_nar_oper_filtr, self.ui.tbl_prosm_nar_oper)
        if self.ui.tbl_prosmotr_nar_jurnal_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_prosmotr_nar_jurnal_filtr, self.ui.tbl_prosmotr_nar_jurnal)
        if self.ui.tbl_prosm_nar_zadan_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_prosm_nar_zadan_filtr, self.ui.tbl_prosm_nar_zadan)
        if self.ui.tbl_dse.hasFocus():
            if key_val == 16777220:
                if self.ui.tbl_dse.currentColumn() == CQT.num_col_by_name_c(self.ui.tbl_dse, 'В работу,шт.'):
                    self.raschet_naruada_time_tmp()
            if key_val == 32:
                self.select_dse(0)
        if self.ui.tbl_red_zhur_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_red_zhur_filtr, self.ui.tbl_red_zhur)
        if self.ui.tbl_filtr_prosmotr_nar.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_prosmotr_nar, self.ui.tbl_prosmotr_nar)
        if self.ui.tbl_filtr_vibor_nar_rasp.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_vibor_nar_rasp, self.ui.tbl_vibor_nar_rasp)
        if self.ui.tbl_filtr_dse.hasFocus():
            if key_val == 16777220:
                if set_modifiers == QtCore.Qt.AltModifier:
                    self.zamena_filtr()
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_dse, self.ui.tbl_dse)
                MARSH.fill_tbl_select_marsh(self)
        if self.ui.le_parol.hasFocus():
            if key_val == 16777220:
                userm.log_in(self)
        if self.ui.tbl_filtr_komplektovka.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_komplektovka, self.ui.tbl_komplektovka)
        if self.ui.tbl_filtr_mk.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_mk, tabl_sp_mk)
                nk_mass = CQT.num_col_by_name_c(self.ui.tableWidget_vibor_mk, 'Вес')
                summ = 0
                for i in range(self.ui.tableWidget_vibor_mk.rowCount()):
                    if not self.ui.tableWidget_vibor_mk.isRowHidden(i):
                        if F.is_numeric(self.ui.tableWidget_vibor_mk.item(i, nk_mass).text()):
                            summ += F.valm(self.ui.tableWidget_vibor_mk.item(i, nk_mass).text())
                self.ui.lbl_for_summ.setText(f' Сумма {round(summ)} кг.')
        if tabl_sp_mk.hasFocus():
            if key_val == 16777268:  # F5
                self.reload_list_mk()
            if key_val == 16777220:
                if tabl_sp_mk.currentColumn() == CQT.num_col_by_name_c(tabl_sp_mk, "Статус_ЧПУ"):
                    self.open_papka_chpy()
                if tabl_sp_mk.currentColumn() == CQT.num_col_by_name_c(tabl_sp_mk, "Дата_раскладки"):
                    row, col = CQT.number_selection_cell_by_row_and_column_c(tabl_sp_mk)
                    if tabl_sp_mk.item(row, CQT.num_col_by_name_c(tabl_sp_mk, "Статус_ЧПУ")).text() == "":
                        CQT.msgbox(f'поле Статус ЧПУ не может быть пусто')
                        return
                    if F.is_date(tabl_sp_mk.item(row, col).text(), "%d.%m.%Y") or tabl_sp_mk.item(row,
                                                                                                  col).text() == '':
                        query = f'''
                                                    UPDATE zagot SET Дата_раскладки = "{tabl_sp_mk.item(row, col).text()}" 
                                                    WHERE Ном_МК == {int(tabl_sp_mk.item(row, CQT.num_col_by_name_c(tabl_sp_mk, "Пномер")).text())};
                                                    '''
                        CSQ.custom_request_c(self.db_naryd, query)
                    else:
                        tabl_sp_mk.item(row, col).setText('')
                        CQT.msgbox(f'ошибка! формат даты дд.мм.гггг')
                if tabl_sp_mk.currentColumn() == CQT.num_col_by_name_c(tabl_sp_mk, "Прим_резка"):
                    row, col = CQT.number_selection_cell_by_row_and_column_c(tabl_sp_mk)
                    if tabl_sp_mk.item(row, col).text() in self.CORT_DOP_ZN_PRIM_REZKA_MK:
                        query = f'''
                                UPDATE zagot SET Прим_резка = "{tabl_sp_mk.item(row, col).text()}" 
                                WHERE Ном_МК == {int(tabl_sp_mk.item(row, CQT.num_col_by_name_c(tabl_sp_mk, "Пномер")).text())};
                                '''
                        CSQ.custom_request_c(self.db_naryd, query)
                    else:
                        tabl_sp_mk.item(row, col).setText('')
                        CQT.msgbox(f'ошибка! допустимые значения: {self.CORT_DOP_ZN_PRIM_REZKA_MK}')

                if tabl_sp_mk.currentColumn() == CQT.num_col_by_name_c(tabl_sp_mk, "Дата_компл_загот"):
                    row, col = CQT.number_selection_cell_by_row_and_column_c(tabl_sp_mk)
                    now_str = F.now("%Y-%m-%d %H:%M:%S")
                    query = f'''
                            UPDATE zagot SET Дата_компл_загот = "{now_str}" 
                            WHERE Ном_МК == {int(tabl_sp_mk.item(row, CQT.num_col_by_name_c(tabl_sp_mk, "Пномер")).text())};
                            '''
                    tabl_sp_mk.item(row, col).setText(now_str)
                    CSQ.custom_request_c(self.db_naryd, query)

    @CQT.onerror
    def keyReleaseEvent(self, e):
        self.key_handler(e.key(), e.modifiers())

    def reload_list_mk(self):
        if self.glob_login != '':
            self.zapoln_tabl_mk()

    @CQT.onerror
    def app_icons(self):
        self.ui.btn_reload_list_mk.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)))
        self.ui.checkBox_min_rezhjim.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogHelpButton)))
        self.ui.checkBox_full_dse.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton)))
        self.ui.btn_login.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton)))
        self.ui.btn_login.setIconSize(QtCore.QSize(16, 16))
        self.ui.btn_logout.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton)))
        self.ui.btn_logout.setIconSize(QtCore.QSize(16, 16))
        self.ui.btn_select_all.setIcon(QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_ToolBarVerticalExtensionButton)))
        self.ui.btn_select_all.setIconSize(QtCore.QSize(16, 16))
        self.ui.btn_invers.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_TitleBarShadeButton)))
        self.ui.btn_invers.setIconSize(QtCore.QSize(16, 16))
        self.ui.btn_create_nar.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)))
        self.ui.btn_create_nar.setIconSize(QtCore.QSize(16, 16))
        self.ui.btn_primen_imena.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)))
        self.ui.btn_primen_imena.setIconSize(QtCore.QSize(64, 64))
        self.ui.btn_komplect.setIcon(
            QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)))
        self.ui.btn_komplect.setIconSize(QtCore.QSize(16, 16))
        self.ui.tabWidget_2.setTabIcon(0, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)))
        self.ui.tabWidget_2.setTabIcon(1, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileDialogListView)))
        self.ui.tabWidget_2.setTabIcon(2, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_TrashIcon)))
        self.ui.tabWidget_2.setTabIcon(3, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)))
        self.ui.tabWidget.setTabIcon(0, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)))
        self.ui.tabWidget.setTabIcon(1, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DialogOkButton)))
        self.ui.tabWidget.setTabIcon(2, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileDialogInfoView)))
        self.ui.tabWidget.setTabIcon(4, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_DriveHDIcon)))
        self.ui.tabWidget.setTabIcon(5, QtGui.QIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView)))

    def get_plan_proj(self):

        self.DICT_ACCESS_USER_DELTA = F.deploy_dict_c(
            CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM list_py_users_delta_month WHERE poki = {self.place.poki}""", rez_dict=True), 'user')

        dict_poz = F.deploy_dict_c(CSQ.custom_request_c(self.db_kplan, f"""SELECT пл_оуп.НомПл, 
        пл_оуп.№ERP FROM пл_оуп INNER JOIN plan ON plan.Пномер = пл_оуп.НомПл WHERE plan.poki = {self.place.poki} and пл_оуп.№ERP != "-";""", rez_dict=True), 'НомПл')
        list_plans = CSQ.custom_request_c(self.db_kplan, f"""SELECT Дата, file_poz_plan FROM 
         mnts_plan WHERE poki = {self.place.poki} and file_poz_plan is NOT NULL""", rez_dict=True)

        self.DICT_ACCESS_PROJ_MONTH = dict()
        for item in list_plans:
            data_pl = F.from_binary_pickle(item['file_poz_plan'])
            if item['Дата'] not in self.DICT_ACCESS_PROJ_MONTH:
                self.DICT_ACCESS_PROJ_MONTH[item['Дата']] = set()
            for poz in data_pl.keys():
                if poz in dict_poz:
                    self.DICT_ACCESS_PROJ_MONTH[item['Дата']].add(dict_poz[poz])

        dict_access_proj_month = CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM list_py_month""",
                                                      rez_dict=True)
        for item in dict_access_proj_month:
            month = '20' + item['Месяц']
            if month not in self.DICT_ACCESS_PROJ_MONTH:
                self.DICT_ACCESS_PROJ_MONTH[month] = set()
            self.DICT_ACCESS_PROJ_MONTH[month].add(item['ПУ'])

    @CQT.onerror
    @CQT.progress_decorator
    def tab_clcik(self, nom, hook_prog_bar, *args):
        hook_prog_bar.set(10)
        hook_prog_bar.text('Обработка')
        if CMS.kontrol_ver(self.versia, self.NAME_MODULE_BASE) == False:
            sys.exit()
        if not CMS.check_actual_parol(self.glob_ima):
            CQT.msgbox(f'Нужно обновить пароль через меню "Параметры"')
            userm.logout(self)
        name = self.ui.tabWidget.tabText(nom)
        if name == 'Комплектование':
            self.load_table_komplekt()
        if name == 'Оповещение':
            pass
        if name == 'Просмотр нарядов':
            self.load_table_prosm_nar()
        if name == 'Распределение нарядов':
            self.get_plan_proj()
            rez = True
            if self.place.ИспПроверкуВнесенияТрудозатрат:
                rez = self.check_vnesenie_trudozatrat()
            if rez:
                self.load_table_projects_for_raspred_nar()

                #self.load_table_raspred_nar()
                self.ui.fr_vibor_assoc_prost.setVisible(False)
            else:
                self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget, 'Просмотр нарядов'))
        if name == 'Корректировка':
            self.load_table_korr_naruad()
        if name == 'Контроль проектов':#DEL!
            compare.load_py(self)
        if name == 'Внеплан':
            if self.glob_ima == "":
                return
            self.outplan_edit_acces = False
            if CMS.user_access(self.db_naryd, 'создание_внепалн_ответ', self.glob_ima, False):
                self.outplan_edit_acces = True
            outplan.load_form(self)

    @CQT.onerror
    def tab2_clcik(self, nom, *args):
        name = self.ui.tabWidget_2.tabText(nom)
        if name == 'МК':
            pass
        if name == 'ДСЕ':
            # self.load_brak()
            # if self.ui.tbl_brak.rowCount() > 0:
            #    self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Брак'))
            # else:
            #    self.load_mk()
            if self.ui.tabWidget_2.tabText(self.tab2_clcik_old_index) == 'МК':
                self.load_mk()
                self.raschet_naruada_time_tmp()


        if name == 'Наряд':
            self.ui.cmb_kat_vnepl.setCurrentText('')
            self.ui.cmb_prof_vnepl.setCurrentText('')
            self.un_block_nar_tbl()
            self.raschet_naruada_time_tmp()
            check_tables = (
                self.ui.tbl_dse_check_time,
                self.ui.tbl_dse_check_podr,
                self.ui.tbl_dse_check_prof
            )
            for tbl in check_tables:
                validate = tbl.property('validate')
                if not validate:
                    self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, 'ДСЕ'))
                    return CQT.blink_obj_c(self, 2, tbl,
                                    msg='Для продолжения необходимо исправить ошибки')
            self.raschet_naruada()
        if name == 'Брак':
            self.load_brak()

        self.tab2_clcik_old_index = nom

    def tab_prosm_nar(self, nom, *args):
        name = self.ui.tab_prosm_nar.tabText(nom)
        if name == 'Материалы':
            self.load_mats_prosmotr(self)

    @CQT.onerror
    def order_recheck_otk(self, *args):
        tbl = self.ui.tbl_brak
        row = CQT.get_dict_line_form_tbl(tbl)
        if len(row) == 0:
            CQT.msgbox(f'Не выбрана строка')
            return
        if row['неисправимый'] == '1':
            CQT.msgbox(f'Брак НЕИСПРАВИМЫЙ')
            return
        if self.ui.le_order_recheck_otk.text().strip() == "" or len(self.ui.le_order_recheck_otk.text().strip()) < 4:
            CQT.msgbox(f'Не указано примечание')
            return
        # obj = B24.B24('chat17679')
        nar = CMS.Naryads(int(row["Наряд"]), self.db_naryd, self.DICT_DOLGN_ETAP, self.bd_users,
                          self.DICT_EMPLOEE_FULL_WITH_DEL)
        nar.get_mk(self.db_resxml)
        count_pr = int(row["Кол-во повт. приемок"]) + 1
        msg_rows = (f'Мастер {F.user_full_namre()}, вызывает на повторную приемку:\n'
                    f'наряд №{row["Наряд"]}\n'
                    f'    (Номер_проекта:{nar.mk.Номер_проекта} {nar.mk.Номер_заказа} {nar.mk.Номенклатура})\n'
                    f'Описание исправления: {self.ui.le_order_recheck_otk.text()}\n'
                    f'Описание брака:\n    Проверил:{row["Контролёр"]}\n    Примечание:{row["Примечание"]}\n    Категория:{row["group_3"]}\n    Повторная сдача№ {count_pr}')
        old_prim = copy.deepcopy(nar.Примечание)
        old_count_order = copy.deepcopy(nar.Кол_повт_приемок)
        nar.Примечание = f'(Повт.Приёмка {F.now("%Y-%m-%d %H:%M")})' + nar.Примечание
        nar.Кол_повт_приемок += 1
        try:
            CMS.send_info_mk_b24_by_action(msg_rows, 'Только брак')
            # obj.msg(msg_rows)
            nar._save_nar()
            CQT.msgbox(f'Успешно')
            self.ui.le_order_recheck_otk.setText('')
            return
        except:
            nar.Примечание = old_prim
            nar.Кол_повт_приемок = old_count_order
            nar._save_nar()
            CQT.msgbox(f'Ошибка')
            return

    def check_vnesenie_trudozatrat(self):
        config = CFG.Config.project
        if not int(config.check_vnesenie_trudozatrat):
            return True
        if self.superuser:
            return True
        now = F.now('')
        dict_check_days = dict()
        set_month = set()
        RAB_DAY_LIMIT = 3
        DAYS_CHECK = 5
        counter = 0
        for i in range(-1, -20, -1):
            if counter - RAB_DAY_LIMIT >= DAYS_CHECK:
                break
            day = F.datetostr(F.date_add_days(now, i, '', ''), 'd_%Y_%m_%d')
            month = F.datetostr(F.date_add_days(now, i, '', ''), 'jurnaltdz_%Y_%m_01')
            vihodn_val = CSQ.custom_request_c(self.bd_users, f"""SELECT {day} FROM {month} WHERE Пномер = 1""")
            if vihodn_val == False:
                CQT.msgbox(f'ОШибка загрузки календаря')
                return False
            if vihodn_val[-1][0] == 0:
                counter += 1
            if counter > RAB_DAY_LIMIT:
                dict_check_days[day] = month
                set_month.add(month)
        list_month = sorted(list(set_month))
        rez = []
        for month in list_month:
            tbl = CSQ.custom_request_c(self.bd_users, f"""SELECT * FROM {month}""")
            for i in range(3, len(tbl)):
                if self.glob_ima in tbl[i][2]:
                    for day in dict_check_days.keys():
                        if dict_check_days[day] == month:
                            for j in range(3, len(tbl[0])):
                                if day == tbl[0][j]:
                                    if tbl[i][j] == 0:
                                        day_name = F.datetostr(F.strtodate(day, 'd_%Y_%m_%d'), '%d.%m.%Y')
                                        rez.append(
                                            f'{day_name} для РЦ{tbl[i][1]} не выгружено. Ответственные: {tbl[i][2]}')
                                    break
        if rez == []:
            return True
        CQT.msgbox("\n".join(rez))
        return False

    def check_dost_proj_moth(self, py, fio):
        if not self.place.ИспользоватьФильтрМКПоплану:
            return True
        if fio not in self.DICT_ACCESS_USER_DELTA:
            return True
        delta = self.DICT_ACCESS_USER_DELTA[fio]['delta']
        for month, set_py in self.DICT_ACCESS_PROJ_MONTH.items():
            if py in set_py:
                if F.now('') > F.date_add_days(month, delta, '%Y-%m-%d', ''):
                    return True
        return False

    @CQT.onerror
    def open_zayavk(self, *args):
        if self.glob_login == "":
            CQT.msgbox('Необходимо войти')
            return
        nom_pr = ''
        nom_pu = ''

        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Создание наряда'):
            if self.ui.tableWidget_vibor_mk.currentRow() != -1:
                nom_pu = self.ui.tableWidget_vibor_mk.item(self.ui.tableWidget_vibor_mk.currentRow(),
                                                           CQT.num_col_by_name_c(self.ui.tableWidget_vibor_mk,
                                                                                 'Номер_заказа')).text()
                nom_pr = self.ui.tableWidget_vibor_mk.item(self.ui.tableWidget_vibor_mk.currentRow(),
                                                           CQT.num_col_by_name_c(self.ui.tableWidget_vibor_mk,
                                                                                 'Номер_проекта')).text()
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Распределение нарядов'):
            if self.ui.tbl_vibor_nar_rasp.currentRow() != -1:
                nom_pu = self.ui.tbl_vibor_nar_rasp.item(self.ui.tbl_vibor_nar_rasp.currentRow(),
                                                         CQT.num_col_by_name_c(self.ui.tbl_vibor_nar_rasp,
                                                                               'Номер_заказа')).text()
                nom_pr = self.ui.tbl_vibor_nar_rasp.item(self.ui.tbl_vibor_nar_rasp.currentRow(),
                                                         CQT.num_col_by_name_c(self.ui.tbl_vibor_nar_rasp,
                                                                               'Номер_проекта')).text()
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Просмотр нарядов'):
            if self.ui.tbl_prosmotr_nar.currentRow() != -1:
                nom_pu = self.ui.tbl_prosmotr_nar.item(self.ui.tbl_prosmotr_nar.currentRow(),
                                                       CQT.num_col_by_name_c(self.ui.tbl_prosmotr_nar,
                                                                             'Номер_заказа')).text()
                nom_pr = self.ui.tbl_prosmotr_nar.item(self.ui.tbl_prosmotr_nar.currentRow(),
                                                       CQT.num_col_by_name_c(self.ui.tbl_prosmotr_nar,
                                                                             'Номер_проекта')).text()
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Комплектование'):
            if self.ui.tbl_komplektovka.currentRow() != -1:
                nom_pu = self.ui.tbl_komplektovka.item(self.ui.tbl_komplektovka.currentRow(),
                                                       CQT.num_col_by_name_c(self.ui.tbl_komplektovka,
                                                                             'Номер_заказа')).text()
                nom_pr = self.ui.tbl_komplektovka.item(self.ui.tbl_komplektovka.currentRow(),
                                                       CQT.num_col_by_name_c(self.ui.tbl_komplektovka,
                                                                             'Номер_проекта')).text()
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Корректировка'):
            if self.ui.tbl_red_zhur.currentRow() != -1:
                nom_pu = self.ui.tbl_red_zhur.item(self.ui.tbl_red_zhur.currentRow(),
                                                   CQT.num_col_by_name_c(self.ui.tbl_red_zhur, 'Номер_заказа')).text()
                nom_pr = self.ui.tbl_red_zhur.item(self.ui.tbl_red_zhur.currentRow(),
                                                   CQT.num_col_by_name_c(self.ui.tbl_red_zhur,
                                                                         'Номер_проекта')).text()
        if nom_pu == '':
            return
        putf = CMS.path_to_proj_NPPY_c(nom_pr, nom_pu)
        modifiers = CQT.get_key_modifiers(self)
        if modifiers == ['shift']:
            F.open_dir_c(putf)
            return
        list_files = F.list_of_files_c(putf)
        if list_files == []:
            return
        for file in list_files[0][2]:
            if 'Заказ на производство №' in file and '.pdf' in file:
                F.run_file_c(list_files[0][0] + file)
                return
        F.open_dir_c(list_files[0][0])

    @CQT.onerror
    def poz_kol_add(self, *args):
        if self.glob_login == "":
            CQT.msgbox('Необходимо войти')
            return
        try:
            custom_request_c = f'''SELECT Количество FROM mk WHERE Пномер == {self.glob_nom_mk}'''
            rez = CSQ.custom_request_c(self.db_naryd, custom_request_c)
            kol_izd = int(rez[-1][0])
        except:
            CQT.msgbox('Ошибка загрузки количества')
            return
        tbl = self.ui.tbl_dse
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        nk_kol = CQT.num_col_by_name_c(tbl, 'Количество,шт.')
        nk_vrab = CQT.num_col_by_name_c(tbl, 'В работу,шт.')

        for i in range(tbl.rowCount()):
            if tbl.cellWidget(i, nk_check).isChecked():
                kol = F.valm(tbl.item(i, nk_kol).text())
                kol_ed = kol / kol_izd
                vrab = int(tbl.item(i, nk_vrab).text())
                if vrab + kol_ed > kol:
                    tbl.item(i, nk_vrab).setText(str(kol))
                else:
                    tbl.item(i, nk_vrab).setText(str(int(vrab + kol_ed)))

    @CQT.onerror
    def poz_kol_minus(self, *args):
        if self.glob_login == "":
            CQT.msgbox('Необходимо войти')
            return
        try:
            custom_request_c = f'''SELECT Количество FROM mk WHERE Пномер == {self.glob_nom_mk}'''
            rez = CSQ.custom_request_c(self.db_naryd, custom_request_c)
            kol_izd = int(rez[-1][0])
        except:
            CQT.msgbox('Ошибка загрузки количества')
            return
        tbl = self.ui.tbl_dse
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        nk_kol = CQT.num_col_by_name_c(tbl, 'Количество,шт.')
        nk_vrab = CQT.num_col_by_name_c(tbl, 'В работу,шт.')

        for i in range(tbl.rowCount()):
            if tbl.cellWidget(i, nk_check).isChecked():
                kol = F.valm(tbl.item(i, nk_kol).text())
                kol_ed = kol / kol_izd
                vrab = int(tbl.item(i, nk_vrab).text())
                if vrab - kol_ed < 0:
                    tbl.item(i, nk_vrab).setText("0")
                else:
                    tbl.item(i, nk_vrab).setText(str(int(vrab - kol_ed)))

    @CQT.onerror
    def create_peresilniy(self, *args):
        if self.glob_login == "":
            CQT.msgbox('Необходимо войти')
            return
        if self.ui.tabWidget.currentIndex() != CQT.number_table_by_name_c(self.ui.tabWidget, 'Комплектование'):
            CQT.msgbox(f'Необходимо выбрать наряд на вкладке Комплектование')
            return
            # self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget, 'Комплектование'))
        tbl = self.ui.tbl_komplektovka
        tblv = self.ui.tbl_komplektovka_view
        CMS.load_peresilniy(self, tbl, tblv)

    @CQT.onerror
    def load_csv(self, *args):
        # list_nar = CSQ.custom_request_c(self.db_naryd,f"""
        #    SELECT * FROM naryad WHERE naryad.Пномер IN (SELECT naryad.Пномер FROM
        #     naryad INNER JOIN mk ON mk.Пномер = naryad.Номер_мк  WHERE mk.Статус != "Закрыта")""",rez_dict=True)
        # summ_change = 0
        # count = 0
        # for item in list_nar:
        #    nar = CMS.Naryads(item,self.db_naryd)
        #    nar.recalc_astronom_time(self.DICT_OPER_NAME)
        #    if nar.count_users() == 2:
        #        change = 100 * (nar.Норма_времени / nar.Твремя/2-1)
        #    else:
        #        change = 100 * ( nar.Норма_времени / nar.Твремя-1)
        #        print(change)
        #    summ_change += change
        #    count += 1
        #    #F.sleep(0.05)
        #    #print(f'{count} / {len(list_nar)}')
        # print(round(summ_change/count,2))
        # return
        if self.glob_login == "":
            CQT.msgbox('Необходимо войти')
            return
        if not CMS.load_csv(self, self.db_nomen, self.db_kplan):
            return
        if not CFG.Config.user_config.is_developer:
            self.zapoln_tabl_mk()

    @CQT.onerror
    def load_mats_prosmotr(self, *args):
        tblp = self.ui.tbl_prosmotr_nar
        row = CQT.get_dict_line_form_tbl(tblp)
        CQT.clear_tbl(self.ui.tbl_prosm_nar_mater)
        res = CMS.load_res(int(row['Номер_мк']), db_resxml=self.db_resxml)

        list_dse_id = row['ДСЕ_ID'].split('|')
        list_oper = row['Операции'].split('|')
        list_oper_kol = row['Опер_колво'].split('|')
        dict_mats = dict()
        for i in range(len(list_dse_id)):
            dse = list_dse_id[i]
            oper_nom = list_oper[i].split('$')[0]
            oper_kol = list_oper_kol[i]
            for dse_res in res:
                if dse_res['Номерпп'] == int(dse):
                    for oper in dse_res['Операции']:
                        if oper['Опер_номер'] == oper_nom:
                            for mat in oper['Материалы']:
                                norma_nar = mat['Мат_норма_ед'] * F.valm(oper_kol)
                                if mat['Мат_код'] not in dict_mats:
                                    dict_mats[mat['Мат_код']] = {'Мат_наименование': mat['Мат_наименование'],
                                                                 'Мат_норма': 0,
                                                                 'Мат_ед_изм': mat['Мат_ед_изм'],
                                                                 'Материалы_Статья_калькуляции': mat[
                                                                     'Материалы_Статья_калькуляции'],
                                                                 'Способы_получения_материала': mat[
                                                                     'Способы_получения_материала']
                                                                 }
                                dict_mats[mat['Мат_код']]['Мат_норма'] += norma_nar
                                dict_mats[mat['Мат_код']]['Мат_норма'] = round(dict_mats[mat['Мат_код']]['Мат_норма'],
                                                                               6)

        list_mats = F.dict_of_dicts_to_list_of_lists(dict_mats, 'Код')
        CQT.fill_wtabl(list_mats, self.ui.tbl_prosm_nar_mater,
                       list_column_widths=CMS.load_column_widths(self, self.ui.tbl_prosm_nar_mater))

    @CQT.onerror
    def tbl_prosmotr_nar_jurnal_cellChanged(self, row, column, *args):
        row = CQT.get_dict_line_form_tbl(self.ui.tbl_prosmotr_nar_jurnal, row)
        CSQ.custom_request_c(self.db_naryd,
                             f"""UPDATE jurnal SET (Примечание) = (?) WHERE Пномер = {int(row['Пномер'])};""",
                             list_of_lists_c=[[row['Примечание']]])

    def btns_edit_jur_in_prosmtr_nar_enabled(self, enable=True):
        self.ui.cmb_edit_time_jur.setEnabled(enable)
        self.ui.hs_edit_time_jur.setEnabled(enable)
        self.ui.dt_edit_time_jur.setEnabled(enable)
        self.ui.btn_edit_time_jur.setEnabled(enable)
        self.ui.btn_add_row_jur.setEnabled(enable)
        self.ui.btn_set_edit_time_jur.setEnabled(enable)
        self.ui.btn_del_row_jur.setEnabled(enable)
        self.ui.btn_apply_deladd_row_jur.setEnabled(enable)
        self.ui.btn_prosm_edit_time_clear_fio.setEnabled(enable)
        self.ui.btn_prosm_edit_time_clear_fio2.setEnabled(enable)

    @CQT.onerror
    def tbl_prosmotr_nar_click(self, *args):
        tblp = self.ui.tbl_prosmotr_nar
        tblj = self.ui.tbl_prosmotr_nar_jurnal
        nk_nom_nar = CQT.num_col_by_name_c(tblp, 'Пномер')
        nom_nar = int(tblp.item(tblp.currentRow(), nk_nom_nar).text())
        custom_request_c = f'''SELECT  Пномер, Номер_наряда, Дата, ФИО, Статус, Подытог, Примечание FROM jurnal WHERE Номер_наряда == {nom_nar}'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c)
        zad = CSQ.custom_request_c(self.db_naryd, f"""SELECT mk.Дата_завершения,
         naryad.Пномер, naryad.Задание FROM naryad Inner join mk ON mk.Пномер = naryad.Номер_мк WHERE naryad.Пномер == {nom_nar}""",
                                   rez_dict=True)
        CQT.fill_wtabl_old_c(self, rez, tblj, isp_hat_c=True, separ='',
                             set_editeble_col_nomera={CQT.num_col_by_name_c(tblj, 'Примечание')})
        CMS.load_column_widths(self, tblj)
        CMS.fill_filtr_c(self, self.ui.tbl_prosmotr_nar_jurnal_filtr, self.ui.tbl_prosmotr_nar_jurnal)
        CMS.apply_filtr_c(self, self.ui.tbl_prosmotr_nar_jurnal_filtr, self.ui.tbl_prosmotr_nar_jurnal)

        nk_zad = CQT.num_col_by_name_c(tblp, 'Задание')
        nk_oper = CQT.num_col_by_name_c(tblp, 'Операции')
        nk_vrem = CQT.num_col_by_name_c(tblp, 'Опер_время')
        nk_kol = CQT.num_col_by_name_c(tblp, 'Опер_колво')

        nar = CMS.Naryads(nom_nar, self.db_naryd, self.DICT_DOLGN_ETAP, self.bd_users,
                          self.DICT_EMPLOEE_FULL_WITH_DEL)

        if nar.is_month_closing_block() or zad[0]['Дата_завершения'] != '':
            self.btns_edit_jur_in_prosmtr_nar_enabled(False)
        else:
            self.btns_edit_jur_in_prosmtr_nar_enabled(True)

        zad = zad[0]['Задание'].split('LF')
        zad = [[_] for _ in zad]
        zad.insert(0, ['Задание'])
        oper = tblp.item(tblp.currentRow(), nk_oper).text().split('|')
        vrem = tblp.item(tblp.currentRow(), nk_vrem).text().split('|')
        kol = tblp.item(tblp.currentRow(), nk_kol).text().split('|')
        spis_oper = [['Операция', 'шт.', 'мин.']]
        for i in range(len(oper)):
            spis_oper.append([oper[i].replace('$', ' '), kol[i], vrem[i]])
        CQT.fill_wtabl_old_c(self, zad, self.ui.tbl_prosm_nar_zadan, separ='', isp_hat_c=True)
        CMS.load_column_widths(self, self.ui.tbl_prosm_nar_zadan)
        CMS.fill_filtr_c(self, self.ui.tbl_prosm_nar_zadan_filtr, self.ui.tbl_prosm_nar_zadan)

        CQT.fill_wtabl_old_c(self, spis_oper, self.ui.tbl_prosm_nar_oper, separ='', isp_hat_c=True)
        CMS.load_column_widths(self, self.ui.tbl_prosm_nar_oper)
        CMS.fill_filtr_c(self, self.ui.tbl_prosm_nar_oper_filtr, self.ui.tbl_prosm_nar_oper)

        self.ui.btn_apply_deladd_row_jur.setText('Применить')

    @CQT.onerror
    def tbl_komplektovka_view_click(self, *args):
        tblv = self.ui.tbl_komplektovka_view
        r = tblv.currentRow()
        nk_dse = CQT.num_col_by_name_c(tblv, 'Операции')
        self.ui.lbl_kompl_info.setText(tblv.item(r, nk_dse).text())

    @CQT.onerror
    def tbl_komplektovka_click(self, *args):
        tblk = self.ui.tbl_komplektovka
        tblv = self.ui.tbl_komplektovka_view
        CMS.specification_task_c(self, tblk, tblv)

    @CQT.onerror
    def otmeka_komplekt(self, *args):
        tbl = self.ui.tbl_komplektovka
        if tbl.currentRow() == -1:
            CQT.msgbox(f'Не вабран наряд')
            return
        if not CMS.user_access(self.db_naryd, 'создание_комплектация',
                               CMS.name_by_empl_c(self.glob_login)):
            return

        nk_nom = CQT.num_col_by_name_c(tbl, 'Пномер')
        nk_nom_tara = CQT.num_col_by_name_c(tbl, 'Компл_номер_тара')
        nk_adres = CQT.num_col_by_name_c(tbl, 'Компл_адрес')
        nk_tvrem = CQT.num_col_by_name_c(tbl, 'Твремя')
        # if float(tbl.item(tbl.currentRow(), nk_tvrem).text()) == 0:
        #    CQT.msgbox(f'Наряд необходимо отнормировать, обратись к нормировщице ТОП')
        #    CQT.migat(self, tbl, tbl.currentRow(), nk_tvrem)
        #    return
        if tbl.item(tbl.currentRow(), nk_nom_tara).text() == '':
            CQT.msgbox(f'Не указана Компл_номер_тара')
            CQT.migat(self, tbl, tbl.currentRow(), nk_nom_tara)
            return
        if F.is_numeric(tbl.item(tbl.currentRow(), nk_nom_tara).text()) == False:
            CQT.msgbox(f'Компл_номер_тара должно быть число')
            CQT.migat(self, tbl, tbl.currentRow(), nk_nom_tara)
            return
        if tbl.item(tbl.currentRow(), nk_adres).text() == '':
            CQT.msgbox(f'Не указан Компл_адрес')
            CQT.migat(self, tbl, tbl.currentRow(), nk_adres)
            return
        nom_nar = int(tbl.item(tbl.currentRow(), nk_nom).text())

        # if not CMS.check_execution_previous_operations(self,nom_nar,2):
        #    CQT.msgbox(f'по наряду {nom_nar} не выполнены требования маршрута, работа ЗАБЛОКИРОВАНА')
        #    return

        if CQT.msgboxgYN(f'Я, {CMS.name_by_empl_c(self.glob_login)}, подтверждаю наличие полного комплекта по'
                         f' наряду №{nom_nar}. Я осознаю и несу полную ответственность за производственные'
                         f' потери, вызванные недостоверностью предоставленных данных.'):
            custom_request_c = f'UPDATE naryad SET Компл_ФИО = "{CMS.name_by_empl_c(self.glob_login)}", Компл_Дата = "{F.now()}",' \
                               f' Компл_номер_тара = "{tbl.item(tbl.currentRow(), nk_nom_tara).text()}",' \
                               f' Компл_адрес = "{tbl.item(tbl.currentRow(), nk_adres).text()}" WHERE Пномер = {nom_nar}'
            CSQ.custom_request_c(self.db_naryd, custom_request_c)
            self.load_table_komplekt()

    @CQT.onerror
    def select_invers_dse(self, *args):
        tbl = self.ui.tbl_dse
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        for i in range(tbl.rowCount()):
            if tbl.isRowHidden(i) == False:
                if tbl.cellWidget(i, nk_check).isChecked():
                    tbl.cellWidget(i, nk_check).setChecked(False)
                    tbl.item(i, nk_check).setText('')
                else:
                    tbl.cellWidget(i, nk_check).setChecked(True)
                    tbl.item(i, nk_check).setText('1')
        self.tbl_dse_select()
        self.raschet_naruada_time_tmp()

    @CQT.onerror
    def select_dse(self, korr=1, row=''):
        tbl = self.ui.tbl_dse
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        if row == '':
            row = tbl.currentRow()
        if tbl.cellWidget(row - korr, nk_check) == None:
            return
        if tbl.cellWidget(row - korr, nk_check).isChecked():
            tbl.cellWidget(row - korr, nk_check).setChecked(False)
            tbl.item(row - korr, nk_check).setText('')

        else:
            tbl.cellWidget(row - korr, nk_check).setChecked(True)
            tbl.item(row - korr, nk_check).setText('1')
        MARSH.bold_in_marsh_selected_dse(self)

    @CQT.onerror
    def unselect_all_dse(self, *args):
        tbl = self.ui.tbl_dse
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        shift = (QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier) == QtCore.Qt.ShiftModifier

        for i in range(tbl.rowCount()):
            if not shift and tbl.isRowHidden(i):
                continue
            tbl.cellWidget(i, nk_check).setChecked(False)
            tbl.item(i, nk_check).setText('')
            self.rc_outsource_is_selected()
        self.tbl_dse_select()
        self.ui.tbl_dse_check_podr.setProperty('selected_row', 0)         #  16.06.25 по задаче (100055264)
        self.ui.tbl_dse_check_prof.setProperty('selected_row', 0)
        self.raschet_naruada_time_tmp()

    # +++ 16.06.25 по задаче (100055264)
    def on_check_tbl_click_cr_nar(self, model_index: QtCore.QModelIndex, *args):
        model = model_index.model()
        tbl = model.parent()
        field = tbl.property('field')
        nk_field = CQT.num_col_by_name_c(tbl, field)
        if field is None:
            return

        main_tbl: QtWidgets.QTableWidget = self.ui.tbl_dse
        fltr_dse = self.ui.tbl_filtr_dse
        if field == 'Строка':
            row_nk = CQT.num_col_by_name_c(tbl, field)
            row = tbl.item(tbl.currentRow(), row_nk).text()
            if not F.is_numeric(row):
                return
            row = int(row) - 1
            if main_tbl.isRowHidden(row):
                return CQT.msgbox('Строка скрыта из-за примененного фильтра')
            main_tbl.setCurrentCell(row, 0)
            main_tbl.scrollToItem(main_tbl.item(row, 0))
            return

        prev_fltrs = CQT.get_dict_line_form_tbl(fltr_dse, 0)
        curr_fltr_values = {key: '' for key, val in prev_fltrs.items()}
        value = tbl.item(tbl.currentRow(), nk_field).text()
        curr_fltr_values[field] = '|'.join(value.split(';'))
        CQT.fill_filtr_c(self, fltr_dse, main_tbl, curr_fltr_values)
        CQT.apply_filtr_c(self, fltr_dse, main_tbl)
        tbl.setProperty('selected_row', tbl.currentRow())
        self.raschet_naruada_time_tmp()

    def fill_state_tables(self, data_rc: list[str], data_prof: dict[tuple, int], data_time: list[dict]):
        sorted_time_data = list(sorted(data_time, key=lambda x: x['Сумма минут'], reverse=True))
        bad_state = '🔴'
        success_state = '🟢'
        sourted_prof = [{'Кол-во вхождений': count, 'Профессия': ';'.join(prof)}
                        for prof, count in sorted(data_prof.items())
                        if count != 0]
        counter_rc = collections.Counter(data_rc)
        sourted_rc = [{'Кол-во вхождений': count, 'РЦ': rc} for rc, count in counter_rc.most_common()]
        table_credentials = [
            {'field': 'РЦ', 'table': self.ui.tbl_dse_check_podr, 'data': sourted_rc,
             'label': self.ui.lbl_dse_check_podr,
             'postfix': 'РЦ', 'out_validate': False},
            {'field': 'Профессия', 'table': self.ui.tbl_dse_check_prof, 'data': sourted_prof,
             'label': self.ui.lbl_dse_check_prof, 'postfix': 'Допустимые профессии', 'out_validate': False},
            {'field': 'Строка', 'table': self.ui.tbl_dse_check_time, 'data': sorted_time_data,
             'label': self.ui.lbl_dse_check_time, 'postfix': 'Выделенные строки', 'out_validate': True},
        ]
        bad_rgb = 255, 148, 148
        success_rgb = 204, 255, 204
        base_font = QtGui.QFont()
        base_font.setPointSize(8)
        for credential in table_credentials:
            match credential:
                case {"field": str(field), "table": tbl, 'data': data, 'label': label, 'postfix': postfix,
                      'out_validate': out_validate}:  # type: tbl: QtWidgets.QTableWidget
                    selected_row = tbl.property('selected_row') or 0
                    mutable = tbl.property('mutable')
                    bad_rows = set()
                    if mutable is None:
                        tbl.doubleClicked.connect(self.on_check_tbl_click_cr_nar)
                        tbl.setProperty('mutable', True)
                        tbl.setProperty('field', field)
                    if data:
                        CQT.fill_wtabl(data, tbl, hide_head_rows=True, auto_type=False, ogr_maxshir_kol=106)
                        nk_field = CQT.num_col_by_name_c(tbl, field)
                        tbl.setFont(base_font)
                        tbl.horizontalHeader().setFont(base_font)
                        if selected_row >= tbl.rowCount():
                            selected_row = 0
                        main_val = set(tbl.item(selected_row, nk_field).text().split(';'))
                        for row in range(tbl.rowCount()):
                            rgb = (255, 255, 255) if out_validate else bad_rgb
                            value = tbl.item(row, nk_field).text()
                            split_val = set(value.split(';'))
                            if main_val.intersection(split_val):
                                rgb = success_rgb
                            else:
                                bad_rows.add(row)
                            for col in range(tbl.columnCount()):
                                tbl.item(row, col).setBackground(QtGui.QBrush(QtGui.QColor(*rgb)))
                        tbl.setCurrentCell(int(selected_row), 0)
                        tbl.scrollToItem(tbl.item(int(selected_row), 0))
                        tbl.setProperty('selected_row', selected_row)
                    else:
                        CQT.clear_tbl(tbl)
                    state = success_state
                    if out_validate:
                        property_state = tbl.property('validate')
                        state = success_state if property_state else bad_state
                    elif len(bad_rows) != 0 or len(data) == 0:
                        state = bad_state
                        tbl.setProperty('validate', False)
                    else:
                        tbl.setProperty('validate', True)
                    label.setText(f'{state} {postfix}')
                case _:
                    print(credential)

    @CQT.onerror
    def select_all_dse(self, *args):
        tbl = self.ui.tbl_dse
        tbl.blockSignals(True)
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        self.glob_etap = set()
        self.set_rc_check_dse = set()
        shift = (QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier) == QtCore.Qt.ShiftModifier

        for i in range(tbl.rowCount()):
            if not shift and tbl.isRowHidden(i):
                continue
            # if tbl.isRowHidden(i) == False:
            tbl.cellWidget(i, nk_check).setChecked(True)
            tbl.item(i, nk_check).setText('1')
            self.rc_outsource_is_selected()
        self.raschet_naruada_time_tmp()
        tbl.blockSignals(False)
    # --- 16.06.25 по задаче (100055264)

    @CQT.onerror
    def check_sootv_res_nommk(self):
        lbl = self.ui.lbl_curr_mk
        if "МК " + str(self.glob_nom_mk) != lbl.text().split(' - ')[0]:
            CQT.msgbox('Не выбрана МК')
            return
        self.glob_res = CMS.load_res(self.glob_nom_mk)
        return True

    @CQT.onerror
    def create_naryd(self, *args):

        def delete_nar(date_nar, dse_id):
            CSQ.custom_request_c(self.db_naryd, f"""DELETE FROM naryad WHERE Дата = '{date_nar}' 
                                    AND ДСЕ_ID = '{dse_id}';""")

        def calc_koef_slogn(self, nom_mk):
            query = CSQ.custom_request_c(self.db_naryd,
                                         f"""SELECT Тип, Тип_доработки FROM mk WHERE Пномер = {nom_mk}""", one=True,
                                         rez_dict=True)
            if query == None or query == False:
                CQT.msgbox(f'ОШибка расчета коэффициента сложности тип')
                return False

            if query['Тип'] == 2:
                query_dorez = CSQ.custom_request_c(self.db_naryd,
                                                   f"""SELECT Причина, Пномер FROM дорезки_мк WHERE Номер_мк = {nom_mk}""",
                                                   rez_dict=True)
                if query_dorez == None or query_dorez == False:
                    CQT.msgbox(f'ОШибка расчета коэффициента сложности дорезка')
                    return False
                if len(query_dorez) > 0:
                    if query_dorez[0]['Причина'] not in self.DICT_TIP_DOREZ:
                        CQT.msgbox(f'ОШибка определения коэффициента сложности дорезка')
                        return False
                    return self.DICT_TIP_DOREZ[query_dorez[0]['Причина']]['Коэффициент_наряда']
            if query['Тип'] == 5:
                if query['Тип_доработки'] not in self.DICT_TIP_DORAB:
                    CQT.msgbox(f'ОШибка определения коэффициента сложности доработка')
                    return False
                return self.DICT_TIP_DORAB[query['Тип_доработки']]['Коэффициент_наряда']
            return 1

        if self.glob_login == '':
            return
        try:
            len(self.spis_dse)
        except:
            return
        is_vneplan_project_mode = self.ui.checkBox_vneplan_rab.isChecked()

        if not is_vneplan_project_mode:
            if len(self.spis_dse) == 0:
                CQT.msgbox('Не выбраны операции')
                return
            if F.valm(self.ui.lineEdit_cr_nar_norma.text()) == 0:
                CQT.msgbox('Норма времени не может быть 0')
                return
            if not F.is_numeric(self.ui.lineEdit_koef_norm.text()):
                CQT.msgbox('Коэфф. норм не число')
                return
            if F.valm(self.ui.lineEdit_koef_norm.text()) <= 0 or F.valm(self.ui.lineEdit_koef_norm.text()) > 1:
                CQT.msgbox('Коэфф. норм должен быть от 0 до 1')
                return
            if self.ui.plainTextEdit_zadanie.toPlainText() == '':
                CQT.msgbox('Задание не может быть пусто')
                return
            if self.check_sootv_res_nommk() != True:
                return

            kat_vnepl = 0
        else:  # Внеплан
            if self.spis_dse != []:
                CQT.msgbox('Для внеплана не должны быть выбраны ДСЕ')
                return

            if F.valm(self.ui.lineEdit_cr_nar_norma.text()) != 0:
                CQT.msgbox('Норма времени должна быть 0')
                return
            if self.ui.plainTextEdit_zadanie.toPlainText() != '':
                CQT.msgbox('Задание должно пусто')
                return

            if self.ui.cmb_kat_vnepl.currentText() == "":
                CQT.msgbox('Не выбрана категория Внеплановых работ')
                return

            if self.ui.cmb_prof_vnepl.currentText() == "":
                CQT.msgbox('Не выбрана профессия')
                return
            if self.ui.lineEdit_cr_nar_kolvo.text() == "":
                CQT.msgbox('Не указано количество')
                return
            if F.is_numeric(self.ui.lineEdit_cr_nar_kolvo.text()) == False:
                CQT.msgbox('Количество должно быть числом')
                return

            kat_vnepl = self.DICT_KATEG_VNEPLAN[self.ui.cmb_kat_vnepl.currentText()]
            if kat_vnepl in (2, 3):
                if self.ui.le_nom_zam.text() == '':
                    CQT.msgbox('Не указан номер из журнала замечаний')
                    return

            self.spis_sort_crab = ['']

            self.spis_dse = ['ДСЕ$НН']
            self.spis_id = ['0']
            self.spis_oper = ['001$Сварка']
            self.spis_prof = [self.ui.cmb_prof_vnepl.currentText()]
            self.spis_vr = [self.ui.lineEdit_cr_nar_norma.text()]
            self.spis_kolvo = [self.ui.lineEdit_cr_nar_kolvo.text()]
        nom_zam_zhurnal = self.ui.le_nom_zam.text()
        kompl_fio = ''
        kompl_data = ''
        kompl_tara = ''
        kompl_address = ''
        if self.ui.checkBox_bez_kompl.isChecked() or self.CHECK_KOMPLEKT_TAB == False:
            kompl_fio = CMS.name_by_empl_c(self.glob_login)
            kompl_data = F.now()
            kompl_tara = '-'
            kompl_address = 'Авто'
        koef_slogn = calc_koef_slogn(self, self.glob_nom_mk)
        if koef_slogn == False:
            return

        date_nar = F.now()
        dse_id = '|'.join(self.spis_id)
        zadanie_fix = self.ui.plainTextEdit_zadanie.toPlainText().replace("\n", "LF")
        prim_fix = self.ui.plainTextEdit_primechanie.toPlainText().replace("\n", "LF")
        stroka = [date_nar,
                  CMS.name_by_empl_c(self.glob_login),
                  self.glob_nom_mk,
                  self.ui.checkBox_vneplan_rab.isChecked(),
                  zadanie_fix,
                  kompl_fio,
                  kompl_data,
                  kompl_tara,
                  kompl_address,
                  '',
                  '',
                  '',
                  '',
                  round(F.valm(self.ui.lineEdit_cr_nar_norma.text()) * F.valm(self.ui.lineEdit_koef_norm.text()), 2),
                  '|'.join(self.spis_dse),
                  dse_id,
                  '|'.join(self.spis_oper),
                  '|'.join(self.spis_vr),
                  '|'.join(self.spis_kolvo),
                  prim_fix,
                  koef_slogn, 0, kat_vnepl, '|'.join(self.spis_sort_crab), nom_zam_zhurnal, '', '',
                  '|'.join(self.spis_prof), list(self.set_rc_check_dse)[0], F.valm(self.ui.lineEdit_koef_norm.text()),
                  int(self.ui.chkb_autcourse.isChecked()),
                  round(F.valm(self.ui.lineEdit_cr_nar_norma.text()), 2)]

        custom_request_c = f'''INSERT INTO naryad (Дата,	Автор,Номер_мк,Внеплан,Задание,Компл_ФИО,Компл_Дата,
        Компл_номер_тара,
        Компл_адрес,ФИО,Фвремя,ФИО2,Фвремя2,Твремя,ДСЕ,ДСЕ_ID,Операции,Опер_время,Опер_колво,Примечание,Коэфф_сложности,
        Подтвержд_вып,Категория_внепл,Виды_работ,Номер_замечания_журнал,Подтвержд_вып_дата,Подтвержд_вып_фио,Профессии,
        РЦ_наряд,Коэф_норм_созд,Аутсорсинг,Норма_времени) VALUES 
        ({", ".join(("?" * len(stroka)))}) RETURNING *;'''
        nom_nar = CSQ.custom_request_c(self.db_naryd, custom_request_c, list_of_lists_c=stroka)
        # if rez == None or rez == False:
        #     CQT.msgbox(f'Неудачно!, попробуй еще.')
        #     self.spis_dse = []
        #     self.spis_id = []
        #     self.spis_oper = []
        #     delete_nar(date_nar, dse_id)
        #     return
        # nom_nar = CSQ.custom_request_c(self.db_naryd, f"""SELECT Пномер FROM naryad WHERE Дата = '{date_nar}'
        # AND ДСЕ_ID = '{dse_id}' ORDER BY Пномер DESC LIMIT 1""")

        try:
            if len(nom_nar) != 2 or F.is_numeric(nom_nar[-1][0]) == False:
                CQT.msgbox(f'Неудачно!, попробуй еще.')
                self.spis_dse = []
                self.spis_id = []
                self.spis_oper = []
                delete_nar(date_nar, dse_id)
                return
        except:
            CQT.msgbox(f'Неудачно!, попробуй еще.')
            delete_nar(date_nar, dse_id)
            self.spis_dse = []
            self.spis_id = []
            self.spis_oper = []
            return



        CQT.msgbox(f'Наряд №{nom_nar[-1][0]} создан')
        self.ui.plainTextEdit_zadanie.setPlainText('')
        self.ui.plainTextEdit_primechanie.setPlainText('')
        self.ui.lineEdit_cr_nar_norma.setText('')
        self.load_mk()

    @CQT.onerror
    def primen_imena(self, *args):
        def is_osnovnoy(self, fio):
            if fio not in self.DICT_EMPLOEE_FULL_WITH_DEL:
                return False
            if self.DICT_EMPLOEE_FULL_WITH_DEL[fio]['Должность'] not in self.DICT_PROFESSIONS_NAME:
                return False
            if self.DICT_PROFESSIONS_NAME[self.DICT_EMPLOEE_FULL_WITH_DEL[fio]['Должность']]['Прямые'] == 0:
                return False
            return True

        # list_boch = CSQ.custom_request_c(self.db_naryd,f"""SELECT * from naryad WHERE Пномер =34239""",rez_dict=True)
        # for nar in list_boch:
        #    list_nar = self.get_list_last_base_nar(nar['Номер_мк'], nar['Пномер'])
        #    if list_nar == None:
        #        return
        #    line =','.join([str(_) for _ in list_nar])
        #    CSQ.custom_request_c(self.db_naryd,f"""UPDATE naryad SET (ФИО_для_ОТК)
        #   = ('{line}')
        #    WHERE Пномер == {nar['Пномер']} ;""")
        #
        # return
        nk_py = CQT.num_col_by_name_c(self.ui.tbl_vibor_nar_rasp, 'Номер_заказа')
        if nk_py == None:
            CQT.msgbox(f'Поле Номер_заказа не найдено')
            return

        nom_py = self.ui.tbl_vibor_nar_rasp.item(self.ui.tbl_vibor_nar_rasp.currentRow(), nk_py).text()
        nom_nar = int(self.ui.lbl_vibr_nar.text())

        if not CMS.check_execution_previous_operations(self, nom_nar, check_by_vip=False):
            CQT.msgbox(f'по наряду {nom_nar} не выполнены требования маршрута, работа ЗАБЛОКИРОВАНА')
            return

        fio_for_otk = ''
        dict_row = CQT.get_dict_line_form_tbl(self.ui.tbl_vibor_nar_rasp)
        nums_compl = self.ui.le_nom_compl.text().strip().replace(';', ',')
        if nums_compl == '':
            CQT.msgbox(f'Не введены номера комплектов')
            return
        try:
            list_compl = nums_compl.split(',')
            nums_compl = [int(_) for _ in list_compl]
            for num_k in nums_compl:
                if num_k > int(dict_row["Кол. изделий"]):
                    CQT.msgbox(f'Не корректно введены номера комплектов')
                    return
            list_compl = ','.join([str(_) for _ in nums_compl])
        except:
            CQT.msgbox(f'Не корректно введены номера комплектов')
            return
        str_fio_otk_from_master = ''
        if not self.ui.fr_otk.isHidden():
            # if self.ui.cmb_rab_for_otk_1.currentText() == '' and self.ui.cmb_rab_for_otk_2.currentText() == '':
            #    CQT.msgbox(f'по наряду {nom_nar} не выбраны ФИО работников, контролируемых в ОТК')
            #    return
            # fio_for_otk = self.ui.cmb_rab_for_otk_1.currentText() + "|" + self.ui.cmb_rab_for_otk_2.currentText()

            fl_open_fr_otk = self.is_nar_for_otk(dict_row['Операции'])

            if fl_open_fr_otk and int(dict_row['Аутсорсинг']) == 0:
                if self.ui.lbl_nnar_for_control.text() == '':
                    CQT.msgbox(f'Для распределения наряда необходимо сформировать предыдущие нарды')
                    return
            fio_for_otk = self.ui.lbl_nnar_for_control.text()
            users_for_otk = []
            for i in range(self.ui.tbl_list_empl_for_kontr.rowCount()):
                if self.ui.tbl_list_empl_for_kontr.item(i, 0).text() == '1':
                    users_for_otk.append(self.ui.tbl_list_empl_for_kontr.item(i, 1).text())
            if len(users_for_otk) == 0:
                CQT.blink_obj_c(self, 2, self.ui.tbl_list_empl_for_kontr, f'Не выбраны исполнители под контроль ОТК')
                return
            if len(users_for_otk) > 2:
                CQT.blink_obj_c(self, 2, self.ui.tbl_list_empl_for_kontr, f'Не более 2 исполнителей под контроль ОТК')
                return
            str_fio_otk_from_master = ';'.join(users_for_otk)

        if self.ui.lbl_vibr_nar.text() == '':
            CQT.msgbox('Не выбран наряд')
            return
        if self.ui.lbl_ispoln1.text() == '' and self.ui.lbl_ispoln2.text() == '':
            CQT.msgbox('Не выбран исполнитель')
            return
        fio = self.ui.lbl_ispoln1.text()
        fio2 = self.ui.lbl_ispoln2.text()

        nk_norma = CQT.num_col_by_name_c(self.ui.tbl_vibor_nar_rasp, 'Твремя')
        if nk_norma == None:
            CQT.msgbox(f'Поле Твремя не найдено')
            return
        norma = F.valm(self.ui.tbl_vibor_nar_rasp.item(self.ui.tbl_vibor_nar_rasp.currentRow(), nk_norma).text())
        if norma == 0 or norma == 0.0:
            CQT.msgbox(f'Наряд {nom_nar} необходимо отнормировать, обратись к нормировщице ТОП')
            return

        fl_check_max_time = False  # BD_users_srv professions Прямые
        if fio != '':
            if is_osnovnoy(self, fio):
                fl_check_max_time = True
        if fio2 != '':
            if is_osnovnoy(self, fio2):
                fl_check_max_time = True
        if fl_check_max_time:
            nar = CMS.Naryads(nom_nar, self.db_naryd, self.DICT_DOLGN_ETAP, self.bd_users,
                              self.DICT_EMPLOEE_FULL_WITH_DEL)
            if fio2 != '' and fio != '':
                norma = norma / 2
            if not (len(nar.params) == 1 and nar.params[0]['Опер_колво'] == 1):
                if not (fio2 != '' and fio != ''):
                    if norma > self.MAX_TIME_NARUAD / 2:
                        CQT.msgbox(f'Наряд {nom_nar} слишком большой по времени для одного исполнителя')
                        return
        if self.ui.te_comment.toPlainText() != dict_row['Примечание']:
            CSQ.custom_request_c(self.db_naryd, f"""UPDATE naryad SET Примечание =?  WHERE Пномер == ?""",
                                 list_of_lists_c=[self.ui.te_comment.toPlainText(), nom_nar])
            CQT.set_val_tbl_by_name(self.ui.tbl_vibor_nar_rasp, self.ui.tbl_vibor_nar_rasp.currentRow(), 'Примечание',
                                    self.ui.te_comment.toPlainText())
        is_outsource = self.ui.chk_outsource_nar.isChecked()
        if self.ui.chk_obosobl_rasc.checkState() == 2:
            params = [F.now(), self.glob_ima, fio, fio2, norma, fio_for_otk, str_fio_otk_from_master, 1, 0.0001, is_outsource,
                      nom_nar]
            custom_request_c = f'''  UPDATE naryad SET Распред_дата==?, Распред_ФИО==?, ФИО==?, ФИО2==?, Твремя==?, ФИО_для_ОТК = ?, 
                        ФИО_для_ОТК_от_мастера = ?, Обособленная_расценка = ?, Коэфф_сложности = ? , Аутсорсинг = ?
                          WHERE Пномер == ?'''
        else:
            params = [F.now(), self.glob_ima, fio, fio2, norma, fio_for_otk, str_fio_otk_from_master, list_compl, is_outsource,
                      nom_nar]
            custom_request_c = f'''  UPDATE naryad SET Распред_дата==?, Распред_ФИО==?, ФИО==?, ФИО2==?, Твремя==?, ФИО_для_ОТК = ?, 
             ФИО_для_ОТК_от_мастера = ?, Заводской_комплект = ? , Аутсорсинг = ?
              WHERE Пномер == ?'''

        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c, list_of_lists_c=params)
        if not rez:
            CQT.msgbox(f'Ошибка занесения', time_life=3)
            return

        nar = CMS.Naryads(nom_nar, self.db_naryd)
        nar.recalc_astronom_time(self.DICT_OPER_NAME)

        self.ui.lbl_vibr_nar.clear()
        self.ui.lbl_ispoln1.clear()
        self.ui.lbl_ispoln2.clear()
        self.ui.cmb_prof_rasp.clear()
        self.select_tbl_projs_raspred()
        CQT.clear_tbl(self.ui.tbl_vibor_rabotn_rasp)
        CQT.msgbox(f'Наряд №{nom_nar} успешно распределен')

    @CQT.onerror
    def zapoln_table_rabont_po_prof(self, prof):
        chk_filtr_usr_by_rc: QtWidgets.QCheckBox = self.ui.chk_filtr_usr_by_rc
        fio_by_rc = True
        if chk_filtr_usr_by_rc.checkState() == QtCore.Qt.CheckState.Unchecked:
            fio_by_rc = False
        tbl_nars = self.ui.tbl_vibor_nar_rasp
        tbl = self.ui.tbl_vibor_rabotn_rasp
        spis_sotr = [['Наряды', "ФИО", "Остаток, мин.", 'Выработано, %']]
        tup_fileds = ('ФИО', 'ФИО2')
        custom_request_c = ''
        list_template_req = []
        if fio_by_rc:
            nf_nar = CQT.num_col_by_name_c(tbl_nars, 'Пномер')
            nnar = self.ui.lbl_vibr_nar.text()
            dict_row = None
            for i in range(tbl_nars.rowCount()):
                if tbl_nars.item(i,nf_nar).text() == nnar:
                    dict_row = CQT.get_dict_line_form_tbl(tbl_nars)
                    break
            if dict_row == None:
                CQT.msgbox(f'Ошибка связи с нарядом')
                return
            rcs = dict_row['РЦ'].split(',')
            list_podrs = [self.DICT_RC_FULL[_]['empl_Подразделение'] for _ in rcs if _ in self.DICT_RC_FULL]


        company = CFG.Config.place.Имя

        if fio_by_rc:
            list_users = [k for k, v in self.DICT_EMPLOEE_FULL.items() if
                          v['Должность'] == prof and (v['Компания'] == company or v['Режим'] == 'Абстракт') and v[
                              'Подразделение'] in  list_podrs]
        else:
            list_users = [k for k, v in self.DICT_EMPLOEE_FULL.items() if v['Должность'] == prof and (v['Компания'] == company or v['Режим'] == 'Абстракт')]



        for f in tup_fileds:
            template_req = f'''
                SELECT 
                    naryad.Пномер, 
                    naryad.{f} as "ФИО_",  
                    naryad.Твремя, 
                    naryad.Норма_времени, 
                    SUM(jurnal.Подытог) as Подытог
                FROM naryad  
                INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
                INNER JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер AND jurnal.ФИО = ФИО_  AND jurnal.Подытог_нормы != ""
                WHERE ФИО_ in ({CSQ.prepare_list_to_tuple(list_users)}) AND ((mk.Статус != "Закрыта" AND mk.Дата_завершения == "") OR (naryad.Внеплан == {self.place.КодыНарядов.Простой})) 
                                        AND ФИО_ != "" AND Фвремя == "" and Подтвержд_вып_дата == "" 
                                    GROUP BY naryad.Пномер, ФИО_  '''
            list_template_req.append(template_req)
        custom_request_c = ' UNION '.join(list_template_req) + ' ORDER BY  naryad.Пномер;'

        spis_nezav_nar = CSQ.custom_request_c(self.db_naryd, custom_request_c, rez_dict=True)
        if spis_nezav_nar == False:
            CQT.msgbox('БД занята, пробуй позже')
            return
        catched_empls = sorted(list({_['ФИО_'] for _ in spis_nezav_nar}))
        set_catched_empls = set(catched_empls)
        for empl in list_users:
            remain_summ = 0
            norma_summ = 0
            count_nar = 0
            poditog_summ = 0
            for nar in spis_nezav_nar:
                if not nar['ФИО_'] == empl:
                    continue
                delta = nar['Норма_времени'] - nar['Подытог']
                if delta < 0:
                    delta = 0
                remain_summ += delta
                poditog_summ += nar['Подытог']
                norma_summ += nar['Норма_времени']
                count_nar += 1
            spis_sotr.append([count_nar, empl, f'{round(remain_summ)} из {round(norma_summ)} по {count_nar} открытым',
                              f'{norma_summ}|{poditog_summ}'])

        CQT.fill_wtabl(spis_sotr, tbl, height_row=24, auto_type=False, hide_head_rows=True,
                       list_column_widths=CMS.load_column_widths(self, tbl), StretchLastRow=False)
        CQT.fill_progress_c(self, tbl, 3, True, True, True)

        def show_nars(self, r, c):
            tbl: QtWidgets.QTableWidget = self.ui.tbl_vibor_rabotn_rasp
            nf_user = CQT.num_col_by_name_c(tbl, 'ФИО')
            fio = tbl.item(r, nf_user).text()
            tup_fileds = ('ФИО', 'ФИО2')
            custom_request_c = ''
            list_template_req = []

            for f in tup_fileds:
                template_req = f'''SELECT naryad.Пномер, naryad.Дата, naryad.Номер_мк, naryad.Задание, naryad.ФИО, naryad.ФИО2, 
                        naryad.Твремя, naryad.Норма_времени AS "Норматив время", SUM(jurnal.Подытог) as Подытог,      
                           CASE WHEN ROUND(naryad.Норма_времени - SUM(jurnal.Подытог),2) < 0
                           THEN 0 
                           ELSE ROUND(naryad.Норма_времени - SUM(jurnal.Подытог),2) 
                           END AS Остаток, 
                          naryad.Компл_номер_тара,
                         naryad.Компл_адрес, naryad.Примечание, naryad.Внеплан,
                         
                        CASE WHEN знпр.№проекта IS NOT NULL 
                       THEN знпр.№проекта 
                       ELSE mk.Номер_проекта 
                       END AS Номер_проекта, 
                        
                        
                        CASE WHEN знпр.№ERP IS NOT NULL 
                       THEN знпр.№ERP 
                       ELSE mk.Номер_заказа 
                       END AS Номер_заказа, 
                
                        CASE WHEN plan.Приоритет IS NOT NULL 
                       THEN plan.Приоритет 
                       ELSE mk.Приоритет 
                       END AS Приоритет, 
                        
                        
                        naryad.Коэфф_сложности, naryad.Виды_работ, 
                        naryad.Опер_время, mk.Статус_ЧПУ, zagot.Прим_резка, naryad.ФИО_для_ОТК , naryad.Операции  , 
                        naryad.Распред_ФИО , naryad.Кол_повт_приемок AS "Кол_во повт. приёмок" 
                                                    FROM naryad  INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
                                                    INNER JOIN zagot ON zagot.Ном_МК = naryad.Номер_мк 
                                                       LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
                                                       LEFT JOIN plan ON plan.Пномер = mk.НомКплан  
                                                LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
               INNER JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер AND jurnal.ФИО = naryad.{f}  AND jurnal.Подытог_нормы != ""
                WHERE naryad.{f} = "{fio}" AND ((mk.Статус != "Закрыта" AND mk.Дата_завершения == "") OR (naryad.Внеплан == {self.place.КодыНарядов.Простой})) 
                                                    AND naryad.{f} != "" AND Фвремя == "" and Подтвержд_вып_дата == "" 
                                                GROUP BY naryad.Пномер, naryad.{f}  '''
                list_template_req.append(template_req)
            custom_request_c = ' UNION '.join(list_template_req) + ' ORDER BY  naryad.Пномер;'
            spis_nezav_nar = CSQ.custom_request_c(self.db_naryd, custom_request_c, rez_dict=True,
                                                  attach_dbs=(self.db_kplan))
            CQT.msgboxg_get_table(self, 'Данные по нарядам для ' + fio, spis_nezav_nar, btn1_name='OK',
                                  disable_btn0=True, load_summ=True, WindowTitle='Список данных по нарядам')

        nf_nar = CQT.num_col_by_name_c(tbl, 'Наряды')
        for i in range(tbl.rowCount()):
            if tbl.item(i, nf_nar).text() == '0':
                tbl.item(i, nf_nar).setText('')
                continue
            CQT.add_btn(tbl, i, 0, 'Наряды сотрудника', conn_func_checked_row_col=show_nars, self=self,
                        img_path=r'C:\Python\Terminal_sozd_new\icons\cust_btn_show_nar')

    @CQT.onerror
    def select_prof_raspr(self, nom, *args):
        if nom == 0:
            return
        prof = self.ui.cmb_prof_rasp.itemText(nom)
        self.zapoln_table_rabont_po_prof(prof)

    @CQT.onerror
    def clear_radio_isp(self, *args):
        if self.ui.radioButton_ispoln1.isChecked():
            self.ui.lbl_ispoln1.clear()
        else:
            self.ui.lbl_ispoln2.clear()

    @CQT.onerror
    def tbl_rabotn_raspr_click(self, *args):
        tbl = self.ui.tbl_vibor_rabotn_rasp
        nk_fio = CQT.num_col_by_name_c(tbl, 'ФИО')
        if self.ui.radioButton_ispoln1.isChecked():
            if self.ui.lbl_ispoln2.text() != tbl.item(tbl.currentRow(), nk_fio).text():
                self.ui.lbl_ispoln1.setText(tbl.item(tbl.currentRow(), nk_fio).text())
        if self.ui.radioButton_ispoln2.isChecked():
            if self.ui.lbl_ispoln1.text() != tbl.item(tbl.currentRow(), nk_fio).text():
                self.ui.lbl_ispoln2.setText(tbl.item(tbl.currentRow(), nk_fio).text())

    @CQT.onerror
    def is_nar_for_otk(self, operacii):
        list_opers = operacii.split('|')
        for oper in list_opers:
            name = oper.split('$')[-1]
            if name in self.DICT_OPER_NAME and self.DICT_OPER_NAME[name]['kontrol_opers']:
                return True

        return False

    @CQT.onerror
    def get_list_last_base_nar(self, nom_mk, nom_nar):

        def get_last_oper(self, dse_id: int, oper_nom, res, list_predv_opers):
            prev_osv = ''
            prev_zav = ''
            prev_oper_nom = ''
            prev_oper_name = ''
            prev_oper_rc = ''
            dse = ''
            dse_id_prev = ''
            prev_oper_kod = ''
            ret = []
            for dse in res:
                if dse['Номерпп'] == dse_id:
                    prev_kol = dse['Количество']
                    fl = False
                    for i in range(len(dse['Операции'])):
                        if dse['Операции'][i]['Опер_номер'] == oper_nom:
                            if i == 0:
                                # print(f'{nom_nar} первая операция не проверяется на выполенние предыдущей')
                                list_predv_opers = CMS.get_parent_dse(self, res, dse, list_predv_opers)
                                return list_predv_opers
                            oper = dse['Операции'][i - 1]
                            cur_oper = dse['Операции'][i]
                            if self.DICT_OPER[cur_oper['Опер_код']]['kontrol_opers'] and self.DICT_OPER[oper['Опер_код']]['kontrol_opers']:
                                oper = dse['Операции'][i - 2]
                            if self.DICT_OPER[oper['Опер_код']]['kontrol_opers']:
                                return list_predv_opers
                            prev_osv = oper.get('Освоено,шт.', 0)
                            prev_zav = oper.get('Закрыто,шт.', 0)
                            prev_oper_nom = oper['Опер_номер']
                            prev_oper_name = oper['Опер_наименование']
                            prev_oper_rc = oper['Опер_РЦ_код']
                            prev_oper_kod = oper['Опер_код']
                            fl = True
                            break
                    if fl == False:
                        return fl
                    list_predv_opers.append(
                        {'dse_id': dse['Номерпп'], 'dse': f"{dse['Наименование']} {dse['Номенклатурный_номер']}",
                         'prev_kol': prev_kol,
                         'prev_osv': prev_osv,
                         'prev_zav': prev_zav, 'prev_oper_nom': prev_oper_nom, 'prev_oper_name': prev_oper_name,
                         'prev_oper_rc': prev_oper_rc, 'prev_oper_kod': prev_oper_kod})
                    return list_predv_opers
            return list_predv_opers

        def get_last_base_oper_nar(self, dse_id: int, oper_nom, res, list_nar):

            def get_last_base_oper(self, dse_id: int, oper_nom, res):
                list_predv_opers = []
                list_nar = []
                list_oper_for_check = []
                list_id = [dse_id]
                list_oper_nom = [oper_nom]
                while len(list_id):

                    for i, dse_id in enumerate(list_id):
                        oper_nom = list_oper_nom[i]
                        list_predv_opers = get_last_oper(self, dse_id, oper_nom, res, list_predv_opers)
                        list_id.pop(0)
                        list_oper_nom.pop(0)

                        if list_predv_opers == []:
                            break
                        for oper in list_predv_opers:
                            if oper['prev_oper_kod'] in self.DICT_OPER:
                                if self.DICT_OPER[oper['prev_oper_kod']]['skip_check_otk'] == 0:
                                    list_oper_for_check.append(
                                        {'dse_id': oper['dse_id'], 'prev_oper_nom': oper['prev_oper_nom'], })
                            dse_id = oper['dse_id']
                            oper_nom = oper['prev_oper_nom']
                            list_id.append(dse_id)
                            list_oper_nom.append(oper_nom)
                        list_predv_opers = []
                if list_oper_for_check == []:
                    return
                return list_oper_for_check

            list_base_oper_nar = []
            list_last_base_oper = get_last_base_oper(self, dse_id, oper_nom, res)
            if list_last_base_oper == None:
                return
            for base in list_last_base_oper:
                base_id = base['dse_id']
                base_nomop = base['prev_oper_nom']
                for nar in list_nar:
                    list_dse_id = nar['ДСЕ_ID'].split('|')
                    list_opers_id = nar['Операции'].split('|')
                    for i in range(len(list_dse_id)):
                        nom_oper_id = list_opers_id[i].split('$')[0]
                        if int(list_dse_id[i]) == base_id and nom_oper_id == base_nomop:
                            list_base_oper_nar.append(nar['Пномер'])
            return list_base_oper_nar

        ret_set = set()

        resp = \
            CSQ.custom_request_c(self.db_naryd, f"""SELECT * FROM naryad WHERE Пномер = {int(nom_nar)};""",
                                 rez_dict=True)[
                0]

        list_nar = CSQ.custom_request_c(self.db_naryd, f"""SELECT * FROM naryad WHERE Номер_мк == {nom_mk};""",
                                        rez_dict=True)

        list_dse_id = resp['ДСЕ_ID'].split('|')
        list_opers_id = resp['Операции'].split('|')
        res = CMS.load_res(resp['Номер_мк'], db_resxml=self.db_resxml)
        for i in range(len(list_dse_id)):
            dse_id = list_dse_id[i]
            oper_nom, name = list_opers_id[i].split('$')
            if name in self.DICT_OPER_NAME and self.DICT_OPER_NAME[name]['kontrol_opers']:
                nars = get_last_base_oper_nar(self, int(dse_id), oper_nom, res, list_nar)
                if nars != None:
                    for nar in nars:
                        ret_set.add(nar)
        return list(ret_set)

    @CQT.onerror
    def tbl_nar_raspr_click(self, *args):

        def get_lust_empl_from_mk(self, nom_mk):
            query = f"""SELECT DISTINCT jurnal.ФИО FROM jurnal INNER JOIN 
            naryad ON naryad.Пномер == jurnal.Номер_наряда, 
            mk ON mk.Пномер == naryad.Номер_мк 
            WHERE mk.Пномер == {nom_mk};
            """
            list_empl = CSQ.custom_request_c(self.db_naryd, query, one_column=True, hat_c=False)
            exclude_department = ['Отдел технического контроля', 'Планово-диспетчерский отдел Производства']

            rez = []
            for item in list_empl:
                if item in self.DICT_EMPLOEE_FULL and self.DICT_EMPLOEE_FULL[item][
                    'Подразделение'] not in exclude_department:
                    rez.append(item)
                else:
                    print(f'Исключон {item}')
            return sorted(rez)

        def fill_cmb_empl_for_otk(self, list_empl):
            self.ui.cmb_rab_for_otk_1.clear()
            self.ui.cmb_rab_for_otk_1.addItem('')
            self.ui.cmb_rab_for_otk_1.addItems(list_empl)
            self.ui.cmb_rab_for_otk_2.clear()
            self.ui.cmb_rab_for_otk_2.addItem('')
            self.ui.cmb_rab_for_otk_2.addItems(list_empl)

        self.ui.fr_otk.setHidden(True)
        tbl = self.ui.tbl_vibor_nar_rasp
        self.ui.lbl_ispoln1.clear()
        self.ui.lbl_ispoln2.clear()
        self.ui.cmb_prof_rasp.clear()
        self.ui.cmb_prof_rasp.addItem('')
        CQT.clear_tbl(self.ui.tbl_vibor_rabotn_rasp)
        dict_row = CQT.list_from_wtabl_c(tbl, '', rez_dict=True, only_current_row=True)[0]
        nk_nom_mar = CQT.num_col_by_name_c(tbl, 'Номер_мк')
        nk_nom_nar = CQT.num_col_by_name_c(tbl, 'Пномер')
        nk_vneplan = CQT.num_col_by_name_c(tbl, 'Внеплан')
        nom_nar = tbl.item(tbl.currentRow(), nk_nom_nar).text()
        self.ui.lbl_vibr_nar.setText(nom_nar)
        nom_mk = int(tbl.item(tbl.currentRow(), nk_nom_mar).text())
        vneplan = int(tbl.item(tbl.currentRow(), nk_vneplan).text())
        line = CQT.get_dict_line_form_tbl(tbl, tbl.currentRow())
        self.ui.lbl_nnar_for_control.setText("")
        autsource = int(line['Аутсорсинг'])
        self.ui.chk_outsource_nar.blockSignals(True)
        self.ui.chk_outsource_nar.setChecked(bool(autsource))
        self.ui.chk_outsource_nar.blockSignals(False)
        set_prof = set()
        # spis_dop_prof = F.load_file(F.scfg('Filtr_rab') + F.sep() + 'spis_dop_prof.txt')
        # if spis_dop_prof:
        #    for prof in spis_dop_prof:
        #        set_prof.add(prof)
        self.ui.te_comment.setText(dict_row['Примечание'])
        if autsource == 1:
            for prof in self.DICT_PROFESSIONS.keys():
                if self.DICT_PROFESSIONS[prof]['Группа_в_распред'] == "Снабжение":
                    set_prof.add(self.DICT_PROFESSIONS[prof]['имя'])
        else:
            if vneplan == 1:
                for prof in self.DICT_PROFESSIONS.keys():
                    set_prof.add(self.DICT_PROFESSIONS[prof]['имя'])
            else:
                list_dse_id = dict_row['ДСЕ_ID'].split("|")
                list_opers = dict_row['Операции'].split("|")

                res = CMS.load_res(nom_mk)

                if res == False:
                    CQT.msgbox(f'Не удалось загрузить ресурнсую попробуй позже')
                    return
                for i, id in enumerate(list_dse_id):
                    for dse in res:
                        if dse['Номерпп'] == int(id):
                            for oper in dse['Операции']:
                                if oper['Опер_номер'] == list_opers[i].split("$")[0]:
                                    if oper['Опер_профессия_код'] in self.DICT_PROFESSIONS:
                                        set_prof.add(self.DICT_PROFESSIONS[oper['Опер_профессия_код']]['имя'])
                                    else:
                                        CQT.msgbox(f'Профессия {oper["Опер_профессия_код"]} не найдена в БД')

        set_group = set()
        for _ in set_prof:
            if _ in self.DICT_PROFESSIONS_NAME:
                set_group.add(self.DICT_PROFESSIONS_NAME[_]['Группа_в_распред'])
            else:
                CQT.msgbox(f'{_} не отмечена как основная')
        if set_group == {''}:
            CQT.msgbox(f'{set_prof} не образуют группу учета в БД ')

        set_prof = set()
        for prof in list(self.DICT_PROFESSIONS_NAME.keys()):
            if self.DICT_PROFESSIONS_NAME[prof]['Группа_в_распред'] != "" and \
                    self.DICT_PROFESSIONS_NAME[prof]['Группа_в_распред_блок'] == 0:
                if self.DICT_PROFESSIONS_NAME[prof]['Группа_в_распред'] in set_group:
                    set_prof.add(prof)
        spis_prof = sorted(list(set_prof))

        for prof in spis_prof:
            self.ui.cmb_prof_rasp.addItem(prof)
        fl_open_fr_otk = self.is_nar_for_otk(dict_row['Операции'])
        if fl_open_fr_otk and autsource == 0:
            list_nar = self.get_list_last_base_nar(dict_row['Номер_мк'], dict_row['Пномер'])
            self.ui.lbl_nnar_for_control.setText(', '.join([str(_) for _ in list_nar]))
            set_users = set()

            for nom_nar_empl in list_nar:
                empl_nar = CMS.Naryads(nom_nar_empl, self.db_naryd, self.DICT_DOLGN_ETAP, self.bd_users,
                                       self.DICT_EMPLOEE_FULL_WITH_DEL)
                if empl_nar.ФИО != '':
                    set_users.add((empl_nar.ФИО, empl_nar.Заводской_комплект))
                if empl_nar.ФИО2 != '':
                    set_users.add((empl_nar.ФИО2, empl_nar.Заводской_комплект))
            list_empl = [{'Чек': 0, 'ФИО': _[0], 'Комплект': _[1]} for _ in set_users]
            CQT.clear_tbl(self.ui.tbl_list_empl_for_kontr)
            CQT.fill_wtabl(list_empl, self.ui.tbl_list_empl_for_kontr, {}, 400,
                           list_column_widths=CMS.load_column_widths(self, self.ui.tbl_list_empl_for_kontr))
            for i in range(len(list_empl)):
                CQT.add_check_box(self.ui.tbl_list_empl_for_kontr, i, 0,
                                  conn_func_checked_row_col=self.select_empl_for_kontr)
            self.ui.fr_otk.setHidden(False)
            # fill_cmb_empl_for_otk(self,get_lust_empl_from_mk(self,nom_mk))
        self.ui.le_nom_compl.setText('')

    @CQT.onerror
    def select_empl_for_kontr(self, checked, row, col, *args):
        pass
        tbl = self.ui.tbl_list_empl_for_kontr
        if checked:
            tbl.item(row, col).setText('1')
        else:
            tbl.item(row, col).setText('0')

    @CQT.onerror
    def edit_check_vneplan(self, *args):

        if not CMS.user_access(self.db_naryd, 'создание_корректировка_подтвердить_внеплан',
                               CMS.name_by_empl_c(self.glob_login)):
            return
        tbl = self.ui.tbl_red_zhur
        if tbl.currentRow() == -1:
            return
        nk_vneplan = CQT.num_col_by_name_c(tbl, 'Внеплан')
        vneplan_status = tbl.item(tbl.currentRow(), nk_vneplan).text()

        nk_nom_nar = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_nar = tbl.item(tbl.currentRow(), nk_nom_nar).text()

        if vneplan_status == '0':
            CQT.msgbox(f'Наряд {nom_nar} не является внеплановым')
            return

        vneplan_val = CSQ.custom_request_c(self.db_naryd,
                                           f"""SELECT Внеплан FROM naryad WHERE Пномер == {int(nom_nar)}""",
                                           one=True)
        if vneplan_val[-1][0] == 1:
            new_status = 2
        else:
            new_status = 1
        custom_request_c = f'''UPDATE naryad SET Внеплан = {new_status} WHERE Пномер == {int(nom_nar)}'''
        CSQ.custom_request_c(self.db_naryd, custom_request_c)

        tbl.item(tbl.currentRow(), nk_vneplan).setText(str(new_status))

    @CQT.onerror
    def edit_check_naruad(self, *args):
        # if not CMS.user_access(self.db_naryd, 'создание_корректировка_подтвердить_наряд',
        #                       CMS.name_by_empl_c(self.glob_login)):
        #    return

        tbl = self.ui.tbl_red_zhur
        if tbl.currentRow() == -1:
            return
        nk_nom_nar = CQT.num_col_by_name_c(tbl, 'Пномер')
        nk_nom_mk = CQT.num_col_by_name_c(tbl, 'Номер_мк')
        nk_nom_pr = CQT.num_col_by_name_c(tbl, 'Номер_проекта')
        nk_zadanie = CQT.num_col_by_name_c(tbl, 'Задание')
        nk_fvrem = CQT.num_col_by_name_c(tbl, 'Фвремя')
        nk_fvrem2 = CQT.num_col_by_name_c(tbl, 'Фвремя2')
        nom_nar = tbl.item(tbl.currentRow(), nk_nom_nar).text()
        nom_mk = int(tbl.item(tbl.currentRow(), nk_nom_mk).text())
        nom_pr = tbl.item(tbl.currentRow(), nk_nom_pr).text()
        zadanie = tbl.item(tbl.currentRow(), nk_zadanie).text()
        fvrem = F.valm(tbl.item(tbl.currentRow(), nk_fvrem).text())
        fvrem2 = F.valm(tbl.item(tbl.currentRow(), nk_fvrem2).text())
        summ_fvrem = round(fvrem + fvrem2, 1)
        nk_primech = CQT.num_col_by_name_c(tbl, 'Примечание')
        primech = tbl.item(tbl.currentRow(), nk_primech).text()

        if not CMS.check_execution_previous_operations(self, nom_nar, check_by_vip=False):
            CQT.msgbox(f'по наряду {nom_nar} не выполнены требования маршрута, работа ЗАБЛОКИРОВАНА')
            return
        if not CQT.msgboxgYN(f'Подтверждаю, что наряд №{nom_nar} выполнен качественно и в полном объеме'):
            return

        rez = self.check_podtv_naruad(int(nom_nar))
        if rez:
            CQT.msgbox(f'Наряд №{nom_nar} уже подтвержден')
            self.load_table_korr_naruad()
            return

        rez = self.check_zaversh_naruad(int(nom_nar))
        if rez == False:
            CQT.msgbox(f'Наряд №{nom_nar} еще не завершен всеми работниками, подтверждение не возможно')
            self.load_table_korr_naruad()

            return
        if nom_pr == 'ПРОСТОЙ' and zadanie == 'ПРОСТОЙ':
            if primech.strip().lower() == 'прочее' or primech.strip() == '':
                CQT.msgbox('Не указана причина в примечании')
                return
            custom_request_c = f'''UPDATE naryad SET Подтвержд_вып = 1, Подтвержд_вып_дата = "{F.now()}", 
            Подтвержд_вып_фио = "{self.glob_ima}", Твремя = {summ_fvrem} WHERE Пномер == {int(nom_nar)}'''
        else:
            custom_request_c = f'''UPDATE naryad SET Подтвержд_вып = 1, Подтвержд_вып_дата = "{F.now()}", 
            Подтвержд_вып_фио = "{self.glob_ima}" WHERE Пномер == {int(nom_nar)}'''
        CSQ.custom_request_c(self.db_naryd, custom_request_c)


        CQT.msgbox(f'Наряд №{nom_nar} успешно подтвержден')
        self.load_table_korr_naruad()
        self.load_mk()

    @CQT.onerror
    def edit_delete_naruad(self, *args):
        if not CMS.user_access(self.db_naryd, 'создание_корректировка_удалить_наряд',
                               CMS.name_by_empl_c(self.glob_login)):
            return
        tbl = self.ui.tbl_red_zhur
        if tbl.currentRow() == -1:
            return
        nk_nom_nar = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_nar = tbl.item(tbl.currentRow(), nk_nom_nar).text()
        if not CQT.msgboxgYN(f'Точно удалить наряд №{nom_nar} ?'):
            return
        rez = self.check_nenachat_naruad(int(nom_nar))
        if rez == False:
            CQT.msgbox(f'Наряд №{nom_nar} уже начат, корректировка невозможна')
            self.load_table_korr_naruad()
            return
        custom_request_c = f'''DELETE FROM naryad WHERE Пномер == {int(nom_nar)}'''
        CSQ.custom_request_c(self.db_naryd, custom_request_c)
        CQT.msgbox(f'Наряд №{nom_nar} успешно удален')
        self.load_table_korr_naruad()
        self.load_mk()

    @CQT.onerror
    def edit_add_addition_fio(self, *args):
        tbl = self.ui.tbl_red_zhur
        row = CQT.get_dict_line_form_tbl(tbl)
        if len(row) == 0:
            CQT.msgbox(f'Не выбрана строка')
            return
        if not CMS.user_access(self.db_naryd, 'создание_корректировка_удаление_начатых_нарядов', self.glob_ima):
            return
        s_num_nar = int(row['Пномер'])
        nar = CMS.Naryads(s_num_nar, self.db_naryd, self.DICT_DOLGN_ETAP, self.bd_users,
                          self.DICT_EMPLOEE_FULL_WITH_DEL)
        if nar.is_month_closing_block():
            CQT.msgbox(f'Наряд был зафиксирован в предыдущем отчетном периоде. Корректировка не возможна')
            return
        if nar.count_users() != 1:
            CQT.msgbox(f'Для добавления второго, в наряде должен быть уже 1 человек')
            return

        list_msgs = []
        nar.get_mk(self.db_resxml)

        fl_fio_recalc = False
        if nar.ФИО == "":
            fl_fio_recalc = nar.ФИО2
        if nar.ФИО2 == "":
            fl_fio_recalc = nar.ФИО
        if fl_fio_recalc == False:
            return
        if fl_fio_recalc not in self.DICT_EMPLOEE_FULL_WITH_DEL:
            CQT.msgbox(f'{fl_fio_recalc} не найден в БД')
            return
        podr = self.DICT_EMPLOEE_FULL_WITH_DEL[fl_fio_recalc]['Подразделение']
        if podr == '':
            CQT.msgbox(f'для {fl_fio_recalc} не найдено подразделение')
            return
        list_users = [{'ФИО': k, 'Должность': _['Должность']} for k, _ in self.DICT_EMPLOEE_FULL.items() if
                      _['Подразделение'] == podr and k != '']
        user_data = CQT.msgboxg_get_table(self, 'Выбор работника', F.sort_by_column_c(list_users, 'ФИО'))
        if user_data == False:
            return
        fio_add = user_data['ФИО']
        if not CQT.msgboxgYN(f'Добавить в наряд №{nar.Пномер} "{fio_add}" в пару к "{fl_fio_recalc}"'):
            return

        if nar.ФИО == "":
            nar.ФИО = fio_add
        if nar.ФИО2 == "":
            nar.ФИО2 = fio_add

        dict_date_norm = dict()
        jur = CMS.Jurnal_nar(self.db_naryd, nar.Пномер, fl_fio_recalc)
        for row in jur.rows:
            if row['Подытог_нормы'] != '':
                dict_date_norm[row['Пномер']] = row['Подытог_нормы']

        nar.Распред_ФИО = self.glob_ima
        nar.ФИО_для_ОТК = ''
        nar.ФИО_для_ОТК_от_мастера = ''

        nar.Подтвержд_вып = 0
        nar.Подтвержд_вып_дата = ""
        nar.Подтвержд_вып_фио = ""
        nar.recalc_tvrem()
        nar.recalc_astronom_time(self.DICT_OPER_NAME)

        nar.recalc_jur_n_time(fl_fio_recalc)

        jur = CMS.Jurnal_nar(self.db_naryd, nar.Пномер, fl_fio_recalc)
        list_date_norm = []
        for row in jur.rows:
            if row['Подытог_нормы'] != '':
                if row['Пномер'] in dict_date_norm:
                    list_date_norm.append(
                        f"""За {F.datetostr(F.strtodate(row['Дата']), '%d.%m.%Y')}\n    было {dict_date_norm[row['Пномер']]} минут\n    стало {row['Подытог_нормы']} минут""")

        str_list_date_norm = "\n".join(list_date_norm)
        msg = f"""Добавлен в наряд {nar.Пномер} в помощь {fio_add}\n. Поэтому для {fl_fio_recalc} по {nar.mk.Номер_заказа} {nar.mk.Номер_проекта} были
                    пересчитаны строки:\n{str_list_date_norm}\n\n Необходимо проверить и откорректировать трудозатраты в 1С"""
        list_msgs.append(msg)
        for msg in list_msgs:
            # CMS.send_info_mk_b24(self, msg, 'chat41228')
            CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
        CQT.msgbox(f'Успешно')

    @CQT.onerror
    def edit_clear_fio_and_jur(self, *args):
        tbl = self.ui.tbl_red_zhur
        row = CQT.get_dict_line_form_tbl(tbl)
        if len(row) == 0:
            return
        if not CMS.user_access(self.db_naryd, 'создание_корректировка_удаление_начатых_нарядов', self.glob_ima):
            return
        s_num_nar = int(row['Пномер'])
        nar = CMS.Naryads(s_num_nar, self.db_naryd, self.DICT_DOLGN_ETAP, self.bd_users,
                          self.DICT_EMPLOEE_FULL_WITH_DEL)
        fl = False
        list_msgs = []

        nar.get_mk(self.db_resxml)
        if nar.ФИО:
            if CQT.msgboxgYN(f'Очистить журнал и ФИО для {nar.ФИО}'):
                jur = CMS.Jurnal_nar(self.db_naryd, nar.Пномер, nar.ФИО)
                if len(jur.rows):
                    if nar.is_month_closing_block():
                        CQT.msgbox(f'Наряд был зафиксирован в предыдущем отчетном периоде. Корректировка не возможна')
                        return
                list_date_norm = []
                for row in jur.rows:
                    if row['Подытог_нормы'] != '':
                        list_date_norm.append(
                            f"""За {F.datetostr(F.strtodate(row['Дата']), '%d.%m.%Y')} - {row['Подытог_нормы']} минут""")
                jur.delete_all_rows()
                str_list_date_norm = "\n".join(list_date_norm)
                fl = True
                msg = f"""Для {nar.ФИО} по {nar.mk.Номер_заказа} {nar.mk.Номер_проекта} наряд {nar.Пномер} были {self.glob_login} 
                удалены строки:\n{str_list_date_norm}\n\n Необходимо откорректировать трудозатраты в 1С"""
                list_msgs.append(msg)
                nar.ФИО = ''
                nar.Фвремя = ''
        if nar.ФИО2:
            if CQT.msgboxgYN(f'Очистить журнал и ФИО для {nar.ФИО2}'):
                jur = CMS.Jurnal_nar(self.db_naryd, nar.Пномер, nar.ФИО2)
                if len(jur.rows):
                    if nar.is_month_closing_block():
                        CQT.msgbox(f'Наряд был зафиксирован в предыдущем отчетном периоде. Корректировка не возможна')
                        return
                list_date_norm = []
                for row in jur.rows:
                    if row['Подытог_нормы'] != '':
                        list_date_norm.append(
                            f"""За {F.datetostr(F.strtodate(row['Дата']), '%d.%m.%Y')} - {row['Подытог_нормы']} минут""")
                jur.delete_all_rows()
                str_list_date_norm = "\n".join(list_date_norm)
                fl = True
                msg = f"""Для {nar.ФИО2} по {nar.mk.Номер_заказа} {nar.mk.Номер_проекта} наряд {nar.Пномер} были {self.glob_login} 
                 удалены строки:\n{str_list_date_norm}\n\n Необходимо откорректировать трудозатраты в 1С"""
                list_msgs.append(msg)
                nar.ФИО2 = ''
                nar.Фвремя2 = ''
        if fl:
            if nar.ФИО == '' and nar.ФИО2 == '':
                nar.Распред_ФИО = ''
                nar.Распред_дата = ""
                nar.ФИО_для_ОТК = ''
                nar.ФИО_для_ОТК_от_мастера = ''
            nar.Подтвержд_вып = 0
            nar.Подтвержд_вып_дата = ""
            nar.Подтвержд_вып_фио = ""
            nar.recalc_tvrem()
            nar.recalc_astronom_time(self.DICT_OPER_NAME)
            for msg in list_msgs:
                # CMS.send_info_mk_b24(self, msg, 'chat41228')
                CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
            CQT.msgbox(f'Успешно')

    @CQT.onerror
    def edit_clear_fio(self, *args):
        # if not CMS.user_access(self.db_naryd,'создание_корректировка_удалить_ФИО',CMS.name_by_empl_c(self.glob_login)):
        #    return
        tbl = self.ui.tbl_red_zhur
        if tbl.currentRow() == -1:
            return
        nk_nom_nar = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_nar = tbl.item(tbl.currentRow(), nk_nom_nar).text()
        if not CQT.msgboxgYN(f'Точно удалить ФИО исполнителей из наряда №{nom_nar} ?'):
            return
        rez = self.check_nenachat_naruad(int(nom_nar))
        if rez == False:
            CQT.msgbox(f'Наряд №{nom_nar} уже начат, корректировка невозможна')
            self.load_table_korr_naruad()
            return
        nk_fio = CQT.num_col_by_name_c(tbl, 'ФИО')
        nk_fio2 = CQT.num_col_by_name_c(tbl, 'ФИО2')
        nk_tvrem = CQT.num_col_by_name_c(tbl, 'Твремя')
        if tbl.item(tbl.currentRow(), nk_fio).text() != "" and tbl.item(tbl.currentRow(), nk_fio2).text() != "":
            tvrem = F.valm(tbl.item(tbl.currentRow(), nk_tvrem).text()) * 2
        else:
            tvrem = F.valm(tbl.item(tbl.currentRow(), nk_tvrem).text())

        custom_request_c = f'''UPDATE naryad SET ФИО="", ФИО2="", ФИО2="", Распред_дата ="", Распред_ФИО ="", Твремя={tvrem}  WHERE Пномер == {int(nom_nar)}'''

        CSQ.custom_request_c(self.db_naryd, custom_request_c)
        CQT.msgbox(f'Наряд №{nom_nar} успешно очищен')
        nar = CMS.Naryads(int(nom_nar), self.db_naryd)
        nar.recalc_astronom_time(self.DICT_OPER_NAME)
        self.load_table_korr_naruad()

    @CQT.onerror
    def check_podtv_naruad(self, nom_nar: int, conn='', cur=''):
        custom_request_c = f'''SELECT 
             naryad.Подтвержд_вып
         FROM naryad WHERE naryad.Пномер == {nom_nar}'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c, rez_dict=True, one=True)
        if rez['Подтвержд_вып'] == 1:
            return True
        return False

    @CQT.onerror
    def check_zaversh_naruad(self, nom_nar: int, conn='', cur=''):
        custom_request_c = f'''SELECT 
             naryad.ФИО, naryad.Фвремя, naryad.ФИО2, naryad.Фвремя2, naryad.Твремя
         FROM naryad WHERE naryad.Пномер == {nom_nar}'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c, rez_dict=True, one=True)
        if rez['ФИО'] == "" and rez['ФИО2'] == "":
            return False
        fl_zav = True
        if rez['ФИО'] != "":
            if rez['Фвремя'] == '':
                fl_zav = False
        if rez['ФИО2'] != "":
            if rez['Фвремя2'] == '':
                fl_zav = False
        return fl_zav

    @CQT.onerror
    def check_nenachat_naruad(self, nom_nar: int):
        custom_request_c = f'''SELECT jurnal.Пномер
     FROM jurnal WHERE jurnal.Номер_наряда == {nom_nar}'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c)
        if len(rez) > 1:
            return False
        return True

    @CQT.onerror
    def load_table_korr_naruad(self, close_mk=True):
        if self.glob_login == '':
            return

        if close_mk:
            custom_request_c = f'''SELECT         
        CASE WHEN знпр.№проекта IS NOT NULL 
       THEN знпр.№проекта 
       ELSE mk.Номер_проекта 
       END AS Номер_проекта, 
        
        
        CASE WHEN знпр.№ERP IS NOT NULL 
       THEN знпр.№ERP 
       ELSE mk.Номер_заказа 
       END AS Номер_заказа, 
        naryad.Пномер, naryad.Дата, naryad.Автор, naryad.Номер_мк, naryad.Внеплан, naryad.Коэфф_сложности,
naryad.Компл_ФИО, naryad.Задание, naryad.Примечание, naryad.Опер_колво, naryad.Компл_Дата, naryad.Компл_номер_тара, naryad.Компл_адрес,
 naryad.ФИО, naryad.Фвремя, naryad.ФИО2, naryad.Фвремя2, naryad.Твремя, naryad.Подтвержд_вып, naryad.Подтвержд_вып_дата , naryad.Подтвержд_вып_фио, naryad.month_closing_block as "Блок по периоду"  
  FROM naryad 
   INNER JOIN mk ON mk.Пномер = naryad.Номер_мк 
   LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
   LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
    WHERE  plan.poki = {self.place.poki}  AND mk.Статус != "Закрыта" or 
    (naryad.Внеплан == {self.place.КодыНарядов.Простой} and datetime(naryad.Дата) >= datetime("{F.date_add_days(F.now(), -60)}")); '''
        else:
            custom_request_c = f'''SELECT         CASE WHEN знпр.№проекта IS NOT NULL 
       THEN знпр.№проекта 
       ELSE mk.Номер_проекта 
       END AS Номер_проекта, 
        
        
        CASE WHEN знпр.№ERP IS NOT NULL 
       THEN знпр.№ERP 
       ELSE mk.Номер_заказа 
       END AS Номер_заказа, 
        naryad.Пномер, naryad.Дата, naryad.Автор, naryad.Номер_мк, naryad.Внеплан, naryad.Коэфф_сложности,
            naryad.Компл_ФИО, naryad.Задание, naryad.Примечание, naryad.Операции, naryad.Опер_колво, naryad.Компл_Дата, naryad.Компл_номер_тара, naryad.Компл_адрес,
             naryad.ФИО, naryad.Фвремя, naryad.ФИО2, naryad.Фвремя2, naryad.Твремя, naryad.Подтвержд_вып, naryad.Подтвержд_вып_дата, naryad.Подтвержд_вып_фио, naryad.month_closing_block as "Блок по периоду",  jurnal.Дата as Дата_журнал, jurnal.ФИО, jurnal.Статус, jurnal.Примечание
              FROM naryad 
              JOIN mk ON mk.Пномер = naryad.Номер_мк 
              INNER JOIN jurnal ON jurnal.Номер_наряда = naryad.Пномер 
              LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
              LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
            LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
              
              WHERE  plan.poki = {self.place.poki}  AND jurnal.Статус == 'Завершен' or naryad.Внеплан == {self.place.КодыНарядов.Простой}
              ; '''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c, attach_dbs=(self.db_kplan))
        edit_columns = {F.num_col_by_name_in_hat_c(rez, 'Коэфф_сложности'), F.num_col_by_name_in_hat_c(rez, 'Твремя'),
                        F.num_col_by_name_in_hat_c(rez, 'Примечание')}
        CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_red_zhur, isp_hat_c=True, separ='', select_last_row=False,
                             set_editeble_col_nomera=edit_columns)
        CMS.load_column_widths(self, self.ui.tbl_red_zhur)
        CMS.fill_filtr_c(self, self.ui.tbl_red_zhur_filtr, self.ui.tbl_red_zhur, hidden_scroll=True)

        CQT.color_cell_wtable_c(self.ui.tbl_red_zhur, 'Внеплан', '', '2', 200, 240, 200)
        CQT.color_cell_wtable_c(self.ui.tbl_red_zhur, 'Внеплан', '', '1', 240, 200, 200)

    @CQT.onerror
    def edit_red_zhur_koef_sl(self, r, c):
        tbl = self.ui.tbl_red_zhur

        def return_old_val(r, c, val):
            tbl.blockSignals(True)
            tbl.item(r, c).setText(str(val))
            tbl.blockSignals(False)

        def access_change_koef_sl_type_mk(self, nom_mk: int, koef_user, old_koef_user):
            query = CSQ.custom_request_c(self.db_naryd,
                                         f"""SELECT Тип, Тип_доработки FROM mk WHERE Пномер = {nom_mk}""", one=True,
                                         rez_dict=True)
            if query == None or query == False:
                CQT.msgbox(f'Ошибка расчета коэффициента сложности "тип" в МК {nom_mk}')
                return False
            if len(query) > 0:
                if query['Тип'] == 2 or query['Тип'] == 5:
                    if koef_user > old_koef_user:
                        CQT.msgbox(f'Выставлять повышенный коэффициент за брак не правильно')
                        return False
            if koef_user > old_koef_user and koef_user > 1:
                CQT.msgbox(f'Выставлять повышенный коэффициент через СЗ с обоснованием и с указанием номеров нарядов')
                return False
            return True

        # if tbl.hasFocus() == False:
        #    return
        row = CQT.get_dict_line_form_tbl(tbl, r)

        nom_mk = int(row['Номер_мк'])
        nom_nar = int(row['Пномер'])
        if c == CQT.num_col_by_name_c(tbl, 'Коэфф_сложности'):
            old_koef_user = CSQ.custom_request_c(self.db_naryd,
                                                 f"""SELECT Коэфф_сложности FROM naryad WHERE Пномер == {nom_nar}""",
                                                 rez_dict=True, one=True)['Коэфф_сложности']

            if F.is_numeric(row['Коэфф_сложности']) == False:
                CQT.msgbox(f'Введено не число')

                return_old_val(r, c, str(old_koef_user))
                return

            koef_user = float(row['Коэфф_сложности'])

            if koef_user != old_koef_user:

                if not CMS.user_access(self.db_naryd, 'создание_корректировка_подтвердить_внеплан',
                                       CMS.name_by_empl_c(self.glob_login)):
                    return_old_val(r, c, str(old_koef_user))
                    return

                if not access_change_koef_sl_type_mk(self, nom_mk, koef_user, old_koef_user):
                    return_old_val(r, c, str(old_koef_user))
                    return

                rez = CSQ.custom_request_c(self.db_naryd, f"""UPDATE naryad SET Коэфф_сложности 
                = {koef_user} WHERE Пномер == {nom_nar}""")

        if c == CQT.num_col_by_name_c(tbl, 'Твремя'):
            old_time = CSQ.custom_request_c(self.db_naryd,
                                            f"""SELECT Твремя FROM naryad WHERE Пномер == {nom_nar}""",
                                            rez_dict=True, one=True)
            if not CMS.user_access(self.db_naryd, 'создание_корректировка_норма_внеплан',
                                   CMS.name_by_empl_c(self.glob_login)) or row['Задание'] == 'ПРОСТОЙ':
                return_old_val(r, c, str(old_time['Твремя']))
                return

            if F.is_numeric(row['Твремя']) == False:
                rez = CSQ.custom_request_c(self.db_naryd,
                                           f"""SELECT Твремя FROM naryad WHERE Пномер == {nom_nar}""",
                                           rez_dict=True, one=True)
                return_old_val(r, c, str(old_time['Твремя']))
                CQT.msgbox(f'Введено не число')
                return

            rez = CSQ.custom_request_c(self.db_naryd, f"""UPDATE naryad SET Твремя 
            = {float(row['Твремя'])} , Опер_время 
            = {float(row['Твремя'])} WHERE 
            Пномер == {nom_nar}""")

        if c == CQT.num_col_by_name_c(tbl, 'Примечание'):

            if not CMS.user_access(self.db_naryd, 'создание_корректировка_подтвердить_наряд',
                                   CMS.name_by_empl_c(self.glob_login)):
                rez = CSQ.custom_request_c(self.db_naryd,
                                           f"""SELECT Примечание FROM naryad WHERE Пномер == {nom_nar}""",
                                           rez_dict=True, one=True)
                return_old_val(r, c, str(rez['Примечание']))
                return

            rez = CSQ.custom_request_c(self.db_naryd, f"""UPDATE naryad SET Примечание 
            = "{row['Примечание']}" WHERE 
            Пномер == {nom_nar}""")

    @CQT.onerror
    def load_tbl_vibor_assoc_proste_info(self, type_nar):

        date_obj = F.start_end_dates_c(vid='m', format_out="")[0]
        date_obj = F.add_months(date_obj, -1)
        date_str = F.datetostr(date_obj)
        self.ui.lbl_nom_nar_assoc_prost_1.setText('')
        self.ui.lbl_nom_nar_assoc_prost_2.setText('')

        if type_nar == 'prost':
            query = f"""SELECT naryad.Пномер, naryad.Дата, naryad.ФИО, "" as Должность, naryad.Фвремя,
             naryad.Примечание, naryad.Подтвержд_вып, 
            naryad.Подтвержд_вып_дата, naryad.Подтвержд_вып_фио FROM naryad  INNER JOIN mk ON mk.Пномер = naryad.Номер_мк WHERE 
             naryad.Подтвержд_вып_дата != "" AND naryad.Внеплан = 3 and (mk.Дата_завершения = "" and mk.Статус = "Открыта"  or mk.Пномер =0);"""
            self.ui.lbl_nom_nar_assoc_prost_1.setEnabled(True)
            self.ui.lbl_nom_nar_assoc_prost_2.setEnabled(True)
            rez = CSQ.custom_request_c(self.db_naryd, query, rez_dict=True)
            for i in range(len(rez)):
                if rez[i]['ФИО'] in self.DICT_EMPLOEE:
                    rez[i]['Должность'] = self.DICT_EMPLOEE[rez[i]['ФИО']]
                else:
                    rez[i]['Должность'] = ''

        else:
            query = f"""SELECT naryad.Пномер,naryad.Дата,naryad.Твремя, naryad.ФИО, "" as Должность, 
            naryad.Фвремя, naryad.ФИО2, "" as Должность2, naryad.Фвремя2, naryad.Примечание, naryad.Подтвержд_вып, 
                        naryad.Подтвержд_вып_дата, naryad.Подтвержд_вып_фио FROM naryad 
                        INNER JOIN mk ON mk.Пномер = naryad.Номер_мк WHERE 
                         naryad.Подтвержд_вып_дата != "" AND naryad.Внеплан = 0 and mk.Дата_завершения = "" and mk.Статус = "Открыта";"""
            self.ui.lbl_nom_nar_assoc_prost_1.setEnabled(False)
            self.ui.lbl_nom_nar_assoc_prost_2.setEnabled(False)
            rez = CSQ.custom_request_c(self.db_naryd, query, rez_dict=True)
            for i in range(len(rez)):
                if rez[i]['ФИО'] in self.DICT_EMPLOEE:
                    rez[i]['Должность'] = self.DICT_EMPLOEE[rez[i]['ФИО']]
                else:
                    rez[i]['Должность'] = ''
                if rez[i]['ФИО2'] in self.DICT_EMPLOEE:
                    rez[i]['Должность2'] = self.DICT_EMPLOEE[rez[i]['ФИО2']]
                else:
                    rez[i]['Должность2'] = ''

        CQT.fill_wtabl(rez, self.ui.tbl_vibor_assoc_prost, min_width_col=15, height_row=20, auto_type=False,
                       list_column_widths=CMS.load_column_widths(self, self.ui.tbl_vibor_assoc_prost))
        CMS.fill_filtr_c(self, self.ui.tbl_filtr_vibor_assoc_prost, self.ui.tbl_vibor_assoc_prost, hidden_scroll=True)

    @CQT.onerror
    def tbl_out_select_row(self, *args):
        row_prost = CQT.get_dict_line_form_tbl(self.ui.tbl_vibor_assoc_prost,
                                               self.ui.tbl_vibor_assoc_prost.currentRow())
        nom_prost = row_prost['Пномер']
        if self.ui.rb_assoc_prost_1.isChecked():
            self.ui.lbl_nom_nar_assoc_prost_1.setText(str(nom_prost))
        if self.ui.rb_assoc_prost_2.isChecked():
            self.ui.lbl_nom_nar_assoc_prost_2.setText(str(nom_prost))

    @CQT.onerror
    def vibor_assoc_prost_plan(self, *args):
        if self.type_assoc_prost_plan == 'plan':
            self.vibor_assoc_plan()

        if self.type_assoc_prost_plan == 'prost':
            self.vibor_assoc_prost()

    def vibor_assoc_plan(self):
        def check_vibor_assoc_prost(obj_nar_new, obj_nar_old):
            list_dolgn = CQT.list_from_cmb_c(self.ui.cmb_prof_rasp)
            if row_nar_new == dict():
                CQT.msgbox(f'Не выбран новый наряд')
                return False
            if obj_nar_old.ФИО != '':
                if self.DICT_EMPLOEE[obj_nar_old.ФИО] not in list_dolgn:
                    CQT.msgbox(f'Должность наряда {obj_nar_old.ФИО} не соответствует новому наряду')
                    return False
            if obj_nar_old.ФИО2 != '':
                if self.DICT_EMPLOEE[obj_nar_old.ФИО2] not in list_dolgn:
                    CQT.msgbox(f'Должность наряда {obj_nar_old.ФИО2} не соответствует новому наряду')
                    return False
            jurnal_row_nar = CSQ.custom_request_c(self.db_naryd,
                                                  f"""SELECT * FROM jurnal WHERE Номер_наряда = {obj_nar_new.Пномер}""",
                                                  rez_dict=True)
            if len(jurnal_row_nar) > 0:
                CQT.msgbox(f'плановый наряд не должен быть в работе')
                return False
            return True

        row_nar_new = CQT.get_dict_line_form_tbl(self.ui.tbl_vibor_nar_rasp, self.ui.tbl_vibor_nar_rasp.currentRow())
        row_nar_old = CQT.get_dict_line_form_tbl(self.ui.tbl_vibor_assoc_prost,
                                                 self.ui.tbl_vibor_assoc_prost.currentRow())
        if row_nar_old == dict() or row_nar_new == dict():
            CQT.msgbox(f'Не выбраны наряды')
            return
        obj_nar_new = CMS.Naryads(int(row_nar_new['Пномер']), self.db_naryd)
        obj_nar_old = CMS.Naryads(int(row_nar_old['Пномер']), self.db_naryd)
        if not check_vibor_assoc_prost(obj_nar_new, obj_nar_old):
            return

        fio = ''
        fio2 = ''
        ftime = ''
        ftime2 = ''
        podtv = ''
        podtv_date = ''
        podtv_fio = ''
        respred_fio = ''
        t_time = obj_nar_new.Твремя
        if obj_nar_old.count_users() == 1:
            fio = obj_nar_old.ФИО
            ftime = obj_nar_old.Фвремя
            podtv = obj_nar_old.Подтвержд_вып
            podtv_date = obj_nar_old.Подтвержд_вып_дата
            podtv_fio = obj_nar_old.Подтвержд_вып_фио
            respred_fio = obj_nar_old.Подтвержд_вып_фио
        else:

            fio = obj_nar_old.ФИО
            fio2 = obj_nar_old.ФИО2
            ftime = obj_nar_old.Фвремя
            ftime2 = obj_nar_old.Фвремя2
            podtv = obj_nar_old.Подтвержд_вып
            podtv_date = obj_nar_old.Подтвержд_вып_дата
            podtv_fio = obj_nar_old.Подтвержд_вып_фио
            respred_date = obj_nar_old.Распред_дата
            respred_fio = obj_nar_old.Подтвержд_вып_фио
            t_time = round(t_time / 2, 2)

        if not CQT.msgboxgYN(f'Произойдет слияние наряда {obj_nar_new.Пномер} с нарядом'
                             f' {obj_nar_old.Пномер} \n в результате чего,'
                             f' наряд {obj_nar_old.Пномер} будen УДАЛЕН, история работ и примечания будет переведена '
                             f' на плановый наряд.\n\n Продолжить?'):
            return

        # .подмена в журнале
        CSQ.custom_request_c(self.db_naryd, f"""UPDATE jurnal SET Номер_наряда = {obj_nar_new.Пномер} 
            WHERE Номер_наряда = {obj_nar_old.Пномер}""")
        # .перенос данные в наряд
        tmp_row = [fio, fio2, ftime, ftime2, podtv, podtv_date, podtv_fio, respred_fio, respred_date, t_time]
        CSQ.custom_request_c(self.db_naryd, f"""UPDATE naryad SET  (ФИО,ФИО2, Фвремя, Фвремя2, Подтвержд_вып,
         Подтвержд_вып_дата, Подтвержд_вып_фио, Распред_ФИО,Распред_дата, Твремя) 
            = ({CSQ.questions_for_mask(tmp_row)}) 
              WHERE Пномер = {obj_nar_new.Пномер}""", list_of_lists_c=[tmp_row])
        # .удаление простоя
        CSQ.custom_request_c(self.db_naryd, f"""DELETE FROM naryad WHERE Пномер = {obj_nar_old.Пномер}""")
        self.load_tbl_vibor_assoc_proste_info('plan')
        CMS.apply_filtr_c(self, self.ui.tbl_filtr_vibor_assoc_prost, self.ui.tbl_vibor_assoc_prost)
        self.select_tbl_projs_raspred()
        CMS.apply_filtr_c(self, self.ui.tbl_filtr_vibor_nar_rasp, self.ui.tbl_vibor_nar_rasp)
        CQT.msgbox(f'Удачно')

    def vibor_assoc_prost(self):
        row_nar = CQT.get_dict_line_form_tbl(self.ui.tbl_vibor_nar_rasp, self.ui.tbl_vibor_nar_rasp.currentRow())
        if self.ui.lbl_nom_nar_assoc_prost_1.text() == self.ui.lbl_nom_nar_assoc_prost_2.text():
            CQT.msgbox(f'Выбран один и тот же наряд в простоях')
            return
        dict_nar_prost = dict()
        if self.ui.lbl_nom_nar_assoc_prost_1.text() != '':
            nom_nar_prost = int(self.ui.lbl_nom_nar_assoc_prost_1.text())
            dict_nar_prost[nom_nar_prost] = CMS.Naryads(nom_nar_prost, self.db_naryd)
        if self.ui.lbl_nom_nar_assoc_prost_2.text() != '':
            nom_nar_prost = int(self.ui.lbl_nom_nar_assoc_prost_2.text())
            dict_nar_prost[nom_nar_prost] = CMS.Naryads(nom_nar_prost, self.db_naryd)

        if len(dict_nar_prost) == 0:
            CQT.msgbox(f'Не выбран наряд/ы простоя')
            return

        # row_prost = CQT.get_dict_line_form_tbl(self.ui.tbl_vibor_assoc_prost, self.ui.tbl_vibor_assoc_prost.currentRow())

        def check_vibor_assoc_prost(row_nar, row_prost):
            list_dolgn = CQT.list_from_cmb_c(self.ui.cmb_prof_rasp)
            if row_nar == dict():
                CQT.msgbox(f'Не выбран плановый наряд')
                return False
            if self.DICT_EMPLOEE[row_prost.ФИО] not in list_dolgn:
                CQT.msgbox(f'Должность наряда {row_prost.Пномер} не соответствует плановому наряду')
                return False

            jurnal_row_nar = CSQ.custom_request_c(self.db_naryd,
                                                  f"""SELECT * FROM jurnal WHERE Номер_наряда = {int(row_nar['Пномер'])}""",
                                                  rez_dict=True)
            if len(jurnal_row_nar) > 0:
                CQT.msgbox(f'плановый наряд не должен быть в работе')
                return False
            return True

        for obj_prost in dict_nar_prost.values():
            if not check_vibor_assoc_prost(row_nar, obj_prost):
                return

        fio = ''
        fio2 = ''
        ftime = ''
        ftime2 = ''
        podtv = ''
        podtv_date = ''
        podtv_fio = ''
        respred_fio = ''
        t_time = F.valm(row_nar['Твремя'])
        if len(dict_nar_prost) == 1:
            obj1 = list(dict_nar_prost.values())[0]
            fio = obj1.ФИО

            ftime = obj1.Фвремя

            podtv = obj1.Подтвержд_вып
            podtv_date = obj1.Подтвержд_вып_дата
            podtv_fio = obj1.Подтвержд_вып_фио
            respred_fio = obj1.Подтвержд_вып_фио
            respred_date = obj1.Распред_дата
        else:
            obj1, obj2 = list(dict_nar_prost.values())
            fio = obj1.ФИО
            fio2 = obj2.ФИО
            ftime = obj1.Фвремя
            ftime2 = obj2.Фвремя
            podtv = obj1.Подтвержд_вып
            podtv_date = obj1.Подтвержд_вып_дата
            podtv_fio = obj1.Подтвержд_вып_фио
            respred_fio = obj1.Подтвержд_вып_фио
            respred_date = obj1.Распред_дата
            t_time = round(F.valm(row_nar['Твремя']) / 2, 2)

        if not CQT.msgboxgYN(f'Произойдет слияние наряда {row_nar["Пномер"]} с нарядами'
                             f' {";".join([str(_) for _ in dict_nar_prost.keys()])} \n в результате чего,'
                             f' наряды на простой будут УДАЛЕНЫ, история работ и примечания будет переведена '
                             f'на плановый наряд.\n\n Продолжить?'):
            return
        for obj_prost in dict_nar_prost.values():
            # .подмена в журнале
            CSQ.custom_request_c(self.db_naryd, f"""UPDATE jurnal SET Номер_наряда = {int(row_nar['Пномер'])} 
            WHERE Номер_наряда = {obj_prost.Пномер}""")
        # .перенос данные в наряд
        tmp_row = [fio, fio2, ftime, ftime2, podtv, podtv_date, podtv_fio, respred_fio, respred_date, t_time]
        CSQ.custom_request_c(self.db_naryd, f"""UPDATE naryad SET  (ФИО,ФИО2, Фвремя, Фвремя2, Подтвержд_вып,
         Подтвержд_вып_дата, Подтвержд_вып_фио, Распред_ФИО,Распред_дата, Твремя) 
            = ({CSQ.questions_for_mask(tmp_row)}) 
              WHERE Пномер = {int(row_nar['Пномер'])}""", list_of_lists_c=[tmp_row])
        # .удаление простоя
        for obj_prost in dict_nar_prost.values():
            CSQ.custom_request_c(self.db_naryd, f"""DELETE FROM naryad WHERE Пномер = {obj_prost.Пномер}""")
        self.load_tbl_vibor_assoc_proste_info('prost')
        CMS.apply_filtr_c(self, self.ui.tbl_filtr_vibor_assoc_prost, self.ui.tbl_vibor_assoc_prost)
        self.select_tbl_projs_raspred()
        CMS.apply_filtr_c(self, self.ui.tbl_filtr_vibor_nar_rasp, self.ui.tbl_vibor_nar_rasp)
        CQT.msgbox(f'Удачно')

    def open_vibor_assoc_proste_info(self, type_nar):
        if not CMS.user_access(self.db_naryd, 'создание_распределение_подмена',
                               CMS.name_by_empl_c(self.glob_login)):
            return
        if self.ui.fr_vibor_assoc_prost.isVisible():
            self.ui.fr_vibor_assoc_prost.setHidden(True)
            self.ui.tbl_vibor_rabotn_rasp.setHidden(False)
        else:
            self.ui.fr_vibor_assoc_prost.setHidden(False)
            self.ui.tbl_vibor_rabotn_rasp.setHidden(True)
            self.type_assoc_prost_plan = type_nar
            self.load_tbl_vibor_assoc_proste_info(type_nar)

    @CQT.onerror
    def select_tbl_projs_raspred(self,*args):
        if self.glob_login == '':
            return
        tbl = self.ui.tbl_projs_raspred



        row = CQT.get_dict_line_form_tbl(tbl)
        if not row:
            return
        s_num_znpr = row['s_num']
        self.load_table_raspred_nar(int(s_num_znpr))



    @CQT.onerror
    def load_table_projects_for_raspred_nar(self):
        if self.glob_login == '':
            return
        tbl_rasp = self.ui.tbl_vibor_nar_rasp
        self.ui.fr_additions_raspr.setHidden(True)
        CQT.clear_tbl(tbl_rasp)

        tbl = self.ui.tbl_projs_raspred
        custom_request_c = f'''
                SELECT DISTINCT
                    знпр.s_num,
                    знпр.Год,
                   plan.Направление_деятельности,
                    napravl_deyat.Псевдоним as Направление,
                    знпр.№ERP,
                    знпр.№проекта,
                    знпр.Статус_поз_ЕРП,
                    знпр.Дата_отгрузки_ПУ,
                    COUNT(*) as Нарядов,
                    GROUP_CONCAT(naryad.Пномер, ";") as Номера_нарядов ,
                    знпр.Комментарий
                    
                    FROM naryad
                    LEFT JOIN mk ON mk.Пномер = naryad.Номер_мк 
                    LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
                    LEFT JOIN пл_оуп ON plan.Пномер = пл_оуп.НомПл  
                     LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
                      LEFT JOIN napravl_deyat ON napravl_deyat.Пномер == plan.Направление_деятельности 
                       WHERE plan.poki = {self.place.poki} AND знпр.Статус_поз_ЕРП != "Закрыт" and mk.Статус == "Открыта" and naryad.Компл_ФИО !="" 
                                                 and naryad.Компл_Дата !="" and naryad.ФИО == "" and naryad.ФИО2 == "" 
                    GROUP BY             
                     знпр.s_num,
                    знпр.Год,
                    знпр.№ERP,
                    знпр.№проекта,
                    знпр.Статус_поз_ЕРП,
                    знпр.Дата_отгрузки_ПУ,
                    знпр.Комментарий 
                    HAVING COUNT(*) > 0 order BY знпр.Дата_отгрузки_ПУ;'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c,  rez_dict=True, attach_dbs=(self.db_kplan))
        CQT.fill_wtabl(rez,tbl,sortingEnabled=True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl,'s_num'),True)
        tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Направление_деятельности'), True)
        CMS.fill_filtr_c(self,self.ui.tbl_filtr_projs_raspred,tbl)
        nf_Дата_отгрузки_ПУ = CQT.num_col_by_name_c(tbl, 'Дата_отгрузки_ПУ')
        nf_Статус_поз_ЕРП = CQT.num_col_by_name_c(tbl, 'Статус_поз_ЕРП')
        nf_Направление = CQT.num_col_by_name_c(tbl, 'Направление')
        clrs_10 = CMS.Color_tbl(10)
        clrs_80 = CMS.Color_tbl(80)
        clrs_50 = CMS.Color_tbl(50)
        for i, item in  enumerate(rez):
            if F.strtodate(item['Дата_отгрузки_ПУ'],"%Y-%m-%d") <= F.now(''):
                r,g,b = clrs_10.rgb
                CQT.set_color_wtab_c(tbl,i,nf_Дата_отгрузки_ПУ,r,g,b)
            if item['Статус_поз_ЕРП']  == 'КПроизводству':
                r, g, b = clrs_80.rgb
            else:
                r, g, b = clrs_50.rgb
            CQT.set_color_wtab_c(tbl, i, nf_Статус_поз_ЕРП, r, g, b)

            r, g, b = self.DICT_NAPR_DEYAT[item['Направление_деятельности']]['Цвет'].split(';')
            CQT.set_color_wtab_c(tbl, i, nf_Направление, r, g, b)

    @CQT.onerror
    def load_table_raspred_nar(self,s_num_znpr:int ):
        if self.glob_login == '':
            return
        self.ui.fr_additions_raspr.setHidden(False)
        tbl = self.ui.tbl_vibor_nar_rasp
        CQT.clear_tbl(tbl)
        self.ui.radioButton_ispoln1.setChecked(True)
        custom_request_c = f'''
                SELECT  

        CASE WHEN знпр.№проекта IS NOT NULL 
       THEN знпр.№проекта 
       ELSE mk.Номер_проекта 
       END AS Номер_проекта, 
        
        
        CASE WHEN знпр.№ERP IS NOT NULL 
       THEN знпр.№ERP 
       ELSE mk.Номер_заказа 
       END AS Номер_заказа, 
       
       
                 naryad.Пномер, naryad.Дата, naryad.Автор, "" as Этап, "" as РЦ, naryad.Номер_мк,
naryad.Внеплан, naryad.Компл_ФИО, naryad.Задание, naryad.Примечание, 
                                                 naryad.Твремя, naryad.Операции, naryad.ДСЕ_ID , naryad.Профессии, naryad.Аутсорсинг , mk.Количество AS "Кол. изделий"
                                                 FROM naryad 
                                                 INNER JOIN mk ON naryad.Номер_мк == mk.Пномер 
                                                 LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
                                                LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
                                                LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
                                                 WHERE plan.poki = {self.place.poki} and naryad.Компл_ФИО !="" 
                                                 and naryad.Компл_Дата !="" and naryad.ФИО == "" and naryad.ФИО2 == ""  and mk.Статус == "Открыта" and знпр.s_num == {s_num_znpr}'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c,  rez_dict=True,
                                   attach_dbs=(self.db_kplan))
        mk_noms = {naryad['Номер_мк'] for naryad in rez}
        if not mk_noms:
            CQT.msgbox('Нет нарядов к распределению')
            return
        mk_noms_for_sql = CSQ.prepare_list_to_tuple(mk_noms)
        mk_rows = CSQ.custom_request_c(
            self.db_resxml,
            f'SELECT mk.*, res.data, res.Номер_мк FROM res INNER JOIN mk ON mk.Пномер = res.Номер_мк WHERE mk.Пномер IN ({mk_noms_for_sql})',
            rez_dict=True,
            attach_dbs=self.db_naryd
        )
        mk_rows_by_pk = F.deploy_dict_c(mk_rows, 'Номер_мк')
        cache = {}
        for item in rez:
            operations = item['Операции'].split('|')
            dse_ids = item['ДСЕ_ID'].split('|')
            nom_mk = item['Номер_мк']
            if nom_mk not in cache:
                row_mk = mk_rows_by_pk[nom_mk]
                res = row_mk.pop('data')
                cache[nom_mk] = CMS.Marshrut_cards(
                    nom_mk=nom_mk,
                    db_mk=self.db_naryd,
                    row_from_db=row_mk,
                    load_resource=True,
                    db_resxml=self.db_resxml,
                    byte_data_res_from_db=res,
                    load_znpr=False,
                    DICT_RC_BY_CODE=self.DICT_RC
                )
            obj_mk = cache[nom_mk]
            etaps = set()
            rcs = set()
            for dse_id, operation in zip(dse_ids, operations):
                oper_num, oper_name = operation.split('$')
                etap, rc, err = obj_mk.get_etap_by_num_operation(dse_id, oper_num)
                if err is None:
                    etaps.add(etap)
                    rcs.add(rc)
            item['Этап'] = ','.join(etaps)
            item['РЦ'] = ','.join(rcs)
        self.ui.te_comment.setText('')
        CQT.fill_wtabl(rez, tbl, auto_type=False, list_column_widths=CMS.load_column_widths(self, tbl))
        nf_etap = CQT.num_col_by_name_c(tbl, 'Этап')
        col_out = CQT.num_col_by_name_c(tbl, 'Аутсорсинг')
        for i in range(tbl.rowCount()):
            is_outsource = tbl.item(i, col_out).text()
            if is_outsource == '1':
                rgb = self.DICT_RC_FULL['020201']['Цвет']
                new_rgb = F.align_colors(rgb.split(','), saturation_percent=-36, level_percent=8, sep_out='')
                CQT.set_color_row_wtab_c(tbl, i, *new_rgb)
            else:
                etap = tbl.item(i, nf_etap).text()
                if etap in self.DICT_ETAPS:
                    color = self.DICT_ETAPS[etap]['color']
                    new_rgb = F.align_colors(F.hex_to_rgb(color[1:]), saturation_percent=-36, level_percent=8, sep_out='')
                    CQT.set_color_row_wtab_c(tbl, i, *new_rgb)
        if CQT.num_col_by_name_c(tbl, 'ДСЕ_ID'):
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'ДСЕ_ID'), True)

        CMS.fill_filtr_c(self, self.ui.tbl_filtr_vibor_nar_rasp, tbl, hidden_scroll=True)
        CMS.load_column_widths(self, tbl)
        self.ui.splitter_4.setSizes([385, 1180])

    def dblclick_tbl_prosmotr_nar(self, *args):
        if self.ui.tbl_prosmotr_nar.currentColumn() == CQT.num_col_by_name_c(self.ui.tbl_prosmotr_nar,
                                                                             "Обособленная_расценка"):
            self.raschet_stoimosti_naryada()

    @CQT.onerror
    def raschet_stoimosti_naryada(self):
        if self.superuser == False:
            if not CMS.user_access(self.db_naryd, 'создание_просмотр_стоимость_по_расценке',
                                   CMS.name_by_empl_c(self.glob_login)):
                return
        row = CQT.get_dict_line_form_tbl(self.ui.tbl_prosmotr_nar)
        if row['Обособленная_расценка'] == '0':
            CQT.msgbox(f'Расценка считается только для обособленных нарядов')
            return
        koef_slog = F.valm(row['Коэфф_сложности'])
        list_time_oper = row['Опер_время'].split('|')
        list_sort_c_rab_name = row['Виды_работ'].split('|')
        summ = 0
        if len(list_time_oper) != len(list_sort_c_rab_name):
            return 0
        for i in range(len(list_sort_c_rab_name)):
            vid = list_sort_c_rab_name[i]
            time = F.valm(list_time_oper[i])
            if vid == '':
                continue
            if vid not in self.PRICES_BY_VID_RABOT:
                print(f'{vid} не в списке видов')
                continue
            stavka = self.PRICES_BY_VID_RABOT[vid]['Руб_мин']
            summ += stavka * time
        CQT.msgbox(f'На обоих! {round(summ)} руб. при коэффициенте сложности 1')
        return round(summ)

    def load_table_prosm_nar_by_year(self):
        list_years = [[str(_)] for _ in range(2021, int(F.now("%Y")) + 1)]
        list_years.insert(0, ['Год'])

        data_year = CQT.msgboxg_get_table(
            self,
            'Выбрать год создания нарядов',
            list_years,
            btn0_name='OK',
            ExtendedSelection=False #10.04.25
        )
        if data_year == False:
            return
        self.load_table_prosm_nar(data_year["Год"])

    # @F.time_of_exec_cls_func_args_c
    @CQT.progress_decorator
    @CQT.onerror
    def load_table_prosm_nar(self, year=None, hook_prog_bar=None, num_mk=None):
        hook_prog_bar.open()
        tbl = self.ui.tbl_prosmotr_nar
        if self.glob_login == '':
            return
        try:
            org_key = self.place.Организация_Key
            CMS.Naryads.check_month_block(self.db_naryd, org_key, self.DICT_EMPLOEE_FULL_WITH_DEL_ref)
        except:
            CQT.msgbox(f'Связаться с ЕРП не удалось')

        colorfull = True
        select = f"""SELECT      
           CASE WHEN знпр.№проекта IS NOT NULL 
       THEN знпр.№проекта 
       ELSE mk.Номер_проекта 
       END AS Номер_проекта, 
        
        
        CASE WHEN знпр.№ERP IS NOT NULL 
       THEN знпр.№ERP 
       ELSE mk.Номер_заказа 
       END AS Номер_заказа,  
       naryad.Пномер, naryad.Дата, naryad.Автор, naryad.Распред_дата, naryad.Распред_ФИО,
naryad.Номер_мк, mk.Статус, naryad.Внеплан, naryad.Номер_замечания_журнал, naryad.Примечание,
                                        naryad.ФИО,naryad.Фвремя,"" AS Дельта, "" AS Смена, naryad.ФИО2,naryad.Фвремя2, "" AS Дельта2,"" AS Смена_, naryad.Твремя, naryad.Норма_времени, 
naryad.Операции, naryad.Опер_колво, naryad.Опер_время, naryad.ДСЕ_ID, naryad.Коэфф_сложности, naryad.Категория_внепл, naryad.Подтвержд_вып,
             naryad.Подтвержд_вып_дата, naryad.Подтвержд_вып_фио, 
               naryad.Обособленная_расценка, naryad.ФИО_для_ОТК, naryad.month_closing_block as "Блок по периоду" 
                                         FROM naryad 
                                         INNER JOIN mk ON naryad.Номер_мк == mk.Пномер
                                         LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
                                         LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
                                        LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП """

        if num_mk != None:
            custom_request_c = f'''{select} WHERE plan.poki = {self.place.poki} AND naryad.Номер_мк = {num_mk}'''
        else:
            if year == None:
                custom_request_c = f'''{select} WHERE plan.poki = {self.place.poki} AND mk.Статус = "Открыта" OR naryad.Внеплан == {self.place.КодыНарядов.Простой} ;'''
            else:
                colorfull = False

                custom_request_c = f''' {select}  WHERE plan.poki = {self.place.poki} AND datetime(naryad.Дата) >= datetime("{year}-01-01 03:00:00") AND 
                                                               datetime(naryad.Дата) <= datetime("{year}-12-31 02:59:59") '''
        hook_prog_bar.set(0)
        hook_prog_bar.text('Получение данных')
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c, rez_dict=True, attach_dbs=(self.db_kplan))
        hook_prog_bar.set(20)
        hook_prog_bar.text('Получение данных')
        if rez == False:
            CQT.msgbox(f'БД занята, пробуй позже')
            return
        set_edit = {}
        if CMS.user_access(self.db_naryd, 'создание_просмотр_корр_внеплан_ксложн_подввып',
                           CMS.name_by_empl_c(self.glob_login), False):
            set_edit = {
                'Коэфф_сложности'
            }

        list_dicts_jur = CSQ.custom_request_c(self.db_naryd,
                                              f"""SELECT * FROM jurnal WHERE Номер_наряда IN ({CSQ.prepare_list_to_tuple([_['Пномер'] for _ in rez])})""",
                                              rez_dict=True)

        def calc_delta(self, Фвремя, ФИО, Пномер, Норма_времени, count_users, list_dicts_jur):

            if Фвремя != "":
                f_time = Фвремя
            else:
                jur = CMS.Jurnal_nar(self.db_naryd, Пномер, ФИО, list_dicts_jur=list_dicts_jur)
                zadel = jur.calc_zadel()
                poditog = jur.get_summ_poditog(True)
                f_time = zadel + poditog
                if poditog == 0:
                    return ''
            difference = round(Норма_времени / count_users - f_time, 2)
            partial = round(f_time / (Норма_времени / count_users) * 100 - 100, 2)
            return f"{difference}({partial}%)"

        hook_prog_bar.text('Расчеты')
        if year == None:
            for i in range(len(rez)):
                hook_prog_bar.set(20 + round(i / len(rez) * 50))
                if rez[i]['Статус'] != 'Открыта':
                    continue
                count_users = 0
                if rez[i]['ФИО'] != "":
                    count_users += 1
                if rez[i]['ФИО2'] != "":
                    count_users += 1
                if count_users == 0 or rez[i]['Норма_времени'] == 0:
                    continue
                if rez[i]['ФИО'] != "":
                    rez[i]['Дельта'] = calc_delta(self, rez[i]['Фвремя'], rez[i]['ФИО'], rez[i]['Пномер'],
                                                  rez[i]['Норма_времени'], count_users, list_dicts_jur)
                    if rez[i]['ФИО'] in self.DICT_EMPLOEE_FULL_WITH_DEL:
                        rez[i]['Смена'] = self.DICT_EMPLOEE_FULL_WITH_DEL[rez[i]['ФИО']]['Режим']
                if rez[i]['ФИО2'] != "":
                    rez[i]['Дельта2'] = calc_delta(self, rez[i]['Фвремя2'], rez[i]['ФИО2'], rez[i]['Пномер'],
                                                   rez[i]['Норма_времени'], count_users, list_dicts_jur)
                    if rez[i]['ФИО2'] in self.DICT_EMPLOEE_FULL_WITH_DEL:
                        rez[i]['Смена_'] = self.DICT_EMPLOEE_FULL_WITH_DEL[rez[i]['ФИО2']]['Режим']
        hook_prog_bar.set(70)
        hook_prog_bar.text('Заполнение таблицы')
        CQT.fill_wtabl(rez, tbl, set_edit, 200, 18, 25, select_last_row=True, colorful_edit=colorfull,
                       list_column_widths=CMS.load_column_widths(self, tbl))
        hook_prog_bar.set(80)
        nf_delta = CQT.num_col_by_name_c(tbl, 'Дельта')
        nf_delta2 = CQT.num_col_by_name_c(tbl, 'Дельта2')
        nf_norm_time = CQT.num_col_by_name_c(tbl, 'Норма_времени')
        nf_ftime = CQT.num_col_by_name_c(tbl, 'Фвремя')
        nf_ftime2 = CQT.num_col_by_name_c(tbl, 'Фвремя2')

        def set_col(tbl, i, nf_delta):
            val = tbl.item(i, nf_delta).text()
            if val != None and val != "" and '%)' in val:
                delta, percent = val.split('(')
                percent = percent.replace('%)', '')
                if F.is_numeric(delta) and F.valm(delta) < 0:
                    # percent = (100 - F.valm(percent)) * -1
                    percent = F.valm(percent)
                    if percent > 100:
                        percent = 100
                    color = CMS.Color_tbl(percent, True)
                    CQT.set_color_wtab_c(tbl, i, nf_delta, color.r, color.g, color.b)

        for i in range(tbl.rowCount()):
            hook_prog_bar.set(80 + round(i / tbl.rowCount() * 30))
            set_col(tbl, i, nf_delta)
            set_col(tbl, i, nf_delta2)

        # tbl.hideColumn(CQT.num_col_by_name_c(tbl, 'Операции'))
        # tbl.hideColumn(CQT.num_col_by_name_c(tbl, 'Опер_колво'))
        # tbl.hideColumn(CQT.num_col_by_name_c(tbl, 'Опер_время'))

        CMS.fill_filtr_c(self, self.ui.tbl_filtr_prosmotr_nar, tbl, hidden_scroll=True)
        CMS.load_column_widths(self, tbl)

        # self.ui.tbl_filtr_prosmotr_nar.setColumnWidth(CQT.num_col_by_name_c(tbl, 'Задание'),220)
        # tbl.setColumnWidth(CQT.num_col_by_name_c(tbl, 'Дельта'), 130)
        # tbl.setColumnWidth(CQT.num_col_by_name_c(tbl, 'Дельта2'), 130)
        self.ui.btn_apply_deladd_row_jur.setText('Применить')

    @CQT.onerror
    def edit_koeff_nar_tbl(self, row, column, *args):
        tbl = self.ui.tbl_prosmotr_nar
        if tbl.hasFocus() == True:
            if tbl.currentRow() == -1:
                return
            name = tbl.horizontalHeaderItem(column).text()
            self.edit_koeff_nar(name)

    @CQT.onerror
    def edit_koeff_nar(self, ima=''):
        if ima == '':
            return
        tbl = self.ui.tbl_prosmotr_nar
        row = tbl.currentRow()
        nk_nom_nar = CQT.num_col_by_name_c(tbl, 'Пномер')
        nk_ima = CQT.num_col_by_name_c(tbl, ima)
        if nk_nom_nar == None:
            CQT.msgbox('Не найдена колонка Пномер')
            return
        if nk_ima == None:
            CQT.msgbox(f'Не найдена колонка {ima}')
            return
        if CMS.user_access(self.db_naryd, 'создание_просмотр_корр_внеплан_ксложн_подввып',
                           CMS.name_by_empl_c(self.glob_login)):
            if F.is_numeric(tbl.item(row, nk_ima).text()) == False:
                CQT.msgbox(f'{tbl.item(row, nk_ima).text()} не число')
                return
            ima_val = F.valm(tbl.item(row, nk_ima).text())
            nom_nar = int(tbl.item(row, nk_nom_nar).text())
            custom_request_c = f'''UPDATE naryad SET {ima} = {ima_val} WHERE Пномер == {nom_nar}'''
            rez = CSQ.custom_request_c(self.db_naryd, custom_request_c)
            self.ui.tbl_prosmotr_nar.item(row, nk_ima).setText(str(ima_val))
        else:
            rez = CSQ.custom_request_c(self.db_naryd,
                                       f"""SELECT {ima} FROM naryad WHERE Пномер == {int(self.ui.tbl_prosmotr_nar.item(row, nk_nom_nar).text())}""",
                                       rez_dict=True, one=True)
            self.ui.tbl_prosmotr_nar.item(row, nk_ima).setText(str(rez[ima]))
            # self.load_table_prosm_nar()

    @CQT.onerror
    def load_table_komplekt(self):
        if self.glob_login == "":
            return
        custom_request_c = f'''SELECT         CASE WHEN знпр.№проекта IS NOT NULL 
       THEN знпр.№проекта 
       ELSE mk.Номер_проекта 
       END AS Номер_проекта, 
        
        
        CASE WHEN знпр.№ERP IS NOT NULL 
       THEN знпр.№ERP 
       ELSE mk.Номер_заказа 
       END AS Номер_заказа, 
 naryad.Пномер, naryad.Дата, naryad.Автор, 
        naryad.Номер_мк, naryad.Компл_ФИО, naryad.Компл_Дата, naryad.Компл_номер_тара, naryad.Компл_адрес, naryad.Твремя,
                                 naryad.Примечание,  naryad.ДСЕ, naryad.Операции,
                                 naryad.Опер_колво, naryad.Внеплан FROM naryad  
                                 INNER JOIN mk ON naryad.Номер_мк == mk.Пномер 
                                 LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
                                 LEFT JOIN plan ON plan.Пномер = mk.НомКплан 
                                LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
                                WHERE  plan.poki = {self.place.poki}  AND naryad.Подтвержд_вып_дата == "" and mk.Статус != "Закрыта"'''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c, attach_dbs=(self.db_kplan))
        if rez == False:
            CQT.msgbox(f'Не удалось загрузить данные попробуй еще раз')
            return
        red = {F.num_col_by_name_in_hat_c(rez, 'Компл_Дата') + 1,
               F.num_col_by_name_in_hat_c(rez, 'Компл_номер_тара') + 1}

        CQT.fill_wtabl_old_c(self, rez, self.ui.tbl_komplektovka, isp_hat_c=True, separ='', set_editeble_col_nomera=red,
                             ogr_maxshir_kol=400, select_last_row=True)
        CMS.load_column_widths(self, self.ui.tbl_komplektovka)
        CMS.fill_filtr_c(self, self.ui.tbl_filtr_komplektovka, self.ui.tbl_komplektovka, hidden_scroll=True)

        CQT.clear_tbl(self.ui.tbl_komplektovka_view)
        self.ui.lbl_kompl_info.clear()

    @CQT.onerror
    def btn_prosm_edit_time_clear_fio(self, field_name, *args):
        if '*' in self.ui.btn_apply_deladd_row_jur.text():
            CQT.msgbox(f'Необходимо применить предыдущие изменения')
            return
        tbl = self.ui.tbl_prosmotr_nar
        autor_nar = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Автор')).text()
        if not CMS.user_access(self.db_naryd, f'создание_корректировка_журнал_работ_{autor_nar}',
                               CMS.name_by_empl_c(self.glob_login)):
            return
        if tbl.currentRow() == -1:
            CQT.msgbox(f'Не выбрана запись в списке нарядов')
            return
        fio = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, field_name)).text()
        nom_nar = int(tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Пномер')).text())
        if fio == '':
            CQT.msgbox(f'{field_name} - пусто')
            return
        rez = CSQ.custom_request_c(self.db_naryd,
                                   f"""SELECT Пномер FROM jurnal WHERE Номер_наряда == {nom_nar} AND ФИО == '{fio}' """)
        if rez == False:
            CQT.msgbox(f'ОШикба загрузки бд, попробуй позже')
            return
        if len(rez) >= 2:
            CQT.msgbox(f'Нелья удалить исполнителя проводившего работы')
            return
        rez = CSQ.custom_request_c(self.db_naryd, f"""SELECT * FROM naryad WHERE Пномер = {nom_nar}""", rez_dict=True)
        if rez == False:
            CQT.msgbox(f'ОШикба загрузки бд, попробуй позже')
            return
        if rez[0]['ФИО'] != '' and rez[0]['ФИО2'] != '':
            double_time = rez[0]['Твремя'] * 2
            rez = CSQ.custom_request_c(self.db_naryd,
                                       f"""UPDATE naryad SET {field_name} = '', Твремя = {double_time} WHERE Пномер = {nom_nar} """)
            tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Твремя')).setText(str(double_time))
        else:
            rez = CSQ.custom_request_c(self.db_naryd,
                                       f"""UPDATE naryad SET {field_name} = '' WHERE Пномер = {nom_nar} """)
        tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, field_name)).setText('')
        nar = CMS.Naryads(nom_nar, self.db_naryd)
        nar.recalc_astronom_time(self.DICT_OPER_NAME)

        CQT.msgbox(f'Удачно удален {fio} из {field_name}')

    @CQT.onerror
    def load_jurnal_by_user(self, nom_nar, fio):
        # list_zap = CSQ.custom_request_c(self.db_naryd, f"""SELECT *
        #                         FROM jurnal WHERE Номер_наряда = {nom_nar} AND ФИО = '{fio}';""", rez_dict=True)
        list_zap = [_ for _ in CQT.list_from_wtabl_c(self.ui.tbl_prosmotr_nar_jurnal, rez_dict=True) if _['ФИО'] == fio]
        if list_zap == False:
            CQT.msgbox(f'Не удалось выгрузить журнал')
            return
        list_zap.insert(0, CPY.deepcopy(list_zap[0]))
        list_zap[0]['Дата'] = '2000-02-03 22:50:32'
        list_zap[0]['Пномер'] = -1
        list_zap[0]['Статус'] = ''
        list_zap.append(CPY.deepcopy(list_zap[-1]))
        list_zap[-1]['Дата'] = '2123-02-03 22:50:32'
        list_zap[-1]['Пномер'] = -1
        list_zap[-1]['Статус'] = ''
        return list_zap

    @CQT.onerror
    def check_hstory_jur(self, list_zap, curren_pnum=None):
        for i in range(1, len(list_zap) - 1):
            previos_date = list_zap[i - 1]['Дата']
            previos_status = list_zap[i - 1]['Статус']
            previos_pnom = list_zap[i - 1]['Пномер']

            next_date = list_zap[i + 1]['Дата']
            next_status = list_zap[i + 1]['Статус']
            previos_date = F.date_add_time(F.strtodate(previos_date), '', minutes=1)
            next_date = F.date_add_time(F.strtodate(next_date), '', minutes=-1)
            current_date = F.strtodate(list_zap[i]['Дата'])
            current_status = list_zap[i]['Статус']
            if current_date <= previos_date:
                CQT.msgbox(f'В строке {list_zap[i]} \n {current_date} не может быть меньше {previos_date}')
                return
            if current_date >= next_date:
                CQT.msgbox(f'В строке {list_zap[i]} \n {current_date} не может быть больше {next_date}')
                return

            if current_status == 'Начат':
                if previos_status == 'Начат':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя начать два раза')
                    return
                if previos_status == 'Завершен':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя начать после завершения')
                    return
                if next_status == 'Начат':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя начать два раза')
                    return
            if current_status == 'Приостановлен':
                if list_zap[i]['Примечание'] == '' or len(list_zap[i]['Примечание']) < 4:
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Не указана причина паузы')
                if previos_status == 'Приостановлен':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя приостановить два раза')
                    return
                if previos_status == 'Завершен':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя приостановить после завершения')
                    return
                if next_status == 'Приостановлен':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя приостановить два раза')
                    return
                if next_status == 'Завершен':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя приостановить до завершения')
                    return
            if current_status == 'Завершен':
                if previos_status == 'Приостановлен':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя завершить после приостановки')
                    return
                if previos_status == 'Завершен':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя завершить после завершения')
                    return
                if next_status == 'Приостановлен':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя завершить до приостановки')
                    return
                if next_status == 'Завершен':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя завершить до завершения')
                    return
                if next_status == 'Начат':
                    CQT.msgbox(f'№ {list_zap[i]["Пномер"]} Нельзя завершить до начала')
                    return
            if curren_pnum and int(list_zap[i]['Пномер']) == curren_pnum:
                return True
        return True

    @CQT.onerror
    def add_row_jur(self, *args):
        if '*' in self.ui.btn_apply_deladd_row_jur.text():
            CQT.msgbox(f'Необходимо применить предыдущие изменения')
            return

        tbl_j = self.ui.tbl_prosmotr_nar_jurnal
        c_row = tbl_j.currentRow()

        tbl_data = CQT.list_from_wtabl_c(tbl_j, rez_dict=True)
        tbl_data.insert(c_row + 1, copy.deepcopy(tbl_data[c_row]))
        tbl_data[c_row + 1]['Примечание'] = '*копия'
        tbl_data[c_row + 1]['Пномер'] = ''
        CQT.fill_wtabl(tbl_data, tbl_j, auto_type=False, list_column_widths=CMS.load_column_widths(self, tbl_j))

        self.ui.btn_apply_deladd_row_jur.setText('Применить*')
        return

    @CQT.onerror
    def del_row_jur(self, *args):
        CQT.msgbox(f'В РАЗРАБОТКЕ')
        return
        if '*' in self.ui.btn_apply_deladd_row_jur.text():
            CQT.msgbox(f'Необходимо применить предыдущие изменения')
            return

    @CQT.onerror
    def apply_deladd_row_jur(self, *args):
        tbl = self.ui.tbl_prosmotr_nar_jurnal
        nom_nar = int(tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Номер_наряда')).text())
        fio = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'ФИО')).text()
        list_tbl = self.load_jurnal_by_user(nom_nar, fio)
        if not self.check_hstory_jur(list_tbl):
            return
        if 'edit_jur_nar_data' not in self.__dict__:
            CQT.msgbox(f'ОШибка учета данных редактирования')
            return
        if self.edit_jur_nar_data['type'] == 'add':
            start_num = None
            row = self.edit_jur_nar_data["row"]
            data_jur = CMS.Jurnal_nar(self.db_naryd, nom_nar, fio)
            if self.edit_jur_nar_data['row']['Статус'] in ('Приостановлен', 'Завершен'):
                fl_9999 = False
                for i in range(len(list_tbl) - 1, -1, -1):
                    if list_tbl[i]['Пномер'] == '99999999':
                        fl_9999 = True
                    if fl_9999 and list_tbl[i]['Статус'] == 'Начат':
                        start_num = list_tbl[i]['Пномер']
                        break
                if start_num == None:
                    CQT.msgbox(f'Не найти начало блока')
                    return
                data_jur.set_selected_fragment(int(start_num))

            data_jur.add_new_row(self.DICT_EMPLOEE_FULL_WITH_DEL, row['ФИО'], row['Дата'], row['Статус'],
                                 row['Примечание'])
        self.tbl_prosmotr_nar_click()
        self.ui.btn_apply_deladd_row_jur.setText('Применить')

    @CQT.onerror
    def set_edit_time_jur(self, *args):
        tbl_j = self.ui.tbl_prosmotr_nar_jurnal
        c_row = tbl_j.currentRow()
        current_new_date_time = self.ui.dt_edit_time_jur.text()
        current_status = self.ui.cmb_edit_time_jur.currentText()
        nf_pnum = CQT.num_col_by_name_c(tbl_j, 'Пномер')
        tbl_j.item(c_row, nf_pnum).setText('999999999')
        CQT.set_val_tbl_by_name(tbl_j, c_row, 'Пномер', '99999999')
        CQT.set_val_tbl_by_name(tbl_j, c_row, 'Статус', current_status)
        CQT.set_val_tbl_by_name(tbl_j, c_row, 'Дата', current_new_date_time)
        self.edit_jur_nar_data = {"row": CQT.get_dict_line_form_tbl(tbl_j, c_row),
                                  'type': 'add'}

    @CQT.onerror
    def edit_time_jur_btn(self, *args):
        if '*' in self.ui.btn_apply_deladd_row_jur.text():
            CQT.msgbox(f'Необходимо применить предыдущие изменения')
            return

        @CQT.onerror
        def edit_abstract_current_row_jur(self, list_zap, s_num_row_jur, ):
            flag = False
            for i, item in enumerate(list_zap):
                if int(item['Пномер']) == s_num_row_jur:
                    flag = True
                    # previos_row_date = list_zap[i-1]['Дата']
                    # next_row_date = list_zap[i+1]['Дата']
                    # nach_pnom = list_zap[i-1]['Пномер']
                    current_new_date_time = list_zap[i]['Дата'] = self.ui.dt_edit_time_jur.text()
                    current_status = list_zap[i]['Статус'] = self.ui.cmb_edit_time_jur.currentText()
                    break
            if flag == False:
                CQT.msgbox(f'Не найден номер строки')
                return False
            return list_zap, current_new_date_time, current_status

        if not CQT.msgboxgYN(f'Точно изменить запись на\n\t"{self.ui.cmb_edit_time_jur.currentText()}"\nи '
                             f'время на:\n\t "{self.ui.dt_edit_time_jur.text()}"'):
            return
        tbl = self.ui.tbl_prosmotr_nar
        autor_nar = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Автор')).text()
        if not CMS.user_access(self.db_naryd, f'создание_корректировка_журнал_работ_{autor_nar}',
                               CMS.name_by_empl_c(self.glob_login)):
            if not CMS.user_access(self.db_naryd, f'создание_корректировка_журнал_работ',
                                   CMS.name_by_empl_c(self.glob_login)):
                return
        tbl = self.ui.tbl_prosmotr_nar_jurnal
        tbl_nar = self.ui.tbl_prosmotr_nar
        if tbl.currentRow() == -1:
            CQT.msgbox(f'Не выбрана запись в журнале')
            return
        if self.ui.cmb_edit_time_jur.currentText() == '':
            CQT.msgbox(f'Статус не может быть пусто')
            return
        row = CQT.get_dict_line_form_tbl(tbl)

        nom_nar = int(row['Номер_наряда'])
        por_nom = int(row['Пномер'])

        fio = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'ФИО')).text()

        abstr_list = self.load_jurnal_by_user(nom_nar, fio)
        if abstr_list == None:
            return
        result = edit_abstract_current_row_jur(self, abstr_list, por_nom)
        if result == False:
            return
        abstr_list, current_new_date_time, current_status = result
        if not self.check_hstory_jur(abstr_list, por_nom):
            return

        rez = CSQ.custom_request_c(self.db_naryd, f"""UPDATE jurnal SET Дата = '{current_new_date_time}' , 
         Статус = '{current_status}' WHERE Пномер = {por_nom};""")
        if rez == False:
            CQT.msgbox(f'ОШибка, не занесено')
            return

        jur = CMS.Jurnal_nar(self.db_naryd, nom_nar, fio)
        por_nom = jur.get_s_num_start(por_nom)
        if por_nom == False:
            CQT.msgbox(f'ОШибка, не занесено')
            return
        jur.set_selected_fragment(por_nom)
        jur.calc_and_set_poditog(jur.selected_fragment_end_state, jur.selected_fragment_end_date)

        rez = CSQ.custom_request_c(self.db_naryd,
                                   f"""SELECT Пномер FROM jurnal WHERE Номер_наряда = {nom_nar} AND ФИО = '{fio}' 
                          and Статус = 'Завершен';""")
        if rez == False:
            CQT.msgbox(f'Ошибка выгрузки в наряд попробуй еще')
            return
        if len(rez) >= 2:
            jur.calc_and_fill_nar_by_zaversh(self.DICT_EMPLOEE_FULL_WITH_DEL, jur.user)
        else:
            jur.clear_nar_by_zaversh()
        if row.get('Статус') == 'Завершен' and current_status in ('Начат', 'Приостановлен'): #10.04.25
            jur.clear_mark_confirm()
        tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Дата')).setText(current_new_date_time)
        tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Статус')).setText(current_status)
        cur_row = tbl.currentIndex()
        self.tbl_prosmotr_nar_click()
        tbl.setCurrentIndex(cur_row)
        CQT.msgbox(f'Успешно')

    @CQT.onerror
    def tbl_prosmotr_nar_jurnal_clk(self, *args):
        self.TIME_DEAL = 5
        tbl = self.ui.tbl_prosmotr_nar_jurnal
        old_date = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Дата')).text()
        old_status = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Статус')).text()
        dt_old_date = F.strtodate(old_date)
        cld = self.ui.cal_edit_time_jur
        cld.setSelectedDate(dt_old_date)
        pl = self.ui.hs_edit_time_jur
        pl.setMinimum(0)
        pl.setMaximum(int(24 * 60 / self.TIME_DEAL))
        val_time = dt_old_date.hour * 60 + dt_old_date.minute
        val_time = val_time // self.TIME_DEAL
        pl.setValue(val_time)
        pl.setTickInterval(self.TIME_DEAL)
        self.set_dt_line_jur_edit(self.TIME_DEAL)
        self.ui.cmb_edit_time_jur.setCurrentText(old_status)

    @CQT.onerror
    def edit_time_jur_time_change(self, *args):
        if self.ui.hs_edit_time_jur.hasFocus():
            self.set_dt_line_jur_edit(self.TIME_DEAL)

    @CQT.onerror
    def edit_date_jur_time_change(self, *args):
        if self.ui.cal_edit_time_jur.hasFocus():
            self.set_dt_line_jur_edit(self.TIME_DEAL)

    @CQT.onerror
    def set_dt_line_jur_edit(self, time_deal, *args):
        cld = self.ui.cal_edit_time_jur
        pl = self.ui.hs_edit_time_jur
        dt_line = self.ui.dt_edit_time_jur
        date = cld.selectedDate()
        date = date.toPyDate()
        minutes = pl.value() * time_deal
        hour = minutes // 60
        minute = minutes - 60 * hour
        if hour > 23:
            hour = 23
        date_and_time = F.date_to_datetime(date, hour=hour, minute=minute)
        dt_line.setDateTime(date_and_time)

    @CQT.onerror
    def dblclick_brak(self, *args):
        # tabl_mk = self.ui.tableWidget_vibor_det
        # tabl_sp_mk = self.ui.tableWidget_vibor_mk
        tabl_vib_brak = self.ui.tbl_brak
        if tabl_vib_brak.currentIndex() == -1:
            return
        row = tabl_vib_brak.currentRow()
        nk_nom_nar = CQT.num_col_by_name_c(tabl_vib_brak, 'Номер_наряда')
        nk_nom_act = CQT.num_col_by_name_c(tabl_vib_brak, 'Пномер')
        nk_text = CQT.num_col_by_name_c(tabl_vib_brak, 'Вид_брака')
        nk_kolvo = CQT.num_col_by_name_c(tabl_vib_brak, 'Количество')

        nom_nar = tabl_vib_brak.item(row, nk_nom_nar).text()
        nom_nar = tabl_vib_brak.item(row, nk_nom_nar).text()
        N_act = tabl_vib_brak.item(row, nk_nom_act).text()
        brak_t = tabl_vib_brak.item(row, nk_text).text()
        kol_det_brak = tabl_vib_brak.item(row, nk_kolvo).text()

        if F.is_numeric(kol_det_brak) == False:
            kol_det_brak = 1
        n_k = CQT.num_col_by_name_c(tabl_vib_brak, 'Фото')
        if tabl_vib_brak.currentColumn() == n_k:
            if tabl_vib_brak.item(row, n_k).text() != "":
                sp_foto = tabl_vib_brak.item(row, n_k).text().split(')(')
                sp_pap = F.list_of_files_c(F.scfg('foto_brak'))[0][1]
                for j in range(len(sp_foto)):
                    sp_foto[j] = sp_foto[j].replace(')', '')
                    sp_foto[j] = sp_foto[j].replace('(', '')
                    for i in range(len(sp_pap)):
                        if F.existence_file_c(F.scfg('foto_brak') + os.sep + sp_pap[i] + os.sep + sp_foto[j]) == True:
                            F.run_file_c(F.scfg('foto_brak') + os.sep + sp_pap[i] + os.sep + sp_foto[j])
                return
        n_k = CQT.num_col_by_name_c(tabl_vib_brak, 'Категория_брака')
        if tabl_vib_brak.item(row, n_k).text() == "Неисправимый":
            CQT.msgbox('Брак неисправимый! Необходимо заказать ДСЕ на новое изготовление через служебную по форме ПДО')
            return

        if self.glob_nom_mk == 0:
            CQT.msgbox('Не выбрана мк')
            self.ui.tabWidget_2.setCurrentIndex(0)
            return
        msg = "Акт №" + N_act + " по наряду №" + nom_nar + "(" + brak_t + ")"
        if self.check_nalich_narad_po_ispravl(msg):
            return
        self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Наряд'))
        self.select_last_dse()
        self.raschet_naruada(prinuditelno=True)
        self.ui.lineEdit_cr_nar_norma.setEnabled(True)
        self.ui.lineEdit_cr_nar_kolvo.setText(str(kol_det_brak))
        self.ui.checkBox_vneplan_rab.setChecked(True)

        self.ui.plainTextEdit_zadanie.setPlainText('Исправление ' + msg + ' Инструкции у цехового технолога')
        self.ui.plainTextEdit_zadanie.setReadOnly(True)
        self.ui.plainTextEdit_primechanie.setPlainText(msg)

    @CQT.onerror
    def check_nalich_narad_po_ispravl(self, msg):
        '''Проверка создан ли ранее наряд на исправление'''
        custom_request_c = f'''SELECT Пномер FROM naryad WHERE Номер_мк == {self.glob_nom_mk} AND Внеплан != 0 AND Задание LIKE "%{msg}%" '''
        rez = CSQ.custom_request_c(self.db_naryd, custom_request_c)
        if len(rez) == 2:
            nomer = rez[-1][0]
            CQT.msgbox(f'Наряд на исправление уже создан ранее: №{nomer} ')
            return True
        return False

    @CQT.onerror
    def select_last_dse(self):
        tbl = self.ui.tbl_dse
        self.load_mk()
        # self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, 'ДСЕ'))
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        tbl.cellWidget(tbl.rowCount() - 1, nk_check).setChecked(True)
        tbl.item(tbl.rowCount() - 1, nk_check).setText('1')

    @CQT.onerror
    def click_vneplan(self, val, *args):
        if val == False:
            self.ui.plainTextEdit_zadanie.clear()
            self.ui.plainTextEdit_zadanie.setReadOnly(True)
            self.ui.lineEdit_cr_nar_norma.clear()
            # self.ui.lineEdit_cr_nar_norma.setEnabled(False)
            self.ui.lineEdit_cr_nar_kolvo.clear()
            self.ui.lineEdit_cr_nar_kolvo.setEnabled(False)
            self.ui.plainTextEdit_zadanie.setHidden(False)
            self.ui.lineEdit_cr_nar_nom_proect.setReadOnly(True)
            self.ui.lineEdit_cr_nar_nomerPU.setReadOnly(True)
        else:
            self.ui.plainTextEdit_zadanie.clear()
            self.ui.plainTextEdit_zadanie.setReadOnly(True)
            self.ui.plainTextEdit_zadanie.setHidden(True)
            self.ui.lineEdit_cr_nar_norma.clear()
            # self.ui.lineEdit_cr_nar_norma.setEnabled(True)
            self.ui.lineEdit_cr_nar_norma.setText('0')
            self.ui.lineEdit_cr_nar_kolvo.clear()
            self.ui.lineEdit_cr_nar_kolvo.setEnabled(True)
            self.ui.lineEdit_cr_nar_nom_proect.setReadOnly(True)
            self.ui.lineEdit_cr_nar_nomerPU.setReadOnly(True)

    @CQT.onerror
    def load_brak(self):
        if self.glob_login == '':
            return
        # ==========================OLD vers====================================================
        # if self.glob_nom_mk == 0:
        #    return
        # custom_request_c = f'''SELECT Пномер,Инициатор,
        # Дата,Номер_наряда,Фото,Вид_брака,Категория_брака,
        # Примечание,Количество FROM act WHERE Наряд_исправления == "" AND Номер_наряда != ""'''
        # rez = CSQ.custom_request_c(self.db_act, custom_request_c)
        # nk_nom_nar = F.num_col_by_name_in_hat_c(rez, 'Номер_наряда')
        # spis = [rez[0]]
        ## custom_request_c = F'''SELECT Номер_мк FROM naryad WHERE Пномер == {int(rez[i][nk_nom_nar])}'''
        ## sp_nom_mk = CSQ.custom_request_c(self.db_naryd, custom_request_c, conn)
        # custom_request_c = F'''SELECT Номер_мк, Пномер FROM naryad'''
        # sp_nom_mk = CSQ.custom_request_c(self.db_naryd, custom_request_c, rez_dict=True)
        # if sp_nom_mk == False:
        #    CQT.msgbox(f'Не найдено')
        #    return
        # dict_mk = F.deploy_dict_c(sp_nom_mk, 'Пномер')
        # for i in range(1, len(rez)):
        #    if rez[i][nk_nom_nar] in dict_mk:
        #        nom_mk = dict_mk[rez[i][nk_nom_nar]]
        #        if self.glob_nom_mk == nom_mk:
        #            spis.append(rez[i])
        # CQT.fill_wtabl_old_c(self, spis, self.ui.tbl_brak, isp_hat_c=True, separ='', ogr_maxshir_kol=600)
        # =====================================================================================

        query = f"""SELECT list_brak.s_num, 
        brak.date, 
        brak_price.Код,
        list_brak.group_1, 
        list_brak.group_2, 
        list_brak.group_3, 
        list_brak.neisprav as "неисправимый", 
        list_brak.count_dse as "число ДСЕ", 
        brak.nom_nar as "Наряд", 
        brak.msg as "Примечание", 
        brak.usr_1, 
        brak.usr_2,
        naryad.ФИО,
        naryad.Фвремя,
        naryad.Кол_повт_приемок as "Кол-во повт. приемок",
        naryad.Подтвержд_вып_дата,
        brak_price.Исправимый,
        brak_price.Неисправимый,
        brak.empl  as "Контролёр"
        FROM list_brak 
        INNER JOIN brak ON brak.s_num = list_brak.num_list_brak,
        naryad ON naryad.Пномер = brak.nom_nar,
        mk ON mk.Пномер = naryad.Номер_мк,
        plan ON plan.Пномер = mk.НомКплан,  
        brak_price ON brak_price.Имя = list_brak.group_1 || "$" || list_brak.group_2 || "$" || list_brak.group_3 
        WHERE mk.Статус not in ("НаУдаление") and plan.poki = {self.place.poki}"""
        resp = CSQ.custom_request_c(self.db_naryd, query, rez_dict=True,attach_dbs=(self.db_kplan))
        for i in range(len(resp)):
            if resp[i]['неисправимый'] == 1:
                resp[i]['Исправимый'] = ""
            else:
                resp[i]['Неисправимый'] = ""
            resp[i]["Примечание"] = resp[i]["Примечание"].replace("LF", " ")
        tbl = self.ui.tbl_brak
        CQT.fill_wtabl(resp, tbl, auto_type=False, height_row=24, list_column_widths=CMS.load_column_widths(self, tbl))
        CMS.fill_filtr_c(self, self.ui.tbl_brak_filtr, tbl, hidden_scroll=True)

        clr_bad = CMS.Color_tbl(10)
        clr_good = CMS.Color_tbl(90)
        nf_ispr = CQT.num_col_by_name_c(tbl, 'неисправимый')
        nf_podtv = CQT.num_col_by_name_c(tbl, 'Подтвержд_вып_дата')
        for i in range(tbl.rowCount()):
            if tbl.item(i, nf_ispr).text() == '1':
                CQT.set_color_wtab_c(tbl, i, nf_ispr, clr_bad.r, clr_bad.g, clr_bad.b)
            if tbl.item(i, nf_podtv).text() != '':
                CQT.set_color_wtab_c(tbl, i, nf_podtv, clr_good.r, clr_good.g, clr_good.b)

    @CQT.onerror
    def min_rejim(self, val, *args):
        if self.glob_login == '':
            return
        tbl = self.ui.tbl_dse
        if tbl.rowCount() == 0:
            return
        nk_osv = CQT.num_col_by_name_c(tbl, 'Освоено,шт.')
        nk_kol = CQT.num_col_by_name_c(tbl, 'Количество,шт.')
        if val == 2:
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Масса/М1,М2,М3'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Освоено,шт.'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Ссылка'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'ПКИ'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Ном_оп'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Оборудование'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Документы'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Переходы'), True)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Уровень'), True)
            for i in range(tbl.rowCount()):
                if tbl.item(i, nk_osv).text() == tbl.item(i, nk_kol).text():
                    tbl.setRowHidden(i, True)
                else:
                    tbl.setRowHidden(i, False)
        else:
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Масса/М1,М2,М3'), False)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Освоено,шт.'), False)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Ссылка'), False)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'ПКИ'), False)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Ном_оп'), False)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Оборудование'), False)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Документы'), False)
            tbl.setColumnHidden(CQT.num_col_by_name_c(tbl, 'Переходы'), False)
            for i in range(tbl.rowCount()):
                tbl.setRowHidden(i, False)

    @CQT.onerror
    def select_etap_dse(self, i, *args):
        text = self.ui.cmb_etapi.itemText(i)
        tblf = self.ui.tbl_filtr_dse
        nk_imaop = CQT.num_col_by_name_c(tblf, 'Операция')
        tblf.item(0, nk_imaop).setText(text)
        CMS.apply_filtr_c(self, tblf, self.ui.tbl_dse)

    @CQT.onerror
    def select_etap_mat(self, i, *args):
        text = self.ui.cmb_mat.itemText(i)
        tblf = self.ui.tbl_filtr_dse
        nk_mat = CQT.num_col_by_name_c(tblf, 'Масса/М1,М2,М3')
        tblf.item(0, nk_mat).setText(text)
        CMS.apply_filtr_c(self, tblf, self.ui.tbl_dse)

    @CQT.onerror
    def load_podbor_marsh(self, res, *args):

        def fill_table_marsh(self, res):
            # tbl= self.ui.tbl_dse
            # tbl_m = self.ui.tbl_podb_marsh
            list_mar = [['дсе']]
            for rc in self.DICT_RC.keys():
                if rc[0] == '0' and rc[-2:] != '00':
                    list_mar[0].append(rc)
            res_rev = reversed(res)
            set_mar_neformat = set()
            set_rc = set()
            dict_dse_marh = dict()
            for dse in res_rev:
                dse_name = f"{dse['Номенклатурный_номер']} {dse['Наименование']}"
                tmp_mar = []
                for oper in dse['Операции']:
                    rc = oper['Опер_РЦ_код']
                    if rc[:2] == '01':
                        set_rc.add(rc[:4])
                    tmp_mar.append([
                        oper['Опер_РЦ_код'], {
                            'id': f"{dse['Номерпп']}_{oper['Опер_номер']}",
                            'Количество': dse['Количество'],
                            'Освоено,шт.': oper['Освоено,шт.'],
                            'Закрыто,шт.': oper['Закрыто,шт.']
                        }
                    ])
                marh_str = '->'.join([_[0] for _ in tmp_mar if _[0][:2] == '01'])
                if marh_str in dict_dse_marh:
                    dict_dse_marh[marh_str].append(dse['Номерпп'])
                else:
                    dict_dse_marh[marh_str] = [dse['Номерпп']]
                set_mar_neformat.add(marh_str)
                list_mar.append([dse_name])
            #    limit = 1
            #    for item in tmp_mar:
            #        rc = item[0]
            #        dict_param = item[1]
            #        dict_param_str = '/'.join([str(_) for _ in dict_param.values()])
            #        fl= False
            #        for i in range(limit,len(list_mar[0])):
            #            if list_mar[0][i] == rc:
            #                fl = True
            #                list_mar[-1].append(dict_param_str)
            #                break
            #            else:
            #                list_mar[-1].append('')
            #            limit = i + 1
            #        if fl == False:
            #            list_mar[0].append(rc)
            #            list_mar[-1].append(dict_param_str)
            #            limit = len(list_mar[0])
            #
            # CQT.fill_wtabl(list_mar,tbl_m,height_row=20,ogr_maxshir_kol=20)
            # tbl_m.setColumnWidth(0,200)
            return set_mar_neformat, set_rc, dict_dse_marh

        self.set_mar_neformat, set_rc, self.dict_dse_marh = fill_table_marsh(self, res)

        self.ui.cmb_current_rc.clear()
        self.ui.cmb_current_rc.addItem('')
        self.ui.cmb_current_rc.addItems(sorted(list(set_rc)))
        return

    @CQT.onerror
    def select_current_rc(self, *args):
        # self.ui.cmb_list_marsh.clear()
        # self.ui.cmb_list_marsh.addItem('')
        current_rc = self.ui.cmb_current_rc.currentText()
        if current_rc == '':
            return
        list_rows = [_ for _ in self.set_mar_neformat if current_rc in [x[:len(current_rc)] for x in _.split('->')]]
        list_tooltips = ['->'.join('%(Имя)s(%(Примечание)s)' % self.DICT_RC[rc]
                                    for rc in _.split('->')) for _ in list_rows]
        list_colors = []
        list_bold = []
        for marsh in list_rows:
            rgb = '245,245,245'
            list_rc = marsh.split('->')
            for i, rc in enumerate(list_rc):
                if rc[:4] == current_rc:
                    if i < len(list_rc) - 1:
                        next_rc = list_rc[i + 1]
                        rgb = self.DICT_RC_FULL[next_rc]['Цвет']
                    break
            list_colors.append(rgb)
            list_bold.append(True)
        # self.ui.cmb_list_marsh.addItems()
        CQT.fill_list_combobx(self, self.ui.cmb_list_marsh, list_rows, list_colors, list_tooltips, ',', first_void=True,
                              list_bold=list_bold)

    @CQT.onerror
    def select_prof(self, i, *args):
        spis_prof = self.ui.cmb_prof.itemText(i).split('|')
        rez_op = []
        for key in self.DICT_ETAPI.keys():
            fl_add = True
            for prof in spis_prof:
                if prof not in self.DICT_ETAPI[key]:
                    fl_add = False
                    break
            if fl_add:
                rez_op.append(key)
        rez = '|'.join(rez_op)
        tblf = self.ui.tbl_filtr_dse
        nk_imaop = CQT.num_col_by_name_c(tblf, 'Операция')
        tblf.item(0, nk_imaop).setText(rez)
        CMS.apply_filtr_c(self, tblf, self.ui.tbl_dse)

    @CQT.onerror
    def rasch_strukt_dostup(self, res, i, j):
        kol = res[i]['Количество']
        level_c = res[i]['Уровень']
        for i_dse in range(i + 1, len(res)):
            if res[i_dse]['Уровень'] <= level_c:
                break
            if res[i_dse]['Уровень'] == level_c + 1:
                if 'Закрыто,шт.' not in res[i_dse]['Операции'][-1]:
                    dost_vhod_kol = 0
                else:
                    dost_vhod_kol = res[i_dse]['Операции'][-1]['Закрыто,шт.']
                if dost_vhod_kol < kol:
                    kol = dost_vhod_kol
        if kol == 0:
            return False
        return True

    @CQT.onerror
    def rasch_zakritiy_dostup(self, res, i, j):
        if res[i]['Операции'][0]['Освоено,шт.'] == res[i]['Количество']:
            return False
        if j == 0:
            pass
        else:
            if res[i]['Операции'][j - 1]['Закрыто,шт.'] > 0:
                return True
            else:
                return False
        return True

    @CQT.onerror
    def check_box_load_full(self, *args):
        self.load_mk()

    @CQT.onerror
    def load_mk(self, lite=False, nom_mk='', conn='', res=''):
        if nom_mk == '':
            nom_mk = self.glob_nom_mk
        if nom_mk == 0:
            return
        if res == '':
            res = CMS.load_res(nom_mk)

        filtr = self.ui.checkBox_full_dse.isChecked()
        # print(filtr)
        tabl_mk = self.ui.tbl_dse

        tabl_sp_mk = self.ui.tableWidget_vibor_mk
        set_rc = set()
        if res == False:
            self.ui.tabWidget_2.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget_2, 'МК'))
            CSQ.close_bd(conn)
            CQT.msgbox('Не найдена структура, необходимо переоткрыть МК')
            return
        spis_shap_mk = [
            ['Чек', "Наименование", "Обозначение", "В работу,шт.", 'Уровень', "Количество,шт.", "Освоено,шт.",
             'Закрыто,шт.',
             'Ном_оп', "Опер_код", "Операция",
             "Масса/М1,М2,М3", "Ссылка", "ID",
             "Примечание", "ПКИ", "Тпз", "Тшт", 'РЦ', 'РЦ_имя', 'Оборудование', "Профессия", "Вид_работ", "Этап",
             "КР", "КОИД", "Документы", 'Переходы']]
        spis_shab_mk = []

        set_oper = set()
        set_mat = set()
        for i, dse in enumerate(res):
            naim = CMS.level_decor_c(dse['Наименование'], dse['Уровень'])
            nn = CMS.level_decor_c(dse['Номенклатурный_номер'], dse['Уровень'])
            kolich = dse['Количество']
            mat = dse['Мат_кд']
            ssil = dse['Ссылка']
            id = dse['Номерпп']
            prim = dse['Прим']
            pki = dse['ПКИ']
            ur = dse['Уровень']
            if mat.split('/')[1] != '':
                set_mat.add('/'.join(mat.split('/')[1:]))
            for j, oper in enumerate(dse['Операции']):
                if 'Освоено,шт.' not in oper:
                    res[i]['Операции'][j]['Освоено,шт.'] = 0
                if 'Закрыто,шт.' not in oper:
                    res[i]['Операции'][j]['Закрыто,шт.'] = 0
                if filtr or lite:
                    flag_ogranich_oper = False
                    if self.SPIS_DOST_OPER != []:
                        if oper['Опер_наименование'] in self.SPIS_DOST_OPER:
                            flag_ogranich_oper = True
                    else:
                        flag_ogranich_oper = True
                    flag_zakritiy_dostup = False
                    flag_strukturn_dostup = False
                    if flag_ogranich_oper:
                        flag_zakritiy_dostup = self.rasch_zakritiy_dostup(res, i, j)
                    if flag_zakritiy_dostup:
                        flag_strukturn_dostup = self.rasch_strukt_dostup(res, i, j)
                else:
                    flag_strukturn_dostup = True
                # print(flag_strukturn_dostup)
                if flag_strukturn_dostup:
                    zakrito = oper['Закрыто,шт.']
                    osvoeno = oper['Освоено,шт.']
                    oper_naim = oper['Опер_наименование']
                    oper_nom = oper['Опер_номер']
                    oper_rc_kod = oper['Опер_РЦ_код']
                    rc_name = ''
                    if oper_rc_kod in self.DICT_RC:
                        rc_name = self.DICT_RC[oper_rc_kod]
                    set_rc.add(f'{oper_rc_kod}({rc_name})')
                    oper_oborud = oper['Опер_оборудование_наименование']
                    oper_tpz = oper['Опер_Тпз']
                    oper_tst = round(F.valm(oper['Опер_Тшт']) / kolich, 6)
                    etap = ''
                    oper_rc_name = ''

                    if oper_rc_kod in self.DICT_RC:
                        etap = self.DICT_RC[oper_rc_kod]['etaps_name']
                        oper_rc_name = self.DICT_RC[oper_rc_kod]['Имя']

                    if oper['Опер_профессия_код'] in self.DICT_PROFESSIONS:
                        oper_prof = self.DICT_PROFESSIONS[oper['Опер_профессия_код']]['имя']
                    else:
                        oper_prof = oper['Опер_профессия_код']
                    set_oper.add(oper['Опер_наименование'])
                    oper_sort_crab = oper['Опер_профессия_код']
                    if oper_sort_crab in self.DICT_PROFESSIONS:
                        oper_sort_crab = self.DICT_PROFESSIONS[oper_sort_crab]['вид_работ']
                    oper_kr = oper['Опер_КР']
                    oper_koid = oper['Опер_КОИД']
                    docs = '; '.join(dse['Документы']) + "; " + '; '.join(oper['Опер_документы'])
                    perehod = '; '.join(oper['Переходы'])
                    v_raboty = kolich - osvoeno
                    oper_kod = oper['Опер_код']
                    spis_shab_mk.append(
                        ['', naim, nn, v_raboty, ur, kolich, osvoeno, zakrito, oper_nom, oper_kod, oper_naim, mat, ssil,
                         id,
                         prim, pki, oper_tpz, oper_tst, oper_rc_kod, oper_rc_name, oper_oborud,
                         oper_prof, oper_sort_crab, etap, oper_kr, oper_koid, docs, perehod])
        if lite:
            if len(spis_shab_mk) == 0:
                return False
            else:
                return True
        spis_shab_mk = sorted(spis_shab_mk, key=lambda ppor: ppor[F.num_col_by_name_in_hat_c(spis_shap_mk, 'ID')],
                              reverse=True)
        spis_shab_mk.insert(0, spis_shap_mk[0])
        set_red = {F.num_col_by_name_in_hat_c(spis_shab_mk, "В работу,шт.")}

        CQT.clear_tbl(self.ui.tbl_select_marsh)
        CQT.clear_tbl(self.ui.tbl_dse)
        CQT.clear_tbl(self.ui.tbl_select_marsh_filtr)
        # CQT.clear_tbl(self.ui.tbl_filtr_dse)
        tblf = self.ui.tbl_filtr_dse
        nk_imaop = CQT.num_col_by_name_c(tblf, 'ID')
        if nk_imaop != None:
            tblf.item(0, nk_imaop).setText('')

        # CQT.fill_wtabl_old_c(self, spis_shab_mk, tabl_mk, 0, set_red, '', '', 600, True, '', 20,0)
        CQT.fill_wtabl(spis_shab_mk, tabl_mk, set_red, 600, 1, 24, auto_type=False,
                       list_column_widths=CMS.load_column_widths(self, tabl_mk))

        # tabl_mk.setColumnHidden(CQT.num_col_by_name_c(tabl_mk, 'ID'), True)
        nk_check = CQT.num_col_by_name_c(tabl_mk, 'Чек')
        nk_oper_kod = CQT.num_col_by_name_c(tabl_mk, "Опер_код")
        nk_oper_name = CQT.num_col_by_name_c(tabl_mk, "Операция")
        nk_osv = CQT.num_col_by_name_c(tabl_mk, "Освоено,шт.")
        nk_kolvo = CQT.num_col_by_name_c(tabl_mk, "Количество,шт.")
        nk_zakr = CQT.num_col_by_name_c(tabl_mk, 'Закрыто,шт.')
        nk_kod_rc = CQT.num_col_by_name_c(tabl_mk, 'РЦ')
        nk_rc_name = CQT.num_col_by_name_c(tabl_mk, 'РЦ_имя')
        for i in range(tabl_mk.rowCount()):
            CQT.add_check_box(tabl_mk, i, nk_check, conn_func_checked_row_col=self.clck_check_box_dse)
            if tabl_mk.item(i, nk_oper_kod).text() in self.DICT_OPER:
                if self.DICT_OPER[tabl_mk.item(i, nk_oper_kod).text()]['Вспомогат'] == 1:
                    CQT.set_font_color_wtab_c(tabl_mk, i, nk_oper_kod, 120, 120, 120)
                    CQT.set_font_color_wtab_c(tabl_mk, i, nk_oper_name, 120, 120, 120)
            if tabl_mk.item(i, nk_osv).text() == tabl_mk.item(i, nk_kolvo).text():
                CQT.font_cell_size_format(tabl_mk, i, nk_osv, bold=True)
            if tabl_mk.item(i, nk_zakr).text() == tabl_mk.item(i, nk_kolvo).text():
                CQT.font_cell_size_format(tabl_mk, i, nk_zakr, bold=True)
                CQT.font_cell_size_format(tabl_mk, i, nk_kolvo, bold=True)

        CMS.fill_filtr_c(self, self.ui.tbl_filtr_dse, tabl_mk,
                         spis_znach=CQT.get_dict_line_form_tbl(self.ui.tbl_filtr_dse, 0), hidden_scroll=True)
        CMS.apply_filtr_c(self, self.ui.tbl_filtr_dse, self.ui.tbl_dse)
        CMS.load_column_widths(self, self.ui.tbl_dse)

        self.info_label()
        self.oform_dse()
        for i in range(tabl_mk.rowCount()):
            if tabl_mk.item(i, nk_kod_rc).text() in self.DICT_RC_FULL:
                r, g, b = self.DICT_RC_FULL[tabl_mk.item(i, nk_kod_rc).text()]['Цвет'].split(',')
                r = int(r)
                g = int(g)
                b = int(b)
                # min_val =min([r,g,b])
                # r= r - min_val
                # g= g - min_val
                # b = b - min_val
                CQT.set_color_wtab_c(tabl_mk, i, nk_kod_rc, r, g, b)
                CQT.set_color_wtab_c(tabl_mk, i, nk_rc_name, r, g, b)
        # tabl_mk.setItemDelegate(CQT.Delegate(tabl_mk))

        self.ui.cmb_mat.clear()
        self.ui.cmb_mat.addItem('')
        list_mat = sorted(list(set_mat))
        self.ui.cmb_mat.addItems(list_mat)

        spis_oper = sorted(list(set_oper))
        self.ui.cmb_etapi.clear()
        self.ui.cmb_etapi.addItem('')
        for oper in spis_oper:
            self.ui.cmb_etapi.addItem(oper)

        self.ui.chkb_autcourse.setChecked(False)
        self.ui.cmb_prof.clear()
        self.ui.cmb_prof.addItem('')
        set_prof = set()
        for prof in self.DICT_ETAPI.keys():
            set_prof.add('|'.join(self.DICT_ETAPI[prof]))
        for prof in set_prof:
            self.ui.cmb_prof.addItem(prof)
        self.glob_res = res

        if not CMS.user_access(self.db_naryd, 'создание_создание_наряда_аутсорс', self.glob_ima, False):
            self.ui.chkb_autcourse.setEnabled(False)
        else:
            self.ui.chkb_autcourse.setEnabled(True)

        # ======списки для фильра маршрутов=======
        self.load_podbor_marsh(res)
        MARSH.fill_tbl_select_marsh(self)
        MARSH.load_cmb_cust_mar(self)
        self.ui.fr_dse_filtrs.setHidden(CMS.load_tmp_val('fr_dse_filtrs_setHidden', True, True))
        self.ui.fr_dse_elems.setHidden(CMS.load_tmp_val('fr_dse_elems_setHidden', True, True))
        self.ui.fr_dse_tree.setHidden(CMS.load_tmp_val('r_dse_tree_setHidden', True, True))



    def rc_outsource_is_selected(self):
        tbl = self.ui.tbl_dse
        for item in CQT.list_from_wtabl_c(tbl, rez_dict=True):
            if item.get('РЦ') == '020201' and item.get('Чек') == '1':
                self.ui.chkb_autcourse.setChecked(True)
                return True
        self.ui.chkb_autcourse.setChecked(False)

    def clck_check_box_dse(self, check='', i='', j='', *args):
        tbl = self.ui.tbl_dse
        if check:
            tbl.item(i, j).setText('1')
        else:
            tbl.item(i, j).setText('')
        self.rc_outsource_is_selected()
        self.raschet_naruada_time_tmp(check, i, j, *args)
        MARSH.bold_in_marsh_selected_dse(self)


    @CQT.onerror
    def click_chkb_autcourse(self, *args):
        self.unselect_all_dse()

    @CQT.onerror
    def raschet_naruada_time_tmp(self, check='', i='', j='', *, clear_prof_state: bool = True):
        tbl = self.ui.tbl_dse
        state_prof: QtWidgets.QTableWidget = self.ui.tbl_dse_check_prof

        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        col_prof_tbl_check = CQT.num_col_by_name_c(self.ui.tbl_dse_check_prof, 'Профессия')
        set_opers = {item['Операция'] for item in CQT.list_from_wtabl_c(tbl, rez_dict=True)}
        # counter_prof = {tuple(dopust_prof): 0 for oper, dopust_prof in self.DICT_ETAPI.items() if oper in set_opers}
        counter_prof = {}
        checked_profs = set()
        oper_profs = {}
        for item in CQT.list_from_wtabl_c(tbl, rez_dict=True):
            cur_oper = item['Операция']
            cur_prof = item['Профессия']
            dopust_prof = set(self.DICT_ETAPI[cur_oper])
            dopust_prof.add(cur_prof)
            # counter_prof[tuple(dopust_prof)] = 0
            oper_profs.setdefault(cur_oper, set()).update(dopust_prof)

        for oper, profs in oper_profs.items():
            counter_prof[tuple(profs)] = 0
        if nk_check == None:
            return
        time = 0
        time_potenc = 0
        tpz_potenc = 0
        tsht_potenc = 0
        work_count_potenc = 0
        kolvo_check_dse = 0

        if clear_prof_state:
            self.glob_etap = set()
            self.set_rc_check_dse = set()
        tmp_max_time_nar = copy.copy(self.MAX_TIME_NARUAD)
        data_time = []
        data_rc = []
        for i in range(tbl.rowCount()):
            if tbl.cellWidget(i, nk_check).isChecked():
                row = CQT.get_dict_line_form_tbl(tbl, i)
                time_tmp = (F.valm(row['Тпз']) + F.valm(row['Тшт']) *
                            F.valm(row['В работу,шт.']) / F.valm(row['КОИД']))
                if F.valm(row['В работу,шт.']) != 0:
                    tpz_potenc += F.valm(row['Тпз'])
                    work_count_potenc += F.valm(row['В работу,шт.'])
                    tsht_potenc += F.valm(row['Тшт'])
                else:
                    time_tmp = 0
                data_time.append({
                    'Строка': i + 1,
                    'Тпз': round(F.valm(row['Тпз']), 2),
                    'Тшт': round(F.valm(row['Тшт']), 2),
                    'В работу,шт.': F.valm(row['В работу,шт.']),
                    'Сумма минут': round(time_tmp, 2),
                })

                time_tmp_per_one_dse = (F.valm(row['Тпз']) + F.valm(row['Тшт'])) / F.valm(row['КОИД'])
                if time_tmp_per_one_dse > tmp_max_time_nar:
                    tmp_max_time_nar = time_tmp_per_one_dse

                time_potenc += time_tmp

                data_rc.append(row['РЦ'][:5])

                self.set_rc_check_dse.add(row['РЦ'][:5])
                kolvo_check_dse += int(row['Количество,шт.'])
                checked_profs.add(row['Профессия'])
                if not self.ui.chkb_autcourse.isChecked():
                    if self.DICT_ETAPI != dict():
                        for lst_prof in counter_prof.keys():
                            if row['Профессия'] in lst_prof:
                                counter_prof[lst_prof] += 1
                if not F.valm(row['В работу,шт.']) > F.valm(row['Количество,шт.']) - \
                        F.valm(row['Освоено,шт.']):
                    time += time_tmp
        if tbl.currentRow() != -1:
            if kolvo_check_dse == 0:
                if self.ui.tabWidget_2.tabText(self.ui.tabWidget_2.currentIndex()) == 'Наряд':
                    return CQT.msgbox(f'Не выбрано ДСЕ')
        self.ui.lbl_tmp_time.setText(f'{str(round(time, 2))} мин.')
        # ++25.06.25
        # counter_prof = {profs: count for profs, count in counter_prof.items() if count > 0}

        time_is_valid = (
            time_potenc > 0 and
            (self.ui.chkb_autcourse.isChecked() or time_potenc <= self.MAX_TIME_NARUAD)
        )
        if self.ui.chkb_autcourse.isChecked():
            prof_name = ''
            if '21629.1' in self.DICT_PROFESSIONS:
                prof_name = self.DICT_PROFESSIONS['21629.1']['имя']

            counter_prof[(prof_name,)] = len(data_time)
            data_rc = ['020201'] * len(data_time)
        # -- 25.06.25
        self.ui.tbl_dse_check_time.setProperty('validate', time_is_valid)
        data_time.insert(0, {
            'Строка': 'Сумма по строкам',
            'Тпз': round(tpz_potenc, 2),
            'Тшт': round(tsht_potenc, 2),
            'В работу,шт.': work_count_potenc,
            'Сумма минут': round(time_potenc, 2),
        })
        self.fill_state_tables(data_rc, counter_prof, data_time)

    @CQT.onerror
    def un_block_nar_tbl(self, block=True):
        self.ui.checkBox_vneplan_rab.setEnabled(False)
        self.ui.checkBox_bez_kompl.setEnabled(False)
        self.ui.checkBox_vneplan_rab.setHidden(True)
        self.ui.checkBox_bez_kompl.setHidden(True)
        self.ui.lineEdit_cr_nar_kolvo.setEnabled(False)
        self.ui.cmb_kat_vnepl.setEnabled(False)
        self.ui.cmb_prof_vnepl.setEnabled(False)
        self.ui.cmb_rc_vnepl.setEnabled(False)
        self.ui.lineEdit_koef_norm.setText("1")
        if block:
            self.ui.btn_create_nar.setEnabled(False)
            self.ui.plainTextEdit_zadanie.clear()
            self.ui.plainTextEdit_zadanie.setEnabled(False)
            self.ui.lineEdit_cr_nar_norma.clear()
            self.ui.lineEdit_cr_nar_norma.setEnabled(False)
            self.ui.lineEdit_cr_nar_norma.setText('0')
            self.ui.lineEdit_cr_nar_kolvo.clear()

            self.ui.lineEdit_cr_nar_nom_proect.setEnabled(False)
            self.ui.lineEdit_cr_nar_nomerPU.setEnabled(False)
            return
        self.ui.btn_create_nar.setEnabled(True)

        self.ui.plainTextEdit_zadanie.setEnabled(True)
        self.ui.plainTextEdit_zadanie.setReadOnly(True)
        self.ui.lineEdit_cr_nar_norma.setEnabled(True)
        self.ui.lineEdit_cr_nar_norma.setReadOnly(True)

        self.ui.lineEdit_cr_nar_nom_proect.setEnabled(True)
        self.ui.lineEdit_cr_nar_nomerPU.setEnabled(True)
        self.ui.lineEdit_cr_nar_nomerPU.setReadOnly(True)
        self.ui.lineEdit_cr_nar_nom_proect.setReadOnly(True)

    @CQT.onerror
    def raschet_naruada(self, prinuditelno=False):
        tbl = self.ui.tbl_dse
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        zadanie = ''
        nk_dse_naim = CQT.num_col_by_name_c(tbl, 'Наименование')
        nk_dse_nn = CQT.num_col_by_name_c(tbl, 'Обозначение')
        nk_dse_kol = CQT.num_col_by_name_c(tbl, 'Количество,шт.')
        nk_oper_nom = CQT.num_col_by_name_c(tbl, 'Ном_оп')
        nk_oper = CQT.num_col_by_name_c(tbl, 'Операция')
        nk_tpz = CQT.num_col_by_name_c(tbl, 'Тпз')
        nk_tst = CQT.num_col_by_name_c(tbl, 'Тшт')
        nk_docs = CQT.num_col_by_name_c(tbl, 'Документы')
        nk_per = CQT.num_col_by_name_c(tbl, 'Переходы')
        nk_v_rab = CQT.num_col_by_name_c(tbl, 'В работу,шт.')
        nk_kr = CQT.num_col_by_name_c(tbl, 'КР')
        nk_koid = CQT.num_col_by_name_c(tbl, 'КОИД')
        nk_id = CQT.num_col_by_name_c(tbl, 'ID')
        nk_sort_c_rab = CQT.num_col_by_name_c(tbl, 'Вид_работ')
        nk_prof = CQT.num_col_by_name_c(tbl, 'Профессия')
        time = 0
        if nk_check == None:
            return
        self.spis_dse = []
        self.spis_id = []
        self.spis_oper = []
        self.spis_vr = []
        self.spis_kolvo = []
        self.spis_sort_crab = []
        self.spis_prof = []
        for i in range(tbl.rowCount()):
            if tbl.cellWidget(i, nk_check).isChecked():
                if F.valm(tbl.item(i, nk_v_rab).text()) != '' and F.valm(
                        tbl.item(i, nk_v_rab).text()) != 0 or prinuditelno:
                    naim = tbl.item(i, nk_dse_naim).text().strip()
                    nn = tbl.item(i, nk_dse_nn).text().strip()
                    time_tmp = (F.valm(tbl.item(i, nk_tpz).text()) + F.valm(tbl.item(i, nk_tst).text()) *
                                F.valm(tbl.item(i, nk_v_rab).text()) / F.valm(tbl.item(i, nk_koid).text()))
                    time += time_tmp

                    list_pereh = [f'        {str(i + 1)}. {_}' + _ for i, _ in
                                  enumerate(tbl.item(i, nk_per).text().split(";"))]
                    str_pereh = '\n'.join(list_pereh)

                    docs_list = tbl.item(i, nk_docs).text().split("; ")
                    str_docs_list = '; '.join([_ for _ in docs_list if _.strip() != ''])
                    if len(docs_list) > 0:
                        body = f'    Документы: {str_docs_list}' + '\n' + \
                               f'    {tbl.item(i, nk_oper_nom).text()} {tbl.item(i, nk_oper).text()}' + '\n' + \
                               f'{str_pereh}'
                    else:
                        body = f'    {tbl.item(i, nk_oper_nom).text()} {tbl.item(i, nk_oper).text()}' + '\n' + \
                               f'{str_pereh}'

                    head = f'{naim} {nn} ' \
                           f'({tbl.item(i, nk_v_rab).text()} шт.) - {round(time_tmp, 2)} мин. вид_работ: {tbl.item(i, nk_sort_c_rab).text()}'

                    zadanie += head + '\n' + body + '\n' + '\n'

                    self.spis_dse.append(naim + '$' + nn)
                    self.spis_id.append(tbl.item(i, nk_id).text())
                    self.spis_oper.append(tbl.item(i, nk_oper_nom).text() + '$' + tbl.item(i, nk_oper).text())
                    self.spis_vr.append(str(round(time_tmp, 2)))
                    self.spis_kolvo.append(str(tbl.item(i, nk_v_rab).text()))
                    self.spis_prof.append(str(tbl.item(i, nk_prof).text()))
                    # vidrab = tbl.item(i,nk_professia).text()
                    # if vidrab in self.DICT_PROFESSIONS:
                    #    vidrab = self.DICT_PROFESSIONS[vidrab]
                    self.spis_sort_crab.append(tbl.item(i, nk_sort_c_rab).text())

        self.ui.lineEdit_cr_nar_norma.setText(str(round(time, 2)))
        self.ui.plainTextEdit_zadanie.setPlainText(zadanie)
        tbl_mk = self.ui.tableWidget_vibor_mk
        nk_pnom = CQT.num_col_by_name_c(tbl_mk, 'Пномер')
        nk_pnom_pr = CQT.num_col_by_name_c(tbl_mk, 'Номер_проекта')
        nk_pnom_zak = CQT.num_col_by_name_c(tbl_mk, 'Номер_заказа')
        for i in range(tbl_mk.rowCount()):
            if tbl_mk.item(i, nk_pnom).text() == str(self.glob_nom_mk):
                np = tbl_mk.item(i, nk_pnom_pr).text()
                py = tbl_mk.item(i, nk_pnom_zak).text()
                self.ui.lineEdit_cr_nar_nom_proect.setText(np)
                self.ui.lineEdit_cr_nar_nomerPU.setText(py)
                break

        # self.ui.checkBox_vneplan_rab.setChecked(False)

        if self.spis_dse != []:
            # self.ui.checkBox_vneplan_rab.setChecked(True)
            self.un_block_nar_tbl(False)

    @CQT.onerror
    def oform_dse(self):
        tbl = self.ui.tbl_dse
        nk_ur = CQT.num_col_by_name_c(tbl, 'Уровень')
        nk_v_rab = CQT.num_col_by_name_c(tbl, 'В работу,шт.')
        max_ur = 0
        for i in range(tbl.rowCount()):
            ur = int(tbl.item(i, nk_ur).text())
            if ur > max_ur:
                max_ur = ur
        if max_ur == 0:
            shag = 55
        else:
            shag = 155 // max_ur
        for i in range(tbl.rowCount()):
            ur = int(tbl.item(i, nk_ur).text())
            ed = 255 - (max_ur - ur) * shag
            CQT.set_color_row_wtab_c(tbl, i, 0 + ed, 225, 0 + ed)
            CQT.add_color_wtab_c(tbl, i, nk_v_rab, 0, 15, 15)

    @CQT.onerror
    def info_label(self):
        lbl = self.ui.lbl_curr_mk
        tabl_sp_mk = self.ui.tableWidget_vibor_mk
        flag = None
        for i in range(tabl_sp_mk.rowCount()):
            if tabl_sp_mk.item(i, 0) == None:
                break
            if tabl_sp_mk.item(i, 0).text() == str(self.glob_nom_mk):
                tabl_sp_mk.setCurrentCell(i, 0)
                flag = i
                break
        if flag == None:
            lbl.setText('')
        else:
            lbl.setText(
                f'МК {tabl_sp_mk.item(flag, 0).text()} - {tabl_sp_mk.item(flag, 3).text()} '
                f'({tabl_sp_mk.item(flag, 6).text()})')

    @CQT.onerror
    def tbl_red_zhur_click(self, *args):
        text = ''
        tbl = self.ui.tbl_red_zhur
        if tbl.currentRow() == -1:
            pass
        else:
            r = tbl.currentRow()
            nk_zad = CQT.num_col_by_name_c(tbl, 'Задание')
            nk_prim = CQT.num_col_by_name_c(tbl, 'Примечание')
            nk_kolvo = CQT.num_col_by_name_c(tbl, 'Опер_колво')
            zad = tbl.item(r, nk_zad).text()
            prim = tbl.item(r, nk_prim).text()
            kolvo = tbl.item(r, nk_kolvo).text()
            text = f'    Количество: {kolvo} \n    Задание: {zad} \n    Примечание: {prim}'
        self.ui.lbl_red_info.setText(text)

    @CQT.onerror
    def tbl_dse_dblclick(self, *args):
        tbl = self.ui.tbl_dse
        r = tbl.currentRow()
        if r == -1:
            return
        if tbl.currentColumn() == CQT.num_col_by_name_c(tbl, 'Ссылка'):
            os.startfile(f"{tbl.item(r, tbl.currentColumn()).text()}")
        if tbl.currentColumn() == CQT.num_col_by_name_c(tbl, 'Освоено,шт.'):
            row = CQT.get_dict_line_form_tbl(self.ui.tbl_dse)
            dict_filtr = {'Номер_мк': self.glob_nom_mk, 'ДСЕ_ID': row['ID'],
                          'Операции': f"{row['Ном_оп']}${row['Операция']}"}
            self.load_table_prosm_nar(num_mk=self.glob_nom_mk)
            self.ui.tabWidget.blockSignals(True)
            self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget, 'Просмотр нарядов'))
            self.ui.tabWidget.blockSignals(False)
            CMS.fill_filtr_c(self, self.ui.tbl_filtr_prosmotr_nar, self.ui.tbl_prosmotr_nar, dict_filtr, True)

            CMS.apply_filtr_c(self, self.ui.tbl_filtr_prosmotr_nar, self.ui.tbl_prosmotr_nar)

    @CQT.onerror
    def tbl_dse_click(self, *args):
        tbl = self.ui.tbl_dse
        nk_check = CQT.num_col_by_name_c(tbl, 'Чек')
        if tbl.currentColumn() == nk_check:
            self.select_dse(0)

    @CQT.onerror
    def tbl_dse_select(self, *args):
        # self.calc_time_for_selection_rows()
        tbl = self.ui.tbl_dse
        # lbl = self.ui.lbl_ima_rc

        nk_rc = CQT.num_col_by_name_c(tbl, 'РЦ')
        nk_nn = CQT.num_col_by_name_c(tbl, 'Обозначение')
        nk_naim = CQT.num_col_by_name_c(tbl, 'Наименование')
        nk_nom_op = CQT.num_col_by_name_c(tbl, 'Ном_оп')
        if tbl.currentRow() == -1 or nk_nn == None:
            return
        if tbl.item(tbl.currentRow(), nk_nn) == None:
            return
        nn = tbl.item(tbl.currentRow(), nk_nn).text().strip()
        naim = tbl.item(tbl.currentRow(), nk_naim).text().strip()
        nom_oper = tbl.item(tbl.currentRow(), nk_nom_op).text()
        # lbl.setText(
        #     f'РЦ {tbl.item(tbl.currentRow(), nk_rc).text()} - {self.DICT_RC[tbl.item(tbl.currentRow(), nk_rc).text()]}')
        return
        marsh = []
        if self.glob_res == False:
            CQT.msgbox(f'Не загружена ресурсная попробуй позже')
            return
        for dse in self.glob_res:
            if dse['Номенклатурный_номер'] == nn and dse['Наименование'] == naim:
                for oper in dse['Операции']:
                    ima_rc = 'Не известен'
                    if oper["Опер_РЦ_код"] in self.DICT_RC:
                        ima_rc = self.DICT_RC[oper["Опер_РЦ_код"]]
                    if nom_oper == oper["Опер_номер"]:
                        marsh.append(f' ___***{ima_rc} ({oper["Опер_РЦ_код"]})***___ ')
                    else:

                        marsh.append(f'{ima_rc} ({oper["Опер_РЦ_код"]})')
                break

        lbl_info.setText('-->'.join(marsh))

    @CQT.onerror
    def tbl_mk_click(self, *args):
        tbl = self.ui.tableWidget_vibor_mk
        self.glob_nom_mk = int(tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Пномер')).text())
        self.ui.plainTextEdit_zadanie.setPlainText('')
        self.ui.lineEdit_cr_nar_norma.setText('')
        self.ui.lineEdit_cr_nar_nom_proect.clear()
        self.ui.lineEdit_cr_nar_nomerPU.clear()
        self.ui.plainTextEdit_primechanie.clear()
        self.ui.tbl_dse.clear()

        if self.is_brak_mk(self.glob_nom_mk):
            CQT.msgbox(f'На мк {self.glob_nom_mk} имеется брак')

    @CQT.onerror
    def open_papka_chpy(self, *args):
        tabl_sp_mk = self.ui.tableWidget_vibor_mk
        row, column_number = CQT.number_selection_cell_by_row_and_column_c(tabl_sp_mk)
        if column_number == CQT.num_col_by_name_c(tabl_sp_mk, "Статус_ЧПУ"):
            text = tabl_sp_mk.item(tabl_sp_mk.currentRow(), CQT.num_col_by_name_c(tabl_sp_mk, "Статус_ЧПУ")).text()
            if text != "":
                try:
                    put = text.split('_')
                    F.open_dir_c(put[2])
                except:
                    CQT.msgbox('Не удалось открыть папку')

    @CQT.onerror
    def zapoln_tabl_mk(self, *args):
        if self.glob_login == '':
            return
        self.get_plan_proj()
        tabl_sp_mk = self.ui.tableWidget_vibor_mk
        row = tabl_sp_mk.currentRow()


        var = "Открыта"
        if 'shift' in CQT.get_key_modifiers(self):
            var = "Закрыта"
        custom_request_c = f'''SELECT mk.Пномер, mk.Дата, mk.Статус, Тип_мк.Имя as Тип, mk.Номенклатура, 
        CASE WHEN знпр.№ERP IS NOT NULL 
       THEN знпр.№ERP 
       ELSE mk.Номер_заказа 
       END AS Номер_заказа, 
       
        CASE WHEN знпр.№проекта IS NOT NULL 
       THEN знпр.№проекта 
       ELSE mk.Номер_проекта 
       END AS Номер_проекта, 
       
        CASE WHEN napravl_deyat.Псевдоним IS NOT NULL 
       THEN napravl_deyat.Псевдоним 
       ELSE mk.Вид 
       END AS Вид, 
         
        mk.Примечание, mk.Основание,
        mk.Прогресс,
         CASE WHEN plan.Приоритет IS NOT NULL 
       THEN plan.Приоритет 
       ELSE mk.Приоритет 
       END AS Приоритет, 
       
               CASE WHEN napravlenie.name IS NOT NULL 
       THEN napravlenie.name 
       ELSE mk.Направление 
       END AS Направление, 
        mk.Вес, mk.Количество, mk.Статус_ЧПУ, zagot.Дата_раскладки, zagot.Прим_резка, zagot.Дата_компл_загот, 
        "Ресурсная",mk.НомКплан, пл_топ.Отв_технолог AS Разработчик 
        FROM mk 
         LEFT JOIN plan ON plan.Пномер = mk.НомКплан  
          LEFT JOIN napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности 
          LEFT JOIN napravlenie ON napravlenie.Пномер = napravl_deyat.Направление  
         LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
         LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
         LEFT JOIN пл_топ ON пл_топ.НомПл = plan.Пномер 
        INNER JOIN zagot ON mk.Пномер = zagot.Ном_МК 
        INNER JOIN Тип_мк ON mk.Тип = Тип_мк.Пномер 
        WHERE mk.Статус == "{var}" AND plan.poki == {self.place.poki}  ORDER BY mk.Приоритет ASC;'''

        list_mk = CSQ.custom_request_c(self.db_naryd, custom_request_c, attach_dbs=(self.db_kplan))

        spis = [list_mk[0]]

        for i in range(1, len(list_mk)):
            if 'shift' in CQT.get_key_modifiers(self):
                if not self.check_dost_proj_moth(list_mk[i][5], self.glob_ima):
                    continue

            spis.append(list_mk[i])

        nk_res = F.num_col_by_name_in_hat_c(spis, 'Ресурсная')
        spis_wt_res = CPY.deepcopy(spis)

        if spis == False:
            CQT.msgbox(f'Не удалось загрузить данные, попробуй позже')
            return
        nk_nom_mk = F.num_col_by_name_in_hat_c(spis, 'Пномер')

        if self.ui.chk_progress.isChecked():
            conn_res, cur_res = CSQ.connect_bd(self.db_resxml)
            for i in range(1, len(spis)):
                nom_mk = int(spis[i][0])
                data = CSQ.custom_request_c(self.db_resxml, f"""SELECT data FROM res WHERE Номер_мк == {nom_mk}""",
                                            conn=conn_res, cur=cur_res)
                if len(data) == 2:
                    spis[i][nk_res] = data[-1][0]
            CSQ.close_bd(conn_res, cur_res)
            spis[0].append('Прогресс_01')
            spis[0].append('Прогресс_0101')
            spis[0].append('Прогресс_0102')
            spis[0].append('Прогресс_0103')
            spis[0].append('Прогресс_0104')
            nk_obsh = F.num_col_by_name_in_hat_c(spis, 'Прогресс_01')
            nk_zag = F.num_col_by_name_in_hat_c(spis, 'Прогресс_0101')
            nk_meh = F.num_col_by_name_in_hat_c(spis, 'Прогресс_0102')
            nk_sb = F.num_col_by_name_in_hat_c(spis, 'Прогресс_0103')
            nk_mal = F.num_col_by_name_in_hat_c(spis, 'Прогресс_0104')
            for i in range(1, len(spis)):
                spis[i].append('Прогресс_01')
                spis[i].append('Прогресс_0101')
                spis[i].append('Прогресс_0102')
                spis[i].append('Прогресс_0103')
                spis[i].append('Прогресс_0104')
                res = F.from_binary_pickle(spis[i][nk_res])
                spis[i][nk_obsh] = CMS.percent_of_completion_c(res, '01')
                spis[i][nk_zag] = CMS.percent_of_completion_c(res, '0101')
                spis[i][nk_meh] = CMS.percent_of_completion_c(res, '0102')
                spis[i][nk_sb] = CMS.percent_of_completion_c(res, '0103')
                spis[i][nk_mal] = CMS.percent_of_completion_c(res, '0104')
            spis_wt_res = spis
            red_col = {F.num_col_by_name_in_hat_c(spis, 'Прим_резка'),
                       F.num_col_by_name_in_hat_c(spis, 'Дата_компл_загот')}
            set_isp_col = {_ for _ in range(len(spis[0])) if _ != nk_res}
            CQT.fill_wtabl_old_c(self, spis, tabl_sp_mk, set_isp_col, red_col, (), '', 200, True, '', )
            CMS.load_column_widths(self, tabl_sp_mk)
        else:
            red_col = {F.num_col_by_name_in_hat_c(spis, 'Прим_резка'),
                       F.num_col_by_name_in_hat_c(spis, 'Дата_компл_загот'),
                       F.num_col_by_name_in_hat_c(spis, 'Дата_раскладки'), }
            CQT.fill_wtabl(spis_wt_res, tabl_sp_mk, red_col, 200, 20, 30, auto_type=False,
                           list_column_widths=CMS.load_column_widths(self, tabl_sp_mk))

        # tmp_spis = spis_wt_res
        # for i in range(len(tmp_spis)):
        #    for j in range(len(tmp_spis[i])):
        #        tmp_spis[i][j] = str(tmp_spis[i][j]).replace('|', '$')
        # F.save_file('mkards.txt', tmp_spis)
        if row != -1 and row != None:
            tabl_sp_mk.setCurrentCell(row, 0)
        if self.ui.chk_progress.isChecked():
            nk_obsh_t = CQT.num_col_by_name_c(tabl_sp_mk, 'Прогресс_01')
            nk_zag_t = CQT.num_col_by_name_c(tabl_sp_mk, 'Прогресс_0101')
            nk_meh_t = CQT.num_col_by_name_c(tabl_sp_mk, 'Прогресс_0102')
            nk_sb_t = CQT.num_col_by_name_c(tabl_sp_mk, 'Прогресс_0103')
            nk_mal_t = CQT.num_col_by_name_c(tabl_sp_mk, 'Прогресс_0104')
            CQT.fill_progress_c(self, tabl_sp_mk, nk_obsh_t)
            CQT.fill_progress_c(self, tabl_sp_mk, nk_zag_t, isp_poc=False)
            CQT.fill_progress_c(self, tabl_sp_mk, nk_meh_t, isp_poc=False)
            CQT.fill_progress_c(self, tabl_sp_mk, nk_sb_t, isp_poc=False)
            CQT.fill_progress_c(self, tabl_sp_mk, nk_mal_t, isp_poc=False)
        nl_pnom = F.num_col_by_name_in_hat_c(spis, 'Пномер')
        # for i in range(1, len(spis)):
        #    if self.load_mk(True, spis[i][nk_nom_mk], conn='', res=F.from_binary_pickle(spis[i][nk_res])):
        #        CQT.set_color_wtab_c(tabl_sp_mk, i - 1, nl_pnom, 102, 153, 102)
        for key in self.DICT_TIP_MK.keys():
            r, g, b = self.DICT_TIP_MK[key]['rgb'].split(',')
            CQT.color_cell_wtable_c(tabl_sp_mk, 'Тип', '', key, r, g, b, False)

        nf_vid = CQT.num_col_by_name_c(tabl_sp_mk, 'Вид')
        list_brak_mk = self.get_list_brak_mk()
        for i in range(tabl_sp_mk.rowCount()):
            if int(tabl_sp_mk.item(i, nk_nom_mk).text()) in list_brak_mk:
                CQT.set_color_wtab_c(tabl_sp_mk, i, CQT.num_col_by_name_c(tabl_sp_mk, "Номенклатура"), 155, 20, 20)
            vid = tabl_sp_mk.item(i, nf_vid).text()
            if vid in self.DICT_NAPR_DEYAT_PSDNAME:
                r, g, b = self.DICT_NAPR_DEYAT_PSDNAME[vid]['Цвет'].split(';')
                CQT.set_color_wtab_c(tabl_sp_mk, i, nf_vid, r, g, b)

        CMS.fill_filtr_c(self, self.ui.tbl_filtr_mk, self.ui.tableWidget_vibor_mk, hidden_scroll=True)

    def get_list_brak_mk(self):
        list_brak_mk = CSQ.custom_request_c(self.db_naryd, f"""SELECT DISTINCT naryad.Номер_мк
                FROM list_brak INNER JOIN brak ON brak.s_num = list_brak.num_list_brak,
                naryad ON naryad.Пномер = brak.nom_nar and naryad.Фвремя = "" ;""", one_column=True, hat_c=False)
        return list_brak_mk

    def is_brak_mk(self, nom_mk: int):
        if nom_mk in self.get_list_brak_mk():
            return True
        return False

    def btn_dse_sh_tree(self):
        if self.ui.fr_dse_tree.isHidden():
            self.ui.fr_dse_tree.setHidden(False)
            CMS.save_tmp_val('r_dse_tree_setHidden', False)
        else:
            self.ui.fr_dse_tree.setHidden(True)
            CMS.save_tmp_val('r_dse_tree_setHidden', True)

    def btn_dse_sh_filtr(self):
        if self.ui.fr_dse_filtrs.isHidden():
            self.ui.fr_dse_filtrs.setHidden(False)
            CMS.save_tmp_val('fr_dse_filtrs_setHidden', False)
        else:
            self.ui.fr_dse_filtrs.setHidden(True)
            CMS.save_tmp_val('fr_dse_filtrs_setHidden', True)

    def btn_dse_sh_elems(self):
        if self.ui.fr_dse_elems.isHidden():
            self.ui.fr_dse_elems.setHidden(False)
            CMS.save_tmp_val('fr_dse_elems_setHidden', False)
        else:
            self.ui.fr_dse_elems.setHidden(True)
            CMS.save_tmp_val('fr_dse_elems_setHidden', True)

    def btn_dse_info(self):
        msg = []
        for key in self.DICT_RC.keys():
            msg.append(f'{key}:{self.DICT_RC[key]}')
        txt = pprint.pformat(msg)
        CQT.msgbox(txt)


app = QtWidgets.QApplication(sys.argv)

args = sys.argv[1:]
myappid = 'Powerz.BAG.SystCreateWork.1.0.3'  # !!!
QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
app.setWindowIcon(QtGui.QIcon(os.path.join("icons", "tab.png")))

# S = F.scfg['Stile'].split(",")
app.setStyle('Fusion')
application = mywindow()
# ======================================================
versia = application.versia
if CMS.kontrol_ver(versia, "Создание2") == False:
    sys.exit()
# =========================================================
application.show()
sys.exit(app.exec())
