from __future__ import annotations

from typing import Any

from PyQt5.QtCore import QByteArray, QSettings, QSignalBlocker, Qt
from PyQt5.QtGui import QBrush, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QShortcut,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.theme import theme_color

from .columns import (
    BOOL_COLUMNS,
    EDITABLE_EXISTING_COLUMNS,
    EDITABLE_NEW_COLUMNS,
    IDENTITY_COLUMNS,
    SYSTEM_COLUMNS,
    TABLE_COLUMNS,
    TABLE_LABELS,
)
from .delegate import ROW_ID_ROLE, MutatedCellDelegate
from .edit_model import PhysicalTablesEditModel, build_unicode_table_key
from .filter_bar import ColumnFilterControl
from .filters import ColumnFilter, FilterSet, FilterValueError


class PhysicalTablesEditorDialog(QDialog):
    SETTINGS_ORGANIZATION = "powerz"
    SETTINGS_APPLICATION = "admin_panel"
    GEOMETRY_KEY = "physical_tables_editor/geometry"
    STANDARD_MIN_WIDTH = 1000
    STANDARD_MIN_HEIGHT = 650
    COMPACT_MIN_WIDTH = 520
    COMPACT_MIN_HEIGHT = 420

    def __init__(
        self,
        parent,
        repository,
        *,
        selected_table_key: str = "",
        start_new: bool = False,
        settings: QSettings | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.model = PhysicalTablesEditModel()
        self.saved = False
        self._loading = False
        self._save_in_progress = False
        self._issues: dict[tuple[str, str], str] = {}
        self._active_filters: dict[str, ColumnFilter] = {}
        self._filter_controls: dict[str, ColumnFilterControl] = {}
        self._settings = settings or QSettings(
            self.SETTINGS_ORGANIZATION,
            self.SETTINGS_APPLICATION,
        )
        self.setWindowTitle("Редактор реестра физических таблиц")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowMinMaxButtonsHint, True)
        self._build_ui()
        self._restore_geometry()
        self._load_rows(selected_table_key)
        if start_new:
            self.add_row()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(7)

        toolbar = QHBoxLayout()
        self.add_button = QPushButton("Добавить таблицу", self)
        self.disable_button = QPushButton("Отключить", self)
        self.delete_button = QPushButton("Пометить на удаление", self)
        self.refresh_button = QPushButton("Обновить", self)
        self.apply_filters_button = QPushButton("Применить фильтры", self)
        self.clear_filters_button = QPushButton("Сбросить все фильтры", self)
        self.filter_count_label = QLabel("Показано: 0 / 0", self)
        self.filter_count_label.setObjectName("physical_tables_filter_count")
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.disable_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.filter_count_label)
        toolbar.addWidget(self.apply_filters_button)
        toolbar.addWidget(self.clear_filters_button)
        root.addLayout(toolbar)

        hint = QLabel(
            "Identity существующих строк и служебные поля доступны только для чтения. "
            "Добавление, отключение и удаление применятся лишь после общего сохранения.",
            self,
        )
        hint.setObjectName("physical_tables_editor_hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.table = QTableWidget(self)
        self.table.setObjectName("physical_tables_editor_grid")
        self.table.setColumnCount(len(TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels(
            [TABLE_LABELS[column] for column in TABLE_COLUMNS]
        )
        for index, column in enumerate(TABLE_COLUMNS):
            header_item = self.table.horizontalHeaderItem(index)
            if header_item is not None:
                header_item.setToolTip(column)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(True)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for column in ("table_key", "db_key", "table_name"):
            self.table.horizontalHeader().setSectionResizeMode(
                TABLE_COLUMNS.index(column),
                QHeaderView.ResizeToContents,
            )
        self.table.horizontalHeader().setSectionResizeMode(
            TABLE_COLUMNS.index("notes"),
            QHeaderView.Stretch,
        )
        self.table.setItemDelegate(
            MutatedCellDelegate(TABLE_COLUMNS, self._cell_state, self.table)
        )
        self._build_filter_grid(root)
        root.addWidget(self.table, 1)

        self.status_label = QLabel("Нет несохранённых изменений", self)
        self.status_label.setObjectName("physical_tables_edit_status")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.revert_button = QPushButton("Отменить изменения", self)
        self.save_button = QPushButton("Сохранить изменения", self)
        self.close_button = QPushButton("Закрыть", self)
        bottom.addWidget(self.revert_button)
        bottom.addWidget(self.save_button)
        bottom.addWidget(self.close_button)
        root.addLayout(bottom)

        self.add_button.clicked.connect(self.add_row)
        self.disable_button.clicked.connect(self.disable_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.refresh_button.clicked.connect(self.refresh_rows)
        self.apply_filters_button.clicked.connect(self.apply_column_filters)
        self.clear_filters_button.clicked.connect(self.clear_column_filters)
        self.revert_button.clicked.connect(self.revert_changes)
        self.save_button.clicked.connect(self.save_changes)
        self.close_button.clicked.connect(self.close)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.currentCellChanged.connect(lambda *_: self._refresh_actions())
        QShortcut(QKeySequence.Save, self, activated=self.save_changes)

    def _build_filter_grid(self, root: QVBoxLayout) -> None:
        self.filter_table = QTableWidget(1, len(TABLE_COLUMNS), self)
        self.filter_table.setObjectName("physical_tables_filter_grid")
        self.filter_table.setFocusPolicy(Qt.NoFocus)
        self.filter_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.filter_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.filter_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filter_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filter_table.horizontalHeader().hide()
        self.filter_table.verticalHeader().setVisible(True)
        self.filter_table.verticalHeader().setFixedWidth(
            self.table.verticalHeader().width()
        )
        self.filter_table.setVerticalHeaderItem(0, QTableWidgetItem(""))
        self.filter_table.setRowHeight(0, 38)
        self.filter_table.setFixedHeight(42)
        self.filter_table.setToolTip(
            "Фильтры применяются явно и объединяются по AND. Новая несохранённая строка всегда остаётся видимой."
        )
        for index, column in enumerate(TABLE_COLUMNS):
            control = ColumnFilterControl(column, self.filter_table)
            control.setToolTip(f"Фильтр колонки: {TABLE_LABELS[column]}")
            control.resetRequested.connect(self.reset_column_filter)
            self.filter_table.setCellWidget(0, index, control)
            self._filter_controls[column] = control
        self.table.horizontalHeader().sectionResized.connect(
            lambda index, _old, width: self.filter_table.setColumnWidth(index, width)
        )
        self.table.horizontalHeader().geometriesChanged.connect(
            self._sync_filter_geometry
        )
        self.table.verticalHeader().geometriesChanged.connect(
            self._sync_filter_geometry
        )
        self.table.horizontalScrollBar().valueChanged.connect(
            self.filter_table.horizontalScrollBar().setValue
        )
        self.filter_table.horizontalScrollBar().valueChanged.connect(
            self.table.horizontalScrollBar().setValue
        )
        root.addWidget(self.filter_table)
        self._sync_filter_geometry()

    def _sync_filter_geometry(self) -> None:
        self.filter_table.verticalHeader().setFixedWidth(
            self.table.verticalHeader().width()
        )
        for index in range(len(TABLE_COLUMNS)):
            self.filter_table.setColumnWidth(index, self.table.columnWidth(index))

    def _restore_geometry(self) -> None:
        screen = QApplication.primaryScreen()
        available = (
            screen.availableGeometry() if screen is not None else self.geometry()
        )
        minimum_width = max(
            self.COMPACT_MIN_WIDTH,
            min(self.STANDARD_MIN_WIDTH, available.width() - 80),
        )
        minimum_height = max(
            self.COMPACT_MIN_HEIGHT,
            min(self.STANDARD_MIN_HEIGHT, available.height() - 80),
        )
        self.setMinimumSize(minimum_width, minimum_height)

        raw = self._settings.value(self.GEOMETRY_KEY)
        restored = False
        if isinstance(raw, QByteArray):
            restored = self.restoreGeometry(raw)
        if not restored:
            width = min(1280, max(minimum_width, int(available.width() * 0.88)))
            height = min(780, max(minimum_height, int(available.height() * 0.82)))
            self.resize(width, height)
            self.move(
                available.center().x() - width // 2,
                available.center().y() - height // 2,
            )
        self._constrain_to_screens()

    def _constrain_to_screens(self) -> None:
        screens = QApplication.screens()
        frame = self.frameGeometry()
        if any(screen.availableGeometry().intersects(frame) for screen in screens):
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.resize(
            min(self.width(), available.width() - 40),
            min(self.height(), available.height() - 40),
        )
        self.move(available.left() + 20, available.top() + 20)

    def _load_rows(self, selected_table_key: str = "") -> None:
        rows = self.repository.load()
        self.model.capture(rows)
        self._populate_table(selected_table_key)

    def _populate_table(self, selected_table_key: str = "") -> None:
        selected_row_id = self._current_row_id()
        desired = selected_table_key or selected_row_id
        self._loading = True
        sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        try:
            with QSignalBlocker(self.table):
                self.table.setRowCount(len(self.model.row_ids))
                for visual_row, row_id in enumerate(self.model.row_ids):
                    self._write_visual_row(visual_row, row_id)
        finally:
            self.table.setSortingEnabled(sorting)
            self._loading = False
        self._refresh_state()
        if desired:
            self._select_row_id(desired)
        if self.table.currentRow() < 0 and self.table.rowCount():
            self.table.setCurrentCell(0, 0)
        self._apply_active_filters()

    def _write_visual_row(self, visual_row: int, row_id: str) -> None:
        row = self.model.get_row(row_id)
        new_row = self.model.is_new(row_id)
        pending_delete = self.model.is_pending_delete(row_id)
        editable_columns = (
            EDITABLE_NEW_COLUMNS if new_row else EDITABLE_EXISTING_COLUMNS
        )
        for column_index, column in enumerate(TABLE_COLUMNS):
            value = row.get(column)
            checkable = column in BOOL_COLUMNS
            item = QTableWidgetItem("" if checkable or value is None else str(value))
            flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
            if checkable:
                if column in editable_columns and not pending_delete:
                    flags |= Qt.ItemIsUserCheckable
                item.setCheckState(Qt.Checked if int(value or 0) else Qt.Unchecked)
            elif column in editable_columns and not pending_delete:
                flags |= Qt.ItemIsEditable
            item.setFlags(flags)
            item.setData(ROW_ID_ROLE, row_id)
            if (column in IDENTITY_COLUMNS and not new_row) or column in SYSTEM_COLUMNS:
                item.setForeground(theme_color("disabled_text"))
            if pending_delete:
                font = QFont(item.font())
                font.setStrikeOut(True)
                item.setFont(font)
                item.setForeground(theme_color("canvas_disabled"))
            self.table.setItem(visual_row, column_index, item)
        marker = "+" if new_row else "-" if pending_delete else ""
        header = QTableWidgetItem(marker)
        if new_row:
            header.setForeground(theme_color("saved"))
        elif pending_delete:
            header.setForeground(theme_color("canvas_disabled"))
        self.table.setVerticalHeaderItem(visual_row, header)

    def apply_application_theme(self, _theme=None) -> None:
        # Foreground roles are item data, not QSS. Repaint them under a signal
        # blocker so a palette switch can never become a metadata edit.
        with QSignalBlocker(self.table):
            for visual_row in range(self.table.rowCount()):
                first = self.table.item(visual_row, 0)
                row_id = str(first.data(ROW_ID_ROLE) or "") if first is not None else ""
                if not row_id:
                    continue
                pending = self.model.is_pending_delete(row_id)
                new_row = self.model.is_new(row_id)
                for column_index, column in enumerate(TABLE_COLUMNS):
                    item = self.table.item(visual_row, column_index)
                    if item is None:
                        continue
                    if pending:
                        item.setForeground(theme_color("canvas_disabled"))
                    elif (column in IDENTITY_COLUMNS and not new_row) or column in SYSTEM_COLUMNS:
                        item.setForeground(theme_color("disabled_text"))
                    else:
                        item.setForeground(QBrush())
                header = self.table.verticalHeaderItem(visual_row)
                if header is not None:
                    if new_row:
                        header.setForeground(theme_color("saved"))
                    elif pending:
                        header.setForeground(theme_color("canvas_disabled"))
                    else:
                        header.setForeground(QBrush())
        self.table.viewport().update()

    def _current_row_id(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        item = self.table.item(row, 0)
        return str(item.data(ROW_ID_ROLE) or "") if item is not None else ""

    def _find_visual_row(self, row_id: str) -> int:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and str(item.data(ROW_ID_ROLE) or "") == row_id:
                return row
        return -1

    def _select_row_id(self, row_id_or_key: str) -> bool:
        row_id = row_id_or_key
        if row_id not in self.model.row_ids:
            row_id = next(
                (
                    candidate
                    for candidate in self.model.row_ids
                    if str(self.model.get_row(candidate).get("table_key") or "")
                    == row_id_or_key
                ),
                "",
            )
        visual_row = self._find_visual_row(row_id)
        if visual_row < 0:
            return False
        self.table.setCurrentCell(visual_row, 0)
        self.table.scrollToItem(self.table.item(visual_row, 0))
        return True

    def _finish_editor(self) -> None:
        focus = QApplication.focusWidget()
        if focus is not None and focus is not self.table:
            self.table.setFocus(Qt.OtherFocusReason)
        QApplication.processEvents()

    def _read_item_value(self, item: QTableWidgetItem, column: str) -> Any:
        if column in BOOL_COLUMNS:
            return 1 if item.checkState() == Qt.Checked else 0
        return item.text()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or self._save_in_progress:
            return
        row_id = str(item.data(ROW_ID_ROLE) or "")
        if not row_id or item.column() >= len(TABLE_COLUMNS):
            return
        column = TABLE_COLUMNS[item.column()]
        before = self.model.get_row(row_id)
        old_suggestion = build_unicode_table_key(
            before.get("db_key"), before.get("table_name")
        )
        try:
            self.model.set_value(row_id, column, self._read_item_value(item, column))
            if self.model.is_new(row_id) and column in {"db_key", "table_name"}:
                old_key = str(before.get("table_key") or "")
                if not old_key or old_key == old_suggestion:
                    current = self.model.get_row(row_id)
                    suggestion = build_unicode_table_key(
                        current.get("db_key"),
                        current.get("table_name"),
                    )
                    self.model.set_value(row_id, "table_key", suggestion)
                    key_item = self.table.item(
                        self._find_visual_row(row_id),
                        TABLE_COLUMNS.index("table_key"),
                    )
                    if key_item is not None and key_item.text() != suggestion:
                        with QSignalBlocker(self.table):
                            key_item.setText(suggestion)
        except (KeyError, ValueError) as exc:
            QMessageBox.warning(self, "Поле доступно только для чтения", str(exc))
            self._populate_table(row_id)
            return
        self._refresh_state()

    def _cell_state(self, row_id: str, column: str) -> str:
        if (row_id, column) in self._issues:
            return "invalid"
        if self.model.is_pending_delete(row_id):
            return "pending_delete"
        if (row_id, column) in self.model.changed_cells:
            return "new" if self.model.is_new(row_id) else "dirty"
        return ""

    def _refresh_state(self) -> None:
        issues = self.model.validation_issues
        self._issues = {(issue.row_id, issue.column): issue.message for issue in issues}
        changed_cells = self.model.changed_cells
        changed_rows = self.model.changed_row_ids
        dirty = self.model.is_dirty
        error_count = len(issues)

        if dirty:
            parts = [
                f"Изменено: {len(changed_cells)} ячеек в {len(changed_rows)} таблицах"
            ]
            if self.model.new_count:
                parts.append(f"Новых: {self.model.new_count}")
            if self.model.pending_delete_count:
                parts.append(f"Удаляемых: {self.model.pending_delete_count}")
            if error_count:
                parts.append(f"Ошибок: {error_count}")
            self.status_label.setText(" · ".join(parts))
        else:
            self.status_label.setText("Нет несохранённых изменений")

        can_save = dirty and not error_count and not self._save_in_progress
        self.save_button.setEnabled(can_save)
        self.revert_button.setEnabled(dirty and not self._save_in_progress)
        if not dirty:
            self.save_button.setToolTip("Нет несохранённых изменений")
            self.revert_button.setToolTip("Нет изменений для отмены")
        elif error_count:
            self.save_button.setToolTip(f"Исправьте ошибки: {error_count}")
            self.revert_button.setToolTip("Вернуть исходный снимок")
        elif self._save_in_progress:
            self.save_button.setToolTip("Сохранение выполняется")
        else:
            self.save_button.setToolTip(
                "Сохранить семантическую разницу одной транзакцией (Ctrl+S)"
            )
            self.revert_button.setToolTip("Вернуть исходный снимок")

        with QSignalBlocker(self.table):
            for row in range(self.table.rowCount()):
                for column_index, column in enumerate(TABLE_COLUMNS):
                    item = self.table.item(row, column_index)
                    if item is None:
                        continue
                    row_id = str(item.data(ROW_ID_ROLE) or "")
                    item.setToolTip(self._issues.get((row_id, column), ""))
        self.table.viewport().update()
        self._refresh_actions()

    def _refresh_actions(self) -> None:
        row_id = self._current_row_id()
        selected = bool(row_id)
        pending = bool(selected and self.model.is_pending_delete(row_id))
        new_row = bool(selected and self.model.is_new(row_id))
        enabled = selected and not self._save_in_progress
        self.add_button.setEnabled(not self._save_in_progress)
        self.refresh_button.setEnabled(not self._save_in_progress)
        self.apply_filters_button.setEnabled(not self._save_in_progress)
        self.clear_filters_button.setEnabled(
            not self._save_in_progress
            and bool(
                self._active_filters
                or any(not control.is_empty() for control in self._filter_controls.values())
            )
        )
        self.disable_button.setEnabled(enabled and not pending)
        self.delete_button.setEnabled(enabled)
        if pending:
            self.delete_button.setText("Вернуть строку")
        elif new_row:
            self.delete_button.setText("Убрать новую строку")
        else:
            self.delete_button.setText("Пометить на удаление")

    def apply_column_filters(self) -> None:
        if self._save_in_progress:
            return
        self._finish_editor()
        parsed: dict[str, ColumnFilter] = {}
        first_error: FilterValueError | None = None
        for column, control in self._filter_controls.items():
            try:
                current = control.current_filter()
            except FilterValueError as exc:
                control.mark_invalid(True, str(exc))
                if first_error is None:
                    first_error = exc
                continue
            control.mark_invalid(False)
            if current is not None:
                parsed[column] = current
        if first_error is not None:
            QMessageBox.warning(
                self,
                "Некорректный фильтр",
                f"{TABLE_LABELS.get(first_error.column, first_error.column)}: {first_error}",
            )
            control = self._filter_controls[first_error.column]
            if control.value_edit is not None:
                control.value_edit.setFocus(Qt.OtherFocusReason)
                control.value_edit.selectAll()
            return
        self._active_filters = parsed
        self._apply_active_filters()
        self._refresh_actions()

    def reset_column_filter(self, column: str) -> None:
        self._active_filters.pop(column, None)
        self._apply_active_filters()
        self._refresh_actions()

    def clear_column_filters(self) -> None:
        for control in self._filter_controls.values():
            control.reset(emit_signal=False)
        self._active_filters.clear()
        self._apply_active_filters()
        self._refresh_actions()

    def _apply_active_filters(self) -> None:
        filters = FilterSet(tuple(self._active_filters.values()))
        visible = 0
        total = self.table.rowCount()
        current_row = self.table.currentRow()
        for visual_row in range(total):
            item = self.table.item(visual_row, 0)
            row_id = str(item.data(ROW_ID_ROLE) or "") if item is not None else ""
            show = bool(row_id) and (
                self.model.is_new(row_id) or filters.matches(self.model.get_row(row_id))
            )
            self.table.setRowHidden(visual_row, not show)
            if show:
                visible += 1
        self.filter_count_label.setText(f"Показано: {visible} / {total}")
        if current_row >= 0 and self.table.isRowHidden(current_row):
            for visual_row in range(total):
                if not self.table.isRowHidden(visual_row):
                    self.table.setCurrentCell(visual_row, 0)
                    break
            else:
                self.table.clearSelection()
        self._sync_filter_geometry()
        self._refresh_actions()

    def add_row(self) -> None:
        if self._save_in_progress:
            return
        row_id = self.model.add_row()
        self._populate_table(row_id)
        visual_row = self._find_visual_row(row_id)
        if visual_row >= 0:
            column = TABLE_COLUMNS.index("db_key")
            self.table.setCurrentCell(visual_row, column)
            self.table.editItem(self.table.item(visual_row, column))

    def disable_selected(self) -> None:
        row_id = self._current_row_id()
        if not row_id or self._save_in_progress:
            return
        self.model.disable(row_id)
        visual_row = self._find_visual_row(row_id)
        item = self.table.item(visual_row, TABLE_COLUMNS.index("is_enabled"))
        if item is not None:
            with QSignalBlocker(self.table):
                item.setCheckState(Qt.Unchecked)
        self._refresh_state()

    def delete_selected(self) -> None:
        row_id = self._current_row_id()
        if not row_id or self._save_in_progress:
            return
        if self.model.is_pending_delete(row_id):
            self.model.restore_pending_delete(row_id)
            self._populate_table(row_id)
            return
        if self.model.is_new(row_id):
            self.model.remove_or_stage_delete(row_id)
            self._populate_table()
            return

        table_key = str(self.model.get_row(row_id).get("table_key") or "")
        try:
            audit = self.repository.audit_dependencies(table_key)
        except Exception as exc:  # noqa: BLE001 - граница UI не должна завершать приложение
            QMessageBox.warning(self, "Не удалось проверить зависимости", str(exc))
            return
        if audit.blocking_count:
            answer = QMessageBox.question(
                self,
                "Удаление заблокировано зависимостями",
                audit.message(table_key)
                + "\n\nУдаление небезопасно. Отключить таблицу вместо удаления?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.Yes:
                self.disable_selected()
            return
        answer = QMessageBox.question(
            self,
            "Подтверждение удаления",
            audit.message(table_key)
            + f"\n\nПосле сохранения metadata будет удалена; полей каскадно удалится: {audit.fields}. Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.model.remove_or_stage_delete(row_id)
        self._populate_table(row_id)

    def revert_changes(self) -> None:
        if self._save_in_progress or not self.model.is_dirty:
            return
        selected = self._current_row_id()
        self.model.restore()
        self._populate_table(selected)

    def refresh_rows(self) -> None:
        if self._save_in_progress:
            return
        if self.model.is_dirty and not self._resolve_pending(
            "Перед обновлением реестра сохраните или отмените локальные изменения."
        ):
            return
        selected = self._current_table_key()
        try:
            self._load_rows(selected)
        except Exception as exc:  # noqa: BLE001 - граница UI не должна завершать приложение
            QMessageBox.warning(self, "Ошибка обновления реестра", str(exc))

    def _current_table_key(self) -> str:
        row_id = self._current_row_id()
        if not row_id or row_id not in self.model.row_ids:
            return ""
        return str(self.model.get_row(row_id).get("table_key") or "")

    @property
    def selected_table_key(self) -> str:
        return self._current_table_key()

    def save_changes(self) -> bool:
        if self._save_in_progress or not self.model.is_dirty:
            return not self.model.is_dirty
        self._finish_editor()
        self._refresh_state()
        if self.model.validation_issues:
            QMessageBox.warning(
                self,
                "Исправьте ошибки",
                f"Сохранение заблокировано. Ошибок: {len(self.model.validation_issues)}.",
            )
            return False
        selected = self._current_table_key()
        write_completed = False
        rows = None
        error = None
        try:
            changes = self.model.changeset()
            self._save_in_progress = True
            self.save_button.setText("Сохранение…")
            self._refresh_state()
            QApplication.processEvents()
            self.repository.save(changes)
            write_completed = True
            rows = self.repository.load()
        except Exception as exc:  # noqa: BLE001 - показываем любую ошибку операции пользователю
            error = exc
        finally:
            self._save_in_progress = False
            self.save_button.setText("Сохранить изменения")
        if error is not None:
            if write_completed:
                committed_rows = [
                    self.model.get_row(row_id)
                    for row_id in self.model.row_ids
                    if not self.model.is_pending_delete(row_id)
                ]
                self.model.capture(committed_rows)
                self.saved = True
                self._populate_table(selected)
                QMessageBox.warning(
                    self,
                    "Реестр сохранён, но не перечитан",
                    "Транзакция завершилась успешно, однако перечитать фактические строки не удалось. "
                    f"Повторная запись не выполнялась. Закройте редактор и обновите список.\n\n{error}",
                )
                return True
            self._refresh_state()
            QMessageBox.warning(
                self,
                "Ошибка сохранения реестра",
                str(error),
            )
            return False
        assert rows is not None
        self.model.capture(rows)
        self.saved = True
        self._populate_table(selected)
        return True

    def _resolve_pending(self, message: str) -> bool:
        if not self.model.is_dirty:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Несохранённые изменения")
        box.setText(message)
        save_button = box.addButton("Сохранить", QMessageBox.AcceptRole)
        discard_button = box.addButton("Не сохранять", QMessageBox.DestructiveRole)
        cancel_button = box.addButton("Отмена", QMessageBox.RejectRole)
        box.setDefaultButton(save_button)
        box.exec_()
        clicked = box.clickedButton()
        if clicked is save_button:
            return self.save_changes()
        if clicked is discard_button:
            self.model.restore()
            self._populate_table()
            return True
        if clicked is cancel_button:
            return False
        return False

    def closeEvent(self, event) -> None:
        if self.model.is_dirty and not self._resolve_pending(
            "В реестре физических таблиц есть несохранённые изменения."
        ):
            event.ignore()
            return
        self._settings.setValue(self.GEOMETRY_KEY, self.saveGeometry())
        super().closeEvent(event)
