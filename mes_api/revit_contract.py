"""Pure helpers for the Revit ERP HTTP contract.

The module intentionally has no FastAPI or project_cust_38 imports.  This keeps
the contract parsing/query construction testable without connecting to 1C.
"""

from __future__ import annotations

import math
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence


MAX_SEARCH_QUERY_LENGTH = 120
MAX_SEARCH_LIMIT = 500
MAX_SEARCH_SCAN = 2_000
MAX_SEARCH_OFFSET = MAX_SEARCH_SCAN - MAX_SEARCH_LIMIT
MAX_CODE_LENGTH = 100
CODE_BATCH_SIZE = 200
MAX_RESOURCE_ROWS = 10_000
_CODE_RE = re.compile(r"^[0-9A-Za-zА-Яа-яЁё._/+\-]+$")


def _read_value(source: Any, *names: str) -> Any:
    for name in names:
        if isinstance(source, Mapping):
            if name in source and source[name] is not None:
                return source[name]
        elif hasattr(source, name):
            value = getattr(source, name)
            if value is not None:
                return value
    return None


def _first_text(source: Any, *names: str) -> str:
    fallback = ""
    for name in names:
        value = _read_value(source, name)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
        fallback = text
    return fallback


def _semantic_value(source: Any, tokens: Sequence[str]) -> str:
    values = _read_value(source, "values")
    if not isinstance(values, Mapping):
        return ""
    normalized_tokens = tuple(token.casefold() for token in tokens)
    for key, value in values.items():
        normalized_key = str(key).casefold()
        if any(token in normalized_key for token in normalized_tokens):
            text = "" if value is None else str(value).strip()
            if text:
                return text
    return ""


def _flagged_cell_value(
    source: Any,
    columns: Sequence[Mapping[str, Any]] | None,
    flag: str,
) -> str:
    cells = _read_value(source, "cells")
    if not isinstance(cells, (list, tuple)) or not columns:
        return ""
    for fallback_index, column in enumerate(columns):
        if not isinstance(column, Mapping) or column.get(flag) is not True:
            continue
        try:
            index = int(column.get("order", fallback_index))
        except (TypeError, ValueError, OverflowError):
            index = fallback_index
        if 0 <= index < len(cells) and cells[index] is not None:
            text = str(cells[index]).strip()
            if text:
                return text
    return ""


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if parsed > 0 else default


def quote_1c_string(value: Any) -> str:
    """Return a safe 1C query string literal.

    1C escapes a quote inside a string by doubling it. Control characters are
    replaced with spaces so a value cannot change the query layout.
    """

    text = "" if value is None else str(value)
    text = "".join(" " if ord(char) < 32 else char for char in text)
    return '"' + text.replace('"', '""') + '"'


def quote_odata_string(value: Any) -> str:
    """Return an OData single-quoted string literal."""

    text = "" if value is None else str(value)
    text = "".join(" " if ord(char) < 32 else char for char in text)
    return "'" + text.replace("'", "''") + "'"


def normalize_code(value: Any) -> str:
    code = "" if value is None else str(value).strip()
    if (
        not code
        or len(code) > MAX_CODE_LENGTH
        or _CODE_RE.fullmatch(code) is None
    ):
        return ""
    return code


def unique_codes(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        code = normalize_code(value)
        key = code.casefold()
        if not code or key in seen:
            continue
        seen.add(key)
        result.append(code)
    return result


def chunked(values: Sequence[str], size: int = CODE_BATCH_SIZE) -> list[list[str]]:
    if size < 1:
        raise ValueError("Размер пакета должен быть положительным")
    return [list(values[index:index + size]) for index in range(0, len(values), size)]


def build_codes_query(codes: Iterable[Any]) -> str | None:
    normalized = unique_codes(codes)
    if not normalized:
        return None
    literals = ", ".join(quote_1c_string(code) for code in normalized)
    return f"""
        ВЫБРАТЬ
            Номенклатура.Код КАК Code,
            Номенклатура.Наименование КАК Name
        ИЗ
            Справочник.Номенклатура КАК Номенклатура
        ГДЕ
            Номенклатура.ПометкаУдаления = ЛОЖЬ
            И Номенклатура.Код В ({literals})
    """


def normalize_search_query(value: Any) -> str:
    query = " ".join(("" if value is None else str(value)).split())
    if len(query) > MAX_SEARCH_QUERY_LENGTH:
        raise ValueError(
            f"Поисковая строка длиннее {MAX_SEARCH_QUERY_LENGTH} символов"
        )
    if len(query) < 2:
        raise ValueError("Для глобального поиска введите минимум 2 символа")
    if not any(char.isalnum() for char in query):
        raise ValueError("Поисковая строка должна содержать букву или цифру")
    return query


def normalize_search_window(limit: Any, offset: Any) -> tuple[int, int]:
    try:
        parsed_limit = int(limit)
    except (TypeError, ValueError, OverflowError):
        parsed_limit = 200
    try:
        parsed_offset = int(offset)
    except (TypeError, ValueError, OverflowError):
        parsed_offset = 0
    parsed_limit = min(MAX_SEARCH_LIMIT, max(1, parsed_limit))
    parsed_offset = min(MAX_SEARCH_OFFSET, max(0, parsed_offset))
    return parsed_limit, parsed_offset


def build_search_query(query: Any, scan_limit: int) -> str:
    normalized = normalize_search_query(query)
    scan_limit = min(MAX_SEARCH_SCAN, max(1, int(scan_limit)))
    terms = normalized.split()[:10]
    term_conditions: list[str] = []
    for term in terms:
        pattern = quote_1c_string(f"%{term}%")
        term_conditions.append(
            "(" + " ИЛИ ".join((
                f"Номенклатура.Код ПОДОБНО {pattern}",
                f"Номенклатура.Наименование ПОДОБНО {pattern}",
                f"Номенклатура.НаименованиеПолное ПОДОБНО {pattern}",
                f"Номенклатура.Артикул ПОДОБНО {pattern}",
            )) + ")"
        )
    search_filter = "\n            И ".join(term_conditions)
    return f"""
        ВЫБРАТЬ ПЕРВЫЕ {scan_limit}
            Номенклатура.Код КАК Code,
            Номенклатура.Наименование КАК Name,
            Номенклатура.ЕдиницаИзмерения.Наименование КАК Unit,
            Номенклатура.Артикул КАК Article,
            Номенклатура.НаименованиеПолное КАК FullName
        ИЗ
            Справочник.Номенклатура КАК Номенклатура
        ГДЕ
            Номенклатура.ПометкаУдаления = ЛОЖЬ
            И {search_filter}
        УПОРЯДОЧИТЬ ПО
            Номенклатура.Наименование,
            Номенклатура.Код
    """


def _search_rank(item: Mapping[str, str], query: str) -> tuple[int, str, str]:
    needle = query.casefold()
    code = item.get("Code", "").casefold()
    name = item.get("Name", "").casefold()
    extra = item.get("Extra", "").casefold()
    if code == needle:
        rank = 0
    elif code.startswith(needle):
        rank = 1
    elif name.startswith(needle):
        rank = 2
    elif extra.startswith(needle):
        rank = 3
    elif needle in code:
        rank = 4
    elif needle in name:
        rank = 5
    else:
        rank = 6
    return rank, name, code


def normalize_nomenclature_items(rows: Any, query: str = "") -> list[dict[str, str]]:
    if not isinstance(rows, list):
        return []
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        code = _first_text(row, "Code", "code", "Код")
        name = _first_text(row, "Name", "name", "Description", "Наименование")
        unit = _first_text(row, "Unit", "unit", "UnitName", "Единица")
        article = _first_text(row, "Article", "article", "Артикул")
        full_name = _first_text(row, "FullName", "full_name", "НаименованиеПолное")
        extra_parts: list[str] = []
        for part in (article, full_name):
            known_parts = {name.casefold()} | {item.casefold() for item in extra_parts}
            if part and part.casefold() not in known_parts:
                extra_parts.append(part)
        if not code and not name:
            continue
        key = (code.casefold(), name.casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "Code": code,
            "Name": name,
            "Unit": unit,
            "Extra": " · ".join(extra_parts),
        })
    if query:
        result.sort(key=lambda item: _search_rank(item, query))
    return result


_QUANTITY_RE = re.compile(
    r"^\s*([+-]?\d(?:[\d\s\u00a0]*\d)?(?:[.,]\d+)?)\s*([^\d]*)$"
)


def parse_positive_quantity(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            return None
    else:
        match = _QUANTITY_RE.fullmatch(str(value))
        if match is None:
            return None
        numeric = match.group(1).replace("\u00a0", "").replace(" ", "").replace(",", ".")
        try:
            number = Decimal(numeric)
        except InvalidOperation:
            return None
    try:
        parsed = float(number)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed <= 0:
        return None
    return parsed


@dataclass(frozen=True)
class NormalizedResourceRow:
    row: int
    source_row: int
    stage: str
    erp_code: str
    unit: str
    quantity_text: str
    quantity: float | None
    element_ids: tuple[int, ...]
    match_state: str
    match_info: str


def normalize_resource_row(
    source: Any,
    index: int,
    columns: Sequence[Mapping[str, Any]] | None = None,
) -> NormalizedResourceRow:
    row = _positive_int(_read_value(source, "row"), index)
    source_row = _positive_int(_read_value(source, "source_row"), row)
    quantity_value = _read_value(source, "quantity")
    if quantity_value is None or str(quantity_value).strip() == "":
        quantity_value = _semantic_value(source, ("количество", "кол-во", "quantity", "qty", "count"))
    if quantity_value is None or str(quantity_value).strip() == "":
        quantity_value = _flagged_cell_value(source, columns, "is_quantity")
    if quantity_value is None or str(quantity_value).strip() == "":
        quantity_value = _read_value(source, "Quantity")
    quantity_text = "" if quantity_value is None else str(quantity_value).strip()

    erp_code = _first_text(source, "erp_code")
    if not erp_code:
        erp_code = _semantic_value(source, ("erp", "1c", "1с"))
    if not erp_code:
        erp_code = _flagged_cell_value(source, columns, "is_erp_code")
    if not erp_code:
        erp_code = _first_text(source, "ErpCode")

    unit = _first_text(source, "unit")
    if not unit:
        unit = _semantic_value(source, ("единица измерения", "ед. изм", "unit"))
    if not unit:
        unit = _flagged_cell_value(source, columns, "is_unit")
    if not unit:
        unit = _first_text(source, "Unit")

    stage = _first_text(source, "stage")
    if not stage:
        stage = _semantic_value(source, ("этап", "stage"))
    if not stage:
        stage = _first_text(source, "Stage")

    raw_element_ids = _read_value(source, "element_ids") or []
    element_ids: list[int] = []
    if isinstance(raw_element_ids, (list, tuple, set)):
        for raw_id in raw_element_ids:
            try:
                element_id = int(raw_id)
            except (TypeError, ValueError, OverflowError):
                continue
            if element_id > 0 and element_id not in element_ids:
                element_ids.append(element_id)
    return NormalizedResourceRow(
        row=row,
        source_row=source_row,
        stage=stage,
        erp_code=normalize_code(erp_code),
        unit=unit,
        quantity_text=quantity_text,
        quantity=parse_positive_quantity(quantity_value),
        element_ids=tuple(element_ids),
        match_state=_first_text(source, "match_state"),
        match_info=_first_text(source, "match_info"),
    )


def local_resource_errors(
    rows: Sequence[NormalizedResourceRow],
    contract_version: int,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    field_errors: dict[str, str] = {}
    table_errors: list[dict[str, Any]] = []
    if not rows:
        field_errors["rows"] = "В спецификации нет строк для выгрузки"
        return field_errors, table_errors
    if len(rows) > MAX_RESOURCE_ROWS:
        field_errors["rows"] = (
            f"В одной выгрузке допускается не более {MAX_RESOURCE_ROWS} строк"
        )

    seen_elements: dict[int, NormalizedResourceRow] = {}
    for row in rows:
        def add_error(message: str) -> None:
            table_errors.append({
                "row": row.row,
                "source_row": row.source_row,
                "msg": message,
            })

        if not row.quantity_text:
            add_error("Не задано количество")
        elif row.quantity is None:
            add_error("Количество должно быть положительным числом")
        if not row.erp_code:
            add_error("Не задан код ERP")

        if contract_version >= 2:
            if row.match_state.casefold() != "matched":
                add_error("Строка не имеет однозначной связи с элементами Revit")
            if not row.element_ids:
                add_error("У строки отсутствуют связанные ElementId")
            association_errors: set[str] = set()
            for element_id in row.element_ids:
                previous = seen_elements.get(element_id)
                if previous is not None and previous.row != row.row:
                    same_group = previous.element_ids == row.element_ids
                    same_code = previous.erp_code.casefold() == row.erp_code.casefold()
                    if same_group and same_code:
                        # Itemized schedules may contain visually identical rows.
                        # Revit intentionally assigns the same association group;
                        # preserving both quantities is correct when the code agrees.
                        continue
                    if same_group:
                        association_errors.add(
                            "Визуально неразличимые строки связаны с одними ElementId, "
                            "но имеют разные ERP-коды"
                        )
                    else:
                        association_errors.add(
                            f"ElementId {element_id} уже используется строкой {previous.source_row}"
                        )
                else:
                    seen_elements[element_id] = row
            for message in sorted(association_errors):
                add_error(message)
    return field_errors, table_errors


class TtlCache:
    """Small thread-safe bounded TTL cache for read-only ERP lookups."""

    def __init__(self, ttl_seconds: float, max_items: int = 128):
        if ttl_seconds <= 0 or max_items <= 0:
            raise ValueError("TTL и размер кеша должны быть положительными")
        self._ttl_seconds = float(ttl_seconds)
        self._max_items = int(max_items)
        self._items: OrderedDict[Any, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any:
        now = time.monotonic()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= now:
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            self._items[key] = (time.monotonic() + self._ttl_seconds, value)
            self._items.move_to_end(key)
            while len(self._items) > self._max_items:
                self._items.popitem(last=False)

    def pop(self, key: Any) -> Any:
        with self._lock:
            entry = self._items.pop(key, None)
        if entry is None or entry[0] <= time.monotonic():
            return None
        return entry[1]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
