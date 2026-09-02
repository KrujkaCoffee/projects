from __future__ import annotations

import datetime as _dt
from typing import Any, Iterable, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QTableWidget, QTableWidgetItem


BOOL_TRUE = {"1", "true", "t", "yes", "y", "on"}
BOOL_FALSE = {"0", "false", "f", "no", "n", "off", ""}


def now_text() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def to_int_bool(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return 1 if value else 0
    text = str(value or "").strip().lower()
    if text in BOOL_TRUE:
        return 1
    if text in BOOL_FALSE:
        return 0
    return 1 if text else 0


def nullable_text(value: Any) -> str:
    return "" if value is None else str(value)


def make_item(value: Any = "", *, editable: bool = True, checkable: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem("" if checkable else nullable_text(value))
    flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
    if editable and not checkable:
        flags |= Qt.ItemIsEditable
    if checkable:
        flags |= Qt.ItemIsUserCheckable
        item.setCheckState(Qt.Checked if to_int_bool(value) else Qt.Unchecked)
        item.setText("")
    item.setFlags(flags)
    item.setData(Qt.UserRole, value)
    return item


def read_item(table: QTableWidget, row: int, col: int, *, checkable: bool = False, as_int: bool = False) -> Any:
    item = table.item(row, col)
    if item is None:
        return 0 if as_int else ""
    if checkable:
        return 1 if item.checkState() == Qt.Checked else 0
    text = item.text()
    if as_int:
        try:
            return int(text.strip() or "0")
        except ValueError:
            return 0
    return text


def set_headers(table: QTableWidget, headers: Iterable[str], tooltips: Optional[Iterable[str]] = None) -> None:
    headers = list(headers)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    if tooltips is not None:
        for idx, tooltip in enumerate(tooltips):
            item = table.horizontalHeaderItem(idx)
            if item is not None:
                item.setToolTip(str(tooltip))


def selected_row(table: QTableWidget) -> int:
    # indexes = table.selectionModel().selectedRows() if table.selectionModel() else []
    # if indexes:
    #     print('INDEXES', [i.row() for i in indexes])
    #     return indexes[0].row()
    # print('CURRENT', table.currentRow())
    return table.currentRow()


def warn(parent, text: str, title: str = "Внимание") -> None:
    QMessageBox.warning(parent, title, text)


def info(parent, text: str, title: str = "Готово") -> None:
    QMessageBox.information(parent, title, text)


def confirm(parent, text: str, title: str = "Подтверждение") -> bool:
    return QMessageBox.question(parent, title, text, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes


def coerce_cell_value(text: str) -> Optional[str]:
    """Browser cell convention: literal NULL means database NULL, empty string stays empty."""
    if text.strip().upper() == "NULL":
        return None
    return text
