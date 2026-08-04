import unittest
from dataclasses import replace

import planner_registry_stage2 as registry
import planner_registry_runtime_stage2 as runtime


class _Status:
    name = "IDLE"


class _Info:
    transaction_status = _Status()


class _ProbeCursor:
    description = (("value",),)

    def __init__(self):
        self.closed = False
        self.sql = []

    def execute(self, sql):
        self.sql.append(sql)

    def fetchone(self):
        return (1,)

    def close(self):
        self.closed = True


class _ProbeConnection:
    autocommit = False
    info = _Info()

    def __init__(self):
        self.cursor_obj = _ProbeCursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


class _FakePool:
    created = []

    @staticmethod
    def check_connection(connection):
        return None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.opened = False
        self.closed = False
        self.put_count = 0
        self.connections = []
        type(self).created.append(self)

    def open(self):
        self.opened = True

    def close(self):
        self.closed = True

    def getconn(self, timeout=None):
        connection = _ProbeConnection()
        self.connections.append(connection)
        return connection

    def putconn(self, connection):
        self.put_count += 1

    def get_stats(self):
        return {"pool_max": self.kwargs["max_size"], "returns": self.put_count}


class _Column:
    def __init__(self, name):
        self.name = name


class _CatalogCursor:
    def __init__(self, rows_by_table, fail=None):
        self.rows_by_table = rows_by_table
        self.fail = fail
        self.description = None
        self.current_rows = []
        self.sql = []
        self.closed = False

    def execute(self, sql):
        self.sql.append(sql)
        if self.fail is not None:
            error = self.fail
            self.fail = None
            raise error
        if sql.startswith("SET TRANSACTION"):
            self.description = None
            self.current_rows = []
            return
        for table_name, rows in self.rows_by_table.items():
            if table_name in sql:
                self.current_rows = rows
                names = tuple(rows[0].keys()) if rows else ()
                self.description = tuple(_Column(name) for name in names)
                return
        raise AssertionError(sql)

    def fetchall(self):
        if not self.current_rows:
            return []
        names = [item.name for item in self.description]
        return [tuple(row[name] for name in names) for row in self.current_rows]

    def close(self):
        self.closed = True


class _CatalogConnection:
    autocommit = True

    def __init__(self, rows_by_table, fail=None):
        self.cursor_obj = _CatalogCursor(rows_by_table, fail=fail)
        self.rollbacks = 0
        self.closed = 0

    def cursor(self):
        return self.cursor_obj

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


def _catalog_rows():
    return {
        "admin_physical_tables": [
            {
                "table_key": "Demo.items",
                "db_key": "Demo",
                "table_name": "items",
                "is_enabled": 1,
                "schema_enabled": 1,
            }
        ],
        "admin_table_fields": [
            {
                "table_key": "Demo.items",
                "field_name": "id",
                "is_pk": 1,
                "include_in_schema": 1,
            }
        ],
        "admin_table_relations": [],
        "admin_relation_field_pairs": [],
    }


class TestPlannerRegistryRuntimeStage2(unittest.TestCase):
    def setUp(self):
        _FakePool.created.clear()

    def test_pool_is_explicitly_bounded_and_returns_lease_once(self):
        settings = runtime.PlannerPoolSettings(
            min_size=0,
            max_size=3,
            max_waiting=5,
            acquire_timeout_sec=2,
            max_idle_sec=30,
            max_lifetime_sec=300,
        )
        pool = runtime.PsycopgPlannerPool(
            "postgresql://example",
            settings,
            pool_class=_FakePool,
        )
        pool.open()
        created = _FakePool.created[-1]
        self.assertFalse(created.kwargs["open"])
        self.assertEqual(created.kwargs["min_size"], 0)
        self.assertEqual(created.kwargs["max_size"], 3)
        self.assertEqual(created.kwargs["max_waiting"], 5)
        self.assertEqual(created.kwargs["timeout"], 2)
        self.assertIn("check", created.kwargs)

        lease = pool.get_connection()
        lease.close()
        lease.close()
        self.assertEqual(created.put_count, 2)
        self.assertEqual(pool.stats()["pool_max"], 3)
        pool.close()
        self.assertTrue(created.closed)

    def test_pool_rejects_unbounded_waiting_queue(self):
        with self.assertRaisesRegex(runtime.PlannerPoolError, "max_waiting"):
            runtime.PlannerPoolSettings(max_waiting=0).validate()

    def test_callable_conninfo_is_deferred_when_pool_supports_it(self):
        class CallableConninfoPool(_FakePool):
            _planner_supports_callable_conninfo = True

        calls = []

        def provide_conninfo():
            calls.append(len(calls) + 1)
            return f"postgresql://example/db{len(calls)}"

        pool = runtime.PsycopgPlannerPool(
            provide_conninfo,
            pool_class=CallableConninfoPool,
        )
        pool.open(verify=False)
        created = CallableConninfoPool.created[-1]
        forwarded = created.kwargs["conninfo"]

        self.assertTrue(callable(forwarded))
        self.assertEqual(calls, [])
        self.assertEqual(forwarded(), "postgresql://example/db1")
        self.assertEqual(forwarded(), "postgresql://example/db2")
        pool.close()

    def test_callable_conninfo_is_resolved_once_for_legacy_pool(self):
        calls = []

        def provide_conninfo():
            calls.append(True)
            return "postgresql://example/legacy"

        pool = runtime.PsycopgPlannerPool(
            provide_conninfo,
            pool_class=_FakePool,
        )
        pool.open(verify=False)
        created = _FakePool.created[-1]

        self.assertEqual(calls, [True])
        self.assertEqual(
            created.kwargs["conninfo"],
            "postgresql://example/legacy",
        )
        pool.close()

    def test_legacy_checkout_discards_failed_connection_before_retry(self):
        class FailingCursor(_ProbeCursor):
            def execute(self, sql):
                raise OSError("connection lost")

        class FailingConnection(_ProbeConnection):
            def __init__(self):
                super().__init__()
                self.cursor_obj = FailingCursor()

        class LegacyPool(_FakePool):
            check_connection = None

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.queue = [FailingConnection(), _ProbeConnection()]
                self.returned = []

            def getconn(self, timeout=None):
                connection = self.queue.pop(0)
                self.connections.append(connection)
                return connection

            def putconn(self, connection):
                self.put_count += 1
                self.returned.append(connection)

        pool = runtime.PsycopgPlannerPool(
            "postgresql://example",
            pool_class=LegacyPool,
        )
        pool.open(verify=False)
        created = LegacyPool.created[-1]

        lease = pool.get_connection()
        failed = created.connections[0]
        self.assertEqual(failed.closed, 1)
        self.assertIs(created.returned[0], failed)

        lease.close()
        self.assertEqual(created.put_count, 2)
        pool.close()

    def test_catalog_is_read_on_one_repeatable_read_snapshot(self):
        connection = _CatalogConnection(_catalog_rows())
        reader = runtime.PostgresAdminCatalogReader(lambda: connection)
        catalog = reader.load()

        self.assertIn("Demo.items", catalog.tables)
        self.assertIn(("Demo.items", "id"), catalog.fields)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.closed, 1)
        self.assertEqual(
            connection.cursor_obj.sql[0],
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY",
        )
        self.assertEqual(len(connection.cursor_obj.sql), 5)

    def test_catalog_read_retries_exactly_once_after_disconnect(self):
        class DisconnectError(Exception):
            pass

        connections = [
            _CatalogConnection(_catalog_rows(), fail=DisconnectError("lost")),
            _CatalogConnection(_catalog_rows()),
        ]

        def factory():
            return connections.pop(0)

        reader = runtime.PostgresAdminCatalogReader(
            factory,
            disconnect_checker=lambda exc: isinstance(exc, DisconnectError),
        )
        catalog = reader.load()
        self.assertIn("Demo.items", catalog.tables)
        self.assertEqual(len(connections), 0)

    def test_schema_installer_uses_one_commit_and_qualified_schema(self):
        class Cursor:
            def __init__(self):
                self.statements = []
                self.closed = False

            def execute(self, sql):
                self.statements.append(sql)

            def close(self):
                self.closed = True

        class Connection:
            autocommit = True

            def __init__(self):
                self.cursor_obj = Cursor()
                self.commits = 0
                self.rollbacks = 0
                self.closed = 0

            def cursor(self):
                return self.cursor_obj

            def commit(self):
                self.commits += 1

            def rollback(self):
                self.rollbacks += 1

            def close(self):
                self.closed += 1

        connection = Connection()
        count = runtime.PlannerSchemaInstaller(lambda: connection).install()
        joined = "\n".join(connection.cursor_obj.statements)
        self.assertEqual(count, len(connection.cursor_obj.statements))
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertEqual(connection.closed, 1)
        self.assertIn("CREATE SCHEMA IF NOT EXISTS planner", joined)
        self.assertIn("planner.planner_sources", joined)
        self.assertIn("public.admin_physical_tables", joined)

    def test_initial_seed_omits_reversed_type_relation(self):
        demo = registry.build_demo_catalog()
        reverse_pair = registry.RelationFieldPair(
            relation_key="rel_reverse_type",
            pair_no=0,
            left_table_key="Naryad.Тип_мк",
            left_field_name="Пномер",
            right_table_key="Naryad.mk",
            right_field_name="Тип",
        )
        reverse_relation = registry.AdminRelation(
            relation_key="rel_reverse_type",
            relation_name="Обратный тип",
            source_table_key="Naryad.Тип_мк",
            target_table_key="Naryad.mk",
            cardinality="many_to_one",
            field_pairs=(reverse_pair,),
        )
        catalog = replace(demo, relations={reverse_relation.relation_key: reverse_relation})

        definition = runtime.build_initial_seed(catalog)
        event = next(
            item
            for item in definition.configs
            if item.source.source_key == "gant.event.mk"
        )
        self.assertEqual(len(event.presentations), 1)
        self.assertTrue(any("обратная связь" in item for item in definition.warnings))

    def test_bootstrap_is_dry_run_then_missing_only(self):
        catalog = registry.build_demo_catalog()
        repository = registry.InMemoryPlannerRegistryRepository()
        service = registry.PlannerRegistryService(catalog, repository)
        bootstrapper = runtime.PlannerRegistryBootstrapper(service)
        definition = runtime.build_initial_seed(catalog)

        preview = bootstrapper.apply(definition, dry_run=True)
        self.assertEqual(len(preview.planned), 2)
        self.assertEqual(service.list_configs(), [])

        applied = bootstrapper.apply(definition, dry_run=False)
        self.assertEqual(len(applied.created), 2)
        self.assertEqual(len(service.list_configs()), 2)

        repeated = bootstrapper.apply(definition, dry_run=False)
        self.assertEqual(repeated.created, ())
        self.assertEqual(len(repeated.skipped), 2)

    def test_catalog_health_reports_relation_without_pairs(self):
        demo = registry.build_demo_catalog()
        empty_relation = replace(
            next(iter(demo.relations.values())),
            relation_key="empty",
            field_pairs=(),
        )
        catalog = replace(demo, relations={"empty": empty_relation})
        report = runtime.inspect_catalog(catalog)
        self.assertTrue(
            any(item.code == "relation_without_pairs" for item in report.issues)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
