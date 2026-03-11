from __future__ import annotations

import datetime

import app_dataclasses

if __name__ == "__main__":
    quit()

from typing import  TYPE_CHECKING

import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Functions as F
import project_cust_38.api_erp_commands as APIERP
import project_cust_38.Cust_emoji as CEMOJ
from dataclasses import dataclass
import uuid
from app_dataclasses import data_app as DTCLS
from PyQt5 import QtWidgets
from functools import partial

if TYPE_CHECKING:
    from arm_ww import mywindow as mywindow

class Operation():
    def __init__(self,name,text,emo):
        self.name:str=name
        self.text:str=text
        self.emo:str=emo
    def __str__(self):
        return f'{self.emo} {self.text}'

@dataclass
class Operations():
    Receiving:Operation = Operation('Receiving','Получение',CEMOJ.EmojiMain.ДокументыДанные.receiving.symbol)
    Extradition:Operation= Operation('Extradition','Выдача',CEMOJ.EmojiMain.ДокументыДанные.extradition.symbol)
    Shipment:Operation= Operation('Shipment','Отгрузка',CEMOJ.EmojiMain.ДокументыДанные.shipment.symbol)

class Param_doc():
    def __init__(self,type,doc_name,operation):
        self.type:str|None = type
        self.doc_name:str|None = doc_name
        self.operation:Operation|None = operation


@dataclass
class Params_doc():
    rd:Param_doc = Param_doc('Документ.Д_РаспоряжениеНаДоставку','Распоряжение На Доставку',Operations.Shipment)
    vsk:Param_doc = Param_doc('Документ.ДвижениеПродукцииИМатериалов','Движение Продукции И Материалов',Operations.Receiving)
    zmp:Param_doc = Param_doc('Документ.ЗаказМатериаловВПроизводство','Заказ материалов в производство',Operations.Extradition)
    zp:Param_doc = Param_doc('Документ.ЗаказПоставщику','Заказ Поставщику',Operations.Receiving)
    zsb:Param_doc = Param_doc('Документ.ЗаказНаСборку','Заказ на сборку',Operations.Extradition)
    zvp:Param_doc = Param_doc('Документ.ЗаказНаВнутреннееПотребление','Заказ на внутреннее потребление',Operations.Extradition)
    @staticmethod
    def get_param(name:str)->Param_doc:
        doc:Param_doc = eval(f'Params_doc.{name.split("_")[-1]}')
        return  doc

DTCLS.params_doc = Params_doc()

class Storage():
    def __init__(self,text:str,ref:str,is_output:bool):
        self.is_output:bool|None =is_output
        self.ref: str | None = ref
        self.text:str|None =text


    def data_template(self)->dict:
        data = F.get_all_attrs_with_properties(self)
        if self.is_output:
            data['is_output'] = CEMOJ.EmojiMain.СтатусыПроизводства.success_tin.symbol
        else:
            data['is_output'] = ''
        return data
class Storages():
    NAME_CACHE = 'user_filtr_storages'
    def __init__(self):
        self.list_storages:list[Storage] = []
        text = f"""
                ВЫБРАТЬ
        Склады.Наименование КАК text,
        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Склады.Ссылка)) КАК ref_key,
        ВЫБОР
            КОГДА Склады.Наименование ПОДОБНО "%готовой продукции%"
                ТОГДА 1
            ИНАЧЕ 0
        КОНЕЦ КАК output
    ИЗ
        Справочник.Склады КАК Склады
    ГДЕ
        Склады.Ссылка В ИЕРАРХИИ
                (ВЫБРАТЬ
                    Склады.Ссылка КАК Ссылка
                ИЗ
                    Справочник.Склады КАК Склады
                ГДЕ
                    Склады.Наименование ПОДОБНО "%Склады Пауэрз%")
        И Склады.Родитель В
                (ВЫБРАТЬ
                    Склады.Ссылка КАК Ссылка
                ИЗ
                    Справочник.Склады КАК Склады
                ГДЕ
                    Склады.Наименование ПОДОБНО "%получатель-отправитель%")
        И Склады.ПометкаУдаления = ЛОЖЬ
        И Склады.ЭтоГруппа = ЛОЖЬ
        """

        if (data := APIERP.get_wet_request_result(text=text,
                                                 msg_err=f'данные не найдены',lazy_method_huours=24),) is None:
            data = []
        for item in data:
            self.list_storages.append(Storage(item['text'],item['ref_key'],item['output']))

    def save_user_filter(self,data:set):
        CMS.save_tmp_stukt(data,self.NAME_CACHE)

    def load_user_filter(self)->set:
        return CMS.load_tmp_stukt(self.NAME_CACHE,set())

    def req_form_selected(self)->list[dict]:
        rez = []
        list_refs = [_ for _ in self.load_user_filter()]
        cntr = 1
        for ref in list_refs:
            rez.append({
                'ref':ref,
                'var_name':f'stor{cntr}'
            })
            cntr+=1
        return rez





    def get_output(self)->list[Storage]:
        return [_ for _ in self.list_storages if _.is_output]

    def get_storage(self,ref:str)->Storage|None:
        for st in self.list_storages:
            if st.ref == ref:
                return st

    def list_template(self):
        return [_.data_template() for _ in self.list_storages]

DTCLS.storages = Storages()
class Details():
    def __init__(self):
        pass

    def update(self,ref:str,text:str,name_var:str,path_conf_1c:str):
        if not self.is_visible_details():
            return
        ref = APIERP.Ref_wet(name_var, path_conf_1c, ref)
        refs = APIERP.Refs_wet(text)
        refs.add_ref(ref)
        if (data := APIERP.get_wet_request_result(text=text, refs=refs,
                                                  msg_err=f'Данные не найдены')) is None:
            return
        self.set_data(data[0])
    def is_visible_details(self):
        sizes = DTCLS.app_self.ui.splitter_details.sizes()
        if sizes:
            if sizes[1]:
                return True
        return False

    def set_data(self,data:dict,aliases=None):
        self.tbl = DTCLS.app_self.ui.tbl_detail
        CQT.clear_tbl(self.tbl)
        if self.is_visible_details():
            data = [{'Параметр':aliases[k] if aliases and k in aliases else k,'Значение':v} for k,v in data.items() if not k.startswith('_')]
            CQT.fill_wtabl(data,self.tbl,styleSheet=CQT.ERP_CSS,height_row=42)

DTCLS.tbl_details = Details()

class DateFiltr():
    def __init__(self):
        self._start_obj:CQT.QtWidgets.QDateEdit = DTCLS.app_self.ui.de_start
        self._end_obj:CQT.QtWidgets.QDateEdit = DTCLS.app_self.ui.de_end
        self.set_default()
        self._start = None
        self._end = None

    @property
    def erp_start(self)->str:
        str_start = ', '.join([str(_) for _ in [*self.start,0,0,0]])
        return  f'ДАТАВРЕМЯ({str_start})'

    @property
    def erp_end(self) -> str:
        str_end = ', '.join([str(_) for _ in [*self.end, 0, 0, 0]])
        return f'ДАТАВРЕМЯ({str_end})'
    @property
    def start(self)->tuple[int,int,int]:
        return (self._start_obj.date().year(),self._start_obj.date().month(),self._start_obj.date().day())
    @property
    def qstart(self)->CQT.QtCore.QDate:
        return self._start_obj.date()
    @property
    def end(self) -> tuple[int,int,int]:
        return (self._end_obj.date().year(), self._end_obj.date().month(), self._end_obj.date().day())
    @property
    def qend(self)->CQT.QtCore.QDate:
        return self._end_obj.date()
    def set_default(self):
        now = [int(_) for _ in  F.now("%Y-%m-%d").split('-')]
        prev_year = F.now('').year-1
        self.set_start(prev_year,1,1)
        self.set_end(*now)

    def set_start(self,y,m=None,d=None):
        if isinstance(y,int):
            if m is None or d is None:
                raise TypeError
        elif isinstance(y,datetime.date):
            m = y.month
            d = y.day
            y = y.year
        self._set_date(self._start_obj,y,m,d)

    def set_end(self,y,m=None,d=None):
        if isinstance(y,int):
            if m is None or d is None:
                raise TypeError
        elif isinstance(y,datetime.date):
            m = y.month
            d = y.day
            y = y.year
        self._set_date(self._end_obj,y,m,d)
    def _set_date(self, obj:CQT.QtWidgets.QDateEdit, y,m,d):
        obj.setDate(CQT.QtCore.QDate(y,m,d))

DTCLS.dateFiltr = DateFiltr()