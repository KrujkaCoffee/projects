from __future__ import annotations

import enum
import hashlib
import json
import logging
import re
import typing
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

try:
    from project_cust_38 import Cust_Functions as F  # noqa
except Exception:
    import Cust_Functions as F  # type: ignore

try:
    from project_cust_38 import Cust_SQLite as CSQ  # noqa
except Exception:
    import Cust_SQLite as CSQ  # type: ignore

try:
    from project_cust_38 import Cust_config as CFG  # noqa
except Exception:
    CFG = None  # type: ignore

try:
    from project_cust_38 import Cust_client_socket as CCS  # noqa
except Exception:
    CCS = None  # type: ignore

try:
    from project_cust_38.Cust_orm import SmartList
except Exception:
    try:
        from Cust_orm import SmartList  # type: ignore
    except Exception:
        class SmartList(list):
            pass

logger = logging.getLogger(__name__)


def _field_name_compat(value: Any) -> str:
    if value in (None, ''):
        return ''
    try:
        from project_cust_38.context_relations import field_name as _rel_field_name
        return _rel_field_name(value)
    except Exception:
        try:
            from context_relations import field_name as _rel_field_name  # type: ignore
            return _rel_field_name(value)
        except Exception:
            pass
    name = getattr(value, 'name', None) or getattr(value, 'db_column', None)
    if name:
        return str(name).strip()
    return str(value or '').strip()


def _field_list_compat(values: Iterable[Any] | None) -> tuple[str, ...]:
    return tuple(name for name in (_field_name_compat(item) for item in (values or ())) if name)


def _relation_module():
    try:
        from project_cust_38 import context_relations as REL  # type: ignore
        return REL
    except Exception:
        try:
            import context_relations as REL  # type: ignore
            return REL
        except Exception:
            return None


def _is_relation_spec(value: Any) -> bool:
    return hasattr(value, 'normalized') and hasattr(value, 'relation_key') and hasattr(value, 'field_pairs')


def _is_relation_ref(value: Any) -> bool:
    return hasattr(value, 'apply_to') and hasattr(value, 'name') and hasattr(value, 'fields')


def _relation_ref_to_jsonable(item: Any) -> Any:
    if item in (None, ''):
        return ''
    if isinstance(item, str):
        return item
    if isinstance(item, Mapping):
        payload = dict(item)
        if 'fields' in payload:
            payload['fields'] = list(_field_list_compat(payload.get('fields') or ()))
        if 'select_fields' in payload and 'fields' not in payload:
            payload['fields'] = list(_field_list_compat(payload.get('select_fields') or ()))
            payload.pop('select_fields', None)
        return payload
    if _is_relation_ref(item):
        return {
            'name': str(getattr(item, 'name', '') or ''),
            'fields': list(_field_list_compat(getattr(item, 'fields', ()) or ())),
            'prefix': str(getattr(item, 'prefix', '') or ''),
            'mode': str(getattr(item, 'mode', '') or ''),
            'required': bool(getattr(item, 'required', False)),
            'explode': bool(getattr(item, 'explode', False)),
        }
    if _is_relation_spec(item):
        try:
            spec = item.normalized()
            return {'name': spec.relation_key or spec.name or spec.relation_name}
        except Exception:
            return {'name': str(getattr(item, 'relation_key', '') or getattr(item, 'name', '') or '')}
    return str(item)


def _normalize_relation_ref(item: Any) -> Any:
    if item in (None, ''):
        return None
    REL = _relation_module()
    RelationRef = getattr(REL, 'RelationRef', None) if REL is not None else None
    RelationSpec = getattr(REL, 'RelationSpec', None) if REL is not None else None
    if RelationSpec is not None and isinstance(item, RelationSpec):
        return item.normalized()
    if RelationRef is not None and isinstance(item, RelationRef):
        return RelationRef(
            str(item.name),
            fields=tuple(_field_list_compat(getattr(item, 'fields', ()) or ())),
            prefix=str(getattr(item, 'prefix', '') or ''),
            mode=str(getattr(item, 'mode', '') or ''),
            required=bool(getattr(item, 'required', False)),
            explode=bool(getattr(item, 'explode', False)),
        )
    if isinstance(item, Mapping):
        name = item.get('name') or item.get('relation_key') or item.get('relation_name')
        if not name:
            return None
        fields = item.get('fields', item.get('select_fields', ())) or ()
        if RelationRef is not None:
            return RelationRef(
                str(name),
                fields=tuple(_field_list_compat(fields)),
                prefix=str(item.get('prefix', item.get('select_prefix', '')) or ''),
                mode=str(item.get('mode', item.get('select_mode', '')) or ''),
                required=bool(item.get('required', False)),
                explode=bool(item.get('explode', False)),
            )
        return str(name)
    return item if not isinstance(item, str) else str(item).strip()


def _relation_refs_compat(*groups: Iterable[Any] | None) -> tuple[Any, ...]:
    result: list[Any] = []
    for values in groups:
        for item in values or ():
            normalized = _normalize_relation_ref(item)
            if normalized in (None, ''):
                continue
            result.append(normalized)
    return tuple(result)


def _load_relation_refs(value: Any) -> tuple[Any, ...]:
    if value in (None, ''):
        return ()
    if isinstance(value, (list, tuple)):
        return _relation_refs_compat(value)
    try:
        data = json.loads(value)
    except Exception:
        return ()
    if isinstance(data, list):
        return _relation_refs_compat(data)
    return ()


def _relation_ref_name(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, Mapping):
        return str(item.get('name') or item.get('relation_key') or item.get('relation_name') or '')
    return str(getattr(item, 'relation_key', '') or getattr(item, 'name', '') or '')



def _model_ref_compat(value: Any) -> str:
    if value in (None, ''):
        return ''
    if isinstance(value, str):
        return value
    table_key = getattr(value, '__table_key__', '') or getattr(value, '__table__', '')
    if table_key:
        return str(table_key)
    name = getattr(value, '__name__', None)
    if name:
        return str(name)
    return str(value)


__all__ = [
    'REGISTER_ADMIN_TABLES',
    'StateField',
    'RegisterTypes',
    'RegisterSpec',
    'RegisterAdminRepo',
    'RegisterRuntime',
    'Registers',
    'EMPLOYEE_STATE_BY_EMPLOYEE',
    'DECLARED_REGISTER_SPECS',
    'get_registers',
]


REGISTER_ADMIN_TABLES = {
    'register_specs': 'admin_register_specs',
}


def _json_dumps(data: Any) -> str:
    return json.dumps(data if data is not None else {}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _question_mask(items: Sequence[Any]) -> str:
    return ', '.join('?' for _ in items)


def _quote_ident(value: str) -> str:
    text = str(value or '').replace('"', '""')
    return f'"{text}"'


def _split_select_sql(select_sql: str) -> list[str]:
    text = str(select_sql or '').strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r',\s*\n\s*', text) if part.strip()]


def _select_output_alias(select_part: str) -> str:
    match = re.search(r'\s+AS\s+"((?:""|[^"])*)"\s*$', str(select_part or ''), flags=re.I)
    if not match:
        return ''
    return match.group(1).replace('""', '"')


def _safe_alias(value: str, default: str) -> str:
    text = str(value or '').strip()
    if not text:
        return default
    text = re.sub(r'\W+', '_', text, flags=re.UNICODE).strip('_')
    if not text:
        return default
    if text[0].isdigit():
        text = '_' + text
    return text


def _server_str(server_name: str, default: str) -> str:
    try:
        if CCS is None:
            return default
        server = getattr(CCS.Servers, server_name)
        return str(server)
    except Exception:
        return default


def _db_alias(db_name: str | None) -> str:
    text = str(db_name or '').strip()
    if not text:
        return ''
    if text.startswith('SRV:'):
        return text.split('SRV:')[-1].split('\\')[0].split('/')[-1].split('.')[0]
    cleaned = text.replace('\\', '/').rstrip('/')
    return cleaned.split('/')[-1].split('.')[0]


def _resolve_db_files() -> str | None:
    try:
        return CFG.Config.project.db_files  # type: ignore[attr-defined]
    except Exception:
        try:
            return F.scfg('files')
        except Exception:
            return None


class _HumanEnum(enum.Enum):
    def __new__(cls, value: str, title: str, description: str, params_hint: str = ''):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.title = title
        obj.description = description
        obj.params_hint = params_hint
        return obj

    def to_dict(self) -> dict[str, str]:
        return {
            'code': self.value,
            'title': self.title,
            'description': self.description,
            'params_hint': self.params_hint,
        }

    @classmethod
    def rows(cls) -> list[dict[str, str]]:
        return [item.to_dict() for item in cls]


class RegisterTypes:
    class StorageKind(_HumanEnum):
        VIRTUAL = (
            'virtual',
            'Виртуальный',
            'Регистр не хранит собственные строки, а вычисляется на чтении через custom_request_c.',
            'Нужны source_db и source_sql/source_table/source_model.'
        )
        PG_MATERIALIZED = (
            'pg_materialized',
            'Материализованный в PostgreSQL',
            'Устаревший режим. Сохраняется только для совместимости старых записей и приводится к virtual.',
            'Новый runtime этот режим не использует.'
        )
        SQLITE_MATERIALIZED = (
            'sqlite_materialized',
            'Материализованный в SQLite',
            'Устаревший режим. Сохраняется только для совместимости старых записей и приводится к virtual.',
            'Новый runtime этот режим не использует.'
        )

        @classmethod
        def normalize(cls, value: str | None) -> str:
            if value in (None, '', cls.VIRTUAL.value, cls.VIRTUAL):
                return cls.VIRTUAL.value
            text = str(value)
            if text in (cls.PG_MATERIALIZED.value, cls.SQLITE_MATERIALIZED.value):
                return cls.VIRTUAL.value
            return cls.VIRTUAL.value

        @classmethod
        def active_rows(cls) -> list[dict[str, str]]:
            return [cls.VIRTUAL.to_dict()]

    class RegisterKind(_HumanEnum):
        STATE = (
            'state',
            'Регистр состояний',
            'Хранит последнее актуальное состояние сущности на дату: сотрудник, изделие, заказ, объект.',
            'Нужны entity_fields, period_field, state_fields, order_fields.'
        )
        ACCUMULATION = (
            'accumulation',
            'Регистр накоплений',
            'Хранит движения/обороты по сущности и периоду: остатки, приходы, расходы, суммы и количества.',
            'Нужны entity_fields, period_field и правила агрегации.'
        )

    class RefreshPolicy(_HumanEnum):
        MANUAL = (
            'manual',
            'Ручное обновление',
            'Регистр обновляется только по явному вызову из UI/сервиса.',
            'Подходит для редких или контролируемых пересборок.'
        )
        ON_READ = (
            'on_read',
            'Обновление при чтении',
            'Регистр пересчитывается во время чтения, если найдено устаревание.',
            'Подходит для виртуальных и легких регистров.'
        )
        ON_INVALIDATE = (
            'on_invalidate',
            'Обновление по инвалидации',
            'Регистр пересчитывается после изменения зависимых таблиц.',
            'Нужны dependency_table_keys и корректный invalidation hook.'
        )

    class SourceKind(_HumanEnum):
        MODEL = (
            'model',
            'Источник ORM-модель',
            'Данные для регистра берутся из ORM-модели или queryset.',
            'Нужен source_model.'
        )
        SQL = (
            'sql',
            'Источник SQL',
            'Данные для регистра берутся из SQL-запроса или таблицы через custom_request_c.',
            'Нужны source_db и source_sql/source_table.'
        )


class StateField(typing.NamedTuple):
    field_name: str
    db_name: str | None = None
    join_table: str | None = None
    field_for_join: str | None = None
    join_type: str = 'LEFT JOIN'
    join_mode: str = 'all'
    select_fields: tuple[str, ...] = ()
    select_prefix: str = ''
    join_alias: str = ''
    join_on_sql: str = ''


@dataclass(frozen=True)
class _SqlState:
    select: str = ''
    where: str = ''
    order_by: str = ''
    join: str = ''
    limit: int | str = ''
    attach_dbs: tuple[str, ...] = ()
    dependency_table_keys: tuple[str, ...] = ()



def _normalize_state_field(item: Any) -> str | StateField:
    if isinstance(item, StateField):
        return StateField(
            field_name=_field_name_compat(item.field_name),
            db_name=str(item.db_name or '').strip() or None,
            join_table=str(item.join_table or '').strip() or None,
            field_for_join=_field_name_compat(item.field_for_join) or None,
            join_type=str(item.join_type or 'LEFT JOIN').strip() or 'LEFT JOIN',
            join_mode=str(item.join_mode or 'all').strip() or 'all',
            select_fields=_field_list_compat(item.select_fields),
            select_prefix=str(item.select_prefix or '').strip(),
            join_alias=str(item.join_alias or '').strip(),
            join_on_sql=str(item.join_on_sql or '').strip(),
        )
    if isinstance(item, Mapping) and item.get('field_name'):
        return _normalize_state_field(StateField(**dict(item)))
    return _field_name_compat(item)



def _state_field_name(item: str | StateField | Any) -> str:
    if isinstance(item, StateField):
        return _field_name_compat(item.field_name)
    return _field_name_compat(item)



def _state_field_to_jsonable(item: str | StateField):
    if isinstance(item, StateField):
        payload = item._asdict()
        payload['select_fields'] = list(payload.get('select_fields') or ())
        return payload
    return _field_name_compat(item)



def _load_state_fields(value: Any) -> tuple[str | StateField, ...]:
    if value in (None, ''):
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(_normalize_state_field(item) for item in value)
    try:
        data = json.loads(value)
    except Exception:
        return ()
    if isinstance(data, list):
        return tuple(_normalize_state_field(item) for item in data)
    return ()


@dataclass(frozen=True)
class RegisterSpec:
    code: str
    title: str
    source_kind: str = RegisterTypes.SourceKind.SQL.value
    source_db: str | None = None
    source_table: str | None = None
    source_model: Any = None
    source_sql: str | None = None
    entity_fields: tuple[Any, ...] = ()
    period_field: Any = ''
    period_format: str = '%Y-%m-%d %H:%M:%S'
    state_fields: tuple[Any | StateField, ...] = ()
    order_fields: tuple[Any, ...] = ()
    relation_refs: tuple[Any, ...] = ()
    enrichments: tuple[Any, ...] = ()
    filters_sql: str = ''
    dependency_table_keys: tuple[str, ...] = ()
    register_kind: str = RegisterTypes.RegisterKind.STATE.value
    storage_kind: str = RegisterTypes.StorageKind.VIRTUAL.value
    refresh_policy: str = RegisterTypes.RefreshPolicy.ON_INVALIDATE.value
    enabled: int = 1
    notes: str = ''
    version: str = ''
    content_hash: str = ''
    updated_at: str = ''

    def normalized(self) -> 'RegisterSpec':
        content_hash = self.content_hash or self.compute_content_hash()
        version = self.version or content_hash[:12]
        updated_at = self.updated_at or F.now()
        return RegisterSpec(
            code=str(self.code or '').strip(),
            title=str(self.title or '').strip(),
            source_kind=str(self.source_kind or RegisterTypes.SourceKind.SQL.value),
            source_db=str(self.source_db or '').strip() or None,
            source_table=str(self.source_table or '').strip() or None,
            source_model=self.source_model,
            source_sql=self.source_sql,
            entity_fields=_field_list_compat(self.entity_fields),
            period_field=_field_name_compat(self.period_field),
            period_format=str(self.period_format or '%Y-%m-%d %H:%M:%S'),
            state_fields=tuple(_normalize_state_field(item) for item in (self.state_fields or ())),
            order_fields=_field_list_compat(self.order_fields),
            relation_refs=_relation_refs_compat(self.relation_refs, self.enrichments),
            enrichments=(),
            filters_sql=str(self.filters_sql or ''),
            dependency_table_keys=tuple(str(item) for item in (self.dependency_table_keys or ())),
            register_kind=str(self.register_kind or RegisterTypes.RegisterKind.STATE.value),
            storage_kind=RegisterTypes.StorageKind.normalize(self.storage_kind),
            refresh_policy=str(self.refresh_policy or RegisterTypes.RefreshPolicy.ON_INVALIDATE.value),
            enabled=1 if bool(self.enabled) else 0,
            notes=str(self.notes or ''),
            version=version,
            content_hash=content_hash,
            updated_at=updated_at,
        )

    def compute_content_hash(self) -> str:
        payload = {
            'code': self.code,
            'title': self.title,
            'source_kind': self.source_kind,
            'source_db': self.source_db,
            'source_table': self.source_table,
            'source_model': _model_ref_compat(self.source_model),
            'source_sql': self.source_sql,
            'entity_fields': list(_field_list_compat(self.entity_fields)),
            'period_field': _field_name_compat(self.period_field),
            'period_format': self.period_format,
            'state_fields': [_state_field_to_jsonable(item) for item in (self.state_fields or ())],
            'order_fields': list(_field_list_compat(self.order_fields)),
            'relation_refs': [_relation_ref_to_jsonable(item) for item in _relation_refs_compat(self.relation_refs, self.enrichments)],
            'filters_sql': self.filters_sql,
            'dependency_table_keys': list(self.dependency_table_keys or ()),
            'register_kind': self.register_kind,
            'storage_kind': RegisterTypes.StorageKind.normalize(self.storage_kind),
            'refresh_policy': self.refresh_policy,
            'enabled': int(bool(self.enabled)),
            'notes': self.notes,
        }
        return hashlib.sha256(_json_dumps(payload).encode('utf-8')).hexdigest()

    def to_record(self) -> dict[str, Any]:
        spec = self.normalized()
        return {
            'code': spec.code,
            'title': spec.title,
            'source_kind': spec.source_kind,
            'source_db': spec.source_db or '',
            'source_table': spec.source_table or '',
            'source_model': _model_ref_compat(spec.source_model),
            'source_sql': spec.source_sql or '',
            'entity_fields_json': json.dumps(list(spec.entity_fields), ensure_ascii=False),
            'period_field': spec.period_field,
            'period_format': spec.period_format,
            'state_fields_json': json.dumps([_state_field_to_jsonable(item) for item in spec.state_fields], ensure_ascii=False),
            'order_fields_json': json.dumps(list(spec.order_fields), ensure_ascii=False),
            'relation_refs_json': json.dumps([_relation_ref_to_jsonable(item) for item in spec.relation_refs], ensure_ascii=False),
            'filters_sql': spec.filters_sql,
            'dependency_table_keys_json': json.dumps(list(spec.dependency_table_keys), ensure_ascii=False),
            'register_kind': spec.register_kind,
            'storage_kind': spec.storage_kind,
            'refresh_policy': spec.refresh_policy,
            'enabled': spec.enabled,
            'notes': spec.notes,
            'version': spec.version,
            'content_hash': spec.content_hash,
            'updated_at': spec.updated_at,
        }

    def to_dict(self) -> dict[str, Any]:
        spec = self.normalized()
        return {
            'code': spec.code,
            'title': spec.title,
            'source_kind': spec.source_kind,
            'source_db': spec.source_db,
            'source_table': spec.source_table,
            'source_model': _model_ref_compat(spec.source_model),
            'source_sql': spec.source_sql,
            'entity_fields': list(spec.entity_fields),
            'period_field': spec.period_field,
            'period_format': spec.period_format,
            'state_fields': [_state_field_to_jsonable(item) for item in spec.state_fields],
            'order_fields': list(spec.order_fields),
            'relation_refs': [_relation_ref_to_jsonable(item) for item in spec.relation_refs],
            'filters_sql': spec.filters_sql,
            'dependency_table_keys': list(spec.dependency_table_keys),
            'register_kind': spec.register_kind,
            'storage_kind': spec.storage_kind,
            'refresh_policy': spec.refresh_policy,
            'enabled': spec.enabled,
            'notes': spec.notes,
            'version': spec.version,
            'content_hash': spec.content_hash,
            'updated_at': spec.updated_at,
        }

    @classmethod
    def from_record(cls, row: Mapping[str, Any]) -> 'RegisterSpec':
        def loads_list(value: Any) -> tuple[str, ...]:
            if value in (None, ''):
                return ()
            if isinstance(value, (list, tuple)):
                return tuple(str(item) for item in value)
            try:
                data = json.loads(value)
            except Exception:
                return ()
            if isinstance(data, list):
                return tuple(str(item) for item in data)
            return ()
        return RegisterSpec(
            code=str(row.get('code') or '').strip(),
            title=str(row.get('title') or '').strip(),
            source_kind=str(row.get('source_kind') or RegisterTypes.SourceKind.SQL.value),
            source_db=str(row.get('source_db') or '').strip() or None,
            source_table=str(row.get('source_table') or '').strip() or None,
            source_model=(row.get('source_model') or None),
            source_sql=(row.get('source_sql') or None),
            entity_fields=loads_list(row.get('entity_fields_json')),
            period_field=str(row.get('period_field') or ''),
            period_format=str(row.get('period_format') or '%Y-%m-%d %H:%M:%S'),
            state_fields=_load_state_fields(row.get('state_fields_json')),
            order_fields=loads_list(row.get('order_fields_json')),
            relation_refs=_load_relation_refs(row.get('relation_refs_json')),
            filters_sql=str(row.get('filters_sql') or ''),
            dependency_table_keys=loads_list(row.get('dependency_table_keys_json')),
            register_kind=str(row.get('register_kind') or RegisterTypes.RegisterKind.STATE.value),
            storage_kind=RegisterTypes.StorageKind.normalize(row.get('storage_kind')),
            refresh_policy=str(row.get('refresh_policy') or RegisterTypes.RefreshPolicy.ON_INVALIDATE.value),
            enabled=1 if bool(row.get('enabled', 1)) else 0,
            notes=str(row.get('notes') or ''),
            version=str(row.get('version') or ''),
            content_hash=str(row.get('content_hash') or ''),
            updated_at=str(row.get('updated_at') or ''),
        ).normalized()


class RegisterAdminRepo:
    def __init__(self, db: str | None = None, function_custom_request_c=None):
        self.db = db or _resolve_db_files()
        self.function_custom_request_c = function_custom_request_c or CSQ.custom_request_c
        if not self.db:
            raise RuntimeError('Не удалось определить БД для admin_register_specs')
        self.ensure_schema()

    def ensure_schema(self):
        ddl = f'''
        CREATE TABLE IF NOT EXISTS {REGISTER_ADMIN_TABLES['register_specs']}(
            code TEXT PRIMARY KEY,
            title TEXT DEFAULT '',
            source_kind TEXT DEFAULT '{RegisterTypes.SourceKind.SQL.value}',
            source_db TEXT DEFAULT '',
            source_table TEXT DEFAULT '',
            source_model TEXT DEFAULT '',
            source_sql TEXT DEFAULT '',
            entity_fields_json TEXT DEFAULT '[]',
            period_field TEXT DEFAULT '',
            period_format TEXT DEFAULT '%Y-%m-%d %H:%M:%S',
            state_fields_json TEXT DEFAULT '[]',
            order_fields_json TEXT DEFAULT '[]',
            relation_refs_json TEXT DEFAULT '[]',
            filters_sql TEXT DEFAULT '',
            dependency_table_keys_json TEXT DEFAULT '[]',
            register_kind TEXT DEFAULT '{RegisterTypes.RegisterKind.STATE.value}',
            storage_kind TEXT DEFAULT '{RegisterTypes.StorageKind.VIRTUAL.value}',
            refresh_policy TEXT DEFAULT '{RegisterTypes.RefreshPolicy.ON_INVALIDATE.value}',
            enabled INTEGER NOT NULL DEFAULT 1,
            notes TEXT DEFAULT '',
            version TEXT DEFAULT '',
            content_hash TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        );
        '''
        result = self.function_custom_request_c(self.db, ddl)
        self._ensure_schema_columns()
        return result

    def _ensure_schema_columns(self):
        table_name = REGISTER_ADMIN_TABLES['register_specs']
        rows = self.function_custom_request_c(self.db, f'PRAGMA table_info({table_name})', rez_dict=True) or []
        existing = {str(row.get('name')) for row in rows if isinstance(row, Mapping)}
        if 'relation_refs_json' not in existing:
            self.function_custom_request_c(self.db, f"ALTER TABLE {table_name} ADD COLUMN relation_refs_json TEXT DEFAULT '[]'")

    def _upsert(self, table_name: str, record: Mapping[str, Any], conflict_cols: Sequence[str], update_cols: Sequence[str] | None = None):
        cols = list(record.keys())
        if not cols:
            return False
        if update_cols is None:
            update_cols = [col for col in cols if col not in set(conflict_cols)]
        update_cols = [col for col in update_cols if col not in set(conflict_cols)]
        placeholders = _question_mask(cols)
        if update_cols:
            update_sql = ', '.join(f'{col}=excluded.{col}' for col in update_cols)
            sql = f'INSERT INTO {table_name} ({", ".join(cols)}) VALUES ({placeholders}) ON CONFLICT({", ".join(conflict_cols)}) DO UPDATE SET {update_sql};'
        else:
            sql = f'INSERT INTO {table_name} ({", ".join(cols)}) VALUES ({placeholders}) ON CONFLICT({", ".join(conflict_cols)}) DO NOTHING;'
        values = [record[col] for col in cols]
        return bool(self.function_custom_request_c(self.db, sql, list_of_lists_c=[values]))

    def upsert_spec(self, spec: RegisterSpec) -> bool:
        return bool(self._upsert(REGISTER_ADMIN_TABLES['register_specs'], spec.to_record(), ['code']))

    def upsert_specs(self, specs: Iterable[RegisterSpec]) -> dict[str, Any]:
        codes = []
        count = 0
        for spec in specs or ():
            normalized = spec.normalized()
            if self.upsert_spec(normalized):
                count += 1
                codes.append(normalized.code)
        return {'ok': True, 'count': count, 'codes': codes}

    def get_spec(self, code: str) -> RegisterSpec | None:
        row = self.function_custom_request_c(
            self.db,
            f"SELECT * FROM {REGISTER_ADMIN_TABLES['register_specs']} WHERE code = {code!r} LIMIT 1",
            rez_dict=True,
            one=True,
        )
        if not row:
            return None
        return RegisterSpec.from_record(row)

    def list_specs(self, enabled: int | None = None) -> list[RegisterSpec]:
        where = ''
        if enabled is not None:
            where = f' WHERE enabled = {1 if bool(enabled) else 0}'
        rows = self.function_custom_request_c(
            self.db,
            f"SELECT * FROM {REGISTER_ADMIN_TABLES['register_specs']}{where} ORDER BY code",
            rez_dict=True,
        ) or []
        return [RegisterSpec.from_record(row) for row in rows]


class RegisterRuntime:
    @staticmethod
    def convert_to_dt(value: Any, dt_format: str = '%Y-%m-%d %H:%M:%S'):
        if value in (None, ''):
            return None
        try:
            if F.is_date(value, maska=dt_format):
                return F.strtodate(value, format=dt_format)
        except Exception:
            pass
        try:
            return F.strtodate(value)
        except Exception:
            pass
        try:
            import datetime as _dt
            return _dt.datetime.fromisoformat(str(value).replace(' ', 'T'))
        except Exception:
            return None

    @classmethod
    def resolve(cls, spec: RegisterSpec, rows: Iterable[Mapping[str, Any]], *, as_of: Any = None) -> list[dict[str, Any]]:
        spec = spec.normalized()
        if spec.register_kind == RegisterTypes.RegisterKind.STATE.value:
            return cls.resolve_state(spec, rows, as_of=as_of)
        return cls.resolve_accumulation(spec, rows, as_of=as_of)

    @classmethod
    def resolve_state(cls, spec: RegisterSpec, rows: Iterable[Mapping[str, Any]], *, as_of: Any = None) -> list[dict[str, Any]]:
        if not spec.entity_fields:
            raise ValueError('Для state-регистра требуется entity_fields')
        if not spec.period_field:
            raise ValueError('Для state-регистра требуется period_field')

        as_of_dt = cls.convert_to_dt(as_of, dt_format=spec.period_format)
        latest_by_entity: dict[tuple[Any, ...], Mapping[str, Any]] = {}
        latest_sort_key: dict[tuple[Any, ...], tuple[Any, ...]] = {}

        def sort_token(row: Mapping[str, Any], field_name: str):
            value = row.get(field_name)
            dt_val = cls.convert_to_dt(value, dt_format=spec.period_format)
            return dt_val if dt_val is not None else value

        order_fields = tuple(spec.order_fields or ())
        state_field_names = tuple(_state_field_name(item) for item in spec.state_fields)
        for row in rows or ():
            if not isinstance(row, Mapping):
                continue
            entity_key = tuple(row.get(field_name) for field_name in spec.entity_fields)
            period_value = row.get(spec.period_field)
            period_dt = cls.convert_to_dt(period_value, dt_format=spec.period_format)
            if as_of_dt is not None and period_dt is not None and period_dt > as_of_dt:
                continue
            sort_key = tuple(sort_token(row, field_name) for field_name in (spec.period_field, *order_fields))
            prev_sort_key = latest_sort_key.get(entity_key)
            if prev_sort_key is None or sort_key >= prev_sort_key:
                latest_by_entity[entity_key] = row
                latest_sort_key[entity_key] = sort_key

        result: list[dict[str, Any]] = []
        for entity_key, row in latest_by_entity.items():
            payload = {field_name: row.get(field_name) for field_name in spec.entity_fields}
            payload[spec.period_field] = row.get(spec.period_field)
            for field_name in state_field_names:
                payload[field_name] = row.get(field_name)
            for state_field in spec.state_fields:
                if not isinstance(state_field, StateField):
                    continue
                prefix = state_field.select_prefix or state_field.join_table or ''
                join_mode = str(state_field.join_mode or 'all').lower()
                if not prefix or join_mode == 'none':
                    continue
                if join_mode == 'all':
                    for key, value in row.items():
                        if not str(key).startswith(f'{prefix}.'):
                            continue
                        payload[key] = value
                elif join_mode == 'only':
                    for field in state_field.select_fields:
                        payload[f'{prefix}.{field}'] = row.get(f'{prefix}.{field}')
            # Relation-stage enrichment fields are intentionally copied after
            # core state fields. They are normally emitted as "Prefix.Field"
            # or "Prefix[]" by context_relations.SQLRelationCompiler /
            # EnrichmentStage. This keeps RegisterRuntime independent from
            # concrete relation registries while preserving enriched output.
            core_keys = set(spec.entity_fields) | {spec.period_field} | set(state_field_names)
            for key, value in row.items():
                text_key = str(key)
                if key in core_keys or text_key.startswith('_'):
                    continue
                if '.' in text_key or text_key.endswith('[]'):
                    payload[key] = value
            payload['_register_code'] = spec.code
            payload['_register_kind'] = spec.register_kind
            payload['_storage_kind'] = spec.storage_kind
            result.append(payload)
        return result

    @classmethod
    def resolve_accumulation(cls, spec: RegisterSpec, rows: Iterable[Mapping[str, Any]], *, as_of: Any = None) -> list[dict[str, Any]]:
        result = []
        as_of_dt = cls.convert_to_dt(as_of, dt_format=spec.period_format)
        for row in rows or ():
            if not isinstance(row, Mapping):
                continue
            if as_of_dt is not None and spec.period_field:
                period_dt = cls.convert_to_dt(row.get(spec.period_field), dt_format=spec.period_format)
                if period_dt is not None and period_dt > as_of_dt:
                    continue
            result.append(dict(row))
        return result


class Registers:
    def __init__(self, repo: RegisterAdminRepo | None = None, fetch_rows=None,
                 declared_specs: Sequence[RegisterSpec] | None = None, auto_sync: bool = False,
                 relation_registry: Any = None, relation_right_data: Mapping[str, Iterable[Any]] | None = None,
                 relation_loader=None, enrich_rows: bool = True):
        self.fetch_rows = fetch_rows
        self.relation_registry = relation_registry
        self.relation_right_data = relation_right_data or {}
        self.relation_loader = relation_loader
        self.enrich_rows = enrich_rows
        self._declared_specs: OrderedDict[str, RegisterSpec] = OrderedDict()
        self.repo = repo
        if self.repo is None:
            try:
                self.repo = RegisterAdminRepo()
            except Exception:
                self.repo = None
        for spec in tuple(declared_specs or ()):
            self.register(spec, sync=False)
        if auto_sync and self.repo is not None and self._declared_specs:
            self.sync_declared_specs()

    def register(self, spec: RegisterSpec, *, sync: bool = False) -> RegisterSpec:
        normalized = self._with_relation_dependencies(spec.normalized())
        self._declared_specs[normalized.code] = normalized
        if sync and self.repo is not None:
            self.repo.upsert_spec(normalized)
        return normalized

    def _with_relation_dependencies(self, spec: RegisterSpec) -> RegisterSpec:
        deps = list(spec.dependency_table_keys or ())
        if not spec.relation_refs:
            return spec
        for ref_item in spec.relation_refs:
            dep = ''
            try:
                if _is_relation_spec(ref_item):
                    dep = ref_item.normalized().dependency_key
                elif self.relation_registry is not None:
                    dep = self.relation_registry.resolve(ref_item).dependency_key
            except Exception:
                dep = ''
            if dep and dep not in deps:
                deps.append(dep)
        if tuple(deps) == tuple(spec.dependency_table_keys or ()):  # no changes
            return spec
        return replace(spec, dependency_table_keys=tuple(deps), content_hash='', version='').normalized()

    def sync_declared_specs(self) -> dict[str, Any]:
        if self.repo is None:
            return {'ok': False, 'reason': 'register_repo_unavailable', 'count': 0, 'codes': []}
        return self.repo.upsert_specs(self._declared_specs.values())

    def declared_specs(self) -> list[RegisterSpec]:
        return list(self._declared_specs.values())

    def get_spec(self, code: str, *, prefer_db: bool = True) -> RegisterSpec:
        if prefer_db and self.repo is not None:
            spec = self.repo.get_spec(code)
            if spec is not None:
                return spec
        spec = self._declared_specs.get(code)
        if spec is not None:
            return spec
        raise ValueError(f'Регистр {code!r} не найден')

    def list_specs(self, *, prefer_db: bool = True, enabled: bool | None = 1, merge_declared: bool = True) -> list[RegisterSpec]:
        result: OrderedDict[str, RegisterSpec] = OrderedDict()
        if prefer_db and self.repo is not None:
            normalized_enabled = None if enabled is None else (1 if enabled else 0)
            for spec in self.repo.list_specs(enabled=normalized_enabled):
                result[spec.code] = spec
        if merge_declared:
            for spec in self._declared_specs.values():
                if enabled is not None and bool(spec.enabled) != bool(enabled):
                    continue
                result.setdefault(spec.code, spec)
        return list(result.values())

    def _table_field_names(self, db_name: str | None, table_name: str | None) -> list[str]:
        if not db_name or not table_name:
            return []
        rows = CSQ.custom_request_c(
            db_name,
            f'PRAGMA table_info({_quote_ident(table_name)})',
            rez_dict=True,
        ) or []
        result = []
        for row in rows:
            field_name = row.get('name') if isinstance(row, Mapping) else None
            if field_name:
                result.append(str(field_name))
        if result:
            return result
        try:
            info_rows = CSQ.custom_request_c(
                db_name,
                f"SELECT column_name FROM information_schema.columns WHERE table_name = {table_name!r} ORDER BY ordinal_position",
                rez_dict=True,
            ) or []
        except Exception:
            info_rows = []
        for row in info_rows:
            field_name = row.get('column_name') if isinstance(row, Mapping) else None
            if field_name:
                result.append(str(field_name))
        return result

    def make_sql_by_spec(self, spec: RegisterSpec) -> _SqlState | None:
        spec = spec.normalized()
        if not spec.source_db:
            return None
        if not spec.source_table and not spec.source_sql:
            return None
        sql_state = _SqlState()
        attach_dbs = []
        join_parts = []
        select_parts = []
        output_names = set()
        src_alias = 'src'
        source_model = spec.source_model if not isinstance(spec.source_model, str) else None

        def add_select(expression: str, output_name: str):
            if output_name in output_names:
                return
            output_names.add(output_name)
            select_parts.append(f'{expression} AS {_quote_ident(output_name)}')

        def source_ref(field_name: Any) -> tuple[str, str]:
            name = _field_name_compat(field_name)
            if source_model is not None:
                REL = _relation_module()
                resolver = getattr(REL, 'resolve_field_ref', None) if REL is not None else None
                if resolver is not None:
                    try:
                        ref = resolver(name, model=source_model)
                        return str(getattr(ref, 'field_name', name) or name), str(getattr(ref, 'db_column', name) or name)
                    except Exception:
                        pass
            return name, name

        def add_source_field(field_name: Any):
            out_name, db_column = source_ref(field_name)
            if out_name:
                add_select(f'{src_alias}.{_quote_ident(db_column)}', out_name)

        for field_name in spec.entity_fields:
            add_source_field(field_name)
        if spec.period_field:
            add_source_field(spec.period_field)
        for field_name in spec.order_fields:
            add_source_field(field_name)

        for state_field in spec.state_fields:
            field_name = _state_field_name(state_field)
            if field_name:
                add_source_field(field_name)
            if not isinstance(state_field, StateField):
                continue
            if not state_field.join_table:
                continue
            if not state_field.field_for_join and not state_field.join_on_sql:
                continue
            join_mode = str(state_field.join_mode or 'all').strip().lower()
            if join_mode not in ('all', 'only', 'none'):
                join_mode = 'all'
            join_db = state_field.db_name or spec.source_db
            join_alias = _safe_alias(state_field.join_alias, f'j{len(join_parts) + 1}')
            db_alias = _db_alias(join_db)
            join_table_ref = _quote_ident(state_field.join_table)
            if join_db and spec.source_db and str(join_db) != str(spec.source_db):
                if join_db not in attach_dbs:
                    attach_dbs.append(join_db)
                if db_alias:
                    join_table_ref = f'{db_alias}.{_quote_ident(state_field.join_table)}'
            join_type = str(state_field.join_type or 'LEFT JOIN').strip().upper()
            if join_type not in ('LEFT JOIN', 'INNER JOIN', 'RIGHT JOIN', 'FULL JOIN', 'FULL OUTER JOIN'):
                join_type = 'LEFT JOIN'
            if state_field.join_on_sql:
                on_sql = state_field.join_on_sql
            else:
                _, src_join_column = source_ref(state_field.field_name)
                on_sql = f'{join_alias}.{_quote_ident(state_field.field_for_join)} = {src_alias}.{_quote_ident(src_join_column)}'
            join_parts.append(f'{join_type} {join_table_ref} AS {join_alias} ON {on_sql}')
            if join_mode == 'none':
                continue
            prefix = state_field.select_prefix or state_field.join_table or join_alias
            if join_mode == 'only':
                if not state_field.select_fields:
                    raise ValueError(f'Для StateField({state_field.field_name!r}) join_mode="only" требует select_fields')
                for select_field in state_field.select_fields:
                    add_select(f'{join_alias}.{_quote_ident(select_field)}', f'{prefix}.{select_field}')
                continue
            for join_field in self._table_field_names(join_db, state_field.join_table):
                add_select(f'{join_alias}.{_quote_ident(join_field)}', f'{prefix}.{join_field}')

        if spec.relation_refs:
            relation_plan = self._make_relation_sql_plan(spec)
            if relation_plan is not None:
                for part in _split_select_sql(relation_plan.select_sql):
                    alias = _select_output_alias(part)
                    if alias and alias in output_names:
                        continue
                    if alias:
                        output_names.add(alias)
                    if part:
                        select_parts.append(part)
                if relation_plan.join_sql:
                    join_parts.extend(line for line in relation_plan.join_sql.splitlines() if line.strip())
                for db_path in relation_plan.attach_dbs:
                    if db_path not in attach_dbs:
                        attach_dbs.append(db_path)
                dependency_keys = tuple(getattr(relation_plan, 'dependency_table_keys', ()) or ())
            else:
                dependency_keys = ()
        else:
            dependency_keys = ()

        if not select_parts:
            select_parts.append(f'{src_alias}.*')
        return _SqlState(
            select=',\n                    '.join(select_parts),
            join='\n                '.join(join_parts),
            attach_dbs=tuple(attach_dbs),
            dependency_table_keys=dependency_keys,
        )

    def _make_relation_sql_plan(self, spec: RegisterSpec):
        REL = _relation_module()
        if REL is None:
            return None
        compiler_cls = getattr(REL, 'SQLRelationCompiler', None)
        if compiler_cls is None:
            return None
        compiler = compiler_cls(self.relation_registry)
        source_fields = []
        for field_name in (*spec.entity_fields, spec.period_field, *(_state_field_name(item) for item in spec.state_fields), *spec.order_fields):
            if field_name and field_name not in source_fields:
                source_fields.append(field_name)
        source_model = spec.source_model if not isinstance(spec.source_model, str) else None
        source_table = spec.source_table or source_model
        if not source_table and not spec.source_sql:
            return None
        return compiler.compile_select(
            source_table=source_table,
            source_model=source_model,
            source_sql=spec.source_sql,
            source_db=spec.source_db,
            source_fields=tuple(source_fields),
            relations=spec.relation_refs,
            source_alias='src',
            where_sql='',
        )

    def _apply_relation_stage(self, spec: RegisterSpec, rows: Iterable[Any]) -> list[dict[str, Any]]:
        spec = spec.normalized()
        if not spec.relation_refs or not self.enrich_rows:
            return list(rows or ())
        if not self.relation_right_data and self.relation_loader is None:
            return list(rows or ())
        REL = _relation_module()
        if REL is None:
            return list(rows or ())
        stage_cls = getattr(REL, 'EnrichmentStage', None)
        stage_spec_cls = getattr(REL, 'RegisterStageSpec', None)
        if stage_cls is None or stage_spec_cls is None:
            return list(rows or ())
        stage = stage_cls(self.relation_registry)
        stage_spec = stage_spec_cls(code=spec.code, relation_refs=spec.relation_refs, dependency_table_keys=spec.dependency_table_keys)
        return stage.apply(rows, stage_spec, right_data=self.relation_right_data, loader=self.relation_loader)

    def _fetch_rows_default(self, spec: RegisterSpec) -> list[dict[str, Any]]:
        spec = spec.normalized()
        if not spec.source_db:
            raise ValueError(f'Для регистра {spec.code!r} не задан source_db')
        if spec.source_kind == RegisterTypes.SourceKind.MODEL.value:
            raise ValueError(f'Для регистра {spec.code!r} требуется внешний fetch_rows для source_model')
        sql_state = self.make_sql_by_spec(spec)
        if spec.source_sql:
            source_sql = str(spec.source_sql).strip().rstrip(';')
            _from = f'({source_sql}) AS src'
        elif spec.source_table:
            _from = f'{_quote_ident(spec.source_table)} AS src'
        else:
            raise ValueError(f'Для регистра {spec.code!r} не задан source_sql/source_table')
        _select = sql_state.select if sql_state is not None and sql_state.select else 'src.*'
        _join = sql_state.join if sql_state is not None and sql_state.join else ''
        _where = f' WHERE {spec.filters_sql}' if spec.filters_sql else ''
        query = f'''
                SELECT
                    {_select}
                FROM {_from}
                {_join}
                {_where}
            '''
        attach_dbs = sql_state.attach_dbs if sql_state is not None else ()
        return CSQ.custom_request_c(spec.source_db, query, rez_dict=True, attach_dbs=attach_dbs) or []

    def _ensure_rows(self, spec: RegisterSpec, rows=None):
        spec = spec.normalized()
        if rows is not None:
            return self._apply_relation_stage(spec, rows)
        if callable(self.fetch_rows):
            return self._apply_relation_stage(spec, self.fetch_rows(spec))
        # Default SQL fetch compiles relation_refs directly into SELECT/JOIN, so
        # applying EnrichmentStage again would duplicate work or require right_data.
        return self._fetch_rows_default(spec)

    def _entity_filter(self, spec: RegisterSpec, *, entity_key: Any = None, entity_map: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if entity_map:
            return {field_name: entity_map.get(field_name) for field_name in spec.entity_fields if field_name in entity_map}
        if entity_key is None:
            return {}
        if len(spec.entity_fields) == 1:
            return {spec.entity_fields[0]: entity_key}
        if isinstance(entity_key, Mapping):
            return {field_name: entity_key.get(field_name) for field_name in spec.entity_fields if field_name in entity_key}
        if isinstance(entity_key, (list, tuple)):
            return {field_name: entity_key[idx] for idx, field_name in enumerate(spec.entity_fields) if idx < len(entity_key)}
        return {}

    def _filter_rows_by_entity(self, rows, entity_filter: Mapping[str, Any]):
        if not entity_filter:
            return list(rows or ())
        result = []
        for row in rows or ():
            if not isinstance(row, Mapping):
                continue
            if all(row.get(field_name) == expected for field_name, expected in entity_filter.items()):
                result.append(row)
        return result

    def check_date(self, target_date, target_date_format: str = '%Y-%m-%d %H:%M:%S'):
        if target_date in (None, ''):
            return None
        return RegisterRuntime.convert_to_dt(target_date, dt_format=target_date_format)

    def state_at(self, spec: RegisterSpec | str, *, entity_key: Any = None, entity_map: Mapping[str, Any] | None = None,
                 as_of: Any = None, rows=None, prefer_db: bool = True):
        if isinstance(spec, str):
            spec = self.get_spec(spec, prefer_db=prefer_db)
        if spec is None:
            logger.warning('[state_at] Не удалось определить спецификацию регистра')
            return None
        source_rows = self._ensure_rows(spec, rows)
        filtered_rows = self._filter_rows_by_entity(source_rows, self._entity_filter(spec, entity_key=entity_key, entity_map=entity_map))
        resolved = RegisterRuntime.resolve(spec, filtered_rows, as_of=as_of)
        if entity_key is not None or entity_map:
            return resolved[0] if resolved else None
        return SmartList(resolved)

    def history(self, spec: RegisterSpec | str, *, entity_key: Any = None, entity_map: Mapping[str, Any] | None = None,
                date_from: Any = None, date_to: Any = None, rows=None, prefer_db: bool = True) -> SmartList:
        if isinstance(spec, str):
            spec = self.get_spec(spec, prefer_db=prefer_db)
        source_rows = self._ensure_rows(spec, rows)
        filtered_rows = self._filter_rows_by_entity(source_rows, self._entity_filter(spec, entity_key=entity_key, entity_map=entity_map))
        dt_from = RegisterRuntime.convert_to_dt(date_from, dt_format=spec.period_format)
        dt_to = RegisterRuntime.convert_to_dt(date_to, dt_format=spec.period_format)
        result = []
        for row in filtered_rows:
            period_dt = RegisterRuntime.convert_to_dt(row.get(spec.period_field), dt_format=spec.period_format) if spec.period_field else None
            if dt_from is not None and period_dt is not None and period_dt < dt_from:
                continue
            if dt_to is not None and period_dt is not None and period_dt > dt_to:
                continue
            result.append(dict(row))
        if spec.period_field:
            result.sort(key=lambda item: (RegisterRuntime.convert_to_dt(item.get(spec.period_field), dt_format=spec.period_format) or item.get(spec.period_field), *[item.get(field_name) for field_name in spec.order_fields]))
        return SmartList(result)

    def distinct_values_at(self, code: str, *, field: str, as_of: Any = None, rows=None,
                           entity_key: Any = None, entity_map: Mapping[str, Any] | None = None,
                           with_count: bool = False, prefer_db: bool = True) -> SmartList:
        resolved_rows = self.state_at(code, entity_key=entity_key, entity_map=entity_map, as_of=as_of, rows=rows, prefer_db=prefer_db)
        if isinstance(resolved_rows, dict):
            resolved_rows = [resolved_rows]
        counts: OrderedDict[Any, int] = OrderedDict()
        for row in resolved_rows or ():
            if not isinstance(row, Mapping):
                continue
            value = row.get(field)
            counts[value] = counts.get(value, 0) + 1
        if with_count:
            return SmartList([{field: key, 'count': count} for key, count in counts.items()])
        return SmartList([{field: key} for key in counts.keys()])


EMPLOYEE_STATE_BY_EMPLOYEE = RegisterSpec(
    code='СостояниеСотрудникаНаПериод',
    title='Кадровое состояние сотрудника',
    source_kind=RegisterTypes.SourceKind.SQL.value,
    source_db=_server_str('db_users', 'SRV:BD_users.db'),
    source_table='КадроваяИстория',
    entity_fields=('ФизическоеЛицо_Key',),
    period_field='Период',
    period_format='%Y-%m-%dT%H:%M:%S',
    state_fields=(
        StateField(field_name='Событие'),
        StateField(field_name='Должность_Key', db_name=_server_str('db_users', 'SRV:BD_users.db'), join_table='Должности', field_for_join='Ref_Key'),
        StateField(field_name='Подразделение_Key', db_name=_server_str('db_users', 'SRV:BD_users.db'), join_table='Подразделения', field_for_join='Подразделение_Key'),
        StateField(field_name='Организация_Key', db_name=_server_str('db_naryad', 'SRV:Naryad.db'), join_table='places', field_for_join='Организация_Key', join_mode='only', select_fields=('Имя',), select_prefix='Организация'),
        StateField(field_name='ФизическоеЛицо_Key', db_name=_server_str('db_users', 'SRV:BD_users.db'), join_table='ФизическиеЛица', field_for_join='ФизическоеЛицо_Key', join_mode='only', select_fields=('Наименование',), select_prefix='ФизическоеЛицо'),
    ),
    order_fields=('Период',),
    dependency_table_keys=('BD_users.КадроваяИстория',),
    register_kind=RegisterTypes.RegisterKind.STATE.value,
    storage_kind=RegisterTypes.StorageKind.VIRTUAL.value,
    refresh_policy=RegisterTypes.RefreshPolicy.ON_INVALIDATE.value,
    notes='Текущее кадровое состояние по ключу сотрудника.',
)


DECLARED_REGISTER_SPECS: tuple[RegisterSpec, ...] = (
    EMPLOYEE_STATE_BY_EMPLOYEE,
)


_REGISTERS_SINGLETON: Registers | None = None


def get_registers(*, reset: bool = False, fetch_rows=None, declared_specs: Sequence[RegisterSpec] | None = None,
                  repo: RegisterAdminRepo | None = None, auto_sync: bool = False, relation_registry: Any = None,
                  relation_right_data: Mapping[str, Iterable[Any]] | None = None, relation_loader=None,
                  enrich_rows: bool = True) -> Registers:
    global _REGISTERS_SINGLETON
    if (reset or _REGISTERS_SINGLETON is None or fetch_rows is not None or declared_specs is not None or
            repo is not None or relation_registry is not None or relation_right_data is not None or relation_loader is not None):
        specs = tuple(declared_specs or DECLARED_REGISTER_SPECS)
        _REGISTERS_SINGLETON = Registers(
            repo=repo,
            fetch_rows=fetch_rows,
            declared_specs=specs,
            auto_sync=auto_sync,
            relation_registry=relation_registry,
            relation_right_data=relation_right_data,
            relation_loader=relation_loader,
            enrich_rows=enrich_rows,
        )
    return _REGISTERS_SINGLETON
