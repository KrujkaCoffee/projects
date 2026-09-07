from __future__ import annotations

import hashlib
import importlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_odata_erp as COE
from project_cust_38 import Cust_resource_creator as CRC
from project_cust_38 import api_erp_commands as APIERP

try:
    from .revit_contract import (
        MAX_SEARCH_SCAN,
        TtlCache,
        build_codes_query,
        build_search_query,
        chunked,
        local_resource_errors,
        normalize_code,
        normalize_nomenclature_items,
        normalize_resource_row,
        normalize_search_query,
        normalize_search_window,
        quote_odata_string,
        unique_codes,
    )
except ImportError:  # API_server imports this module as a top-level file.
    from revit_contract import (
        MAX_SEARCH_SCAN,
        TtlCache,
        build_codes_query,
        build_search_query,
        chunked,
        local_resource_errors,
        normalize_code,
        normalize_nomenclature_items,
        normalize_resource_row,
        normalize_search_query,
        normalize_search_window,
        quote_odata_string,
        unique_codes,
    )


router = APIRouter(prefix="/api/v1/revit")
logger = logging.getLogger(__name__)

_format = "?$format=json"
_base_name = "ERP_MES1"
_search_cache = TtlCache(ttl_seconds=30, max_items=128)
_nomenclature_cache = TtlCache(ttl_seconds=60, max_items=256)
_reference_cache = TtlCache(ttl_seconds=600, max_items=16)
_validated_payloads = TtlCache(ttl_seconds=120, max_items=512)
_crc_reload_lock = threading.Lock()
_crc_last_reload = 0.0


class ErpUnavailableError(RuntimeError):
    pass


class ResourceUploadError(RuntimeError):
    pass


class ActionRequest(BaseModel):
    action: str = ""


class NomenclatureRequest(BaseModel):
    action: str = ""
    parent_ref: str = ""
    query: str = ""
    limit: int = 200
    offset: int = 0


class OutputProduct(BaseModel):
    code: str = ""
    name: str = ""
    unit: str | None = None


class ResourceMaterial(BaseModel):
    row: int | None = None
    source_row: int | None = None
    stage: str | None = None
    erp_code: str | None = None
    unit: str | None = None
    quantity: str | int | float | None = None
    values: dict[str, Any] = Field(default_factory=dict)
    cells: list[Any] = Field(default_factory=list)
    element_ids: list[int] = Field(default_factory=list)
    match_state: str = ""
    match_info: str = ""

    # Legacy fields remain accepted while old clients are upgraded.
    Stage: str | None = None
    FamilyName: str = ""
    TypeName: str = ""
    DisplayName: str = ""
    ErpCode: str = ""
    Unit: str = ""
    Quantity: str | int | float | None = None


class ResourceRequest(BaseModel):
    action: str = ""
    contract_version: int = 1
    title: str = ""
    context: str = ""
    output_product: OutputProduct = Field(default_factory=OutputProduct)
    schedule: dict[str, Any] | None = None
    rows: list[ResourceMaterial] = Field(default_factory=list)
    creator: str = ""
    start_date: str = ""
    end_date: str = ""
    comment: str = "ПР:T:1"
    user: str = ""


class CreateNomenSchemeRequest(BaseModel):
    action: str = ""
    article: str = ""
    kind_ref: str = ""
    name: str = ""
    unit_ref: str = ""
    type_ref: int | str = ""


class FilledNomenCredentials(BaseModel):
    finance_group: str | None
    analyst_group: str | None
    access_group: str | None
    sale_option: str | None


class LinkRequest(BaseModel):
    action: str = ""
    link: str = ""


class NomenCodesArray(BaseModel):
    action: str = ""
    codes: list[str] = Field(default_factory=list)


def _model_dict(model: BaseModel) -> dict[str, Any]:
    model_dump = getattr(model, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return model.dict()


def _payload_fingerprint(body: ResourceRequest) -> str:
    raw = json.dumps(
        _model_dict(body),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _run_wet_query(query: str, refs: Any = None) -> list[dict[str, Any]]:
    with patch.dict(
        "project_cust_38.Cust_config.Config.user_config.ERP_base_name",
        {"Значение": _base_name},
    ):
        code, response = APIERP.get_wet_request(query, refs)
    if code != 200 or not isinstance(response, dict):
        raise ErpUnavailableError(f"1С вернула код {code!r}")
    rows = response.get("data")
    if rows is None:
        raise ErpUnavailableError("1С вернула ответ без поля data")
    if not isinstance(rows, list):
        raise ErpUnavailableError("Поле data в ответе 1С не является массивом")
    return rows


def _fetch_nomenclature(codes: list[str]) -> dict[str, dict[str, str]]:
    started = time.monotonic()
    result: dict[str, dict[str, str]] = {}
    batches = chunked(codes)
    for code_batch in batches:
        query = build_codes_query(code_batch)
        if query is None:
            continue
        for item in normalize_nomenclature_items(_run_wet_query(query)):
            code = normalize_code(item.get("Code"))
            if code:
                result[code.casefold()] = item
    logger.info(
        "Revit API: пакетная проверка кодов, requested=%s found=%s requests=%s elapsed=%.3fs",
        len(codes),
        len(result),
        len(batches),
        time.monotonic() - started,
    )
    return result


def _append_table_error(errors: list[dict[str, Any]], row: Any, message: str) -> None:
    errors.append({"row": row.row, "source_row": row.source_row, "msg": message})


def _validate_dates(body: ResourceRequest, field_errors: dict[str, str]) -> None:
    start = None
    end = None
    if not body.start_date:
        field_errors["start_date"] = "Не заполнена дата начала действия ресурсной"
    else:
        try:
            start = datetime.strptime(body.start_date, "%Y-%m-%d")
        except ValueError:
            field_errors["start_date"] = "Дата начала должна быть в формате ГГГГ-ММ-ДД"
    if not body.end_date:
        field_errors["end_date"] = "Не заполнена дата окончания действия ресурсной"
    else:
        try:
            end = datetime.strptime(body.end_date, "%Y-%m-%d")
        except ValueError:
            field_errors["end_date"] = "Дата окончания должна быть в формате ГГГГ-ММ-ДД"
    if start is not None and end is not None and start >= end:
        field_errors["end_date"] = "Дата окончания должна быть позже даты начала"


def _validate_resource_request(
    body: ResourceRequest,
) -> tuple[dict[str, str], list[dict[str, Any]], list[Any], list[str]]:
    field_errors: dict[str, str] = {}
    warnings: list[str] = []
    schedule_columns = (
        body.schedule.get("columns", []) if isinstance(body.schedule, dict) else []
    )
    normalized_rows = [
        normalize_resource_row(material, index, schedule_columns)
        for index, material in enumerate(body.rows, start=1)
    ]
    local_fields, table_errors = local_resource_errors(normalized_rows, body.contract_version)
    field_errors.update(local_fields)

    if body.contract_version >= 2:
        if body.action != "upload_resource_map":
            field_errors["action"] = "Для контракта v2 ожидается action=upload_resource_map"
        if not isinstance(body.schedule, dict):
            field_errors["schedule"] = "Не передан снимок активной спецификации"
        else:
            if not str(body.schedule.get("name") or "").strip():
                field_errors["schedule"] = "Не передано имя активной спецификации"
            if body.schedule.get("field_mapping_exact") is False:
                warnings.append(
                    "Текст спецификации получен точно, но метаданные части колонок "
                    "сопоставлены не полностью"
                )

    title = body.title.strip()
    if len(title) < 4:
        field_errors["title"] = "Наименование ресурсной слишком короткое"
    elif len(title) > 150:
        field_errors["title"] = "Наименование ресурсной длиннее 150 символов"
    else:
        odata_client = COE.OrdersComposit(_base_name)
        title_literal = quote_odata_string(title)
        wet_filter = (
            f"{_format}&$select=Ref_Key&$filter="
            f"Description eq {title_literal} and DeletionMark eq false&$top=1"
        )
        code, data = odata_client.get_response(
            "Catalog_РесурсныеСпецификации",
            wet_filtr=wet_filter,
            with_cod=True,
        )
        if code != 200 or not isinstance(data, list):
            field_errors["title"] = "Не удалось проверить уникальность наименования в 1С"
        elif data:
            field_errors["title"] = "Ресурсная с таким наименованием уже существует"

    creator = (body.creator or body.user).strip()
    if not creator:
        field_errors["creator"] = "Не удалось определить пользователя"
    elif len(creator) > 150:
        field_errors["creator"] = "Имя пользователя длиннее 150 символов"
    if not normalize_code(body.output_product.code):
        field_errors["output_dse"] = "Не задан код основного изделия"

    _validate_dates(body, field_errors)

    requested_codes = unique_codes(
        [body.output_product.code] + [row.erp_code for row in normalized_rows if row.erp_code]
    )
    if requested_codes:
        try:
            existing = _fetch_nomenclature(requested_codes)
        except ErpUnavailableError:
            existing = None
        if existing is None:
            if normalize_code(body.output_product.code):
                field_errors["output_dse"] = "Не удалось проверить код основного изделия"
            for row in normalized_rows:
                if row.erp_code:
                    _append_table_error(table_errors, row, "Не удалось проверить код номенклатуры")
        else:
            output_code = normalize_code(body.output_product.code)
            if output_code and output_code.casefold() not in existing:
                field_errors["output_dse"] = "Код основного изделия не найден в 1С"
            for row in normalized_rows:
                if row.erp_code and row.erp_code.casefold() not in existing:
                    _append_table_error(table_errors, row, "Код номенклатуры не найден в 1С")

    return field_errors, table_errors, normalized_rows, warnings


def _validation_response(
    field_errors: dict[str, str], table_errors: list[dict[str, Any]]
) -> JSONResponse:
    return JSONResponse(
        {"field_errors": field_errors, "table_errors": table_errors}, status_code=400
    )


def _upload_resource_once(body: ResourceRequest, normalized_rows: list[Any]) -> dict[str, Any]:
    dispatcher = (
        CRC.SubdivisionsData
        ._hnt_проектный_отдел_пкб_производственные_подразделения_пкб_пауэрз_00_000021
    )
    parent = CRC.GroupResData._hnt_проектирование_пкб_пауэрз_00_010491
    allocation_method = (
        CRC.TheMethodOfAllocatingTheCostOfTheOutputProductsData._hnt_по_долям_стоимости_0
    )
    creator = (body.creator or body.user).strip()
    output_product = CRC.MainProduct(
        body.output_product.code.strip(),
        body.output_product.name.strip(),
        (body.output_product.unit or "").strip(),
    )
    header = CRC.ResourceHeader(
        ОсновноеИзделиеКод=output_product,
        Наименование=body.title.strip(),
        ТекущийПользователь=CRC.CurrentUser(creator),
        ДатаНачала=body.start_date,
        ДатаОкончания=body.end_date,
        ПодразделениеДиспетчер=dispatcher,
        РодительКод=parent,
        Описание=body.comment,
        СпособРаспределенияЗатратНаВыходныеИзделия=allocation_method,
        ИмяБазы=_base_name,
        ПроверятьОсновноеИзделие=False,
    )

    article = getattr(CRC.ArticulationArticlesData, "_hnt_основной_фот_none", None)
    if article is None:
        CRC.ArticulationArticlesData.init_data()
        article = CRC.ArticulationArticlesData._hnt_основной_фот_none
    obtaining_method = CRC.MethodOfObtainingMaterialspecificationsData.find_by_ref(
        "5c796eb7-92d0-494a-aad9-76cf7a28b3dd"
    )
    stages: OrderedDict[str, Any] = OrderedDict()
    for row in normalized_rows:
        stage_name = row.stage.strip()
        stage_data = stages.get(stage_name)
        if stage_data is None:
            stage_data = CRC.StageData(Подразделение=dispatcher, ДлительностьМинут=0)
            stages[stage_name] = stage_data
        stage_data.add_material(CRC.Material(row.erp_code, row.quantity, article, obtaining_method))

    specification = CRC.ResourceSpecification(header)
    for stage_name, stage_data in stages.items():
        specification.add_stage(CRC.Stage(stage_name, stage_data))

    logger.info(
        "Revit API: отправка ресурсной в 1С, rows=%s stages=%s contract=%s",
        len(normalized_rows),
        len(stages),
        body.contract_version,
    )
    success, response = specification.send(msg=False, return_err=True)
    if not success:
        raise ResourceUploadError(str(response))
    if not isinstance(response, dict):
        raise ResourceUploadError("1С вернула ответ неизвестного формата")
    return response


def upload_resource(body: ResourceRequest, normalized_rows: list[Any]) -> dict[str, Any]:
    global _crc_last_reload
    try:
        return _upload_resource_once(body, normalized_rows)
    except AttributeError:
        with _crc_reload_lock:
            now = time.monotonic()
            if now - _crc_last_reload < 60 * 60:
                raise
            _crc_last_reload = now
            logger.warning("Revit API: однократная перезагрузка Cust_resource_creator")
            importlib.reload(CRC)
        return _upload_resource_once(body, normalized_rows)


def exclude_descendants_iterative(
    rows: list[dict[str, Any]], exclude_refs: set[str]
) -> list[dict[str, Any]]:
    excluded = set(exclude_refs)
    changed = True
    while changed:
        changed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            ref = row.get("Ref_Key")
            if row.get("Parent_Key") in excluded and ref not in excluded:
                excluded.add(ref)
                changed = True
    return [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("Ref_Key") not in excluded
        and not row.get("ПометкаУдаления")
    ]


def mark_folders(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    return [
        {
            **row,
            "Description": f"{'📁' if row.get('IsFolder') else '📄'}{row.get('Description', '')}",
        }
        for row in rows
        if isinstance(row, dict)
    ]


@router.post("/types")
def nomen_types(credentials: ActionRequest) -> list[dict[str, Any]]:
    cached = _reference_cache.get("types")
    if cached is not None:
        return cached
    filtered_types = {
        "6f1c7234-5795-11ee-84be-00d861dd2b4a",
        "a67f77cb-c347-11ee-8502-00d861dd2b4a",
        "fe0bdde9-5e4d-11ec-8463-00d861dd2b4a",
        "55066dac-e639-11ec-8468-00d861dd2b4a",
        "4afe4741-7ec6-11ee-84d2-00d861dd2b4a",
        "d4b555aa-7b2a-11eb-845c-00d861dd2b4a",
        "cf2f3789-b017-11e7-80c7-4ccc6a67082d",
        "ecc86b0a-b4e9-11e8-80d2-4ccc6a67082d",
    }
    query = """
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
    try:
        result = mark_folders(
            exclude_descendants_iterative(_run_wet_query(query), filtered_types)
        )
    except ErpUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    _reference_cache.set("types", result)
    return result


@router.post("/nomens")
def nomens(credentials: NomenclatureRequest) -> Any:
    if credentials.action == "search_nomenclature":
        started = time.monotonic()
        try:
            query_text = normalize_search_query(credentials.query)
            limit, offset = normalize_search_window(credentials.limit, credentials.offset)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        cache_key = (query_text.casefold(), limit, offset)
        cached = _search_cache.get(cache_key)
        if cached is not None:
            return cached
        scan_limit = min(MAX_SEARCH_SCAN, max(500, offset + limit + 1))
        try:
            raw_rows = _run_wet_query(build_search_query(query_text, scan_limit))
        except ErpUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        items = normalize_nomenclature_items(raw_rows, query_text)
        result = {
            "items": items[offset:offset + limit],
            "limit": limit,
            "offset": offset,
            "has_more": len(items) > offset + limit or len(raw_rows) >= scan_limit,
        }
        _search_cache.set(cache_key, result)
        logger.info(
            "Revit API: глобальный поиск, raw=%s returned=%s offset=%s elapsed=%.3fs",
            len(raw_rows),
            len(result["items"]),
            offset,
            time.monotonic() - started,
        )
        return result

    if credentials.action not in ("", "get_nomenclature_list"):
        raise HTTPException(status_code=400, detail="Неизвестное действие для /nomens")
    ref_key = credentials.parent_ref.strip()
    if not ref_key:
        raise HTTPException(status_code=400, detail="Не задан parent_ref")
    cache_key = ref_key.casefold()
    cached = _nomenclature_cache.get(cache_key)
    if cached is not None:
        return cached
    query = """
        ВЫБРАТЬ
            Номенклатура.Код КАК Code,
            Номенклатура.Наименование КАК Name,
            Номенклатура.ЕдиницаИзмерения.Наименование КАК Unit,
            Номенклатура.Артикул КАК Article,
            Номенклатура.НаименованиеПолное КАК FullName
        ИЗ
            Справочник.Номенклатура КАК Номенклатура
        ГДЕ
            Номенклатура.ВидНоменклатуры.Ссылка = &ВидНоменклатуры_Key
            И Номенклатура.ПометкаУдаления = ЛОЖЬ
        УПОРЯДОЧИТЬ ПО
            Номенклатура.Наименование
    """
    try:
        refs = APIERP.Refs_wet(query)
        refs.add_ref(
            APIERP.Ref_wet(
                "ВидНоменклатуры_Key", "Справочники.ВидыНоменклатуры", ref_key
            )
        )
        result = normalize_nomenclature_items(_run_wet_query(query, refs))
    except (ErpUnavailableError, ValueError) as error:
        status = 400 if isinstance(error, ValueError) else 503
        raise HTTPException(status_code=status, detail=str(error)) from error
    _nomenclature_cache.set(cache_key, result)
    return result


def calc_type_chars(ref_key: str) -> FilledNomenCredentials | None:
    try:
        normalized_ref = str(UUID(ref_key))
    except (ValueError, TypeError, AttributeError):
        return None
    doc = f"Catalog_ВидыНоменклатуры(guid'{normalized_ref}')"
    select = (
        "&$select=ГруппаАналитическогоУчета_Key,ГруппаФинансовогоУчета_Key,"
        "ГруппаДоступа_Key,ВариантОформленияПродажи"
    )
    code, data = COE.OrdersComposit(_base_name).get_response(
        doc, wet_filtr=f"{_format}{select}", with_cod=True
    )
    if code == 200 and isinstance(data, dict):
        return FilledNomenCredentials(
            finance_group=data.get("ГруппаФинансовогоУчета_Key"),
            analyst_group=data.get("ГруппаАналитическогоУчета_Key"),
            access_group=data.get("ГруппаДоступа_Key"),
            sale_option=data.get("ВариантОформленияПродажи"),
        )
    return None


def make_nomen(data: dict[str, Any]) -> tuple[int, Any]:
    url = (
        f"{CFG.Config.project.ERB_BASE_URL}/{_base_name}"
        "/ru_RU/hs/mes/sysexchange/v1/make_nomen/none"
    )
    user = os.environ.get("ERP_HTTP_USER", APIERP.USER_ERP)
    password = os.environ.get("ERP_HTTP_PASSWORD", APIERP.PASS_ERP)
    try:
        response = requests.post(
            url,
            json=data,
            headers={"Accept": "application/json"},
            auth=(user, password),
            timeout=30,
        )
    except requests.exceptions.RequestException as error:
        raise ErpUnavailableError("Нет соединения с сервисом создания номенклатуры") from error
    try:
        response_data = response.json()
    except ValueError:
        response_data = {
            "Код": "",
            "ЕстьОшибки": True,
            "Ошибки": [response.text[:500]],
        }
    return response.status_code, response_data


@router.post("/nomen/create/", status_code=201)
def create_nomen(nomen_credentials: CreateNomenSchemeRequest) -> Any:
    defaults = calc_type_chars(nomen_credentials.kind_ref)
    if defaults is None:
        return JSONResponse(
            {"kind_ref": ["Не найден выбранный вид номенклатуры"]}, status_code=400
        )
    try:
        UUID(nomen_credentials.unit_ref)
    except (ValueError, TypeError, AttributeError):
        return JSONResponse(
            {"unit_ref": ["Некорректная единица измерения"]}, status_code=400
        )
    try:
        type_ref = int(nomen_credentials.type_ref)
    except (TypeError, ValueError):
        return JSONResponse(
            {"type_ref": ["Некорректный тип номенклатуры"]}, status_code=400
        )
    data = {
        "Наименование": nomen_credentials.name.strip(),
        "НаименованиеПолное": nomen_credentials.name.strip(),
        "Артикул": nomen_credentials.article.strip(),
        "ТипНоменклатуры": type_ref,
        "ВариантОформленияПродажи": defaults.sale_option,
        "ГруппаДоступа": defaults.access_group,
        "ЕдиницаИзмерения": nomen_credentials.unit_ref,
        "ЕдиницаДляОтчетов": nomen_credentials.unit_ref,
        "ИспользованиеХарактеристик": "НеИспользовать",
        "ВидНоменклатуры": nomen_credentials.kind_ref,
        "СтавкаНДС": "20%",
        "ГруппаАналитическогоУчета": defaults.analyst_group,
        "ГруппаФинансовогоУчета": defaults.finance_group,
    }
    try:
        code, response = make_nomen(data)
    except ErpUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if code != 200 or not isinstance(response, dict) or not response.get("Код"):
        errors = response.get("Ошибки") if isinstance(response, dict) else response
        raise HTTPException(
            status_code=502, detail=f"1С не создала номенклатуру: {str(errors)[:500]}"
        )
    _search_cache.clear()
    _nomenclature_cache.clear()
    return {
        "code": str(response["Код"]),
        "name": nomen_credentials.name.strip(),
        "unit": nomen_credentials.unit_ref,
    }


@router.post("/nomen/kind/form/")
def nomen_kinds(credentials: ActionRequest) -> list[dict[str, Any]]:
    cached = _reference_cache.get("nomen_kinds")
    if cached is not None:
        return cached
    code, response = APIERP.get_enum("ТипыНоменклатуры")
    if code != 200 or not isinstance(response, dict):
        raise HTTPException(status_code=503, detail="Не удалось получить типы номенклатуры из 1С")
    result = [
        {"Ref_Key": item.get("Порядок"), "Description": item.get("Ссылка", "")}
        for item in (response.get("data") or [])
        if isinstance(item, dict)
    ]
    _reference_cache.set("nomen_kinds", result)
    return result


@router.post("/nomen/stages/form/")
def stages(credentials: ActionRequest) -> list[dict[str, Any]]:
    return []


@router.post("/nomen/units/form/")
def nomen_units(credentials: ActionRequest) -> list[dict[str, Any]]:
    cached = _reference_cache.get("units")
    if cached is not None:
        return cached
    allowed_unit_types = {"Вес", "Длина", "Объем", "Площадь"}
    query = """
        ВЫБРАТЬ РАЗЛИЧНЫЕ
            УпаковкиЕдиницыИзмерения.Наименование КАК Description,
            УНИКАЛЬНЫЙИДЕНТИФИКАТОР(УпаковкиЕдиницыИзмерения.Ссылка) КАК Ref_Key,
            ПРЕДСТАВЛЕНИЕ(УпаковкиЕдиницыИзмерения.ТипИзмеряемойВеличины) КАК ТипВеличиныНаименование
        ИЗ
            Справочник.УпаковкиЕдиницыИзмерения КАК УпаковкиЕдиницыИзмерения
        ГДЕ
            УпаковкиЕдиницыИзмерения.ПометкаУдаления = ЛОЖЬ
            И УпаковкиЕдиницыИзмерения.Владелец.Наименование = "Базовые единицы измерения"
    """
    try:
        result = [
            item
            for item in _run_wet_query(query)
            if isinstance(item, dict)
            and item.get("ТипВеличиныНаименование") in allowed_unit_types
        ]
    except ErpUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    _reference_cache.set("units", result)
    return result


@router.post("/resource/validate/", status_code=200)
def validate_resource(body: ResourceRequest) -> Any:
    started = time.monotonic()
    field_errors, table_errors, normalized_rows, warnings = _validate_resource_request(body)
    if field_errors or table_errors:
        logger.info(
            "Revit API: ресурсная не прошла проверку, fields=%s rows=%s elapsed=%.3fs",
            len(field_errors),
            len(table_errors),
            time.monotonic() - started,
        )
        return _validation_response(field_errors, table_errors)
    _validated_payloads.set(_payload_fingerprint(body), True)
    logger.info(
        "Revit API: ресурсная проверена, rows=%s elapsed=%.3fs",
        len(normalized_rows),
        time.monotonic() - started,
    )
    return {
        "status": "ok",
        "contract_version": body.contract_version,
        "validated_rows": len(normalized_rows),
        "warnings": warnings,
    }


@router.post("/resource/create/")
def create_resource(body: ResourceRequest) -> Any:
    fingerprint = _payload_fingerprint(body)
    validated = _validated_payloads.pop(fingerprint) is True
    if validated:
        schedule_columns = (
            body.schedule.get("columns", []) if isinstance(body.schedule, dict) else []
        )
        normalized_rows = [
            normalize_resource_row(material, index, schedule_columns)
            for index, material in enumerate(body.rows, start=1)
        ]
    else:
        field_errors, table_errors, normalized_rows, _ = _validate_resource_request(body)
        if field_errors or table_errors:
            return _validation_response(field_errors, table_errors)
    try:
        return upload_resource(body, normalized_rows)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (
        ConnectionError,
        ErpUnavailableError,
        requests.exceptions.RequestException,
    ) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ResourceUploadError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/resource/link_exists/")
def resource_link_exists(credentials: LinkRequest) -> bool:
    fragment = urlparse(credentials.link).fragment
    query = parse_qs(urlparse("http://local/" + fragment).query)
    reference = query.get("ref", [None])[0]
    if reference is None:
        return False
    ref_key = F.restore_uuid_from_client_1C_reference(reference)
    if not ref_key:
        return False
    order_client = COE.OrdersComposit(_base_name)
    code, data = order_client.get_response(
        f"Catalog_РесурсныеСпецификации(guid'{ref_key}')",
        wet_filtr=_format,
        with_cod=True,
    )
    if code == 404:
        return False
    if code != 200 or not isinstance(data, dict):
        raise HTTPException(status_code=503, detail="Не удалось проверить ссылку в 1С")
    return not bool(data.get("DeletionMark"))


@router.post("/nomen/validate/")
def validate_nomen(body: CreateNomenSchemeRequest) -> Any:
    errors: dict[str, str] = {}
    odata_client = COE.OrdersComposit(_base_name)
    try:
        unit_ref = str(UUID(body.unit_ref))
    except (ValueError, TypeError, AttributeError):
        errors["unit"] = "Единица измерения не выбрана"
    else:
        code, data = odata_client.get_response(
            "Catalog_УпаковкиЕдиницыИзмерения",
            wet_filtr=(
                f"{_format}&$select=Description&$filter="
                f"Ref_Key eq guid'{unit_ref}'&$top=1"
            ),
            with_cod=True,
        )
        if code != 200:
            errors["unit"] = "Не удалось проверить единицу измерения"
        elif not isinstance(data, list) or not data:
            errors["unit"] = "Единица измерения не найдена"

    if len(body.article.strip()) < 3:
        errors["article"] = "Артикул слишком короткий"
    if calc_type_chars(body.kind_ref) is None:
        errors["kind_ref"] = "Вид номенклатуры не найден"
    if len(body.name.strip()) < 4:
        errors["name"] = "Наименование слишком короткое"
    else:
        name_literal = quote_odata_string(body.name.strip())
        code, data = odata_client.get_response(
            "Catalog_Номенклатура",
            wet_filtr=(
                f"{_format}&$select=Ref_Key&$filter="
                f"Description eq {name_literal} and DeletionMark eq false&$top=1"
            ),
            with_cod=True,
        )
        if code != 200:
            errors["name"] = "Не удалось проверить наименование в 1С"
        elif isinstance(data, list) and data:
            errors["name"] = "Наименование уже существует"
    if errors:
        return JSONResponse(errors, status_code=400)
    return {}


@router.post("/nomens/bycodearray/")
def nomenclature_names_by_codes(body: NomenCodesArray) -> dict[str, dict[str, str]]:
    codes = unique_codes(body.codes)
    if not codes:
        return {}
    try:
        items = _fetch_nomenclature(codes)
    except ErpUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {item["Code"]: {"name": item["Name"]} for item in items.values()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("revit_router:router", reload=True, host="pow18-08", port=8000)
