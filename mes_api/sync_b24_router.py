import hashlib
from typing import Optional
import pprint

from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel, Field

from dependencies import import_for1c_depend

router = APIRouter()

class BaseAttributes1c(BaseModel):
    def serialize_and_hash(self) -> str:
        json_data = self.json()
        sha256_hash = hashlib.sha256(json_data.encode('utf-8')).hexdigest()
        return sha256_hash

import logging
logger = logging.getLogger('uvicorn')
class ProductFromOrderTab(BaseAttributes1c):
    Ref_Key: Optional[str] = Field(..., alias='Номенклатура_Key')
    count: Optional[float] = Field(..., alias='Количество')
    price: Optional[float] = Field(..., alias='Цена')
    description: Optional[str] = Field(..., alias='Наименование')
    ratio_for_report: Optional[float] = Field(..., alias='КоэффициентЕдиницыДляОтчетов')
    measure_code: Optional[str] = Field(..., alias='Code')
    measure_code_pos: Optional[str] = Field(None, alias='УпаковкаНаименование') # единица товарной позиции
    measure_code_nomen: Optional[str] = Field(None, alias='НоменклатураЕдиницаИзмеренияНаименование') # единица номенклатуры

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
    ufCrm18Shipper2: Optional[str] = Field("", alias="Грузоотправитель")
    ufCrm18ShippingAddress: Optional[str] = Field(..., alias="ЮридическийАдресСтрока2")
    ufCrm18ShippingAddress2: Optional[str] = Field("", alias="АдресОтгрузки")
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
    types_tree: Optional[str] = Field(default=None, alias='ИерархияRefKeyРодителей')
    unit_code: Optional[str] = Field(default=None, alias='КодЕдиницыИзмерения')
    unit_ratio: Optional[float] = Field(default=None, alias='КоэффициентЕдиницыДляОтчетов')


class DealStatus(BaseAttributes1c):
    id: int = Field(..., alias='bitrx_id')
    status_code: str = Field(..., alias='status_code')
    UF_CRM_1737727925: str = Field(default="", alias='UF_CRM_1737727925')
    UF_CRM_1737711083528: str = Field(default="", alias='UF_CRM_1737711083528')
    forced: bool = False


class OkpStatus(BaseAttributes1c):
    # Заказ на производство
    Ref_Key_ZNPR: str = Field(..., alias='Ref_Key_ZNPR')
    Number_ZNPR: str = Field(..., alias='Number_ZNPR')
    Ref_Key_nomen: str = Field(..., alias='Ref_Key_Номенклатура')
    Number_nomen: str = Field(..., alias='НоменклатураКод')
    Name_nomen: str = Field(..., alias='НоменклатураНаименование')
    count: int | float = Field(None, alias='Количество')
    # Этап
    Ref_Key_STAGE: str = Field(..., alias='Ref_Key_STAGE')
    Title_STAGE: str = Field(default="", alias='Title_STAGE')
    # Движение продукции и материалов
    Title_TRANSFER: str = Field(default="", alias='Title_TRANSFER')
    # Системные
    forced: bool = False

class TransferZNPRTriggerResponse(BaseAttributes1c):
    nomens: list[OkpStatus] = Field(..., alias='МассивИзделий')

@router.post(
    '/hs/mes/exchange/{version}/order-supplier/',
    status_code=status.HTTP_200_OK)
def sync_order_supplier(version: str, data: OrderSupplierFrom1C, request: Request, for_1c = Depends(import_for1c_depend)):
    is_test_base = request.headers.get('ExternalResourcesWorkBlocked')
    logger.info(f'IS_TEST_BASE: {is_test_base!r}' )

    if version == 'v1':
        queue = 'bitrix24.ЗаказПоставщику.СинхронизацияЗаказа/ТабличнойЧасти'
        try:
            data_dict = data.model_dump()
            answ, list_err = for_1c.update_drawback_journal(
                data.Ref_Key,
                data_dict,
                queue=queue,
                is_test=is_test_base
            )
            logger.info(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
            return {"Данные": answ, "Ошибки": list_err}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='err')
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')

@router.post(
    '/hs/mes/exchange/{version}/order-delivery/',
    status_code=status.HTTP_200_OK)
def sync_order_delivery(version: str, data: DeliveryOrder, request: Request, for_1c = Depends(import_for1c_depend)):
    is_test_base = request.headers.get('ExternalResourcesWorkBlocked')
    logger.info(f'IS_TEST_BASE: {is_test_base!r}' )

    if version == 'v1':
        queue = 'bitrix24.РаспоряжениеНаДоставку.СинхронизацияТабличнойЧасти'
        try:
            data_dict = data.model_dump()
            answ, list_err = for_1c.update_drawback_journal(
                data.xmlId,
                data_dict,
                queue=queue,
                is_test=is_test_base
            )
            logger.info(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
            return {"Данные": answ, "Ошибки": list_err}
        except Exception as e:
            logger.info(f'Ошибка: {queue!r}\n{e}')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='err')
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')


@router.post(
    '/hs/mes/exchange/{version}/order-delivery/pack/',
    status_code=status.HTTP_200_OK)
def sync_order_delivery_pack(version: str, data: list[DeliveryOrderPack], request: Request, for_1c = Depends(import_for1c_depend)):
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
                    queue=queue,
                    is_test=is_test_base
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
def sync_nomenclature(version: str, data: Nomenclature, request: Request, for_1c = Depends(import_for1c_depend)):
    is_test_base = request.headers.get('ExternalResourcesWorkBlocked')
    logger.info(f'IS_TEST_BASE: {is_test_base!r}' )
    if version == 'v1':
        queue = 'MES.Номенклатура/СинхронизацияПолей'
        errors = []
        answers = []
        try:
            data_dict = data.model_dump()
            answ, list_err = for_1c.update_drawback_journal(
                data.Ref_Key,
                data_dict,
                queue=queue,
                is_test=is_test_base
            )
            answers.append(answ)
            logger.info(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
        except Exception as e:
            errors.append(f'Ошибка при сохранении {data.Ref_Key}')
        return {"Данные": all(answers), "Ошибки": errors}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')


@router.post(
    '/hs/mes/exchange/{version}/deal/status/',
    status_code=status.HTTP_200_OK)
def sync_deal_status(version: str, data: DealStatus, request: Request, for_1c = Depends(import_for1c_depend)):
    is_test_base = request.headers.get('ExternalResourcesWorkBlocked')
    logger.info(f'IS_TEST_BASE: {is_test_base!r}' )
    if version == 'v1':
        queue = 'bitrix24.Сделка/ОбновлениеСтатуса'
        errors = []
        answers = []
        try:
            data_dict = data.model_dump()
            answ, list_err = for_1c.update_drawback_journal(
                data.id,
                data_dict,
                queue=queue,
                is_test=is_test_base
            )
            answers.append(answ)
            logger.info(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
        except Exception as e:
            errors.append(f'Ошибка при сохранении {data.Ref_Key}')
        return {"Данные": all(answers), "Ошибки": errors}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')


@router.post(
    '/hs/mes/exchange/{version}/production-order/change-status/',
    status_code=status.HTTP_200_OK)
def sync_okp_status(version: str, lst_items: TransferZNPRTriggerResponse, request: Request, for_1c = Depends(import_for1c_depend)):
    is_test_base = request.headers.get('ExternalResourcesWorkBlocked')
    logger.info(f'IS_TEST_BASE: {is_test_base!r}' )
    if version == 'v1':
        queue = 'MES.plan.ОбновлениеСтатусаПозиции'
        errors = []
        answers = []
        try:
            hash_struct = lst_items.serialize_and_hash()
            data_struct = [item.model_dump() for item in lst_items.nomens]

            answ, list_err = for_1c.update_drawback_journal(
                hash_struct,
                data_struct,
                queue=queue,
                is_test=is_test_base
            )
            answers.append(answ)
            logger.info(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_struct)}')
        except Exception as e:
            logger.error(f'Ошибка при сохранении {queue!r} {e}', exc_info=e)
            errors.append(f'Ошибка при сохранении {queue!r}')
        return {"Данные": all(answers), "Ошибки": errors}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')
