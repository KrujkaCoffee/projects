from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.theme import theme_color

TABLE_KEY_ROLE = Qt.UserRole
TABLE_ROW_ROLE = Qt.UserRole + 1


class PhysicalTablesNavigator(QWidget):
    """Компактное представление реестра только для чтения."""

    tableSelected = pyqtSignal(str)
    editRequested = pyqtSignal(str)
    refreshRequested = pyqtSignal()
    checkRequested = pyqtSignal()
    fieldsRequested = pyqtSignal()
    relationsRequested = pyqtSignal()
    mapRequested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("physical_tables_navigator")
        self.setMinimumWidth(270)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._rows: list[dict[str, Any]] = []
        self._current_key = ""
        self._rebuilding = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel("Физические таблицы", self)
        title.setObjectName("physical_tables_title")
        layout.addWidget(title)

        filter_panel = QFrame(self)
        filter_panel.setObjectName("tables_filter_panel")
        filter_layout = QHBoxLayout(filter_panel)
        filter_layout.setContentsMargins(6, 4, 6, 4)
        filter_layout.setSpacing(4)
        self.filter_edit = QLineEdit(filter_panel)
        self.filter_edit.setObjectName("table_name_filter")
        self.filter_edit.setPlaceholderText("Фильтр по имени таблицы…")
        self.count_label = QLabel("0 / 0", filter_panel)
        self.count_label.setObjectName("tables_filter_count_label")
        filter_layout.addWidget(self.filter_edit, 1)
        filter_layout.addWidget(self.count_label)
        layout.addWidget(filter_panel)

        self.db_filter = QComboBox(self)
        self.db_filter.setObjectName("physical_tables_db_filter")
        self.db_filter.setToolTip("Ограничить список выбранной базой/источником")
        layout.addWidget(self.db_filter)

        self.list = QTreeWidget(self)
        self.list.setObjectName("physical_tables_list")
        self.list.setColumnCount(2)
        self.list.setHeaderHidden(True)
        self.list.setRootIsDecorated(False)
        self.list.setItemsExpandable(False)
        self.list.setIndentation(0)
        self.list.setAlternatingRowColors(True)
        self.list.setSelectionMode(QTreeWidget.SingleSelection)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.list.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout.addWidget(self.list, 1)

        self.edit_button = QPushButton("Редактировать реестр таблиц…", self)
        self.edit_button.setObjectName("edit_physical_tables_btn")
        self.edit_button.setToolTip("Открыть полный редактор admin_physical_tables")
        layout.addWidget(self.edit_button)

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Обновить", self)
        self.refresh_button.setObjectName("refresh_physical_tables_btn")
        self.check_button = QPushButton("Проверить", self)
        self.check_button.setObjectName("check_physical_tables_btn")
        actions.addWidget(self.refresh_button, 1)
        actions.addWidget(self.check_button)
        layout.addLayout(actions)

        self.filter_edit.textChanged.connect(self._rebuild)
        self.db_filter.currentIndexChanged.connect(self._rebuild)
        self.list.currentItemChanged.connect(self._on_current_item_changed)
        self.list.itemDoubleClicked.connect(lambda *_: self.fieldsRequested.emit())
        self.list.customContextMenuRequested.connect(self._open_context_menu)
        self.edit_button.clicked.connect(
            lambda: self.editRequested.emit(self._current_key)
        )
        self.refresh_button.clicked.connect(self.refreshRequested)
        self.check_button.clicked.connect(self.checkRequested)

    @property
    def current_key(self) -> str:
        return self._current_key

    @property
    def rows(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(row) for row in self._rows)

    def set_rows(self, rows: Iterable[Mapping[str, Any]]) -> None:
        selected = self._current_key
        self._rows = [dict(row) for row in rows]
        db_keys = sorted(
            {
                str(row.get("db_key") or "")
                for row in self._rows
                if str(row.get("db_key") or "")
            },
            key=str.casefold,
        )
        old = self.db_filter.blockSignals(True)
        current_db = str(self.db_filter.currentData() or "")
        try:
            self.db_filter.clear()
            self.db_filter.addItem("Все базы", "")
            for db_key in db_keys:
                self.db_filter.addItem(db_key, db_key)
            index = self.db_filter.findData(current_db)
            self.db_filter.setCurrentIndex(max(index, 0))
        finally:
            self.db_filter.blockSignals(old)
        self._current_key = (
            selected if any(self._key(row) == selected for row in self._rows) else ""
        )
        self._rebuild()

    @staticmethod
    def _key(row: Mapping[str, Any]) -> str:
        return str(row.get("table_key") or "")

    def _filtered_rows(self) -> list[dict[str, Any]]:
        needle = self.filter_edit.text().strip().casefold()
        db_key = str(self.db_filter.currentData() or "")
        candidates = [
            row
            for row in self._rows
            if (not db_key or str(row.get("db_key") or "") == db_key)
            and (not needle or needle in str(row.get("table_name") or "").casefold())
        ]

        def sort_key(row: Mapping[str, Any]):
            name = str(row.get("table_name") or "")
            folded = name.casefold()
            if needle and folded == needle:
                rank = 0
            elif needle and folded.startswith(needle):
                rank = 1
            else:
                rank = 2
            return (
                rank,
                folded,
                str(row.get("db_key") or "").casefold(),
                self._key(row).casefold(),
            )

        return sorted(candidates, key=sort_key)

    @staticmethod
    def _tooltip(row: Mapping[str, Any]) -> str:
        fields = (
            "table_key",
            "db_key",
            "table_name",
            "schema_enabled",
            "cache_enabled",
            "validity_mark",
            "updated_at",
        )
        return "\n".join(
            f"{field}: {row.get(field)}" for field in fields if field in row
        )

    def _rebuild(self) -> None:
        if not hasattr(self, "list"):
            return
        visible = self._filtered_rows()
        name_counts = Counter(
            str(row.get("table_name") or "").casefold() for row in self._rows
        )
        self._rebuilding = True
        old = self.list.blockSignals(True)
        try:
            self.list.clear()
            selected_item = None
            for row in visible:
                name = str(row.get("table_name") or row.get("table_key") or "")
                duplicate = name_counts[name.casefold()] > 1
                qualifier = f"[{row.get('db_key') or '—'}]" if duplicate else ""
                item = QTreeWidgetItem([name, qualifier])
                item.setData(0, TABLE_KEY_ROLE, self._key(row))
                item.setData(0, TABLE_ROW_ROLE, dict(row))
                tooltip = self._tooltip(row)
                item.setToolTip(0, tooltip)
                item.setToolTip(1, tooltip)
                if not int(row.get("is_enabled") or 0):
                    color = theme_color("disabled_text")
                    item.setForeground(0, color)
                    item.setForeground(1, color)
                    font = item.font(0)
                    font.setItalic(True)
                    item.setFont(0, font)
                self.list.addTopLevelItem(item)
                if self._key(row) == self._current_key:
                    selected_item = item
            if selected_item is not None:
                self.list.setCurrentItem(selected_item)
            else:
                self.list.clearSelection()
                self.list.setCurrentItem(None)
        finally:
            self.list.blockSignals(old)
            self._rebuilding = False
        self.count_label.setText(f"{len(visible)} / {len(self._rows)}")

    def apply_application_theme(self, _theme=None) -> None:
        self._rebuild()

    def select_key(self, table_key: str, *, emit: bool = False) -> bool:
        if not table_key or not any(self._key(row) == table_key for row in self._rows):
            return False
        changed = table_key != self._current_key
        self._current_key = table_key
        self._rebuild()
        if emit and changed:
            self.tableSelected.emit(table_key)
        return True

    def select_first(self, *, enabled_only: bool = False, emit: bool = False) -> str:
        rows = self._filtered_rows()
        if enabled_only:
            rows = [row for row in rows if int(row.get("is_enabled") or 0)]
        if not rows:
            return ""
        key = self._key(rows[0])
        self.select_key(key, emit=emit)
        return key

    def nearest_enabled_key(self, previous_key: str) -> str:
        ordered = sorted(
            self._rows,
            key=lambda row: (
                str(row.get("table_name") or "").casefold(),
                str(row.get("db_key") or "").casefold(),
            ),
        )
        enabled = [row for row in ordered if int(row.get("is_enabled") or 0)]
        if not enabled:
            return self._key(ordered[0]) if ordered else ""
        old_index = next(
            (
                index
                for index, row in enumerate(ordered)
                if self._key(row) == previous_key
            ),
            0,
        )
        return self._key(
            min(enabled, key=lambda row: abs(ordered.index(row) - old_index))
        )

    def _on_current_item_changed(self, current, _previous) -> None:
        if self._rebuilding or current is None:
            return
        table_key = str(current.data(0, TABLE_KEY_ROLE) or "")
        if table_key and table_key != self._current_key:
            self._current_key = table_key
            self.tableSelected.emit(table_key)

    def _selected_row(self) -> dict[str, Any]:
        item = self.list.currentItem()
        data = item.data(0, TABLE_ROW_ROLE) if item is not None else None
        return dict(data) if isinstance(data, Mapping) else {}

    def _open_context_menu(self, position) -> None:
        item = self.list.itemAt(position)
        if item is None:
            return
        self.list.setCurrentItem(item)
        row = self._selected_row()
        menu = QMenu(self)
        open_fields = menu.addAction("Открыть поля")
        open_relations = menu.addAction("Открыть связи")
        open_map = menu.addAction("Открыть на карте")
        menu.addSeparator()
        edit = menu.addAction("Редактировать запись…")
        menu.addSeparator()
        copy_name = menu.addAction("Скопировать table_name")
        copy_key = menu.addAction("Скопировать table_key")
        menu.addSeparator()
        refresh = menu.addAction("Обновить список")
        chosen = menu.exec_(self.list.viewport().mapToGlobal(position))
        if chosen is open_fields:
            self.fieldsRequested.emit()
        elif chosen is open_relations:
            self.relationsRequested.emit()
        elif chosen is open_map:
            self.mapRequested.emit()
        elif chosen is edit:
            self.editRequested.emit(self._current_key)
        elif chosen is copy_name:
            QApplication.clipboard().setText(str(row.get("table_name") or ""))
        elif chosen is copy_key:
            QApplication.clipboard().setText(str(row.get("table_key") or ""))
        elif chosen is refresh:
            self.refreshRequested.emit()
