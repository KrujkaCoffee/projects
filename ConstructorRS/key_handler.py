from __future__ import annotations
from typing import TYPE_CHECKING
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import general as GEN
from PyQt5 import QtWidgets, QtCore
if TYPE_CHECKING:
    from constr_rc import mywindow
def keyReleaseEvent(self:mywindow, key_val: int, set_modifiers: set = ()):
    if self.ui.le_fr_add_erp_filtr.hasFocus():
        if key_val == 16777220:
            GEN.find_fr_add_erp()
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
        if key_val == QtCore.Qt.Key_Return:
            focus: QtWidgets.QTableWidget = QtWidgets.QApplication.focusWidget()
            if not focus == None:
                if '_filtr' in focus.objectName():
                    tbl_name =focus.objectName().replace('_filtr','')
                    if hasattr(self.ui, tbl_name):
                        CMS.apply_filtr_c(self, focus, self.ui.__getattribute__(tbl_name))

        if key_val == QtCore.Qt.Key_P and set_modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.refill_tbl_into_msgbox_get_table(self, QtWidgets.QApplication.focusWidget())

        if key_val == QtCore.Qt.Key_C and set_modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if CQT.focus_is_QTableWidget():
                CQT.copy_bufer_table(QtWidgets.QApplication.focusWidget())

        if key_val == QtCore.Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()