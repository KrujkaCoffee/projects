from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

try:
    from . import planner_registry_stage2 as registry
except ImportError:
    import planner_registry_stage2 as registry


MES_ENTITY_REF_VERSION = 1
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 200
_IDENTITY_ALIAS = "__mes_identity"
_DISPLAY_ALIAS = "__mes_display"
_FILTER_ALIAS_PREFIX = "__mes_filter_"


class MesEntityError(registry.PlannerRegistryError):
    """Экземпляр зарегистрированного справочника нельзя безопасно выбрать или восстановить."""


class MesQueryExecutor(Protocol):
    def __call__(
        self,
        db_key: str,
        sql: str,
        parameters: Sequence[Any],
    ) -> Sequence[Mapping[str, Any]]: ...


@dataclass(frozen=True)
class MesEntityRef:
    source_key: str
    identity: tuple[tuple[str, Any], ...]
    presentation_key: str
    display_snapshot: str
    version: int = MES_ENTITY_REF_VERSION

    def __post_init__(self) -> None:
        if self.version != MES_ENTITY_REF_VERSION:
            raise MesEntityError(
                f"Версия ссылки на сущность МЕС {self.version!r} не поддерживается."
            )
        if not self.source_key.strip():
            raise MesEntityError("В ссылке на сущность МЕС не задан source_key.")
        if not self.presentation_key.strip():
            raise MesEntityError("В ссылке на сущность МЕС не задан presentation_key.")
        if not self.identity:
            raise MesEntityError("В ссылке на сущность МЕС не задана идентичность строки.")
        names: set[str] = set()
        for name, value in self.identity:
            if not str(name).strip():
                raise MesEntityError("В идентичности строки найдено пустое имя поля.")
            if name in names:
                raise MesEntityError(f"Поле идентичности {name!r} указано несколько раз.")
            if value is None or not isinstance(value, (str, int, float, bool)):
                raise MesEntityError(
                    f"Значение идентичности {name!r} имеет неподдерживаемый тип."
                )
            names.add(name)

    @classmethod
    def create(
        cls,
        *,
        source_key: str,
        identity: Mapping[str, Any],
        presentation_key: str,
        display_snapshot: Any,
    ) -> "MesEntityRef":
        return cls(
            source_key=str(source_key),
            identity=tuple((str(name), value) for name, value in identity.items()),
            presentation_key=str(presentation_key),
            display_snapshot="" if display_snapshot is None else str(display_snapshot),
        )

    @classmethod
    def deserialize(cls, data: Any) -> "MesEntityRef":
        if isinstance(data, cls):
            return data
        if not isinstance(data, Mapping):
            raise MesEntityError("Ссылка на сущность МЕС должна быть словарём.")
        identity = data.get("identity")
        if isinstance(identity, Mapping):
            identity_items = tuple((str(name), value) for name, value in identity.items())
        elif isinstance(identity, (list, tuple)):
            try:
                identity_items = tuple((str(item[0]), item[1]) for item in identity)
            except (IndexError, TypeError) as exc:
                raise MesEntityError(
                    "В ссылке на сущность МЕС повреждена идентичность строки."
                ) from exc
        else:
            raise MesEntityError("В ссылке на сущность МЕС повреждена идентичность строки.")
        display_snapshot = data.get("display_snapshot")
        try:
            version = int(data.get("version", MES_ENTITY_REF_VERSION))
        except (TypeError, ValueError) as exc:
            raise MesEntityError("В ссылке на сущность МЕС повреждена версия формата.") from exc
        return cls(
            source_key=str(data.get("source_key") or ""),
            identity=identity_items,
            presentation_key=str(data.get("presentation_key") or ""),
            display_snapshot="" if display_snapshot is None else str(display_snapshot),
            version=version,
        )

    def serialize(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source_key": self.source_key,
            "identity": dict(self.identity),
            "presentation_key": self.presentation_key,
            "display_snapshot": self.display_snapshot,
        }

    @property
    def identity_dict(self) -> dict[str, Any]:
        return dict(self.identity)

    @property
    def identity_text(self) -> str:
        return ", ".join(f"{name}={value}" for name, value in self.identity)

    def __str__(self) -> str:
        return self.display_snapshot or self.identity_text


@dataclass(frozen=True)
class MesEntityRow:
    reference: MesEntityRef
    filter_values: tuple[tuple[str, Any], ...] = ()

    @property
    def display(self) -> str:
        return str(self.reference)

    @property
    def identity(self) -> dict[str, Any]:
        return self.reference.identity_dict

    @property
    def filters(self) -> dict[str, Any]:
        return dict(self.filter_values)


@dataclass(frozen=True)
class MesSearchPage:
    rows: tuple[MesEntityRow, ...]
    offset: int
    limit: int
    has_more: bool


@dataclass(frozen=True)
class MesEntityResolution:
    requested: MesEntityRef
    current: MesEntityRef | None
    resolved: bool
    reason: str = ""


@dataclass(frozen=True)
class MesEntitySelection:
    accepted: bool
    reference: MesEntityRef | None = None


@dataclass(frozen=True)
class _QueryLayout:
    db_key: str
    source_table_name: str
    identity_field_name: str
    display_expression: str
    join_sql: str
    filter_fields: tuple[tuple[str, str, str], ...]


class MesEntityService:
    def __init__(
        self,
        catalog: registry.AdminCatalog,
        executor: MesQueryExecutor,
        *,
        max_page_size: int = MAX_PAGE_SIZE,
    ) -> None:
        self.catalog = catalog
        self.executor = executor
        self.max_page_size = max(1, min(int(max_page_size), MAX_PAGE_SIZE))

    @classmethod
    def from_type_catalog(
        cls,
        type_catalog: Any,
        *,
        executor: MesQueryExecutor | None = None,
    ) -> "MesEntityService":
        runtime = type_catalog.session.get_runtime()
        catalog = getattr(runtime, "catalog", None)
        if not isinstance(catalog, registry.AdminCatalog):
            raise MesEntityError("Runtime справочников МЕС не передал административный каталог.")
        return cls(catalog, executor or CustSqliteMesExecutor())

    def search(
        self,
        choice: Any,
        *,
        presentation_key: str | None = None,
        text: str = "",
        filters: Mapping[str, Any] | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> MesSearchPage:
        presentation = self._presentation(choice, presentation_key)
        page_size = max(1, min(int(limit), self.max_page_size))
        page_offset = max(0, int(offset))
        rows = self._select(
            choice,
            presentation,
            text=str(text or "").strip(),
            filters=filters or {},
            identity=None,
            limit=page_size + 1,
            offset=page_offset,
        )
        has_more = len(rows) > page_size
        return MesSearchPage(
            rows=tuple(rows[:page_size]),
            offset=page_offset,
            limit=page_size,
            has_more=has_more,
        )

    def resolve(self, choice: Any, reference: MesEntityRef) -> MesEntityResolution:
        reference = MesEntityRef.deserialize(reference)
        if reference.source_key != choice.source_key:
            raise MesEntityError(
                f"Ссылка {reference.source_key!r} не принадлежит справочнику {choice.source_key!r}."
            )
        presentation = self._presentation_or_none(choice, reference.presentation_key)
        if presentation is None:
            return MesEntityResolution(
                requested=reference,
                current=None,
                resolved=False,
                reason=(
                    f"Представление {reference.presentation_key!r} больше не зарегистрировано. "
                    "Сохранённый снимок оставлен без изменений."
                ),
            )
        identity = reference.identity_dict
        if set(identity) != {choice.identity_field_name}:
            return MesEntityResolution(
                requested=reference,
                current=None,
                resolved=False,
                reason=(
                    "Состав идентичности источника изменился. "
                    "Сохранённый снимок оставлен без изменений."
                ),
            )
        rows = self._select(
            choice,
            presentation,
            text="",
            filters={},
            identity=identity,
            limit=2,
            offset=0,
        )
        if not rows:
            return MesEntityResolution(
                requested=reference,
                current=None,
                resolved=False,
                reason="Строка источника не найдена. Сохранённая ссылка не удалена.",
            )
        if len(rows) > 1:
            raise MesEntityError(
                f"Идентичность {reference.identity_text} вернула несколько строк."
            )
        return MesEntityResolution(
            requested=reference,
            current=rows[0].reference,
            resolved=True,
        )

    def _select(
        self,
        choice: Any,
        presentation: Any,
        *,
        text: str,
        filters: Mapping[str, Any],
        identity: Mapping[str, Any] | None,
        limit: int,
        offset: int,
    ) -> list[MesEntityRow]:
        layout = self._layout(choice, presentation)
        source_alias = "mes_src"
        identity_expression = f"{source_alias}.{_quote(layout.identity_field_name)}"
        select_parts = [
            f"{identity_expression} AS {_quote(_IDENTITY_ALIAS)}",
            f"{layout.display_expression} AS {_quote(_DISPLAY_ALIAS)}",
        ]
        for index, (_, field_name, _) in enumerate(layout.filter_fields):
            select_parts.append(
                f"{source_alias}.{_quote(field_name)} AS "
                f"{_quote(_FILTER_ALIAS_PREFIX + str(index))}"
            )

        where_parts: list[str] = []
        parameters: list[Any] = []
        if identity is not None:
            expected = {layout.identity_field_name}
            if set(identity) != expected:
                raise MesEntityError(
                    f"Для {choice.source_key!r} ожидается идентичность {expected!r}."
                )
            where_parts.append(f"{identity_expression} = ?")
            parameters.append(identity[layout.identity_field_name])

        normalized_filters = self._normalize_filters(layout, filters)
        for field_name, value in normalized_filters:
            where_parts.append(f"{source_alias}.{_quote(field_name)} = ?")
            parameters.append(value)

        if text:
            search_expressions = [identity_expression, layout.display_expression]
            search_expressions.extend(
                f"{source_alias}.{_quote(field_name)}"
                for _, field_name, _ in layout.filter_fields
            )
            search_expressions = list(dict.fromkeys(search_expressions))
            where_parts.append(
                "(" + " OR ".join(
                    f"CAST({expression} AS TEXT) LIKE ? ESCAPE '\\'"
                    for expression in search_expressions
                ) + ")"
            )
            pattern = _like_pattern(text)
            parameters.extend(pattern for _ in search_expressions)

        sql = (
            "SELECT " + ", ".join(select_parts)
            + f" FROM {_quote(layout.source_table_name)} AS {source_alias}"
            + layout.join_sql
        )
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        sql += (
            f" ORDER BY {_quote(_DISPLAY_ALIAS)} IS NULL, "
            f"CAST({_quote(_DISPLAY_ALIAS)} AS TEXT) COLLATE NOCASE, "
            f"CAST({_quote(_IDENTITY_ALIAS)} AS TEXT) COLLATE NOCASE"
            " LIMIT ? OFFSET ?"
        )
        parameters.extend((int(limit), int(offset)))

        try:
            raw_rows = self.executor(layout.db_key, sql, tuple(parameters)) or ()
        except MesEntityError:
            raise
        except Exception as exc:
            raise MesEntityError(
                f"Не удалось прочитать строки справочника {choice.caption!r}: {exc}"
            ) from exc

        result: list[MesEntityRow] = []
        for raw_row in raw_rows:
            if not isinstance(raw_row, Mapping):
                raise MesEntityError("Исполнитель SQL вернул строку без имён колонок.")
            identity_value = raw_row.get(_IDENTITY_ALIAS)
            reference = MesEntityRef.create(
                source_key=choice.source_key,
                identity={layout.identity_field_name: identity_value},
                presentation_key=presentation.presentation_key,
                display_snapshot=raw_row.get(_DISPLAY_ALIAS),
            )
            filter_values = tuple(
                (
                    requisite_key,
                    raw_row.get(_FILTER_ALIAS_PREFIX + str(index)),
                )
                for index, (requisite_key, _, _) in enumerate(layout.filter_fields)
            )
            result.append(MesEntityRow(reference=reference, filter_values=filter_values))
        return result

    def _layout(self, choice: Any, presentation: Any) -> _QueryLayout:
        source_table = self.catalog.tables.get(choice.table_key)
        if source_table is None: #todo or not source_table.is_enabled or not source_table.schema_enabled:
            raise MesEntityError(
                f"Таблица {choice.table_key!r} отсутствует или выключена в административном каталоге."
            )
        self._require_field(choice.table_key, choice.identity_field_name)
        source_alias = "mes_src"
        join_sql = ""
        self._require_field(choice.table_key, presentation.source_field_name)
        if not presentation.relation_steps:
            if presentation.result_table_key != choice.table_key:
                raise MesEntityError("Прямое представление указывает на другую таблицу.")
            self._require_field(choice.table_key, presentation.result_field_name)
            display_expression = f"{source_alias}.{_quote(presentation.result_field_name)}"
        else:
            if len(presentation.relation_steps) != 1:
                raise MesEntityError("Поддерживается только один шаг скалярного представления.")
            relation_key = presentation.relation_steps[0]
            relation = self.catalog.relations.get(relation_key)
            if relation is None or not relation.is_enabled:
                raise MesEntityError(f"Связь {relation_key!r} отсутствует или выключена.")
            if relation.source_table_key != choice.table_key:
                raise MesEntityError(
                    f"Связь {relation_key!r} начинается не от {choice.table_key!r}."
                )
            target_table = self.catalog.tables.get(relation.target_table_key)
            if target_table is None: #todo or not target_table.is_enabled or not target_table.schema_enabled:
                raise MesEntityError(
                    f"Целевая таблица связи {relation.target_table_key!r} недоступна."
                )
            if target_table.table_key != presentation.result_table_key:
                raise MesEntityError("Связь и представление указывают на разные таблицы.")
            if source_table.db_key != target_table.db_key:
                raise MesEntityError(
                    "Скалярное представление между разными бизнес-базами пока не поддерживается."
                )
            if relation.cardinality not in {"many_to_one", "one_to_one"}:
                raise MesEntityError(
                    f"Связь {relation_key!r} не является скалярной."
                )
            if not relation.field_pairs:
                raise MesEntityError(f"У связи {relation_key!r} нет пар полей.")
            join_type = str(relation.join_type or "LEFT JOIN").upper()
            if join_type not in {"LEFT JOIN", "INNER JOIN"}:
                raise MesEntityError(
                    f"Связь {relation_key!r} использует неподдерживаемый тип JOIN."
                )
            target_alias = "mes_view"
            join_parts: list[str] = []
            for pair in relation.field_pairs:
                if pair.operator != "=":
                    raise MesEntityError(
                        f"Связь {relation_key!r} использует неподдерживаемый оператор."
                    )
                self._require_field(pair.left_table_key, pair.left_field_name)
                self._require_field(pair.right_table_key, pair.right_field_name)
                join_parts.append(
                    f"{source_alias}.{_quote(pair.left_field_name)} = "
                    f"{target_alias}.{_quote(pair.right_field_name)}"
                )
            self._require_field(target_table.table_key, presentation.result_field_name)
            join_sql = (
                f" {join_type} {_quote(target_table.table_name)} AS {target_alias} ON "
                + " AND ".join(join_parts)
            )
            display_expression = f"{target_alias}.{_quote(presentation.result_field_name)}"

        filter_fields: list[tuple[str, str, str]] = []
        for item in choice.filters:
            self._require_field(choice.table_key, item.field_name)
            filter_fields.append((item.requisite_key, item.field_name, item.caption))
        return _QueryLayout(
            db_key=source_table.db_key,
            source_table_name=source_table.table_name,
            identity_field_name=choice.identity_field_name,
            display_expression=display_expression,
            join_sql=join_sql,
            filter_fields=tuple(filter_fields),
        )

    def _normalize_filters(
        self,
        layout: _QueryLayout,
        filters: Mapping[str, Any],
    ) -> list[tuple[str, Any]]:
        if not filters:
            return []
        by_key: dict[str, str] = {}
        for requisite_key, field_name, _ in layout.filter_fields:
            by_key[requisite_key] = field_name
            by_key[field_name] = field_name
        result: list[tuple[str, Any]] = []
        used: set[str] = set()
        for key, value in filters.items():
            if value is None or value == "":
                continue
            field_name = by_key.get(str(key))
            if field_name is None:
                raise MesEntityError(f"Фильтр {key!r} не зарегистрирован для этого источника.")
            if field_name in used:
                raise MesEntityError(f"Фильтр по полю {field_name!r} указан несколько раз.")
            result.append((field_name, value))
            used.add(field_name)
        return result

    def _presentation(self, choice: Any, presentation_key: str | None) -> Any:
        if presentation_key:
            item = self._presentation_or_none(choice, presentation_key)
            if item is None:
                raise MesEntityError(
                    f"Представление {presentation_key!r} не зарегистрировано для {choice.caption!r}."
                )
            return item
        return choice.default_presentation

    @staticmethod
    def _presentation_or_none(choice: Any, presentation_key: str) -> Any | None:
        return next(
            (
                item
                for item in choice.presentations
                if item.presentation_key == presentation_key
            ),
            None,
        )

    def _require_field(self, table_key: str, field_name: str) -> None:
        if (table_key, field_name) not in self.catalog.fields:
            raise MesEntityError(
                f"Поле {table_key}.{field_name} отсутствует в административном каталоге."
            )


class CustSqliteMesExecutor:
    def __call__(
        self,
        db_key: str,
        sql: str,
        parameters: Sequence[Any],
    ) -> Sequence[Mapping[str, Any]]:
        try:
            from project_cust_38 import Cust_SQLite as CSQ
        except Exception as exc:
            raise MesEntityError(f"Не удалось загрузить клиент бизнес-баз: {exc}") from exc
        database = self._database(CSQ, db_key)
        kwargs: dict[str, Any] = {
            "rez_dict": True,
            "debug": False,
        }
        if parameters:
            kwargs["list_of_lists_c"] = [list(parameters)]
        rows = CSQ.custom_request_c(database, sql, **kwargs)
        if rows in (None, False):
            return ()
        if not isinstance(rows, list):
            raise MesEntityError("Клиент бизнес-базы вернул неожиданный формат ответа.")
        return rows

    @staticmethod
    def _database(csq_module: Any, db_key: str) -> Any:
        candidates = [db_key]
        if not str(db_key).lower().endswith(".db"):
            candidates.append(f"{db_key}.db")
        for candidate in candidates:
            database = csq_module.DB_NAMES[candidate]
            if database is not None:
                return database
        for database in csq_module.DB_NAMES:
            alias = str(getattr(database, "alias", ""))
            if alias.removesuffix(".db") == str(db_key).removesuffix(".db"):
                return database
        raise MesEntityError(
            f"Для db_key={db_key!r} не найден сервер в Cust_SQLite.DB_NAMES."
        )


class SqliteConnectionExecutor:
    def __init__(self, connection: sqlite3.Connection, db_key: str = "demo") -> None:
        self.connection = connection
        self.db_key = db_key

    def __call__(
        self,
        db_key: str,
        sql: str,
        parameters: Sequence[Any],
    ) -> Sequence[Mapping[str, Any]]:
        if db_key != self.db_key:
            raise MesEntityError(f"Демонстрационная база {db_key!r} не подключена.")
        cursor = self.connection.execute(sql, tuple(parameters))
        names = [item[0] for item in cursor.description or ()]
        return [dict(zip(names, row)) for row in cursor.fetchall()]


def select_mes_entity(
    parent: Any,
    service: MesEntityService,
    choice: Any,
    *,
    presentation_key: str | None = None,
    current: MesEntityRef | None = None,
) -> MesEntitySelection:
    try:
        from PyQt5 import QtCore, QtWidgets
    except Exception as exc:
        raise MesEntityError(f"Не удалось открыть окно выбора сущности МЕС: {exc}") from exc

    class _MesEntityDialog(QtWidgets.QDialog):
        def __init__(self) -> None:
            super().__init__(parent)
            self.selected_reference: MesEntityRef | None = current
            self.page_offset = 0
            self.page: MesSearchPage | None = None
            self.setWindowTitle(f"Выбор сущности: {choice.caption}")
            self.resize(920, 560)
            layout = QtWidgets.QVBoxLayout(self)

            current_text = "Не выбрано" if current is None else str(current)
            self.current_label = QtWidgets.QLabel(f"Текущее значение: {current_text}")
            self.current_label.setWordWrap(True)
            layout.addWidget(self.current_label)

            search_layout = QtWidgets.QHBoxLayout()
            self.search_edit = QtWidgets.QLineEdit()
            self.search_edit.setPlaceholderText(
                "Поиск по идентификатору, представлению и зарегистрированным фильтрам"
            )
            self.search_button = QtWidgets.QPushButton("Найти")
            search_layout.addWidget(self.search_edit, 1)
            search_layout.addWidget(self.search_button)
            layout.addLayout(search_layout)

            self.filter_edits: dict[str, Any] = {}
            if choice.filters:
                filter_group = QtWidgets.QGroupBox("Точные фильтры")
                filter_layout = QtWidgets.QFormLayout(filter_group)
                for item in choice.filters:
                    editor = QtWidgets.QLineEdit()
                    editor.setPlaceholderText(item.field_name)
                    filter_layout.addRow(item.caption, editor)
                    self.filter_edits[item.requisite_key] = editor
                layout.addWidget(filter_group)

            self.table = QtWidgets.QTableWidget()
            headers = ["Идентичность", "Представление"] + [
                item.caption for item in choice.filters
            ]
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.horizontalHeader().setSectionResizeMode(
                1, QtWidgets.QHeaderView.Stretch
            )
            layout.addWidget(self.table, 1)

            page_layout = QtWidgets.QHBoxLayout()
            self.previous_button = QtWidgets.QPushButton("Назад")
            self.next_button = QtWidgets.QPushButton("Далее")
            self.status_label = QtWidgets.QLabel()
            page_layout.addWidget(self.previous_button)
            page_layout.addWidget(self.next_button)
            page_layout.addWidget(self.status_label, 1)
            layout.addLayout(page_layout)

            button_layout = QtWidgets.QHBoxLayout()
            self.clear_button = QtWidgets.QPushButton("Очистить значение")
            self.cancel_button = QtWidgets.QPushButton("Отмена")
            self.select_button = QtWidgets.QPushButton("Выбрать")
            self.select_button.setDefault(True)
            button_layout.addWidget(self.clear_button)
            button_layout.addStretch(1)
            button_layout.addWidget(self.cancel_button)
            button_layout.addWidget(self.select_button)
            layout.addLayout(button_layout)

            self.search_button.clicked.connect(self._search)
            self.search_edit.returnPressed.connect(self._search)
            self.previous_button.clicked.connect(self._previous)
            self.next_button.clicked.connect(self._next)
            self.select_button.clicked.connect(self._accept_current)
            self.clear_button.clicked.connect(self._clear)
            self.cancel_button.clicked.connect(self.reject)
            self.table.doubleClicked.connect(self._accept_current)
            self.table.itemSelectionChanged.connect(self._update_buttons)
            QtCore.QTimer.singleShot(0, self._search)

        def _filters(self) -> dict[str, str]:
            return {
                key: editor.text().strip()
                for key, editor in self.filter_edits.items()
                if editor.text().strip()
            }

        def _search(self) -> None:
            self.page_offset = 0
            self._load()

        def _previous(self) -> None:
            self.page_offset = max(0, self.page_offset - DEFAULT_PAGE_SIZE)
            self._load()

        def _next(self) -> None:
            if self.page is None or not self.page.has_more:
                return
            self.page_offset += self.page.limit
            self._load()

        def _load(self) -> None:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                self.page = service.search(
                    choice,
                    presentation_key=presentation_key,
                    text=self.search_edit.text(),
                    filters=self._filters(),
                    limit=DEFAULT_PAGE_SIZE,
                    offset=self.page_offset,
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Ошибка выбора сущности МЕС", str(exc))
                return
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()
            self._fill_table()

        def _fill_table(self) -> None:
            rows = () if self.page is None else self.page.rows
            self.table.setSortingEnabled(False)
            self.table.setRowCount(len(rows))
            for row_index, item in enumerate(rows):
                identity_item = QtWidgets.QTableWidgetItem(item.reference.identity_text)
                identity_item.setData(QtCore.Qt.UserRole, item.reference)
                self.table.setItem(row_index, 0, identity_item)
                self.table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(item.display))
                filter_values = item.filters
                for column_index, filter_choice in enumerate(choice.filters, 2):
                    value = filter_values.get(filter_choice.requisite_key)
                    self.table.setItem(
                        row_index,
                        column_index,
                        QtWidgets.QTableWidgetItem("" if value is None else str(value)),
                    )
            self.table.setSortingEnabled(True)
            if rows:
                self.table.selectRow(0)
            shown_from = self.page_offset + 1 if rows else 0
            shown_to = self.page_offset + len(rows)
            self.status_label.setText(f"Показаны строки {shown_from}–{shown_to}")
            self.previous_button.setEnabled(self.page_offset > 0)
            self.next_button.setEnabled(bool(self.page and self.page.has_more))
            self._update_buttons()

        def _current_reference(self) -> MesEntityRef | None:
            row = self.table.currentRow()
            if row < 0:
                return None
            item = self.table.item(row, 0)
            if item is None:
                return None
            value = item.data(QtCore.Qt.UserRole)
            return value if isinstance(value, MesEntityRef) else None

        def _update_buttons(self) -> None:
            self.select_button.setEnabled(self._current_reference() is not None)

        def _accept_current(self, *args: Any) -> None:
            reference = self._current_reference()
            if reference is None:
                return
            self.selected_reference = reference
            self.accept()

        def _clear(self) -> None:
            self.selected_reference = None
            self.accept()

    dialog = _MesEntityDialog()
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return MesEntitySelection(accepted=False, reference=current)
    return MesEntitySelection(accepted=True, reference=dialog.selected_reference)


def _quote(identifier: str) -> str:
    identifier = str(identifier or "")
    if not identifier:
        raise MesEntityError("В административном каталоге найден пустой SQL-идентификатор.")
    if "\x00" in identifier:
        raise MesEntityError("SQL-идентификатор содержит нулевой байт.")
    return '"' + identifier.replace('"', '""') + '"'


def _like_pattern(text: str) -> str:
    escaped = str(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _demo() -> None:
    try:
        from PyQt5 import QtWidgets
        from .planner_mes_types import MesFilterChoice, MesPresentationChoice, MesTypeChoice
    except ImportError:
        from PyQt5 import QtWidgets
        from planner_mes_types import MesFilterChoice, MesPresentationChoice, MesTypeChoice

    connection = sqlite3.connect(":memory:")
    connection.execute(
        'CREATE TABLE "demo_items" ("id" INTEGER PRIMARY KEY, "name" TEXT, "group_name" TEXT)'
    )
    connection.executemany(
        'INSERT INTO "demo_items" ("id", "name", "group_name") VALUES (?, ?, ?)',
        (
            (1, "Маршрутная карта 6888", "МК"),
            (2, "Номенклатура 101", "ERP"),
            (3, "Подразделение сборки", "Ресурс"),
        ),
    )
    table = registry.AdminTable(
        table_key="demo.items",
        db_key="demo",
        table_name="demo_items",
    )
    fields = {
        ("demo.items", name): registry.AdminField(
            table_key="demo.items",
            field_name=name,
            is_pk=name == "id",
        )
        for name in ("id", "name", "group_name")
    }
    catalog = registry.AdminCatalog(
        tables={table.table_key: table},
        fields=fields,
        relations={},
    )
    presentation = MesPresentationChoice(
        presentation_key="demo.items.view.default",
        caption="Наименование",
        source_field_name="id",
        result_table_key="demo.items",
        result_field_name="name",
        is_default=True,
    )
    choice = MesTypeChoice(
        source_key="demo.items",
        table_key="demo.items",
        caption="Демонстрационный справочник",
        identity_field_name="id",
        presentations=(presentation,),
        filters=(
            MesFilterChoice(
                requisite_key="demo.items.req.group",
                field_name="group_name",
                caption="Группа",
            ),
        ),
    )
    service = MesEntityService(catalog, SqliteConnectionExecutor(connection))
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    result = select_mes_entity(None, service, choice)
    if result.accepted:
        print(None if result.reference is None else result.reference.serialize())
    application.quit()
    connection.close()


if __name__ == "__main__":
    _demo()


__all__ = [
    "MES_ENTITY_REF_VERSION",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "MesEntityError",
    "MesEntityRef",
    "MesEntityRow",
    "MesSearchPage",
    "MesEntityResolution",
    "MesEntitySelection",
    "MesEntityService",
    "CustSqliteMesExecutor",
    "SqliteConnectionExecutor",
    "select_mes_entity",
]
