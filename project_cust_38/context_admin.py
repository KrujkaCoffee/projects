from __future__ import annotations

import hashlib
import json
import keyword
import logging
import pathlib
import re
import os
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from project_cust_38 import Cust_SQLite as CSQ  # noqa
from project_cust_38 import Cust_Functions as F  # noqa
from project_cust_38.db_identity import (
    canonical_db_key,
    equivalent_db_keys,
    make_table_key as _make_canonical_table_key,
    resolve_db_identity,
    split_table_key,
    server_db_path,
    srv_db_name,
)

try:
    import Cust_postgresql_cache as CPG
except Exception as e:
    CPG = None

logger = logging.getLogger(__name__)

__all__ = [
    'ADMIN_TABLES',
    'PhysicalTableMeta',
    'TableFieldMeta',
    'SourceMeta',
    'SourceVariantMeta',
    'SchemaManifestMeta',
    'RelationMeta',
    'RelationFieldPairMeta',
    'TableIdentityConflictError',
    'ContextAdminRepo',
    'resolve_db_key',
    'make_table_key',
    'detect_sql_write_targets',
    'is_sql_write',
    'guess_python_name',
    'guess_orm_field_class',
]

ADMIN_TABLES = {
    'physical_tables': 'admin_physical_tables',
    'table_fields': 'admin_table_fields',
    'schema_manifest': 'admin_schema_manifest',
    'relations': 'admin_table_relations',
    'relation_field_pairs': 'admin_relation_field_pairs',
}

EXCLUDED_PREFIXES = ('m_', 'mtdz_', 'eq_', 'rm_', 'jurnaltdz_', 'm_cld_')


class TableIdentityConflictError(RuntimeError):
    """Several admin rows represent one physical database/table identity.

    The server must stop rather than guess which table_key owns cache and
    invalidation state. Resolution/migration is an explicit maintenance task.
    """


def _json_dumps(data: Any) -> str:
    return json.dumps(data if data is not None else {}, ensure_ascii=False, sort_keys=False, separators=(',', ':'))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _normalize_path(value: str | pathlib.Path | None) -> str:
    if value is None:
        return ''
    text = str(value).strip().strip('"').strip("'")
    if not text:
        return ''
    return str(pathlib.Path(text))


def _is_server_process() -> bool:
    return bool(os.environ.get('MES_IS_SERVER'))


def _quote_sqlite_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _is_excluded_table(table_name: str) -> bool:
    return any(str(table_name or '').startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def _coerce_bool(value: Any, default: int = 0) -> int:
    if value in (None, ''):
        return int(default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(bool(value))
    text = str(value).strip().lower()
    if text in {'1', 'true', 'yes', 'y', 'да'}:
        return 1
    if text in {'0', 'false', 'no', 'n', 'нет'}:
        return 0
    return int(default)


def resolve_db_key(db_path: str | pathlib.Path | None) -> str:
    """Compatibility wrapper returning the canonical physical file stem.

    Historic values such as ``db_naryad`` remain accepted by
    :mod:`db_identity`, but new metadata is always written as ``Naryad``.
    """
    return canonical_db_key(db_path)


def make_table_key(db_key: str, table_name: str) -> str:
    return _make_canonical_table_key(db_key, table_name)


def guess_python_name(field_name: str) -> str:
    text = str(field_name).strip()
    if not text:
        return '_'
    text = re.sub(r'[\s\-./]+', '_', text)
    text = re.sub(r'[^\w]', '_', text, flags=re.UNICODE)
    text = re.sub(r'_+', '_', text).strip('_')
    if not text:
        text = '_'
    if text[0].isdigit():
        text = f'_{text}'
    if keyword.iskeyword(text):
        text = f'{text}_'
    return text


def guess_orm_field_class(db_type: str | None) -> str:
    raw = str(db_type or '').strip().lower()
    if any(token in raw for token in ('int', 'integer', 'bigint', 'smallint', 'tinyint')):
        return 'IntField'
    if any(token in raw for token in ('real', 'float', 'double', 'numeric', 'decimal')):
        return 'FloatField'
    if 'blob' in raw or 'binary' in raw:
        return 'BlobField'
    if 'bool' in raw:
        return 'BoolField'
    if 'date' in raw or 'time' in raw:
        return 'DateTimeField'
    return 'StrField'


def _default_for_orm_field(orm_field_class: str, nullable: bool) -> str:
    if nullable:
        return 'None'
    mapping = {
        'IntField': '0',
        'FloatField': '0.0',
        'BlobField': "b''",
        'BoolField': '0',
        'DateTimeField': "''",
        'StrField': "''",
    }
    return mapping.get(orm_field_class, "''")


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.S)
    sql = re.sub(r'--[^\n]*', ' ', sql)
    return sql


def is_sql_write(sql: str) -> bool:
    if not isinstance(sql, str):
        return False
    cleaned = _strip_sql_comments(sql).strip().upper()
    if not cleaned:
        return False
    first = cleaned.split(None, 1)[0]
    return first in {'INSERT', 'UPDATE', 'DELETE', 'REPLACE'}


def _normalize_sql_target_name(name: str) -> str:
    cleaned = name.strip().strip('"').strip('`').strip('[').strip(']')
    cleaned = cleaned.rstrip(',;')
    return cleaned


def detect_sql_write_targets(sql: str) -> list[str]:
    if not is_sql_write(sql):
        return []
    cleaned = _strip_sql_comments(sql)
    targets: list[str] = []
    patterns = (
        r'\bINSERT\s+INTO\s+([\w.\[\]"`]+)',
        r'\bREPLACE\s+INTO\s+([\w.\[\]"`]+)',
        r'\bUPDATE\s+([\w.\[\]"`]+)',
        r'\bDELETE\s+FROM\s+([\w.\[\]"`]+)',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, cleaned, flags=re.I):
            target = _normalize_sql_target_name(match.group(1))
            if target and target not in targets:
                targets.append(target)
    return targets


@dataclass(frozen=True)
class PhysicalTableMeta:
    table_key: str
    db_key: str
    table_name: str
    is_enabled: int = 1
    cache_enabled: int = 1
    schema_enabled: int = 1
    stale_after_dt: str | None = None
    cache_lifetime_min: int = 120
    validity_mark: str = ''
    content_hash: str = ''
    version: str = ''
    invalidated_at: str | None = None
    notes: str = ''
    updated_at: str = ''


@dataclass(frozen=True)
class TableFieldMeta:
    table_key: str
    field_name: str
    python_name: str
    db_type: str = ''
    nullable: int = 1
    is_pk: int = 0
    label: str = ''
    sort_order: int = 0
    include_in_schema: int = 1
    orm_field_class: str = ''
    widget_hint: str = ''
    form_hint: str = ''
    notes: str = ''
    updated_at: str = ''


@dataclass(frozen=True)
class SourceMeta:
    source_code: str
    source_kind: str = 'sql'
    base_table_key: str | None = None
    schema_source_table_key: str | None = None
    schema_enabled: int = 1
    cache_enabled: int = 1
    stale_after_dt: str | None = None
    cache_lifetime_min: int = 120
    validity_mark: str = ''
    invalidated_at: str | None = None
    notes: str = ''
    updated_at: str = ''


@dataclass(frozen=True)
class SourceVariantMeta:
    source_code: str
    sql_text: str = ''
    sql_template: str = ''
    resolved_args_json: str = '{}'
    variant_fingerprint: str = ''
    resolved_sql_hash: str = ''
    dependency_fingerprint: str = ''
    invalidated_at: str | None = None
    last_used_at: str | None = None
    last_refresh_at: str | None = None
    last_verified_at: str | None = None
    is_pinned: int = 0
    notes: str = ''
    updated_at: str = ''


@dataclass(frozen=True)
class SchemaManifestMeta:
    generated_at_utc: str
    generator_version: str
    admin_schema_hash: str
    table_fields_hash: str
    artifact_version: str
    notes: str = ''


@dataclass(frozen=True)
class RelationMeta:
    relation_key: str
    relation_name: str
    source_table_key: str
    target_table_key: str
    cardinality: str = 'many_to_one'
    join_type: str = 'LEFT JOIN'
    missing_policy: str = 'none'
    on_many_policy: str = 'error'
    select_prefix: str = ''
    is_enabled: int = 1
    is_generated: int = 0
    notes: str = ''
    updated_at: str = ''


@dataclass(frozen=True)
class RelationFieldPairMeta:
    relation_key: str
    pair_no: int
    left_table_key: str
    left_field_name: str
    right_table_key: str
    right_field_name: str
    role: str = 'direct'
    operator: str = '='
    pair_join_type: str = ''


class ContextAdminRepo:
    """административный контур кэшируемых таблиц"""

    def __init__(self, db_files: str | pathlib.Path | None = None, create_base_tables: bool = False):
        self.db_files = _normalize_path(db_files) or 'SRV:BD_files.db'
        self.create_base_tables = create_base_tables

    @staticmethod
    def _identity_aliases(db_key_or_path: Any) -> tuple[str, ...]:
        return equivalent_db_keys(db_key_or_path)

    @staticmethod
    def _validate_identity_row(row: Mapping[str, Any]) -> None:
        table_key = str(row.get('table_key') or '').strip()
        db_key = str(row.get('db_key') or '').strip()
        table_name = str(row.get('table_name') or '').strip()
        key_db, key_table = split_table_key(table_key)
        errors: list[str] = []
        if not table_key or not db_key or not table_name or not key_table:
            errors.append('неполная identity')
        if key_table and key_table.casefold() != table_name.casefold():
            errors.append(f'table_key table={key_table!r} != table_name={table_name!r}')
        if key_db and canonical_db_key(key_db).casefold() != canonical_db_key(db_key).casefold():
            errors.append(f'table_key db={key_db!r} != db_key={db_key!r}')
        if errors:
            raise TableIdentityConflictError(
                f'Неконсистентная admin_physical_tables identity {table_key!r}: ' + '; '.join(errors)
            )

    def find_registered_table_identity(
            self,
            *,
            db_key_or_path: Any,
            table_name: str,
            raise_on_conflict: bool = True,
    ) -> dict[str, Any]:
        """Resolve a physical table without rewriting any existing key.

        ``Naryad`` and historic ``db_naryad`` are aliases of one physical DB.
        If one matching row exists, its current ``table_key`` remains the
        authoritative cache/invalidation key. If two matching rows exist, the
        method refuses to choose: an automatic merge could orphan relation,
        field and request-cache rows.
        """
        table_name = str(table_name or '').strip()
        identity = resolve_db_identity(db_key_or_path)
        aliases = self._identity_aliases(db_key_or_path)
        canonical_table_key = _make_canonical_table_key(identity.canonical_key, table_name)
        if not table_name:
            return {
                'canonical_db_key': identity.canonical_key,
                'canonical_table_key': '',
                'aliases': aliases,
                'row': None,
                'conflicts': [],
            }

        lowered = [alias.casefold() for alias in aliases]
        placeholders = ','.join('%s' for _ in lowered)
        rows = CPG.custom_request_pg(
            f"""
            SELECT table_key, db_key, table_name
            FROM {ADMIN_TABLES['physical_tables']}
            WHERE lower(table_name) = lower(%s)
              AND lower(db_key) IN ({placeholders})
            ORDER BY table_key
            """,
            params=[table_name, *lowered],
            rez_dict=True,
        ) or []
        unique_rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            normalized_row = dict(row)
            self._validate_identity_row(normalized_row)
            key = str(normalized_row.get('table_key') or '')
            if not key or key in seen:
                continue
            seen.add(key)
            unique_rows.append(normalized_row)

        if len(unique_rows) > 1:
            message = (
                f'Конфликт table identity: {identity.canonical_key}.{table_name}; '
                f'найдены {[row.get("table_key") for row in unique_rows]!r}. '
                'Автоматическая нормализация запрещена.'
            )
            if raise_on_conflict:
                raise TableIdentityConflictError(message)
            return {
                'canonical_db_key': identity.canonical_key,
                'canonical_table_key': canonical_table_key,
                'aliases': aliases,
                'row': None,
                'conflicts': unique_rows,
                'error': message,
            }

        return {
            'canonical_db_key': identity.canonical_key,
            'canonical_table_key': canonical_table_key,
            'aliases': aliases,
            'row': unique_rows[0] if unique_rows else None,
            'conflicts': [],
        }

    def audit_table_identity_conflicts(self) -> list[dict[str, Any]]:
        """Read-only audit. It never updates admin/cache tables."""
        rows = CPG.custom_request_pg(
            f"""SELECT table_key, db_key, table_name
            FROM {ADMIN_TABLES['physical_tables']}
            ORDER BY table_name, db_key""",
            rez_dict=True,
        ) or []
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows:
            canonical = canonical_db_key(row.get('db_key'))
            marker = (canonical.casefold(), str(row.get('table_name') or '').casefold())
            grouped.setdefault(marker, []).append(dict(row))
        return [
            {
                'canonical_db_key': canonical_db_key(items[0].get('db_key')),
                'table_name': items[0].get('table_name'),
                'rows': items,
            }
            for items in grouped.values()
            if len({str(item.get('table_key') or '') for item in items}) > 1
        ]

    def _upsert(self, table_name: str, record: Mapping[str, Any], conflict_cols: Sequence[str],
                update_cols: Sequence[str] | None = None) -> bool:
        if not record:
            return False
        cols = list(record.keys())
        placeholders = ','.join('%s' for _ in cols)
        if update_cols is None:
            update_cols = [col for col in cols if col not in set(conflict_cols)]
        update_cols = [col for col in update_cols if col not in set(conflict_cols)]
        if update_cols:
            update_sql = ', '.join(f'{col}=excluded.{col}' for col in update_cols)
            sql = f'INSERT INTO {table_name} ({", ".join(cols)}) VALUES ({placeholders}) ON CONFLICT({", ".join(conflict_cols)}) DO UPDATE SET {update_sql};'
        else:
            sql = f'INSERT OR IGNORE INTO {table_name} ({", ".join(cols)}) VALUES ({placeholders});'
        return CPG.custom_request_pg(
            sql,
            params=[[record[col] for col in cols]]
        )

    def register_physical_table(
            self,
            *,
            table_key: str,
            db_key: str,
            table_name: str,
            is_enabled: int = 1,
            cache_enabled: int = 1,
            schema_enabled: int = 1,
            stale_after_dt: str | None = None,
            cache_lifetime_min: int = 120,
            validity_mark: str | None = None,
            content_hash: str = '',
            version: str = '',
            invalidated_at: str | None = None,
            notes: str = '',
    ) -> bool:
        now = F.now()
        record = {
            'table_key': table_key,
            'db_key': db_key,
            'table_name': table_name,
            'is_enabled': _coerce_bool(is_enabled, 1),
            'cache_enabled': _coerce_bool(cache_enabled, 1),
            'schema_enabled': _coerce_bool(schema_enabled, 1),
            'stale_after_dt': stale_after_dt,
            'cache_lifetime_min': int(cache_lifetime_min or 120),
            'validity_mark': validity_mark or uuid.uuid4().hex,
            'content_hash': content_hash or '',
            'version': version or '',
            'invalidated_at': invalidated_at,
            'notes': notes or '',
            'updated_at': now,
        }
        return self._upsert(ADMIN_TABLES['physical_tables'], record, ['table_key'])

    def register_table_field(
            self,
            *,
            table_key: str,
            field_name: str,
            python_name: str | None = None,
            db_type: str = '',
            nullable: int = 1,
            is_pk: int = 0,
            label: str = '',
            sort_order: int = 0,
            include_in_schema: int = 1,
            orm_field_class: str | None = None,
            widget_hint: str = '',
            form_hint: str = '',
            notes: str = '',
    ) -> bool:
        record = {
            'table_key': table_key,
            'field_name': field_name,
            'python_name': python_name or guess_python_name(field_name),
            'db_type': db_type or '',
            'nullable': _coerce_bool(nullable, 1),
            'is_pk': _coerce_bool(is_pk, 0),
            'label': label or field_name,
            'sort_order': int(sort_order or 0),
            'include_in_schema': _coerce_bool(include_in_schema, 1),
            'orm_field_class': orm_field_class or guess_orm_field_class(db_type),
            'widget_hint': widget_hint or '',
            'form_hint': form_hint or '',
            'notes': notes or '',
            'updated_at': F.now(),
        }
        return self._upsert(ADMIN_TABLES['table_fields'], record, ['table_key', 'field_name'])

    def register_relation(
            self,
            *,
            relation_key: str,
            relation_name: str,
            source_table_key: str,
            target_table_key: str,
            cardinality: str = 'many_to_one',
            shape: str = 'one',  # compatibility input; derived from cardinality, not persisted
            join_type: str = 'LEFT JOIN',
            missing_policy: str = 'none',
            on_many_policy: str = 'error',
            select_prefix: str = '',
            is_enabled: int = 1,
            is_generated: int = 0,
            notes: str = '',
    ) -> bool:
        record = {
            'relation_key': relation_key,
            'relation_name': relation_name or relation_key.split('.')[-1],
            'source_table_key': source_table_key,
            'target_table_key': target_table_key,
            'cardinality': cardinality or 'many_to_one',
            'join_type': join_type or 'LEFT JOIN',
            'missing_policy': missing_policy or 'none',
            'on_many_policy': on_many_policy or 'error',
            'select_prefix': select_prefix or '',
            'is_enabled': _coerce_bool(is_enabled, 1),
            'is_generated': _coerce_bool(is_generated, 0),
            'notes': notes or '',
            'updated_at': F.now(),
        }
        return self._upsert(ADMIN_TABLES['relations'], record, ['relation_key'])

    def register_relation_field_pair(
            self,
            *,
            relation_key: str,
            pair_no: int = 0,
            left_table_key: str,
            left_field_name: str,
            right_table_key: str,
            right_field_name: str,
            role: str = 'direct',
            operator: str = '=',
            pair_join_type: str = '',
    ) -> bool:
        record = {
            'relation_key': relation_key,
            'pair_no': int(pair_no or 0),
            'left_table_key': left_table_key,
            'left_field_name': left_field_name,
            'right_table_key': right_table_key,
            'right_field_name': right_field_name,
            'role': role or 'direct',
            'operator': operator or '=',
            'pair_join_type': pair_join_type or '',
        }
        return self._upsert(ADMIN_TABLES['relation_field_pairs'], record, ['relation_key', 'pair_no'])

    def upsert_relation_spec(self, relation_spec: Any) -> dict[str, Any]:
        try:
            from project_cust_38.context_relations import relation_to_admin_records
        except Exception:
            from context_relations import relation_to_admin_records  # type: ignore

        header, pairs = relation_to_admin_records(relation_spec)
        ok_header = self.register_relation(**header)
        ok_pairs = []
        for pair in pairs:
            ok_pairs.append(self.register_relation_field_pair(**pair))
        return {
            'ok': bool(ok_header and all(ok_pairs or [True])),
            'relation_key': header.get('relation_key'),
            'pairs_count': len(pairs),
        }

    def get_relations(self, *, only_enabled: bool = False) -> list[dict[str, Any]]:
        where_sql = 'WHERE is_enabled = 1' if only_enabled else ''
        return CPG.custom_request_pg(
            f"""SELECT * FROM {ADMIN_TABLES['relations']}
            {where_sql}
            ORDER BY source_table_key, relation_name""",
            rez_dict=True,
        ) or []

    def get_relation_field_pairs(self, relation_key: str | None = None) -> list[dict[str, Any]]:
        if relation_key:
            return CPG.custom_request_pg(
                f"""SELECT * FROM {ADMIN_TABLES['relation_field_pairs']}
                WHERE relation_key = {relation_key!r}
                ORDER BY relation_key, pair_no""",
                rez_dict=True,
            ) or []
        return CPG.custom_request_pg(
            f"""SELECT * FROM {ADMIN_TABLES['relation_field_pairs']}
            ORDER BY relation_key, pair_no""",
            rez_dict=True,
        ) or []

    def write_manifest(self, manifest: SchemaManifestMeta | Mapping[str, Any]) -> int:
        data = manifest if isinstance(manifest, Mapping) else manifest.__dict__
        cols = list(data.keys())
        placeholders = ','.join('%s' for _ in cols)
        sql = f"INSERT INTO {ADMIN_TABLES['schema_manifest']} ({', '.join(cols)}) VALUES ({placeholders}) RETURNING generated_at_utc;"
        last_rowid = CPG.custom_request_pg(
            sql,
            one_column=True,
            one=True,
            params=list(data.values())
        )
        logger.info(f'Запись лога манифеста окончена, номер созданной строки: {last_rowid}')
        return last_rowid

    def table_exists_in_db(self, db_path: str, table_name: str) -> bool:
        read_db_path = self._schema_read_db_path(db_path)
        count = CSQ.custom_request_c(
            read_db_path,
            'SELECT COUNT(*) FROM sqlite_master WHERE type = "table" AND name = ?',
            list_of_lists_c=[[table_name]],
            hat_c=False,
            one=True,
            one_column=True,
        )
        try:
            return int(count or 0) > 0
        except Exception:
            return False

    def list_tables_in_db(self, db_path: str) -> list[str]:
        read_db_path = self._schema_read_db_path(db_path)
        return CSQ.custom_request_c(
            read_db_path,
            'SELECT name FROM sqlite_master WHERE type = "table" AND name != "sqlite_sequence" ORDER BY name',
            one_column=True,
            hat_c=False,
        ) or []

    def get_srv_nickname(self, abs_path: str) -> str:
        # Pure path/alias conversion. Importing Cust_client_socket here used to
        # pull a large runtime graph into schema/invalidation paths.
        return srv_db_name(abs_path)

    def bootstrap_physical_table(
            self,
            *,
            db_path: str,
            table_name: str,
            db_key: str | None = None,
            table_key: str | None = None,
            include_fields: bool = True,
            schema_enabled: int = 1,
            cache_enabled: int = 1,
            is_enabled: int = 1,
            cache_lifetime_min: int = 120,
            notes: str = '',
    ) -> str:
        db_path = _normalize_path(db_path)
        if not db_path:
            raise ValueError('db_path не задан')

        read_db_path = self._schema_read_db_path(db_path)

        if not self.table_exists_in_db(read_db_path, table_name):
            raise ValueError(
                f'Таблица {table_name!r} не найдена в БД {db_path!r}; schema_read_db_path={read_db_path!r}'
            )

        identity_state = self.find_registered_table_identity(
            db_key_or_path=db_key or db_path,
            table_name=table_name,
        )
        existing_row = identity_state.get('row') or {}
        if existing_row:
            # Preserve the key already referenced by fields, relations and
            # request-cache rows. Renaming is an explicit migration only.
            db_key = str(existing_row.get('db_key') or identity_state['canonical_db_key'])
            table_key = str(existing_row.get('table_key') or identity_state['canonical_table_key'])
        else:
            db_key = str(identity_state['canonical_db_key'])
            table_key = str(identity_state['canonical_table_key'])
        is_success = self.register_physical_table(
            table_key=table_key,
            db_key=db_key,
            table_name=table_name,
            is_enabled=is_enabled,
            cache_enabled=cache_enabled,
            schema_enabled=schema_enabled,
            cache_lifetime_min=cache_lifetime_min,
            notes=notes,
        )
        logger.info(
            f'[ContextAdminRepo.bootstrap_physical_table] Регистрация таблицы {table_name} Статус: {is_success}')
        if include_fields:
            self.bootstrap_table_fields(db_path=db_path, table_name=table_name, table_key=table_key)
        return table_key

    def bootstrap_table_fields(self, *, db_path: str, table_name: str, table_key: str) -> int:
        read_db_path = self._schema_read_db_path(db_path)
        sql = f'PRAGMA table_info({_quote_sqlite_ident(table_name)})'
        rows = CSQ.custom_request_c(
            read_db_path,
            sql,
            hat_c=False,
        ) or []
        count = 0
        for row in rows:
            cid, field_name, db_type, notnull, default_value, pk = row
            is_success = self.register_table_field(
                table_key=table_key,
                field_name=field_name,
                python_name=guess_python_name(field_name),
                db_type=db_type or '',
                nullable=0 if notnull else 1,
                is_pk=1 if pk else 0,
                label=field_name,
                sort_order=int(cid or 0),
                include_in_schema=1,
                orm_field_class=guess_orm_field_class(db_type),
                notes=f'default={default_value!r}' if default_value is not None else '',
            )
            logger.info(
                f'[ContextAdminRepo.bootstrap_table_fields] - [{table_name}] Регистрация поля {field_name} Статус: {is_success}'
            )
            count += 1

        return count

        count = 0
        current_field_names: list[str] = []
        for row in rows:
            cid, field_name, db_type, notnull, default_value, pk = row
            current_field_names.append(str(field_name))
            is_success = self.register_table_field(
                table_key=table_key,
                field_name=field_name,
                python_name=guess_python_name(field_name),
                db_type=db_type or '',
                nullable=0 if notnull else 1,
                is_pk=1 if pk else 0,
                label=field_name,
                sort_order=int(cid or 0),
                include_in_schema=1,
                orm_field_class=guess_orm_field_class(db_type),
                notes=f'default={default_value!r}' if default_value is not None else '',
            )
            logger.info(
                f'[ContextAdminRepo.bootstrap_table_fields] - [{table_name}] Регистрация поля {field_name} Статус: {is_success}')
            count += 1

        self.disable_removed_table_fields(table_key=table_key, current_field_names=current_field_names)
        return count

    def bootstrap_tables_from_db(
            self,
            *,
            db_path: str,
            table_names: Sequence[str] | None = None,
            db_key: str | None = None,
            include_fields: bool = True,
            schema_enabled: int = 1,
            cache_enabled: int = 1,
            is_enabled: int = 1,
            cache_lifetime_min: int = 120,
            notes: str = '',
            skip_tables: list[str] = None
    ) -> list[str]:
        if not isinstance(skip_tables, (tuple, set, list)):
            skip_tables = []
        db_path = _normalize_path(db_path)
        names = list(table_names or self.list_tables_in_db(db_path))
        result: list[str] = []
        for table_name in names:
            if any(table_name.startswith(prefix) for prefix in EXCLUDED_PREFIXES) or table_name in skip_tables:
                logger.info(f'[bootstrap_tables_from_db] table {table_name} skip')
                continue
            result.append(
                self.bootstrap_physical_table(
                    db_path=db_path,
                    table_name=table_name,
                    db_key=db_key,
                    include_fields=include_fields,
                    schema_enabled=schema_enabled,
                    cache_enabled=cache_enabled,
                    is_enabled=is_enabled,
                    cache_lifetime_min=cache_lifetime_min,
                    notes=notes,
                )
            )
        return result

    def get_physical_tables(self, *, schema_enabled: int | None = None, only_enabled: bool = False) -> list[
        dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if schema_enabled is not None:
            where.append(f'schema_enabled = {int(schema_enabled)}')
            params.append(int(schema_enabled))
        if only_enabled:
            where.append('is_enabled = 1')
        where_sql = f"WHERE {' AND '.join(where)}" if where else ''
        return CPG.custom_request_pg(
            f"SELECT * FROM {ADMIN_TABLES['physical_tables']} {where_sql} ORDER BY db_key, table_name",
            rez_dict=True
        )

    def get_table_fields(self, table_key: str | None = None, *, include_disabled: bool = True) -> list[dict[str, Any]]:
        if table_key:
            where_sql = '' if include_disabled else ' AND include_in_schema = 1 '
            return CPG.custom_request_pg(
                f"""SELECT * FROM {ADMIN_TABLES['table_fields']}
                WHERE table_key = {table_key!r}{where_sql}
                ORDER BY sort_order, field_name""",
                rez_dict=True,
            )
        where_sql = '' if include_disabled else 'WHERE include_in_schema = 1'
        return CPG.custom_request_pg(
            f"""SELECT * FROM {ADMIN_TABLES['table_fields']}
            {where_sql}
            ORDER BY table_key, sort_order, field_name""",
            rez_dict=True
        )

    def latest_manifest(self) -> dict[str, Any] | None:
        return CPG.custom_request_pg(
            f"""SELECT * FROM {ADMIN_TABLES['schema_manifest']}
                ORDER BY manifest_id DESC
                LIMIT 1""",
            one=True,
        )

    def compute_manifest_hashes(self) -> dict[str, str]:
        physical_tables = self.get_physical_tables()
        table_fields = self.get_table_fields()
        relation_specs = self.get_relations()
        relation_field_pairs = self.get_relation_field_pairs()
        admin_schema_hash = _sha256_text(_json_dumps({
            'physical_tables': physical_tables,
            'relation_specs': relation_specs,
        }))
        table_fields_hash = _sha256_text(_json_dumps(table_fields))
        relation_specs_hash = _sha256_text(_json_dumps({
            'relation_specs': relation_specs,
            'relation_field_pairs': relation_field_pairs,
        }))
        return {
            'admin_schema_hash': admin_schema_hash,
            'table_fields_hash': table_fields_hash,
            'relation_specs_hash': relation_specs_hash,
        }

    def ensure_table_registered_for_invalidation(self, *, db_path: str, table_name: str) -> dict[str, str]:
        db_path = _normalize_path(db_path)
        identity_state = self.find_registered_table_identity(
            db_key_or_path=db_path,
            table_name=table_name,
        )
        existing_row = identity_state.get('row') or {}
        db_key = str(existing_row.get('db_key') or identity_state['canonical_db_key'])
        table_key = str(existing_row.get('table_key') or identity_state['canonical_table_key'])
        existing = bool(existing_row)
        is_dynamic_table = _is_excluded_table(table_name)
        if not existing and db_path and self.table_exists_in_db(db_path, table_name):
            self.bootstrap_physical_table(
                db_path=db_path,
                table_name=table_name,
                db_key=db_key,
                table_key=table_key,
                include_fields=not is_dynamic_table,
                schema_enabled=1,
                cache_enabled=1,
                is_enabled=1,
                notes='auto-registered by server-side invalidation',
            )
        return {
            'db_path': db_path,
            'db_key': db_key,
            'table_name': table_name,
            'table_key': table_key,
        }

    @staticmethod
    def _sql_literal(value: Any) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    @staticmethod
    def _escape_like(value: Any) -> str:
        text = str(value)
        text = text.replace('\\', '\\\\')
        text = text.replace('%', '\\%')
        text = text.replace('_', '\\_')
        return text

    @staticmethod
    def _unique_names(values: Sequence[Any] | None) -> list[str]:
        result: list[str] = []
        seen = set()
        for value in values or ():
            text = str(value or '').strip()
            if not text or text in {'__schema__', 'sqlite_master', 'sqlite_schema'}:
                continue
            if '.' in text:
                text = text.split('.')[-1].strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
        return result

    def get_physical_tables_by_names(self, table_names: Sequence[str] | None) -> list[dict[str, Any]]:
        names = self._unique_names(table_names)
        if not names:
            return []

        in_sql = ','.join(self._sql_literal(name) for name in names)
        like_sql = ' OR '.join(
            f"table_key LIKE {self._sql_literal(f'%.{self._escape_like(name)}')} ESCAPE '\\'"
            for name in names
        )
        where_sql = f"table_name IN ({in_sql})"
        if like_sql:
            where_sql = f"({where_sql} OR {like_sql})"

        return CPG.custom_request_pg(
            f"""
            SELECT *
            FROM {ADMIN_TABLES['physical_tables']}
            WHERE {where_sql}
            ORDER BY db_key, table_name
            """,
            rez_dict=True,
        ) or []

    def mark_all_tables_invalidated(self, notes: str = '', return_details: bool = False) -> dict[str, Any]:
        rows = CPG.custom_request_pg(
            f"SELECT table_key, table_name FROM {ADMIN_TABLES['physical_tables']} ORDER BY db_key, table_name",
            rez_dict=True,
        ) or []
        table_keys = [str(row.get('table_key') or '').strip() for row in rows if row.get('table_key')]
        table_names = [str(row.get('table_name') or '').strip() for row in rows if row.get('table_name')]
        if not table_keys:
            result = {'ok': False, 'wide': True, 'table_names': [], 'table_keys': []}
            return result if return_details else result

        now = F.now()
        joined = ','.join(self._sql_literal(key) for key in table_keys)
        update_result = CPG.custom_request_pg(
            f"""
            UPDATE {ADMIN_TABLES['physical_tables']}
            SET validity_mark = %s,
                invalidated_at = %s,
                updated_at = %s,
                notes = CASE WHEN notes IS NULL OR notes = '' THEN %s ELSE notes END
            WHERE table_key IN ({joined})
            """,
            params=[[uuid.uuid4().hex, now, now, notes or 'external_schema_wide_invalidation']],
        )
        result = {'ok': bool(update_result), 'wide': True, 'table_names': table_names, 'table_keys': table_keys}
        return result if return_details else result

    def mark_table_names_invalidated(self, table_names: Sequence[str] | None, notes: str = '',
                                     return_details: bool = False) -> dict[str, Any]:
        names = self._unique_names(table_names)
        rows = self.get_physical_tables_by_names(names)
        table_keys = []
        seen = set()
        for row in rows:
            key = str(row.get('table_key') or '').strip()
            if key and key not in seen:
                seen.add(key)
                table_keys.append(key)

        if not table_keys:
            result = {'ok': False, 'table_names': names, 'table_keys': []}
            return result if return_details else result

        now = F.now()
        joined = ','.join(self._sql_literal(key) for key in table_keys)
        update_result = CPG.custom_request_pg(
            f"""
            UPDATE {ADMIN_TABLES['physical_tables']}
            SET validity_mark = %s,
                invalidated_at = %s,
                updated_at = %s,
                notes = CASE WHEN notes IS NULL OR notes = '' THEN %s ELSE notes END
            WHERE table_key IN ({joined})
            """,
            params=[[uuid.uuid4().hex, now, now, notes or 'external_invalidation']],
        )
        result = {'ok': bool(update_result), 'table_names': names, 'table_keys': table_keys}
        return result if return_details else result

    def _resolve_local_db_path_by_key(self, db_key: str) -> str:
        raw_key = str(db_key or '').strip()
        if not raw_key:
            return ''
        return server_db_path(raw_key)

    def disable_removed_table_fields(self, *, table_key: str, current_field_names: Sequence[str]) -> bool:
        current = [str(name) for name in current_field_names if str(name).strip()]
        if not table_key or not current:
            return False

        joined_fields = ','.join(self._sql_literal(name) for name in current)
        now = F.now()
        return bool(CPG.custom_request_pg(
            f"""
            UPDATE {ADMIN_TABLES['table_fields']}
            SET include_in_schema = 0,
                updated_at = %s,
                notes = CASE WHEN notes IS NULL OR notes = '' THEN %s ELSE notes END
            WHERE table_key = %s
              AND field_name NOT IN ({joined_fields})
            """,
            params=[[now, 'disabled by ddl schema sync', table_key]],
        ))

    def disable_missing_physical_table(self, *, table_key: str, notes: str = '') -> bool:
        if not table_key:
            return False
        now = F.now()
        ok_table = CPG.custom_request_pg(
            f"""
            UPDATE {ADMIN_TABLES['physical_tables']}
            SET is_enabled = 0,
                schema_enabled = 0,
                cache_enabled = 0,
                validity_mark = %s,
                invalidated_at = %s,
                updated_at = %s,
                notes = CASE WHEN notes IS NULL OR notes = '' THEN %s ELSE notes END
            WHERE table_key = %s
            """,
            params=[[uuid.uuid4().hex, now, now, notes or 'disabled by ddl schema sync', table_key]],
        )
        ok_fields = CPG.custom_request_pg(
            f"""
            UPDATE {ADMIN_TABLES['table_fields']}
            SET include_in_schema = 0,
                updated_at = %s,
                notes = CASE WHEN notes IS NULL OR notes = '' THEN %s ELSE notes END
            WHERE table_key = %s
            """,
            params=[[now, notes or 'disabled by ddl schema sync', table_key]],
        )
        return bool(ok_table or ok_fields)

    def sync_schema_for_table_names(self, table_names: Sequence[str] | None, notes: str = '') -> dict[str, Any]:
        rows = self.get_physical_tables_by_names(table_names)
        refreshed: list[dict[str, Any]] = []
        disabled: list[str] = []
        errors: list[dict[str, str]] = []

        for row in rows:
            table_key = str(row.get('table_key') or '').strip()
            table_name = str(row.get('table_name') or '').strip()
            db_key = str(row.get('db_key') or '').strip()
            db_path = self._resolve_local_db_path_by_key(db_key)
            if not table_key or not table_name or not db_path:
                errors.append({'table_key': table_key, 'error': 'Данные запроса не содержат информации'})
                continue
            try:
                if self.table_exists_in_db(db_path, table_name):
                    fields_count = self.bootstrap_table_fields(db_path=db_path, table_name=table_name,
                                                               table_key=table_key)
                    refreshed.append({'table_key': table_key, 'fields_count': fields_count})
                else:
                    if self.disable_missing_physical_table(table_key=table_key, notes=notes):
                        disabled.append(table_key)
            except Exception as exc:
                logger.error('[sync_schema_for_table_names] %s %s', table_key, exc)
                errors.append({'table_key': table_key, 'error': str(exc)})

        return {
            'ok': bool(refreshed or disabled) and not errors,
            'refreshed': refreshed,
            'disabled': disabled,
            'errors': errors,
        }

    def mark_tables_invalidated(
            self,
            *,
            table_records: Sequence[Mapping[str, str]],
            notes: str = '',
    ) -> dict[str, Any]:
        now = F.now()
        affected_table_keys: list[str] = []
        for record in table_records:
            db_path = record.get('db_path') or ''
            table_name = record.get('table_name') or ''
            if not table_name:
                continue
            ensured = self.ensure_table_registered_for_invalidation(db_path=db_path, table_name=table_name)
            table_key = ensured['table_key']
            success = CPG.custom_request_pg(
                f"""UPDATE {ADMIN_TABLES['physical_tables']}
                SET validity_mark = %s,
                    invalidated_at = %s,
                    updated_at = %s,
                    notes = CASE WHEN notes IS NULL OR notes = '' THEN %s ELSE notes END
                WHERE table_key = %s""",
                params=[[uuid.uuid4().hex, now, now, notes or '', table_key]]
            )
            if success:
                affected_table_keys.append(table_key)

        if not affected_table_keys:
            logger.info('[mark_sql_write_invalidated] NOT AFFECTED')
            return {'affected_tables': []}
        return {'affected_tables': affected_table_keys}

    def mark_sql_write_invalidated(
            self,
            *,
            sql: str,
            main_db_path: str,
            attach_dbs: Sequence[str] | str | None = (),
            notes: str = '',
            attached_alias_paths: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        targets = detect_sql_write_targets(sql)
        if not targets:
            logger.info('[mark_sql_write_invalidated] NOT TARGETS')
            return {'affected_tables': []}

        if isinstance(attach_dbs, str):
            attach_dbs = (attach_dbs,)
        attached_alias_paths = dict(attached_alias_paths or {})
        records: list[dict[str, str]] = []
        for target in targets:
            if '.' in target:
                alias, table_name = target.split('.', 1)
                db_path = attached_alias_paths.get(alias, '')
                records.append({'db_path': db_path, 'table_name': table_name})
            else:
                records.append({'db_path': main_db_path, 'table_name': target})
        if not records:
            logger.info('[mark_sql_write_invalidated] NOT INVALIDATED')

            return {}
        return self.mark_tables_invalidated(table_records=records, notes=notes)

    def _srv_to_abs_path(self, db_path: str) -> str:
        """SRV:BD_users.db -> C://DB_srv//BD_users.db"""
        db_path = _normalize_path(db_path)
        if not db_path.startswith('SRV:'):
            return db_path
        return _normalize_path(server_db_path(db_path))

    def _schema_read_db_path(self, db_path: str) -> str:
        db_path = _normalize_path(db_path)
        if not db_path:
            return ''

        if _is_server_process():
            if db_path.startswith('SRV:'):
                return self._srv_to_abs_path(db_path)
            return db_path

        if not db_path.startswith('SRV:'):
            return self.get_srv_nickname(db_path) or db_path

        return db_path

    @staticmethod
    def can_direct_sqlite_schema_read(db_path: str) -> bool:
        db_path = _normalize_path(db_path)
        return bool(db_path) and not db_path.startswith('SRV:')
