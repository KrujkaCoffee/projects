from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

from project_cust_38 import context_admin as CADM   # noqa
from project_cust_38 import Cust_Functions as F     # noqa


GENERATOR_VERSION = '1.0.4'

CORE_FOLDER_NAME = 'project_cust_38'
DEFAULT_ARTIFACT_DIRNAME = 'dynamic_db_models'

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
        'from project_cust_38.Cust_orm import BaseModel, IntField, FloatField, StrField, BoolField, DateTimeField, BlobField',
        'from project_cust_38 import Cust_config as CFG         #noqa',
        'from project_cust_38 import Cust_client_socket as CCS  # noqa',
        '',
        'def db(db_key: str):',
        '    def wrap():',
        '        server = CCS.Servers[f"{db_key}.db"]',
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
        pk_field = next((field['field_name'] for field in fields if field.get('is_pk')), None) or 'id'
        lines.extend([
            f'class {class_name}(BaseModel): # noqa',
            f'    __table__ = {table["table_name"]!r}',
            f'    __db__ = db({table["db_key"]!r})',
            f'    __pk__ = {pk_field!r}',
            '',
        ])
        if not fields:
            lines.append('    pass')
            lines.append('')
            continue
        for field in fields:
            orm_field_class = field.get('orm_field_class') or CADM.guess_orm_field_class(field.get('db_type'))
            nullable = bool(field.get('nullable', 1))
            default_value = CADM._default_for_orm_field(orm_field_class, nullable)
            annotation = 'str'
            if orm_field_class == 'IntField':
                annotation = 'int'
            elif orm_field_class == 'FloatField':
                annotation = 'float'
            elif orm_field_class == 'BoolField':
                annotation = 'bool'
            elif orm_field_class == 'BlobField':
                annotation = 'bytes'
            py_name = field['python_name'] or CADM.guess_python_name(field['field_name'])
            lines.append(
                f"    {py_name}: {annotation} = {orm_field_class}(db_column={field['field_name']!r}, default={default_value}, nullable={str(nullable)}, primary_key={str(bool(field.get('is_pk', 0)))})"
            )
        lines.append('')

    lines.append(f'__all__ = {_py_repr(model_names)}')
    return '\n'.join(lines).rstrip() + '\n'


def _render_init_py(model_names: list[str]) -> str:
    exports = [
        'MANIFEST',
        'ARTIFACT_VERSION',
        'GENERATED_AT_UTC',
        'TABLE_HINTS',
        'SOURCE_HINTS',
        *model_names,
    ]
    return (
        'from .schema_manifest import MANIFEST, ARTIFACT_VERSION, GENERATED_AT_UTC\n'
        'from .table_hints import TABLE_HINTS\n'
        'from .source_hints import SOURCE_HINTS\n'
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
    }

    py_manifest = _render_manifest_py(manifest)

    _write_text(out_dir / 'orm_models.py', _render_orm_models(tables, all_table_fields, py_manifest))
    _write_text(out_dir / '__init__.py', _render_init_py(model_names))
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
    repo.bootstrap_tables_from_db(
        db_path=args.db_path,
        table_names=args.tables,
        db_key=args.db_key,
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
    p_boot.add_argument('--db-path', required=True, help='Путь к физической sqlite БД (Например SRV:Naryads.db)')
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
