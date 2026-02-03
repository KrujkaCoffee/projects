from __future__ import annotations
from typing import TYPE_CHECKING
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import general as GEN
from dataClass import data_app as DTCLS
import project_cust_38.Cust_tree_widget as CTREE
from main_classes import TypesDoc
if TYPE_CHECKING:
    from constr_rc import mywindow

def load_connects(self):
    combos(self)
    tbls(self)
    btns(self)
    toolbox(self)
    actions(self)
    chks(self)
    trees(self)
    dockNavigator(self)
    connect_to_resize(self)
    splitters(self)

def connect_to_resize(self:mywindow):
    # подключение события изменения размера окна
    CQT.connect_to_resize(self, CMS.tmp_dir())

def splitters(self:mywindow):
    ui = self.ui
    CQT.QtCore.QTimer.singleShot(50, lambda: CQT.load_resize_splitters(self, CMS.tmp_dir()))
    CQT.QtCore.QTimer.singleShot(0, self.showMaximized)
def tbls(self:mywindow):
    ui = self.ui
    ui.tbl_list_orders.itemSelectionChanged.connect(lambda: GEN.tbl_list_orders_itemSelectionChanged(self))

    ui.tbl_select.itemSelectionChanged.connect(lambda: GEN.tbl_select_itemSelectionChanged(self))
    ui.tbl_select.cellDoubleClicked.connect(lambda: GEN.clicked_btn_select(self,True))

    ui.tbl_current_elem.itemActivated.connect(lambda item: GEN.tbl_current_elem_itemActivated(self, item))
    ui.tbl_current_elem.cellClicked.connect(lambda i,j : GEN.tbl_current_elem_cellEntered(self, i,j))
    ui.tbl_current_elem.itemChanged.connect(lambda item: GEN.tbl_current_elem_itemChanged(self, item) )

    ui.tbl_cr_res.itemActivated.connect(lambda item: GEN.tbl_cr_res_itemActivated(self, item))
    ui.tbl_cr_res.cellClicked.connect(lambda i,j : GEN.tbl_cr_res_cellEntered(self, i,j,ui.tbl_cr_res))
    ui.tbl_cr_res.itemChanged.connect(lambda item: GEN.tbl_cr_res_itemChanged(self, item,ui.tbl_cr_res))

    ui.tbl_cr_dse.itemActivated.connect(lambda item: GEN.tbl_cr_res_itemActivated(self, item))
    ui.tbl_cr_dse.cellClicked.connect(lambda i,j : GEN.tbl_cr_res_cellEntered(self, i,j,ui.tbl_cr_dse))
    ui.tbl_cr_dse.itemChanged.connect(lambda item: GEN.tbl_cr_res_itemChanged(self, item,ui.tbl_cr_dse))

    ui.tbl_cr_etaps_res.itemActivated.connect(lambda item: GEN.tbl_cr_res_itemActivated(self, item))
    ui.tbl_cr_etaps_res.cellClicked.connect(lambda i,j : GEN.tbl_cr_res_cellEntered(self, i,j,ui.tbl_cr_etaps_res))
    ui.tbl_cr_etaps_res.itemChanged.connect(lambda item: GEN.tbl_cr_etaps_res_itemChanged(self, item,ui.tbl_cr_etaps_res) )
def combos(self:mywindow):
    ui = self.ui
    ui.cmb_list_folders_docs.activated[int].connect(lambda: GEN.cmb_list_folders_docs_activated(self))

def chks(self:mywindow):
    ui = self.ui
    ui.chk_view_hidden_fields.clicked.connect(lambda: GEN.view_hidden_fields(self))
    ui.chk_use_cache_params.stateChanged.connect(lambda state: GEN.use_cache_params(self, state))
    ui.chk_nomen_desc.clicked.connect(lambda: GEN.save_nomen_config(self))
    ui.chk_nomen_unit.clicked.connect(lambda: GEN.save_nomen_config(self))
    ui.chk_nomen_maker.clicked.connect(lambda: GEN.save_nomen_config(self))
    ui.chk_nomen_describe.clicked.connect(lambda: GEN.save_nomen_config(self))
    ui.chk_nomen_add_r.clicked.connect(lambda: GEN.save_nomen_config(self))


    if not GEN.CFG.Config.user_config.is_developer:
         if 'chk_view_hidden_fields' not in self.APP_ARGS:
            self.ui.chk_view_hidden_fields.setHidden(True)

    if not self.ui.chk_view_hidden_fields.isHidden():
        ui.chk_view_hidden_fields.setChecked(CMS.load_tmp_stukt('view_hidden_fields', False))

    ui.chk_use_cache_params.setChecked(CMS.load_tmp_stukt('use_cache_params', False))

    GEN.view_hidden_fields(self)
    GEN.use_cache_params(self)
def actions(self:mywindow):
    ui = self.ui
    ui.actn_check_rs.triggered.connect(lambda: GEN.check_rs(self))
    ui.actn_clear_rs.triggered.connect(lambda: GEN.clear_rs(self))
def btns(self:mywindow):
    ui = self.ui
    ui.btnToggle.clicked.connect(lambda: GEN.toggleMaximizeRestore(self,self.ui.dockNavigator,ui.btnToggle))
    ui.btnToggle_ierarch.clicked.connect(lambda: GEN.toggleMaximizeRestore(self,self.ui.dockW_ierarch,ui.btnToggle_ierarch))

    ui.btn_insert_dockW.clicked.connect(lambda: GEN.insert_dockW(self,self.ui.dockNavigator,ui.btn_insert_dockW,
                                                                   self.ui.splitter_navigator))
    ui.btn_insert_ierarch.clicked.connect(lambda: GEN.insert_dockW(self,self.ui.dockW_ierarch,ui.btn_insert_ierarch,
                                                                   self.ui.splitter_ierarch))

    ui.btn_add_row.clicked.connect(lambda: GEN.clicked_btn_add_row(self))
    ui.btn_delete_row.clicked.connect(lambda: GEN.clicked_btn_delete_row(self))
    ui.btn_clear_row.clicked.connect(lambda: GEN.clicked_btn_clear_row(self))
    ui.btn_clear_tree.clicked.connect(lambda: GEN.clicked_btn_clear_tree(self))

    ui.btn_add_res.clicked.connect(lambda: GEN.clicked_btn_add_obj(self,TypesDoc.res))
    ui.btn_add_dse.clicked.connect(lambda: GEN.clicked_btn_add_obj(self,TypesDoc.dse))


    ui.btn_select_ok.clicked.connect(lambda: GEN.clicked_btn_select(self,True))
    ui.btn_select_cancel.clicked.connect(lambda: GEN.clicked_btn_select(self,False))

    ui.btn_save_tree.clicked.connect(lambda: GEN.clicked_btn_save_tree(self))
    ui.btn_load_tree.clicked.connect(lambda: GEN.clicked_btn_load_tree(self))

    ui.btn_import_exel.clicked.connect(lambda: GEN.clicked_btn_import_exel(self))

    ui.cbtn_favour.clicked.connect(lambda: GEN.clicked_cbtn_favour(self))



def toolbox(self:mywindow):
    ui = self.ui

    ui.tb_elem.currentChanged.connect(
        lambda index: GEN.tbox_page_changed(self, index)
    )
def trees(self:mywindow):
    ui = self.ui

    DTCLS.treeNavigator:CTREE.ExtTreeWidget|CQT.QtWidgets.QTreeWidget = CTREE.ExtTreeWidget(ui.treeNavigator,ui)
    DTCLS.treeNavigator.itemSelectionChanged.connect(lambda: GEN.treeNavigator_itemSelectionChanged(self))
    DTCLS.treeNavigator.doubleClicked.connect(lambda: GEN.treeNavigator_doubleClicked(self))

    tree_add_res = CTREE.ExtTreeWidget(ui.tree_add_res, ui)
    tree_add_res.itemSelectionChanged.connect(lambda: GEN.tree_add_res_itemSelectionChanged(self))
    tree_add_res.itemDoubleClicked.connect(lambda: GEN.clicked_btn_add_obj(self,TypesDoc.res))

    tree_add_dse = CTREE.ExtTreeWidget(ui.tree_add_dse, ui)
    tree_add_dse.itemSelectionChanged.connect(lambda: GEN.tree_add_dse_itemSelectionChanged(self))
    tree_add_dse.itemDoubleClicked.connect(lambda: GEN.clicked_btn_add_obj(self,TypesDoc.dse))




def dockNavigator(self:mywindow):
    ui = self.ui

    # Использование
    ui.dockNavigator.installEventFilter(self)
    # для хранения геометрии
    ui.dockNavigator._normalGeometry = None

