from __future__ import annotations
import project_cust_38.Cust_Qt as CQT
from typing import  TYPE_CHECKING
if TYPE_CHECKING:
    from  main_mngr import CentralWindow
def prepare_ui(sub_self: CentralWindow):
    pass
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
def load_connects(sub_self:CentralWindow):
    load_tbls(sub_self)
    load_btns(sub_self)


def load_btns(sub_self:CentralWindow):
    sub_self.ui.btn_edit_current.clicked.connect(lambda : sub_self.edit_manual(False))
    sub_self.ui.btn_edit_last.clicked.connect(lambda : sub_self.edit_manual(True))
    pass

def load_tbls(sub_self:CentralWindow):
    sub_self.ui.tbl_history.clicked.connect(lambda: sub_self.select_ver())
    pass