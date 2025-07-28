from __future__ import annotations

import project_cust_38.Cust_Functions as F

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtCore import QSettings
    from PyQt5.QtWidgets import QComboBox, QTableWidget, QLabel, QPushButton


class UserFilter:
    def __init__(
            self,
            settings: QSettings,
            tbl: QTableWidget,
            filtr: QTableWidget,
            combo: QComboBox,
            label: QLabel,
            btn_save: QPushButton,
            name_filter: str
    ) -> None:
        self.settings = settings
        self.tbl = tbl
        self.filter = filtr
        self.combo = combo
        self.label = label
        self.name_filter = name_filter
        self.btn_save = btn_save
        self.btn_save.clicked.connect(self.add_pl_user_filtrs)
        self.combo.activated[int].connect(self.apply_select_filtr)
        self.fill_pl_user_filtrs()

    @property
    def values(self):
        return self.settings.value(self.name_filter, {})

    def apply_select_filtr(self, *args):
        name = self.combo.currentText()
        if name == '':
            dict_fields = {}
            # return
        else:
            if name not in self.values:
                CQT.msgbox(f'Имя не в списке')
                return
            dict_fields = self.values[name]
        CMS.fill_filtr_c(self, self.filter, self.tbl, dict_fields)
        CMS.update_width_filtr(self.tbl, self.filter)
        CMS.apply_filtr_c(self, self.filter, self.tbl)

    @CQT.onerror
    def fill_pl_user_filtrs(self):
        self.combo.clear()
        self.combo.addItem('')
        for key in self.values:
            self.combo.addItem(key)

    @CQT.onerror
    def add_pl_user_filtrs(self, *args):
        name = self.label.text()
        if name == "" or len(name) <= 4:
            CQT.msgbox(f'Имя нового фильтра не достаточной длины')
            return
        dict_fields = dict()
        for j in range(self.filter.columnCount()):
            name_field = self.filter.horizontalHeaderItem(j).text()
            val = self.filter.item(0, j).text()
            dict_fields[name_field] = val
        dict_filtrs = self.values
        dict_filtrs[name] = dict_fields
        self.settings.setValue(self.name_filter, dict_filtrs)
        self.fill_pl_user_filtrs()
        self.label.clear()
        CQT.msgbox(f'Успешно')


    @CQT.onerror
    def save_pl_user_filtrs(self, dict_filtr: dict):
        path_mes_dir = CMS.tmp_dir()
        name_filtr_file = f"{self.name_filter}.pickle"
        self.settings.setValue(self.name_filter, dict_filtr)
        patf = path_mes_dir + F.sep() + name_filtr_file
        F.save_file_pickle(patf, dict_filtr)
        return

    @CQT.onerror
    def del_filt_pl_user_filtrs(self):
        name = self.combo.currentText()
        if name == '':
            return
        dict_filtrs = self.values
        if name in dict_filtrs:
            dict_filtrs.pop(name)
            self.settings.setValue(self.name_filter, dict_filtrs)
            self.fill_pl_user_filtrs()
