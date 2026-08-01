from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib
import json
import keyword
import os
import pathlib
import re
import shutil
import tempfile
from typing import Any

from project_cust_38.db_identity import canonical_db_key, split_table_key, srv_db_name


GENERATOR_VERSION = '1.2.0'

CORE_FOLDER_NAME = 'project_cust_38'
DEFAULT_ARTIFACT_DIRNAME = 'dynamic_db_models'

debug = False

CURRENT_MODULE_FOLDER = pathlib.Path(__file__).resolve().parent


def _module_root() -> pathlib.Path:
    """Locate the repository root without importing MES configuration.

    The generator normally lives in ``Srv/`` while generated artifacts live in
    the sibling ``project_cust_38/`` directory.  The old implementation created
    an accidental ``Srv/project_cust_38`` tree when no explicit output path was
    supplied.
    """
    start = pathlib.Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / CORE_FOLDER_NAME).is_dir():
            return candidate
    raise FileNotFoundError(
        f'Не найден корень проекта с каталогом {CORE_FOLDER_NAME!r} начиная от {start}'
    )


def _default_output_dir(output_dir: str | pathlib.Path | None = None) -> pathlib.Path:
    if output_dir:
        return pathlib.Path(output_dir)
    return _module_root() / CORE_FOLDER_NAME / DEFAULT_ARTIFACT_DIRNAME


def _write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _py_repr(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True)


def _stable_json_dumps(data: Any) -> str: # todo
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=str, separators=(',', ':'))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()


def _utc_now_text() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')


def _load_admin_backend():
    """Import the DB-aware admin layer only for an explicit command.

    Rendering helpers and importing this generator stay side-effect free.  The
    MES admin module imports the SQL/config contour, so it must never be pulled
    merely to obtain a naming helper or type mapping.
    """
    return importlib.import_module('project_cust_38.context_admin')


def _guess_python_name(field_name: str) -> str:
    text = str(field_name or '').strip()
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


def _guess_orm_field_class(db_type: str | None) -> str:
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


def _default_expression_for_orm_field(orm_field_class: str, nullable: bool) -> str:
    """Return source code, not a Python string value.

    The generator embeds this result directly into ``Field(default=...)``.
    Quoting it with ``!r`` would turn ``None``/``0`` into the strings
    ``'None'``/``'0'`` and silently corrupt default semantics.
    """
    if nullable:
        return 'None'
    return {
        'IntField': '0',
        'FloatField': '0.0',
        'BlobField': "b''",
        'BoolField': '0',
        'DateTimeField': "''",
        'StrField': "''",
    }.get(orm_field_class, "''")


def _orm_class_name(table_key: str, postfix: str = '') -> str:
    chunks = [part for part in table_key.replace('.', '_').split('_') if part]
    if not chunks:
        return 'GeneratedModel'
    return ''.join(part[:1].upper() + part[1:] for part in chunks) + postfix


def _field_python_name(field: dict[str, Any]) -> str:
    py_name = field.get('python_name') or _guess_python_name(field.get('field_name', ''))
    if not isinstance(py_name, str) or not py_name.isidentifier() or keyword.iskeyword(py_name):
        py_name = _guess_python_name(field.get('field_name', ''))
    if not isinstance(py_name, str) or not py_name.isidentifier():
        py_name = '_'
    if keyword.iskeyword(py_name):
        py_name = f'{py_name}_'
    return py_name


def _render_manifest_py(manifest: dict[str, Any]) -> str:
    return (
        '"""Автогенерированный manifest схем project_cust_38."""\n\n'
        f'MANIFEST = {_py_repr(manifest)}\n'
        f'ARTIFACT_VERSION = {manifest["artifact_version"]!r}\n'
        f'GENERATED_AT_UTC = {manifest["generated_at_utc"]!r}\n'
    )


def _render_table_hints(tables: list[dict[str, Any]], table_fields: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for field in table_fields:
        grouped.setdefault(field['table_key'], []).append(field)
    payload = {}
    for table in tables:
        fields = sorted(grouped.get(table['table_key'], []), key=lambda item: (item.get('sort_order', 0), item['field_name']))
        payload[table['table_key']] = {
            'db_key': table['db_key'],
            'table_name': table['table_name'],
            'schema_enabled': table['schema_enabled'],
            'cache_enabled': table['cache_enabled'],
            'cache_lifetime_min': table['cache_lifetime_min'],
            'validity_mark': table['validity_mark'],
            'fields': fields,
        }
    return (
        '"""Автогенерированные table-centric hints по физическим таблицам."""\n\n'
        f'TABLE_HINTS = {_py_repr(payload)}\n'
    )


def _render_source_hints() -> str:
    return (
        '"""Автогенерированные source hints. Пока источник не заполнен, остается совместимый stub."""\n\n'
        'SOURCE_HINTS = {}\n'
    )


def _enabled_tables(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [table for table in tables if table.get('schema_enabled', 1)]


def _validate_table_identities(tables: list[dict[str, Any]]) -> None:
    """Validate table_key/db_key/table_name and fail on alias duplicates.

    Existing legacy prefixes are accepted, but the three columns must still
    describe the same physical identity.  No row is renamed here.
    """
    grouped: dict[tuple[str, str], list[str]] = {}
    errors: list[str] = []
    for table in _enabled_tables(tables):
        table_key = str(table.get('table_key') or '').strip()
        db_key = str(table.get('db_key') or '').strip()
        table_name = str(table.get('table_name') or '').strip()
        if not table_key or not db_key or not table_name:
            errors.append(f'неполная identity: table_key={table_key!r}, db_key={db_key!r}, table_name={table_name!r}')
            continue
        key_db, key_table = split_table_key(table_key)
        if not key_table:
            errors.append(f'table_key={table_key!r} не содержит разделитель db.table')
            continue
        if key_table.casefold() != table_name.casefold():
            errors.append(
                f'table_key={table_key!r} указывает таблицу {key_table!r}, '
                f'но table_name={table_name!r}'
            )
        if canonical_db_key(key_db).casefold() != canonical_db_key(db_key).casefold():
            errors.append(
                f'table_key={table_key!r} и db_key={db_key!r} принадлежат разным БД'
            )
        marker = (canonical_db_key(db_key).casefold(), table_name.casefold())
        grouped.setdefault(marker, []).append(table_key)
    conflicts = [sorted(set(keys)) for keys in grouped.values() if len(set(keys)) > 1]
    if conflicts:
        errors.append(
            'дубликаты canonical table identity: '
            + '; '.join(', '.join(keys) for keys in conflicts)
        )
    if errors:
        raise RuntimeError('Генерация остановлена: ' + ' | '.join(errors))


def _model_name_map(tables: list[dict[str, Any]]) -> dict[str, str]:
    """Stable names; prefix with db_key only when table names collide."""
    _validate_table_identities(tables)
    enabled = _enabled_tables(tables)
    base_names = [_orm_class_name(str(table.get('table_name') or '')) for table in enabled]
    counts = {name: base_names.count(name) for name in set(base_names)}
    result: dict[str, str] = {}
    used: set[str] = set()
    for table, base_name in zip(enabled, base_names):
        table_key = str(table.get('table_key') or '')
        stable_identity = f"{canonical_db_key(table.get('db_key'))}.{table.get('table_name') or ''}"
        name = base_name if counts.get(base_name, 0) == 1 else _orm_class_name(stable_identity)
        original = name
        suffix = 2
        while name in used:
            name = f'{original}{suffix}'
            suffix += 1
        used.add(name)
        result[table_key] = name
    return result


def _collect_model_names(tables: list[dict[str, Any]]) -> list[str]:
    model_names = _model_name_map(tables)
    return [model_names[str(table.get('table_key') or '')] for table in _enabled_tables(tables)]


def _static_contract_names(model_class_name: str) -> list[str]:
    return [
        f'{model_class_name}Hint',
        f'{model_class_name}CreateHint',
        f'{model_class_name}UpdateHint',
        f'{model_class_name}FilterHint',
        f'{model_class_name}QuerySetProtocol',
        f'{model_class_name}ObjectManagerProtocol',
        f'{model_class_name}QueryCallable',
        f'{model_class_name}FilterCallable',
        f'{model_class_name}ExcludeCallable',
        f'{model_class_name}GetCallable',
        f'{model_class_name}FirstCallable',
        f'{model_class_name}CountCallable',
        f'{model_class_name}AllCallable',
        f'{model_class_name}ValuesCallable',
        f'{model_class_name}AsSmartListCallable',
        f'{model_class_name}CreateCallable',
        f'{model_class_name}UpdateCallable',
    ]


def _collect_hint_names(tables: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    model_names = _model_name_map(tables)
    for table in _enabled_tables(tables):
        result.extend(_static_contract_names(model_names[str(table.get('table_key') or '')]))
    return result


def _manager_hint_name(model_class_name: str) -> str:
    return f'{model_class_name}ObjectManagerProtocol'


def _queryset_protocol_name(model_class_name: str) -> str:
    return f'{model_class_name}QuerySetProtocol'


def _callable_name(model_class_name: str, kind: str) -> str:
    return f'{model_class_name}{kind}Callable'


def _create_param_annotation_for_field(orm_field_class: str, nullable: bool) -> str:
    return _hint_annotation_for_field(orm_field_class, nullable)


def _annotation_for_orm_field(orm_field_class: str) -> str:
    if orm_field_class == 'IntField':
        return 'int'
    if orm_field_class == 'FloatField':
        return 'float'
    if orm_field_class == 'BoolField':
        return 'bool'
    if orm_field_class == 'BlobField':
        return 'bytes'
    if orm_field_class == 'JsonTextField':
        return 'Any'
    if orm_field_class == 'ListTextField':
        return 'list[Any]'
    return 'str'


def _hint_annotation_for_field(orm_field_class: str, nullable: bool) -> str:
    annotation = _annotation_for_orm_field(orm_field_class)
    if nullable:
        return f'{annotation} | None'
    return annotation


def _aliases_for_fields(fields: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in fields:
        py_name = _field_python_name(field)
        alias = field.get('label') or field.get('field_name')
        if alias not in (None, ''):
            result[py_name] = str(alias)
    return result


def _filter_iter_annotation(annotation: str) -> str:
    return f'list[{annotation}] | tuple[{annotation}, ...] | set[{annotation}]'


def _filter_contains_annotation(orm_field_class: str) -> str | None:
    if orm_field_class in {'StrField', 'DateTimeField', 'JsonTextField', 'ListTextField'}:
        return 'str'
    return None


def _filter_ordered_annotation(orm_field_class: str, annotation: str) -> str | None:
    if orm_field_class in {'IntField', 'FloatField', 'DateTimeField'}:
        return annotation
    return None


def _append_typed_dict_body(lines: list[str], fields: list[dict[str, Any]], *, exclude_pk: bool = False) -> None:
    appended = False
    used_names: set[str] = set()
    for field in fields:
        if exclude_pk and field.get('is_pk'):
            continue
        orm_field_class = field.get('orm_field_class') or _guess_orm_field_class(field.get('db_type'))
        nullable = bool(field.get('nullable', 1))
        py_name = _field_python_name(field)
        if not py_name.isidentifier() or keyword.iskeyword(py_name) or py_name in used_names:
            continue
        lines.append(f'    {py_name}: {_hint_annotation_for_field(orm_field_class, nullable)}')
        used_names.add(py_name)
        appended = True
    if not appended:
        lines.append('    pass')


def _append_filter_hint_body(lines: list[str], fields: list[dict[str, Any]]) -> None:
    appended = False
    used_names: set[str] = set()
    lines.append('    pk: Any')
    lines.append('    pk__in: list[Any] | tuple[Any, ...] | set[Any]')
    lines.append('    pk__isnull: bool')
    appended = True
    for field in fields:
        orm_field_class = field.get('orm_field_class') or _guess_orm_field_class(field.get('db_type'))
        nullable = bool(field.get('nullable', 1))
        py_name = _field_python_name(field)
        if not py_name.isidentifier() or keyword.iskeyword(py_name) or py_name in used_names:
            continue
        annotation = _hint_annotation_for_field(orm_field_class, nullable)
        lines.append(f'    {py_name}: {annotation}')
        lines.append(f'    {py_name}__in: {_filter_iter_annotation(annotation)}')
        lines.append(f'    {py_name}__isnull: bool')
        ordered_annotation = _filter_ordered_annotation(orm_field_class, annotation)
        if ordered_annotation:
            lines.append(f'    {py_name}__gt: {ordered_annotation}')
            lines.append(f'    {py_name}__gte: {ordered_annotation}')
            lines.append(f'    {py_name}__lt: {ordered_annotation}')
            lines.append(f'    {py_name}__lte: {ordered_annotation}')
        contains_annotation = _filter_contains_annotation(orm_field_class)
        if contains_annotation:
            lines.append(f'    {py_name}__contains: {contains_annotation}')
            lines.append(f'    {py_name}__icontains: {contains_annotation}')
        used_names.add(py_name)
        appended = True
    if not appended:
        lines.append('    pass')


def _append_field_parameters(
    lines: list[str],
    fields: list[dict[str, Any]],
    *,
    indent: str,
    exclude_pk: bool = False,
    used_names: set[str] | None = None,
) -> int:
    used_names = used_names if used_names is not None else set()
    appended = 0
    for field in fields:
        if exclude_pk and field.get('is_pk'):
            continue
        orm_field_class = field.get('orm_field_class') or _guess_orm_field_class(field.get('db_type'))
        nullable = bool(field.get('nullable', 1))
        py_name = _field_python_name(field)
        if not py_name.isidentifier() or keyword.iskeyword(py_name) or py_name in used_names:
            continue
        annotation = _create_param_annotation_for_field(orm_field_class, nullable)
        lines.append(f'{indent}{py_name}: {annotation} = ...,')
        used_names.add(py_name)
        appended += 1
    return appended


def _append_explicit_create_signature(
    lines: list[str],
    *,
    owner: str,
    fields: list[dict[str, Any]],
    model_class_name: str,
    method_name: str = 'create',
    runtime_proxy_names: bool = False,
) -> None:
    lines.append(f'    def {method_name}(')
    lines.append('        self,')
    keyword_lines: list[str] = []
    if runtime_proxy_names:
        keyword_lines.append('        db: str | None = None,')
        keyword_lines.append('        attach_dbs: Any = None,')
        keyword_lines.append('        executor: Any = None,')
        used = {'self', 'db', 'attach_dbs', 'executor', '_kwargs'}
    else:
        keyword_lines.append('        _db: str | None = None,')
        keyword_lines.append('        _attach_dbs: Any = None,')
        keyword_lines.append('        _executor: Any = None,')
        used = {'self', '_db', '_attach_dbs', '_executor', '_kwargs'}
    _append_field_parameters(keyword_lines, fields, indent='        ', used_names=used)
    if keyword_lines:
        lines.append('        *,')
        lines.extend(keyword_lines)
    lines.append('        **_kwargs: Any,')
    lines.append(f'    ) -> "{model_class_name}": ...')
    lines.append('')


def _append_explicit_update_signature(
    lines: list[str],
    *,
    fields: list[dict[str, Any]],
    return_annotation: str,
    method_name: str = 'update',
    include_pk_arg: bool = False,
    include_manager_context: bool = False,
) -> None:
    lines.append(f'    def {method_name}(')
    lines.append('        self,')
    if include_pk_arg:
        lines.append('        pk: Any,')
    keyword_lines: list[str] = []
    used = {'self', 'pk', '_kwargs'}
    if include_manager_context:
        keyword_lines.append('        _db: str | None = None,')
        keyword_lines.append('        _attach_dbs: Any = None,')
        keyword_lines.append('        _executor: Any = None,')
        used.update({'_db', '_attach_dbs', '_executor'})
    _append_field_parameters(keyword_lines, fields, indent='        ', exclude_pk=True, used_names=used)
    if keyword_lines:
        lines.append('        *,')
        lines.extend(keyword_lines)
    lines.append('        **_kwargs: Any,')
    lines.append(f'    ) -> {return_annotation}: ...')
    lines.append('')


def _render_orm_hints(tables: list[dict[str, Any]], table_fields: list[dict[str, Any]], manifest: str) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for field in table_fields:
        if not field.get('include_in_schema', 1):
            continue
        grouped.setdefault(field['table_key'], []).append(field)

    model_name_by_table = _model_name_map(tables)
    hint_names = _collect_hint_names(tables)
    model_names = _collect_model_names(tables)
    lines = [
        'from __future__ import annotations',
        manifest,
        '',
        'from typing import TYPE_CHECKING, Any, Protocol, TypedDict, Unpack',
        '',
        'from project_cust_38.Cust_orm import SaveResult, SmartList, SmartRow',
        '',
    ]
    if model_names:
        lines.append('if TYPE_CHECKING:')
        for model_name in model_names:
            lines.append(f'    from .orm_models import {model_name}')
        lines.append('')

    for table in tables:
        if not table.get('schema_enabled', 1):
            continue
        fields = sorted(grouped.get(table['table_key'], []), key=lambda item: (item.get('sort_order', 0), item['field_name']))
        class_name = model_name_by_table[str(table.get('table_key') or '')]
        hint_name = f'{class_name}Hint'
        create_hint_name = f'{class_name}CreateHint'
        update_hint_name = f'{class_name}UpdateHint'
        filter_hint_name = f'{class_name}FilterHint'
        qs_name = _queryset_protocol_name(class_name)
        manager_name = _manager_hint_name(class_name)

        lines.append(f'class {hint_name}(TypedDict, total=False): # noqa')
        _append_typed_dict_body(lines, fields)
        lines.append('')

        lines.append(f'class {create_hint_name}({hint_name}, total=False): # noqa')
        lines.append('    pass')
        lines.append('')

        lines.append(f'class {update_hint_name}(TypedDict, total=False): # noqa')
        _append_typed_dict_body(lines, fields, exclude_pk=True)
        lines.append('')

        lines.append(f'class {filter_hint_name}(TypedDict, total=False): # noqa')
        _append_filter_hint_body(lines, fields)
        lines.append('')

        lines.append(f'class {qs_name}(Protocol): # noqa')
        lines.append(f'    def using(self, db: str | None = None, attach_dbs: Any = None) -> "{qs_name}": ...')
        lines.append(f'    def with_executor(self, executor: Any) -> "{qs_name}": ...')
        lines.append(f'    def filter(self, **kwargs: Unpack[{filter_hint_name}]) -> "{qs_name}": ...')
        lines.append(f'    def exclude(self, **kwargs: Unpack[{filter_hint_name}]) -> "{qs_name}": ...')
        lines.append(f'    def where(self, sql: str, params: Any = None) -> "{qs_name}": ...')
        lines.append(f'    def order_by(self, *fields: str) -> "{qs_name}": ...')
        lines.append(f'    def limit(self, value: int | None) -> "{qs_name}": ...')
        lines.append('    def all(self, *, as_dict: bool = False, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None) -> SmartList: ...')
        lines.append('    def as_smartlist(self, *, by_aliases: bool = False, by_db_columns: bool = True, aliases: dict[str, str] | None = None) -> SmartList: ...')
        lines.append('    def values(self, *fields: str, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None) -> SmartList: ...')
        lines.append(f'    def first(self, *, as_dict: bool = False, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None) -> "{class_name} | SmartRow | None": ...')
        lines.append(f'    def get(self, *, as_dict: bool = False, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None, **kwargs: Unpack[{filter_hint_name}]) -> "{class_name} | SmartRow": ...')
        lines.append('    def count(self) -> int: ...')
        lines.append('')

        lines.append(f'class {manager_name}(Protocol): # noqa')
        lines.append(f'    def query(self, *, _db: str | None = None, _attach_dbs: Any = None, _executor: Any = None) -> "{qs_name}": ...')
        lines.append(f'    def using(self, _db: str | None = None, _attach_dbs: Any = None) -> "{qs_name}": ...')
        lines.append(f'    def with_executor(self, _executor: Any) -> "{qs_name}": ...')
        lines.append(f'    def filter(self, **_kwargs: Unpack[{filter_hint_name}]) -> "{qs_name}": ...')
        lines.append(f'    def exclude(self, **_kwargs: Unpack[{filter_hint_name}]) -> "{qs_name}": ...')
        lines.append(f'    def where(self, sql: str, params: Any = None) -> "{qs_name}": ...')
        lines.append(f'    def order_by(self, *fields: str) -> "{qs_name}": ...')
        lines.append(f'    def limit(self, value: int | None) -> "{qs_name}": ...')
        lines.append('    def all(self, *, as_dict: bool = False, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None) -> SmartList: ...')
        lines.append(f'    def as_smartlist(self, *, by_aliases: bool = False, by_db_columns: bool = True, aliases: dict[str, str] | None = None, **_kwargs: Unpack[{filter_hint_name}]) -> SmartList: ...')
        lines.append('    def values(self, *fields: str, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None) -> SmartList: ...')
        lines.append(f'    def first(self, *, as_dict: bool = False, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None, **_kwargs: Unpack[{filter_hint_name}]) -> "{class_name} | SmartRow | None": ...')
        lines.append(f'    def get(self, pk: Any = ..., *, _db: str | None = None, _attach_dbs: Any = None, _executor: Any = None, as_dict: bool = False, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None, **_kwargs: Unpack[{filter_hint_name}]) -> "{class_name} | SmartRow": ...')
        lines.append(f'    def count(self, **_kwargs: Unpack[{filter_hint_name}]) -> int: ...')
        _append_explicit_create_signature(lines, owner=manager_name, fields=fields, model_class_name=class_name, runtime_proxy_names=False)
        _append_explicit_update_signature(lines, fields=fields, return_annotation='SaveResult', include_pk_arg=True, include_manager_context=True)

        lines.append(f'class {_callable_name(class_name, "Query")}(Protocol): # noqa')
        lines.append(f'    def __call__(self, *, db: str | None = None, attach_dbs: Any = None, executor: Any = None) -> "{qs_name}": ...')
        lines.append('')

        lines.append(f'class {_callable_name(class_name, "Filter")}(Protocol): # noqa')
        lines.append(f'    def __call__(self, **kwargs: Unpack[{filter_hint_name}]) -> "{qs_name}": ...')
        lines.append('')

        lines.append(f'class {_callable_name(class_name, "Exclude")}(Protocol): # noqa')
        lines.append(f'    def __call__(self, **kwargs: Unpack[{filter_hint_name}]) -> "{qs_name}": ...')
        lines.append('')

        lines.append(f'class {_callable_name(class_name, "Get")}(Protocol): # noqa')
        lines.append(f'    def __call__(self, pk: Any = ..., *, db: str | None = None, attach_dbs: Any = None, executor: Any = None, as_dict: bool = False, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None, **kwargs: Unpack[{filter_hint_name}]) -> "{class_name} | SmartRow": ...')
        lines.append('')

        lines.append(f'class {_callable_name(class_name, "First")}(Protocol): # noqa')
        lines.append(f'    def __call__(self, *, as_dict: bool = False, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None, **kwargs: Unpack[{filter_hint_name}]) -> "{class_name} | SmartRow | None": ...')
        lines.append('')

        lines.append(f'class {_callable_name(class_name, "Count")}(Protocol): # noqa')
        lines.append(f'    def __call__(self, **kwargs: Unpack[{filter_hint_name}]) -> int: ...')
        lines.append('')

        lines.append(f'class {_callable_name(class_name, "All")}(Protocol): # noqa')
        lines.append('    def __call__(self, *, as_dict: bool = False, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None) -> SmartList: ...')
        lines.append('')

        lines.append(f'class {_callable_name(class_name, "Values")}(Protocol): # noqa')
        lines.append('    def __call__(self, *fields: str, by_aliases: bool = False, by_db_columns: bool = False, aliases: dict[str, str] | None = None) -> SmartList: ...')
        lines.append('')

        lines.append(f'class {_callable_name(class_name, "AsSmartList")}(Protocol): # noqa')
        lines.append(f'    def __call__(self, *, by_aliases: bool = False, by_db_columns: bool = True, aliases: dict[str, str] | None = None, **kwargs: Unpack[{filter_hint_name}]) -> SmartList: ...')
        lines.append('')

        lines.append(f'class {_callable_name(class_name, "Create")}(Protocol): # noqa')
        _append_explicit_create_signature(lines, owner=_callable_name(class_name, 'Create'), fields=fields, model_class_name=class_name, method_name='__call__', runtime_proxy_names=True)

        lines.append(f'class {_callable_name(class_name, "Update")}(Protocol): # noqa')
        _append_explicit_update_signature(lines, fields=fields, return_annotation='bool', method_name='__call__')

    lines.append(f'__all__ = {_py_repr(hint_names)}')
    return '\n'.join(lines).rstrip() + '\n'




def _group_relation_pairs(relation_pairs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for pair in relation_pairs or []:
        grouped.setdefault(str(pair.get('relation_key') or ''), []).append(pair)
    for key in list(grouped):
        grouped[key] = sorted(grouped[key], key=lambda item: int(item.get('pair_no', 0) or 0))
    return grouped


def _relation_python_name(relation: dict[str, Any]) -> str:
    raw = str(
        relation.get('relation_name')
        or str(relation.get('relation_key') or '').rsplit('.', 1)[-1]
        or ''
    ).strip()
    name = _guess_python_name(raw)
    if not name or not name.isidentifier() or keyword.iskeyword(name) or name.startswith('_'):
        raise ValueError(f'Некорректное имя ORM relation: {raw!r} -> {name!r}')
    return name


_RELATION_RESERVED_NAMES = {
    'object_manager', 'query', 'filter', 'exclude', 'where', 'order_by', 'limit',
    'all', 'first', 'get', 'count', 'values', 'as_smartlist', 'create', 'update',
    'save', 'delete', 'pk', 'pk_name', 'get_field', 'get_relation', 'relation_specs',
    'resolve_db', 'resolve_attach_dbs', 'to_dict', 'from_row', 'ALIASES',
}


def _field_python_index(table_fields: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for field in table_fields:
        if not field.get('include_in_schema', 1):
            continue
        table_key = str(field.get('table_key') or '')
        field_name = str(field.get('field_name') or '')
        py_name = _field_python_name(field)
        if table_key and field_name:
            result[(table_key, field_name)] = py_name
        if table_key and py_name:
            result[(table_key, py_name)] = py_name
    return result


def _relation_annotation(
    cardinality: str,
    target_model: str,
    missing_policy: str,
    join_type: str,
    on_many_policy: str = 'error',
) -> str:
    """Render the value type actually returned by Relationship.__get__."""
    cardinality = str(cardinality or 'many_to_one').strip().lower()
    missing_policy = str(missing_policy or 'none').strip().lower()
    on_many_policy = str(on_many_policy or 'error').strip().lower()
    if cardinality in {'one_to_many', 'many_to_many'}:
        base = f'list[{target_model}]'
        return f'{base} | None' if missing_policy in {'none', 'drop', 'default'} else base

    alternatives = [target_model]
    if on_many_policy == 'list':
        alternatives.append(f'list[{target_model}]')
    if missing_policy == 'empty':
        alternatives.append(f'list[{target_model}]')
    elif missing_policy != 'raise':
        alternatives.append('None')
    return ' | '.join(dict.fromkeys(alternatives))


def _prepare_relation_declarations(
    tables: list[dict[str, Any]],
    table_fields: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    relation_pairs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Validate and normalize admin relation rows for inline model declarations.

    No MES runtime module is imported here.  A relation that cannot be represented
    faithfully by the current lazy ORM descriptor stops generation instead of
    disappearing behind ``try/except: pass``.
    """
    model_by_table_key = _model_name_map(tables)
    table_by_key = {
        str(table.get('table_key') or ''): table
        for table in _enabled_tables(tables)
    }
    fields_by_table: dict[str, set[str]] = {}
    for field in table_fields:
        if not field.get('include_in_schema', 1):
            continue
        table_key = str(field.get('table_key') or '')
        fields_by_table.setdefault(table_key, set()).add(_field_python_name(field))
    field_py_by_key = _field_python_index(table_fields)
    pairs_by_relation = _group_relation_pairs(relation_pairs)
    declarations: dict[str, list[dict[str, Any]]] = {}
    seen_names: dict[str, set[str]] = {
        table_key: set(fields_by_table.get(table_key, set())) | set(_RELATION_RESERVED_NAMES)
        for table_key in table_by_key
    }

    for relation in sorted(
        (dict(item) for item in relations if item.get('is_enabled', 1)),
        key=lambda item: (str(item.get('source_table_key') or ''), str(item.get('relation_name') or '')),
    ):
        relation_key = str(relation.get('relation_key') or '').strip()
        source_table_key = str(relation.get('source_table_key') or '').strip()
        target_table_key = str(relation.get('target_table_key') or '').strip()
        if not relation_key:
            raise ValueError(f'Relation без relation_key: {relation!r}')
        if source_table_key not in table_by_key:
            raise ValueError(
                f'Relation {relation_key!r}: source_table_key={source_table_key!r} '
                'не входит в активный набор генерируемых таблиц'
            )
        if target_table_key not in table_by_key:
            raise ValueError(
                f'Relation {relation_key!r}: target_table_key={target_table_key!r} '
                'не входит в активный набор генерируемых таблиц'
            )

        relation_name = _relation_python_name(relation)
        if relation_name in seen_names[source_table_key]:
            raise ValueError(
                f'Relation {relation_key!r}: имя {relation_name!r} конфликтует '
                f'с полем/методом модели {model_by_table_key[source_table_key]}'
            )
        seen_names[source_table_key].add(relation_name)

        cardinality = str(relation.get('cardinality') or 'many_to_one').strip().lower()
        if cardinality not in {'one_to_one', 'many_to_one', 'one_to_many', 'many_to_many'}:
            raise ValueError(f'Relation {relation_key!r}: неподдерживаемая cardinality={cardinality!r}')
        if cardinality == 'many_to_many':
            raise ValueError(
                f'Relation {relation_key!r}: many_to_many ещё не имеет исполняемого through-runtime; '
                'генерация остановлена, чтобы не создать ложный рабочий API'
            )

        join_type = str(relation.get('join_type') or 'LEFT JOIN').strip().upper()
        if join_type in {'LEFT', 'LEFT OUTER'}:
            join_type = 'LEFT JOIN'
        elif join_type in {'INNER', 'JOIN'}:
            join_type = 'INNER JOIN'
        if join_type not in {'LEFT JOIN', 'INNER JOIN'}:
            raise ValueError(f'Relation {relation_key!r}: ORM stage 1 не поддерживает join_type={join_type!r}')

        missing_policy = str(relation.get('missing_policy') or 'none').strip().lower()
        if missing_policy not in {'none', 'empty', 'raise', 'drop', 'default'}:
            raise ValueError(f'Relation {relation_key!r}: неподдерживаемый missing_policy={missing_policy!r}')
        on_many = str(relation.get('on_many_policy') or 'error').strip().lower()
        if on_many not in {'error', 'first', 'last', 'list'}:
            raise ValueError(f'Relation {relation_key!r}: неподдерживаемый on_many_policy={on_many!r}')

        raw_pairs = pairs_by_relation.get(relation_key, [])
        if not raw_pairs:
            raise ValueError(f'Relation {relation_key!r}: отсутствуют admin_relation_field_pairs')
        normalized_pairs: list[dict[str, Any]] = []
        direct_count = 0
        used_local_fields: set[str] = set()
        used_remote_fields: set[str] = set()
        for pair in raw_pairs:
            left_table_key = str(pair.get('left_table_key') or '').strip()
            right_table_key = str(pair.get('right_table_key') or '').strip()
            left_field_name = str(pair.get('left_field_name') or '').strip()
            right_field_name = str(pair.get('right_field_name') or '').strip()
            role = str(pair.get('role') or 'direct').strip().lower()
            operator = str(pair.get('operator') or '=').strip()
            pair_join_type = str(pair.get('pair_join_type') or '').strip()
            if role != 'direct':
                raise ValueError(
                    f'Relation {relation_key!r}: lazy ORM stage 1 не исполняет role={role!r}; '
                    'метаданные не будут молча проигнорированы'
                )
            if pair_join_type:
                raise ValueError(
                    f'Relation {relation_key!r}: lazy ORM stage 1 не исполняет '
                    f'pair_join_type={pair_join_type!r}'
                )

            if left_table_key == source_table_key and right_table_key == target_table_key:
                local_table_key, local_field_name = left_table_key, left_field_name
                remote_table_key, remote_field_name = right_table_key, right_field_name
            elif right_table_key == source_table_key and left_table_key == target_table_key:
                if operator != '=':
                    raise ValueError(
                        f'Relation {relation_key!r}: обратная ориентация пары допустима только для operator="="'
                    )
                local_table_key, local_field_name = right_table_key, right_field_name
                remote_table_key, remote_field_name = left_table_key, left_field_name
            else:
                raise ValueError(
                    f'Relation {relation_key!r}: пара #{pair.get("pair_no", 0)} '
                    f'связывает {left_table_key!r} -> {right_table_key!r}, '
                    'но ORM descriptor поддерживает только source <-> target'
                )

            local_py = field_py_by_key.get((local_table_key, local_field_name))
            remote_py = field_py_by_key.get((remote_table_key, remote_field_name))
            if not local_py:
                raise ValueError(
                    f'Relation {relation_key!r}: локальное поле {local_table_key}.{local_field_name} '
                    'не найдено среди генерируемых полей'
                )
            if not remote_py:
                raise ValueError(
                    f'Relation {relation_key!r}: удалённое поле {remote_table_key}.{remote_field_name} '
                    'не найдено среди генерируемых полей'
                )
            if role == 'direct':
                direct_count += 1
                if operator != '=':
                    raise ValueError(
                        f'Relation {relation_key!r}: lazy ORM поддерживает direct operator только "=", '
                        f'получено {operator!r}'
                    )
                if local_py in used_local_fields or remote_py in used_remote_fields:
                    raise ValueError(
                        f'Relation {relation_key!r}: direct field_pairs содержат повторное '
                        f'локальное/удалённое поле ({local_py!r}, {remote_py!r})'
                    )
                used_local_fields.add(local_py)
                used_remote_fields.add(remote_py)
            normalized_pairs.append({
                'local_python_name': local_py,
                'remote_python_name': remote_py,
                'role': role or 'direct',
                'operator': operator or '=',
                'pair_join_type': pair_join_type,
            })
        if direct_count == 0:
            raise ValueError(f'Relation {relation_key!r}: нет ни одной пары role="direct"')

        target_model = model_by_table_key[target_table_key]
        declaration = {
            'relation_key': relation_key,
            'relation_name': relation_name,
            'source_table_key': source_table_key,
            'target_table_key': target_table_key,
            'target_model': target_model,
            'annotation': _relation_annotation(
                cardinality,
                target_model,
                missing_policy,
                join_type,
                on_many,
            ),
            'cardinality': cardinality,
            'join_type': join_type,
            'missing_policy': missing_policy,
            'on_many_policy': on_many,
            'select_prefix': str(relation.get('select_prefix') or relation_name),
            'notes': str(relation.get('notes') or ''),
            'pairs': normalized_pairs,
        }
        declarations.setdefault(source_table_key, []).append(declaration)

    return declarations


def _append_inline_relations(lines: list[str], declarations: list[dict[str, Any]]) -> None:
    for relation in declarations:
        lines.append(
            f'    {relation["relation_name"]}: {relation["annotation"]} = Relationship('
        )
        lines.append(f'        {relation["target_model"]!r},')
        lines.append(f'        relation_key={relation["relation_key"]!r},')
        lines.append('        field_pairs=(')
        for pair in relation['pairs']:
            lines.append(
                '            RelationFieldPair('
                f'{pair["local_python_name"]!r}, {pair["remote_python_name"]!r}, '
                f'role={pair["role"]!r}, operator={pair["operator"]!r}, '
                f'pair_join_type={pair["pair_join_type"]!r}),'
            )
        lines.append('        ),')
        lines.append(f'        cardinality={relation["cardinality"]!r},')
        lines.append(f'        missing_policy={relation["missing_policy"]!r},')
        lines.append(f'        join_type={relation["join_type"]!r},')
        lines.append(f'        on_many={relation["on_many_policy"]!r},')
        lines.append(f'        select_prefix={relation["select_prefix"]!r},')
        lines.append(f'        notes={relation["notes"]!r},')
        lines.append('    )')


def _render_orm_models(
    tables: list[dict[str, Any]],
    table_fields: list[dict[str, Any]],
    manifest: str,
    relations: list[dict[str, Any]] | None = None,
    relation_pairs: list[dict[str, Any]] | None = None,
) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for field in table_fields:
        if not field.get('include_in_schema', 1):
            continue
        grouped.setdefault(field['table_key'], []).append(field)

    model_name_by_table = _model_name_map(tables)
    relation_declarations = _prepare_relation_declarations(
        tables,
        table_fields,
        relations or [],
        relation_pairs or [],
    )
    model_names = _collect_model_names(tables)
    lines = [
        'from __future__ import annotations',
        manifest,
        '',
        'from typing import TYPE_CHECKING, ClassVar',
        '',
        'from project_cust_38.Cust_orm import BaseModel, IntField, FloatField, StrField, BoolField, DateTimeField, BlobField, JsonTextField, ListTextField',
        'from project_cust_38.context_relations import Relationship, RelationFieldPair',
        'from .orm_hints import *',
        '',
    ]

    for table in _enabled_tables(tables):
        table_key = str(table.get('table_key') or '')
        fields = sorted(
            grouped.get(table_key, []),
            key=lambda item: (item.get('sort_order', 0), item['field_name']),
        )
        inline_relations = relation_declarations.get(table_key, [])
        class_name = model_name_by_table[table_key]
        hint_name = f'{class_name}Hint'
        manager_hint_name = _manager_hint_name(class_name)
        pk_field = next((field for field in fields if field.get('is_pk')), None)
        pk_python_name = _field_python_name(pk_field) if pk_field is not None else 'id'
        canonical_key = canonical_db_key(table.get('db_key'))
        db_reference = srv_db_name(canonical_key)
        lines.extend([
            f'class {class_name}(BaseModel[{hint_name}]): # noqa',
            '    if TYPE_CHECKING:',
            f'        object_manager: ClassVar["{manager_hint_name}"]',
            f'        query: ClassVar["{_callable_name(class_name, "Query")}"]',
            f'        filter: ClassVar["{_callable_name(class_name, "Filter")}"]',
            f'        exclude: ClassVar["{_callable_name(class_name, "Exclude")}"]',
            f'        get: ClassVar["{_callable_name(class_name, "Get")}"]',
            f'        count: ClassVar["{_callable_name(class_name, "Count")}"]',
            f'        values: ClassVar["{_callable_name(class_name, "Values")}"]',
            f'        create: ClassVar["{_callable_name(class_name, "Create")}"]',
            f'        update: "{_callable_name(class_name, "Update")}"',
            '',
            f'    __table__ = {table["table_name"]!r}',
            f'    __db_key__ = {str(table.get("db_key") or canonical_key)!r}',
            f'    __canonical_db_key__ = {canonical_key!r}',
            f'    __table_key__ = {table_key!r}',
            f'    __db__ = {db_reference!r}',
            f'    __pk__ = {pk_python_name!r}',
            f'    ALIASES = {_py_repr(_aliases_for_fields(fields))}',
            '',
        ])
        for field in fields:
            orm_field_class = field.get('orm_field_class') or _guess_orm_field_class(field.get('db_type'))
            nullable = bool(field.get('nullable', 1))
            is_pk = bool(field.get('is_pk', 0))
            default_value = None if is_pk else _default_expression_for_orm_field(orm_field_class, nullable)
            annotation = _hint_annotation_for_field(orm_field_class, nullable)
            py_name = _field_python_name(field)
            lines.append(
                f"    {py_name}: {annotation} = {orm_field_class}(db_column={field['field_name']!r}, "
                f"default={default_value}, nullable={nullable!r}, primary_key={is_pk!r})"
            )
        if fields and inline_relations:
            lines.append('')
        _append_inline_relations(lines, inline_relations)
        if not fields and not inline_relations:
            lines.append('    pass')
        lines.append('')

    lines.append(f'__all__ = {_py_repr(model_names)}')
    return '\n'.join(lines).rstrip() + '\n'



def _render_manager_hint_classes(tables: list[dict[str, Any]], grouped: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Совместимый stub: manager/queryset/proxy-контракты теперь генерируются в orm_hints.py."""
    return []


def _render_init_py(model_names: list[str], hint_names: list[str] | None = None) -> str:
    exports = [
        # 'MANIFEST',
        # 'ARTIFACT_VERSION',
        # 'GENERATED_AT_UTC',
        # 'TABLE_HINTS',
        # 'SOURCE_HINTS',
        *model_names,
        # *(hint_names or []),
    ]
    return (
        # 'from .orm_hints import *\n'
        'from .orm_models import *\n'
        f'__all__ = {_py_repr(exports)}\n'
    )


def _group_fields_by_table(table_fields: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for field in table_fields:
        grouped.setdefault(field['table_key'], []).append(field)
    return grouped


def _build_table_signatures(
    tables: list[dict[str, Any]],
    table_fields: list[dict[str, Any]],
    relations: list[dict[str, Any]] | None = None,
    relation_pairs: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    grouped = _group_fields_by_table(table_fields)
    relation_declarations = _prepare_relation_declarations(
        tables, table_fields, relations or [], relation_pairs or []
    )
    result: dict[str, dict[str, Any]] = {}
    for table in tables:
        table_key = table['table_key']
        fields = sorted(grouped.get(table_key, []), key=lambda item: (item.get('sort_order', 0), item.get('field_name', '')))
        api_payload = {
            'db_key': table.get('db_key'),
            'table_name': table.get('table_name'),
            'schema_enabled': table.get('schema_enabled'),
            'fields': [
                {
                    'field_name': field.get('field_name'),
                    'python_name': field.get('python_name'),
                    'db_type': field.get('db_type'),
                    'nullable': field.get('nullable'),
                    'is_pk': field.get('is_pk'),
                    'include_in_schema': field.get('include_in_schema'),
                    'orm_field_class': field.get('orm_field_class'),
                }
                for field in fields
            ],
            'relations': relation_declarations.get(table_key, []),
        }
        cache_payload = {
            'cache_enabled': table.get('cache_enabled'),
            'cache_lifetime_min': table.get('cache_lifetime_min'),
            'stale_after_dt': table.get('stale_after_dt'),
            'validity_mark': table.get('validity_mark'),
        }
        ui_payload = {
            'label_data': [
                {
                    'field_name': field.get('field_name'),
                    'label': field.get('label'),
                    'widget_hint': field.get('widget_hint'),
                    'form_hint': field.get('form_hint'),
                    'sort_order': field.get('sort_order'),
                    'notes': field.get('notes'),
                }
                for field in fields
            ],
            'table_notes': table.get('notes'),
        }
        result[table_key] = {
            'api_hash': _sha256_text(_stable_json_dumps(api_payload)),
            'cache_hash': _sha256_text(_stable_json_dumps(cache_payload)),
            'ui_hash': _sha256_text(_stable_json_dumps(ui_payload)),
            'table_name': table.get('table_name'),
            'db_key': table.get('db_key'),
        }
    return result


def _load_existing_manifest(out_dir: pathlib.Path) -> dict[str, Any] | None:
    manifest_json = out_dir / 'manifest.json'
    if manifest_json.exists():
        try:
            return json.loads(manifest_json.read_text(encoding='utf-8'))
        except Exception:
            return None
    return None


def preview_schema_diff(*, output_dir: str | pathlib.Path | None = None, generator_version: str = GENERATOR_VERSION) -> dict[str, Any]:
    admin = _load_admin_backend()
    repo = admin.ContextAdminRepo()
    out_dir = _default_output_dir(output_dir)
    tables = repo.get_physical_tables(schema_enabled=1, only_enabled=True)
    all_table_fields = repo.get_table_fields(include_disabled=False)
    relations = repo.get_relations(only_enabled=True)
    relation_pairs = repo.get_relation_field_pairs()
    _validate_table_identities(tables)
    current_signatures = _build_table_signatures(tables, all_table_fields, relations, relation_pairs)
    previous_manifest = _load_existing_manifest(out_dir) or {}
    previous_signatures = previous_manifest.get('table_signatures', {}) or {}

    added_tables: list[str] = []
    removed_tables: list[str] = []
    changed_tables: dict[str, dict[str, Any]] = {}
    safe_changes: list[str] = []
    breaking_changes: list[str] = []

    all_keys = sorted(set(current_signatures.keys()).union(previous_signatures.keys()))
    for table_key in all_keys:
        old = previous_signatures.get(table_key)
        new = current_signatures.get(table_key)
        if old is None and new is not None:
            added_tables.append(table_key)
            breaking_changes.append(f'Добавлена таблица/модель: {table_key}')
            continue
        if old is not None and new is None:
            removed_tables.append(table_key)
            breaking_changes.append(f'Удалена таблица/модель: {table_key}')
            continue
        if not old or not new:
            continue
        api_changed = str(old.get('api_hash') or '') != str(new.get('api_hash') or '')
        cache_changed = str(old.get('cache_hash') or '') != str(new.get('cache_hash') or '')
        ui_changed = str(old.get('ui_hash') or '') != str(new.get('ui_hash') or '')
        if not any((api_changed, cache_changed, ui_changed)):
            continue
        changes = []
        if api_changed:
            changes.append('api')
            breaking_changes.append(f'Изменен публичный API модели: {table_key}')
        if cache_changed:
            changes.append('cache')
            safe_changes.append(f'Изменена cache-политика: {table_key}')
        if ui_changed:
            changes.append('ui')
            safe_changes.append(f'Изменены ui-hints: {table_key}')
        changed_tables[table_key] = {
            'api_changed': api_changed,
            'cache_changed': cache_changed,
            'ui_changed': ui_changed,
            'changes': changes,
            'old': old,
            'new': new,
        }

    has_changes = bool(added_tables or removed_tables or changed_tables)
    has_breaking_changes = bool(added_tables or removed_tables or any(item.get('api_changed') for item in changed_tables.values()))
    return {
        'output_dir': str(out_dir),
        'generator_version': generator_version,
        'has_changes': has_changes,
        'has_breaking_changes': has_breaking_changes,
        'added_tables': added_tables,
        'removed_tables': removed_tables,
        'changed_tables': changed_tables,
        'safe_changes': safe_changes,
        'breaking_changes': breaking_changes,
        'current_model_names': _collect_model_names(tables),
        'previous_model_names': previous_manifest.get('model_names', []) or [],
    }


def _validate_rendered_python(files: dict[str, str]) -> None:
    for relative_name, text in files.items():
        if not relative_name.endswith('.py'):
            continue
        try:
            compile(text, relative_name, 'exec')
        except SyntaxError as exc:
            raise SyntaxError(
                f'Генератор создал синтаксически некорректный {relative_name}: '
                f'line={exc.lineno}, offset={exc.offset}, msg={exc.msg}'
            ) from exc


def _publish_rendered_files(out_dir: pathlib.Path, files: dict[str, str]) -> None:
    """Render/compile everything first; replace target files only after validation."""
    out_dir.mkdir(parents=True, exist_ok=True)
    _validate_rendered_python(files)
    staging = pathlib.Path(tempfile.mkdtemp(prefix='.schema-stage-', dir=str(out_dir.parent)))
    try:
        for relative_name, text in files.items():
            target = staging / relative_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        # Manifest is the commit marker and is replaced last.
        ordered = [name for name in files if name != 'manifest.json']
        if 'manifest.json' in files:
            ordered.append('manifest.json')
        for relative_name in ordered:
            source = staging / relative_name
            target = out_dir / relative_name
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def generate_schema_artifacts(*, debug: bool = False, output_dir: str | pathlib.Path | None = None, generator_version: str = GENERATOR_VERSION) -> dict[str, Any]:
    admin = _load_admin_backend()
    repo = admin.ContextAdminRepo()
    out_dir = _default_output_dir(output_dir)

    tables = repo.get_physical_tables(schema_enabled=1, only_enabled=True)
    all_table_fields = repo.get_table_fields(include_disabled=False)
    relations = repo.get_relations(only_enabled=True)
    relation_pairs = repo.get_relation_field_pairs()
    _validate_table_identities(tables)
    # Validation happens before any output file is touched.
    _prepare_relation_declarations(tables, all_table_fields, relations, relation_pairs)
    model_names = _collect_model_names(tables)

    hashes = repo.compute_manifest_hashes()
    generated_at_utc = _utc_now_text()
    artifact_version = _sha256_text(
        hashes['admin_schema_hash']
        + hashes['table_fields_hash']
        + hashes.get('relation_specs_hash', '')
    )[:12]
    table_signatures = _build_table_signatures(
        tables, all_table_fields, relations, relation_pairs
    )

    manifest = {
        'generated_at_utc': generated_at_utc,
        'generator_version': generator_version,
        'admin_schema_hash': hashes['admin_schema_hash'],
        'table_fields_hash': hashes['table_fields_hash'],
        'relation_specs_hash': hashes.get('relation_specs_hash', ''),
        'artifact_version': artifact_version,
        'notes': f'generated into {out_dir}',
        'table_signatures': table_signatures,
        'model_names': model_names,
        'hint_names': _collect_hint_names(tables),
    }

    py_manifest = _render_manifest_py(manifest)
    rendered = {
        'orm_hints.py': _render_orm_hints(tables, all_table_fields, py_manifest),
        'orm_models.py': _render_orm_models(
            tables, all_table_fields, py_manifest, relations, relation_pairs
        ),
        '__init__.py': _render_init_py(model_names, _collect_hint_names(tables)),
        'manifest.json': json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True, default=str),
    }
    if debug:
        rendered.update({
            'table_hints.py': _render_table_hints(tables, all_table_fields),
            'schema_manifest.py': _render_manifest_py(manifest),
            'source_hints.py': _render_source_hints(),
        })
    _publish_rendered_files(out_dir, rendered)

    repo.write_manifest(admin.SchemaManifestMeta(**{
        'generated_at_utc': generated_at_utc,
        'generator_version': generator_version,
        'admin_schema_hash': hashes['admin_schema_hash'],
        'table_fields_hash': hashes['table_fields_hash'],
        'artifact_version': artifact_version,
        'notes': f'generated into {out_dir}',
    }))
    return {
        'output_dir': str(out_dir),
        'manifest': manifest,
        'files': sorted(str(path.relative_to(out_dir)) for path in out_dir.rglob('*') if path.is_file()),
    }


def _cmd_bootstrap(args: argparse.Namespace) -> int:
    admin = _load_admin_backend()
    repo = admin.ContextAdminRepo()
    if not args.db_path:
        from project_cust_38 import Cust_client_socket as CCS
        srvs = [CCS.Servers.db_naryad, CCS.Servers.db_kplan, CCS.Servers.db_users, CCS.Servers.db_nomen, CCS.Servers.db_dse]
    else:
        srvs = [args.db_path]
    for db_path in srvs:
        repo.bootstrap_tables_from_db(
            db_path=db_path,
            table_names=args.tables,
            db_key=None,
            include_fields=not args.skip_fields,
            schema_enabled=1 if args.schema_enabled else 0,
            cache_enabled=1,
            is_enabled=1,
            cache_lifetime_min=args.cache_lifetime_min,
            notes=args.notes or 'bootstrap via context_schema_generator',
            skip_tables=args.skip_tables,
        )
    print(f'Генерация таблиц для БД {repo.db_files}: Для таблиц <{args.tables or "Всех"}>')
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    result = generate_schema_artifacts(output_dir=args.output_dir, generator_version=args.generator_version)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    result = preview_schema_diff(output_dir=args.output_dir, generator_version=args.generator_version)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generator/schema wrapper для административного контура project_cust_38')
    parser.add_argument('--db-files', dest='db_files', default=None, help='Путь к CFG.Config.project.db_files')

    sub = parser.add_subparsers(dest='command', required=True)

    p_boot = sub.add_parser('bootstrap-db', help='Заполнить admin_physical_tables и admin_table_fields из физической БД')
    p_boot.add_argument('--db-path', required=False, help='Путь к физической sqlite БД (Например SRV:Naryads.db)')
    p_boot.add_argument('--tables', nargs='*', default=None, help='Список таблиц для обновления/создания; если не задан — все')
    p_boot.add_argument('--skip-fields', action='store_true', help='Поля, которые не должны входить в схемы')
    p_boot.add_argument('--schema-enabled', action='store_true', help='Пометить таблицы schema_enabled = True')
    p_boot.add_argument('--cache-lifetime-min', type=int, default=120, help='Время жизни кэша в таблицах')
    p_boot.add_argument('--notes', default='', help='Заметка последнего изменения')
    p_boot.add_argument('--skip-tables', nargs='*', default=None, help='Таблицы которые нужно пропустить')
    p_boot.set_defaults(func=_cmd_bootstrap)

    p_preview = sub.add_parser('preview', help='Показать diff между текущей схемой и последним локальным manifest')
    p_preview.add_argument('--output-dir', default=None, help=f'Каталог вывода (дефолт /project_cust_38/{DEFAULT_ARTIFACT_DIRNAME})')
    p_preview.add_argument('--generator-version', default=GENERATOR_VERSION)
    p_preview.set_defaults(func=_cmd_preview)

    p_gen = sub.add_parser('generate', help='Сгенерировать shipped schema artifacts')
    p_gen.add_argument('--output-dir', default=None, help=f'Каталог вывода (дефолт /project_cust_38/{DEFAULT_ARTIFACT_DIRNAME})')
    p_gen.add_argument('--generator-version', default=GENERATOR_VERSION)
    p_gen.set_defaults(func=_cmd_generate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == '__main__':
    raise SystemExit(main())
