from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtGui import QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsView

from .palette import PORT
from .space_pan import SpacePanState


class InteractionMixin:
    _drag_start: Optional[dict]
    _drag_line: Optional[QGraphicsPathItem]
    _pan_start: Optional[QPoint]
    _pan_button: object
    _space_pan_state: SpacePanState

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Space:
            if not event.isAutoRepeat() and not self._space_pan_state.space_pressed:
                self._space_pan_state.press_space()
                self._space_previous_cursor = self.viewport().cursor()
                self.viewport().setCursor(Qt.OpenHandCursor)
            event.accept()
            return
        QGraphicsView.keyPressEvent(self, event)

    def keyReleaseEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Space:
            if event.isAutoRepeat():
                event.accept()
                return
            if self._space_pan_state.active:
                self._finish_view_pan()
            self._space_pan_state.release_space()
            self._restore_space_cursor()
            event.accept()
            return
        QGraphicsView.keyReleaseEvent(self, event)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        had_space = self._space_pan_state.space_pressed
        if self._pan_start is not None:
            self._finish_view_pan()
        self._space_pan_state.reset()
        if had_space:
            self._restore_space_cursor()
        QGraphicsView.focusOutEvent(self, event)

    def _restore_space_cursor(self) -> None:
        previous = self._space_previous_cursor
        self._space_previous_cursor = None
        if previous is not None:
            self.viewport().setCursor(previous)
        else:
            self.viewport().unsetCursor()

    def _begin_view_pan(self, event, button) -> None:
        self._pan_start = event.pos()
        self._pan_button = button
        self._pan_previous_drag_mode = self.dragMode()
        self._pan_previous_cursor = self.viewport().cursor()
        self.setDragMode(QGraphicsView.NoDrag)
        self.viewport().setCursor(Qt.ClosedHandCursor)
        event.accept()

    def _finish_view_pan(self) -> None:
        self._pan_start = None
        self._pan_button = None
        if self._pan_previous_drag_mode is not None:
            self.setDragMode(self._pan_previous_drag_mode)
        self._pan_previous_drag_mode = None
        previous = self._pan_previous_cursor
        self._pan_previous_cursor = None
        if previous is not None:
            self.viewport().setCursor(previous)
        else:
            self.viewport().unsetCursor()
        self._space_pan_state.end_left_drag()

    def wheelEvent(self, event) -> None:  # noqa: N802
        factor = 1.14 if event.angleDelta().y() > 0 else 1 / 1.14
        self.scale(factor, factor)
        event.accept()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self._space_pan_state.begin_left_drag():
            self._begin_view_pan(event, Qt.LeftButton)
            return
        if event.button() == Qt.MiddleButton:
            self._begin_view_pan(event, Qt.MiddleButton)
            return
        if event.button() == Qt.LeftButton:
            port = self.port_at_view_position(event.pos())
            if port:
                self._drag_start = port
                point = self.port_scene_position(port) or self.mapToScene(event.pos())
                self._drag_line = self.scene().addPath(QPainterPath(point), QPen(PORT, 2.1, Qt.DashLine))
                self._drag_line.setZValue(50)
                event.accept()
                return
        QGraphicsView.mousePressEvent(self, event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        if self._drag_start and self._drag_line:
            start = self.port_scene_position(self._drag_start) or self.mapToScene(event.pos())
            end = self.mapToScene(event.pos())
            path = QPainterPath(start)
            dx = max(65.0, abs(end.x() - start.x()) * 0.45)
            direction = 1.0 if end.x() >= start.x() else -1.0
            path.cubicTo(start.x() + direction * dx, start.y(), end.x() - direction * dx, end.y(), end.x(), end.y())
            self._drag_line.setPath(path)
            event.accept()
            return
        QGraphicsView.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == self._pan_button and self._pan_start is not None:
            self._finish_view_pan()
            event.accept()
            return
        if event.button() == Qt.LeftButton and self._drag_start:
            start = self._drag_start
            target = self.port_at_view_position(event.pos())
            if self._drag_line:
                self.scene().removeItem(self._drag_line)
            self._drag_line = None
            self._drag_start = None
            if target and (start['table_key'], start['field_name']) != (target['table_key'], target['field_name']):
                self.pairDropped.emit(
                    start['table_key'], start['field_name'], target['table_key'], target['field_name']
                )
                event.accept()
                return
        QGraphicsView.mouseReleaseEvent(self, event)

    def port_scene_position(self, port: dict) -> Optional[QPointF]:
        card = self._cards.get(port.get('table_key') or '')
        if card is None:
            return None
        return card.port_scene_position(port.get('field_name') or '', port.get('side') or 'right')

    def port_at_view_position(self, view_pos) -> Optional[dict]:
        scene_pos = self.mapToScene(view_pos)
        for item in self.scene().items(scene_pos):
            card = item
            while card is not None and not hasattr(card, 'port_at'):
                card = card.parentItem()
            if card is not None and hasattr(card, 'port_at'):
                result = card.port_at(card.mapFromScene(scene_pos))
                if result:
                    return result
        return None
