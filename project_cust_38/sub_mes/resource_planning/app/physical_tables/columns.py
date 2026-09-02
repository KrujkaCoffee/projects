from __future__ import annotations

TABLE_COLUMNS = (
    "table_key",
    "db_key",
    "table_name",
    "is_enabled",
    "cache_enabled",
    "schema_enabled",
    "stale_after_dt",
    "cache_lifetime_min",
    "validity_mark",
    "content_hash",
    "version",
    "invalidated_at",
    "notes",
    "updated_at",
)

TABLE_LABELS = {
    "table_key": "Ключ таблицы",
    "db_key": "База/источник",
    "table_name": "Имя таблицы",
    "is_enabled": "Включена",
    "cache_enabled": "Кеш включён",
    "schema_enabled": "В схеме",
    "stale_after_dt": "Устаревает после",
    "cache_lifetime_min": "TTL кеша, мин",
    "validity_mark": "Метка валидности",
    "content_hash": "Хеш содержимого",
    "version": "Версия",
    "invalidated_at": "Инвалидирована",
    "notes": "Заметки",
    "updated_at": "Обновлена",
}

BOOL_COLUMNS = frozenset({"is_enabled", "cache_enabled", "schema_enabled"})
INT_COLUMNS = frozenset({"cache_lifetime_min"})
NULLABLE_TEXT_COLUMNS = frozenset({"stale_after_dt", "invalidated_at"})
IDENTITY_COLUMNS = frozenset({"table_key", "db_key", "table_name"})
SYSTEM_COLUMNS = frozenset(
    {"validity_mark", "content_hash", "version", "invalidated_at", "updated_at"}
)
EDITABLE_EXISTING_COLUMNS = frozenset(
    {
        "is_enabled",
        "cache_enabled",
        "schema_enabled",
        "stale_after_dt",
        "cache_lifetime_min",
        "notes",
    }
)
EDITABLE_NEW_COLUMNS = frozenset(IDENTITY_COLUMNS | EDITABLE_EXISTING_COLUMNS)
IGNORED_DIRTY_COLUMNS = frozenset({"updated_at"})

NEW_ROW_DEFAULTS = {
    "table_key": "",
    "db_key": "main",
    "table_name": "",
    "is_enabled": 0,
    "cache_enabled": 1,
    "schema_enabled": 1,
    "stale_after_dt": None,
    "cache_lifetime_min": 120,
    "validity_mark": "",
    "content_hash": "",
    "version": "",
    "invalidated_at": None,
    "notes": "",
    "updated_at": "",
}
