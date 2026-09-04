import enum
from dataclasses import dataclass

class ProviderState(str, enum.Enum):
    MES = 'MES'
    ERP = 'ERP'

class CombineState(str, enum.Enum):
    DIRECT = 'DIRECT'   # Прямой вывод поля
    CONCAT = 'CONCAT'   # Конкатенация нескольких полей

class OriginState(str, enum.Enum):
    EXPLICIT = 'EXPLICIT' # Юзер выбрал поле
    INFERRED = 'INFERRED' # Система выбрала поле



@dataclass(frozen=True)
class FieldRef:
    provider: ProviderState          # "mes" | "erp"
    source_key: str        # (например Документы.ЗаказКлиента)
    entity_key: str        # (например ЗаказКлиента)
    field_key: str         # Номер
    caption: str           # представление: Заказ клиента
    data_type: str         # Тип Дата/Date


@dataclass(frozen=True)
class RelationSpec:
    sources: tuple[FieldRef, ...]       # одно или два поля источника
    target_key: str                     # атрибут ресурса/события
    relation_steps: tuple[str, ...]     # стабильные relation_key
    combine: str                        # "direct" | "concat"
    separator: str
    origin: str                         # "explicit" | "inferred"
    version: int = 1


class PlannerAttributeBinder:
    def list_attribute_sources(self, provider=None): ... # Возвращает источники
    def select_source(self, source_key): ...             # Возвращает SourceSelection
    def list_presentations(self, source): ...            # Возвращает поля
    def suggest_bindings(self, target, source): ...     # Возвращает предложения
    def validate_binding(self, draft): ...              # Валидация байндов
    def build_binding(self, draft) -> RelationSpec: ... #
    def describe_binding(self, spec) -> str: ...



####


@dataclass(frozen=True, slots=True)
class SourceSelection:

    provider: SourceProvider
    source_key: str
    entity_key: str
    caption: str