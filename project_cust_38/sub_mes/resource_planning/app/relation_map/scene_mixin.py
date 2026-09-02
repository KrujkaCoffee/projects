from __future__ import annotations

import math
from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen

from .card_item import TableCardItem
from .line_item import RelationLineItem
from .palette import GRID


class SceneMixin:
    def _rebuild(self, *, preserve: bool) -> None:
        if preserve:
            self._positions.update({key: QPointF(card.pos()) for key, card in self._cards.items()})
        self._suspend_selection = True
        self._cards.clear()
        self._lines.clear()
        self._scene.clear()
        for key in sorted(self.visible_keys):
            card = TableCardItem(
                self.tables_by_key[key],
                self.fields_by_table.get(key, []),
                is_root=(key == self.root_key),
                on_moved=self._card_moved,
            )
            self._scene.addItem(card)
            self._cards[key] = card
            if key in self._positions:
                card.setPos(self._positions[key])
        self._suspend_selection = False
        self._rebuild_lines()
        self._update_scene_rect()

    def _rebuild_lines(self) -> None:
        for line in self._lines:
            if line.scene() is self._scene:
                self._scene.removeItem(line)
        self._lines.clear()
        drafts = list(getattr(self, 'drafts', []) or [])
        for relation in self.relations:
            endpoints = set(self.relation_endpoints(relation))
            if not endpoints.issubset(self.visible_keys):
                continue
            key = str(relation.get('relation_key') or '')
            replaced_by_draft = any(
                key
                and key == str(
                    (draft.get('relation') or {}).get('_original_relation_key')
                    or (draft.get('relation') or {}).get('relation_key')
                    or ''
                )
                and endpoints == set(self.relation_endpoints(draft.get('relation') or {}))
                for draft in drafts
            )
            if replaced_by_draft:
                continue
            for index, pair in enumerate(self.pairs_by_relation.get(key, [])):
                self._add_line(relation, pair, saved=True, index=index)
        for draft in drafts:
            relation = draft.get('relation') or {}
            for index, pair in enumerate(draft.get('pairs') or []):
                self._add_line(relation, pair, saved=False, index=index)

    def _add_line(self, relation: dict, pair: dict, *, saved: bool, index: int) -> None:
        line = RelationLineItem(relation, pair, self.connection_path, saved=saved, index=index)
        self._scene.addItem(line)
        self._lines.append(line)

    def _card_moved(self, card: TableCardItem) -> None:
        if card.table_key in self._cards:
            self._positions[card.table_key] = QPointF(card.pos())
            runtime = getattr(self, '_stage2_runtime', None)
            if runtime is not None:
                runtime.card_moved(card)
            else:
                self._update_lines()

    def _update_lines(self) -> None:
        runtime = getattr(self, '_stage2_runtime', None)
        if runtime is not None:
            runtime.refresh_all()
            return
        for line in self._lines:
            line.update_path()

    def _update_scene_rect(self) -> None:
        runtime = getattr(self, '_stage2_runtime', None)
        if runtime is not None:
            runtime.expand_workspace()
            return
        rect = self._scene.itemsBoundingRect().adjusted(-160, -130, 160, 130)
        self._scene.setSceneRect(rect if rect.isValid() else QRectF(-500, -400, 1000, 800))

    def _selection_changed(self) -> None:
        if not self._suspend_selection:
            self.selectedTableChanged.emit(self.selected_table_key)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        super().drawBackground(painter, rect)
        step = 32.0
        left = math.floor(rect.left() / step) * step
        top = math.floor(rect.top() / step) * step
        painter.setPen(QPen(GRID, 0.55))
        x = left
        while x < rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += step
        y = top
        while y < rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += step
