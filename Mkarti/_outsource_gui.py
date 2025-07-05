# -*- coding: utf-8 -*-
import copy
import pprint

import project_cust_38.Cust_Functions as F
import project_cust_38.xml_v_drevo as XML
from PyQt5 import QtWidgets, QtCore, QtGui, QtDesigner
from PyQt5.QtWinExtras import QtWin
import os
import project_cust_38.Cust_Qt as CQT
import data_class

CQT.convert_UI_into_PY_c()
from mk_gui import Ui_MainWindow  # импорт нашего сгенерированного файла

import sys
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Excel as CEX
import project_cust_38.Zamechaniya as ZMCH
import obespechenie as OBSP
import industrial_capacity as IND
import export_docs_mkarts as EXPD
import Selector_conversation as SLCT
import calculate_vo as CVO
import resourse_board as RESB
import kal_plan as KPL
import gui_kal_plan as GKPL
import gui_vol_plan as GVKPL
import pl_user_fiters as KPLUF
import project_cust_38.Cust_b24 as CB24
import interaction_googlesheets
import invest_pr as INVPR
import state_prod as STATE
import chpy_calcs as CHPY
import make_poz_plan as POZPL
import recalc_norm as RECLC
import equipment_rc as EQRC
import tabel_edit as TABEL

try:
    import pl_xl_loader as PXL
except Exception as e:
    print('Error import pl_xl_loader')


# TODO """разложить поэтапно порядок постанвоки и подготовки проектив +
# доработать сообщенияв части регламнтов
# включить расчет сроков выдачи КД с учетом срока обсепечения
# фиксировать Пдату Кд от ПДО и Пдату Кд от КО в разыне поля.
# добавить в чат новаковскую, МХ
# """


class mywindow(QtWidgets.QMainWindow):
    resized = QtCore.pyqtSignal()

    def __init__(self):
        super(mywindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.versia = '1.0.0.1.2'
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.NAME_MODULE_BASE = "Создание маршрутных карт"
        self.name_module = f'{self.NAME_MODULE_BASE}'
        # enable custom window hint
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint)



app = QtWidgets.QApplication(['', '--no-sandbox'])

myappid = 'Powerz.BAG.SustControlWork.0.0.0'  # !!!

QtWin.setCurrentProcessExplicitAppUserModelID(myappid)
app.setWindowIcon(QtGui.QIcon(os.path.join("icons", "icon.png")))

S = F.scfg('Stile').split(",")
app.setStyle(S[0])

application = mywindow()
# =============================================================
if CMS.kontrol_ver(application.versia, 'МКарты') == False:
    quit()
# =============================================================

application.showMaximized()

sys.exit(app.exec())
# pyinstaller.exe --onefile --icon=1.ico --noconsole MKart.py
