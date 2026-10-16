from __future__ import annotations
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_tree_widget  as CTREE
from typing import  TYPE_CHECKING
if TYPE_CHECKING:
    from  main_constructor import CentralWindow

def set_tree_readonly(tree, readonly: bool = True) -> None:
    """Включить/выключить режим только-чтение для дерева (без drag&drop)."""
    if readonly:
        tree.setDragEnabled(False)
        tree.setAcceptDrops(False)
        tree.setDropIndicatorShown(False)
        tree.setDragDropMode(CQT.QtWidgets.QAbstractItemView.NoDragDrop)
        tree.setDefaultDropAction(CQT.QtCore.Qt.IgnoreAction)
    else:
        tree.setDragEnabled(True)
        tree.setAcceptDrops(True)
        tree.setDropIndicatorShown(False)
        tree.setDragDropMode(CQT.QtWidgets.QAbstractItemView.InternalMove)
        tree.setDefaultDropAction(CQT.QtCore.Qt.MoveAction)

def prepare_ui(sub_self: CentralWindow):

    CTREE.ExtTreeWidget(sub_self.ui.tree_of_product, sub_self.ui)
    sub_self.ui.tree_of_product.on_drop_access = sub_self._on_tree_drop

    CSS = CQT.MES_TREE_CSS('branch_closed','branch_open')

    sub_self.ui.tree_of_product.setStyleSheet(CSS)
    CQT.connect_to_resize_treew(sub_self,sub_self.ui.tree_of_product, CQT.qt_tmp_dir())


    lbl = sub_self.ui.lbl_cards
    CQT.Fonts.set_cust_font(lbl)


    sub_self.ui.fr_tree_btns.setVisible(sub_self.DTCLS.mode.editable)
    sub_self.ui.fr_row_btns.setVisible(sub_self.DTCLS.mode.editable)
    sub_self.ui.btn_save_card.setVisible(sub_self.DTCLS.mode.editable)
    sub_self.ui.fr_tree_btns_ronly.setVisible(not sub_self.DTCLS.mode.editable)



def key_release_event(sub_self:CentralWindow, key:int, mod:CQT.QtCore.Qt.KeyboardModifiers):
    if key == 16777268:#F5
        sub_self.update_table()
    if key == 80 and mod == (CQT.QtCore.Qt.ControlModifier | CQT.QtCore.Qt.ShiftModifier):
        if CQT.focus_is_QTableWidget():
            CQT.refill_tbl_into_msgbox_get_table(sub_self, CQT.QtWidgets.QApplication.focusWidget())
    if key == 67 and mod == (CQT.QtCore.Qt.ControlModifier | CQT.QtCore.Qt.ShiftModifier):
        if CQT.focus_is_QTableWidget():
            CQT.copy_bufer_table(CQT.QtWidgets.QApplication.focusWidget())
    if key == CQT.QtCore.Qt.Key_F11:
        if sub_self.isFullScreen():
            sub_self.showNormal()
        else:
            sub_self.showFullScreen()

    if not sub_self.DTCLS.mode.editable:
        return

    if CQT.QtWidgets.QApplication.focusWidget() is sub_self.ui.tree_of_product:
        if key == CQT.QtCore.Qt.Key_D and mod == CQT.QtCore.Qt.ControlModifier:
            sub_self.duplicate_row()
            return
        if key == CQT.QtCore.Qt.Key_Delete:
            sub_self.del_row()
            return
        if key == CQT.QtCore.Qt.Key_Insert:
            sub_self.new_row()
        if key == CQT.QtCore.Qt.Key_S and mod ==  (CQT.QtCore.Qt.ControlModifier | CQT.QtCore.Qt.ShiftModifier):
            sub_self.save_struct_f()

        if key == CQT.QtCore.Qt.Key_S and mod == CQT.QtCore.Qt.ControlModifier :
            sub_self.save_current_struct_f()

        if key == CQT.QtCore.Qt.Key_L and mod == CQT.QtCore.Qt.ControlModifier:
            sub_self.load_struct_f()

        if key == CQT.QtCore.Qt.Key_N and mod == CQT.QtCore.Qt.ControlModifier:
            sub_self.new_struct(new= True)


def load_connects(sub_self:CentralWindow):
    load_tbls(sub_self)
    load_trees(sub_self)
    load_btns(sub_self)


def load_tbls(sub_self:CentralWindow):
    #sub_self.ui.tbl_s_list_shabl.clicked.connect(lambda: sub_self.select_shablon())
    pass

def load_btns(sub_self:CentralWindow):
    sub_self.ui.btn_save_struct_f.clicked.connect(lambda: sub_self.save_struct_f())
    sub_self.ui.btn_save.clicked.connect(lambda: sub_self.save_current_struct_f())
    sub_self.ui.btn_load_f.clicked.connect(lambda: sub_self.load_struct_f())
    sub_self.ui.btn_new_row.clicked.connect(lambda: sub_self.new_row())
    sub_self.ui.btn_del_row.clicked.connect(lambda: sub_self.del_row())
    sub_self.ui.btn_duplicate.clicked.connect(lambda: sub_self.duplicate_row())
    sub_self.ui.btn_apply.clicked.connect(lambda: sub_self.apply_changes_row())
    sub_self.ui.btn_new_struct.clicked.connect(lambda: sub_self.load_struct_f(new= True))
    sub_self.ui.btn_maximize.clicked.connect(lambda: sub_self.toggle_dock_fullscreen())
    sub_self.ui.btn_floating.clicked.connect(lambda: sub_self.toggle_dock_floating())
    sub_self.ui.btn_load_card.clicked.connect(lambda: sub_self.btn_load_card_struct())
    sub_self.ui.btn_save_card.clicked.connect(lambda: sub_self.btn_save_card_struct())
    sub_self.ui.btn_get_to_mk.clicked.connect(lambda: sub_self.btn_get_to_mk())

def load_trees(sub_self:CentralWindow):
    sub_self.ui.tree_of_product.currentItemChanged.connect(
        lambda cur, prev: sub_self.select_tree_row( cur, prev)
    )
