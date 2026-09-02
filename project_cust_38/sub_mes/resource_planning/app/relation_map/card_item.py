from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsItem

from .palette import (
    BORDER, CARD_BG, CARD_ROOT_BG, GRID, HEADER_BG, HEADER_ROOT_BG,
    MUTED, PORT, ROOT_BORDER, TEXT, as_bool,
)


class TableCardItem(QGraphicsItem):
    WIDTH = 360.0
    HEADER_HEIGHT = 52.0
    ROW_HEIGHT = 27.0
    FOOTER = 13.0
    PORT_RADIUS = 6.0

    def __init__(
        self,
        table: dict,
        fields: List[dict],
        *,
        is_root: bool = False,
        on_moved: Optional[Callable[['TableCardItem'], None]] = None,
    ) -> None:
        super().__init__()
        self.table = table
        self.fields = fields
        self.table_key = str(table.get('table_key') or '')
        self.is_root = is_root
        self.on_moved = on_moved
        self._ports: Dict[str, Dict[str, QPointF]] = {}
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.OpenHandCursor)
        self.setZValue(10)
        self._index_ports()

    @property
    def height(self) -> float:
        return self.HEADER_HEIGHT + max(1, len(self.fields)) * self.ROW_HEIGHT + self.FOOTER

    def boundingRect(self) -> QRectF:  # noqa: N802
        margin = self.PORT_RADIUS + 2
        return QRectF(-margin, -margin, self.WIDTH + margin * 2, self.height + margin * 2)

    def _index_ports(self) -> None:
        self._ports.clear()
        if not self.fields:
            return
        for index, field in enumerate(self.fields):
            name = str(field.get('field_name') or '')
            y = self.HEADER_HEIGHT + index * self.ROW_HEIGHT + self.ROW_HEIGHT / 2
            self._ports[name] = {'left': QPointF(0, y), 'right': QPointF(self.WIDTH, y)}

    def port_scene_position(self, field_name: str, side: str) -> Optional[QPointF]:
        local = self._ports.get(field_name, {}).get(side)
        return self.mapToScene(local) if local is not None else None

    def port_at(self, local_pos: QPointF) -> Optional[dict]:
        radius = self.PORT_RADIUS + 4
        for field_name, sides in self._ports.items():
            for side, point in sides.items():
                if (point - local_pos).manhattanLength() <= radius * 1.5:
                    return {'table_key': self.table_key, 'field_name': field_name, 'side': side}
        return None

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: D401
        painter.setRenderHint(QPainter.Antialiasing, True)
        border = ROOT_BORDER if self.is_root else BORDER
        card_bg = CARD_ROOT_BG if self.is_root else CARD_BG
        header_bg = HEADER_ROOT_BG if self.is_root else HEADER_BG
        card = QRectF(0, 0, self.WIDTH, self.height)
        path = QPainterPath()
        path.addRoundedRect(card, 10, 10)
        painter.setPen(QPen(border, 1.8))
        painter.setBrush(QBrush(card_bg))
        painter.drawPath(path)

        header = QPainterPath()
        header.addRoundedRect(QRectF(0, 0, self.WIDTH, self.HEADER_HEIGHT + 9), 10, 10)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(header_bg))
        painter.drawPath(header)
        painter.fillRect(QRectF(0, self.HEADER_HEIGHT - 9, self.WIDTH, 18), header_bg)
        painter.setPen(QPen(border, 1.0))
        painter.drawLine(0, int(self.HEADER_HEIGHT), int(self.WIDTH), int(self.HEADER_HEIGHT))

        title = str(self.table.get('table_name') or self.table_key)
        font = QFont(painter.font())
        font.setBold(True)
        font.setPointSizeF(9.2)
        painter.setFont(font)
        painter.setPen(TEXT)
        painter.drawText(QRectF(14, 6, self.WIDTH - 28, 20), Qt.AlignLeft | Qt.AlignVCenter, title)
        font.setBold(False)
        font.setPointSizeF(7.6)
        painter.setFont(font)
        painter.setPen(MUTED)
        badge = ' · базовая' if self.is_root else ''
        painter.drawText(QRectF(14, 26, self.WIDTH - 28, 19), Qt.AlignLeft | Qt.AlignVCenter, self.table_key + badge)

        if not self.fields:
            painter.drawText(QRectF(14, self.HEADER_HEIGHT + 6, self.WIDTH - 28, self.ROW_HEIGHT), Qt.AlignVCenter, 'нет описанных полей')
            return

        font.setPointSizeF(8.0)
        painter.setFont(font)
        for index, field in enumerate(self.fields):
            y = self.HEADER_HEIGHT + index * self.ROW_HEIGHT
            if index:
                painter.setPen(QPen(GRID, 1))
                painter.drawLine(10, int(y), int(self.WIDTH - 10), int(y))
            name = str(field.get('field_name') or '')
            db_type = str(field.get('db_type') or '')
            flags = []
            if as_bool(field.get('is_pk')):
                flags.append('PK')
            if not as_bool(field.get('nullable'), 1):
                flags.append('NOT NULL')
            if not as_bool(field.get('include_in_schema'), 1):
                flags.append('выкл.')
            suffix = f" · {', '.join(flags)}" if flags else ''
            value = f'{name} : {db_type}{suffix}' if db_type else f'{name}{suffix}'
            painter.setPen(TEXT)
            painter.drawText(QRectF(16, y, self.WIDTH - 32, self.ROW_HEIGHT), Qt.AlignVCenter, value)
            for point in self._ports.get(name, {}).values():
                painter.setPen(QPen(PORT, 1.5))
                painter.setBrush(QBrush(CARD_BG))
                painter.drawEllipse(point, self.PORT_RADIUS, self.PORT_RADIUS)

        if self.isSelected():
            painter.setPen(QPen(PORT, 1.4, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(card.adjusted(3, 3, -3, -3), 8, 8)

    def itemChange(self, change, value):  # noqa: N802
        result = super().itemChange(change, value)
        if change == QGraphicsItem.ItemPositionHasChanged and self.on_moved:
            self.on_moved(self)
        return result

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)
