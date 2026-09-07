from __future__ import annotations
from typing import TYPE_CHECKING
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import general as GEN
from app_dataclasses import data_app as DTCLS
import project_cust_38.Cust_tree_widget as CTREE
from functools import partial
import doc_modules.doc_rd as DCRD
import doc_modules.doc_zp as DCZP
import doc_modules.doc_zvp as DCZVP
import doc_modules.doc_vsk as DCVSK
import doc_modules.doc_zmp as DCZMP
import doc_modules.doc_zsb as DCZSB
import doc_modules.doc_common as DCCOM
if TYPE_CHECKING:
    from arm_ww import mywindow


def load_connects(self):
    tabs()
    combos(self)
    tbls(self)
    btns(self)
    actions(self)
    chks(self)
    trees(self)
    tedit(self)
    connect_to_resize(self)
    splitters(self)


def tedit(self):
    ui = DTCLS.app_self.ui
    pline = CQT.Cust_plane_edit(ui.pte_start)
    text = GEN.load_plane_text()
    pline.set_text(text)
    pline.event_text_edit(GEN.save_plane_text)
    DTCLS.pline = pline

def tabs():
    ui = DTCLS.app_self.ui
    fnc = partial(GEN.tab_w_currentChanged)
    ui.tab_w.currentChanged[int].connect(fnc)
def connect_to_resize(self: mywindow):
    # подключение события изменения размера окна
    CQT.connect_to_resize(self, CMS.tmp_dir())

def splitters(self: mywindow):
    ui = self.ui
    CQT.QtCore.QTimer.singleShot(50, lambda: CQT.load_resize_splitters(self, CMS.tmp_dir()))
    CQT.QtCore.QTimer.singleShot(0, self.showMaximized)


def tbls(self: mywindow):
    ui = self.ui
    ui.tbl_rd.itemSelectionChanged.connect(partial(DCRD.tbl_select_itemSelectionChanged))
    ui.tbl_zp.itemSelectionChanged.connect(partial(DCZP.tbl_select_itemSelectionChanged))
    ui.tbl_vsk.itemSelectionChanged.connect(partial(DCVSK.tbl_select_itemSelectionChanged))
    ui.tbl_zmp.itemSelectionChanged.connect(partial(DCZMP.tbl_select_itemSelectionChanged))
    ui.tbl_zvp.itemSelectionChanged.connect(partial(DCZVP.tbl_select_itemSelectionChanged))
    ui.tbl_zsb.itemSelectionChanged.connect(partial(DCZSB.tbl_select_itemSelectionChanged))
    ui.tbl_common.itemSelectionChanged.connect(partial(DCCOM.tbl_select_itemSelectionChanged))
    #ui.tbl_vsk.cellDoubleClicked.connect(partial(DCVSK.tbl_cellDoubleClicked))
    # ui.tbl_list_orders.itemSelectionChanged.connect(lambda: GEN.tbl_list_orders_itemSelectionChanged(self))
    #
    # ui.tbl_select.itemSelectionChanged.connect(lambda: GEN.tbl_select_itemSelectionChanged(self))
    # ui.tbl_select.cellDoubleClicked.connect(lambda: GEN.clicked_btn_select(self,True))
    #
    # ui.tbl_current_elem.itemActivated.connect(lambda item: GEN.tbl_current_elem_itemActivated(self, item))
    # ui.tbl_current_elem.cellClicked.connect(lambda i,j : GEN.tbl_current_elem_cellEntered(self, i,j))
    # ui.tbl_current_elem.itemChanged.connect(lambda item: GEN.tbl_current_elem_itemChanged(self, item) )
    #
    # ui.tbl_cr_res.itemActivated.connect(lambda item: GEN.tbl_cr_res_itemActivated(self, item))
    # ui.tbl_cr_res.cellClicked.connect(lambda i,j : GEN.tbl_cr_res_cellEntered(self, i,j,ui.tbl_cr_res))
    # ui.tbl_cr_res.itemChanged.connect(lambda item: GEN.tbl_cr_res_itemChanged(self, item,ui.tbl_cr_res))
    #
    # ui.tbl_cr_dse.itemActivated.connect(lambda item: GEN.tbl_cr_res_itemActivated(self, item))
    # ui.tbl_cr_dse.cellClicked.connect(lambda i,j : GEN.tbl_cr_res_cellEntered(self, i,j,ui.tbl_cr_dse))
    # ui.tbl_cr_dse.itemChanged.connect(lambda item: GEN.tbl_cr_res_itemChanged(self, item,ui.tbl_cr_dse))
    #
    # ui.tbl_cr_etaps_res.itemActivated.connect(lambda item: GEN.tbl_cr_res_itemActivated(self, item))
    # ui.tbl_cr_etaps_res.cellClicked.connect(lambda i,j : GEN.tbl_cr_res_cellEntered(self, i,j,ui.tbl_cr_etaps_res))
    # ui.tbl_cr_etaps_res.itemChanged.connect(lambda item: GEN.tbl_cr_etaps_res_itemChanged(self, item,ui.tbl_cr_etaps_res) )


def combos(self: mywindow):
    ui = self.ui
    # ui.cmb_list_folders_docs.activated[int].connect(lambda: GEN.cmb_list_folders_docs_activated(self))


def chks(self: mywindow):
    ui = self.ui
    # ui.chk_view_hidden_fields.clicked.connect(lambda: GEN.view_hidden_fields(self))
    # ui.chk_use_cache_params.stateChanged.connect(lambda state: GEN.use_cache_params(self, state))
    # ui.chk_nomen_desc.clicked.connect(lambda: GEN.save_nomen_config(self))
    # ui.chk_nomen_unit.clicked.connect(lambda: GEN.save_nomen_config(self))
    # ui.chk_nomen_maker.clicked.connect(lambda: GEN.save_nomen_config(self))
    # ui.chk_nomen_describe.clicked.connect(lambda: GEN.save_nomen_config(self))
    # ui.chk_nomen_add_r.clicked.connect(lambda: GEN.save_nomen_config(self))


def actions(self: mywindow):
    ui = self.ui


def btns(self: mywindow):
    ui = self.ui
    ui.btn_update.clicked.connect(partial(GEN.update_tab))
    ui.btn_dates.clicked.connect(partial(GEN.update_dates))
    ui.btn_storage.clicked.connect(partial(GEN.select_storages))
    ui.btn_update.setToolTip(f'Синхронизация с 1С,\nраз в {DTCLS.lazy_time_munutes} минут.')
def trees(self: mywindow):
    ui = self.ui
