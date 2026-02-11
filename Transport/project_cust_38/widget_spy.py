from concurrent.futures import ThreadPoolExecutor
import faulthandler
import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, QTimer, QEvent, Qt

from project_cust_38 import Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_Functions as F



def try_task(fn):
    def wrap(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            print(e)
    return wrap

class PyQtEventHook(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_hover_widget_name = None
        self._textedit_timers = {}
        self.user = self.app_name = self.department = self.profession = ''
        self.sender_function = CSQ.custom_request_c
        if isinstance(self.sender_function, F.StatisticDecorator):
            self.sender_function = self.sender_function.function
        try:
            self.user = F.user_name()
            self.app_name = F.name_of_executable_file_c()
            profile = self.get_employee(self.user)
            if not profile or not isinstance(profile, dict):
                return
            self.department = profile.get('Подразделение', '')
            self.profession = profile.get('Должность', '')
        except Exception as e:
            print(e)

        self._executor = ThreadPoolExecutor()

    def get_employee(self, login):
        query = f"""
            SELECT 
                login, Должность, Подразделение 
            FROM employee WHERE Статус != "Увольнение" AND login = {login!r}
        """
        profile = CSQ.custom_request_c(
            CFG.Config.project.db_users,
            query,
            rez_dict=True,
            one=True
        )
        return profile

    def attach_hooks(self, parent):
        """
        Находим и подключаемся к таблицам, чекбоксам, комбобоксам,
        QLineEdit и QTextEdit в parent и его дочерним элементам
        """
        tables = parent.findChildren(QtWidgets.QTableWidget)
        # Таблицы
        for table in tables:
            table.itemChanged.connect(self._on_table_item_changed, Qt.DirectConnection)
            table.installEventFilter(self)

        # Чекбоксы
        checkboxes = parent.findChildren(QtWidgets.QCheckBox)
        for cb in checkboxes:
            cb.stateChanged.connect(lambda state, cb=cb: self._on_checkbox_changed(cb, state))

        # Комбобоксы
        comboboxes = parent.findChildren(QtWidgets.QComboBox)
        for cbx in comboboxes:
            cbx.currentIndexChanged.connect(lambda index, cbx=cbx: self._on_combobox_changed(cbx, index))

        lineedits = parent.findChildren(QtWidgets.QLineEdit)
        for le in lineedits:
            le.editingFinished.connect(lambda le=le: self._on_lineedit_finished(le))

        textedits = parent.findChildren(QtWidgets.QTextEdit)
        for te in textedits:
            te.installEventFilter(self)
            te.textChanged.connect(lambda te=te: self._on_textedit_text_changed(te))
    @try_task
    def _on_table_item_changed(self, item):
        table = self.sender()
        if getattr(self, "_closing", False):
            return
        if table is None:
            return
        row = item.row()
        column = item.column()
        if row == -1 or column == -1:
            return
        cell = table.cellWidget(item.row(), item.column())
        widget = QtWidgets.QApplication.focusWidget()
        if cell is widget:
            data = {
                'event': 'table_edit',
                'object_name': table.objectName() if table else '',
                'widget_name': type(table).__name__ if isinstance(table, QtWidgets.QWidget) else '',
                'text': item.text() if item else '',
            }
            self._post(data)


    @try_task
    def _on_checkbox_changed(self, checkbox, state):
        data = {
            'event': 'checkbox_changed',
            'object_name': checkbox.objectName() if checkbox else '',
            'widget_name': type(checkbox).__name__ if isinstance(checkbox, QtWidgets.QWidget) else '',
            'text': bool(state),
        }
        self._post(data)

    @try_task
    def _on_combobox_changed(self, combobox, index):
        widget = QtWidgets.QApplication.focusWidget()
        if isinstance(widget, QtWidgets.QComboBox) and widget.objectName() == self.sender().objectName():
            data = {
                'event': 'text changed',
                'object_name': combobox.objectName() if combobox else '',
                'widget_name': type(combobox).__name__ if isinstance(combobox, QtWidgets.QWidget) else '',
                'text':  combobox.currentText() if combobox else '',
            }
            self._post(data)

    @try_task
    def _on_lineedit_finished(self, lineedit: QtWidgets.QLineEdit):
        if lineedit and not lineedit.text():
            return
        data = {
            'event': 'text changed',
            'object_name': lineedit.objectName() if lineedit else '',
            'widget_name': type(lineedit).__name__ if isinstance(lineedit, QtWidgets.QWidget) else '',
            'text': lineedit.text() if lineedit else '',
        }
        self._post(data)

    @try_task
    def _on_textedit_text_changed(self, textedit):
        # Запускаем или перезапускаем таймер на 1.5 сек, после которого считаем редактирование завершенным
        if textedit in self._textedit_timers:
            self._textedit_timers[textedit].stop()
        else:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda te=textedit: self._on_textedit_editing_finished(te))
            self._textedit_timers[textedit] = timer

        self._textedit_timers[textedit].start(1500)

    def eventFilter(self, obj, event):
        try:
            if isinstance(obj, QtWidgets.QTextEdit):
                if event.type() == QEvent.FocusOut:
                    if obj in self._textedit_timers and self._textedit_timers[obj].isActive():
                        self._textedit_timers[obj].stop()
                    self._on_textedit_editing_finished(obj)
            if event.type() == QEvent.MouseButtonPress and isinstance(obj, QtWidgets.QPushButton):
                self._send_button_click(obj)
            if event.type() == QEvent.MouseButtonPress and isinstance(obj, QtWidgets.QTabBar):
                tab_index = obj.tabAt(event.pos())
                if tab_index != -1:
                    self._send_tab_click(obj.parentWidget(), tab_index)
            return super().eventFilter(obj, event)
        except Exception as e:
            print(e)
            faulthandler.enable()
            faulthandler.dump_traceback(file=sys.stdout, all_threads=True)

    @try_task
    def _on_textedit_editing_finished(self, textedit: QtWidgets.QTextEdit):
        try:
            data = {
                'event': 'text changed',
                'object_name': textedit.objectName() if textedit else '',
                'widget_name': type(textedit).__name__ if isinstance(textedit, QtWidgets.QWidget) else '',
                'text': textedit.toPlainText() if textedit else '',
            }
            self._post(data)
        except Exception as e:
            print(e)

    @try_task
    def _send_button_click(self, button: QtWidgets.QPushButton):
        txt = button.text()
        if not txt:
            txt = button.toolTip()
        if button and not button.objectName():
            return
        data = {
            'event': 'button_click',
            'object_name': button.objectName() if button else '',
            'widget_name': type(button).__name__ if isinstance(button, QtWidgets.QWidget) else '',
            'text': txt,
        }
        self._post(data)

    @try_task
    def _send_tab_click(self, tab_widget, index):
        data = {
            'event': 'tab_click',
            'object_name': tab_widget.objectName() if tab_widget else '',
            'widget_name': type(tab_widget).__name__ if isinstance(tab_widget, QtWidgets.QWidget) else '',
            'text': tab_widget.tabText(index) if tab_widget else '',
        }
        self._post(data)

    def _post(self, data):
        def task():
            profession = self.profession
            department = self.department
            app_name = self.app_name
            user = self.user
            try:
                CSQ.custom_request_c(
                    CFG.Config.project.db_files,
                    '''
                        INSERT INTO WidgetEvents(widget_type, widget_name, action, extra_data, profession, department, app, user)
                            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                    list_of_lists_c=[[
                        data['widget_name'],
                        data['object_name'],
                        data['event'],
                        data['text'],
                        profession,
                        department,
                        app_name,
                        user
                    ]]
                )
            except Exception as e:
                print(e)
            return True
        self._executor.submit(task)

    def close(self):
        # faulthandler.dump_traceback(file=sys.__stdout__, all_threads=True)
        print("[hook] shutdown begin", flush=True)
        self._executor.shutdown(wait=True, cancel_futures=False)
        print("[hook] shutdown done", flush=True)

def install_pyqt_event_hook(app: QtWidgets.QApplication, root_widget=None):
    """
    Устанавливает хук на QApplication для кнопок, вкладок,
    таблиц, чекбоксов, комбобоксов, QLineEdit и QTextEdit.
    Для виджетов ищет внутри root_widget (если None — по всем topLevelWidgets).
    """
    if CFG.Config.user_config.is_developer:
        return
    hook = PyQtEventHook(app)
    app.aboutToQuit.connect(hook.close)
    app.installEventFilter(hook)

    if root_widget is None:
        widgets = app.topLevelWidgets()
    else:
        widgets = [root_widget]

    for w in widgets:
        hook.attach_hooks(w)

    return hook
