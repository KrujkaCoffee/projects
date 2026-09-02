from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set

from PyQt5.QtCore import QEvent, QPointF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QPainter
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView

from .card_item import TableCardItem
from .graph_model import GraphModelMixin
from .interaction import InteractionMixin
from .palette import CANVAS_BG
from .runtime_bridge import install_relation_map_runtime
from .scene_mixin import SceneMixin
from .space_pan import SpacePanState


class RelationGraphCanvas(InteractionMixin, SceneMixin, GraphModelMixin, QGraphicsView):
    pairDropped = pyqtSignal(str, str, str, str)
    selectedTableChanged = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints() | QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(CANVAS_BG))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setFocusPolicy(Qt.StrongFocus)

        self.tables_by_key: Dict[str, dict] = {}
        self.fields_by_table: Dict[str, List[dict]] = {}
        self.relations: List[dict] = []
        self.pairs_by_relation: Dict[str, List[dict]] = {}
        self.root_key = ''
        self.visible_keys: Set[str] = set()
        self.drafts: List[dict] = []
        self.active_draft_id = ''
        self.draft_relation: Optional[dict] = None
        self.draft_pairs: List[dict] = []
        self._cards: Dict[str, TableCardItem] = {}
        self._lines: List[object] = []
        self._positions: Dict[str, QPointF] = {}
        self._drag_start = None
        self._drag_line = None
        self._pan_start = None
        self._pan_button = None
        self._pan_previous_drag_mode = None
        self._pan_previous_cursor = None
        self._space_previous_cursor = None
        self._space_pan_state = SpacePanState()
        self._suspend_selection = False
        self._scene.selectionChanged.connect(self._selection_changed)
        self._stage2_runtime = install_relation_map_runtime(self)

    def apply_application_theme(self, _theme=None) -> None:
        self.setBackgroundBrush(QBrush(CANVAS_BG))
        for line in self._lines:
            line._style()
        self._scene.update()
        self.viewport().update()

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().changeEvent(event)
        if event.type() in {QEvent.PaletteChange, QEvent.StyleChange}:
            self.apply_application_theme()

    @property
    def visible_table_keys(self) -> Set[str]:
        return set(self.visible_keys)

    @property
    def selected_table_key(self) -> str:
        selected = [item.table_key for item in self._scene.selectedItems() if isinstance(item, TableCardItem)]
        return selected[0] if selected else ''

    def load_graph(
        self,
        tables: List[dict],
        fields_by_table: Dict[str, List[dict]],
        relations: List[dict],
        pairs_by_relation: Dict[str, List[dict]],
        root_table_key: str,
        *,
        draft_relation: Optional[dict] = None,
        draft_pairs: Optional[List[dict]] = None,
        drafts: Optional[List[dict]] = None,
        active_draft_id: str = '',
    ) -> None:
        self.tables_by_key = {str(row.get('table_key') or ''): row for row in tables if row.get('table_key')}
        self.fields_by_table = fields_by_table
        self.relations = relations
        self.pairs_by_relation = pairs_by_relation
        self.root_key = root_table_key or ''
        self.visible_keys = self.connected_component(self.root_key) or ({self.root_key} if self.root_key else set())
        self._assign_drafts(
            drafts
            if drafts is not None
            else ([{'relation': draft_relation, 'pairs': list(draft_pairs or [])}] if draft_relation else []),
            active_draft_id,
        )
        for draft in self.drafts:
            self.visible_keys.update(self.relation_endpoints(draft.get('relation') or {}))
        self.visible_keys.intersection_update(self.tables_by_key)
        self._positions.clear()
        self._rebuild(preserve=False)
        self.auto_layout()
        self.fit_to_content()

    def add_table(self, table_key: str) -> bool:
        return bool(self.add_tables([table_key]))

    def add_tables(self, table_keys: Iterable[str]) -> List[str]:
        added: List[str] = []
        seen: Set[str] = set()
        for value in table_keys:
            key = str(value or '')
            if key in seen or key not in self.tables_by_key or key in self.visible_keys:
                continue
            seen.add(key)
            added.append(key)
        if not added:
            return []

        self.visible_keys.update(added)
        self._rebuild(preserve=True)
        existing = [card.pos().x() for card in self._cards.values() if card.table_key not in seen]
        first_x = max(existing, default=-470.0) + 470.0
        for index, key in enumerate(added):
            point = QPointF(first_x + index * 470.0, 0.0)
            self._cards[key].setPos(point)
            self._positions[key] = QPointF(point)
        self._update_scene_rect()
        return added

    def remove_table(self, table_key: str) -> bool:
        if not table_key or table_key == self.root_key or table_key not in self.visible_keys:
            return False
        self.visible_keys.remove(table_key)
        self._positions.pop(table_key, None)
        self._rebuild(preserve=True)
        return True

    def reset_to_connected_component(self) -> None:
        self.visible_keys = self.connected_component(self.root_key) or ({self.root_key} if self.root_key else set())
        for draft in self.drafts:
            self.visible_keys.update(self.relation_endpoints(draft.get('relation') or {}))
        self._rebuild(preserve=True)
        self.auto_layout()
        self.fit_to_content()

    def set_draft(self, relation: Optional[dict], pairs: Optional[List[dict]]) -> None:
        drafts = [{'relation': relation, 'pairs': list(pairs or [])}] if relation else []
        self.set_drafts(drafts)

    def set_drafts(self, drafts: Optional[List[dict]], active_draft_id: str = '') -> None:
        self._assign_drafts(drafts or [], active_draft_id)
        for draft in self.drafts:
            self.visible_keys.update(self.relation_endpoints(draft.get('relation') or {}))
        self.visible_keys.intersection_update(self.tables_by_key)
        self._rebuild(preserve=True)

    def _assign_drafts(self, drafts: List[dict], active_draft_id: str) -> None:
        self.drafts = []
        for index, draft in enumerate(drafts):
            relation = draft.get('relation') if isinstance(draft, dict) else None
            if not relation:
                continue
            self.drafts.append(
                {
                    'draft_id': str(draft.get('draft_id') or f'draft-{index + 1}'),
                    'relation': relation,
                    'pairs': list(draft.get('pairs') or []),
                }
            )
        ids = {draft['draft_id'] for draft in self.drafts}
        self.active_draft_id = active_draft_id if active_draft_id in ids else (
            self.drafts[0]['draft_id'] if self.drafts else ''
        )
        active = next(
            (draft for draft in self.drafts if draft['draft_id'] == self.active_draft_id),
            None,
        )
        self.draft_relation = active.get('relation') if active else None
        self.draft_pairs = list(active.get('pairs') or []) if active else []

    def auto_layout(self) -> None:
        for key, point in self.layout_positions().items():
            card = self._cards.get(key)
            if card:
                card.setPos(point)
                self._positions[key] = QPointF(point)
        self._update_lines()
        self._update_scene_rect()

    def fit_to_content(self) -> None:
        rect = self._scene.itemsBoundingRect().adjusted(-70, -70, 70, 70)
        if rect.isValid() and not rect.isNull():
            self.fitInView(rect, Qt.KeepAspectRatio)

    def reset_zoom(self) -> None:
        self.resetTransform()
