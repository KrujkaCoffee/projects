from __future__ import annotations

import copy

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem

from app.relation_contract import validate_relation_contract


class DraftPanelMixin:
    def _populate_draft_panel(self) -> None:
        ui = self.draft_ui
        self._loading_draft = True
        try:
            active = self.draft_relation is not None
            ui.draft_box.setEnabled(True)
            for editor in (
                ui.draft_key_edit,
                ui.draft_name_edit,
                ui.draft_cardinality_combo,
                ui.draft_join_type_combo,
                ui.draft_pairs_grid,
            ):
                editor.setEnabled(active)
            relation = self.draft_relation or {}
            ui.draft_key_edit.setText(str(relation.get('relation_key') or ''))
            ui.draft_name_edit.setText(str(relation.get('relation_name') or ''))
            ui.draft_source_label.setText(str(relation.get('source_table_key') or '—'))
            ui.draft_target_label.setText(str(relation.get('target_table_key') or '—'))
            ui.draft_cardinality_combo.setCurrentText(str(relation.get('cardinality') or 'many_to_one'))
            ui.draft_join_type_combo.setCurrentText(str(relation.get('join_type') or 'LEFT JOIN'))
            entry = self._drafts.active
            ui.draft_key_edit.setReadOnly(bool(entry and entry.original_relation_key))
            grid = ui.draft_pairs_grid
            grid.setRowCount(len(self.draft_pairs))
            keys = ('pair_no', 'left_table_key', 'left_field_name', 'operator', 'right_table_key', 'right_field_name', 'role')
            for row_no, pair in enumerate(self.draft_pairs):
                values = {'pair_no': row_no, **pair}
                for column, key in enumerate(keys):
                    item = QTableWidgetItem(str(values.get(key) or ''))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    grid.setItem(row_no, column, item)
            grid.resizeColumnsToContents()
        finally:
            self._loading_draft = False
        self._update_draft_buttons()

    def _draft_form_changed(self) -> None:
        if self._loading_draft or not self.draft_relation:
            return
        ui = self.draft_ui
        self.draft_relation['relation_key'] = ui.draft_key_edit.text().strip()
        self.draft_relation['relation_name'] = ui.draft_name_edit.text().strip()
        self.draft_relation['cardinality'] = ui.draft_cardinality_combo.currentText()
        self.draft_relation['join_type'] = ui.draft_join_type_combo.currentText()
        active = self._drafts.active
        if active is not None:
            active.touch()
        self._sync_active_aliases()
        self._refresh_draft_selector()
        self.canvas.set_drafts(self._drafts.canvas_states(), self._drafts.active_id)
        self._update_draft_buttons()
        self._update_status()

    def _remove_selected_pair(self) -> None:
        row = self.draft_ui.draft_pairs_grid.currentRow()
        if 0 <= row < len(self.draft_pairs):
            self.draft_pairs.pop(row)
            active = self._drafts.active
            if active is not None:
                active.touch()
            self._refresh_draft_views()

    def _discard_draft(self) -> None:
        active = self._drafts.active
        if active is None:
            return
        if active.dirty and not self._confirm_discard('Сбросить выбранный черновик?', dirty=True):
            return
        removed = self._drafts.remove_active()
        self._refresh_draft_views()
        key = removed.relation_key if removed is not None else 'черновик'
        self._update_status(f'Черновик {key} сброшен.')

    def _clear_draft(self) -> None:
        self._drafts.clear()
        self._refresh_draft_views()

    def _confirm_discard(self, text: str, *, dirty: bool | None = None) -> bool:
        changed = self._drafts.is_dirty if dirty is None else dirty
        if not changed:
            return True
        return QMessageBox.question(
            self, 'Несохранённые черновики', text,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) == QMessageBox.Yes

    def _batch_validation(self):
        entries = self._drafts.dirty_entries
        duplicates = self._drafts.duplicate_relation_keys()
        validations = [
            (entry, validate_relation_contract(entry.relation, entry.pairs))
            for entry in entries
        ]
        return entries, duplicates, validations

    def _update_draft_buttons(self) -> None:
        ui = self.draft_ui
        active = self.draft_relation is not None
        ui.remove_pair_btn.setEnabled(active and ui.draft_pairs_grid.currentRow() >= 0)
        ui.discard_draft_btn.setEnabled(active)
        entries, duplicates, validations = self._batch_validation()
        clear_initial = bool(getattr(self, '_had_initial_drafts', False) and not entries)
        valid = bool(
            clear_initial
            or (entries and not duplicates and all(result.valid for _, result in validations))
        )
        ui.apply_draft_btn.setEnabled(valid)
        if clear_initial:
            ui.apply_draft_btn.setText('✓ Отменить неприменённый пакет')
        else:
            ui.apply_draft_btn.setText(f'✓ Применить пакет ({len(entries)}) в основную панель')

        total = len(self._drafts.entries)
        if not total:
            ui.draft_summary_label.setText('Черновиков нет. Соедините поля двух таблиц на карте.')
        elif duplicates:
            ui.draft_summary_label.setText(
                f'⛔ Повторяются ключи связей: {", ".join(duplicates)}.'
            )
        else:
            invalid = [entry.relation_key or 'без ключа' for entry, result in validations if not result.valid]
            if invalid:
                ui.draft_summary_label.setText(
                    f'⛔ Некорректные черновики: {", ".join(invalid)}. '
                    f'Всего открыто: {total}; изменено: {len(entries)}.'
                )
            else:
                ui.draft_summary_label.setText(
                    f'Открыто: {total}; к применению: {len(entries)}. '
                    'Все линии остаются локальными до пакетного сохранения.'
                )

    def _apply_draft(self) -> None:
        if self.draft_relation:
            self._draft_form_changed()
        entries, duplicates, validations = self._batch_validation()
        if not entries and getattr(self, '_had_initial_drafts', False):
            self.applied_drafts = []
            self.applied_active_draft_id = ''
            self.applied_relation = None
            self.applied_pairs = []
            self.applied_cleared = True
            self._accepting_draft = True
            self.accept()
            return
        if duplicates:
            QMessageBox.warning(
                self,
                'Повторяющиеся ключи',
                f'Каждой связи нужен отдельный relation_key: {", ".join(duplicates)}.',
            )
            return
        invalid = [(entry, result) for entry, result in validations if not result.valid]
        if not entries or invalid:
            details = '\n\n'.join(
                f'{entry.relation_key or "без ключа"}:\n{result.message()}'
                for entry, result in invalid
            ) or 'Нет изменённых черновиков для применения.'
            QMessageBox.warning(self, 'Пакет не готов', details)
            return

        self.applied_drafts = self._drafts.packages(dirty_only=True)
        ids = {package['draft_id'] for package in self.applied_drafts}
        self.applied_active_draft_id = (
            self._drafts.active_id
            if self._drafts.active_id in ids
            else self.applied_drafts[0]['draft_id']
        )
        active = next(
            package
            for package in self.applied_drafts
            if package['draft_id'] == self.applied_active_draft_id
        )
        self.applied_relation = copy.deepcopy(active['relation'])
        self.applied_pairs = copy.deepcopy(active['pairs'])
        self._accepting_draft = True
        self.accept()
