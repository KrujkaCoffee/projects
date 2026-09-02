from __future__ import annotations

from typing import Callable, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsSimpleTextItem

from .palette import DISABLED, DRAFT, SAVED


class RelationLineItem(QGraphicsPathItem):
    def __init__(
        self,
        relation: dict,
        pair: dict,
        path_factory: Callable[[dict, dict, int], QPainterPath],
        *,
        saved: bool,
        index: int = 0,
    ) -> None:
        super().__init__()
        self.relation = relation
        self.pair = pair
        self.path_factory = path_factory
        self.saved = saved
        self.index = index
        self.label = QGraphicsSimpleTextItem(self)
        self.setZValue(2)
        self.label.setZValue(3)
        self._style()
        self.update_path()

    @staticmethod
    def _enabled(relation: dict) -> bool:
        try:
            return int(relation.get('is_enabled', 1)) == 1
        except (TypeError, ValueError):
            return bool(relation.get('is_enabled', True))

    @property
    def endpoint_table_keys(self) -> frozenset[str]:
        return frozenset(
            str(self.pair.get(key) or '')
            for key in ('left_table_key', 'right_table_key')
            if self.pair.get(key)
        )

    def _style(self) -> None:
        if not self.saved:
            color, style, width = DRAFT, Qt.SolidLine, 2.8
            prefix = 'черновик'
        elif self._enabled(self.relation):
            color, style, width = SAVED, Qt.SolidLine, 2.2
            prefix = ''
        else:
            color, style, width = DISABLED, Qt.DashLine, 1.8
            prefix = 'выключена'
        self.setPen(QPen(color, width, style, Qt.RoundCap, Qt.RoundJoin))
        pieces: List[str] = [p for p in [prefix, str(self.relation.get('cardinality') or '')] if p]
        operator = str(self.pair.get('operator') or '=')
        if operator != '=':
            pieces.append(operator)
        if not pieces:
            pieces.append(str(self.relation.get('relation_key') or 'связь'))
        self.label.setText(' · '.join(pieces))
        self.label.setBrush(color)

    def update_path(self) -> None:
        """Refresh only this line's geometry and label position."""

        path = self.path_factory(self.relation, self.pair, self.index)
        self.setPath(path)
        if not path.isEmpty():
            point = path.pointAtPercent(0.5)
            self.label.setPos(point.x() + 5, point.y() - 18)
