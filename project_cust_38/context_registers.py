from __future__ import annotations

import enum
import hashlib
import json
import logging
import re
import typing
from collections import OrderedDict
from dataclasses import dataclass
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


__all__ = [
    'REGISTER_ADMIN_TABLES',
    'StateField',
    'RegisterTypes',
    'RegisterSpec',
    'RegisterAdminRepo',
    'RegisterRuntime',
    'Registers',
    'EMPLOYEE_STATE_BY_EMPLOYEE',
    'REGISTERS',
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



def _normalize_state_field(item: Any) -> str | StateField:
    if isinstance(item, StateField):
        return StateField(
            field_name=str(item.field_name or '').strip(),
            db_name=str(item.db_name or '').strip() or None,
            join_table=str(item.join_table or '').strip() or None,
            field_for_join=str(item.field_for_join or '').strip() or None,
            join_type=str(item.join_type or 'LEFT JOIN').strip() or 'LEFT JOIN',
            join_mode=str(item.join_mode or 'all').strip() or 'all',
            select_fields=tuple(str(field) for field in (item.select_fields or ())),
            select_prefix=str(item.select_prefix or '').strip(),
            join_alias=str(item.join_alias or '').strip(),
            join_on_sql=str(item.join_on_sql or '').strip(),
        )
    if isinstance(item, Mapping) and item.get('field_name'):
        return _normalize_state_field(StateField(**dict(item)))
    return str(item or '').strip()



def _state_field_name(item: str | StateField) -> str:
    if isinstance(item, StateField):
        return item.field_name
    return str(item)



def _state_field_to_jsonable(item: str | StateField):
    if isinstance(item, StateField):
        payload = item._asdict()
        payload['select_fields'] = list(payload.get('select_fields') or ())
        return payload
    return str(item)



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
    source_model: str | None = None
    source_sql: str | None = None
    entity_fields: tuple[str, ...] = ()
    period_field: str = ''
    period_format: str = '%Y-%m-%d %H:%M:%S'
    state_fields: tuple[str | StateField, ...] = ()
    order_fields: tuple[str, ...] = ()
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
            entity_fields=tuple(str(item) for item in (self.entity_fields or ())),
            period_field=str(self.period_field or '').strip(),
            period_format=str(self.period_format or '%Y-%m-%d %H:%M:%S'),
            state_fields=tuple(_normalize_state_field(item) for item in (self.state_fields or ())),
            order_fields=tuple(str(item) for item in (self.order_fields or ())),
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
            'source_model': self.source_model,
            'source_sql': self.source_sql,
            'entity_fields': list(self.entity_fields or ()),
            'period_field': self.period_field,
            'period_format': self.period_format,
            'state_fields': [_state_field_to_jsonable(item) for item in (self.state_fields or ())],
            'order_fields': list(self.order_fields or ()),
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
            'source_model': spec.source_model or '',
            'source_sql': spec.source_sql or '',
            'entity_fields_json': json.dumps(list(spec.entity_fields), ensure_ascii=False),
            'period_field': spec.period_field,
            'period_format': spec.period_format,
            'state_fields_json': json.dumps([_state_field_to_jsonable(item) for item in spec.state_fields], ensure_ascii=False),
            'order_fields_json': json.dumps(list(spec.order_fields), ensure_ascii=False),
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
            'source_model': spec.source_model,
            'source_sql': spec.source_sql,
            'entity_fields': list(spec.entity_fields),
            'period_field': spec.period_field,
            'period_format': spec.period_format,
            'state_fields': [_state_field_to_jsonable(item) for item in spec.state_fields],
            'order_fields': list(spec.order_fields),
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
        return self.function_custom_request_c(self.db, ddl)

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
                 declared_specs: Sequence[RegisterSpec] | None = None, auto_sync: bool = False):
        self.fetch_rows = fetch_rows
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
        normalized = spec.normalized()
        self._declared_specs[normalized.code] = normalized
        if sync and self.repo is not None:
            self.repo.upsert_spec(normalized)
        return normalized

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

        def add_select(expression: str, output_name: str):
            if output_name in output_names:
                return
            output_names.add(output_name)
            select_parts.append(f'{expression} AS {_quote_ident(output_name)}')

        for field_name in spec.entity_fields:
            add_select(f'{src_alias}.{_quote_ident(field_name)}', field_name)
        if spec.period_field:
            add_select(f'{src_alias}.{_quote_ident(spec.period_field)}', spec.period_field)

        for state_field in spec.state_fields:
            field_name = _state_field_name(state_field)
            if field_name:
                add_select(f'{src_alias}.{_quote_ident(field_name)}', field_name)
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
                on_sql = f'{join_alias}.{_quote_ident(state_field.field_for_join)} = {src_alias}.{_quote_ident(state_field.field_name)}'
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

        if not select_parts:
            select_parts.append(f'{src_alias}.*')
        return _SqlState(
            select=',\n                    '.join(select_parts),
            join='\n                '.join(join_parts),
            attach_dbs=tuple(attach_dbs),
        )

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
        if rows is not None:
            return rows
        if callable(self.fetch_rows):
            return self.fetch_rows(spec)
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


class REGISTERS(typing.NamedTuple):
    EMPLOYEE_STATE_BY_EMPLOYEE: RegisterSpec = EMPLOYEE_STATE_BY_EMPLOYEE


_REGISTERS_SINGLETON: Registers | None = None


def get_registers(*, reset: bool = False, fetch_rows=None, declared_specs: Sequence[RegisterSpec] | None = None,
                  repo: RegisterAdminRepo | None = None, auto_sync: bool = False) -> Registers:
    global _REGISTERS_SINGLETON
    if reset or _REGISTERS_SINGLETON is None or fetch_rows is not None or declared_specs is not None or repo is not None:
        specs = tuple(declared_specs or REGISTERS)
        _REGISTERS_SINGLETON = Registers(repo=repo, fetch_rows=fetch_rows, declared_specs=specs, auto_sync=auto_sync)
    return _REGISTERS_SINGLETON
