from __future__ import annotations

import copy
from typing import Dict, List, Optional

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget

from app.ui_loader import load_ui

from .canvas import RelationGraphCanvas
from .draft import DraftMixin
from .draft_store import DraftStore
from .table_picker import RelationTablePickerDialog


class FullRelationMapDialog(DraftMixin, QDialog):
    """Full-screen graph editor that never writes to the database directly."""

    def __init__(
        self,
        parent,
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
        super().__init__(parent)
        load_ui('relation_map_dialog.ui', self)
        self.tables = tables
        self.fields_by_table = fields_by_table
        self.relations = relations
        self.pairs_by_relation = pairs_by_relation
        self.root_table_key = root_table_key
        self._had_initial_drafts = bool(drafts or draft_relation)
        self._drafts = DraftStore(copy.deepcopy(drafts or []))
        if not self._drafts.entries and draft_relation:
            self._drafts.add(
                copy.deepcopy(draft_relation),
                copy.deepcopy(draft_pairs or []),
                baseline=None,
            )
        if active_draft_id:
            self._drafts.set_active(active_draft_id)
        self._sync_active_aliases()
        self.applied_relation: Optional[dict] = None
        self.applied_pairs: List[dict] = []
        self.applied_drafts: List[dict] = []
        self.applied_active_draft_id = ''
        self.applied_cleared = False
        self._loading_draft = False
        self._accepting_draft = False

        self.canvas = RelationGraphCanvas(self)
        self.canvas_container_layout.addWidget(self.canvas)
        self.draft_ui = QWidget(self)
        load_ui('relation_draft_panel.ui', self.draft_ui)
        self.draft_container_layout.addWidget(self.draft_ui)
        self.map_splitter.setSizes([1220, 420])
        self.root_table_label.setText(root_table_key or '—')

        self.canvas.pairDropped.connect(self._on_pair_dropped)
        self.canvas.selectedTableChanged.connect(self._on_selected_table_changed)
        self.add_table_btn.clicked.connect(self._add_table)
        self.remove_table_btn.clicked.connect(self._remove_selected_table)
        self.reset_component_btn.clicked.connect(self._reset_component)
        self.auto_layout_btn.clicked.connect(self.canvas.auto_layout)
        self.fit_btn.clicked.connect(self.canvas.fit_to_content)
        self.reset_zoom_btn.clicked.connect(self.canvas.reset_zoom)
        self.close_btn.clicked.connect(self.reject)
        self._setup_draft_panel()
        self.canvas.load_graph(
            tables,
            fields_by_table,
            relations,
            pairs_by_relation,
            root_table_key,
            drafts=self._drafts.canvas_states(),
            active_draft_id=self._drafts.active_id,
        )
        self._update_status()
        QTimer.singleShot(0, self.canvas.fit_to_content)

    def _add_table(self) -> None:
        dialog = RelationTablePickerDialog(
            self,
            self.tables,
            self.fields_by_table,
            self.relations,
            self.canvas.visible_table_keys,
        )
        if dialog.exec_() != dialog.Accepted:
            return
        added = self.canvas.add_tables(dialog.selected_table_keys)
        if added:
            names = ', '.join(added)
            self._update_status(f'Добавлено таблиц: {len(added)} ({names}).')

    def _remove_selected_table(self) -> None:
        key = self.canvas.selected_table_key
        if not key:
            return
        used_by = [
            entry.relation_key or 'без ключа'
            for entry in self._drafts.entries
            if key in entry.endpoints
        ]
        if used_by:
            QMessageBox.warning(
                self,
                'Таблица используется',
                f'Нельзя убрать таблицу из черновиков: {", ".join(used_by)}.',
            )
            return
        if self.canvas.remove_table(key):
            self._update_status(f'Таблица {key} убрана с поля. Данные БД не изменены.')

    def _reset_component(self) -> None:
        self.canvas.reset_to_connected_component()
        self._update_status('Восстановлен полный связный компонент базовой таблицы.')

    def _on_selected_table_changed(self, key: str) -> None:
        self.remove_table_btn.setEnabled(bool(key and key != self.root_table_key))

    def _update_status(self, message: str = '') -> None:
        visible = self.canvas.visible_table_keys if hasattr(self, 'canvas') else set()
        relation_count = sum(
            1
            for relation in self.relations
            if set(self.canvas.relation_endpoints(relation)).issubset(visible)
        ) if hasattr(self, 'canvas') else 0
        drafts = self._drafts.entries if hasattr(self, '_drafts') else ()
        dirty_count = len(self._drafts.dirty_entries) if hasattr(self, '_drafts') else 0
        draft = f' · локальных черновиков: {len(drafts)} · изменено: {dirty_count}' if drafts else ''
        base = f'Таблиц на поле: {len(visible)} · сохранённых связей внутри поля: {relation_count}{draft}'
        self.map_status_label.setText(f'{message}\n{base}' if message else base)

    def reject(self) -> None:
        if (self._drafts.is_dirty or self._had_initial_drafts) and not self._accepting_draft:
            if not self._confirm_discard('Закрыть карту и потерять весь локальный пакет черновиков?'):
                return
        super().reject()
