from __future__ import annotations
if __name__ == "__main__":
    quit()
from app_dataclasses import data_app as DTCLS
import main_classes as CLSS

from typing import  TYPE_CHECKING
from PyQt5 import QtWidgets
import project_cust_38.Cust_mes as CMS
import project_cust_38.Cust_Functions as F

import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_Qt as CQT
import project_cust_38.Cust_emoji as CEMOJ
import general as GEN
import project_cust_38.api_erp_commands as APIERP

if TYPE_CHECKING:
    from arm_ww import mywindow


def gen_data():
    refs, filtr_war = GEN.prepare_stor_vars('ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Склад.Ссылка')
    text = f"""
   ВЫБРАТЬ
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Склад)) КАК _Warehouse_ref,
    ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Склад.Представление КАК Warehouse,
    "Операция" КАК Operation,
    ВЫБОР
        КОГДА ЗаказНаВнутреннееПотреблениеТовары.Ссылка.НеОтгружатьЧастями = ИСТИНА
            ТОГДА ЗаказНаВнутреннееПотреблениеТовары.Ссылка.ДатаОтгрузки
        ИНАЧЕ ЗаказНаВнутреннееПотреблениеТовары.ДатаОтгрузки
    КОНЕЦ КАК Date_shipment,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Ссылка)) КАК _Foundation_document_ref,
    ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Ссылка.Представление КАК Foundation_document,
    ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Дата КАК Date_foundation_document,
    ПРЕДСТАВЛЕНИЕ(ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Статус) КАК Status_foundation_document,
    "" КАК State,
    ПРЕДСТАВЛЕНИЕ(ЗаказНаВнутреннееПотреблениеТовары.ВариантОбеспечения) КАК Activity,
    "Ничего" КАК Counterparty,
    ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Подразделение.Представление КАК Recipient_sender,
    ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Ответственный.Представление КАК Initiator,
    ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Сделка.Представление КАК Project,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказНаВнутреннееПотреблениеТовары.Номенклатура)) КАК _Nomenclature_ref,
    ЗаказНаВнутреннееПотреблениеТовары.Номенклатура.Представление КАК Nomenclature,
    ЗаказНаВнутреннееПотреблениеТовары.Характеристика.Представление КАК Nomenclature_params,
    ЗаказНаВнутреннееПотреблениеТовары.КоличествоУпаковок КАК Quantity,
    ВЫБОР КОГДА ЗаказНаВнутреннееПотреблениеТовары.Упаковка = Значение(Справочник.УпаковкиЕдиницыИзмерения.ПустаяСсылка) ТОГДА 
	    ЗаказНаВнутреннееПотреблениеТовары.Номенклатура.ЕдиницаИзмерения.Представление
    ИНАЧЕ
        ЗаказНаВнутреннееПотреблениеТовары.Упаковка.Представление 
    КОНЕЦ КАК Quantity_unit,
    ЗаказНаВнутреннееПотреблениеТовары.Количество КАК Quantity_abs,
    ЗаказНаВнутреннееПотреблениеТовары.Номенклатура.ЕдиницаИзмерения.Представление КАК Quantity_abs_unit,
    "0" КАК Available,
    "" КАК Available_unit
ИЗ
    Документ.ЗаказНаВнутреннееПотребление.Товары КАК ЗаказНаВнутреннееПотреблениеТовары
ГДЕ
    ЗаказНаВнутреннееПотреблениеТовары.Ссылка.ПометкаУдаления = ЛОЖЬ
    И ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Проведен = ИСТИНА
    И ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Статус <> ЗНАЧЕНИЕ(Перечисление.СтатусыВнутреннихЗаказов.Закрыт)
    И ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Организация = &Организация_ref
    {filtr_war}
    И ВЫБОР
        КОГДА ЗаказНаВнутреннееПотреблениеТовары.Ссылка.НеОтгружатьЧастями = ИСТИНА
            ТОГДА ЗаказНаВнутреннееПотреблениеТовары.Ссылка.ДатаОтгрузки
        ИНАЧЕ ЗаказНаВнутреннееПотреблениеТовары.ДатаОтгрузки
    КОНЕЦ >= {DTCLS.dateFiltr.erp_start}
    И ВЫБОР
        КОГДА ЗаказНаВнутреннееПотреблениеТовары.Ссылка.НеОтгружатьЧастями = ИСТИНА
            ТОГДА ЗаказНаВнутреннееПотреблениеТовары.Ссылка.ДатаОтгрузки
        ИНАЧЕ ЗаказНаВнутреннееПотреблениеТовары.ДатаОтгрузки
    КОНЕЦ <= {DTCLS.dateFiltr.erp_end}
               """
    refs.text_req = text
    refs.add_ref(APIERP.Ref_wet('Организация_ref','Справочники.Организации',
                                DTCLS.app_self.place.Организация_Key))
    lazy = round(DTCLS.lazy_time_munutes/60,2)
    TYPE_DOC_NAME = DTCLS.params_doc.get_param(__name__).doc_name
    if (data := APIERP.get_wet_request_result(text=text,refs=refs,lazy_method_huours=lazy,
                                             msg_err=f'{TYPE_DOC_NAME} не найдены')) is None:
        return []
    return data

def oform(tbl:QtWidgets.QTableWidget):
    t = CQT.TableContext(tbl)
    for k in t.nf.keys():
        if k.startswith('_'):
            t.hide(k)
    t.hide('Counterparty')
    t.add_column_events('Foundation_document',double_click=True,on_double_click=tbl_cellDoubleClicked)
    clr_good = CMS.Color_tbl(90).rgb
    for row in t.rows():
        if F.valm(row.value('Available')) >= F.valm(row.value('Quantity_abs')):
            row.set_color_background(*clr_good)
            row.set_value('State',CEMOJ.EmojiMain.СтатусыПроизводства.normal.symbol)

def fix_date(date:str):
    if date:
        return  F.dateStrToStr(date,
                                                   format="%Y-%m-%dT%H:%M:%S",
                                                   format_out="%d.%m.%Y",
                                                   onerror='')
    return date
def prep(data:list[dict]):
    OPERATION = DTCLS.params_doc.get_param(__name__).operation
    dict_stores_ref = dict()
    for item in data:
        dict_stores_ref[item['_Warehouse_ref']] = None

    dict_stores_ref = GEN.calc_leftover(list(dict_stores_ref.keys()), use_params=True)

    for item in data:
        store = ''
        leftovers = dict()
        store_ref = item['_Warehouse_ref']
        if store_ref and store_ref in dict_stores_ref:
            leftovers = dict_stores_ref[store_ref]
        if store_ref and store_ref in dict_stores_ref:
            store_obj = DTCLS.storages.get_storage(store_ref)
            if store_obj:
                store = store_obj.text
        item['Date_shipment'] = fix_date(item['Date_shipment'])
        item['Date_foundation_document'] = fix_date(item['Date_foundation_document'])
        item['Warehouse'] = store
        item['_Warehouse_ref'] = store_ref
        item['Operation'] = str(OPERATION)
        key = (item['_Nomenclature_ref'], item['Nomenclature_params'])
        if key in leftovers:
            item['Available'] = leftovers[key]['Available']
            ЕдИзм = leftovers[key]['ЕдИзм']
            item['Available_unit'] = ЕдИзм
        else:
            item['Available_unit'] = item['Quantity_abs_unit']

    return data
@CQT.progress_decorator
def fill_table(app_self,hook_prog_bar):
    tbl = DTCLS.app_self.ui.tbl_zvp
    tblf = DTCLS.app_self.ui.tbl_zvp_filtr
    hook_prog_bar.open()
    hook_prog_bar.set(0)
    hook_prog_bar.text('Получение данных')
    CQT.clear_tbl(tbl)
    data = gen_data()
    if not data:
        hook_prog_bar.close()
        return
    hook_prog_bar.text('Обработка данных')
    hook_prog_bar.set(30)
    data = prep(data)
    CQT.fill_wtabl(data,tbl,styleSheet=CQT.ERP_EDIT_CSS,sortingEnabled=True,auto_type=True,aliases_header=GEN.ALIASES,
                   selectionBehavior='SelectRows',colorful_edit=False)
    CQT.load_column_widths(DTCLS.app_self, tbl, CMS.tmp_dir())
    hook_prog_bar.text('Оформление таблицы')
    hook_prog_bar.set(90)
    oform(tbl)
    CMS.fill_filtr_c(DTCLS.app_self, tblf, tbl)
    hook_prog_bar.close()

def tbl_select_itemSelectionChanged():
    tbl = DTCLS.app_self.ui.tbl_zvp
    row = CQT.get_dict_line_form_tbl(tbl)
    DTCLS.tbl_details.set_data(row,GEN.ALIASES)

def tbl_cellDoubleClicked(t:CQT.TableContext,i:int,clmn_name:str):
    if clmn_name == 'Foundation_document':
        ref = t.current_row().value('_Foundation_document_ref')
        TYPE_DOC = DTCLS.params_doc.get_param(__name__).type
        link = GEN.open_in_1c(ref,TYPE_DOC)
