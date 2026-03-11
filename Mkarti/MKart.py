# -*- coding: utf-8 -*-
import copy
import pprint

import project_cust_38.Cust_Functions as F
import project_cust_38.xml_v_drevo as XML
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWinExtras import QtWin
import os
import project_cust_38.Cust_Qt as CQT


CQT.convert_UI_into_PY_c()
from mk_gui import Ui_MainWindow  # импорт нашего сгенерированного файла

import sys
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Excel as CEX
import project_cust_38.Zamechaniya as ZMCH
import obespechenie as OBSP
import industrial_capacity as IND
import Selector_conversation as SLCT
import calculate_vo as CVO
import resourse_board as RESB
import kal_plan as KPL
import gui_kal_plan as GKPL
import gui_vol_plan as GVKPL
import pl_user_fiters as KPLUF
import project_cust_38.Cust_b24 as CB24
import interaction_googlesheets
import invest_pr as INVPR
import state_prod as STATE
import chpy_calcs as CHPY
import make_poz_plan as POZPL
import recalc_norm as RECLC
import equipment_rc as EQRC
import tabel_edit as TABEL
import tatkuz_molding as TTKZ
import project_cust_38.Cust_config as USRCNF
import data_class
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_emoji as CEMOJ
try:
    import pl_xl_loader as PXL
except Exception as e:
    print('Error import pl_xl_loader')


# TODO """разложить поэтапно порядок постанвоки и подготовки проектив +
# доработать сообщенияв части регламнтов
# включить расчет сроков выдачи КД с учетом срока обсепечения
# фиксировать Пдату Кд от ПДО и Пдату Кд от КО в разыне поля.
# добавить в чат новаковскую, МХ
# """


class mywindow(QtWidgets.QMainWindow):
    resized = QtCore.pyqtSignal()

    def __init__(self):
        super(mywindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.versia = '1.0.0.1.5'
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.NAME_MODULE_BASE = "Маршрутные карты"
        self.name_module = f'{self.NAME_MODULE_BASE}'
        self.USER_CONFIG: USRCNF.User_config = None
        self.place: USRCNF.Place = None
        self.APP_ARGS:dict|None = None
        USRCNF.Config.user_config.load_user_config(self)
        # enable custom window hint
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint)

        CQT.connect_to_resize(self, CMS.tmp_dir())
        CQT.load_resize_splitters(self,CQT.qt_tmp_dir())
        CMS.add_action_config_save_tbl_filtrs(self, self.ui)
        CQT.load_icons(self, 24)
        # disable (but not hide) close button
        # self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        # F.test_path()
        # self.resized.connect(self.widths)
        # self.ip_srv = ''
        self.mk_file_founding = ''
        # CMS.load_ip_srv(self)

        self.Data_plan = data_class.Data_plan
        self.Data_plan.app_self = self
        self.bd_naryad_TEST = F.scfg('Naryad') + F.sep() + 'old' + F.sep() + 'Naryad.db'
        self.bd_naryad = F.bdcfg('Naryad')
        self.bd_act = F.bdcfg('BDact')
        self.db_users = F.bdcfg('BD_users')
        self.bd_files = F.bdcfg('files')
        self.db_kplan = F.bdcfg('DB_kplan')
        self.db_mater = self.bd_nomen = F.bdcfg('nomenklatura_erp')
        self.db_selector = F.bdcfg('BD_selector')
        self.db_resxml = F.bdcfg('db_resxml')
        self.db_dse = F.bdcfg('BD_dse')

        # obj = CMS.Msg_b24(self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, 2770)
        # for type_msg in CMS.Msg_b24.DATA_MSG_DICT.keys():
        #    print(f'{type_msg}:')
        #    obj.send_msg(type_msg)
        #    print('\n\n')

        self.count_izd_from_kpl_for_create_mk = 0
        self.current_kpl_table = ''
        self.selected_napr_koef = 1
        self.selected_napr = ''
        self.dict_tbls_kpl_info = dict()
        self.dict_tbls_kpl = dict()
        self.res = ''
        self.glob_plan_addit_info_poz_gant_old_date = None
        self.glob_nom_mk_obesp = ''
        self.glob_pre_csv_file_path = ''
        self.glob_dict_etaps_from_erp = None
        self.regim = ''
        self.list_vars_vo = []
        self.hat_c = ['Наименование', 'Обозначение', 'Количество', 'Ед.изм.', 'Масса/М1,М2,М3', 'Ссылка',
                      'ID', 'Количество на изделие', 'Примечание', 'ПКИ', 'Сумм.Количество', 'Код ERP',
                      'Наименование_аналог', 'Обозначение_аналог', 'Уд_количество_аналог', 'Коэфф_длины_швов',
                      'Опер_потребл', 'Окрашивание'
            , 'dreva_kod', 'Кол. по заявке', 'Уровень']


        # self.DICT_FILTR = F.deploy_dict_c(CSQ.custom_request_c(self.db_mater, f"""SELECT * FROM complex_filtr""", rez_dict=True), 'kod')
        LIST_MAT = CSQ.custom_request_c(self.db_mater, f"""SELECT * FROM nomen""", rez_dict=True)
        self.DICT_MAT = F.deploy_dict_c(LIST_MAT,
                                        'Код')
        self.DICT_NOMEN_BY_SNUM = F.deploy_dict_c(LIST_MAT,
                                        'Пномер')
        self.DICT_OP, self.DICT_OP_NAME = CMS.calc_dicts_opers(USRCNF.Config.place.poki)
        conn_users, cur_users = CSQ.connect_bd(self.db_users)
        CMS.dict_rc(self,self.db_users)


        if self.SPIS_RC == False:
            CSQ.close_bd(conn_users, cur_users)
            CQT.msgbox(f'БД занята, пробуй позже')
            quit()
        self.SPIS_OB = CSQ.custom_request_c(self.db_users,
                                            """SELECT Инв_номер,Наименование,Примечание FROM equipment""",
                                            conn=conn_users, cur=cur_users)
        if self.SPIS_OB == False:
            CSQ.close_bd(conn_users, cur_users)
            CQT.msgbox(f'БД занята, пробуй позже')
            quit()
        self.SPIS_PROF = CSQ.custom_request_c(self.db_users, """SELECT * FROM professions""", conn=conn_users,
                                              cur=cur_users)
        self.DICT_PROF_CODE = F.list_of_lists_to_dict_of_dicts(self.SPIS_PROF, 'код')
        if self.SPIS_PROF == False:
            CSQ.close_bd(conn_users, cur_users)
            CQT.msgbox(f'БД занята, пробуй позже')
            quit()
        CSQ.close_bd(conn_users, cur_users)

        # ================CALENDAR===================================
        self.ui.cld_obespechenie.clicked.connect(lambda _, x=self: OBSP.data_obespech(x))
        self.ui.calendarWidget.clicked.connect(lambda: KPL.clck_cld(self))
        # ==============TREE=========================================
        self.ui.tree_fields.doubleClicked.connect(lambda: GKPL.tree_fields_dbl_clck(self))
        # ==================================================================
        self.ui.le_pl_find_field.textChanged.connect(lambda: KPL.find_field_reset(self))
        self.ui.le_schema_font_height.textChanged.connect(lambda _, x=self: IND.select_schema(x))
        self.ui.btn_set_start_end_dates.clicked.connect(lambda: GKPL.set_start_end_dates(self))
        # ===============TAB================================================
        tab = self.ui.tabWidget
        tab.currentChanged[int].connect(self.tab_click)
        self.ui.tabWidget_10.currentChanged[int].connect(self.tab_click10)
        self.ui.tabWidget_2.currentChanged[int].connect(self.tab_click2)
        self.ui.tabWidget_3.currentChanged[int].connect(self.tab_mk_click)
        self.ui.tabWidget_4.currentChanged[int].connect(self.tab_zagruzka_rc)
        self.ui.tab_addit_info_poz_gant.currentChanged[int].connect(self.tab_addit_info_poz_gant_click)
        self.ui.tabW_rab_places.currentChanged[int].connect(self.tabW_rab_places_click)
        self.ui.tab_rs_tch.currentChanged[int].connect(lambda: TTKZ.tab_rs_tch_currentChanged(self))

        #++24.12.2025
        # ================== UNSAVED CHANGES GUARD (Создание МК) ==================
        self._mk_dirty = CQT.DirtyState(self)
        self._mk_dirty.watch_table_widget(self.ui.table_razr_MK)     # таблица разработки МК
        self._mk_dirty.watch_table_widget(self.ui.table_zayavk)      # таблица из XML
        self._mk_dirty.watch_line_edit(self.ui.lineEdit_ves)         # вес
        self._mk_dirty.watch_combo_box(self.ui.comboBox_napravlenia, user_only=True)
        self._mk_dirty.watch_combo_box(self.ui.comboBox_sort_c, user_only=True)

        self._mk_tab_guard = CQT.TabLeaveGuard(
            self.ui.tabWidget,
            is_dirty=self._mk_dirty.is_dirty,
            discard=self._discard_create_mk_changes,
            from_tabs={"Создание МК"},
            allowed_tabs={"Номенклатура", "Брак", "Просмотр структуры"},
            message="Вы покидаете вкладку «Создание МК» не сохранив данные.\nПри подтверждении данные будут очищены\nВы уверены что хотите покинуть вкладку?",
            title="Несохраненные данные",
            sub_tubs={self.ui.tabWidget_2},
            forbidden_sub_tubs={'ТКП'},
        )
        self._mk_dirty.mark_clean()
        # ========================================================================
        #--24.12.25

        # ============================================================
        # ==================TABLE=====================================
        self.ui.tbl_data_mold.cellChanged.connect(lambda row, col: TTKZ.data_mold_cellchanged(self, row, col))
        self.ui.tbl_data_mold_tch.cellChanged.connect(lambda row, col: TTKZ.mold_tch_cellchanged(self, row, col))
        self.ui.tbl_data_mold_tch_res_product.cellChanged.connect(
            lambda row, col: TTKZ.mold_tch_res_product_cellchanged(self, row, col))
        self.ui.tbl_data_mold_tch.itemSelectionChanged.connect(lambda: TTKZ.mold_tch_itemSelectionChanged(self))
        self.ui.tbl_data_mold_tch_res_product.itemSelectionChanged.connect(
            lambda: TTKZ.mold_tch_res_product_itemSelectionChanged(self))
        self.ui.tbl_list_orders_mold.itemSelectionChanged.connect(lambda: TTKZ.select_order(self))
        self.ui.tbl_state.clicked.connect(lambda: STATE.select_field_tbl_state(self))
        self.ui.tbL_tkp_list.cellDoubleClicked[int, int].connect(self.CVO_path_kd_dbl_clk)
        self.ui.tbL_tkp_list.itemSelectionChanged.connect(lambda: CVO.load_vid_izd(self))
        self.ui.tbl_selector_proj_view.clicked.connect(self.SLCT_click)
        self.ui.tbl_selector_proj_view.cellChanged[int, int].connect(self.SLCT_edit_primech)
        self.ui.tbl_selector_proj_view_zamech.cellDoubleClicked[int, int].connect(self.SLCT_edit_zamech_from_view)
        self.ui.tbl_selector_proj_view.itemSelectionChanged.connect(self.SLCT_selector_proj_view_itemSelection)
        self.ui.tbl_selector_proj_view.cellDoubleClicked[int, int].connect(self.SLCT_add_new_zamech)
        self.ui.tbl_selector.cellDoubleClicked[int, int].connect(self.SLCT_select_zamech)
        self.tabl_nomenk = self.ui.table_nomenkl
        self.tabl_nomenk.cellDoubleClicked[int, int].connect(self.zapusk_docs)
        self.ui.tbl_obespechenie.cellDoubleClicked[int, int].connect(self.OBSP_select_obesp_po_mk_from_table)
        self.ui.tbl_rc.cellChanged[int, int].connect(self.IND_cellChanged)
        CQT.set_color_sort_cell_table_c(self.tabl_nomenk)
        self.tabl_nomenk.setSelectionBehavior(1)
        self.tabl_nomenk.setSelectionMode(1)
        self.tabl_mk = self.ui.table_spis_MK
        CQT.set_color_sort_cell_table_c(self.tabl_mk)
        self.tabl_mk.setSelectionBehavior(1)
        self.tabl_mk.setSelectionMode(1)
        self.tabl_mk.cellChanged[int, int].connect(self.corr_mk)

        # self.tabl_mk.cellActivated[int, int].connect(self.corr_mk)
        self.tabl_mk.clicked.connect(self.spis_MK_clck)
        self.tabl_brak = self.ui.table_brak
        CQT.set_color_sort_cell_table_c(self.tabl_brak)
        self.tabl_brak.setSelectionBehavior(1)
        self.tabl_brak.setSelectionMode(1)
        self.tabl_brak.clicked.connect(self.click_brak)
        self.tabl_brak.doubleClicked.connect(self.tabl_brak_dbl_clk)

        self.ui.table_spis_MK.setSelectionBehavior(1)
        self.ui.table_spis_MK.setSelectionMode(1)
        CQT.set_color_sort_cell_table_c(self.ui.table_spis_MK)
        self.ui.tbl_poz_from_exel.itemSelectionChanged.connect(lambda: GKPL.fill_select_poz_exel(self))
        self.ui.tbl_kal_pl.itemSelectionChanged.connect(lambda: KPL.clck_tbl_kal_pl_tbl(self))
        self.ui.tbl_preview.itemSelectionChanged.connect(
            lambda x=self, y=self.ui.tbl_preview: KPL.clck_tbl_preview(x, y))
        self.ui.tbl_pl_gaf.itemSelectionChanged.connect(
            lambda x=self, y=self.ui.tbl_pl_gaf: KPL.clck_tbl_pl_gaf(x, y))
        self.ui.tbl_pl_gaf.verticalHeader().setSectionsClickable(True)
        self.ui.tbl_pl_gaf.verticalHeader().sectionDoubleClicked[int].connect(
            lambda logicalIndex: KPL.clck_tbl_verticalHeader(self, logicalIndex))
        self.ui.tbl_kal_pl.horizontalHeader().sectionResized.connect(
            lambda i, j, k: CMS.on_section_resized(self, i, j, k))
        self.ui.tbl_preview.horizontalHeader().sectionClicked.connect(self.tbl_preview_on_header_click)

        # self.ui.tbl_kal_pl.clicked.connect(lambda : KPL.clck_tbl_kal_pl_tbl(self))
        self.ui.tbl_kal_pl.doubleClicked.connect(lambda: KPL.doubleclck_tbl_kal_pl(self))
        self.ui.tbl_rc.itemSelectionChanged.connect(self.clck_tbl_rc)
        self.ui.tbl_rc.clicked.connect(self.clck_tbl_rc)
        self.ui.tbl_rc.doubleClicked.connect(lambda _, x=self: IND.select_schema_dbl_clk(x))
        self.ui.tbl_pl_add_poz.doubleClicked.connect(lambda: KPL.dbl_clk_tbl_add_poz(self))
        self.ui.tbl_tabeli.doubleClicked.connect(lambda: IND.set_old_val(self))
        self.ui.tbl_tabeli.clicked.connect(lambda: IND.set_tooltip_val(self))
        self.ui.tbl_preview.doubleClicked.connect(lambda: KPL.select_field_from_kgui(self))
        self.ui.tbl_pl_gaf.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_pl_gaf_filtr.horizontalScrollBar().setValue)
        self.ui.tbl_pl_gaf.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_pl_gaf_svod.horizontalScrollBar().setValue)
        self.ui.tbl_kal_pl.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_filtr_kal_pl.horizontalScrollBar().setValue)
        # self.ui.tbl_pl_gaf_svod.clicked.connect(lambda: GVKPL.set_tooltip_val(self))
        self.ui.tbl_pl_gaf_svod.setMouseTracking(True)
        self.ui.tbl_pl_gaf_svod.mouseMoveEvent = self.tbl_pl_gaf_svod_mouseMoveEvent
        self.ui.tbl_kal_pl.horizontalHeader().setMouseTracking(True)
        self.ui.tbl_kal_pl.setMouseTracking(True)
        self.ui.tbl_kal_pl.mouseMoveEvent = self.tbl_kal_pl_header_mouseMoveEvent
        # !!!!!!!!!!! self.ui.tbl_kal_pl.cell .connect(lambda: KPL.tbl_kal_pl_cellChanged(self))
        self.ui.table_spis_MK.horizontalScrollBar().valueChanged.connect(
            self.ui.tbl_filtr_mk.horizontalScrollBar().setValue)
        self.ui.tbl_pl_gaf_svod.doubleClicked.connect(lambda: GVKPL.dbl_clk_svod_select_etap(self))
        self.ui.tbl_pl_gaf.doubleClicked.connect(lambda: GVKPL.dbl_clk_select_etap(self))
        self.ui.tbl_preview.setMouseTracking(True)
        self.ui.tbl_preview.mouseMoveEvent = self.tbl_preview_mouseMoveEvent
        self.ui.tbl_pl_gaf.setMouseTracking(True)
        self.ui.tbl_pl_gaf.mouseMoveEvent = self.tbl_pl_gaf_mouseMoveEvent
        self.ui.tbl_pull_etaps.cellChanged[int, int].connect(lambda: POZPL.corr_tbl_pull_etaps(self))
        self.ui.tbl_cld_plan_workforce.clicked.connect(lambda: POZPL.select_month(self))
        self.ui.tbl_cld_plan_workforce.doubleClicked.connect(lambda: POZPL.reselect_month(self))
        self.ui.tbl_equipment.cellChanged[int, int].connect(lambda: EQRC.tbl_eq_change_cell(self))
        # self.ui.tbl_tabeli_person.cellChanged[int, int].connect(lambda : TABEL.update_val(self))
        self.ui.tbl_pull_poz.cellChanged[int, int].connect(lambda: POZPL.edit_handle_pl(self))
        self.ui.tbl_pull_poz.doubleClicked.connect(lambda: POZPL.select_poz_from_pull(self))
        self.ui.tbl_addit_info_poz_gant.doubleClicked.connect(lambda: GKPL.dbl_click_etap_addit_info_poz_gant(self))
        # =================================================================

        # ==============BUTTON==========================================
        self.ui.btn_update_dates_obesp.clicked.connect(lambda: GKPL.update_dates_obesp(self))
        self.ui.pushButton_up_row.clicked.connect(lambda: self.edit_strukt_move_row('up'))
        self.ui.pushButton_down_row.clicked.connect(lambda: self.edit_strukt_move_row('down'))
        self.ui.pushButton_push_strukt_into_db_dse.clicked.connect(self.push_strukt_into_db_dse)
        self.ui.btn_get_res_as_file.clicked.connect(self.get_res_as_file)
        self.ui.btn_adapt_pl_with_gant_after_right.clicked.connect(
            lambda: POZPL.adapt_pl_with_gant(self, 'after_right'))
        self.ui.btn_adapt_pl_with_gant_right.clicked.connect(lambda: POZPL.adapt_pl_with_gant(self, 'right'))
        self.ui.btn_adapt_pl_with_gant.clicked.connect(lambda: POZPL.adapt_pl_with_gant(self))

        self.ui.btn_show_hide_tree_fields.clicked.connect(lambda: GKPL.show_hide_tree_fields(self))
        self.ui.btn_cld_pl_apply_filtr_month.clicked.connect(lambda: POZPL.cld_pl_apply_filtr_month(self))

        self.ui.btn_del_dates_etaps.clicked.connect(lambda: GKPL.del_dates_etaps(self))
        self.ui.btn_set_dates_etaps.clicked.connect(lambda: GKPL.set_dates_etaps(self))
        self.ui.btn_set_dates_etaps_by_sb.clicked.connect(lambda: GKPL.set_dates_etaps(self, True))

        self.ui.btn_pull_poz_del_all.clicked.connect(lambda: POZPL.btn_pull_poz_del_all(self))
        self.ui.btn_pull_poz_del.clicked.connect(lambda: POZPL.btn_pull_poz_del(self))
        self.ui.btn_pull_poz_add.clicked.connect(lambda: POZPL.btn_pull_poz_add(self))
        self.ui.btn_pull_poz_add_all.clicked.connect(lambda: POZPL.btn_pull_poz_add_all(self))
        self.ui.btn_pull_poz_update.clicked.connect(lambda: POZPL.btn_pull_poz_update(self))
        self.ui.btn_pull_all_update.clicked.connect(lambda: POZPL.btn_pull_all_update(self))

        self.ui.btn_clear_filtr.clicked.connect(lambda: KPL.btn_clear_filtr(self))
        self.ui.btn_copy_excel.clicked.connect(lambda: KPL.copy_excel_local(self))
        self.ui.btn_exel_svod.clicked.connect(lambda: KPL.copy_exel_svod(self))
        self.ui.btn_add_rm.clicked.connect(lambda _, x=self: IND.add_rm(x))

        self.ui.btn_obespechenie_spis_po_mk.clicked.connect(lambda _, x=self: OBSP.spis_obesp_po_mk(x))
        self.ui.btn_obespechenie_zapisat.clicked.connect(lambda _, x=self: OBSP.zapisat(x))
        self.ui.btn_add_zamech.clicked.connect(lambda _, x=self: ZMCH.add_zamech(x))
        self.ui.btn_edit_zamech.clicked.connect(lambda _, x=self: ZMCH.load_zamech_to_edit(x))
        # self.ui.btn_add_v_planetapi.clicked.connect(self.add_v_planetapi)
        self.ui.btn_zaversh.clicked.connect(self.zaversh_mkards)

        self.ui.btn_obnov_po_strukt.clicked.connect(self.obnov_po_strukt)
        self.ui.btn_obnovit_naruadi_po_mk.clicked.connect(self.obnovit_naruadi_po_mk)

        self.ui.btn_edit_res_xml.clicked.connect(self.edit_res_xml)
        self.ui.btn_generate_precsv_tree.clicked.connect(lambda: CHPY.generate_precsv_tree(self))
        self.ui.btn_generate_txt_res.clicked.connect(self.generate_txt_res)
        self.ui.btn_tkp_add_to_plan.clicked.connect(lambda: CVO.btn_tkp_add_to_plan(self))
        self.ui.btn_close_all_groups.clicked.connect(lambda: KPL.close_all_groups(self))



        btn_korr_nom = self.ui.btn_korr_nom
        btn_korr_nom.clicked.connect(self.btn_korr_nom)

        btn_del_nom = self.ui.btn_del_poz_nom
        btn_del_nom.clicked.connect(self.del_nom)

        butt_vib_nomen = self.ui.pushButton_ass_nomen_MK
        butt_vib_nomen.clicked.connect(self.ass_dse_to_mk)
        # CQT.set_color_sort_cell_table_c(butt_vib_nomen)

        self.ui.btn_obnov_pr.clicked.connect(self.obn_spis_pr)
        self.ui.btn_select_poz_cr_mk_pr.clicked.connect(self.select_poz_cr_mk_pr)
        self.ui.pushButton_create_MK.clicked.connect(self.create_mk)
        self.ui.pushButton_create_mk_clear.clicked.connect(self.clear_mk)

        but_add_gl_uzel = self.ui.pushButton_create_koren
        but_add_gl_uzel.clicked.connect(self.add_gl_uzel)

        but_add_vhod = self.ui.pushButton_create_vxodyash
        but_add_vhod.clicked.connect(self.add_vhod)

        but_add_paral = self.ui.pushButton_create_paralel
        but_add_paral.clicked.connect(self.add_paral)

        but_udal_uzel = self.ui.pushButton_create_udalituzel
        but_udal_uzel.clicked.connect(self.del_uzel)

        btn_save_cust_drevo = self.ui.btn_save_cust_drevo
        btn_save_cust_drevo.clicked.connect(self.save_cust_drevo)

        btn_load_cust_drevo = self.ui.btn_load_cust_drevo
        btn_load_cust_drevo.clicked.connect(self.load_cust_drevo)

        but_add_bd = self.ui.pushButton_add_v_bd
        but_add_bd.clicked.connect(self.dob_izd_k_bd)

        but_save_mk = self.ui.pushButton_save_MK
        but_save_mk.clicked.connect(self.save_mk)

        but_add_v_mk = self.ui.pushButton_add_v_MK
        but_add_v_mk.clicked.connect(self.add_v_mk)

        but_add_v_nomenk = self.ui.pushButton_add_v_bd_2
        but_add_v_nomenk.clicked.connect(self.add_v_nomenkl)

        btn_normi = self.ui.btn_vigruzka_norm
        btn_normi.clicked.connect(self.vigruzka_norm)

        btn_normi = self.ui.btn_vigruzka_norm_mat
        btn_normi.clicked.connect(self.vigruzka_norm_mat)

        self.but_ass_brak_to_mk = self.ui.pushButton_ass_brak_to_mk
        self.but_ass_brak_to_mk.clicked.connect(self.ass_brak_to_mk)
        self.ui.pushButton_ass_brak_to_mk.setEnabled(False)

        self.but_open_mk = self.ui.pushButton_open_mk
        self.but_open_mk.clicked.connect(self.open_mk)

        self.but_close_mk = self.ui.pushButton_close_mk
        self.but_close_mk.clicked.connect(self.close_mk)

        self.but_del_mk = self.ui.pushButton_del_mk
        self.but_del_mk.clicked.connect(self.del_mk)

        self.ui.pushButton_clear_label.clicked.connect(self.del_ass)
        self.ui.pushButton_clear_label.setToolTip('Удалить ассоциации с актами о браке')

        self.ui.btn_update_norm.clicked.connect(lambda _, x='vrem': self.update_norm(x))
        self.ui.btn_update_norm_prof.clicked.connect(lambda _, x='prof': self.update_norm(x))
        self.ui.btn_update_norm_rc.clicked.connect(lambda _, x='rc': self.update_norm(x))
        self.ui.btn_update_norm_mat.clicked.connect(lambda _, x='mat': self.update_norm(x))

        self.ui.btn_selector_add.clicked.connect(lambda _, x=self: SLCT.add_zamech(x))
        self.ui.btn_selector_edit.clicked.connect(lambda _, x=self: SLCT.edit_zamech(x))
        self.ui.btn_pl_add_poz.clicked.connect(lambda _, x=self: KPL.btn_pl_add_poz_click(x))
        self.ui.btn_pl_ok_add_poz.clicked.connect(lambda _, x=self: KPL.btn_pl_ok_add_poz_click(x))
        self.ui.btn_pl_edit_poz.clicked.connect(lambda _, x=self: KPL.btn_pl_edit_poz_click(x))

        self.ui.btn_settings.clicked.connect(lambda _, x=self: KPL.btn_pl_settings(x))
        self.ui.btn_pl_mode.clicked.connect(lambda _, x=self: KPL.btn_pl_mode(x))
        self.ui.btn_pull_poz_show.clicked.connect(lambda _, x=self: KPL.btn_pull_poz_show(x))
        # self.ui.btn_pull_poz_show.setEnabled(False)
        self.ui.btn_kal_pl_left.clicked.connect(lambda _, x=self: KPL.kal_pl_left(x))
        self.ui.btn_kal_pl_right.clicked.connect(lambda _, x=self: KPL.kal_pl_right(x))
        self.ui.btn_fdate_res_erp.clicked.connect(self.clk_fdate_res_erp)
        self.ui.btn_edit_local_gant_left.clicked.connect(lambda: GKPL.move_left(self))
        self.ui.btn_edit_local_gant_right.clicked.connect(lambda: GKPL.move_right(self))
        self.ui.btn_show_svod.clicked.connect(lambda: GVKPL.show_svod(self))
        self.ui.btn_pl_tabel.clicked.connect(lambda: KPL.show_tabel(self))
        self.ui.btn_load_file_mk_founfing.clicked.connect(self.load_file_mk_founfing)
        self.ui.btn_select_nom_jur_vneplan.clicked.connect(self.select_nom_jur_vneplan)
        self.ui.btn_show_file_founding_mk.clicked.connect(self.show_file_founding_mk)
        self.ui.btn_pl_open_dir.clicked.connect(lambda: KPL.btn_pl_open_dir(self))
        self.ui.btn_pl_add_trbl.clicked.connect(lambda: KPL.btn_pl_add_trbl(self))
        self.ui.btn_pl_load_norm.clicked.connect(lambda: KPL.btn_pl_load_norm(self))
        self.ui.btn_norm_fact_by_opers.clicked.connect(lambda: KPL.btn_norm_fact_by_opers(self))
        self.ui.btn_edit_zp_kpl.clicked.connect(lambda: KPL.btn_edit_zp_kpl(self))
        self.ui.btn_pl_reload.clicked.connect(lambda: KPL.update_tabels(self))
        self.ui.btn_pl_send_dates_into_ERP.clicked.connect(lambda: KPL.send_into_ERP(self))
        self.ui.btn_pl_send_dates_into_ERP_from_exel.clicked.connect(lambda: KPL.pl_send_dates_into_ERP_from_exel(self))
        self.ui.btn_select_exel_file.clicked.connect(lambda: KPL.select_exel_file(self))

        self.ui.btn_pl_kopy_norm_etap_buff.clicked.connect(lambda: KPL.btn_pl_kopy_norm_etap_buff(self))
        self.ui.btn_pl_update_graf_site.clicked.connect(lambda: KPL.update_graf_pad_moshn(self))

        self.ui.pl_btn_add_new_filtr.clicked.connect(lambda: KPLUF.add_pl_user_filtrs(self))
        self.ui.btn_tkp_load_strukt.clicked.connect(lambda: CVO.btn_tkp_load_strukt(self))

        self.ui.btn_tkp_date_res.clicked.connect(lambda: CVO.btn_tkp_date_res(self))
        self.ui.btn_save_pl.clicked.connect(lambda: POZPL.save_kpl_plan(self))
        self.ui.btn_load_pl.clicked.connect(lambda: POZPL.load_poz_pl_from_db(self))
        self.ui.btn_save_pl_local.clicked.connect(lambda: POZPL.save_local_pl(self))
        self.ui.btn_load_pl_local.clicked.connect(lambda: POZPL.load_local_pl(self))
        self.ui.btn_set_vnepl.clicked.connect(lambda: POZPL.btn_set_poz_vnepl(self))

        self.ui.btn_pl_load_google_sheets.clicked.connect(lambda: interaction_googlesheets.get_g_plan(self))
        self.ui.btn_pl_fill_google_sheets.clicked.connect(lambda: interaction_googlesheets.fill_g_plan(self))
        self.ui.btn_pl_set_stat_closed.clicked.connect(lambda: KPL.set_stat_closed(self))
        self.ui.btn_pl_cr_mk.clicked.connect(lambda: KPL.pl_cr_mk(self))
        self.ui.btn_pl_cr_dir_poz.clicked.connect(lambda: KPL.pl_cr_dir_poz(self))
        self.ui.btn_apply_recalc_dates_etaps.clicked.connect(lambda: KPL.apply_recalc_dates_etaps(self))
        self.ui.btn_recalc_fr.clicked.connect(lambda: RECLC.show_fr(self))
        self.ui.btn_recalc_norm_ok.clicked.connect(lambda: RECLC.recalc_opers_norm(self))
        self.ui.btn_add_equipment.clicked.connect(lambda: EQRC.tbl_eq_add_new_row(self))
        self.ui.btn_synch_erp.clicked.connect(lambda: KPL.check_kpl_by_erp(self))
        self.ui.btn_pl_update_graf_site_and_get_local.clicked.connect(lambda: KPL.update_graf_site_and_get_local(self))
        self.ui.btn_recalc_and_fill_fact_rab.clicked.connect(lambda: KPL.recalc_and_fil_fact(self))
        self.ui.btn_apply_diap_dates_to_sb_in_tbl.clicked.connect(lambda: POZPL.apply_diap_dates_to_sb_in_tbl(self))
        self.ui.btn_plan_on_of_day_edit_frame.clicked.connect(lambda: KPL.plan_on_of_day_edit_frame(self))
        self.ui.btn_plan_day_edit_recalc.clicked.connect(lambda: KPL.plan_day_edit_recalc(self))
        self.ui.btn_plan_day_edit_set_weekend.clicked.connect(lambda: KPL.plan_day_edit_set_weekend(self))
        self.ui.btn_show_gui_res.clicked.connect(self.laod_res_board)
        self.ui.btn_apply_data_mold.clicked.connect(lambda: TTKZ.apply_new_or_edit_order(self))
        self.ui.btn_cancel_data_mold.clicked.connect(lambda: TTKZ.cancel_new_or_edit_order(self))
        self.ui.btn_sand_data.clicked.connect(lambda: TTKZ.add_sand_data(self))
        self.ui.btn_add_row_mold_tch.clicked.connect(lambda: TTKZ.add_row_mold_tch(self))
        self.ui.btn_del_row_mold_tch.clicked.connect(lambda: TTKZ.del_row_mold_tch(self))
        self.ui.btn_upload_1c_mold_tch.clicked.connect(lambda: TTKZ.upload_1c_mold(self))
        self.ui.btn_mat_mold_calc.clicked.connect(lambda: TTKZ.mat_mold_calc(self))
        self.ui.btn_res_product.clicked.connect(lambda: TTKZ.create_res_product(self))
        self.ui.btn_apply_next_stage.clicked.connect(lambda: TTKZ.apply_next_stage(self))
        # =================================================================
        # ===========COMBOBOX===========================================
        self.ui.cmb_pl_tabel_place.activated[int].connect(self.cmb_pl_tabel_place)
        self.ui.cmb_year_for_select_tkp.activated[int].connect(self.cmb_year_for_select_tkp)
        self.ui.cmb_cr_mk_pr.activated[int].connect(self.cmb_cr_mk_select_pr)
        self.ui.cmb_cr_mk_py.activated[int].connect(self.cmb_cr_mk_select_py)
        self.ui.cmb_cr_mk_poz.activated[int].connect(self.cmb_cr_mk_select_poz)
        self.ui.cmb_tkp_otv_techn.activated[int].connect(lambda: CVO.cmb_tkp_otv_techn(self))
        self.ui.cmb_tabeli.activated[int].connect(lambda: TABEL.cmb_select_month(self))
        CQT.freeze_mouse_wheel(self.ui.cmb_vid_izd)
        self.ui.cmb_vid_izd.activated.connect(lambda: CVO.cmb_select_vid_izd(self))
        # combo_nap = self.ui.comboBox_napravlenia
        # spis_napr = F.open_file_c(F.scfg('mk_data') + os.sep + 'Направления.txt')
        # for i in range(len(spis_napr)):
        #    combo_nap.addItem(spis_napr[i])

        # combo_sort_c = self.ui.comboBox_sort_c
        # spis_sort_c = F.open_file_c(F.scfg('mk_data') + os.sep + 'Виды.txt')
        # for i in range(len(spis_sort_c)):
        #    combo_sort_c.addItem(spis_sort_c[i])

        dict_tip = CSQ.custom_request_c(self.bd_naryad, """SELECT * FROM Тип_мк""", rez_dict=True)
        self.DICT_TIP_MK = F.deploy_dict_c(dict_tip, 'Имя')
        self.ui.cmb_tip_mk.addItem('')
        self.ui.cmb_tip_mk.addItems([*self.DICT_TIP_MK.keys()])

        dict_tip = CSQ.custom_request_c(self.bd_naryad, """SELECT * FROM тип_дорезок""", rez_dict=True)
        self.DICT_TIP_DOREZ = F.deploy_dict_c(dict_tip, 'Имя')

        dict_tip_dorab = CSQ.custom_request_c(self.bd_naryad, """SELECT * FROM тип_доработок""", rez_dict=True)
        self.DICT_TIP_DORAB = F.deploy_dict_c(dict_tip_dorab, 'Имя')

        self.ui.cmb_schems.activated[int].connect(lambda _, x=self: IND.select_schema(x))
        self.ui.cmb_tip_mk.activated[int].connect(self.cmb_tip_click)
        self.ui.cmb_etap.activated[int].connect(lambda: KPL.select_etap_edit(self))
        self.ui.pl_cmb_filtrs.activated[int].connect(lambda: KPLUF.apply_select_filtr(self))
        # =================================================================
        # ==========================LINEEDIT=============================

        self.ui.lineEdit_naim.textEdited.connect(self.poisk_nn)
        self.ui.lineEdit_nom_n.textEdited.connect(self.poisk_nn)
        self.ui.lineEdit_primech.textEdited.connect(self.poisk_nn)
        self.ui.le_edit_local_gant_full_etap.textEdited.connect(lambda: GKPL.le_edit_local_gant_full_etap(self))
        # =================================================================
        # =================SLIDER==========================================
        # self.ui.sl_mash_local.valueChanged[int].connect(self.sl_mash_change)
        # =================DATE_EDIT==========================================
        self.ui.de_vol_pl.dateChanged.connect(lambda: GVKPL.save_diapazon_month(self))
        self.ui.de_vol_pl_end.dateChanged.connect(lambda: GVKPL.save_diapazon_month(self))
        # =================================================================
        # ===================Check_box=================================
        self.ui.chk_kpl_zaversch.blockSignals(True)
        self.ui.chk_kpl_zaversch.setChecked(False)
        self.ui.chk_kpl_zaversch.blockSignals(False)
        self.ui.chk_kpl_groups.blockSignals(True)
        self.ui.chk_kpl_groups.setChecked(CMS.load_tmp_stukt('chk_kpl_groups',False))
        self.ui.chk_kpl_groups.blockSignals(False)
        self.ui.chk_kpl_zaversch.clicked.connect(lambda: KPL.set_params_kpl(self))
        self.ui.chk_kpl_groups.clicked.connect(lambda: KPL.set_groups_kpl(self))
        self.ui.chk_paint_dates.clicked.connect(lambda: KPL.set_chk_paint_dates(self))
        self.ui.chk_schemas_show_alias.clicked.connect(lambda _, x=self: IND.select_schema(x))
        self.ui.chk_schemas_show_position.clicked.connect(lambda _, x=self: IND.select_schema(x))
        self.ui.chk_schemas_show_fio.clicked.connect(lambda _, x=self: IND.select_schema(x))
        self.ui.chk_autorepeat_update_fact.clicked.connect(lambda: KPL.chk_autorepeat_update_fact(self))
        self.ui.chk_lump_production_method.clicked.connect(lambda: TTKZ.chk_lump_production_method(self))
        # ========================ACTIONS=================================
        if not self.USER_CONFIG.is_developer:
            self.ui.menu_2.setEnabled(False)
            self.ui.menu_2.setTitle('')
        else:
            CQT.add_sub_action_menu(self,self.ui,'menu_2', 'Удалить КПЛ', KPL.del_poz)#удаление строки КПЛ 04.09.2025
            CQT.add_sub_action_menu(self,self.ui,'menu_2', 'Восстановить КПЛ', KPL.fix_crashed_poz)#восстановление строки КПЛ 05.09.2025
            CQT.add_sub_action_menu(self,self.ui,'menu_2', '!тестовй тык', self.test_fnc)#восстановление строки КПЛ 05.09.2025

        self.ui.test_action_1.triggered.connect(self.test_action_1)

        self.ui.action_XML.triggered.connect(self.viborXML)
        # self.ui.action_JSON_p_fabr.triggered.connect(self.export_json)
        self.ui.action_generate_res_erp.triggered.connect(self.export_json_kotl)

        self.ui.action_opn_dir_mk.triggered.connect(self.open_zayavk)
        # self.ui.action_res_ERP.triggered.connect(lambda _, x=self: EXPD.export_res_erp(x))  # это файлами эксель когда выгружали с самого начала,для загрузки ресурсной. Не используется
        self.ui.action4_px.triggered.connect(lambda: self.sl_mash_change(4))
        self.ui.action6_px.triggered.connect(lambda: self.sl_mash_change(6))
        self.ui.action8_px.triggered.connect(lambda: self.sl_mash_change(8))
        self.ui.action10_px.triggered.connect(lambda: self.sl_mash_change(10))
        self.ui.action12_px.triggered.connect(lambda: self.sl_mash_change(12))
        self.ui.action14_px.triggered.connect(lambda: self.sl_mash_change(14))
        self.ui.action16_px.triggered.connect(lambda: self.sl_mash_change(16))
        self.ui.action18_px.triggered.connect(lambda: self.sl_mash_change(18))

        self.ui.action_reload_xml_to_mk.triggered.connect(self.action_reload_xml_to_mk)
        self.ui.action_genetate_res_to_mk.triggered.connect(self.action_genetate_res_to_mk)
        self.ui.action_download_xml.triggered.connect(lambda _, x=self: CMS.save_xml(x))
        self.ui.action_xml_calc_weights.triggered.connect(self.calc_xml_res)
        self.ui.action_xml_add_xml.triggered.connect(self.add_xml_to_mk)
        self.ui.action_clear_xml.triggered.connect(self.del_xml_from_mk)
        self.ui.action_update_db_info_fields_kpl.triggered.connect(lambda: KPL.update_db_info_fields_kpl(self))


        # =================================================================
        # =============LOADS========================================
        # KPL.load_gui(self)
        ZMCH.init_zamech_const(self)
        SLCT.load_dicts_for_selector(self)
        # ===================
        conn_naryad, cur_naryad = CSQ.connect_bd(self.bd_naryad)
        rez = CMS.dict_etapi(self, self.bd_naryad, conn_naryad)
        if rez == False:
            CSQ.close_bd(conn_naryad, cur_naryad)
            CQT.msgbox(f'база нарядов занята')
            quit()
        rez = self.DICT_KOD_OPER = F.deploy_dict_c(
            CSQ.custom_request_c(self.bd_naryad, f"""SELECT kod, name FROM operacii WHERE poki == {self.place.poki}""",
                                 rez_dict=True, conn=conn_naryad,
                                 cur=cur_naryad), 'name')
        if rez == False:
            CSQ.close_bd(conn_naryad, cur_naryad)
            CQT.msgbox(f'база нарядов занята')
            quit()
        CSQ.close_bd(conn_naryad, cur_naryad)
        # ======================== nomen

        self.DICT_NOMEN = self.DICT_MAT

        if self.DICT_NOMEN == False:
            CQT.msgbox(f'база номенклатуры занята')
            quit()

        self.DICT_FILTR_NOMEN = CSQ.custom_request_c(self.bd_nomen, f'''SELECT * FROM complex_filtr''',
                                                     one=False, hat_c=False, rez_dict=True)
        self.DICT_KOD_CAM = F.deploy_dict_c(CSQ.custom_request_c(self.bd_naryad, f'''SELECT * FROM material_kod''',
                                                                 one=False, hat_c=False, rez_dict=True), 'name')
        if self.DICT_FILTR_NOMEN == False:
            CQT.msgbox(f'база номенклатуры занята')
            quit()

        # ====================== txt
        self.DICT_PROJECTS = dict()#todo вычисить
        #CMS.dict_projects(self, F.tcfg('BD_Proect'))
        CVO.DICT_VAR_OPER(self)
        CMS.DICT_PLACES(self, self.db_users)

        # ======================= users
        conn_users, cur_users = CSQ.connect_bd(self.db_users)
        self.DICT_VID_RABOT:dict = None
        self.pnom_kplan_select:int = None
        rez = CMS.dict_professions(self, self.db_users, conn_users)
        if rez == False:
            CSQ.close_bd(conn_users, cur_users)
            CQT.msgbox(f'база users занята')
            quit()
        self.DICT_RC = dict()
        rez = CMS.dict_rc(self, self.db_users, conn_users)

        if rez == False:
            CSQ.close_bd(conn_users, cur_users)
            CQT.msgbox(f'база users занята')
            quit()
        self.DICT_EMPLOEE = CMS.dict_emploee(self.db_users, conn_users)
        self.DICT_EMPLOEE_FULL = CMS.dict_emploee_full(self.db_users, conn_users, self)

        if self.DICT_EMPLOEE == False:
            CSQ.close_bd(conn_users, cur_users)
            CQT.msgbox(f'база users занята')
            quit()
        rez = CMS.dict_emploee_rc(self, conn_users)
        if rez == False:
            CSQ.close_bd(conn_users, cur_users)
            CQT.msgbox(f'база users занята')
            quit()
        CMS.dict_rab_mesta(self, self.db_users, conn_users)
        CSQ.close_bd(conn_users, cur_users)

        # =================================
        self.load_lbl_schema()

        self.obn_spis_pr()
        self.clear_mk()
        self.edit_cr_mk = {2, 3, 4, 5, 8, 9, 19}
        self.edit_cr_mk_ruch = {0, 1, 2, 3, 4, 5, 8, 9, 19, 20}
        self.ui.cmb_nom_jur_vneplan.setEnabled(False)
        self.ui.btn_select_nom_jur_vneplan.setEnabled(False)
        # self.TIP_NEGRUZ_DSE = ('Сборочный чертёж', 'Изделие проекта', 'Монтажный чертёж', 'Материал')
        self.TIP_NEGRUZ_DSE = CMS.LIST_NEGRUZ_DSE(self.db_mater)
        # CMS.add_menu(self)

        # self.ui.tabWidget.setCurrentIndex(3)
        self.START_TAB_IND = CQT.number_table_by_name_c(self.ui.tabWidget, 'Создание МК')
        self.ui.tabWidget.setCurrentIndex(self.START_TAB_IND)

        self.sp_ins = ['комплектация', 'изготовление', 'контроль']
        self.nom_mk_dlya_korr = None
        self.spis_nom_tk_kor_mk = []
        self.spis_nom_tk_del_kor_mk = []
        try:
            get_list_of_tables_c_db = CSQ.get_list_of_tables_c(self.bd_naryad)
        except:
            CQT.msgbox(f'База занята')
            quit()

        path = F.scfg('mk_data') + F.sep() + 'schems' + F.sep()
        if F.existence_file_c(path):
            list_files = F.list_of_files_c(path)
            for file in list_files[0][2]:
                if F.keep_extention_c(file) == '.jpg':
                    self.ui.cmb_schems.addItem(F.throw_out_extention_c(file))

        # self.ui.btn_obnovit_naruadi_po_mk.setEnabled(False)
        # self.ui.btn_obnovit_naruadi_po_mk.setToolTip('На корректировке') # todo
        if not CMS.user_access(self.bd_naryad, 'mkart_mk_korrect_res_xml', F.user_name(), msg=False):
            self.ui.btn_update_norm.setEnabled(False)
            self.ui.btn_update_norm_rc.setEnabled(False)
            self.ui.btn_update_norm_prof.setEnabled(False)
            self.ui.btn_obnov_po_strukt.setEnabled(False)
            self.ui.btn_obnovit_naruadi_po_mk.setEnabled(False)
            self.ui.btn_ochistit.setEnabled(False)
            self.ui.btn_open_korr_mk.setEnabled(False)
            self.ui.btn_zapoln_osv_zav_po_nar.setEnabled(False)
            self.ui.btn_ochistit.setEnabled(False)

        # ==============VREMENNO========================================
        # self.ui.btn_zaversh.setDisabled(1)
        # self.VREMENNO_pereschet_vesa_mk()
        self.ui.btn_open_korr_mk.setDisabled(1)
        self.ui.btn_add_v_planetapi.setDisabled(1)
        self.ui.btn_recalc_fr.setDisabled(1)
        self.ui.btn_zapoln_osv_zav_po_nar.setDisabled(1)
        self.ui.btn_ochistit.setDisabled(1)
        # VREMENNO   self.miration_data_sql()
        # self.ui.btn_vigruzka_norm.setDisabled(1)
        # ==============================================================

        self.push_work_plan_fact = PXL.PushWorkPlan(
            window=self,
            plan_tbl=self.ui.tbl_pl_tabel_month,
            plan_tbl_fltr=self.ui.tbl_pl_tabel_month_filtr,
            fact_tbl=self.ui.tbl_pl_tabel_fmonth,
            fact_tbl_fltr=self.ui.tbl_pl_tabel_fmonth_filtr
        )
        self.ui.btn_add_month.clicked.connect(lambda *_: self.push_work_plan_fact.insert_one_month())
        self.ui.btn_del_month.clicked.connect(lambda *_: self.push_work_plan_fact.remove_month())
        self.ui.btn_cpy_data.clicked.connect(lambda *_: self.push_work_plan_fact.copy_data())
        self.ui.btn_pst_data.clicked.connect(lambda *_: self.push_work_plan_fact.paste_data())
        self.ui.btn_load_data.clicked.connect(lambda *_: self.push_work_plan_fact.load_xlsx())

        self.ui.fr_recacl_norm.setVisible(False)

        self.ui.lbl_shema.mousePressEvent = self.getPos

        self._tkp_current_schema = CMS.TkpSchema()
        self.ui.chk_consider_project_abs_product.clicked[bool].connect(self.on_click_chk_consider_project_abs_product) #12.11.25
        self._ttkz_tmp_settings = TTKZ.Ttkz_tmp_settings(self.ui.lbl_data_mold,self)
        IND.load_control_schema_output(self)
        self.apply_visible_by_places()

        self.ui.tbl_rc_autopause_2.cellChanged.connect(lambda *args: IND.on_autopause_table_changed(self, *args)) #25.01.2026



    @CQT.onerror
    def test_fnc(self,*args):
        #KPL.test_add_field_kpl()#30.01.2026 тест внесения в план дат
        pnums = CSQ.custom_request_c(USRCNF.Config.project.db_kplan,f"""SELECT Пномер FROM plan WHERE Статус IN (1,
                    2,
                    3,
                    7,
                    8,
                    9);""",one_column=True)
        CMS.update_local_graf(self,update=True,fill_gant=False,pnom=pnums[1:])

        pass

    def _discard_create_mk_changes(self): #24.12.2025
        try:
            with self._mk_dirty.suspended():
                self.clear_mk()
        finally:
            self._mk_dirty.mark_clean()

    def fill_chk_consider_project_abs_product(self):
        schema = getattr(self, 'tkp_current_schema', None)
        if isinstance(schema, CMS.TkpSchema):
            self.ui.chk_consider_project_abs_product.setChecked(
                bool(schema.XML_start_from_project_product_type)
            )

    def on_click_chk_consider_project_abs_product(self, activated: bool) -> None: #12.11.25
        self.tkp_current_schema['XML_start_from_project_product_type'] = activated
        tree = self.ui.tree_base_tree
        if tree.topLevelItemCount() >= 1:
            tree.clear()

    @property
    def tkp_current_schema(self):
        return self._tkp_current_schema

    @CQT.onerror
    def test_action_1(self, *args):
        # 18.04.2025
        def fix_error(list_nar: list):  # по ТЗ
            # list_nar = CSQ.custom_request_c(self.db_naryd,f"""SELECT Пномер FROM naryad WHERE datetime(Дата) >= datetime('2024-08-01 07:12:41')""",hat_c=False)
            # list_nar = [48176]
            for num in list_nar:
                nar = CMS.Naryads(num, self.bd_naryad)
                if nar.ФИО:
                    nar.recalc_jur_n_time(nar.ФИО)
                if nar.ФИО2:
                    nar.recalc_jur_n_time(nar.ФИО2)
                # if len(nar.params) == 1 and nar.params[0]['Опер_колво'] == 1:
                nar.recalc_tvrem()
                nar.recalc_astronom_time(self.DICT_OP_NAME)
                nar.recalc_fact()
            return
            pass

        fix_error([61534])
        return

    @CQT.onerror
    def apply_visible_by_places(self):
        hide_elems_names = {}
        show_elems_names = {}
        invisible_tab_texts = {}
        visible_tab_texts = {}
        place = self.place.Имя
        if place == 'Пауэрз':
            invisible_tab_texts = {"РС для литья"}
        if place == 'Келаст':
            invisible_tab_texts = {"РС для литья"}
        if place == 'ТатКуз':
            hide_elems_names = {'fr_cr_mk_btns', 'fr_weight', 'gr_select_proj', 'pushButton_create_mk_clear'}
            show_elems_names = {}

            invisible_tab_texts = {'*'}
            visible_tab_texts = {"Создание МК", "РС для литья"}
            TTKZ.load_form_rs_for_molding(self)

        for item in self.ui.__dict__:
            obj = eval(f'self.ui.{item}')
            if hide_elems_names:
                if item in hide_elems_names or '*' in hide_elems_names:
                    obj.blockSignals(True)
                    obj.setVisible(False)
                    obj.blockSignals(False)
            if show_elems_names:
                if item in show_elems_names or '*' in show_elems_names:
                    obj.blockSignals(True)
                    obj.setVisible(True)
                    obj.blockSignals(False)

            if isinstance(obj, QtWidgets.QTabWidget):
                count_tabs = obj.count()
                for i in range(count_tabs):
                    tab_name = obj.tabText(i)

                    if invisible_tab_texts:
                        if tab_name in invisible_tab_texts or '*' in invisible_tab_texts:
                            obj.blockSignals(True)
                            obj.setTabVisible(i, False)
                            obj.blockSignals(False)

                    if visible_tab_texts:
                        if tab_name in visible_tab_texts or '*' in visible_tab_texts:
                            obj.blockSignals(True)
                            obj.setTabVisible(i, True)
                            obj.blockSignals(False)

    @tkp_current_schema.setter
    def tkp_current_schema(self, new_val) -> CMS.TkpSchema:
        self._tkp_current_schema.update(new_val)

    def update_dates(self):
        dict_pr = {
            38: '19.01.2022',
            42: '19.01.2022',
            43: '19.01.2022',
            44: '24.01.2022',
            45: '24.01.2022',
            48: '19.01.2022',
            49: '10.03.2022',
            50: '05.03.2022',
            51: '05.03.2022',
            52: '05.03.2022',
            53: '05.03.2022',
            54: '05.03.2022',
            55: '05.03.2022',
            56: '05.03.2022',
            57: '05.03.2022',
            58: '05.03.2022',
            59: '05.03.2022',
            60: '05.03.2022',
            61: '05.03.2022',
            62: '05.03.2022',
            63: '05.03.2022',
            65: '28.12.2021',
            66: '28.12.2021',
            67: '28.12.2021',
            68: '14.02.2022',
            69: '14.02.2022',
            70: '14.02.2022',
            71: '19.11.2021',
            72: '14.03.2022',
            74: '10.03.2022',
            75: '28.12.2021',
            76: '28.12.2021',
            77: '28.12.2021',
            78: '14.03.2022',
            79: '05.04.2022',
            80: '24.03.2022',
            81: '24.03.2022',
            82: '24.03.2022',
            83: '24.03.2022',
            84: '24.03.2022',
            85: '29.04.2022',
            86: '06.04.2022',
            87: '17.05.2022',
            88: '11.03.2022',
            89: '22.03.2022',
            90: '22.03.2022',
            91: '22.03.2022',
            92: '22.03.2022',
            93: '08.04.2022',
            94: '08.04.2022',
            95: '20.04.2022',
            96: '14.03.2022',
            97: '18.03.2022',
            98: '11.03.2022',
            99: '30.05.2022',
            100: '30.05.2022',
            102: '06.05.2022',
            103: '06.05.2022',
            104: '27.04.2022',
            105: '27.04.2022',
            106: '18.03.2022',
            107: '25.03.2022',
            108: '31.03.2022',
            109: '31.03.2022',
            110: '31.03.2022',
            111: '31.03.2022',
            112: '05.03.2022',
            113: '05.03.2022',
            114: '05.03.2022',
            115: '05.03.2022',
            118: '24.02.2022',
            119: '24.02.2022',
            120: '24.02.2022',
            121: '25.04.2022',
            122: '25.04.2022',
            123: '25.04.2022',
            124: '25.04.2022',
            125: '25.04.2022',
            126: '25.04.2022',
            127: '25.04.2022',
            128: '25.04.2022',
            129: '20.05.2022',
            130: '20.05.2022',
            131: '18.03.2022',
            132: '27.05.2022',
            133: '27.05.2022',
            134: '21.10.2021',
            136: '02.06.2022',
            137: '30.05.2022',
            138: '28.06.2022',
            139: '28.06.2022',
            148: '30.06.2022',
            149: '30.06.2022',
            150: '30.06.2022',
            151: '30.06.2022',
            152: '30.06.2022',
            153: '30.06.2022',
            154: '30.06.2022',
            155: '30.06.2022',
            156: '30.06.2022',
            165: '12.08.2022',
            166: '12.08.2022',
            169: '30.06.2022',
            170: '30.06.2022',
            171: '30.06.2022',
            172: '30.06.2022',
            173: '30.06.2022',
            174: '30.06.2022',
            175: '30.06.2022',
            176: '30.06.2022',
            177: '16.06.2022',
            179: '02.06.2022',
            180: '10.06.2022',
            181: '02.06.2022',
            182: '02.06.2022',
            183: '30.05.2022',
            184: '30.05.2022',
            185: '09.06.2022',
            186: '20.06.2022',
            187: '20.06.2022',
            188: '20.06.2022',
            189: '20.06.2022',
            191: '30.06.2022',
            192: '28.06.2022',
            193: '28.06.2022',
            194: '28.06.2022',
            195: '28.06.2022',
            196: '28.06.2022',
            197: '28.06.2022',
            198: '28.06.2022',
            199: '28.06.2022',
            200: '28.06.2022',
            201: '28.06.2022',
            202: '28.06.2022',
            203: '28.06.2022',
            204: '28.06.2022',
            205: '28.06.2022',
            206: '28.06.2022',
            207: '29.06.2022',
            208: '29.06.2022',
            209: '28.06.2022',
            210: '01.05.2022',
            211: '01.05.2022',
            212: '01.05.2022',
            213: '28.11.2022',
            222: '30.06.2022',
            224: '20.06.2022',
            225: '04.07.2022',
            227: '04.07.2022',
            228: '04.07.2022',
            234: '01.07.2022',
            238: '01.07.2022',
            239: '29.06.2022',
            241: '01.07.2022',
            242: '01.07.2022',
            243: '01.07.2022',
            244: '01.07.2022',
            245: '01.07.2022',
            246: '01.07.2022',
            247: '01.07.2022',
            248: '01.07.2022',
            252: '23.06.2022',
            255: '20.01.2023',
            256: '20.01.2023',
            257: '15.06.2022',
            266: '23.06.2022',
            314: '02.08.2022',
            319: '19.08.2022',
            331: '02.08.2022',
            355: '09.12.2022',
            357: '29.09.2023',
            358: '29.09.2023',
            501: '29.11.2022',
            507: '06.04.2023',
            559: '26.08.2022',
            565: '26.09.2022',
            636: '30.09.2022',
            654: '28.10.2022',
            707: '07.11.2022',
            708: '07.11.2022',
            768: '28.12.2022',
            867: '29.11.2022',
            870: '29.11.2022',
            874: '29.11.2022',
            884: '29.11.2022',
            902: '29.11.2022',
            904: '29.11.2022',
            906: '19.12.2022',
            908: '19.12.2022',
            909: '19.12.2022',
            923: '29.12.2022',
            943: '',
            946: '04.10.2023',
            976: '27.02.2023',
            977: '27.02.2023',
            989: '14.04.2023',
            1002: ' - ',
            1013: '01.03.2023',
            1015: '22.03.2023',
            1042: '13.02.2023',
            1066: '25.01.2023',
            1075: '26.01.2023',
            1076: '26.01.2023',
            1080: '26.01.2023',
            1083: '26.01.2023',
            1085: '25.01.2023',
            1117: '06.10.2023',
            1727: '15.09.2023',
            1729: '15.09.2023',
            1739: '13.07.2023',
            1742: '13.07.2023',
            1759: '10.05.2023',
            1760: '10.05.2023',
            1761: '10.05.2023',
            1765: '10.07.2023',
            1779: '05.05.2023',
            1780: '05.05.2023',
            1809: '07.07.2023',
            1840: '26.06.2023',
            1841: '09.11.2022',
            1845: '27.03.2024',
            1856: '21.09.2023',
            1862: '30.05.2023',
            1867: '10.05.2023',
            1869: '25.09.2023',
            1871: '18.08.2023',
            1872: '25.09.2023',
            1878: '26.06.2023',
            1879: '15.09.2023',
            1898: '11.08.2023',
            1900: '14.07.2023',
            1901: '14.07.2023',
            1902: '14.07.2023',
            1907: '14.07.2023',
            1918: '01.09.2023',
            1922: '24.08.2023',
            1927: '07.06.2023',
            1928: '07.06.2023',
            1938: '30.05.2023',
            1941: '30.05.2023',
            1942: '01.09.2023',
            1943: '01.09.2023',
            1947: '30.06.2023',
            1951: '28.04.2023',
            1952: '13.07.2023',
            1959: '31.05.2023',
            1961: '31.05.2023',
            1963: '13.07.2023',
            1964: '13.07.2023',
            1965: '28.03.2023',
            1977: '24.08.2023',
            1980: '21.08.2023',
            1981: '07.06.2023',
            1992: '01.09.2023',
            2070: '30.12.2022',
            2085: '09.08.2023',
            2092: '30.06.2023',
            2099: '09.08.2023',
            2101: '31.07.2023',
            2109: '22.12.2023',
            2113: '05.04.2023',
            2130: '27.07.2023',
            2138: '21.07.2023',
            2148: '05.07.2023',
            2238: '07.08.2023',
            2239: '07.08.2023',
            2242: '22.05.2023',
            2243: '29.06.2023',
            2244: '17.07.2023',
            2248: '27.06.2023',
            2290: '22.05.2023',
            2298: '22.05.2023',
            2314: '07.08.2023',
            2337: '09.06.2023',
            2363: '15.09.2023',
            2369: '20.07.2023',
            2376: '05.07.2023',
            2383: '31.07.2023',
            2412: '21.07.2023',
            2429: '29.08.2023',
            2441: '30.05.2023',
            2499: '18.08.2023',
            2503: '11.07.2024',
            2504: '07.08.2023',
            2521: '18.09.2023',
            2583: '23.08.2023',
            2661: ' - ',
            2684: '14.08.2023',
            2738: '17.04.2023',
            2763: '18.09.2023',
            2774: '18.09.2023',
            2781: '29.08.2023',
            2808: '21.07.2023',
            2865: '25.10.2023',
            2901: '',
            3015: '',
            3128: '',
            3131: '20.11.2023',
            3133: ' - ',
            3254: '',
            3340: '',
            3361: '',
            3368: '22.01.2024',
            3370: '01.08.2023',
            3404: '',
            3405: '',
            3406: '',
            3437: '',
            3489: '07.03.2024',
            3494: '07.03.2024',
            3581: '09.04.2024',
            3652: '',
            3699: '',
            3720: '',
            3728: '',
            3732: '',
            3734: '',
            3735: '',
            3748: '',
            3749: '',
            3756: '',
            3757: '',
            3773: '',
            3797: ' - ',
            3799: ' - ',
            3805: ' - ',
            3807: '',
            3808: '',
            3809: '',
            3849: '',
            3890: '',
            3891: '',
            3947: '',
            3955: '',
            3958: ' - ',
            3959: ' - ',
            3964: ' - ',
            3973: '',
            4021: ' - ',
            4027: ' - ',
            4033: '',
            4034: ' - ',
            4035: ' - ',
            4039: '',
            4041: ' - ',
            4059: '',
            4060: '',
            4108: '',
            4110: ' - ',
            4113: ' - ',
            4116: '',
            4117: '',
            4118: '',
            4119: '',
            4122: '',
            4123: '',
            4124: '',
            4128: '',
            4129: '',
            4132: '08.07.2024',
            4138: '',
            4140: '',
            4142: '',
            4145: '',
            4146: '',
            4148: '',
            4149: '',
            4150: '',
            4151: '',
            4152: '',
            4155: ' - ',
            4156: '',
            4157: ' - ',

        }
        for k, v in dict_pr.items():
            if F.is_date(v, "%d.%m.%Y"):
                date = F.strtodate(v, "%d.%m.%Y")
                format_date = F.datetostr(date, "%Y-%m-%d 08:30:00")
                CSQ.custom_request_c(self.bd_naryad,
                                     f"""UPDATE mk SET Дата_завершения = "{format_date}" WHERE Пномер = {k}""")

    @CQT.onerror
    def edit_strukt_move_row(self, direction, *args):
        tbl = self.ui.table_razr_MK
        if tbl.rowCount() < 2:
            return
        print(direction)
        num_row = tbl.currentRow()
        if num_row == -1:
            return
        list_tbl = CQT.list_from_wtabl_c(tbl, rez_dict=True)
        tmp = copy.deepcopy(list_tbl[num_row])
        koef = 0
        if direction == 'up':
            if num_row == 0:
                return
            koef = -1
        if direction == 'down':
            if num_row == tbl.rowCount() - 1:
                return
            koef = 1

        for k, v in list_tbl[num_row + koef].items():
            tbl.item(num_row, CQT.num_col_by_name_c(tbl, k)).setText(v)
        for k, v in tmp.items():
            tbl.item(num_row + koef, CQT.num_col_by_name_c(tbl, k)).setText(v)
        CQT.select_cell(tbl, num_row + koef, 0)

    @CQT.onerror
    def push_strukt_into_db_dse(self, *args):
        tbl = self.ui.table_razr_MK
        if tbl.rowCount() == 0:
            return
        data = CQT.list_from_wtabl_c(tbl, rez_dict=True)
        list_err = []
        list_info = []
        list_dse = CSQ.custom_request_c(self.db_dse,
                                        f"""SELECT Номенклатурный_номер FROM dse WHERE poki = {self.place.poki}""",
                                        one_column=True)
        set_dse = set(list_dse)

        def check_row(item):
            errors = []
            row = f"*{item['ID']}"

            if item['Наименование'] == "":
                text = f'Наименование пусто'
                errors.append({'Строка ID': row,
                               'Ошибка': text})
            if item['Обозначение'] == "":
                text = f'Обозначение пусто'
                errors.append({'Строка ID': row,
                               'Ошибка': text})

            if item['Обозначение'] != '' and item['Обозначение'] in set_dse:
                text = f'ДСЕ уже имеется в БД(не добавлено)'
                list_info.append({'Строка ID': row,
                                  'Ошибка': text})
            if errors:
                return errors

        for item in data:
            rez = check_row(item)
            if rez != None:
                for err in rez:
                    list_err.append(err)
        if list_err:
            CQT.msgboxg_get_table_ok_inf(self, 'Ошибки при разборе структуры', list_err,
                                         style_icon='SP_MessageBoxWarning')
            return
        list_add = []
        for item in data:
            nn = item['Обозначение']
            if nn not in set_dse:
                list_add.append([item['Обозначение'],
                                 item['Наименование'],
                                 item['Примечание'],
                                 item['Ссылка'],
                                 self.place.poki,
                                 ])
        if list_add:
            rez = CSQ.custom_request_c(self.db_dse, f"""INSERT INTO dse (Номенклатурный_номер, Наименование,
                         Примечание, Путь_docs, poki) VALUES ({', '.join(['?'] * len(list_add[0]))});""",
                                       list_of_lists_c=list_add)
            if rez:
                if list_info:
                    CQT.msgboxg_get_table_ok_inf(self, 'Успешно', list_info, )
                else:
                    CQT.msgbox('Успешно')
                return
            CQT.msgbox(f'Ошибка выгрузки')

    def get_res_as_file(self):
        tbl = self.ui.tbL_tkp_list
        row = CQT.get_dict_line_form_tbl(tbl)
        if len(row):
            nom_tkp = row['Номер ТКП']
            data = CSQ.custom_request_c(self.db_resxml, f"""SELECT * FROM predv_res WHERE Имя = '{nom_tkp}';""",
                                        rez_dict=True)
            if data:
                stukt = F.from_binary_pickle(data[0]['data'])
                puth = CQT.f_dialog_save(self, 'Сохранение структуры', CMS.tmp_dir(), '*.json')
                F.write_json_c(stukt, puth, lines=False)
                return
            else:
                CQT.msgbox('Не корректные данные')
                return
        else:
            CQT.msgbox('Не создана реурсная')
            return

    def tbl_preview_on_header_click(self, ind):
        GKPL.tbl_preview_on_header_click(self, ind)

    def tbl_pl_gaf_svod_mouseMoveEvent(self, e):
        self.current_kpl_table = 'tbl_pl_gaf_svod'
        GVKPL.hover_tbl_pl_gaf_svod(self, e)

    def tbl_preview_mouseMoveEvent(self, e):
        self.current_kpl_table = 'tbl_preview'
        GKPL.hover_tbl_preview(self, e)

    @CQT.onerror
    def tbl_pl_gaf_mouseMoveEvent(self, e):
        self.current_kpl_table = 'tbl_pl_gaf'
        GKPL.hover_tbl_pl_gaf(self, e)

    @CQT.onerror
    def tbl_kal_pl_header_mouseMoveEvent(self, e):
        GKPL.hover_tbl_kal_pl_header(self, e)

    def getPos(self, event):
        x = event.pos().x()
        y = event.pos().y()
        prc_x = round(x / self.ui.lbl_shema.width(), 2)
        prc_y = round(y / self.ui.lbl_shema.height(), 2)
        CQT.statusbar_text(self, f'Mouse coords: ( {prc_x} : {prc_y} )')
        F.copy_bufer(str(prc_x) + ";" + str(prc_y))

    def key_handler(self, key_val: int, set_modifiers: set = ()):
        if CQT.focus_is_QTableWidget():
            if key_val == QtCore.Qt.Key_Up:
                focus: QtWidgets.QTableWidget = QtWidgets.QApplication.focusWidget()
                if not focus == None:
                    if 'filtr' in focus.objectName():
                        data = CQT.get_spis_znach_for_filtr(self, focus)
                        name_field = focus.horizontalHeaderItem(focus.currentColumn()).text()
                        if name_field in data:
                            list_vals = data[name_field]
                            focus.item(0, focus.currentColumn()).setText(list_vals)

        if self.ui.tbl_list_orders_mold.hasFocus():
            if key_val == 16777268:
                TTKZ.load_form_rs_for_molding(self)
        if self.ui.tbl_list_orders_mold_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_list_orders_mold_filtr, self.ui.tbl_list_orders_mold)
        if self.ui.tbl_data_mold_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_data_mold_filtr, self.ui.tbl_data_mold)
        if self.ui.tbl_data_mold_tch_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_data_mold_tch_filtr, self.ui.tbl_data_mold_tch)
        if self.ui.tbl_rc_autopause_filtr.hasFocus(): #29.12.2025
            if key_val == 16777220:
                IND.apply_autoschedule_filter(self)
                IND.load_breaks_tab(self)
        if self.ui.tbl_rc_autopause_filtr_2.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_rc_autopause_filtr_2, self.ui.tbl_rc_autopause_2)
        if self.ui.tbl_data_mold_tch_res_product_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_data_mold_tch_res_product_filtr,
                                  self.ui.tbl_data_mold_tch_res_product)
        if key_val == 80 and set_modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.refill_tbl_into_msgbox_get_table(self, QtWidgets.QApplication.focusWidget())
        if self.ui.tbl_tabeli_person.hasFocus():
            if key_val == 16777220:
                TABEL.update_val(self)
        if self.ui.tbl_kal_pl.hasFocus():
            if key_val == 16777220:
                KPL.tbl_kal_pl_cellChanged(self)
            if key_val in (73, 1064) and 'alt' in CQT.get_key_modifiers(self):
                KPL.get_history(self)
            if key_val == 16777223:  # delete
                KPL.delete_from_cell(self)
        if self.ui.tbl_tabeli_person_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_tabeli_person_filtr, self.ui.tbl_tabeli_person)
        if self.ui.tbl_equipment_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_equipment_filtr, self.ui.tbl_equipment)
        if self.ui.tbl_pull_etaps.hasFocus():
            if key_val == 16777220:
                POZPL.calc_row_tbl_pull_etaps(self)
        if self.ui.le_mosh_state.hasFocus():
            if key_val == 16777220:
                STATE.load_tbl(self)
        if self.ui.tbL_tkp_list_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbL_tkp_list_filtr, self.ui.tbL_tkp_list)
        if self.ui.tbl_filtr_edit_txt_res.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_edit_txt_res, self.ui.tbl_edit_txt_res)
        if self.ui.tbl_state_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_state_filtr, self.ui.tbl_state)
        if self.ui.le_tkp_dir_res.hasFocus():
            if key_val == 16777220:
                CVO.edit_tkp_dir_res(self)
        if self.ui.le_tkp_dir_shablons.hasFocus():
            if key_val == 16777220:
                CVO.edit_tkp_dir_shablons(self)
        if self.ui.le_tkp_name_res.hasFocus():
            if key_val == 16777220:
                CVO.edit_le_tkp_name_res(self)
        if self.ui.le_pl_find_field.hasFocus():
            if key_val == 16777220:
                KPL.find_field(self)
        if self.ui.pl_cmb_filtrs.hasFocus():
            if key_val == QtCore.Qt.Key_Delete:
                KPLUF.del_filt_pl_user_filtrs(self)
        if self.ui.tbl_pl_gaf_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_pl_gaf_filtr, self.ui.tbl_pl_gaf)
                self.ui.tbl_pl_gaf.setRowHidden(0, True)
                self.ui.tbl_pl_gaf.setRowHidden(1, True)
                GVKPL.load_svod(self)

        if self.ui.tbl_filtr_kal_pl.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_kal_pl, self.ui.tbl_kal_pl)
                CMS.apply_gui_groups(self)
        if self.ui.tbl_vacant_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_vacant_filtr, self.ui.tbl_vacant)
        if self.ui.tbl_emploee_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_emploee_filtr, self.ui.tbl_emploee)
        if self.ui.tbl_tabeli_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_tabeli_filtr, self.ui.tbl_tabeli)
        if self.ui.tbl_rc_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_rc_filtr, self.ui.tbl_rc)
        if self.ui.tbl_rc.hasFocus():
            if key_val == 16777220:
                row = self.ui.tbl_rc.currentRow()
                column = self.ui.tbl_rc.currentColumn()
                IND.cellChanged(self, row, column)

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

        if self.ui.tbl_selector_proj_view_zamech_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_selector_proj_view_zamech_filtr,
                                  self.ui.tbl_selector_proj_view_zamech)
        if self.ui.tbl_selector_proj_view.hasFocus():
            if key_val == 16777220:
                if self.ui.tbl_selector_proj_view.currentColumn() == CQT.num_col_by_name_c(
                        self.ui.tbl_selector_proj_view, 'Примечание'):
                    self.SLCT_edit_primech(self.ui.tbl_selector_proj_view.currentRow(),
                                           self.ui.tbl_selector_proj_view.currentColumn())
        if self.ui.tbl_selector_proj_view_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_selector_proj_view_filtr, self.ui.tbl_selector_proj_view)
        if self.ui.tbl_selector_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_selector_filtr, self.ui.tbl_selector)
        if self.ui.tbl_obespechenie_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_obespechenie_filtr, self.ui.tbl_obespechenie)
        if self.ui.tbl_zamech_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_zamech_filtr, self.ui.tbl_zamech)
        if self.ui.tbl_filtr_nomenkl.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_nomenkl, self.ui.table_nomenkl)
        if self.ui.tbl_filtr_mk.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_filtr_mk, self.ui.table_spis_MK)
        if self.ui.tbl_pl_tabel_month_filtr.hasFocus():
            if key_val == 16777220:
                CMS.apply_filtr_c(self, self.ui.tbl_pl_tabel_month_filtr, self.ui.tbl_pl_tabel_month)

            if key_val == 16777220:
                self.corr_mk(self.ui.table_spis_MK.currentRow(), self.ui.table_spis_MK.currentColumn())
            if key_val == 16777222 and set_modifiers == QtCore.Qt.ShiftModifier:  # Key_Insert
                self.create_and_add_res_to_mk()
        if self.ui.table_zayavk.hasFocus() == True:
            if key_val == QtCore.Qt.Key_Delete:
                self.ui.table_zayavk.removeRow(self.ui.table_zayavk.currentRow())

    def keyReleaseEvent(self, e):
        self.key_handler(e.key(), e.modifiers())

    @CQT.onerror
    def select_nom_jur_vneplan(self,*args):
        self.ui.cmb_nom_jur_vneplan.setCurrentText('')
        query = f"""SELECT 
           jur_vnepl.Пномер,
           jur_vnepl.МК,  
           jur_vnepl.Дата,
           jur_vnepl.ФИО,
           jur_vnepl.Запрос,
           jur_vnepl.Кплан_номер,
           jur_vnepl.Примечание_цех_техн,
           jur_vnepl.Дата_ответ,
           jur_vnepl.Ответ,
           jur_vnepl.Статус,
           jur_vnepl.Журнал_замеч_номер,
           jur_vnepl.Утверждено,
           jur_vnepl.Номер_наряда_с_ошибкой,
           jur_vnepl.Номер_внепланового_наряда
             FROM jur_vnepl 
                               INNER JOIN mk ON mk.Пномер == jur_vnepl.МК  
                               INNER JOIN plan ON plan.Пномер == mk.НомКплан  
                               WHERE jur_vnepl.Номер_нов_мк == 0 
                               and  mk.Статус == 'Открыта' 
                               and  jur_vnepl.Статус != 'Отклонено' 
                               and plan.poki == {self.place.poki};"""
        list_vneplan = CSQ.custom_request_c(self.bd_naryad, query, one_column=False, hat_c=False, rez_dict=True,
                                            attach_dbs=self.db_kplan)

        result = CQT.msgboxg_get_table(self,'Выбор внеплана',list_vneplan,"Выбор",
                                    selection_from_tbl=True,ExtendedSelection=False,
                                    selectRows=True,sortingEnabled=True)
        if result:
            self.ui.cmb_nom_jur_vneplan.setCurrentText(result['Пномер'])




    @CQT.onerror
    def cmb_tip_click(self, nom):
        self.fill_cmb_dorez(True)
        self.ui.btn_select_nom_jur_vneplan.setEnabled(False)
        if self.ui.cmb_tip_mk.currentText() == '':
            self.fill_cmb_dorez(True)
            return
        if self.DICT_TIP_MK[self.ui.cmb_tip_mk.currentText()]['Пномер'] == 2:  # Дорезка
            self.fill_cmb_dorez()
            self.fill_cmb_nom_jur_vneplan()
            self.ui.btn_select_nom_jur_vneplan.setEnabled(True)
            return
        if self.DICT_TIP_MK[self.ui.cmb_tip_mk.currentText()]['Пномер'] == 5:  # Доработка(без дорезки)
            self.fill_cmb_dorab()
            self.fill_cmb_nom_jur_vneplan()
            self.ui.btn_select_nom_jur_vneplan.setEnabled(True)
            return

    def fill_cmb_dorab(self, clear=False):
        if clear:
            self.ui.cmb_tip_dorez.clear()
        else:

            self.ui.cmb_tip_dorez.addItems([*self.DICT_TIP_DORAB.keys()])
            self.ui.cmb_tip_dorez.adjustSize()

    def fill_cmb_dorez(self, clear=False):
        if clear:
            self.ui.cmb_tip_dorez.clear()
        else:
            self.ui.cmb_tip_dorez.addItem('')
            self.ui.cmb_tip_dorez.addItems([*self.DICT_TIP_DOREZ.keys()])
            self.ui.cmb_tip_dorez.adjustSize()

    def fill_cmb_nom_jur_vneplan(self, clear=False):
        if clear:
            self.ui.cmb_nom_jur_vneplan.clear()
        else:
            self.ui.cmb_nom_jur_vneplan.clear()
            self.ui.cmb_nom_jur_vneplan.addItem('')
            query = f"""SELECT jur_vnepl.Пномер, jur_vnepl.Запрос FROM jur_vnepl 
                        INNER JOIN mk ON mk.Пномер == jur_vnepl.МК  
                        INNER JOIN plan ON plan.Пномер == mk.НомКплан  
                        WHERE jur_vnepl.Номер_нов_мк == 0 and  mk.Статус == 'Открыта' 
                        and  jur_vnepl.Статус != 'Отклонено' 
                         and plan.poki == {self.place.poki};"""
            list_vneplan = CSQ.custom_request_c(self.bd_naryad, query, one_column=False, hat_c=False, rez_dict=True,
                                                attach_dbs=self.db_kplan)
            for i, item in enumerate(list_vneplan):
                self.ui.cmb_nom_jur_vneplan.addItem(str(item['Пномер']))
                self.ui.cmb_nom_jur_vneplan.setItemData(i + 1, item['Запрос'], QtCore.Qt.ToolTipRole)

            self.ui.cmb_nom_jur_vneplan.adjustSize()

    def load_lbl_schema(self):
        self.ui.tabW_rab_places.blockSignals(True)
        self.ui.tabW_rab_places.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabW_rab_places, 'Схема'))
        self.ui.tabW_rab_places.blockSignals(False)
        self.SIZE_SCHEMA_LBL = self.ui.lbl_shema.maximumSize()
        self.ui.lbl_shema.setScaledContents(False)

    @CQT.onerror
    def tab_addit_info_poz_gant_click(self, ind):
        GKPL.tab_addit_info_poz_gant_click(self, ind)

    @CQT.onerror
    def tabW_rab_places_click(self, ind):
        if CQT.number_table_by_name_c(self.ui.tabW_rab_places, 'Схема') == ind:
            IND.select_schema(self)

    def validate_main_tab(self, tab_bar, from_index, to_index): # 09.02.2026
        if not USRCNF.Config.place.ИспПроверкуНаВнесенныйТипПланаОтделомТО or not CMS.is_user_profession('Главный технолог'):# CMS.is_user_profession('Главный технолог')::
            return True
        not_available_tabs = (
            'Создание МК',
            'Номенклатура',
            'Маршрутные карты',
        )
        name = tab_bar.tabText(to_index)
        if name in not_available_tabs:
            query = f"""
    SELECT plan.Пномер AS КПЛ, пл_топ.Вид, пл_топ.Отв_технолог
    FROM пл_топ 
    INNER JOIN plan ON plan.Пномер = пл_топ.НомПл 
    WHERE пл_топ.Вид = 1 AND DATE(plan.Дата_внесения) >= DATE("2023-08-01") and plan.Статус IN (1,2,3,7) and plan.poki = {self.place.poki}"""
            result = CSQ.custom_request_c(USRCNF.Config.project.db_kplan, query, rez_dict=True)
            if result:
                CQT.msgboxg_get_table_ok_inf(
                    self,
                    f'Найдено {len(result)} позиций c пустым полем пл_топ.Вид. Необходима срочная корректировка ',
                    result
                )
                return False
        return True

    @CQT.progress_decorator
    def tab_click(self, ind, hook_prog_bar=None):

        if CMS.kontrol_ver(self.versia, 'МКарты') == False:
            quit()
        tab = self.ui.tabWidget
        # Валидация работающая на проф: "Главный технолог" на предмет проставленного пл_топ.Вид
        main_tech_validator = CQT.TabValidator(tab_widget=tab, validate_func=self.validate_main_tab)
        hook_prog_bar.set(10)
        hook_prog_bar.text('Обработка')
        if tab.currentIndex() == 2:  # номенклатура
            self.zapoln_tabl_nomenkl()
        if tab.currentIndex() == 3:  # брак
            if F.existence_file_c(self.bd_act):
                usl = "Категория_брака == 'Неисправимый' AND Ном_мк_повт_изг == ''"
                spis_itog = CSQ.find_in_db_c(self.bd_act, 'act', {}, siroe_usl=usl, hat_c=True)
            else:
                spis_itog = [["Не найдена база данных BDact"]]
            CQT.fill_wtabl_old_c(self, spis_itog, self.tabl_brak, 0, 0, (), (), 200, True, '')
        if tab.currentIndex() == CQT.number_table_by_name_c(tab, 'Маршрутные карты'):  # мк
            self.load_table_mk()
        if tab.tabText(ind) == 'Загрузка рабочих центров':
            if self.ui.tabWidget_4.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_4, 'Рабочие места'):
                IND.zagruzka_rc(self)
                self.load_lbl_schema()
            IND.add_list_of_months_to_cmb(self)
        if tab.tabText(ind) == 'Замечания по МК':
            ZMCH.load_table_add(self)
            ZMCH.load_table_zamech(self)
        if tab.tabText(ind) == 'Селектор':
            SLCT.load_table_db(self)
            SLCT.load_table_add(self)
        if tab.tabText(ind) == 'Объемно-календарное планирование':
            user = F.user_full_namre()  # self.DICT_EMPLOEE_FULL[user] = {'Подразделение':'Планово-диспетчерский отдел Производства'}
            if user in self.DICT_EMPLOEE_FULL:
                if self.DICT_EMPLOEE_FULL[user]['Подразделение'] == 'Планово-диспетчерский отдел Производства':
                    val = CMS.load_tmp_val('count_exeptions_compare_erp_mes', autotype=True, db_kplan=self.db_kplan)
                    if val:
                        if CQT.msgboxgYN(
                                f'Обнаружено {val} несоответствий при сверке КПЛ и ЕРП. Необходимо провести корректровку.\nЗапустить проверку?',
                                icon=QtWidgets.QMessageBox.Information):
                            KPL.check_kpl_by_erp(self)

            CMS.save_tmp_path('kpl_bool_load_zav', '0')
            KPL.update_tabels(self)
        if tab.tabText(ind) == 'Инвестиции производство':
            INVPR.load_tbl(self)
            INVPR.load_tbl_add(self)
        if tab.tabText(ind) == 'Штат':
            self.push_work_plan_fact.fill_tbl()

            # query = f"""SELECT *
            #            FROM koef_epml_per_ton"""
            # self.LIST_STATE_KOEF = CSQ.custom_request_c(self.Data_plan.db_state, query, rez_dict=True)
            # query = f"""SELECT *
            #            FROM napravlenie"""
            # self.DICT_NAPR_KPLAN = F.deploy_dict_c(CSQ.custom_request_c(self.Data_plan.db_kplan, query, rez_dict=True),
            #                                       'name')
            STATE.load_tbl(self)

            self.ui.splitter_state.setSizes([400, 180])

    def tab_click10(self, ind: int):
        if CMS.kontrol_ver(self.versia, 'МКарты') == False:
            quit()
        self.push_work_plan_fact.fill_tbl()

    def tab_zagruzka_rc(self, nom):
        if self.ui.tabWidget_4.tabText(nom) == 'Рабочие места':
            IND.zagruzka_rc(self)
            self.load_lbl_schema()
        if self.ui.tabWidget_4.tabText(nom) == 'АвтоПерерывы':
            IND.load_breaks_tab(self)
        if self.ui.tabWidget_4.tabText(nom) == 'Список сотрудников':
            IND.load_emploee(self)
        if self.ui.tabWidget_4.tabText(nom) == 'Вакантные места':
            IND.load_deficit_emploee(self)
        if self.ui.tabWidget_4.tabText(nom) == 'Табели':
            IND.add_list_of_months_to_cmb(self)
        if self.ui.tabWidget_4.tabText(nom) == 'Оборудование':
            EQRC.load_equipment(self)

    def tab_click2(self, nom):
        self.ui.fr_cr_mk_btns.setHidden(False)
        self.ui.gr_select_proj.setHidden(False)
        if self.ui.tabWidget_2.tabText(nom) == 'Разработка МК':
            self.ui.btn_vigruzka_norm_mat.setEnabled(True)
            self.list_vars_vo = []
            self.spis_poziciy_rez_ruchnoi = []
            self.res = ''
        if self.ui.tabWidget_2.tabText(nom) == 'Создание МК из *.XML':
            self.ui.btn_vigruzka_norm_mat.setEnabled(False)
        if self.ui.tabWidget_2.tabText(nom) == 'Корректировка':
            self.load_mk_to_edit()
            self.load_xml_to_edit()
            self.ui.fr_cr_mk_btns.setHidden(True)
            self.ui.gr_select_proj.setHidden(True)

        if self.ui.tabWidget_2.tabText(nom) == 'ТКП':
            self._mk_dirty.mark_clean() #25.12.2025
            CMS.load_tkp_list(self, self.db_dse, CMS.DICT_NAME_SQL['tkp'], self.ui.tbL_tkp_list,
                              self.ui.tbL_tkp_list_filtr, {})
            list_technologs = [_ for _ in self.DICT_EMPLOEE_FULL.keys() if
                               self.DICT_EMPLOEE_FULL[_]['Подразделение'] == 'Технологический отдел Производства']
            list_technologs.sort()
            self.ui.cmb_tkp_otv_techn.clear()
            self.ui.cmb_tkp_otv_techn.addItem('')
            self.ui.cmb_tkp_otv_techn.addItems(list_technologs)
            CVO.load_le_tkp_dir_shablons(self)
            CVO.load_le_tkp_dir_res(self)

            self.ui.cmb_year_for_select_tkp.blockSignals(True)
            self.ui.cmb_year_for_select_tkp.addItems([str(year) for year in range(2023, F.now('').year + 1)])
            self.ui.cmb_year_for_select_tkp.setCurrentIndex(self.ui.cmb_year_for_select_tkp.count() - 1)
            self.ui.chk_deleted_for_select_tkp.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.ui.cmb_year_for_select_tkp.blockSignals(False)
            self.ui.fr_cr_mk_btns.setHidden(True)
            self.ui.gr_select_proj.setHidden(False)
        if self.ui.tabWidget_2.tabText(nom) == 'РС для литья':
            TTKZ.load_form_rs_for_molding(self)

    def tab_mk_click(self, nom):
        self.glob_nom_mk_obesp = ''
        if self.ui.tabWidget_3.tabText(nom) == 'Обеспечение':
            OBSP.load_obesp_mk(self)

    def clck_tbl_rc(self):
        IND.clck_tbl_rc(self)

    def load_xml_to_edit(self):
        if not CMS.user_access(self.bd_naryad, 'mkart_mk_korrect_res_xml', F.user_name()):
            return
        tbl = self.ui.table_spis_MK
        if tbl.currentRow() == -1:
            CQT.msgbox(f'Не выбрана МК')
            return
        nk_nom_mk = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_mk = int(tbl.item(tbl.currentRow(), nk_nom_mk).text())
        query = f'''SELECT data, Head FROM xml 
                WHERE Номер_мк == {int(nom_mk)}
                            '''
        rez_xml = CSQ.custom_request_c(self.db_resxml, query)
        xml = rez_xml[-1][0]
        xml_head = rez_xml[-1][1]
        if xml != '':
            xml = XML.spisok_iz_xml(str_f=xml)
        self.ui.txt_xml.setPlainText(pprint.pformat(xml))
        return

    def load_mk_to_edit(self):
        if not CMS.user_access(self.bd_naryad, 'mkart_mk_korrect_res_xml', F.user_name()):
            return
        tbl = self.ui.table_spis_MK
        if tbl.currentRow() == -1:
            CQT.msgbox(f'Не выбрана МК')
            return
        nk_nom_mk = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_mk = int(tbl.item(tbl.currentRow(), nk_nom_mk).text())
        res = CSQ.custom_request_c(self.db_resxml, f'''SELECT data FROM res WHERE Номер_мк == {nom_mk};''', hat_c=False,
                                   one=True)
        if res == False:
            CQT.msgbox(f'ОШибка')
            return
        try:
            res = F.from_binary_pickle(res[-1][0])
            self.ui.txt_res.setPlainText(pprint.pformat(res))
            list_lists_txt = [['dse', 'oper', 'row']]
            dse = ''
            naim = ''
            oper = ''
            oper_nom = ''
            list_oper_reset = ["'Материалы':", "'ПКИ':", "'Параметрика':", "'Прим': ",
                               "'Способы_получения_материала': ", "'Ссылка': ", "'Уровень': ", "'кол_во_инф':"]
            for row in pprint.pformat(res).split('\n'):
                if "'dreva_kod':" in row:
                    dse = ''
                    naim = ''
                    oper = ''
                    oper_nom = ''
                for name in list_oper_reset:
                    if name in row:
                        oper = ''
                        oper_nom = ''
                if "'Номенклатурный_номер':" in row:
                    dse = row.split(': ')[-1].replace("'", "")[:-1]
                if "'Наименование':" in row:
                    naim = row.split(': ')[-1].replace("'", "")[:-1]
                if "'Опер_наименование':" in row:
                    oper = row.split(': ')[-1].replace("'", "")[:-1]
                if "'Опер_номер':" in row:
                    oper_nom = row.split(': ')[-1].replace("'", "")[:-1]
                dse_naim = ''
                if dse != '' and naim != '':
                    dse_naim = f'{dse} {naim}'
                oper_nom_oper = ''
                if oper_nom != '' and oper != '':
                    oper_nom_oper = f'{oper_nom} {oper}'
                list_lists_txt.append([dse_naim, oper_nom_oper, row])

            dse = ''
            oper = ''
            for i in range(len(list_lists_txt) - 1, 0, -1):
                if "'Операции': " in list_lists_txt[i][2]:
                    oper = ''
                if list_lists_txt[i][0] == '':
                    list_lists_txt[i][0] = dse
                else:
                    dse = list_lists_txt[i][0]
                if list_lists_txt[i][1] == '':
                    list_lists_txt[i][1] = oper
                else:
                    oper = list_lists_txt[i][1]

            CQT.fill_wtabl(list_lists_txt, self.ui.tbl_edit_txt_res, set_editeble_col_nomera={'row'}, height_row=24,
                           auto_type=False)
            CQT.fill_filtr_c(self, self.ui.tbl_filtr_edit_txt_res, self.ui.tbl_edit_txt_res, hidden_scroll=True)


        except:
            CQT.msgbox(f'Некорректные данные')
        return

    def generate_txt_res(self):
        tbl = self.ui.tbl_edit_txt_res
        if tbl.rowCount() == 0:
            return

        list_form_tbl = CQT.list_from_wtabl_c(tbl, '', only_visible=False)
        txt_list = [_[-1] for _ in list_form_tbl]
        txt = '\n'.join(txt_list)
        self.ui.txt_res.setPlainText(txt)
        CQT.msgbox('Готово', time_life=0.5)

    def edit_res_xml(self):
        if not CMS.user_access(self.bd_naryad, 'мкарт_создмк_корректировка_рес', F.user_name()):
            return
        tbl = self.ui.table_spis_MK
        if tbl.currentRow() == -1:
            CQT.msgbox(f'Не выбрана МК')
            return
        nk_nom_mk = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_mk = int(tbl.item(tbl.currentRow(), nk_nom_mk).text())
        if self.ui.tabWidget_5.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_5, 'RES'):
            res = self.ui.txt_res.toPlainText()
            res = eval(res)
            blob = F.to_binary_pickle(res)
            if not CQT.msgboxgYN(f'ТОчно внести правку?'):
                return
            CSQ.custom_request_c(self.db_resxml, f'''UPDATE res SET data = ? WHERE Номер_мк == ?;''',
                                 list_of_lists_c=[blob, int(nom_mk)])

        if self.ui.tabWidget_5.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_5, 'XML'):
            if not CQT.msgboxgYN(f'ТОчно внести правку?'):
                return
            xml = self.ui.txt_xml.toPlainText()
            if xml.strip() == '':
                blob = ''
            else:
                xml = eval(xml)
                blob = F.to_binary_pickle(xml)
            CSQ.custom_request_c(self.db_resxml, f'''UPDATE xml SET data = ? WHERE Номер_мк == ?;''',
                                 list_of_lists_c=[blob, int(nom_mk)])

        self.ui.txt_res.setPlainText("")
        self.ui.txt_xml.setPlainText("")
        CQT.clear_tbl(self.ui.tbl_edit_txt_res)
        CQT.msgbox('Готово', time_life=0.5)

    def CVO_path_kd_dbl_clk(self, r, c):
        CMS.path_kd_dbl_clk(self.ui.tbL_tkp_list, r, c)

    def SLCT_click(self):
        CMS.on_section_resized(self)

    def SLCT_edit_primech(self, row, column):
        if self.ui.tbl_selector_proj_view.hasFocus():
            SLCT.edit_primech(self, row, column)

    def SLCT_edit_zamech_from_view(self, row, column):
        SLCT.edit_zamech_from_view(self, row, column)

    def SLCT_add_new_zamech(self, row, column):
        SLCT.add_new_zamech(self, row, column)

    def SLCT_selector_proj_view_itemSelection(self):
        SLCT.selector_proj_view_itemSelection(self)

    def SLCT_select_zamech(self, row, column):
        SLCT.select_zamech(self, row, column)

    def OBSP_select_obesp_po_mk_from_table(self, row, column):
        OBSP.select_obesp_po_mk_from_table(self, row, column)

    def IND_cellChanged(self, row, column):
        if self.ui.tbl_rc.hasFocus():
            IND.cellChanged(self, row, column)

    def load_table_mk(self, fitr=''):
        self.load_tab_mk()
        tbl = self.ui.table_spis_MK
        CMS.fill_filtr_c(self, self.ui.tbl_filtr_mk, tbl, fitr, hidden_scroll=True)
        CMS.update_width_filtr(tbl, self.ui.tbl_filtr_mk)
        nk_ststus = CQT.num_col_by_name_c(self.ui.tbl_filtr_mk, 'Статус')
        self.ui.tbl_filtr_mk.item(0, nk_ststus).setText('=Открыта')
        self.ui.tbl_filtr_mk.item(0, CQT.num_col_by_name_c(self.ui.tbl_filtr_mk, 'Дата_завершения')).setText('!*')
        CMS.apply_filtr_c(self, self.ui.tbl_filtr_mk, tbl)
        # === процент выполнения====
        nk_nom_mk = CQT.num_col_by_name_c(tbl, 'Пномер')
        nk_progress = CQT.num_col_by_name_c(tbl, 'Прогресс_01')
        if nk_progress != None:
            conn, cur = CSQ.connect_bd(self.db_resxml)
            for i in range(tbl.rowCount()):
                if not tbl.isRowHidden(i):
                    query = f'''SELECT data FROM res WHERE Номер_мк == {int(tbl.item(i, nk_nom_mk).text())}
                                        '''
                    res = F.from_binary_pickle(CSQ.custom_request_c(self.db_resxml, query, conn)[-1][0])
                    if res == False:
                        CSQ.close_bd(conn, cur)
                        CQT.msgbox(f'БД занята пробуй позже')
                        return
                    if res == None:
                        tbl.item(i, nk_progress).setText('0|0')
                    else:
                        tbl.item(i, nk_progress).setText(CMS.percent_of_completion_c(res, '01'))
                else:
                    tbl.item(i, nk_progress).setText('0|0')

            CQT.fill_progress_c(self, tbl, nk_progress)
            CSQ.close_bd(conn, cur)
        # =======
        tbl.selectRow(tbl.rowCount() - 1)
        tbl.scrollToBottom()

    def zaversh_naryad(self, nom_nar, conn):
        custom_request_c = f'''SELECT ФИО, Фвремя, ФИО2, Фвремя2 FROM naryad WHERE Пномер == {nom_nar}'''
        naryad = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True, conn=conn)[0]
        flag_zav = True
        if naryad['ФИО'] == "" and naryad['ФИО2'] == "":
            flag_zav = False
        if flag_zav:
            if naryad['ФИО'] != "":
                if naryad['Фвремя'] == "":
                    flag_zav = False
        if flag_zav:
            if naryad['ФИО2'] != "":
                if naryad['Фвремя2'] == "":
                    flag_zav = False
        return flag_zav

    def check_zaversheni_naruady(self, mkarti: list) -> bool:
        '''
            True if all naruads closed

            19.06.2025 (Изменение SQL запроса)
            1. В выборке журналов инициализируется колонка Дата_с_вычетом - представления
                Дата завершения - 2 часа
            2. После определения day_before(День начала) -> day(День конца) определяем разницу между этими днями
                Если разница между днями >= 1 и при day_before(День начала) != day_deducation(День конца со смещением)
                Возвращаем запись
        '''
        list_err = []
        custom_request_c = f'''       
        SELECT *
          FROM (
                   SELECT RowNum,
                          Пномер,
                          Статус,
                          Дата,
                          Штамп,
                          Номер_наряда,
                          ФИО,
                          Подытог,
                          Пномер_mk,
                          day,
                          day_before,
                          day_deduction,
                          CASE WHEN day = day_before THEN 1 ELSE 0 END AS into_day,
                          CASE WHEN Подытог > 15 * 60 THEN 0 ELSE 1 END AS less_15h,
                          (CAST(day AS INTEGER) - CAST(day_before AS INTEGER)) as РазницаДней
                     FROM (
                              SELECT RowNum,
                                     Пномер,
                                     Статус,
                                     Дата,
                                     Штамп,
                                     Номер_наряда,
                                     ФИО,
                                     Подытог,
                                     Пномер_mk,
                                     day,
                                     strftime("%d", Дата_с_вычетом) as day_deduction,
                                     CASE WHEN Статус = "Начат" THEN day ELSE lag(strftime('%d', Дата) ) OVER (ORDER BY RowNum) END AS day_before
                                FROM (
                                         SELECT ROW_NUMBER() OVER (ORDER BY ФИО, Дата, Пномер) RowNum,
                                                Пномер,
                                                Статус,
                                                Дата,
                                                Штамп,
                                                Номер_наряда,
                                                ФИО,
                                                Подытог,
                                                Пномер_mk,
                                                Дата_с_вычетом,
                                                strftime('%d', Дата) AS day
                                           FROM (
                                                    SELECT jurnal.Пномер,
                                                           jurnal.Статус,
                                                           jurnal.Дата,       
                                                           CASE 
                                                                WHEN jurnal.Статус IN ('Завершен', 'Приостановлен') AND CAST(strftime('%H', jurnal.Дата) AS INTEGER) <= 2
                                                                THEN DATETIME(jurnal.Дата, '-120 minutes')
                                                                ELSE jurnal.Дата
                                                           END as Дата_с_вычетом,                                                             
                                                           jurnal.Штамп,
                                                           jurnal.Номер_наряда,
                                                           jurnal.ФИО,
                                                           jurnal.Подытог,
                                                           mk.Пномер as Пномер_mk
                                                           
                                                      FROM jurnal
                                                           INNER JOIN
                                                           naryad ON naryad.Пномер = jurnal.Номер_наряда,
                                                           mk ON mk.Пномер = naryad.Номер_мк
                                                     WHERE mk.Пномер IN ({CSQ.prepare_list_to_tuple(mkarti)}) 
                                                     
                                                ) 
                                                              ORDER BY ФИО,
                                                              Дата,
                                                              Пномер
                                     )
                                                                         
                          )
               ) WHERE (РазницаДней >= 1 and day_deduction != day_before) or less_15h = 0 
        ;'''
        dict_forgotten_nars = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)

        for i in range(len(dict_forgotten_nars)):
            list_err.append([f'Не корректно отмечены наряды по времени.',
                             f"МК № {dict_forgotten_nars[i]['Пномер_mk']}, Наряд № {dict_forgotten_nars[i]['Номер_наряда']} - {dict_forgotten_nars[i]['ФИО']}\n\n"])

        custom_request_c = f'''SELECT mk.Пномер, mk.Дата, mk.Тип, mk.НомКплан 
        FROM mk WHERE mk.Пномер IN ({CSQ.prepare_list_to_tuple(mkarti)});'''
        list_mk = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)

        for mk in list_mk:
            if mk['Тип'] == 1 and F.strtodate(mk['Дата'], "%y-%m-%d") > F.strtodate('2024-02-01'):
                res_row = \
                    CSQ.custom_request_c(self.db_kplan, f"""SELECT * FROM пл_отк WHERE НомПл = {mk['НомКплан']}""",
                                         rez_dict=True)[0]
                if res_row['Контр_покрытие_ФИО'] == '':
                    list_err.append([f'Не проведены финишный ОТК (Контр_покрытие_ФИО)',
                                     f'МК № {mk}, финишный контроль после покрытия, пассивирования, пескоструйной обработки'])

        self.naryad__ = f'''SELECT mk.Пномер, mk.Тип, mk.НомКплан, naryad.Пномер as Номер_Наряда, naryad.ФИО , 
        naryad.ФИО2, naryad.Подтвержд_вып_фио  FROM mk INNER JOIN naryad ON mk.Пномер = naryad.Номер_мк WHERE
                (naryad.ФИО != "" and naryad.Фвремя == "") or (naryad.ФИО2 != "" and naryad.Фвремя2 == "")'''
        custom_request_c = self.naryad__
        dict_nezversh_nar = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)

        for mk in mkarti:
            for i in range(len(dict_nezversh_nar)):
                if mk == dict_nezversh_nar[i]['Пномер']:
                    list_err.append([f'Не завершены наряды',
                                     f"МК № {mk}, Наряд № {dict_nezversh_nar[i]['Номер_Наряда']} ({dict_nezversh_nar[i]['ФИО']},"
                                     f"{dict_nezversh_nar[i]['ФИО2']})"])

        custom_request_c = f'''SELECT mk.Пномер, mk.Тип, mk.НомКплан, naryad.Пномер as Номер_Наряда, naryad.ФИО , 
        naryad.ФИО2, naryad.Подтвержд_вып_фио  FROM mk INNER JOIN naryad ON mk.Пномер = naryad.Номер_мк WHERE
                naryad.Подтвержд_вып_фио == "" and mk.Пномер IN ({CSQ.prepare_list_to_tuple(mkarti)});'''
        dict_nepodtver_nar = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)
        for i in range(len(dict_nepodtver_nar)):
            if dict_nepodtver_nar[i]['ФИО'] == '' and dict_nepodtver_nar[i]['ФИО2'] == '':
                continue
            list_err.append([f'Не подтверждены наряды.',
                             f"МК № {dict_nepodtver_nar[i]['Пномер']}, Наряд № {dict_nepodtver_nar[i]['Номер_Наряда']} ({dict_nepodtver_nar[i]['ФИО']},"
                             f"{dict_nepodtver_nar[i]['ФИО2']})"])

        if list_err:
            list_err.insert(0, ['Тип', 'Ошибка'])
            CQT.msgboxg_get_table_ok_inf(self, 'Завершение не возможно', list_err, )
            return False

        return True

    def del_xml_from_mk(self, *args):
        if self.ui.tabWidget.tabText(self.ui.tabWidget.currentIndex()) != 'Маршрутные карты':
            return

        tbl = self.ui.table_spis_MK
        nk_nommk = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_mk = int(tbl.item(tbl.currentRow(), nk_nommk).text())
        self.xml_head = 0
        kolvo = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Количество')).text()

        CSQ.custom_request_c(self.db_resxml, """UPDATE xml SET(data,Head) = (?,?) WHERE Номер_мк = ?;""",
                             list_of_lists_c=[['', self.xml_head, int(nom_mk)]])
        CQT.msgbox(f'Успешно')

    def add_xml_to_mk(self, *args):
        if self.ui.tabWidget.tabText(self.ui.tabWidget.currentIndex()) != 'Маршрутные карты':
            return
        tmp_putt = CMS.load_tmp_path("tmp_putt")
        putt_xml = CQT.f_dialog_name(self, 'Выбрать XML', tmp_putt, "Файлы *.xml")
        if putt_xml == '' or putt_xml == '.':
            return
        self.xml_head = int(CMS.XML_check_root_on_project_product_type(putt_xml))
        CMS.save_tmp_path("tmp_putt", putt_xml, True)

        sp_xml_tmp = CMS.podgotovka_xml(self, XML.spisok_iz_xml(putt_xml))
        if sp_xml_tmp == None:
            CQT.msgbox('Файл не корректный')
            return
        self.xml_file = F.load_file_convert_to_binary(putt_xml)

        tbl = self.ui.table_spis_MK
        nk_nommk = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_mk = int(tbl.item(tbl.currentRow(), nk_nommk).text())
        kolvo = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Количество')).text()

        rez = CSQ.custom_request_c(self.db_resxml, f"""SELECT Номер_мк FROM xml WHERE Номер_мк = {int(nom_mk)}""",
                                   one=True)
        if len(rez) == 1:
            CSQ.custom_request_c(self.db_resxml, """INSERT INTO  xml(Номер_мк,data,Head) VALUES (?,?,?);""",
                                 list_of_lists_c=[[int(nom_mk), self.xml_file, self.xml_head]])
        else:
            CSQ.custom_request_c(self.db_resxml, """UPDATE xml SET(data,Head) = (?,?) WHERE Номер_мк = ?;""",
                                 list_of_lists_c=[[self.xml_file, self.xml_head, int(nom_mk)]])
        CQT.msgbox(f'Успешно')

    def calc_xml_res(self, *args):
        if self.ui.tabWidget.tabText(self.ui.tabWidget.currentIndex()) != 'Маршрутные карты':
            return
        tbl = self.ui.table_spis_MK
        nk_nommk = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_mk = int(tbl.item(tbl.currentRow(), nk_nommk).text())

        kolvo = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Количество')).text()
        if not CMS.calc_and_fill_weight_by_xml_and_res(self, self.db_resxml, self.bd_naryad, self.db_mater,
                                                       int(nom_mk), int(kolvo)):
            CQT.msgbox('Ошибка подсчета масс calc_xml_res weight_by_xml')
            return
        CQT.msgbox(f'Успешно')

    def zaversh_mkards(self):
        if not CMS.user_access(self.bd_naryad, 'мкарт_маршрутные_завершить', F.user_name()):
            return
        modifiers = CQT.get_key_modifiers(self)
        tbl = self.ui.table_spis_MK
        nk_nommk = CQT.num_col_by_name_c(tbl, 'Пномер')
        mk_obj = CMS.Marshrut_cards(int(nk_nommk), self.bd_naryad, self.db_resxml, load_resource=False)
        if mk_obj.is_del():
            CQT.msgbox(f'Заблокировано')
            return

        list_mkards = []
        if modifiers == ['shift']:
            for i in range(tbl.rowCount()):
                if tbl.isRowHidden(i) == False:
                    nom_mk = int(tbl.item(i, nk_nommk).text())
                    list_mkards.append(int(nom_mk))
        else:
            nom_mk = int(tbl.item(tbl.currentRow(), nk_nommk).text())
            list_mkards.append(int(nom_mk))

        if not self.check_zaversheni_naruady(list_mkards):
            return

        spis_mk_text = ", ".join([str(_) for _ in list_mkards])
        if CQT.msgboxgYN(f'Будут принудительно завершены и закрыты маршрутные карты №№ {spis_mk_text}'):
            DICT_FILTR = F.deploy_dict_c(
                CSQ.custom_request_c(self.db_mater, f"""SELECT * FROM complex_filtr""", rez_dict=True), 'kod')
            DICT_MAT = F.deploy_dict_c(
                CSQ.custom_request_c(self.db_mater, f"""SELECT * FROM nomen""", rez_dict=True),
                'Код')
            data_for_msg = {}  # ++09.06.2025
            for nom_mk in list_mkards:
                query_mk = f"""
                SELECT
                    mk.Количество,
                    mk.Пномер,
                    mk.Номенклатура,
                    mk.Примечание,
                    mk.Основание,
                    CASE WHEN знпр.№ERP IS NOT NULL 
                        THEN знпр.№ERP 
                        ELSE пл_оуп.№ERP
                    END AS Номер_заказа,  
                    CASE WHEN знпр.№проекта IS NOT NULL 
                       THEN знпр.№проекта 
                       ELSE пл_оуп.№проекта 
                    END AS Номер_проекта
                FROM mk
                INNER JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан
                INNER JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП
                WHERE mk.Пномер = {int(nom_mk)}
                """
                result_col = CSQ.custom_request_c(self.bd_naryad, query_mk, rez_dict=True, one=True,
                                                  attach_dbs=self.db_kplan)
                # result_col = CSQ.custom_request_c(self.bd_naryad,
                #                                   f"""SELECT Количество, Пномер FROM mk WHERE Пномер = {int(nom_mk)};""",
                #                                   rez_dict=True)
                data_for_msg[nom_mk] = result_col
                if result_col == None or result_col == False:
                    CQT.msgbox('Ошибка подсчета масс result_col')
                    return
                kolvo = result_col['Количество']
                if not CMS.calc_and_fill_weight_by_xml_and_res(self, self.db_resxml, self.bd_naryad, self.db_mater,
                                                               int(nom_mk), int(kolvo), DICT_FILTR, DICT_MAT):
                    CQT.msgbox('Ошибка подсчета масс weight_by_xml')
                    return

            conn, cur = CSQ.connect_bd(self.bd_naryad)
            for i in range(tbl.rowCount()):
                nom_mk = int(tbl.item(i, nk_nommk).text())
                if int(nom_mk) in list_mkards:
                    rez = self.zaversh_mk(i, conn=conn, cur=cur)
                    if rez == False:
                        CSQ.close_bd(conn, cur)
                        return
            CSQ.close_bd(conn, cur)
            CQT.msgbox(f'Успешно завершено')
            filtr = CMS.values_of_filter_c(self, self.ui.tbl_filtr_mk)
            self.load_table_mk(filtr)
            try:

                for nom_mk, mk_data in data_for_msg.items():
                    kolvo = mk_data['Количество']
                    nom_pu_r = mk_data['Номер_заказа']
                    nom_pr_r = mk_data['Номер_проекта']
                    prim = mk_data['Примечание']
                    project = mk_data['Номенклатура']
                    osnovanie = mk_data['Основание']
                    msg = f"{F.user_full_namre()}(PC:{os.environ.get('COMPUTERNAME')}) ЗАВЕРШИЛ МК № {str(nom_mk)}:\n{project} - {str(kolvo)} шт.\n{nom_pu_r.strip()} Проект: {nom_pr_r.strip()}\n" \
                          f"Прим.: {prim} {osnovanie}"
                    CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
            # -- 09.06.2025
            # msg = f"{F.user_full_namre()}(PC:{os.environ.get('COMPUTERNAME')}) ЗАВЕРШИЛ МК №№ {spis_mk_text}"
            # CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
            except:
                print('Ошибка отправки в Б24')

    def zaversh_mk(self, row: int = '', conn='', cur=''):
        tbl = self.ui.table_spis_MK
        mode_one = False
        if row == "":
            mode_one = True
            row = tbl.currentRow()
        if row == -1:
            return
        nk_pnom = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_mk = int(tbl.item(row, nk_pnom).text())
        if mode_one:
            if not CQT.msgboxgYN(f'Завершить МК №{nom_mk}?'):
                return
        custom_request_c = f'''SELECT Номер_мк FROM res WHERE Номер_мк == {nom_mk}'''
        rez = CSQ.custom_request_c(self.db_resxml, custom_request_c, rez_dict=True, one=True)
        if rez == False:
            CQT.msgbox(f'Не найдена ресурсная. Нужно переоткрыть')
            return False
        custom_request_c = f'''SELECT mk.Дата_завершения, mk.Статус, mk.Основание  FROM mk
            WHERE Пномер == {nom_mk}'''
        rez = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True, one=True, conn=conn, cur=cur)
        if rez['Дата_завершения'] != '':
            CQT.msgbox(f'Нельзя завершить ранее завершенную МК №{nom_mk}')
            return False
        if rez['Статус'] == "Закрыта":
            CQT.msgbox(f'Нельзя завершить закрытую МК №{nom_mk}')
            return False
        if rez['Статус'] == "Открыта":
            if mode_one:
                conn_res, cur_res = CSQ.connect_bd(self.db_resxml)
                res = CMS.load_res(nom_mk, conn=conn_res, cur=cur_res)
                CSQ.close_bd(conn_res, cur_res)
                neosvoeno = self.check_gotovnost_mk(res)
                flag_zav = False
                if neosvoeno == None:
                    flag_zav = True
                else:
                    F.copy_bufer(neosvoeno)
                    CQT.msgbox(f'(Скопировано в буфер)* По мк {nom_mk} еще не завершено {neosvoeno}')
                    if CQT.msgboxgYN(F'Завершить принудительно?'):
                        flag_zav = True
            else:
                flag_zav = True
            if flag_zav:
                custom_request_c = f'''UPDATE mk SET Статус = "Закрыта", Дата_завершения = "{F.now()}" WHERE Пномер =={nom_mk}'''
                CSQ.custom_request_c(self.bd_naryad, custom_request_c, conn=conn, cur=cur)
                if rez['Основание'] != "":
                    arr_tmp_ass = rez['Основание'].split(';')
                    for nom_acta in arr_tmp_ass:
                        CSQ.update_bd_sql(self.bd_act, 'act', {'Ном_мк_повт_изг': int(nk_pnom)},
                                          {'Пномер': int(nom_acta)}, conn=conn, cur=cur)
                if mode_one:
                    CQT.msgbox(f'Успешно завершено')
                    filtr = CMS.values_of_filter_c(self, self.ui.tbl_filtr_mk)
                    self.load_table_mk(filtr)

    def check_gotovnost_mk(self, res):
        rez = []
        for i in range(len(res)):
            kolich = res[i]['Количество']
            nn = res[i]['Номенклатурный_номер']
            naim = res[i]['Наименование']
            for oper in res[i]['Операции']:
                osv = 0
                zav = 0
                oper_name = f"{oper['Опер_номер']} {oper['Опер_наименование']}"
                if 'Освоено,шт.' in oper:
                    osv = oper['Освоено,шт.']
                if 'Закрыто,шт.' in oper:
                    zav = oper['Закрыто,шт.']
                if osv < kolich:
                    rez.append(f'{nn} {naim} {oper_name} не освоено {kolich - osv} шт.')
                if zav < kolich:
                    rez.append(f'{nn} {naim} {oper_name} не закрыто {kolich - zav} шт.')
        if rez == []:
            return
        return '\n'.join(rez)

    @CQT.onerror
    def update_norm(self, vid=''):  # 26.06.25


        tbl = self.ui.table_spis_MK
        if tbl.currentRow() == -1:
            return
        fl_nar_exist = False
        tbl_row = CQT.get_dict_line_form_tbl(tbl)
        num_kpl = tbl_row['Номер КПЛ']
        type_mk = tbl_row['Тип']
        nk_nommk = CQT.num_col_by_name_c(tbl, 'Пномер')
        nk_count_izd = CQT.num_col_by_name_c(tbl, 'Количество')
        count_izd = F.valm(tbl.item(tbl.currentRow(), nk_count_izd).text())
        nom_mk = tbl.item(tbl.currentRow(), nk_nommk).text()
        if not CQT.msgboxgYN(f'Обновить нормы для МК {nom_mk}?'):
            return
        res = CMS.load_res(int(nom_mk))
        if vid != 'mat':
            journal = [['ДСЕ', 'Операция', 'Атрибут', 'Было', 'Стало']]
        else:
            journal = []
        fl_is_exist_erp_res = False
        res_spec = CMS.ResSpec(nom_mk)
        list_erp_res = res_spec.find_erp_res()
        if list_erp_res:
            fl_is_exist_erp_res = True
        #TODO не учтен случай когда ЕРП РС есть, но нормы в МК меньше, и нужно увеличить не превышая ЕРП рес

        list_nar = CSQ.custom_request_c(USRCNF.Config.project.db_naryad,
                    f'SELECT * FROM naryad WHERE Номер_мк == {int(nom_mk)}',rez_dict=True)
        msg_error_ingr_time =  f'''введен строгий запрет на редактирование маршрутных карт в сторону 
                                               увеличения трудоемкости свыше трудоемкости указанной в рабочей
                                               ресурсной спецификации'''
        if res:
            for i in range(0, len(res)):
                nn = res[i]['Номенклатурный_номер'].strip()
                naim = res[i]['Наименование'].strip()
                tech_card = CMS.Techkards(
                    nn_or_snum=nn,
                    db_dse=self.db_dse,
                    nom_mk=nom_mk,
                    DICT_OP_NAME=self.DICT_OP_NAME, #03.09.25
                    DICT_PROFESSIONS=self.DICT_PROF_CODE
                )
                error = tech_card.check_tk() #03.09.25
                if error is not None:
                    CQT.msgbox(error)
                    return
                list_oper_names = [_ for _ in self.DICT_OP_NAME.keys() if self.DICT_OP_NAME[_]['auto_recalc_pred_tkp']]
                tech_card._update_params_oper(self.DICT_OP_NAME)
                if vid == '' or vid == 'vrem': #05.07.25
                    tech_card.recalc_opers(list_oper_names, self.DICT_OP_NAME)
                for tk_idx, tk in enumerate(tech_card.tk['bodys']):
                    for j, oper in enumerate(tk['opers']):
                        dse = res[i]
                        operation = dse['Операции'][j]

                        spis_per = []
                        rez_spis_instr = []
                        rez_spis_osn = []
                        rez_spis_doc = []

                        materials = []
                        kolvo_koef = self.kol_v_uzel(res, i, 'Наименование', 'Количество', 'Уровень')
                        kolvo_summ = kolvo_koef * int(dse['Количество_ед']) * count_izd
                        for material in oper['materials']:
                            materials.append(CMS.add_mat_into_rez_spis(
                                self,
                                material['cod'],
                                material['naimen'],
                                material['ed_izm'],
                                material['norma'],
                                kolvo_summ,
                                name_oper=oper['name_ver']
                            ))
                        rez_spis_doc.extend(oper['doc_card'])
                        for pereh in oper['perehs']:
                            spis_per.append(pereh['name_ver'])
                            rez_spis_instr.extend(pereh['instrums'])
                            rez_spis_doc.extend(F.clear_free_items(pereh['doc_card']))
                            rez_spis_osn.extend(pereh['prisposobs'])
                        if vid == '':
                            if res[i]['Операции'][j]['Опер_код'] != oper['cod']:
                                res[i]['Операции'][j]['Опер_код'] = oper['cod']
                                journal.append([nn, oper['name_ver'], 'Опер_код', operation['Опер_код'], oper['cod']])
                            if res[i]['Операции'][j]['Опер_наименование'] != oper['name_ver']:
                                res[i]['Операции'][j]['Опер_наименование'] = oper['name_ver']
                                journal.append(
                                    [nn, oper['name_ver'], 'Опер_наименование', operation['Опер_наименование'],
                                     oper['name_ver']])

                            if res[i]['Операции'][j]['Опер_КР'] != oper['kr']:
                                journal.append([nn, oper['name_ver'], 'Опер_КР', operation['Опер_КР'], oper['kr']])
                                res[i]['Операции'][j]['Опер_КР'] = oper['kr']

                            if res[i]['Операции'][j]['Опер_КОИД'] != oper['koid']:
                                journal.append(
                                    [nn, oper['name_ver'], 'Опер_КОИД', operation['Опер_КОИД'], oper['koid']])
                                res[i]['Операции'][j]['Опер_КОИД'] = oper['koid']

                            if res[i]['Операции'][j]['Опер_документы'] != rez_spis_doc:
                                journal.append(
                                    [nn, oper['name_ver'], 'Опер_документы', operation['Опер_документы'], rez_spis_doc])
                                res[i]['Операции'][j]['Опер_документы'] = F.clear_free_items(rez_spis_doc)

                            if res[i]['Операции'][j]['Опер_инстумент'] != rez_spis_instr:
                                journal.append([nn, oper['name_ver'], 'Опер_инстумент', operation['Опер_инстумент'],
                                                rez_spis_instr])
                                res[i]['Операции'][j]['Опер_инстумент'] = F.clear_free_items(rez_spis_instr)

                            if res[i]['Операции'][j]['Опер_оснастка'] != rez_spis_osn:
                                journal.append(
                                    [nn, oper['name_ver'], 'Опер_оснастка', operation['Опер_оснастка'], rez_spis_osn])
                                res[i]['Операции'][j]['Опер_оснастка'] = F.clear_free_items(rez_spis_osn)

                            if res[i]['Операции'][j]['Переходы'] != spis_per:
                                journal.append([nn, oper['name_ver'], 'Переходы', operation['Переходы'],
                                                spis_per])
                                res[i]['Операции'][j]['Переходы'] = spis_per

                        if vid == 'mat':
                            if res[i]['Операции'][j]['Материалы'] != materials:
                                journal.extend(materials) #03.09.25
                                res[i]['Операции'][j]['Материалы'] = materials
                        if vid == 'vrem':
                            tpz_new, tpz_old = oper['t_pz'], operation['Опер_Тпз']
                            if round(res[i]['Операции'][j]['Опер_Тпз'], 3) != round(oper['t_pz'], 3):
                                row_j = [nn, oper['name_ver'], 'Опер_Тпз', tpz_old, oper['t_pz']]
                                if fl_is_exist_erp_res and round(res[i]['Операции'][j]['Опер_Тпз'], 3) < round(oper['t_pz'], 3):
                                    CQT.msgbox(f'{msg_error_ingr_time}:\n{str(row_j)}')
                                    return
                                journal.append(row_j)
                                res[i]['Операции'][j]['Опер_Тпз'] = oper['t_pz']

                            if round(res[i]['Операции'][j]['Опер_Тшт_ед'], 3) != round(oper['t_sht'], 3):
                                row_j = [nn, oper['name_ver'], 'Опер_Тшт_ед', operation['Опер_Тшт_ед'], oper['t_sht']]
                                if fl_is_exist_erp_res and round(res[i]['Операции'][j]['Опер_Тшт_ед'], 3) < round(oper['t_sht'], 3):
                                    CQT.msgbox(f'{msg_error_ingr_time}:\n{str(row_j)}')
                                    return
                                journal.append(row_j)
                                res[i]['Операции'][j]['Опер_Тшт_ед'] = oper['t_sht']
                            if round(res[i]['Операции'][j]['Опер_Тшт'], 3) != round(oper['t_sht'] * dse['Количество'], 3):
                                row_j = [nn, oper['name_ver'], 'Опер_Тшт', operation['Опер_Тшт'],
                                                oper['t_sht'] * dse['Количество']]
                                if fl_is_exist_erp_res and round(res[i]['Операции'][j]['Опер_Тшт'], 3) < round(oper['t_sht'] * dse['Количество'], 3):
                                    CQT.msgbox(f'{msg_error_ingr_time}:\n{str(row_j)}')
                                    return
                                journal.append(row_j)
                                res[i]['Операции'][j]['Опер_Тшт'] = oper['t_sht'] * dse['Количество']


                        if vid == 'rc':
                            if res[i]['Операции'][j]['Опер_РЦ_код'] != oper['rab_centr']:
                                for nar in list_nar:
                                    nar_obj = CMS.Naryads(nar)
                                    for param in nar_obj.params:
                                        if param['ДСЕ'] == '$'.join([naim, nn]):
                                            if param['Операции_номер'] == oper['s_name']:
                                                fl_nar_exist = True
                                journal.append([nn, oper['name_ver'], 'РЦ', res[i]['Операции'][j]['Опер_РЦ_код'], oper['rab_centr']])
                                res[i]['Операции'][j]['Опер_РЦ_код'] = oper['rab_centr']

                        if vid == 'prof':
                            if res[i]['Операции'][j]['Опер_профессия_код'] != oper['profession']:
                                if oper['profession'] not in self.DICT_PROF_CODE:
                                    CQT.msgbox(f"Код проф. {oper['profession']} отсутствует в БД")
                                    return

                                journal.append(
                                    [nn, oper['name_ver'], 'КодПрофессии', res[i]['Операции'][j]['Опер_профессия_код'], oper['profession']])
                                journal.append(
                                    [nn, oper['name_ver'], 'ИмяПрофессии', res[i]['Операции'][j]['Опер_профессия_наименование'], self.DICT_PROF_CODE[oper['profession']]['имя']])

                                res[i]['Операции'][j]['Опер_профессия_код'] = oper['profession']
                                res[i]['Операции'][j]['Опер_профессия_наименование'] = \
                                self.DICT_PROF_CODE[oper['profession']]['имя']
            if fl_nar_exist:
                CQT.msgbox(f'Нельзя проводить изменения {vid} если наряды уже существуют')
                return
            if len(journal) > 1:
                if not self.USER_CONFIG.is_developer:
                    user = F.user_full_namre()
                    result = CB24.B24Sender().send_msg_table(journal, 'chat83112', f'{user} пересчитал(а) МК {nom_mk}')
                    result = CB24.B24Sender().send_msg_table(journal, 'chat41228', f'{user} пересчитал(а) МК {nom_mk}')
                    if not result:
                        CQT.msgbox('Ошибка отправки сообщения в б24')
                else:
                    return
            ves, ves_res_list = self.raschet_vesa_dse(res)
            if not self.USER_CONFIG.is_developer:
                CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Вес = {ves} WHERE Пномер = {int(nom_mk)}""")
            nk_ves = CQT.num_col_by_name_c(tbl, 'Вес')
            tbl.item(tbl.currentRow(), nk_ves).setText(str(ves))
            if not self.USER_CONFIG.is_developer:
                CMS.save_res(self.db_resxml, nom_mk, res)
            CQT.msgbox(f'маршрутка {nom_mk} обновлена, {len(journal) - 1} изменений')
        else:
            CQT.msgbox(f'маршрутка {nom_mk} ОТСУТСТВУЕТ')

    def clk_fdate_res_erp(self):
        tbl = self.ui.table_spis_MK

        row_data = CQT.get_dict_line_form_tbl(tbl)

        val_date = row_data['Ресурсная_дата']
        nf = CQT.nums_col_by_name_dict(tbl)
        nk_date_etap = nf['Ресурсная_дата']
        nom_mk = int(row_data['Пномер'])
        tip = row_data['Тип']
        nom_pl = int(row_data['Номер КПЛ'])
        now = F.now("%Y-%m-%d")
        buf = F.paste_bufer()
        if buf.strip() != '':
            if F.is_date(buf, "%Y-%m-%d"):
                if CQT.msgboxgYN(f'Использовать дату {buf} вместо текущей {now} для МК {nom_mk}? '):
                    now = buf

        if val_date != now:
            if not CQT.msgboxgYN(f'Заменить дату {val_date} на {now} для МК {nom_mk}? '):
                return

            request = f"""UPDATE mk SET Ресурсная_дата = '{now}' where Пномер == {nom_mk}"""
            CSQ.custom_request_c(self.bd_naryad, request)
            if tip == 'Плановая':
                if nom_pl > 1:
                    CSQ.custom_request_c(self.db_kplan, f"""UPDATE пл_топ SET ( Фдата_зав_спецЕРП, Фдата_нач_спецЕРП)
                        = ('{now}', '{now}') where НомПл == {nom_pl}""")
            tbl.item(tbl.currentRow(), nk_date_etap).setText(now)
            obj_msg = CMS.Msg_b24(self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, nom_pl)
            old_str = F.dateStrToStr(val_date,format_out="%d.%m.%Y", onerror='')
            now_str = F.dateStrToStr(now,format_out="%d.%m.%Y", onerror='')
            obj_msg.send_msg('upd_fdate_res_erp',additional_str=f'\n    было: {old_str}\n    стало: {now_str}')
            CQT.msgbox(f'Успешно')

        pass

    def raschet_etapa(self, fio):
        for key in self.DICT_EMPLOEE_RC:
            if fio in key:
                return self.DICT_EMPLOEE_RC[key]
        return

    def obnovit_naruadi_po_mk(self):
        tbl = self.ui.table_spis_MK
        row = tbl.currentRow()
        if row == -1:
            return
        nk_pnom = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_mk = int(tbl.item(row, nk_pnom).text())
        if not CQT.msgboxgYN(f'Заполнить наряды по новым наименованию, нормам, количеству из МК №{nom_mk}?'):
            return

        request_mk = f"""
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
                           WHERE mk.Пномер == {nom_mk};"""
        row_mk_from_db = CSQ.custom_request_c(self.bd_naryad, request_mk, rez_dict=True)[0]
        byre_data_res = CSQ.custom_request_c(self.db_resxml, f'''SELECT data FROM res WHERE Номер_мк == {nom_mk}''')
        byre_data_res = byre_data_res[-1][0]
        custom_request_c = f'''SELECT Пномер, Внеплан, Задание, ФИО, ФИО2, Твремя, ДСЕ, ДСЕ_ID, Операции, Опер_время, Опер_колво FROM naryad WHERE Номер_мк == {nom_mk} AND Внеплан == 0'''
        rez_naruad = CSQ.custom_request_c(self.bd_naryad, custom_request_c, rez_dict=True)

        for nar in rez_naruad:
            nar = CMS.Naryads(nar['Пномер'], self.bd_naryad, self.Data_plan.DICT_DOLGN_ETAP, self.db_users,
                              self.Data_plan.DICT_EMPLOEE_FULL_WITH_DEL)
            nar.mk = CMS.Marshrut_cards(nom_mk, self.bd_naryad, self.db_resxml, True, row_from_db=row_mk_from_db,
                                        byte_data_res_from_db=byre_data_res)
            nar.recalc_by_mk(self.DICT_OP_NAME, self.DICT_PROFESSIONS)  # 05.07.25
        user = F.user_full_namre()
        CMS.send_info_mk_b24_by_action(
            f'{user} пересчитал(а) Опер_время, Теор_время в нарядах по МК {nom_mk}',
            'Ошибки МК'
        )
        CQT.msgbox(f'Наряды по мк {nom_mk} обновлены')

    def obnov_po_strukt(self):
        # ============================Обновление количества по структуре==========================================================================
        tbl = self.ui.table_spis_MK
        n_k = CQT.num_col_by_name_c(tbl, 'Пномер')
        nom_mk = int(tbl.item(tbl.currentRow(), n_k).text())
        query = f'''SELECT mk.Количество FROM mk 
            WHERE Пномер == {int(nom_mk)}
                        '''
        rez = CSQ.custom_request_c(self.bd_naryad, query)

        conn_res, cur_res = CSQ.connect_bd(self.db_resxml)
        res = CMS.load_res(int(nom_mk), conn=conn_res, cur=cur_res)
        if res == False:
            CQT.msgbox('Нет ресурсной')
            return

        query = f'''SELECT data, Head FROM xml 
            WHERE Номер_мк == {int(nom_mk)}
                        '''
        rez_xml = CSQ.custom_request_c(self.db_resxml, query)
        xml = rez_xml[-1][0]
        xml_head = rez_xml[-1][1]
        if xml == '':
            CQT.msgbox('Нет хмл файла')
            return

        CSQ.close_bd(conn_res, cur_res)

        res_new = CMS.resource_from_xml_c(self, CMS.podgotovka_xml(self, XML.spisok_iz_xml(str_f=xml), xml_head),
                                          kol_vo_izdeliy=rez[-1][1])
        if len(res) != len(res_new):
            CQT.msgbox(f'Несовпадение числа деталей')
            return
        if res:
            for i in range(len(res)):
                if res[i]['Номенклатурный_номер'] != res_new[i]['Номенклатурный_номер']:
                    CQT.msgbox(f'Несовпадение номеров старой и новой мк')
                    return
                if res[i]['Количество'] != res_new[i]['Количество']:
                    print(
                        f"мК {nom_mk}, {res[i]['Номенклатурный_номер']} было {res[i]['Количество']}, стало {res_new[i]['Количество']}")
                    res[i]['Количество'] = res_new[i]['Количество']
                    for j in range(len(res[i]['Операции'])):
                        res[i]['Операции'][j]['Опер_Тшт'] = res_new[i]['Операции'][j]['Опер_Тшт']
                        res[i]['Операции'][j]['Материалы'] = res_new[i]['Операции'][j]['Материалы']

            CMS.save_res(self.db_resxml, nom_mk, res)
            CQT.msgbox(f'маршрутка {nom_mk} обновлена')

    # ====================================================================================================================
    @CQT.onerror
    def load_cust_drevo(self, *args):
        if 'dict_cur_poz_cr_mk' not in self.__dict__:
            CQT.blink_obj_c(self, 2, self.ui.cmb_cr_mk_poz, f'Не выбрана позиция')
            return
        tmp_path = CMS.load_tmp_path('razr_mk')
        put_ima = CQT.f_dialog_name(self, 'выбор файла', tmp_path, '*.pickle', True)
        if put_ima == '.':
            return
        CMS.save_tmp_path('razr_mk', put_ima)
        main_list = CQT.list_from_wtabl_c(self.ui.table_razr_MK, hat_c=True)
        row = self.ui.table_razr_MK.currentRow() + 1
        spis = CMS.add_cust_drevo(self, put_ima, main_list, row)
        if spis == None:
            return
        spis_dict = F.list_of_lists_to_list_of_dicts(spis)
        rez_list = [copy.deepcopy(self.hat_c)]
        for item in spis_dict:
            tmp_line = []
            for hat_i in rez_list[0]:
                if hat_i in item:
                    tmp_line.append(item[hat_i])
                else:
                    tmp_line.append('')
            rez_list.append(tmp_line)
        CQT.fill_wtabl_old_c(self, rez_list, self.ui.table_razr_MK, 0, self.edit_cr_mk_ruch, (), (), 200, True, '', 30)
        self.mark_count_by_position(self.ui.table_razr_MK)  # 09.06.2025
        self.spis_poziciy_rez_ruchnoi = []
        try:
            self.tkp_current_schema.clear()
            # del self.tkp_current_schema
        except:
            pass

    def save_cust_drevo(self):
        tbl = self.ui.table_razr_MK
        spis = CQT.list_from_wtabl_c(tbl, '', True)
        tmp_path = CMS.load_tmp_path('razr_mk_save')

        put_ima = CQT.f_dialog_save(self, 'Выбрать куда сохранить', tmp_path, '*.pickle')
        if put_ima == '.':
            return
        CMS.save_tmp_path('razr_mk_save', put_ima)
        F.write_file_c(put_ima, spis, separ='', pickl=True)
        CQT.msgbox('Успешно')

    @CQT.onerror
    def export_json_kotl(self, *args, **kwargs):
        # if USRCNF.Config.place.poki == 1 and not USRCNF.User_config.is_developer:
        #   return CQT.msgbox(f'Данный функционал не адаптирован для {USRCNF.Config.place.Имя!r}') #25.07.25
        self.export_json(exel=False, kotel=True)

    @CQT.onerror
    def export_json(self, exel=False, kotel=False):

        def add_code_erp(self, res):
            dict_dse = CMS.load_dict_dse(self.db_dse)
            for i, dse in enumerate(res):
                if 'Код ERP' in dse and 'Код_ERP' not in dse:
                    dse['Код_ERP'] = dse['Код ERP']
                dse.pop('Код ERP', None)
                if 'Код_ERP' not in dse:
                    kod_erp = ''
                    if dse['Номенклатурный_номер'] in dict_dse:
                        kod_erp = dict_dse[dse['Номенклатурный_номер']]['Код_ЕРП']
                    res[i]['Код_ERP'] = kod_erp

            return res

        def clear_zero_time_opers(res):
            list_msg = []
            for i, dse in enumerate(res):
                tmp_opers = []
                for j, oper in enumerate(dse['Операции']):
                    if oper['Опер_Тшт_ед'] == 0 and len(oper['Материалы']) == 0:
                        list_msg.append({'Операция': oper['Опер_наименование'],
                                         'ДСЕ': f"{dse['Наименование']} {dse['Номенклатурный_номер']} ",
                                         'val': f"не учтена т.к. норма времени = 0 и материалов нет"
                                         })

                        continue
                    tmp_opers.append(oper)
                if len(tmp_opers) != dse['Операции']:
                    res[i]['Операции'] = tmp_opers
            return res, list_msg

        def check_py_name(self):
            try:
                py = self.dict_cur_poz_cr_mk["№ERP"]
                if py != '-':
                    CQT.msgbox(f'№ERP создано. этот метод должен использоваться до создания №ERP')
                    return False
                name_res = self.ui.le_name_predv_res.text().strip()
                if name_res == '' or len(name_res) < 3:
                    CQT.msgbox(f'Имя ресурсной не указано')
                    return False
            except:
                CQT.blink_obj_c(self, 1, self.ui.cmb_cr_mk_py, f'Ошибка чтения №ERP')
                return False
            return True

        def check_prices_dse(self, rez):
            for dse in rez:
                if dse['Код_ERP'] != '':
                    if dse['Код_ERP'] not in self.DICT_NOMEN:
                        CQT.msgbox(f"Код номенклатуры {dse['Код_ERP']} отсутствует в БД MEC")
                        return False
                    price = self.DICT_NOMEN[dse['Код_ERP']]['Закупочная_цена']
                    if price == None or F.valm(price) == 0:
                        CSQ.custom_request_c(self.db_dse,
                                             f"""UPDATE tkp SET (check_prices) = (2) WHERE s_nom = {self.tkp_current_schema['s_nom']}""")
                        break
            return True

        def from_statistik(self, exel, kotel):
            if self.res == '':
                CQT.msgbox('Не создана ресурсная')
                return

            if "file_name" not in self.tkp_current_schema:
                CQT.msgbox(f'Не сгенерирована структура шаблона')
                return
            rez = copy.deepcopy(self.res)
            rez, msg = clear_zero_time_opers(rez)
            rez = add_code_erp(self, rez)

            if not check_prices_dse(self, rez):
                return

            if not check_py_name(self):
                return
            self.res = rez
            num_kpl = None
            if 'dict_cur_poz_cr_mk' in self.__dict__:
                num_kpl = self.dict_cur_poz_cr_mk['Пномер']
            self.laod_res_board(name=f'{self.tkp_current_schema["file_name"]}_TKPSTAT_{F.now("%Y%m%d-%H%M%S")}',
                                possible_upload_ERP=True, save_as_predv_res=True, num_kpl=num_kpl)

            return

            # ========================JSON FILE===============================================================
            # generate(self, exel, rez, "ВО", self.dict_cur_poz_cr_mk["№ERP"], self.ui.le_tkp_dir_res.text(),
            #         f'{self.tkp_current_schema["file_name"]}_TKPSTAT_{F.now("%Y%m%d-%H%M%S")}.json', kotel)
            # ========================JSON FILE===============================================================

        def from_abstract_mk(self, exel, kotel):

            if self.res == '':
                CQT.msgbox('Не создана ресурсная')
                return

            if "file_name" not in self.tkp_current_schema:
                CQT.msgbox(f'Не сгенерирована структура шаблона')
                return
            rez = copy.deepcopy(self.res)
            rez, msg = clear_zero_time_opers(rez)
            rez = add_code_erp(self, rez)

            if not check_prices_dse(self, rez):
                return

            if not check_py_name(self):
                return

            self.res = rez
            num_kpl = None
            if 'dict_cur_poz_cr_mk' in self.__dict__:
                num_kpl = self.dict_cur_poz_cr_mk['Пномер']

            self.laod_res_board(name=f'{self.tkp_current_schema["file_name"]}_TKP_{F.now("%Y%m%d-%H%M%S")}',
                                possible_upload_ERP=True, save_as_predv_res=True, num_kpl=num_kpl)
            return

        def from_real_mk(self, exel, kotel):
            def divide_tpz_by_count_izd(self: mywindow, res: list) -> list:
                count_izd = res[0]['Количество'] / res[0]['Количество_ед']
                for i, dse in enumerate(res):
                    for i_op, oper in enumerate(dse['Операции']):
                        oper['Опер_Тпз'] = round(oper['Опер_Тпз'] / count_izd, 3)
                return res

            if self.ui.table_spis_MK.currentRow() == -1:
                CQT.msgbox(f'Не выбрана МК')
                return
            nom_mk = self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(),
                                                CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Пномер')).text()
            py = self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(),
                                            CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Номер_заказа')).text()
            kpl = int(self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(),
                                                 CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Номер КПЛ')).text())
            poz = CMS.Pozition(kpl, self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
            poz.load_kpl_table('пл_оуп')
            poz.load_kpl_table('пл_топ')
            izd = poz.dict_tables['пл_оуп']['Номенклатура_ЕРП']
            type_dse = poz.dict_tables['пл_топ']['Вид']
            # смена интерфейса 25.08.25
            # if type_dse == 1: #21.07.25
            #     confirm_continue = CMS.TypesWorkingByDirections().get_table_for_select_type(window=self, poz=poz)
            #     if not confirm_continue:
            #         return
            rez = CMS.resursnaya_from_mk(self, nom_mk)
            if rez == None:
                return
            rez = add_code_erp(self, rez)
            rez = divide_tpz_by_count_izd(self, rez)
            self.res = rez
            primech = {'Номер проекта': poz.dict_tables['пл_оуп']['№проекта'],
                       'Номер ЗП': poz.dict_tables['пл_оуп']['№ERP'],
                       'Номер МК': nom_mk,
                       'Номер КПЛ': str(kpl),
                       'Дата': F.now("%d.%m.%Y %H:%M"),
                       'Изделие': poz.dict_tables['пл_оуп']['Номенклатура_ЕРП'],
                       'Примечание ПДО': poz.Примечание,
                       'Примечание ОУП': poz.dict_tables['пл_оуп']['Номенклатура_ЕРП'],
                       'Выгрузил': F.user_full_namre(),
                       }
            max_len = max([len(k) for k in primech.keys()])
            primech_str = '\n'.join([f'{k + ":" + " " * (max_len - len(k))} "{str(v)}"' for k, v in primech.items()])

            self.dict_cur_poz_cr_mk = CSQ.custom_request_c(self.db_kplan, f"""SELECT 
             пл_оуп.№проекта as "Проект", plan.Статус as Статус_poz, status_poz.Имя AS СтатусИмя, 
            пл_оуп.№ERP as "№ERP",  napravl_deyat.Псевдоним as "Вид",
                         napravlenie.name as "Направление",  пл_оуп.Количество as "Количество", 
                         plan.Позиция, plan.Пномер as "Пномер", пл_оуп.Номенклатура_ЕРП as "Номен. ЕРП" 
                         FROM пл_оуп  INNER JOIN 
                         plan ON пл_оуп.НомПл = plan.Пномер,
                         status_poz ON status_poz.Пномер = plan.Статус,
                napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
                napravlenie ON napravlenie.Пномер = napravl_deyat.Направление 
                WHERE plan.Пномер = {kpl} and plan.poki = {self.place.poki};""",
                                                           rez_dict=True)

            if len(self.dict_cur_poz_cr_mk) == 1:
                if self.dict_cur_poz_cr_mk[0]['Статус_poz'] not in (2, 3, 1, 7):
                    if not USRCNF.User_config.is_developer:
                        if not CQT.msgboxgYN(
                                f'Позиция КПЛ № {kpl} находится в статусе `{self.dict_cur_poz_cr_mk[0]["СтатусИмя"]}`.\n Все равно продолжить?'):
                            return
                self.dict_cur_poz_cr_mk = self.dict_cur_poz_cr_mk[0]
            else:
                CQT.msgbox(f'Ошибка загрузки данных КПЛ из БД')
                return

            self.laod_res_board_mk(f'{izd}', rez, int(nom_mk), primech_str)
            return
            # generate(self, exel, rez, nom_mk, py, name=f'{nom_mk}_{py}_{F.now("%Y%m%d-%H%M%S")}.json', kotlovoy=kotel)

        if self.ui.tabWidget.tabText(self.ui.tabWidget.currentIndex()) == 'Маршрутные карты':
            kpl = int(self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(),
                                                 CQT.num_col_by_name_c(self.ui.table_spis_MK, 'Номер КПЛ')).text())
            if kpl == 3345:
                name_nomen = self.ui.table_spis_MK.item(self.ui.table_spis_MK.currentRow(),
                                                        CQT.num_col_by_name_c(self.ui.table_spis_MK,
                                                                              'Номенклатура')).text()
                self.tkp_current_schema['file_name'] = name_nomen  # 08.08.25
            from_real_mk(self, exel, kotel)
            try:
                # del self.tkp_current_schema
                self.tkp_current_schema.clear()
            except:
                pass
            try:
                del self.dict_cur_poz_cr_mk
            except:
                pass
        if self.ui.tabWidget.tabText(self.ui.tabWidget.currentIndex()) == 'Создание МК':
            if 'dict_cur_poz_cr_mk' not in self.__dict__:
                CQT.blink_obj_c(self, 2, self.ui.cmb_cr_mk_poz, f'Не выбрана позиция')
                return
            if self.ui.tabWidget_2.tabText(self.ui.tabWidget_2.currentIndex()) == 'Разработка МК':
                if self.tkp_current_schema != dict():
                    if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] == 4:
                        from_statistik(self, exel, kotel)
                    if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] == 3:
                        from_abstract_mk(self, exel, kotel)
                else:
                    CQT.msgbox(f'Схема ТКП не загружена')
                    return
            if self.ui.tabWidget_2.tabText(self.ui.tabWidget_2.currentIndex()) == 'Создание МК из *.XML':
                return

        return

    def spisok_tek_tehkarta(self, spis_sod_tk):
        nach = 0
        kon = len(spis_sod_tk) - 1
        for i in range(len(spis_sod_tk)):
            if len(spis_sod_tk[i]) == 21 and spis_sod_tk[i][-1] == '0':
                if nach == 0:
                    nach = i
                else:
                    kon = i - 1
        return spis_sod_tk[nach:kon + 1]

    def open_zayavk(self):
        nom_pr = ''
        nom_pu = ''
        year_py = None

        def by_kpl(kpl):
            poz = CMS.Pozition(int(kpl), parent_self=self)
            poz.load_kpl_table('пл_оуп')
            nom_pr = poz.dict_tables['пл_оуп']['№проекта']
            nom_pu = poz.dict_tables['пл_оуп']['№ERP']
            year_py = poz.dict_tables['пл_оуп']['Год']
            return nom_pr, nom_pu, year_py

        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Создание МК'):
            if 'dict_cur_poz_cr_mk' not in self.__dict__:
                CQT.blink_obj_c(self, 2, self.ui.cmb_cr_mk_poz, f'Не выбрана позиция')
                return
            nom_pr = self.dict_cur_poz_cr_mk['Проект']
            nom_pu = self.dict_cur_poz_cr_mk["№ERP"]
        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Маршрутные карты'):
            if self.ui.table_spis_MK.currentRow() == None or self.ui.table_spis_MK.currentRow() == -1:
                CQT.msgbox('Не выбран номер проекта')
                return
            row = CQT.get_dict_line_form_tbl(self.ui.table_spis_MK)
            nom_pr, nom_pu, year_py = by_kpl(row['Номер КПЛ'])

        if self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget,
                                                                          'Объемно-календарное планирование'):
            row = CQT.get_dict_line_form_tbl(self.ui.table_spis_MK)
            nom_pr, nom_pu, year_py = by_kpl(row['plan.Пномер'])

        if nom_pu == '':
            return
        putf = CMS.path_to_proj_NPPY_c(nom_pr, nom_pu, True, year_py)
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

    def vigruzka_norm_vr_po_spis_xml(self, spis_xml, razrabotka=0):
        n_k_nn = 1
        n_k_naim = 0
        n_k_kol = 7
        if razrabotka == True:
            n_k_kol = 10
        n_k_kol_bez_summ = 2
        n_k_ves = 4
        ves = 0
        rez = []
        ima_sbor = spis_xml[0][0] + '$' + spis_xml[0][1]
        dict_dse = CSQ.custom_request_c(self.db_dse, """SELECT Номенклатурный_номер, Номер_техкарты FROM dse""",
                                        rez_dict=True)
        dict_dse = F.deploy_dict_c(dict_dse, 'Номенклатурный_номер')
        for i in range(len(spis_xml)):
            ves_det = 0
            chislo_det = 0
            if spis_xml[i][n_k_ves].split('/')[1] != '' and spis_xml[i][n_k_ves].split('/')[2] != '':
                ves_det = F.valm(spis_xml[i][n_k_ves].split('/')[0])
                chislo_det = self.kol_v_uzel(spis_xml, i, 1, 2)  # F.valm(spis_xml[i][n_k_kol])
                ves += ves_det * chislo_det
                print(spis_xml[i][n_k_nn], ves_det, chislo_det)
            if spis_xml[i][n_k_nn] not in dict_dse:
                CQT.msgbox(f'Не найден номер техкарты на {spis_xml[i][n_k_nn]} {spis_xml[i][n_k_naim]}')
                return
            nom_t_k = dict_dse[spis_xml[i][n_k_nn]]
            if F.existence_file_c(
                    F.scfg('add_docs') + os.sep + nom_t_k + "_" + spis_xml[i][n_k_nn] + '.pickle') == False:
                CQT.msgbox(f'Не найдена техкарта {nom_t_k}')
                return
            spis_sod_tk = F.open_file_c(F.scfg('add_docs') + os.sep + nom_t_k + "_" + spis_xml[i][n_k_nn] + '.txt',
                                        separ='|', pickl=True)
            tek_karta = self.spisok_tek_tehkarta(spis_sod_tk)
            for j in range(len(tek_karta)):
                if tek_karta[j][-1] == '1':
                    if F.is_numeric(tek_karta[j][7]) == False or tek_karta[j][7] == '':
                        CQT.msgbox(
                            f'{spis_xml[i][n_k_naim] + "$" + spis_xml[i][n_k_nn]} операция {tek_karta[j][2]} не отнормирована')
                        return
                    rez.append([ima_sbor, spis_xml[i][n_k_naim] + "$" + spis_xml[i][n_k_nn], spis_xml[i][n_k_kol],
                                tek_karta[j][0],
                                tek_karta[j][2],
                                tek_karta[j][4],
                                tek_karta[j][6],
                                tek_karta[j][7],
                                tek_karta[j][8],
                                ves_det, chislo_det])
                    ves_det = 0
                    chislo_det = 0
        return [rez, ves]

    def vigruzka_norm_mat_po_spis_xml(self, xml, rez, kol_izd, ruchnoiy=0):  # отключена
        nk_naim = 0
        nk_nn = 1
        nk_sumkol = 7
        if ruchnoiy == True:
            nk_sumkol = 10
        err_arr = []
        conn1, cur1 = CSQ.connect_bd(self.db_dse)
        dict_dse = CSQ.custom_request_c(self.bd_naryad, """SELECT Номенклатурный_номер, Номер_техкарты FROM dse""",
                                        rez_dict=True, conn=conn1, cur=cur1)
        CSQ.close_bd(conn1, cur1)
        dict_dse = F.deploy_dict_c(dict_dse, 'Номенклатурный_номер')
        for i in range(1, len(xml)):
            nn = xml[i]['data']['Обозначение'].strip()
            naim = xml[i]['data']['Наименование'].strip()
            kolvo = int(xml[i][nk_sumkol])  # * kol_izd
            if nn not in dict_dse:
                CQT.msgbox(f'{nn} в дсе не найдена')
            nom_tk = dict_dse[nn]
            putf = F.scfg('add_docs') + os.sep + nom_tk + '_' + nn + '.pickle'
            if F.existence_file_c(putf):
                nk_rc_tk = 4
                nk_ur_tk = 20
                nk_op_tk = 2
                nk_mat_tk = 10
                nk_doc_tk = 15
                nk_textper = 0
                sp_tk = F.open_file_c(putf, False, "|", pickl=True)
                for j in range(11, len(sp_tk)):
                    if sp_tk[j][nk_ur_tk] == '0':
                        break
                    if sp_tk[j][nk_ur_tk] == '1':
                        mat_str = sp_tk[j][nk_mat_tk].split('{')
                        for k in range(len(mat_str)):
                            if sp_tk[j][nk_rc_tk] == '':
                                CQT.msgbox(
                                    f'В техкарте {sp_tk[0][0]} {sp_tk[1][0]} не корректно занесен РЦ на {sp_tk[j][nk_op_tk]} операцию')
                                return
                            if mat_str[k] != '':
                                rez = self.add_mats_into_list_c(rez, mat_str[k] + '$' + sp_tk[j][nk_rc_tk], kolvo)
                                if rez == False:
                                    CQT.msgbox(
                                        f'В техкарте {sp_tk[0][0]} {sp_tk[1][0]} не корректно занесен материал на {sp_tk[j][nk_op_tk]} операцию')
                                    return
            else:
                CQT.msgbox(f'Не найдена техкарта {putf}')

                return

        return rez

    def add_mats_into_list_c(self, spis: list, list_mat, kolvo):
        if list_mat == '':
            return spis
        list_mat = list_mat.split('$')
        if len(list_mat) < 5:
            return False
        list_mat[3] = F.valm(list_mat[3]) * int(kolvo)
        flag = False
        for i in range(len(spis)):
            if spis[i][0] == list_mat[0] and spis[i][4] == list_mat[4]:
                spis[i][3] += list_mat[3]
                flag = True
                break
        if flag == False:
            spis.append(list_mat)
        return spis

    def vigruzka_norm_mat(self):
        self.w2 = CVO.mywindow2(self)
        # self.w3 = CQT.msgboxg(self,'text')

    @CQT.onerror
    def laod_res_board_mk(self, nomen: str, res: list, s_num_mk: int, primech=None):
        self.res = res
        DICT_DSE = CSQ.custom_request_c(self.db_dse,
                                        f'''SELECT poki, Номер_техкарты, Номенклатурный_номер, Код_ЕРП FROM dse WHERE poki = {self.place.poki}''',
                                        rez_dict=True)
        self.DICT_DSE_save_mk = F.deploy_dict_c(DICT_DSE, 'Номенклатурный_номер')

        # TODO dict_cur_poz_cr_mk
        self.laod_res_board(name=nomen,
                            possible_upload_ERP=True,
                            nom_mk=s_num_mk, primech=primech)

    @CQT.onerror
    def laod_res_board(self, save_as_predv_res=False, num_kpl=None, primech: str | None = None, *args, **kwargs):
        if 'res' not in self.__dict__ or self.res == '' or self.res == None:
            CQT.msgbox(f'Для работы с ресурсной, нужно создать МК')
            return
        name = ''
        possible_upload_ERP = False  # TODO
        nom_mk = None

        if 'name' in kwargs:
            name = kwargs['name']
        if 'possible_upload_ERP' in kwargs:
            possible_upload_ERP = kwargs['possible_upload_ERP']
        if 'nom_mk' in kwargs:
            nom_mk = kwargs['nom_mk']
        self.w3 = RESB.mywindow_res(self, name, possible_upload_ERP, nom_mk=nom_mk, save_as_predv_res=True,
                                    num_kpl=num_kpl, primech=primech)

    @CQT.onerror
    def vigruzka_norm(self, *args):
        """    стадия МК(ресурсной план)
    этап по имени операции (operacii)
    вид работ по профессии (professions)

    стадия выгрузки трудов (факт)
    этап по должности исполнителя (dolgn_etap)
    вид работ по должности исполнителя (professions)"""
        tbl = self.ui.table_spis_MK
        row = CQT.get_dict_line_form_tbl(tbl)
        if row == {}:
            return

        poz = CMS.Pozition(row['Номер КПЛ'], self.db_kplan, self.bd_naryad, self.db_resxml, self.db_users, self)
        poz.load_kpl_table('пл_топ')
        nom_vid_po_napr = poz.dict_tables['пл_топ']['Вид']
        self.res = CMS.resursnaya_from_mk(self, row['Пномер'])
        self.calc_report_and_statistic(nom_vid_po_napr, show_opers=True, delete_mat_mode=False)
        return

    def vigruzka_norm_old(self):
        def export_spis_etapov_s_vesom_for_plan_exel(self, putt, spis_poziciy_rez):
            dict_etapov = {}
            ves = 0
            for poz in spis_poziciy_rez:
                kolvo = poz['kol_zayavk']
                for dse in poz['data']:
                    mat = dse['Мат_кд'].split('/')
                    if mat[1] != '' and mat[2] != '':
                        ves += F.valm(mat[0]) * dse['Количество']
                    for oper in dse['Операции']:
                        if oper['Опер_наименование'] not in self.DICT_ETAPI:
                            CQT.msgbox(
                                f"Операция {oper['Опер_наименование']} отсутствует в списке операций БД. не выгружено")
                            return
                        etap = self.DICT_ETAPI[oper['Опер_наименование']]
                        vrema = oper['Опер_Тпз'] + oper['Опер_Тшт']
                        if etap in dict_etapov:
                            dict_etapov[etap] += vrema
                        else:
                            dict_etapov[etap] = vrema
            spis_etapov = [[k, round(v)] for k, v in dict_etapov.items()]
            spis_etapov.insert(0, ['Вес', round(ves)])
            F.save_file(putt, spis_etapov, utf=False)
            CQT.msgbox(f'Многоуважаемый {F.user_name()}! Нормы для плана успешно выгружены, хорошего дня.')

        def vigruzka_norm_exel(self, putt, spis_poziciy_rez):
            if 'dict_cur_poz_cr_mk' not in self.__dict__:
                CQT.blink_obj_c(self, 2, self.ui.cmb_cr_mk_poz, f'Не выбрана позиция')
                return

            putp = os.sep.join(putt.split(os.sep)[:-1])
            file = putt.split(os.sep)[-1]
            if '.xlsx' not in file:
                CQT.msgbox('Файл должен быть *.xlsx')
                return

            summ_ves = 0
            rez = [['Позиция', 'ДСЕ', 'Количество', 'Операция', 'Номер', 'РЦ', 'Тпз', 'Тшт', 'Профессия', 'По заявке',
                    'Тшт*Кол*Заяв', 'Вес',
                    'Кол-во для веса']]
            for item in spis_poziciy_rez:
                resyrsnaya = item['data']
                poz = item['name']
                kol_vo_izdeliy = item['kol_zayavk']
                for dse in resyrsnaya:
                    dse_name = f"{dse['Наименование']} {dse['Номенклатурный_номер']}"
                    kol_vo_dse = dse['Количество'] / kol_vo_izdeliy
                    ves_spis = F.valm(dse['Мат_кд'].split('/'))
                    ves = 0
                    if ves_spis[1] != '' and ves_spis[2] != '':
                        ves = F.valm(ves_spis[0])
                    ves_kol_vo = dse['Количество']
                    for oper in dse['Операции']:
                        oper_name = oper['Опер_наименование']
                        oper_nom = oper['Опер_номер']
                        oper_rc = oper['Опер_РЦ_код']
                        oper_tpz = oper['Опер_Тпз']

                        oper_prof = oper['Опер_профессия_наименование']

                        oper_tsht_ed = oper['Опер_Тшт_ед']
                        oper_tsht = oper['Опер_Тшт']
                        tsht_kol_zayv = oper_tsht + oper_tpz
                        rez.append(
                            [poz, dse_name, kol_vo_dse, oper_name, oper_nom, oper_rc, oper_tpz, oper_tsht_ed, oper_prof,
                             kol_vo_izdeliy,
                             tsht_kol_zayv, ves,
                             ves_kol_vo])
                        summ_ves += ves * ves_kol_vo
                        ves = 0
                        ves_kol_vo = 0
            for i in range(4):
                rez.append(['' for x in range(len(rez[0]))])
            rez[-1][3] = 'масса'
            rez[-1][4] = round(summ_ves, 1)

            file = F.clear_row_for_file_name_c(file)
            CEX.zap_spis(rez, putp, file, 'Нормы времени', 0, 0)
            if F.existence_file_c(putp + F.sep() + file):
                rez = CQT.msgboxgYN('эксель успешно сохранен. Запустить?')
                if rez == True:
                    F.run_file_c(putp + F.sep() + file)
            else:
                CQT.msgbox('Файл эксель не сохранен, что то пошло не так')

        if self.ui.tabWidget_2.tabText(self.ui.tabWidget_2.currentIndex()) == 'Разработка МК':
            if self.spis_poziciy_rez_ruchnoi == []:
                CQT.msgbox(f'Не сформирована МК')
                return

        nom_pr = self.dict_cur_poz_cr_mk['Проект']
        tmp_putt = CMS.load_tmp_path('table_normi')

        putt = CQT.f_dialog_save(self, 'Сохранить нормы', tmp_putt[0] + F.sep() + nom_pr + '_Нормы_поэтапно',
                                 "Text files (*.txt)")
        if putt == '' or putt == '.':
            return
        CMS.save_tmp_path('table_normi', putt)
        # puttres = F.sep().join(putt.split(F.sep())[:-1]) + F.sep() + nom_pr + '_Ресурсная.pickle'
        spis_poziciy_rez = self.vigruzka_norm_resusrnaya()
        if spis_poziciy_rez == None:
            return
        vigruzka_norm_exel(self, putt.replace('.txt', '.xlsx'), spis_poziciy_rez)
        export_spis_etapov_s_vesom_for_plan_exel(self, putt, spis_poziciy_rez)
        return

    def vigruzka_norm_resusrnaya(self):
        if self.ui.tabWidget_2.tabText(self.ui.tabWidget_2.currentIndex()) == 'Создание МК из *.XML':
            tbl = self.ui.table_zayavk
            if tbl.rowCount() == 0:
                CQT.msgbox('Не заполнены позиции')
                return
            spis_poziciy = CQT.list_from_wtabl_c(tbl, '', True)
            if len(spis_poziciy) == 1:
                CQT.msgbox('Не заполнены позиции')
                return
            n_k_file = F.num_col_by_name_in_hat_c(spis_poziciy, 'Файл')
            n_k_count = F.num_col_by_name_in_hat_c(spis_poziciy, 'Количество')
            if n_k_file == None:
                CQT.msgbox('Не найден путь')
                return
            spis_poziciy_rez = []
            for i in range(1, len(spis_poziciy)):
                dict_poziciy_rez = dict()
                if spis_poziciy[i][n_k_count] == '':
                    CQT.msgbox('Не указано количество')
                    return
                if F.is_numeric(spis_poziciy[i][n_k_count]) == False:
                    CQT.msgbox('Количество не число')
                    return
                if F.existence_file_c(spis_poziciy[i][n_k_file]) == False:
                    CQT.msgbox(f'Не найден XML {spis_poziciy[i][n_k_file]}')
                    return
                else:
                    spis_det_xml = CMS.podgotovka_xml(self, XML.spisok_iz_xml(spis_poziciy[i][n_k_file]))
                    kol_vo_izdeliy = int(spis_poziciy[i][n_k_count])
                    rez = CMS.resource_from_xml_c(self, spis_det_xml, kol_vo_izdeliy)
                    if rez == None:
                        return
                    dict_poziciy_rez['name'] = f"{rez[0]['Наименование']} {rez[0]['Номенклатурный_номер']}"
                    dict_poziciy_rez['data'] = rez
                    dict_poziciy_rez['kol_zayavk'] = kol_vo_izdeliy
                    spis_poziciy_rez.append(dict_poziciy_rez)
            # F.save_file_pickle(putt, dict_poziciy_rez)
            return spis_poziciy_rez
        else:
            return self.spis_poziciy_rez_ruchnoi

    def select_poz_cr_mk_pr(self):
        row = CQT.msgboxg_get_table(self,'Выбор проекта',self.list_projects,'Выбор',
                                    selection_from_tbl=True,ExtendedSelection=False,
                                    selectRows=True,sortingEnabled=True)

        if row:
            self.ui.cmb_cr_mk_py.clear()
            self.ui.cmb_cr_mk_poz.clear()
            CQT.clear_tbl(self.ui.tbl_info_cr_mk)
            self.ui.comboBox_sort_c.clear()
            self.ui.comboBox_napravlenia.clear()
            self.dict_cur_poz_cr_mk = row
            self.fill_select_poz_for_mk()
            self.res = ''

    def obn_spis_pr(self):
        self.list_projects = CSQ.custom_request_c(self.db_kplan, f"""SELECT  
        пл_оуп.№проекта as "Проект",
         пл_оуп.№ERP as "№ERP", 
          
         napravl_deyat.Псевдоним as "Вид",
        napravlenie.name as "Направление",  
        пл_оуп.Количество as "Количество", 
        plan.Позиция, 
        plan.Пномер as "Пномер", пл_оуп.Номенклатура_ЕРП as "Номен. ЕРП" 
        FROM пл_оуп  
        INNER JOIN plan ON пл_оуп.НомПл = plan.Пномер,
        napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности,
        napravlenie ON napravlenie.Пномер = napravl_deyat.Направление 
        WHERE 
        plan.Статус in (2,3,1,7) and plan.poki = {self.place.poki}""")
        field = F.num_col_by_name_in_hat_c(self.list_projects, 'Проект')
        set_proj = list(set([str(_[field]) for _ in self.list_projects[1:]]))
        set_proj.sort()
        self.ui.cmb_cr_mk_pr.clear()
        self.ui.cmb_cr_mk_py.clear()
        self.ui.cmb_cr_mk_poz.clear()
        CQT.clear_tbl(self.ui.tbl_info_cr_mk)
        self.ui.comboBox_sort_c.clear()
        self.ui.comboBox_napravlenia.clear()
        self.ui.cmb_cr_mk_pr.addItems(set_proj)

    @CQT.onerror
    def cmb_pl_tabel_place(self, i=None):
        self.push_work_plan_fact.fill_tbl()

    @CQT.onerror
    def cmb_year_for_select_tkp(self, i=None):
        year = int(self.ui.cmb_year_for_select_tkp.currentText())
        include_del = self.ui.chk_deleted_for_select_tkp.checkState() == QtCore.Qt.CheckState.Checked
        CMS.load_tkp_list(self, self.db_dse, CMS.DICT_NAME_SQL['tkp'], self.ui.tbL_tkp_list,
                          self.ui.tbL_tkp_list_filtr, {}, date_res=year, include_deleted=include_del)

    def cmb_cr_mk_select_pr(self, i=None):
        pr = self.ui.cmb_cr_mk_pr.currentText()
        field = F.num_col_by_name_in_hat_c(self.list_projects, "№ERP")
        field_pr = F.num_col_by_name_in_hat_c(self.list_projects, 'Проект')
        set_proj = list(set([str(_[field]) for _ in self.list_projects[1:] if _[field_pr] == pr]))
        set_proj.sort()
        self.ui.cmb_cr_mk_py.clear()
        self.ui.cmb_cr_mk_poz.clear()
        CQT.clear_tbl(self.ui.tbl_info_cr_mk)
        self.ui.cmb_cr_mk_py.addItems(set_proj)
        self.ui.comboBox_sort_c.clear()
        self.ui.comboBox_napravlenia.clear()
        if len(set_proj) == 1:
            self.ui.cmb_cr_mk_py.setCurrentIndex(0)
            self.cmb_cr_mk_select_py()

    def cmb_cr_mk_select_py(self, i=None):
        py = self.ui.cmb_cr_mk_py.currentText()
        pr = self.ui.cmb_cr_mk_pr.currentText()
        field = F.num_col_by_name_in_hat_c(self.list_projects, 'Позиция')
        field_pr = F.num_col_by_name_in_hat_c(self.list_projects, 'Проект')
        field_py = F.num_col_by_name_in_hat_c(self.list_projects, "№ERP")
        set_proj = list(set([str(_[field]) for _ in self.list_projects[1:] if
                             _[field_pr] == pr and _[field_py] == py]))
        set_proj.sort()
        self.ui.cmb_cr_mk_poz.clear()
        CQT.clear_tbl(self.ui.tbl_info_cr_mk)
        self.ui.cmb_cr_mk_poz.addItems(set_proj)
        self.ui.comboBox_sort_c.clear()
        self.ui.comboBox_napravlenia.clear()
        if len(set_proj) == 1:
            self.ui.cmb_cr_mk_poz.setCurrentIndex(0)
            self.cmb_cr_mk_select_poz()

    @CQT.onerror
    def cmb_cr_mk_select_poz(self, i=None):
        self.ui.comboBox_sort_c.clear()
        self.ui.comboBox_napravlenia.clear()
        py = self.ui.cmb_cr_mk_py.currentText()
        pr = self.ui.cmb_cr_mk_pr.currentText()
        poz = self.ui.cmb_cr_mk_poz.currentText()

        field = F.num_col_by_name_in_hat_c(self.list_projects, 'Позиция')
        field_pr = F.num_col_by_name_in_hat_c(self.list_projects, 'Проект')

        field_py = F.num_col_by_name_in_hat_c(self.list_projects, "№ERP")
        set_proj = [_ for _ in self.list_projects[1:] if str(_[field_pr]) == pr and
                    str(_[field_py]) == py and str(_[field]) == poz]
        if len(set_proj) == 0:
            CQT.msgbox(f'Не найдено')
            return
        self.dict_cur_poz_cr_mk = {k: v for k, v in zip(self.list_projects[0], set_proj[0])}
        self.fill_select_poz_for_mk()
        self.res = ''

    @CQT.onerror
    def fill_select_poz_for_mk(self):
        def list_vals_cmb(cmb):
            list_rez = []
            for i in range(cmb.count()):
                list_rez.append(cmb.itemText(i))
            return list_rez


        CQT.fill_wtabl(F.dict_to_param_val(self.dict_cur_poz_cr_mk,'Параметр','Значение'),self.ui.tbl_info_cr_mk)
        if self.dict_cur_poz_cr_mk['Проект'] not in list_vals_cmb(self.ui.cmb_cr_mk_pr):
            self.ui.cmb_cr_mk_pr.addItem(self.dict_cur_poz_cr_mk['Проект'])
        self.ui.cmb_cr_mk_pr.setCurrentText(self.dict_cur_poz_cr_mk['Проект'])

        if self.dict_cur_poz_cr_mk["№ERP"] not in list_vals_cmb(self.ui.cmb_cr_mk_py):
            self.ui.cmb_cr_mk_py.addItem(self.dict_cur_poz_cr_mk["№ERP"])
        self.ui.cmb_cr_mk_py.setCurrentText(self.dict_cur_poz_cr_mk["№ERP"])

        if self.dict_cur_poz_cr_mk['Позиция'] not in list_vals_cmb(self.ui.cmb_cr_mk_poz):
            self.ui.cmb_cr_mk_poz.addItem(self.dict_cur_poz_cr_mk['Позиция'])
        self.ui.cmb_cr_mk_poz.setCurrentText(self.dict_cur_poz_cr_mk['Позиция'])

        self.ui.comboBox_sort_c.addItem(self.dict_cur_poz_cr_mk['Вид'])
        self.ui.comboBox_sort_c.setCurrentText(self.dict_cur_poz_cr_mk['Вид'])
        self.ui.comboBox_napravlenia.addItem(self.dict_cur_poz_cr_mk['Направление'])
        self.ui.comboBox_napravlenia.setCurrentText(self.dict_cur_poz_cr_mk['Направление'])

        self.ui.btn_select_nom_jur_vneplan.setEnabled(False)

        tbl = self.ui.table_zayavk
        CQT.clear_tbl(tbl)
        CQT.clear_tbl(self.ui.table_razr_MK)

        # if "tkp_current_schema" in self.__dict__ and self.tkp_current_schema is not None: # 03.04.25
        #     if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] in  (3,4):
        #         return
        if self.tkp_current_schema.is_tkp and not self.tkp_current_schema.is_parametric:
            return
        if self.ui.tabWidget_2.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_2,
                                                                            'Создание МК из *.XML'):
            # CQT.msgbox(f'Далее, "Файл" -> Загрузить XML')
            hat_c = ['Файл', 'Изделие', 'Количество', 'К_мат', 'К_врем']
            tbl.setColumnCount(5)
            tbl.setRowCount(0)
            tbl.setHorizontalHeaderLabels(hat_c)
            self.viborXML()
        if self.ui.tabWidget_2.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_2,
                                                                            'Разработка МК'):
            self.ui.table_razr_MK.clearContents()
            self.ui.table_razr_MK.setRowCount(0)
            self.ui.table_razr_MK.setColumnCount(21)
            self.ui.table_razr_MK.setHorizontalHeaderLabels(self.hat_c)
            self.ui.table_razr_MK.resizeColumnsToContents()
            # self.load_cust_drevo()
        # tbl.item(0, nk_kolvo).setText(str(self.dict_cur_poz_cr_mk['Количество']))

    def zapusk_docs(self, strok, kol):
        tbl = self.ui.table_nomenkl
        kol_naim = CQT.num_col_by_name_c(tbl, 'Наименование')
        kol_nn = CQT.num_col_by_name_c(tbl, 'Номенклатурный_номер')
        kol_pn = CQT.num_col_by_name_c(tbl, 'Пномер')
        if kol == kol_pn:
            nn_det = tbl.item(strok, kol_nn).text()
            naim = tbl.item(strok, kol_naim).text()
            CMS.run_link_DOCs_c(nn_det, naim)
            # F.run_file_c(adres,False)

    def poisk_nn(self):
        nn = self.ui.lineEdit_nom_n.text()
        naim = self.ui.lineEdit_naim.text()
        prim = self.ui.lineEdit_primech.text()
        tab_dse = self.ui.table_nomenkl
        for i in range(0, tab_dse.model().rowCount()):
            if nn in CQT.cells(i, 0, tab_dse) and naim in CQT.cells(i, 1, tab_dse) and prim in CQT.cells(i, 3, tab_dse):
                tab_dse.selectRow(i)
                return
        tab_dse.clearSelection()

    def otmizm_nom(self):
        self.zapoln_tabl_nomenkl()

    def del_nom(self):
        if self.tabl_nomenk.rowCount() < 1:
            return
        if self.tabl_nomenk.currentRow() == -1:
            CQT.msgbox('Не выбрана номенклатура')
            return
        rez = CQT.msgboxgYN(f'Удалить строку для {self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 1).text()}?')
        if rez == False:
            return
        if self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 3).text() == "":
            CSQ.custom_request_c(self.db_dse,
                                 f"""DELETE FROM dse where Пномер = {int(self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 0).text())} """)
        else:
            CQT.msgbox(
                f'На {self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 1).text()} уже создана техкарта, удаление не возможно.')
            return
        self.zapoln_tabl_nomenkl()
        CQT.msgbox(f'Строка успешно удалена')

    def cvet_izm_nom(self):
        CQT.set_color_of_obj_c(self.ui.btn_korr_nom, 155, 253, 155)

    def btn_korr_nom(self):
        if self.tabl_nomenk.rowCount() < 1:
            return
        if self.tabl_nomenk.currentRow() == -1:
            CQT.msgbox('Не выбрана номенклатура')
            return
        rez = CQT.msgboxgYN(
            f'Откорректировать строку для {self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 1).text()}?')
        if rez == False:
            return

        if self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 3).text() == "":

            CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Номенклатурный_номер = ?, Наименование = ?, 
            Примечание, = ? WHERE Пномер == {int(self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 0).text())};""",
                                 (self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 1).text(),
                                  self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 2).text(),
                                  self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 4).text().replace("|", "-"))
                                 )

        else:
            rez = CQT.msgboxgYN(
                f'Откорректировать <Номенклатурный_номер> невозможно, т.к. техкарта уже создана.'
                f' Внести корректировку в <Наименование> и <Примечание> ?')
            if rez == False:
                return

            CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Наименование = ?, 
                    Примечание, = ? WHERE Пномер == {int(self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 0).text())};""",
                                 (self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 2).text(),
                                  self.tabl_nomenk.item(self.tabl_nomenk.currentRow(), 4).text().replace("|", "-")))
        self.zapoln_tabl_nomenkl()
        # CQT.set_color_of_obj_c(self.ui.btn_korr_nom)
        CQT.msgbox(f'Изменения успешно записаны')

    def add_v_nomenkl(self):
        le_nn = self.ui.lineEdit_nom_n
        le_naim = self.ui.lineEdit_naim
        le_prim = self.ui.lineEdit_primech
        if le_naim.text() == "":
            le_naim.setFocus()
            CQT.msgbox("Не указано наименование")
            return
        nn = F.clear_row_for_file_name_c(le_nn.text())
        naim = F.clear_row_for_file_name_c(le_naim.text())
        if nn == '':
            CQT.msgbox(f'Номенклатурный номер не может быть пусто')
            return
        if naim == '':
            CQT.msgbox(f'Наименование не может быть пусто')
            return
        # rez = CSQ.find_in_db_c(self.db_dse, 'dse', {'Номенклатурный_номер': nn, 'Наименование': naim})
        rez = CSQ.custom_request_c(
            self.db_dse,
            f"""SELECT Номенклатурный_номер FROM dse WHERE Номенклатурный_номер == '{nn}' AND poki = {self.place.poki}; """)
        if len(rez) > 1:
            CQT.msgbox(f'ДСЕ {nn} уже существует')
            return
        # 15.04.25
        list_add = [nn.strip(), naim.strip(), '', le_prim.text(), "", '', '', '', '', '', '', '', '', "",
                    self.place.poki]
        # CSQ.add_line_into_db_sql_c(self.db_dse, 'dse',
        #                       [list_add])

        CSQ.custom_request_c(self.db_dse, f"""INSERT INTO dse (Номенклатурный_номер, Наименование, 
        Номер_техкарты, Примечание, Путь_docs, Доступ, Процесс, Нормы, Материалы, Тех_заметки, Теги, Мат_кд,
         Код_ЕРП, Классификатор, poki) VALUES ({', '.join(['?'] * len(list_add))});""", list_of_lists_c=[list_add])

        self.zapoln_tabl_nomenkl()
        self.ui.lineEdit_primech.setText(' шт.')
        CQT.msgbox(f'ДСЕ {nn} {naim} успешно занесена')

    def spis_MK_clck(self):
        param = self.tabl_mk.currentRow()
        if self.tabl_mk.item(param, CQT.num_col_by_name_c(self.tabl_mk, "Статус")).text() == "Открыта":
            self.ui.pushButton_close_mk.setEnabled(True)
            self.ui.pushButton_open_mk.setEnabled(False)
        else:
            self.ui.pushButton_close_mk.setEnabled(False)
            self.ui.pushButton_open_mk.setEnabled(True)

    def tabl_brak_dbl_clk(self):
        return
        label = self.ui.label_opis_braka
        strok = self.tabl_brak.currentRow()
        label_brak = self.ui.label_opis_braka
        n_k = 4
        if F.existence_file_c(F.scfg('foto_brak')) == False:
            CQT.msgbox(f'Недоступна папка {F.scfg("foto_brak")}')
            return
        if self.tabl_brak.currentColumn() == n_k:
            if self.tabl_brak.item(self.tabl_brak.currentRow(), n_k).text().replace('Фото:', '') != "":
                sp_foto = self.tabl_brak.item(self.tabl_brak.currentRow(), n_k).text().split(')(')
                sp_pap = F.list_of_files_c(F.scfg('foto_brak'))[0][1]
                for j in range(len(sp_foto)):
                    sp_foto[j] = sp_foto[j].replace(')', '')
                    sp_foto[j] = sp_foto[j].replace('(', '')
                    for i in range(len(sp_pap)):
                        if F.existence_file_c(F.scfg('foto_brak') + os.sep + sp_pap[i] + os.sep + sp_foto[j]) == True:
                            F.run_file_c(F.scfg('foto_brak') + os.sep + sp_pap[i] + os.sep + sp_foto[j])
                return
            return
        if label == "":
            return
        nom_id = self.naiti_parametr_v_stroke(label.text(), 'ID:')

        if nom_id == "":
            return
        kol_det = self.tabl_brak.item(strok, 8).text().replace('Количество:', '')

        nom_mk_isprav = self.naiti_parametr_v_stroke(label_brak.text(), 'Изгот.вновь по МК:')
        if nom_mk_isprav != '' and nom_mk_isprav != 'None':
            CQT.msgbox(f'ДСЕ уже изготавливается по МК №{nom_mk_isprav}')
            return

        if nom_id.startswith("0x"):
            pass
        else:
            self.ui.tabWidget.setCurrentIndex(1)
            self.ui.tabWidget_2.setCurrentIndex(1)
            self.add_gl_uzel(nom_id)
            return

        tree = self.ui.tree_base_tree
        spis_tree = CQT.list_from_tree_c(tree)
        if spis_tree == []:
            CQT.msgbox("Не открыто древо")
            self.viborXML()
            self.ui.tabWidget.setCurrentIndex(3)
            self.tabl_brak.selectRow(strok)
            self.tabl_brak_dbl_clk()
            return
        nom_kol_id = CQT.num_col_by_name_c(tree, 'ID')
        for i in range(len(spis_tree)):
            if spis_tree[i][nom_kol_id] == nom_id:
                level_c = spis_tree[i][20]
                rez = CQT.highlight_tree_number_c(tree, i + 1)
                if rez == False:
                    CQT.msgbox(f'Деталь {spis_tree[i][20]} не найдена')
                    return
                self.add_v_mk()
                table = self.ui.table_razr_MK
                for j in range(table.rowCount()):
                    if table.item(j, 6).text() == nom_id:
                        table.item(j, CQT.num_col_by_name_c(table, 'Кол. по заявке')).setText(kol_det)
                        break
                # table.setCurrentCell(table.rowCount() - 1, 1)
                # for j in range(i + 1, len(spis_tree)):
                #    if spis_tree[j][20] > level_c:
                #        rez = CQT.highlight_tree_number_c(tree, i + 1)
                #        if rez == False:
                #            CQT.msgbox(f'Деталь {spis_tree[j][20]} не найдена')
                #            self.ui.tabWidget.setCurrentIndex(0)
                #            return
                #        self.add_v_mk()
                #    else:
                #        break
                CQT.msgbox(
                    'В случе если основание создания маршрутной карты это БРАК, то необходимо, посел создания ассоциировать брак с МК. во вкладке брак, а после сохранить.')
                self.ui.pushButton_save_MK.setEnabled(False)
                return

    def click_brak(self):
        return

    def del_ass(self):
        self.ui.label_ass.clear()

    def close_mk(self):
        if self.tabl_mk.currentRow() == -1:
            return
        tbl = self.tabl_mk
        if not CMS.user_access(self.bd_naryad, 'мкарт_маршрутные_закрытьоткрыть', F.user_name()):
            return
        row = self.tabl_mk.currentRow()
        nom_tek_mk = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Пномер')).text()
        mk_obj = CMS.Marshrut_cards(int(nom_tek_mk), self.bd_naryad, self.db_resxml, load_resource=False)
        if mk_obj.is_del():
            CQT.msgbox(f'Заблокировано')
            return
        nom_mk = nom_tek_mk
        project = tbl.item(tbl.currentRow(),
                           CQT.num_col_by_name_c(tbl, 'Номенклатура')).text()
        nom_pu_r = tbl.item(tbl.currentRow(),
                            CQT.num_col_by_name_c(tbl, 'Номер_заказа')).text()
        nom_pr_r = tbl.item(tbl.currentRow(),
                            CQT.num_col_by_name_c(tbl, 'Номер_проекта')).text()
        kolvo = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Количество')).text()
        prim = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Примечание')).text()
        osnovanie = tbl.item(tbl.currentRow(),
                             CQT.num_col_by_name_c(tbl, 'Основание')).text()

        # qery = CSQ.find_in_db_c(self.bd_naryad, 'mk', {'Пномер': int(nom_tek_mk)},
        #                      ['Статус', 'Дата_завершения', 'Основание'])
        qery = CSQ.custom_request_c(self.bd_naryad, f"""SELECT Статус, Дата_завершения, Основание FROM mk 
        WHERE Пномер == {int(nom_tek_mk)};""", hat_c=False)

        if qery[0][0] == "Открыта":
            # rez = CSQ.update_bd_sql(self.bd_naryad, 'mk', {'Статус': 'Закрыта'}, {'Пномер': int(nom_tek_mk)})
            rez = CSQ.custom_request_c(self.bd_naryad,
                                       f"""UPDATE mk SET Статус == 'Закрыта' WHERE Пномер = {int(nom_tek_mk)};""")

            if rez == False:
                CQT.msgbox('Не удалось записать')
                return
            self.tab_click(row)

            try:
                msg = f"{F.user_full_namre()} ЗАКРЫЛ мк № {str(nom_mk)}:\n{project} - {str(kolvo)} шт.\n{nom_pu_r.strip()} Проект: {nom_pr_r.strip()}\n" \
                      f"Прим.: {prim} {osnovanie}"
                CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
            except:
                print('Ошибка отправки в Б24')
        self.ui.pushButton_open_mk.setEnabled(True)
        self.ui.pushButton_close_mk.setEnabled(False)

    def spis_op_po_mk_id_op(self, sp_tabl_mk, id, op):
        for j in range(1, len(sp_tabl_mk)):
            if sp_tabl_mk[j][6] == id:
                for i in range(11, len(sp_tabl_mk[0]), 4):
                    if sp_tabl_mk[j][i].strip() != '':
                        obr = sp_tabl_mk[j][i].strip().split('$')
                        obr2 = obr[-1].split(";")
                        if op in obr2:
                            return obr2
                return None

    def del_mk(self):
        if self.tabl_mk.currentRow() == -1:
            return
        tbl = self.ui.table_spis_MK

        row = CQT.get_dict_line_form_tbl(tbl)

        nom_mk = row['Пномер']
        project = row['Номенклатура']
        nom_pu_r = row['Номер_заказа']
        nom_pr_r = row['Номер_проекта']
        kolvo = row['Количество']
        prim = row['Примечание']
        osnovanie = row['Основание']

        if CMS.user_access(self.bd_naryad, 'созданиемаршрутныхкарт_удалить', F.user_name()) == False:
            return


        mk_obj = CMS.Marshrut_cards(int(nom_mk), self.bd_naryad, self.db_resxml, load_resource=False)
        if mk_obj.is_del():
            if not CQT.msgboxgYN(f'Cнять отметку на УДАЛЕНИЕ маршрутной карты № {nom_mk} ?'):
                return
            CSQ.custom_request_c(self.bd_naryad,
                                 f"""UPDATE mk SET (На_удал,Статус) = (0,"Закрыта") WHERE Пномер = {int(nom_mk)}""")
            CQT.set_val_tbl_by_name(tbl, tbl.currentRow(), 'Статус', 'Закрыта')
            CQT.set_val_tbl_by_name(tbl, tbl.currentRow(), 'На удаление', '')
            CQT.msgbox(f"Маршрутная карта номер {nom_mk} снята с УДАЛЕНИЯ успешно")
            try:
                msg = (f"{F.user_full_namre()} !снял с УДАЛЕНИЯ мк"
                       f" № {str(nom_mk)}:\n{project} - {str(kolvo)} шт.\n{nom_pu_r.strip()} Проект: {nom_pr_r.strip()}\n"
                       f"Прим.: {prim} {osnovanie}")
                CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
            except:
                print('Ошибка отправки в Б24')

            return

        if row['Статус'] != 'Закрыта':
            CQT.msgbox(f'Удалить можно только закрытаую МК')
            return

        if not CQT.msgboxgYN(f'Провести отметку на УДАЛЕНИЕ маршрутной карты № {nom_mk} ?'):
            return

        CSQ.custom_request_c(self.bd_naryad,
                             f"""UPDATE mk SET (На_удал,Статус) = (1,"НаУдаление") WHERE Пномер = {int(nom_mk)}""")
        CQT.set_val_tbl_by_name(tbl, tbl.currentRow(), 'Статус', 'НаУдаление')
        CQT.msgbox(f"Маршрутная карта номер {nom_mk} отмечена на УДАЛЕНИЕ успешно")
        try:
            msg = (f"{F.user_full_namre()} !поставил на УДАЛЕНИЕ мк"
                   f" № {str(nom_mk)}:\n{project} - {str(kolvo)} шт.\n{nom_pu_r.strip()} Проект: {nom_pr_r.strip()}\n"
                   f"Прим.: {prim} {osnovanie}")
            CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
        except:
            print('Ошибка отправки в Б24')
        return

        # ++++++++++++++++++++++++03.07.2024 изменение логики++++++++++++++++++++++
        # if 'shift' in CQT.get_key_modifiers(self):
        #    if CMS.user_access(self.bd_naryad, 'созданиемаршрутныхкарт_удалить', F.user_name()) == False:
        #        return
        #    progress = self.tabl_mk.item(self.tabl_mk.currentRow(), CQT.num_col_by_name_c(self.tabl_mk, 'Прогресс')).text()
        #    if progress != '':
        #        CQT.msgbox('Нельзя удалить начатую МК')
        #        return
        #    otv = CQT.msgboxgYN('Точно удалить полность маршрутную карту №'
        #                        + nom_mk + '?')
        #    if otv:
        #        # rez = CSQ.delete(self.bd_naryad, 'mk', {'Пномер': int(nom_mk)})
        #        rez = CSQ.custom_request_c(self.bd_naryad, f"""DELETE FROM mk where Пномер = {int(nom_mk)}""")
        #        if rez == False:
        #            CQT.msgbox('Запрос не выполнен')
        #            return
        #        rez = CSQ.custom_request_c(self.bd_naryad, f"""DELETE FROM zagot where Ном_МК = {int(nom_mk)}""")
        #        rez = CSQ.custom_request_c(self.db_resxml, f"""DELETE FROM res where Номер_мк = {int(nom_mk)}""")
        #        rez = CSQ.custom_request_c(self.db_resxml, f"""DELETE FROM xml where Номер_мк = {int(nom_mk)}""")
        #        rez = CSQ.custom_request_c(self.bd_files, f"""DELETE FROM MK_founding where Num_mk = {int(nom_mk)}""")
        #        try:
        #            rez = CSQ.custom_request_c(self.bd_naryad,
        #                                       f"""DELETE FROM дорезки_мк where Номер_мк = {int(nom_mk)}""")
        #        except:
        #            pass
        #        self.tab_click(row)
        #        if F.existence_file_c(F.scfg('mk_data') + os.sep + nom_mk + '.txt') == True:
        #            F.delete_file_c(F.scfg('mk_data') + os.sep + nom_mk + '.txt')
        #        if F.existence_file_c(F.scfg('mk_data') + os.sep + nom_mk):
        #            F.delete_dir_c(F.scfg('mk_data') + os.sep + nom_mk)
        #        CQT.msgbox(f"Маршрутная карта номер {nom_mk} удалена успешно")
        #        try:
        #            msg = f"{F.user_full_namre()} !УДАЛИЛ мк № {str(nom_mk)}:\n{project} - {str(kolvo)} шт.\n{nom_pu_r.strip()} Проект: {nom_pr_r.strip()}\n" \
        #                  f"Прим.: {prim} {osnovanie}"
        #            self.send_info_mk_b24(msg, 'chat41228')
        #        except:
        #            print('Ошибка отправки в Б24')
        #        return
        #
        #    if not CQT.msgboxgYN('Точно удалить полность маршрутную карту №'
        #                  + nom_mk + '?'):
        #        return
        #    if self.tabl_mk.item(self.tabl_mk.currentRow(), CQT.num_col_by_name_c(self.tabl_mk, 'Статус')).text() != "Закрыта":
        #        CQT.msgbox(f'Статус должен быть -=Закрыта=-')
        #        return
        #    CSQ.custom_request_c(self.bd_naryad,f"""UPDATE mk SET На_удал = 1 WHERE Пномер = {nom_mk}""")
        #    CQT.msgbox(f"Маршрутная карта номер {nom_mk} удалена успешно")
        #    try:
        #        msg = (f"{F.user_full_namre()} !поставил на УДАЛЕНИЕ мк"
        #               f" № {str(nom_mk)}:\n{project} - {str(kolvo)} шт.\n{nom_pu_r.strip()} Проект: {nom_pr_r.strip()}\n"
        #              f"Прим.: {prim} {osnovanie}")
        #        self.send_info_mk_b24(msg, 'chat41228')
        #    except:
        #        print('Ошибка отправки в Б24')
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def add_res_to_mk(self, xml, kol_vo_izdeliy, nom_tek_mk, xml_head, conn='', cur=''):
        self.res = CMS.resource_from_xml_c(self, CMS.podgotovka_xml(self, XML.spisok_iz_xml(str_f=xml), xml_head),
                                           kol_vo_izdeliy, conn=conn, cur=cur)

        ves, self.ves_res_list = self.raschet_vesa_dse(self.res)

        check_line_db = CSQ.custom_request_c(self.db_resxml,
                                             f"""SELECT * FROM res WHERE Номер_мк == {int(nom_tek_mk)}""", one=True)

        if len(check_line_db) > 1:
            res_pickle = F.to_binary_pickle(self.res)
            rez = CSQ.custom_request_c(self.db_resxml, f"""UPDATE res SET data = ? WHERE Номер_мк = ?;""",
                                       list_of_lists_c=[[res_pickle, int(nom_tek_mk)]])
            if rez == False:
                CSQ.close_bd(conn, cur)
                CQT.msgbox('!!! Ресурсная НЕ обновлена')
                return False
            CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Вес = {ves} WHERE Пномер = {int(nom_tek_mk)}""")
            CQT.msgbox('Ресурсная успешно обновлена')
        else:
            res_pickle = F.to_binary_pickle(self.res)
            rez = CSQ.custom_request_c(self.db_resxml, """INSERT INTO res(Номер_мк,data) VALUES (?,?);""",
                                       list_of_lists_c=[[int(nom_tek_mk),
                                                         res_pickle]], conn=conn, cur=cur)
            if rez == False or rez == None:
                CSQ.close_bd(conn, cur)
                CQT.msgbox('!!! Ресурсная НЕ добавлена')
                return False
            CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Вес = {ves} WHERE Пномер = {int(nom_tek_mk)}""")
            user = F.user_full_namre()
            CMS.send_info_mk_b24_by_action(
                # 05.08.25 именованные параметры вызывают ошибку в декораторе CQT.onerror если не передан self
                f'{user} перегенерировал(а) ресурсную МК {nom_tek_mk}',
                'Ошибки МК'
            )
            CQT.msgbox('Ресурсная успешно добавлена')

    @CQT.onerror
    def create_and_add_res_to_mk(self):
        if self.tabl_mk.currentRow() == -1:
            return
        row = self.tabl_mk.currentRow()
        nom_tek_mk = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Пномер')).text()
        kolvo = int(self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Количество')).text())
        query = f'''SELECT data as xml FROM xml 
                    WHERE Номер_мк == {int(nom_tek_mk)}'''
        rez = CSQ.custom_request_c(self.db_resxml, query)
        if rez == False or len(rez) == 1:
            CQT.msgbox(f'Ошибка загузки XML')
            return
        xml = rez[-1][0]
        self.add_res_to_mk(xml, kolvo, nom_tek_mk, 1)

    def open_mk(self):
        if self.tabl_mk.currentRow() == -1:
            return
        if not CMS.user_access(self.bd_naryad, 'мкарт_маршрутные_закрытьоткрыть', F.user_name()):
            return
        row = self.tabl_mk.currentRow()
        tbl = self.tabl_mk
        nom_tek_mk = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Пномер')).text()
        mk_obj = CMS.Marshrut_cards(int(nom_tek_mk), self.bd_naryad, self.db_resxml, load_resource=False)
        if mk_obj.is_del():
            CQT.msgbox(f'Заблокировано')
            return
        nom_mk = nom_tek_mk
        project = tbl.item(tbl.currentRow(),
                           CQT.num_col_by_name_c(tbl, 'Номенклатура')).text()
        nom_pu_r = tbl.item(tbl.currentRow(),
                            CQT.num_col_by_name_c(tbl, 'Номер_заказа')).text()
        nom_pr_r = tbl.item(tbl.currentRow(),
                            CQT.num_col_by_name_c(tbl, 'Номер_проекта')).text()
        kolvo = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Количество')).text()
        prim = tbl.item(tbl.currentRow(), CQT.num_col_by_name_c(tbl, 'Примечание')).text()
        osnovanie = tbl.item(tbl.currentRow(),
                             CQT.num_col_by_name_c(tbl, 'Основание')).text()
        conn, cur = CSQ.connect_bd(self.bd_naryad)
        # qery = CSQ.find_in_db_c(self.bd_naryad, 'mk', {'Пномер': int(nom_tek_mk)}, ['Статус', 'Прогресс', 'Основание', 'Количество'], conn=conn,cur=cur)
        qery = CSQ.custom_request_c(self.bd_naryad, f"""SELECT Статус, Прогресс, Основание, Количество, Дата_завершения, Номер_заказа 
            FROM mk WHERE Пномер == {int(nom_tek_mk)};""", conn=conn, cur=cur, rez_dict=True, one=True)
        if qery['Статус'] == "Закрыта":
            if qery['Номер_заказа'] == "-":
                CSQ.close_bd(conn, cur)
                CQT.msgbox('Нельзя открыть МК без №ERP')
                return
            if qery['Дата_завершения'] != "":
                CSQ.close_bd(conn, cur)
                CQT.msgbox('Нельзя открыть завершенную закрытую МК')
                return
            kolvo = qery['Количество']
            if kolvo == 0:
                CSQ.close_bd(conn, cur)
                CQT.msgbox('Необходимо исправить количество, не может быть 0')
                return

            query = f'''SELECT xml.data as xml, res.data as Ресурсная, xml.Head as xml_head FROM xml 
                                            INNER JOIN res ON res.Номер_мк = xml.Номер_мк
                                            WHERE xml.Номер_мк == {int(nom_tek_mk)}'''
            rez = CSQ.custom_request_c(self.db_resxml, query)

            if len(rez) == 1:
                CQT.msgbox(f'Ошибка выгрузки ресурсной или хмл')
                return

            if rez[-1][1] == '':
                xml = rez[-1][0]
                xml_head = rez[-1][2]
                rez = self.add_res_to_mk(xml, kolvo, nom_tek_mk, xml_head, conn=conn, cur=cur)
                if rez == False:
                    return
            # rez = CSQ.update_bd_sql(self.bd_naryad, 'mk', {'Статус': 'Открыта'}, {'Пномер': int(nom_tek_mk)}, conn = conn, cur = cur)
            rez = CSQ.custom_request_c(self.bd_naryad,
                                       f"""UPDATE mk SET Статус = 'Открыта' WHERE Пномер = {int(nom_tek_mk)};""",
                                       conn=conn, cur=cur)
            if rez == False:
                CSQ.close_bd(conn, cur)
                CQT.msgbox('Запрос не выполнен')
                return
            self.ui.pushButton_open_mk.setEnabled(False)
            self.ui.pushButton_close_mk.setEnabled(True)
            self.tab_click(row)

            try:
                msg = f"{F.user_full_namre()} ОТКРЫЛ мк № {str(nom_mk)}:\n{project} - {str(kolvo)} шт.\n{nom_pu_r.strip()} Проект: {nom_pr_r.strip()}\n" \
                      f"Прим.: {prim} {osnovanie}"
                CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
            except:
                print('Ошибка отправки в Б24')
        else:
            CSQ.close_bd(conn, cur)

    def corr_mk(self, row, kol):
        if self.tabl_mk.hasFocus() == True:
            if self.tabl_mk.currentRow() == -1:
                return
            nom_tek_mk = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Пномер')).text()
            prim = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Примечание')).text()
            prior = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Приоритет')).text()
            paral = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Коэф_парал')).text()
            vid = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Вид')).text()
            iscl = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Искл_план_рм')).text()
            if F.is_numeric(prior) == False:
                CQT.msgbox('Не число Приоритет')
                self.load_tab_mk()
                return
            if F.is_numeric(paral) == False:
                CQT.msgbox('Не число Коэф_парал')
                self.load_tab_mk()
                return

            prior = int(prior)
            paral = int(paral)
            dict_zamen = {';': ',', '-': ',', '/': ',', '\\': ',', ' ': ','}
            for key in dict_zamen.keys():
                iscl = iscl.replace(key, dict_zamen[key])
            # rez = CSQ.update_bd_sql(self.bd_naryad, 'mk',
            #                        {'Примечание': prim, 'Приоритет': prior, 'Коэф_парал': paral, 'Вид': vid, 'Искл_план_рм': iscl},
            #                        {'Пномер': int(nom_tek_mk)})
            rez = CSQ.custom_request_c(self.bd_naryad, f"""UPDATE mk SET Примечание = '{prim}', Приоритет = {prior}, 
                    Коэф_парал = {paral}, Вид = '{vid}', Искл_план_рм = '{iscl}' WHERE Пномер = '{int(nom_tek_mk)}';""")
            if rez == False:
                CQT.msgbox('Запрос не выполнен')
                return
            self.cvet_prioritetov()

    def naiti_parametr_v_stroke(self, stroka, parametr):
        arr = stroka.split('  ')
        for i in arr:
            if i != '':
                if i.strip().startswith(parametr) == True:
                    return i.replace(parametr, '').strip()

    def ass_brak_to_mk(self):
        if self.tabl_brak.currentIndex() == -1:
            return
        tabl_razr_mk = self.ui.table_razr_MK
        label = self.ui.label_ass
        label_brak = self.ui.label_opis_braka
        nom_oper = self.naiti_parametr_v_stroke(label_brak.text(), '№ операции:')
        nom_id = self.naiti_parametr_v_stroke(label_brak.text(), 'ID:')
        dse = self.naiti_parametr_v_stroke(label_brak.text(), 'ДСЕ:')
        nom_kol_nach_tabl = CQT.num_col_by_name_c(tabl_razr_mk, 'Сумм.Количество')
        if nom_id == None:
            return
        if self.tabl_brak.currentRow() == None or self.tabl_brak.currentRow() == -1:
            CQT.msgbox("Не выбран акт о браке")
            return
        nom = self.tabl_brak.item(self.tabl_brak.currentRow(), 0).text().replace('Номер акта:', '')

        if nom_kol_nach_tabl == None:
            CQT.msgbox('Не создана МК')
            return
        kol_id = CQT.num_col_by_name_c(tabl_razr_mk, 'ID')
        kol_naim = CQT.num_col_by_name_c(tabl_razr_mk, 'Наименование')
        kol_nn = CQT.num_col_by_name_c(tabl_razr_mk, 'Обозначение')
        flag_naid = False
        for i in range(tabl_razr_mk.rowCount()):
            if flag_naid == True:
                break
            if tabl_razr_mk.item(i, kol_id).text() == nom_id or tabl_razr_mk.item(i,
                                                                                  kol_naim).text() + ' ' + tabl_razr_mk.item(
                i, kol_nn).text() == dse:
                for j in range(tabl_razr_mk.columnCount() - 1, nom_kol_nach_tabl, -1):
                    if tabl_razr_mk.item(i, j).text() != '':
                        if nom_oper not in tabl_razr_mk.item(i, j).text():
                            tabl_razr_mk.item(i, j).setText('')
                            flag_pust = True
                            for k in range(tabl_razr_mk.rowCount()):
                                if tabl_razr_mk.item(k, j).text() != '':
                                    flag_pust = False
                                    break
                            if flag_pust == True:
                                for k in range(4):
                                    t = CQT.list_from_wtabl_c(tabl_razr_mk, "", True)
                                    tabl_razr_mk.removeColumn(j)
                        else:
                            flag_naid = True
                            break
        if flag_naid == False:
            CQT.msgbox('Не найдена деталь для ассоциации ' + nom_id)
            return

        spis_ass = self.ui.label_ass.text().split(';')
        if spis_ass[0] == '':
            spis_ass.pop(0)
        spis_ass.append(nom)
        self.ui.label_ass.setText(';'.join(spis_ass))
        CQT.msgbox(
            'Нужно проверить, что концовка новой маршрутной карты должна совпдать с местом возникновения брака по основной маршрутной карте.')
        self.ui.tabWidget.setCurrentIndex(1)
        self.ui.pushButton_save_MK.setEnabled(True)

    def zapoln_tabl_nomenkl(self):
        tabl_nomenk = self.ui.table_nomenkl
        conn, cur = CSQ.connect_bd(self.db_dse)
        # spis = CSQ.list_from_db_sql_c(self.db_dse, 'dse', False, True,conn=conn, cur=cur)
        spis = CSQ.custom_request_c(self.db_dse,
                                    f"""SELECT Пномер,Номенклатурный_номер,Наименование,Номер_техкарты,Примечание FROM dse WHERE poki == {self.place.poki};""",
                                    hat_c=True)
        CSQ.close_bd(conn, cur)
        red_nom = {1, 2, 4}
        CQT.fill_wtabl_old_c(self, spis, tabl_nomenk, 0, red_nom, (), (), 200, True, '',
                             max_vis_row=20)
        CMS.fill_filtr_c(self, self.ui.tbl_filtr_nomenkl, tabl_nomenk, hidden_scroll=True)
        # tabl_nomenk.setMouseTracking(True)
        # tabl_nomenk.selectRow(tabl_nomenk.rowCount()-1)
        # CQT.set_color_of_obj_c(self.ui.btn_korr_nom)

    @CQT.onerror
    def load_tab_mk(self):
        tabl_mk = self.ui.table_spis_MK
        tmp_poz = -1
        if tabl_mk.currentIndex() != -1:
            tmp_poz = tabl_mk.currentIndex()
        start_date = F.start_end_dates_c(F.date_add_days(F.now(''), -1365, '', ''),
                                         '', 'y', "%Y-%m-%d")[0]
        custom_request_c = f'''SELECT mk.Пномер, Тип_мк.Имя as Тип,  mk.Дата, mk.Статус,  mk.Номенклатура,
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
        mk.На_удал as "На удаление", 
           mk.Ресурсная_дата, mk.Примечание, mk.Основание,
         mk.Прогресс, 
         
         CASE WHEN plan.Приоритет IS NOT NULL 
       THEN plan.Приоритет 
       ELSE mk.Приоритет 
       END AS Приоритет, 
        
        CASE WHEN napravlenie.name IS NOT NULL 
       THEN napravlenie.name 
       ELSE mk.Направление 
       END AS Направление, 
        
         
         mk.Вес, mk.Количество,  mk.Дата_завершения,  mk.Коэф_парал, 
          mk.Искл_план_рм, тип_дорезок.Имя AS тип_дорезок, тип_доработок.Имя AS тип_доработок,
           mk.НомКплан as "Номер КПЛ", mk.ФИО as "Создал"  FROM mk 
          LEFT JOIN plan ON plan.Пномер = mk.НомКплан  
          LEFT JOIN napravl_deyat ON napravl_deyat.Пномер = plan.Направление_деятельности 
          LEFT JOIN napravlenie ON napravlenie.Пномер = napravl_deyat.Направление  
         LEFT JOIN пл_оуп ON пл_оуп.НомПл = mk.НомКплан 
         LEFT JOIN знпр ON знпр.s_num = пл_оуп.Пномер_ЗП 
         LEFT JOIN Тип_мк ON Тип_мк.Пномер = mk.Тип 
         LEFT JOIN дорезки_мк ON дорезки_мк.Номер_мк = mk.Пномер
         LEFT JOIN тип_дорезок ON тип_дорезок.Пномер = дорезки_мк.Причина
         LEFT JOIN тип_доработок ON тип_доработок.Пномер = mk.Тип_доработки
         WHERE Date("20" || Дата) > Date("{start_date}") and plan.poki = {self.place.poki};'''
        # spis = CSQ.list_from_db_sql_c(self.bd_naryad, 'mk', False, True)
        spis = CSQ.custom_request_c(self.bd_naryad, custom_request_c, '', True, attach_dbs=(self.db_kplan))

        spis_korr = {F.num_col_by_name_in_hat_c(spis, 'Примечание')
            , F.num_col_by_name_in_hat_c(spis, 'Коэф_парал')
            , F.num_col_by_name_in_hat_c(spis, 'Искл_план_рм')}

        if self.ui.chk_progress.isChecked():
            # === процент выполнения====
            spis[0].append('Прогресс_01')
            for i in range(1, len(spis)):
                spis[i].append('Прогресс_01')
        CQT.fill_wtabl_old_c(self, spis, tabl_mk, 0, spis_korr, (), (), 200, True, '')
        CQT.color_cell_wtable_c(tabl_mk, 'Прогресс', '', 'Завершено', 207, 247, 193, False)
        CQT.color_cell_wtable_c(tabl_mk, 'Статус', '', 'Закрыта')
        CQT.color_cell_wtable_c(tabl_mk, 'Статус', '', 'Открыта', 243, 232, 149, False)
        CQT.color_cell_wtable_c(tabl_mk, 'Статус', '', 'НаУдаление', 255, 144, 75, False)
        nf_vid = CQT.num_col_by_name_c(tabl_mk, 'Вид')
        nf_del = CQT.num_col_by_name_c(tabl_mk, "На удаление")
        for i in range(tabl_mk.rowCount()):
            vid = tabl_mk.item(i, nf_vid).text()
            udal = tabl_mk.item(i, nf_del).text()
            if udal == '1':
                tabl_mk.item(i, nf_del).setText(CEMOJ.EmojiMain.Статусы.error.symbol)
            else:
                tabl_mk.item(i, nf_del).setText('')
            if vid in self.Data_plan.DICT_NAPR_DEYAT_PSDNAME:
                r, g, b = self.Data_plan.DICT_NAPR_DEYAT_PSDNAME[vid]['Цвет'].split(';')
                CQT.set_color_wtab_c(tabl_mk, i, nf_vid, r, g, b)
        for key in self.DICT_TIP_MK.keys():
            r, g, b = self.DICT_TIP_MK[key]['rgb'].split(',')
            CQT.color_cell_wtable_c(tabl_mk, 'Тип', '', key, r, g, b, False)
        self.cvet_prioritetov()
        # CQT.fill_progress_c(self, tabl_mk, CQT.num_col_by_name_c(tabl_mk, 'Уровень_вып'))
        tabl_mk.setCurrentIndex(tmp_poz)

    def cvet_prioritetov(self):
        tabl_mk = self.ui.table_spis_MK
        CQT.color_cell_wtable_c(tabl_mk, 'Приоритет', '', "0", 254, 254, 254, False)
        CQT.color_cell_wtable_c(tabl_mk, 'Приоритет', '', "1", 254, 200, 200, False)
        CQT.color_cell_wtable_c(tabl_mk, 'Приоритет', '', "2", 254, 150, 150, False)
        CQT.color_cell_wtable_c(tabl_mk, 'Приоритет', '', "3", 254, 100, 100, False)
        CQT.color_cell_wtable_c(tabl_mk, 'Приоритет', '', "4", 254, 50, 50, False)
        CQT.color_cell_wtable_c(tabl_mk, 'Приоритет', '', "5", 254, 0, 0, False)

    def set_btns_manual_edit_enabled(self, val=True):
        self.ui.pushButton_create_koren.setEnabled(val)
        self.ui.pushButton_create_vxodyash.setEnabled(val)
        self.ui.pushButton_create_udalituzel.setEnabled(val)
        self.ui.pushButton_up_row.setEnabled(val)
        self.ui.pushButton_down_row.setEnabled(val)
        self.ui.pushButton_push_strukt_into_db_dse.setEnabled(val)
        self.ui.label_ass.clear()
        self.ui.lineEdit_ves.clear()
        self.ui.comboBox_napravlenia.setCurrentText('')
        self.ui.comboBox_sort_c.setCurrentText('')

        self.ui.cmb_cr_mk_py.clear()
        self.ui.cmb_cr_mk_poz.clear()
        CQT.clear_tbl(self.ui.tbl_info_cr_mk)
        self.ui.pushButton_ass_brak_to_mk.setEnabled(val)
        self.ui.btn_save_cust_drevo.setEnabled(val)
        self.ui.btn_load_cust_drevo.setEnabled(val)
        self.ui.pushButton_create_paralel.setEnabled(val)

        if self.ui.tabWidget_2.tabText(self.ui.tabWidget_2.currentIndex()) == 'Разработка МК':
            self.ui.btn_vigruzka_norm_mat.setEnabled(True)
        else:
            self.ui.btn_vigruzka_norm_mat.setEnabled(False)

        self.ui.pushButton_save_MK.setEnabled(val)
        if 'dict_cur_poz_cr_mk' in self.__dict__:
            CQT.fill_wtabl(F.dict_to_param_val(self.dict_cur_poz_cr_mk, 'Параметр', 'Значение'), self.ui.tbl_info_cr_mk)
    def clear_mk(self):
        tabl_cr_stukt = self.ui.table_razr_MK

        tabl_cr_stukt.clearContents()
        tabl_cr_stukt.setRowCount(0)
        tabl_cr_stukt.setColumnCount(21)
        tabl_cr_stukt.setHorizontalHeaderLabels(self.hat_c)
        tabl_cr_stukt.resizeColumnsToContents()
        # for i in range(12, 19):
        #    tabl_cr_stukt.setColumnHidden(i, True)
        CQT.set_color_sort_cell_table_c(tabl_cr_stukt)
        tabl_cr_stukt.setSelectionMode(1)
        self.list_vars_vo = []
        self.set_btns_manual_edit_enabled(True)
        self.а = 1
        self.cr_mk_xml_koef_norm_time = 1
        try:
            del self.dict_cur_poz_cr_mk
        except:
            pass
        self.ui.cmb_cr_mk_poz.setEnabled(True)
        self.ui.le_name_predv_res.clear()
        self.ui.lbl_stat_kalc_tkp.setText('')
        self.ui.lbl_summ_weight.clear()
        self.ui.lbl_summ_weight_wo_pki.clear()
        self.ui.lbl_stat_kalc_tkp.clear()
        try:
            # del self.tkp_current_schema
            self.tkp_current_schema.clear()
        except:
            pass
        CQT.clear_tbl(self.ui.table_zayavk)
        # 24.12.2025
        if hasattr(self, '_mk_dirty'):
            self._mk_dirty.mark_clean()

    def check_pre_create_mk(self):
        butt_add_gl_uzel = self.ui.pushButton_create_koren
        tabl_cr_stukt = self.ui.table_razr_MK
        nk = CQT.num_col_by_name_c(tabl_cr_stukt, 'Уровень')
        nk_kol_p_z = CQT.num_col_by_name_c(tabl_cr_stukt, 'Кол. по заявке')
        nk_kol = CQT.num_col_by_name_c(tabl_cr_stukt, 'Количество')
        nk_kol_izd = CQT.num_col_by_name_c(tabl_cr_stukt, 'Количество на изделие')
        nk_kol_pki = CQT.num_col_by_name_c(tabl_cr_stukt, 'ПКИ')
        naim = CQT.num_col_by_name_c(tabl_cr_stukt, 'Наименование')
        nn = CQT.num_col_by_name_c(tabl_cr_stukt, 'Обозначение')
        nom_kol_mass = CQT.num_col_by_name_c(tabl_cr_stukt, 'Масса/М1,М2,М3')
        nk_name_potreb_oper_analogue = CQT.num_col_by_name_c(tabl_cr_stukt, 'Опер_потребл')

        if nk == False or nk_kol_p_z == False:
            CQT.msgbox('Ошибка выбора колонок')
            return False
        if nk == None:
            return False
        if nk_kol_p_z == None:
            return False

        # if "tkp_current_schema" in self.__dict__ and self.tkp_current_schema is not None:
        #     if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] in (3,4):
        if self.tkp_current_schema.is_tkp and not self.tkp_current_schema.is_parametric:

            for i in range(tabl_cr_stukt.rowCount()):
                if tabl_cr_stukt.item(i, nom_kol_mass).text().replace('0//', '') != '' and tabl_cr_stukt.item(i,
                                                                                                              nk_kol_pki).text() != '1':
                    if tabl_cr_stukt.item(i, nk_name_potreb_oper_analogue).text() == '':
                        CQT.msgbox(f'В строке {i + 1} не указана целевая операция потребления материала')
                        return False

        min = 1000
        for i in range(tabl_cr_stukt.rowCount()):
            if int(tabl_cr_stukt.item(i, nk).text()) < min:
                min = int(tabl_cr_stukt.item(i, nk).text())
        if min > 0:
            for i in range(tabl_cr_stukt.rowCount()):
                tabl_cr_stukt.item(i, nk).setText(str(int(tabl_cr_stukt.item(i, nk).text()) - min))
        for i in range(tabl_cr_stukt.rowCount()):
            flag_err = False
            if int(tabl_cr_stukt.item(i, nk).text()) == 0:
                tabl_cr_stukt.item(i, nk_kol).setText(str(1))
            if tabl_cr_stukt.item(i, nom_kol_mass).text() == "" or tabl_cr_stukt.item(i, nom_kol_mass).text() == "//":
                tabl_cr_stukt.item(i, nom_kol_mass).setText("0//")
            if tabl_cr_stukt.item(i, nom_kol_mass).text().count('/') < 1 or F.is_numeric(
                    tabl_cr_stukt.item(i, nom_kol_mass).text().split('/')[0]) == False:
                CQT.msgbox(
                    f'Не записана масса в {i + 1} строке, {tabl_cr_stukt.horizontalHeaderItem(nom_kol_mass).text()} колонке. Значение:({tabl_cr_stukt.item(i, nom_kol_mass).text()})')
                flag_err = True
            if F.is_numeric(tabl_cr_stukt.item(i, 19).text()) == False and int(tabl_cr_stukt.item(i, nk).text()) == 0:
                CQT.msgbox(
                    f'Не число в {i + 1} строке, {tabl_cr_stukt.horizontalHeaderItem(19).text()} колонке. Значение:({tabl_cr_stukt.item(i, 19).text()})')
                flag_err = True
            if F.is_numeric(tabl_cr_stukt.item(i, 9).text()) == False and tabl_cr_stukt.item(i, 9).text() != "":
                CQT.msgbox(
                    f'Не число в {i + 1} строке, {tabl_cr_stukt.horizontalHeaderItem(9).text()} колонке. Значение:({tabl_cr_stukt.item(i, 9).text()})')
                flag_err = True
            if flag_err == True:
                return False
            if F.is_numeric(tabl_cr_stukt.item(i, nk_kol).text()) == False:
                CQT.msgbox(
                    f'в строке {i + 1}, колонке {nk_kol} не число. Значение:({tabl_cr_stukt.item(i, nk_kol).text()})')
                return False

            naim_ = tabl_cr_stukt.item(i, naim).text()
            nn_ = tabl_cr_stukt.item(i, nn).text()
            summ = 0
            for j in range(tabl_cr_stukt.rowCount()):
                if naim_ == tabl_cr_stukt.item(j, naim).text() and nn_ == tabl_cr_stukt.item(j, nn).text():
                    nach_ur = int(tabl_cr_stukt.item(j, nk).text())
                    if tabl_cr_stukt.item(j, nk_kol).text() == "":
                        CQT.msgbox(f'В колонке {nk_kol} не число')
                        return
                    kol_ = int(F.valm(tabl_cr_stukt.item(j, nk_kol).text()))
                    for k in range(j - 1, -1, -1):
                        if int(tabl_cr_stukt.item(k, nk).text()) > nach_ur:
                            break
                        if int(tabl_cr_stukt.item(k, nk).text()) < nach_ur:
                            kol_ *= int(F.valm(tabl_cr_stukt.item(k, nk_kol).text()))
                            nach_ur = int(tabl_cr_stukt.item(k, nk).text())
                        if int(tabl_cr_stukt.item(k, nk).text()) == 0:
                            break
                    summ += kol_
            tabl_cr_stukt.item(i, nk_kol_izd).setText(str(summ))

        for i in range(tabl_cr_stukt.rowCount()):
            if int(tabl_cr_stukt.item(i, nk).text()) == 0:
                if tabl_cr_stukt.item(i, nk_kol_p_z).text() == "":
                    CQT.msgbox('не указано Количество комплектов на ' + tabl_cr_stukt.item(i, 1).text())
                    tabl_cr_stukt.setCurrentCell(i, nk_kol_p_z)
                    return False

            # tabl_cr_stukt.item(i,nk_kol).setText(str(int(tabl_cr_stukt.item(i,nk_kol_izd).text())* int(kol)))

        self.ui.btn_vigruzka_norm_mat.setEnabled(False)
        return

    def add_v_mk(self):
        tab = self.ui.tabWidget
        tab2 = self.ui.tabWidget_2
        tabl_cr_stukt = self.ui.table_razr_MK

        tree = self.ui.tree_base_tree
        if tree.currentIndex().row() == -1:
            CQT.msgbox('Не выбран узел')
            return
        item = tree.currentItem()
        if item == None:
            return
        nk = CQT.num_col_by_name_c(tree, 'ID')
        current_ID = item.text(nk)
        sp_tree = CQT.list_from_tree_c(tree, hat_c=True)
        flag_naid = -1
        for i in range(len(sp_tree)):
            if sp_tree[i][nk] == current_ID:
                flag_naid = i
                break
        if flag_naid == -1:
            CQT.msgbox("Не найден выбранный узел")
            return

        q_strok = tabl_cr_stukt.currentRow() + 1
        q_column = tabl_cr_stukt.currentColumn()
        spisok = CQT.list_from_wtabl_c(tabl_cr_stukt, "", True)
        hat_c = spisok[0]

        list_add = ['Сумм.Количество', '', 'dreva_kod', 'Кол. по заявке', 'Наименование_аналог', 'Обозначение_аналог',
                    'Уд_количество_аналог', 'Коэфф_длины_швов',
                    'Опер_потребл', 'Окрашивание']
        for item in list_add:
            sp_tree[0].append(item)
            for i in range(1, len(sp_tree)):
                sp_tree[i].append('')

        dict_tree = F.list_to_dict(sp_tree, 'ID')
        nk_level_c = F.num_col_by_name_in_hat_c(sp_tree, 'Уровень')
        nk_level_c_out = F.num_col_by_name_in_hat_c(spisok, 'Уровень')

        dict_zamen = {'Ссылка на объект DOCs': 'Ссылка', 'Покупное изделие': 'ПКИ', 'Обозначение': 'Обозначение2',
                      'Обозначение полное': 'Обозначение'}

        for i in range(len(sp_tree[0])):
            for key in dict_zamen.keys():
                if sp_tree[0][i] == key:
                    sp_tree[0][i] = dict_zamen[key]

        for item in hat_c:
            if item not in sp_tree[0]:
                CQT.msgbox(f'В xml не найдено поле {item}')
                return

        list_to_add = [sp_tree[0]]
        ur = int(sp_tree[flag_naid][nk_level_c])
        list_to_add.append(sp_tree[flag_naid])
        for i in range(flag_naid + 1, len(sp_tree)):
            if int(sp_tree[i][nk_level_c]) <= ur:
                break
            list_to_add.append(sp_tree[i])
        dict_to_add = F.list_to_dict(list_to_add, 'ID')

        for id in dict_to_add.keys():
            dict_to_add[id]['Количество на изделие'] = ''
            tmp = []
            for item in hat_c:
                tmp.append(dict_to_add[id][item])
            spisok.append(tmp)

        CQT.fill_wtabl_old_c(self, spisok, tabl_cr_stukt, 0, self.edit_cr_mk, (), (), 200, True, '', 30)

        tabl_cr_stukt.clearSelection()
        tabl_cr_stukt.setCurrentCell(q_strok, q_column)
        tab.setCurrentIndex(1)
        tab2.setCurrentIndex(1)

    def ass_dse_to_mk(self):
        tabl_cr_stukt = self.ui.table_razr_MK
        tabl_nomenk = self.ui.table_nomenkl
        if tabl_cr_stukt.currentRow() == -1:
            CQT.msgbox('Не выбрана позиция в МК')
            return
        if tabl_nomenk.currentRow() == -1:
            CQT.msgbox('Не выбрана ДСЕ')
            return

        naim = CQT.value_of_selection_row_by_column_c(tabl_nomenk, 'Наименование')
        nn = CQT.value_of_selection_row_by_column_c(tabl_nomenk, 'Номенклатурный_номер')
        if nn == False or naim == False:
            return
        CQT.write_value_selection_row_by_column_c(tabl_cr_stukt, 'Наименование', naim)
        CQT.write_value_selection_row_by_column_c(tabl_cr_stukt, 'Обозначение', nn)
        self.ui.tabWidget.setCurrentIndex(1)
        self.ui.tabWidget_2.setCurrentIndex(1)

    def del_uzel(self):

        tabl_cr_stukt = self.ui.table_razr_MK
        if tabl_cr_stukt.currentRow() == -1:
            CQT.msgbox('Не выбрана позиция в МК')
            return
        q_strok = tabl_cr_stukt.currentRow()
        q_column = tabl_cr_stukt.currentColumn()
        # if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] in (3,4):
        if self.tkp_current_schema.is_tkp and not self.tkp_current_schema.is_parametric:
            tabl_cr_stukt.removeRow(q_strok)

        else:
            spisok = CQT.list_from_wtabl_c(tabl_cr_stukt, "", True)
            spisok_tmp = spisok.copy()
            k = 0
            spisok.pop(q_strok + 1)
            k += 1
            ur = int(tabl_cr_stukt.item(q_strok, 20).text())
            for i in range(q_strok + 2, len(spisok_tmp)):
                if int(spisok_tmp[i][20]) > ur:
                    spisok.pop(i - k)
                    k += 1
                else:
                    break

            CQT.fill_wtabl_old_c(self, spisok, tabl_cr_stukt, 0, self.edit_cr_mk_ruch, (), (), 200, True, '', 30)
            tabl_cr_stukt.setCurrentCell(q_strok, q_column)

    def add_paral(self):

        def select_tk():
            list_tk = CSQ.custom_request_c(self.db_dse,
                                           f"""SELECT Пномер, Номенклатурный_номер, Наименование, 
                                           Номер_техкарты, Примечание, Путь_docs FROM dse 
                                           WHERE Номер_техкарты !='' and  poki = {self.place.poki} and Примечание LIKE 'Комплексы%';""",
                                           rez_dict=True)
            answ = CQT.msgboxg_get_table(self, 'Выбрать ТК с материалами', list_tk, selection_from_tbl=True,
                                         selectRows=True, ExtendedSelection=False)
            if answ:
                return int(answ['Пномер'])
            return

        def select_oper_potrebl(self: mywindow, text, row, col):
            self.ui.table_razr_MK.item(row, col).setText(text)

        def select_mat(self, row, col):
            list_mats = CSQ.custom_request_c(self.db_mater, f"""SELECT ВидыНоменклатуры.name, nomen.Код,
              nomen.Наименование, 
              nomen.ЕдиницаИзмерения, 
              nomen.Примечание 
              FROM nomen 
            INNER JOIN ВидыНоменклатуры ON ВидыНоменклатуры.name == nomen.Вид WHERE ВидыНоменклатуры.s_num IN (81,33,50,165,100,102) and nomen.На_удаление == 0""",
                                             rez_dict=True)
            kod = ''
            mat = CQT.msgboxg_get_table(self, 'Выбор материала', list_mats, 'Выбор', selection_from_tbl=True)
            if mat:
                kod = mat['Код']
                row_old = CQT.get_dict_line_form_tbl(tbl, row)
                row_old['Наименование'] = mat['Наименование']
                row_old['Обозначение'] = F.shifr(row_old['Наименование'])[:13]
                row_old['Количество'] = '1'
                list_new_mass = row_old['Масса/М1,М2,М3'].split('/')
                name_fix = copy.deepcopy(mat['Наименование'])
                new_mass = '/'.join([list_new_mass[0], name_fix.replace('/', '-')])
                row_old['Масса/М1,М2,М3'] = new_mass
                row_old['Количество на изделие'] = '1'
                row_old['ПКИ'] = '0'
                row_old['Коэф_н_м'] = '1'
                row_old['Уровень'] = '1'
                row_old['К_узла'] = '1'
                CQT.set_dict_line_form_tbl(tbl, row_old, row)
                tbl.item(row, col).setText(kod)
                tbl.cellWidget(row, col).setText(kod)

        # if "tkp_current_schema" in self.__dict__:
        if self.tkp_current_schema.is_tkp and not self.tkp_current_schema.is_parametric:
            tbl = self.ui.table_razr_MK

            nf_kod_erp = CQT.num_col_by_name_c(tbl, 'Код ERP')
            nf_name_oper_potr_mat = CQT.num_col_by_name_c(tbl, 'Опер_потребл')
            nf_mat = CQT.num_col_by_name_c(tbl, 'Масса/М1,М2,М3')
            num_tk = select_tk()
            if num_tk == None:
                return
            tk_obj = CMS.Techkards(num_tk, self.db_dse, DICT_OP_NAME=self.DICT_OP_NAME)
            tbl.setCurrentCell(tbl.rowCount() - 1, 0)
            num_row = self.add_vhod("0")
            row_old = CQT.get_dict_line_form_tbl(tbl, num_row)
            # if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] == 4:
            if self.tkp_current_schema.is_statistic:
                pass
                # tbl.setCurrentCell(tbl.rowCount()-1, 0)
                # num_row = self.add_vhod("0")
                #
                #
                # CQT.add_btn(tbl, num_row, nf_kod_erp, 'Выбор мат.', True, select_mat, self)
                # list_opers = list(self.Data_plan.DICT_ETAPS_NAME.keys())
                # CQT.add_combobox(self, tbl, num_row, nf_name_oper_potr_mat, list_opers, True,
                #                 select_oper_potrebl)
                # CQT.set_cell_editable(tbl, num_row, nf_mat)

            # if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] in(3,4):
            if self.tkp_current_schema.is_tkp and not self.tkp_current_schema.is_parametric:
                # CQT.set_cell_editable(tbl, num_row, nf_mat)

                row_old['Наименование'] = tk_obj.dse['Наименование']
                row_old['Обозначение'] = tk_obj.dse['Номенклатурный_номер']
                row_old['Количество'] = '1'
                row_old['Ед.изм.'] = ''
                row_old['Масса/М1,М2,М3'] = ''
                row_old['Ссылка'] = ''
                row_old['ID'] = str(F.get_time_shtamp_c())
                row_old['Количество на изделие'] = '1'
                row_old['Примечание'] = 'Комплексы'
                row_old['ПКИ'] = '0'
                row_old['Сумм.Количество'] = ''
                row_old['Код ERP'] = ''
                row_old['Наименование_аналог'] = tk_obj.dse['Наименование']
                row_old['Обозначение_аналог'] = tk_obj.dse['Номенклатурный_номер']
                row_old['Уд_количество_аналог'] = '1'
                row_old['Коэфф_длины_швов'] = ''
                row_old['Опер_потребл'] = ''
                row_old['Окрашивание'] = ''
                row_old['dreva_kod'] = ''
                row_old['Кол. по заявке'] = ''
                row_old['Уровень'] = '1'
                row_old['Мат_аналог_кд'] = '1///'
                row_old['Код_аналог_кд'] = ''
                row_old['К_узла'] = '1'
                row_old['Коэф_н_м'] = '1'
            CQT.set_dict_line_form_tbl(tbl, row_old, num_row)

        else:
            num_row = self.add_vhod("0")

    @CQT.onerror
    def add_vhod(self, ur="1", *args):
        if ur == False:
            ur = "1"
        tabl_cr_stukt = self.ui.table_razr_MK
        if tabl_cr_stukt.currentRow() == -1:
            CQT.msgbox('Не выбрана позиция в МК')
            return
        q_strok = tabl_cr_stukt.currentRow()
        q_column = tabl_cr_stukt.currentColumn()
        tabl_cr_stukt.insertRow(q_strok + 1)
        tabl_cr_stukt.setRowHeight(q_strok + 1, tabl_cr_stukt.rowHeight(q_strok))
        nk_level = CQT.num_col_by_name_c(tabl_cr_stukt, 'Уровень')
        for i in range(tabl_cr_stukt.columnCount()):
            item_obr = tabl_cr_stukt.item(q_strok, i)
            new_item = QtWidgets.QTableWidgetItem('')
            new_item.setFont(item_obr.font())
            new_item.setBackground(item_obr.background())  # Копируем стиль
            new_item.setForeground(item_obr.foreground())
            new_item.setFlags(item_obr.flags())
            tabl_cr_stukt.setItem(q_strok + 1, i, new_item)
            # tabl_cr_stukt.item(q_strok + 1,i).setText('')
        tabl_cr_stukt.item(q_strok + 1, nk_level).setText(
            str(int(tabl_cr_stukt.item(q_strok, nk_level).text()) + int(ur)))
        tabl_cr_stukt.item(q_strok + 1, 6).setText(str(F.get_time_shtamp_c()))
        tabl_cr_stukt.item(q_strok + 1, 4).setText('/М1/М2/М3')

        # CQT.fill_wtabl_old_c(self, spisok, tabl_cr_stukt, 0, self.edit_cr_mk_ruch, (), (), 200, True, '', 30)
        tabl_cr_stukt.clearSelection()

        tabl_cr_stukt.setCurrentCell(q_strok, q_column)
        return q_strok + 1

    def add_gl_uzel(self, id=''):
        butt_add_gl_uzel = self.ui.pushButton_create_koren
        tabl_cr_stukt = self.ui.table_razr_MK
        if 'dict_cur_poz_cr_mk' not in self.__dict__:
            CQT.msgbox(f'Не выбрана позиция')
            return
        spisok = CQT.list_from_wtabl_c(tabl_cr_stukt, "", True)
        strok = []
        for i in range(20):
            strok.append('')
        strok.append('0')
        strok[2] = '1'
        if id == '' or id == False:
            strok[6] = F.get_time_shtamp_c()
        else:
            strok[6] = id
        strok[4] = '/М1/М2/М3'
        spisok.append(strok)

        CQT.fill_wtabl_old_c(self, spisok, tabl_cr_stukt, 0, self.edit_cr_mk_ruch, (), (), 200, True, '', 30)
        self.mark_count_by_position(tabl_cr_stukt)  # 09.06.2025
        self.ui.btn_vigruzka_norm_mat.setEnabled(True)
        try:
            self.tkp_current_schema.clear()
            # del self.tkp_current_schema
        except:
            pass

    def kol_po_zayav(self, sp_xml_tmp, kol):
        sp_xml_tmp[10] = int(sp_xml_tmp[2]) * int(kol)
        return sp_xml_tmp

    def kol_v_uzel(self, s, j, nk_naim, nk_kol, nk_ur=''):
        koef = 1
        if nk_ur != "":
            koef_ur = int(s[j][nk_ur])
        else:
            koef_ur = CMS.level_c(s[j][nk_naim])
        for k in range(j - 1, 0, -1):
            if nk_ur != "":
                ur_tmp = int(s[k][nk_ur])
            else:
                ur_tmp = CMS.level_c(s[k][nk_naim])
            if ur_tmp < koef_ur:
                koef *= int(s[k][nk_kol])
                koef_ur = ur_tmp
            if koef_ur == 0:
                break
        return int(koef)

    def kol_na_izd(self, s, kol_po_zayav: int):
        nk_kol = F.num_col_by_name_in_hat_c(s, 'Количество')
        nk_kol_izd = F.num_col_by_name_in_hat_c(s, 'Количество на изделие')
        nk_kol_summ = F.num_col_by_name_in_hat_c(s, 'Сумм.Количество')
        nk_naim = F.num_col_by_name_in_hat_c(s, 'Наименование')
        nk_nn = F.num_col_by_name_in_hat_c(s, 'Обозначение')
        nk_ur = F.num_col_by_name_in_hat_c(s, 'Уровень')
        if s[0][nk_ur] == 'Уровень':
            for i in range(1, len(s)):
                s[i][nk_naim] = '    ' * int(s[i][nk_ur]) + s[i][nk_naim].strip()
                s[i][nk_nn] = '    ' * int(s[i][nk_ur]) + s[i][nk_nn].strip()
        for i in range(1, len(s)):
            naim = s[i][nk_naim].strip()
            nn = s[i][nk_nn].strip()
            summ = 0
            if type(F.valm(s[i][nk_kol])) == float:
                if F.valm(s[i][nk_kol]).is_integer():
                    s[i][nk_kol] = int(F.valm(s[i][nk_kol]))
            koef = self.kol_v_uzel(s, i, nk_naim, nk_kol)
            if type(F.valm(s[i][nk_kol])) == float:
                if not F.valm(s[i][nk_kol]).is_integer():
                    CQT.msgbox(
                        f'{s[i][nk_naim]} {s[i][nk_nn]} по количеству занесен как расходник, обратиться к технологу')
                    CQT.statusbar_text(self)
                    return
            s[i][nk_kol_summ] = koef * kol_po_zayav * int(F.valm(s[i][nk_kol]))
            for j in range(1, len(s)):
                if s[j][nk_naim].strip() == naim and s[j][nk_nn].strip() == nn:
                    koef = self.kol_v_uzel(s, j, nk_naim, nk_kol)
                    summ += int(F.valm(s[j][nk_kol])) * koef
            s[i][nk_kol_izd] = str(summ) + ' (' + str(summ * kol_po_zayav) + ')'
        return s

    def kol_na_izd_zayav_1(self, s):
        # ===========================================================доделать
        nk_kol = F.num_col_by_name_in_hat_c(s, 'Количество')
        nk_kol_p_z = F.num_col_by_name_in_hat_c(s, 'Кол. по заявке')
        nk_kol_izd = F.num_col_by_name_in_hat_c(s, 'Количество на изделие')
        s[0][10] = 'Сумм.Количество'
        nk_kol_summ = F.num_col_by_name_in_hat_c(s, 'Сумм.Количество')
        kol = 1
        if nk_kol_p_z == None:
            CQT.msgbox('Не подходящий набор данных для формирования МК')
            return
        for i in range(1, len(s)):
            koef = 1
            if int(s[i][20]) == 0:

                kol = int(s[i][nk_kol_p_z])
            else:

                tek_ur = int(s[i][20])
                for j in range(i - 1, -1, -1):
                    if int(s[j][20]) < tek_ur:
                        koef *= int(s[j][nk_kol])
                        tek_ur = int(s[j][20])
                    if int(s[j][20]) == 0:
                        break

            if i:
                s[i][nk_kol_izd] = str(s[i][nk_kol_izd]) + ' (' + str(int(s[i][nk_kol_izd]) * kol) + ')'
                s[i][nk_kol_summ] = int(s[i][nk_kol]) * kol * koef

        return s

    # ===========================================================

    def raschet_vesa_xml(self, s_vert):
        nom_kol_mat = F.num_col_by_name_in_hat_c(s_vert, 'Масса/М1,М2,М3')
        nom_kol_kol = F.num_col_by_name_in_hat_c(s_vert, 'Количество')
        ves = 0
        for i in range(1, len(s_vert)):
            if s_vert[i][nom_kol_mat].split('/')[1] != '' and s_vert[i][nom_kol_mat].split('/')[2] != '':
                if F.is_numeric(s_vert[i][nom_kol_mat].split('/')[0]) == False:
                    CQT.msgbox(f'В строке {i} вес не число')
                    return 0

                ves += (F.valm(s_vert[i][nom_kol_mat].split('/')[0]) * F.valm(s_vert[i][nom_kol_kol]))
        return ves

    def raschet_vesa_dse(self, res='', show_info_table=True):
        self.LIST_ED_IZM_MAT = ['Килограмм', 'кг']
        # nom_kol_mat = F.num_col_by_name_in_hat_c(s_vert, 'Масса/М1,М2,М3')
        # nom_kol_kol = F.num_col_by_name_in_hat_c(s_vert, 'Количество')
        # nom_kol_naim = F.num_col_by_name_in_hat_c(s_vert, 'Наименование')
        # nom_kol_tip = F.num_col_by_name_in_hat_c(s_vert, 'Тип')
        # ves = 0
        # if ruchnoi == False:
        #    for i in range(1, len(s_vert)):
        #        if s_vert[i][nom_kol_tip] != 'Сборочная единица':
        #            if F.is_numeric(s_vert[i][nom_kol_mat].split('/')[0]) == False:
        #                CQT.msgbox(f'В строке {i} вес не число')
        #                return 0
        #            ves += (F.valm(s_vert[i][nom_kol_mat].split('/')[0]) * F.valm(s_vert[i][nom_kol_kol]) *  self.kol_v_uzel(s_vert, i,nom_kol_naim, nom_kol_kol))
        #
        # else:
        #    for i in range(1, len(s_vert)):
        #        if s_vert[i][nom_kol_mat].split('/')[1] != '' and s_vert[i][nom_kol_mat].split('/')[2] != '':
        #            if F.is_numeric(s_vert[i][nom_kol_mat].split('/')[0]) == False:
        #                CQT.msgbox(f'В строке {i} вес не число')
        #                return 0
        #            ves += (F.valm(s_vert[i][nom_kol_mat].split('/')[0]) * F.valm(s_vert[i][nom_kol_kol]) *  self.kol_v_uzel(s_vert, i,nom_kol_naim, nom_kol_kol))
        if res == '':
            res = self.res
        if res == '':
            CQT.msgbox(f'ОШибка')
            return
        ves_res = 0
        ves_res_list = 0
        n_chas_cbsv = 0
        rez_s_pki = 0

        self.ui.lbl_summ_weight.setText('')
        self.ui.lbl_summ_weight_wo_pki.setText('')
        list_hz_mat = []
        msg_ = []
        for dse in res:
            for oper in dse['Операции']:
                for mat in oper['Материалы']:
                    if mat['Мат_ед_изм'] in self.LIST_ED_IZM_MAT:
                        norma = F.valm(mat['Мат_норма'])
                        ves_res += norma
                        # print(f"{F.valm(mat['Мат_норма'])} опер {oper['Опер_наименование']} дет {dse['Наименование']}")
                        vid = f'Не найден код в БД'
                        ves_ = round(norma, 2)
                        if mat['Мат_код'] in self.DICT_MAT:
                            if self.DICT_MAT[mat['Мат_код']]['Вид'] not in self.Data_plan.DICT_VID_NOMEN:
                                continue
                            vid = f'Вспомогательный'
                            ves_ = round(norma, 2)

                            if self.Data_plan.DICT_VID_NOMEN[self.DICT_MAT[mat['Мат_код']]['Вид']][
                                'Основной_мат_для_пересыльных'] == 1:  # VSPOM
                                rez_s_pki += norma / 1.3

                                if not self.Data_plan.DICT_VID_NOMEN[self.DICT_MAT[mat['Мат_код']]['Вид']][
                                           'Склад_для_змвп'] == 1:  # NOT PKI

                                    ves_res_list += norma
                                    vid = f'Чистый ({self.LIST_ED_IZM_MAT}) c 30%'
                                    ves_ = round(norma, 2)

                                else:  # PKI
                                    vid = f'ПКИ ({self.LIST_ED_IZM_MAT}) без 30%'
                                    ves_ = round(norma / 1.3, 2)

                        msg_.append(
                            {'Вид': vid,
                             'ДСЕ': dse["Номенклатурный_номер"],
                             'Операция': oper["Опер_наименование"],
                             'Мат_наименование': mat["Мат_наименование"],
                             'Вес': ves_})

        if rez_s_pki > 0:
            self.ui.lbl_summ_weight.setText(str(round(rez_s_pki, 2)))
            pass
        if ves_res_list > 0:
            self.ui.lbl_summ_weight_wo_pki.setText(str(round(ves_res_list, 2)))
            pass
        if show_info_table:
            if msg_:
                CQT.msgboxg_get_table(self, 'Расчет веса для сравнения', msg_, 'OK', disable_btn1=True,
                                      load_summ=True)
        return round(ves_res, 2), round(ves_res_list, 2)

    @CQT.onerror
    def create_sp_dreva_ruchnoi(self):

        tabl_cr_stukt = self.ui.table_razr_MK
        if tabl_cr_stukt.rowCount() == 0:
            return
        but_add_gl_uzel = self.ui.pushButton_create_koren
        but_add_vhod = self.ui.pushButton_create_vxodyash
        but_udal_uzel = self.ui.pushButton_create_udalituzel
        if self.check_pre_create_mk() == False:
            return
        s_vert = CQT.list_from_wtabl_c(tabl_cr_stukt, "", True)
        self.kol_izdeliy = int(s_vert[1][F.num_col_by_name_in_hat_c(s_vert, 'Кол. по заявке')])
        s_vert = self.kol_na_izd(s_vert, self.kol_izdeliy)
        if s_vert == None:
            CQT.msgbox('Не подходящий набор данных для формирования МК')
            return

        if F.num_col_by_name_in_hat_c(s_vert, 'К_узла') != None:
            nf_k_knot = F.num_col_by_name_in_hat_c(s_vert, 'К_узла')
            fl = True
            for i in range(1, len(s_vert)):
                if not F.is_numeric(s_vert[i][nf_k_knot]) or s_vert[i][nf_k_knot] == '':
                    fl = False
                    break
            if not fl:
                CQT.msgbox(f'Не корректно занесен К_узла')
                return

        self.xml_file = ''

        # =========================================РЕСУРСНАЯ
        list_msg = []
        self.res = CMS.resursnaya_from_cust_struktura(self, s_vert, kol_vo_izdeliy=self.kol_izdeliy, ruchnoi=True,
                                                      list_msg=list_msg)
        if self.res == None:
            return

        dict_poziciy_rez = dict()
        dict_poziciy_rez[
            'name'] = f"{s_vert[1][F.num_col_by_name_in_hat_c(s_vert, 'Наименование')]}" \
                      f" {s_vert[1][F.num_col_by_name_in_hat_c(s_vert, 'Обозначение')]}"
        dict_poziciy_rez['data'] = self.res
        dict_poziciy_rez['kol_zayavk'] = self.kol_izdeliy
        self.spis_poziciy_rez_ruchnoi = [dict_poziciy_rez]
        return s_vert

    def create_sp_dreva_po_xml(self):
        tabl = self.ui.table_zayavk
        if tabl.rowCount() == 0:
            CQT.msgbox('Не добавлены заявки')
            return
        if tabl.columnCount() > 5:
            return
        sp_izd = CQT.list_from_wtabl_c(tabl)
        if len(sp_izd) > 1:
            CQT.msgbox('Создать МК можно только на одну позицию, Del - удалить строку')
            return
        putt_xml = sp_izd[0][0]
        if F.is_numeric(sp_izd[0][3]) == False:
            CQT.msgbox(f'К_мат не число')
            return
        if F.is_numeric(sp_izd[0][4]) == False:
            CQT.msgbox(f'К_врем не число')
            return
        self.cr_mk_xml_koef_norm_mat = F.valm(sp_izd[0][3])
        self.cr_mk_xml_koef_norm_time = F.valm(sp_izd[0][4])
        sp_xml_tmp = CMS.podgotovka_xml(self, XML.spisok_iz_xml(putt_xml),
                                        correct_code_erp_tbl=True,
                                        xml_head=self.tkp_current_schema.XML_start_from_project_product_type)  # 05.08.25 задача 100057976
        if sp_xml_tmp == None:
            CQT.msgbox('Файл не корректный')
            return
        self.xml_file = F.load_file_convert_to_binary(putt_xml)
        if sp_izd[0][2] == '':
            CQT.msgbox("Не указано Количество по заявке")
            return
        try:
            self.kol_izdeliy = int(sp_izd[0][2])
        except:
            CQT.msgbox(f'Количество изделий не целое число')
            return
        # ==========================================РЕСУРСНАЯ
        self.res = CMS.resource_from_xml_c(self, sp_xml_tmp, self.kol_izdeliy)
        # ==============================================какое то складывние
        """        for i in range(len(sp_xml_tmp)):
            for j in range(i + 1, len(sp_xml_tmp)):
                if i < len(sp_xml_tmp) - 1:
                    if sp_xml_tmp[i]['data']['Наименование'] == sp_xml_tmp[j]['data']['Наименование'] \
                            and sp_xml_tmp[i]['data']['Обозначение полное'] == sp_xml_tmp[j]['data']['Обозначение полное'] \
                            and sp_xml_tmp[i]['level_c'] == sp_xml_tmp[j]['level_c']:#НЕДОДАЕЛАНО!!!!
                        sp_xml_tmp[i][2] = str(int(sp_xml_tmp[i][2]) + int(sp_xml_tmp[j][2]))
                        sp_xml_tmp[j][0] = "deletes" + str(F.get_time_shtamp_c())
                    else:
                        break
        sp_xml_tmp_ = []
        for i in range(len(sp_xml_tmp)):
            if sp_xml_tmp[i][0].startswith('deletes') == False:
                sp_xml_tmp_.append(sp_xml_tmp[i])
        sp_xml_tmp = sp_xml_tmp_"""
        # =============================================================
        s_vert = [["Наименование"
                      , "Обозначение"
                      , "Количество"
                      , "Ед.изм."
                      , "Масса/М1,М2,М3"
                      , "Ссылка"
                      , "ID"
                      , "Количество на изделие"
                      , "Код ERP"
                      , 'Примечание'
                      , 'ПКИ'
                      , 'Сумм.Количество'
                      , 'Уровень'
                      , 'Тип']]

        for j in range(len(sp_xml_tmp)):
            for item in ['Наименование', 'Обозначение полное', 'Количество', 'Единица измерения', 'Масса/М1,М2,М3',
                         'Ссылка на объект DOCs', 'ID', 'Количество на изделие', "Код ERP", 'Примечание',
                         'Покупное изделие'
                , 'Тип']:
                if item not in sp_xml_tmp[j]['data']:
                    CQT.msgbox(f"В файле XML в строке ,\n{sp_xml_tmp[j]} \n\n\nотсутствует поле {item}")
                    return
        try:
            for j in range(len(sp_xml_tmp)):
                s_vert.append([sp_xml_tmp[j]['data']['Наименование'], sp_xml_tmp[j]['data']['Обозначение полное'],
                               sp_xml_tmp[j]['data']['Количество'], sp_xml_tmp[j]['data']['Единица измерения'],
                               sp_xml_tmp[j]['data']['Масса/М1,М2,М3'], sp_xml_tmp[j]['data']['Ссылка на объект DOCs'],
                               sp_xml_tmp[j]['data']['ID'], sp_xml_tmp[j]['data']['Количество на изделие'],
                               sp_xml_tmp[j]['data']['Код ERP'],
                               sp_xml_tmp[j]['data']['Примечание'], sp_xml_tmp[j]['data']['Покупное изделие'],
                               '', sp_xml_tmp[j]['level_c'], sp_xml_tmp[j]['data']['Тип']])
        except:
            CQT.msgbox(f'Ошибка обработки ХМЛ')
            return
        s_vert = self.kol_na_izd(s_vert, self.kol_izdeliy)
        if s_vert == None:
            return
        return s_vert

    @CQT.onerror
    def calc_report_and_statistic(self, vid_napr, show_stat=True, show_opers=True, delete_mat_mode=False):
        napr_deyat = self.Data_plan.DICT_VID_PO_NAPR[vid_napr]['Направл']
        napr = self.Data_plan.DICT_NAPR_DEYAT[int(napr_deyat)]['Направление']

        koef_vneplana = self.Data_plan.DICT_NAPRAVLENIE[napr]['koef_vneplana']
        koef_pogr_norm = self.Data_plan.DICT_NAPRAVLENIE[napr]['koef_pogr_norm']
        dict_norm, list_opers = self.dict_norm_from_res(self.res, '', koef_vneplana, koef_pogr_norm)
        if dict_norm == None:
            return
        if show_stat:
            stat_proizv = 121
            if self.Data_plan.DICT_VID_PO_NAPR[vid_napr]['Выборка'] >= 1:
                stat_proizv = self.Data_plan.DICT_VID_PO_NAPR[vid_napr]['кг_на_пост_см']
            sb_sv = (dict_norm['пл_сб.Нчас_слсб'] + dict_norm['пл_сб.Нчас_св']) / 60
            ves_tkp = F.valm(self.ui.lbl_summ_weight_wo_pki.text())
            proizv = 0
            if sb_sv > 0:
                proizv = round(ves_tkp * 8 / (sb_sv / 2))
            otkl = 100
            if stat_proizv != 0 and proizv != 0:
                if proizv > stat_proizv:
                    otkl = round(abs(proizv / stat_proizv) * 100, 1)
                else:
                    otkl = round(abs(stat_proizv / proizv) * 100, 1)
            self.ui.lbl_stat_kalc_tkp.setText(f'По {self.Data_plan.DICT_VID_PO_NAPR[int(vid_napr)]["Имя"]}: '
                                              f'Средняя производительность {round(stat_proizv)} кг/п-см. В текущей'
                                              f' выборке производительность {proizv} кг/п-см., при весе {ves_tkp} кг.'
                                              f'       отклонение {round(otkl - 100)}%.')

        if show_opers:

            nf_snum_mat = F.get_key_index_dict(list_opers[0], 'Пном мат')
            list_opers_new = F.insert_key_to_dicts(list_opers, nf_snum_mat + 1, 'Удалить мат.', '0')

            @CQT.onerror
            def set_editable_norm(tbl: QtWidgets.QTableWidget, self, *args):
                if delete_mat_mode:
                    nf_val_norm = CQT.num_col_by_name_c(tbl, 'Удалить мат.')
                    nf_mat = CQT.num_col_by_name_c(tbl, 'Мат_тд_наим')
                    for i in range(tbl.rowCount()):
                        if tbl.item(i, nf_mat).text() != '':
                            CQT.set_cell_editable(tbl, i, nf_val_norm, True)

            @CQT.onerror
            def get_delete_mats(tbl: QtWidgets.QTableWidget, self, *args):
                def delete_mat(obj_mat: list, mat_kod_erp: str):
                    new_list = []
                    for mat in obj_mat:
                        if mat['Мат_код'] == mat_kod_erp:
                            continue
                        new_list.append(mat)
                    return new_list

                if not delete_mat_mode:
                    return
                nf_val_norm = CQT.num_col_by_name_c(tbl, 'Удалить мат.')
                nf_kod_mat = CQT.num_col_by_name_c(tbl, 'Мат_тд_код')
                nf_snum_oper = CQT.num_col_by_name_c(tbl, 'Пном Опер')
                nf_snum_dse = CQT.num_col_by_name_c(tbl, 'Пном ДСЕ')
                for i in range(tbl.rowCount()):
                    if tbl.item(i, nf_val_norm).text() == '1':
                        snum_oper = int(tbl.item(i, nf_snum_oper).text())
                        snum_dse = int(tbl.item(i, nf_snum_dse).text())
                        mat_kod = tbl.item(i, nf_kod_mat).text()
                        mat_kod_erp = mat_kod
                        if mat_kod == '':
                            self.res[snum_dse]['Мат_кд'] = '0//'
                        else:
                            if self.res[snum_dse]['Код_ERP'] == mat_kod_erp:
                                self.res[snum_dse]['Мат_кд'] = '0//'
                            self.res[snum_dse]['Операции'][snum_oper]['Материалы'] = delete_mat(
                                self.res[snum_dse]['Операции'][snum_oper]['Материалы'], mat_kod_erp)

                    # path_tmp_list = CMS.tmp_dir() + F.sep() + 'tkp_tmp_list_norm.txt'

            # F.save_file(path_tmp_list,F.list_of_dicts_to_list_of_lists(list_opers))
            # F.run_file_os_c(path_tmp_list)
            CQT.msgboxg_get_table(self, 'Расчеты', list_opers_new, 'OK', disable_btn1=True, load_summ=True,
                                  func_oform_tbl=set_editable_norm, func_btn0=get_delete_mats, parent_self=self)

    # +++09.06.2025
    @CQT.onerror
    def mark_count_by_position(self, tbl: QtWidgets.QTableWidget):  # 09.06.2025
        if tbl.columnCount() == 0:
            return
        nk_kol_po_zayav = CQT.num_col_by_name_c(tbl, 'Кол. по заявке')

        dict_cur_poz_cr_mk = getattr(self, 'dict_cur_poz_cr_mk', {})
        count_in_pos = dict_cur_poz_cr_mk.get('Количество')
        if count_in_pos is not None:
            tbl.item(0, nk_kol_po_zayav).setText(str(count_in_pos))

    # ---09.06.2025

    @CQT.onerror
    def create_mk(self, *args):
        # if not hasattr(self, 'tkp_current_schema'):
        #     self.tkp_current_schema = None
        def apply_dse_new_nomen_tkp(self, s_vert):
            nf_obozn = F.num_col_by_name_in_hat_c(s_vert, 'Обозначение')
            nf_naimen = F.num_col_by_name_in_hat_c(s_vert, 'Наименование')
            nf_urov = F.num_col_by_name_in_hat_c(s_vert, 'Уровень')
            nf_pki = F.num_col_by_name_in_hat_c(s_vert, 'ПКИ')
            nnom_tkp = self.tkp_current_schema['nnom_tkp']
            name_tkp = self.tkp_current_schema['name_tkp']
            for i in range(1, len(s_vert)):
                if s_vert[i][nf_pki] == '1':
                    continue
                if s_vert[i][nf_urov] == 0 and i == 1:
                    s_vert[i][nf_naimen] = '    ' * int(s_vert[i][nf_urov]) + name_tkp
                list_ob = s_vert[i][nf_obozn].strip().split('.')
                if len(list_ob) >= 3:
                    list_ob = list_ob[3:]
                list_ob.insert(0, nnom_tkp)
                new_list_ob = '    ' * int(s_vert[i][nf_urov]) + '.'.join(list_ob)
                s_vert[i][nf_obozn] = new_list_ob

            for i in range(len(self.res)):
                if self.res[i]['ПКИ'] == '1':
                    continue
                if self.res[i]['Уровень'] == 0 and i == 0:
                    self.res[i]['Наименование'] = name_tkp
                list_ob = self.res[i]['Номенклатурный_номер'].split('.')
                if len(list_ob) >= 3:
                    list_ob = list_ob[3:]
                list_ob.insert(0, nnom_tkp)
                new_list_ob = '.'.join(list_ob)
                self.res[i]['Номенклатурный_номер'] = new_list_ob
            return s_vert

        self.ves_res_list = 0
        self.ui.lbl_stat_kalc_tkp.setText('')
        if self.ui.comboBox_napravlenia.currentText() == '':
            CQT.msgbox('Не указано направление')
            return

        if self.ui.tabWidget_2.currentIndex() == 1:  # вручную# вручную# вручную# вручную# вручную# вручную# вручную
            if self.ui.table_razr_MK.columnCount() == 0:
                return
            CQT.statusbar_text(self, 'Формирование списка вручную')
            s_vert = self.create_sp_dreva_ruchnoi()
            if s_vert == None:
                return
            tabl = self.ui.table_razr_MK
        else:  # xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml
            CQT.statusbar_text(self, 'Формирование списка по ХМЛ')
            s_vert = self.create_sp_dreva_po_xml()
            # if "ВО" not in self.ui.cmb_cr_mk_pr.currentText() and (self.cr_mk_xml_koef_norm_mat != 1 or self.cr_mk_xml_koef_norm_time != 1) :
            #    CQT.msgbox(f'Для сохранения МК, коэффициенты материала и времени не могут быть отличны от 1')
            #     return
            if s_vert == None:
                return
            tabl = self.ui.table_zayavk

        CQT.statusbar_text(self, 'Форматирование списка')
        nach_sod = len(s_vert[0])

        DICT_DSE = CSQ.custom_request_c(self.db_dse,
                                        f'''SELECT poki, Номер_техкарты, Номенклатурный_номер, Код_ЕРП FROM dse WHERE poki = {self.place.poki}''',
                                        rez_dict=True)
        self.DICT_DSE_save_mk = F.deploy_dict_c(DICT_DSE, 'Номенклатурный_номер')
        if not self.tkp_current_schema.is_statistic:
            for i in range(1, len(s_vert)):
                ima = s_vert[i][F.num_col_by_name_in_hat_c(s_vert, 'Наименование')].strip()
                pseudo_naim = copy.copy(ima)
                nn = s_vert[i][F.num_col_by_name_in_hat_c(s_vert, 'Обозначение')].strip()
                pseudo_nn = copy.copy(nn)

                # if hasattr(self, 'tkp_current_schema') and isinstance(self.tkp_current_schema, dict): #07.04.25
                # if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] in (3,4):
                if self.tkp_current_schema.is_analogue:
                    ima = s_vert[i][F.num_col_by_name_in_hat_c(s_vert, 'Наименование_аналог')].strip()
                    nn = s_vert[i][F.num_col_by_name_in_hat_c(s_vert, 'Обозначение_аналог')].strip()

                # kol_det_vseg = s_vert[i][F.num_col_by_name_in_hat_c(s_vert, 'Сумм.Количество')]

                if nn not in self.DICT_DSE_save_mk:
                    CQT.msgbox('Не найден в БД ' + ima + ' ' + nn)
                    return
                if self.DICT_DSE_save_mk[nn]['Номер_техкарты'] == '':
                    CQT.msgbox('Не найдена техкарта ' + ima + ' ' + nn)
                    return
                nom_tk = self.DICT_DSE_save_mk[nn]['Номер_техкарты']
                put_name_tk = F.scfg('add_docs') + os.sep + nom_tk + "_" + nn
                tk = F.open_file_c(put_name_tk + '.txt', False, "|", True, True)
                if tk == ['']:
                    CQT.msgbox(f'Не найдена техкарта {put_name_tk}')
                    return
                tk = CMS.grouping_TK_by_work_centres_c(self, tk, nn, ima)
                self.ogran = nach_sod - 1
                for k in tk:
                    if k[0] == "":
                        CQT.msgbox('Рабочий центр на ' + k[2] + ' операцию не назначен для ' + nn)
                        return
                    print(k[0], k[1], k[2], i, self.ogran)
                    s_vert = self.dob_etap(s_vert, k[0], k[1], k[2], i, self.ogran)
                s_vert[i][F.num_col_by_name_in_hat_c(s_vert, 'Наименование')] = pseudo_naim
                s_vert[i][F.num_col_by_name_in_hat_c(s_vert, 'Обозначение')] = pseudo_nn

        ves, self.ves_res_list = self.raschet_vesa_dse(self.res)
        # if self.ui.tabWidget_2.currentIndex() == 1:               # вручную# вручную# вручную# вручную# вручную# вручную# вручную:
        self.ui.lineEdit_ves.setText(str(round(ves, 2)))
        # else:                                           # xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml# xml
        #    self.ui.lineEdit_ves.setText(str(round(self.raschet_vesa_dse()[0], 2)))

        nom_vid_po_napr = None
        # if hasattr(self, 'tkp_current_schema') and isinstance(self.tkp_current_schema, dict) and 'type_tkp' in self.tkp_current_schema: #07.04.25
        if self.tkp_current_schema.is_tkp:
            nom_vid_po_napr = self.tkp_current_schema['вид_по_напр']
            # if 'type_tkp' in self.tkp_current_schema and self.tkp_current_schema['type_tkp'] == 3:
        else:
            if 'dict_cur_poz_cr_mk' not in self.__dict__:
                CQT.msgbox(f'Не выбрана позиция')
                return
            poz = CMS.Pozition(self.dict_cur_poz_cr_mk['Пномер'], self.db_kplan, self.bd_naryad, self.db_resxml,
                               self.db_users, self)
            poz.load_kpl_table('пл_топ')
            nom_vid_po_napr = poz.dict_tables['пл_топ']['Вид']
        delete_mat_mode = False
        # if not hasattr(self, 'tkp_current_schema') or not isinstance(self.tkp_current_schema, dict) or not self.tkp_current_schema.get('type_tkp') == 4: #07.04.25
        if self.tkp_current_schema.is_tkp:
            delete_mat_mode = True
        self.calc_report_and_statistic(nom_vid_po_napr, show_opers=self.ui.chk_make_tesult_tbl_from_mk.isChecked(),
                                       delete_mat_mode=delete_mat_mode)

        CQT.statusbar_text(self, 'Оформление итоговой табицы')
        # s_vert = self.oformlenie_sp_pod_mk(s_vert)
        if s_vert == None:
            return

        if self.ui.tabWidget_2.currentIndex() == 1:
            # if 'tkp_current_schema' in self.__dict__ and isinstance(self.tkp_current_schema, dict):
            if self.tkp_current_schema.is_tkp:
                s_vert = apply_dse_new_nomen_tkp(self, s_vert)
                self.ui.pushButton_save_MK.setEnabled(False)
            else:
                self.ui.pushButton_save_MK.setEnabled(True)

        for i in range(tabl.columnCount()):
            tabl.setColumnHidden(i, False)
        CQT.fill_wtabl_old_c(self, s_vert, tabl, 0,
                             0, "", "",
                             200, True, '', 90)

        tabl.setSelectionBehavior(1)
        CQT.statusbar_text(self, 'Раскрашивание')
        self.oformlenie_formi_mk(tabl, s_vert)

        self.ui.pushButton_ass_brak_to_mk.setEnabled(True)
        # if self.ui.pushButton_save_MK.isEnabled() == False:
        #    self.ui.tabWidget.setCurrentIndex(3)
        CQT.statusbar_text(self)
        self.ui.btn_save_cust_drevo.setEnabled(False)
        self.ui.btn_load_cust_drevo.setEnabled(False)
        self.ui.pushButton_create_paralel.setEnabled(False)
        self.mk_file_founding = ''
        self.ui.cmb_cr_mk_poz.setEnabled(False)

    @CQT.onerror
    def dict_norm_from_res(self, res, dict_norm='', koef_vneplana=1, koef_pogr_norm=1):
        if dict_norm == '':
            dict_norm = KPL.generate_dict_norm(self)
        list_log = []
        pozition = res[0]['Номенклатурный_номер']
        count_izd = res[0]['Количество']
        for dse in res:
            fl_mat = True
            for s_num_oper, oper in enumerate(dse['Операции']):
                if oper['Опер_наименование'] in self.DICT_VAR_OPER:
                    count_dse = dse['Количество'] / count_izd
                    tsht_kol_zayvk = oper['Опер_Тшт']
                    kal_pl_podr = self.DICT_VAR_OPER[oper['Опер_наименование']][0]['kal_pl_podr'].split("|")

                    kr = self.DICT_OP[oper['Опер_код']]['kr_default']
                    koef_posta = 1
                    if kr == 2:
                        koef_posta = round(1 / 0.7, 2)
                    time = tsht_kol_zayvk * koef_posta

                    for podr_per in kal_pl_podr:
                        if podr_per == '':
                            CQT.msgbox(
                                f"В бд не занесен  этап МЕС для  {oper['Опер_наименование']}")
                            return None, None
                        podr, per = podr_per.split("%")
                        if podr not in dict_norm:
                            CQT.msgbox(
                                f"В бд для операции {oper['Опер_наименование']} не соответствует этап {podr} базовому dict_norm")
                        else:
                            time_paral = (oper['Опер_Тпз'] + time) * F.valm(per) / 100
                            koef_vneplana_tmp = 1
                            if podr in ('пл_сб.Нчас_слсб', 'пл_сб.Нчас_св', 'пл_сб.Нчас_зач'):
                                koef_vneplana_tmp = koef_vneplana
                            itog_time = time_paral * koef_vneplana_tmp * koef_pogr_norm
                            dict_norm[podr] += itog_time

                    mat_znch = 0
                    mat_name = ''
                    link_docs = ''
                    if fl_mat:
                        if '/' in dse['Мат_кд']:
                            if dse['Мат_кд'].split("/")[1] != '':
                                mat_znch = F.valm(dse['Мат_кд'].split("/")[0])
                        mat_name = dse['Мат_кд']
                        link_docs = dse['Ссылка']
                        fl_mat = False
                    if oper['Опер_профессия_код'] not in self.DICT_PROFESSIONS:  # 29.07.25 по задача 100057652
                        nn = dse['Номенклатурный_номер']
                        oper_num = oper['Опер_номер']
                        CQT.msgbox(f'Некорректный код профессии ДСЕ: {nn!r}. Номер операции: {oper_num!r}')
                        return None, None

                    tmp_row = {'Позиция': pozition,
                               'Пном ДСЕ': dse['Номерпп'] - 1,
                               'ДСЕ': f"{dse['Наименование']} {dse['Номенклатурный_номер']}",
                               'Колво_в_узел': dse['Количество_ед'], 'Колво_в_изд': count_dse, 'Изделий': count_izd,
                               'Колво_всего': dse['Количество'],
                               'Пном Опер': s_num_oper,
                               'Опер_номер': oper['Опер_номер'],
                               'Опер_имя': oper['Опер_наименование'],

                               'Пном мат': '',
                               'Мат_кд_шт.': mat_znch,
                               'Мат_кд_кол': round(mat_znch * dse['Количество'], 2),
                               'Мат_кд': mat_name,
                               'Ссылка': link_docs,

                               'Мат_тд_код': '',
                               'Мат_тд_наим': '',
                               'Мат_тд_шт': '',
                               'Мат_тд_кол': '',
                               'Этап': oper['Этап'],
                               'Профессия': oper['Опер_профессия_наименование'],
                               'Вид_работ': self.DICT_PROFESSIONS[oper['Опер_профессия_код']][
                                   'Вид_работ'],
                               'КР': kr, 'КОИД': oper['Опер_КОИД'], 'Коэф.Поста': koef_posta,
                               'РЦ': oper['Опер_РЦ_код'], 'Тпз_мин': oper['Опер_Тпз'],
                               'Тшт_1дет_мин': oper['Опер_Тшт_ед'],
                               'Тшт*Кол-во*Заяв_мин': tsht_kol_zayvk, 'Тшт*Кол-во*Заяв_минk_post_мин': round(time, 2),
                               }
                    list_log.append(tmp_row)

                    for s_num_mat, mat in enumerate(oper['Материалы']):
                        if mat['Материалы_Статья_калькуляции'] == 'Сырье' and mat[
                            'Способы_получения_материала'] == 'Обеспечивать':
                            tmp_row_mat = copy.deepcopy(tmp_row)
                            tmp_row_mat['Пном мат'] = s_num_mat
                            tmp_row_mat['Мат_кд_шт.'] = ''
                            tmp_row_mat['Мат_кд_кол'] = ''
                            tmp_row_mat['Мат_кд'] = ''
                            tmp_row_mat['Ссылка'] = ''
                            tmp_row_mat['Мат_тд_код'] = mat['Мат_код']
                            tmp_row_mat['Мат_тд_наим'] = mat['Мат_наименование']
                            tmp_row_mat['Мат_тд_шт'] = mat['Мат_норма_ед']
                            tmp_row_mat['Мат_тд_кол'] = round(mat['Мат_норма'], 2)
                            tmp_row_mat['КР'] = ''
                            tmp_row_mat['КОИД'] = ''
                            tmp_row_mat['Коэф.Поста'] = ''
                            tmp_row_mat['РЦ'] = oper['Опер_РЦ_код']
                            tmp_row_mat['Тпз_мин'] = ''
                            tmp_row_mat['Тшт_1дет_мин'] = ''
                            tmp_row_mat['Тшт*Кол-во*Заяв_мин'] = ''
                            tmp_row_mat['Тшт*Кол-во*Заяв_минk_post_мин'] = ''

                            list_log.append(tmp_row_mat)
        return dict_norm, list_log

    def oformlenie_formi_mk(self, tabl, s):
        for i in range(11, len(s[0]) - 1, 4):
            for j in range(0, len(s) - 1):
                # if tabl.item(j,i) == None:
                #    cellinfo = QtWidgets.QTableWidgetItem('')
                #    tabl.setItem(j,i, cellinfo)
                CQT.set_color_wtab_c(tabl, j, i, 227, 227, 227)

                # tabl.item(j,i).setBackground(QtGui.QColor(227,227,227))
        for i in range(0, 11):
            for j in range(0, len(s) - 1):
                # if tabl.item(j,i) == None:
                #    cellinfo = QtWidgets.QTableWidgetItem('')
                #    tabl.setItem(j,i, cellinfo)
                # tabl.item(j,i).setBackground(QtGui.QColor(227,227,227))
                CQT.set_color_wtab_c(tabl, j, i, 227, 227, 227)

    def show_file_founding_mk(self):
        def add_file(self, nom_mk):
            self.load_file_mk_founfing()
            resp = CSQ.custom_request_c(self.bd_files,
                                        f"""SELECT Num_mk, fio from MK_founding WHERE Num_mk = {nom_mk};""")
            if resp == None or resp == False:
                CQT.msgbox(f'Ошибка доступа к БД')
                return
            if len(resp) == 1:
                CSQ.custom_request_c(self.bd_files, """INSERT INTO  MK_founding(Num_mk,file,fio) VALUES (?,?,?);""",
                                     list_of_lists_c=[[nom_mk, self.mk_file_founding, F.user_name()]])
            else:
                CSQ.custom_request_c(self.bd_files, """UPDATE  MK_founding SET (file,fio) = (?,?) WHERE Num_mk = ?;""",
                                     list_of_lists_c=[[self.mk_file_founding, F.user_name(), nom_mk]])

        if self.tabl_mk.currentRow() == -1:
            return
        row = self.tabl_mk.currentRow()
        tbl = self.tabl_mk
        nom_tek_mk = self.tabl_mk.item(row, CQT.num_col_by_name_c(self.tabl_mk, 'Пномер')).text()
        nom_mk = int(nom_tek_mk)

        if CQT.get_key_modifiers(self) == ['alt']:
            add_file(self, nom_mk)

        path = self.get_file_founding(nom_mk, F.put_po_umolch())
        if path == False:
            if not CQT.msgboxgYN(f'Отсутствует файл. Прикрепить вновь?'):
                return
            add_file(self, nom_mk)
            CQT.msgbox('Успешно')
            return
        F.run_file_os_c(path)

    def load_file_mk_founfing(self):
        path = CQT.f_dialog_name(self, 'Выбрать СЗ', CMS.load_tmp_path('file_mk_founfing'), "PDF files (*.pdf)")
        if path == '.':
            return
        CMS.save_tmp_path('file_mk_founfing', path, True)
        self.mk_file_founding = F.load_file_convert_to_binary(path)
        if sys.getsizeof(self.mk_file_founding) > 1048576:
            self.mk_file_founding = ''
            CQT.msgbox(f'Размер файла должен быть не более 1 мб')
            return
        self.mk_file_founding = F.pack_byte_file(self.mk_file_founding)
        return

    def check_file_founding(self):
        if self.mk_file_founding == "":
            CQT.blink_obj_c(self, 2, self.ui.btn_load_file_mk_founfing, 'Файл - СЗ основание не выбран')
            return False
        return True

    def get_file_founding(self, nom_mk, path_save):
        file = CSQ.custom_request_c(self.bd_files, f"""SELECT file FROM MK_founding WHERE Num_mk = {int(nom_mk)}""",
                                    one=True,
                                    hat_c=False, one_column=True)
        if file == False or file == [] or file == '':
            return False
        unpack = F.unpack_byte_file(file)
        try:
            F.save_binary_convert_to_file(unpack,
                                          path_save + F.sep() + f'{str(nom_mk)}.pdf')
        except:
            CQT.msgbox(f'Ошибка выгрузки, файл занят')
        return path_save + F.sep() + f'{str(nom_mk)}.pdf'

    @CQT.onerror
    def save_mk(self, *args):

        if self.cr_mk_xml_koef_norm_mat != 1 or self.cr_mk_xml_koef_norm_time != 1:
            CQT.msgbox(f'Для сохранения МК, коэффициенты материала и времени не могут быть отличны от 1')
            return

        if 'dict_cur_poz_cr_mk' not in self.__dict__:
            CQT.blink_obj_c(self, 2, self.ui.cmb_cr_mk_poz, f'Не выбрана позиция')
            return

        msg_proizv_err = 'Необходима СЗ .pdf подписанная нач. Производства'
        msg_pdo_err = 'Необходима СЗ .pdf подписанная нач. ПДО'
        msg_tehn_err = 'Необходима СЗ .pdf подписанная гл. Технологом'
        # nom_pu = self.ui.comboBox_PY

        prim = self.ui.lineEdit_prim
        tab2 = self.ui.tabWidget_2

        if self.res == '':
            CQT.msgbox('Не создана ресурсная')
            return
        res_pickle = F.to_binary_pickle(self.res)
        if self.ui.comboBox_napravlenia.currentText() == '':
            CQT.msgbox('Не указано направление')
            return
        if self.ui.comboBox_sort_c.currentText() == '':
            CQT.msgbox('Не указан Вид изделия')
            return
        if self.ui.lineEdit_ves.text() == "" or F.is_numeric(self.ui.lineEdit_ves.text()) == False:
            CQT.msgbox("Не указан вес")
            return
        if self.ui.cmb_tip_mk.currentText() == '':
            CQT.blink_obj_c(self, 2, self.ui.cmb_tip_mk, 'Не выбран тип МК')
            return

        if self.ui.cmb_tip_mk.currentText() == 'Плановая':
            nom_mk = CSQ.custom_request_c(self.db_kplan,  # 08.07.25 Если мк привязанная к плану удалена - игнорируем
                                          f"""
                                            SELECT МК FROM plan 
                                            LEFT JOIN mk ON mk.Пномер = plan.МК 
                                            WHERE plan.Пномер = {self.dict_cur_poz_cr_mk['Пномер']}
                                                AND plan.МК != 0 AND mk.На_удал != 1
            """,
                                          hat_c=False, one=True, one_column=True, attach_dbs=self.bd_naryad)
            if nom_mk == False:
                CQT.msgbox(f'Ошибка подбора МК')
                return
            if nom_mk != []: #11.11.25
                CQT.msgbox(f'На эту позицию плановая МК {nom_mk} уже ранее создана')
                return

        tip_mk = self.DICT_TIP_MK[self.ui.cmb_tip_mk.currentText()]['Пномер']

        if tip_mk == 4:
            CQT.msgbox(f'Отключено')
            return
        if tip_mk == 2:
            if self.ui.cmb_tip_dorez.currentText() == '':
                CQT.blink_obj_c(self, 2, self.ui.cmb_tip_dorez, 'Не выбран тип дорезки')
                return
            if self.ui.cmb_nom_jur_vneplan.currentText() == '':
                CQT.blink_obj_c(self, 2, self.ui.cmb_nom_jur_vneplan, 'Не выбран номер из журнала внеплана')
                return
            if not self.check_file_founding():
                if self.DICT_TIP_DOREZ[self.ui.cmb_tip_dorez.currentText()]['Пномер'] in (1, 2, 3, 11):
                    CQT.msgbox(msg_proizv_err)
                    return
                if self.DICT_TIP_DOREZ[self.ui.cmb_tip_dorez.currentText()]['Пномер'] in (10, 12):
                    CQT.msgbox(msg_pdo_err)
                    return
                if self.DICT_TIP_DOREZ[self.ui.cmb_tip_dorez.currentText()]['Пномер'] in (4, 5, 6, 7, 8, 9):
                    CQT.msgbox(msg_tehn_err)
                    return
        if tip_mk in (3,):
            if not self.check_file_founding():
                CQT.msgbox(msg_tehn_err)
                return
        if tip_mk in (6,):
            if not self.check_file_founding():
                CQT.msgbox(msg_pdo_err)
                return
        tip_dorabot = 0
        if tip_mk == 5:
            if self.ui.cmb_tip_dorez.currentText() == '':
                CQT.blink_obj_c(self, 2, self.ui.cmb_tip_dorez, 'Не выбран тип доработки')
                return
            if self.ui.cmb_nom_jur_vneplan.currentText() == '':
                CQT.blink_obj_c(self, 2, self.ui.cmb_nom_jur_vneplan, 'Не выбран номер из журнала внеплана')
                return
            if not self.check_file_founding():
                if self.DICT_TIP_DORAB[self.ui.cmb_tip_dorez.currentText()]['Пномер'] in (1, 2, 3, 4, 10, 11):
                    CQT.msgbox(msg_proizv_err)
                    return
                if self.DICT_TIP_DORAB[self.ui.cmb_tip_dorez.currentText()]['Пномер'] in (12, 6, 9, 5, 7, 8, 12):
                    CQT.msgbox(msg_tehn_err)
                    return
                # if self.DICT_TIP_DORAB[self.ui.cmb_tip_dorez.currentText()]['kod'] in (6, 7):
                #    CQT.msgbox(msg_pdo_err)
                #    return
            tip_dorabot = self.DICT_TIP_DORAB[self.ui.cmb_tip_dorez.currentText()]['Пномер']
        ves = F.valm(self.ui.lineEdit_ves.text())
        if ves <= 0 and self.place.poki == 0:  # 15.04.25
            CQT.msgbox(f'Вес не может быть 0')
            return

        nom_pu_r = self.dict_cur_poz_cr_mk["№ERP"]
        # if nom_pu_r == '-':
        #    CQT.msgbox(f'№ERP не может быть '-'')
        #    return
        nom_pr_r = self.dict_cur_poz_cr_mk["Проект"]
        tablrazr_MK = self.ui.table_razr_MK
        tabl = self.ui.table_zayavk
        if tab2.currentIndex() == 1:

            if tablrazr_MK.rowCount() == 0:
                return
        if tab2.currentIndex() == 0:

            if tabl.rowCount() == 0:
                return

        project = ''
        spisok = ''
        if self.ui.tabWidget_2.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_2,
                                                                            'Создание МК из *.XML'):
            spisok = CQT.list_from_wtabl_c(tabl, '', True)
        if self.ui.tabWidget_2.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget_2, 'Разработка МК'):
            spisok = CQT.list_from_wtabl_c(tablrazr_MK, '', True)
        if spisok == '':
            return
        nk_ur = F.num_col_by_name_in_hat_c(spisok, 'Уровень')
        nk_naim = F.num_col_by_name_in_hat_c(spisok, 'Наименование')
        nk_oboz = F.num_col_by_name_in_hat_c(spisok, 'Обозначение')
        min_ur = 100
        for i in range(1, len(spisok)):
            if int(spisok[i][nk_ur]) < min_ur:
                min_ur = int(spisok[i][nk_ur])
                project = f'{spisok[i][nk_oboz]} {spisok[i][nk_naim]}'
        osnovanie = self.ui.label_ass.text()
        data_sozd = F.date(2)

        prim = prim.text().replace('\n', ' ')
        stroki_strok = [  # 04.08.25 При ошибке в sql мк создается поверх последнего номерка
            data_sozd, 'Закрыта', project, '', '', "",
            prim, osnovanie, '', '',
            "",
            ves, '', self.kol_izdeliy, '', '', '', 2, '', self.place.Код, '', tip_mk, '', F.user_full_namre(),
            self.dict_cur_poz_cr_mk['Пномер'], tip_dorabot]
        self.xml_head = int(bool(self.tkp_current_schema.XML_start_from_project_product_type))

        if 'dict_cur_poz_cr_mk' not in self.__dict__:
            CQT.blink_obj_c(self, 2, self.ui.cmb_cr_mk_poz, f'Не выбрана позиция')
            return
        # ---------------
        CONN, cur = CSQ.connect_bd(self.bd_naryad)
        # CSQ.add_line_into_db_sql_c(self.bd_naryad, 'mk', stroki_strok, conn=CONN, cur = cur)
        response = CSQ.custom_request_c(self.bd_naryad, f"""INSERT INTO mk(Дата
            , Статус
            , Номенклатура
            , Номер_заказа
            , Номер_проекта
            , Вид
            , Примечание
            , Основание
            , Прогресс
            , Приоритет
            , Направление
            , Вес
            , xml
            , Количество
            , Статус_ЧПУ
            , Ресурсная
            , Дата_завершения
            , Коэф_парал
            , Обеспечение
            , Место
            , Искл_план_рм
            , Тип
            , Ресурсная_дата
            , ФИО
            , НомКплан 
            , Тип_доработки) VALUES ({", ".join(['?'] * len(stroki_strok))}) RETURNING Пномер;""",
                                        # ++ 28.07.25 по задаче 100057537
                                        list_of_lists_c=stroki_strok,
                                        rez_dict=True,
                                        one=True,
                                        conn=CONN,
                                        cur=cur)
        if not response:
            return CQT.msgbox('Ошибка создания МК')
        nom = response['Пномер']
        # -- 27.07.25 по задаче 100057537
        CSQ.custom_request_c(self.bd_naryad, """INSERT INTO  zagot(Ном_МК,Прим_резка,Вес_по_рес) VALUES (?,?,?);""",
                             conn=CONN,
                             cur=cur, list_of_lists_c=[[int(nom), '', self.ves_res_list]])
        check_zagot = CSQ.custom_request_c(self.bd_naryad, f"""SELECT * FROM zagot WHERE Ном_МК == {int(nom)}""")
        if len(check_zagot) == 1:
            CSQ.custom_request_c(self.bd_naryad, """INSERT INTO  zagot(Ном_МК,Прим_резка,Вес_по_рес) VALUES (?,?,?);""",
                                 conn=CONN,
                                 cur=cur, list_of_lists_c=[[int(nom), '', self.ves_res_list]])
            check_zagot = CSQ.custom_request_c(self.bd_naryad, f"""SELECT * FROM zagot WHERE Ном_МК == {int(nom)}""")
            if len(check_zagot) == 1:
                CQT.msgbox(f'Ошибка загрузки МК, не внесена строка в журнал zagot нужно внести вручную')

        if tip_mk == 2:
            CSQ.custom_request_c(self.bd_naryad, """INSERT INTO  дорезки_мк(Номер_мк,Причина) VALUES (?,?);""",
                                 conn=CONN,
                                 cur=cur,
                                 list_of_lists_c=[
                                     [int(nom), self.DICT_TIP_DOREZ[self.ui.cmb_tip_dorez.currentText()]['Пномер']]])

        CSQ.close_bd(CONN, cur)

        CONN, cur = CSQ.connect_bd(self.db_resxml)
        # CSQ.add_line_into_db_sql_c(self.db_resxml, 'xml', stroki_strok=[[int(nom), self.xml_file, self.xml_head]],
        #                       s_pervoi=True, conn=CONN, cur =cur)
        rez = CSQ.custom_request_c(self.db_resxml, f"""SELECT Номер_мк FROM xml WHERE Номер_мк = {int(nom)}""",
                                   conn=CONN,
                                   cur=cur, one=True)
        if len(rez) == 1:
            CSQ.custom_request_c(self.db_resxml, """INSERT INTO  xml(Номер_мк,data,Head) VALUES (?,?,?);""", conn=CONN,
                                 cur=cur, list_of_lists_c=[[int(nom), self.xml_file, self.xml_head]])
        else:
            CSQ.custom_request_c(self.db_resxml, """UPDATE xml SET(data,Head) = (?,?) WHERE Номер_мк = ?;""", conn=CONN,
                                 cur=cur, list_of_lists_c=[[self.xml_file, self.xml_head, int(nom)]])

        # CSQ.add_line_into_db_sql_c(self.db_resxml, 'res', stroki_strok=[[int(nom), res_pickle]], s_pervoi=True,
        #                       conn=CONN, cur =cur)
        rez = CSQ.custom_request_c(self.db_resxml, f"""SELECT Номер_мк FROM res WHERE Номер_мк = {int(nom)}""",
                                   conn=CONN,
                                   cur=cur, one=True)
        if len(rez) == 1:
            CSQ.custom_request_c(self.db_resxml, """INSERT INTO res(Номер_мк,data) VALUES (?,?);""", conn=CONN,
                                 cur=cur, list_of_lists_c=[[int(nom), res_pickle]])
        else:
            CSQ.custom_request_c(self.db_resxml, """UPDATE res SET(Номер_мк,data) = (?,?);""", conn=CONN,
                                 cur=cur, list_of_lists_c=[[int(nom), res_pickle]])
        CSQ.close_bd(CONN, cur)

        CSQ.custom_request_c(self.bd_files, """INSERT INTO  MK_founding(Num_mk,file,fio) VALUES (?,?,?);""",
                             list_of_lists_c=[[int(nom), self.mk_file_founding, F.user_name()]])
        if tip_mk == 2 or tip_mk == 5:
            if not F.is_numeric(self.ui.cmb_nom_jur_vneplan.currentText()):
                CQT.msgbox(f'Не выбран номер из журнала внеплана')
                return
            nom_jur_vnepl = int(self.ui.cmb_nom_jur_vneplan.currentText())
            CSQ.custom_request_c(self.bd_naryad,
                                 f'''UPDATE jur_vnepl SET Номер_нов_мк = {nom} WHERE Пномер ={nom_jur_vnepl}''')

        # nom = str(CSQ.find_in_db_c(self.bd_naryad, 'mk',{'Дата':data_sozd},['Пномер'])[0][0])
        if self.ui.tabWidget_2.currentIndex() == 0:
            spisok = CQT.list_from_wtabl_c(tabl, '', True)
        else:
            spisok = CQT.list_from_wtabl_c(tablrazr_MK, '', True)

        if F.existence_file_c(F.scfg('mk_data') + os.sep + str(nom)) == False:
            F.create_dir_c(F.scfg('mk_data') + os.sep + str(nom))
        dir_tp = F.scfg('mk_data') + os.sep + str(nom)

        for i in range(0, len(spisok)):
            for j in range(9, len(spisok[0])):
                if '\n' in spisok[i][j]:
                    spisok[i][j] = spisok[i][j].replace('\n', '$')
        nom_kol_naim = F.num_col_by_name_in_hat_c(spisok, 'Наименование')
        nom_kol_nn = F.num_col_by_name_in_hat_c(spisok, 'Обозначение')
        for i in range(0, len(spisok)):
            if i > 0:
                naim_dse = spisok[i][nom_kol_naim].strip()
                nn_dse = spisok[i][nom_kol_nn].strip()
                if nn_dse not in self.DICT_DSE_save_mk:
                    CQT.msgbox(f'Не найден номер техкарты {nn_dse}')
                ntk = self.DICT_DSE_save_mk[nn_dse]['Номер_техкарты']
                # ntk = \
                #    CSQ.find_in_db_c(self.bd_naryad, 'dse', {'Номенклатурный_номер': nn_dse, 'Наименование': naim_dse},
                #                   ['Номер_техкарты'], all=False, conn=CONN)[0]
                rez = F.copy_file_c(F.scfg('add_docs') + os.sep + ntk + "_" + nn_dse + '.pickle',
                                    dir_tp + os.sep + ntk + "_" + nn_dse + '.pickle')
                if rez == False:
                    CQT.msgbox(f'Не удалось скопировать файл {ntk + "_" + nn_dse + ".pickle"}, не сохранено')
            spisok[i] = "|".join(spisok[i])

        # =================KPLAN============================================
        if self.ui.cmb_tip_mk.currentText() == 'Плановая':
            CSQ.custom_request_c(self.db_kplan,
                                 f"""UPDATE plan SET МК = {int(nom)} WHERE Пномер = {self.dict_cur_poz_cr_mk['Пномер']};""")
            # CSQ.custom_request_c(self.db_kplan,
            #                     f"""UPDATE пл_топ SET Дата_МК = {F.now("%Y-%m-%d")} WHERE НомПл = {self.dict_cur_poz_cr_mk['Пномер']};""")
        # ==================================================================

        if self.ui.tabWidget_2.currentIndex() == 1:
            self.clear_mk()
        else:
            self.ui.table_zayavk.clear()
            self.ui.table_zayavk.setRowCount(0)

        dop = ''
        if nom_pu_r.strip() == '-':
            dop = '!!! Необходимо выгрузить ресурсную в ЕРП и создать №ERP'
        try:
            msg = f"{F.user_full_namre()} СОЗДАЛ МК № {str(nom)}:\n{project} - {self.kol_izdeliy} шт.\n{nom_pu_r.strip()} Проект: {nom_pr_r.strip()}\n" \
                  f"Прим.: {prim} {osnovanie},\nТип: {self.ui.cmb_tip_mk.currentText()}  {self.ui.cmb_tip_dorez.currentText()} {dop}"
            CMS.send_info_mk_b24_by_action(msg, 'Готовность Маршрутных карт')
        except:
            print('Ошибка отправки в Б24')
        CQT.msgbox('маршрутная карта ' + str(nom) + ' успешно сохранена')
        # 24.12.2025
        if hasattr(self, '_mk_dirty'):
            self._mk_dirty.mark_clean()
        try:
            self.ui.tabWidget.setCurrentIndex(CQT.number_table_by_name_c(self.ui.tabWidget, 'Маршрутные карты'))
            nk_ststus = CQT.num_col_by_name_c(self.ui.tbl_filtr_mk, 'Статус')
            nk_dat_zav = CQT.num_col_by_name_c(self.ui.tbl_filtr_mk, 'Дата_завершения')
            self.ui.tbl_filtr_mk.item(0, nk_ststus).setText('Закрыта')
            self.ui.tbl_filtr_mk.item(0, nk_dat_zav).setText('!*')
            CMS.apply_filtr_c(self, self.ui.tbl_filtr_mk, self.ui.table_spis_MK)
            self.ui.table_spis_MK.selectRow(self.ui.table_spis_MK.rowCount() - 1)
            self.ui.table_spis_MK.scrollToBottom()
        except:
            pass

    def summ_kol(self, s, i):
        naim = s[i][0].strip()
        nn = s[i][1].strip()
        summ = 0
        for j in range(1, len(s)):
            if s[j][0].strip() == naim and s[j][1].strip() == nn:
                summ += int(s[j][2])
        return summ

    def udal_kol(self, spisok, nom_kol):
        for i in range(0, len(spisok)):
            spisok[i].pop(nom_kol)
        return spisok

    def oformlenie_sp_pod_mk(self, s):
        nk_pki = F.num_col_by_name_in_hat_c(s, 'ПКИ')
        nk_level_c = F.num_col_by_name_in_hat_c(s, 'Уровень')
        if nk_pki == None:
            CQT.msgbox(f'Не найдена колонка ПКИ')
            return
        if nk_level_c == None:
            CQT.msgbox(f'Не найдена колонка Уровень')
            return
        for i in range(1, len(s)):
            if s[i][nk_pki] != '+':
                s[i][nk_pki] = s[i][nk_pki].replace('0', '')
                s[i][nk_pki] = s[i][nk_pki].replace('1', '+')
        # for j in range(nk_level_c, len(s[0])):
        #    s = self.udal_kol(s, nk_level_c)
        for j in s:
            for i in range(nk_level_c, len(s[0])):
                if '$' in str(j[i]):
                    vrem, oper = [x for x in j[i].split("$")]
                    j[i] = 'Время: ' + vrem + ' мин.' + '\n' + 'Операции:' + '\n' + oper
        i = 12
        while i:
            if i > len(s[0]):
                break
            for j in self.sp_ins:
                s = self.dob_kol(s, i, j)
                i += 1
            i += 1
        return s

    def summa_rc(self, rc):
        s = ''
        if F.is_numeric(rc):
            return int(rc)
        for i in rc:
            if F.is_numeric(i):
                s += str(i)
        s = int(s)
        return s

    def dob_kol(self, spis, nomer, ima):
        for i in range(0, len(spis)):
            if i == 0:
                spis[i].insert(nomer, ima)
            else:
                spis[i].insert(nomer, '')
        return spis

    def poporyadku(self, i, spis, stroka, oper):
        for j in range(i, len(spis[0])):
            if spis[stroka][j] != "":
                arr_tmp_nom = spis[stroka][j].split(';')
                arr_tmp_nom2 = arr_tmp_nom[-1].split('$')
                tmp_nom = arr_tmp_nom2[-1]
                sp_oper = oper.split(';')
                for k in range(len(sp_oper)):
                    if int(tmp_nom) < int(sp_oper[k]):
                        return False

        return True

    def dob_etap(self, spis, rc, vrem, oper, stroka, ogran):
        flag = 0
        for i in range(ogran + 1, len(spis[0])):
            if flag == 1:
                break
            if spis[0][i] == rc and self.poporyadku(i, spis, stroka, oper) == True:
                flag = 1
                spis[stroka][i] = str(vrem) + "$" + oper
                self.ogran = i - 1
                break
            if self.summa_rc(rc) < self.summa_rc(spis[0][i]):
                j = i - 1
                while j >= self.ogran:
                    if self.poporyadku(j + 1, spis, stroka, oper) == False:
                        if j + 2 >= len(spis[0]):
                            spis = self.dob_kol(spis, j + 2, rc)
                        if spis[0][j + 2] != rc:
                            spis = self.dob_kol(spis, j + 2, rc)
                        spis[stroka][j + 2] = str(vrem) + "$" + oper
                        self.ogran = j + 2
                        flag = 1
                        break
                    if j <= ogran:
                        if spis[0][j + 1] != rc:
                            spis = self.dob_kol(spis, j + 1, rc)
                        spis[stroka][j + 1] = str(vrem) + "$" + oper
                        self.ogran = j + 1
                        flag = 1
                        break
                    if self.summa_rc(rc) >= self.summa_rc(spis[0][j]):
                        if spis[0][j + 1] != rc:
                            spis = self.dob_kol(spis, j + 1, rc)
                        spis[stroka][j + 1] = str(vrem) + "$" + oper
                        self.ogran = j + 1
                        flag = 1
                        break
                    if j == self.ogran:
                        if spis[0][self.ogran] != rc:
                            spis = self.dob_kol(spis, self.ogran, rc)
                        spis[stroka][self.ogran] = str(vrem) + "$" + oper
                        flag = 1
                        break
                    j -= 1
            else:
                j = i + 1
                while j <= len(spis[0]) - 1:
                    if self.summa_rc(rc) == self.summa_rc(spis[0][j]) and self.poporyadku(j + 1, spis, stroka,
                                                                                          oper) == True:
                        spis[stroka][j] = str(vrem) + "$" + oper
                        self.ogran = j
                        flag = 1
                        break
                    if self.summa_rc(rc) < self.summa_rc(spis[0][j]) and self.poporyadku(j + 1, spis, stroka,
                                                                                         oper) == True:
                        spis = self.dob_kol(spis, j - 1, rc)
                        spis[stroka][j - 1] = str(vrem) + "$" + oper
                        self.ogran = j - 1
                        flag = 1
                        break
                    j += 1
                if flag == 0:
                    spis = self.dob_kol(spis, len(spis[0]), rc)
                    spis[stroka][len(spis[0]) - 1] = str(vrem) + "$" + oper
                    self.ogran = len(spis[0]) - 1
                    flag = 1
                    break

        if flag == 0:
            spis = self.dob_kol(spis, len(spis[0]), rc)
            spis[stroka][len(spis[0]) - 1] = str(vrem) + "$" + oper
            self.ogran = len(spis[0]) - 1
        return spis

    def dob_izd_k_bd(self):
        def get_nr_nv_from_auts(self, list_auts, nn, ima):
            nr = ''
            nv = ''
            dse = nn + " " + ima + ".dft"
            for aut in list_auts:
                for num in aut['num']:
                    if aut['num'][num]['Part file name'] == dse:
                        return aut['num'][num]['weight_with_rem'], aut['num'][num]['TOTAL_CUT_MACHINE_TIME_MINUTES']

            return nr, nv

        if self.place.poki == 0:
            list_auts = CHPY.check_full_raskroy(self)
            if list_auts == None:
                CQT.msgbox(f'Не соответсвуют раскладки структуре')
                return

        tree = self.ui.tree_base_tree
        spis_dse = CQT.list_from_tree_c(tree, True)
        # bd = CSQ.list_from_db_sql_c(self.bd_naryad, 'dse', False, hat_c=True)
        n = 0
        m = 0
        nk_ima = F.num_col_by_name_in_hat_c(spis_dse, 'Наименование')
        nk_nn = F.num_col_by_name_in_hat_c(spis_dse, 'Обозначение полное')
        nk_mat = F.num_col_by_name_in_hat_c(spis_dse, 'Масса/М1,М2,М3')
        nk_adres = F.num_col_by_name_in_hat_c(spis_dse, 'Ссылка на объект DOCs')
        nk_klass = F.num_col_by_name_in_hat_c(spis_dse, 'Классификатор изделия')
        nk_kod_erp = F.num_col_by_name_in_hat_c(spis_dse, 'Код ERP')
        nk_prim = F.num_col_by_name_in_hat_c(spis_dse, 'Примечание')
        nk_razdel = F.num_col_by_name_in_hat_c(spis_dse, 'Раздел')
        nk_tip = F.num_col_by_name_in_hat_c(spis_dse, 'Тип')
        conn, cur = CSQ.connect_bd(self.db_dse)
        for i in range(1, len(spis_dse)):
            bd_tmp = []
            nr = None
            nv = None
            ima = F.clear_row_for_file_name_c(spis_dse[i][nk_ima])
            nn = F.clear_row_for_file_name_c(spis_dse[i][nk_nn])
            if nn == '':
                CSQ.close_bd(conn, cur)
                CQT.msgbox(f'{ima} строка {i} Номенклатурный_номер не может быть пусто')
                return
            nr, nv = get_nr_nv_from_auts(self, list_auts, nn, ima)
            adres = spis_dse[i][nk_adres]
            mat = spis_dse[i][nk_mat]
            klass = spis_dse[i][nk_klass]
            kod_erp = spis_dse[i][nk_kod_erp]
            tip = spis_dse[i][nk_tip]
            if tip in self.TIP_NEGRUZ_DSE:
                continue
            if spis_dse[i][nk_prim] != '':
                prim = f'(ОГК: {spis_dse[i][nk_prim]})'
            else:
                prim = ''
            # custom_request_c = f'SELECT * FROM dse WHERE Номенклатурный_номер = "{nn}" AND Наименование = "{ima}"'
            # query = CSQ.find_in_db_c(self.db_dse, siroy_custom_request_c=custom_request_c, conn=conn, cur=cur, hat_c=True, all=False)
            poki = USRCNF.Config.place.poki
            query = CSQ.custom_request_c(self.db_dse,
                                         f'SELECT * FROM dse WHERE Номенклатурный_номер = "{nn}" AND poki = {poki};',
                                         conn=conn, cur=cur, hat_c=True,
                                         one=True)
            if len(query) == 1:
                bd_tmp.append(
                    [nn, ima, '', prim, adres, '', '', '', '', '', '', mat, kod_erp, klass, nr, nv, self.place.poki])
                # CSQ.add_line_into_db_sql_c(self.db_dse, 'dse', bd_tmp, conn=conn, cur=cur)
                CSQ.custom_request_c(self.db_dse, f"""INSERT INTO dse(Номенклатурный_номер 
                    ,Наименование 
                    ,Номер_техкарты 
                    ,Примечание 
                    ,Путь_docs 
                    ,Доступ 
                    ,Процесс 
                    ,Нормы 
                    ,Материалы 
                    ,Тех_заметки 
                    ,Теги 
                    ,Мат_кд 
                    ,Код_ЕРП 
                    ,Классификатор, 
                    Нр_техн_дет, 
                    Нв_техн_раскрой, 
                    poki
                    ) VALUES ({', '.join(['?'] * len(bd_tmp[-1]))});""",
                                     list_of_lists_c=bd_tmp,
                                     conn=conn, cur=cur)
                n += 1
            else:
                if ima != query[1][F.num_col_by_name_in_hat_c(query, 'Наименование')]:
                    # CSQ.update_bd_sql(self.db_dse, 'dse', {'Примечание': prim},
                    #                  {'Пномер': query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}, conn=conn, cur=cur)
                    CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Наименование = '{ima}' WHERE
                     Пномер = {query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}; """, conn=conn, cur=cur)
                    m += 1
                if prim != query[1][F.num_col_by_name_in_hat_c(query, 'Примечание')]:
                    # CSQ.update_bd_sql(self.db_dse, 'dse', {'Примечание': prim},
                    #                  {'Пномер': query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}, conn=conn, cur=cur)
                    CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Примечание = '{prim}' WHERE
                     Пномер = {query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}; """, conn=conn, cur=cur)
                    m += 1
                if adres != query[1][F.num_col_by_name_in_hat_c(query, 'Путь_docs')]:
                    # CSQ.update_bd_sql(self.db_dse, 'dse', {'Путь_docs': adres},
                    #                  {'Пномер': query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}, conn=conn, cur=cur)
                    CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Путь_docs = '{adres}' WHERE
                                         Пномер = {query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}; """,
                                         conn=conn,
                                         cur=cur)
                    m += 1
                if mat != query[1][F.num_col_by_name_in_hat_c(query, "Мат_кд")]:
                    # CSQ.update_bd_sql(self.db_dse, 'dse', {'Мат_кд': mat},
                    #                  {'Пномер': query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}, conn=conn, cur=cur)
                    CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Мат_кд = '{mat}' WHERE
                                                             Пномер = {query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}; """,
                                         conn=conn,
                                         cur=cur)
                    m += 1
                if klass != query[1][F.num_col_by_name_in_hat_c(query, "Классификатор")]:
                    # CSQ.update_bd_sql(self.db_dse, 'dse', {'Классификатор': klass},
                    #                  {'Пномер': query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}, conn=conn, cur=cur)
                    CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Классификатор = '{klass}' WHERE
                                               Пномер = {query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}; """,
                                         conn=conn,
                                         cur=cur)
                    m += 1
                if kod_erp != query[1][F.num_col_by_name_in_hat_c(query, "Код_ЕРП")]:
                    # CSQ.update_bd_sql(self.db_dse, 'dse', {'Код_ЕРП': kod_erp},
                    #                  {'Пномер': query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}, conn=conn, cur=cur)
                    CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Код_ЕРП = '{kod_erp}' WHERE
                                                Пномер = {query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}; """,
                                         conn=conn,
                                         cur=cur)
                    m += 1
                if nr != query[1][F.num_col_by_name_in_hat_c(query, "Нр_техн_дет")]:
                    # CSQ.update_bd_sql(self.db_dse, 'dse', {'Код_ЕРП': kod_erp},
                    #                  {'Пномер': query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}, conn=conn, cur=cur)
                    CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Нр_техн_дет = '{nr}' WHERE
                                                Пномер = {query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}; """,
                                         conn=conn,
                                         cur=cur)
                    m += 1
                if nv != query[1][F.num_col_by_name_in_hat_c(query, "Нв_техн_раскрой")]:
                    # CSQ.update_bd_sql(self.db_dse, 'dse', {'Код_ЕРП': kod_erp},
                    #                  {'Пномер': query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}, conn=conn, cur=cur)
                    CSQ.custom_request_c(self.db_dse, f"""UPDATE dse SET Нв_техн_раскрой = '{nv}' WHERE
                                                Пномер = {query[1][F.num_col_by_name_in_hat_c(query, 'Пномер')]}; """,
                                         conn=conn,
                                         cur=cur)
                    m += 1
        CSQ.close_bd(conn, cur)
        if n == 0:
            CQT.msgbox(f'Новых ДСЕ не добавлено, обновлено {m} значений')
        else:
            CQT.msgbox(f'Добавлено ' + str(n) + f' ед. ДСЕ, обновлено {m} значений')

    @CQT.onerror
    def viborXML(self, *args):
        vklad = self.ui.tabWidget
        tabl = self.ui.table_zayavk
        tree = self.ui.tree_base_tree
        tab = self.ui.tabWidget
        CQT.clear_tbl(tabl)
        hat_c = ['Файл', 'Изделие', 'Количество', 'К_мат', 'К_врем']
        tabl.setColumnCount(5)
        tabl.setHorizontalHeaderLabels(hat_c)
        self.xml_name = None
        if tab.tabText(tab.currentIndex()) == 'Просмотр структуры':
            head_state = self.ui.chk_consider_project_abs_product.isChecked()
            xml_head = int(bool(head_state))
        else:
            xml_head = self.tkp_current_schema.XML_start_from_project_product_type

        def select_and_load_file(self):
            tmp_putt = CMS.load_tmp_path("tmp_putt")
            nomen_name = ''
            if getattr(self,'dict_cur_poz_cr_mk',False):
                if 'Номен. ЕРП' in self.dict_cur_poz_cr_mk:
                    nomen_name = f" для Номен. ЕРП: {self.dict_cur_poz_cr_mk['Номен. ЕРП']}"
            putt = CQT.f_dialog_name(self, 'Выбрать XML' + nomen_name, tmp_putt, "Файлы *.xml")
            if putt == '' or putt == '.':
                return None, None

            CMS.save_tmp_path("tmp_putt", putt, True)

            xml = XML.spisok_iz_xml(putt)
            self.xml_name = F.throw_out_extention_c(putt.split(F.sep())[-1])
            spis_xml = CMS.podgotovka_xml(self, xml, show_negruz=True, xml_head=xml_head)
            return putt, spis_xml

        def check_file(spis_xml):

            if spis_xml == None:
                CQT.msgbox('Файл не корректный')
                return False
            err_flag = False

            msg_text = ''
            for i in range(len(spis_xml)):
                if 'Тип' not in spis_xml[i]['data']:
                    err_flag = True
                    msg_text = f'Отсутствует поле Тип'
                if spis_xml[i]['data']['Наименование'] == "" and spis_xml[i]['data']['Обозначение полное'] == "":
                    err_flag = True
                    msg_text = f'Наименование  и  Обозначение полное ПУСТО'
                if spis_xml[i]['data']['Количество'] == "" or spis_xml[i]['data']['Количество на изделие'] == "":
                    msg_text = f'Количество  и  Количество на изделие ПУСТО'
                    err_flag = True
            if err_flag == True:
                CQT.msgbox(f'Файл XML {putt} имеет ошибки \n{msg_text}\n работать с ним нельзя!')

            if err_flag == True:
                self.ui.pushButton_add_v_bd.setEnabled(False)
                self.ui.pushButton_add_v_MK.setEnabled(False)
                return False
            else:
                self.ui.pushButton_add_v_bd.setEnabled(True)
                self.ui.pushButton_add_v_MK.setEnabled(True)
            return True

        if vklad.currentIndex() == CQT.number_table_by_name_c(vklad, 'Маршрутные карты'):
            xml = ''
            tbl = self.ui.table_spis_MK
            row = tbl.currentRow()
            if row == -1:
                return
            nk_pnom = CQT.num_col_by_name_c(tbl, 'Пномер')
            nom_mk = int(tbl.item(row, nk_pnom).text())
            try:
                query = f'''SELECT data, Head FROM xml 
                                   WHERE Номер_мк == {nom_mk}
                                               '''
                rez_xml = CSQ.custom_request_c(self.db_resxml, query)
                xml = rez_xml[-1][0]
                xml_head = rez_xml[-1][1]
                if xml != '':
                    xml = XML.spisok_iz_xml(str_f=xml)
                    self.ui.tabWidget.setCurrentIndex(0)
                putt = ''

            except:
                pass

        if vklad.currentIndex() == CQT.number_table_by_name_c(vklad, 'Просмотр структуры'):
            self.glob_pre_csv_file_path = ''

            putt, spis_xml = select_and_load_file(self)
            if putt == None:
                return
            if not check_file(spis_xml):
                return

            list_user = CMS.load_tree(self, spis_xml, tree)
            CMS.zapoln_tree_spiskom(self, spis_xml, list_user, tree, xml_head)
            for _ in range(0, 8):
                tree.resizeColumnToContents(_)

        if vklad.currentIndex() == CQT.number_table_by_name_c(vklad, 'Создание МК'):

            if self.ui.tabWidget_2.currentIndex() != CQT.number_table_by_name_c(self.ui.tabWidget_2,
                                                                                'Создание МК из *.XML'):
                CQT.msgbox(f'Не выбрана вкладка "Создание МК из *.XML"')
                return

            if 'dict_cur_poz_cr_mk' not in self.__dict__:
                CQT.msgbox(f'Не выбрана позиция')
                return

            putt, spis_xml = select_and_load_file(self)
            if putt == None:
                return
            if not check_file(spis_xml):
                return

            self.dob_izd(spis_xml, putt)
            self.xml_name = F.throw_out_extention_c(putt.split(F.sep())[-1])
            # self.clear_mk()

    def nalich_dannih_v_tk(self, tk, nomer_st, conn='', nomenklatura='', DICT_doc_reestr=''):
        flag = 0
        for i in range(10, len(tk)):
            if len(tk[i]) == 21:
                if tk[i][20] == '0' and flag == 1:
                    return True
                if tk[i][20] == '0' and flag == 0:
                    flag = 1
                if tk[i][20] == '1' and nomer_st == 7:
                    clean_tsht = str(tk[i][nomer_st]).lstrip(CMS.Techkards.UNRECALC_MARK)
                    if tk[i][nomer_st] == "" or F.is_numeric(clean_tsht) == False:
                        return 'norma_vr'

                if tk[i][20] == '1':
                    if nomer_st == 0:
                        if tk[i][10] == '':
                            if tk[i][0] == 'Отрезка слесарная' and tk[i][8] == '19149':
                                return False
                            if tk[i][0] == 'Отрезка(гильотина)':
                                return False
                            if tk[i][0] == 'Отрезка(лентопил)':
                                return False

                    if nomer_st == 4:
                        if tk[i][15] != '': # 05.11.25
                            attached_docs = set(tk[i][15].split('%20'))
                            exists_in_db_files = attached_docs.intersection(DICT_doc_reestr.keys())
                            exists_docs_protocol = any(
                                doc for doc in attached_docs
                                if doc.startswith('docs://')
                            )
                            if not exists_in_db_files and not exists_docs_protocol:
                                return 'docs'
                        if tk[i][nomer_st] == "010101":
                            if tk[i][0] != 'Резка(ЧПУ)':
                                return "rc"
                            else:
                                if tk[i][15] == '':
                                    return 'dxf'
                                else:
                                    if '.dxf' not in tk[i][15]:
                                        return 'dxf'
                                if i < len(tk) - 2:
                                    if tk[i + 1][20] != '2':
                                        return 'seg'

                    if tk[i][nomer_st] == 'Резка(ЧПУ)' and nomer_st == 0:
                        if tk[i][10] == '':
                            return False

                        nk_nn_nom = F.num_col_by_name_in_hat_c(nomenklatura, 'Код')
                        nk_sort_nom = F.num_col_by_name_in_hat_c(nomenklatura, 'П5')
                        nk_kod_cam = F.num_col_by_name_in_hat_c(nomenklatura, 'П6')
                        kod_mat = ''
                        material = '?'
                        nn_mat = '?'
                        sp_mat = tk[i][10].split('{')
                        for material in sp_mat:
                            if kod_mat != '':
                                break
                            nn_mat = material.split('$')[0]
                            for k in range(1, len(nomenklatura)):
                                if nomenklatura[k][nk_nn_nom] == nn_mat:
                                    if nomenklatura[k][nk_sort_nom] == '1':
                                        kod_mat = nomenklatura[k][nk_kod_cam]
                                        break
                        if kod_mat == '':
                            CQT.msgbox(f'Не найден код CAM в номенклатуре для {material} на {nn_mat}')
                            return False
        if flag == 1:
            return True
        else:
            return False

    def rc_n_k(self, ntk, nn):
        tk = F.open_file_c(F.scfg('add_docs') + os.sep + ntk + "_" + nn + '.txt', False, "|")
        nachalo = ''
        konec = ''
        if len(tk) < 11:
            return [nachalo, konec, '', '']
        for i in range(10, len(tk)):
            if tk[i][20] == '0':
                if i == len(tk) - 1:
                    return [nachalo, konec, '', '']
                for j in range(i + 1, len(tk)):
                    if tk[j][20] == '1':
                        if nachalo == '':
                            nachalo = tk[j][4]
                            nach_op = tk[j][0]
                        konec = tk[j][4]
                        kon_op = tk[j][0]
                    if tk[j][20] == '0':
                        break
        return [nachalo, konec, nach_op, kon_op]

    def ispravit_koncovky_tehkart(self, n_dse, n_tk, new_rc):
        tk = F.open_file_c(F.scfg('add_docs') + os.sep + n_tk + "_" + n_dse + '.txt', False, "|")
        f_naid = 0
        nom_st_op = 0
        for i in range(len(tk)):
            if len(tk[i]) == 21:
                if tk[i][20] == '0' and f_naid == 1:
                    break
                if tk[i][20] == '0' and f_naid == 0:
                    f_naid = 1
                if tk[i][20] == '1' and f_naid == 1:
                    nom_st_op = i
        if nom_st_op == 0:
            CQT.msgbox(f'Не удалось найти последнюю операцию в техкарте {n_tk}')
            return
        tk[nom_st_op][4] = new_rc
        F.write_file_c(F.scfg("add_docs") + os.sep + n_tk + "_" + n_dse + '.txt', tk, pickl=True, separ='|')
        return True

    def nalich_tk(self, spisok):
        xml_head = self.tkp_current_schema.XML_start_from_project_product_type
        unavailable_types = CMS.XML_get_unavailable_xml_types(xml_head)
        s_bd = []
        spis_rc = self.SPIS_RC
        custom_request_c = f'''SELECT * FROM nomen WHERE П5 == "1" '''
        nomenklatura = CSQ.custom_request_c(self.bd_nomen, custom_request_c)
        DICT_NN_NTK = CMS.load_dict_dse(self.db_dse)

        custom_request_c = f""" SELECT Пномер, file_name FROM t_kards"""
        query = CSQ.custom_request_c(self.bd_files, custom_request_c, '', hat_c=True, rez_dict=True)
        if query == False:
            CQT.msgbox(f'ОШИбка получения данных файлов с БД')
            return
        DICT_doc_reestr = F.deploy_dict_c(query, 'file_name')

        spisok = [_ for _ in spisok if _['data']['Тип'] not in unavailable_types]

        for i in range(len(spisok)):
            print(f'{i} из {len(spisok)}')
            CQT.statusbar_text(self, f'{i} из {len(spisok)}')
            ima = spisok[i]['data']['Наименование']
            nn = spisok[i]['data']['Обозначение полное']
            type_nn = spisok[i]['data']['Тип']
            flag_bd = 0
            flag_tk = 0
            flag_marsh = 0
            flag_vrema = 0
            flag_mat = 0
            flag_rc = 1
            flag_dxf = 1
            flag_seg = 1
            flag_docs = 1
            flag_rashodnik = 0
            if type(F.valm(spisok[i]['data']['Количество'])) == type(1.1):
                flag_rashodnik = 1
            nom_tk = ''
            if type_nn in unavailable_types:
                continue
            if nn not in DICT_NN_NTK:
                CQT.msgbox(f'Не найдена {nn} в БД ДСЕ')
                return
            query_dse = DICT_NN_NTK[nn]
            if len(query_dse) > 1:
                nom_tk = query_dse["Номер_техкарты"]
                flag_bd = 1
                if nom_tk != '':
                    try:
                        tk = F.open_file_c(F.scfg('add_docs') + os.sep + nom_tk + "_" + nn + '.txt', False, separ='|',
                                           pickl=True)
                        flag_tk = 1
                        if self.nalich_dannih_v_tk(tk, 4, nomenklatura=nomenklatura,
                                                   DICT_doc_reestr=DICT_doc_reestr) == True:
                            flag_marsh = 1
                        if self.nalich_dannih_v_tk(tk, 6, nomenklatura=nomenklatura,
                                                   DICT_doc_reestr=DICT_doc_reestr) == True and \
                                self.nalich_dannih_v_tk(tk, 7, nomenklatura=nomenklatura,
                                                        DICT_doc_reestr=DICT_doc_reestr) == True:
                            flag_vrema = 1
                        if self.nalich_dannih_v_tk(tk, 0, nomenklatura=nomenklatura,
                                                   DICT_doc_reestr=DICT_doc_reestr) == True:
                            flag_mat = 1
                        rez = self.nalich_dannih_v_tk(tk, 4, conn='', nomenklatura=nomenklatura,
                                                      DICT_doc_reestr=DICT_doc_reestr)
                        if rez == 'rc':
                            flag_rc = 0
                        if rez == 'dxf':
                            flag_dxf = 0
                        if rez == 'seg':
                            flag_seg = 0
                        if rez == 'docs':
                            flag_docs = 0
                    except:
                        CQT.msgbox(f'Что то не то с ТК {nom_tk}')
                        return
            if flag_bd == 0:
                s_bd.append('нет в базе ' + " " + nn + ' ' + ima)
            if flag_tk == 0:
                s_bd.append('нет техкарты ' + " " + nn + " " + ima)
            else:
                nachalo, konec, nach_op, kon_op = self.rc_n_k(nom_tk, nn)
                spisok[i]['tk'] = dict()
                spisok[i]['tk']['nach_op'] = nach_op
                spisok[i]['tk']['kon_op'] = kon_op
                spisok[i]['tk']['nachalo'] = nachalo
                spisok[i]['tk']['konec'] = konec
                spisok[i]['tk']['nom_tk'] = nom_tk
                # spisok[i][15] = nach_op
                # spisok[i][16] = kon_op
                # spisok[i][18] = nachalo
                # spisok[i][19] = konec
                # spisok[i][17] = nom_tk
            if flag_marsh == 0:
                s_bd.append('нет маршрутов в тк ' + " " + nn + " " + ima)
            if flag_vrema == 0:
                s_bd.append('нет/не корректное времени в тк ' + " " + nn + " " + ima)
            if flag_mat == 0:
                s_bd.append('не корректно занесен материал на операцию в тк ' + " " + nn + " " + ima)
            if flag_rc == 0:
                s_bd.append(
                    'не корректно занесено имя операции на РЦ 010101, должно быть Резка(чпу) в тк ' + " " + nn + " " + ima)
            if flag_dxf == 0:
                s_bd.append('не занесен DXF на РЦ 010101 где Резка(чпу) в тк ' + " " + nn + " " + ima)
            if flag_seg == 0:
                s_bd.append('не занесено число сегментов на РЦ 010101 где Резка(чпу) в тк ' + " " + nn + " " + ima)
            if flag_docs == 0:
                s_bd.append('отсутствует в бд файл вложения, прикрепелнный в тк ' + " " + nn + " " + ima)
            if flag_rashodnik == 1:
                s_bd.append(f'{nn} {ima} занесен как расходник, материалы в структуре не допустимы')

        for i in range(len(spisok)):
            ur = spisok[i]['level_c']
            ur2 = int(ur) + 1
            if i + 1 > len(spisok) - 1:
                break
            # print(f'{i}--')
            for j in range(i + 1, len(spisok)):
                if spisok[j]['level_c'] < ur2:
                    break
                if spisok[j]['level_c'] == ur2:
                    # print(f'{j}++')
                    if 'tk' in spisok[i] and 'tk' in spisok[j]:

                        if spisok[i]['tk']['nachalo'] != spisok[j]['tk']['konec']:
                            frase = f'Не совдают концовки \n{spisok[i]["data"]["Наименование"]} {spisok[i]["data"]["Наименование"]} (Операция <<{spisok[i]["tk"]["nach_op"]}>> РЦ {spisok[i]["tk"]["nachalo"]}-{CMS.name_RC_by_code_c(spis_rc, spisok[i]["tk"]["nachalo"])})\n ' \
                                    f'и \n{spisok[j]["data"]["Наименование"]} {spisok[j]["data"]["Наименование"]} (Операция <<{spisok[j]["tk"]["kon_op"]}>> РЦ {spisok[j]["tk"]["konec"]}-{CMS.name_RC_by_code_c(spis_rc, spisok[j]["tk"]["konec"])})'
                            rez = CQT.msgboxgYN(
                                frase + f"\n\nВыполнить корректировку концовки для {spisok[j]['data']['Наименование']} "
                                        f"{spisok[j]['data']['Обозначение полное']}"
                                        f" для операции <<{spisok[j]['tk']['kon_op']}>>?\n\n"
                                        f"    РЦ {spisok[j]['tk']['konec']}-{CMS.name_RC_by_code_c(spis_rc, spisok[j]['tk']['konec'])} \n\nбудет заменен на \n\n"
                                        f"        {spisok[i]['tk']['nachalo']}-{CMS.name_RC_by_code_c(spis_rc, spisok[i]['tk']['nachalo'])}")
                            if rez == True:
                                rez2 = self.ispravit_koncovky_tehkart(spisok[j]['data']['Обозначение полное'],
                                                                      spisok[j]['tk']['nom_tk'],
                                                                      spisok[i]['tk']['nachalo'])
                                if rez2 == None:
                                    s_bd.append(frase)
                            else:
                                s_bd.append(frase)
                    else:
                        s_bd.append(f' не сравнить концовки на'
                                    f' {spisok[i]["data"]["Наименование"]} {spisok[i]["data"]["Обозначение полное"]}'
                                    f' и {spisok[j]["data"]["Наименование"]} {spisok[j]["data"]["Обозначение полное"]}')
        CQT.statusbar_text(self)
        return s_bd

    def dob_izd(self, spisok, putt):
        sp_tk = self.nalich_tk(spisok)
        if sp_tk == None:
            return
        if len(sp_tk) > 0:
            viv = ''
            for i in sp_tk:
                viv += i + '\n'
            F.copy_bufer(viv)
            CQT.msgbox("Скопировано в буфер:" + '\n' + viv)
            return
        tabl = self.ui.table_zayavk
        if tabl.columnCount() > 5:
            tabl.clear()
            tabl.clearContents()
            hat_c = ['Файл', 'Изделие', 'Количество', 'К_мат', 'К_врем']
            tabl.setColumnCount(5)
            tabl.setRowCount(0)
            tabl.setHorizontalHeaderLabels(hat_c)
        s = CQT.list_from_wtabl_c(tabl, '', True)

        kol_po_zayavke = ''
        if 'dict_cur_poz_cr_mk' in self.__dict__:
            kol_po_zayavke = str(self.dict_cur_poz_cr_mk["Количество"])
        s.append(
            [putt, f"{spisok[0]['data']['Обозначение полное']} {spisok[0]['data']['Наименование']}", kol_po_zayavke, 1,
             1])
        edit = {3, 4}
        CQT.fill_wtabl_old_c(self, s, tabl, 0, edit, (), (), 2200, True, "")

        try:
            if 'Отдел технолога\В работе' in putt:
                spis_put = putt.split('\\')
                for i, item in enumerate(spis_put):
                    if item == 'В работе':
                        np = spis_put[i + 2]
                        py = spis_put[i + 3]
                        break
        except:
            return
        try:
            for i in range(self.ui.cmb_cr_mk_pr.count()):
                if np in self.ui.cmb_cr_mk_pr.itemText(i):
                    self.ui.cmb_cr_mk_pr.setCurrentIndex(i)
                    break
        except:
            pass
            try:
                for i in range(self.ui.cmb_cr_mk_py.count()):
                    if py in self.ui.cmb_cr_mk_py.itemText(i):
                        self.ui.cmb_cr_mk_py.setCurrentIndex(i)

                        break
            except:
                pass
            return

    def sl_mash_change(self, val):
        self.val_masht = val
        CMS.save_tmp_path('mk_val_masht', str(self.val_masht))
        if self.kpl_mode == 0:
            CMS.oforml_table(self, self.ui.tbl_preview)
        else:
            CMS.oforml_table(self, self.ui.tbl_pl_gaf, self.ui.tbl_pl_gaf_filtr)
            GVKPL.load_svod(self)

    @CQT.onerror
    def action_genetate_res_to_mk(self, *args):
        if not self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Маршрутные карты'):
            CQT.msgbox(f'Не выбрана вкладка МК')
            return
        if self.ui.table_spis_MK.currentRow() == -1:
            CQT.msgbox(f'Не выбрана МК')
            return
        if not CMS.user_access(self.bd_naryad, 'мкарт_меню_обновить_хмл_в_мк', F.user_name()):
            return
        self.create_and_add_res_to_mk()

    @CQT.onerror
    def action_reload_xml_to_mk(self, *args):
        if not self.ui.tabWidget.currentIndex() == CQT.number_table_by_name_c(self.ui.tabWidget, 'Маршрутные карты'):
            CQT.msgbox(f'Не выбрана вкладка МК')
            return
        if self.ui.table_spis_MK.currentRow() == -1:
            CQT.msgbox(f'Не выбрана МК')
            return
        if not CMS.user_access(self.bd_naryad, 'мкарт_меню_обновить_хмл_в_мк', F.user_name()):
            return
        tbl = self.ui.table_spis_MK
        nk_pnom = CQT.num_col_by_name_c(tbl, 'Пномер')
        pnom = int(tbl.item(tbl.currentRow(), nk_pnom).text())
        tmp_putt = CMS.load_tmp_path("tmp_putt")
        path_file = CQT.f_dialog_name(self, 'Выбрать XML', tmp_putt, "Файлы *.xml")
        if path_file == '' or path_file == '.':
            return
        CMS.save_tmp_path("tmp_putt", path_file, True)
        xml = XML.spisok_iz_xml(path_file)
        spis_xml = CMS.podgotovka_xml(self, xml, show_negruz=False)
        if spis_xml == None:
            CQT.msgbox('Файл не корректный')
            return
        bin_xml = F.load_file_convert_to_binary(path_file)

        check_line_db = CSQ.custom_request_c(self.db_resxml, f"""SELECT * FROM xml WHERE Номер_мк == {pnom}""",
                                             one=True)

        if len(check_line_db) > 1:
            CSQ.custom_request_c(self.db_resxml, """UPDATE xml SET(data) = (?);""",
                                 list_of_lists_c=[[bin_xml]])
            CQT.msgbox(f'Успешно обновлено')
        else:
            CSQ.custom_request_c(self.db_resxml, """INSERT INTO  xml(Номер_мк,data,Head) VALUES (?,?,?);""",
                                 list_of_lists_c=[[pnom, bin_xml, 1]])
            CQT.msgbox(f'Успешно добавлено')


app = QtWidgets.QApplication(['', '--no-sandbox'])

myappid = 'Powerz.BAG.SustControlWork.0.0.0'  # !!!

QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
app.setWindowIcon(QtGui.QIcon(os.path.join("icons", "icon.png")))

S = F.scfg('Stile').split(",")
app.setStyle(S[1])

application = mywindow()
from project_cust_38.widget_spy import install_pyqt_event_hook

install_pyqt_event_hook(app)
# =============================================================
if CMS.kontrol_ver(application.versia, 'МКарты') == False:
    quit()
# =============================================================

application.showMaximized()

sys.exit(app.exec())
# pyinstaller.exe --onefile --icon=1.ico --noconsole MKart.py
