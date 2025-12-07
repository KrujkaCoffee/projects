# стандартные библиотеки
import sys
import os

# PyQt5 библиотеки
from PyQt5 import QtWidgets, QtCore, QtGui

try:
    from PyQt5.QtWinExtras import QtWin  # Windows-specific
except ImportError:
    QtWin = None
import project_cust_38.Cust_config as CFG
CFG.load_place()

from dataClass import data_app as DTCLS
# локальные модули проекта
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS

import general as GEN

import key_handler
import connects

# преобразование UI в PY (можно закомментировать после первого запуска)
CQT.convert_UI_into_PY_c()

from cr_gui import Ui_MainWindow  # GUI сгенерированный через Qt Designer

NAME_MODULE_BASE = "КонструкторРС"
VERSION = "0.1"
class mywindow(QtWidgets.QMainWindow):
    # сигнал на изменение размера окна (если нужен)
    resized = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # версия модуля
        self.versia = VERSION

        # название модуля
        self.NAME_MODULE_BASE = NAME_MODULE_BASE
        self.name_module = self.NAME_MODULE_BASE  # f-string здесь не нужен

        # пользовательская конфигурация
        self.USER_CONFIG: CFG.User_config|None = None
        self.place: CFG.Place|None = None
        CFG.Config.user_config.load_user_config(self)


        # добавление действий для сохранения фильтров таблицы
        CMS.add_action_config_save_tbl_filtrs(self, self.ui)
        # загрузка иконок и стилей
        CQT.load_icons(self, 24)
        DTCLS.app_self = self
        GEN.init_guo_qt()
        connects.load_connects(self)


        GEN.load_list_folders(self)
        GEN.load_res_structure(self)
        GEN.load_dse_structure(self)
        GEN.load_nomen_config(self)
        DTCLS.gui_qt.toggle_select()
        #GEN.tbl_list_orders_simulate(self)
        if not CFG.Config.user_config.is_developer:
            GEN.toggle_select_struct(self)





    def keyReleaseEvent(self, e):
        key_handler.keyReleaseEvent(self, e.key(), e.modifiers())

    def eventFilter(self, obj, event):
        # noinspection PyUnresolvedReferences
        if  isinstance(obj, QtWidgets.QDockWidget) and event.type() == QtCore.QEvent.MouseButtonDblClick:
            # noinspection PyUnresolvedReferences
            if event.button() == QtCore.Qt.LeftButton:
                obj.setFloating(True)
                screen = QtWidgets.QApplication.primaryScreen()
                rect = screen.availableGeometry()
                if obj.geometry() == rect:
                    # Уже развернут — вернуть нормальный размер
                    #self.ui.dockNavigator.showNormal()
                    obj.showMaximized()
                else:
                    # Растянуть ровно по рабочей области (без панели задач)
                    obj.setGeometry(rect)
                    obj.show()
                return True

        if isinstance(obj, QtWidgets.QDockWidget) and event.type() == QtCore.QEvent.Resize:
            # Сохранять только если пользователь держит кнопку мыши
            if QtWidgets.QApplication.mouseButtons() == QtCore.Qt.LeftButton:
                CQT.on_section_resized(self, CQT.qt_tmp_dir(), obj)
        return super().eventFilter(obj, event)

app = QtWidgets.QApplication(['', '--no-sandbox'])
# установка AppUserModelID для Windows (для красивого отображения в таскбаре)
if QtWin:
    myappid = f'Powerz.BAG.SustControlWork.{str(VERSION)}'
    # noinspection PyArgumentList
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)

# установка иконки окна
app.setWindowIcon(QtGui.QIcon(os.path.join("icons", "icon.png")))

# установка стиля приложения из конфигурации
S = F.scfg('Stile').split(",")
if len(S) > 1:
    app.setStyle(S[1])
else:
    app.setStyle('Fusion')  # дефолтный стиль

# создаем экземпляр главного окна
application = mywindow()

# установка хука событий для отладки
from project_cust_38.widget_spy import install_pyqt_event_hook

install_pyqt_event_hook(app)

# контроль версии модуля, если проверка не пройдена, закрываем приложение
if not CMS.kontrol_ver(application.versia, NAME_MODULE_BASE):
    sys.exit(1)



# показываем окно на весь экран
application.show()

# старт основного цикла приложения
sys.exit(app.exec())
