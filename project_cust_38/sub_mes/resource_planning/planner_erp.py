import dataclasses
import sys
import typing
from dataclasses import dataclass, replace

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

from PyQt5 import QtCore, QtWidgets

from project_cust_38.sub_mes.resource_planning import planner_erp as PERP
from project_cust_38.sub_mes.resource_planning import attribute_binding as AB


class ErpEntityDialog(QtWidgets.QDialog):
    def __init__(self, parent, service, field, *, current=None, limit=100):
        super().__init__(parent)
        field = AB.BindingField.from_dict(field) if isinstance(field, dict) else field
        self.session = PERP.ErpSearchSession(service, field, limit=limit)
        self.selected_reference = current
        self.loaded = False
        self.busy = False
        self.setWindowTitle('Выбор записи ERP')
        self.resize(920, 560)
        layout = QtWidgets.QVBoxLayout(self)

        current_label = QtWidgets.QLabel(
            f'Сейчас: {current if current is not None else "не выбрано"}'
        )
        current_label.setTextFormat(QtCore.Qt.PlainText)
        current_label.setWordWrap(True)
        layout.addWidget(current_label)

        search_layout = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setMaxLength(200)
        self.search_edit.setPlaceholderText(f'Поиск по полю: {field.display_name}')
        self.search_button = QtWidgets.QPushButton('Найти')
        search_layout.addWidget(self.search_edit, 1)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['Представление', 'UUID'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSortIndicator(0, QtCore.Qt.AscendingOrder)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table, 1)

        bottom = QtWidgets.QHBoxLayout()
        self.more_button = QtWidgets.QPushButton('Ещё')
        self.status_label = QtWidgets.QLabel()
        self.clear_button = QtWidgets.QPushButton('Очистить')
        self.cancel_button = QtWidgets.QPushButton('Отмена')
        self.select_button = QtWidgets.QPushButton('Выбрать')
        bottom.addWidget(self.more_button)
        bottom.addWidget(self.status_label, 1)
        for button in (self.clear_button, self.cancel_button, self.select_button):
            bottom.addWidget(button)
        layout.addLayout(bottom)
        for button in self.findChildren(QtWidgets.QPushButton):
            button.setAutoDefault(False)

        self.search_button.clicked.connect(lambda: self._load(False))
        self.search_edit.returnPressed.connect(lambda: self._load(False))
        self.more_button.clicked.connect(lambda: self._load(True))
        self.search_edit.textChanged.connect(self._update_buttons)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.select_button.clicked.connect(self._choose)
        self.table.doubleClicked.connect(self._choose)
        self.clear_button.clicked.connect(self._clear)
        self.cancel_button.clicked.connect(self.reject)
        self._update_buttons()
        QtCore.QTimer.singleShot(0, lambda: self._load(False))

    def _matches_query(self):
        return self.loaded and self.search_edit.text().strip() == self.session.text.strip()

    def _reference(self):
        item = self.table.item(self.table.currentRow(), 0)
        return None if item is None else item.data(QtCore.Qt.UserRole)

    def _update_buttons(self, *args):
        ready = not self.busy and self._matches_query()
        self.search_edit.setEnabled(not self.busy)
        self.search_button.setEnabled(not self.busy)
        self.clear_button.setEnabled(not self.busy)
        self.more_button.setEnabled(ready and self.session.has_more)
        self.select_button.setEnabled(ready and self._reference() is not None)
        if self.busy:
            text = 'Загрузка…'
        elif not self._matches_query():
            text = 'Нажмите «Найти»'
        else:
            text = f'Загружено: {len(self.session.items)}'
        self.status_label.setText(text)

    def _load(self, more):
        if self.busy or (more and (not self._matches_query() or not self.session.has_more)):
            return
        self.busy = True
        self._update_buttons()
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            page = self.session.load_more() if more else self.session.start(self.search_edit.text().strip())
            self.loaded = True
            self.table.setSortingEnabled(False)
            if not more:
                self.table.setRowCount(0)
            for reference in page.items:
                row = self.table.rowCount()
                self.table.insertRow(row)
                item = QtWidgets.QTableWidgetItem(str(reference))
                item.setToolTip(str(reference))
                item.setData(QtCore.Qt.UserRole, reference)
                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(reference.ref_key))
            self.table.setSortingEnabled(True)
            if self.table.currentRow() < 0 and self.table.rowCount():
                self.table.selectRow(0)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, 'Ошибка поиска ERP', str(exc))
        finally:
            self.busy = False
            QtWidgets.QApplication.restoreOverrideCursor()
            self._update_buttons()

    def _choose(self, *args):
        if self.busy or not self._matches_query():
            return
        reference = self._reference()
        if reference is not None:
            self.selected_reference = reference
            self.accept()

    def _clear(self):
        if not self.busy:
            self.selected_reference = None
            self.accept()


def select_erp_entity(parent, service, field, *, current=None, limit=100):
    dialog = ErpEntityDialog(parent, service, field, current=current, limit=limit)
    accepted = dialog.exec_() == QtWidgets.QDialog.Accepted
    return PERP.ErpEntitySelection(
        accepted=accepted,
        reference=dialog.selected_reference if accepted else current
    )

