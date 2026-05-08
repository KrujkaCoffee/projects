import project_cust_38.Cust_Functions as F
import os
import project_cust_38.Cust_SQLite as CSQ
from PyQt5 import QtWidgets, QtGui, QtCore
import sys


def add_menu(self,name_dir):
    self.ui.action_style = QtWidgets.QMenu('Выбор темы', self.ui.menu)
    font = QtGui.QFont()
    font.setPointSize(16)
    self.ui.action_style.setFont(font)
    self.ui.action_dark = QtWidgets.QAction('Темная', self)
    self.ui.action_dark.triggered.connect(lambda _, x=name_dir: action_dark(self,x))
    self.ui.action_dark.setFont(font)
    self.ui.action_lite = QtWidgets.QAction('Светлая', self)
    self.ui.action_lite.triggered.connect(lambda _, x=name_dir: action_lite(self,x))
    self.ui.action_lite.setFont(font)
    self.ui.action_style.addAction(self.ui.action_dark)
    self.ui.action_style.addAction(self.ui.action_lite)
    self.ui.menu.addAction(self.ui.action_style.menuAction())


def tmp_dir(dir_name):
    ima_module = F.name_of_executable_file_c().split('.')[0]
    if F.existence_file_c(os.sep.join([F.put_po_umolch(), dir_name])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch(), dir_name]))
    if F.existence_file_c(os.sep.join([F.put_po_umolch(), dir_name, ima_module])) == False:
        F.create_dir_c(os.sep.join([F.put_po_umolch(), dir_name, ima_module]))
    return os.sep.join([F.put_po_umolch(), dir_name, ima_module])


def action_dark(self,dir_name):
    if F.existence_file_c("Config\\dark.qss"):
        F.copy_file_c("Config\\dark.qss", tmp_dir(dir_name) + os.sep + 'style.qss')
        CQT.msgbox('Успешно, необходимо перезайти')


def action_lite(self,dir_name):
    if F.existence_file_c("Config\\lite.qss"):
        F.copy_file_c("Config\\lite.qss", tmp_dir(dir_name) + os.sep + 'style.qss')
        CQT.msgbox('Успешно, необходимо перезайти')


def use_CSS_c(spis):
    tmp_dict = dict()
    rez = []
    try:
        for i in range(len(spis)):
            if spis[i] == '' or '{' in spis[i]:
                nach = i
                break
            if spis[i][0] == '$':
                tmp_dict[spis[i].split(' = ')[0]] = spis[i].split(' = ')[1].split(';')[0]

        for key in tmp_dict.keys():
            if '#' in tmp_dict[key]:
                tmp_dict[key] = f'rgb{F.hex_to_rgb(tmp_dict[key][1:])}'

        for i in range(nach, len(spis)):
            for key in tmp_dict.keys():
                spis[i] = spis[i].replace(key, tmp_dict[key])
            rez.append(spis[i])
    except:
        return ''
    return rez


def load_theme(self, name_dir):
    if F.existence_file_c(tmp_dir(name_dir) + os.sep + 'style.qss'):
        spis_korr = use_CSS_c(F.open_file_c(tmp_dir(name_dir) + os.sep + 'style.qss'))
        if spis_korr == '':
            return
        self.setStyleSheet("".join(spis_korr))
