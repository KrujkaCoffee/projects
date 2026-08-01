# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import datetime
import hashlib
import importlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'project_cust_38'
_actual_sql_env = os.environ.get('MES_ACTUAL_SCHEMA_SQL', '').strip()
ACTUAL_SQL = pathlib.Path(_actual_sql_env) if _actual_sql_env else None
ACTUAL_RELATION_COLUMNS = {
    'relation_key', 'relation_name', 'source_table_key', 'target_table_key',
    'cardinality', 'join_type', 'missing_policy', 'on_many_policy',
    'select_prefix', 'is_enabled', 'is_generated', 'notes', 'updated_at',
}
ACTUAL_RELATION_PAIR_COLUMNS = {
    'relation_key', 'pair_no', 'left_table_key', 'left_field_name',
    'right_table_key', 'right_field_name', 'role', 'operator', 'pair_join_type',
}

# Cust_orm only needs the symbol at import time; no database is opened in tests.
fake_sql = types.ModuleType('project_cust_38.Cust_SQLite')
fake_sql.custom_request_c = lambda *args, **kwargs: []
sys.modules.setdefault('project_cust_38.Cust_SQLite', fake_sql)

from project_cust_38.db_identity import (  # noqa: E402
    canonical_db_key,
    equivalent_table_keys,
    make_table_key,
)
from project_cust_38.Cust_orm import BaseModel, IntField  # noqa: E402
from project_cust_38.context_relations import (  # noqa: E402
    RelationFieldPair,
    Relationship,
    relation_to_admin_records,
)


def _fake_context_admin_module() -> types.ModuleType:
    module = types.ModuleType('project_cust_38.context_admin')

    def guess_python_name(value):
        text = re.sub(r'[^\w]+', '_', str(value or ''), flags=re.UNICODE).strip('_') or '_'
        if text[0].isdigit():
            text = '_' + text
        return text

    module.guess_python_name = guess_python_name
    module.guess_orm_field_class = lambda value: {
        'INTEGER': 'IntField',
        'INT': 'IntField',
        'REAL': 'FloatField',
        'BLOB': 'BlobField',
    }.get(str(value or '').upper(), 'StrField')
    module._default_for_orm_field = lambda cls, nullable: (
        None if nullable else {'IntField': 0, 'FloatField': 0.0, 'BlobField': b''}.get(cls, '')
    )
    module._sha256_text = lambda value: hashlib.sha256(str(value).encode('utf-8')).hexdigest()
    module.ContextAdminRepo = object
    module.SchemaManifestMeta = dict
    return module


def _load_generator_module():
    saved = {
        key: sys.modules.get(key)
        for key in ('project_cust_38.context_admin', 'project_cust_38.Cust_Functions')
    }
    fake_admin = _fake_context_admin_module()
    fake_f = types.ModuleType('project_cust_38.Cust_Functions')
    fake_f.now = lambda *args, **kwargs: '2026-07-29 12:00:00'
    sys.modules['project_cust_38.context_admin'] = fake_admin
    sys.modules['project_cust_38.Cust_Functions'] = fake_f
    try:
        name = f'_stage1_generator_test_{id(fake_admin)}'
        spec = importlib.util.spec_from_file_location(name, ROOT / 'Srv' / 'context_schema_generator.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


def _fixture_schema():
    tables = [
        {
            'table_key': 'Naryad.mk', 'db_key': 'Naryad', 'table_name': 'mk',
            'schema_enabled': 1, 'cache_enabled': 1, 'cache_lifetime_min': 120,
            'validity_mark': 'mk-v', 'is_enabled': 1,
        },
        {
            'table_key': 'Naryad.naryad', 'db_key': 'Naryad', 'table_name': 'naryad',
            'schema_enabled': 1, 'cache_enabled': 1, 'cache_lifetime_min': 120,
            'validity_mark': 'nar-v', 'is_enabled': 1,
        },
    ]
    fields = [
        {'table_key': 'Naryad.mk', 'field_name': 'Пномер', 'python_name': 'Пномер', 'db_type': 'INTEGER', 'nullable': 0, 'is_pk': 1, 'include_in_schema': 1, 'sort_order': 0},
        {'table_key': 'Naryad.mk', 'field_name': 'Номенклатура', 'python_name': 'Номенклатура', 'db_type': 'TEXT', 'nullable': 1, 'is_pk': 0, 'include_in_schema': 1, 'sort_order': 1},
        {'table_key': 'Naryad.naryad', 'field_name': 'Пномер', 'python_name': 'Пномер', 'db_type': 'INTEGER', 'nullable': 0, 'is_pk': 1, 'include_in_schema': 1, 'sort_order': 0},
        {'table_key': 'Naryad.naryad', 'field_name': 'Номер_мк', 'python_name': 'Номер_мк', 'db_type': 'INTEGER', 'nullable': 1, 'is_pk': 0, 'include_in_schema': 1, 'sort_order': 1},
    ]
    relations = [
        {
            'relation_key': 'Naryad.mk.naryads', 'relation_name': 'naryads',
            'source_table_key': 'Naryad.mk', 'target_table_key': 'Naryad.naryad',
            'cardinality': 'one_to_many', 'join_type': 'LEFT JOIN',
            'missing_policy': 'empty', 'on_many_policy': 'error',
            'select_prefix': 'Наряды', 'is_enabled': 1, 'notes': 'reverse',
        },
        {
            'relation_key': 'Naryad.naryad.mk', 'relation_name': 'mk',
            'source_table_key': 'Naryad.naryad', 'target_table_key': 'Naryad.mk',
            'cardinality': 'many_to_one', 'join_type': 'LEFT JOIN',
            'missing_policy': 'none', 'on_many_policy': 'error',
            'select_prefix': 'МК', 'is_enabled': 1, 'notes': 'forward',
        },
    ]
    pairs = [
        {
            'relation_key': 'Naryad.mk.naryads', 'pair_no': 0,
            'left_table_key': 'Naryad.mk', 'left_field_name': 'Пномер',
            'right_table_key': 'Naryad.naryad', 'right_field_name': 'Номер_мк',
            'role': 'direct', 'operator': '=', 'pair_join_type': '',
        },
        {
            'relation_key': 'Naryad.naryad.mk', 'pair_no': 0,
            'left_table_key': 'Naryad.naryad', 'left_field_name': 'Номер_мк',
            'right_table_key': 'Naryad.mk', 'right_field_name': 'Пномер',
            'role': 'direct', 'operator': '=', 'pair_join_type': '',
        },
    ]
    return tables, fields, relations, pairs


class MemoryExecutor:
    def __init__(self):
        self.calls = []
        self.rows = {
            'mk': [
                {'Пномер': 10, 'Номенклатура': 'МК-10'},
            ],
            'naryad': [
                {'Пномер': 1, 'Номер_мк': 10},
                {'Пномер': 2, 'Номер_мк': 10},
            ],
        }

    def execute(self, bd, query, *, params=None, rez_dict=False, one=False, one_column=False, attach_dbs=()):
        params = list(params or [])
        self.calls.append({'db': bd, 'query': query, 'params': params, 'one': one})
        match = re.search(r'\bFROM\s+([^\s]+)', query, flags=re.I)
        table = (match.group(1).strip('"`[]') if match else '')
        rows = [dict(row) for row in self.rows.get(table, [])]
        where_matches = re.findall(r'(?:"([^"]+)"|([A-Za-zА-Яа-яЁё_][\wА-Яа-яЁё]*))\s*=\s*\?', query)
        where_fields = [quoted or plain for quoted, plain in where_matches]
        for field_name, value in zip(where_fields, params):
            rows = [row for row in rows if row.get(field_name) == value]
        limit_match = re.search(r'\bLIMIT\s+(\d+)', query, flags=re.I)
        if limit_match:
            rows = rows[:int(limit_match.group(1))]
        if one:
            return rows[0] if rows else None
        return rows


class TestDbIdentity(unittest.TestCase):
    def test_aliases_share_one_canonical_identity_without_rewrite(self):
        values = [
            'Naryad', 'Naryad.db', 'db_naryad', 'SRV:Naryad.db',
            r'C:\\DB_srv\\Naryad.db',
        ]
        self.assertEqual({canonical_db_key(value) for value in values}, {'Naryad'})
        self.assertEqual(make_table_key('db_naryad', 'naryad'), 'Naryad.naryad')
        aliases = equivalent_table_keys('db_naryad', 'naryad')
        self.assertIn('Naryad.naryad', aliases)
        self.assertIn('db_naryad.naryad', aliases)

    def test_identity_module_has_no_runtime_mes_imports(self):
        source = (PROJECT / 'db_identity.py').read_text(encoding='utf-8')
        forbidden = ('Cust_config', 'Cust_SQLite', 'Cust_client_socket', 'context_admin', 'CMS')
        for token in forbidden:
            self.assertNotIn(f'import {token}', source)
            self.assertNotIn(f'from project_cust_38 import {token}', source)


class TestGeneratorFinal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = _load_generator_module()
        cls.tables, cls.fields, cls.relations, cls.pairs = _fixture_schema()
        cls.manifest = 'MANIFEST = {}\nARTIFACT_VERSION = "test"\nGENERATED_AT_UTC = "test"'

    def test_pk_only_signatures_do_not_emit_bare_star_before_kwargs(self):
        hints = self.generator._render_orm_hints(
            [self.tables[0]], [self.fields[0]], self.manifest
        )
        compile(hints, 'orm_hints.py', 'exec')
        self.assertNotRegex(hints, r'\*,\s*\n\s*\*\*_kwargs')

    def test_generated_field_defaults_are_values_not_stringified_source(self):
        models = self.generator._render_orm_models(
            self.tables, self.fields, self.manifest, self.relations, self.pairs
        )
        self.assertIn("default=None, nullable=True", models)
        self.assertNotIn("default='None'", models)
        self.assertNotIn("default='0'", models)

    def test_relations_are_inline_typed_and_not_post_bound(self):
        models = self.generator._render_orm_models(
            self.tables, self.fields, self.manifest, self.relations, self.pairs
        )
        compile(models, 'orm_models.py', 'exec')
        mk_pos = models.index('class Mk(')
        relation_pos = models.index('    naryads: list[Naryad] = Relationship(', mk_pos)
        naryad_pos = models.index('class Naryad(')
        self.assertLess(mk_pos, relation_pos)
        self.assertLess(relation_pos, naryad_pos)
        self.assertIn('    mk: Mk | None = Relationship(', models)
        self.assertNotIn('__set_name__(', models)
        self.assertNotIn('__relations__[', models)
        self.assertNotIn('except Exception as _relationship_error', models)
        self.assertNotIn('Cust_config', models)
        self.assertNotIn('Cust_client_socket', models)
        self.assertIn("__db__ = 'SRV:Naryad.db'", models)
        self.assertIn("__table_key__ = 'Naryad.naryad'", models)

    def test_duplicate_canonical_db_identity_fails_closed(self):
        conflicting = [
            dict(self.tables[1]),
            {
                **dict(self.tables[1]),
                'table_key': 'db_naryad.naryad',
                'db_key': 'db_naryad',
            },
        ]
        with self.assertRaisesRegex(RuntimeError, 'дубликаты canonical table identity'):
            self.generator._model_name_map(conflicting)

    def test_same_table_name_in_two_databases_gets_unique_stable_classes(self):
        tables = [
            {**dict(self.tables[1]), 'table_key': 'Naryad.status', 'table_name': 'status'},
            {**dict(self.tables[1]), 'table_key': 'BD_users.status', 'db_key': 'BD_users', 'table_name': 'status'},
        ]
        names = self.generator._model_name_map(tables)
        self.assertEqual(len(set(names.values())), 2)
        self.assertIn('NaryadStatus', names.values())
        self.assertIn('BDUsersStatus', names.values())

    def test_generated_module_imports_and_relations_work(self):
        hints = self.generator._render_orm_hints(self.tables, self.fields, self.manifest)
        models = self.generator._render_orm_models(
            self.tables, self.fields, self.manifest, self.relations, self.pairs
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            pkg = root / 'generated_stage1'
            pkg.mkdir()
            (pkg / '__init__.py').write_text('', encoding='utf-8')
            (pkg / 'orm_hints.py').write_text(hints, encoding='utf-8')
            (pkg / 'orm_models.py').write_text(models, encoding='utf-8')
            sys.path.insert(0, str(root))
            try:
                module = importlib.import_module('generated_stage1.orm_models')
                executor = MemoryExecutor()
                mk = module.Mk(_persisted=True, _db='SRV:WrongSource.db', _executor=executor, Пномер=10)
                children = mk.naryads
                self.assertEqual([item.Пномер for item in children], [1, 2])
                self.assertEqual(executor.calls[-1]['db'], 'SRV:Naryad.db')

                nar = module.Naryad(_persisted=True, _db='SRV:WrongSource.db', _executor=executor, Пномер=1, Номер_мк=10)
                self.assertEqual(nar.mk.Пномер, 10)
                self.assertEqual(executor.calls[-1]['db'], 'SRV:Naryad.db')

                missing = module.Naryad(_persisted=True, _executor=executor, Пномер=3, Номер_мк=999)
                self.assertIsNone(missing.mk)
                specs = module.Naryad.relation_specs()
                self.assertEqual(specs['mk'].relation_key, 'Naryad.naryad.mk')
                self.assertIn('mk', module.Naryad.__annotations__)
            finally:
                sys.path.remove(str(root))
                for key in list(sys.modules):
                    if key == 'generated_stage1' or key.startswith('generated_stage1.'):
                        sys.modules.pop(key, None)


class TestCompositeLazyRelation(unittest.TestCase):
    def test_composite_relation_uses_all_fields_and_tuple_cache_key(self):
        class Target(BaseModel):
            __table__ = 'target'
            __db__ = 'SRV:Target.db'
            __db_key__ = 'Target'
            __table_key__ = 'Target.target'
            __pk__ = 'id'
            id: int = IntField(primary_key=True, nullable=False)
            x: int = IntField(nullable=False)
            y: int = IntField(nullable=False)

        class Source(BaseModel):
            __table__ = 'source'
            __db__ = 'SRV:Source.db'
            __db_key__ = 'Source'
            __table_key__ = 'Source.source'
            __pk__ = 'id'
            id: int = IntField(primary_key=True, nullable=False)
            a: int = IntField(nullable=False)
            b: int = IntField(nullable=False)
            target: Target | None = Relationship(
                Target,
                relation_key='Source.source.target',
                field_pairs=(
                    RelationFieldPair('a', 'x'),
                    RelationFieldPair('b', 'y'),
                ),
                cardinality='one_to_one',
                missing_policy='none',
            )

        class Executor(MemoryExecutor):
            def __init__(self):
                super().__init__()
                self.rows['target'] = [
                    {'id': 1, 'x': 7, 'y': 8},
                    {'id': 2, 'x': 7, 'y': 9},
                ]

        executor = Executor()
        src = Source(_persisted=True, _executor=executor, id=1, a=7, b=8)
        self.assertEqual(src.target.id, 1)
        self.assertEqual(executor.calls[-1]['params'], [7, 8])
        self.assertEqual(getattr(src, '_relationship_cache_key_target'), (7, 8))


class TestActualSchemaContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = ACTUAL_SQL.read_text(encoding='utf-8') if ACTUAL_SQL and ACTUAL_SQL.exists() else ''

    @staticmethod
    def _columns(sql: str, table: str) -> set[str]:
        match = re.search(
            rf'CREATE TABLE public\.{re.escape(table)}\s*\((.*?)\n\);',
            sql,
            flags=re.S,
        )
        if not match:
            raise AssertionError(f'table {table} not found')
        result = set()
        for raw_line in match.group(1).splitlines():
            line = raw_line.strip().rstrip(',')
            if not line or line.upper().startswith(('CONSTRAINT ', 'PRIMARY ', 'UNIQUE ', 'FOREIGN ')):
                continue
            result.add(line.split()[0].strip('"'))
        return result

    def test_relation_serialization_matches_actual_sql_columns(self):
        class A(BaseModel):
            __table__ = 'a'; __table_key__ = 'Naryad.a'; __db_key__ = 'Naryad'; __pk__ = 'id'
            id: int = IntField(primary_key=True, nullable=False)

        class B(BaseModel):
            __table__ = 'b'; __table_key__ = 'Naryad.b'; __db_key__ = 'Naryad'; __pk__ = 'id'
            id: int = IntField(primary_key=True, nullable=False)
            a_id: int = IntField(nullable=False)
            a: A | None = Relationship(
                A,
                relation_key='Naryad.b.a',
                field_pairs=(RelationFieldPair('a_id', 'id', pair_join_type=''),),
                cardinality='many_to_one',
                notes='test',
            )

        spec = B.relation_specs()['a']
        header, pairs = relation_to_admin_records(spec)
        header_columns = (
            self._columns(self.sql, 'admin_table_relations')
            if self.sql else ACTUAL_RELATION_COLUMNS
        )
        pair_columns = (
            self._columns(self.sql, 'admin_relation_field_pairs')
            if self.sql else ACTUAL_RELATION_PAIR_COLUMNS
        )
        self.assertTrue(set(header).issubset(header_columns), set(header) - header_columns)
        self.assertTrue(set(pairs[0]).issubset(pair_columns), set(pairs[0]) - pair_columns)
        self.assertNotIn('shape', header)
        self.assertNotIn('updated_at', pairs[0])


class TestCacheIdentityPolicy(unittest.TestCase):
    def _load_cache_module(self, rows):
        saved = {
            key: sys.modules.get(key)
            for key in ('project_cust_38.Cust_Functions', 'Cust_postgresql_cache')
        }
        fake_f = types.ModuleType('project_cust_38.Cust_Functions')
        fake_f.now = lambda *args, **kwargs: '2026-07-29 12:00:00'
        fake_cpg = types.ModuleType('Cust_postgresql_cache')
        calls = []

        def custom_request_pg(sql, params=None, rez_dict=False, one=False, one_column=False, **kwargs):
            calls.append({'sql': sql, 'params': params})
            if 'FROM admin_physical_tables' in sql:
                return [dict(row) for row in rows]
            if 'FROM admin_request_cache_tables' in sql:
                return []
            return []

        fake_cpg.custom_request_pg = custom_request_pg
        sys.modules['project_cust_38.Cust_Functions'] = fake_f
        sys.modules['Cust_postgresql_cache'] = fake_cpg
        try:
            name = f'_stage1_cache_test_{id(rows)}'
            spec = importlib.util.spec_from_file_location(name, PROJECT / 'srv_sql_cache.py')
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)
            module._test_calls = calls
            return module
        finally:
            for key, value in saved.items():
                if value is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = value

    @staticmethod
    def _row(table_key, db_key):
        return {
            'table_key': table_key,
            'db_key': db_key,
            'table_name': 'naryad',
            'cache_enabled': 1,
            'validity_mark': 'v1',
            'updated_at': '2026-07-29 10:00:00',
            'invalidated_at': None,
            'stale_after_dt': None,
            'cache_lifetime_min': 120,
        }

    def test_single_legacy_alias_is_reused_for_cache_dependency(self):
        module = self._load_cache_module([self._row('db_naryad.naryad', 'db_naryad')])
        cache = module.FileRequestCache(cache_dir=pathlib.Path(tempfile.mkdtemp()))
        policy = cache.compute_policy(table_keys=['Naryad.naryad'])
        self.assertTrue(policy['identity_ok'])
        self.assertTrue(policy['cache_enabled'])
        self.assertEqual(policy['resolved_table_keys'], ['db_naryad.naryad'])
        self.assertTrue(policy['dependency_fingerprint'])

    def test_duplicate_alias_rows_disable_cache_without_update_or_delete(self):
        module = self._load_cache_module([
            self._row('Naryad.naryad', 'Naryad'),
            self._row('db_naryad.naryad', 'db_naryad'),
        ])
        cache = module.FileRequestCache(cache_dir=pathlib.Path(tempfile.mkdtemp()))
        policy = cache.compute_policy(table_keys=['Naryad.naryad'])
        self.assertFalse(policy['identity_ok'])
        self.assertFalse(policy['cache_enabled'])
        self.assertEqual(len(policy['identity_conflicts']), 1)
        sql_text = '\n'.join(call['sql'] for call in module._test_calls)
        self.assertNotRegex(sql_text, r'\b(?:UPDATE|DELETE|INSERT)\b')

    def test_sql_extractor_uses_physical_stem_identity(self):
        module = self._load_cache_module([])
        records = module.extract_query_table_records(
            sql_text='SELECT * FROM naryad',
            main_db_path=r'C:\\DB_srv\\Naryad.db',
        )
        self.assertEqual(records[0]['db_key'], 'Naryad')
        self.assertEqual(records[0]['table_key'], 'Naryad.naryad')

class TestGeneratorFailClosed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = _load_generator_module()
        cls.tables, cls.fields, cls.relations, cls.pairs = _fixture_schema()
        cls.manifest = 'MANIFEST = {}\nARTIFACT_VERSION = "test"\nGENERATED_AT_UTC = "test"'

    def test_default_output_dir_is_project_core_not_srv_shadow(self):
        expected = ROOT / 'project_cust_38' / 'dynamic_db_models'
        self.assertEqual(self.generator._default_output_dir(), expected)
        self.assertFalse((ROOT / 'Srv' / 'project_cust_38').exists())

    def test_legacy_alias_does_not_change_collision_class_name(self):
        tables = [
            {**dict(self.tables[1]), 'table_key': 'db_naryad.status', 'db_key': 'db_naryad', 'table_name': 'status'},
            {**dict(self.tables[1]), 'table_key': 'BD_users.status', 'db_key': 'BD_users', 'table_name': 'status'},
        ]
        names = self.generator._model_name_map(tables)
        self.assertEqual(names['db_naryad.status'], 'NaryadStatus')
        self.assertEqual(names['BD_users.status'], 'BDUsersStatus')

    def test_inconsistent_table_key_db_key_is_rejected(self):
        bad = [{
            **dict(self.tables[1]),
            'table_key': 'BD_users.naryad',
            'db_key': 'Naryad',
            'table_name': 'naryad',
        }]
        with self.assertRaisesRegex(RuntimeError, 'принадлежат разным БД'):
            self.generator._validate_table_identities(bad)

    def test_unsupported_pair_role_is_not_silently_ignored(self):
        pairs = [dict(item) for item in self.pairs]
        pairs[0]['role'] = 'fallback'
        with self.assertRaisesRegex(ValueError, 'role=.*fallback'):
            self.generator._render_orm_models(
                self.tables, self.fields, self.manifest, self.relations, pairs
            )

    def test_unsupported_pair_join_type_is_rejected(self):
        pairs = [dict(item) for item in self.pairs]
        pairs[0]['pair_join_type'] = 'INNER JOIN'
        with self.assertRaisesRegex(ValueError, 'pair_join_type'):
            self.generator._render_orm_models(
                self.tables, self.fields, self.manifest, self.relations, pairs
            )

    def test_many_to_many_is_rejected_until_through_runtime_exists(self):
        relations = [dict(item) for item in self.relations]
        relations[0]['cardinality'] = 'many_to_many'
        with self.assertRaisesRegex(ValueError, 'many_to_many'):
            self.generator._render_orm_models(
                self.tables, self.fields, self.manifest, relations, self.pairs
            )

    def test_relation_name_collision_with_field_is_rejected(self):
        relations = [dict(item) for item in self.relations]
        relations[0]['relation_name'] = 'Номенклатура'
        with self.assertRaisesRegex(ValueError, 'конфликтует'):
            self.generator._render_orm_models(
                self.tables, self.fields, self.manifest, relations, self.pairs
            )

    def test_on_many_list_annotation_matches_runtime_union(self):
        relations = [dict(item) for item in self.relations]
        relations[1]['on_many_policy'] = 'list'
        models = self.generator._render_orm_models(
            self.tables, self.fields, self.manifest, relations, self.pairs
        )
        self.assertIn('mk: Mk | list[Mk] | None = Relationship(', models)
        compile(models, 'orm_models.py', 'exec')


class TestLazyRelationNoDoubleExecution(unittest.TestCase):
    def test_internal_type_error_is_not_retried(self):
        class Target:
            __table__ = 'target'
            __table_key__ = 'Target.target'
            __db_key__ = 'Target'
            __pk__ = 'id'
            calls = 0

            @classmethod
            def pk_name(cls):
                return 'id'

            @classmethod
            def get(cls, pk, *, executor=None):
                cls.calls += 1
                raise TypeError('internal target failure')

        class Source:
            __table__ = 'source'
            __table_key__ = 'Source.source'
            __db_key__ = 'Source'
            target_id = 10
            _executor = object()
            target: Target | None = Relationship(
                Target,
                local_field='target_id',
                remote_field='id',
                cardinality='many_to_one',
            )

        with self.assertRaisesRegex(TypeError, 'internal target failure'):
            _ = Source().target
        self.assertEqual(Target.calls, 1)


class TestImportSafety(unittest.TestCase):
    def test_generator_import_does_not_pull_admin_or_config_graph(self):
        script = f'''
import importlib.util, json, pathlib, sys
root = pathlib.Path({str(ROOT)!r})
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('safe_generator_probe', root / 'Srv' / 'context_schema_generator.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
forbidden = [
    'project_cust_38.context_admin',
    'project_cust_38.Cust_Functions',
    'project_cust_38.Cust_SQLite',
    'project_cust_38.Cust_client_socket',
    'project_cust_38.Cust_config',
]
print(json.dumps([name for name in forbidden if name in sys.modules]))
'''
        output = subprocess.check_output([sys.executable, '-c', script], text=True).strip()
        self.assertEqual(json.loads(output), [])

    def test_db_identity_import_does_not_pull_mes_runtime_graph(self):
        script = (
            "import importlib.util, json, pathlib, sys\n"
            f"path = pathlib.Path({str(PROJECT / 'db_identity.py')!r})\n"
            "before = set(sys.modules)\n"
            "spec = importlib.util.spec_from_file_location('_identity_isolated', path)\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "sys.modules[spec.name] = module\n"
            "spec.loader.exec_module(module)\n"
            "loaded = sorted(set(sys.modules) - before)\n"
            "tokens = ('Cust_config', 'Cust_SQLite', 'Cust_client_socket', 'context_admin', 'CMS', 'PyQt5')\n"
            "forbidden = [name for name in loaded if any(token in name for token in tokens)]\n"
            "print(json.dumps(forbidden))\n"
        )
        proc = subprocess.run(
            [sys.executable, '-I', '-c', script],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(proc.stdout.strip()), [])


class TestCacheFreshnessFailClosed(unittest.TestCase):
    def test_legacy_entry_without_identity_fingerprint_is_stale(self):
        helper = TestCacheIdentityPolicy()
        module = helper._load_cache_module([
            helper._row('db_naryad.naryad', 'db_naryad'),
        ])
        cache = module.FileRequestCache(cache_dir=pathlib.Path(tempfile.mkdtemp()))
        entry = {
            'request_key': 'old',
            'invalidated_at': None,
            'result_state': 'filled',
            'dependency_fingerprint': '',
            'last_refresh_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'cache_lifetime_sec': 7200,
        }
        self.assertFalse(cache.is_entry_fresh(entry))

class TestContextAdminIdentity(unittest.TestCase):
    @staticmethod
    def _load_context_admin(rows):
        module_keys = (
            'project_cust_38.Cust_SQLite',
            'project_cust_38.Cust_Functions',
            'Cust_postgresql_cache',
        )
        saved = {key: sys.modules.get(key) for key in module_keys}
        fake_sql = types.ModuleType('project_cust_38.Cust_SQLite')
        fake_sql.custom_request_c = lambda *args, **kwargs: []
        fake_f = types.ModuleType('project_cust_38.Cust_Functions')
        fake_f.now = lambda *args, **kwargs: '2026-07-29 12:00:00'
        fake_cpg = types.ModuleType('Cust_postgresql_cache')
        calls = []

        def custom_request_pg(sql, params=None, rez_dict=False, one=False, one_column=False, **kwargs):
            calls.append({'sql': sql, 'params': params})
            if 'FROM admin_physical_tables' in sql:
                return [dict(row) for row in rows]
            return []

        fake_cpg.custom_request_pg = custom_request_pg
        sys.modules['project_cust_38.Cust_SQLite'] = fake_sql
        sys.modules['project_cust_38.Cust_Functions'] = fake_f
        sys.modules['Cust_postgresql_cache'] = fake_cpg
        try:
            name = f'_stage1_context_admin_test_{id(rows)}'
            spec = importlib.util.spec_from_file_location(name, PROJECT / 'context_admin.py')
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)
            module._test_calls = calls
            return module
        finally:
            for key, value in saved.items():
                if value is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = value

    def test_one_legacy_identity_is_reused_without_write(self):
        module = self._load_context_admin([
            {'table_key': 'db_naryad.naryad', 'db_key': 'db_naryad', 'table_name': 'naryad'},
        ])
        state = module.ContextAdminRepo().find_registered_table_identity(
            db_key_or_path=r'C:\\DB_srv\\Naryad.db',
            table_name='naryad',
        )
        self.assertEqual(state['row']['table_key'], 'db_naryad.naryad')
        self.assertEqual(state['canonical_table_key'], 'Naryad.naryad')
        sql_text = '\n'.join(call['sql'] for call in module._test_calls)
        self.assertNotRegex(sql_text, r'\b(?:UPDATE|DELETE|INSERT)\b')

    def test_duplicate_alias_identity_raises_without_write(self):
        module = self._load_context_admin([
            {'table_key': 'Naryad.naryad', 'db_key': 'Naryad', 'table_name': 'naryad'},
            {'table_key': 'db_naryad.naryad', 'db_key': 'db_naryad', 'table_name': 'naryad'},
        ])
        with self.assertRaises(module.TableIdentityConflictError):
            module.ContextAdminRepo().find_registered_table_identity(
                db_key_or_path='Naryad', table_name='naryad'
            )
        sql_text = '\n'.join(call['sql'] for call in module._test_calls)
        self.assertNotRegex(sql_text, r'\b(?:UPDATE|DELETE|INSERT)\b')

    def test_malformed_existing_identity_raises(self):
        module = self._load_context_admin([
            {'table_key': 'BD_users.naryad', 'db_key': 'Naryad', 'table_name': 'naryad'},
        ])
        with self.assertRaisesRegex(module.TableIdentityConflictError, 'Неконсистентная'):
            module.ContextAdminRepo().find_registered_table_identity(
                db_key_or_path='Naryad', table_name='naryad'
            )

    def test_relation_metadata_dataclasses_match_actual_schema(self):
        import dataclasses
        module = self._load_context_admin([])
        if ACTUAL_SQL and ACTUAL_SQL.exists():
            sql = ACTUAL_SQL.read_text(encoding='utf-8')
            header_columns = TestActualSchemaContract._columns(sql, 'admin_table_relations')
            pair_columns = TestActualSchemaContract._columns(sql, 'admin_relation_field_pairs')
        else:
            header_columns = ACTUAL_RELATION_COLUMNS
            pair_columns = ACTUAL_RELATION_PAIR_COLUMNS
        header_fields = {field.name for field in dataclasses.fields(module.RelationMeta)}
        pair_fields = {field.name for field in dataclasses.fields(module.RelationFieldPairMeta)}
        self.assertTrue(header_fields.issubset(header_columns), header_fields - header_columns)
        self.assertTrue(pair_fields.issubset(pair_columns), pair_fields - pair_columns)


if __name__ == '__main__':
    unittest.main(verbosity=2)
