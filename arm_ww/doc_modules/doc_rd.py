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
if __name__ == '__main__':
    quit()





def gen_data():
    list_stores = DTCLS.storages.get_output()
    if list_stores:
        store = list_stores[0].text
        store_ref = list_stores[0].ref
    else:
        return []
    refs, filtr_war = GEN.prepare_stor_vars('&stor_out')
    text = f"""ВЫБРАТЬ
            "{store}" КАК Warehouse,
            "{store_ref}" КАК _Warehouse_ref,
            "" КАК Operation,
            Д_РаспоряжениеНаДоставкуТовары.Ссылка.ЖелаемаяДатаОтгрузки КАК Date_shipment,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Д_РаспоряжениеНаДоставкуТовары.Ссылка)) КАК _Foundation_document_ref,
            Д_РаспоряжениеНаДоставкуТовары.Ссылка.Представление КАК Foundation_document,
            Д_РаспоряжениеНаДоставкуТовары.Ссылка.Дата КАК Date_foundation_document,
            ПРЕДСТАВЛЕНИЕ(Д_РаспоряжениеНаДоставкуТовары.Ссылка.Статус) КАК Status_foundation_document,
            "" КАК State,
            Д_РаспоряжениеНаДоставкуТовары.Ссылка.Грузополучатель.НаименованиеПолное КАК Counterparty,
            "Отдел продаж" КАК Recipient_sender,
            Д_РаспоряжениеНаДоставкуТовары.Ссылка.Ответственный.Наименование КАК Initiator,
            ПРЕДСТАВЛЕНИЕ(Д_РаспоряжениеНаДоставкуТовары.Ссылка.НомерПроекта) КАК Project,
            ПРЕДСТАВЛЕНИЕ(Д_РаспоряжениеНаДоставкуТовары.Номенклатура) КАК Nomenclature,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Д_РаспоряжениеНаДоставкуТовары.Номенклатура.Ссылка)) КАК _Nomenclature_ref,
            Д_РаспоряжениеНаДоставкуТовары.Количество КАК Quantity_abs,
            Д_РаспоряжениеНаДоставкуТовары.Номенклатура.ЕдиницаИзмерения КАК Quantity_abs_unit,
            0 КАК Available,
            "" КАК Available_unit
        ИЗ
            Документ.Д_РаспоряжениеНаДоставку.Товары КАК Д_РаспоряжениеНаДоставкуТовары
        ГДЕ 
             Д_РаспоряжениеНаДоставкуТовары.Ссылка.Проведен = ИСТИНА 
	        И Д_РаспоряжениеНаДоставкуТовары.Ссылка.ПометкаУдаления = ЛОЖЬ 
	        {filtr_war}
	           И Д_РаспоряжениеНаДоставкуТовары.Ссылка.ЖелаемаяДатаОтгрузки >= {DTCLS.dateFiltr.erp_start}
            И Д_РаспоряжениеНаДоставкуТовары.Ссылка.ЖелаемаяДатаОтгрузки <= {DTCLS.dateFiltr.erp_end}  
           И Д_РаспоряжениеНаДоставкуТовары.Ссылка.Статус <> ЗНАЧЕНИЕ(ПЕРЕЧИСЛЕНИЕ.Д_СтатусыРаспоряжений.Закрыто)
           И Д_РаспоряжениеНаДоставкуТовары.Ссылка.Грузоотправитель.Ссылка = &Организация_ref
                                                """
    refs.text_req = text
    ref = APIERP.Ref_wet('Организация_ref','Справочники.Организации', DTCLS.app_self.place.Организация_Key)
    refs.add_ref(ref)
    refs.add_ref(APIERP.Ref_wet('stor_out','Справочники.Склады', store_ref))
    lazy = round(DTCLS.lazy_time_munutes / 60, 2)
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
    t.add_column_events('Foundation_document', double_click=True, on_double_click=tbl_cellDoubleClicked)
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
    leftovers = []
    store = ''
    store_ref = ''
    list_stores = DTCLS.storages.get_output()
    if list_stores:
        store = list_stores[0].text
        store_ref = list_stores[0].ref
        leftovers = GEN.calc_leftover(store_ref,use_params=False)

    for item in data:
        item['Date_shipment'] = fix_date(item['Date_shipment'])
        item['Date_foundation_document'] = fix_date(item['Date_foundation_document'])
        item['Warehouse'] = store
        item['_Warehouse_ref'] = store_ref
        item['Operation'] = str(OPERATION)
        if item['_Nomenclature_ref'] in leftovers:
            item['Available'] = leftovers[item['_Nomenclature_ref']]['Available']
            ЕдИзм = leftovers[item['_Nomenclature_ref']]['ЕдИзм']
            item['Available_unit'] = ЕдИзм
        else:
            item['Available_unit'] = item['Quantity_abs_unit']
    return data
@CQT.progress_decorator
def fill_table(app_self,hook_prog_bar):
    tbl = DTCLS.app_self.ui.tbl_rd
    tblf = DTCLS.app_self.ui.tbl_rd_filtr
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
    tbl = DTCLS.app_self.ui.tbl_rd
    row = CQT.get_dict_line_form_tbl(tbl)
    DTCLS.tbl_details.set_data(row,GEN.ALIASES)

def tbl_cellDoubleClicked(t:CQT.TableContext,i:int,clmn_name:str):
    if clmn_name == 'Foundation_document':
        ref = t.current_row().value('_Foundation_document_ref')
        TYPE_DOC = DTCLS.params_doc.get_param(__name__).type
        link = GEN.open_in_1c(ref,TYPE_DOC)