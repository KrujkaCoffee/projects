from __future__ import annotations

import sys
if __name__ == "__main__":
    quit()
import project_cust_38.Cust_Qt as CQT
from project_cust_38.sub_mes.resource_planning.dataClass_res_pl import data_app as DTCLS
from project_cust_38.sub_mes.resource_planning.clses import Type_entitys
from project_cust_38.Cust_Functions import get_all_attrs
import project_cust_38.sub_mes.resource_planning.clses as CLSS
import project_cust_38.Cust_overlay as COV

DTSUB = DTCLS.module_manage_sub_app
from typing import  TYPE_CHECKING
from functools import partial
if TYPE_CHECKING:
    from project_cust_38.sub_mes.resource_planning.manage_res_pl import (Plwindow,Type_entity)
    from project_cust_38.sub_mes.resource_planning.manage_res_pl import Plwindow


def toggle_focus(new_focus):
    DTSUB.sub_self.ui.fr_cont_event.setVisible(False)
    DTSUB.sub_self.ui.fr_cont_res.setVisible(False)
    if DTSUB.info_o:
        DTSUB.info_o.clear()
    new_focus.setVisible(True)

def toggle_settings_mode(sub_self: Plwindow,mode:Type_entity|None=None):
    if DTSUB.tmp_overlay:
        DTSUB.tmp_overlay.clear_background()
    if mode is None or sub_self.ui.fr_settings.isVisible():
        sub_self.ui.fr_work.setVisible(True)
        sub_self.ui.fr_settings.setVisible(False)
        sub_self.ui.btn_shab_extit.setVisible(False)
        sub_self.ui.btn_shab_res.setVisible(True)
        sub_self.ui.btn_shab_eve.setVisible(True)
        if DTSUB.info_o:
            DTSUB.info_o.clear()
    else:
        sub_self.ui.fr_work.setVisible(False)
        sub_self.ui.fr_settings.setVisible(True)
        sub_self.ui.fr_cont_event.setVisible(False)
        sub_self.ui.fr_cont_res.setVisible(False)
        sub_self.ui.btn_shab_extit.setVisible(True)
        sub_self.ui.btn_shab_res.setVisible(False)
        sub_self.ui.btn_shab_eve.setVisible(False)



    DTSUB.current_settings_mode = mode
    if mode:
        sub_self.ui.label.setText(mode.text)
    else:
        sub_self.ui.label.setText('')

    sub_self.list_shablons_reload()



@CQT.onerror()
def _on_focus_changed(self:Plwindow, old_widget, new_widget, *args):
    def activate_focus(self):
        if DTCLS.curren_frame is DTSUB.fr_ev:
            toggle_focus(self.ui.fr_cont_event)
            DTSUB.current_focus_type = CLSS.FocusTypes.EVENT
            self.ui.fr_orn_vl.setHidden(False)
            self.ui.fr_orn_vr.setHidden(True)
            self.ui.fr_orn_g_r.setHidden(False)
            self.ui.fr_orn_g_l.setHidden(True)

            if DTSUB.tmp_overlay:
                DTSUB.tmp_overlay.clear_background()
            DTSUB.tmp_overlay = COV.apply_blur(self.ui.fr_resources, radius=1, interactive=True)


        if DTCLS.curren_frame is DTSUB.fr_res:
            toggle_focus(self.ui.fr_cont_res)
            DTSUB.current_focus_type = CLSS.FocusTypes.RESOURCE
            self.ui.fr_orn_vl.setHidden(True)
            self.ui.fr_orn_vr.setHidden(False)
            self.ui.fr_orn_g_r.setHidden(True)
            self.ui.fr_orn_g_l.setHidden(False)

            if DTSUB.tmp_overlay:
                DTSUB.tmp_overlay.clear_background()
            DTSUB.tmp_overlay = COV.apply_blur(self.ui.fr_events, radius=1, interactive=True)
    # Проверяем, что новый виджет находится внутри нашего фрейма
    if new_widget and new_widget.parent().__class__ == CQT.QtWidgets.QFrame:
        new_fr = new_widget.parent()
        if new_fr == DTCLS.curren_frame:
            return
        DTCLS.curren_frame = new_fr
        activate_focus(self)

def prepare_ui(sub_self: Plwindow):
    sub_self.ui.fr_cont_event.setVisible(False)
    sub_self.ui.fr_cont_res.setVisible(False)
    sub_self.ui.fr_settings.setVisible(False)
    sub_self.ui.btn_shab_extit.setVisible(False)
    list_sbjpl = [_.name for _ in CLSS.SubjectsPl.get_all()]
    toggle_settings_mode(sub_self)
    fill_list_subj_pl(sub_self)


def fill_list_subj_pl(sub_self):
    cmb:CQT.QtWidgets.QComboBox = sub_self.ui.cmb_select_sbjpl
    cmb.blockSignals(True)
    CQT.fill_list_combobx(sub_self,cmb,
                          [_.text for _ in CLSS.SubjectsPl.get_all()],
                          list_tooltip=   [_.descr for _ in CLSS.SubjectsPl.get_all()],
                          first_void=False,
                          list_data= [_.name for _ in CLSS.SubjectsPl.get_all()],
                          current_text=DTSUB.subj_pl.text
                          )
    cmb.blockSignals(False)



def load_connects(sub_self: Plwindow):
    # Подключаем глобальный сигнал изменения фокуса
    sub_self._on_focus_changed = _on_focus_changed
    CQT.QApplication.instance().focusChanged.connect(partial(sub_self._on_focus_changed,sub_self))

    load_tbls(sub_self)
    load_frs(sub_self)
    load_btns(sub_self)
    load_cmbs(sub_self)


def load_frs(sub_self):
    DTSUB.fr_ev = sub_self.ui.fr_events
    DTSUB.fr_res = sub_self.ui.fr_resources

def load_tbls(sub_self):
    sub_self.ui.tbl_s_list_shabl.clicked.connect(lambda: sub_self.select_shablon())
    sub_self.ui.tbl_resuorces.clicked.connect(lambda: sub_self.select_resource())
    sub_self.ui.tbl_events.clicked.connect(lambda: sub_self.select_event())
    sub_self.ui.tbl_cross.clicked.connect(lambda: sub_self.select_cross())
    sub_self.ui.tbl_gr.clicked.connect(lambda: sub_self.select_graph())
    sub_self.ui.tbl_gr_v_sub.clicked.connect(lambda: sub_self.select_graph_sub_tbl())

    sub_self.ui.tbl_gr_v_sub.horizontalHeader().sortIndicatorChanged.connect(sub_self.on_sort_changed)
    sub_self.ui.tbl_gr_v_sub.model().layoutChanged.connect(sub_self.on_layout_changed)
def load_cmbs(sub_self):
    sub_self.ui.cmb_select_sbjpl.currentIndexChanged.connect(lambda: sub_self.select_sbjpl())
    sub_self.ui.cmb_type_gr.currentIndexChanged.connect(lambda: sub_self.select_report())
def load_btns(sub_self):
    sub_self.ui.btn_shab_res.clicked.connect(lambda: toggle_settings_mode(sub_self,Type_entitys.Res))
    sub_self.ui.btn_shab_eve.clicked.connect(lambda: toggle_settings_mode(sub_self,Type_entitys.Eve))
    sub_self.ui.btn_shab_extit.clicked.connect(lambda: toggle_settings_mode(sub_self))
    sub_self.ui.btn_s_shab_new.clicked.connect(sub_self.new_shablon)
    sub_self.ui.btn_add_new_res.clicked.connect(sub_self.new_res)
    sub_self.ui.btn_add_new_eve.clicked.connect(sub_self.new_eve)
    sub_self.ui.btn_s_shab_save.clicked.connect(sub_self.s_shab_save)
    sub_self.ui.btn_cross_add.clicked.connect(sub_self.cross_add)
    sub_self.ui.btn_cross_show_all.clicked.connect(sub_self.cross_show_all)
    sub_self.ui.btn_report_preset.clicked.connect(sub_self.report_preset)
    # btn_info_new_attr -> CLSS.Info

def key_release_event(sub_self:Plwindow, key:int, mod:CQT.QtCore.Qt.KeyboardModifiers):
    if key == 16777268:#F5
        sub_self.update_table()