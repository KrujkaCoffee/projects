from __future__ import annotations

from typing import Dict, List, Set

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QTableWidgetItem

from app.ui_loader import load_ui

from .palette import as_bool


class RelationTablePickerDialog(QDialog):
    def __init__(
        self,
        parent,
        tables: List[dict],
        fields_by_table: Dict[str, List[dict]],
        relations: List[dict],
        excluded_keys: Set[str],
    ) -> None:
        super().__init__(parent)
        load_ui('relation_table_picker_dialog.ui', self)
        self.tables = tables
        self.fields_by_table = fields_by_table
        self.relations = relations
        self.excluded_keys = set(excluded_keys)
        self._visible_rows: List[dict] = []
        self.tables_grid.setColumnCount(6)
        self.tables_grid.setHorizontalHeaderLabels(
            ['Ключ', 'Название', 'База', 'Включена', 'Поля', 'Связи']
        )
        self.tables_grid.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tables_grid.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tables_grid.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tables_grid.setToolTip('Для выбора нескольких таблиц используйте Ctrl или Shift.')
        self.filter_edit.textChanged.connect(self._apply_filter)
        self.tables_grid.itemDoubleClicked.connect(lambda *_: self.accept())
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        ok = self.buttonBox.button(QDialogButtonBox.Ok)
        cancel = self.buttonBox.button(QDialogButtonBox.Cancel)
        if ok:
            ok.setText('Добавить выбранные')
        if cancel:
            cancel.setText('Отмена')
        self._apply_filter()

    @property
    def selected_table_keys(self) -> List[str]:
        selection = self.tables_grid.selectionModel()
        indexes = sorted(selection.selectedRows(0), key=lambda index: index.row()) if selection else []
        result: List[str] = []
        seen: Set[str] = set()
        for index in indexes:
            item = self.tables_grid.item(index.row(), 0)
            key = str(item.data(Qt.UserRole) or item.text() or '') if item is not None else ''
            if key and key not in seen:
                seen.add(key)
                result.append(key)
        return result

    @property
    def selected_table_key(self) -> str:
        selected = self.selected_table_keys
        return selected[0] if selected else ''

    def _relation_count(self, key: str) -> int:
        return sum(
            1
            for relation in self.relations
            if key in {
                str(relation.get('source_table_key') or ''),
                str(relation.get('target_table_key') or ''),
            }
        )

    def _apply_filter(self) -> None:
        tokens = [token.casefold() for token in self.filter_edit.text().split() if token.strip()]
        self._visible_rows = []
        for row in self.tables:
            key = str(row.get('table_key') or '')
            if not key or key in self.excluded_keys:
                continue
            haystack = ' '.join(
                [key, str(row.get('table_name') or ''), str(row.get('db_key') or '')]
            ).casefold()
            if tokens and not all(token in haystack for token in tokens):
                continue
            self._visible_rows.append(row)
        self._populate()

    def _populate(self) -> None:
        grid = self.tables_grid
        grid.setSortingEnabled(False)
        grid.setRowCount(len(self._visible_rows))
        for row_no, row in enumerate(self._visible_rows):
            key = str(row.get('table_key') or '')
            values = [
                key,
                str(row.get('table_name') or ''),
                str(row.get('db_key') or ''),
                'да' if as_bool(row.get('is_enabled')) else 'нет',
                str(len(self.fields_by_table.get(key, []))),
                str(self._relation_count(key)),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 0:
                    item.setData(Qt.UserRole, key)
                grid.setItem(row_no, column, item)
        grid.resizeColumnsToContents()
        grid.horizontalHeader().setStretchLastSection(True)
        grid.setSortingEnabled(True)
        self.result_count_label.setText(f'Доступно: {len(self._visible_rows)}')
        if self._visible_rows:
            grid.selectRow(0)
