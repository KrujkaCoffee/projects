from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

from project_cust_38 import context_admin as CADM  # type: ignore


GENERATOR_VERSION = '1.0.0'
DEFAULT_ARTIFACT_DIRNAME = 'generated_schemas'


def _module_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def _default_output_dir(output_dir: str | pathlib.Path | None = None) -> pathlib.Path:
    if output_dir:
        return pathlib.Path(output_dir)
    return _module_root() / DEFAULT_ARTIFACT_DIRNAME


def _write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _py_repr(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True)


def _orm_class_name(table_key: str) -> str:
    chunks = [part for part in table_key.replace('.', '_').split('_') if part]
    if not chunks:
        return 'GeneratedModel'
    return ''.join(part[:1].upper() + part[1:] for part in chunks) + 'Model'


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


def _render_source_hints(sources: list[dict[str, Any]], source_tables: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[str]] = {}
    for row in source_tables:
        grouped.setdefault(row['source_code'], []).append(row['table_key'])
    payload = {}
    for source in sources:
        payload[source['source_code']] = {
            'source_kind': source['source_kind'],
            'base_table_key': source['base_table_key'],
            'schema_source_table_key': source['schema_source_table_key'],
            'schema_enabled': source['schema_enabled'],
            'cache_enabled': source['cache_enabled'],
            'cache_lifetime_min': source['cache_lifetime_min'],
            'dependencies': sorted(grouped.get(source['source_code'], [])),
        }
    return (
        '"""Автогенерированные source-level hints."""\n\n'
        f'SOURCE_HINTS = {_py_repr(payload)}\n'
    )


def _render_orm_models(tables: list[dict[str, Any]], table_fields: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for field in table_fields:
        if not field.get('include_in_schema', 1):
            continue
        grouped.setdefault(field['table_key'], []).append(field)

    lines = [
        '"""Автогенерированные ORM-lite skeleton models."""',
        '',
        'from __future__ import annotations',
        '',
        'try:',
        '    from project_cust_38.Cust_orm import BaseModel, IntField, FloatField, StrField, BoolField, DateTimeField, BlobField',
        'except Exception:',
        '    from Cust_orm import BaseModel, IntField, FloatField, StrField, BoolField, DateTimeField, BlobField  # type: ignore',
        '',
        'try:',
        '    from project_cust_38 import Cust_config as CFG',
        'except Exception:',
        '    try:',
        '        import Cust_config as CFG  # type: ignore',
        '    except Exception:',
        '        CFG = None  # type: ignore',
        '',
        '',
        'def _resolve_db_path(db_key: str):',
        '    try:',
        '        return getattr(CFG.Config.project, db_key)  # type: ignore[attr-defined]',
        '    except Exception:',
        '        return db_key',
        '',
    ]

    for table in tables:
        if not table.get('schema_enabled', 1):
            continue
        fields = sorted(grouped.get(table['table_key'], []), key=lambda item: (item.get('sort_order', 0), item['field_name']))
        class_name = _orm_class_name(table['table_key'])
        pk_field = next((field['field_name'] for field in fields if field.get('is_pk')), None) or 'id'
        lines.extend([
            f'class {class_name}(BaseModel):',
            f'    __table__ = {table["table_name"]!r}',
            f'    __db__ = lambda: _resolve_db_path({table["db_key"]!r})',
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
            default_value = CADM._default_for_orm_field(orm_field_class, nullable)  # type: ignore[attr-defined]
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
    return '\n'.join(lines).rstrip() + '\n'


def _render_init_py() -> str:
    return (
        'from .schema_manifest import MANIFEST, ARTIFACT_VERSION, GENERATED_AT_UTC\n'
        'from .table_hints import TABLE_HINTS\n'
        'from .source_hints import SOURCE_HINTS\n'
        '__all__ = ["MANIFEST", "ARTIFACT_VERSION", "GENERATED_AT_UTC", "TABLE_HINTS", "SOURCE_HINTS"]\n'
    )


def generate_schema_artifacts(*, db_files: str | None = None, output_dir: str | pathlib.Path | None = None, generator_version: str = GENERATOR_VERSION) -> dict[str, Any]:
    repo = CADM.ensure_admin_schema(db_files)
    out_dir = _default_output_dir(output_dir)

    tables = repo.get_physical_tables(schema_enabled=1, only_enabled=True)
    all_table_fields = repo.get_table_fields(include_disabled=False)
    sources = repo.get_sources(schema_enabled=1)
    source_tables = repo.get_source_tables()

    hashes = repo.compute_manifest_hashes()
    generated_at_utc = CADM._utc_now()  # type: ignore[attr-defined]
    artifact_version = hashes['admin_schema_hash'][:12]
    manifest = {
        'generated_at_utc': generated_at_utc,
        'generator_version': generator_version,
        'admin_schema_hash': hashes['admin_schema_hash'],
        'source_templates_hash': hashes['source_templates_hash'],
        'table_fields_hash': hashes['table_fields_hash'],
        'artifact_version': artifact_version,
        'notes': f'generated into {out_dir}',
    }

    _write_text(out_dir / '__init__.py', _render_init_py())
    _write_text(out_dir / 'schema_manifest.py', _render_manifest_py(manifest))
    _write_text(out_dir / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    _write_text(out_dir / 'table_hints.py', _render_table_hints(tables, all_table_fields))
    _write_text(out_dir / 'source_hints.py', _render_source_hints(sources, source_tables))
    _write_text(out_dir / 'orm_models.py', _render_orm_models(tables, all_table_fields))

    repo.write_manifest(CADM.SchemaManifestMeta(**manifest))
    return {
        'output_dir': str(out_dir),
        'manifest': manifest,
        'files': sorted(str(path.relative_to(out_dir)) for path in out_dir.rglob('*') if path.is_file()),
    }


def _cmd_bootstrap(args: argparse.Namespace) -> int:
    repo = CADM.ensure_admin_schema(args.db_files)
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
    )
    print(f'Bootstrapped tables into {repo.db_files}: {args.tables or "<all>"}')
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    result = generate_schema_artifacts(db_files=args.db_files, output_dir=args.output_dir, generator_version=args.generator_version)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_cleanup(args: argparse.Namespace) -> int:
    repo = CADM.ensure_admin_schema(args.db_files)
    result = repo.cleanup_source_variants(
        older_than_days=args.older_than_days,
        source_code=args.source_code,
        dry_run=args.dry_run,
        keep_pinned=not args.drop_pinned,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generator/schema wrapper для административного контура project_cust_38')
    parser.add_argument('--db-files', dest='db_files', default=None, help='Путь к CFG.Config.project.db_files')

    sub = parser.add_subparsers(dest='command', required=True)

    p_boot = sub.add_parser('bootstrap-db', help='Заполнить admin_physical_tables и admin_table_fields из физической БД')
    p_boot.add_argument('--db-path', required=True, help='Путь к физической sqlite БД')
    p_boot.add_argument('--db-key', default=None, help='Явный db_key вместо auto-resolve')
    p_boot.add_argument('--tables', nargs='*', default=None, help='Список таблиц для bootstrap; если не задан — все')
    p_boot.add_argument('--skip-fields', action='store_true', help='Не загружать PRAGMA table_info')
    p_boot.add_argument('--schema-enabled', action='store_true', help='Пометить bootstrapped tables как schema_enabled=1')
    p_boot.add_argument('--cache-lifetime-min', type=int, default=120)
    p_boot.add_argument('--notes', default='')
    p_boot.set_defaults(func=_cmd_bootstrap)

    p_gen = sub.add_parser('generate', help='Сгенерировать shipped schema artifacts')
    p_gen.add_argument('--output-dir', default=None, help='Каталог вывода внутри project_cust_38')
    p_gen.add_argument('--generator-version', default=GENERATOR_VERSION)
    p_gen.set_defaults(func=_cmd_generate)

    p_cleanup = sub.add_parser('cleanup-variants', help='Ручной cleanup source realizations')
    p_cleanup.add_argument('--older-than-days', type=int, default=30)
    p_cleanup.add_argument('--source-code', default=None)
    p_cleanup.add_argument('--limit', type=int, default=None)
    p_cleanup.add_argument('--drop-pinned', action='store_true')
    p_cleanup.add_argument('--dry-run', action='store_true')
    p_cleanup.set_defaults(func=_cmd_cleanup)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == '__main__':
    raise SystemExit(main())
