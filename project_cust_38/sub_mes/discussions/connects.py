from __future__ import annotations
import project_cust_38.Cust_Qt as CQT
from typing import  TYPE_CHECKING
if TYPE_CHECKING:
    from  main_discuss import CentralWindow
def prepare_ui(sub_self: CentralWindow):
    t = sub_self.ui.tree_treads
    # 1. Многострочный текст
    t.setWordWrap(True)
    # 2. ВАЖНО: иначе Qt режет высоту по первой строке
    t.setUniformRowHeights(False)
    # 3. Колонка на всю ширину
    t.header().setSectionResizeMode(0, CQT.QHeaderView.Stretch)
    # 4. Убрать дефолтный заголовок "1"
    t.setHeaderLabels([''])
    t.header().setVisible(False)  # или True, если хочешь пустую шапку
    # 5. (по желанию) — компактнее отступы
    t.setIndentation(14)
    t.setRootIsDecorated(True)
    t.setAnimated(True)
    t.setAllColumnsShowFocus(False)
    t.setExpandsOnDoubleClick(True)
    t.setStyleSheet(CQT.TREE_CSS)
    sub_self.ui.pltxt_msg.setStyleSheet(CQT.PLAINTEXT_CSS)
    sub_self.ui.fr_emoj.setHidden(True)



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
    if key in (CQT.QtCore.Qt.Key_Return, CQT.QtCore.Qt.Key_Enter) and mod == CQT.QtCore.Qt.ControlModifier:
        fw = CQT.QtWidgets.QApplication.focusWidget()
        if isinstance(fw, CQT.QtWidgets.QPlainTextEdit) and fw is sub_self.ui.pltxt_msg:
            sub_self.send_msg()

def load_connects(sub_self:CentralWindow):
    load_tbls(sub_self)
    load_btns(sub_self)


def load_tbls(sub_self:CentralWindow):
    #sub_self.ui.tbl_s_list_shabl.clicked.connect(lambda: sub_self.select_shablon())
    pass
def load_btns(sub_self:CentralWindow):
    sub_self.ui.btn_send.clicked.connect(lambda: sub_self.send_msg())
    sub_self.ui.btn_subscribe.clicked.connect(lambda: sub_self.subscribe())
    sub_self.ui.btn_emoj.clicked.connect(lambda: sub_self.toggle_emoji())
    pass