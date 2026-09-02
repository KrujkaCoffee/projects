from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from .filters import ColumnFilter, build_filter, column_kind

TEXT_OPERATORS = (
    ("∋", "contains", "содержит все слова"),
    ("=", "equals", "равно"),
    ("≠", "not_equals", "не равно"),
    ("^", "starts", "начинается с"),
    ("$", "ends", "заканчивается на"),
    ("∌", "not_contains", "не содержит"),
    ("∅", "empty", "пусто / NULL"),
    ("¬∅", "not_empty", "не пусто"),
)
ORDER_OPERATORS = (
    ("=", "equals", "равно"),
    ("≠", "not_equals", "не равно"),
    (">", "gt", "больше"),
    ("≥", "gte", "больше или равно"),
    ("<", "lt", "меньше"),
    ("≤", "lte", "меньше или равно"),
    ("↔", "between", "диапазон включительно"),
    ("∅", "empty", "пусто / NULL"),
    ("¬∅", "not_empty", "не пусто"),
)


class ColumnFilterControl(QWidget):
    resetRequested = pyqtSignal(str)

    def __init__(self, column: str, parent=None) -> None:
        super().__init__(parent)
        self.column = column
        self.kind = column_kind(column)
        self.setObjectName(f"physical_filter_{column}")
        self.setProperty("filterInvalid", False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.operator = QComboBox(self)
        self.operator.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.operator.setMinimumContentsLength(2)
        self.value_edit: QLineEdit | None = None
        if self.kind == "bool":
            for title, value in (("Все", "all"), ("Да", "true"), ("Нет", "false")):
                self.operator.addItem(title, value)
            self.operator.setToolTip("Логический фильтр")
        else:
            operators = TEXT_OPERATORS if self.kind == "text" else ORDER_OPERATORS
            for title, value, tooltip in operators:
                self.operator.addItem(title, value)
                self.operator.setItemData(
                    self.operator.count() - 1,
                    tooltip,
                    Qt.ToolTipRole,
                )
            self.operator.setToolTip("Оператор фильтра")
            self.value_edit = QLineEdit(self)
            self.value_edit.setClearButtonEnabled(True)
            self.value_edit.setPlaceholderText(self._placeholder())
            self.value_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.value_edit.returnPressed.connect(self._request_apply_from_parent)

        self.reset_button = QToolButton(self)
        self.reset_button.setObjectName("column_filter_reset")
        self.reset_button.setText("×")
        self.reset_button.setToolTip("Сбросить фильтр этой колонки")
        self.reset_button.setAutoRaise(True)
        self.reset_button.setFixedWidth(22)

        layout.addWidget(self.operator)
        if self.value_edit is not None:
            layout.addWidget(self.value_edit, 1)
        layout.addWidget(self.reset_button)

        self.operator.currentIndexChanged.connect(self._operator_changed)
        self.reset_button.clicked.connect(self.reset)
        self._operator_changed()

    def _placeholder(self) -> str:
        if self.kind == "int":
            return "число / 10..50"
        if self.kind == "date":
            return "YYYY-MM-DD"
        return "значение"

    def _operator_changed(self) -> None:
        if self.value_edit is None:
            return
        operator = str(self.operator.currentData() or "")
        self.value_edit.setEnabled(operator not in {"empty", "not_empty"})
        if operator == "between":
            self.value_edit.setPlaceholderText(
                "начало..конец" if self.kind != "date" else "2026-01-01..2026-01-31"
            )
        else:
            self.value_edit.setPlaceholderText(self._placeholder())

    def _request_apply_from_parent(self) -> None:
        parent = self.parent()
        while parent is not None:
            callback = getattr(parent, "apply_column_filters", None)
            if callable(callback):
                callback()
                return
            parent = parent.parent()

    def current_filter(self) -> ColumnFilter | None:
        raw = self.value_edit.text() if self.value_edit is not None else ""
        return build_filter(self.column, str(self.operator.currentData() or ""), raw)

    def mark_invalid(self, invalid: bool, message: str = "") -> None:
        self.setProperty("filterInvalid", bool(invalid))
        self.setToolTip(message)
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()

    def reset(self, *, emit_signal: bool = True) -> None:
        self.operator.setCurrentIndex(0)
        if self.value_edit is not None:
            self.value_edit.clear()
        self.mark_invalid(False)
        if emit_signal:
            self.resetRequested.emit(self.column)

    def is_empty(self) -> bool:
        if self.kind == "bool":
            return str(self.operator.currentData() or "") == "all"
        operator = str(self.operator.currentData() or "")
        if operator in {"empty", "not_empty"}:
            return False
        return not bool(self.value_edit and self.value_edit.text().strip())


__all__ = ["ColumnFilterControl"]
