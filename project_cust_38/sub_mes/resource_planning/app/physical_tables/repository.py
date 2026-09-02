from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .columns import EDITABLE_EXISTING_COLUMNS
from .edit_model import PhysicalTablesChangeSet, normalize_value


class PhysicalTablesConflictError(RuntimeError):
    pass


class PhysicalTablesDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class DependencyAudit:
    fields: int = 0
    relations: int = 0
    pairs: int = 0
    cache_dependencies: int = 0

    @property
    def blocking_count(self) -> int:
        return self.relations + self.pairs + self.cache_dependencies

    def message(self, table_key: str) -> str:
        return (
            f"Зависимости {table_key}: полей — {self.fields}, связей — {self.relations}, "
            f"пар полей — {self.pairs}, кеш-зависимостей — {self.cache_dependencies}."
        )


def _row_value(row: Any, key: str, index: int = 0) -> Any:
    if row is None:
        return None
    if isinstance(row, Mapping):
        return row.get(key)
    return row[index]


class PhysicalTablesRepository:
    """Единая граница чтения и записи реестра физических таблиц."""

    _UPDATE_COLUMNS = tuple(sorted(EDITABLE_EXISTING_COLUMNS))

    def __init__(self, db) -> None:
        self.db = db

    def load(self) -> list[dict[str, Any]]:
        return list(self.db.list_admin_tables())

    @staticmethod
    def _count_from_cursor(cur, query: str, params) -> int:
        cur.execute(query, params)
        row = cur.fetchone()
        return int(_row_value(row, "count", 0) or 0)

    @classmethod
    def _audit_with_cursor(cls, cur, table_key: str) -> DependencyAudit:
        fields = cls._count_from_cursor(
            cur,
            "SELECT COUNT(*) AS count FROM public.admin_table_fields WHERE table_key=%s",
            [table_key],
        )
        relations = cls._count_from_cursor(
            cur,
            """
            SELECT COUNT(*) AS count
            FROM public.admin_table_relations
            WHERE source_table_key=%s OR target_table_key=%s
            """,
            [table_key, table_key],
        )
        pairs = cls._count_from_cursor(
            cur,
            """
            SELECT COUNT(*) AS count
            FROM public.admin_relation_field_pairs
            WHERE left_table_key=%s OR right_table_key=%s
            """,
            [table_key, table_key],
        )
        cur.execute(
            "SELECT to_regclass('public.admin_request_cache_tables') AS table_name"
        )
        cache_table_exists = bool(_row_value(cur.fetchone(), "table_name", 0))
        cache_dependencies = 0
        if cache_table_exists:
            cache_dependencies = cls._count_from_cursor(
                cur,
                "SELECT COUNT(*) AS count FROM public.admin_request_cache_tables WHERE table_key=%s",
                [table_key],
            )
        return DependencyAudit(fields, relations, pairs, cache_dependencies)

    def audit_dependencies(self, table_key: str) -> DependencyAudit:
        fields = int(
            (
                self.db.fetchone(
                    "SELECT COUNT(*) AS count FROM public.admin_table_fields WHERE table_key=%s",
                    [table_key],
                )
                or {}
            ).get("count")
            or 0
        )
        relations = int(
            (
                self.db.fetchone(
                    """
                SELECT COUNT(*) AS count
                FROM public.admin_table_relations
                WHERE source_table_key=%s OR target_table_key=%s
                """,
                    [table_key, table_key],
                )
                or {}
            ).get("count")
            or 0
        )
        pairs = int(
            (
                self.db.fetchone(
                    """
                SELECT COUNT(*) AS count
                FROM public.admin_relation_field_pairs
                WHERE left_table_key=%s OR right_table_key=%s
                """,
                    [table_key, table_key],
                )
                or {}
            ).get("count")
            or 0
        )
        exists = self.db.fetchone(
            "SELECT to_regclass('public.admin_request_cache_tables') AS table_name"
        )
        cache_dependencies = 0
        if exists and exists.get("table_name"):
            cache_dependencies = int(
                (
                    self.db.fetchone(
                        "SELECT COUNT(*) AS count FROM public.admin_request_cache_tables WHERE table_key=%s",
                        [table_key],
                    )
                    or {}
                ).get("count")
                or 0
            )
        return DependencyAudit(fields, relations, pairs, cache_dependencies)

    @classmethod
    def _update_row(cls, cur, update) -> None:
        columns = tuple(sorted(update.values))
        if not columns or any(column not in cls._UPDATE_COLUMNS for column in columns):
            raise ValueError("Набор обновляемых колонок реестра недопустим")
        select_columns = ", ".join(columns)
        cur.execute(
            f"SELECT {select_columns} FROM public.admin_physical_tables "
            "WHERE table_key=%s FOR UPDATE",
            [update.table_key],
        )
        actual = cur.fetchone()
        if actual is None:
            raise PhysicalTablesConflictError(
                f"Таблица {update.table_key} была удалена другим пользователем. Перечитайте реестр."
            )
        conflicts = []
        for index, column in enumerate(columns):
            actual_value = normalize_value(column, _row_value(actual, column, index))
            if actual_value != update.baseline[column]:
                conflicts.append(column)
        if conflicts:
            raise PhysicalTablesConflictError(
                f"Таблица {update.table_key} параллельно изменена в полях: "
                + ", ".join(conflicts)
                + ". Перечитайте реестр; локальный черновик сохранён."
            )
        assignments = ", ".join(f"{column}=%s" for column in columns)
        params = [update.values[column] for column in columns]
        params.append(update.table_key)
        cur.execute(
            f"""
            UPDATE public.admin_physical_tables
            SET {assignments},
                updated_at=to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
            WHERE table_key=%s
            """,
            params,
        )
        if cur.rowcount != 1:
            raise PhysicalTablesConflictError(
                f"Не удалось обновить {update.table_key}: строка исчезла во время сохранения."
            )

    @staticmethod
    def _insert_row(cur, row: Mapping[str, Any]) -> None:
        columns = (
            "table_key",
            "db_key",
            "table_name",
            "is_enabled",
            "cache_enabled",
            "schema_enabled",
            "stale_after_dt",
            "cache_lifetime_min",
            "notes",
        )
        cur.execute(
            """
            INSERT INTO public.admin_physical_tables
                (table_key, db_key, table_name, is_enabled, cache_enabled, schema_enabled,
                 stale_after_dt, cache_lifetime_min, notes, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
            """,
            [row[column] for column in columns],
        )

    @classmethod
    def _delete_row(cls, cur, table_key: str) -> None:
        cur.execute(
            "SELECT table_key FROM public.admin_physical_tables WHERE table_key=%s FOR UPDATE",
            [table_key],
        )
        if cur.fetchone() is None:
            raise PhysicalTablesConflictError(
                f"Таблица {table_key} уже удалена. Перечитайте реестр."
            )
        audit = cls._audit_with_cursor(cur, table_key)
        if audit.blocking_count:
            raise PhysicalTablesDependencyError(
                audit.message(table_key)
                + " Удаление заблокировано: сначала устраните связи и кеш-зависимости либо отключите таблицу."
            )
        cur.execute(
            "DELETE FROM public.admin_physical_tables WHERE table_key=%s", [table_key]
        )
        if cur.rowcount != 1:
            raise PhysicalTablesConflictError(
                f"Не удалось удалить {table_key}: строка изменилась во время сохранения."
            )

    def save(self, changes: PhysicalTablesChangeSet) -> None:
        if changes.is_empty:
            return
        with self.db.transaction() as cur:
            for update in sorted(changes.updates, key=lambda item: item.table_key):
                self._update_row(cur, update)
            for row in sorted(
                changes.inserts, key=lambda item: str(item.get("table_key") or "")
            ):
                self._insert_row(cur, row)
            for table_key in sorted(changes.deletes):
                self._delete_row(cur, table_key)
