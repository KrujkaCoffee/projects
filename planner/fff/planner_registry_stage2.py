from __future__ import annotations

import contextlib
import copy
import enum
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence


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


class TransactionalPostgresExecutor:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

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
        if attach_dbs:
            raise PlannerRepositoryError(
                "PostgreSQL executor не поддерживает SQLite ATTACH."
            )
        sql = _qmark_to_percent(query)
        values = list(params or [])
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, values)
            if cursor.description is None:
                return True
            row = cursor.fetchone() if one else cursor.fetchall()
            if one:
                if row is None:
                    return None
                converted = _cursor_row_to_result(cursor, row, rez_dict)
                if one_column:
                    return _first_value(converted)
                return converted
            converted_rows = [
                _cursor_row_to_result(cursor, item, rez_dict) for item in (row or [])
            ]
            if one_column:
                return [_first_value(item) for item in converted_rows]
            return converted_rows
        finally:
            cursor.close()


class CustOrmPlannerRegistryRepository:
    def __init__(
        self,
        connection_factory: Callable[[], Any],
        *,
        corm_module: Any | None = None,
        close_connection: bool = True,
        planner_schema: str = PLANNER_SCHEMA,
    ) -> None:
        self.connection_factory = connection_factory
        self.corm = corm_module or _import_cust_orm()
        self.models = build_cust_orm_models(
            self.corm,
            planner_schema=planner_schema,
        )
        self.close_connection = close_connection

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
        executor: TransactionalPostgresExecutor,
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
        connection = self.connection_factory()
        if connection is None:
            raise PlannerRepositoryError("Фабрика PostgreSQL не вернула соединение.")
        previous_autocommit = getattr(connection, "autocommit", None)
        operation_error: BaseException | None = None
        commit_started = False
        try:
            if previous_autocommit is not None:
                connection.autocommit = False
            executor = TransactionalPostgresExecutor(connection)
            yield executor
            if write:
                commit_started = True
                connection.commit()
            else:
                connection.rollback()
        except BaseException as exc:
            if commit_started:
                operation_error = PlannerCommitOutcomeUnknown(
                    "PostgreSQL не подтвердил COMMIT. Автоматический повтор запрещён: "
                    "сначала нужно проверить фактическое состояние planner.*."
                )
                raise operation_error from exc
            operation_error = exc
            self._rollback_without_masking(connection, exc)
            raise
        finally:
            try:
                if self.close_connection:
                    connection.close()
                elif previous_autocommit is not None:
                    connection.autocommit = previous_autocommit
            except Exception as close_exc:
                message = f"Не удалось освободить PostgreSQL-соединение: {close_exc}"
                if operation_error is not None:
                    if hasattr(operation_error, "add_note"):
                        operation_error.add_note(message)
                else:
                    raise PlannerRepositoryError(message) from close_exc

    @staticmethod
    def _rollback_without_masking(connection: Any, original_error: BaseException) -> None:
        try:
            connection.rollback()
        except Exception as rollback_exc:
            if hasattr(original_error, "add_note"):
                original_error.add_note(
                    f"Дополнительно не удалось выполнить rollback: {rollback_exc}"
                )

    def _load_config(self, source_row: Any, executor: TransactionalPostgresExecutor) -> PlannerSourceConfig:
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
        executor: TransactionalPostgresExecutor,
        *order_by: str,
    ) -> list[Any]:
        query = model.query(db="planner_registry", executor=executor).filter(source_key=source_key)
        if order_by:
            query = query.order_by(*order_by)
        return list(query.all())

    def _delete_children(
        self,
        source_key: str,
        executor: TransactionalPostgresExecutor,
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


def _cursor_row_to_result(cursor: Any, row: Any, rez_dict: bool) -> Any:
    if not rez_dict or isinstance(row, Mapping):
        return row
    columns = [item[0] for item in cursor.description or ()]
    return {columns[index]: row[index] for index in range(len(columns))}


def _first_value(row: Any) -> Any:
    if isinstance(row, Mapping):
        return next(iter(row.values()), None)
    if isinstance(row, (tuple, list)):
        return row[0] if row else None
    return row


def build_demo_catalog() -> AdminCatalog:
    tables = [
        {"table_key": "DB_kplan.podrazdel", "db_key": "DB_kplan", "table_name": "podrazdel"},
        {"table_key": "DB_kplan.plan", "db_key": "DB_kplan", "table_name": "plan"},
        {"table_key": "Naryad.mk", "db_key": "Naryad", "table_name": "mk"},
        {"table_key": "Naryad.Тип_мк", "db_key": "Naryad", "table_name": "Тип_мк"},
    ]
    fields = [
        _demo_field("DB_kplan.podrazdel", "Пномер", "Код", "INTEGER", True, 0),
        _demo_field("DB_kplan.podrazdel", "Имя", "Имя", "TEXT", False, 1),
        _demo_field("DB_kplan.podrazdel", "Цвет", "Цвет", "TEXT", False, 2),
        _demo_field("DB_kplan.podrazdel", "alias", "Псевдоним", "TEXT", False, 3),
        _demo_field("DB_kplan.plan", "Пномер", "Код", "INTEGER", True, 0),
        _demo_field("DB_kplan.plan", "Позиция", "Позиция", "TEXT", False, 1),
        _demo_field("DB_kplan.plan", "Группа", "Группа", "TEXT", False, 2),
        _demo_field("Naryad.mk", "Пномер", "Номер МК", "INTEGER", True, 0),
        _demo_field("Naryad.mk", "Номенклатура", "Номенклатура", "TEXT", False, 1),
        _demo_field("Naryad.mk", "Тип", "Тип МК", "INTEGER", False, 2),
        _demo_field("Naryad.mk", "Дата", "Дата начала", "TEXT", False, 3),
        _demo_field("Naryad.mk", "Дата_завершения", "Дата завершения", "TEXT", False, 4),
        _demo_field("Naryad.mk", "НомКплан", "Позиция плана", "INTEGER", False, 5),
        _demo_field("Naryad.Тип_мк", "Пномер", "Код типа", "INTEGER", True, 0),
        _demo_field("Naryad.Тип_мк", "Имя", "Имя типа", "TEXT", False, 1),
        _demo_field("Naryad.Тип_мк", "rgb", "Цвет типа", "TEXT", False, 2),
    ]
    relations = [
        {
            "relation_key": "Naryad.mk.type",
            "relation_name": "Тип МК",
            "source_table_key": "Naryad.mk",
            "target_table_key": "Naryad.Тип_мк",
            "cardinality": "many_to_one",
            "join_type": "LEFT JOIN",
            "missing_policy": "none",
            "on_many_policy": "error",
            "is_enabled": 1,
        }
    ]
    pairs = [
        {
            "relation_key": "Naryad.mk.type",
            "pair_no": 0,
            "left_table_key": "Naryad.mk",
            "left_field_name": "Тип",
            "right_table_key": "Naryad.Тип_мк",
            "right_field_name": "Пномер",
            "role": "direct",
            "operator": "=",
            "pair_join_type": "",
        }
    ]
    return AdminCatalog.from_rows(tables, fields, relations, pairs)


def build_demo_configurations() -> tuple[PlannerSourceConfig, ...]:
    resource_key = "gant.resource.podrazdel"
    event_key = "gant.event.mk"
    return (
        PlannerSourceConfig(
            source=PlannerSource(
                source_key=resource_key,
                subject_code="gant",
                table_key="DB_kplan.podrazdel",
                caption="Подразделения",
                identity_field_name="Пномер",
                sort_order=10,
            ),
            roles=(SourceRole.RESOURCE,),
            requisites=(
                PlannerRequisite(
                    requisite_key=_requisite_key(resource_key, "Имя"),
                    source_key=resource_key,
                    field_name="Имя",
                    caption="Имя",
                    semantic_role=SemanticRole.LABEL,
                    sort_order=10,
                ),
                PlannerRequisite(
                    requisite_key=_requisite_key(resource_key, "Цвет"),
                    source_key=resource_key,
                    field_name="Цвет",
                    caption="Цвет",
                    semantic_role=SemanticRole.COLOR,
                    sort_order=20,
                ),
            ),
            presentations=(
                PlannerPresentation(
                    presentation_key=_presentation_key(resource_key, "default"),
                    source_key=resource_key,
                    source_field_name="Пномер",
                    result_table_key="DB_kplan.podrazdel",
                    result_field_name="Имя",
                    caption="Имя подразделения",
                    is_default=True,
                ),
            ),
        ),
        PlannerSourceConfig(
            source=PlannerSource(
                source_key=event_key,
                subject_code="gant",
                table_key="Naryad.mk",
                caption="Маршрутные карты",
                identity_field_name="Пномер",
                sort_order=20,
            ),
            roles=(SourceRole.EVENT,),
            requisites=(
                PlannerRequisite(
                    requisite_key=_requisite_key(event_key, "Номенклатура"),
                    source_key=event_key,
                    field_name="Номенклатура",
                    caption="Номенклатура",
                    semantic_role=SemanticRole.LABEL,
                    sort_order=10,
                ),
                PlannerRequisite(
                    requisite_key=_requisite_key(event_key, "Тип"),
                    source_key=event_key,
                    field_name="Тип",
                    caption="Тип МК",
                    sort_order=20,
                ),
                PlannerRequisite(
                    requisite_key=_requisite_key(event_key, "Дата"),
                    source_key=event_key,
                    field_name="Дата",
                    caption="Дата начала",
                    semantic_role=SemanticRole.START,
                    sort_order=30,
                ),
                PlannerRequisite(
                    requisite_key=_requisite_key(event_key, "Дата_завершения"),
                    source_key=event_key,
                    field_name="Дата_завершения",
                    caption="Дата завершения",
                    semantic_role=SemanticRole.END,
                    sort_order=40,
                ),
            ),
            presentations=(
                PlannerPresentation(
                    presentation_key=_presentation_key(event_key, "default"),
                    source_key=event_key,
                    source_field_name="Пномер",
                    result_table_key="Naryad.mk",
                    result_field_name="Номенклатура",
                    caption="Номенклатура МК",
                    is_default=True,
                    sort_order=10,
                ),
                PlannerPresentation(
                    presentation_key=_presentation_key(event_key, "type"),
                    source_key=event_key,
                    source_field_name="Тип",
                    result_table_key="Naryad.Тип_мк",
                    result_field_name="Имя",
                    caption="Имя типа МК",
                    relation_steps=("Naryad.mk.type",),
                    sort_order=20,
                ),
            ),
        ),
    )


def _demo_field(
    table_key: str,
    field_name: str,
    label: str,
    db_type: str,
    is_pk: bool,
    sort_order: int,
) -> dict[str, Any]:
    return {
        "table_key": table_key,
        "field_name": field_name,
        "label": label,
        "db_type": db_type,
        "nullable": int(not is_pk),
        "is_pk": int(is_pk),
        "sort_order": sort_order,
        "include_in_schema": 1,
    }


def _run_demo() -> int:
    try:
        from PyQt5 import QtCore, QtWidgets
    except ImportError as exc:
        raise SystemExit(
            "Для ручного GUI-теста нужен PyQt5.15: python -m pip install PyQt5==5.15.11"
        ) from exc

    class PresentationDialog(QtWidgets.QDialog):
        def __init__(self, catalog: AdminCatalog, table_key: str, parent=None) -> None:
            super().__init__(parent)
            self.catalog = catalog
            self.table_key = table_key
            self.setWindowTitle("Новое представление")
            layout = QtWidgets.QFormLayout(self)
            self.caption = QtWidgets.QLineEdit(self)
            self.kind = QtWidgets.QComboBox(self)
            self.kind.addItem("Прямое поле", PresentationKind.DIRECT.value)
            self.kind.addItem("Через relation", PresentationKind.RELATION.value)
            self.relation = QtWidgets.QComboBox(self)
            self.result_field = QtWidgets.QComboBox(self)
            self.is_default = QtWidgets.QCheckBox("Использовать по умолчанию", self)
            layout.addRow("Название", self.caption)
            layout.addRow("Тип", self.kind)
            layout.addRow("Связь", self.relation)
            layout.addRow("Результирующее поле", self.result_field)
            layout.addRow("", self.is_default)
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
                parent=self,
            )
            layout.addRow(buttons)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            self.kind.currentIndexChanged.connect(self._reload)
            self.relation.currentIndexChanged.connect(self._reload_result_fields)
            self._reload()

        def _reload(self) -> None:
            relation_mode = self.kind.currentData() == PresentationKind.RELATION.value
            self.relation.setEnabled(relation_mode)
            self.relation.blockSignals(True)
            self.relation.clear()
            if relation_mode:
                for item in self.catalog.outgoing_relations(self.table_key):
                    self.relation.addItem(
                        f"{item.relation_name} [{item.cardinality}]",
                        item.relation_key,
                    )
            self.relation.blockSignals(False)
            self._reload_result_fields()

        def _reload_result_fields(self) -> None:
            self.result_field.clear()
            table_key = self.table_key
            if self.kind.currentData() == PresentationKind.RELATION.value:
                relation = self.catalog.relations.get(str(self.relation.currentData() or ""))
                if relation is not None:
                    table_key = relation.target_table_key
            for item in self.catalog.table_fields(table_key):
                self.result_field.addItem(item.label or item.field_name, item.field_name)

        def build(self, source: PlannerSource, order: int) -> PlannerPresentation:
            relation_steps: tuple[str, ...] = ()
            source_field = source.identity_field_name
            result_table = source.table_key
            if self.kind.currentData() == PresentationKind.RELATION.value:
                relation = self.catalog.relations[str(self.relation.currentData())]
                if not relation.field_pairs:
                    raise PlannerValidationError(
                        f"У связи {relation.relation_key!r} нет пар полей."
                    )
                relation_steps = (relation.relation_key,)
                result_table = relation.target_table_key
                source_field = relation.field_pairs[0].left_field_name
            result_field = str(self.result_field.currentData() or "")
            key = _presentation_key(
                source.source_key,
                source_field,
                result_table,
                result_field,
                *relation_steps,
            )
            return PlannerPresentation(
                presentation_key=key,
                source_key=source.source_key,
                source_field_name=source_field,
                result_table_key=result_table,
                result_field_name=result_field,
                caption=self.caption.text().strip() or result_field,
                relation_steps=relation_steps,
                is_default=self.is_default.isChecked(),
                sort_order=order,
            )

    class DemoWindow(QtWidgets.QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.catalog = build_demo_catalog()
            self.repository = InMemoryPlannerRegistryRepository(build_demo_configurations())
            self.service = PlannerRegistryService(self.catalog, self.repository)
            self.current_table_key = ""
            self.current_presentations: list[PlannerPresentation] = []
            self.setWindowTitle("Stage 2.1 — регистрация источников Ганта")
            self.resize(1180, 760)
            self._build_ui(QtWidgets)
            self._reload_source_list()

        def _build_ui(self, widgets: Any) -> None:
            root = widgets.QWidget(self)
            self.setCentralWidget(root)
            layout = widgets.QVBoxLayout(root)
            info = widgets.QLabel(
                "Стенд работает в памяти: продактовые БД и admin_* не изменяются.", root
            )
            layout.addWidget(info)
            splitter = widgets.QSplitter(QtCore.Qt.Horizontal, root)
            layout.addWidget(splitter, 1)

            left = widgets.QWidget(splitter)
            left_layout = widgets.QVBoxLayout(left)
            left_layout.addWidget(widgets.QLabel("Физические таблицы", left))
            self.source_list = widgets.QListWidget(left)
            left_layout.addWidget(self.source_list, 1)
            self.source_list.currentRowChanged.connect(self._select_source)

            right = widgets.QWidget(splitter)
            right_layout = widgets.QVBoxLayout(right)
            form = widgets.QFormLayout()
            self.source_key = widgets.QLineEdit(right)
            self.caption = widgets.QLineEdit(right)
            self.identity = widgets.QComboBox(right)
            self.enabled = widgets.QCheckBox("Регистрация включена", right)
            self.enabled.setChecked(True)
            roles = widgets.QWidget(right)
            roles_layout = widgets.QHBoxLayout(roles)
            roles_layout.setContentsMargins(0, 0, 0, 0)
            self.role_resource = widgets.QCheckBox("Ресурс", roles)
            self.role_event = widgets.QCheckBox("Событие", roles)
            self.role_attribute = widgets.QCheckBox("Реквизит", roles)
            for item in (self.role_resource, self.role_event, self.role_attribute):
                roles_layout.addWidget(item)
            roles_layout.addStretch(1)
            form.addRow("source_key", self.source_key)
            form.addRow("Название", self.caption)
            form.addRow("Поле идентичности", self.identity)
            form.addRow("Роли", roles)
            form.addRow("", self.enabled)
            right_layout.addLayout(form)

            right_layout.addWidget(widgets.QLabel("Разрешённые реквизиты", right))
            self.fields = widgets.QTableWidget(0, 6, right)
            self.fields.setHorizontalHeaderLabels(
                ["Выбрать", "Поле", "Название", "Семантика", "Фильтр", "Группа"]
            )
            self.fields.horizontalHeader().setStretchLastSection(True)
            right_layout.addWidget(self.fields, 2)

            presentation_bar = widgets.QHBoxLayout()
            presentation_bar.addWidget(widgets.QLabel("Представления", right))
            presentation_bar.addStretch(1)
            add_presentation = widgets.QPushButton("Добавить", right)
            remove_presentation = widgets.QPushButton("Удалить", right)
            preview_presentation = widgets.QPushButton("Проверить ID → текст", right)
            presentation_bar.addWidget(add_presentation)
            presentation_bar.addWidget(remove_presentation)
            presentation_bar.addWidget(preview_presentation)
            right_layout.addLayout(presentation_bar)
            self.presentations = widgets.QTableWidget(0, 5, right)
            self.presentations.setHorizontalHeaderLabels(
                ["По умолчанию", "Исходное поле", "Путь", "Результат", "Название"]
            )
            self.presentations.horizontalHeader().setStretchLastSection(True)
            right_layout.addWidget(self.presentations, 1)

            actions = widgets.QHBoxLayout()
            self.status = widgets.QLabel("Готово", right)
            save = widgets.QPushButton("Сохранить регистрацию", right)
            delete = widgets.QPushButton("Удалить регистрацию", right)
            actions.addWidget(self.status, 1)
            actions.addWidget(delete)
            actions.addWidget(save)
            right_layout.addLayout(actions)
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 3)

            add_presentation.clicked.connect(self._add_presentation)
            remove_presentation.clicked.connect(self._remove_presentation)
            preview_presentation.clicked.connect(self._preview_presentation)
            save.clicked.connect(self._save)
            delete.clicked.connect(self._delete)

        def _reload_source_list(self) -> None:
            selected = self.current_table_key
            registered = {item.source.table_key: item for item in self.service.list_configs("gant")}
            self.source_list.clear()
            selected_row = 0
            for index, table in enumerate(sorted(self.catalog.tables.values(), key=lambda item: item.table_key)):
                config = registered.get(table.table_key)
                marker = "✓" if config is not None else "·"
                roles = ", ".join(role.value for role in config.roles) if config else "не зарегистрирована"
                item = QtWidgets.QListWidgetItem(f"{marker} {table.table_key}\n    {roles}")
                item.setData(QtCore.Qt.UserRole, table.table_key)
                self.source_list.addItem(item)
                if table.table_key == selected:
                    selected_row = index
            if self.source_list.count():
                self.source_list.setCurrentRow(selected_row)

        def _select_source(self, row: int) -> None:
            item = self.source_list.item(row)
            if item is None:
                return
            table_key = str(item.data(QtCore.Qt.UserRole))
            self.current_table_key = table_key
            existing = next(
                (config for config in self.service.list_configs("gant") if config.source.table_key == table_key),
                None,
            )
            fields = self.catalog.table_fields(table_key)
            primary = next((field for field in fields if field.is_pk), fields[0] if fields else None)
            source_key = existing.source.source_key if existing else "gant." + re.sub(r"[^\w.:-]+", "_", table_key)
            self.source_key.setText(source_key)
            self.source_key.setReadOnly(existing is not None)
            self.caption.setText(existing.source.caption if existing else self.catalog.tables[table_key].table_name)
            self.enabled.setChecked(existing.source.is_enabled if existing else True)

            self.identity.clear()
            for field_meta in fields:
                self.identity.addItem(field_meta.label or field_meta.field_name, field_meta.field_name)
            target_identity = existing.source.identity_field_name if existing else (primary.field_name if primary else "")
            identity_index = self.identity.findData(target_identity)
            self.identity.setCurrentIndex(max(0, identity_index))

            roles = set(existing.roles if existing else ())
            self.role_resource.setChecked(SourceRole.RESOURCE in roles)
            self.role_event.setChecked(SourceRole.EVENT in roles)
            self.role_attribute.setChecked(SourceRole.ATTRIBUTE in roles)
            self._fill_fields(fields, existing)
            self.current_presentations = list(existing.presentations if existing else ())
            self._fill_presentations()
            self.status.setText("Загружено")

        def _fill_fields(
            self,
            fields: Sequence[AdminField],
            existing: PlannerSourceConfig | None,
        ) -> None:
            selected = {item.field_name: item for item in (existing.requisites if existing else ())}
            self.fields.setRowCount(len(fields))
            for row, field_meta in enumerate(fields):
                requisite = selected.get(field_meta.field_name)
                choose = QtWidgets.QTableWidgetItem()
                choose.setFlags(choose.flags() | QtCore.Qt.ItemIsUserCheckable)
                choose.setCheckState(QtCore.Qt.Checked if requisite else QtCore.Qt.Unchecked)
                self.fields.setItem(row, 0, choose)
                name = QtWidgets.QTableWidgetItem(field_meta.field_name)
                name.setFlags(name.flags() & ~QtCore.Qt.ItemIsEditable)
                self.fields.setItem(row, 1, name)
                self.fields.setItem(
                    row,
                    2,
                    QtWidgets.QTableWidgetItem(requisite.caption if requisite else field_meta.label or field_meta.field_name),
                )
                semantic = QtWidgets.QComboBox(self.fields)
                for role in SemanticRole:
                    semantic.addItem(role.value, role.value)
                semantic.setCurrentIndex(
                    semantic.findData((requisite.semantic_role if requisite else SemanticRole.ATTRIBUTE).value)
                )
                self.fields.setCellWidget(row, 3, semantic)
                for column, checked in (
                    (4, requisite.is_filterable if requisite else False),
                    (5, requisite.is_groupable if requisite else False),
                ):
                    flag = QtWidgets.QTableWidgetItem()
                    flag.setFlags(flag.flags() | QtCore.Qt.ItemIsUserCheckable)
                    flag.setCheckState(QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)
                    self.fields.setItem(row, column, flag)

        def _fill_presentations(self) -> None:
            self.presentations.setRowCount(len(self.current_presentations))
            for row, item in enumerate(self.current_presentations):
                values = (
                    "да" if item.is_default else "",
                    item.source_field_name,
                    item.relation_steps[0] if item.relation_steps else "прямое поле",
                    f"{item.result_table_key}.{item.result_field_name}",
                    item.caption,
                )
                for column, value in enumerate(values):
                    cell = QtWidgets.QTableWidgetItem(value)
                    cell.setFlags(cell.flags() & ~QtCore.Qt.ItemIsEditable)
                    self.presentations.setItem(row, column, cell)

        def _source_for_form(self) -> PlannerSource:
            return PlannerSource(
                source_key=self.source_key.text().strip(),
                subject_code="gant",
                table_key=self.current_table_key,
                caption=self.caption.text().strip(),
                identity_field_name=str(self.identity.currentData() or ""),
                is_enabled=self.enabled.isChecked(),
            )

        def _add_presentation(self) -> None:
            dialog = PresentationDialog(self.catalog, self.current_table_key, self)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            try:
                item = dialog.build(self._source_for_form(), len(self.current_presentations) * 10)
            except PlannerRegistryError as exc:
                QtWidgets.QMessageBox.warning(self, "Представление отклонено", str(exc))
                return
            if item.is_default:
                self.current_presentations = [
                    PlannerPresentation(**{**current.__dict__, "is_default": False})
                    for current in self.current_presentations
                ]
            self.current_presentations.append(item)
            self._fill_presentations()

        def _remove_presentation(self) -> None:
            row = self.presentations.currentRow()
            if 0 <= row < len(self.current_presentations):
                self.current_presentations.pop(row)
                self._fill_presentations()

        def _collect_config(self) -> PlannerSourceConfig:
            source = self._source_for_form()
            roles = tuple(
                role
                for role, checkbox in (
                    (SourceRole.RESOURCE, self.role_resource),
                    (SourceRole.EVENT, self.role_event),
                    (SourceRole.ATTRIBUTE, self.role_attribute),
                )
                if checkbox.isChecked()
            )
            requisites = []
            for row in range(self.fields.rowCount()):
                if self.fields.item(row, 0).checkState() != QtCore.Qt.Checked:
                    continue
                field_name = self.fields.item(row, 1).text()
                caption = self.fields.item(row, 2).text().strip() or field_name
                semantic = SemanticRole(self.fields.cellWidget(row, 3).currentData())
                requisites.append(
                    PlannerRequisite(
                        requisite_key=_requisite_key(source.source_key, field_name),
                        source_key=source.source_key,
                        field_name=field_name,
                        caption=caption,
                        is_filterable=self.fields.item(row, 4).checkState() == QtCore.Qt.Checked,
                        is_groupable=self.fields.item(row, 5).checkState() == QtCore.Qt.Checked,
                        semantic_role=semantic,
                        sort_order=row * 10,
                    )
                )
            presentations = tuple(
                PlannerPresentation(
                    **{
                        **item.__dict__,
                        "source_key": source.source_key,
                        "presentation_key": _presentation_key(
                            source.source_key,
                            item.source_field_name,
                            item.result_table_key,
                            item.result_field_name,
                            *item.relation_steps,
                        ),
                    }
                )
                for item in self.current_presentations
            )
            return PlannerSourceConfig(source, roles, tuple(requisites), presentations)

        def _save(self) -> None:
            try:
                config = self._collect_config()
                self.service.save_config(config)
            except PlannerRegistryError as exc:
                QtWidgets.QMessageBox.warning(self, "Регистрация отклонена", str(exc))
                self.status.setText("Ошибка проверки")
                return
            self.status.setText("Регистрация сохранена в памяти")
            self._reload_source_list()

        def _delete(self) -> None:
            existing = next(
                (
                    config
                    for config in self.service.list_configs("gant")
                    if config.source.table_key == self.current_table_key
                ),
                None,
            )
            if existing is not None:
                self.service.delete_config(existing.source.source_key)
            self.status.setText("Регистрация удалена из памяти")
            self._reload_source_list()

        def _preview_presentation(self) -> None:
            row = self.presentations.currentRow()
            if row < 0 and self.current_presentations:
                row = 0
            if not (0 <= row < len(self.current_presentations)):
                QtWidgets.QMessageBox.information(self, "Предпросмотр", "Выберите представление.")
                return
            presentation = self.current_presentations[row]
            if self.current_table_key != "Naryad.mk":
                QtWidgets.QMessageBox.information(
                    self,
                    "Предпросмотр",
                    "Полупродовый пример ID → текст подготовлен для Naryad.mk.",
                )
                return
            source_row = {"Пномер": 6476, "Номенклатура": "КТ.741136.003 Шильда", "Тип": 1}
            rows = {
                "Naryad.Тип_мк": [
                    {"Пномер": 1, "Имя": "Плановая", "rgb": "245,245,245"},
                    {"Пномер": 2, "Имя": "Дорезка", "rgb": "214,112,112"},
                ]
            }
            try:
                value = PlannerPresentationResolver(self.catalog).resolve(
                    self.current_table_key,
                    source_row,
                    presentation,
                    rows,
                )
            except PlannerRegistryError as exc:
                QtWidgets.QMessageBox.warning(self, "Предпросмотр", str(exc))
                return
            QtWidgets.QMessageBox.information(
                self,
                "Предпросмотр",
                f"Исходная строка: Пномер=6476, Тип=1\nРезультат: {value!r}",
            )

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = DemoWindow()
    window.show()
    return int(app.exec_())


__all__ = [
    "PlannerRegistryError",
    "PlannerValidationError",
    "PlannerCatalogError",
    "PlannerRepositoryError",
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
    "TransactionalPostgresExecutor",
    "CustOrmPlannerRegistryRepository",
    "build_demo_catalog",
    "build_demo_configurations",
]


if __name__ == "__main__":
    raise SystemExit(_run_demo())
