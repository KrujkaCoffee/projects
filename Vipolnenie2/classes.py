from __future__ import annotations

import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_SQLite as CSQ
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_emoji as CEMOJ
from app_dataclasses import data_app as DTCLS
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vipoln import mywindow

class State_nar():
    def __init__(self,name,descr,emoj):
        self.name:str = name
        self.descr:str = descr
        self.emoj:str = emoj

    def as_str(self):
        return f'{self.emoj} {self.descr}'


class States_nar():
    new:State_nar = State_nar('new',"Новый",CEMOJ.СтатусыПроизводства.selected.symbol)
    started:State_nar = State_nar("started","В работе",CEMOJ.СтатусыПроизводства.running.symbol)
    pause:State_nar = State_nar("pause","На паузе",CEMOJ.СтатусыПроизводства.progress.symbol)
class Naryad_info():
    def __init__(self, parent_self:mywindow, row_data:dict[str,str|CMS.Composition]):
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
        self.composition:None|CMS.Composition = row_data['composition']
        self._jur:CMS.Jurnal_nar|None=None
        self.calc_obj_jur()
        self.state:State_nar|None = None
        self.calc_state()

        if self.composition:
            self.group_id = ''
            self.group = ''
    @property
    def nom_nar(self):
        if self._nom_nar is None:
            return '-'
        return self._nom_nar

    def calc_obj_jur(self):
        absts = DTCLS.user_abstracts
        fio_fix = CFG.Config.user_config.User.ФИО
        for abst in absts:
            if abst["ФИО"] in (self.fio,self.fio2):
                fio_fix = abst["ФИО"]
        self._jur = CMS.Jurnal_nar(CFG.Config.project.db_naryad, self._nom_nar, fio_fix)


    def calc_state(self):
        if not self._jur.rows:
            self.state =States_nar.new
            return
        if self.is_unclosed:
            self.state = States_nar.started
            return
        self.state = States_nar.pause

    @property
    def is_unclosed(self)->bool:
        if self._jur.is_fregments_unclose():
            return True
        return False

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
        gr_comp_data =  {"Параметр":'Группа', 'Значение':self.group}
        if self.composition:
            gr_comp_data =  {"Параметр":'Раскрой', 'Значение':self.composition.emo_name}
        state = self.state.as_str()
        data = [
            {"Параметр":'Наряд', 'Значение':self.nom_nar},
            {"Параметр":'Статус','Значение':state},
            gr_comp_data,
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