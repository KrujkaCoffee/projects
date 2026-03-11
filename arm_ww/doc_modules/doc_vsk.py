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
    refs, filtr_war = GEN.prepare_stor_vars('ДвижениеПродукцииИМатериаловТовары.Ссылка.Получатель.Ссылка')
    text = f"""
    ВЫБРАТЬ РАЗРЕШЕННЫЕ
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Ссылка КАК Ссылка,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Дата КАК Date_shipment,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Ссылка КАК Foundation_document,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Дата КАК Date_foundation_document,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Статус КАК Status_foundation_document,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Отправитель.Представление КАК Recipient_sender,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Ответственный.Представление КАК Initiator,
    ДвижениеПродукцииИМатериаловТовары.Номенклатура КАК Nomenclature,
    ДвижениеПродукцииИМатериаловТовары.Характеристика.Представление КАК Nomenclature_params,
    ДвижениеПродукцииИМатериаловТовары.Упаковка КАК Упаковка,
    ДвижениеПродукцииИМатериаловТовары.КоличествоУпаковок КАК Quantity,
    ДвижениеПродукцииИМатериаловТовары.Количество КАК Quantity_abs,
    ЕСТЬNULL(СУММА(ПриходныйОрдерНаТоварыТовары.КоличествоУпаковок), 0) КАК КоличествоУпаковок,
    ПриходныйОрдерНаТоварыТовары.Упаковка КАК УпаковкаОрдер,
    ЕСТЬNULL(СУММА(ПриходныйОрдерНаТоварыТовары.Количество), 0) КАК Количество
ПОМЕСТИТЬ ВТ_Ордера
ИЗ
    Документ.ДвижениеПродукцииИМатериалов.Товары КАК ДвижениеПродукцииИМатериаловТовары
        ЛЕВОЕ СОЕДИНЕНИЕ Документ.ПриходныйОрдерНаТовары.Товары КАК ПриходныйОрдерНаТоварыТовары
        ПО (ДвижениеПродукцииИМатериаловТовары.Ссылка.Ссылка = ПриходныйОрдерНаТоварыТовары.Ссылка.Распоряжение
                И ДвижениеПродукцииИМатериаловТовары.Номенклатура = ПриходныйОрдерНаТоварыТовары.Номенклатура
                И ПриходныйОрдерНаТоварыТовары.Ссылка.Проведен = ИСТИНА
                И ПриходныйОрдерНаТоварыТовары.Ссылка.ПометкаУдаления = ЛОЖЬ)
ГДЕ
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Организация = &Организация_ref
    {filtr_war}
    И ДвижениеПродукцииИМатериаловТовары.Ссылка.Проведен = ИСТИНА
    И ДвижениеПродукцииИМатериаловТовары.Ссылка.ПометкаУдаления = ЛОЖЬ
    И ДвижениеПродукцииИМатериаловТовары.Ссылка.ХозяйственнаяОперация = ЗНАЧЕНИЕ(Перечисление.ХозяйственныеОперации.ВозвратМатериаловИзКладовой)
    И ДвижениеПродукцииИМатериаловТовары.Ссылка.Дата >= {DTCLS.dateFiltr.erp_start}
    И ДвижениеПродукцииИМатериаловТовары.Ссылка.Дата <= {DTCLS.dateFiltr.erp_end}

СГРУППИРОВАТЬ ПО
    ДвижениеПродукцииИМатериаловТовары.Ссылка,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Дата,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Статус,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Ссылка,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Отправитель.Представление,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Ответственный.Представление,
    ДвижениеПродукцииИМатериаловТовары.Номенклатура,
    ДвижениеПродукцииИМатериаловТовары.Характеристика.Представление,
    ДвижениеПродукцииИМатериаловТовары.КоличествоУпаковок,
    ДвижениеПродукцииИМатериаловТовары.Упаковка,
    ДвижениеПродукцииИМатериаловТовары.Количество,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Ссылка,
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Дата,
    ПриходныйОрдерНаТоварыТовары.Упаковка
;

////////////////////////////////////////////////////////////////////////////////
ВЫБРАТЬ
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВТ_Ордера.Ссылка.Получатель.Ссылка)) КАК _Warehouse_ref,
    ВТ_Ордера.Ссылка.Получатель.Представление КАК Warehouse,
    "операция" КАК Operation,
    ВТ_Ордера.Date_shipment КАК Date_shipment,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВТ_Ордера.Foundation_document.Ссылка)) КАК _Foundation_document_ref,
    ВТ_Ордера.Foundation_document.Представление КАК Foundation_document,
    ВТ_Ордера.Date_foundation_document КАК Date_foundation_document,
    ПРЕДСТАВЛЕНИЕ(ВТ_Ордера.Status_foundation_document) КАК Status_foundation_document,
    "" КАК State,
    "Контрагент" КАК Counterparty,
    ВТ_Ордера.Recipient_sender КАК Recipient_sender,
    ВТ_Ордера.Initiator КАК Initiator,
    "Сделка" КАК Project,
    ВТ_Ордера.Nomenclature КАК Nomenclature,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВТ_Ордера.Nomenclature)) КАК _Nomenclature_ref,
    ВТ_Ордера.Nomenclature_params КАК Nomenclature_params,
    ВТ_Ордера.Quantity КАК Quantity,
    ВЫБОР КОГДА ВТ_Ордера.Упаковка = Значение(Справочник.УпаковкиЕдиницыИзмерения.ПустаяСсылка) ТОГДА 
	    ВТ_Ордера.Nomenclature.ЕдиницаИзмерения.Представление
    ИНАЧЕ
        ВТ_Ордера.Упаковка.Представление 
    КОНЕЦ КАК Quantity_unit,
    ВТ_Ордера.Quantity_abs КАК Quantity_abs,
    ВТ_Ордера.Nomenclature.ЕдиницаИзмерения.Представление КАК Quantity_abs_unit,
    ВТ_Ордера.Количество КАК Order_Quantity_abs,
    ВТ_Ордера.Nomenclature.ЕдиницаИзмерения.Представление КАК Order_Quantity_abs_unit,
    ВТ_Ордера.КоличествоУпаковок КАК Order_Quantity,
    ВЫБОР КОГДА  ВТ_Ордера.УпаковкаОрдер = Значение(Справочник.УпаковкиЕдиницыИзмерения.ПустаяСсылка) ТОГДА 
	    ВТ_Ордера.Nomenclature.ЕдиницаИзмерения.Представление
    ИНАЧЕ
        ВТ_Ордера.УпаковкаОрдер.Представление 
    КОНЕЦ КАК Order_Quantity_unit,
    0 КАК Available,
    "" КАК Available_unit
ИЗ
    ВТ_Ордера КАК ВТ_Ордера
    
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
    t.add_column_events('Foundation_document',double_click=True,on_double_click=tbl_cellDoubleClicked)
    #clr_good = CMS.Color_tbl(90).rgb
    #for row in t.rows():
    #    if F.valm(row.value('Available')) >= F.valm(row.value('Quantity')):
    #        row.set_color_background(*clr_good)
    #        row.set_value('State',CEMOJ.EmojiMain.СтатусыПроизводства.normal.symbol)

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
    tbl = DTCLS.app_self.ui.tbl_vsk
    tblf = DTCLS.app_self.ui.tbl_vsk_filtr
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
    tbl = DTCLS.app_self.ui.tbl_vsk
    row = CQT.get_dict_line_form_tbl(tbl)
    DTCLS.tbl_details.set_data(row,GEN.ALIASES)

def tbl_cellDoubleClicked(t:CQT.TableContext,i:int,clmn_name:str):
    if clmn_name == 'Foundation_document':
        ref = t.current_row().value('_Foundation_document_ref')
        TYPE_DOC = DTCLS.params_doc.get_param(__name__).type
        link = GEN.open_in_1c(ref,TYPE_DOC)
