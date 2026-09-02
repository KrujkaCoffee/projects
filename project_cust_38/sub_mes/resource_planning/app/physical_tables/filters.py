from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .columns import BOOL_COLUMNS, INT_COLUMNS

DATE_COLUMNS = frozenset({"stale_after_dt", "invalidated_at", "updated_at"})
TEXT_OPERATORS = frozenset(
    {"contains", "equals", "not_equals", "starts", "ends", "not_contains"}
)
ORDER_OPERATORS = frozenset({"equals", "not_equals", "gt", "gte", "lt", "lte"})
EMPTY_OPERATORS = frozenset({"empty", "not_empty"})


class FilterValueError(ValueError):
    def __init__(self, column: str, message: str) -> None:
        super().__init__(message)
        self.column = column


@dataclass(frozen=True)
class ParsedDate:
    value: dt.datetime
    date_only: bool = False


@dataclass(frozen=True)
class ColumnFilter:
    column: str
    kind: str
    operator: str
    operand: Any = None

    def matches(self, value: Any) -> bool:
        if self.operator == "empty":
            return _is_empty(value)
        if self.operator == "not_empty":
            return not _is_empty(value)
        if self.kind == "bool":
            return _as_bool(value) is bool(self.operand)
        if self.kind == "int":
            return _match_order(_as_int(value), self.operator, self.operand)
        if self.kind == "date":
            return _match_date(value, self.operator, self.operand)
        return _match_text(value, self.operator, str(self.operand or ""))


@dataclass(frozen=True)
class FilterSet:
    filters: tuple[ColumnFilter, ...] = ()

    def matches(self, row: Mapping[str, Any]) -> bool:
        return all(item.matches(row.get(item.column)) for item in self.filters)

    @property
    def active_columns(self) -> frozenset[str]:
        return frozenset(item.column for item in self.filters)


def column_kind(column: str) -> str:
    if column in BOOL_COLUMNS:
        return "bool"
    if column in INT_COLUMNS:
        return "int"
    if column in DATE_COLUMNS:
        return "date"
    return "text"


def build_filter(
    column: str, operator: str, raw_value: Any = ""
) -> ColumnFilter | None:
    kind = column_kind(column)
    operator = str(operator or "").strip()
    if not operator:
        return None
    if operator in EMPTY_OPERATORS:
        return ColumnFilter(column, kind, operator)
    if kind == "bool":
        if operator == "all":
            return None
        if operator not in {"true", "false"}:
            raise FilterValueError(column, "Неизвестный логический фильтр")
        return ColumnFilter(column, kind, "equals", operator == "true")

    text = str(raw_value or "").strip()
    if not text:
        return None
    if kind == "text":
        if operator not in TEXT_OPERATORS:
            raise FilterValueError(column, "Неизвестный текстовый оператор")
        return ColumnFilter(column, kind, operator, text)
    if operator == "between":
        left, right = _split_range(column, text)
        if kind == "int":
            lower, upper = _parse_int(column, left), _parse_int(column, right)
        else:
            lower, upper = _parse_date(column, left), _parse_date(column, right)
        if _comparable_value(lower) > _comparable_value(upper):
            raise FilterValueError(column, "Начало диапазона больше конца")
        return ColumnFilter(column, kind, operator, (lower, upper))
    if operator not in ORDER_OPERATORS:
        raise FilterValueError(column, "Неизвестный оператор сравнения")
    operand = _parse_int(column, text) if kind == "int" else _parse_date(column, text)
    return ColumnFilter(column, kind, operator, operand)


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() not in {"", "0", "false", "no", "нет", "off"}
    return bool(value)


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_int(column: str, text: str) -> int:
    try:
        return int(text.strip())
    except ValueError as exc:
        raise FilterValueError(column, "Ожидается целое число") from exc


def _split_range(column: str, text: str) -> tuple[str, str]:
    pieces = text.split("..", 1)
    if len(pieces) != 2 or not all(piece.strip() for piece in pieces):
        raise FilterValueError(column, "Диапазон задаётся как начало..конец")
    return pieces[0].strip(), pieces[1].strip()


_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_date(column: str, text: str) -> ParsedDate:
    value = text.strip()
    date_only = bool(_DATE_ONLY_RE.fullmatch(value))
    try:
        if date_only:
            parsed = dt.datetime.combine(dt.date.fromisoformat(value), dt.time.min)
        else:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FilterValueError(
            column,
            "Ожидается ISO-дата: YYYY-MM-DD или YYYY-MM-DD HH:MM:SS",
        ) from exc
    return ParsedDate(_without_timezone(parsed), date_only)


def _as_date(value: Any) -> dt.datetime | None:
    if isinstance(value, dt.datetime):
        return _without_timezone(value)
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time.min)
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return _parse_date("", text).value
    except FilterValueError:
        return None


def _without_timezone(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(dt.timezone.utc).replace(tzinfo=None)


def _comparable_value(value: Any) -> Any:
    return value.value if isinstance(value, ParsedDate) else value


def _match_order(value: Any, operator: str, operand: Any) -> bool:
    if value is None:
        return False
    if operator == "between":
        return operand[0] <= value <= operand[1]
    if operator == "equals":
        return value == operand
    if operator == "not_equals":
        return value != operand
    if operator == "gt":
        return value > operand
    if operator == "gte":
        return value >= operand
    if operator == "lt":
        return value < operand
    if operator == "lte":
        return value <= operand
    return False


def _match_date(value: Any, operator: str, operand: Any) -> bool:
    actual = _as_date(value)
    if actual is None:
        return False
    if operator == "between":
        lower, upper = operand
        lower_value = lower.value
        upper_value = upper.value
        if upper.date_only:
            upper_value = (
                upper_value + dt.timedelta(days=1) - dt.timedelta(microseconds=1)
            )
        return lower_value <= actual <= upper_value
    expected: ParsedDate = operand
    if expected.date_only and operator in {"equals", "not_equals"}:
        equal = actual.date() == expected.value.date()
        return equal if operator == "equals" else not equal
    return _match_order(actual, operator, expected.value)


def _match_text(value: Any, operator: str, operand: str) -> bool:
    actual = "" if value is None else str(value)
    folded = actual.casefold()
    expected = operand.casefold()
    if operator == "contains":
        words = [word for word in expected.split() if word]
        return all(word in folded for word in words)
    if operator == "not_contains":
        return expected not in folded
    if operator == "equals":
        return folded == expected
    if operator == "not_equals":
        return folded != expected
    if operator == "starts":
        return folded.startswith(expected)
    if operator == "ends":
        return folded.endswith(expected)
    return False
