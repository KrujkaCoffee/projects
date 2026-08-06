from __future__ import annotations

import dataclasses
import unittest

from project_cust_38.sub_mes.resource_planning import planner_mes_seed as seed
from project_cust_38.sub_mes.resource_planning import planner_mes_types as mes_types
from project_cust_38.sub_mes.resource_planning import planner_registry_stage2 as registry
from project_cust_38.sub_mes.resource_planning import planner_registry_runtime_stage2 as runtime_registry


class _MesBase:
    pass


class _Runtime:
    def __init__(self, configs=()):
        self.configs = list(configs)
        self.list_calls = []
        self.close_calls = 0

    def list_sources(self, subject_code=None, *, role=None):
        self.list_calls.append((subject_code, role))
        return list(self.configs)

    def close(self):
        self.close_calls += 1


def _source_config(
    source_key="gant.event.mk",
    *,
    roles=(registry.SourceRole.ATTRIBUTE,),
    is_enabled=True,
    with_default=True,
):
    presentations = (
        registry.PlannerPresentation(
            presentation_key=f"{source_key}.view.default",
            source_key=source_key,
            source_field_name="Пномер",
            result_table_key="Naryad.mk",
            result_field_name="Номенклатура",
            caption="Номенклатура МК",
            is_default=with_default,
            sort_order=10,
        ),
        registry.PlannerPresentation(
            presentation_key=f"{source_key}.view.type",
            source_key=source_key,
            source_field_name="Тип",
            result_table_key="Naryad.Тип_мк",
            result_field_name="Имя",
            caption="Имя типа МК",
            relation_steps=("naryad.mk.type",),
            sort_order=20,
        ),
    )
    return registry.PlannerSourceConfig(
        source=registry.PlannerSource(
            source_key=source_key,
            subject_code="gant",
            table_key="Naryad.mk",
            caption="Маршрутные карты",
            identity_field_name="Пномер",
            is_enabled=is_enabled,
            sort_order=20,
        ),
        roles=roles,
        requisites=(
            registry.PlannerRequisite(
                requisite_key=f"{source_key}.req.type",
                source_key=source_key,
                field_name="Тип",
                caption="Тип МК",
                is_filterable=True,
                is_groupable=True,
            ),
        ),
        presentations=presentations,
    )


def _full_admin_catalog():
    tables = {}
    fields = {}
    for source in seed.MES_SOURCE_SEEDS:
        db_key, table_name = source.table_key.split(".", 1)
        tables[source.table_key] = registry.AdminTable(
            table_key=source.table_key,
            db_key=db_key,
            table_name=table_name,
        )
        names = {source.identity_field_name}
        names.update(item.field_name for item in source.requisites)
        names.update(item.field_name for item in source.presentations)
        for order, name in enumerate(sorted(names), 1):
            fields[(source.table_key, name)] = registry.AdminField(
                table_key=source.table_key,
                field_name=name,
                is_pk=name == source.identity_field_name,
                sort_order=order,
            )

    tables["Naryad.Тип_мк"] = registry.AdminTable(
        table_key="Naryad.Тип_мк",
        db_key="Naryad",
        table_name="Тип_мк",
    )
    for name in ("Пномер", "Имя"):
        fields[("Naryad.Тип_мк", name)] = registry.AdminField(
            table_key="Naryad.Тип_мк",
            field_name=name,
            is_pk=name == "Пномер",
        )
    fields[("DB_nomenklatura_erp.ВидыНоменклатуры", "Ref_Key")] = registry.AdminField(
        table_key="DB_nomenklatura_erp.ВидыНоменклатуры",
        field_name="Ref_Key",
    )

    relations = {}

    def add_relation(key, source_table, source_field, target_table, target_field):
        pair = registry.RelationFieldPair(
            relation_key=key,
            pair_no=1,
            left_table_key=source_table,
            left_field_name=source_field,
            right_table_key=target_table,
            right_field_name=target_field,
        )
        relations[key] = registry.AdminRelation(
            relation_key=key,
            relation_name=key,
            source_table_key=source_table,
            target_table_key=target_table,
            cardinality="many_to_one",
            field_pairs=(pair,),
        )

    add_relation("naryad.mk.type", "Naryad.mk", "Тип", "Naryad.Тип_мк", "Пномер")
    add_relation("naryad.naryad.mk", "Naryad.naryad", "Номер_мк", "Naryad.mk", "Пномер")
    add_relation(
        "erp.nomen.kind",
        "DB_nomenklatura_erp.nomen",
        "Вид_Ref_Key",
        "DB_nomenklatura_erp.ВидыНоменклатуры",
        "Ref_Key",
    )
    return registry.AdminCatalog(tables=tables, fields=fields, relations=relations)


class PlannerMesTypeCatalogTests(unittest.TestCase):
    def test_catalog_returns_only_enabled_attribute_sources(self):
        usable = _source_config()
        disabled = _source_config("gant.event.disabled", is_enabled=False)
        event_only = _source_config(
            "gant.event.only",
            roles=(registry.SourceRole.EVENT,),
        )
        without_default = _source_config(
            "gant.event.no_default",
            with_default=False,
        )
        runtime = _Runtime((usable, disabled, event_only, without_default))
        catalog = mes_types.PlannerMesTypeCatalog(
            mes_types.PlannerRuntimeSession(runtime)
        )

        entries = catalog.reload(_MesBase)

        self.assertEqual([item.source_key for item in entries], ["gant.event.mk"])
        self.assertEqual(
            runtime.list_calls,
            [("gant", registry.SourceRole.ATTRIBUTE)],
        )
        self.assertTrue(any("по умолчанию" in item for item in catalog.warnings))

    def test_dynamic_type_and_stable_presentation_keys_are_reused(self):
        runtime = _Runtime((_source_config(),))
        catalog = mes_types.PlannerMesTypeCatalog(
            mes_types.PlannerRuntimeSession(runtime)
        )

        first = catalog.reload(_MesBase)[0]
        second = catalog.reload(_MesBase)[0]
        default = catalog.default_presentation(first.value)
        rows = catalog.presentation_template(first.value)

        self.assertIs(first.value, second.value)
        self.assertTrue(issubclass(first.value, _MesBase))
        self.assertEqual(first.value._planner_source_key, "gant.event.mk")
        self.assertEqual(default.presentation_key, "gant.event.mk.view.default")
        self.assertEqual(rows[1]["_presentation_key"], "gant.event.mk.view.type")
        self.assertEqual(rows[1]["Фильтр"], "Да")

    def test_session_is_lazy_reused_and_closed_once(self):
        runtime = _Runtime()
        created = []

        def factory(conninfo):
            created.append(conninfo)
            return runtime

        session = mes_types.PlannerRuntimeSession(
            runtime_factory=factory,
            conninfo_provider=lambda: "dbname=planner",
        )

        self.assertTrue(session.configured)
        self.assertIs(session.get_runtime(), runtime)
        self.assertIs(session.get_runtime(), runtime)
        session.close()
        session.close()

        self.assertEqual(created, ["dbname=planner"])
        self.assertEqual(runtime.close_calls, 1)

    def test_session_reports_missing_configuration_in_russian(self):
        session = mes_types.PlannerRuntimeSession(conninfo_provider=lambda: "")

        with self.assertRaisesRegex(
            mes_types.PlannerMesTypeError,
            "Не задана переменная окружения",
        ):
            session.get_runtime()


class PlannerMesSeedTests(unittest.TestCase):
    def test_seed_registers_ten_curated_sources_and_relation_views(self):
        definition = seed.build_mes_seed(_full_admin_catalog())

        self.assertEqual(len(definition.configs), 10)
        self.assertEqual(definition.warnings, ())
        mk = next(
            item for item in definition.configs
            if item.source.source_key == "gant.event.mk"
        )
        self.assertIn(registry.SourceRole.ATTRIBUTE, mk.roles)
        type_requisite = next(item for item in mk.requisites if item.field_name == "Тип")
        self.assertTrue(type_requisite.is_filterable)
        self.assertTrue(type_requisite.is_groupable)
        type_view = next(item for item in mk.presentations if item.result_field_name == "Имя")
        self.assertEqual(type_view.relation_steps, ("naryad.mk.type",))

    def test_seed_skips_unknown_physical_tables(self):
        definition = seed.build_mes_seed(
            registry.AdminCatalog(tables={}, fields={}, relations={})
        )

        self.assertEqual(definition.configs, ())
        self.assertEqual(len(definition.warnings), 10)

    def test_apply_adds_attribute_role_without_overwriting_source(self):
        catalog = _full_admin_catalog()
        desired = seed.build_mes_seed(catalog).configs
        desired_mk = next(
            item for item in desired
            if item.source.source_key == "gant.event.mk"
        )
        current_mk = dataclasses.replace(
            desired_mk,
            source=dataclasses.replace(
                desired_mk.source,
                caption="Настроенное имя",
            ),
            roles=(registry.SourceRole.EVENT,),
            requisites=desired_mk.requisites[:1],
            presentations=desired_mk.presentations[:1],
        )
        repository = registry.InMemoryPlannerRegistryRepository((current_mk,))
        service = registry.PlannerRegistryService(catalog, repository)

        class Runtime:
            def __init__(self):
                self.catalog = catalog
                self.service = service

            def list_sources(self, subject_code=None):
                return self.service.list_configs(subject_code)

            def save_sources(self, configs):
                self.service.save_configs(configs)

        result = seed.apply_mes_seed(Runtime(), dry_run=False)
        saved = service.get_config("gant.event.mk")

        self.assertIn("gant.event.mk", result.updated)
        self.assertEqual(saved.source.caption, "Настроенное имя")
        self.assertIn(registry.SourceRole.EVENT, saved.roles)
        self.assertIn(registry.SourceRole.ATTRIBUTE, saved.roles)
        self.assertTrue(any(item.field_name == "Тип" for item in saved.requisites))

    def test_apply_upgrades_previous_bootstrap_without_semantic_conflict(self):
        catalog = _full_admin_catalog()
        previous = runtime_registry.build_initial_seed(catalog).configs
        repository = registry.InMemoryPlannerRegistryRepository(previous)
        service = registry.PlannerRegistryService(catalog, repository)

        class Runtime:
            def __init__(self):
                self.catalog = catalog
                self.service = service

            def list_sources(self, subject_code=None):
                return self.service.list_configs(subject_code)

            def save_sources(self, configs):
                self.service.save_configs(configs)

        result = seed.apply_mes_seed(Runtime(), dry_run=False)
        mk = service.get_config("gant.event.mk")
        podrazdel = service.get_config("gant.resource.podrazdel")
        mk_type = next(item for item in mk.requisites if item.field_name == "Тип")
        podrazdel_labels = [
            item for item in podrazdel.requisites
            if item.semantic_role == registry.SemanticRole.LABEL
        ]

        self.assertIn("gant.event.mk", result.updated)
        self.assertIn("gant.resource.podrazdel", result.updated)
        self.assertTrue(mk_type.is_filterable)
        self.assertTrue(mk_type.is_groupable)
        self.assertEqual(len(podrazdel_labels), 1)

    def test_apply_skips_source_key_bound_to_another_table(self):
        catalog = _full_admin_catalog()
        desired_mk = next(
            item for item in seed.build_mes_seed(catalog).configs
            if item.source.source_key == "gant.event.mk"
        )
        wrong_source = dataclasses.replace(
            desired_mk,
            source=dataclasses.replace(
                desired_mk.source,
                table_key="DB_kplan.plan",
                identity_field_name="Пномер",
            ),
            requisites=(),
            presentations=(),
        )
        repository = registry.InMemoryPlannerRegistryRepository((wrong_source,))
        service = registry.PlannerRegistryService(catalog, repository)

        class Runtime:
            def __init__(self):
                self.catalog = catalog
                self.service = service

            def list_sources(self, subject_code=None):
                return self.service.list_configs(subject_code)

            def save_sources(self, configs):
                self.service.save_configs(configs)

        result = seed.apply_mes_seed(Runtime(), dry_run=False)

        self.assertIn("gant.event.mk", result.skipped)
        self.assertTrue(any("автоматическая замена" in item for item in result.warnings))
        self.assertEqual(
            service.get_config("gant.event.mk").source.table_key,
            "DB_kplan.plan",
        )


if __name__ == "__main__":
    unittest.main()
