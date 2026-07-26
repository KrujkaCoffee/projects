from __future__ import annotations

import argparse
import json
import keyword
import pathlib
from typing import Any

from project_cust_38 import context_admin as CADM   # noqa
from project_cust_38 import Cust_Functions as F     # noqa


GENERATOR_VERSION = '1.1.0'

CORE_FOLDER_NAME = 'project_cust_38'
DEFAULT_ARTIFACT_DIRNAME = 'dynamic_db_models'

debug = False

CURRENT_MODULE_FOLDER = pathlib.Path(__file__).resolve().parent


def _module_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def _default_output_dir(output_dir: str | pathlib.Path | None = None) -> pathlib.Path:
    if output_dir:
        return pathlib.Path(output_dir)
    base_path = CURRENT_MODULE_FOLDER / CORE_FOLDER_NAME
    base_path.mkdir(parents=True, exist_ok=True)
    if not base_path.exists():
        raise Exception(f"В текущей директории отсутсвует {CORE_FOLDER_NAME}")
    return _module_root() / CORE_FOLDER_NAME / DEFAULT_ARTIFACT_DIRNAME


def _write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _py_repr(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True)


def _stable_json_dumps(data: Any) -> str: # todo
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=str, separators=(',', ':'))


def _sha256_text(value: str) -> str: # todo
    return CADM._sha256_text(value)


def _orm_class_name(table_key: str, postfix: str = '') -> str:
    chunks = [part for part in table_key.replace('.', '_').split('_') if part]
    if not chunks:
        return 'GeneratedModel'
    return ''.join(part[:1].upper() + part[1:] for part in chunks) + postfix


def _field_python_name(field: dict[str, Any]) -> str:
    py_name = field.get('python_name') or CADM.guess_python_name(field.get('field_name', ''))
    if not isinstance(py_name, str) or not py_name.isidentifier() or keyword.iskeyword(py_name):
        py_name = CADM.guess_python_name(field.get('field_name', ''))
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


def _collect_model_names(tables: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for table in tables:
        if not table.get('schema_enabled', 1):
            continue
        result.append(_orm_class_name(table['table_name']))
    return result


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
    for table in tables:
        if not table.get('schema_enabled', 1):
            continue
        result.extend(_static_contract_names(_orm_class_name(table['table_name'])))
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
        orm_field_class = field.get('orm_field_class') or CADM.guess_orm_field_class(field.get('db_type'))
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
        orm_field_class = field.get('orm_field_class') or CADM.guess_orm_field_class(field.get('db_type'))
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
) -> None:
    used_names = used_names if used_names is not None else set()
    for field in fields:
        if exclude_pk and field.get('is_pk'):
            continue
        orm_field_class = field.get('orm_field_class') or CADM.guess_orm_field_class(field.get('db_type'))
        nullable = bool(field.get('nullable', 1))
        py_name = _field_python_name(field)
        if not py_name.isidentifier() or keyword.iskeyword(py_name) or py_name in used_names:
            continue
        annotation = _create_param_annotation_for_field(orm_field_class, nullable)
        lines.append(f'{indent}{py_name}: {annotation} = ...,')
        used_names.add(py_name)


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
    lines.append('        *,')
    if runtime_proxy_names:
        lines.append('        db: str | None = None,')
        lines.append('        attach_dbs: Any = None,')
        lines.append('        executor: Any = None,')
        used = {'self', 'db', 'attach_dbs', 'executor', '_kwargs'}
    else:
        lines.append('        _db: str | None = None,')
        lines.append('        _attach_dbs: Any = None,')
        lines.append('        _executor: Any = None,')
        used = {'self', '_db', '_attach_dbs', '_executor', '_kwargs'}
    _append_field_parameters(lines, fields, indent='        ', used_names=used)
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
    lines.append('        *,')
    used = {'self', 'pk', '_kwargs'}
    if include_manager_context:
        lines.append('        _db: str | None = None,')
        lines.append('        _attach_dbs: Any = None,')
        lines.append('        _executor: Any = None,')
        used.update({'_db', '_attach_dbs', '_executor'})
    _append_field_parameters(lines, fields, indent='        ', exclude_pk=True, used_names=used)
    lines.append('        **_kwargs: Any,')
    lines.append(f'    ) -> {return_annotation}: ...')
    lines.append('')


def _render_orm_hints(tables: list[dict[str, Any]], table_fields: list[dict[str, Any]], manifest: str) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for field in table_fields:
        if not field.get('include_in_schema', 1):
            continue
        grouped.setdefault(field['table_key'], []).append(field)

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
        class_name = _orm_class_name(table['table_name'])
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



def _render_orm_models(tables: list[dict[str, Any]], table_fields: list[dict[str, Any]], manifest: str) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for field in table_fields:
        if not field.get('include_in_schema', 1):
            continue
        grouped.setdefault(field['table_key'], []).append(field)

    model_names = _collect_model_names(tables)
    lines = [
        'from __future__ import annotations',
        manifest,
        '',
        'from typing import TYPE_CHECKING, ClassVar',
        '',
        'from project_cust_38.Cust_orm import BaseModel, IntField, FloatField, StrField, BoolField, DateTimeField, BlobField, JsonTextField, ListTextField',
        'from .orm_hints import *',
        'from project_cust_38 import Cust_config as CFG         #noqa',
        'from project_cust_38 import Cust_client_socket as CCS  # noqa',
        '',
        'def db(db_key: str):',
        '    def wrap():',
        '        alias_instance = getattr(CCS.Servers, db_key, None)',
        '        if alias_instance:',
        '            db_alias = alias_instance.alias',
        '        else:',
        '            db_alias = f"{db_key}.db"',
        '        server = CCS.Servers[db_alias]',
        '        if server is None:',
        '            print(f"[Cust_orm] Ключ сервера: {db_key!r} не найден!")',
        '            return server',
        '        return server',
        '    return wrap',
        '',
    ]

    for table in tables:
        if not table.get('schema_enabled', 1):
            continue
        fields = sorted(grouped.get(table['table_key'], []), key=lambda item: (item.get('sort_order', 0), item['field_name']))
        class_name = _orm_class_name(table['table_name'])
        hint_name = f'{class_name}Hint'
        manager_hint_name = _manager_hint_name(class_name)
        pk_field = next((field for field in fields if field.get('is_pk')), None)
        pk_python_name = _field_python_name(pk_field) if pk_field is not None else 'id'
        lines.extend([
            f'class {class_name}(BaseModel[{hint_name}]): # noqa',
            '    if TYPE_CHECKING:',
            f'        object_manager: ClassVar["{manager_hint_name}"]',
            f'        query: ClassVar["{_callable_name(class_name, "Query")}"]',
            f'        filter: ClassVar["{_callable_name(class_name, "Filter")}"]',
            f'        exclude: ClassVar["{_callable_name(class_name, "Exclude")}"]',
            f'        get: ClassVar["{_callable_name(class_name, "Get")}"]',
            # f'        first: ClassVar["{_callable_name(class_name, "First")}"]',
            f'        count: ClassVar["{_callable_name(class_name, "Count")}"]',
            # f'        all: ClassVar["{_callable_name(class_name, "All")}"]',
            f'        values: ClassVar["{_callable_name(class_name, "Values")}"]',
            # f'        as_smartlist: ClassVar["{_callable_name(class_name, "AsSmartList")}"]',
            f'        create: ClassVar["{_callable_name(class_name, "Create")}"]',
            f'        update: "{_callable_name(class_name, "Update")}"',
            '',
            f'    __table__ = {table["table_name"]!r}',
            f'    __db__ = db({table["db_key"]!r})',
            f'    __pk__ = {pk_python_name!r}',
            f'    ALIASES = {_py_repr(_aliases_for_fields(fields))}',
            '',
        ])
        if not fields:
            lines.append('    pass')
            lines.append('')
            continue
        for field in fields:
            orm_field_class = field.get('orm_field_class') or CADM.guess_orm_field_class(field.get('db_type'))
            nullable = bool(field.get('nullable', 1))
            is_pk = bool(field.get('is_pk', 0))

            default_value = None if is_pk else CADM._default_for_orm_field(orm_field_class, nullable)
            annotation = _hint_annotation_for_field(orm_field_class, nullable)
            py_name = _field_python_name(field)
            lines.append(
                f"    {py_name}: {annotation} = {orm_field_class}(db_column={field['field_name']!r}, default={default_value}, nullable={str(nullable)}, primary_key={str(is_pk)})"
            )
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
        *(hint_names or []),
    ]
    return (
        'from .orm_hints import *\n'
        'from .orm_models import *\n'
        f'__all__ = {_py_repr(exports)}\n'
    )


def _group_fields_by_table(table_fields: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for field in table_fields:
        grouped.setdefault(field['table_key'], []).append(field)
    return grouped


def _build_table_signatures(tables: list[dict[str, Any]], table_fields: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped = _group_fields_by_table(table_fields)
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
    repo = CADM.ContextAdminRepo()
    out_dir = _default_output_dir(output_dir)
    tables = repo.get_physical_tables(schema_enabled=1, only_enabled=True)
    all_table_fields = repo.get_table_fields(include_disabled=False)
    current_signatures = _build_table_signatures(tables, all_table_fields)
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


def generate_schema_artifacts(*, debug: bool = False, output_dir: str | pathlib.Path | None = None, generator_version: str = GENERATOR_VERSION) -> dict[str, Any]:
    repo = CADM.ContextAdminRepo()
    out_dir = _default_output_dir(output_dir)

    tables = repo.get_physical_tables(schema_enabled=1, only_enabled=True)
    all_table_fields = repo.get_table_fields(include_disabled=False)
    model_names = _collect_model_names(tables)

    hashes = repo.compute_manifest_hashes()
    generated_at_utc = F.now()
    artifact_version = hashes['admin_schema_hash'][:12]
    table_signatures = _build_table_signatures(tables, all_table_fields)

    manifest = {
        'generated_at_utc': generated_at_utc,
        'generator_version': generator_version,
        'admin_schema_hash': hashes['admin_schema_hash'],
        'table_fields_hash': hashes['table_fields_hash'],
        'artifact_version': artifact_version,
        'notes': f'generated into {out_dir}',
        'table_signatures': table_signatures,
        'model_names': model_names,
        'hint_names': _collect_hint_names(tables),
    }

    py_manifest = _render_manifest_py(manifest)

    _write_text(out_dir / 'orm_hints.py', _render_orm_hints(tables, all_table_fields, py_manifest))
    _write_text(out_dir / 'orm_models.py', _render_orm_models(tables, all_table_fields, py_manifest))
    _write_text(out_dir / '__init__.py', _render_init_py(model_names, _collect_hint_names(tables)))

    if debug:
        _write_text(out_dir / 'table_hints.py', _render_table_hints(tables, all_table_fields))
        _write_text(out_dir / 'schema_manifest.py', _render_manifest_py(manifest))
        _write_text(out_dir / 'source_hints.py', _render_source_hints())
        _write_text(out_dir / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))

    repo.write_manifest(CADM.SchemaManifestMeta(**{
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
    repo = CADM.ContextAdminRepo()
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
