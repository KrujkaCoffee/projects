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



OPERATION = CLSS.Operations.Extradition

def gen_data():
    list_stores = DTCLS.storages.get_output()
    if list_stores:
        store = list_stores[0].text
        store_ref = list_stores[0].ref
    else:
        return []

    refs, filtr_war = GEN.prepare_stor_vars('&stor_out')
    refs, filtr_war_vsk = GEN.prepare_stor_vars('ДвижениеПродукцииИМатериаловТовары.Ссылка.Получатель.Ссылка')
    refs, filtr_war_zmp = GEN.prepare_stor_vars('ЗаказМатериаловВПроизводствоТовары.Ссылка.Склад.Ссылка')
    refs, filtr_war_zp = GEN.prepare_stor_vars('ЗаказПоставщикуТовары.Склад.Ссылка')
    refs, filtr_war_zsb = GEN.prepare_stor_vars('ЗаказНаСборкуТовары.Ссылка.Склад.Ссылка')
    refs, filtr_war_zvp = GEN.prepare_stor_vars('ЗаказНаВнутреннееПотреблениеТовары.Ссылка.Склад.Ссылка')
    text = f"""
    ВЫБРАТЬ 
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
    ДвижениеПродукцииИМатериаловТовары.Количество КАК Quantity_abs

ПОМЕСТИТЬ ВТ_Ордера
ИЗ
    Документ.ДвижениеПродукцииИМатериалов.Товары КАК ДвижениеПродукцииИМатериаловТовары
        
ГДЕ
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Организация = &Организация_ref
    {filtr_war_vsk}
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
    ДвижениеПродукцииИМатериаловТовары.Ссылка.Дата
;

////////////////////////////////////////////////////////////////////////////////
    
        ВЫБРАТЬ РАЗРЕШЕННЫЕ
                "" КАК doc_name,
                "tab_rd" КАК _tab_name,
                "{store_ref}" КАК _Warehouse_ref,
                "{store}" КАК Warehouse,
                "" КАК Operation,
                Д_РаспоряжениеНаДоставкуТовары.Ссылка.ЖелаемаяДатаОтгрузки КАК Date_shipment,
                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Д_РаспоряжениеНаДоставкуТовары.Ссылка)) КАК _Foundation_document_ref,
                Д_РаспоряжениеНаДоставкуТовары.Ссылка.Представление КАК Foundation_document,
                Д_РаспоряжениеНаДоставкуТовары.Ссылка.Дата КАК Date_foundation_document,
                ПРЕДСТАВЛЕНИЕ(Д_РаспоряжениеНаДоставкуТовары.Ссылка.Статус) КАК Status_foundation_document,
                "" КАК State,
                "" КАК Activity,
                Д_РаспоряжениеНаДоставкуТовары.Ссылка.Грузополучатель.НаименованиеПолное КАК Counterparty,
                "Отдел продаж" КАК Recipient_sender,
                Д_РаспоряжениеНаДоставкуТовары.Ссылка.Ответственный.Наименование КАК Initiator,
                ПРЕДСТАВЛЕНИЕ(Д_РаспоряжениеНаДоставкуТовары.Ссылка.НомерПроекта) КАК Project,
                ПРЕДСТАВЛЕНИЕ(Д_РаспоряжениеНаДоставкуТовары.Номенклатура) КАК Nomenclature,
                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Д_РаспоряжениеНаДоставкуТовары.Номенклатура.Ссылка)) КАК _Nomenclature_ref,
                "" КАК Nomenclature_params,
                "" КАК Quantity,
                "" КАК Quantity_unit,
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
               
    ОБЪЕДИНИТЬ ВСЕ

                
        ВЫБРАТЬ
            "" КАК doc_name,
            "tab_vsk" КАК _tab_name,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВТ_Ордера.Ссылка.Получатель.Ссылка)) КАК _Warehouse_ref,
            ВТ_Ордера.Ссылка.Получатель.Представление КАК Warehouse,
            "операция" КАК Operation,
            ВТ_Ордера.Date_shipment КАК Date_shipment,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВТ_Ордера.Foundation_document.Ссылка)) КАК _Foundation_document_ref,
            ВТ_Ордера.Foundation_document.Представление КАК Foundation_document,
            ВТ_Ордера.Date_foundation_document КАК Date_foundation_document,
            ПРЕДСТАВЛЕНИЕ(ВТ_Ордера.Status_foundation_document) КАК Status_foundation_document,
            "" КАК State,
            "" КАК Activity,
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
            0 КАК Available,
            "" КАК Available_unit
        ИЗ
            ВТ_Ордера КАК ВТ_Ордера
            
    ОБЪЕДИНИТЬ ВСЕ
        ВЫБРАТЬ
        "" КАК doc_name,
        "tab_zmp" КАК _tab_name,
        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказМатериаловВПроизводствоТовары.Ссылка.Склад.Ссылка)) КАК _Warehouse_ref,
        ЗаказМатериаловВПроизводствоТовары.Ссылка.Склад.Представление КАК Warehouse,
        "Операция" КАК Operation,
        ЗаказМатериаловВПроизводствоТовары.НачалоОтгрузки КАК Date_shipment,
        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказМатериаловВПроизводствоТовары.Ссылка.Ссылка)) КАК _Foundation_document_ref,
        ЗаказМатериаловВПроизводствоТовары.Ссылка.Ссылка.Представление КАК Foundation_document,
        ЗаказМатериаловВПроизводствоТовары.Ссылка.Дата КАК Date_foundation_document,
        ПРЕДСТАВЛЕНИЕ(ЗаказМатериаловВПроизводствоТовары.Ссылка.Статус) КАК Status_foundation_document,
        "" КАК State,
        "" КАК Activity,
        "Контрагент" КАК Counterparty,
        ЗаказМатериаловВПроизводствоТовары.Ссылка.ЦеховаяКладовая.Представление КАК Recipient_sender,
        ЗаказМатериаловВПроизводствоТовары.Ссылка.Ответственный.Представление КАК Initiator,
        ЗаказМатериаловВПроизводствоТовары.Ссылка.ДокументОснование.Представление КАК Project,
        ЗаказМатериаловВПроизводствоТовары.Номенклатура.Представление КАК Nomenclature,
        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказМатериаловВПроизводствоТовары.Номенклатура.Ссылка)) КАК _Nomenclature_ref,
        ЗаказМатериаловВПроизводствоТовары.Характеристика.Представление КАК Nomenclature_params,
        ЗаказМатериаловВПроизводствоТовары.КоличествоУпаковок КАК Quantity,
        ВЫБОР КОГДА ЗаказМатериаловВПроизводствоТовары.Упаковка = Значение(Справочник.УпаковкиЕдиницыИзмерения.ПустаяСсылка) ТОГДА 
            ЗаказМатериаловВПроизводствоТовары.Номенклатура.ЕдиницаИзмерения.Представление
        ИНАЧЕ
            ЗаказМатериаловВПроизводствоТовары.Упаковка.Представление 
        КОНЕЦ КАК Quantity_unit,
        ЗаказМатериаловВПроизводствоТовары.Количество КАК Quantity_abs,
        ЗаказМатериаловВПроизводствоТовары.Номенклатура.ЕдиницаИзмерения.Представление КАК Quantity_abs_unit,
        "0" КАК Available,
        "" КАК Available_unit
    ИЗ
        Документ.ЗаказМатериаловВПроизводство.Товары КАК ЗаказМатериаловВПроизводствоТовары
    ГДЕ
        ЗаказМатериаловВПроизводствоТовары.Ссылка.ПометкаУдаления = ЛОЖЬ
        И ЗаказМатериаловВПроизводствоТовары.Ссылка.Проведен = ИСТИНА
        И ЗаказМатериаловВПроизводствоТовары.Ссылка.Статус <> ЗНАЧЕНИЕ(Перечисление.СтатусыЗаказовМатериаловВПроизводство.Закрыт)
        И ЗаказМатериаловВПроизводствоТовары.Ссылка.Организация = &Организация_ref
        {filtr_war_zmp}
        И ЗаказМатериаловВПроизводствоТовары.НачалоОтгрузки >= {DTCLS.dateFiltr.erp_start}
        И ЗаказМатериаловВПроизводствоТовары.НачалоОтгрузки <= {DTCLS.dateFiltr.erp_end}
    
    ОБЪЕДИНИТЬ ВСЕ
    
            ВЫБРАТЬ
        "" КАК doc_name,
        "tab_zp" КАК _tab_name,
        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказПоставщикуТовары.Склад.Ссылка)) КАК _Warehouse_ref,
        ЗаказПоставщикуТовары.Склад.Представление КАК Warehouse,
        "" КАК Operation,
        ЗаказПоставщикуТовары.ДатаОтгрузки КАК Date_shipment,
        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказПоставщикуТовары.Ссылка.Ссылка)) КАК _Foundation_document_ref,
        ЗаказПоставщикуТовары.Ссылка.Ссылка.Представление КАК Foundation_document,
        ЗаказПоставщикуТовары.Ссылка.Дата КАК Date_foundation_document,
        ПРЕДСТАВЛЕНИЕ(ЗаказПоставщикуТовары.Ссылка.Статус) КАК Status_foundation_document,
        "" КАК State,
        "" КАК Activity,
        ЗаказПоставщикуТовары.Ссылка.Партнер.Представление КАК Counterparty,
        ЗаказПоставщикуТовары.Ссылка.Подразделение.Представление КАК Recipient_sender,
        ЗаказПоставщикуТовары.Ссылка.Менеджер.Представление КАК Initiator,
        ЗаказПоставщикуТовары.Ссылка.Сделка.Представление КАК Project,
        ЗаказПоставщикуТовары.Номенклатура.Представление КАК Nomenclature,
        ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказПоставщикуТовары.Номенклатура.Ссылка)) КАК _Nomenclature_ref,
        ЗаказПоставщикуТовары.Характеристика.Представление КАК Nomenclature_params,
        ЗаказПоставщикуТовары.КоличествоУпаковок КАК Quantity,
        ВЫБОР КОГДА ЗаказПоставщикуТовары.Упаковка = Значение(Справочник.УпаковкиЕдиницыИзмерения.ПустаяСсылка) ТОГДА 
            ЗаказПоставщикуТовары.Номенклатура.ЕдиницаИзмерения.Представление
        ИНАЧЕ
            ЗаказПоставщикуТовары.Упаковка.Представление 
        КОНЕЦ КАК Quantity_unit,
        ЗаказПоставщикуТовары.Количество КАК Quantity_abs,
        ЗаказПоставщикуТовары.Номенклатура.ЕдиницаИзмерения.Представление КАК Quantity_abs_unit,
        "0" КАК Available,
        "" КАК Available_unit
    ИЗ
        Документ.ЗаказПоставщику.Товары КАК ЗаказПоставщикуТовары
    ГДЕ
        ЗаказПоставщикуТовары.Ссылка.Организация = &Организация_ref
        {filtr_war_zp}
        И ЗаказПоставщикуТовары.Ссылка.Проведен = ИСТИНА 
        И ЗаказПоставщикуТовары.Ссылка.ПометкаУдаления = ЛОЖЬ 
        И ЗаказПоставщикуТовары.Ссылка.ДатаОтгрузки >= {DTCLS.dateFiltr.erp_start}
        И ЗаказПоставщикуТовары.Ссылка.ДатаОтгрузки <= {DTCLS.dateFiltr.erp_end}  
        И
        ЗаказПоставщикуТовары.Ссылка.Статус <> ЗНАЧЕНИЕ(ПЕРЕЧИСЛЕНИЕ.СтатусыЗаказовПоставщикам.Закрыт)
                                                    
    
    ОБЪЕДИНИТЬ ВСЕ
    
        ВЫБРАТЬ 
        "" КАК doc_name,
        "tab_zsb" КАК _tab_name,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказНаСборкуТовары.Ссылка.Склад)) КАК _Warehouse_ref,
    ЗаказНаСборкуТовары.Ссылка.Склад.Представление КАК Warehouse,
    "Операция" КАК Operation,
    ЗаказНаСборкуТовары.Ссылка.ОкончаниеСборкиРазборки КАК Date_shipment,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказНаСборкуТовары.Ссылка.Ссылка)) КАК _Foundation_document_ref,
    ЗаказНаСборкуТовары.Ссылка.Ссылка.Представление КАК Foundation_document,
    ЗаказНаСборкуТовары.Ссылка.Дата КАК Date_foundation_document,
    ПРЕДСТАВЛЕНИЕ(ЗаказНаСборкуТовары.Ссылка.Статус) КАК Status_foundation_document,
    "" КАК State,
    ПРЕДСТАВЛЕНИЕ(ЗаказНаСборкуТовары.ВариантОбеспечения) КАК Activity,
    "Ничего" КАК Counterparty,
    ЗаказНаСборкуТовары.Ссылка.Подразделение.Представление КАК Recipient_sender,
    ЗаказНаСборкуТовары.Ссылка.Ответственный.Представление КАК Initiator,
    ЗаказНаСборкуТовары.Ссылка.Сделка.Представление КАК Project,
    ЗаказНаСборкуТовары.Номенклатура.Представление КАК Nomenclature,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказНаСборкуТовары.Номенклатура)) КАК _Nomenclature_ref,
    ЗаказНаСборкуТовары.Характеристика.Представление КАК Nomenclature_params,
    ЗаказНаСборкуТовары.КоличествоУпаковок КАК Quantity,
    ВЫБОР КОГДА ЗаказНаСборкуТовары.Упаковка = Значение(Справочник.УпаковкиЕдиницыИзмерения.ПустаяСсылка) ТОГДА 
	    ЗаказНаСборкуТовары.Номенклатура.ЕдиницаИзмерения.Представление
    ИНАЧЕ
        ЗаказНаСборкуТовары.Упаковка.Представление 
    КОНЕЦ КАК Quantity_unit,
    ЗаказНаСборкуТовары.Количество КАК Quantity_abs,
    ЗаказНаСборкуТовары.Номенклатура.ЕдиницаИзмерения.Представление КАК Quantity_abs_unit,
    "0" КАК Available,
    "" КАК Available_unit
ИЗ
    Документ.ЗаказНаСборку.Товары КАК ЗаказНаСборкуТовары
        ГДЕ 
             ЗаказНаСборкуТовары.Ссылка.Проведен = ИСТИНА 
	        И ЗаказНаСборкуТовары.Ссылка.ПометкаУдаления = ЛОЖЬ 
	           И ЗаказНаСборкуТовары.Ссылка.ОкончаниеСборкиРазборки >= {DTCLS.dateFiltr.erp_start}
            И ЗаказНаСборкуТовары.Ссылка.ОкончаниеСборкиРазборки <= {DTCLS.dateFiltr.erp_end}  
           И ЗаказНаСборкуТовары.Ссылка.Статус <> ЗНАЧЕНИЕ(ПЕРЕЧИСЛЕНИЕ.СтатусыВнутреннихЗаказов.Закрыт)
           И ЗаказНаСборкуТовары.Ссылка.Организация.Ссылка = &Организация_ref
	        {filtr_war_zsb}    
                                                    
                        
    
    ОБЪЕДИНИТЬ ВСЕ
    
      
    ВЫБРАТЬ
    "" КАК doc_name,
    "tab_zvp" КАК _tab_name,
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
    ЗаказНаВнутреннееПотреблениеТовары.Номенклатура.Представление КАК Nomenclature,
    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ЗаказНаВнутреннееПотреблениеТовары.Номенклатура)) КАК _Nomenclature_ref,
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
    {filtr_war_zvp}
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
    refs.add_ref(APIERP.Ref_wet('stor_out', 'Справочники.Склады', store_ref))
    lazy = round(DTCLS.lazy_time_munutes/60,2)
    if (data := APIERP.get_wet_request_result(text=text,refs=refs,lazy_method_huours=lazy,
                                             msg_err=f'Данные не найдены')) is None:
        return []
    return data

def oform(tbl:QtWidgets.QTableWidget):
    t = CQT.TableContext(tbl)
    for k in t.nf.keys():
        if k.startswith('_'):
            t.hide(k)
    t.hide('Counterparty')
    t.add_column_events('Foundation_document',double_click=True,on_double_click=tbl_cellDoubleClicked)
    t.add_column_events('doc_name',double_click=True,on_double_click=tbl_cellDoubleClicked)
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

    dict_stores_ref = dict()
    for item in data:
        dict_stores_ref[item['_Warehouse_ref']] = None

    dict_stores_ref = GEN.calc_leftover(list(dict_stores_ref.keys()), use_params=True)

    for item in data:
        OPERATION = DTCLS.params_doc.get_param(item['_tab_name']).operation
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
        item['doc_name'] = DTCLS.params_doc.get_param(item['_tab_name']).doc_name
        key = (item['_Nomenclature_ref'], item['Nomenclature_params'])
        if key in leftovers:
            item['Available'] = leftovers[key]['Available']
            ЕдИзм = leftovers[key]['ЕдИзм']
            item['Available_unit'] = ЕдИзм
        else:
            item['Available_unit'] = item['Quantity_abs_unit']
    return data
@CQT.progress_decorator
def fill_table(app_self,hook_prog_bar:CQT.progress_decorator):
    tbl = DTCLS.app_self.ui.tbl_common
    tblf = DTCLS.app_self.ui.tbl_common_filtr
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
    hook_prog_bar.close()
    DTCLS.app_self.setHidden(False)
    CMS.fill_filtr_c(DTCLS.app_self, tblf, tbl,
                     check_box_dict =
                     {'Operation':None,
                      'Status_foundation_document':None,
                      'Activity':None,
                      },combo_dict={'State':None})


def tbl_select_itemSelectionChanged():
    tbl = DTCLS.app_self.ui.tbl_common
    row = CQT.get_dict_line_form_tbl(tbl)
    DTCLS.tbl_details.set_data(row,GEN.ALIASES)

def tbl_cellDoubleClicked(t:CQT.TableContext,i:int,clmn_name:str):
    if clmn_name == 'doc_name':
        tab = t.current_row().value('_tab_name')
        tab_obj = DTCLS.app_self.ui.tab_w
        tab_obj.setCurrentIndex(CQT.number_tab_by_object_name(tab_obj,tab))

    if clmn_name == 'Foundation_document':
        ref = t.current_row().value('_Foundation_document_ref')
        TYPE_DOC = DTCLS.params_doc.get_param(t.current_row().value('_tab_name')).type
        link = GEN.open_in_1c(ref,TYPE_DOC)
