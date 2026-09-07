from typing import Optional
import pprint
import importlib
import os
import time

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field

from project_cust_38 import for_1c

import requests
router = APIRouter()

FOR1C_RETRY_DELAY = 60 * 60

def import_for1c_depend():
    now_stamp = str(time.time())
    limit_stamp = str(time.time() + FOR1C_RETRY_DELAY)
    last_update = os.environ.get('LAST_UPDATE_FOR1C_MODULE', limit_stamp)
    try:
        from project_cust_38 import for_1c
        if (float(last_update) - float(now_stamp)) >= FOR1C_RETRY_DELAY:
            importlib.reload(for_1c)
            os.environ['LAST_UPDATE_FOR1C_MODULE'] = now_stamp
        yield for_1c
    except (NameError, ModuleNotFoundError) as e:
        print(e)
        # Если словим повторную ошибку прыгаем -> global_exception_handler и ловим оповещение
        from project_cust_38 import for_1c
        os.environ['LAST_UPDATE_FOR1C_MODULE'] = now_stamp
        yield for_1c


class BaseAttributes1c(BaseModel):
    is_test: Optional[bool] = Field(default=False, alias='РаботаСВнешнимиРесурсамиЗаблокирована')

import logging
logger = logging.getLogger('uvicorn')
class ProductFromOrderTab(BaseAttributes1c):
    Ref_Key: Optional[str] = Field(..., alias='Номенклатура_Key')
    count: Optional[float] = Field(..., alias='Количество')
    price: Optional[float] = Field(..., alias='Цена')
    description: Optional[str] = Field(..., alias='Наименование')
    ratio_for_report: Optional[float] = Field(..., alias='КоэффициентЕдиницыДляОтчетов')
    measure_code: Optional[str] = Field(..., alias='Code')

class OrderSupplierFrom1C(BaseAttributes1c):
    Ref_Key: Optional[str] = Field(..., alias='Ref_Key')
    description: Optional[str] = Field(..., alias='Ссылка')
    DeletionMark: Optional[bool] = Field(..., alias='МеткаУдаления')
    status: Optional[str] = Field(..., alias='Статус')
    data_version: Optional[str] = Field(..., alias='ВерсияДанных')
    products: list[ProductFromOrderTab] = Field(default_factory=list, alias='Товары')


class DeliveryOrder(BaseAttributes1c):
    xmlId: Optional[str] = Field(..., alias='Ref_Key')
    title: Optional[str] = Field(..., alias="НазваниеРаспоряжения")
    ufCrm18Products: Optional[str] = Field(..., alias="Продукция") #
    ufCrm18DateShipment: Optional[str] = Field(..., alias="ЖелаемаяДатаОтгрузки")
    ufCrm18Customer: Optional[str] = Field(..., alias="Заказчик")
    ufCrm18Shipper: Optional[str] = Field(..., alias="Организация")
    ufCrm18ShippingAddress: Optional[str] = Field(..., alias="ЮридическийАдресСтрока2")
    ufCrm18ShipperContact: Optional[str] = Field(..., alias="КонтактноеЛицоГрузоотправителя")
    ufCrm18Recipient: Optional[str] = Field(..., alias="Грузополучатель")
    ufCrm18RecipientAddress: Optional[str] = Field(..., alias="АдресДоставки")
    ufCrm18RecipientContact: Optional[str] = Field(..., alias="КонтактноеЛицо")
    ufCrm18Info: Optional[str] = Field(..., alias="ДополнительнаяИнформация")
    ufCrm18ShippingMethod: Optional[str] = Field(..., alias="СпособОтгрузки")
    ufCrm18Payment: Optional[str] = Field(..., alias="ОплатаОтгрузки")
    ufCrm18Insurance: Optional[float] = Field(..., alias="Страховка")
    ufCrm18PackingType: Optional[str] = Field(..., alias="ВидУпаковки")
    ufCrm18CountSpots: Optional[int] = Field(..., alias="КоличествоМест")
    ufCrm18DimensionsSpots: Optional[str] = Field(..., alias="Габариты")
    ufCrm18Volume: Optional[float] = Field(..., alias="Объем")
    ufCrm18NetWeigth: Optional[float] = Field(..., alias="ВесНетто")
    ufCrm18GrossWeight: Optional[float] = Field(..., alias="ВесБрутто")


class DeliveryOrderPack(BaseAttributes1c):
    xmlId: str = Field(..., alias='Ref_Key')
    title: str = Field(..., alias='НаименованиеДокумента')
    ufCrm21WeightNet: Optional[float] = Field(..., alias='ВесНетто')
    ufCrm21WeightGross: Optional[float] = Field(..., alias='ВесБрутто')
    ufCrm21Volume: Optional[float] = Field(..., alias='Объем')
    ufCrm21PackingType: Optional[str] = Field(..., alias='ВидУпаковки')
    ufCrm21Length: Optional[float] = Field(..., alias='Длина')
    ufCrm21Height: Optional[float] = Field(..., alias='Высота')
    ufCrm21Width: Optional[float] = Field(..., alias='Ширина')
    ufCrm21Dimentions: Optional[str] = Field(..., alias='Габариты')
    ufCrm21Number: Optional[str | int] = Field(..., alias='НомерСтроки')
    parent_ref: str = Field(..., alias='Распоряжение_Key')
    deletion_mark: int | bool = Field(..., alias='НаУдаление')


class Nomenclature(BaseAttributes1c):
    Ref_Key: str = Field(..., alias='RefKey')
    РодительRefKey: Optional[str] = Field(..., alias='РодительRefKey')
    ЭтоГруппа: Optional[bool] = Field(..., alias='ЭтоГруппа')
    Наименование: Optional[str] = Field(..., alias='Наименование')
    На_удаление: Optional[bool] = Field(..., alias='ПометкаУдаления')
    СхемаОбеспечения: Optional[str] = Field(..., alias='СхемаОбеспеченияRefKey')
    Вид_Ref_Key: Optional[str] = Field(..., alias='ВидНоменклатурыRefKey')
    Вид: Optional[str] = Field(..., alias='ВидНоменклатурыНаименование')
    Закупочная_цена: Optional[float] = Field(..., alias='ЗакупочнаяЦена')
    ЕдиницаИзмерения: Optional[str] = Field(..., alias='ЕдиницаИзмеренияНаименование')
    Артикул: Optional[str] = Field(..., alias='Артикул')
    Код: Optional[str] = Field(..., alias='Код')
    data_version: Optional[str] = Field(..., alias='ВерсияДанных')




@router.post(
    '/hs/mes/exchange/{version}/order-supplier/',
    status_code=status.HTTP_200_OK)
def sync_order_supplier(version: str, data: OrderSupplierFrom1C, request: Request):
    is_test_base = request.headers.get('ExternalResourcesWorkBlocked')
    logger.info(f'IS_TEST_BASE: {is_test_base!r}' )

    if version == 'v1':
        queue = 'bitrix24.ЗаказПоставщику.СинхронизацияЗаказа/ТабличнойЧасти'
        try:
            data_dict = data.model_dump()
            answ, list_err = for_1c.update_drawback_journal(
                data.Ref_Key,
                data_dict,
                queue=queue
            )
            logger.info(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
            return {"Данные": answ, "Ошибки": list_err}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='err')
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')

@router.post(
    '/hs/mes/exchange/{version}/order-delivery/',
    status_code=status.HTTP_200_OK)
def sync_order_delivery(version: str, data: DeliveryOrder, request: Request):
    is_test_base = request.headers.get('ExternalResourcesWorkBlocked')
    logger.info(f'IS_TEST_BASE: {is_test_base!r}' )

    if version == 'v1':
        queue = 'bitrix24.РаспоряжениеНаДоставку.СинхронизацияТабличнойЧасти'
        try:
            data_dict = data.model_dump()
            answ, list_err = for_1c.update_drawback_journal(
                data.xmlId,
                data_dict,
                queue=queue
            )
            logger.info(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
            return {"Данные": answ, "Ошибки": list_err}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='err')
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')


@router.post(
    '/hs/mes/exchange/{version}/order-delivery/pack/',
    status_code=status.HTTP_200_OK)
def sync_order_delivery(version: str, data: list[DeliveryOrderPack], request: Request):
    is_test_base = request.headers.get('ExternalResourcesWorkBlocked')
    logger.info(f'IS_TEST_BASE: {is_test_base!r}' )
    if version == 'v1':
        queue = 'bitrix24.РаспоряжениеНаДоставку/Упаковка.СинхронизацияТабличнойЧастиУпаковки'
        errors = []
        answers = []
        for item in data:
            try:
                data_dict = item.model_dump()
                answ, list_err = for_1c.update_drawback_journal(
                    item.xmlId,
                    data_dict,
                    queue=queue
                )
                answers.append(answ)
                logger.info(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
            except Exception as e:
                errors.append(f'Ошибка при сохранении {item.xmlId}')
        return {"Данные": all(answers), "Ошибки": errors}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')


@router.post(
    '/hs/mes/exchange/{version}/nomenclature/',
    status_code=status.HTTP_200_OK)
def sync_nomenclature(version: str, data: dict):
    logger.info(f'data: {data!r}')
    return {"Данные": [], "Ошибки": []}
    if version == 'v1':
        queue = 'MES.Номенклатура/СинхронизацияПолей'
        for_services = ('MES',)
        errors = []
        answers = []
        try:
            for service in for_services:
                data_dict = data.model_dump()
                answ, list_err = for_1c.update_drawback_journal(
                    data.Ref_Key,
                    data_dict,
                    queue=queue,
                    service=service
                )
                answers.append(answ)
                print(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
        except Exception as e:
            errors.append(f'Ошибка при сохранении {data.Ref_Key}')
        return {"Данные": all(answers), "Ошибки": errors}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')
