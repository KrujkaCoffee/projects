from __future__ import annotations

import json

if __name__ == "__main__":
    from project_cust_38 import Cust_pre_config
    Cust_pre_config.reg_env_db_users()


import copy
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_config as CFG
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_emoji as CEMOJ

from project_cust_38.sub_mes.discussions.dataClasses import data_app as DTCLS
from project_cust_38.sub_mes.discussions.dataClasses import ReferenceStore as STORE_C
import project_cust_38.sub_mes.discussions.discuss_ui as discuss_ui
import project_cust_38.sub_mes.discussions.sub_classes as CLSS

if DTCLS.CONFIG.user_config.is_developer:
    if CQT.convert_UI_into_PY_c(str(F.Cust_path(discuss_ui)) + F.sep()):
        import importlib
        importlib.reload(discuss_ui)

import project_cust_38.sub_mes.discussions.connects as _con


from typing import  TYPE_CHECKING

if TYPE_CHECKING:
    pass

STORE = STORE_C()
STORE.load_data_reference()

class CentralWindow(CQT.QtWidgets.QMainWindow):
    def __init__(self,app_self=None,app_name:str='',tbl_name:str='',id_row:str='',title_ui:str='',user_row:str=''):
        """
        BD_users -> app_config -> new_sub_app				new_sub_app.py	0
        :param app_self:
        """
        super(CentralWindow, self).__init__()
        self.VER:str= '0.1'
        self.ui = discuss_ui.Ui_MainWindow()
        self.ui.setupUi(self)
        self.app_self = app_self
        DTCLS.app_self = app_self
        DTCLS.sub_self = self
        DTCLS._app_name = app_name
        DTCLS._tbl_name = tbl_name
        DTCLS._id_row = id_row
        DTCLS._title_ui = title_ui
        DTCLS._user_row = user_row


        if DTCLS.app_self:
             self.setStyleSheet(DTCLS.app_self.styleSheet())
        else:
             self._load_free_css()

        self.setAttribute(CQT.Qt.WA_DeleteOnClose)
        CQT.connect_to_resize(self, CMS.tmp_dir())

        CQT.load_icons(self, 26, dir=str(F.Cust_path(discuss_ui)) + F.sep() + 'icons' + F.sep())
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
        CFG.BaseSubWindow.close_in_event(self)
        event.accept()

    @classmethod
    def start_sub_app(cls,app_self)->'CentralWindow':
        window_manual = CentralWindow(app_self)
        window_manual.showMaximized()
        return window_manual



    def build_emoji_panel(self, layout, emojis, cols=6, on_pick=None):
        """Наполнить готовый QGridLayout кнопками-эмодзи."""
        # на случай повторного вызова — очистить
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for i, e in enumerate(emojis):
            btn = CQT.QtWidgets.QPushButton(e)
            btn.setFixedSize(28, 28)
            btn.setFlat(True)
            btn.setFocusPolicy(CQT.QtCore.Qt.NoFocus)
            btn.setCursor(CQT.QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet("""
                  QPushButton { border: 0; border-radius: 4px; font-size: 16px; }
                  QPushButton:hover { background: #eef2f7; }
                  QPushButton:pressed { background: #dde7f5; }
              """)
            if on_pick:
                btn.clicked.connect(lambda _, s=e: on_pick(s))
            layout.addWidget(btn, i // cols, i % cols)

    def _____________sub__________________(self):
        pass

    def init_data(self):
        CQT.load_resize_splitters(self, CQT.qt_tmp_dir())
        DTCLS.init_data()

    def _load_free_css(self):
        theme_path = F.sep().join([F.path_to_execut_file_c(), 'css'])
        CQT.apply_css_theme(self, theme_path + F.sep()  + 'metallic.qss')

    def apply_subj(self,subject_mode:str=None):
        if subject_mode is None:
            subject_mode_str = ''
        else:
            subject_mode_str = f' - {subject_mode}'
        self.NAME_MODULE_BASE = f'Обсуждения v{self.VER}{subject_mode_str}'
        DTCLS.CONFIG.user_config.set_sub_window_title(self)
        # CONNECTS
        _con.prepare_ui(self)
        if self.app_self:
            CFG.BaseSubWindow.window_binding(self, F.name_of_caller_file(), self.app_self)
            print(f'add sub {CFG.Config.window_manager.active} into window_manager')
        else:
            CFG.BaseSubWindow.set_as_root(self)


        self.init_data()

        self.ui.tree_treads =  CLSS.BaseTreeWidget(self.ui.tree_treads,self.ui)

        DTCLS.current_discuss = CLSS.Discussion(DTCLS._app_name, DTCLS._tbl_name, DTCLS._id_row,DTCLS._title_ui,DTCLS._user_row)
        DTCLS.current_discuss.load()
        DTCLS.subcription_repo = CLSS.SubscriptionRepo(DTCLS.current_discuss)


        DTCLS.current_discuss.fill_tree(self.ui.tree_treads)
        self.upd_img_subcribe()
        self.build_emoji_panel(self.ui.grid_emoj,emojis =CEMOJ.EmojiMain.all_emoj_as_list(),
                               cols=8,
                               on_pick=self.insert_emoji_at_cursor)

        pass

    def insert_emoji_at_cursor(self, emoji: str):
        """Вставить emoji в текущую позицию курсора в pltxt_msg.
        Заменяет выделенный текст, если он есть."""
        editor = self.ui.pltxt_msg
        cursor = editor.textCursor()
        cursor.insertText(emoji)
        editor.setTextCursor(cursor)
        editor.setFocus()

    def upd_img_subcribe(self,is_subscribed:bool|None=None):
        self.ui.btn_subscribe.setEnabled( not DTCLS.subcription_repo.thread_o.id is None)
        file = "btn_subscribe_off"
        dir = str(F.Cust_path(discuss_ui)) + F.sep() + 'icons' + F.sep()

        if is_subscribed is None:
            is_subscribed = DTCLS.subcription_repo.is_subscribed()
        if is_subscribed:
            file = "btn_subscribe"

        name_img = dir + file
        CQT.set_btn_icon(self.ui.btn_subscribe, name_img)


    def _____________________________(self):pass



    def send_msg(self):
        pltxt_msg = self.ui.pltxt_msg.toPlainText().strip()
        if not pltxt_msg:
            return


        msg_id =DTCLS.current_discuss.reply_to_selected(self.ui.tree_treads, body=pltxt_msg,
                                                        author=CFG.Config.user_config.User.ФИОк)
        self.ui.pltxt_msg.clear()
        DTCLS.subcription_repo.on_new_message(msg_id)

        if DTCLS.current_discuss.fl_new:
            self.subscribe()
            DTCLS.current_discuss.fl_new = False

        self.upd_img_subcribe()

    def subscribe(self):
        is_subscribed = DTCLS.subcription_repo.toggle()
        self.upd_img_subcribe(is_subscribed)
        pass

    def toggle_emoji(self):
        self.ui.fr_emoj.setVisible(not self.ui.fr_emoj.isVisible())


if __name__ == "__main__":

    from project_cust_38.Cust_application import install_crash_guard, SafeApplication
    app = SafeApplication(sys.argv)
    install_crash_guard(app, app_name='',user_name='', log_qt_warnings=False,log_qt_debug_info=False, enable_native_fault_handler=False)
    #CQT.ThemeManager.apply(app)
    sub_window = CentralWindow(None)
    sub_window.showMaximized()
    sys.exit(app.exec())
