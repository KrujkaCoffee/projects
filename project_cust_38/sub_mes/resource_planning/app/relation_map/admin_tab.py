from __future__ import annotations

from typing import Dict, List

from PyQt5.QtWidgets import QLabel, QPushButton

from app.db import DbError
from app.edit_state import DirtyTracker, QtEditStateBinder, resolve_pending_changes
from app.relation_contract import (
    SUPPORTED_CARDINALITIES,
    SUPPORTED_JOIN_TYPES,
    SUPPORTED_MISSING_POLICIES,
    SUPPORTED_ON_MANY_POLICIES,
    validate_relation_contract,
)
from app.relation_persistence import persist_relation_batch
from app.ui_helpers import info, to_int_bool, warn
from app.widgets.admin_tab import AdminMetadataTab

from .admin_filter import AdminFilterLayoutMixin
from .dialog import FullRelationMapDialog
from .draft_store import DraftStore


class EnhancedAdminMetadataTab(AdminFilterLayoutMixin, AdminMetadataTab):
    """Production layout with a full-screen relation graph and local drafts."""

    def __init__(self, db, dsn_provider, parent=None) -> None:
        self._relation_dirty_tracker = DirtyTracker()
        self._relation_batch_store = DraftStore()
        self._relation_edit_binder = None
        self._relation_validation_label = None
        self.cancel_relation_changes_btn = None
        super().__init__(db, dsn_provider, parent)
        self._configure_relation_contract_choices()
        self._install_relation_edit_state()
        self._set_relation_dirty(False)

    @staticmethod
    def _set_combo_values(combo, supported, experimental) -> None:
        current = combo.currentText()
        values = list(dict.fromkeys([*supported, *experimental]))
        old_blocked = combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItems(values)
            if current in values:
                combo.setCurrentText(current)
        finally:
            combo.blockSignals(old_blocked)

    def _configure_relation_contract_choices(self) -> None:
        old = self._loading
        self._loading = True
        try:
            self._set_combo_values(self.rel_cardinality, SUPPORTED_CARDINALITIES, ('many_to_many',))
            self._set_combo_values(
                self.rel_join_type,
                SUPPORTED_JOIN_TYPES,
                ('RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN'),
            )
            self._set_combo_values(
                self.rel_missing_policy,
                SUPPORTED_MISSING_POLICIES,
                ('allow', 'warn', 'error', 'drop_row'),
            )
            self._set_combo_values(
                self.rel_on_many_policy,
                SUPPORTED_ON_MANY_POLICIES,
                ('aggregate', 'allow', 'warn'),
            )
        finally:
            self._loading = old
        hint = (
            'Первые значения исполняются текущим ORM. Экспериментальное значение '
            'можно сохранить только у выключенной связи.'
        )
        for combo in (
            self.rel_cardinality,
            self.rel_join_type,
            self.rel_missing_policy,
            self.rel_on_many_policy,
        ):
            combo.setToolTip(hint)

    def apply_application_theme(self, _theme=None) -> None:
        if self._relation_edit_binder is None:
            return
        state = self._relation_edit_state()
        self._relation_edit_binder.refresh(
            self._relation_dirty_tracker.baseline or state,
            self._relation_dirty_tracker.current or state,
        )

    def _install_relation_edit_state(self) -> None:
        self.cancel_relation_changes_btn = QPushButton('↶ Отменить изменения', self)
        save_index = self.pair_toolbar.indexOf(self.save_relation_btn)
        self.pair_toolbar.insertWidget(save_index + 1, self.cancel_relation_changes_btn)
        self.cancel_relation_changes_btn.clicked.connect(self.cancel_relation_changes)

        self._relation_validation_label = QLabel(self)
        self._relation_validation_label.setObjectName('relation_contract_status_label')
        self._relation_validation_label.setWordWrap(True)
        pairs_index = self.relation_editor_layout.indexOf(self.pairs_grid)
        self.relation_editor_layout.insertWidget(pairs_index, self._relation_validation_label)

        widgets = {
            'relation_key': self.rel_key,
            'relation_name': self.rel_name,
            'source_table_key': self.rel_source,
            'target_table_key': self.rel_target,
            'cardinality': self.rel_cardinality,
            'join_type': self.rel_join_type,
            'missing_policy': self.rel_missing_policy,
            'on_many_policy': self.rel_on_many_policy,
            'select_prefix': self.rel_select_prefix,
            'is_enabled': self.rel_enabled,
            'is_generated': self.rel_generated,
            'notes': self.rel_notes,
        }
        self._relation_edit_binder = QtEditStateBinder(widgets, self.pairs_grid, self.PAIR_COLUMNS)

    def _raw_pairs_from_grid(self) -> List[dict]:
        pairs: List[dict] = []
        for row in range(self.pairs_grid.rowCount()):
            pair = {'pair_no': row}
            for column, field in enumerate(self.PAIR_COLUMNS):
                if field == 'pair_no':
                    continue
                item = self.pairs_grid.item(row, column)
                pair[field] = item.text() if item is not None else ''
            pairs.append(pair)
        return pairs

    def _relation_edit_state(self) -> dict:
        relation = {
            'relation_key': self.rel_key.text().strip(),
            'relation_name': self.rel_name.text().strip(),
            'source_table_key': self.rel_source.currentText().strip(),
            'target_table_key': self.rel_target.currentText().strip(),
            'cardinality': self.rel_cardinality.currentText().strip(),
            'join_type': self.rel_join_type.currentText().strip(),
            'missing_policy': self.rel_missing_policy.currentText().strip(),
            'on_many_policy': self.rel_on_many_policy.currentText().strip(),
            'select_prefix': self.rel_select_prefix.text().strip(),
            'is_enabled': 1 if self.rel_enabled.isChecked() else 0,
            'is_generated': 1 if self.rel_generated.isChecked() else 0,
            'notes': self.rel_notes.toPlainText(),
        }
        return {'relation': relation, 'pairs': self._raw_pairs_from_grid()}

    def _apply_relation_edit_state(self, state: dict) -> None:
        relation = state.get('relation') or {}
        old = self._loading
        self._loading = True
        try:
            self.rel_key.setText(str(relation.get('relation_key') or ''))
            self.rel_name.setText(str(relation.get('relation_name') or ''))
            self.rel_source.setCurrentText(str(relation.get('source_table_key') or ''))
            self.rel_target.setCurrentText(str(relation.get('target_table_key') or ''))
            self.rel_cardinality.setCurrentText(str(relation.get('cardinality') or 'many_to_one'))
            self.rel_join_type.setCurrentText(str(relation.get('join_type') or 'LEFT JOIN'))
            self.rel_missing_policy.setCurrentText(str(relation.get('missing_policy') or 'none'))
            self.rel_on_many_policy.setCurrentText(str(relation.get('on_many_policy') or 'error'))
            self.rel_select_prefix.setText(str(relation.get('select_prefix') or ''))
            self.rel_enabled.setChecked(to_int_bool(relation.get('is_enabled', 1)))
            self.rel_generated.setChecked(to_int_bool(relation.get('is_generated', 0)))
            self.rel_notes.setPlainText(str(relation.get('notes') or ''))
            self._populate_pairs_grid(list(state.get('pairs') or []))
        finally:
            self._loading = old

    def _sync_active_batch_draft(self) -> None:
        if self._loading or self._relation_batch_store.active is None:
            return
        state = self._relation_edit_state()
        self._relation_batch_store.update_active(state['relation'], state['pairs'])

    def _relation_batch_validation(self):
        entries = self._relation_batch_store.dirty_entries
        duplicates = self._relation_batch_store.duplicate_relation_keys()
        validations = [
            (entry, validate_relation_contract(entry.relation, entry.pairs))
            for entry in entries
        ]
        return entries, duplicates, validations

    @staticmethod
    def _batch_validation_message(duplicates, validations) -> str:
        messages = []
        if duplicates:
            messages.append(f'Повторяются relation_key: {", ".join(duplicates)}.')
        for entry, result in validations:
            if result.issues:
                messages.append(f'{entry.relation_key or "без ключа"}:\n{result.message()}')
        return '\n\n'.join(messages)

    def _set_relation_dirty(self, dirty: bool, redraw: bool = False) -> None:
        if dirty:
            self._sync_active_batch_draft()
        state = self._relation_edit_state()
        if dirty:
            self._relation_dirty_tracker.update(state)
        else:
            self._relation_dirty_tracker.capture(state)
        validation = validate_relation_contract(state['relation'], state['pairs'])
        batch_entries, duplicates, batch_validations = self._relation_batch_validation()
        batch_pending = bool(batch_entries)
        self._relation_dirty = self._relation_dirty_tracker.is_dirty or batch_pending
        if batch_pending:
            can_save = not duplicates and all(result.valid for _, result in batch_validations)
            batch_errors = bool(duplicates or any(result.errors for _, result in batch_validations))
            batch_warnings = any(result.warnings for _, result in batch_validations)
            validation_message = self._batch_validation_message(duplicates, batch_validations)
        else:
            can_save = validation.valid
            batch_errors = False
            batch_warnings = False
            validation_message = validation.message()

        if hasattr(self, 'save_relation_btn'):
            suffix = ' *' if self._relation_dirty else ''
            if batch_pending:
                self.save_relation_btn.setText(f'💾 Сохранить пакет ({len(batch_entries)}){suffix}')
            else:
                self.save_relation_btn.setText(f'💾 Сохранить связь и пары{suffix}')
            self.save_relation_btn.setEnabled(self._relation_dirty and can_save)
        if hasattr(self, 'delete_relation_btn'):
            self.delete_relation_btn.setEnabled(
                not self._relation_dirty and bool(state['relation'].get('relation_key'))
            )
        if self.cancel_relation_changes_btn is not None:
            self.cancel_relation_changes_btn.setEnabled(self._relation_dirty)
        if self._relation_validation_label is not None:
            blank_clean = not self._relation_dirty and not state['relation'].get('relation_key')
            if blank_clean:
                self._relation_validation_label.setText('Нет неприменённых изменений связи.')
                self._relation_validation_label.setProperty('state', 'clean')
            elif batch_errors or (not batch_pending and validation.errors):
                self._relation_validation_label.setText('⛔ ' + validation_message)
                self._relation_validation_label.setProperty('state', 'error')
            elif batch_warnings or (not batch_pending and validation.warnings):
                self._relation_validation_label.setText('⚠ ' + validation_message)
                self._relation_validation_label.setProperty('state', 'warning')
            elif self._relation_dirty:
                if batch_pending:
                    self._relation_validation_label.setText(
                        f'✓ Пакет из {len(batch_entries)} связей соответствует контракту ORM.'
                    )
                else:
                    self._relation_validation_label.setText('✓ Изменения соответствуют контракту ORM.')
                self._relation_validation_label.setProperty('state', 'valid')
            else:
                self._relation_validation_label.setText('Нет неприменённых изменений связи.')
                self._relation_validation_label.setProperty('state', 'clean')
            style = self._relation_validation_label.style()
            style.unpolish(self._relation_validation_label)
            style.polish(self._relation_validation_label)
        if self._relation_edit_binder is not None:
            self._relation_edit_binder.refresh(
                self._relation_dirty_tracker.baseline or state,
                self._relation_dirty_tracker.current or state,
            )
        if redraw and hasattr(self, 'canvas'):
            self.redraw_canvas()

    def cancel_relation_changes(self) -> None:
        if not self.has_pending_changes():
            return
        self._relation_batch_store.clear()
        state = self._relation_dirty_tracker.restore()
        self._apply_relation_edit_state(state)
        self._set_relation_dirty(False, redraw=True)
        self._update_relation_map_status('Изменения связи отменены.')
        self._refresh_relation_map_dialog()

    def has_pending_changes(self) -> bool:
        return self._relation_dirty_tracker.is_dirty or self._relation_batch_store.is_dirty

    def resolve_pending_relation_changes(self, message: str) -> bool:
        if not self.has_pending_changes():
            return True
        return resolve_pending_changes(
            self,
            save=self.save_relation,
            discard=self.cancel_relation_changes,
            message=message,
        )

    def save_relation(self) -> bool:
        self._sync_active_batch_draft()
        batch_entries, duplicates, batch_validations = self._relation_batch_validation()
        if batch_entries:
            invalid = [(entry, result) for entry, result in batch_validations if not result.valid]
            if duplicates or invalid:
                self._set_relation_dirty(True)
                warn(
                    self,
                    self._batch_validation_message(duplicates, batch_validations),
                    'Пакет связей не соответствует контракту ORM',
                )
                return False
            if not self.require_connection():
                return False
            ordered_entries = sorted(batch_entries, key=lambda entry: entry.relation_key)
            drafts = [entry.package() for entry in ordered_entries]
            keys = [entry.relation_key for entry in ordered_entries]
            try:
                with self.db.transaction() as cur:
                    persist_relation_batch(cur, drafts)
            except Exception as exc:
                self._set_relation_dirty(True)
                warn(self, str(exc), 'Ошибка пакетного сохранения связей')
                return False

            self._relation_batch_store.clear()
            self._set_relation_dirty(False)
            self.load_relations()
            info(self, f'Атомарно сохранено связей: {len(keys)} ({", ".join(keys)})')
            return True

        state = self._relation_edit_state()
        validation = validate_relation_contract(state['relation'], state['pairs'])
        if not validation.valid:
            self._set_relation_dirty(True)
            warn(self, validation.message(), 'Связь не соответствует контракту ORM')
            return False
        return bool(super().save_relation())

    def reload_all(self) -> None:
        if self.has_pending_changes() and not self.resolve_pending_relation_changes(
            'Перед перезагрузкой метаданных сохраните или отмените изменения связи.'
        ):
            return
        super().reload_all()

    def open_physical_tables_editor(
        self,
        selected_table_key: str = '',
        *,
        start_new: bool = False,
    ) -> bool:
        if self.has_pending_changes() and not self.resolve_pending_relation_changes(
            'Перед редактированием реестра таблиц сохраните или отмените изменения связи.'
        ):
            return False
        return bool(
            super().open_physical_tables_editor(
                selected_table_key,
                start_new=start_new,
            )
        )

    def load_relations(self) -> None:
        if self.has_pending_changes() and not self.resolve_pending_relation_changes(
            'Перед перезагрузкой списка связей сохраните или отмените текущие изменения.'
        ):
            return
        super().load_relations()

    def _on_selected_table_changed(self) -> None:
        if self._loading:
            return
        selected = self.current_table_key()
        previous = self._last_selected_table_key
        if previous and selected != previous and self.has_pending_changes():
            if not self.resolve_pending_relation_changes(
                'Перед переходом к другой таблице сохраните или отмените изменения текущей связи.'
            ):
                old = self._loading
                self._loading = True
                try:
                    self._select_table_key(previous)
                finally:
                    self._loading = old
                return
        super()._on_selected_table_changed()

    def _on_selected_relation_changed(self) -> None:
        if self._loading:
            return
        row = self.relations_grid.currentRow()
        target = ''
        if row >= 0:
            item = self.relations_grid.item(row, self.RELATION_GRID_COLUMNS.index('relation_key'))
            target = item.text().strip() if item is not None else ''
        baseline = self._relation_dirty_tracker.baseline or {}
        current_context = str((baseline.get('relation') or {}).get('relation_key') or '')
        if self.has_pending_changes():
            if target == current_context:
                return
            if not self.resolve_pending_relation_changes(
                'Перед выбором другой связи сохраните или отмените текущие изменения.'
            ):
                if current_context:
                    old = self._loading
                    self._loading = True
                    try:
                        key_column = self.RELATION_GRID_COLUMNS.index('relation_key')
                        restored = False
                        for candidate_row in range(self.relations_grid.rowCount()):
                            candidate = self.relations_grid.item(candidate_row, key_column)
                            if candidate is not None and candidate.text() == current_context:
                                self.relations_grid.selectRow(candidate_row)
                                restored = True
                                break
                        if not restored:
                            self.relations_grid.clearSelection()
                            self.relations_grid.setCurrentCell(-1, -1)
                    finally:
                        self._loading = old
                return
            if target:
                self._select_relation_key(target)
            else:
                self._clear_relation_form()
            return
        super()._on_selected_relation_changed()

    def add_relation(self) -> None:
        self.open_relation_map()

    def _load_full_graph_data(self) -> tuple[List[dict], Dict[str, List[dict]]]:
        relations = self.db.fetchall(
            """
            SELECT relation_key, relation_name, source_table_key, target_table_key,
                   cardinality, join_type, missing_policy, on_many_policy, select_prefix,
                   is_enabled, is_generated, notes, updated_at
            FROM public.admin_table_relations
            ORDER BY source_table_key, target_table_key, relation_key
            """
        )
        pairs: Dict[str, List[dict]] = {}
        rows = self.db.fetchall(
            """
            SELECT relation_key, pair_no, left_table_key, left_field_name,
                   right_table_key, right_field_name, role, operator, pair_join_type
            FROM public.admin_relation_field_pairs
            ORDER BY relation_key, pair_no
            """
        )
        for row in rows:
            pairs.setdefault(str(row.get('relation_key') or ''), []).append(row)
        return relations, pairs

    def open_relation_map(self) -> None:
        selected = self.current_table_key()
        if not selected:
            warn(self, 'Сначала выберите физическую таблицу')
            return
        if not self.require_connection():
            return
        try:
            relations, pairs = self._load_full_graph_data()
        except DbError as exc:
            warn(self, str(exc), 'Ошибка загрузки полного графа')
            return
        self._sync_active_batch_draft()
        initial_drafts = self._relation_batch_store.packages()
        active_draft_id = self._relation_batch_store.active_id
        if not initial_drafts and self._relation_dirty_tracker.is_dirty:
            state = self._relation_edit_state()
            baseline = self._relation_dirty_tracker.baseline
            baseline_relation = (baseline or {}).get('relation') or {}
            current_relation = state['relation']
            same_endpoints = {
                str(baseline_relation.get('source_table_key') or ''),
                str(baseline_relation.get('target_table_key') or ''),
            } == {
                str(current_relation.get('source_table_key') or ''),
                str(current_relation.get('target_table_key') or ''),
            }
            initial_drafts = [
                {
                    'draft_id': 'draft-1',
                    'relation': current_relation,
                    'pairs': state['pairs'],
                    'baseline': baseline,
                    'original_relation_key': (
                        str(baseline_relation.get('relation_key') or '') if same_endpoints else ''
                    ),
                }
            ]
            active_draft_id = 'draft-1'
        dialog = FullRelationMapDialog(
            self,
            self._tables_cache,
            self._fields_cache,
            relations,
            pairs,
            selected,
            drafts=initial_drafts,
            active_draft_id=active_draft_id,
        )
        self._relation_map_dialog = dialog
        if dialog.exec_() != dialog.Accepted:
            self._relation_map_dialog = None
            return
        self._relation_map_dialog = None
        if dialog.applied_cleared:
            self.cancel_relation_changes()
            return
        if not dialog.applied_drafts:
            return
        self._relation_batch_store = DraftStore(dialog.applied_drafts)
        self._relation_batch_store.set_active(dialog.applied_active_draft_id)
        active = self._relation_batch_store.active
        if active is not None:
            self._apply_map_draft(active.relation, active.pairs)

    def _apply_map_draft(self, relation: dict, pairs: List[dict]) -> None:
        source = str(relation.get('source_table_key') or '')
        target = str(relation.get('target_table_key') or '')
        old = self._loading
        self._loading = True
        try:
            self.rel_key.setText(str(relation.get('relation_key') or ''))
            self.rel_name.setText(str(relation.get('relation_name') or relation.get('relation_key') or ''))
            self.rel_source.setCurrentText(source)
            self.rel_target.setCurrentText(target)
            self.rel_cardinality.setCurrentText(str(relation.get('cardinality') or 'many_to_one'))
            self.rel_join_type.setCurrentText(str(relation.get('join_type') or 'LEFT JOIN'))
            self.rel_missing_policy.setCurrentText(str(relation.get('missing_policy') or 'none'))
            self.rel_on_many_policy.setCurrentText(str(relation.get('on_many_policy') or 'error'))
            self.rel_select_prefix.setText(str(relation.get('select_prefix') or ''))
            self.rel_enabled.setChecked(to_int_bool(relation.get('is_enabled', 1)))
            self.rel_generated.setChecked(to_int_bool(relation.get('is_generated', 0)))
            self.rel_notes.setPlainText(str(relation.get('notes') or ''))
            self._populate_pairs_grid(pairs)
            peer = target if source == self.current_table_key() else source
            self._set_relation_peer_combo(peer, redraw=False)
            self.right_tabs.setCurrentWidget(self.relations_tab)
        finally:
            self._loading = old
        self._set_relation_dirty(True)
