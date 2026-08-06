from __future__ import annotations

import hashlib
import os
import re
import threading
from dataclasses import dataclass
from typing import Any, Callable

try:
    from . import planner_registry_runtime_stage2 as runtime_api
    from . import planner_registry_stage2 as registry
except ImportError:
    import planner_registry_runtime_stage2 as runtime_api
    import planner_registry_stage2 as registry


PLANNER_CONNINFO_ENV = "MES_PLANNER_PG_DSN"
PLANNER_SUBJECT_CODE = "gant"


class PlannerMesTypeError(registry.PlannerRegistryError):
    """Справочники МЕС нельзя безопасно передать в выбор типа."""


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

    def to_ui_row(self) -> dict[str, Any]:
        return {
            "_name": self.presentation_key,
            "_presentation_key": self.presentation_key,
            "": "⭐" if self.is_default else "",
            "Поле": self.source_field_name,
            "Представление": self.caption,
            "Результат": f"{self.result_table_key}.{self.result_field_name}",
            "Связь": " → ".join(self.relation_steps) if self.relation_steps else "Прямое поле",
            "Фильтр": "Да" if self.is_filterable else "",
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
        # conninfo_provider: Callable[[], str] | None = None,
    ) -> None:
        def conninfo_provider():
            return "postgresql://postgres:Adr1959967 @srv-mes:5432/postgres"
        self._runtime = runtime
        self._runtime_factory = runtime_factory or runtime_api.PlannerRegistryRuntime.connect
        self._conninfo_provider = conninfo_provider or (
            lambda: os.getenv(PLANNER_CONNINFO_ENV, "")
        )
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
                    "Runtime справочников МЕС уже закрыт. Откройте окно планировщика повторно."
                )
            if self._runtime is not None:
                return self._runtime
            conninfo = str(self._conninfo_provider() or "").strip()
            if not conninfo:
                raise PlannerMesTypeError(
                    f"Не задана переменная окружения {PLANNER_CONNINFO_ENV}. "
                    "Справочники МЕС пока недоступны."
                )
            try:
                self._runtime = self._runtime_factory(conninfo)
            except registry.PlannerRegistryError:
                raise
            except Exception as exc:
                raise PlannerMesTypeError(
                    f"Не удалось открыть runtime справочников МЕС: {exc}"
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
        configs = runtime.list_sources(
            self.subject_code,
            role=registry.SourceRole.ATTRIBUTE,
        )
        warnings: list[str] = []
        choices: list[MesTypeChoice] = []
        for config in configs:
            choice = self._choice_from_config(config, warnings)
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
                "Выбранный тип не принадлежит зарегистрированному справочнику МЕС."
            )
        return choice

    def presentation_template(self, type_value: type) -> list[dict[str, Any]]:
        return self.choice_for_type(type_value).presentation_template()

    def default_presentation(self, type_value: type) -> MesPresentationChoice:
        return self.choice_for_type(type_value).default_presentation

    def close(self) -> None:
        self.session.close()

    @staticmethod
    def _choice_from_config(
        config: registry.PlannerSourceConfig,
        warnings: list[str],
    ) -> MesTypeChoice | None:
        if not config.source.is_enabled:
            return None
        if registry.SourceRole.ATTRIBUTE not in config.roles:
            return None
        filter_fields = {
            item.field_name: item
            for item in config.requisites
            if item.is_selectable and item.is_filterable
        }
        presentations = tuple(
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
            )
            for item in sorted(
                config.presentations,
                key=lambda value: (value.sort_order, value.caption.casefold(), value.presentation_key),
            )
        )
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

        return type(
            class_name,
            (mes_base_type,),
            {
                "__module__": __name__,
                "_planner_source_key": choice.source_key,
                "_planner_table_key": choice.table_key,
                "_planner_choice": choice,
                "template": classmethod(template),
                "default_presentation": classmethod(default_presentation),
            },
        )

    @staticmethod
    def _token(source_key: str) -> str:
        digest = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:12]
        return f"source_{digest}"


__all__ = [
    "PLANNER_CONNINFO_ENV",
    "PLANNER_SUBJECT_CODE",
    "PlannerMesTypeError",
    "MesPresentationChoice",
    "MesFilterChoice",
    "MesTypeChoice",
    "MesTypeEntry",
    "PlannerRuntimeSession",
    "PlannerMesTypeCatalog",
]
