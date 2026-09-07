# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from context_relations_stage import (
    EnrichmentStage,
    JoinType,
    OnMany,
    Cardinality,
    RelationCardinalityError,
    RelationError,
    RelationRef,
    RelationRegistry,
    RelationSpec,
    RegisterStageSpec,
    Relationship,
    SQLRelationCompiler,
    relation_from_state_field,
)


EVENT_ROWS = [
    {
        'ФизическоеЛицо_Key': 'emp-1',
        'Период': '2026-01-01T08:00:00',
        'Событие': 'Прием',
        'Должность_Key': 'pos-1',
    },
    {
        'ФизическоеЛицо_Key': 'emp-2',
        'Период': '2026-01-02T08:00:00',
        'Событие': 'Прием',
        'Должность_Key': 'pos-missing',
    },
]

POSITION_ROWS = [
    {'Ref_Key': 'pos-1', 'Наименование': 'Сварщик', 'Разряд': 4},
]


def make_registry(join_type: str = JoinType.LEFT.value) -> RelationRegistry:
    return RelationRegistry([
        RelationSpec(
            name='employee_position',
            local_field='Должность_Key',
            remote_field='Ref_Key',
            target_table='Должности',
            target_db='SRV:BD_users.db',
            join_type=join_type,
            select_fields=('Наименование', 'Разряд'),
            select_prefix='Должность',
        )
    ])


class TestRelationStage(unittest.TestCase):
    def test_left_enrichment_keeps_missing_with_none_fields(self):
        stage = EnrichmentStage(make_registry())
        rows = stage.apply(
            EVENT_ROWS,
            RegisterStageSpec(code='СостояниеСотрудникаНаПериод', relation_refs=('employee_position',)),
            right_data={'employee_position': POSITION_ROWS},
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['Должность.Наименование'], 'Сварщик')
        self.assertEqual(rows[0]['Должность.Разряд'], 4)
        self.assertIsNone(rows[1]['Должность.Наименование'])
        self.assertIsNone(rows[1]['Должность.Разряд'])

    def test_inner_enrichment_skips_missing(self):
        stage = EnrichmentStage(make_registry(join_type=JoinType.INNER.value))
        rows = stage.apply(
            EVENT_ROWS,
            RegisterStageSpec(code='СостояниеСотрудникаНаПериод', relation_refs=('employee_position',)),
            right_data={'employee_position': POSITION_ROWS},
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ФизическоеЛицо_Key'], 'emp-1')

    def test_cardinality_one_raises_on_duplicate_right_rows(self):
        stage = EnrichmentStage(make_registry())
        duplicated_positions = [
            {'Ref_Key': 'pos-1', 'Наименование': 'Сварщик 1', 'Разряд': 4},
            {'Ref_Key': 'pos-1', 'Наименование': 'Сварщик 2', 'Разряд': 5},
        ]
        with self.assertRaises(RelationCardinalityError):
            stage.apply(
                EVENT_ROWS[:1],
                RegisterStageSpec(code='x', relation_refs=('employee_position',)),
                right_data={'employee_position': duplicated_positions},
            )

    def test_cardinality_one_can_take_last_for_dirty_reference_data(self):
        registry = RelationRegistry([
            RelationSpec(
                name='employee_position',
                local_field='Должность_Key',
                remote_field='Ref_Key',
                target_table='Должности',
                select_fields=('Наименование',),
                select_prefix='Должность',
                on_many=OnMany.LAST.value,
            )
        ])
        stage = EnrichmentStage(registry)
        rows = stage.apply(
            EVENT_ROWS[:1],
            RegisterStageSpec(code='x', relation_refs=('employee_position',)),
            right_data={'employee_position': [
                {'Ref_Key': 'pos-1', 'Наименование': 'Старое имя'},
                {'Ref_Key': 'pos-1', 'Наименование': 'Новое имя'},
            ]},
        )
        self.assertEqual(rows[0]['Должность.Наименование'], 'Новое имя')

    def test_many_relation_returns_list_without_multiplying_register_rows(self):
        registry = RelationRegistry([
            RelationSpec(
                name='employee_skills',
                local_field='ФизическоеЛицо_Key',
                remote_field='employee_ref',
                target_table='skills',
                cardinality=Cardinality.MANY.value,
                select_fields=('skill',),
                select_prefix='Навыки',
            )
        ])
        stage = EnrichmentStage(registry)
        rows = stage.apply(
            EVENT_ROWS[:1],
            RegisterStageSpec(code='x', relation_refs=('employee_skills',)),
            right_data={'employee_skills': [
                {'employee_ref': 'emp-1', 'skill': 'MIG'},
                {'employee_ref': 'emp-1', 'skill': 'TIG'},
            ]},
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Навыки[]'], [{'skill': 'MIG'}, {'skill': 'TIG'}])

    def test_relation_ref_can_override_fields_and_prefix(self):
        stage = EnrichmentStage(make_registry())
        rows = stage.apply(
            EVENT_ROWS[:1],
            RegisterStageSpec(
                code='x',
                relation_refs=(RelationRef('employee_position', fields=('Наименование',), prefix='Позиция'),),
            ),
            right_data={'employee_position': POSITION_ROWS},
        )
        self.assertEqual(rows[0]['Позиция.Наименование'], 'Сварщик')
        self.assertNotIn('Позиция.Разряд', rows[0])

    def test_full_join_is_rejected_for_stage_relation(self):
        with self.assertRaises(RelationError):
            RelationSpec(
                name='bad_full_join',
                local_field='x',
                remote_field='id',
                target_table='y',
                join_type='FULL JOIN',
                select_fields=('name',),
            ).normalized()

    def test_sql_compiler_generates_safe_left_join_plan(self):
        compiler = SQLRelationCompiler(make_registry())
        plan = compiler.compile_select(
            source_table='КадроваяИстория',
            source_db='SRV:BD_users.db',
            source_fields=('ФизическоеЛицо_Key', 'Период', 'Должность_Key'),
            relations=('employee_position',),
            order_by_sql='src."Период"',
        )
        self.assertIn('FROM "КадроваяИстория" AS src', plan.sql)
        self.assertIn('LEFT JOIN "Должности" AS employee_position', plan.sql)
        self.assertIn('employee_position."Ref_Key" = src."Должность_Key"', plan.sql)
        self.assertIn('employee_position."Наименование" AS "Должность.Наименование"', plan.sql)
        self.assertEqual(plan.dependency_table_keys, ('BD_users.Должности',))

    def test_legacy_state_field_dict_can_be_converted_to_relation(self):
        relation = relation_from_state_field({
            'field_name': 'Организация_Key',
            'db_name': 'SRV:Naryad.db',
            'join_table': 'places',
            'field_for_join': 'Организация_Key',
            'join_mode': 'only',
            'select_fields': ('Имя',),
            'select_prefix': 'Организация',
        })
        self.assertIsNotNone(relation)
        self.assertEqual(relation.local_field, 'Организация_Key')
        self.assertEqual(relation.remote_field, 'Организация_Key')
        self.assertEqual(relation.target_table, 'places')
        self.assertEqual(relation.select_fields, ('Имя',))


class TestRelationshipDescriptor(unittest.TestCase):
    def test_lazy_relationship_uses_loader_and_cache(self):
        calls = []
        mk_store = {
            10: {'Пномер': 10, 'Статус': 'В работе'},
        }

        def load_mk(instance, local_value, descriptor):
            calls.append((instance, local_value, descriptor.name))
            return mk_store.get(local_value)

        class NaryadLike:
            mk = Relationship(local_field='Номер_мк', loader=load_mk)

            def __init__(self, mk_id):
                self.Номер_мк = mk_id

        naryad = NaryadLike(10)
        self.assertEqual(naryad.mk, {'Пномер': 10, 'Статус': 'В работе'})
        self.assertEqual(naryad.mk, {'Пномер': 10, 'Статус': 'В работе'})
        self.assertEqual(len(calls), 1, 'второе обращение должно взять объект из cache')

        naryad.Номер_мк = 0
        self.assertIsNone(naryad.mk)


if __name__ == '__main__':
    unittest.main(verbosity=2)
