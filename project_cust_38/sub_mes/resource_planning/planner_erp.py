import typing
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from project_cust_38 import api_erp_commands as APIERP


ERP_ENTITY_REF_VERSION = 1


class ErpEntityError(ValueError): ...


@dataclass(frozen=True)
class ErpEntityRef:
    source_key: str
    entity_key: str
    ref_key: str
    display_snapshot: str = ""
    version: int = ERP_ENTITY_REF_VERSION

    @property
    def identity_key(self) -> tuple[str, str, str]:
        return self.source_key, self.entity_key, self.ref_key

    def serialize(self):
        return {
            'version': self.version,
            'source_key': self.source_key,
            'entity_key': self.entity_key,
            'ref_key': self.ref_key,
            'display_snapshot': self.display_snapshot
        }

    @classmethod
    def deserialize(cls, data: typing.Mapping):
        if isinstance(data, cls):
            return data
        if not isinstance(data, typing.Mapping):
            raise ErpEntityError('ERP ссылка должна быть словарем')
        return cls(
            source_key=data.get("source_key", ""),
            entity_key=data.get("entity_key", ""),
            ref_key=data.get("ref_key", ""),
            display_snapshot=data.get("display_snapshot", ""),
            version=data.get("version", ERP_ENTITY_REF_VERSION)
        )

    def __str__(self):
        return self.display_snapshot or self.ref_key


@dataclass
class ErpEntityRow:
    reference: ErpEntityRef
    values: dict[str, object]
    presentations: dict[str, str]


class ErpEntityService:
    def __init__(self, interface, source_key_getter):
        self.interface: APIERP = interface
        self.__source_key_getter: typing.Callable = source_key_getter

    @staticmethod
    def __query_table(entity_key: str):
        group, separator, name = entity_key.partition('.')
        prefix = {
            'Документы': 'Документ',
            'Справочники': 'Справочник'
        }.get(group)
        if not prefix or not separator or not name.isidentifier():
            raise ErpEntityError(f'Неподдерживаемый путь ERP объекта: {entity_key!r}')
        return f'{prefix}.{name}'

    def read(self, reference) -> ErpEntityRef | None:
        row = self.read_fields(reference)
        return None if row is None else row.reference

    def read_fields(self, reference: typing.Mapping, field_keys=()) -> ErpEntityRow | None:
        """Чтение строки из 1с"""
        reference = ErpEntityRef.deserialize(reference)

        if not isinstance(field_keys, (list, tuple)):
            raise ErpEntityError('Некорректный параметр field_keys')

        for field_key in field_keys:
            if not isinstance(field_key, str) or not field_key.isidentifier():
                raise ErpEntityError(f'Некорректное имя ERP-поля: {field_key!r}.')

        field_keys = tuple(dict.fromkeys(field_keys))

        current_source_key = self.__source_key_getter()
        if reference.source_key != current_source_key:
            raise ErpEntityError(f'Некорректный источник')
        table = self.__query_table(reference.entity_key)
        columns = [
            'ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Источник.Ссылка)) КАК ref_key',
            'ПРЕДСТАВЛЕНИЕ(Источник.Ссылка) КАК display_snapshot',
        ]

        for index, field_key in enumerate(field_keys):
            columns.append(f'Источник.{field_key} КАК value_{index}')
            columns.append(f'ПРЕДСТАВЛЕНИЕ(Источник.{field_key}) КАК presentation_{index}')

        select_columns = ',\n'.join(columns)
        query = f"""
            ВЫБРАТЬ ПЕРВЫЕ 2
                {select_columns}
            ИЗ
                {table} КАК Источник
            ГДЕ 
                Источник.Ссылка = &PlannerRef
        """
        refs = self.interface.Refs_wet(query)
        refs.add_ref(self.interface.Ref_wet('PlannerRef', reference.entity_key, reference.ref_key))
        try:
            code, payload = self.interface.get_wet_request(text=query, refs=refs, lazy_method_huours=0)
        except Exception as exc:
            raise ErpEntityError('Не удалось выполнить запрос к ERP') from exc
        if code != 200:
            raise ErpEntityError(f'Ошибка чтения ERP код ответа {code!r}')
        if not isinstance(payload, typing.Mapping):
            raise ErpEntityError(f'ERP вернула некорректный формат ответа.')
        if payload.get('ЕстьОшибки'):
            raise ErpEntityError(f"Ошибка ERP: {payload.get('Ошибки')}")
        rows = payload.get('data')
        if isinstance(rows, typing.Mapping) and rows.get('ЕстьОшибки'):
            raise ErpEntityError(f"Ошибка ERP: {rows.get('Ошибки')}")
        if not isinstance(rows, list):
            raise ErpEntityError('Ошибка ERP некорректный ответ')


        if not rows:
            return None
        if len(rows) != 1:
            raise ErpEntityError('ERP вернула несколько записей для одного UUID')
        row = rows[0]
        required_columns = ['ref_key', 'display_snapshot']
        for index in range(len(field_keys)):
            required_columns.extend((f'value_{index}', f'presentation_{index}'))

        if not isinstance(row, typing.Mapping) or any(name not in row for name in required_columns):
            raise ErpEntityError('Отсутсвует запись запрошенного поля')

        result = ErpEntityRef(
            source_key=reference.source_key,
            entity_key=reference.entity_key,
            ref_key=row['ref_key'],
            display_snapshot=row['display_snapshot']
        )
        if result.identity_key != reference.identity_key:
            raise ErpEntityError('ERP вернула запись с другим UUID')

        values = {}
        presentations = {}

        for index, field_key in enumerate(field_keys):
            values[field_key] = row[f'value_{index}']
            text_value = row[f'presentation_{index}']
            presentations[field_key] = ('' if text_value is None else str(text_value))

        return ErpEntityRow(
            reference=result,
            values=values,
            presentations=presentations
        )

