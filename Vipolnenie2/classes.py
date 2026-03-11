from __future__ import annotations

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vipoln import mywindow

class Naryad_info():
    def __init__(self, parent_self:mywindow, row_data:dict[str,str]):
        self.parent:mywindow = parent_self
        self._nom_nar:int|None = None
        self.nom_nar:int|str|None = row_data['Пномер']
        self.group:str|None = row_data['Группа']
        self.group_id:str|None = row_data['_id']
        self.sozdan:None|str = row_data['Дата']
        self.proj:None|str = row_data['Номер_проекта']
        self.zp:None|str = row_data['Номер_заказа']
        self.vrem:None|str = row_data['Твремя']
        self._mk:None|str = row_data['Номер_мк']
        self.fio:None|str = row_data['ФИО']
        self.fio2:None|str = row_data['ФИО2']
        self._zadanie_wet:None|str = row_data['Задание']
        self.zadanie:None|str = self._zadanie_wet.replace('LF', '\n')
    @property
    def nom_nar(self):
        if self._nom_nar is None:
            return '-'
        return self._nom_nar

    @property
    def mk(self):
        if self._mk is None:
            return None
        if self._mk =='-':
            return None
        return int(self._mk)
    @nom_nar.setter
    def nom_nar(self,val):
        self._nom_nar = None
        if F.is_numeric(val):
            self._nom_nar = int(val)

    def __eq__(self, other):
        if self._nom_nar is None:
            return False
        if str(self._nom_nar) == str(other):
            return True
        return False

    def fill_tbl(self):
        tbl = self.parent.ui.tbl_descr_nar
        data = [
            {"Параметр":'Наряд', 'Значение':self.nom_nar},
            {"Параметр":'Группа', 'Значение':self.group},
            {"Параметр":'Создан', 'Значение':self.sozdan},
            {"Параметр":'Проект', 'Значение':self.proj},
            {"Параметр":'Заказ', 'Значение':self.zp},
            {"Параметр":'Норма, мин.', 'Значение':self.vrem},
            {"Параметр":'Номер МК', 'Значение':self.mk},
            {"Параметр":'Исполнитель 1', 'Значение':self.fio},
            {"Параметр":'Исполнитель 2', 'Значение':self.fio2},
        ]
        with CQT.table_updating(tbl):
            CQT.fill_wtabl(data,tbl,set_editeble_col_nomera={},hide_head_column=True,hide_head_rows=True,
                           styleSheet=CQT.MES_CSS,ogr_maxshir_kol=500,font_size=12)


        linked_text = self.parent.unpack_links_to_documents(task_text=self.zadanie, label=self.parent.ui.textBrowser_zadanie)
        self.parent.ui.textBrowser_zadanie.setHtml(linked_text)

    def clear(self):
        tbl = self.parent.ui.tbl_descr_nar
        CQT.clear_tbl(tbl)
        self.parent.ui.textBrowser_zadanie.clear()