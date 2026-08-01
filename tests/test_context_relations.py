# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from context_relations import (
    MissingPolicy,
    RelationCardinality,
    RelationFieldPair,
    RelationShape,
    RelationSpec,
    Relationship,
    SQLRelationCompiler,
    field_db_column,
    field_name,
    relation_from_admin_records,
    relation_to_admin_records,
    resolve_field_ref,
)


class FakeField:
    def __init__(self, db_column=None, default=None, primary_key=False):
        self.name = None
        self.model = None
        self.db_column = db_column
        self.default = default
        self.primary_key = primary_key

    def __set_name__(self, owner, name):
        self.name = name
        self.model = owner
        if self.db_column is None:
            self.db_column = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name, self.default)

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value


class FakeModelMeta(type):
    def __new__(mcls, name, bases, ns):
        cls = super().__new__(mcls, name, bases, ns)
        fields = {}
        for key, value in cls.__dict__.items():
            if isinstance(value, FakeField):
                fields[key] = value
        cls.__fields__ = fields
        cls.__field_by_column__ = {field.db_column: key for key, field in fields.items()}
        if not hasattr(cls, '__relations__'):
            cls.__relations__ = {}
        return cls


class FakeModel(metaclass=FakeModelMeta):
    __table__ = ''
    __table_key__ = ''
    __pk__ = 'id'

    @classmethod
    def pk_name(cls):
        return cls.__pk__


class Mk(FakeModel):
    __table__ = 'mk'
    __table_key__ = 'db_naryad.mk'
    __pk__ = 'Пномер'

    Пномер = FakeField(primary_key=True)
    Номенклатура = FakeField(db_column='Номенклатура')
    Статус = FakeField(db_column='status_col')

    _store = {
        10: {'Пномер': 10, 'Номенклатура': 'Изделие', 'status_col': 'В работе'},
    }

    @classmethod
    def get(cls, pk, **kwargs):
        row = cls._store.get(pk)
        if row is None:
            return None
        obj = cls()
        for py_name, field in cls.__fields__.items():
            setattr(obj, py_name, row.get(field.db_column, row.get(py_name)))
        return obj


class Naryad(FakeModel):
    __table__ = 'naryad'
    __table_key__ = 'db_naryad.naryad'
    __pk__ = 'Пномер'

    Пномер = FakeField(primary_key=True)
    Номер_мк = FakeField(db_column='mk_id')

    mk: Mk | None = Relationship(
        Mk,
        local_field=Номер_мк,
        remote_field=Mk.Пномер,
        cardinality='many_to_one',
        missing='none',
    )


class Parent(FakeModel):
    __table__ = 'parent'
    __table_key__ = 'db.parent'
    id = FakeField(primary_key=True)


class Child(FakeModel):
    __table__ = 'child'
    __table_key__ = 'db.child'
    id = FakeField(primary_key=True)
    parent_id = FakeField()


class ParentWithChildren(Parent):
    children: list[Child] = Relationship(
        Child,
        local_field=Parent.id,
        remote_field=Child.parent_id,
    )


class TestFieldLikeRelations(unittest.TestCase):
    def test_field_ref_reads_orm_field_names_and_db_columns(self):
        ref = resolve_field_ref(Naryad.Номер_мк)
        self.assertEqual(ref.field_name, 'Номер_мк')
        self.assertEqual(ref.db_column, 'mk_id')
        self.assertEqual(ref.table_key, 'db_naryad.naryad')
        self.assertEqual(field_name(Mk.Статус), 'Статус')
        self.assertEqual(field_db_column(Mk.Статус), 'status_col')

    def test_relationship_descriptor_infers_one_optional_and_loads_object(self):
        relation = Naryad.mk
        spec = relation.as_relation_spec(Naryad)
        self.assertEqual(spec.shape, RelationShape.ONE.value)
        self.assertEqual(spec.cardinality, RelationCardinality.MANY_TO_ONE.value)
        self.assertEqual(spec.missing_policy, MissingPolicy.NONE.value)
        naryad = Naryad()
        naryad.Номер_мк = 10
        self.assertEqual(naryad.mk.Номенклатура, 'Изделие')

    def test_relationship_descriptor_infers_many_collection_from_list_annotation(self):
        rel = ParentWithChildren.children
        spec = rel.as_relation_spec(ParentWithChildren)
        self.assertEqual(spec.shape, RelationShape.MANY.value)
        self.assertEqual(spec.missing_policy, MissingPolicy.EMPTY.value)
        self.assertEqual(spec.cardinality, RelationCardinality.ONE_TO_MANY.value)

    def test_relation_spec_accepts_field_pairs_and_admin_records(self):
        spec = RelationSpec(
            relation_key='db_naryad.naryad.mk',
            relation_name='mk',
            source_table=Naryad,
            target_table=Mk,
            field_pairs=(RelationFieldPair(Naryad.Номер_мк, Mk.Пномер),),
            cardinality='many_to_one',
            missing_policy='none',
            select_fields=(Mk.Номенклатура, Mk.Статус),
            select_prefix='МК',
        ).normalized()
        header, pairs = relation_to_admin_records(spec)
        self.assertEqual(header['source_table_key'], 'db_naryad.naryad')
        self.assertEqual(pairs[0]['left_field_name'], 'mk_id')
        restored = relation_from_admin_records(header, pairs)
        self.assertEqual(restored.relation_key, spec.relation_key)
        self.assertEqual(restored.field_pairs[0].left_field, 'mk_id')

    def test_sql_compiler_uses_db_columns_but_outputs_python_field_names(self):
        spec = RelationSpec(
            relation_key='db_naryad.naryad.mk',
            relation_name='mk',
            source_table=Naryad,
            target_table=Mk,
            field_pairs=(RelationFieldPair(Naryad.Номер_мк, Mk.Пномер),),
            select_fields=(Mk.Номенклатура, Mk.Статус),
            select_prefix='МК',
        )
        plan = SQLRelationCompiler().compile_select(
            source_model=Naryad,
            source_fields=(Naryad.Пномер, Naryad.Номер_мк),
            relations=(spec,),
        )
        self.assertIn('src."mk_id" AS "Номер_мк"', plan.sql)
        self.assertIn('mk."Пномер" = src."mk_id"', plan.sql)
        self.assertIn('mk."status_col" AS "МК.Статус"', plan.sql)


if __name__ == '__main__':
    unittest.main(verbosity=2)
