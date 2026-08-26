from __future__ import annotations

import argparse
import dataclasses
import os
import sys
from dataclasses import dataclass
from typing import Any

try:
    from . import planner_registry_runtime_stage2 as runtime_api
    from . import planner_registry_stage2 as registry
    from .planner_mes_types import PLANNER_CONNINFO_ENV, PLANNER_SUBJECT_CODE
except ImportError:
    import planner_registry_runtime_stage2 as runtime_api
    import planner_registry_stage2 as registry
    from planner_mes_types import PLANNER_CONNINFO_ENV, PLANNER_SUBJECT_CODE


@dataclass(frozen=True)
class RequisiteSeed:
    key: str
    field_name: str
    caption: str
    is_filterable: bool = False
    is_groupable: bool = False
    semantic_role: registry.SemanticRole = registry.SemanticRole.ATTRIBUTE


@dataclass(frozen=True)
class PresentationSeed:
    key: str
    field_name: str
    caption: str
    is_default: bool = False
    required: bool = False


@dataclass(frozen=True)
class SourceSeed:
    source_key: str
    table_key: str
    caption: str
    identity_field_name: str
    roles: tuple[registry.SourceRole, ...]
    requisites: tuple[RequisiteSeed, ...]
    presentations: tuple[PresentationSeed, ...]
    sort_order: int


@dataclass(frozen=True)
class MesSeedDefinition:
    configs: tuple[registry.PlannerSourceConfig, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MesSeedResult:
    planned: tuple[str, ...] = ()
    created: tuple[str, ...] = ()
    updated: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    dry_run: bool = True


MES_SOURCE_SEEDS = (
    SourceSeed(
        source_key="gant.resource.podrazdel",
        table_key="DB_kplan.podrazdel",
        caption="Подразделения",
        identity_field_name="Пномер",
        roles=(registry.SourceRole.RESOURCE, registry.SourceRole.ATTRIBUTE),
        requisites=(
            RequisiteSeed("caption", "Наименование", "Подразделение", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("table", "Имя", "Техническое имя", is_filterable=True),
            RequisiteSeed("alias", "alias", "Краткое имя"),
            RequisiteSeed("color", "Цвет", "Цвет", semantic_role=registry.SemanticRole.COLOR),
        ),
        presentations=(
            PresentationSeed("default", "Наименование", "Подразделение", is_default=True, required=True),
            PresentationSeed("table", "Имя", "Техническое имя"),
        ),
        sort_order=10,
    ),
    SourceSeed(
        source_key="gant.event.mk",
        table_key="Naryad.mk",
        caption="Маршрутные карты",
        identity_field_name="Пномер",
        roles=(registry.SourceRole.EVENT, registry.SourceRole.ATTRIBUTE),
        requisites=(
            RequisiteSeed("name", "Номенклатура", "Номенклатура", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("type", "Тип", "Тип МК", is_filterable=True, is_groupable=True),
            RequisiteSeed("status", "Статус", "Статус", is_filterable=True, is_groupable=True),
            RequisiteSeed("start", "Дата", "Дата начала", semantic_role=registry.SemanticRole.START),
            RequisiteSeed("end", "Дата_завершения", "Дата завершения", semantic_role=registry.SemanticRole.END),
            RequisiteSeed("plan", "НомКплан", "Позиция плана", is_filterable=True),
        ),
        presentations=(
            PresentationSeed("default", "Номенклатура", "Номенклатура МК", is_default=True, required=True),
        ),
        sort_order=20,
    ),
    SourceSeed(
        source_key="gant.attribute.plan",
        table_key="DB_kplan.plan",
        caption="Позиции плана",
        identity_field_name="Пномер",
        roles=(registry.SourceRole.ATTRIBUTE,),
        requisites=(
            RequisiteSeed("position", "Позиция", "Позиция", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("group", "Группа", "Группа", is_filterable=True, is_groupable=True, semantic_role=registry.SemanticRole.GROUP),
            RequisiteSeed("status", "Статус", "Статус", is_filterable=True),
            RequisiteSeed("direction", "Направление_деятельности", "Направление", is_filterable=True, is_groupable=True),
            RequisiteSeed("mk", "МК", "Маршрутная карта", is_filterable=True),
        ),
        presentations=(
            PresentationSeed("default", "Позиция", "Позиция плана", is_default=True, required=True),
            PresentationSeed("group", "Группа", "Группа плана"),
        ),
        sort_order=30,
    ),
    SourceSeed(
        source_key="gant.attribute.naryad",
        table_key="Naryad.naryad",
        caption="Наряды",
        identity_field_name="Пномер",
        roles=(registry.SourceRole.ATTRIBUTE,),
        requisites=(
            RequisiteSeed("dse", "ДСЕ", "ДСЕ", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("mk", "Номер_мк", "Маршрутная карта", is_filterable=True),
            RequisiteSeed("operation", "Операции", "Операции", is_filterable=True),
            RequisiteSeed("work_center", "РЦ_наряд", "Рабочий центр", is_filterable=True, is_groupable=True),
            RequisiteSeed("employee", "ФИО", "Исполнитель", is_filterable=True, is_groupable=True),
            RequisiteSeed("date", "Дата", "Дата"),
        ),
        presentations=(
            PresentationSeed("default", "ДСЕ", "ДСЕ наряда", is_default=True, required=True),
            PresentationSeed("task", "Задание", "Задание"),
        ),
        sort_order=40,
    ),
    SourceSeed(
        source_key="gant.attribute.operations",
        table_key="Naryad.operacii",
        caption="Операции",
        identity_field_name="kod",
        roles=(registry.SourceRole.ATTRIBUTE,),
        requisites=(
            RequisiteSeed("name", "name", "Операция", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("stage", "etap", "Этап", is_filterable=True, is_groupable=True),
            RequisiteSeed("work_center", "rc", "Рабочий центр", is_filterable=True, is_groupable=True),
            RequisiteSeed("enabled", "Onoff", "Используется", is_filterable=True),
        ),
        presentations=(
            PresentationSeed("default", "name", "Операция", is_default=True, required=True),
        ),
        sort_order=50,
    ),
    SourceSeed(
        source_key="gant.attribute.stages",
        table_key="Naryad.etaps",
        caption="Этапы производства",
        identity_field_name="s_num",
        roles=(registry.SourceRole.ATTRIBUTE,),
        requisites=(
            RequisiteSeed("name", "name", "Этап", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("color", "color", "Цвет", semantic_role=registry.SemanticRole.COLOR),
            RequisiteSeed("poki", "poki", "Производство", is_filterable=True, is_groupable=True),
        ),
        presentations=(
            PresentationSeed("default", "name", "Этап производства", is_default=True, required=True),
        ),
        sort_order=60,
    ),
    SourceSeed(
        source_key="gant.attribute.dse",
        table_key="BD_dse.dse",
        caption="ДСЕ",
        identity_field_name="Пномер",
        roles=(registry.SourceRole.ATTRIBUTE,),
        requisites=(
            RequisiteSeed("number", "Номенклатурный_номер", "Обозначение", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("name", "Наименование", "Наименование"),
            RequisiteSeed("tech_card", "Номер_техкарты", "Технологическая карта", is_filterable=True),
            RequisiteSeed("erp", "Код_ЕРП", "Код ERP", is_filterable=True),
            RequisiteSeed("tags", "Теги", "Теги", is_filterable=True),
        ),
        presentations=(
            PresentationSeed("default", "Номенклатурный_номер", "Обозначение ДСЕ", is_default=True, required=True),
            PresentationSeed("name", "Наименование", "Наименование ДСЕ"),
        ),
        sort_order=70,
    ),
    SourceSeed(
        source_key="gant.attribute.tkp",
        table_key="BD_dse.tkp",
        caption="Технологические карты",
        identity_field_name="s_nom",
        roles=(registry.SourceRole.ATTRIBUTE,),
        requisites=(
            RequisiteSeed("name", "name_tkp", "Наименование", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("number", "nnom_tkp", "Номер ТКП", is_filterable=True),
            RequisiteSeed("product", "nnom_izd", "Изделие", is_filterable=True),
            RequisiteSeed("status", "status", "Статус", is_filterable=True, is_groupable=True),
            RequisiteSeed("type", "type_tkp", "Тип ТКП", is_filterable=True, is_groupable=True),
        ),
        presentations=(
            PresentationSeed("default", "name_tkp", "Технологическая карта", is_default=True, required=True),
            PresentationSeed("number", "nnom_tkp", "Номер ТКП"),
        ),
        sort_order=80,
    ),
    SourceSeed(
        source_key="gant.attribute.nomenclature",
        table_key="DB_nomenklatura_erp.nomen",
        caption="Номенклатура MES",
        identity_field_name="Пномер",
        roles=(registry.SourceRole.ATTRIBUTE,),
        requisites=(
            RequisiteSeed("name", "Наименование", "Наименование", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("code", "Код", "Код", is_filterable=True),
            RequisiteSeed("article", "Артикул", "Артикул", is_filterable=True),
            RequisiteSeed("kind", "Вид", "Вид номенклатуры", is_filterable=True, is_groupable=True),
            RequisiteSeed("kind_ref", "Вид_Ref_Key", "Ссылка вида", is_filterable=True),
        ),
        presentations=(
            PresentationSeed("default", "Наименование", "Номенклатура", is_default=True, required=True),
            PresentationSeed("code", "Код", "Код номенклатуры"),
            PresentationSeed("article", "Артикул", "Артикул"),
        ),
        sort_order=90,
    ),
    SourceSeed(
        source_key="gant.attribute.nomenclature_kinds",
        table_key="DB_nomenklatura_erp.ВидыНоменклатуры",
        caption="Виды номенклатуры",
        identity_field_name="s_num",
        roles=(registry.SourceRole.ATTRIBUTE,),
        requisites=(
            RequisiteSeed("name", "name", "Вид номенклатуры", semantic_role=registry.SemanticRole.LABEL),
            RequisiteSeed("has_params", "ЕстьПараметры", "Есть параметры", is_filterable=True),
            RequisiteSeed("tkp", "ТКП", "Используется в ТКП", is_filterable=True),
            RequisiteSeed("parent", "Родитель", "Родитель", is_filterable=True),
        ),
        presentations=(
            PresentationSeed("default", "name", "Вид номенклатуры", is_default=True, required=True),
        ),
        sort_order=100,
    ),
)


def build_mes_seed(catalog: registry.AdminCatalog) -> MesSeedDefinition:
    configs: list[registry.PlannerSourceConfig] = []
    warnings: list[str] = []
    for spec in MES_SOURCE_SEEDS:
        config = _build_source_config(catalog, spec, warnings)
        if config is not None:
            configs.append(config)
    _add_relation_presentations(catalog, configs, warnings)
    return MesSeedDefinition(tuple(configs), tuple(warnings))


def apply_mes_seed(
    runtime: Any,
    *,
    dry_run: bool = True,
) -> MesSeedResult:
    definition = build_mes_seed(runtime.catalog)
    existing = runtime.list_sources(PLANNER_SUBJECT_CODE)
    by_key = {item.source.source_key: item for item in existing}
    by_table = {item.source.table_key: item for item in existing}
    planned: list[registry.PlannerSourceConfig] = []
    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []
    warnings = list(definition.warnings)

    for config in definition.configs:
        current = by_key.get(config.source.source_key)
        if current is None:
            owner = by_table.get(config.source.table_key)
            if owner is not None:
                warnings.append(
                    f"{config.source.table_key!r} уже зарегистрирована как "
                    f"{owner.source.source_key!r}; автоматическое переименование запрещено."
                )
                skipped.append(config.source.source_key)
                continue
            merged = config
            created.append(config.source.source_key)
        else:
            if current.source.table_key != config.source.table_key:
                warnings.append(
                    f"{config.source.source_key!r} уже указывает на таблицу "
                    f"{current.source.table_key!r}; автоматическая замена на "
                    f"{config.source.table_key!r} запрещена."
                )
                skipped.append(config.source.source_key)
                continue
            merged = _merge_config(current, config)
            if merged == current:
                skipped.append(config.source.source_key)
                continue
            updated.append(config.source.source_key)
        runtime.service.validator.validate(merged)
        planned.append(merged)

    if not dry_run and planned:
        runtime.save_sources(planned)
    planned_keys = tuple(item.source.source_key for item in planned)
    return MesSeedResult(
        planned=planned_keys,
        created=() if dry_run else tuple(created),
        updated=() if dry_run else tuple(updated),
        skipped=tuple(skipped),
        warnings=tuple(warnings),
        dry_run=dry_run,
    )


def _build_source_config(
    catalog: registry.AdminCatalog,
    spec: SourceSeed,
    warnings: list[str],
) -> registry.PlannerSourceConfig | None:
    table = catalog.tables.get(spec.table_key)
    if table is None or not table.is_enabled or not table.schema_enabled:
        warnings.append(
            f"{spec.caption!r} пропущен: таблица {spec.table_key!r} отсутствует или выключена в admin-каталоге."
        )
        return None
    if (spec.table_key, spec.identity_field_name) not in catalog.fields:
        warnings.append(
            f"{spec.caption!r} пропущен: отсутствует поле идентичности {spec.identity_field_name!r}."
        )
        return None

    missing_required = [
        item.field_name
        for item in spec.presentations
        if item.required and (spec.table_key, item.field_name) not in catalog.fields
    ]
    if missing_required:
        warnings.append(
            f"{spec.caption!r} пропущен: отсутствуют обязательные поля представления "
            + ", ".join(missing_required)
            + "."
        )
        return None

    requisites: list[registry.PlannerRequisite] = []
    for order, item in enumerate(spec.requisites, 1):
        if (spec.table_key, item.field_name) not in catalog.fields:
            warnings.append(
                f"У {spec.caption!r} пропущен реквизит {item.field_name!r}: поля нет в admin_table_fields."
            )
            continue
        requisites.append(
            registry.PlannerRequisite(
                requisite_key=f"{spec.source_key}.req.{item.key}",
                source_key=spec.source_key,
                field_name=item.field_name,
                caption=item.caption,
                is_filterable=item.is_filterable,
                is_groupable=item.is_groupable,
                semantic_role=item.semantic_role,
                sort_order=order * 10,
            )
        )

    presentations: list[registry.PlannerPresentation] = []
    for order, item in enumerate(spec.presentations, 1):
        if (spec.table_key, item.field_name) not in catalog.fields:
            if not item.required:
                warnings.append(
                    f"У {spec.caption!r} пропущено представление {item.caption!r}: "
                    f"поля {item.field_name!r} нет в admin_table_fields."
                )
            continue
        presentations.append(
            registry.PlannerPresentation(
                presentation_key=f"{spec.source_key}.view.{item.key}",
                source_key=spec.source_key,
                source_field_name=spec.identity_field_name,
                result_table_key=spec.table_key,
                result_field_name=item.field_name,
                caption=item.caption,
                is_default=item.is_default,
                sort_order=order * 10,
            )
        )
    return registry.PlannerSourceConfig(
        source=registry.PlannerSource(
            source_key=spec.source_key,
            subject_code=PLANNER_SUBJECT_CODE,
            table_key=spec.table_key,
            caption=spec.caption,
            identity_field_name=spec.identity_field_name,
            sort_order=spec.sort_order,
        ),
        roles=spec.roles,
        requisites=tuple(requisites),
        presentations=tuple(presentations),
    )


def _add_relation_presentations(
    catalog: registry.AdminCatalog,
    configs: list[registry.PlannerSourceConfig],
    warnings: list[str],
) -> None:
    requests = (
        ("gant.event.mk", "Тип", "Имя", "type", "Имя типа МК"),
        ("gant.attribute.naryad", "Номер_мк", "Номенклатура", "mk", "Номенклатура МК"),
        ("gant.attribute.nomenclature", "Вид_Ref_Key", "name", "kind", "Вид номенклатуры"),
    )
    by_key = {item.source.source_key: index for index, item in enumerate(configs)}
    for source_key, source_field, result_field, key, caption in requests:
        index = by_key.get(source_key)
        if index is None:
            continue
        config = configs[index]
        found = _find_scalar_relation(
            catalog,
            source_table_key=config.source.table_key,
            source_field_name=source_field,
            target_result_field=result_field,
        )
        if found is None:
            warnings.append(
                f"Для {config.source.table_key}.{source_field} не добавлено relation-представление "
                f"{caption!r}: нет однозначной исходящей many_to_one/one_to_one связи."
            )
            continue
        target_table_key, relation_key = found
        presentation = registry.PlannerPresentation(
            presentation_key=f"{source_key}.view.{key}",
            source_key=source_key,
            source_field_name=source_field,
            result_table_key=target_table_key,
            result_field_name=result_field,
            caption=caption,
            relation_steps=(relation_key,),
            sort_order=(len(config.presentations) + 1) * 10,
        )
        configs[index] = dataclasses.replace(
            config,
            presentations=tuple((*config.presentations, presentation)),
        )


def _find_scalar_relation(
    catalog: registry.AdminCatalog,
    *,
    source_table_key: str,
    source_field_name: str,
    target_result_field: str,
) -> tuple[str, str] | None:
    matches: list[tuple[str, str]] = []
    for relation in catalog.outgoing_relations(source_table_key):
        if relation.cardinality not in {"many_to_one", "one_to_one"}:
            continue
        target = catalog.tables.get(relation.target_table_key)
        if target is None or not target.is_enabled or not target.schema_enabled:
            continue
        if (relation.target_table_key, target_result_field) not in catalog.fields:
            continue
        if not any(
            pair.left_table_key == source_table_key
            and pair.left_field_name == source_field_name
            and pair.operator == "="
            for pair in relation.field_pairs
        ):
            continue
        matches.append((relation.target_table_key, relation.relation_key))
    if len(matches) > 1:
        raise registry.PlannerValidationError(
            f"Для {source_table_key}.{source_field_name} найдено несколько скалярных связей: "
            + ", ".join(item[1] for item in matches)
        )
    return matches[0] if matches else None


def _merge_config(
    current: registry.PlannerSourceConfig,
    desired: registry.PlannerSourceConfig,
) -> registry.PlannerSourceConfig:
    roles = tuple(dict.fromkeys((*current.roles, *desired.roles)))
    requisites = list(current.requisites)
    requisite_indexes = {item.field_name: index for index, item in enumerate(requisites)}
    requisite_keys = {item.requisite_key for item in requisites}
    single_roles = {
        registry.SemanticRole.LABEL,
        registry.SemanticRole.START,
        registry.SemanticRole.END,
        registry.SemanticRole.COLOR,
        registry.SemanticRole.GROUP,
    }
    used_single_roles = {
        registry.SemanticRole(item.semantic_role)
        for item in requisites
        if registry.SemanticRole(item.semantic_role) in single_roles
    }
    for item in desired.requisites:
        current_index = requisite_indexes.get(item.field_name)
        if current_index is not None:
            current_item = requisites[current_index]
            requisites[current_index] = dataclasses.replace(
                current_item,
                is_selectable=current_item.is_selectable or item.is_selectable,
                is_filterable=current_item.is_filterable or item.is_filterable,
                is_groupable=current_item.is_groupable or item.is_groupable,
            )
            continue
        if item.requisite_key in requisite_keys:
            raise registry.PlannerValidationError(
                f"requisite_key={item.requisite_key!r} уже занят другим полем."
            )
        semantic_role = registry.SemanticRole(item.semantic_role)
        if semantic_role in used_single_roles:
            item = dataclasses.replace(
                item,
                semantic_role=registry.SemanticRole.ATTRIBUTE,
            )
        requisites.append(item)
        requisite_indexes[item.field_name] = len(requisites) - 1
        requisite_keys.add(item.requisite_key)
        if semantic_role in single_roles:
            used_single_roles.add(semantic_role)

    presentations = list(current.presentations)
    presentation_keys = {item.presentation_key for item in presentations}
    signatures = {
        (
            item.source_field_name,
            item.result_table_key,
            item.result_field_name,
            tuple(item.relation_steps),
        )
        for item in presentations
    }
    has_default = any(item.is_default for item in presentations)
    for item in desired.presentations:
        signature = (
            item.source_field_name,
            item.result_table_key,
            item.result_field_name,
            tuple(item.relation_steps),
        )
        if item.presentation_key in presentation_keys or signature in signatures:
            continue
        if item.is_default and has_default:
            item = dataclasses.replace(item, is_default=False)
        presentations.append(item)
        presentation_keys.add(item.presentation_key)
        signatures.add(signature)
        has_default = has_default or item.is_default
    return registry.PlannerSourceConfig(
        source=current.source,
        roles=roles,
        requisites=tuple(requisites),
        presentations=tuple(presentations),
    )


def _run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Проверка и первичное заполнение справочников МЕС для планировщика."
    )
    parser.add_argument(
        "--install-schema",
        action="store_true",
        help="Создать или проверить таблицы planner.* перед заполнением.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Записать недостающие регистрации. Без флага выполняется только проверка.",
    )
    args = parser.parse_args(argv)
    conninfo = str(os.getenv(PLANNER_CONNINFO_ENV, "") or "").strip()
    if not conninfo:
        print(
            f"Не задана переменная окружения {PLANNER_CONNINFO_ENV}.",
            file=sys.stderr,
        )
        return 2
    runtime = None
    try:
        runtime = runtime_api.PlannerRegistryRuntime.connect(conninfo)
        if args.install_schema:
            statements = runtime.install_schema()
            print(f"Схема planner проверена, выполнено выражений: {statements}.")
        result = apply_mes_seed(runtime, dry_run=not args.apply)
        mode = "Проверка" if result.dry_run else "Заполнение"
        print(f"{mode}: к записи={list(result.planned)}")
        print(f"Созданы={list(result.created)}")
        print(f"Дополнены={list(result.updated)}")
        print(f"Пропущены={list(result.skipped)}")
        for warning in result.warnings:
            print(f"[предупреждение] {warning}")
        return 0
    except registry.PlannerRegistryError as exc:
        print(f"Ошибка регистрации источников: {exc}", file=sys.stderr)
        return 1
    finally:
        if runtime is not None:
            runtime.close()


__all__ = [
    "MES_SOURCE_SEEDS",
    "RequisiteSeed",
    "PresentationSeed",
    "SourceSeed",
    "MesSeedDefinition",
    "MesSeedResult",
    "build_mes_seed",
    "apply_mes_seed",
]


if __name__ == "__main__":
    raise SystemExit(_run_cli())
