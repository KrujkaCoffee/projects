import logging
from datetime import datetime
from collections import defaultdict
from typing import Iterable, Any, Iterable, Tuple
from urllib.parse import urlparse, parse_qs
from collections import defaultdict
from unittest.mock import patch
from dataclasses import field

import requests
from starlette.responses import JSONResponse
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel

from project_cust_38 import Cust_resource_creator as CRC
from project_cust_38 import api_erp_commands as APIERP
from project_cust_38 import Cust_odata_erp as COE
from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_config as CFG

router = APIRouter(prefix='/api/v1/revit')

logging.basicConfig(level=logging.INFO)


_format = '?$format=json'
_base_name = 'ERP_MES1'

class OutputProduct(BaseModel):
    code: str
    name: str
    unit: str | None

class ResourceMaterial(BaseModel):
    Stage: str | None = None
    FamilyName: str
    TypeName: str
    DisplayName: str
    ErpCode: str
    Unit: str
    Quantity: str

class ResourceRequest(BaseModel):
    title: str
    output_product: OutputProduct
    rows: list[ResourceMaterial]
    creator: str = ""
    start_date: str
    end_date: str
    comment: str = 'ПР:T:1'
    user: str = ""

class CreateNomenSchemeRequest(BaseModel):
    action: str = ''
    article: str = ''
    kind_ref: str = ''
    name: str = ''
    unit_ref: str = ''
    type_ref: int | str = ''

class CreateNomenSchemeResponse(BaseModel):
    code: str
    name: str
    unit: str

class FilledNomenCredentials(BaseModel):
    finance_group: str | None
    analyst_group: str | None
    access_group: str | None
    sale_option: str | None

def get_unit_uuid(unit_description: str):
    doc = "Catalog_УпаковкиЕдиницыИзмерения"
    _select = '&$select=Ref_Key'
    _filter = f'&$filter=Description eq {unit_description!r} and DeletionMark eq false'
    _top = '&$top=1'
    odata_client = COE.OrdersComposit(_base_name)
    code, data = odata_client.get_response(doc, wet_filtr=f'{_format}{_filter}{_select}{_top}', with_cod=True)
    if code != 200:
        return None
    match data:
        case [{'Ref_Key': ref_key}]:
            return ref_key
    return None

def upload_resource(body: ResourceRequest):
    ПодразделениеДиспетчер = CRC.SubdivisionsData._hnt_проектный_отдел_пкб_производственные_подразделения_пкб_пауэрз_00_000021
    РодительКод = CRC.GroupResData._hnt_проектирование_пкб_пауэрз_00_010491
    ВариантПодбораВДокументы = CRC.VariationsrespecificationdocumentsData._hnt_вручную_1
    СпособРаспределенияЗатратНаВыходныеИзделия = CRC.TheMethodOfAllocatingTheCostOfTheOutputProductsData._hnt_по_долям_стоимости_0

    # СпособПолучения = MethodOfObtainingMaterialspecificationsData.find_by_name("Обеспечивать")

    hat = CRC.ResourceHeader(
        ОсновноеИзделиеКод=CRC.MainProduct.find_by_code(body.output_product.code),
        Наименование=body.title,
        ТекущийПользователь=CRC.CurrentUser(body.creator),
        ДатаНачала=body.start_date,
        ДатаОкончания=body.end_date,
        ПодразделениеДиспетчер=ПодразделениеДиспетчер,
        РодительКод=РодительКод,
        ВариантПодбораВДокументы=ВариантПодбораВДокументы,
        Описание=body.comment,
        СпособРаспределенияЗатратНаВыходныеИзделия=СпособРаспределенияЗатратНаВыходныеИзделия,
        ИмяБазы=_base_name
    )
    CRC.ArticulationArticlesData.init_data()
    ОсновнойФОТ = CRC.ArticulationArticlesData._hnt_основной_фот_none
    СпособПолучения = CRC.MethodOfObtainingMaterialspecificationsData.find_by_ref("5c796eb7-92d0-494a-aad9-76cf7a28b3dd")
    # Подразделение = SubdivisionsData._hnt_сталелитейный_цех_таткуз_таткуз_00_000164
    stage_data = CRC.StageData(
        Подразделение=ПодразделениеДиспетчер,
        ДлительностьМинут=0
    )
    ИсточникПолученияПолуфабриката = CRC.SourceOfTheHalffactoryReceipt.find_by_code('00-058859')
    for spec_item in body.rows:
        mat1 = CRC.Material(
            spec_item.ErpCode,
            spec_item.Quantity,
            ОсновнойФОТ,
            СпособПолучения
        )
        СтатьяКалькуляции: CRC.ArticulationArticles
        СпособПолучения: CRC.MethodOfObtainingMaterialspecifications
        ИсточникПолученияПолуфабриката: CRC.SourceOfTheHalffactoryReceipt = field(
            default_factory=CRC.SourceOfTheHalffactoryReceipt
        )
        stage_data.add_material(mat1)
        stage = CRC.Stage("", stage_data)
        spec = CRC.ResourceSpecification(hat)
        spec.add_stage(stage)
    dirt_data = spec.to_json()
    logging.info(spec.to_json())
    return spec.send()


def exclude_descendants_iterative(rows: list[dict], exclude_refs: set):
    if not rows:
        return []
    for row in rows:
        if row['Parent_Key'] in exclude_refs and row["Ref_Key"] not in exclude_refs:
            exclude_refs.add(row['Ref_Key'])
            return exclude_descendants_iterative(rows, exclude_refs)
    return [row for row in rows if row['Ref_Key'] not in exclude_refs and not row['ПометкаУдаления'] ]


def mark_folders(rows):
    if not isinstance(rows, list):
        return []
    new_struct = []
    for row in rows:
        desc = row['Description']
        mark = '📁' if row['IsFolder'] else '📄'
        new_struct.append({**row, 'Description': f"{mark}{desc}"})
    return new_struct

@router.post('/types')
def nomen_types(credentials: dict):
    filtered_types = {
        '6f1c7234-5795-11ee-84be-00d861dd2b4a',
        'a67f77cb-c347-11ee-8502-00d861dd2b4a',
        'fe0bdde9-5e4d-11ec-8463-00d861dd2b4a',
        '55066dac-e639-11ec-8468-00d861dd2b4a',
        '4afe4741-7ec6-11ee-84d2-00d861dd2b4a',
        'd4b555aa-7b2a-11eb-845c-00d861dd2b4a',
        'cf2f3789-b017-11e7-80c7-4ccc6a67082d',
        'ecc86b0a-b4e9-11e8-80d2-4ccc6a67082d'
    }
    query = f"""
        ВЫБРАТЬ
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Ссылка)) КАК Ref_Key,
            ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(ВидыНоменклатуры.Родитель)) КАК Parent_Key,
            ВидыНоменклатуры.Наименование КАК Description,
            ВидыНоменклатуры.ПометкаУдаления КАК ПометкаУдаления,
            ВидыНоменклатуры.ЭтоГруппа КАК IsFolder
        ИЗ
            Справочник.ВидыНоменклатуры КАК ВидыНоменклатуры
        УПОРЯДОЧИТЬ ПО
            ВидыНоменклатуры.Наименование
    """
    with patch.dict("project_cust_38.Cust_config.Config.user_config.ERP_base_name", {'Значение': _base_name}) as attr:
        code, data = APIERP.get_wet_request(query)
    if code != 200 or not data or not data['data']:
        return []
    data = exclude_descendants_iterative(data['data'], filtered_types)
    if data:
        return mark_folders(data)
    return data

@router.post('/nomens')
def nomens(credentials: dict):
    ref_key = credentials['parent_ref']
    query = f"""
        ВЫБРАТЬ 
            Номенклатура.Код КАК Code,
            Номенклатура.Наименование КАК Name,
            Номенклатура.ЕдиницаИзмерения.Наименование КАК Unit
        ИЗ
            Справочник.Номенклатура КАК Номенклатура
        ГДЕ
            Номенклатура.ВидНоменклатуры.Ссылка = &ВидНоменклатуры_Key
        УПОРЯДОЧИТЬ ПО
            Наименование
    """
    refs = APIERP.Refs_wet(query)
    refs.add_ref(APIERP.Ref_wet('ВидНоменклатуры_Key', 'Справочники.ВидыНоменклатуры', ref_key))
    with patch.dict("project_cust_38.Cust_config.Config.user_config.ERP_base_name", {'Значение': _base_name}) as attr:

        code, response = APIERP.get_wet_request(query, refs)
    if response and response['data']:
        return response['data']
    return []


def calc_type_chars(ref_key: str) -> FilledNomenCredentials | None:
    doc = f'Catalog_ВидыНоменклатуры(guid{ref_key!r})'
    _select = '&$select=ГруппаАналитическогоУчета_Key,ГруппаФинансовогоУчета_Key,ГруппаДоступа_Key,ВариантОформленияПродажи'
    code, data = COE.OrdersComposit(_base_name).get_response(doc, wet_filtr=f'{_format}{_select}', with_cod=True)
    if code == 200:
        return FilledNomenCredentials(
            finance_group=data['ГруппаФинансовогоУчета_Key'],
            analyst_group=data['ГруппаАналитическогоУчета_Key'],
            access_group=data['ГруппаДоступа_Key'],
            sale_option=data['ВариантОформленияПродажи'],
        )


def make_nomen(dict_data:dict):
    headers = dict(Accept='application/json')
    params = dict()
    url = f'{CFG.Config.project.ERB_BASE_URL}/{_base_name}/ru_RU/hs/mes/sysexchange/v1/make_nomen/none'
    response = requests.post(url, json=dict_data, headers=headers, params=params, auth=('mes_user', '89Luham'))
    logging.info(f"[{response.status_code}] {response.text}")
    logging.info(dict_data)
    try:
        data = response.json()
    except:
        if not response.status_code == 200:
            data = {'Код':'','ЕстьОшибки':True, 'Ошибки':[response.text]}
    logging.info(dict_data)
    return response.status_code, data


@router.post('/nomen/create/', status_code=201)
def create_nomen(nomen_credentials: CreateNomenSchemeRequest):
    new_art = nomen_credentials.article
    new_nomen = nomen_credentials.name
    default_params = calc_type_chars(nomen_credentials.kind_ref)
    dict_nomen = {'Наименование': new_nomen,
                  'НаименованиеПолное': new_nomen,
                  'Артикул': new_art,
                  'ТипНоменклатуры': int( nomen_credentials.type_ref),
                  'ВариантОформленияПродажи': default_params.sale_option,
                  'ГруппаДоступа': default_params.access_group,
                  'ЕдиницаИзмерения': nomen_credentials.unit_ref,
                  'ЕдиницаДляОтчетов': nomen_credentials.unit_ref,
                  'ИспользованиеХарактеристик': 'НеИспользовать',
                  'ВидНоменклатуры': nomen_credentials.kind_ref,
                  'СтавкаНДС': '20%',
                  'ГруппаАналитическогоУчета': default_params.analyst_group,
                  'ГруппаФинансовогоУчета': default_params.finance_group,
                  }
    code, data = make_nomen(dict_nomen)
    if code != 200:
        raise HTTPException(status_code=500, detail=f'Запрос создания номенклатуры в 1С ошибка код {code}\n{data["Ошибки"]}')
    return {'code': data["Код"], 'name': new_nomen, 'unit': nomen_credentials.unit_ref}


@router.post('/nomen/kind/form/')
def nomen_o(credentials: dict = {}):
    code, resp = APIERP.get_enum('ТипыНоменклатуры')
    if code == 200:
        return [{'Ref_Key': item['Порядок'], 'Description': item['Ссылка']} for item in resp['data']]
    raise HTTPException(status_code=500, detail='Не корректный результат из бд 1с')
@router.post('/nomen/stages/form/')
def stages(credentials: dict = {}):
    return [{}]

@router.post('/nomen/units/form/')
def nomen_enums(credentials: dict = {}):
    # return [{'Ref_Key': 'qwe', 'Description': 'м'}]
    allowed_unit_types = (
        'Вес', 'Длина', 'Объем', 'Площадь'
    )
    query = """
    SELECT DISTINCT 
        Наименование AS Description,
        УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Ссылка) AS Ref_Key,
        ПРЕДСТАВЛЕНИЕ(ТипИзмеряемойВеличины) AS ТипВеличиныНаименование
    FROM Справочник.УпаковкиЕдиницыИзмерения AS УпаковкиЕдиницыИзмерения
    WHERE УпаковкиЕдиницыИзмерения.ПометкаУдаления = ЛОЖЬ AND
        УпаковкиЕдиницыИзмерения.Владелец.Наименование = "Базовые единицы измерения"
    """
    with patch.dict("project_cust_38.Cust_config.Config.user_config.ERP_base_name", {'Значение': _base_name}) as attr:

        code, resp = APIERP.get_wet_request(query)
    if code == 200:
        return [item for item in resp['data'] if item['ТипВеличиныНаименование'] in allowed_unit_types]
    raise HTTPException(status_code=500, detail='Не корректный результат из бд 1с')

@router.post('/resource/create/')
def create_resource(credentials: ResourceRequest):
    response = upload_resource(credentials)
    if isinstance(response, dict):
        return response
    raise HTTPException(status_code=500, detail='Не удалось создать ресурсную')

@router.post('/resource/link_exists/')
def create_resource(credentials: dict):
    frag = urlparse(credentials['link']).fragment
    qs = parse_qs(urlparse("http://x/" + frag).query)
    ref = qs.get("ref", [None])[0]
    if ref is None:
        return
    ref_key = F.restore_uuid_from_client_1C_reference(ref)
    if not ref_key:
        return
    order_client = COE.OrdersComposit(_base_name)
    _filter = f'&$filter=DeletionMark eq false'
    code, data = order_client.get_response(f"Catalog_РесурсныеСпецификации(guid{ref_key!r})", wet_filtr=_format, with_cod=True)
    if code == 404:
        return False
    match data:
        case {'DeletionMark': status} if status:
            return False
    return True


@router.post('/resource/validate/', status_code=200)
def validate_resource(res_request: ResourceRequest):
    error_fields = {}
    odata_client = COE.OrdersComposit(_base_name)
    if not res_request.creator:
        error_fields['creator'] = 'Не удалось запросить пользователя'
    if not res_request.title or len(res_request.title) < 4:
        error_fields['title'] = 'Наименование ресурсной слишком короткое'
    else:
        _select = f'&$select=Ref_Key'
        _filter = f'&$filter=Description eq {res_request.title!r} and DeletionMark eq false'
        code, data = odata_client.get_response(f"Catalog_РесурсныеСпецификации", wet_filtr=f'{_format}{_filter}',
                                               with_cod=True)
        if data and len(data) > 0:
            error_fields['title'] = 'Ресурсная с таким наименованием уже существует'

    if res_request.output_product.code:
        doc = "Catalog_Номенклатура"
        _select = '&$select=Description'
        _filter = f'&$filter=Code eq {res_request.output_product.code!r}'
        code, data = odata_client.get_response(doc, wet_filtr=f'{_format}{_select}{_filter}', with_cod=True)
        if code != 200:
            error_fields['output_dse'] = 'Не удалось проверить код основного изделия'
        else:
            if len(data) == 0:
                error_fields['output_dse'] = 'Код основного изделия не найден в 1С'
    if not res_request.start_date:
        error_fields['start_date'] = 'Не заполнена дата даты начала действия ресурсной'
    if not res_request.end_date:
        error_fields['end_date'] = 'Не заполнена дата даты окончания действия ресурсной'
    if res_request.start_date and res_request.end_date:
        try:
            if datetime.strptime(res_request.start_date, '%Y-%m-%d') > datetime.strptime(res_request.end_date, '%Y-%m-%d'):
                error_fields['end_date'] = 'Дата окончания не может быть раньше даты начала'
        except Exception as e: ...
    errors = []

    for idx, material in enumerate(res_request.rows, start=1):
        if not material.Quantity:
            errors.append({'row': idx, 'msg': f'Не задано количество'})
        if material.Quantity == '0':
            errors.append({'row': idx, 'msg': f'Количество равно нулю'})
        # if not material.Stage:
        #     errors.append({'row': idx, 'msg': f'Не задан этап'})
        # if not material.Unit or get_unit_uuid(material.Unit) is None:
        #     errors.append({'row': idx, 'msg': f'Единица измерения некорректна или не была найдена в 1С'})
        if material.ErpCode:
            doc = "Catalog_Номенклатура"
            _select = '&$select=Description'
            _filter = f'&$filter=Code eq {material.ErpCode!r} and DeletionMark eq false'
            code, data = odata_client.get_response(doc, wet_filtr=f'{_format}{_select}{_filter}', with_cod=True)
            if code != 200:
                errors.append({'row': idx, 'msg': f'Не удалось проверить код номенклатуры'})
            else:
                if len(data) == 0:
                    errors.append({'row': idx, 'msg': f'Код номенклатуры не найден в 1С'})
        else:
            errors.append({'row': idx, 'msg': f'Не задан код erp'})
    if errors or error_fields:
        return JSONResponse({'field_errors': error_fields, 'table_errors': errors}, status_code=400)
    return {'status': 'ok'}


@router.post('/nomen/validate/')
def validate_nomen(body: CreateNomenSchemeRequest):
    error_fields = {}
    odata_client = COE.OrdersComposit(_base_name)

    if body.unit_ref:
        doc = f"Catalog_УпаковкиЕдиницыИзмерения"
        _select = '&$select=Description'
        _filter = f'&$filter=Ref_Key eq guid{body.unit_ref!r}'
        code, data = odata_client.get_response(doc, wet_filtr=f'{_format}{_select}{_filter}', with_cod=True)
        if code == 200:
            if len(data) == 0:
                error_fields['unit'] = 'Единица измерения не найдена'
    else:
        error_fields['unit'] = 'Единица измерения не найдена'

    if len(body.article) < 3:
        error_fields['article'] = 'Артикул слишком короткий'
    if body.kind_ref:
        doc = f"Catalog_ВидыНоменклатуры(guid{body.kind_ref!r})"
        _select = '&$select=Description,IsFolder'
        code, data = odata_client.get_response(doc, wet_filtr=f'{_format}{_select}', with_cod=True)

        if code == 200 and isinstance(data, dict):
            if not data:
                error_fields['kind_ref'] = 'Вид номенклатуры не найден'
            elif data['IsFolder']:
                error_fields['kind_ref'] = 'Выбранный вид помечен как папка; для сущности "Номенклатура" это недопустимо.'
    else:
        error_fields['kind_ref'] = 'Тип номенклатуры не найден'
    if len(body.name) < 4:
        error_fields['name'] = 'Наименование слишком короткое'
    else:
        doc = "Catalog_Номенклатура"
        _filter = f'&$filter=Description eq {body.name!r}'
        code, data = odata_client.get_response(doc, wet_filtr=f'{_format}{_select}{_filter}', with_cod=True)
        if code == 200 and len(data) > 0:
            error_fields['name'] = 'Наименование уже существует'
    if error_fields:
        return JSONResponse(error_fields, status_code=400)
    return error_fields

class NomenCodesArray(BaseModel):
    codes: list[str]

@router.post('/nomens/bycodearray/')
def nomen_namee_by_code_array(body: NomenCodesArray):
    try:
        codes = ','.join(f'"{code_nomen}"' for code_nomen in body.codes if isinstance(code_nomen, str) and code_nomen.startswith('00-'))
        query = f"""
            ВЫБРАТЬ 
                Номенклатура.Код КАК code,
                Номенклатура.Наименование КАК name
            ИЗ
                Справочник.Номенклатура КАК Номенклатура
            ГДЕ
                Номенклатура.Код В ({codes})
        """
        with patch.dict("project_cust_38.Cust_config.Config.user_config.ERP_base_name",
                        {'Значение': _base_name}) as attr:

            code, resp = APIERP.get_wet_request(query)
        if code == 200:
            return {item['code']: {'name': item['name']}for item in resp['data']}
    except Exception as e:
        logging.error('[Revit-api ошибка]', e)
    return []
# app = FastAPI()
# app.include_router(router)

if __name__ == '__main__':


    import uvicorn
    uvicorn.run("app:app", reload=True, host='pow18-08', port=8000)
