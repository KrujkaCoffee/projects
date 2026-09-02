from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .columns import (
    BOOL_COLUMNS,
    EDITABLE_EXISTING_COLUMNS,
    EDITABLE_NEW_COLUMNS,
    IDENTITY_COLUMNS,
    IGNORED_DIRTY_COLUMNS,
    INT_COLUMNS,
    NEW_ROW_DEFAULTS,
    NULLABLE_TEXT_COLUMNS,
    TABLE_COLUMNS,
)


@dataclass(frozen=True)
class ValidationIssue:
    row_id: str
    column: str
    message: str


@dataclass(frozen=True)
class RowUpdate:
    table_key: str
    baseline: dict[str, Any]
    values: dict[str, Any]


@dataclass(frozen=True)
class PhysicalTablesChangeSet:
    inserts: tuple[dict[str, Any], ...] = ()
    updates: tuple[RowUpdate, ...] = ()
    deletes: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.inserts or self.updates or self.deletes)


class PhysicalTablesValidationError(ValueError):
    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        message = "\n".join(
            f"{issue.row_id} · {issue.column}: {issue.message}" for issue in self.issues
        )
        super().__init__(message or "Данные реестра таблиц не прошли проверку")


def build_unicode_table_key(db_key: Any, table_name: Any) -> str:
    """Собрать читаемый ключ без транслитерации и потери кириллицы."""

    db_text = str(db_key or "").strip()
    table_text = str(table_name or "").strip()
    if not table_text:
        return ""
    return f"{db_text}.{table_text}" if db_text else table_text


def normalize_value(column: str, value: Any) -> Any:
    if column in BOOL_COLUMNS:
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, int):
            return 1 if value else 0
        text = str(value or "").strip().casefold()
        if text in {"1", "true", "t", "yes", "y", "on", "да"}:
            return 1
        if text in {"0", "false", "f", "no", "n", "off", "нет", ""}:
            return 0
        return 1
    if column in INT_COLUMNS:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        text = str(value or "").strip()
        try:
            return int(text)
        except ValueError:
            return text
    if column in NULLABLE_TEXT_COLUMNS:
        if value is None or str(value).strip() == "":
            return None
        return str(value)
    if column in IDENTITY_COLUMNS:
        return str(value or "").strip()
    return "" if value is None else str(value)


def normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        column: normalize_value(column, row.get(column)) for column in TABLE_COLUMNS
    }


class PhysicalTablesEditModel:
    """Семантическое состояние строк ``admin_physical_tables``."""

    def __init__(self, rows: Iterable[Mapping[str, Any]] = ()) -> None:
        self._baseline: dict[str, dict[str, Any]] = {}
        self._current: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []
        self._new_ids: set[str] = set()
        self._pending_delete: set[str] = set()
        self._new_counter = 0
        self.capture(rows)

    def capture(self, rows: Iterable[Mapping[str, Any]]) -> None:
        baseline: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for source in rows:
            row = normalize_row(source)
            row_id = str(row.get("table_key") or "")
            if not row_id:
                raise ValueError(
                    "Сохранённая строка admin_physical_tables не содержит table_key"
                )
            if row_id in baseline:
                raise ValueError(f"Повторяющийся table_key в снимке: {row_id}")
            baseline[row_id] = row
            order.append(row_id)
        self._baseline = baseline
        self._current = copy.deepcopy(baseline)
        self._order = order
        self._new_ids.clear()
        self._pending_delete.clear()

    def restore(self) -> None:
        self._current = copy.deepcopy(self._baseline)
        self._order = list(self._baseline)
        self._new_ids.clear()
        self._pending_delete.clear()

    @property
    def row_ids(self) -> tuple[str, ...]:
        return tuple(self._order)

    def get_row(self, row_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._current[row_id])

    def is_new(self, row_id: str) -> bool:
        return row_id in self._new_ids

    def is_pending_delete(self, row_id: str) -> bool:
        return row_id in self._pending_delete

    def add_row(self, values: Mapping[str, Any] | None = None) -> str:
        while True:
            self._new_counter += 1
            row_id = f"__new__:{self._new_counter}"
            if row_id not in self._current:
                break
        row = normalize_row(NEW_ROW_DEFAULTS)
        for column, value in (values or {}).items():
            if column in TABLE_COLUMNS:
                row[column] = normalize_value(column, value)
        self._current[row_id] = row
        self._order.append(row_id)
        self._new_ids.add(row_id)
        return row_id

    def set_value(self, row_id: str, column: str, value: Any) -> None:
        if row_id not in self._current:
            raise KeyError(row_id)
        if column not in TABLE_COLUMNS:
            raise KeyError(column)
        if row_id in self._pending_delete:
            raise ValueError("Удаляемую строку нельзя редактировать")
        editable = (
            EDITABLE_NEW_COLUMNS
            if row_id in self._new_ids
            else EDITABLE_EXISTING_COLUMNS
        )
        if column not in editable:
            raise ValueError(f"Поле {column} доступно только для чтения")
        self._current[row_id][column] = normalize_value(column, value)

    def remove_or_stage_delete(self, row_id: str) -> str:
        if row_id in self._new_ids:
            self._new_ids.remove(row_id)
            self._current.pop(row_id, None)
            self._order = [
                candidate for candidate in self._order if candidate != row_id
            ]
            return "removed_new"
        if row_id not in self._current:
            raise KeyError(row_id)
        self._pending_delete.add(row_id)
        return "staged"

    def restore_pending_delete(self, row_id: str) -> None:
        self._pending_delete.discard(row_id)

    def disable(self, row_id: str) -> None:
        if row_id in self._pending_delete:
            self._pending_delete.remove(row_id)
        self.set_value(row_id, "is_enabled", 0)

    @property
    def changed_cells(self) -> frozenset[tuple[str, str]]:
        result: set[tuple[str, str]] = set()
        default_new = normalize_row(NEW_ROW_DEFAULTS)
        for row_id in self._order:
            if row_id in self._pending_delete:
                continue
            current = self._current[row_id]
            if row_id in self._new_ids:
                for column in EDITABLE_NEW_COLUMNS:
                    if current.get(column) != default_new.get(column):
                        result.add((row_id, column))
                continue
            before = self._baseline[row_id]
            for column in TABLE_COLUMNS:
                if column in IGNORED_DIRTY_COLUMNS:
                    continue
                if before.get(column) != current.get(column):
                    result.add((row_id, column))
        return frozenset(result)

    @property
    def changed_row_ids(self) -> frozenset[str]:
        return frozenset(
            {row_id for row_id, _ in self.changed_cells}
            | self._new_ids
            | self._pending_delete
        )

    @property
    def is_dirty(self) -> bool:
        return bool(self.changed_cells or self._new_ids or self._pending_delete)

    @property
    def new_count(self) -> int:
        return len(self._new_ids)

    @property
    def pending_delete_count(self) -> int:
        return len(self._pending_delete)

    @property
    def validation_issues(self) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        active_ids = [
            row_id for row_id in self._order if row_id not in self._pending_delete
        ]
        for row_id in active_ids:
            row = self._current[row_id]
            for column in ("table_key", "db_key", "table_name"):
                if not str(row.get(column) or "").strip():
                    issues.append(
                        ValidationIssue(row_id, column, "значение обязательно")
                    )
            ttl = row.get("cache_lifetime_min")
            if not isinstance(ttl, int) or isinstance(ttl, bool):
                issues.append(
                    ValidationIssue(row_id, "cache_lifetime_min", "нужно целое число")
                )
            elif ttl < 0:
                issues.append(
                    ValidationIssue(
                        row_id,
                        "cache_lifetime_min",
                        "значение не может быть отрицательным",
                    )
                )

        by_table_key: dict[str, list[str]] = {}
        by_source_name: dict[tuple[str, str], list[str]] = {}
        for row_id in self._order:
            # Удаляемая строка занимает identity до завершения транзакции;
            # замена тем же ключом внутри одного черновика намеренно запрещена.
            row = self._current[row_id]
            table_key = str(row.get("table_key") or "").strip()
            db_key = str(row.get("db_key") or "").strip()
            table_name = str(row.get("table_name") or "").strip()
            if table_key:
                by_table_key.setdefault(table_key, []).append(row_id)
            if db_key and table_name:
                by_source_name.setdefault((db_key, table_name), []).append(row_id)
        for table_key, row_ids in by_table_key.items():
            if len(row_ids) > 1:
                for row_id in row_ids:
                    issues.append(
                        ValidationIssue(
                            row_id, "table_key", f"ключ {table_key!r} уже используется"
                        )
                    )
        for (db_key, table_name), row_ids in by_source_name.items():
            if len(row_ids) > 1:
                for row_id in row_ids:
                    issues.append(
                        ValidationIssue(
                            row_id,
                            "table_name",
                            f"пара ({db_key}, {table_name}) уже зарегистрирована",
                        )
                    )
        return tuple(issues)

    def changeset(self) -> PhysicalTablesChangeSet:
        issues = self.validation_issues
        if issues:
            raise PhysicalTablesValidationError(issues)
        inserts = tuple(
            copy.deepcopy(self._current[row_id])
            for row_id in self._order
            if row_id in self._new_ids
        )
        updates: list[RowUpdate] = []
        for row_id in self._order:
            if row_id in self._new_ids or row_id in self._pending_delete:
                continue
            before = self._baseline[row_id]
            current = self._current[row_id]
            values = {
                column: copy.deepcopy(current[column])
                for column in EDITABLE_EXISTING_COLUMNS
                if before.get(column) != current.get(column)
            }
            if values:
                updates.append(
                    RowUpdate(
                        table_key=row_id,
                        baseline={
                            column: copy.deepcopy(before[column]) for column in values
                        },
                        values=values,
                    )
                )
        deletes = tuple(
            str(self._baseline[row_id]["table_key"])
            for row_id in self._order
            if row_id in self._pending_delete
        )
        return PhysicalTablesChangeSet(
            inserts=inserts, updates=tuple(updates), deletes=deletes
        )
