import dataclasses
import enum
import logging
import typing
import uuid

import project_cust_38.sub_mes.resource_planning.attribute_binding as AB


class CatalogLinkCardinality(str, enum.Enum):
    ONE_TO_ONE = 'ONE_TO_ONE'
    MANY_TO_ONE = 'MANY_TO_ONE'


class CatalogLinkComparison(str, enum.Enum):
    EQUAL = 'EQUAL'
    # RLIKE = 'RLIKE'
    # LLIKE = 'LLIKE'


class CatalogLinkDirection(str, enum.Enum):
    LEFT_TO_RIGHT = 'LEFT_TO_RIGHT'
    # RIGHT_TO_LEFT = 'RIGHT_TO_LEFT'


@dataclasses.dataclass(frozen=True)
class CatalogLinkEndpoint:
    provider: AB.SourceProvider
    source_key: str
    entity_key: str
    field_key: str
    caption: str = ''

    @property
    def catalog_key(self) -> tuple[str, str, str]:
        return self.provider, self.source_key, self.entity_key

    @property
    def lookup_key(self) -> tuple[str, str, str, str]:
        return (*self.catalog_key, self.field_key)

    @property
    def display_name(self) -> str:
        return self.caption or self.field_key

    def to_dict(self) -> dict:
        return {
            'provider': self.provider,
            'source_key': self.source_key,
            'entity_key': self.entity_key,
            'field_key': self.field_key,
            'caption': self.caption,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CatalogLinkEndpoint":
        if not isinstance(data, dict):
            raise TypeError('некорректный аргумент data')
        return cls(**data)

    # def __post_init__(self):
    #     try:
    #         provider = AB.SourceProvider(self.provider)
    #     except Exception as e:
    #         raise ValueError(f'{self.source_key} неизвестный provider')
    #     for key in ('source_key', 'entity_key', 'field_key'):
    #         cr_key = getattr(self, key)
    #         if not isinstance(cr_key, str) or not cr_key.strip():
    #             raise ValueError(f'Некорректное значение ключа {cr_key}')
    #         setattr(self, key, cr_key.strip())


@dataclasses.dataclass(frozen=True)
class CatalogLinkSpec:
    link_key: str
    left: CatalogLinkEndpoint
    right: CatalogLinkEndpoint
    cardinality: CatalogLinkCardinality = CatalogLinkCardinality.MANY_TO_ONE
    comparison: CatalogLinkComparison = CatalogLinkComparison.EQUAL
    direction: CatalogLinkDirection = CatalogLinkDirection.LEFT_TO_RIGHT
    caption: str = ''
    version: int = 1

    @property
    def path_key(self) -> tuple:
        return self.left.lookup_key, self.right.lookup_key, self.comparison, self.direction

    @property
    def display_text(self) -> str:
        if self.caption:
            return self.caption
        return f'{self.left.display_name} -> {self.right.display_name}'

    def to_dict(self) -> dict:
        return {
            'version': self.version,
            'link_key': self.link_key,
            'caption': self.caption,
            'cardinality': self.cardinality,
            'comparison': self.comparison,
            'direction': self.direction,
            'left': self.left.to_dict(),
            'right': self.right.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            raise ValueError('Некорректный аргумент data')
        return cls(
            version=data.get('version') or 1,
            link_key=data.get('link_key'),
            caption=data.get('caption') or '',
            cardinality=data.get('cardinality') or CatalogLinkCardinality.MANY_TO_ONE,
            comparison=data.get('comparison') or CatalogLinkComparison.EQUAL,
            direction=data.get('direction') or CatalogLinkDirection.LEFT_TO_RIGHT,
            left=CatalogLinkEndpoint.from_dict(data.get('left')),
            right=CatalogLinkEndpoint.from_dict(data.get('right')),
        )

class CatalogLinkManager:
    def __init__(self, links: typing.Iterable[CatalogLinkSpec] = ()):
        self.__links: dict[str, CatalogLinkSpec] = {}
        for link in links:
            self.register(link)

    def create(
            self,
            left: CatalogLinkEndpoint,
            right: CatalogLinkEndpoint,
            *,
            link_key: str | None = None,
            caption: str = '',
            cardinality: CatalogLinkCardinality = CatalogLinkCardinality.MANY_TO_ONE
    ):
        return CatalogLinkSpec(
            link_key=link_key or uuid.uuid4().hex,
            left=left,
            right=right,
            caption=caption,
            cardinality=cardinality,
            comparison=CatalogLinkComparison.EQUAL
        )

    def register(self, link: CatalogLinkSpec):
        if not isinstance(link, CatalogLinkSpec):
            raise TypeError('Ожидается тип CatalogLinkSpec')
        current = self.__links.get(link.link_key)
        if current is not None:
            logging.warning(f'link_key {current} дублируется ')
            return current
        self.__check_duplicate_path(link)
        self.__links[link.link_key] = link
        return link

    def replace(self, link: CatalogLinkSpec) -> CatalogLinkSpec:
        if not isinstance(link, CatalogLinkSpec):
            raise TypeError('некорректный аргумент link')
        if link.link_key not in self.__links:
            raise KeyError(f'связь {link.link_key} не зарегистрирована')
        self.__check_duplicate_path(link, ignored_link_key=link.link_key)
        self.__links[link.link_key] = link
        return link

    def get(self, link_key: str) -> CatalogLinkSpec | None:
        return self.__links.get(link_key)

    def all(self) -> tuple[CatalogLinkSpec, ...]:
        return tuple(self.__links.values())

    def remove(self, link_key: str) -> bool:
        return self.__links.pop(link_key, None) is not None

    def __check_duplicate_path(self, link: CatalogLinkSpec, ignored_link_key: str | None = None):
        for registered in self.__links.values():
            if registered.link_key == ignored_link_key:
                continue
            if registered.path_key == link.path_key:
                raise ValueError('Связь уже зарегистрирована')

    def to_list(self) -> list[dict]:
        return [
            link.to_dict()
            for link in self.__links.values()
        ]

    @classmethod
    def from_list(cls, data: list[dict]):
        if not isinstance(data, list):
            raise TypeError('аргумент data ожидается типа list')
        return cls(CatalogLinkSpec.from_dict(item) for item in data)

    def __len__(self) -> int:
        return len(self.__links)


if __name__ == '__main__':
    manager = CatalogLinkManager()

    mes_plan_order = CatalogLinkEndpoint(
        provider=AB.SourceProvider.MES,
        source_key='знпр',
        entity_key='знпр',
        field_key='client_order_Key',
        caption='Ссылка на заказ клиента'
    )
    erp_client_order = CatalogLinkEndpoint(
        provider=AB.SourceProvider.ERP,
        source_key='Документы.ЗаказКлиента',
        entity_key='Документы.ЗаказКлиента',
        field_key='Ссылка',
        caption='Ссылка заказа клиента'
    )

    link = manager.create(
        mes_plan_order,
        erp_client_order,
        link_key='kpl_to_erp_client_order',
        caption='План -> заказ клиента',
        cardinality=CatalogLinkCardinality.MANY_TO_ONE
    )
    manager.register(link)
    restored = CatalogLinkManager.from_list(manager.to_list())
    assert restored.get(link.link_key) == link

    print(link.display_text)
    print(restored.to_list())