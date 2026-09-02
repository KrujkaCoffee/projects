from __future__ import annotations

from typing import Dict, Iterable, List

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from .db import normalize_table_key
from .ui_loader import load_ui
from .widgets.relation_canvas import RelationCanvas

def _localize_buttons(button_box: QDialogButtonBox, ok_text: str = "ОК") -> None:
    ok = button_box.button(QDialogButtonBox.Ok)
    cancel = button_box.button(QDialogButtonBox.Cancel)
    if ok is not None:
        ok.setText(ok_text)
    if cancel is not None:
        cancel.setText("Отмена")



class ConnectionDialog(QDialog):
    def __init__(self, parent=None, dsn: str = "") -> None:
        super().__init__(parent)
        load_ui("connection_dialog.ui", self)
        self.dsn_edit.setText(dsn)
        _localize_buttons(self.buttonBox, "Подключиться")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    @property
    def dsn(self) -> str:
        return self.dsn_edit.text().strip()


class PhysicalTableDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        load_ui("physical_table_dialog.ui", self)
        self.cache_enabled.setChecked(True)
        self.schema_enabled.setChecked(True)
        _localize_buttons(self.buttonBox, "Добавить")
        self.table_name.textChanged.connect(self._suggest_key)
        self.db_key.textChanged.connect(self._suggest_key)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def _suggest_key(self) -> None:
        if self.table_key.hasFocus() and self.table_key.text().strip():
            return
        db_key = normalize_table_key(self.db_key.text() or "main")
        table = normalize_table_key(self.table_name.text())
        if table:
            self.table_key.setText(f"{db_key}.{table}" if db_key else table)

    def values(self) -> Dict[str, object]:
        return {
            "table_key": self.table_key.text().strip(),
            "db_key": self.db_key.text().strip() or "main",
            "table_name": self.table_name.text().strip(),
            "is_enabled": 1 if self.is_enabled.isChecked() else 0,
            "cache_enabled": 1 if self.cache_enabled.isChecked() else 0,
            "schema_enabled": 1 if self.schema_enabled.isChecked() else 0,
        }


class PairDialog(QDialog):
    def __init__(
        self,
        parent,
        table_keys: Iterable[str],
        fields_by_table: Dict[str, List[str]],
        left_table: str = "",
        right_table: str = "",
        left_field: str = "",
        right_field: str = "",
        operator: str = "=",
        role: str = "direct",
        pair_join_type: str = "",
    ) -> None:
        super().__init__(parent)
        load_ui("pair_dialog.ui", self)
        self.fields_by_table = fields_by_table

        keys = list(table_keys)
        self.left_table.addItems(keys)
        self.right_table.addItems(keys)
        self.operator.addItems(["=", "!=", ">", ">=", "<", "<=", "IS", "IS NOT"])
        self.role.addItems(["direct", "fallback", "scope", "tenant", "date_range", "custom"])
        self.pair_join_type.addItems(["", "LEFT JOIN", "INNER JOIN", "RIGHT JOIN", "FULL JOIN"])

        self.left_table.currentTextChanged.connect(self._reload_left_fields)
        self.right_table.currentTextChanged.connect(self._reload_right_fields)

        if left_table in keys:
            self.left_table.setCurrentText(left_table)
        if right_table in keys:
            self.right_table.setCurrentText(right_table)
        self._reload_left_fields()
        self._reload_right_fields()
        if left_field:
            self.left_field.setCurrentText(left_field)
        if right_field:
            self.right_field.setCurrentText(right_field)
        self.operator.setCurrentText(operator or "=")
        self.role.setCurrentText(role or "direct")
        self.pair_join_type.setCurrentText(pair_join_type or "")

        _localize_buttons(self.buttonBox, "Добавить пару")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def _reload_left_fields(self) -> None:
        table = self.left_table.currentText()
        self.left_field.clear()
        self.left_field.addItems(self.fields_by_table.get(table, []))

    def _reload_right_fields(self) -> None:
        table = self.right_table.currentText()
        self.right_field.clear()
        self.right_field.addItems(self.fields_by_table.get(table, []))

    def values(self) -> Dict[str, str]:
        return {
            "left_table_key": self.left_table.currentText(),
            "left_field_name": self.left_field.currentText(),
            "right_table_key": self.right_table.currentText(),
            "right_field_name": self.right_field.currentText(),
            "operator": self.operator.currentText(),
            "role": self.role.currentText(),
            "pair_join_type": self.pair_join_type.currentText(),
        }


class RowEditDialog(QDialog):
    """Диалог добавления строки для произвольной таблицы БД."""

    def __init__(self, parent, columns: List[str], title: str = "Добавить строку") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(650, 520)
        self.columns = columns
        self.edits: Dict[str, QLineEdit] = {}
        self.null_checks: Dict[str, QCheckBox] = {}

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        for column in columns:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit()
            edit.setPlaceholderText("пусто = DEFAULT / не передавать колонку")
            null_box = QCheckBox("NULL")
            h.addWidget(edit, 1)
            h.addWidget(null_box)
            form.addRow(column, row)
            self.edits[column] = edit
            self.null_checks[column] = null_box

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(form_widget)

        hint = QLabel("Для вставки NULL поставьте флаг NULL. Пустое поле без флага не участвует в INSERT и оставляет DEFAULT.")
        hint.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        _localize_buttons(buttons, "Добавить")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)

    def values(self) -> Dict[str, object]:
        result: Dict[str, object] = {}
        for column in self.columns:
            if self.null_checks[column].isChecked():
                result[column] = None
                continue
            text = self.edits[column].text()
            if text != "":
                result[column] = text
        return result

class RelationMapDialog(QDialog):
    """Большой modal/fullscreen режим карты связей.

    Диалог не пишет в БД напрямую. Он сообщает родительской вкладке:
    - какая таблица выбрана для карты;
    - какую пару полей пользователь протянул на canvas;
    - что нужно подготовить форму связи под текущую пару таблиц.
    """

    pairDropped = pyqtSignal(str, str, str, str)
    peerChanged = pyqtSignal(str)
    prepareRelationRequested = pyqtSignal(str)

    def __init__(
        self,
        parent,
        tables: List[dict],
        fields_by_table: Dict[str, List[dict]],
        relations: List[dict],
        pairs_by_relation: Dict[str, List[dict]],
        selected_table_key: str,
        peer_table_key: str = "",
        draft_relation: dict | None = None,
        draft_pairs: List[dict] | None = None,
    ) -> None:
        super().__init__(parent)
        load_ui("relation_map_dialog.ui", self)
        # Keep the action explicit and preserve the familiar Designer object
        # name used by the earlier prototype.
        self.prepare_relation_btn = self.use_target_btn
        self.tables = tables
        self.fields_by_table = fields_by_table
        self.relations = relations
        self.pairs_by_relation = pairs_by_relation
        self.selected_table_key = selected_table_key or ""
        self.peer_table_key = peer_table_key or ""
        self.draft_relation = draft_relation
        self.draft_pairs = draft_pairs or []
        self._loading_peer = False

        self.canvas = RelationCanvas(self)
        # self.canvas_container.layout().addWidget(self.canvas)
        self.canvas.pairDropped.connect(self.pairDropped)

        self.peer_combo.currentIndexChanged.connect(lambda *_: self._on_peer_changed())
        self.prepare_relation_btn.clicked.connect(self._emit_prepare)
        self.fit_btn.clicked.connect(self.canvas.fit_to_content)
        self.reset_zoom_btn.clicked.connect(self.canvas.reset_zoom)
        self.close_btn.clicked.connect(self.accept)

        self._populate_peer_combo(self.peer_table_key)
        self.refresh(
            tables,
            fields_by_table,
            relations,
            pairs_by_relation,
            selected_table_key,
            self.current_peer_key(),
            draft_relation,
            draft_pairs or [],
        )

    def current_peer_key(self) -> str:
        return self.peer_combo.currentData() or ""

    def set_peer_key(self, peer_key: str) -> None:
        self._set_combo_by_data(self.peer_combo, peer_key or "")
        self.peer_table_key = peer_key or ""

    def refresh(
        self,
        tables: List[dict],
        fields_by_table: Dict[str, List[dict]],
        relations: List[dict],
        pairs_by_relation: Dict[str, List[dict]],
        selected_table_key: str,
        peer_table_key: str = "",
        draft_relation: dict | None = None,
        draft_pairs: List[dict] | None = None,
    ) -> None:
        self.tables = tables
        self.fields_by_table = fields_by_table
        self.relations = relations
        self.pairs_by_relation = pairs_by_relation
        self.selected_table_key = selected_table_key or ""
        self.peer_table_key = peer_table_key or self.current_peer_key()
        self.draft_relation = draft_relation
        self.draft_pairs = draft_pairs or []

        self.selected_table_label.setText(self.selected_table_key or "—")
        self._populate_peer_combo(self.peer_table_key)
        self._update_status()
        self.canvas.redraw(
            self.tables,
            self.fields_by_table,
            self.relations,
            self.pairs_by_relation,
            self.selected_table_key,
            self.current_peer_key(),
            draft_relation=self.draft_relation,
            draft_pairs=self.draft_pairs,
        )

    def _populate_peer_combo(self, preferred_key: str = "") -> None:
        self._loading_peer = True
        try:
            self.peer_combo.blockSignals(True)
            self.peer_combo.clear()
            self.peer_combo.addItem("— выберите таблицу —", "")
            for row in sorted(self.tables, key=lambda x: (x.get("table_name") or x.get("table_key") or "")):
                key = row.get("table_key") or ""
                if not key or key == self.selected_table_key:
                    continue
                name = row.get("table_name") or key
                rel_count = self._relation_count_between(self.selected_table_key, key)
                prefix = "🔗" if rel_count else "○"
                fields_count = len(self.fields_by_table.get(key, []))
                self.peer_combo.addItem(f"{prefix} {name}  [{key}] · полей: {fields_count}", key)
            self._set_combo_by_data(self.peer_combo, preferred_key or self.peer_table_key, block=False)
            self.peer_combo.blockSignals(False)
        finally:
            self._loading_peer = False

    def _relation_count_between(self, a: str, b: str) -> int:
        result = 0
        for rel in self.relations:
            if {rel.get("source_table_key") or "", rel.get("target_table_key") or ""} == {a, b}:
                result += 1
        return result

    @staticmethod
    def _set_combo_by_data(combo: QComboBox, value: str, block: bool = True) -> None:
        old = combo.blockSignals(block)
        try:
            for idx in range(combo.count()):
                if combo.itemData(idx) == value:
                    combo.setCurrentIndex(idx)
                    return
            combo.setCurrentIndex(0 if combo.count() else -1)
        finally:
            combo.blockSignals(old)

    def _on_peer_changed(self) -> None:
        if self._loading_peer:
            return
        self.peer_table_key = self.current_peer_key()
        self.peerChanged.emit(self.peer_table_key)
        self._update_status()

    def _emit_prepare(self) -> None:
        peer = self.current_peer_key()
        if peer:
            self.prepareRelationRequested.emit(peer)

    def _update_status(self) -> None:
        peer = self.current_peer_key()
        self.prepare_relation_btn.setEnabled(bool(self.selected_table_key and peer))
        if not self.selected_table_key:
            self.prepare_relation_btn.setText("🎯 Использовать выбранную")
            self.relation_status_label.setText("Не выбрана базовая таблица.")
            return
        if not peer:
            self.prepare_relation_btn.setText("🎯 Использовать выбранную")
            self.relation_status_label.setText(
                "Выберите таблицу для карты. Никакая таблица не подставляется автоматически."
            )
            return

        active_draft = bool(
            self.draft_relation
            and {
                self.draft_relation.get("source_table_key") or "",
                self.draft_relation.get("target_table_key") or "",
            } == {self.selected_table_key, peer}
        )
        relations = [
            rel
            for rel in self.relations
            if {rel.get("source_table_key") or "", rel.get("target_table_key") or ""}
            == {self.selected_table_key, peer}
        ]

        if active_draft:
            key = self.draft_relation.get("relation_key") or "черновик"
            self.prepare_relation_btn.setText("✓ Черновик активен")
            self.relation_status_label.setText(
                f"Активен черновик {key}; пар полей: {len(self.draft_pairs)}. "
                "После переноса поля появляется сплошная янтарная линия."
            )
        elif relations:
            names = ", ".join(rel.get("relation_key") or "?" for rel in relations)
            self.prepare_relation_btn.setText("🔗 Открыть связь")
            self.relation_status_label.setText(
                f"Найдены сохранённые связи: {names}. "
                "Нажмите «Открыть связь», чтобы редактировать её пары."
            )
        else:
            self.prepare_relation_btn.setText("➕ Создать черновик")
            self.relation_status_label.setText(
                "Таблица выбрана как кандидат. Связь ещё не создана, поэтому линии нет."
            )
