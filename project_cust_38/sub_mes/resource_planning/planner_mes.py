from __future__ import annotations

import contextlib
import copy
import dataclasses
import enum
import hashlib
import re
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from project_cust_38 import Cust_postgresql_executor as postgres

PLANNER_SCHEMA = "planner"
ADMIN_SCHEMA = "public"


POSTGRES_MIGRATION_SQL = r"""
CREATE SCHEMA IF NOT EXISTS planner;

CREATE TABLE IF NOT EXISTS planner.planner_sources (
    source_key text PRIMARY KEY,
    subject_code text NOT NULL,
    table_key text NOT NULL,
    caption text NOT NULL,
    identity_field_name text NOT NULL,
    is_enabled integer DEFAULT 1 NOT NULL CHECK (is_enabled IN (0, 1)),
    sort_order integer DEFAULT 0 NOT NULL,
    updated_at text DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') NOT NULL,
    CONSTRAINT fk_planner_sources_table
        FOREIGN KEY (table_key)
        REFERENCES public.admin_physical_tables(table_key)
        ON DELETE RESTRICT,
    CONSTRAINT fk_planner_sources_identity
        FOREIGN KEY (table_key, identity_field_name)
        REFERENCES public.admin_table_fields(table_key, field_name)
        ON DELETE RESTRICT,
    CONSTRAINT uq_planner_sources_subject_table UNIQUE (subject_code, table_key),
    CONSTRAINT uq_planner_sources_source_table UNIQUE (source_key, table_key)
);

CREATE TABLE IF NOT EXISTS planner.planner_source_roles (
    role_key text PRIMARY KEY,
    source_key text NOT NULL,
    role text NOT NULL CHECK (role IN ('resource', 'event', 'attribute')),
    CONSTRAINT fk_planner_source_roles_source
        FOREIGN KEY (source_key)
        REFERENCES planner.planner_sources(source_key)
        ON DELETE CASCADE,
    CONSTRAINT uq_planner_source_roles UNIQUE (source_key, role)
);

CREATE TABLE IF NOT EXISTS planner.planner_requisites (
    requisite_key text PRIMARY KEY,
    source_key text NOT NULL,
    table_key text NOT NULL,
    field_name text NOT NULL,
    caption text NOT NULL,
    is_selectable integer DEFAULT 1 NOT NULL CHECK (is_selectable IN (0, 1)),
    is_filterable integer DEFAULT 0 NOT NULL CHECK (is_filterable IN (0, 1)),
    is_groupable integer DEFAULT 0 NOT NULL CHECK (is_groupable IN (0, 1)),
    semantic_role text DEFAULT 'attribute' NOT NULL
        CHECK (semantic_role IN ('attribute', 'label', 'start', 'end', 'color', 'group')),
    sort_order integer DEFAULT 0 NOT NULL,
    CONSTRAINT fk_planner_requisites_source
        FOREIGN KEY (source_key, table_key)
        REFERENCES planner.planner_sources(source_key, table_key)
        ON DELETE CASCADE,
    CONSTRAINT fk_planner_requisites_field
        FOREIGN KEY (table_key, field_name)
        REFERENCES public.admin_table_fields(table_key, field_name)
        ON DELETE RESTRICT,
    CONSTRAINT uq_planner_requisites_source_field UNIQUE (source_key, field_name)
);

CREATE TABLE IF NOT EXISTS planner.planner_presentations (
    presentation_key text PRIMARY KEY,
    source_key text NOT NULL,
    source_table_key text NOT NULL,
    source_field_name text NOT NULL,
    result_table_key text NOT NULL,
    result_field_name text NOT NULL,
    caption text NOT NULL,
    presentation_kind text NOT NULL CHECK (presentation_kind IN ('direct', 'relation')),
    missing_policy text DEFAULT 'none' NOT NULL CHECK (missing_policy IN ('none', 'error')),
    on_many_policy text DEFAULT 'error' NOT NULL CHECK (on_many_policy IN ('error')),
    is_default integer DEFAULT 0 NOT NULL CHECK (is_default IN (0, 1)),
    sort_order integer DEFAULT 0 NOT NULL,
    CONSTRAINT fk_planner_presentations_source
        FOREIGN KEY (source_key, source_table_key)
        REFERENCES planner.planner_sources(source_key, table_key)
        ON DELETE CASCADE,
    CONSTRAINT fk_planner_presentations_source_field
        FOREIGN KEY (source_table_key, source_field_name)
        REFERENCES public.admin_table_fields(table_key, field_name)
        ON DELETE RESTRICT,
    CONSTRAINT fk_planner_presentations_result_field
        FOREIGN KEY (result_table_key, result_field_name)
        REFERENCES public.admin_table_fields(table_key, field_name)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS planner.planner_presentation_steps (
    presentation_step_key text PRIMARY KEY,
    presentation_key text NOT NULL,
    step_no integer DEFAULT 0 NOT NULL CHECK (step_no >= 0),
    relation_key text NOT NULL,
    CONSTRAINT fk_planner_presentation_steps_presentation
        FOREIGN KEY (presentation_key)
        REFERENCES planner.planner_presentations(presentation_key)
        ON DELETE CASCADE,
    CONSTRAINT fk_planner_presentation_steps_relation
        FOREIGN KEY (relation_key)
        REFERENCES public.admin_table_relations(relation_key)
        ON DELETE RESTRICT,
    CONSTRAINT uq_planner_presentation_steps_no UNIQUE (presentation_key, step_no)
);

CREATE INDEX IF NOT EXISTS idx_planner_sources_subject
    ON planner.planner_sources(subject_code, is_enabled, sort_order, source_key);

CREATE INDEX IF NOT EXISTS idx_planner_requisites_source
    ON planner.planner_requisites(source_key, sort_order, requisite_key);

CREATE INDEX IF NOT EXISTS idx_planner_presentations_source
    ON planner.planner_presentations(source_key, sort_order, presentation_key);

CREATE UNIQUE INDEX IF NOT EXISTS uq_planner_presentations_default
    ON planner.planner_presentations(source_key)
    WHERE is_default = 1;
""".strip()


class PlannerRegistryError(Exception):
    """Базовая ошибка регистрационного контура планировщика."""


class PlannerValidationError(PlannerRegistryError):
    """Конфигурация не прошла проверку целостности."""


class PlannerCatalogError(PlannerRegistryError):
    """Административный каталог содержит противоречивые метаданные."""


class PlannerRepositoryError(PlannerRegistryError):
    """Хранилище конфигурации не завершило операцию."""


class PlannerCommitOutcomeUnknown(PlannerRepositoryError):
    """Сервер не подтвердил COMMIT, поэтому результат записи нельзя угадывать."""


class SourceRole(str, enum.Enum):
    RESOURCE = "resource"
    EVENT = "event"
    ATTRIBUTE = "attribute"


class SemanticRole(str, enum.Enum):
    ATTRIBUTE = "attribute"
    LABEL = "label"
    START = "start"
    END = "end"
    COLOR = "color"
    GROUP = "group"


class PresentationKind(str, enum.Enum):
    DIRECT = "direct"
    RELATION = "relation"


@dataclass(frozen=True)
class AdminTable:
    table_key: str
    db_key: str
    table_name: str
    is_enabled: bool = True
    schema_enabled: bool = True


@dataclass(frozen=True)
class AdminField:
    table_key: str
    field_name: str
    label: str = ""
    db_type: str = ""
    nullable: bool = True
    is_pk: bool = False
    sort_order: int = 0
    include_in_schema: bool = True


@dataclass(frozen=True)
class RelationFieldPair:
    relation_key: str
    pair_no: int
    left_table_key: str
    left_field_name: str
    right_table_key: str
    right_field_name: str
    role: str = "direct"
    operator: str = "="
    pair_join_type: str = ""


@dataclass(frozen=True)
class AdminRelation:
    relation_key: str
    relation_name: str
    source_table_key: str
    target_table_key: str
    cardinality: str = "many_to_one"
    join_type: str = "LEFT JOIN"
    missing_policy: str = "none"
    on_many_policy: str = "error"
    is_enabled: bool = True
    field_pairs: tuple[RelationFieldPair, ...] = ()


@dataclass(frozen=True)
class AdminCatalog:
    tables: Mapping[str, AdminTable]
    fields: Mapping[tuple[str, str], AdminField]
    relations: Mapping[str, AdminRelation]

    @classmethod
    def from_rows(
        cls,
        table_rows: Iterable[Mapping[str, Any]],
        field_rows: Iterable[Mapping[str, Any]],
        relation_rows: Iterable[Mapping[str, Any]],
        pair_rows: Iterable[Mapping[str, Any]],
    ) -> "AdminCatalog":
        tables: dict[str, AdminTable] = {}
        fields: dict[tuple[str, str], AdminField] = {}
        pairs_by_relation: dict[str, list[RelationFieldPair]] = {}

        for row in table_rows:
            item = AdminTable(
                table_key=_required_text(row, "table_key", "таблицы"),
                db_key=str(row.get("db_key") or ""),
                table_name=_required_text(row, "table_name", "таблицы"),
                is_enabled=_as_bool(row.get("is_enabled"), True),
                schema_enabled=_as_bool(row.get("schema_enabled"), True),
            )
            if item.table_key in tables:
                raise PlannerCatalogError(
                    f"В admin_physical_tables повторяется table_key={item.table_key!r}."
                )
            tables[item.table_key] = item

        for row in field_rows:
            item = AdminField(
                table_key=_required_text(row, "table_key", "поля"),
                field_name=_required_text(row, "field_name", "поля"),
                label=str(row.get("label") or ""),
                db_type=str(row.get("db_type") or ""),
                nullable=_as_bool(row.get("nullable"), True),
                is_pk=_as_bool(row.get("is_pk"), False),
                sort_order=int(row.get("sort_order") or 0),
                include_in_schema=_as_bool(row.get("include_in_schema"), True),
            )
            key = (item.table_key, item.field_name)
            if key in fields:
                raise PlannerCatalogError(
                    f"В admin_table_fields повторяется поле {item.table_key}.{item.field_name}."
                )
            if item.table_key not in tables:
                raise PlannerCatalogError(
                    f"Поле {item.table_key}.{item.field_name} ссылается на неизвестную таблицу."
                )
            fields[key] = item

        for row in pair_rows:
            item = RelationFieldPair(
                relation_key=_required_text(row, "relation_key", "пары связи"),
                pair_no=int(row.get("pair_no") or 0),
                left_table_key=_required_text(row, "left_table_key", "пары связи"),
                left_field_name=_required_text(row, "left_field_name", "пары связи"),
                right_table_key=_required_text(row, "right_table_key", "пары связи"),
                right_field_name=_required_text(row, "right_field_name", "пары связи"),
                role=str(row.get("role") or "direct"),
                operator=str(row.get("operator") or "="),
                pair_join_type=str(row.get("pair_join_type") or ""),
            )
            pairs_by_relation.setdefault(item.relation_key, []).append(item)

        relations: dict[str, AdminRelation] = {}
        for row in relation_rows:
            relation_key = _required_text(row, "relation_key", "связи")
            item = AdminRelation(
                relation_key=relation_key,
                relation_name=_required_text(row, "relation_name", "связи"),
                source_table_key=_required_text(row, "source_table_key", "связи"),
                target_table_key=_required_text(row, "target_table_key", "связи"),
                cardinality=str(row.get("cardinality") or "many_to_one").lower(),
                join_type=str(row.get("join_type") or "LEFT JOIN").upper(),
                missing_policy=str(row.get("missing_policy") or "none").lower(),
                on_many_policy=str(row.get("on_many_policy") or "error").lower(),
                is_enabled=_as_bool(row.get("is_enabled"), True),
                field_pairs=tuple(
                    sorted(pairs_by_relation.get(relation_key, ()), key=lambda pair: pair.pair_no)
                ),
            )
            if relation_key in relations:
                raise PlannerCatalogError(
                    f"В admin_table_relations повторяется relation_key={relation_key!r}."
                )
            if item.source_table_key not in tables or item.target_table_key not in tables:
                raise PlannerCatalogError(
                    f"Связь {relation_key!r} ссылается на неизвестную таблицу."
                )
            pair_numbers: set[int] = set()
            for pair in item.field_pairs:
                if pair.pair_no in pair_numbers:
                    raise PlannerCatalogError(
                        f"В связи {relation_key!r} повторяется pair_no={pair.pair_no}."
                    )
                pair_numbers.add(pair.pair_no)
                if (
                    pair.left_table_key != item.source_table_key
                    or pair.right_table_key != item.target_table_key
                ):
                    raise PlannerCatalogError(
                        f"Пара {relation_key!r}:{pair.pair_no} не совпадает с направлением связи."
                    )
                if (pair.left_table_key, pair.left_field_name) not in fields:
                    raise PlannerCatalogError(
                        f"Левое поле пары {relation_key!r}:{pair.pair_no} отсутствует в каталоге."
                    )
                if (pair.right_table_key, pair.right_field_name) not in fields:
                    raise PlannerCatalogError(
                        f"Правое поле пары {relation_key!r}:{pair.pair_no} отсутствует в каталоге."
                    )
            relations[relation_key] = item

        orphan_pairs = sorted(set(pairs_by_relation).difference(relations))
        if orphan_pairs:
            raise PlannerCatalogError(
                "Найдены пары полей без заголовка связи: " + ", ".join(orphan_pairs)
            )
        return cls(tables=tables, fields=fields, relations=relations)

    def table_fields(self, table_key: str) -> tuple[AdminField, ...]:
        return tuple(
            sorted(
                (item for (key, _), item in self.fields.items() if key == table_key),
                key=lambda item: (item.sort_order, item.field_name),
            )
        )

    def outgoing_relations(self, table_key: str) -> tuple[AdminRelation, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self.relations.values()
                    if item.source_table_key == table_key and item.is_enabled
                ),
                key=lambda item: (item.relation_name, item.relation_key),
            )
        )


@dataclass(frozen=True)
class PlannerSource:
    source_key: str
    subject_code: str
    table_key: str
    caption: str
    identity_field_name: str
    is_enabled: bool = True
    sort_order: int = 0


@dataclass(frozen=True)
class PlannerRequisite:
    requisite_key: str
    source_key: str
    field_name: str
    caption: str
    is_selectable: bool = True
    is_filterable: bool = False
    is_groupable: bool = False
    semantic_role: SemanticRole = SemanticRole.ATTRIBUTE
    sort_order: int = 0


@dataclass(frozen=True)
class PlannerPresentation:
    presentation_key: str
    source_key: str
    source_field_name: str
    result_table_key: str
    result_field_name: str
    caption: str
    relation_steps: tuple[str, ...] = ()
    missing_policy: str = "none"
    on_many_policy: str = "error"
    is_default: bool = False
    sort_order: int = 0

    @property
    def kind(self) -> PresentationKind:
        return PresentationKind.RELATION if self.relation_steps else PresentationKind.DIRECT


@dataclass(frozen=True)
class PlannerSourceConfig:
    source: PlannerSource
    roles: tuple[SourceRole, ...]
    requisites: tuple[PlannerRequisite, ...] = ()
    presentations: tuple[PlannerPresentation, ...] = ()


class PlannerRegistryRepository(Protocol):
    def list_configs(self, subject_code: str | None = None) -> list[PlannerSourceConfig]: ...

    def get_config(self, source_key: str) -> PlannerSourceConfig | None: ...

    def replace_config(self, config: PlannerSourceConfig) -> None: ...

    def replace_configs(self, configs: Sequence[PlannerSourceConfig]) -> None: ...

    def delete_config(self, source_key: str) -> None: ...


class InMemoryPlannerRegistryRepository:
    def __init__(self, configs: Iterable[PlannerSourceConfig] = ()) -> None:
        self._configs = {item.source.source_key: copy.deepcopy(item) for item in configs}

    def list_configs(self, subject_code: str | None = None) -> list[PlannerSourceConfig]:
        rows = [
            copy.deepcopy(item)
            for item in self._configs.values()
            if subject_code is None or item.source.subject_code == subject_code
        ]
        return sorted(rows, key=lambda item: (item.source.sort_order, item.source.source_key))

    def get_config(self, source_key: str) -> PlannerSourceConfig | None:
        item = self._configs.get(source_key)
        return copy.deepcopy(item) if item is not None else None

    def replace_config(self, config: PlannerSourceConfig) -> None:
        self.replace_configs((config,))

    def replace_configs(self, configs: Sequence[PlannerSourceConfig]) -> None:
        next_state = dict(self._configs)
        for config in configs:
            next_state[config.source.source_key] = copy.deepcopy(config)
        self._configs = next_state

    def delete_config(self, source_key: str) -> None:
        next_state = dict(self._configs)
        next_state.pop(source_key, None)
        self._configs = next_state


class PlannerRegistryValidator:
    _single_semantic_roles = {
        SemanticRole.LABEL,
        SemanticRole.START,
        SemanticRole.END,
        SemanticRole.COLOR,
        SemanticRole.GROUP,
    }

    def __init__(self, catalog: AdminCatalog) -> None:
        self.catalog = catalog

    def validate(self, config: PlannerSourceConfig) -> None:
        source = config.source
        _validate_stable_key(source.source_key, "source_key")
        _validate_stable_key(source.subject_code, "subject_code")

        if source.table_key not in self.catalog.tables:
            raise PlannerValidationError(
                f"Источник {source.source_key!r} ссылается на отсутствующую таблицу {source.table_key!r}."
            )
        if not source.caption.strip():
            raise PlannerValidationError("У источника не заполнено пользовательское наименование.")

        identity = self.catalog.fields.get((source.table_key, source.identity_field_name))
        if identity is None:
            raise PlannerValidationError(
                f"Поле идентичности {source.table_key}.{source.identity_field_name} отсутствует в admin_table_fields."
            )
        primary_keys = [item for item in self.catalog.table_fields(source.table_key) if item.is_pk]
        if len(primary_keys) != 1 or not identity.is_pk:
            names = ", ".join(item.field_name for item in primary_keys) or "не найдены"
            raise PlannerValidationError(
                f"MVP поддерживает один первичный ключ. Для {source.table_key} обнаружено: {names}."
            )

        roles = tuple(_enum_value(SourceRole, item, "роль источника") for item in config.roles)
        if not roles:
            raise PlannerValidationError("Нужно выбрать хотя бы одну роль источника.")
        if len(set(roles)) != len(roles):
            raise PlannerValidationError("Роли источника не должны повторяться.")

        self._validate_requisites(config)
        self._validate_presentations(config)

        if {SourceRole.RESOURCE, SourceRole.EVENT}.intersection(roles):
            if not any(item.is_default for item in config.presentations):
                raise PlannerValidationError(
                    "Для ресурса или события требуется одно представление по умолчанию."
                )

    def _validate_requisites(self, config: PlannerSourceConfig) -> None:
        source = config.source
        keys: set[str] = set()
        fields: set[str] = set()
        semantic_fields: dict[SemanticRole, str] = {}

        for item in config.requisites:
            _validate_stable_key(item.requisite_key, "requisite_key")
            if item.requisite_key in keys:
                raise PlannerValidationError(
                    f"Повторяется requisite_key={item.requisite_key!r}."
                )
            keys.add(item.requisite_key)

            if item.source_key != source.source_key:
                raise PlannerValidationError(
                    f"Реквизит {item.requisite_key!r} принадлежит другому source_key."
                )
            if item.field_name in fields:
                raise PlannerValidationError(
                    f"Поле {item.field_name!r} добавлено в реквизиты дважды."
                )
            fields.add(item.field_name)

            field_meta = self.catalog.fields.get((source.table_key, item.field_name))
            if field_meta is None:
                raise PlannerValidationError(
                    f"Реквизит ссылается на отсутствующее поле {source.table_key}.{item.field_name}."
                )
            role = _enum_value(SemanticRole, item.semantic_role, "семантическая роль")
            if role in self._single_semantic_roles and role in semantic_fields:
                raise PlannerValidationError(
                    f"Роль {role.value!r} уже назначена полю {semantic_fields[role]!r}."
                )
            semantic_fields[role] = item.field_name

    def _validate_presentations(self, config: PlannerSourceConfig) -> None:
        source = config.source
        keys: set[str] = set()
        defaults = 0

        for item in config.presentations:
            _validate_stable_key(item.presentation_key, "presentation_key")
            if item.presentation_key in keys:
                raise PlannerValidationError(
                    f"Повторяется presentation_key={item.presentation_key!r}."
                )
            keys.add(item.presentation_key)
            if item.source_key != source.source_key:
                raise PlannerValidationError(
                    f"Представление {item.presentation_key!r} принадлежит другому source_key."
                )
            if not item.caption.strip():
                raise PlannerValidationError(
                    f"У представления {item.presentation_key!r} не заполнено наименование."
                )
            if (source.table_key, item.source_field_name) not in self.catalog.fields:
                raise PlannerValidationError(
                    f"Поле представления {source.table_key}.{item.source_field_name} отсутствует."
                )
            if (item.result_table_key, item.result_field_name) not in self.catalog.fields:
                raise PlannerValidationError(
                    f"Результат представления {item.result_table_key}.{item.result_field_name} отсутствует."
                )
            if item.missing_policy not in {"none", "error"}:
                raise PlannerValidationError(
                    f"missing_policy={item.missing_policy!r} не поддерживается в MVP."
                )
            if item.on_many_policy != "error":
                raise PlannerValidationError(
                    f"on_many_policy={item.on_many_policy!r} не поддерживается в MVP."
                )
            if len(item.relation_steps) > 1:
                raise PlannerValidationError(
                    "MVP поддерживает прямое поле либо один явный relation-step."
                )

            if item.relation_steps:
                self._validate_relation_presentation(source, item)
            elif item.result_table_key != source.table_key:
                raise PlannerValidationError(
                    "Прямое представление не может читать поле из другой таблицы."
                )

            defaults += int(item.is_default)

        if defaults > 1:
            raise PlannerValidationError(
                "Для одного источника допускается только одно представление по умолчанию."
            )

    def _validate_relation_presentation(
        self,
        source: PlannerSource,
        presentation: PlannerPresentation,
    ) -> None:
        relation_key = presentation.relation_steps[0]
        relation = self.catalog.relations.get(relation_key)
        if relation is None or not relation.is_enabled:
            raise PlannerValidationError(
                f"Связь {relation_key!r} отсутствует или выключена."
            )
        if relation.source_table_key != source.table_key:
            raise PlannerValidationError(
                f"Связь {relation_key!r} начинается не от таблицы {source.table_key!r}."
            )
        if relation.target_table_key != presentation.result_table_key:
            raise PlannerValidationError(
                f"Связь {relation_key!r} ведёт в {relation.target_table_key!r}, а представление — в {presentation.result_table_key!r}."
            )
        if relation.cardinality not in {"one_to_one", "many_to_one"}:
            raise PlannerValidationError(
                f"Связь {relation_key!r} имеет cardinality={relation.cardinality!r}; скалярное представление запрещено."
            )
        if not relation.field_pairs:
            raise PlannerValidationError(
                f"У связи {relation_key!r} не зарегистрированы пары полей."
            )
        if any(item.operator != "=" for item in relation.field_pairs):
            raise PlannerValidationError(
                f"Связь {relation_key!r} использует неподдерживаемый оператор."
            )
        if not any(
            pair.left_table_key == source.table_key
            and pair.left_field_name == presentation.source_field_name
            for pair in relation.field_pairs
        ):
            raise PlannerValidationError(
                f"Поле {presentation.source_field_name!r} не участвует в связи {relation_key!r}."
            )


class PlannerRegistryService:
    def __init__(
        self,
        catalog: AdminCatalog,
        repository: PlannerRegistryRepository,
    ) -> None:
        self.catalog = catalog
        self.repository = repository
        self.validator = PlannerRegistryValidator(catalog)

    def list_configs(self, subject_code: str | None = None) -> list[PlannerSourceConfig]:
        return self.repository.list_configs(subject_code)

    def get_config(self, source_key: str) -> PlannerSourceConfig | None:
        return self.repository.get_config(source_key)

    def save_config(self, config: PlannerSourceConfig) -> None:
        self.save_configs((config,))

    def save_configs(self, configs: Sequence[PlannerSourceConfig]) -> None:
        normalized_items = tuple(_normalize_config(item) for item in configs)
        if not normalized_items:
            return

        source_keys: set[str] = set()
        for item in normalized_items:
            self.validator.validate(item)
            if item.source.source_key in source_keys:
                raise PlannerValidationError(
                    f"В пакетной записи повторяется source_key={item.source.source_key!r}."
                )
            source_keys.add(item.source.source_key)

        next_configs = {
            item.source.source_key: item for item in self.repository.list_configs()
        }
        next_configs.update(
            {item.source.source_key: item for item in normalized_items}
        )
        registered_tables: dict[tuple[str, str], str] = {}
        for item in next_configs.values():
            key = (item.source.subject_code, item.source.table_key)
            previous_source_key = registered_tables.get(key)
            if previous_source_key is not None and previous_source_key != item.source.source_key:
                raise PlannerValidationError(
                    f"Таблица {item.source.table_key!r} уже зарегистрирована как "
                    f"{previous_source_key!r} в предметной области {item.source.subject_code!r}."
                )
            registered_tables[key] = item.source.source_key

        replace_many = getattr(self.repository, "replace_configs", None)
        if not callable(replace_many):
            if len(normalized_items) != 1:
                raise PlannerRepositoryError(
                    "Хранилище не поддерживает атомарную пакетную регистрацию."
                )
            self.repository.replace_config(normalized_items[0])
            return
        replace_many(normalized_items)

    def delete_config(self, source_key: str) -> None:
        self.repository.delete_config(source_key)


class PlannerPresentationResolver:
    def __init__(self, catalog: AdminCatalog) -> None:
        self.catalog = catalog

    def resolve(
        self,
        source_table_key: str,
        source_row: Mapping[str, Any],
        presentation: PlannerPresentation,
        rows_by_table: Mapping[str, Sequence[Mapping[str, Any]]],
    ) -> Any:
        if not presentation.relation_steps:
            return source_row.get(presentation.result_field_name)

        relation = self.catalog.relations[presentation.relation_steps[0]]
        if relation.source_table_key != source_table_key:
            raise PlannerValidationError(
                f"Связь {relation.relation_key!r} не начинается от {source_table_key!r}."
            )
        matches = []
        for target_row in rows_by_table.get(relation.target_table_key, ()):
            if all(
                source_row.get(pair.left_field_name) == target_row.get(pair.right_field_name)
                for pair in relation.field_pairs
            ):
                matches.append(target_row)

        if not matches:
            if presentation.missing_policy == "error":
                raise PlannerValidationError(
                    f"Для связи {relation.relation_key!r} не найдена целевая запись."
                )
            return None
        if len(matches) > 1:
            raise PlannerValidationError(
                f"Связь {relation.relation_key!r} вернула {len(matches)} строк вместо одной."
            )
        return matches[0].get(presentation.result_field_name)


class ContextAdminCatalogAdapter:
    def __init__(self, context_admin_repo: Any) -> None:
        self.context_admin_repo = context_admin_repo

    def load(self) -> AdminCatalog:
        try:
            table_rows = self.context_admin_repo.get_physical_tables() or []
            field_rows = self.context_admin_repo.get_table_fields() or []
            relation_rows = self.context_admin_repo.get_relations() or []
            pair_rows = self.context_admin_repo.get_relation_field_pairs() or []
        except Exception as exc:
            raise PlannerRepositoryError(
                f"Не удалось прочитать административный каталог: {exc}"
            ) from exc
        return AdminCatalog.from_rows(table_rows, field_rows, relation_rows, pair_rows)


@dataclass(frozen=True)
class CustOrmModels:
    source: type
    role: type
    requisite: type
    presentation: type
    presentation_step: type


def build_cust_orm_models(
    corm_module: Any | None = None,
    *,
    planner_schema: str = PLANNER_SCHEMA,
) -> CustOrmModels:
    corm = corm_module or _import_cust_orm()
    _validate_sql_identifier(planner_schema, "схема planner")
    table_names = {
        "source": f"{planner_schema}.planner_sources",
        "role": f"{planner_schema}.planner_source_roles",
        "requisite": f"{planner_schema}.planner_requisites",
        "presentation": f"{planner_schema}.planner_presentations",
        "presentation_step": f"{planner_schema}.planner_presentation_steps",
    }

    class PlannerSourceRow(corm.BaseModel):
        __table__ = table_names["source"]
        __db_key__ = "planner_registry"
        __table_key__ = table_names["source"]
        __db__ = "planner_registry"
        ALIASES = {}

        source_key: str = corm.StrField(primary_key=True, nullable=False)
        subject_code: str = corm.StrField(nullable=False)
        table_key: str = corm.StrField(nullable=False)
        caption: str = corm.StrField(nullable=False)
        identity_field_name: str = corm.StrField(nullable=False)
        is_enabled: int = corm.IntField(default=1, nullable=False)
        sort_order: int = corm.IntField(default=0, nullable=False)

    class PlannerSourceRoleRow(corm.BaseModel):
        __table__ = table_names["role"]
        __db_key__ = "planner_registry"
        __table_key__ = table_names["role"]
        __db__ = "planner_registry"
        ALIASES = {}

        role_key: str = corm.StrField(primary_key=True, nullable=False)
        source_key: str = corm.StrField(nullable=False)
        role: str = corm.StrField(nullable=False)

    class PlannerRequisiteRow(corm.BaseModel):
        __table__ = table_names["requisite"]
        __db_key__ = "planner_registry"
        __table_key__ = table_names["requisite"]
        __db__ = "planner_registry"
        ALIASES = {}

        requisite_key: str = corm.StrField(primary_key=True, nullable=False)
        source_key: str = corm.StrField(nullable=False)
        table_key: str = corm.StrField(nullable=False)
        field_name: str = corm.StrField(nullable=False)
        caption: str = corm.StrField(nullable=False)
        is_selectable: int = corm.IntField(default=1, nullable=False)
        is_filterable: int = corm.IntField(default=0, nullable=False)
        is_groupable: int = corm.IntField(default=0, nullable=False)
        semantic_role: str = corm.StrField(default="attribute", nullable=False)
        sort_order: int = corm.IntField(default=0, nullable=False)

    class PlannerPresentationRow(corm.BaseModel):
        __table__ = table_names["presentation"]
        __db_key__ = "planner_registry"
        __table_key__ = table_names["presentation"]
        __db__ = "planner_registry"
        ALIASES = {}

        presentation_key: str = corm.StrField(primary_key=True, nullable=False)
        source_key: str = corm.StrField(nullable=False)
        source_table_key: str = corm.StrField(nullable=False)
        source_field_name: str = corm.StrField(nullable=False)
        result_table_key: str = corm.StrField(nullable=False)
        result_field_name: str = corm.StrField(nullable=False)
        caption: str = corm.StrField(nullable=False)
        presentation_kind: str = corm.StrField(nullable=False)
        missing_policy: str = corm.StrField(default="none", nullable=False)
        on_many_policy: str = corm.StrField(default="error", nullable=False)
        is_default: int = corm.IntField(default=0, nullable=False)
        sort_order: int = corm.IntField(default=0, nullable=False)

    class PlannerPresentationStepRow(corm.BaseModel):
        __table__ = table_names["presentation_step"]
        __db_key__ = "planner_registry"
        __table_key__ = table_names["presentation_step"]
        __db__ = "planner_registry"
        ALIASES = {}

        presentation_step_key: str = corm.StrField(primary_key=True, nullable=False)
        presentation_key: str = corm.StrField(nullable=False)
        step_no: int = corm.IntField(default=0, nullable=False)
        relation_key: str = corm.StrField(nullable=False)

    return CustOrmModels(
        source=PlannerSourceRow,
        role=PlannerSourceRoleRow,
        requisite=PlannerRequisiteRow,
        presentation=PlannerPresentationRow,
        presentation_step=PlannerPresentationStepRow,
    )


class CustOrmPlannerRegistryRepository:
    def __init__(
        self,
        transaction_factory: Callable[..., Any],
        *,
        corm_module: Any | None = None,
        planner_schema: str = PLANNER_SCHEMA,
    ) -> None:
        self.transaction_factory = transaction_factory
        self.corm = corm_module or _import_cust_orm()
        self.models = build_cust_orm_models(
            self.corm,
            planner_schema=planner_schema,
        )

    def list_configs(self, subject_code: str | None = None) -> list[PlannerSourceConfig]:
        try:
            with self._transaction(write=False) as executor:
                query = self.models.source.query(db="planner_registry", executor=executor)
                if subject_code is not None:
                    query = query.filter(subject_code=subject_code)
                sources = query.order_by("sort_order", "source_key").all()
                return [self._load_config(item, executor) for item in sources]
        except PlannerRegistryError:
            raise
        except Exception as exc:
            raise PlannerRepositoryError(
                f"Не удалось прочитать регистрации планировщика: {exc}"
            ) from exc

    def get_config(self, source_key: str) -> PlannerSourceConfig | None:
        try:
            with self._transaction(write=False) as executor:
                row = (
                    self.models.source.query(db="planner_registry", executor=executor)
                    .filter(source_key=source_key)
                    .first()
                )
                return None if row is None else self._load_config(row, executor)
        except PlannerRegistryError:
            raise
        except Exception as exc:
            raise PlannerRepositoryError(
                f"Не удалось прочитать источник {source_key!r}: {exc}"
            ) from exc

    def replace_config(self, config: PlannerSourceConfig) -> None:
        self.replace_configs((config,))

    def replace_configs(self, configs: Sequence[PlannerSourceConfig]) -> None:
        try:
            with self._transaction(write=True) as executor:
                for config in configs:
                    self._replace_config(config, executor)
        except PlannerRegistryError:
            raise
        except Exception as exc:
            raise PlannerRepositoryError(
                f"Пакетная регистрация отменена: {exc}"
            ) from exc

    def _replace_config(
        self,
        config: PlannerSourceConfig,
        executor: Any,
    ) -> None:
        existing = (
            self.models.source.query(db="planner_registry", executor=executor)
            .filter(source_key=config.source.source_key)
            .first()
        )
        self._delete_children(config.source.source_key, executor)
        values = {
            "subject_code": config.source.subject_code,
            "table_key": config.source.table_key,
            "caption": config.source.caption,
            "identity_field_name": config.source.identity_field_name,
            "is_enabled": int(config.source.is_enabled),
            "sort_order": config.source.sort_order,
        }
        if existing is None:
            self.models.source.create(
                db="planner_registry",
                executor=executor,
                source_key=config.source.source_key,
                **values,
            )
        else:
            existing.update(**values)

        for role in config.roles:
            self.models.role.create(
                db="planner_registry",
                executor=executor,
                role_key=_role_key(config.source.source_key, role),
                source_key=config.source.source_key,
                role=role.value,
            )
        for item in config.requisites:
            self.models.requisite.create(
                db="planner_registry",
                executor=executor,
                requisite_key=item.requisite_key,
                source_key=item.source_key,
                table_key=config.source.table_key,
                field_name=item.field_name,
                caption=item.caption,
                is_selectable=int(item.is_selectable),
                is_filterable=int(item.is_filterable),
                is_groupable=int(item.is_groupable),
                semantic_role=item.semantic_role.value,
                sort_order=item.sort_order,
            )
        for item in config.presentations:
            self.models.presentation.create(
                db="planner_registry",
                executor=executor,
                presentation_key=item.presentation_key,
                source_key=item.source_key,
                source_table_key=config.source.table_key,
                source_field_name=item.source_field_name,
                result_table_key=item.result_table_key,
                result_field_name=item.result_field_name,
                caption=item.caption,
                presentation_kind=item.kind.value,
                missing_policy=item.missing_policy,
                on_many_policy=item.on_many_policy,
                is_default=int(item.is_default),
                sort_order=item.sort_order,
            )
            for step_no, relation_key in enumerate(item.relation_steps):
                self.models.presentation_step.create(
                    db="planner_registry",
                    executor=executor,
                    presentation_step_key=_step_key(item.presentation_key, step_no),
                    presentation_key=item.presentation_key,
                    step_no=step_no,
                    relation_key=relation_key,
                )

    def delete_config(self, source_key: str) -> None:
        try:
            with self._transaction(write=True) as executor:
                row = (
                    self.models.source.query(db="planner_registry", executor=executor)
                    .filter(source_key=source_key)
                    .first()
                )
                if row is not None:
                    row.delete()
        except PlannerRegistryError:
            raise
        except Exception as exc:
            raise PlannerRepositoryError(
                f"Удаление регистрации {source_key!r} отменено: {exc}"
            ) from exc

    @contextlib.contextmanager
    def _transaction(self, *, write: bool):
        manager = self.transaction_factory(write=write)
        if manager is None:
            raise PlannerRepositoryError("Фабрика не вернула контекст транзакции.")
        with manager as executor:
            if executor is None:
                raise PlannerRepositoryError(
                    "Контекст транзакции не вернул SQL executor."
                )
            yield executor

    def _load_config(self, source_row: Any, executor: Any) -> PlannerSourceConfig:
        source_key = source_row.source_key
        roles = tuple(
            SourceRole(item.role)
            for item in self._children(self.models.role, source_key, executor, "role_key")
        )
        requisites = tuple(
            PlannerRequisite(
                requisite_key=item.requisite_key,
                source_key=item.source_key,
                field_name=item.field_name,
                caption=item.caption,
                is_selectable=bool(item.is_selectable),
                is_filterable=bool(item.is_filterable),
                is_groupable=bool(item.is_groupable),
                semantic_role=SemanticRole(item.semantic_role),
                sort_order=item.sort_order,
            )
            for item in self._children(self.models.requisite, source_key, executor, "sort_order", "requisite_key")
        )
        presentation_rows = self._children(
            self.models.presentation,
            source_key,
            executor,
            "sort_order",
            "presentation_key",
        )
        presentations = []
        for item in presentation_rows:
            steps = (
                self.models.presentation_step.query(db="planner_registry", executor=executor)
                .filter(presentation_key=item.presentation_key)
                .order_by("step_no")
                .all()
            )
            presentations.append(
                PlannerPresentation(
                    presentation_key=item.presentation_key,
                    source_key=item.source_key,
                    source_field_name=item.source_field_name,
                    result_table_key=item.result_table_key,
                    result_field_name=item.result_field_name,
                    caption=item.caption,
                    relation_steps=tuple(step.relation_key for step in steps),
                    missing_policy=item.missing_policy,
                    on_many_policy=item.on_many_policy,
                    is_default=bool(item.is_default),
                    sort_order=item.sort_order,
                )
            )
        return PlannerSourceConfig(
            source=PlannerSource(
                source_key=source_row.source_key,
                subject_code=source_row.subject_code,
                table_key=source_row.table_key,
                caption=source_row.caption,
                identity_field_name=source_row.identity_field_name,
                is_enabled=bool(source_row.is_enabled),
                sort_order=source_row.sort_order,
            ),
            roles=roles,
            requisites=requisites,
            presentations=tuple(presentations),
        )

    def _children(
        self,
        model: type,
        source_key: str,
        executor: Any,
        *order_by: str,
    ) -> list[Any]:
        query = model.query(db="planner_registry", executor=executor).filter(source_key=source_key)
        if order_by:
            query = query.order_by(*order_by)
        return list(query.all())

    def _delete_children(
        self,
        source_key: str,
        executor: Any,
    ) -> None:
        presentations = self._children(
            self.models.presentation,
            source_key,
            executor,
            "presentation_key",
        )
        for presentation in presentations:
            steps = (
                self.models.presentation_step.query(db="planner_registry", executor=executor)
                .filter(presentation_key=presentation.presentation_key)
                .all()
            )
            for item in steps:
                item.delete()
        for model in (
            self.models.presentation,
            self.models.requisite,
            self.models.role,
        ):
            for item in self._children(model, source_key, executor):
                item.delete()


def _import_cust_orm() -> Any:
    try:
        from project_cust_38 import Cust_orm as corm
    except ImportError as exc:
        raise PlannerRepositoryError(
            "Cust_orm не найден. Поместите модуль в окружение project_cust_38 "
            "либо передайте corm_module явно."
        ) from exc
    return corm


def _required_text(row: Mapping[str, Any], key: str, entity: str) -> str:
    value = str(row.get(key) or "").strip()
    if not value:
        raise PlannerCatalogError(f"В записи {entity} не заполнено поле {key!r}.")
    return value


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "да"}
    return bool(value)


def _validate_sql_identifier(value: str, caption: str) -> None:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(value or "")):
        raise PlannerRepositoryError(
            f"Некорректный SQL-идентификатор для {caption}: {value!r}."
        )


def _validate_stable_key(value: str, field_name: str) -> None:
    text = str(value or "").strip()
    if not text:
        raise PlannerValidationError(f"Не заполнено поле {field_name}.")
    if any(not (char.isalnum() or char in "._:-") for char in text):
        raise PlannerValidationError(
            f"Поле {field_name}={text!r} содержит пробелы или нестабильные символы."
        )


def _enum_value(enum_type: type[enum.Enum], value: Any, caption: str) -> Any:
    try:
        return value if isinstance(value, enum_type) else enum_type(value)
    except (TypeError, ValueError) as exc:
        raise PlannerValidationError(
            f"Неизвестная {caption}: {value!r}."
        ) from exc


def _normalize_config(config: PlannerSourceConfig) -> PlannerSourceConfig:
    roles = tuple(_enum_value(SourceRole, item, "роль источника") for item in config.roles)
    requisites = tuple(
        PlannerRequisite(
            requisite_key=item.requisite_key,
            source_key=item.source_key,
            field_name=item.field_name,
            caption=item.caption,
            is_selectable=bool(item.is_selectable),
            is_filterable=bool(item.is_filterable),
            is_groupable=bool(item.is_groupable),
            semantic_role=_enum_value(
                SemanticRole,
                item.semantic_role,
                "семантическая роль",
            ),
            sort_order=int(item.sort_order),
        )
        for item in config.requisites
    )
    return PlannerSourceConfig(
        source=config.source,
        roles=roles,
        requisites=requisites,
        presentations=tuple(config.presentations),
    )


def _stable_uuid(prefix: str, *parts: str) -> str:
    payload = "|".join(str(item) for item in parts)
    return f"{prefix}:{uuid.uuid5(uuid.NAMESPACE_URL, payload).hex}"


def _role_key(source_key: str, role: SourceRole) -> str:
    return _stable_uuid("role", source_key, role.value)


def _requisite_key(source_key: str, field_name: str) -> str:
    return _stable_uuid("req", source_key, field_name)


def _presentation_key(source_key: str, *parts: str) -> str:
    return _stable_uuid("pres", source_key, *parts)


def _step_key(presentation_key: str, step_no: int) -> str:
    return _stable_uuid("step", presentation_key, str(step_no))

PLANNER_CONNINFO_ENV = "MES_PLANNER_PG_DSN"
PLANNER_SUBJECT_CODE = "gant"
PRESENTATION_SEPARATOR = ";"
MAX_PRESENTATION_FIELDS = 2


class PlannerMesTypeError(PlannerRegistryError):
    """Справочники  нельзя безопасно передать в выбор типа."""


@dataclass(frozen=True)
class MesPresentationChoice:
    presentation_key: str
    caption: str
    source_field_name: str
    result_table_key: str
    result_field_name: str
    relation_steps: tuple[str, ...] = ()
    is_default: bool = False
    is_filterable: bool = False
    sort_order: int = 0
    db_type: str = ""
    comment: str = ""

    def to_ui_row(self) -> dict[str, Any]:
        return {
            "_name": self.presentation_key,
            "_presentation_key": self.presentation_key,
            "_is_filterable": self.is_filterable,
            "Поле": self.caption,
            "Тип": self.db_type,
            "Стандартный": "⭐" if self.is_default else "",
            "Комментарий": self.comment,
        }


@dataclass(frozen=True)
class MesFilterChoice:
    requisite_key: str
    field_name: str
    caption: str
    is_groupable: bool = False
    sort_order: int = 0


@dataclass(frozen=True)
class MesTypeChoice:
    source_key: str
    table_key: str
    caption: str
    identity_field_name: str
    presentations: tuple[MesPresentationChoice, ...]
    filters: tuple[MesFilterChoice, ...] = ()
    sort_order: int = 0

    @property
    def default_presentation(self) -> MesPresentationChoice:
        item = next((item for item in self.presentations if item.is_default), None)
        if item is None:
            raise PlannerMesTypeError(
                f"У справочника {self.caption!r} не назначено представление по умолчанию."
            )
        return item

    def presentation_template(self) -> list[dict[str, Any]]:
        return [item.to_ui_row() for item in self.presentations]

    def selected_presentations(
        self,
        value: str | Sequence[str] | None = None,
    ) -> tuple[MesPresentationChoice, ...]:
        if value is None or value == "":
            keys = [self.default_presentation.presentation_key]
        elif isinstance(value, str):
            keys = [item.strip() for item in value.split(PRESENTATION_SEPARATOR) if item.strip()]
        else:
            keys = [str(item).strip() for item in value if str(item).strip()]
        keys = list(dict.fromkeys(keys))
        if not keys:
            keys = [self.default_presentation.presentation_key]
        if len(keys) > MAX_PRESENTATION_FIELDS:
            raise PlannerMesTypeError(
                f"Можно выбрать не более {MAX_PRESENTATION_FIELDS} полей представления."
            )
        by_key = {item.presentation_key: item for item in self.presentations}
        missing = [key for key in keys if key not in by_key]
        if missing:
            raise PlannerMesTypeError(
                "Выбранные поля больше не зарегистрированы: " + ", ".join(missing)
            )
        return tuple(by_key[key] for key in keys)

    def selection_key(self, value: str | Sequence[str] | None = None) -> str:
        return PRESENTATION_SEPARATOR.join(
            item.presentation_key for item in self.selected_presentations(value)
        )

    def selection_caption(self, value: str | Sequence[str] | None = None) -> str:
        return " + ".join(item.caption for item in self.selected_presentations(value))


@dataclass(frozen=True)
class MesTypeEntry:
    token: str
    caption: str
    value: type
    source_key: str


class PlannerRuntimeSession:
    """Лениво создаёт один runtime на время жизни окна планировщика."""

    def __init__(
        self,
        runtime: Any | None = None,
        *,
        runtime_factory: Callable[[str], Any] | None = None,
        conninfo_provider: Callable[[], str] | None = None,
    ) -> None:
        def default_conninfo_provider():
            return "postgresql://mes_admin:Adr1959967!@srv-mes:5432/postgres"

        def default_runtime_factory(conninfo: str):
            return PlannerRegistryRuntime.connect(conninfo)

        self._runtime = runtime
        self._runtime_factory = runtime_factory or default_runtime_factory
        self._conninfo_provider = conninfo_provider or default_conninfo_provider
        self._lock = threading.RLock()
        self._closed = False

    @property
    def configured(self) -> bool:
        if self._runtime is not None:
            return True
        return bool(str(self._conninfo_provider() or "").strip())

    def get_runtime(self) -> Any:
        with self._lock:
            if self._closed:
                raise PlannerMesTypeError(
                    "Runtime справочников уже закрыт. Откройте окно планировщика повторно."
                )
            if self._runtime is not None:
                return self._runtime
            conninfo = str(self._conninfo_provider() or "").strip()
            if not conninfo:
                raise PlannerMesTypeError(
                    f"Не задана переменная окружения {PLANNER_CONNINFO_ENV}. "
                    "Справочники пока недоступны."
                )
            try:
                self._runtime = self._runtime_factory(conninfo)
            except PlannerRegistryError:
                raise
            except Exception as exc:
                raise PlannerMesTypeError(
                    f"Не удалось открыть runtime справочников: {exc}"
                ) from exc
            return self._runtime

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            runtime = self._runtime
            self._runtime = None
        if runtime is not None:
            runtime.close()


class PlannerMesTypeCatalog:
    def __init__(
        self,
        session: PlannerRuntimeSession | None = None,
        *,
        subject_code: str = PLANNER_SUBJECT_CODE,
    ) -> None:
        self.session = session or PlannerRuntimeSession()
        self.subject_code = subject_code
        self.warnings: tuple[str, ...] = ()
        self._types_by_source: dict[str, type] = {}
        self._choices_by_source: dict[str, MesTypeChoice] = {}

    @property
    def configured(self) -> bool:
        return self.session.configured

    def reload(self, mes_base_type: type) -> tuple[MesTypeEntry, ...]:
        runtime = self.session.get_runtime()
        admin_catalog = getattr(runtime, "catalog", None)
        configs = runtime.list_sources(
            self.subject_code,
            role=SourceRole.ATTRIBUTE,
        )
        warnings: list[str] = []
        choices: list[MesTypeChoice] = []
        for config in configs:
            choice = self._choice_from_config(config, warnings, admin_catalog)
            if choice is not None:
                choices.append(choice)

        choices.sort(key=lambda item: (item.sort_order, item.caption.casefold(), item.source_key))
        entries: list[MesTypeEntry] = []
        active_choices: dict[str, MesTypeChoice] = {}
        for choice in choices:
            type_value = self._types_by_source.get(choice.source_key)
            if type_value is None:
                type_value = self._make_type(choice, mes_base_type)
                self._types_by_source[choice.source_key] = type_value
            else:
                type_value._planner_choice = choice
            active_choices[choice.source_key] = choice
            entries.append(
                MesTypeEntry(
                    token=self._token(choice.source_key),
                    caption=choice.caption,
                    value=type_value,
                    source_key=choice.source_key,
                )
            )
        self._choices_by_source = active_choices
        self.warnings = tuple(warnings)
        return tuple(entries)

    def choice_for_type(self, type_value: type) -> MesTypeChoice:
        source_key = str(getattr(type_value, "_planner_source_key", "") or "")
        choice = self._choices_by_source.get(source_key)
        if choice is None:
            choice = getattr(type_value, "_planner_choice", None)
        if not isinstance(choice, MesTypeChoice):
            raise PlannerMesTypeError(
                "Выбранный тип не принадлежит зарегистрированному справочнику."
            )
        return choice

    def presentation_template(self, type_value: type) -> list[dict[str, Any]]:
        return self.choice_for_type(type_value).presentation_template()

    def default_presentation(self, type_value: type) -> MesPresentationChoice:
        return self.choice_for_type(type_value).default_presentation

    def type_for_source(
        self,
        source_key: str,
        mes_base_type: type,
        *,
        allow_placeholder: bool = False,
    ) -> type:
        source_key = str(source_key or "")
        type_value = self._types_by_source.get(source_key)
        if type_value is not None:
            return type_value
        choice = self._choices_by_source.get(source_key)
        if choice is None:
            if not allow_placeholder:
                raise PlannerMesTypeError(
                    f"Справочник {source_key!r} не зарегистрирован."
                )
            choice = MesTypeChoice(
                source_key=source_key,
                table_key="",
                caption=f"Недоступный справочник ({source_key})",
                identity_field_name="",
                presentations=(),
            )
        type_value = self._make_type(choice, mes_base_type)
        self._types_by_source[source_key] = type_value
        return type_value

    def close(self) -> None:
        self.session.close()

    @staticmethod
    def _choice_from_config(
        config: PlannerSourceConfig,
        warnings: list[str],
        admin_catalog: AdminCatalog | None = None,
    ) -> MesTypeChoice | None:
        if not config.source.is_enabled:
            return None
        if SourceRole.ATTRIBUTE not in config.roles:
            return None
        filter_fields = {
            item.field_name: item
            for item in config.requisites
            if item.is_selectable and item.is_filterable
        }
        presentations_list: list[MesPresentationChoice] = []
        for item in sorted(
            config.presentations,
            key=lambda value: (value.sort_order, value.caption.casefold(), value.presentation_key),
        ):
            field_meta = None
            if isinstance(admin_catalog, AdminCatalog):
                field_meta = admin_catalog.fields.get(
                    (item.result_table_key, item.result_field_name)
                )
            presentations_list.append(
                MesPresentationChoice(
                    presentation_key=item.presentation_key,
                    caption=item.caption,
                    source_field_name=item.source_field_name,
                    result_table_key=item.result_table_key,
                    result_field_name=item.result_field_name,
                    relation_steps=tuple(item.relation_steps),
                    is_default=item.is_default,
                    is_filterable=item.source_field_name in filter_fields,
                    sort_order=item.sort_order,
                    db_type="" if field_meta is None else field_meta.db_type,
                    comment="",
                )
            )
        presentations = tuple(presentations_list)
        if not presentations:
            warnings.append(
                f"Справочник {config.source.caption!r} скрыт: не зарегистрировано ни одного представления."
            )
            return None
        if not any(item.is_default for item in presentations):
            warnings.append(
                f"Справочник {config.source.caption!r} скрыт: не выбрано представление по умолчанию."
            )
            return None
        filters = tuple(
            MesFilterChoice(
                requisite_key=item.requisite_key,
                field_name=item.field_name,
                caption=item.caption,
                is_groupable=item.is_groupable,
                sort_order=item.sort_order,
            )
            for item in sorted(
                filter_fields.values(),
                key=lambda value: (value.sort_order, value.caption.casefold(), value.requisite_key),
            )
        )
        return MesTypeChoice(
            source_key=config.source.source_key,
            table_key=config.source.table_key,
            caption=config.source.caption,
            identity_field_name=config.source.identity_field_name,
            presentations=presentations,
            filters=filters,
            sort_order=config.source.sort_order,
        )

    @staticmethod
    def _make_type(choice: MesTypeChoice, mes_base_type: type) -> type:
        digest = hashlib.sha1(choice.source_key.encode("utf-8")).hexdigest()[:10]
        slug = re.sub(r"[^A-Za-z0-9_]+", "_", choice.source_key).strip("_")
        class_name = f"Mes_{slug or 'Source'}_{digest}"

        def template(cls) -> list[dict[str, Any]]:
            return cls._planner_choice.presentation_template()

        def default_presentation(cls) -> MesPresentationChoice:
            return cls._planner_choice.default_presentation

        def init_value(self, reference: Any = None) -> None:
            if reference is None:
                self.reference = None
                return
            parsed = MesEntityRef.deserialize(reference)
            if parsed.source_key != choice.source_key:
                raise PlannerMesTypeError(
                    f"Ссылка {parsed.source_key!r} не принадлежит справочнику {choice.source_key!r}."
                )
            self.reference = parsed

        def serialize_value(self) -> dict[str, Any] | None:
            return None if self.reference is None else self.reference.serialize()

        @classmethod
        def deserialize_value(cls, data: Any):
            return cls(data)

        def value_text(self) -> str:
            return "" if self.reference is None else str(self.reference)

        def value_repr(self) -> str:
            return f"{class_name}(reference={self.reference!r})"

        return type(
            class_name,
            (mes_base_type,),
            {
                "__module__": __name__,
                "_planner_source_key": choice.source_key,
                "_planner_table_key": choice.table_key,
                "_planner_choice": choice,
                "__init__": init_value,
                "__str__": value_text,
                "__repr__": value_repr,
                "serialize": serialize_value,
                "deserialize": deserialize_value,
                "template": classmethod(template),
                "default_presentation": classmethod(default_presentation),
            },
        )

    @staticmethod
    def _token(source_key: str) -> str:
        digest = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:12]
        return f"source_{digest}"

MES_ENTITY_REF_VERSION = 1
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 200
_IDENTITY_ALIAS = "__mes_identity"
_DISPLAY_ALIAS = "__mes_display"
_FILTER_ALIAS_PREFIX = "__mes_filter_"


class MesEntityError(PlannerRegistryError):
    """Экземпляр зарегистрированного справочника нельзя безопасно выбрать или восстановить."""


class MesQueryExecutor(Protocol):
    def __call__(
        self,
        db_key: str,
        sql: str,
        parameters: Sequence[Any],
    ) -> Sequence[Mapping[str, Any]]: ...


@dataclass(frozen=True)
class MesEntityRef:
    source_key: str
    identity: tuple[tuple[str, Any], ...]
    presentation_key: str
    display_snapshot: str
    version: int = MES_ENTITY_REF_VERSION

    def __post_init__(self) -> None:
        if self.version != MES_ENTITY_REF_VERSION:
            raise MesEntityError(
                f"Версия ссылки на сущность {self.version!r} не поддерживается."
            )
        if not self.source_key.strip():
            raise MesEntityError("В ссылке на сущность не задан source_key.")
        if not self.presentation_key.strip():
            raise MesEntityError("В ссылке на сущность не задан presentation_key.")
        if not self.identity:
            raise MesEntityError("В ссылке на сущность не задана идентичность строки.")
        names: set[str] = set()
        for name, value in self.identity:
            if not str(name).strip():
                raise MesEntityError("В идентичности строки найдено пустое имя поля.")
            if name in names:
                raise MesEntityError(f"Поле идентичности {name!r} указано несколько раз.")
            if value is None or not isinstance(value, (str, int, float, bool)):
                raise MesEntityError(
                    f"Значение идентичности {name!r} имеет неподдерживаемый тип."
                )
            names.add(name)

    @classmethod
    def create(
        cls,
        *,
        source_key: str,
        identity: Mapping[str, Any],
        presentation_key: str,
        display_snapshot: Any,
    ) -> "MesEntityRef":
        return cls(
            source_key=str(source_key),
            identity=tuple((str(name), value) for name, value in identity.items()),
            presentation_key=str(presentation_key),
            display_snapshot="" if display_snapshot is None else str(display_snapshot),
        )

    @classmethod
    def deserialize(cls, data: Any) -> "MesEntityRef":
        if isinstance(data, cls):
            return data
        if not isinstance(data, Mapping):
            raise MesEntityError("Ссылка на сущность должна быть словарём.")
        identity = data.get("identity")
        if isinstance(identity, Mapping):
            identity_items = tuple((str(name), value) for name, value in identity.items())
        elif isinstance(identity, (list, tuple)):
            try:
                identity_items = tuple((str(item[0]), item[1]) for item in identity)
            except (IndexError, TypeError) as exc:
                raise MesEntityError(
                    "В ссылке на сущность повреждена идентичность строки."
                ) from exc
        else:
            raise MesEntityError("В ссылке на сущность повреждена идентичность строки.")
        display_snapshot = data.get("display_snapshot")
        try:
            version = int(data.get("version", MES_ENTITY_REF_VERSION))
        except (TypeError, ValueError) as exc:
            raise MesEntityError("В ссылке на сущность повреждена версия формата.") from exc
        return cls(
            source_key=str(data.get("source_key") or ""),
            identity=identity_items,
            presentation_key=str(data.get("presentation_key") or ""),
            display_snapshot="" if display_snapshot is None else str(display_snapshot),
            version=version,
        )

    def serialize(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source_key": self.source_key,
            "identity": dict(self.identity),
            "presentation_key": self.presentation_key,
            "display_snapshot": self.display_snapshot,
        }

    @property
    def identity_dict(self) -> dict[str, Any]:
        return dict(self.identity)

    @property
    def identity_text(self) -> str:
        return ", ".join(f"{name}={value}" for name, value in self.identity)

    def __str__(self) -> str:
        return self.display_snapshot or self.identity_text


@dataclass(frozen=True)
class MesEntityRow:
    reference: MesEntityRef
    filter_values: tuple[tuple[str, Any], ...] = ()

    @property
    def display(self) -> str:
        return str(self.reference)

    @property
    def identity(self) -> dict[str, Any]:
        return self.reference.identity_dict

    @property
    def filters(self) -> dict[str, Any]:
        return dict(self.filter_values)


@dataclass(frozen=True)
class MesSearchPage:
    rows: tuple[MesEntityRow, ...]
    offset: int
    limit: int
    has_more: bool


@dataclass(frozen=True)
class MesEntityResolution:
    requested: MesEntityRef
    current: MesEntityRef | None
    resolved: bool
    reason: str = ""


@dataclass(frozen=True)
class MesEntitySelection:
    accepted: bool
    reference: MesEntityRef | None = None


@dataclass(frozen=True)
class _QueryLayout:
    db_key: str
    source_table_name: str
    identity_field_name: str
    display_expressions: tuple[str, ...]
    join_sql: str
    filter_fields: tuple[tuple[str, str, str], ...]


class MesEntityService:
    def __init__(
        self,
        catalog: AdminCatalog,
        executor: MesQueryExecutor,
        *,
        max_page_size: int = MAX_PAGE_SIZE,
    ) -> None:
        self.catalog = catalog
        self.executor = executor
        self.max_page_size = max(1, min(int(max_page_size), MAX_PAGE_SIZE))

    @classmethod
    def from_type_catalog(
        cls,
        type_catalog: Any,
        *,
        executor: MesQueryExecutor | None = None,
    ) -> "MesEntityService":
        runtime = type_catalog.session.get_runtime()
        catalog = getattr(runtime, "catalog", None)
        if not isinstance(catalog, AdminCatalog):
            raise MesEntityError("Runtime справочников не передал административный каталог.")
        runtime_executor = getattr(runtime, "entity_executor", None)
        return cls(catalog, executor or runtime_executor or CustMesQueryExecutor())

    def search(
        self,
        choice: Any,
        *,
        presentation_key: str | None = None,
        text: str = "",
        filters: Mapping[str, Any] | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> MesSearchPage:
        presentations = self._presentations(choice, presentation_key)
        page_size = max(1, min(int(limit), self.max_page_size))
        page_offset = max(0, int(offset))
        rows = self._select(
            choice,
            presentations,
            text=str(text or "").strip(),
            filters=filters or {},
            identity=None,
            limit=page_size + 1,
            offset=page_offset,
        )
        has_more = len(rows) > page_size
        return MesSearchPage(
            rows=tuple(rows[:page_size]),
            offset=page_offset,
            limit=page_size,
            has_more=has_more,
        )

    def resolve(self, choice: Any, reference: MesEntityRef) -> MesEntityResolution:
        reference = MesEntityRef.deserialize(reference)
        if reference.source_key != choice.source_key:
            raise MesEntityError(
                f"Ссылка {reference.source_key!r} не принадлежит справочнику {choice.source_key!r}."
            )
        presentations = self._presentations_or_none(choice, reference.presentation_key)
        if presentations is None:
            return MesEntityResolution(
                requested=reference,
                current=None,
                resolved=False,
                reason=(
                    f"Представление {reference.presentation_key!r} больше не зарегистрировано. "
                    "Сохранённый снимок оставлен без изменений."
                ),
            )
        identity = reference.identity_dict
        if set(identity) != {choice.identity_field_name}:
            return MesEntityResolution(
                requested=reference,
                current=None,
                resolved=False,
                reason=(
                    "Состав идентичности источника изменился. "
                    "Сохранённый снимок оставлен без изменений."
                ),
            )
        rows = self._select(
            choice,
            presentations,
            text="",
            filters={},
            identity=identity,
            limit=2,
            offset=0,
        )
        if not rows:
            return MesEntityResolution(
                requested=reference,
                current=None,
                resolved=False,
                reason="Строка источника не найдена. Сохранённая ссылка не удалена.",
            )
        if len(rows) > 1:
            raise MesEntityError(
                f"Идентичность {reference.identity_text} вернула несколько строк."
            )
        return MesEntityResolution(
            requested=reference,
            current=rows[0].reference,
            resolved=True,
        )

    def _select(
        self,
        choice: Any,
        presentations: Sequence[Any],
        *,
        text: str,
        filters: Mapping[str, Any],
        identity: Mapping[str, Any] | None,
        limit: int,
        offset: int,
    ) -> list[MesEntityRow]:
        layout = self._layout(choice, presentations)
        source_alias = "mes_src"
        identity_expression = f"{source_alias}.{_quote(layout.identity_field_name)}"
        select_parts = [
            f"{identity_expression} AS {_quote(_IDENTITY_ALIAS)}",
        ]
        for index, expression in enumerate(layout.display_expressions):
            select_parts.append(
                f"{expression} AS {_quote(_display_alias(index))}"
            )
        for index, (_, field_name, _) in enumerate(layout.filter_fields):
            select_parts.append(
                f"{source_alias}.{_quote(field_name)} AS "
                f"{_quote(_FILTER_ALIAS_PREFIX + str(index))}"
            )

        where_parts: list[str] = []
        parameters: list[Any] = []
        if identity is not None:
            expected = {layout.identity_field_name}
            if set(identity) != expected:
                raise MesEntityError(
                    f"Для {choice.source_key!r} ожидается идентичность {expected!r}."
                )
            where_parts.append(f"{identity_expression} = ?")
            parameters.append(identity[layout.identity_field_name])

        normalized_filters = self._normalize_filters(layout, filters)
        for field_name, value in normalized_filters:
            where_parts.append(f"{source_alias}.{_quote(field_name)} = ?")
            parameters.append(value)

        if text:
            search_expressions = [identity_expression, *layout.display_expressions]
            search_expressions.extend(
                f"{source_alias}.{_quote(field_name)}"
                for _, field_name, _ in layout.filter_fields
            )
            search_expressions = list(dict.fromkeys(search_expressions))
            where_parts.append(
                "(" + " OR ".join(
                    f"CAST({expression} AS TEXT) LIKE ? ESCAPE '\\'"
                    for expression in search_expressions
                ) + ")"
            )
            pattern = _like_pattern(text)
            parameters.extend(pattern for _ in search_expressions)

        sql = (
            "SELECT " + ", ".join(select_parts)
            + f" FROM {_quote(layout.source_table_name)} AS {source_alias}"
            + layout.join_sql
        )
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        order_parts: list[str] = []
        for expression in layout.display_expressions:
            order_parts.extend(
                (
                    f"{expression} IS NULL",
                    f"LOWER(CAST({expression} AS TEXT))",
                )
            )
        order_parts.append(f"LOWER(CAST({identity_expression} AS TEXT))")
        sql += " ORDER BY " + ", ".join(order_parts) + " LIMIT ? OFFSET ?"
        parameters.extend((int(limit), int(offset)))

        try:
            raw_rows = self.executor(layout.db_key, sql, tuple(parameters)) or ()
        except MesEntityError:
            raise
        except Exception as exc:
            raise MesEntityError(
                f"Не удалось прочитать строки справочника {choice.caption!r}: {exc}"
            ) from exc

        result: list[MesEntityRow] = []
        for raw_row in raw_rows:
            if not isinstance(raw_row, Mapping):
                raise MesEntityError("Исполнитель SQL вернул строку без имён колонок.")
            identity_value = raw_row.get(_IDENTITY_ALIAS)
            reference = MesEntityRef.create(
                source_key=choice.source_key,
                identity={layout.identity_field_name: identity_value},
                presentation_key=PRESENTATION_SEPARATOR.join(
                    item.presentation_key for item in presentations
                ),
                display_snapshot=_join_display_values(
                    raw_row.get(_display_alias(index))
                    for index in range(len(layout.display_expressions))
                ),
            )
            filter_values = tuple(
                (
                    requisite_key,
                    raw_row.get(_FILTER_ALIAS_PREFIX + str(index)),
                )
                for index, (requisite_key, _, _) in enumerate(layout.filter_fields)
            )
            result.append(MesEntityRow(reference=reference, filter_values=filter_values))
        return result

    def _layout(self, choice: Any, presentations: Sequence[Any]) -> _QueryLayout:
        source_table = self.catalog.tables.get(choice.table_key)
        if source_table is None: #todo зависимость  source_table.is_enabled  source_table.schema_enabled:
            raise MesEntityError(
                f"Таблица {choice.table_key!r} отсутствует или выключена в административном каталоге."
            )
        self._require_field(choice.table_key, choice.identity_field_name)
        source_alias = "mes_src"
        join_parts_sql: list[str] = []
        display_expressions: list[str] = []
        for index, presentation in enumerate(presentations):
            self._require_field(choice.table_key, presentation.source_field_name)
            if not presentation.relation_steps:
                if presentation.result_table_key != choice.table_key:
                    raise MesEntityError("Прямое представление указывает на другую таблицу.")
                self._require_field(choice.table_key, presentation.result_field_name)
                display_expressions.append(
                    f"{source_alias}.{_quote(presentation.result_field_name)}"
                )
                continue

            if len(presentation.relation_steps) != 1:
                raise MesEntityError("Поддерживается только один шаг скалярного представления.")
            relation_key = presentation.relation_steps[0]
            relation = self.catalog.relations.get(relation_key)
            if relation is None or not relation.is_enabled:
                raise MesEntityError(f"Связь {relation_key!r} отсутствует или выключена.")
            if relation.source_table_key != choice.table_key:
                raise MesEntityError(
                    f"Связь {relation_key!r} начинается не от {choice.table_key!r}."
                )
            target_table = self.catalog.tables.get(relation.target_table_key)
            if target_table is None: #todo зависимость target_table.is_enabled  target_table.schema_enabled:
                raise MesEntityError(
                    f"Целевая таблица связи {relation.target_table_key!r} недоступна."
                )
            if target_table.table_key != presentation.result_table_key:
                raise MesEntityError("Связь и представление указывают на разные таблицы.")
            if source_table.db_key != target_table.db_key:
                raise MesEntityError(
                    "Скалярное представление между разными базами пока не поддерживается."
                )
            if relation.cardinality not in {"many_to_one", "one_to_one"}:
                raise MesEntityError(
                    f"Связь {relation_key!r} не является скалярной."
                )
            if not relation.field_pairs:
                raise MesEntityError(f"У связи {relation_key!r} нет пар полей.")
            join_type = str(relation.join_type or "LEFT JOIN").upper()
            if join_type not in {"LEFT JOIN", "INNER JOIN"}:
                raise MesEntityError(
                    f"Связь {relation_key!r} использует неподдерживаемый тип JOIN."
                )
            target_alias = f"mes_view_{index}"
            relation_join_parts: list[str] = []
            for pair in relation.field_pairs:
                if pair.operator != "=":
                    raise MesEntityError(
                        f"Связь {relation_key!r} использует неподдерживаемый оператор."
                    )
                self._require_field(pair.left_table_key, pair.left_field_name)
                self._require_field(pair.right_table_key, pair.right_field_name)
                relation_join_parts.append(
                    f"{source_alias}.{_quote(pair.left_field_name)} = "
                    f"{target_alias}.{_quote(pair.right_field_name)}"
                )
            self._require_field(target_table.table_key, presentation.result_field_name)
            join_parts_sql.append(
                f" {join_type} {_quote(target_table.table_name)} AS {target_alias} ON "
                + " AND ".join(relation_join_parts)
            )
            display_expressions.append(
                f"{target_alias}.{_quote(presentation.result_field_name)}"
            )

        filter_fields: list[tuple[str, str, str]] = []
        for item in choice.filters:
            self._require_field(choice.table_key, item.field_name)
            filter_fields.append((item.requisite_key, item.field_name, item.caption))
        return _QueryLayout(
            db_key=source_table.db_key,
            source_table_name=source_table.table_name,
            identity_field_name=choice.identity_field_name,
            display_expressions=tuple(display_expressions),
            join_sql="".join(join_parts_sql),
            filter_fields=tuple(filter_fields),
        )

    def _normalize_filters(
        self,
        layout: _QueryLayout,
        filters: Mapping[str, Any],
    ) -> list[tuple[str, Any]]:
        if not filters:
            return []
        by_key: dict[str, str] = {}
        for requisite_key, field_name, _ in layout.filter_fields:
            by_key[requisite_key] = field_name
            by_key[field_name] = field_name
        result: list[tuple[str, Any]] = []
        used: set[str] = set()
        for key, value in filters.items():
            if value is None or value == "":
                continue
            field_name = by_key.get(str(key))
            if field_name is None:
                raise MesEntityError(f"Фильтр {key!r} не зарегистрирован для этого источника.")
            if field_name in used:
                raise MesEntityError(f"Фильтр по полю {field_name!r} указан несколько раз.")
            result.append((field_name, value))
            used.add(field_name)
        return result

    @staticmethod
    def _presentations(choice: Any, presentation_key: str | None) -> tuple[Any, ...]:
        selector = getattr(choice, "selected_presentations", None)
        if callable(selector):
            try:
                return tuple(selector(presentation_key))
            except Exception as exc:
                raise MesEntityError(str(exc)) from exc
        raw_keys = (
            [choice.default_presentation.presentation_key]
            if not presentation_key
            else [
                item.strip()
                for item in str(presentation_key).split(PRESENTATION_SEPARATOR)
                if item.strip()
            ]
        )
        keys = list(dict.fromkeys(raw_keys))
        if not keys or len(keys) > MAX_PRESENTATION_FIELDS:
            raise MesEntityError(
                f"Нужно выбрать от одного до {MAX_PRESENTATION_FIELDS} полей представления."
            )
        by_key = {item.presentation_key: item for item in choice.presentations}
        missing = [key for key in keys if key not in by_key]
        if missing:
            raise MesEntityError(
                "Выбранные поля больше не зарегистрированы: " + ", ".join(missing)
            )
        return tuple(by_key[key] for key in keys)

    @classmethod
    def _presentations_or_none(
        cls,
        choice: Any,
        presentation_key: str,
    ) -> tuple[Any, ...] | None:
        try:
            return cls._presentations(choice, presentation_key)
        except MesEntityError:
            return None

    def _require_field(self, table_key: str, field_name: str) -> None:
        if (table_key, field_name) not in self.catalog.fields:
            raise MesEntityError(
                f"Поле {table_key}.{field_name} отсутствует в административном каталоге."
            )


class CustMesQueryExecutor:
    """Передаёт SQLite/PG варианты через штатный ``Cust_SQLite.SqlQuery``."""

    def __call__(
        self,
        db_key: str,
        sql: str,
        parameters: Sequence[Any],
    ) -> Sequence[Mapping[str, Any]]:
        try:
            from project_cust_38 import Cust_SQLite as CSQ
        except Exception as exc:
            raise MesEntityError(f"Не удалось загрузить клиент баз: {exc}") from exc
        database = self._database(CSQ, db_key)
        kwargs: dict[str, Any] = {
            "rez_dict": True,
            "debug": False,
        }
        if parameters:
            kwargs["list_of_lists_c"] = [list(parameters)]
        query = CSQ.SqlQuery(
            sqlite=sql,
            postgres=_qmark_to_percent(sql),
        )
        rows = CSQ.custom_request_c(database, query, **kwargs)
        if rows in (None, False):
            return ()
        if not isinstance(rows, list):
            raise MesEntityError("Клиент базы вернул неожиданный формат ответа.")
        return rows

    @staticmethod
    def _database(csq_module: Any, db_key: str) -> Any:
        candidates = [db_key]
        if not str(db_key).lower().endswith(".db"):
            candidates.append(f"{db_key}.db")
        for candidate in candidates:
            database = csq_module.DB_NAMES[candidate]
            if database is not None:
                return database
        for database in csq_module.DB_NAMES:
            alias = str(getattr(database, "alias", ""))
            if alias.removesuffix(".db") == str(db_key).removesuffix(".db"):
                return database
        raise MesEntityError(
            f"Для db_key={db_key!r} не найден сервер в Cust_SQLite.DB_NAMES."
        )


class SqliteConnectionExecutor:
    def __init__(self, connection: sqlite3.Connection, db_key: str = "demo") -> None:
        self.connection = connection
        self.db_key = db_key

    def __call__(
        self,
        db_key: str,
        sql: str,
        parameters: Sequence[Any],
    ) -> Sequence[Mapping[str, Any]]:
        if db_key != self.db_key:
            raise MesEntityError(f"Демонстрационная база {db_key!r} не подключена.")
        cursor = self.connection.execute(sql, tuple(parameters))
        names = [item[0] for item in cursor.description or ()]
        return [dict(zip(names, row)) for row in cursor.fetchall()]


def select_mes_entity(
    parent: Any,
    service: MesEntityService,
    choice: Any,
    *,
    presentation_key: str | None = None,
    current: MesEntityRef | None = None,
) -> MesEntitySelection:
    try:
        from PyQt5 import QtCore, QtWidgets
    except Exception as exc:
        raise MesEntityError(f"Не удалось открыть окно выбора сущности: {exc}") from exc

    selected_presentations = service._presentations(choice, presentation_key)
    display_caption = " + ".join(item.caption for item in selected_presentations)

    class _MesEntityDialog(QtWidgets.QDialog):
        def __init__(self) -> None:
            super().__init__(parent)
            self.selected_reference: MesEntityRef | None = current
            self.page_offset = 0
            self.page: MesSearchPage | None = None
            self.setWindowTitle(f"Выбор: {choice.caption}")
            self.resize(920, 560)
            layout = QtWidgets.QVBoxLayout(self)

            current_text = "пока не выбрано" if current is None else str(current)
            self.current_label = QtWidgets.QLabel(f"Сейчас: {current_text}")
            self.current_label.setWordWrap(True)
            layout.addWidget(self.current_label)

            search_layout = QtWidgets.QHBoxLayout()
            self.search_edit = QtWidgets.QLineEdit()
            self.search_edit.setPlaceholderText(
                "Введите код, название или часть текста"
            )
            self.search_button = QtWidgets.QPushButton("Найти")
            search_layout.addWidget(self.search_edit, 1)
            search_layout.addWidget(self.search_button)
            layout.addLayout(search_layout)

            self.filter_edits: dict[str, Any] = {}
            if choice.filters:
                filter_group = QtWidgets.QGroupBox("Дополнительные фильтры")
                filter_layout = QtWidgets.QFormLayout(filter_group)
                for item in choice.filters:
                    editor = QtWidgets.QLineEdit()
                    editor.setPlaceholderText("Введите значение")
                    filter_layout.addRow(item.caption, editor)
                    self.filter_edits[item.requisite_key] = editor
                layout.addWidget(filter_group)

            self.table = QtWidgets.QTableWidget()
            headers = ["Код", display_caption] + [
                item.caption for item in choice.filters
            ]
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.horizontalHeader().setSectionResizeMode(
                1, QtWidgets.QHeaderView.Stretch
            )
            layout.addWidget(self.table, 1)

            page_layout = QtWidgets.QHBoxLayout()
            self.previous_button = QtWidgets.QPushButton("<--")
            self.next_button = QtWidgets.QPushButton("-->")
            self.status_label = QtWidgets.QLabel()
            page_layout.addWidget(self.previous_button)
            page_layout.addWidget(self.next_button)
            page_layout.addWidget(self.status_label, 1)
            layout.addLayout(page_layout)

            button_layout = QtWidgets.QHBoxLayout()
            self.clear_button = QtWidgets.QPushButton("Закрыть")
            self.cancel_button = QtWidgets.QPushButton("Отмена")
            self.select_button = QtWidgets.QPushButton("Использовать")
            self.select_button.setDefault(True)
            button_layout.addWidget(self.clear_button)
            button_layout.addStretch(1)
            button_layout.addWidget(self.cancel_button)
            button_layout.addWidget(self.select_button)
            layout.addLayout(button_layout)

            self.search_button.clicked.connect(self._search)
            self.search_edit.returnPressed.connect(self._search)
            self.previous_button.clicked.connect(self._previous)
            self.next_button.clicked.connect(self._next)
            self.select_button.clicked.connect(self._accept_current)
            self.clear_button.clicked.connect(self._clear)
            self.cancel_button.clicked.connect(self.reject)
            self.table.doubleClicked.connect(self._accept_current)
            self.table.itemSelectionChanged.connect(self._update_buttons)
            QtCore.QTimer.singleShot(0, self._search)

        def _filters(self) -> dict[str, str]:
            return {
                key: editor.text().strip()
                for key, editor in self.filter_edits.items()
                if editor.text().strip()
            }

        def _search(self) -> None:
            self.page_offset = 0
            self._load()

        def _previous(self) -> None:
            self.page_offset = max(0, self.page_offset - DEFAULT_PAGE_SIZE)
            self._load()

        def _next(self) -> None:
            if self.page is None or not self.page.has_more:
                return
            self.page_offset += self.page.limit
            self._load()

        def _load(self) -> None:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                self.page = service.search(
                    choice,
                    presentation_key=presentation_key,
                    text=self.search_edit.text(),
                    filters=self._filters(),
                    limit=DEFAULT_PAGE_SIZE,
                    offset=self.page_offset,
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Не удалось загрузить данные", str(exc))
                return
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()
            self._fill_table()

        def _fill_table(self) -> None:
            rows = () if self.page is None else self.page.rows
            self.table.setSortingEnabled(False)
            self.table.setRowCount(len(rows))
            for row_index, item in enumerate(rows):
                identity_item = QtWidgets.QTableWidgetItem(item.reference.identity_text)
                identity_item.setData(QtCore.Qt.UserRole, item.reference)
                self.table.setItem(row_index, 0, identity_item)
                self.table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(item.display))
                filter_values = item.filters
                for column_index, filter_choice in enumerate(choice.filters, 2):
                    value = filter_values.get(filter_choice.requisite_key)
                    self.table.setItem(
                        row_index,
                        column_index,
                        QtWidgets.QTableWidgetItem("" if value is None else str(value)),
                    )
            self.table.setSortingEnabled(True)
            if rows:
                self.table.selectRow(0)
            shown_from = self.page_offset + 1 if rows else 0
            shown_to = self.page_offset + len(rows)
            self.status_label.setText(f"Показаны строки {shown_from}–{shown_to}")
            self.previous_button.setEnabled(self.page_offset > 0)
            self.next_button.setEnabled(bool(self.page and self.page.has_more))
            self._update_buttons()

        def _current_reference(self) -> MesEntityRef | None:
            row = self.table.currentRow()
            if row < 0:
                return None
            item = self.table.item(row, 0)
            if item is None:
                return None
            value = item.data(QtCore.Qt.UserRole)
            return value if isinstance(value, MesEntityRef) else None

        def _update_buttons(self) -> None:
            self.select_button.setEnabled(self._current_reference() is not None)

        def _accept_current(self, *args: Any) -> None:
            reference = self._current_reference()
            if reference is None:
                return
            self.selected_reference = reference
            self.accept()

        def _clear(self) -> None:
            self.selected_reference = None
            self.accept()

    dialog = _MesEntityDialog()
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return MesEntitySelection(accepted=False, reference=current)
    return MesEntitySelection(accepted=True, reference=dialog.selected_reference)


def _quote(identifier: str) -> str:
    identifier = str(identifier or "")
    if not identifier:
        raise MesEntityError("В административном каталоге найден пустой SQL-идентификатор.")
    if "\x00" in identifier:
        raise MesEntityError("SQL-идентификатор содержит нулевой байт.")
    return '"' + identifier.replace('"', '""') + '"'


def _display_alias(index: int) -> str:
    return _DISPLAY_ALIAS if index == 0 else f"{_DISPLAY_ALIAS}_{index}"


def _join_display_values(values: Iterable[Any]) -> str:
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            result.append(text)
    return " ".join(result)


def _like_pattern(text: str) -> str:
    escaped = str(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"

PLANNER_DATABASE_ALIAS = "planner_registry"


class PlannerMesIntegrationError(PlannerRegistryError):
    """ контур планировщика не смог завершить операцию."""


class PlannerOrmExecutor:
    """адаптер Cust_orm к PostgreSQL-транзакции."""

    def __init__(self, transaction: postgres.PostgreSqlTransaction) -> None:
        self.transaction = transaction

    def execute(
        self,
        bd: str,
        query: str,
        *,
        params: Any = None,
        rez_dict: bool = False,
        one: bool = False,
        one_column: bool = False,
        attach_dbs: Iterable[str] | str | None = (),
    ) -> Any:
        del bd
        if attach_dbs:
            raise PlannerRepositoryError(
                "PostgreSQL registry не поддерживает SQLite ATTACH."
            )
        return self.transaction.custom_request_c(
            _qmark_to_percent(query),
            hat_c=False,
            list_of_lists_c=[] if params is None else params,
            rez_dict=rez_dict,
            one=one,
            one_column=one_column,
        )


class PostgresAdminCatalogReader:
    _queries = (
        (
            "tables",
            "SELECT * FROM public.admin_physical_tables "
            "ORDER BY db_key, table_name, table_key",
        ),
        (
            "fields",
            "SELECT * FROM public.admin_table_fields "
            "ORDER BY table_key, sort_order, field_name",
        ),
        (
            "relations",
            "SELECT * FROM public.admin_table_relations "
            "ORDER BY source_table_key, relation_name, relation_key",
        ),
        (
            "pairs",
            "SELECT * FROM public.admin_relation_field_pairs "
            "ORDER BY relation_key, pair_no",
        ),
    )

    def __init__(self, executor: postgres.PostgreSqlExecutor) -> None:
        self.executor = executor

    def load(self) -> AdminCatalog:
        for attempt in range(2):
            try:
                rows = self._load_once()
                return AdminCatalog.from_rows(
                    rows["tables"],
                    rows["fields"],
                    rows["relations"],
                    rows["pairs"],
                )
            except PlannerRegistryError:
                raise
            except BaseException as exc:
                if attempt == 0 and _is_disconnect_error(exc):
                    invalidate = getattr(self.executor, "invalidate_pool", None)
                    if callable(invalidate):
                        invalidate()
                    continue
                raise PlannerRepositoryError(
                    f"Не удалось прочитать единый снимок admin-каталога: {exc}"
                ) from exc
        raise AssertionError("Недостижимая ветка повторного чтения каталога.")

    def _load_once(self) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        with self.executor.transaction(
            PLANNER_DATABASE_ALIAS,
            read_only=True,
            isolation="REPEATABLE READ",
        ) as transaction:
            for key, sql in self._queries:
                rows = transaction.custom_request_c(
                    sql,
                    hat_c=False,
                    rez_dict=True,
                )
                result[key] = list(rows or ())
        return result


@contextlib.contextmanager
def planner_orm_transaction(
    executor: postgres.PostgreSqlExecutor,
    *,
    write: bool,
):
    try:
        with executor.transaction(
            PLANNER_DATABASE_ALIAS,
            read_only=not write,
            isolation="READ COMMITTED" if write else "REPEATABLE READ",
        ) as transaction:
            yield PlannerOrmExecutor(transaction)
    except postgres.PostgresCommitOutcomeUnknown as exc:
        raise PlannerCommitOutcomeUnknown(
            "PostgreSQL не подтвердил COMMIT planner.*. Автоматический повтор "
            "запрещён до проверки фактического состояния."
        ) from exc


@dataclass
class PlannerRegistryRuntime:
    executor: postgres.PostgreSqlExecutor
    catalog: AdminCatalog
    repository: CustOrmPlannerRegistryRepository
    service: PlannerRegistryService
    owns_executor: bool = False
    entity_executor: MesQueryExecutor = field(init=False)

    def __post_init__(self) -> None:
        self.entity_executor = CustMesQueryExecutor()

    @classmethod
    def connect(
        cls,
        conninfo: str | Callable[[], str] | None = None,
        *,
        executor: postgres.PostgreSqlExecutor | None = None,
        executor_config: postgres.ExecutorConfig | None = None,
        corm_module: Any | None = None,
    ) -> "PlannerRegistryRuntime":
        resolved_conninfo = conninfo() if callable(conninfo) else conninfo
        active_executor, owns_executor = _resolve_executor(
            resolved_conninfo,
            executor=executor,
            executor_config=executor_config,
        )
        try:
            catalog = PostgresAdminCatalogReader(active_executor).load()
            repository = CustOrmPlannerRegistryRepository(
                lambda *, write: planner_orm_transaction(
                    active_executor,
                    write=write,
                ),
                corm_module=corm_module,
                planner_schema=PLANNER_SCHEMA,
            )
            service = PlannerRegistryService(catalog, repository)
            return cls(
                executor=active_executor,
                catalog=catalog,
                repository=repository,
                service=service,
                owns_executor=owns_executor,
            )
        except BaseException:
            if owns_executor:
                active_executor.close()
            raise

    def install_schema(self) -> int:
        statements = _split_sql_statements(POSTGRES_MIGRATION_SQL)
        try:
            with self.executor.transaction(
                PLANNER_DATABASE_ALIAS,
                read_only=False,
            ) as transaction:
                for statement in statements:
                    transaction.custom_request_c(statement, hat_c=False)
        except postgres.PostgresCommitOutcomeUnknown as exc:
            raise PlannerCommitOutcomeUnknown(
                "PostgreSQL не подтвердил COMMIT миграции planner.*. "
                "Не запускайте миграцию повторно до проверки схемы."
            ) from exc
        except PlannerRegistryError:
            raise
        except Exception as exc:
            raise PlannerMesIntegrationError(
                f"Миграция planner.* отменена: {exc}"
            ) from exc
        return len(statements)

    def reload_catalog(self) -> AdminCatalog:
        catalog = PostgresAdminCatalogReader(self.executor).load()
        self.catalog = catalog
        self.service = PlannerRegistryService(catalog, self.repository)
        return catalog

    def list_sources(
        self,
        subject_code: str | None = None,
        *,
        role: SourceRole | str | None = None,
    ) -> list[PlannerSourceConfig]:
        items = self._read_with_one_disconnect_retry(
            lambda: self.service.list_configs(subject_code)
        )
        if role is None:
            return items
        normalized_role = (
            role if isinstance(role, SourceRole) else SourceRole(role)
        )
        return [item for item in items if normalized_role in item.roles]

    def get_source(self, source_key: str) -> PlannerSourceConfig | None:
        return self._read_with_one_disconnect_retry(
            lambda: self.service.get_config(source_key)
        )

    def save_source(self, config: PlannerSourceConfig) -> None:
        self.service.save_config(config)

    def save_sources(self, configs: Sequence[PlannerSourceConfig]) -> None:
        self.service.save_configs(configs)

    def delete_source(self, source_key: str) -> None:
        self.service.delete_config(source_key)

    def available_tables(
        self,
        *,
        schema_enabled_only: bool = True,
    ) -> tuple[AdminTable, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self.catalog.tables.values()
                    if not schema_enabled_only or item.schema_enabled
                ),
                key=lambda item: (item.db_key, item.table_name, item.table_key),
            )
        )

    def available_fields(self, table_key: str) -> tuple[AdminField, ...]:
        return self.catalog.table_fields(table_key)

    def available_relations(
        self,
        table_key: str,
    ) -> tuple[AdminRelation, ...]:
        return self.catalog.outgoing_relations(table_key)

    def catalog_bundle(self) -> dict[str, Any]:
        relations = []
        pairs = []
        for relation in self.catalog.relations.values():
            relation_data = dataclasses.asdict(relation)
            relation_data.pop("field_pairs", None)
            relations.append(relation_data)
            pairs.extend(dataclasses.asdict(item) for item in relation.field_pairs)
        return {
            "tables": [
                dataclasses.asdict(item) for item in self.catalog.tables.values()
            ],
            "fields": [
                dataclasses.asdict(item) for item in self.catalog.fields.values()
            ],
            "relations": relations,
            "pairs": pairs,
        }

    def health(self) -> dict[str, Any]:
        return {
            "catalog": {
                "table_count": len(self.catalog.tables),
                "field_count": len(self.catalog.fields),
                "relation_count": len(self.catalog.relations),
                "pair_count": sum(
                    len(item.field_pairs) for item in self.catalog.relations.values()
                ),
            },
            "pool": self.executor.pool_stats(),
        }

    def close(self) -> None:
        if self.owns_executor:
            self.executor.close()

    def __enter__(self) -> "PlannerRegistryRuntime":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        self.close()
        return False

    def _read_with_one_disconnect_retry(self, operation: Callable[[], Any]) -> Any:
        for attempt in range(2):
            try:
                return operation()
            except BaseException as exc:
                if attempt == 0 and _is_disconnect_error(exc):
                    self.executor.invalidate_pool()
                    continue
                raise
        raise AssertionError("Недостижимая ветка повторного чтения.")


def _resolve_executor(
    conninfo: str | None,
    *,
    executor: postgres.PostgreSqlExecutor | None,
    executor_config: postgres.ExecutorConfig | None,
) -> tuple[postgres.PostgreSqlExecutor, bool]:
    if executor is not None:
        return executor, False
    normalized_conninfo = str(conninfo or "").strip()
    if executor_config is None:
        try:
            shared = postgres.get_default_executor()
        except postgres.PostgresConfigurationError:
            shared = None
        if shared is not None and (
            not normalized_conninfo
            or shared.config.conninfo.strip() == normalized_conninfo
        ):
            return shared, False
        executor_config = postgres.ExecutorConfig.from_env()
    if normalized_conninfo and executor_config.conninfo.strip() != normalized_conninfo:
        executor_config = dataclasses.replace(
            executor_config,
            conninfo=normalized_conninfo,
            application_name="mes_planner_registry",
        )
    return postgres.PostgreSqlExecutor(executor_config), True


def _qmark_to_percent(query: str) -> str:
    result: list[str] = []
    quote = ""
    index = 0
    while index < len(query):
        char = query[index]
        if quote:
            result.append(char)
            if char == quote:
                if index + 1 < len(query) and query[index + 1] == quote:
                    result.append(query[index + 1])
                    index += 1
                else:
                    quote = ""
        elif char in {"'", '"'}:
            quote = char
            result.append(char)
        elif char == "?":
            result.append("%s")
        else:
            result.append(char)
        index += 1
    return "".join(result)


def _split_sql_statements(sql: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(sql):
        char = sql[index]
        if quote is not None:
            buffer.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    buffer.append(sql[index + 1])
                    index += 1
                else:
                    quote = None
        elif char in {"'", '"'}:
            quote = char
            buffer.append(char)
        elif char == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer.clear()
        else:
            buffer.append(char)
        index += 1
    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return tuple(statements)


def _is_disconnect_error(error: BaseException) -> bool:
    current: BaseException | None = error
    while current is not None:
        sqlstate = str(
            getattr(current, "sqlstate", "")
            or getattr(current, "pgcode", "")
            or ""
        )
        if sqlstate.startswith("08") or sqlstate in {
            "57P01",
            "57P02",
            "57P03",
            "58P01",
        }:
            return True
        class_name = type(current).__name__.lower()
        message = str(current).lower()
        if class_name in {
            "operationalerror",
            "connectiontimeout",
            "poolclosed",
        } and any(
            token in message
            for token in (
                "connection",
                "server closed",
                "terminat",
                "broken",
                "network",
                "socket",
            )
        ):
            return True
        current = current.__cause__ or current.__context__
    return False

__all__ = [
    "PLANNER_SCHEMA",
    "ADMIN_SCHEMA",
    "POSTGRES_MIGRATION_SQL",
    "PLANNER_CONNINFO_ENV",
    "PLANNER_SUBJECT_CODE",
    "PRESENTATION_SEPARATOR",
    "MAX_PRESENTATION_FIELDS",
    "MES_ENTITY_REF_VERSION",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "PlannerRegistryError",
    "PlannerValidationError",
    "PlannerCatalogError",
    "PlannerRepositoryError",
    "PlannerCommitOutcomeUnknown",
    "SourceRole",
    "SemanticRole",
    "PresentationKind",
    "AdminTable",
    "AdminField",
    "RelationFieldPair",
    "AdminRelation",
    "AdminCatalog",
    "PlannerSource",
    "PlannerRequisite",
    "PlannerPresentation",
    "PlannerSourceConfig",
    "PlannerRegistryRepository",
    "InMemoryPlannerRegistryRepository",
    "PlannerRegistryValidator",
    "PlannerRegistryService",
    "PlannerPresentationResolver",
    "ContextAdminCatalogAdapter",
    "build_cust_orm_models",
    "CustOrmPlannerRegistryRepository",
    "PlannerMesTypeError",
    "MesPresentationChoice",
    "MesFilterChoice",
    "MesTypeChoice",
    "MesTypeEntry",
    "PlannerRuntimeSession",
    "PlannerMesTypeCatalog",
    "MesEntityError",
    "MesEntityRef",
    "MesEntityRow",
    "MesSearchPage",
    "MesEntityResolution",
    "MesEntitySelection",
    "MesEntityService",
    "CustMesQueryExecutor",
    "SqliteConnectionExecutor",
    "select_mes_entity",
    "PlannerMesIntegrationError",
    "PlannerOrmExecutor",
    "PostgresAdminCatalogReader",
    "PlannerRegistryRuntime",
]
