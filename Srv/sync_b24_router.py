from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from project_cust_38 import for_1c

router = APIRouter()


class ProductFromOrderTab(BaseModel):
    Ref_Key: Optional[str] = Field(..., alias='Номенклатура_Key')
    count: Optional[float] = Field(..., alias='Количество')
    price: Optional[float] = Field(..., alias='Цена')
    description: Optional[str] = Field(..., alias='Наименование')
    ratio_for_report: Optional[float] = Field(..., alias='КоэффициентЕдиницыДляОтчетов')
    measure_code: Optional[str] = Field(..., alias='Code')

class OrderSupplierFrom1C(BaseModel):
    Ref_Key: Optional[str] = Field(..., alias='Ref_Key')
    description: Optional[str] = Field(..., alias='Ссылка')
    DeletionMark: Optional[bool] = Field(..., alias='МеткаУдаления')
    status: Optional[str] = Field(..., alias='Статус')
    data_version: Optional[str] = Field(..., alias='ВерсияДанных')
    products: list[ProductFromOrderTab] = Field(default_factory=list, alias='Товары')


class DeliveryOrder(BaseModel):
    xmlId: Optional[str] = Field(..., alias='Ref_Key')
    title: Optional[str] = Field(..., alias="НазваниеРаспоряжения")
    ufCrm18Products: Optional[str] = Field(..., alias="Продукция") #
    ufCrm18DateShipment: Optional[str] = Field(..., alias="ЖелаемаяДатаОтгрузки")
    ufCrm18Customer: Optional[str] = Field(..., alias="Заказчик")
    ufCrm18Shipper: Optional[str] = Field(..., alias="Организация")
    ufCrm18ShippingAddress: Optional[str] = Field(..., alias="ЮридическийАдресСтрока2")
    ufCrm18ShipperContact: Optional[str] = Field(..., alias="Подписант")
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


@router.post(
    '/hs/mes/exchange/{version}/order-supplier/',
    status_code=status.HTTP_200_OK)
def sync_order_supplier(version: str, data: OrderSupplierFrom1C):
    if version == 'v1':
        queue = 'bitrix24.ЗаказПоставщику.СинхронизацияЗаказа/ТабличнойЧасти'
        try:
            data_dict = data.model_dump()
            answ, list_err = for_1c.update_drawback_journal(
                data.Ref_Key,
                data_dict,
                queue=queue
            )
            import pprint
            print(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
            return {"Данные": answ, "Ошибки": list_err}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='err')
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')

@router.post(
    '/hs/mes/exchange/{version}/order-delivery/',
    status_code=status.HTTP_200_OK)
def sync_order_delivery(version: str, data: DeliveryOrder):
    if version == 'v1':
        queue = 'bitrix24.РаспоряжениеНаДоставку.СинхронизацияПолейДокумента'
        try:
            data_dict = data.model_dump()
            answ, list_err = for_1c.update_drawback_journal(
                data.xmlId,
                data_dict,
                queue=queue
            )
            import pprint
            print(f'[{queue}] Ответ успешно принят: {pprint.pformat(data_dict)}')
            return {"Данные": answ, "Ошибки": list_err}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='err')
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Version is not found')
