from __future__ import annotations

from collections.abc import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QStyledItemDelegate

from app.theme import theme_color

ROW_ID_ROLE = Qt.UserRole + 101


class MutatedCellDelegate(QStyledItemDelegate):
    """Рисует маркер состояния поверх стандартной отрисовки ячейки."""

    def __init__(
        self, columns, state_provider: Callable[[str, str], str], parent=None
    ) -> None:
        super().__init__(parent)
        self.columns = tuple(columns)
        self.state_provider = state_provider

    @staticmethod
    def _color(option, state: str) -> QColor:
        if state == "invalid":
            return theme_color("danger")
        if state == "new":
            return theme_color("saved")
        if state == "pending_delete":
            return theme_color("canvas_disabled")
        return theme_color("warning")

    def paint(self, painter: QPainter, option, index) -> None:
        super().paint(painter, option, index)
        row_id = str(index.data(ROW_ID_ROLE) or "")
        if not row_id or index.column() >= len(self.columns):
            return
        state = self.state_provider(row_id, self.columns[index.column()])
        if state not in {"dirty", "new", "invalid", "pending_delete"}:
            return

        painter.save()
        pen = QPen(self._color(option, state), 2)
        if state == "pending_delete":
            pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        rect = option.rect.adjusted(2, 0, -2, -2)
        y = rect.bottom()
        painter.drawLine(rect.left(), y, rect.right(), y)
        painter.restore()

    def helpEvent(self, event, view, option, index) -> bool:
        # Подсказка хранится в элементе; стандартный делегат корректно показывает её.
        return super().helpEvent(event, view, option, index)
