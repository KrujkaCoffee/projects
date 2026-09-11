from __future__ import annotations

import json

if __name__ == "__main__":
    import sys
    import os
    os.environ['MODIFIED_CFG'] = '{"BD_users": "SRV:BD_users.db"}'


import copy
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_emoji as CEMOJ

from project_cust_38.sub_mes.manual_mngr.dataClasses import data_app as DTCLS
from project_cust_38.sub_mes.manual_mngr.dataClasses import ReferenceStore as STORE_C
import project_cust_38.sub_mes.manual_mngr.manual_ui as manual_ui
import project_cust_38.sub_mes.manual_mngr.sub_classes as CLSS

if DTCLS.CONFIG.user_config.is_developer:
    if CQT.convert_UI_into_PY_c(str(F.Cust_path(manual_ui)) + F.sep()):
        import importlib
        importlib.reload(manual_ui)

import project_cust_38.sub_mes.manual_mngr.connects as _con


from typing import  TYPE_CHECKING

if TYPE_CHECKING:
    pass

STORE = STORE_C()
STORE.load_data_reference()

class CentralWindow(CQT.QtWidgets.QMainWindow):
    def __init__(self,app_self=None):
        """
        BD_users -> app_config -> new_sub_app				new_sub_app.py	0
        :param app_self:
        """

        super(CentralWindow, self).__init__()
        self.VER:str= '0.1'
        self.ui = manual_ui.Ui_MainWindow()
        self.ui.setupUi(self)

        DTCLS.app_self = app_self
        DTCLS.sub_self = self

        if DTCLS.app_self:
             self.setStyleSheet(DTCLS.app_self.styleSheet())
        else:
             self._load_free_css()

        self.setAttribute(CQT.Qt.WA_DeleteOnClose)
        CQT.connect_to_resize(self, CMS.tmp_dir())

        CQT.load_icons(self, 26, dir=str(F.Cust_path(manual_ui)) + F.sep() + 'icons' + F.sep())
        self.setWindowModality(CQT.Qt.ApplicationModal)
        self.apply_subj()

        _con.load_connects(self)

    def _____________service_______________(self):pass

    def keyReleaseEvent(self, e):
        key = e.key()
        mod = e.modifiers()
        _con.key_release_event(self, key, mod)

    def eventFilter(self, obj, event):
        # noinspection PyUnresolvedReferences
        if isinstance(obj, CQT.QtWidgets.QDockWidget) and event.type() == CQT.QtCore.QEvent.MouseButtonDblClick:
            # noinspection PyUnresolvedReferences
            if event.button() == CQT.QtCore.Qt.LeftButton:
                obj.setFloating(True)
                screen = CQT.QtWidgets.QApplication.primaryScreen()
                rect = screen.availableGeometry()
                if obj.geometry() == rect:
                    # Уже развернут — вернуть нормальный размер
                    # self.ui.dockNavigator.showNormal()
                    obj.showMaximized()
                else:
                    # Растянуть ровно по рабочей области (без панели задач)
                    obj.setGeometry(rect)
                    obj.show()
                return True

        if isinstance(obj, CQT.QtWidgets.QDockWidget) and event.type() == CQT.QtCore.QEvent.Resize:
            if CQT.QtWidgets.QApplication.mouseButtons() == CQT.QtCore.Qt.LeftButton:
                key = f'QDockWidget:{obj.objectName()}'
                target = getattr(self, '_resize_targets', {}).get(key)
                if target is not None:
                    CQT._on_resize_event(self, target)
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        #before_close(self)
        event.accept()

    @classmethod
    def start_sub_app(cls,app_self,tabs:CQT.QtWidgets.QTabWidget,index:int,name_point)->'CentralWindow':
        DTCLS.tabs = tabs
        DTCLS.index = index
        DTCLS.name_point = name_point
        window_manual = CentralWindow(app_self)
        window_manual.showMaximized()

        return window_manual

    def _____________sub__________________(self):
        pass

    def init_data(self):
        CQT.load_resize_splitters(self, CQT.qt_tmp_dir())
        DTCLS.init_data()
        self.fill_manuals()


    def fill_manuals(self):
        DTCLS.manual_o = CMS.Manual.new(DTCLS.tabs, DTCLS.index, DTCLS.name_point)
        load_db_list = DTCLS.manual_o.load_db_list()
        for it in load_db_list:
            if it['user_ref'] in STORE.DICT_ФизическиеЛица_by_ref:
                it['user_ref'] = STORE.DICT_ФизическиеЛица_by_ref[it['user_ref']].Наименование

        CQT.fill_wtabl(load_db_list,self.ui.tbl_history,styleSheet=CQT.MES_CSS,selectionMode=CQT.SelectionModes.SingleSelection,
                       selectionBehavior=CQT.SelectionBehaviors.SelectRows,aliases_header=CMS.Manual.ALIASES)
        t = CQT.TableContext(self.ui.tbl_history)
        t.hide_if_not_dev(CFG,True)

        self.fill_html()

    def fill_html(self):
        self.ui.txtbr_view.setText(DTCLS.manual_o.html)


    def calc_selected_ver(self):
        t = CQT.TableContext(self.ui.tbl_history)
        row = t.current_row()
        if row.no_selection:
            return
        ver = int(row.value('ver'))
        return ver
    def select_ver(self):
        DTCLS.manual_o.load_ver(self.calc_selected_ver())
        self.fill_html()


    def edit_manual(self,last_ver):

        def fnc_validate(text_html: str, plain_text: str, *args) -> bool:
            if not plain_text.strip():
                return True, None
            return True, text_html


        #print(f"Нажата кнопка ({tabs.objectName()}) на вкладке {tab.objectName()}")
        initial_view = CQT.RichTextViewMode.EDIT
        placeholder_text = "Опишите принцип работы с интерфейсом..."
        msg = "Разработка руководства пользователя"

        if last_ver:
            DTCLS.manual_o = CMS.Manual.new(DTCLS.tabs, DTCLS.index, DTCLS.name_point)
        else:
            DTCLS.manual_o.load_ver(self.calc_selected_ver())

        suc, html = CQT.get_dialog_choose_rich_text(
            self,
            msg=msg,
            start_html=DTCLS.manual_o.html,
            placeholder_text=placeholder_text,
            func_validate=fnc_validate,
            initial_view=initial_view,
            showMaximized=True
        )
        if not suc:
            return
        else:
            DTCLS.manual_o.set_html(html)
            DTCLS.manual_o.save()
            self.fill_manuals()
        pass

    def _load_free_css(self):
        theme_path = F.sep().join([F.path_to_execut_file_c(), 'css'])
        CQT.apply_css_theme(self, theme_path + F.sep()  + 'metallic.qss')

    def apply_subj(self,subject_mode:str=None):
        if subject_mode is None:
            subject_mode = ''
        self.NAME_MODULE_BASE = f'Менеджер документации v{self.VER} - {subject_mode}'
        DTCLS.CONFIG.user_config.set_sub_window_title(self)
        # CONNECTS
        _con.prepare_ui(self)
        self.init_data()


    def _____________________________(self):pass


if __name__ == "__main__":

    from project_cust_38.Cust_application import install_crash_guard, SafeApplication
    app = SafeApplication(sys.argv)
    install_crash_guard(app, app_name='',user_name='', log_qt_warnings=False,log_qt_debug_info=False, enable_native_fault_handler=False)
    #CQT.ThemeManager.apply(app)
    sub_window = CentralWindow(None)
    sub_window.showMaximized()
    sys.exit(app.exec())
