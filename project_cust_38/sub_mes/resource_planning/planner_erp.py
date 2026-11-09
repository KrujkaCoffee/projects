import dataclasses
import sys
import typing
from dataclasses import dataclass, replace

from PyQt5 import QtCore, QtWidgets

from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import api_erp_commands as APIERP
from project_cust_38.sub_mes.resource_planning import attribute_binding as AB
from uuid import UUID

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


@dataclass(frozen=True)
class ErpSearchResult:
    items: tuple[ErpEntityRef, ...]
    has_more: bool

    @property
    def next_after(self) -> ErpEntityRef | None:
        if self.has_more and self.items:
            return self.items[-1]
        return None

@dataclasses.dataclass(frozen=True)
class ErpEntitySelection:
    accepted: bool
    reference: ErpEntityRef | None = None

@dataclass(frozen=True)
class ErpSearchPage:
    items: tuple[ErpEntityRow, ...]
    total_count: int
    page_number: int



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

    def read_bound(self, reference, binding: AB.AttributeBinding | dict) -> ErpEntityRef | None:
        reference = ErpEntityRef.deserialize(reference)
        if isinstance(binding, dict):
            binding = AB.AttributeBinding.from_dict(binding)
        if not isinstance(binding, AB.AttributeBinding):
            raise ErpEntityError('Ожидается настройка AttributeBinding.')
        if binding.version != 1:
            raise ErpEntityError('Неподдерживаемая версия настройки представления.')
        if binding.mode == AB.CombineMode.DIRECT:
            expected_count = 1
        elif binding.mode == AB.CombineMode.CONCAT:
            expected_count = 2
        else:
            raise ErpEntityError('Неподдерживаемый способ формирования надписи')
        if len(binding.fields) != expected_count:
            raise ErpEntityError(f'Для выбранного способа требуется {expected_count} полей')
        row = self.read_fields(reference, tuple(field.field_key for field in binding.fields))
        if row is None:
            return None

        parts = [row.presentations[field.field_key] for field in binding.fields]
        if binding.mode == AB.CombineMode.DIRECT:
            display_snapshot = parts[0]
        else:
            display_snapshot = binding.separator.join(part for part in parts if part)
        return replace(row.reference, display_snapshot=display_snapshot)

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

    def search_text(
            self,
            field: AB.BindingField | dict,
            text: str = '',
            *,
            limit: int = 100,
            after: ErpEntityRef | None = None,
    ) -> ErpSearchResult:
        """Поиск значения по одному строковому полю ERP"""
        if isinstance(field, dict):
            field = AB.BindingField.from_dict(field)
        if not isinstance(field, AB.BindingField):
            raise ErpEntityError('field должен быть типа BindingField или dict')
        if field.provider != AB.SourceProvider.ERP or field.relation_steps:
            raise ErpEntityError('атрибут provider у field не поддерживается')
        if not isinstance(field.field_key, str) or not field.field_key.isidentifier():
            raise ErpEntityError('Некорректное имя поля')
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ErpEntityError('Лимит должен быть целым чистом от 1 до 500')
        if not isinstance(text, str) or len(text) > 200:
            raise ErpEntityError('Строка поиска превышает лимит')

        source_key = self.__source_key_getter()
        if field.source_key not in (source_key, field.entity_key):
            raise ErpEntityError('Поле относится к другому источнику ERP')

        if after is not None:
            after = ErpEntityRef.deserialize(after)
            if (after.source_key, after.entity_key) != (source_key, field.entity_key):
                raise ErpEntityError('Некорректный источник для поиска')

        table = self.__query_table(field.entity_key)
        text = text.strip()
        condition = 'ИСТИНА'
        if text:
            from project_cust_38 import Cust_Functions as F
            pattern = text.replace('~', '~~')
            for char in '%_[]^':
                pattern = pattern.replace(char, '~' + char)
            pattern = ('%' + pattern + '%').replace('"', '""')
            condition = (
                f'Источник.{field.field_key} ПОДОБНО "{pattern}" '
                'СПЕЦСИМВОЛ "~" '
            )
        if after is not None:
            condition = f'({condition}) И Источник.Ссылка > &PlannerAfter'

        query = f"""
            ВЫБРАТЬ ПЕРВЫЕ {limit + 1}
                ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР(Источник.Ссылка)) КАК ref_key,
                ПРЕДСТАВЛЕНИЕ(Источник.Ссылка) КАК display_snapshot
            ИЗ
                {table} КАК Источник
            ГДЕ
                {condition}
            УПОРЯДОЧИТЬ ПО
                Источник.Ссылка
        """
        refs = None
        if after is not None:
            refs = self.interface.Refs_wet(query)
            refs.add_ref(self.interface.Ref_wet(
                'PlannerAfter',
                after.entity_key,
                after.ref_key
            ))
        try:
            code, payload = self.interface.get_wet_request(
                text=query,
                lazy_method_huours=0,
                refs=refs
            )
        except Exception as exc:
            raise ErpEntityError('Не удалось выполнить поиск по ERP') from exc
        if code != 200:
            raise ErpEntityError(f'Ошибка поиска ERP: код {code!r}.')
        if not isinstance(payload, typing.Mapping):
            raise ErpEntityError('некорректный ответ из erp')
        if payload.get('ЕстьОшибки'):
            raise ErpEntityError(f'Ошибка на стороне ERP: {payload.get("Ошибки")}')
        rows = payload.get('data')
        if not isinstance(rows, list) or len(rows) > limit + 1:
            raise ErpEntityError('ERP вернула некорректный результат поиска')
        items = []
        for row in rows[:limit]:
            ref_key = row.get('ref_key')
            try:
                ref_uuid = UUID(ref_key)
            except Exception as exc:
                raise ErpEntityError('В результате поиска некорректный UUID,') from exc
            items.append(ErpEntityRef(
                source_key=source_key,
                entity_key=field.entity_key,
                ref_key=str(ref_uuid),
                display_snapshot=str(row['display_snapshot'] or ''),
            ))
        return ErpSearchResult(
            items=tuple(items),
            has_more=len(rows) > limit
        )

    @staticmethod
    def __page_literal(value):
        if not isinstance(value, str) or len(value) > 200 or any(char in value for char in '\x00\r\n'):
            raise ErpEntityError('Условие ERP должно быть строкой до 200 символов без переноса строк')
        return '"' + value.replace('"', '""') + '"'

    def __page_where(self, field, conditions):
        if conditions is None:
            conditions = {}
        if not isinstance(conditions, typing.Mapping):
            raise ErpEntityError('Условия ERP должны быть словарём')
        parts = []
        references = []

        def literal(column, value):
            if column == 'value':
                return self.__page_literal(value)
            try:
                reference = str(UUID(value))
            except (ValueError, TypeError, AttributeError) as exc:
                raise ErpEntityError('Фильтр UUID требует полный корректный UUID') from exc
            name = f'PlannerFilter{len(references)}'
            references.append((name, reference))
            return '&' + name

        def empty_condition(column, expression, is_empty):
            if column == 'value':
                if is_empty:
                    return f'({expression} ЕСТЬ NULL ИЛИ {expression} = "" ИЛИ {expression} = "0")'
                return f'({expression} ЕСТЬ НЕ NULL И {expression} <> "" И {expression} <> "0")'
            empty_reference = literal(column, '00000000-0000-0000-0000-000000000000')
            if is_empty:
                return f'({expression} ЕСТЬ NULL ИЛИ {expression} = {empty_reference})'
            return f'({expression} ЕСТЬ НЕ NULL И {expression} <> {empty_reference})'

        for key, value in conditions.items():
            if not isinstance(key, str):
                raise ErpEntityError('Имя условия ERP должно быть строкой')
            column, separator, lookup = key.partition('__')
            lookup = lookup if separator else 'exact'
            allowed = ('exact', 'ne', 'contains', 'gt', 'gte', 'lt', 'lte', 'in', 'isnull') if column == 'value' else ('exact', 'ne', 'in', 'isnull')
            if column not in ('value', 'ref_key') or lookup not in allowed:
                raise ErpEntityError(f'Неподдерживаемое условие ERP: {key}')
            expression = f'Источник.{field.field_key}' if column == 'value' else 'Источник.Ссылка'
            if lookup == 'isnull':
                if type(value) is not bool:
                    raise ErpEntityError('Условие isnull принимает только True или False')
                parts.append(empty_condition(column, expression, value))
            elif lookup in ('exact', 'ne') and value is None:
                parts.append(empty_condition(column, expression, lookup == 'exact'))
            elif lookup == 'in':
                if not isinstance(value, (list, tuple, set, frozenset)) or len(value) > 500:
                    raise ErpEntityError('Условие in требует коллекцию не более 500 значений')
                values = [literal(column, item) for item in value if item is not None]
                choices = []
                if values:
                    choices.append(f'{expression} В ({", ".join(values)})')
                if None in value:
                    choices.append(f'{expression} ЕСТЬ NULL')
                parts.append('(' + ' ИЛИ '.join(choices) + ')' if choices else 'ЛОЖЬ')
            elif lookup == 'contains':
                self.__page_literal(value)
                pattern = value.replace('~', '~~')
                for char in '%_[]^':
                    pattern = pattern.replace(char, '~' + char)
                pattern = '"%' + pattern.replace('"', '""') + '%"'
                parts.append(f'{expression} ПОДОБНО {pattern} СПЕЦСИМВОЛ "~"')
            else:
                sign = {'exact': '=', 'ne': '<>', 'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<='}[lookup]
                parts.append(f'{expression} {sign} {literal(column, value)}')
        return ' И '.join('(' + part + ')' for part in parts) or 'ИСТИНА', references

    @staticmethod
    def __page_count(value):
        from decimal import Decimal, InvalidOperation

        if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
            raise ErpEntityError('ERP вернула некорректное количество записей')
        try:
            number = Decimal(str(value))
            if not number.is_finite() or number < 0 or number != number.to_integral_value():
                raise ValueError()
            return int(number)
        except (InvalidOperation, ValueError, OverflowError) as exc:
            raise ErpEntityError('ERP вернула некорректное количество записей') from exc

    def search_page(self, field: AB.BindingField | dict, *, conditions=None,
                    page: int = 1, limit: int = 100, last: bool = False) -> ErpSearchPage:
        if isinstance(field, dict):
            field = AB.BindingField.from_dict(field)
        if not isinstance(field, AB.BindingField):
            raise ErpEntityError('field должен быть типа BindingField или dict')
        if field.provider != AB.SourceProvider.ERP or field.relation_steps:
            raise ErpEntityError('Поддерживается только прямое поле ERP')
        if not isinstance(field.field_key, str) or not field.field_key.isidentifier():
            raise ErpEntityError('Некорректное имя поля ERP')
        if not isinstance(field.entity_key, str):
            raise ErpEntityError('Некорректный путь объекта ERP')
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ErpEntityError('Размер страницы должен быть целым числом от 1 до 500')
        if type(page) is not int or page < 1:
            raise ErpEntityError('Номер страницы должен быть положительным целым числом')
        if type(last) is not bool:
            raise ErpEntityError('Параметр last должен быть True или False')
        source_key = self.__source_key_getter()
        if not isinstance(source_key, str) or not source_key:
            raise ErpEntityError('Не задан источник ERP')
        if field.source_key not in (source_key, field.entity_key):
            raise ErpEntityError('Поле относится к другому источнику ERP')
        table = self.__query_table(field.entity_key)
        condition, references = self.__page_where(field, conditions)

        for attempt in range(2):
            descending = last or page > 1
            if last or page == 1:
                window = f'''
                    ВЫБРАТЬ ПЕРВЫЕ {limit}
                        Источник.Ссылка КАК Ссылка,
                        Источник.{field.field_key} КАК field_value
                    ИЗ {table} КАК Источник
                    ГДЕ {condition}
                    УПОРЯДОЧИТЬ ПО Источник.Ссылка {"УБЫВ" if last else ""}
                '''
            else:
                window = f'''
                    ВЫБРАТЬ ПЕРВЫЕ {limit}
                        Окно.Ссылка КАК Ссылка,
                        Окно.field_value КАК field_value
                    ИЗ (
                        ВЫБРАТЬ ПЕРВЫЕ {page * limit}
                            Источник.Ссылка КАК Ссылка,
                            Источник.{field.field_key} КАК field_value
                        ИЗ {table} КАК Источник
                        ГДЕ {condition}
                        УПОРЯДОЧИТЬ ПО Источник.Ссылка
                    ) КАК Окно
                    УПОРЯДОЧИТЬ ПО Окно.Ссылка УБЫВ
                '''
            safe_reference = f'ЕСТЬNULL(Страница.Ссылка, ЗНАЧЕНИЕ({table}.ПустаяСсылка))'
            query = f'''
                ВЫБРАТЬ
                    Счетчик.total_count КАК total_count,
                    ПРЕДСТАВЛЕНИЕ(УНИКАЛЬНЫЙИДЕНТИФИКАТОР({safe_reference})) КАК ref_key,
                    ПРЕДСТАВЛЕНИЕ({safe_reference}) КАК display_snapshot,
                    Страница.field_value КАК field_value
                ИЗ (
                    ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК total_count
                    ИЗ {table} КАК Источник
                    ГДЕ {condition}
                ) КАК Счетчик
                ЛЕВОЕ СОЕДИНЕНИЕ ({window}) КАК Страница
                ПО ИСТИНА
                УПОРЯДОЧИТЬ ПО Страница.Ссылка {"УБЫВ" if descending else ""}
            '''
            refs = None
            if references:
                refs = self.interface.Refs_wet(query)
                for name, reference in references:
                    refs.add_ref(self.interface.Ref_wet(name, field.entity_key, reference))
            try:
                code, payload = self.interface.get_wet_request(text=query, lazy_method_huours=0, refs=refs)
            except Exception as exc:
                raise ErpEntityError('Не удалось загрузить страницу ERP') from exc
            if code != 200:
                raise ErpEntityError(f'Ошибка загрузки ERP: код {code!r}')
            if not isinstance(payload, typing.Mapping):
                raise ErpEntityError('Некорректный ответ ERP')
            if payload.get('ЕстьОшибки'):
                raise ErpEntityError(f'Ошибка на стороне ERP: {payload.get("Ошибки")}')
            rows = payload.get('data')
            if not isinstance(rows, list) or not rows or len(rows) > limit:
                raise ErpEntityError('ERP вернула некорректный размер страницы')
            if any(not isinstance(row, typing.Mapping) or 'total_count' not in row for row in rows):
                raise ErpEntityError('В ответе ERP отсутствует количество записей')
            total_count = self.__page_count(rows[0]['total_count'])
            if any(self.__page_count(row['total_count']) != total_count for row in rows):
                raise ErpEntityError('ERP вернула несовпадающие счётчики страницы')
            if total_count == 0:
                if len(rows) != 1:
                    raise ErpEntityError('ERP вернула некорректную пустую страницу')
                return ErpSearchPage(items=(), total_count=0, page_number=1)
            count_pages = (total_count + limit - 1) // limit
            if not last and page > count_pages:
                last = True
                continue
            if len(rows) != min(limit, total_count):
                raise ErpEntityError('Данные ERP изменились во время загрузки; повторите обновление')
            page_number = count_pages if last else page
            actual_size = min(limit, total_count - (page_number - 1) * limit)
            items = []
            identities = set()
            for row in rows:
                if any(key not in row for key in ('ref_key', 'display_snapshot', 'field_value')):
                    raise ErpEntityError('В ответе ERP отсутствуют поля записи')
                try:
                    reference_uuid = UUID(row['ref_key'])
                    if not reference_uuid.int or reference_uuid in identities:
                        raise ValueError()
                except (ValueError, TypeError, AttributeError) as exc:
                    raise ErpEntityError('ERP вернула пустой, повторный или некорректный UUID') from exc
                identities.add(reference_uuid)
                value = row['field_value']
                display = row['display_snapshot']
                if value is not None and not isinstance(value, str):
                    raise ErpEntityError('Фильтруемое поле ERP должно быть строковым')
                if display is not None and not isinstance(display, str):
                    raise ErpEntityError('ERP вернула некорректное представление записи')
                reference = ErpEntityRef(source_key=source_key, entity_key=field.entity_key,
                                         ref_key=str(reference_uuid), display_snapshot=display or '')
                items.append(ErpEntityRow(reference=reference,
                                          values={field.field_key: value},
                                          presentations={field.field_key: value or ''}))
            items = items[:actual_size]
            if descending:
                items.reverse()
            return ErpSearchPage(items=tuple(items), total_count=total_count, page_number=page_number)
        raise ErpEntityError('Не удалось определить актуальную страницу ERP')


class ErpSearchSession:
    def __init__(self, service: ErpEntityService, field: AB.BindingField | dict, *, limit: int = 100):
        self.__service = service
        self.__field = field
        self.__text = ''
        self.__limit = limit
        self.__items: tuple[ErpEntityRef, ...] = ()
        self.__page: ErpSearchResult | None = None

    @property
    def text(self) -> str:
        return self.__text

    @property
    def items(self) -> tuple[ErpEntityRef, ...]:
        return self.__items

    @property
    def has_more(self) -> bool:
        return self.__page is not None and self.__page.has_more

    def start(self, text: str = '') -> ErpSearchResult:
        page = self.__service.search_text(
            self.__field,
            text,
            limit=self.__limit
        )
        self.__text = text
        self.__items = page.items
        self.__page = page
        return page

    def load_more(self) -> ErpSearchResult:
        if self.__page is None:
            raise ErpEntityError('Объект поиска не инициализирован')
        if not self.__page.has_more:
            return ErpSearchResult(items=(), has_more=False)
        page = self.__service.search_text(
            self.__field,
            self.__text,
            limit=self.__limit,
            after=self.__page.next_after
        )
        self.__items = self.__items + page.items
        self.__page = page
        return page

## === UI

from project_cust_38 import Cust_page_manager as CPM


class ErpTablePageManager(CPM.SqlPageManager):
    """ERP-источник с интерфейсом серверного менеджера страниц CQT."""

    def __init__(self, service, field, *, page_size=100):
        self.service = service
        self.field = AB.BindingField.from_dict(field) if isinstance(field, dict) else field
        if not isinstance(self.field, AB.BindingField):
            raise ErpEntityError('Ожидается поле BindingField')
        self.value_column = self.field.field_key
        if self.value_column in ('Представление', 'UUID'):
            raise ErpEntityError('Имя поля совпадает со служебной колонкой подбора')
        self._seek_last = False
        columns = (self.value_column, 'Представление', 'UUID')
        super().__init__(
            bd=None, query=self.field.entity_key, columns=columns,
            key_column='UUID', order_by=('UUID',), page_size=page_size,
            column_types={column: str for column in columns}
        )

    @staticmethod
    def _positive_int(value):
        value = CPM.SqlPageManager._positive_int(value)
        if value > 500:
            raise ErpEntityError('Размер страницы ERP должен быть от 1 до 500')
        return value

    @classmethod
    def _normalize_query(cls, query):
        if not isinstance(query, str):
            raise ErpEntityError('Источник ERP должен быть строкой')
        group, separator, name = query.partition('.')
        if group not in ('Документы', 'Справочники') or not separator or not name.isidentifier():
            raise ErpEntityError('Некорректный источник ERP')
        return query

    def _normalize_order(self, fields):
        if isinstance(fields, str) or tuple(fields) not in ((), ('UUID',)):
            raise ErpEntityError('В ERP-подборе используется порядок по ссылке 1С')
        return ('UUID',)

    def _normalize_filters(self, conditions):
        result = {}
        for key, value in super()._normalize_filters(conditions).items():
            column, lookup = self._split_filter(key)
            if column == 'Представление':
                raise ErpEntityError('Представление доступно только для просмотра; используйте колонку реквизита')
            if column == 'UUID':
                if lookup == 'contains':
                    lookup = 'exact'
                if lookup not in ('exact', 'ne', 'in', 'isnull'):
                    raise ErpEntityError('Для UUID поддерживаются точное сравнение и проверка пустого значения')
                if lookup != 'isnull' and value is not None:
                    try:
                        value = tuple(str(UUID(item)) for item in value) if lookup == 'in' else str(UUID(value))
                    except (ValueError, TypeError, AttributeError) as exc:
                        raise ErpEntityError('Введите UUID полностью; поиск по части UUID не поддерживается') from exc
            normalized_key = column + '__' + lookup
            if normalized_key in result:
                raise ErpEntityError('Условие фильтра задано дважды')
            result[normalized_key] = value
        return result

    def _load(self, recount=False):
        use_last = self._seek_last and self._committed is not None and self._state()[:3] == self._committed[:3]
        try:
            conditions = {}
            for key, value in self._filters.items():
                column, lookup = self._split_filter(key)
                name = 'ref_key' if column == 'UUID' else 'value'
                conditions[name + '__' + lookup] = value
            page = self.service.search_page(
                self.field, conditions=conditions, page=self.current_page,
                limit=self.page_size, last=use_last
            )
            rows = [
                {
                    self.value_column: item.values[self.field.field_key],
                    'Представление': str(item.reference),
                    'UUID': item.reference.ref_key,
                    '_reference': item.reference
                }
                for item in page.items
            ]
        except Exception as exc:
            self._restore()
            self.last_error = exc
            raise
        finally:
            self._seek_last = False
        self.total_count = page.total_count
        self.current_page = page.page_number
        self._rows = rows
        self._loaded = True
        self._committed = self._state()
        self.last_error = None

    def page_data(self):
        data, _ = super().page_data()
        user_data = [[None] * len(self.columns)]
        user_data.extend([row['_reference'], None, None] for row in self._rows)
        return data, user_data

    def first(self):
        self._seek_last = False
        return super().first()

    def previous(self):
        self._seek_last = False
        return super().previous()

    def next(self):
        self._seek_last = False
        return super().next()

    def last(self):
        changed = super().last()
        self._seek_last = changed
        return changed


class ErpEntityTablePicker:
    """Подбор ERP в общем диалоге с серверным фильтром по колонкам."""

    def __init__(self, service, field, *, current=None, limit=100):
        self.page_manager = ErpTablePageManager(service, field, page_size=limit)
        self.selected_reference = current
        self.committed_filter_texts = None

    def decorate(self, dialog):
        self.dialog = dialog
        self.table = dialog.ui.tbl
        dialog.resize(1100, 560)
        dialog.ui.cmb_action.setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        current_label = QtWidgets.QLabel(
            f'Сейчас: {self.selected_reference if self.selected_reference is not None else "не выбрано"}'
        )
        current_label.setTextFormat(QtCore.Qt.PlainText)
        current_label.setWordWrap(True)
        self.status_label = QtWidgets.QLabel()
        dialog.ui.verticalLayout_5.insertWidget(0, current_label)
        dialog.ui.verticalLayout_5.insertWidget(1, self.status_label)
        for button in dialog.findChildren(QtWidgets.QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.page_manager.bind_dialog(dialog, after_page=self._after_page, on_error=self._on_error)

    def _lock_presentation_filter(self):
        column = self.page_manager.columns.index('Представление')
        item = self.dialog.ui.tbl_filtr.item(0, column)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        item.setToolTip('Представление 1С доступно для просмотра. Фильтруйте по реквизиту или полному UUID')
        self.page_manager._locked_filter_columns.add('Представление')

    def _after_page(self, dialog, manager):
        self._lock_presentation_filter()
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        if self.table.rowCount():
            self.table.selectRow(0)
        self.status_label.setText(f'Записей: {manager.total_count}. Фильтр по всей ERP-выборке')
        self.committed_filter_texts = [
            dialog.ui.tbl_filtr.item(0, column).text()
            for column in range(len(manager.columns))
        ]
        self._update_buttons()

    def _on_error(self, dialog, error):
        if self.committed_filter_texts is not None:
            blocker = QtCore.QSignalBlocker(dialog.ui.tbl_filtr)
            for column, value in enumerate(self.committed_filter_texts):
                dialog.ui.tbl_filtr.item(0, column).setText(value)
            del blocker
        self._lock_presentation_filter()
        self._update_buttons()
        QtWidgets.QMessageBox.critical(dialog, 'Ошибка загрузки ERP', str(error))

    def _reference(self):
        rows = self.table.selectionModel().selectedRows(0)
        if len(rows) != 1 or self.table.isRowHidden(rows[0].row()):
            return None
        reference = CQT.getCustData(self.table, rows[0].row(), 0, modifier=101)
        return reference if isinstance(reference, ErpEntityRef) else None

    def _update_buttons(self, *args):
        self.dialog.yes_btn.setEnabled(self._reference() is not None)

    def on_button(self, button, dialog, table):
        if button is dialog.yes_btn:
            reference = self._reference()
            if reference is not None:
                self.selected_reference = reference
                dialog.accept()
        else:
            dialog.reject()


def select_erp_entity(parent, service, field, *, current=None, limit=100):
    try:
        picker = ErpEntityTablePicker(service, field, current=current, limit=limit)
        accepted = CQT.msgboxg_get_table(
            parent, 'Выбор записи ERP', None,
            btn0_name='Выбрать', btn1_name='Отмена', WindowTitle='Выбор записи ERP',
            show_filtr=True, selection_from_tbl=True, selectRows=True, ExtendedSelection=False,
            sortingEnabled=False, yesNoMode=True, not_standart_close=True,
            page_manager=picker.page_manager, decorate_dialog=picker.decorate, func_btn0=picker.on_button
        ) == QtWidgets.QDialog.Accepted
    except Exception as exc:
        QtWidgets.QMessageBox.critical(parent, 'Ошибка загрузки ERP', str(exc))
        return ErpEntitySelection(accepted=False, reference=current)
    return ErpEntitySelection(
        accepted=accepted,
        reference=picker.selected_reference if accepted else current
    )
