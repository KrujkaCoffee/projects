from __future__ import annotations

import math
from typing import Dict, List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.theme import theme_color

from ..db import ColumnInfo, DbError, PostgresDatabase
from ..dialogs import RowEditDialog
from ..ui_helpers import coerce_cell_value, confirm, warn
from ..ui_loader import load_ui


class DbBrowserTab(QWidget):
    """SQLiteStudio-like generic table browser for PostgreSQL.

    Feature focus:
    - left table list;
    - paginated SELECT;
    - filter row directly above the data rows;
    - cell updates, NULL, insert and delete rows.
    """

    def __init__(self, db: PostgresDatabase, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.current_schema = ""
        self.current_table = ""
        self.columns: List[ColumnInfo] = []
        self.column_names: List[str] = []
        self.primary_keys: List[str] = []
        self.row_identities: List[Dict[str, object]] = []
        self.original_rows: List[Dict[str, object]] = []
        self.dirty_cells: set[Tuple[int, int]] = set()
        self.page = 1
        self.total_rows = 0
        self._loading = False
        self._filters: Dict[str, str] = {}
        self._active_page_size = 100
        self._restoring_tree_selection = False

        self._build_ui()

    def _build_ui(self) -> None:
        load_ui("db_browser_tab.ui", self)
        self.page_size.setCurrentText("100")
        self._active_page_size = 100
        self.tables_tree.setHeaderLabels(["Схема / таблица"])
        self.data_grid.setAlternatingRowColors(True)
        self.data_grid.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.data_grid.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_grid.horizontalHeader().setStretchLastSection(True)
        self.data_grid.verticalHeader().setVisible(True)
        self.data_grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.splitter.setSizes([320, 1180])
        self._connect_signals()
        self._update_dirty_controls()

    def _connect_signals(self) -> None:
        self.reload_tables_btn.clicked.connect(self.load_table_list)
        self.table_search.textChanged.connect(self._filter_table_tree)
        self.tables_tree.currentItemChanged.connect(self._on_table_item_changed)
        self.apply_filters_btn.clicked.connect(self.apply_filters)
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        self.reload_page_btn.clicked.connect(self.reload_page)
        self.save_btn.clicked.connect(self.save_changes)
        self.cancel_btn.clicked.connect(self.cancel_changes)
        self.add_row_btn.clicked.connect(self.add_row)
        self.delete_row_btn.clicked.connect(self.delete_selected_rows)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self.page_spin.valueChanged.connect(self._on_page_spin_changed)
        self.page_size.currentTextChanged.connect(self._on_page_size_changed)
        self.data_grid.itemChanged.connect(self._on_item_changed)
        self.data_grid.customContextMenuRequested.connect(self._show_context_menu)

    # ------------------------------------------------------------------ basics
    def require_connection(self) -> bool:
        if not self.db.is_connected:
            warn(self, "Сначала подключитесь к PostgreSQL")
            return False
        return True

    def load_table_list(self) -> None:
        if not self.require_connection():
            return
        try:
            rows = self.db.list_tables(include_views=False)
            self.tables_tree.clear()
            schemas: Dict[str, QTreeWidgetItem] = {}
            for row in rows:
                schema = row["table_schema"]
                table = row["table_name"]
                parent = schemas.get(schema)
                if parent is None:
                    parent = QTreeWidgetItem([schema])
                    parent.setData(0, Qt.UserRole, {"schema": schema, "table": ""})
                    self.tables_tree.addTopLevelItem(parent)
                    schemas[schema] = parent
                child = QTreeWidgetItem([table])
                child.setData(0, Qt.UserRole, {"schema": schema, "table": table})
                parent.addChild(child)
            self.tables_tree.expandAll()
            self._filter_table_tree()
        except DbError as exc:
            warn(self, str(exc), "Ошибка списка таблиц")

    def _filter_table_tree(self) -> None:
        text = self.table_search.text().strip().lower()
        for i in range(self.tables_tree.topLevelItemCount()):
            schema_item = self.tables_tree.topLevelItem(i)
            visible_children = 0
            for j in range(schema_item.childCount()):
                child = schema_item.child(j)
                full = f"{schema_item.text(0)}.{child.text(0)}".lower()
                hidden = bool(text and text not in full)
                child.setHidden(hidden)
                if not hidden:
                    visible_children += 1
            schema_item.setHidden(bool(text and visible_children == 0 and text not in schema_item.text(0).lower()))

    def _on_table_item_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem) -> None:
        if self._restoring_tree_selection or not current:
            return
        data = current.data(0, Qt.UserRole) or {}
        schema = data.get("schema") or ""
        table = data.get("table") or ""
        if not schema or not table:
            return
        if not self._confirm_discard_changes(
            "Есть неприменённые изменения. Перейти к другой таблице и отменить их?"
        ):
            if previous:
                self._restoring_tree_selection = True
                try:
                    self.tables_tree.setCurrentItem(previous)
                finally:
                    self._restoring_tree_selection = False
            return
        self.open_table(schema, table)

    def open_table(self, schema: str, table: str) -> None:
        self.current_schema = schema
        self.current_table = table
        self.page = 1
        self._filters = {}
        try:
            self.columns = self.db.get_columns(schema, table)
            self.column_names = [c.name for c in self.columns]
            self.primary_keys = self.db.get_primary_keys(schema, table)
            self.table_label.setText(
                f"{schema}.{table}" + (f" | PK: {', '.join(self.primary_keys)}" if self.primary_keys else " | PK нет, используется ctid")
            )
            self.reload_page(force=True)
        except DbError as exc:
            warn(self, str(exc), "Ошибка открытия таблицы")

    # ------------------------------------------------------------------ filters / paging
    def current_page_size(self) -> int:
        return int(self.page_size.currentText())

    def _filter_widgets_values(self) -> Dict[str, str]:
        filters: Dict[str, str] = {}
        for c, col in enumerate(self.column_names):
            widget = self.data_grid.cellWidget(0, c)
            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if text:
                    filters[col] = text
        return filters

    def apply_filters(self) -> None:
        if not self._confirm_discard_changes(
            "Есть неприменённые изменения. Применить фильтры и отменить их?"
        ):
            return
        self._filters = self._filter_widgets_values()
        self.page = 1
        self.reload_page(force=True)

    def clear_filters(self) -> None:
        if not self._confirm_discard_changes(
            "Есть неприменённые изменения. Очистить фильтры и отменить их?"
        ):
            return
        self._filters = {}
        for c in range(self.data_grid.columnCount()):
            widget = self.data_grid.cellWidget(0, c)
            if isinstance(widget, QLineEdit):
                widget.clear()
        self.page = 1
        self.reload_page(force=True)

    def _on_page_spin_changed(self, value: int) -> None:
        if self._loading or value == self.page:
            return
        if not self._confirm_discard_changes(
            "Есть неприменённые изменения. Перейти на другую страницу и отменить их?"
        ):
            self._loading = True
            try:
                self.page_spin.setValue(self.page)
            finally:
                self._loading = False
            return
        self.page = value
        self.reload_page(force=True)

    def _on_page_size_changed(self) -> None:
        if self._loading:
            return
        new_size = self.current_page_size()
        if new_size == self._active_page_size:
            return
        if not self._confirm_discard_changes(
            "Есть неприменённые изменения. Изменить размер страницы и отменить их?"
        ):
            self._loading = True
            try:
                self.page_size.setCurrentText(str(self._active_page_size))
            finally:
                self._loading = False
            return
        self._active_page_size = new_size
        self.page = 1
        self.reload_page(force=True)

    def prev_page(self) -> None:
        if self.page <= 1:
            return
        if not self._confirm_discard_changes(
            "Есть неприменённые изменения. Перейти на предыдущую страницу и отменить их?"
        ):
            return
        self.page -= 1
        self.reload_page(force=True)

    def next_page(self) -> None:
        max_page = max(1, math.ceil(self.total_rows / self.current_page_size()))
        if self.page >= max_page:
            return
        if not self._confirm_discard_changes(
            "Есть неприменённые изменения. Перейти на следующую страницу и отменить их?"
        ):
            return
        self.page += 1
        self.reload_page(force=True)

    def reload_page(self, force: bool = False) -> None:
        if not self.current_schema or not self.current_table:
            return
        if not force and not self._confirm_discard_changes(
            "Есть неприменённые изменения. Перезагрузить страницу и отменить их?"
        ):
            return
        try:
            where_sql, params = self._build_where()
            qname = self.db.qname(self.current_schema, self.current_table)
            order_sql = self._build_order_sql()
            page_size = self.current_page_size()
            self._active_page_size = page_size
            offset = (self.page - 1) * page_size
            count_row = self.db.fetchone(
                f"SELECT count(*) AS cnt FROM {qname} {where_sql}",
                params,
            )
            self.total_rows = int((count_row or {}).get("cnt") or 0)
            max_page = max(1, math.ceil(self.total_rows / page_size))
            if self.page > max_page:
                self.page = max_page
                offset = (self.page - 1) * page_size
            select_cols = ", ".join(self.db.quote_ident(c) for c in self.column_names)
            if self.primary_keys:
                query = (
                    f"SELECT {select_cols} FROM {qname} {where_sql} "
                    f"{order_sql} LIMIT %s OFFSET %s"
                )
            else:
                query = (
                    f"SELECT ctid::text AS __rowid__, {select_cols} FROM {qname} "
                    f"{where_sql} {order_sql} LIMIT %s OFFSET %s"
                )
            rows = self.db.fetchall(query, params + [page_size, offset])
            self._populate_data_grid(rows)
            self._update_pager(max_page)
        except DbError as exc:
            warn(self, str(exc), "Ошибка загрузки данных")

    def _build_where(self) -> Tuple[str, List[object]]:
        clauses: List[str] = []
        params: List[object] = []
        for column, expr in self._filters.items():
            if column not in self.column_names:
                continue
            clause, values = self._parse_filter(column, expr)
            if clause:
                clauses.append(clause)
                params.extend(values)
        return ("WHERE " + " AND ".join(clauses), params) if clauses else ("", params)

    def _parse_filter(self, column: str, expr: str) -> Tuple[str, List[object]]:
        expr = expr.strip()
        ident = self.db.quote_ident(column)
        upper = expr.upper()
        if upper in {"NULL", "IS NULL"}:
            return f"{ident} IS NULL", []
        if upper in {"!NULL", "NOT NULL", "IS NOT NULL"}:
            return f"{ident} IS NOT NULL", []
        for op in (">=", "<=", "!=", "=", ">", "<"):
            if expr.startswith(op):
                value = expr[len(op):].strip()
                sql_op = "<>" if op == "!=" else op
                return f"{ident} {sql_op} %s", [value]
        if expr.startswith("~"):
            return f"CAST({ident} AS TEXT) ILIKE %s", [f"%{expr[1:].strip()}%"]
        return f"CAST({ident} AS TEXT) ILIKE %s", [f"%{expr}%"]

    def _build_order_sql(self) -> str:
        if self.primary_keys:
            cols = ", ".join(self.db.quote_ident(c) for c in self.primary_keys)
        elif self.column_names:
            cols = self.db.quote_ident(self.column_names[0])
        else:
            return ""
        return f"ORDER BY {cols}"

    def _update_pager(self, max_page: int) -> None:
        self._loading = True
        try:
            self.page_spin.setMaximum(max_page)
            self.page_spin.setValue(self.page)
            self.total_label.setText(f"{self.total_rows} строк, страница {self.page}/{max_page}")
            self.prev_btn.setEnabled(self.page > 1)
            self.next_btn.setEnabled(self.page < max_page)
        finally:
            self._loading = False

    # ------------------------------------------------------------------ grid
    def _populate_data_grid(self, rows: List[Dict[str, object]]) -> None:
        self._loading = True
        try:
            self.dirty_cells.clear()
            self.row_identities = []
            self.original_rows = []
            self.data_grid.clear()
            self.data_grid.setColumnCount(len(self.column_names))
            self.data_grid.setHorizontalHeaderLabels(self.column_names)
            self.data_grid.setRowCount(len(rows) + 1)
            self.data_grid.setVerticalHeaderItem(0, QTableWidgetItem("фильтр"))
            for c, col in enumerate(self.column_names):
                edit = QLineEdit()
                edit.setPlaceholderText(col)
                edit.setText(self._filters.get(col, ""))
                edit.returnPressed.connect(self.apply_filters)
                self.data_grid.setCellWidget(0, c, edit)
            for r, row in enumerate(rows, start=1):
                self.data_grid.setVerticalHeaderItem(r, QTableWidgetItem(str((self.page - 1) * self.current_page_size() + r)))
                identity: Dict[str, object] = {}
                if self.primary_keys:
                    for pk in self.primary_keys:
                        identity[pk] = row.get(pk)
                else:
                    identity["__rowid__"] = row.get("__rowid__")
                self.row_identities.append(identity)
                original = {col: row.get(col) for col in self.column_names}
                self.original_rows.append(original)
                for c, col in enumerate(self.column_names):
                    value = row.get(col)
                    text = "NULL" if value is None else str(value)
                    item = QTableWidgetItem(text)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                    item.setData(Qt.UserRole, value)
                    if value is None:
                        item.setToolTip("NULL. Для пустой строки очистите текст; для NULL оставьте/введите NULL или используйте контекстное меню.")
                    self.data_grid.setItem(r, c, item)
            self.data_grid.resizeColumnsToContents()
        finally:
            self._loading = False
        self._update_dirty_controls()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or item.row() == 0:
            return
        data_idx = item.row() - 1
        col_idx = item.column()
        if data_idx < 0 or data_idx >= len(self.original_rows):
            return
        column = self.column_names[col_idx]
        original_text = self._display_value(self.original_rows[data_idx].get(column))
        key = (data_idx, col_idx)
        if item.text() == original_text:
            self.dirty_cells.discard(key)
            item.setBackground(QBrush())
        else:
            self.dirty_cells.add(key)
            item.setBackground(QBrush(theme_color("dirty_bg")))
        self._update_dirty_controls()

    @staticmethod
    def _display_value(value: object) -> str:
        return "NULL" if value is None else str(value)

    def _update_dirty_controls(self) -> None:
        dirty_count = len(self.dirty_cells)
        enabled = dirty_count > 0
        self.save_btn.setEnabled(enabled)
        self.cancel_btn.setEnabled(enabled)
        if hasattr(self, "pending_changes_label"):
            self.pending_changes_label.setText(
                f"Изменено ячеек: {dirty_count}" if enabled else "Нет неприменённых изменений"
            )

    def apply_application_theme(self, _theme=None) -> None:
        old_loading = self._loading
        self._loading = True
        try:
            for data_row, column in self.dirty_cells:
                item = self.data_grid.item(data_row + 1, column)
                if item is not None:
                    item.setBackground(QBrush(theme_color("dirty_bg")))
        finally:
            self._loading = old_loading
        self.data_grid.viewport().update()

    def has_pending_changes(self) -> bool:
        return bool(self.dirty_cells)

    def _confirm_discard_changes(self, message: str) -> bool:
        if not self.dirty_cells:
            return True
        if not confirm(self, message):
            return False
        self.cancel_changes(silent=True)
        return True

    def cancel_changes(self, silent: bool = False) -> None:
        if not self.dirty_cells:
            self._update_dirty_controls()
            return
        self._loading = True
        try:
            for data_idx, col_idx in list(self.dirty_cells):
                if data_idx < 0 or data_idx >= len(self.original_rows):
                    continue
                if col_idx < 0 or col_idx >= len(self.column_names):
                    continue
                item = self.data_grid.item(data_idx + 1, col_idx)
                if item is None:
                    continue
                column = self.column_names[col_idx]
                value = self.original_rows[data_idx].get(column)
                item.setText(self._display_value(value))
                item.setData(Qt.UserRole, value)
                item.setBackground(QBrush())
            self.dirty_cells.clear()
        finally:
            self._loading = False
        self._update_dirty_controls()
        if not silent:
            self.data_grid.viewport().update()

    def _show_context_menu(self, pos) -> None:
        item = self.data_grid.itemAt(pos)
        menu = QMenu(self)
        set_null = QAction("Установить NULL", self)
        revert = QAction("Откатить ячейку", self)
        copy = QAction("Копировать", self)
        menu.addAction(set_null)
        menu.addAction(revert)
        menu.addSeparator()
        menu.addAction(copy)
        action = menu.exec_(self.data_grid.viewport().mapToGlobal(pos))
        if item is None or item.row() == 0:
            return
        if action == set_null:
            item.setText("NULL")
            item.setData(Qt.UserRole, None)
            self._on_item_changed(item)
        elif action == revert:
            data_idx = item.row() - 1
            col_idx = item.column()
            column = self.column_names[col_idx]
            value = self.original_rows[data_idx].get(column)
            self._loading = True
            try:
                item.setText(self._display_value(value))
                item.setData(Qt.UserRole, value)
                item.setBackground(QBrush())
                self.dirty_cells.discard((data_idx, col_idx))
            finally:
                self._loading = False
            self._update_dirty_controls()
        elif action == copy:
            QApplication.clipboard().setText(item.text())

    # ------------------------------------------------------------------ CRUD
    def save_changes(self) -> None:
        if not self.current_schema or not self.current_table:
            return
        if not self.dirty_cells:
            return
        qname = self.db.qname(self.current_schema, self.current_table)
        try:
            changed_by_row: Dict[int, List[int]] = {}
            for data_idx, col_idx in self.dirty_cells:
                changed_by_row.setdefault(data_idx, []).append(col_idx)
            with self.db.transaction() as cur:
                for data_idx, col_indexes in changed_by_row.items():
                    set_parts = []
                    params: List[object] = []
                    for col_idx in sorted(set(col_indexes)):
                        col = self.column_names[col_idx]
                        item = self.data_grid.item(data_idx + 1, col_idx)
                        if item is None:
                            continue
                        set_parts.append(f"{self.db.quote_ident(col)} = %s")
                        params.append(coerce_cell_value(item.text()))
                    if not set_parts:
                        continue
                    where_sql, where_params = self._identity_where(self.row_identities[data_idx])
                    cur.execute(f"UPDATE {qname} SET {', '.join(set_parts)} WHERE {where_sql}", params + where_params)
            self.dirty_cells.clear()
            self._update_dirty_controls()
            self.reload_page(force=True)
        except Exception as exc:
            warn(self, str(exc), "Ошибка UPDATE")

    def _identity_where(self, identity: Dict[str, object]) -> Tuple[str, List[object]]:
        if "__rowid__" in identity:
            return "ctid = %s::tid", [identity["__rowid__"]]
        parts = []
        params = []
        for col, value in identity.items():
            if value is None:
                parts.append(f"{self.db.quote_ident(col)} IS NULL")
            else:
                parts.append(f"{self.db.quote_ident(col)} = %s")
                params.append(value)
        return " AND ".join(parts) if parts else "FALSE", params

    def add_row(self) -> None:
        if not self.current_schema or not self.current_table:
            warn(self, "Выберите таблицу")
            return
        if self.dirty_cells:
            warn(self, "Сначала примените или отмените изменения ячеек")
            return
        dialog = RowEditDialog(self, self.column_names, title=f"Добавить строку в {self.current_schema}.{self.current_table}")
        if dialog.exec_() != dialog.Accepted:
            return
        values = dialog.values()
        qname = self.db.qname(self.current_schema, self.current_table)
        try:
            if values:
                cols = list(values.keys())
                sql_cols = ", ".join(self.db.quote_ident(c) for c in cols)
                placeholders = ", ".join(["%s"] * len(cols))
                params = [values[c] for c in cols]
                self.db.execute(f"INSERT INTO {qname} ({sql_cols}) VALUES ({placeholders})", params)
            else:
                self.db.execute(f"INSERT INTO {qname} DEFAULT VALUES")
            self.reload_page()
        except DbError as exc:
            warn(self, str(exc), "Ошибка INSERT")

    def delete_selected_rows(self) -> None:
        if self.dirty_cells:
            warn(self, "Сначала примените или отмените изменения ячеек")
            return
        selected = sorted({idx.row() - 1 for idx in self.data_grid.selectedIndexes() if idx.row() > 0})
        if not selected:
            warn(self, "Выберите строки или ячейки строк для удаления")
            return
        if not confirm(self, f"Удалить строк: {len(selected)}?"):
            return
        qname = self.db.qname(self.current_schema, self.current_table)
        try:
            with self.db.transaction() as cur:
                for data_idx in reversed(selected):
                    if data_idx < 0 or data_idx >= len(self.row_identities):
                        continue
                    where_sql, params = self._identity_where(self.row_identities[data_idx])
                    cur.execute(f"DELETE FROM {qname} WHERE {where_sql}", params)
            self.reload_page()
        except Exception as exc:
            warn(self, str(exc), "Ошибка DELETE")
