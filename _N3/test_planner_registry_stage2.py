import copy
import unittest
from dataclasses import replace

import planner_registry_stage2 as registry


class TestPlannerRegistryStage2(unittest.TestCase):
    def setUp(self):
        self.catalog = registry.build_demo_catalog()
        self.configs = registry.build_demo_configurations()
        self.repository = registry.InMemoryPlannerRegistryRepository(self.configs)
        self.service = registry.PlannerRegistryService(self.catalog, self.repository)

    def test_demo_vertical_slice_is_valid(self):
        for config in self.configs:
            self.service.validator.validate(config)
        self.assertEqual(
            [item.source.source_key for item in self.service.list_configs("gant")],
            ["gant.resource.podrazdel", "gant.event.mk"],
        )

    def test_registered_relation_resolves_id_to_text(self):
        event = self.service.get_config("gant.event.mk")
        presentation = next(item for item in event.presentations if item.relation_steps)
        value = registry.PlannerPresentationResolver(self.catalog).resolve(
            "Naryad.mk",
            {"Пномер": 6476, "Тип": 1},
            presentation,
            {
                "Naryad.Тип_мк": [
                    {"Пномер": 1, "Имя": "Плановая"},
                    {"Пномер": 2, "Имя": "Дорезка"},
                ]
            },
        )
        self.assertEqual(value, "Плановая")

    def test_direct_presentation_reads_same_row(self):
        event = self.service.get_config("gant.event.mk")
        presentation = next(item for item in event.presentations if item.is_default)
        value = registry.PlannerPresentationResolver(self.catalog).resolve(
            "Naryad.mk",
            {"Пномер": 6476, "Номенклатура": "КТ.741136.003 Шильда"},
            presentation,
            {},
        )
        self.assertEqual(value, "КТ.741136.003 Шильда")

    def test_missing_relation_can_return_none(self):
        event = self.service.get_config("gant.event.mk")
        presentation = next(item for item in event.presentations if item.relation_steps)
        value = registry.PlannerPresentationResolver(self.catalog).resolve(
            "Naryad.mk",
            {"Пномер": 6476, "Тип": 999},
            presentation,
            {"Naryad.Тип_мк": [{"Пномер": 1, "Имя": "Плановая"}]},
        )
        self.assertIsNone(value)

    def test_missing_relation_error_is_explicit(self):
        event = self.service.get_config("gant.event.mk")
        presentation = replace(
            next(item for item in event.presentations if item.relation_steps),
            missing_policy="error",
        )
        with self.assertRaisesRegex(registry.PlannerValidationError, "не найдена"):
            registry.PlannerPresentationResolver(self.catalog).resolve(
                "Naryad.mk",
                {"Пномер": 6476, "Тип": 999},
                presentation,
                {"Naryad.Тип_мк": []},
            )

    def test_multiple_relation_rows_never_multiply_source(self):
        event = self.service.get_config("gant.event.mk")
        presentation = next(item for item in event.presentations if item.relation_steps)
        with self.assertRaisesRegex(registry.PlannerValidationError, "2 строк"):
            registry.PlannerPresentationResolver(self.catalog).resolve(
                "Naryad.mk",
                {"Пномер": 6476, "Тип": 1},
                presentation,
                {
                    "Naryad.Тип_мк": [
                        {"Пномер": 1, "Имя": "Плановая"},
                        {"Пномер": 1, "Имя": "Дубликат"},
                    ]
                },
            )

    def test_one_to_many_scalar_presentation_is_rejected(self):
        relations = dict(self.catalog.relations)
        relation = relations["Naryad.mk.type"]
        relations[relation.relation_key] = replace(relation, cardinality="one_to_many")
        catalog = replace(self.catalog, relations=relations)
        service = registry.PlannerRegistryService(catalog, self.repository)
        event = self.service.get_config("gant.event.mk")
        with self.assertRaisesRegex(registry.PlannerValidationError, "скалярное представление запрещено"):
            service.save_config(event)

    def test_second_default_presentation_is_rejected(self):
        event = self.service.get_config("gant.event.mk")
        presentations = tuple(replace(item, is_default=True) for item in event.presentations)
        with self.assertRaisesRegex(registry.PlannerValidationError, "только одно"):
            self.service.save_config(replace(event, presentations=presentations))

    def test_resource_requires_default_presentation(self):
        resource = self.service.get_config("gant.resource.podrazdel")
        with self.assertRaisesRegex(registry.PlannerValidationError, "представление по умолчанию"):
            self.service.save_config(replace(resource, presentations=()))

    def test_invalid_save_does_not_change_repository(self):
        before = copy.deepcopy(self.service.list_configs("gant"))
        event = self.service.get_config("gant.event.mk")
        invalid = replace(event, roles=())
        with self.assertRaises(registry.PlannerValidationError):
            self.service.save_config(invalid)
        self.assertEqual(self.service.list_configs("gant"), before)

    def test_repository_returns_copies(self):
        first = self.repository.list_configs()
        first.clear()
        self.assertEqual(len(self.repository.list_configs()), 2)

    def test_same_table_cannot_be_registered_twice(self):
        event = self.service.get_config("gant.event.mk")
        duplicate = replace(
            event,
            source=replace(event.source, source_key="gant.event.mk.duplicate"),
            requisites=tuple(
                replace(item, source_key="gant.event.mk.duplicate")
                for item in event.requisites
            ),
            presentations=tuple(
                replace(item, source_key="gant.event.mk.duplicate")
                for item in event.presentations
            ),
        )
        with self.assertRaisesRegex(registry.PlannerValidationError, "уже зарегистрирована"):
            self.service.save_config(duplicate)

    def test_string_enums_are_normalized_before_repository_write(self):
        class CapturingRepository(registry.InMemoryPlannerRegistryRepository):
            saved = None

            def replace_configs(self, configs):
                configs = tuple(configs)
                self.saved = configs[0]
                super().replace_configs(configs)

        repository = CapturingRepository()
        service = registry.PlannerRegistryService(self.catalog, repository)
        resource = self.service.get_config("gant.resource.podrazdel")
        config = replace(
            resource,
            roles=("resource",),
            requisites=tuple(
                replace(item, semantic_role=item.semantic_role.value)
                for item in resource.requisites
            ),
        )
        service.save_config(config)
        self.assertIs(repository.saved.roles[0], registry.SourceRole.RESOURCE)
        self.assertIs(
            repository.saved.requisites[0].semantic_role,
            registry.SemanticRole.LABEL,
        )

    def test_qmark_converter_ignores_quoted_question_marks(self):
        sql = registry._qmark_to_percent(
            "SELECT '?', \"?\" FROM planner_sources WHERE source_key = ? AND caption = ?"
        )
        self.assertEqual(
            sql,
            "SELECT '?', \"?\" FROM planner_sources WHERE source_key = %s AND caption = %s",
        )

    def test_catalog_adapter_uses_existing_read_api(self):
        class FakeContextAdminRepo:
            def get_physical_tables(self):
                return [
                    {
                        "table_key": "Demo.items",
                        "db_key": "Demo",
                        "table_name": "items",
                    }
                ]

            def get_table_fields(self):
                return [
                    {
                        "table_key": "Demo.items",
                        "field_name": "id",
                        "is_pk": 1,
                    }
                ]

            def get_relations(self):
                return []

            def get_relation_field_pairs(self):
                return []

        catalog = registry.ContextAdminCatalogAdapter(FakeContextAdminRepo()).load()
        self.assertIn("Demo.items", catalog.tables)
        self.assertIn(("Demo.items", "id"), catalog.fields)

    def test_orphan_relation_pair_fails_closed(self):
        with self.assertRaisesRegex(registry.PlannerCatalogError, "без заголовка"):
            registry.AdminCatalog.from_rows(
                [{"table_key": "A.a", "db_key": "A", "table_name": "a"}],
                [{"table_key": "A.a", "field_name": "id", "is_pk": 1}],
                [],
                [
                    {
                        "relation_key": "missing",
                        "left_table_key": "A.a",
                        "left_field_name": "id",
                        "right_table_key": "A.a",
                        "right_field_name": "id",
                    }
                ],
            )

    def test_relation_pair_direction_mismatch_fails_closed(self):
        with self.assertRaisesRegex(registry.PlannerCatalogError, "направлением связи"):
            registry.AdminCatalog.from_rows(
                [
                    {"table_key": "A.a", "db_key": "A", "table_name": "a"},
                    {"table_key": "B.b", "db_key": "B", "table_name": "b"},
                ],
                [
                    {"table_key": "A.a", "field_name": "id", "is_pk": 1},
                    {"table_key": "B.b", "field_name": "id", "is_pk": 1},
                ],
                [
                    {
                        "relation_key": "A.a.b",
                        "relation_name": "B",
                        "source_table_key": "A.a",
                        "target_table_key": "B.b",
                    }
                ],
                [
                    {
                        "relation_key": "A.a.b",
                        "left_table_key": "B.b",
                        "left_field_name": "id",
                        "right_table_key": "A.a",
                        "right_field_name": "id",
                    }
                ],
            )

    def test_transactional_executor_converts_rows_and_placeholders(self):
        class Cursor:
            description = (("source_key",), ("caption",))

            def __init__(self):
                self.sql = None
                self.params = None
                self.closed = False

            def execute(self, sql, params):
                self.sql = sql
                self.params = params

            def fetchone(self):
                return ("gant.demo", "Демо")

            def fetchall(self):
                return [("gant.demo", "Демо")]

            def close(self):
                self.closed = True

        class Connection:
            def __init__(self):
                self.last_cursor = None

            def cursor(self):
                self.last_cursor = Cursor()
                return self.last_cursor

        connection = Connection()
        executor = registry.TransactionalPostgresExecutor(connection)
        row = executor.execute(
            "ignored",
            "SELECT source_key, caption FROM planner_sources WHERE source_key = ?",
            params=["gant.demo"],
            rez_dict=True,
            one=True,
        )
        self.assertEqual(row, {"source_key": "gant.demo", "caption": "Демо"})
        self.assertIn("source_key = %s", connection.last_cursor.sql)
        self.assertEqual(connection.last_cursor.params, ["gant.demo"])
        self.assertTrue(connection.last_cursor.closed)

    def test_migration_contains_required_integrity_guards(self):
        sql = registry.POSTGRES_MIGRATION_SQL
        self.assertIn("CREATE SCHEMA IF NOT EXISTS planner", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS planner.planner_sources", sql)
        self.assertIn("REFERENCES public.admin_physical_tables", sql)
        self.assertIn("REFERENCES public.admin_table_fields", sql)
        self.assertIn("REFERENCES public.admin_table_relations", sql)
        self.assertIn("ON DELETE CASCADE", sql)
        self.assertIn("role IN ('resource', 'event', 'attribute')", sql)
        self.assertIn("uq_planner_presentations_default", sql)

    def test_batch_validation_is_atomic_in_memory(self):
        before = self.service.list_configs()
        resource = self.service.get_config("gant.resource.podrazdel")
        event = self.service.get_config("gant.event.mk")
        invalid_event = replace(event, roles=())

        with self.assertRaises(registry.PlannerValidationError):
            self.service.save_configs((resource, invalid_event))

        self.assertEqual(self.service.list_configs(), before)

    def test_read_transaction_ends_with_rollback(self):
        class Connection:
            autocommit = True

            def __init__(self):
                self.commits = 0
                self.rollbacks = 0
                self.closed = 0

            def commit(self):
                self.commits += 1

            def rollback(self):
                self.rollbacks += 1

            def close(self):
                self.closed += 1

        connection = Connection()
        repository = object.__new__(registry.CustOrmPlannerRegistryRepository)
        repository.connection_factory = lambda: connection
        repository.close_connection = True

        with repository._transaction(write=False):
            pass

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.closed, 1)

    def test_failed_commit_is_not_retried_or_reported_as_rollback(self):
        class Connection:
            autocommit = False

            def __init__(self):
                self.commits = 0
                self.rollbacks = 0
                self.closed = 0

            def commit(self):
                self.commits += 1
                raise OSError("соединение потеряно во время COMMIT")

            def rollback(self):
                self.rollbacks += 1

            def close(self):
                self.closed += 1

        connection = Connection()
        repository = object.__new__(registry.CustOrmPlannerRegistryRepository)
        repository.connection_factory = lambda: connection
        repository.close_connection = True

        with self.assertRaises(registry.PlannerCommitOutcomeUnknown):
            with repository._transaction(write=True):
                pass

        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertEqual(connection.closed, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
