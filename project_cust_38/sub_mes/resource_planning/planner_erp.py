from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID


ERP_ENTITY_REF_VERSION = 1


class ErpEntityError(ValueError):
    pass


@dataclass(frozen=True)
class ErpEntityRef:
    source_key: str
    entity_key: str
    ref_key: str
    display_snapshot: str = ""
    version: int = ERP_ENTITY_REF_VERSION

    def __post_init__(self):
        if self.version != ERP_ENTITY_REF_VERSION:
            raise ErpEntityError(
                f"Версия ERP-ссылки {self.version!r} не поддерживается."
            )

        for name in ("source_key", "entity_key"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ErpEntityError(f"В ERP-ссылке не задан {name}.")

        try:
            ref_key = str(UUID(str(self.ref_key)))
        except ValueError as exc:
            raise ErpEntityError(
                "В ERP-ссылке указан некорректный UUID."
            ) from exc

        object.__setattr__(self, "ref_key", ref_key)
        object.__setattr__(
            self,
            "display_snapshot",
            "" if self.display_snapshot is None else str(self.display_snapshot),
        )

    @property
    def identity_key(self) -> tuple[str, str, str]:
        return self.source_key, self.entity_key, self.ref_key

    def serialize(self) -> dict:
        return {
            "version": self.version,
            "source_key": self.source_key,
            "entity_key": self.entity_key,
            "ref_key": self.ref_key,
            "display_snapshot": self.display_snapshot,
        }

    @classmethod
    def deserialize(cls, data):
        if isinstance(data, cls):
            return data
        if not isinstance(data, Mapping):
            raise ErpEntityError(
                "Сохранённая ERP-ссылка должна быть словарём."
            )

        return cls(
            source_key=data.get("source_key", ""),
            entity_key=data.get("entity_key", ""),
            ref_key=data.get("ref_key", ""),
            display_snapshot=data.get("display_snapshot", ""),
            version=data.get("version", ERP_ENTITY_REF_VERSION),
        )

    def __str__(self):
        return self.display_snapshot or self.ref_key