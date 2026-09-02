from __future__ import annotations

import copy
from typing import List, Optional

from app.relation_keys import build_relation_key

from .draft_panel import DraftPanelMixin
from .draft_store import DraftEntry, DraftStore

from PyQt5.QtWidgets import QAbstractItemView, QInputDialog, QMessageBox


class DraftMixin(DraftPanelMixin):
    draft_relation: Optional[dict]
    draft_pairs: List[dict]
    relations: List[dict]
    pairs_by_relation: dict
    _drafts: DraftStore

    def _setup_draft_panel(self) -> None:
        ui = self.draft_ui
        ui.draft_cardinality_combo.addItems(['one_to_one', 'one_to_many', 'many_to_one', 'many_to_many'])
        ui.draft_join_type_combo.addItems(['LEFT JOIN', 'INNER JOIN', 'RIGHT JOIN', 'FULL JOIN'])
        ui.draft_pairs_grid.setColumnCount(7)
        ui.draft_pairs_grid.setHorizontalHeaderLabels(
            ['№', 'Левая таблица', 'Левое поле', 'Оператор', 'Правая таблица', 'Правое поле', 'Роль']
        )
        ui.draft_pairs_grid.setEditTriggers(QAbstractItemView.NoEditTriggers)
        ui.draft_pairs_grid.itemSelectionChanged.connect(self._update_draft_buttons)
        ui.draft_selector_combo.currentIndexChanged.connect(self._on_draft_selector_changed)
        ui.remove_pair_btn.clicked.connect(self._remove_selected_pair)
        ui.discard_draft_btn.clicked.connect(self._discard_draft)
        ui.apply_draft_btn.clicked.connect(self._apply_draft)
        for editor in (ui.draft_key_edit, ui.draft_name_edit):
            editor.textChanged.connect(self._draft_form_changed)
        ui.draft_cardinality_combo.currentTextChanged.connect(self._draft_form_changed)
        ui.draft_join_type_combo.currentTextChanged.connect(self._draft_form_changed)
        self._refresh_draft_views(update_canvas=False)

    def _relation_between(self, left: str, right: str) -> List[dict]:
        result = []
        for relation in self.relations:
            source = str(relation.get('source_table_key') or '')
            target = str(relation.get('target_table_key') or '')
            if {source, target} == {left, right}:
                result.append(relation)
        return result

    def _sync_active_aliases(self) -> None:
        active = self._drafts.active
        self.draft_relation = active.relation if active is not None else None
        self.draft_pairs = active.pairs if active is not None else []

    @staticmethod
    def _draft_selector_text(entry: DraftEntry) -> str:
        relation = entry.relation
        marker = '* ' if entry.dirty else ''
        key = entry.relation_key or 'без ключа'
        source = str(relation.get('source_table_key') or '?')
        target = str(relation.get('target_table_key') or '?')
        return f'{marker}{key} · {source} → {target} · пар: {len(entry.pairs)}'

    def _refresh_draft_selector(self) -> None:
        combo = self.draft_ui.draft_selector_combo
        old = combo.blockSignals(True)
        try:
            combo.clear()
            active_index = -1
            for index, entry in enumerate(self._drafts.entries):
                combo.addItem(self._draft_selector_text(entry), entry.draft_id)
                if entry.draft_id == self._drafts.active_id:
                    active_index = index
            combo.setCurrentIndex(active_index)
        finally:
            combo.blockSignals(old)

    def _refresh_draft_views(self, *, update_canvas: bool = True) -> None:
        self._sync_active_aliases()
        self._refresh_draft_selector()
        self._populate_draft_panel()
        if update_canvas and hasattr(self, 'canvas'):
            self.canvas.set_drafts(self._drafts.canvas_states(), self._drafts.active_id)

    def _on_draft_selector_changed(self) -> None:
        draft_id = str(self.draft_ui.draft_selector_combo.currentData() or '')
        if not draft_id or draft_id == self._drafts.active_id:
            return
        if self._drafts.set_active(draft_id):
            self._refresh_draft_views()
            self._update_status('Выбран другой локальный черновик.')

    def _choose_draft(self, entries: List[DraftEntry]) -> Optional[DraftEntry]:
        if len(entries) == 1:
            return entries[0]
        labels = [self._draft_selector_text(entry) for entry in entries]
        choice, accepted = QInputDialog.getItem(
            self,
            'Выбор черновика',
            'Для этих таблиц открыто несколько черновиков:',
            labels,
            0,
            False,
        )
        if not accepted:
            return None
        return entries[labels.index(choice)]

    def _start_or_open_draft(self, left: str, right: str) -> bool:
        opened = self._drafts.matching_endpoints(left, right)
        if opened:
            entry = self._choose_draft(opened)
            if entry is None:
                return False
            self._drafts.set_active(entry.draft_id)
            self._refresh_draft_views()
            return True

        existing = self._relation_between(left, right)
        if existing:
            labels = [str(row.get('relation_key') or '?') for row in existing]
            choice, accepted = QInputDialog.getItem(
                self, 'Выбор связи', 'Найдены существующие связи. Выберите редактируемую:', labels, 0, False
            )
            if not accepted:
                return False
            relation = next(row for row in existing if str(row.get('relation_key') or '') == choice)
            pairs = copy.deepcopy(self.pairs_by_relation.get(choice, []))
            baseline = {'relation': copy.deepcopy(relation), 'pairs': copy.deepcopy(pairs)}
            self._drafts.add(
                relation,
                pairs,
                baseline=baseline,
                original_relation_key=choice,
            )
        else:
            key = build_relation_key(left, right)
            self._drafts.add(
                {
                    'relation_key': key,
                    'relation_name': key,
                    'source_table_key': left,
                    'target_table_key': right,
                    'cardinality': 'many_to_one',
                    'join_type': 'LEFT JOIN',
                    'missing_policy': 'none',
                    'on_many_policy': 'error',
                    'select_prefix': '',
                    'is_enabled': 1,
                    'is_generated': 0,
                    'notes': '',
                },
                [],
                baseline=None,
            )
        self._refresh_draft_views()
        return True

    def _on_pair_dropped(self, left_table: str, left_field: str, right_table: str, right_field: str) -> None:
        if not self._start_or_open_draft(left_table, right_table):
            return
        relation = self.draft_relation or {}
        source = str(relation.get('source_table_key') or '')
        if left_table == source:
            pair = {
                'left_table_key': left_table, 'left_field_name': left_field,
                'right_table_key': right_table, 'right_field_name': right_field,
            }
        else:
            pair = {
                'left_table_key': right_table, 'left_field_name': right_field,
                'right_table_key': left_table, 'right_field_name': left_field,
            }
        pair.update({'operator': '=', 'role': 'direct', 'pair_join_type': ''})
        identity = tuple(str(pair.get(key) or '') for key in (
            'left_table_key', 'left_field_name', 'right_table_key', 'right_field_name', 'operator'
        ))
        if any(identity == tuple(str(row.get(key) or '') for key in (
            'left_table_key', 'left_field_name', 'right_table_key', 'right_field_name', 'operator'
        )) for row in self.draft_pairs):
            QMessageBox.information(self, 'Пара уже есть', 'Эта пара полей уже добавлена в активную связь.')
            return
        self.draft_pairs.append(pair)
        active = self._drafts.active
        if active is not None:
            active.touch()
        self._refresh_draft_views()
        self._update_status('Пара добавлена в локальный пакет черновиков.')
