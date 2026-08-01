# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import types
import unittest

import context_relations as _context_relations

_fake_f = types.ModuleType('Cust_Functions')
_fake_f.now = lambda *args, **kwargs: '2026-01-01 00:00:00'
_fake_f.is_date = lambda *args, **kwargs: False
_fake_f.strtodate = lambda value, *args, **kwargs: __import__('datetime').datetime.fromisoformat(str(value).replace(' ', 'T'))
_fake_f.scfg = lambda *args, **kwargs: ''
sys.modules.setdefault('Cust_Functions', _fake_f)

_fake_sql = types.ModuleType('Cust_SQLite')
_fake_sql.custom_request_c = lambda *args, **kwargs: []
sys.modules.setdefault('Cust_SQLite', _fake_sql)

_fake_orm = types.ModuleType('Cust_orm')
_fake_orm.SmartList = list
sys.modules.setdefault('Cust_orm', _fake_orm)

from context_registers import RegisterSpec, Registers
from context_relations import RelationFieldPair, RelationRef, RelationRegistry, RelationSpec
from test_context_relations import Mk, Naryad


class TestRegisterFinalStage(unittest.TestCase):
    def make_registry(self):
        relation = RelationSpec(
            relation_key='db_naryad.naryad.mk',
            relation_name='mk',
            source_table=Naryad,
            target_table=Mk,
            field_pairs=(RelationFieldPair(Naryad.Номер_мк, Mk.Пномер),),
            select_fields=(Mk.Номенклатура, Mk.Статус),
            select_prefix='МК',
        )
        return RelationRegistry([relation])

    def test_register_spec_serializes_relation_refs(self):
        spec = RegisterSpec(
            code='НарядПоМК',
            title='Наряд по МК',
            source_model=Naryad,
            source_table='naryad',
            entity_fields=(Naryad.Пномер,),
            period_field='Дата',
            state_fields=(Naryad.Номер_мк,),
            relation_refs=(RelationRef('db_naryad.naryad.mk', fields=(Mk.Статус,), prefix='МК'),),
        )
        record = spec.to_record()
        restored = RegisterSpec.from_record(record)
        self.assertIn('relation_refs_json', record)
        self.assertEqual(restored.relation_refs[0].name, 'db_naryad.naryad.mk')
        self.assertEqual(restored.relation_refs[0].fields, ('Статус',))

    def test_register_sql_compiles_relation_refs_and_orm_db_columns(self):
        spec = RegisterSpec(
            code='НарядПоМК',
            title='Наряд по МК',
            source_db='SRV:Naryad.db',
            source_model=Naryad,
            source_table='naryad',
            entity_fields=(Naryad.Пномер,),
            period_field=Naryad.Пномер,
            state_fields=(Naryad.Номер_мк,),
            relation_refs=(RelationRef('db_naryad.naryad.mk', fields=(Mk.Статус,), prefix='МК'),),
        )
        registers = Registers(repo=None, relation_registry=self.make_registry(), declared_specs=())
        sql_state = registers.make_sql_by_spec(spec)
        self.assertIn('src."mk_id" AS "Номер_мк"', sql_state.select)
        self.assertIn('mk."Пномер" = src."mk_id"', sql_state.join)
        self.assertIn('mk."status_col" AS "МК.Статус"', sql_state.select)

    def test_register_runtime_keeps_relation_enrichment_fields(self):
        spec = RegisterSpec(
            code='НарядПоМК',
            title='Наряд по МК',
            entity_fields=('Пномер',),
            period_field='Дата',
            state_fields=('Номер_мк',),
            relation_refs=('db_naryad.naryad.mk',),
        )
        rows = [
            {'Пномер': 1, 'Дата': '2026-01-01 10:00:00', 'Номер_мк': 10, 'МК.Статус': 'В работе'},
            {'Пномер': 1, 'Дата': '2026-01-02 10:00:00', 'Номер_мк': 10, 'МК.Статус': 'Закрыта'},
        ]
        resolved = Registers(repo=None, declared_specs=()).state_at(spec, rows=rows)
        self.assertEqual(resolved[0]['МК.Статус'], 'Закрыта')

    def test_custom_fetch_rows_can_be_enriched_in_memory(self):
        spec = RegisterSpec(
            code='НарядПоМК',
            title='Наряд по МК',
            entity_fields=('Пномер',),
            period_field='Дата',
            state_fields=('Номер_мк',),
            relation_refs=(RelationRef('db_naryad.naryad.mk', fields=(Mk.Номенклатура,), prefix='МК'),),
        )
        rows = [{'Пномер': 1, 'Дата': '2026-01-01 10:00:00', 'Номер_мк': 10}]
        right_data = {'db_naryad.naryad.mk': [{'Пномер': 10, 'Номенклатура': 'Изделие'}]}
        registers = Registers(
            repo=None,
            declared_specs=(),
            relation_registry=self.make_registry(),
            relation_right_data=right_data,
        )
        resolved = registers.state_at(spec, rows=rows)
        self.assertEqual(resolved[0]['МК.Номенклатура'], 'Изделие')


if __name__ == '__main__':
    unittest.main(verbosity=2)
