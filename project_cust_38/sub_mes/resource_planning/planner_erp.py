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

class ErpTablePageManager:

    def __init__(self, session: ErpSearchSession):
        self.session = session
        self.__pages: list[ErpSearchResult] = []
        self.__index = 0

    @property
    def loaded(self):
        return bool(self.__pages)

    @property
    def text(self):
        return self.session.text

    @property
    def count_pages(self):
        if self.session.has_more:
            return None
        if not self.__pages or not self.__pages[0].items:
            return 0
        return len(self.__pages)

    @property
    def shown_page(self):
        return self.__index + 1 if self.count_pages != 0 else 0

    @property
    def can_go_back(self):
        return self.__index > 0

    @property
    def can_go_forward(self):
        return self.__index + 1 < len(self.__pages) or self.session.has_more

    @property
    def can_go_last(self):
        return self.count_pages is not None and self.can_go_forward

    def set_data(self, data, user_data=None):
        pass

    def page_data(self):
        data = [['Представление', 'UUID']]
        user_data = [[None, None]]
        if self.loaded:
            for reference in self.__pages[self.__index].items:
                data.append([str(reference), reference.ref_key])
                user_data.append([reference, None])
        return data, user_data

    def start(self, text=''):
        page = self.session.start(text)
        self.__pages = [page]
        self.__index = 0
        return page

    def first(self):
        if not self.can_go_back:
            return False
        self.__index = 0
        return True

    def previous(self):
        if not self.can_go_back:
            return False
        self.__index -= 1
        return True

    def next(self):
        if self.__index + 1 < len(self.__pages):
            self.__index += 1
            return True
        if not self.session.has_more:
            return False
        page = self.session.load_more()
        if page.items:
            self.__pages.append(page)
            self.__index += 1
        return True

    def last(self):
        if not self.can_go_last:
            return False
        self.__index = len(self.__pages) - 1
        return True


class ErpEntityTablePicker:
    """ERP-подбор со штатной таблицей и фильтром CQT."""

    def __init__(self, service, field, *, current=None, limit=100):
        self.field = AB.BindingField.from_dict(field) if isinstance(field, dict) else field
        self.page_manager = ErpTablePageManager(ErpSearchSession(service, self.field, limit=limit))
        self.selected_reference = current
        self.busy = False

    def decorate(self, dialog):
        self.dialog = dialog
        self.table = dialog.ui.tbl
        self.filter_table = dialog.ui.tbl_filtr
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        dialog.resize(1000, 560)
        dialog.ui.cmb_action.setVisible(False)

        CQT.ConnectFilterKeyEvents(dialog, self.table, self.filter_table)
        self.native_filter_key_release = self.filter_table.keyReleaseEvent
        self.filter_table.keyReleaseEvent = self._filter_key_release

        for button, action in (
            (dialog.ui.btn_skip_back, self.page_manager.first),
            (dialog.ui.btn_back, self.page_manager.previous),
            (dialog.ui.btn_forward, self.page_manager.next),
            (dialog.ui.btn_skip_forward, self.page_manager.last)
        ):
            button.clicked.disconnect()
            button.clicked.connect(lambda checked=False, action=action: self._change_page(action))
        self.first_page_tooltip = dialog.ui.btn_skip_back.toolTip()
        for button in dialog.findChildren(QtWidgets.QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)

        self.table.itemSelectionChanged.connect(self._update_buttons)
        self._update_buttons()
        self.filter_table.setFocus()
        self.initial_load = QtCore.QTimer(dialog)
        self.initial_load.setSingleShot(True)
        self.initial_load.timeout.connect(lambda: self._run(self.page_manager.start))
        dialog.finished.connect(self.initial_load.stop)
        self.initial_load.start(0)

    def _reference(self):
        rows = self.table.selectionModel().selectedRows(0)
        if len(rows) != 1 or self.table.isRowHidden(rows[0].row()):
            return None
        reference = CQT.getCustData(self.table, rows[0].row(), 0, modifier=101)
        return reference if isinstance(reference, ErpEntityRef) else None

    def _ensure_visible_selection(self):
        if self._reference() is not None:
            return
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                self.table.selectRow(row)
                break

    def _filter_key_release(self, event):
        self.native_filter_key_release(event)
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) or (
            event.key() == QtCore.Qt.Key_Delete and event.modifiers() == QtCore.Qt.ShiftModifier
        ):
            self._ensure_visible_selection()
            self._update_buttons()

    def _update_buttons(self, *args):
        ready = not self.busy and self.page_manager.loaded
        self.filter_table.setEnabled(not self.busy)
        self.dialog.yes_btn.setEnabled(ready and self._reference() is not None)
        self.dialog.set_page()
        if self.page_manager.count_pages is None:
            label = self.dialog.ui.lbl_page
            label.setText(label.text().replace('/None', '/?'))
            label.setToolTip(f'Страница {self.page_manager.shown_page}. Общее число страниц пока неизвестно')
        self.dialog.ui.btn_skip_back.setEnabled(
            not self.busy and (self.page_manager.can_go_back or not self.page_manager.loaded)
        )
        self.dialog.ui.btn_skip_back.setToolTip(
            self.first_page_tooltip if self.page_manager.loaded else 'Повторить загрузку первой страницы'
        )
        self.dialog.ui.btn_back.setEnabled(ready and self.page_manager.can_go_back)
        self.dialog.ui.btn_forward.setEnabled(ready and self.page_manager.can_go_forward)
        self.dialog.ui.btn_skip_forward.setEnabled(ready and self.page_manager.can_go_last)

    def _run(self, action):
        if self.busy:
            return
        self.busy = True
        self._update_buttons()
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            if action():
                self.dialog.fill_current_page()
                header = self.table.horizontalHeader()
                header.setStretchLastSection(False)
                header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
                header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
                CQT.apply_filtr_c(self.dialog, self.filter_table, self.table, save_data=False)
                self._ensure_visible_selection()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self.dialog, 'Ошибка загрузки ERP', str(exc))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.busy = False
            self._update_buttons()

    def _change_page(self, action):
        self._run(action if self.page_manager.loaded else self.page_manager.start)

    def on_button(self, button, dialog, table):
        if button is dialog.yes_btn:
            if not self.busy and self.page_manager.loaded:
                reference = self._reference()
                if reference is not None:
                    self.selected_reference = reference
                    dialog.accept()
        else:
            dialog.reject()


def select_erp_entity(parent, service, field, *, current=None, limit=100):
    picker = ErpEntityTablePicker(service, field, current=current, limit=limit)
    accepted = CQT.msgboxg_get_table(
        parent, 'Выбор записи ERP', [['Представление', 'UUID']],
        btn0_name='Выбрать', btn1_name='Отмена', WindowTitle='Выбор записи ERP',
        show_filtr=True, selection_from_tbl=True, selectRows=True, ExtendedSelection=False,
        sortingEnabled=False, yesNoMode=True, not_standart_close=True,
        page_manager=picker.page_manager, decorate_dialog=picker.decorate, func_btn0=picker.on_button
    ) == QtWidgets.QDialog.Accepted
    return ErpEntitySelection(
        accepted=accepted,
        reference=picker.selected_reference if accepted else current
    )