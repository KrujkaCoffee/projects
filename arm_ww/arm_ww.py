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

from app_dataclasses import data_app as DTCLS
# локальные модули проекта
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import key_handler





# преобразование UI в PY (можно закомментировать после первого запуска)
CQT.convert_UI_into_PY_c()

from cr_gui import Ui_MainWindow  # GUI сгенерированный через Qt Designer

NAME_MODULE_BASE = "АРМ_складского_работника"
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
        self.name_module = self.NAME_MODULE_BASE


        CFG.Config.user_config.load_user_config(self)
        # добавление действий для сохранения фильтров таблицы
        CMS.add_action_config_save_tbl_filtrs(self, self.ui)
        # загрузка иконок и стилей
        CQT.load_icons(self, 24)
        DTCLS.app_self = self

        import connects

        connects.load_connects(self)
        import general as GEN
        GEN.startup()

    def keyReleaseEvent(self, e):
        key_handler.keyReleaseEvent(self, e.key(), e.modifiers())



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
