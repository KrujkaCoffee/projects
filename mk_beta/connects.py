from __future__ import annotations

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import project_cust_38.Zamechaniya as ZMCH
import obespechenie as OBSP
import industrial_capacity as IND
import Selector_conversation as SLCT
import calculate_vo as CVO
import kal_plan as KPL
import gui_kal_plan as GKPL
import gui_vol_plan as GVKPL
import pl_user_fiters as KPLUF
import interaction_googlesheets
import state_prod as STATE
import chpy_calcs as CHPY
import make_poz_plan as POZPL
import recalc_norm as RECLC
import equipment_rc as EQRC
import tabel_edit as TABEL
import tatkuz_molding as TTKZ
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from MKart import mywindow


def actions(self: mywindow):
    ui = self.ui
    ui.test_action_1.triggered.connect(self.test_action_1)
    ui.action_XML.triggered.connect(self.viborXML)
    # ui.action_JSON_p_fabr.triggered.connect(self.export_json)
    ui.action_generate_res_erp.triggered.connect(self.export_json_kotl)
    ui.action_opn_dir_mk.triggered.connect(self.open_zayavk)
    # ui.action_res_ERP.triggered.connect(lambda _, x=self: EXPD.export_res_erp(x))  # это файлами эксель когда выгружали с самого начала,для загрузки ресурсной. Не используется
    ui.action4_px.triggered.connect(lambda: self.sl_mash_change(4))
    ui.action6_px.triggered.connect(lambda: self.sl_mash_change(6))
    ui.action8_px.triggered.connect(lambda: self.sl_mash_change(8))
    ui.action10_px.triggered.connect(lambda: self.sl_mash_change(10))
    ui.action12_px.triggered.connect(lambda: self.sl_mash_change(12))
    ui.action14_px.triggered.connect(lambda: self.sl_mash_change(14))
    ui.action16_px.triggered.connect(lambda: self.sl_mash_change(16))
    ui.action18_px.triggered.connect(lambda: self.sl_mash_change(18))

    ui.action_reload_xml_to_mk.triggered.connect(self.action_reload_xml_to_mk)
    ui.action_genetate_res_to_mk.triggered.connect(self.action_genetate_res_to_mk)
    ui.action_download_xml.triggered.connect(lambda _, x=self: CMS.save_xml(x))
    ui.action_xml_calc_weights.triggered.connect(self.calc_xml_res)
    ui.action_xml_add_xml.triggered.connect(self.add_xml_to_mk)
    ui.action_clear_xml.triggered.connect(self.del_xml_from_mk)



def combobox(self: mywindow):
    ui = self.ui
    ui.cmb_pl_tabel_place.activated[int].connect(self.cmb_pl_tabel_place)
    ui.cmb_year_for_select_tkp.activated[int].connect(self.cmb_year_for_select_tkp)
    ui.cmb_cr_mk_pr.activated[int].connect(self.cmb_cr_mk_select_pr)
    ui.cmb_cr_mk_py.activated[int].connect(self.cmb_cr_mk_select_py)
    ui.cmb_cr_mk_poz.activated[int].connect(self.cmb_cr_mk_select_poz)
    ui.cmb_tkp_otv_techn.activated[int].connect(lambda: CVO.cmb_tkp_otv_techn(self))
    ui.cmb_tabeli.activated[int].connect(lambda: TABEL.cmb_select_month(self))
    CQT.freeze_mouse_wheel(ui.cmb_vid_izd)
    ui.cmb_vid_izd.activated.connect(lambda: CVO.cmb_select_vid_izd(self))
    ui.cmb_schems.activated[int].connect(lambda _, x=self: IND.select_schema(x))
    ui.cmb_tip_mk.activated[int].connect(self.cmb_tip_click)
    ui.pl_cmb_filtrs.activated[int].connect(lambda: KPLUF.apply_select_filtr(self))
    ui.cmb_select_napr.activated[int].connect(lambda: KPL.update_graf_site_and_get_local(self))


def check_box(self: mywindow):
    ui = self.ui
    ui.chk_kpl_zaversch.blockSignals(True)
    ui.chk_kpl_zaversch.setChecked(False)
    ui.chk_kpl_zaversch.blockSignals(False)
    ui.chk_kpl_groups.blockSignals(True)
    ui.chk_kpl_groups.setChecked(CMS.load_tmp_stukt('chk_kpl_groups', False))
    ui.chk_kpl_groups.blockSignals(False)
    ui.chk_kpl_zaversch.clicked.connect(lambda: KPL.set_params_kpl(self))
    ui.chk_kpl_groups.clicked.connect(lambda: KPL.set_groups_kpl(self))
    ui.chk_paint_dates.clicked.connect(lambda: KPL.set_chk_paint_dates(self))
    ui.chk_schemas_show_alias.clicked.connect(lambda _, x=self: IND.select_schema(x))
    ui.chk_schemas_show_position.clicked.connect(lambda _, x=self: IND.select_schema(x))
    ui.chk_schemas_show_fio.clicked.connect(lambda _, x=self: IND.select_schema(x))
    ui.chk_autorepeat_update_fact.clicked.connect(lambda: KPL.chk_autorepeat_update_fact(self))
    ui.chk_lump_production_method.clicked.connect(lambda: TTKZ.chk_lump_production_method(self))
    ui.chk_link_gant_blocks.clicked.connect(lambda: KPL.save_val_chk_link_gant_blocks(self))



def calendar(self: mywindow):
    ui = self.ui
    # ================CALENDAR===================================
    ui.cld_obespechenie.clicked.connect(lambda _, x=self: OBSP.data_obespech(x))
    # ===========================================================


def date_edit(self: mywindow):
    ui = self.ui
    ui.de_vol_pl.dateChanged.connect(lambda: GVKPL.save_diapazon_month(self))
    ui.de_vol_pl_end.dateChanged.connect(lambda: GVKPL.save_diapazon_month(self))


def tree(self: mywindow):
    ui = self.ui
    # ==============TREE=========================================
    ui.tree_fields.doubleClicked.connect(lambda: GKPL.tree_fields_dbl_clck(self))
    # ==================================================================


def line_edit(self: mywindow):
    ui = self.ui
    ui.le_pl_find_field.textChanged.connect(lambda: KPL.find_field_reset(self))
    ui.le_schema_font_height.textChanged.connect(lambda _, x=self: IND.select_schema(x))
    self.ui.lineEdit_naim.textEdited.connect(self.poisk_nn)
    self.ui.lineEdit_nom_n.textEdited.connect(self.poisk_nn)
    self.ui.lineEdit_primech.textEdited.connect(self.poisk_nn)
    self.ui.le_edit_local_gant_full_etap.textEdited.connect(lambda: GKPL.le_edit_local_gant_full_etap(self))


def btns(self: mywindow):
    ui = self.ui

    ui.btn_recalc_gant_forced.clicked.connect(lambda: GKPL.recalc_gant_forced(self))
    ui.btn_pl_mode_upd.clicked.connect(lambda: GVKPL.pl_mode_upd(self))
    ui.btn_set_start_end_dates_clnd.clicked.connect(lambda: GKPL.set_start_end_dates_clnd(self))
    ui.btn_pickup_date_nach.clicked.connect(lambda: GKPL.pickup_date_nach(self))
    ui.btn_pickup_date_kon.clicked.connect(lambda: GKPL.pickup_date_kon(self))
    ui.btn_clear_edit_local_gant_nach.clicked.connect(lambda: GKPL.clear_edit_local_gant_nach(self))
    ui.btn_clear_edit_local_gant_kon.clicked.connect(lambda: GKPL.clear_edit_local_gant_kon(self))
    ui.btn_set_start_end_dates.clicked.connect(lambda: GKPL.set_start_end_dates(self))
    ui.btn_update_dates_obesp.clicked.connect(lambda: GKPL.update_dates_obesp(self))
    ui.btn_tree_pl_unwrap_all.clicked.connect(GKPL.btn_tree_pl_unwrap_all)
    ui.btn_tree_pl_wrap_all.clicked.connect(GKPL.btn_tree_pl_wrap_all)
    ui.pushButton_up_row.clicked.connect(lambda: self.edit_strukt_move_row('up'))
    ui.pushButton_down_row.clicked.connect(lambda: self.edit_strukt_move_row('down'))
    ui.pushButton_push_strukt_into_db_dse.clicked.connect(self.push_strukt_into_db_dse)
    ui.btn_get_res_as_file.clicked.connect(self.get_res_as_file)
    ui.btn_adapt_pl_with_gant_after_right.clicked.connect(
        lambda: POZPL.adapt_pl_with_gant(self, 'after_right'))
    ui.btn_adapt_pl_with_gant_right.clicked.connect(lambda: POZPL.adapt_pl_with_gant(self, 'right'))
    ui.btn_adapt_pl_with_gant.clicked.connect(lambda: POZPL.adapt_pl_with_gant(self))

    ui.btn_show_hide_tree_fields.clicked.connect(lambda: GKPL.show_hide_tree_fields(self))
    ui.btn_cld_pl_apply_filtr_month.clicked.connect(lambda: POZPL.cld_pl_apply_filtr_month(self))


    ui.btn_set_dates_etaps.clicked.connect(lambda: GKPL.set_dates_etaps(self))


    ui.btn_pull_poz_del_all.clicked.connect(lambda: POZPL.btn_pull_poz_del_all(self))
    ui.btn_pull_poz_del.clicked.connect(lambda: POZPL.btn_pull_poz_del(self))
    ui.btn_pull_poz_add.clicked.connect(lambda: POZPL.btn_pull_poz_add(self))
    ui.btn_pull_poz_add_all.clicked.connect(lambda: POZPL.btn_pull_poz_add_all(self))
    ui.btn_pull_poz_update.clicked.connect(lambda: POZPL.btn_pull_poz_update(self))
    ui.btn_pull_all_update.clicked.connect(lambda: POZPL.btn_pull_all_update(self))

    ui.btn_clear_filtr.clicked.connect(lambda: KPL.btn_clear_filtr(self))
    ui.btn_copy_excel.clicked.connect(lambda: KPL.copy_excel_local(self))
    ui.btn_exel_svod.clicked.connect(lambda: KPL.copy_exel_svod(self))
    ui.btn_add_rm.clicked.connect(lambda _, x=self: IND.add_rm(x))

    ui.btn_obespechenie_spis_po_mk.clicked.connect(lambda _, x=self: OBSP.spis_obesp_po_mk(x))
    ui.btn_obespechenie_zapisat.clicked.connect(lambda _, x=self: OBSP.zapisat(x))
    ui.btn_add_zamech.clicked.connect(lambda _, x=self: ZMCH.add_zamech(x))
    ui.btn_edit_zamech.clicked.connect(lambda _, x=self: ZMCH.load_zamech_to_edit(x))
    # ui.btn_add_v_planetapi.clicked.connect(self.add_v_planetapi)
    ui.btn_zaversh.clicked.connect(self.zaversh_mkards)

    ui.btn_obnov_po_strukt.clicked.connect(self.obnov_po_strukt)
    ui.btn_obnovit_naruadi_po_mk.clicked.connect(self.obnovit_naruadi_po_mk)

    ui.btn_edit_res_xml.clicked.connect(self.edit_res_xml)
    ui.btn_generate_precsv_tree.clicked.connect(lambda: CHPY.generate_precsv_tree(self))
    ui.btn_generate_txt_res.clicked.connect(self.generate_txt_res)
    ui.btn_tkp_add_to_plan.clicked.connect(lambda: CVO.btn_tkp_add_to_plan(self))
    ui.btn_close_all_groups.clicked.connect(lambda: KPL.close_all_groups(self))
    ui.btn_korr_nom.clicked.connect(self.btn_korr_nom)
    ui.btn_del_poz_nom.clicked.connect(self.del_nom)
    ui.pushButton_ass_nomen_MK.clicked.connect(self.ass_dse_to_mk)
    # CQT.set_color_sort_cell_table_c(butt_vib_nomen)

    ui.btn_obnov_pr.clicked.connect(self.obn_spis_pr)
    ui.btn_select_poz_cr_mk_pr.clicked.connect(self.select_poz_cr_mk_pr)
    ui.pushButton_create_MK.clicked.connect(self.create_mk)
    ui.pushButton_create_mk_clear.clicked.connect(self.clear_mk)

    ui.pushButton_create_koren.clicked.connect(self.add_gl_uzel)

    ui.pushButton_create_vxodyash.clicked.connect(self.add_vhod)

    ui.pushButton_create_paralel.clicked.connect(self.add_paral)

    ui.pushButton_create_udalituzel.clicked.connect(self.del_uzel)

    ui.btn_save_cust_drevo.clicked.connect(self.save_cust_drevo)

    ui.btn_load_cust_drevo.clicked.connect(self.load_cust_drevo)

    ui.pushButton_add_v_bd.clicked.connect(self.dob_izd_k_bd)

    ui.pushButton_save_MK.clicked.connect(self.save_mk)

    ui.pushButton_add_v_MK.clicked.connect(self.add_v_mk)

    ui.pushButton_add_v_bd_2.clicked.connect(self.add_v_nomenkl)

    ui.btn_vigruzka_norm.clicked.connect(self.vigruzka_norm)

    ui.btn_vigruzka_norm_mat.clicked.connect(self.vigruzka_norm_mat)

    self.but_ass_brak_to_mk = ui.pushButton_ass_brak_to_mk
    self.but_ass_brak_to_mk.clicked.connect(self.ass_brak_to_mk)
    ui.pushButton_ass_brak_to_mk.setEnabled(False)

    self.but_open_mk = ui.pushButton_open_mk
    self.but_open_mk.clicked.connect(self.open_mk)

    self.but_close_mk = ui.pushButton_close_mk
    self.but_close_mk.clicked.connect(self.close_mk)

    self.but_del_mk = ui.pushButton_del_mk
    self.but_del_mk.clicked.connect(self.del_mk)

    ui.pushButton_clear_label.clicked.connect(self.del_ass)
    ui.pushButton_clear_label.setToolTip('Удалить ассоциации с актами о браке')

    ui.btn_update_norm.clicked.connect(lambda _, x='vrem': self.update_norm(x))
    ui.btn_update_norm_prof.clicked.connect(lambda _, x='prof': self.update_norm(x))
    ui.btn_update_norm_rc.clicked.connect(lambda _, x='rc': self.update_norm(x))
    ui.btn_update_norm_mat.clicked.connect(lambda _, x='mat': self.update_norm(x))

    ui.btn_selector_add.clicked.connect(lambda _, x=self: SLCT.add_zamech(x))
    ui.btn_selector_edit.clicked.connect(lambda _, x=self: SLCT.edit_zamech(x))
    ui.btn_pl_add_poz.clicked.connect(lambda _, x=self: KPL.btn_pl_add_poz_click(x))
    ui.btn_pl_ok_add_poz.clicked.connect(lambda _, x=self: KPL.btn_pl_ok_add_poz_click(x))
    ui.btn_pl_edit_poz.clicked.connect(lambda _, x=self: KPL.btn_pl_edit_poz_click(x))

    ui.btn_settings.clicked.connect(lambda _, x=self: KPL.btn_pl_settings(x))
    ui.btn_config_fields.clicked.connect(KPL.btn_config_fields)
    ui.btn_config_limit_gant.clicked.connect(KPL.btn_config_limit_gant)
    ui.btn_pl_mode.clicked.connect(lambda _, x=self: KPL.btn_pl_mode(x))
    ui.btn_pull_poz_show.clicked.connect(lambda _, x=self: KPL.btn_pull_poz_show(x))
    # ui.btn_pull_poz_show.setEnabled(False)

    ui.btn_fdate_res_erp.clicked.connect(self.clk_fdate_res_erp)
    ui.btn_edit_local_gant_left.clicked.connect(lambda: GKPL.move_left(self))
    ui.btn_edit_local_gant_right.clicked.connect(lambda: GKPL.move_right(self))
    ui.btn_show_svod_as_tbl.clicked.connect(GVKPL.show_svod_tbl)
    ui.btn_pl_graf_context_as_tbl.clicked.connect(KPL.pl_graf_context_as_tbl)
    ui.btn_pl_tabel.clicked.connect(lambda: KPL.show_tabel(self))
    ui.btn_load_file_mk_founfing.clicked.connect(self.load_file_mk_founfing)
    ui.btn_select_nom_jur_vneplan.clicked.connect(self.select_nom_jur_vneplan)
    ui.btn_show_file_founding_mk.clicked.connect(self.show_file_founding_mk)
    ui.btn_pl_open_dir.clicked.connect(lambda: KPL.btn_pl_open_dir(self))
    ui.btn_pl_add_trbl.clicked.connect(lambda: KPL.btn_pl_add_trbl(self))
    ui.btn_pl_load_norm.clicked.connect(lambda: KPL.btn_pl_load_norm(self))
    ui.btn_norm_fact_by_opers.clicked.connect(lambda: KPL.btn_norm_fact_by_opers(self))
    ui.btn_edit_zp_kpl.clicked.connect(lambda: KPL.btn_edit_zp_kpl(self))
    ui.btn_pl_reload.clicked.connect(lambda: KPL.update_plan_main_tbl(self))
    ui.btn_pl_send_dates_into_ERP.clicked.connect(lambda: KPL.send_into_ERP(self))
    ui.btn_pl_send_dates_into_ERP_from_exel.clicked.connect(lambda: KPL.pl_send_dates_into_ERP_from_exel(self))
    ui.btn_select_exel_file.clicked.connect(lambda: KPL.select_exel_file(self))

    ui.btn_pl_kopy_norm_etap_buff.clicked.connect(lambda: KPL.btn_pl_kopy_norm_etap_buff(self))


    ui.pl_btn_add_new_filtr.clicked.connect(lambda: KPLUF.add_pl_user_filtrs(self))
    ui.btn_tkp_load_strukt.clicked.connect(lambda: CVO.btn_tkp_load_strukt(self))

    ui.btn_tkp_date_res.clicked.connect(lambda: CVO.btn_tkp_date_res(self))
    ui.btn_save_pl.clicked.connect(lambda: POZPL.save_kpl_plan(self))
    ui.btn_load_pl.clicked.connect(lambda: POZPL.load_poz_pl_from_db(self))
    ui.btn_save_pl_local.clicked.connect(lambda: POZPL.save_local_pl(self))
    ui.btn_load_pl_local.clicked.connect(lambda: POZPL.load_local_pl(self))
    ui.btn_set_vnepl.clicked.connect(lambda: POZPL.btn_set_poz_vnepl(self))

    ui.btn_pl_load_google_sheets.clicked.connect(lambda: interaction_googlesheets.get_g_plan(self))
    ui.btn_pl_fill_google_sheets.clicked.connect(lambda: interaction_googlesheets.fill_g_plan(self))
    ui.btn_pl_set_stat_closed.clicked.connect(lambda: KPL.set_stat_closed(self))
    ui.btn_pl_cr_mk.clicked.connect(lambda: KPL.pl_cr_mk(self))
    ui.btn_pl_cr_dir_poz.clicked.connect(lambda: KPL.pl_cr_dir_poz(self))
    ui.btn_apply_recalc_dates_etaps.clicked.connect(lambda: KPL.apply_recalc_dates_etaps(self))
    ui.btn_recalc_fr.clicked.connect(lambda: RECLC.show_fr(self))
    ui.btn_recalc_norm_ok.clicked.connect(lambda: RECLC.recalc_opers_norm(self))
    ui.btn_add_equipment.clicked.connect(lambda: EQRC.tbl_eq_add_new_row(self))
    ui.btn_synch_erp.clicked.connect(lambda: KPL.check_kpl_by_erp(self))

    ui.btn_recalc_and_fill_fact_rab.clicked.connect(lambda: KPL.recalc_and_fil_fact(self))
    ui.btn_apply_diap_dates_to_sb_in_tbl.clicked.connect(lambda: POZPL.apply_diap_dates_to_sb_in_tbl(self))
    ui.btn_plan_on_of_day_edit_frame.clicked.connect(lambda: KPL.plan_on_of_day_edit_frame(self))
    ui.btn_plan_day_edit_recalc.clicked.connect(lambda: KPL.plan_day_edit_recalc(self))
    ui.btn_plan_day_edit_set_weekend.clicked.connect(lambda: KPL.plan_day_edit_set_weekend(self))
    ui.btn_show_gui_res.clicked.connect(self.laod_res_board)
    ui.btn_apply_data_mold.clicked.connect(lambda: TTKZ.apply_new_or_edit_order(self))
    ui.btn_cancel_data_mold.clicked.connect(lambda: TTKZ.cancel_new_or_edit_order(self))
    ui.btn_sand_data.clicked.connect(lambda: TTKZ.add_sand_data(self))
    ui.btn_add_row_mold_tch.clicked.connect(lambda: TTKZ.add_row_mold_tch(self))
    ui.btn_del_row_mold_tch.clicked.connect(lambda: TTKZ.del_row_mold_tch(self))
    ui.btn_upload_1c_mold_tch.clicked.connect(lambda: TTKZ.upload_1c_mold(self))
    ui.btn_mat_mold_calc.clicked.connect(lambda: TTKZ.mat_mold_calc(self))
    ui.btn_res_product.clicked.connect(lambda: TTKZ.create_res_product(self))
    ui.btn_apply_next_stage.clicked.connect(lambda: TTKZ.apply_next_stage(self))


def tabs(self: mywindow):
    ui = self.ui
    ui.tabWidget.currentChanged[int].connect(self.tab_click)
    ui.tabWidget_10.currentChanged[int].connect(self.tab_click10)
    ui.tabWidget_2.currentChanged[int].connect(self.tab_click2)
    ui.tabWidget_3.currentChanged[int].connect(self.tab_mk_click)
    ui.tabWidget_4.currentChanged[int].connect(self.tab_zagruzka_rc)
    ui.tab_addit_info_poz_gant.currentChanged[int].connect(self.tab_addit_info_poz_gant_click)
    ui.tabW_rab_places.currentChanged[int].connect(self.tabW_rab_places_click)
    ui.tab_rs_tch.currentChanged[int].connect(lambda: TTKZ.tab_rs_tch_currentChanged(self))
    ui.tab_pl_graf_context.currentChanged[int].connect(lambda: GVKPL.click_tab_pl_graf_context(self))


def tbls(self: mywindow):
    ui = self.ui
    ui.tbl_select_etap_edit_poz.clicked.connect(KPL.fnc_click_load_tbl_edit_poz)
    ui.tbl_data_mold.cellChanged.connect(lambda row, col: TTKZ.data_mold_cellchanged(self, row, col))
    ui.tbl_data_mold_tch.cellChanged.connect(lambda row, col: TTKZ.mold_tch_cellchanged(self, row, col))
    ui.tbl_data_mold_tch_res_product.cellChanged.connect(
        lambda row, col: TTKZ.mold_tch_res_product_cellchanged(self, row, col))
    ui.tbl_data_mold_tch.itemSelectionChanged.connect(lambda: TTKZ.mold_tch_itemSelectionChanged(self))
    ui.tbl_data_mold_tch_res_product.itemSelectionChanged.connect(
        lambda: TTKZ.mold_tch_res_product_itemSelectionChanged(self))
    ui.tbl_list_orders_mold.itemSelectionChanged.connect(lambda: TTKZ.select_order(self))
    ui.tbl_state.clicked.connect(lambda: STATE.select_field_tbl_state(self))
    ui.tbL_tkp_list.cellDoubleClicked[int, int].connect(self.CVO_path_kd_dbl_clk)
    ui.tbL_tkp_list.itemSelectionChanged.connect(lambda: CVO.load_vid_izd(self))
    ui.tbl_selector_proj_view.clicked.connect(self.SLCT_click)
    ui.tbl_selector_proj_view.cellChanged[int, int].connect(self.SLCT_edit_primech)
    ui.tbl_selector_proj_view_zamech.cellDoubleClicked[int, int].connect(self.SLCT_edit_zamech_from_view)
    ui.tbl_selector_proj_view.itemSelectionChanged.connect(self.SLCT_selector_proj_view_itemSelection)
    ui.tbl_selector_proj_view.cellDoubleClicked[int, int].connect(self.SLCT_add_new_zamech)
    ui.tbl_selector.cellDoubleClicked[int, int].connect(self.SLCT_select_zamech)
    self.tabl_nomenk = ui.table_nomenkl
    self.tabl_nomenk.cellDoubleClicked[int, int].connect(self.zapusk_docs)
    ui.tbl_obespechenie.cellDoubleClicked[int, int].connect(self.OBSP_select_obesp_po_mk_from_table)
    ui.tbl_rc.cellChanged[int, int].connect(self.IND_cellChanged)
    CQT.set_color_sort_cell_table_c(self.tabl_nomenk)
    self.tabl_nomenk.setSelectionBehavior(1)
    self.tabl_nomenk.setSelectionMode(1)
    self.tabl_mk = ui.table_spis_MK
    CQT.set_color_sort_cell_table_c(self.tabl_mk)
    self.tabl_mk.setSelectionBehavior(1)
    self.tabl_mk.setSelectionMode(1)

    CQT.connect_cell_edit(self.tabl_mk, self.corr_mk)

    # self.tabl_mk.cellActivated[int, int].connect(self.corr_mk)
    self.tabl_mk.clicked.connect(self.spis_MK_clck)
    self.tabl_brak = ui.table_brak
    CQT.set_color_sort_cell_table_c(self.tabl_brak)
    self.tabl_brak.setSelectionBehavior(1)
    self.tabl_brak.setSelectionMode(1)
    self.tabl_brak.clicked.connect(self.click_brak)
    self.tabl_brak.doubleClicked.connect(self.tabl_brak_dbl_clk)

    ui.table_spis_MK.setSelectionBehavior(1)
    ui.table_spis_MK.setSelectionMode(1)
    CQT.set_color_sort_cell_table_c(ui.table_spis_MK)
    ui.tbl_poz_from_exel.itemSelectionChanged.connect(lambda: GKPL.fill_select_poz_exel(self))
    ui.tbl_kal_pl.itemSelectionChanged.connect(lambda: KPL.clck_tbl_kal_pl_tbl(self))
    ui.tbl_preview.itemSelectionChanged.connect(
        lambda x=self, y=ui.tbl_preview: KPL.clck_tbl_preview(x, y))
    ui.tbl_pl_gaf.itemSelectionChanged.connect(
        lambda x=self, y=ui.tbl_pl_gaf: KPL.clck_tbl_pl_gaf(x, y))
    ui.tbl_pl_gaf.verticalHeader().setSectionsClickable(True)
    ui.tbl_pl_gaf.verticalHeader().sectionDoubleClicked[int].connect(
        lambda logicalIndex: KPL.clck_tbl_verticalHeader(self, logicalIndex))
    ui.tbl_kal_pl.horizontalHeader().sectionResized.connect(
        lambda i, j, k: CMS.on_section_resized(self, i, j, k))
    ui.tbl_preview.horizontalHeader().sectionClicked.connect(lambda ind: GKPL.tbl_preview_on_header_click(self, ind))

    # ui.tbl_kal_pl.clicked.connect(lambda : KPL.clck_tbl_kal_pl_tbl(self))
    ui.tbl_kal_pl.doubleClicked.connect(lambda: KPL.doubleclck_tbl_kal_pl(self))
    ui.tbl_rc.itemSelectionChanged.connect(self.clck_tbl_rc)
    ui.tbl_rc.clicked.connect(self.clck_tbl_rc)
    ui.tbl_rc.doubleClicked.connect(lambda _, x=self: IND.select_schema_dbl_clk(x))
    ui.tbl_pl_add_poz.doubleClicked.connect(lambda: KPL.dbl_clk_tbl_add_poz(self))
    ui.tbl_tabeli.doubleClicked.connect(lambda: IND.set_old_val(self))
    ui.tbl_tabeli.clicked.connect(lambda: IND.set_tooltip_val(self))
    ui.tbl_preview.doubleClicked.connect(lambda: KPL.show_fact_etap_by_current_day(self))
    ui.tbl_pl_gaf.horizontalScrollBar().valueChanged.connect(
        ui.tbl_pl_gaf_filtr.horizontalScrollBar().setValue)
    ui.tbl_kal_pl.horizontalScrollBar().valueChanged.connect(
        ui.tbl_filtr_kal_pl.horizontalScrollBar().setValue)


    ui.tbl_kal_pl.horizontalHeader().setMouseTracking(True)
    ui.tbl_kal_pl.setMouseTracking(True)
    ui.tbl_kal_pl.mouseMoveEvent = self.tbl_kal_pl_header_mouseMoveEvent

    ui.table_spis_MK.horizontalScrollBar().valueChanged.connect(
        ui.tbl_filtr_mk.horizontalScrollBar().setValue)

    ui.tbl_pl_gaf.doubleClicked.connect(lambda: GVKPL.dbl_clk_select_etap(self))
    ui.tbl_preview.setMouseTracking(True)
    ui.tbl_preview.mouseMoveEvent = self.tbl_preview_mouseMoveEvent
    ui.tbl_pl_gaf.setMouseTracking(True)
    ui.tbl_pl_gaf.mouseMoveEvent = self.tbl_pl_gaf_mouseMoveEvent
    CQT.connect_cell_edit(ui.tbl_pull_etaps, POZPL.corr_tbl_pull_etaps)
    ui.tbl_cld_plan_workforce.clicked.connect(lambda: POZPL.select_month(self))
    ui.tbl_cld_plan_workforce.doubleClicked.connect(lambda: POZPL.reselect_month(self))
    ui.tbl_equipment.cellChanged[int, int].connect(lambda: EQRC.tbl_eq_change_cell(self))

    ui.tbl_pull_poz.cellChanged[int, int].connect(lambda: POZPL.edit_handle_pl(self))
    ui.tbl_pull_poz.doubleClicked.connect(lambda: POZPL.select_poz_from_pull(self))
    ui.tbl_addit_info_poz_gant.doubleClicked.connect(lambda: GKPL.dbl_click_etap_addit_info_poz_gant(self))


def connect_objects(self: mywindow):
    calendar(self)
    btns(self)
    tree(self)
    line_edit(self)
    tabs(self)
    tbls(self)
    combobox(self)
    date_edit(self)
    check_box(self)
    actions(self)
