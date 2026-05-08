from __future__ import annotations

import hashlib
import json
import keyword
import logging
import pathlib
import re
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from project_cust_38 import Cust_SQLite as CSQ  # noqa
from project_cust_38 import Cust_Functions as F # noqa
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
}

EXCLUDED_PREFIXES = ('m_', 'mtdz_', 'eq_', 'rm_', 'jurnaltdz_', 'm_cld_')


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


def _iter_project_db_attrs() -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = [
        ("db_naryad", "SRV:Naryad.db"),
        ("db_files", "SRV:BD_files.db"),
        ("db_kplan", "SRV:DB_kplan.db"),
        ("db_users", "SRV:BD_users.db"),
        ("db_resxml", "SRV:BD_resxml.db"),
        ("db_dse", "SRV:BD_dse.db"),
        ("db_nomen", "SRV:DB_nomenklatura_erp.db"),
    ]
    return result




def resolve_db_key(db_path: str | pathlib.Path | None) -> str:
    normalized = _normalize_path(db_path)
    if not normalized:
        return 'unknown_db'
    for attr, candidate in _iter_project_db_attrs():
        if _normalize_path(candidate) == normalized:
            return attr
    return pathlib.Path(normalized).stem


def make_table_key(db_key: str, table_name: str) -> str:
    return f'{db_key}.{table_name}'


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


class ContextAdminRepo:
    """административный контур кэшируемых таблиц"""

    def __init__(self, db_files: str | pathlib.Path | None = None, create_base_tables: bool = False):
        self.db_files = _normalize_path(db_files) or 'SRV:BD_files.db'
        self.create_base_tables = create_base_tables


    def _upsert(self, table_name: str, record: Mapping[str, Any], conflict_cols: Sequence[str], update_cols: Sequence[str] | None = None) -> bool:
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


    def write_manifest(self, manifest: SchemaManifestMeta | Mapping[str, Any]) -> int:
        data = manifest if isinstance(manifest, Mapping) else manifest.__dict__
        cols = list(data.keys())
        placeholders = ','.join('%s' for _ in cols)
        sql = f"INSERT INTO {ADMIN_TABLES['schema_manifest']} ({', '.join(cols)}) VALUES ({placeholders}) RETURNING generated_at_utc;"
        conn, cur = CPG.connect_pg(CPG.PostgresConfig())
        try:
            last_rowid = CPG.custom_request_pg(
                sql,
                one_column=True,
                one=True,
                params=list(data.values())
            )
        finally:
            CPG.close_pg(conn, cur)
        print('[write_manifest] returning: ', last_rowid)
        print('db_files', self.db_files)
        print('LAST_ROWID:', last_rowid)
        return last_rowid

    def table_exists_in_db(self, db_path: str, table_name: str) -> bool:
        return bool(CSQ.custom_request_c(
                db_path,
                'SELECT COUNT(*) FROM sqlite_master WHERE type = "table" AND name = ?',
                list_of_lists_c=(table_name,)
        ))

    def list_tables_in_db(self, db_path: str) -> list[str]:
        return CSQ.custom_request_c(
            db_path,
            'SELECT name FROM sqlite_master WHERE type = "table" AND name != "sqlite_sequence" ORDER BY name',
            one_column=True,
            hat_c=False
        ) or []

    def get_srv_nickname(self, abs_path: str) -> str:
        from project_cust_38 import Cust_client_socket as CCS
        from pathlib import Path
        all_servers = CCS.Servers._declared_attrs               # noqa
        for key, server in CCS.Servers._declared_attrs.items(): # noqa
            if isinstance(server, CCS._ServerItem) and Path(server.absolute_path).resolve() == Path(abs_path).resolve(): # noqa
                return str(server)




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
        if not db_path.startswith('SRV:'):
            print(f'[bootstrap_physical_table] принят абсолютный путь к бд {db_path}')
            db_path = self.get_srv_nickname(db_path)
            if db_path is None or not db_path:
                raise ValueError('Неверный формат ключа db-path ожидается "SRV:..."')
        if not self.table_exists_in_db(db_path, table_name):
            raise ValueError(f'Таблица {table_name!r} не найдена в БД {db_path!r}')
        db_key = db_key or resolve_db_key(db_path)
        table_key = table_key or make_table_key(db_key, table_name)
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
        logger.info(f'[ContextAdminRepo.bootstrap_physical_table] Регистрация таблицы {table_name} Статус: {is_success}')
        if include_fields:
            self.bootstrap_table_fields(db_path=db_path, table_name=table_name, table_key=table_key)
        return table_key

    def bootstrap_table_fields(self, *, db_path: str, table_name: str, table_key: str) -> int:
        rows = CSQ.custom_request_c(
            db_path,
            f'PRAGMA table_info("{table_name}")',
            hat_c=False
        )

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
                f'[ContextAdminRepo.bootstrap_table_fields] - [{table_name}] Регистрация поля {field_name} Статус: {is_success}')
            count += 1
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

    def get_physical_tables(self, *, schema_enabled: int | None = None, only_enabled: bool = False) -> list[dict[str, Any]]:
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
        admin_schema_hash = _sha256_text(_json_dumps({
            'physical_tables': physical_tables,
        }))
        table_fields_hash = _sha256_text(_json_dumps(table_fields))
        return {
            'admin_schema_hash': admin_schema_hash,
            'table_fields_hash': table_fields_hash,
        }

    def ensure_table_registered_for_invalidation(self, *, db_path: str, table_name: str) -> dict[str, str]:
        db_path = _normalize_path(db_path)
        db_key = resolve_db_key(db_path)
        table_key = make_table_key(db_key, table_name)
        existing = CPG.custom_request_pg(
            f"SELECT table_key FROM {ADMIN_TABLES['physical_tables']} WHERE table_key = {table_key!r}",
        )
        if not existing and db_path and self.table_exists_in_db(db_path, table_name):
            self.bootstrap_physical_table(
                db_path=db_path,
                table_name=table_name,
                db_key=db_key,
                table_key=table_key,
                include_fields=True,
                schema_enabled=0,
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

if __name__ == '__main__':
    from project_cust_38 import Cust_SQLite as CSQ
    from project_cust_38 import Cust_config as CFG
    b = ContextAdminRepo().get_srv_nickname('C://DB_srv//DB_kplan.db')
    print(b)
    b = CSQ.custom_request_c(CFG.Config.project.db_kplan, 'DELETE FROM gant_poz_val_by_day where val_minutes = 3333.6')
    a = CSQ.custom_request_c(CFG.Config.project.db_kplan, 'SELECT * FROM gant_poz_val_by_day where id_poz = 7131')
    print(a)
