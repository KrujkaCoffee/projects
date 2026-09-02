import copy
import dataclasses
import typing
from enum import Enum


class SourceProvider(str, Enum):
    MES = "MES"
    ERP = "ERP"
    TEST = "TEST"


class CombineMode(str, Enum):
    DIRECT = "DIRECT"       # Прямой вывод
    CONCAT = "CONCAT"       # Конкатенация полей


class BindingOrigin(str, Enum):
    EXPLICIT = "explicit"       # Системное зарегистрированное соединение
    INFERRED = "inferred"       # Пользовательское


class BindingValidationStatus(str, Enum):
    VALID = "VALID"             # Подвязка корректна
    INVALID = "INVALID"         # Сущность изменилась
    UNAVAILABLE = "UNAVAILABLE" # Источник не удалось проверить


@dataclasses.dataclass(frozen=True)
class BindingValidationResult:
    status: BindingValidationStatus

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    is_valid: bool = True
    need_reconfigure: bool = True
    is_available: bool = True

    @property
    def status_text(self) -> str:
        return {
            BindingValidationStatus.VALID: 'Связка актуальна',
            BindingValidationStatus.INVALID: 'Требует перенастройки',
            BindingValidationStatus.UNAVAILABLE: 'Не удалось проверить',
        }[self.status]


class BindingTarget(typing.Protocol):
    attr_view: str
    binding_spec: dict | None


@dataclasses.dataclass(frozen=True)
class BindingField:

    provider: SourceProvider
    source_key: str
    entity_key: str
    field_key: str

    presentation_key: str
    caption: str = ""
    relation_steps: tuple[str] = ()

    def __post_init__(self):
        # todo валидация полей
        ...

    @property
    def display_name(self) -> str:
        return self.caption or self.field_key

    @property
    def lookup_key(self) -> tuple[str, str, str]:
        return self.provider, self.source_key, self.presentation_key

    def to_dict(self):
        return {
            "provider": self.provider,
            "source_key": self.source_key,
            "entity_key": self.entity_key,
            "field_key": self.field_key,
            "presentation_key": self.presentation_key,
            "caption": self.caption,
            "relation_steps": list(self.relation_steps)
        }

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            raise TypeError("Неверный тип данных")
        return cls(
            provider=data.get("provider") or "",
            source_key=data.get("source_key") or "",
            entity_key=data.get("entity_key") or "",
            field_key=data.get("field_key") or "",
            presentation_key=data.get("presentation_key") or "",
            caption=data.get("caption") or "",
            relation_steps=data.get("relation_steps") or (),
        )

@dataclasses.dataclass(frozen=True)
class AttributeBinding:
    mode: CombineMode
    origin: BindingOrigin
    fields: tuple[BindingField, ...]
    separator: str = " "

    version: int = 1

    def __post_init__(self): ...
        # todo валидация полей

    @property
    def attr_view(self) -> str:
        return ';'.join(
            field.presentation_key
            for field in self.fields
        )

    @property
    def display_text(self):
        return " + ".join(
            field.display_name
            for field in self.fields
        )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "mode": self.mode,
            "origin": self.origin,
            "separator": self.separator,
            "fields": [
                field.to_dict()
                for field in self.fields
            ]
        }

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            raise TypeError("Некорректный тип данных")
        return cls(
            version=data.get("version") or 1,
            mode=data.get("mode") or CombineMode.DIRECT,
            origin=data.get("origin") or BindingOrigin.EXPLICIT,
            fields=tuple(
                BindingField.from_dict(item)
                for item in data.get("fields") or ()
            ),
            separator=data.get("separator") or "",
        )


@dataclasses.dataclass
class AttributeBindingManager:


    def direct(
            self,
            field: BindingField,
            origin: BindingOrigin = BindingOrigin.EXPLICIT
    ) -> AttributeBinding:
        return AttributeBinding(
            mode=CombineMode.DIRECT,
            origin=origin,
            fields=(field,)
        )

    def concat(
            self,
            first: BindingField,
            second: BindingField,
            origin: BindingOrigin = BindingOrigin.EXPLICIT,
            separator: str = " "
        ) -> AttributeBinding:
        return AttributeBinding(
            mode=CombineMode.CONCAT,
            origin=origin,
            separator=separator,
            fields=(first, second),
        )

    def from_fields(
            self,
            fields: typing.Iterable[BindingField],
            separator: str = " ",
            origin: BindingOrigin = BindingOrigin.EXPLICIT
    ) -> AttributeBinding:
        fields = tuple(fields)
        if len(fields) == 1:
            return self.direct(fields[0], origin=origin)
        if len(fields) == 2:
            return self.concat(fields[0], fields[1], origin=origin, separator=separator)
        raise ValueError("Запрещено создавать связь 2> полей")

    @staticmethod
    def restore(data: dict):
        return AttributeBinding.from_dict(data)

    def apply_binding(
            self,
            target: BindingTarget,
            binding: AttributeBinding
    ) -> AttributeBinding:
        if not isinstance(binding, AttributeBinding):
            raise ValueError('Некорректные входные данные')
        previous_attr_view = target.attr_view
        previous_spec = target.binding_spec
        new_spec = binding.to_dict()
        try:
            self.__write_target(target, binding.attr_view, new_spec)
        except Exception as e:
            print(e)
            self.__write_target(target, previous_attr_view, previous_spec)
        return binding

    def get_binding(self, target: BindingTarget):
        attr_view, binding_spec = target.attr_view, target.binding_spec
        if binding_spec is None:
            return None
        binding = self.restore(binding_spec)
        if attr_view != binding.attr_view:
            raise ValueError('attr_view некорректен')
        return binding

    def clear_binding(self, target: BindingTarget):
        previous_attr_view, previous_spec = target.attr_view, target.binding_spec
        changed = bool(previous_attr_view or previous_spec is not None)
        try:
            self.__write_target(target, "", None)
        except Exception as e:
            print(e)
            self.__write_target(target, previous_attr_view, previous_spec)
        return changed

    def validate_againts(
            self,
            binding: AttributeBinding,
            current_fields: typing.Iterable[BindingField] | None,
            unavailable_reason: str = "Источник данных недоступен"
    ):
        ... # todo
        errors = []
        warnings = []
        current_by_key = {}
        for current in current_fields:
            current_by_key[current.lookup_key] = current

        for expected in binding.fields:
            current = current_by_key.get(expected.lookup_key)
            if current is None:
                errors.append(f'Поле {expected.display_name} не найдено в источнике')
                continue

        status = BindingValidationStatus.INVALID if errors else BindingValidationStatus.VALID
        return BindingValidationResult(
            status=status,
            errors=tuple(errors),
            warnings=tuple(warnings))

    @staticmethod
    def __write_target(target: BindingTarget, attr_view: str, binding_spec: dict | None = None):
        target.binding_spec = copy.deepcopy(binding_spec)
        target.attr_view = copy.deepcopy(attr_view)



if __name__ == '__main__':
    manager = AttributeBindingManager()

    plan_pk = BindingField(
        provider=SourceProvider.MES,
        source_key="plan",
        entity_key="plan",
        field_key="Пномер",
        presentation_key="plan.Пномер",
        caption="Номер КПЛ"
    )
    direction = BindingField(
        provider=SourceProvider.MES,
        source_key="plan",
        entity_key="napravl_deyat",
        field_key="name",
        presentation_key="plan.direction_name",
        caption="Направление деятельности"
    )

    binding = manager.concat(
        plan_pk,
        direction,
        separator=" / "
    )

    restored = manager.restore(
        binding.to_dict()
    )
    assert restored == binding
    assert binding.attr_view == (
        "plan.Пномер;plan.direction_name"
    )
    assert binding.display_text == (
        "Номер КПЛ + "
        "Направление деятельности"
    )

    validate_result = manager.validate_againts(
        binding,
        current_fields=[plan_pk, direction]
    )
    assert validate_result.is_valid

    changed_route = BindingField(
        provider=direction.provider,
        source_key=direction.source_key,
        entity_key=direction.entity_key,
        field_key=direction.field_key,
        presentation_key=direction.presentation_key,
        caption=direction.caption,
        relation_steps=("testest",),

    )
    stale = manager.validate_againts(binding, (plan_pk, changed_route))
    assert stale.need_reconfigure
