from __future__ import annotations

import os
import shlex
import sys
from typing import Dict, List, Optional

from PyQt5.QtCore import QProcess, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..db import DbError, PostgresDatabase, normalize_table_key
from ..dialogs import PairDialog, RelationMapDialog
from ..physical_tables.columns import (
    BOOL_COLUMNS as PHYSICAL_TABLE_BOOL_COLUMNS,
    INT_COLUMNS as PHYSICAL_TABLE_INT_COLUMNS,
    TABLE_COLUMNS as PHYSICAL_TABLE_COLUMNS,
    TABLE_LABELS as PHYSICAL_TABLE_LABELS,
)
from ..physical_tables.editor_dialog import PhysicalTablesEditorDialog
from ..physical_tables.repository import PhysicalTablesRepository
from ..relation_keys import build_relation_key
from ..relation_persistence import persist_relation
from ..ui_helpers import confirm, info, make_item, read_item, selected_row, set_headers, to_int_bool, warn
from ..ui_loader import load_ui
from .relation_canvas import RelationCanvas


class AdminMetadataTab(QWidget):
    TABLE_COLUMNS = list(PHYSICAL_TABLE_COLUMNS)
    TABLE_BOOL_COLUMNS = set(PHYSICAL_TABLE_BOOL_COLUMNS)
    TABLE_INT_COLUMNS = set(PHYSICAL_TABLE_INT_COLUMNS)

    FIELD_COLUMNS = [
        "field_name",
        "python_name",
        "db_type",
        "nullable",
        "is_pk",
        "label",
        "sort_order",
        "include_in_schema",
        "orm_field_class",
        "widget_hint",
        "form_hint",
        "notes",
        "updated_at",
    ]
    FIELD_BOOL_COLUMNS = {"nullable", "is_pk", "include_in_schema"}
    FIELD_INT_COLUMNS = {"sort_order"}

    PAIR_COLUMNS = [
        "pair_no",
        "left_table_key",
        "left_field_name",
        "operator",
        "right_table_key",
        "right_field_name",
        "role",
        "pair_join_type",
    ]

    TABLE_LABELS = dict(PHYSICAL_TABLE_LABELS)
    FIELD_LABELS = {
        "field_name": "Имя поля",
        "python_name": "Python-имя",
        "db_type": "Тип БД",
        "nullable": "NULL разрешён",
        "is_pk": "PK",
        "label": "Метка",
        "sort_order": "Порядок",
        "include_in_schema": "Включать в схему",
        "orm_field_class": "ORM-класс",
        "widget_hint": "Виджет",
        "form_hint": "Подсказка формы",
        "notes": "Описание",
        "updated_at": "Обновлено",
    }
    RELATION_GRID_COLUMNS = [
        "relation_key",
        "relation_name",
        "source_table_key",
        "target_table_key",
        "cardinality",
        "join_type",
        "is_enabled",
    ]
    RELATION_LABELS = {
        "relation_key": "Ключ связи",
        "relation_name": "Название",
        "source_table_key": "Левая таблица",
        "target_table_key": "Правая таблица",
        "cardinality": "Кардинальность",
        "join_type": "JOIN",
        "is_enabled": "Включена",
    }
    PAIR_LABELS = {
        "pair_no": "№",
        "left_table_key": "Левая таблица",
        "left_field_name": "Левое поле",
        "operator": "Оператор",
        "right_table_key": "Правая таблица",
        "right_field_name": "Правое поле",
        "role": "Роль",
        "pair_join_type": "JOIN пары",
    }

    def __init__(self, db: PostgresDatabase, dsn_provider, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.dsn_provider = dsn_provider
        self._loading = False
        self._original_fields: set[str] = set()
        self._tables_cache: List[dict] = []
        self._fields_cache: Dict[str, List[dict]] = {}
        self._relations_cache: List[dict] = []
        self._pairs_cache: Dict[str, List[dict]] = {}
        self._relation_dirty = False
        self._last_selected_table_key = ""
        self._physical_tables_repository = PhysicalTablesRepository(db)
        self.generator_process: Optional[QProcess] = None

        self._build_ui()
        self.right_tabs.tabBar().setDrawBase(False)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        load_ui("admin_metadata_tab.ui", self)

        self.rel_cardinality.addItems(["many_to_one", "one_to_one", "one_to_many", "many_to_many"])
        self.rel_join_type.addItems(["LEFT JOIN", "INNER JOIN", "RIGHT JOIN", "FULL JOIN", "CROSS JOIN"])
        self.rel_missing_policy.addItems(["none", "allow", "warn", "error", "drop_row"])
        self.rel_on_many_policy.addItems(["error", "first", "aggregate", "allow", "warn"])

        self._prepare_grid(self.tables_grid, single_row=True)
        self._prepare_grid(self.fields_grid, single_row=False)
        self._prepare_grid(self.relations_grid, single_row=True)
        self._prepare_grid(self.pairs_grid, single_row=False)

        set_headers(self.tables_grid, [self.TABLE_LABELS.get(c, c) for c in self.TABLE_COLUMNS], self.TABLE_COLUMNS)
        set_headers(self.fields_grid, [self.FIELD_LABELS.get(c, c) for c in self.FIELD_COLUMNS], self.FIELD_COLUMNS)
        set_headers(self.relations_grid, [self.RELATION_LABELS.get(c, c) for c in self.RELATION_GRID_COLUMNS], self.RELATION_GRID_COLUMNS)
        set_headers(self.pairs_grid, [self.PAIR_LABELS.get(c, c) for c in self.PAIR_COLUMNS], self.PAIR_COLUMNS)

        self.main_splitter.setSizes([620, 980])
        self.relation_top.setSizes([520, 760])

        self.canvas = RelationCanvas()
        self.canvas.setMinimumHeight(300)
        # self.canvas_container.layout().addWidget(self.canvas)
        self._relation_map_dialog = None
        
        self._connect_signals()

    @staticmethod
    def _prepare_grid(grid: QTableWidget, single_row: bool) -> None:
        grid.setAlternatingRowColors(True)
        grid.setSelectionBehavior(QAbstractItemView.SelectRows)
        if single_row:
            grid.setSelectionMode(QAbstractItemView.SingleSelection)
        grid.horizontalHeader().setStretchLastSection(True)
        grid.verticalHeader().setVisible(False)

    def _connect_signals(self) -> None:
        self.refresh_btn.clicked.connect(self.reload_all)
        self.check_schema_btn.clicked.connect(self.check_admin_tables)
        self.save_tables_btn.clicked.connect(self.save_tables)
        self.add_table_btn.clicked.connect(self.add_physical_table)
        self.delete_table_btn.clicked.connect(self.delete_physical_table)
        self.table_filter.textChanged.connect(self._apply_table_filter)
        self.tables_grid.currentCellChanged.connect(lambda *_: self._on_selected_table_changed())

        self.save_fields_btn.clicked.connect(self.save_fields)
        self.add_field_btn.clicked.connect(self.add_field)
        self.delete_field_btn.clicked.connect(self.delete_field)

        self.refresh_relations_btn.clicked.connect(self.load_relations)
        self.add_relation_btn.clicked.connect(self.add_relation)
        self.delete_relation_btn.clicked.connect(self.delete_relation)
        self.relations_grid.currentCellChanged.connect(lambda *_: self._on_selected_relation_changed())
        self.save_relation_btn.clicked.connect(self.save_relation)
        self.add_pair_btn.clicked.connect(self.add_pair)
        self.delete_pair_btn.clicked.connect(self.delete_pair)
        self.canvas.pairDropped.connect(self.add_pair_from_canvas)
        self.relation_peer_combo.currentIndexChanged.connect(lambda *_: self._on_relation_peer_changed())
        self.prepare_relation_btn.clicked.connect(self.prepare_relation_for_current_peer)
        self.open_relation_map_btn.clicked.connect(self.open_relation_map)
        self.fit_relation_canvas_btn.clicked.connect(self.canvas.fit_to_content)
        self.reset_relation_canvas_btn.clicked.connect(self.canvas.reset_zoom)

        # Relation form dirty-state.  Only controls affecting the map trigger an
        # immediate redraw; the remaining controls merely mark the draft.
        self.rel_key.textChanged.connect(lambda *_: self._mark_relation_dirty())
        self.rel_name.textChanged.connect(lambda *_: self._mark_relation_dirty())
        self.rel_source.currentTextChanged.connect(lambda *_: self._mark_relation_dirty(redraw=True))
        self.rel_target.currentTextChanged.connect(lambda *_: self._mark_relation_dirty(redraw=True))
        self.rel_cardinality.currentTextChanged.connect(lambda *_: self._mark_relation_dirty(redraw=True))
        self.rel_join_type.currentTextChanged.connect(lambda *_: self._mark_relation_dirty())
        self.rel_missing_policy.currentTextChanged.connect(lambda *_: self._mark_relation_dirty())
        self.rel_on_many_policy.currentTextChanged.connect(lambda *_: self._mark_relation_dirty())
        self.rel_select_prefix.textChanged.connect(lambda *_: self._mark_relation_dirty())
        self.rel_enabled.stateChanged.connect(lambda *_: self._mark_relation_dirty(redraw=True))
        self.rel_generated.stateChanged.connect(lambda *_: self._mark_relation_dirty())
        self.rel_notes.textChanged.connect(lambda: self._mark_relation_dirty())
        self.pairs_grid.itemChanged.connect(lambda *_: self._mark_relation_dirty(redraw=True))

        self.browse_generator_btn.clicked.connect(self._browse_generator)
        self.browse_output_btn.clicked.connect(self._browse_output)
        self.bootstrap_btn.clicked.connect(lambda: self.run_generator("bootstrap"))
        self.generate_btn.clicked.connect(lambda: self.run_generator("generate"))

    # ------------------------------------------------------------------ general
    def require_connection(self) -> bool:
        if not self.db.is_connected:
            warn(self, "Сначала подключитесь к PostgreSQL")
            return False
        return True

    def reload_all(self) -> None:
        if not self.require_connection():
            return
        try:
            ok, missing = self.db.admin_tables_available()
            if not ok:
                warn(self, "Не найдены admin-таблицы в public: " + ", ".join(missing))
                return
            selected_key = self.current_table_key()
            self._tables_cache = self.db.list_admin_tables()
            self._populate_table_combos()
            self._populate_physical_tables(self._tables_cache)
            self._select_table_key(selected_key)
            if not self.current_table_key() and self._tables_cache:
                self._select_first_table()
            self._last_selected_table_key = self.current_table_key()
            self._load_all_fields_cache()
            self.load_fields()
            self.load_relations()
        except DbError as exc:
            warn(self, str(exc), "Ошибка БД")

    def check_admin_tables(self) -> None:
        if not self.require_connection():
            return
        try:
            ok, missing = self.db.admin_tables_available()
            if ok:
                info(self, "Все admin-таблицы найдены: admin_physical_tables, admin_table_fields, admin_table_relations, admin_relation_field_pairs")
            else:
                warn(self, "Не найдены: " + ", ".join(missing))
        except DbError as exc:
            warn(self, str(exc), "Ошибка БД")

    # ------------------------------------------------------------------ physical tables
    def _populate_physical_tables(self, rows: List[dict]) -> None:
        self._loading = True
        try:
            self.tables_grid.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, col in enumerate(self.TABLE_COLUMNS):
                    value = row.get(col)
                    checkable = col in self.TABLE_BOOL_COLUMNS
                    editable = col not in {"table_key", "updated_at"}
                    self.tables_grid.setItem(r, c, make_item(value, editable=editable, checkable=checkable))
            self.tables_grid.resizeColumnsToContents()
            self._apply_table_filter()
        finally:
            self._loading = False

    def _apply_table_filter(self) -> None:
        text = self.table_filter.text().strip().lower()
        for row in range(self.tables_grid.rowCount()):
            values = []
            for col_name in ("table_key", "db_key", "table_name"):
                col = self.TABLE_COLUMNS.index(col_name)
                item = self.tables_grid.item(row, col)
                values.append(item.text().lower() if item else "")
            self.tables_grid.setRowHidden(row, bool(text and text not in " ".join(values)))

    def current_table_key(self) -> str:
        row = selected_row(self.tables_grid)
        if row < 0:
            return ""
        col = self.TABLE_COLUMNS.index("table_key")
        item = self.tables_grid.item(row, col)
        return item.text().strip() if item else ""

    def _select_table_key(self, table_key: str) -> None:
        if not table_key:
            return
        col = self.TABLE_COLUMNS.index("table_key")
        for r in range(self.tables_grid.rowCount()):
            item = self.tables_grid.item(r, col)
            if item and item.text() == table_key:
                self.tables_grid.selectRow(r)
                return

    def _select_first_table(self) -> str:
        if not self._tables_cache:
            return ""
        enabled = next(
            (row for row in self._tables_cache if int(row.get("is_enabled") or 0)),
            self._tables_cache[0],
        )
        table_key = str(enabled.get("table_key") or "")
        self._select_table_key(table_key)
        return table_key

    def _on_selected_table_changed(self) -> None:
        if self._loading:
            return
        key = self.current_table_key()
        self.selected_table_label.setText(f"Таблица: {key}" if key else "Таблица не выбрана")
        if key != self._last_selected_table_key:
            self._last_selected_table_key = key
            self._reset_relation_context()
        self.load_fields()
        self.load_relations()

    def _reset_relation_context(self) -> None:
        """Clear any peer/relation inherited from the previously selected table."""
        old = self._loading
        self._loading = True
        try:
            if hasattr(self, "relation_peer_combo") and self.relation_peer_combo.count():
                self.relation_peer_combo.setCurrentIndex(0)
            self.relations_grid.clearSelection()
            self.relations_grid.setCurrentCell(-1, -1)
            self._clear_relation_form()
        finally:
            self._loading = old
        self._set_relation_dirty(False)
        self._update_relation_map_status()
        self.redraw_canvas()

    def save_tables(self) -> None:
        self.open_physical_tables_editor()

    def add_physical_table(self) -> None:
        self.open_physical_tables_editor(start_new=True)

    def delete_physical_table(self) -> None:
        self.open_physical_tables_editor(selected_table_key=self.current_table_key())

    def open_physical_tables_editor(
        self,
        selected_table_key: str = "",
        *,
        start_new: bool = False,
    ) -> bool:
        if not self.require_connection():
            return False
        selected = selected_table_key or self.current_table_key()
        try:
            dialog = PhysicalTablesEditorDialog(
                self,
                self._physical_tables_repository,
                selected_table_key=selected,
                start_new=start_new,
            )
        except Exception as exc:  # noqa: BLE001 - граница UI не должна завершать приложение
            warn(self, str(exc), "Ошибка открытия реестра таблиц")
            return False
        dialog.exec_()
        if dialog.saved:
            self._refresh_after_physical_tables_editor(dialog.selected_table_key or selected)
        return dialog.saved

    def _refresh_after_physical_tables_editor(self, preferred_key: str) -> None:
        try:
            rows = self._physical_tables_repository.load()
            self._tables_cache = rows
            self._populate_table_combos()
            self._populate_physical_tables(rows)
            selected = next(
                (
                    str(row.get("table_key") or "")
                    for row in rows
                    if str(row.get("table_key") or "") == preferred_key
                    and int(row.get("is_enabled") or 0)
                ),
                "",
            )
            if not selected:
                selected = self._fallback_table_key(preferred_key)
            self._select_table_key(selected)
            self._last_selected_table_key = selected
            self._load_all_fields_cache()
            self.load_fields()
            self.load_relations()
        except DbError as exc:
            warn(self, str(exc), "Ошибка обновления после сохранения реестра")

    def _fallback_table_key(self, _previous_key: str) -> str:
        enabled = next(
            (row for row in self._tables_cache if int(row.get("is_enabled") or 0)),
            self._tables_cache[0] if self._tables_cache else {},
        )
        return str(enabled.get("table_key") or "")

    # ------------------------------------------------------------------ fields
    def _load_all_fields_cache(self) -> None:
        rows = self.db.fetchall(
            """
            SELECT table_key, field_name, python_name, db_type, nullable, is_pk, label, sort_order,
                   include_in_schema, orm_field_class, widget_hint, form_hint, notes, updated_at
            FROM public.admin_table_fields
            ORDER BY table_key, sort_order, field_name
            """
        )
        cache: Dict[str, List[dict]] = {}
        for row in rows:
            cache.setdefault(row["table_key"], []).append(row)
        self._fields_cache = cache

    def load_fields(self) -> None:
        key = self.current_table_key()
        self._loading = True
        try:
            rows = self._fields_cache.get(key, []) if key else []
            self._original_fields = {row.get("field_name", "") for row in rows}
            self.fields_grid.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, col in enumerate(self.FIELD_COLUMNS):
                    value = row.get(col)
                    checkable = col in self.FIELD_BOOL_COLUMNS
                    editable = col != "updated_at"
                    self.fields_grid.setItem(r, c, make_item(value, editable=editable, checkable=checkable))
            self.fields_grid.resizeColumnsToContents()
            self.selected_table_label.setText(f"Таблица: {key}" if key else "Таблица не выбрана")
            self.redraw_canvas()
        finally:
            self._loading = False

    def add_field(self) -> None:
        key = self.current_table_key()
        if not key:
            warn(self, "Сначала выберите физическую таблицу")
            return
        row = self.fields_grid.rowCount()
        self.fields_grid.insertRow(row)
        default = {
            "field_name": "new_field",
            "python_name": "new_field",
            "db_type": "text",
            "nullable": 1,
            "is_pk": 0,
            "label": "",
            "sort_order": row + 1,
            "include_in_schema": 1,
            "orm_field_class": "",
            "widget_hint": "",
            "form_hint": "",
            "notes": "",
            "updated_at": "",
        }
        for c, col in enumerate(self.FIELD_COLUMNS):
            self.fields_grid.setItem(row, c, make_item(default.get(col), editable=(col != "updated_at"), checkable=(col in self.FIELD_BOOL_COLUMNS)))
        self.fields_grid.selectRow(row)

    def delete_field(self) -> None:
        row = selected_row(self.fields_grid)
        if row < 0:
            warn(self, "Выберите поле")
            return
        self.fields_grid.removeRow(row)

    def save_fields(self) -> None:
        key = self.current_table_key()
        if not key:
            warn(self, "Выберите физическую таблицу")
            return
        try:
            rows = []
            names = []
            for r in range(self.fields_grid.rowCount()):
                row = {}
                for c, col in enumerate(self.FIELD_COLUMNS):
                    if col == "updated_at":
                        continue
                    if col in self.FIELD_BOOL_COLUMNS:
                        row[col] = read_item(self.fields_grid, r, c, checkable=True)
                    elif col in self.FIELD_INT_COLUMNS:
                        row[col] = read_item(self.fields_grid, r, c, as_int=True)
                    else:
                        row[col] = read_item(self.fields_grid, r, c)
                if not row.get("field_name"):
                    continue
                if not row.get("python_name"):
                    row["python_name"] = normalize_table_key(row["field_name"]).replace(".", "_")
                names.append(row["field_name"])
                rows.append(row)
            if len(set(names)) != len(names):
                warn(self, "field_name должен быть уникальным внутри таблицы")
                return
            deleted = self._original_fields - set(names)
            with self.db.transaction() as cur:
                for field_name in deleted:
                    cur.execute("DELETE FROM public.admin_table_fields WHERE table_key=%s AND field_name=%s", [key, field_name])
                for row in rows:
                    cur.execute(
                        """
                        INSERT INTO public.admin_table_fields
                            (table_key, field_name, python_name, db_type, nullable, is_pk, label, sort_order,
                             include_in_schema, orm_field_class, widget_hint, form_hint, notes, updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))
                        ON CONFLICT (table_key, field_name) DO UPDATE SET
                            python_name=EXCLUDED.python_name,
                            db_type=EXCLUDED.db_type,
                            nullable=EXCLUDED.nullable,
                            is_pk=EXCLUDED.is_pk,
                            label=EXCLUDED.label,
                            sort_order=EXCLUDED.sort_order,
                            include_in_schema=EXCLUDED.include_in_schema,
                            orm_field_class=EXCLUDED.orm_field_class,
                            widget_hint=EXCLUDED.widget_hint,
                            form_hint=EXCLUDED.form_hint,
                            notes=EXCLUDED.notes,
                            updated_at=EXCLUDED.updated_at
                        """,
                        [
                            key,
                            row["field_name"],
                            row["python_name"],
                            row["db_type"],
                            row["nullable"],
                            row["is_pk"],
                            row["label"],
                            row["sort_order"],
                            row["include_in_schema"],
                            row["orm_field_class"],
                            row["widget_hint"],
                            row["form_hint"],
                            row["notes"],
                        ],
                    )
            self._load_all_fields_cache()
            self.load_fields()
            self._populate_relation_peer_combo()
        except Exception as exc:
            warn(self, str(exc), "Ошибка сохранения полей")

    # ------------------------------------------------------------------ relations
    def _populate_table_combos(self) -> None:
        current_source = self.rel_source.currentText() if hasattr(self, "rel_source") else ""
        current_target = self.rel_target.currentText() if hasattr(self, "rel_target") else ""
        keys = [row.get("table_key") or "" for row in self._tables_cache]
        self.rel_source.blockSignals(True)
        self.rel_target.blockSignals(True)
        self.rel_source.clear()
        self.rel_target.clear()
        self.rel_source.addItems(keys)
        self.rel_target.addItems(keys)
        if current_source in keys:
            self.rel_source.setCurrentText(current_source)
        if current_target in keys:
            self.rel_target.setCurrentText(current_target)
        self.rel_source.blockSignals(False)
        self.rel_target.blockSignals(False)

    def load_relations(self) -> None:
        if not self.db.is_connected:
            return
        key = self.current_table_key()
        preferred_relation_key = self.rel_key.text().strip() if hasattr(self, "rel_key") else ""
        try:
            self._relations_cache = self.db.fetchall(
                """
                SELECT relation_key, relation_name, source_table_key, target_table_key, cardinality, join_type,
                       missing_policy, on_many_policy, select_prefix, is_enabled, is_generated, notes, updated_at
                FROM public.admin_table_relations
                WHERE %s = '' OR source_table_key = %s OR target_table_key = %s
                ORDER BY source_table_key, target_table_key, relation_key
                """,
                [key, key, key],
            )
            rel_keys = [r["relation_key"] for r in self._relations_cache]
            self._pairs_cache = {}
            if rel_keys:
                pairs = self.db.fetchall(
                    """
                    SELECT relation_key, pair_no, left_table_key, left_field_name,
                           right_table_key, right_field_name, role, operator, pair_join_type
                    FROM public.admin_relation_field_pairs
                    WHERE relation_key = ANY(%s::text[])
                    ORDER BY relation_key, pair_no
                    """,
                    [rel_keys],
                )
                for pair in pairs:
                    self._pairs_cache.setdefault(pair["relation_key"], []).append(pair)

            # Loading a physical table never selects an arbitrary neighbour.
            self._populate_relation_peer_combo(preferred_key="")
            self._populate_relations_grid(preferred_relation_key)
            self.redraw_canvas()
        except DbError as exc:
            warn(self, str(exc), "Ошибка загрузки связей")

    def _populate_relations_grid(self, preferred_relation_key: str = "") -> None:
        self._loading = True
        try:
            rows = self._relations_cache
            self.relations_grid.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, col in enumerate(self.RELATION_GRID_COLUMNS):
                    self.relations_grid.setItem(
                        r,
                        c,
                        make_item(row.get(col), editable=False, checkable=(col == "is_enabled")),
                    )
            self.relations_grid.resizeColumnsToContents()
            self.relations_grid.clearSelection()
            self.relations_grid.setCurrentCell(-1, -1)
        finally:
            self._loading = False

        if preferred_relation_key and self._select_relation_key(preferred_relation_key):
            return
        self._clear_relation_form()
        self._set_relation_peer_combo("", redraw=False)
        self._set_relation_dirty(False)

    def _clear_relation_form(self) -> None:
        old = self._loading
        self._loading = True
        try:
            self.rel_key.clear()
            self.rel_name.clear()
            selected = self.current_table_key()
            if selected:
                self.rel_source.setCurrentText(selected)
            self.rel_target.setCurrentIndex(0 if self.rel_target.count() else -1)
            self.rel_cardinality.setCurrentText("many_to_one")
            self.rel_join_type.setCurrentText("LEFT JOIN")
            self.rel_missing_policy.setCurrentText("none")
            self.rel_on_many_policy.setCurrentText("error")
            self.rel_select_prefix.clear()
            self.rel_enabled.setChecked(True)
            self.rel_generated.setChecked(False)
            self.rel_notes.clear()
            self.pairs_grid.setRowCount(0)
        finally:
            self._loading = old
        self._set_relation_dirty(False)

    def _on_selected_relation_changed(self) -> None:
        if self._loading:
            return
        row = selected_row(self.relations_grid)
        if row < 0 or row >= len(self._relations_cache):
            self._clear_relation_form()
            return
        rel_key_item = self.relations_grid.item(row, 0)
        rel_key = rel_key_item.text() if rel_key_item else ""
        relation = next((r for r in self._relations_cache if r.get("relation_key") == rel_key), None)
        if relation:
            self._load_relation_form(relation)

    def _load_relation_form(self, relation: dict) -> None:
        self._loading = True
        try:
            self.rel_key.setText(relation.get("relation_key") or "")
            self.rel_name.setText(relation.get("relation_name") or "")
            self.rel_source.setCurrentText(relation.get("source_table_key") or "")
            self.rel_target.setCurrentText(relation.get("target_table_key") or "")
            self.rel_cardinality.setCurrentText(relation.get("cardinality") or "many_to_one")
            self.rel_join_type.setCurrentText(relation.get("join_type") or "LEFT JOIN")
            self.rel_missing_policy.setCurrentText(relation.get("missing_policy") or "none")
            self.rel_on_many_policy.setCurrentText(relation.get("on_many_policy") or "error")
            self.rel_select_prefix.setText(relation.get("select_prefix") or "")
            self.rel_enabled.setChecked(to_int_bool(relation.get("is_enabled")))
            self.rel_generated.setChecked(to_int_bool(relation.get("is_generated")))
            self.rel_notes.setPlainText(relation.get("notes") or "")
            self._populate_pairs_grid(self._pairs_cache.get(relation.get("relation_key"), []))
        finally:
            self._loading = False
        self._set_relation_dirty(False)
        self._set_relation_peer_combo(self._other_table_for_relation(relation, self.current_table_key()), redraw=False)
        self._update_relation_map_status()
        self.redraw_canvas()

    def _populate_pairs_grid(self, rows: List[dict]) -> None:
        self.pairs_grid.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, col in enumerate(self.PAIR_COLUMNS):
                value = row.get(col)
                editable = col != "pair_no"
                self.pairs_grid.setItem(r, c, make_item(value, editable=editable))
        self.pairs_grid.resizeColumnsToContents()

    def add_relation(self) -> None:
        selected = self.current_table_key()
        peer = self.current_peer_table_key()
        if not selected:
            warn(self, "Сначала выберите физическую таблицу")
            return
        if not peer:
            warn(self, "Сначала явно выберите таблицу в блоке карты связей")
            return
        self._prepare_potential_relation(selected, peer)

    def delete_relation(self) -> None:
        relation_key = self.rel_key.text().strip()
        if not relation_key:
            warn(self, "Выберите связь")
            return
        if not confirm(self, f"Удалить связь {relation_key} и все пары полей?"):
            return
        try:
            with self.db.transaction() as cur:
                cur.execute("DELETE FROM public.admin_relation_field_pairs WHERE relation_key=%s", [relation_key])
                cur.execute("DELETE FROM public.admin_table_relations WHERE relation_key=%s", [relation_key])
            self.load_relations()
        except Exception as exc:
            warn(self, str(exc), "Ошибка удаления связи")

    def save_relation(self) -> bool:
        if not self.require_connection():
            return False
        relation_key = self.rel_key.text().strip()
        if not relation_key:
            warn(self, "Ключ связи не может быть пустым")
            return False
        source = self.rel_source.currentText().strip()
        target = self.rel_target.currentText().strip()
        if not source or not target:
            warn(self, "Нужны левая и правая таблицы")
            return False
        pairs = self._read_pairs_from_grid()
        relation = self._current_relation_from_form()
        if relation is None:
            warn(self, "Не удалось прочитать форму связи")
            return False
        try:
            with self.db.transaction() as cur:
                persist_relation(cur, relation, pairs)
            self._set_relation_dirty(False)
            self.load_relations()
            info(self, f"Связь {relation_key} и пары полей сохранены")
            return True
        except Exception as exc:
            warn(self, str(exc), "Ошибка сохранения связи")
            return False

    def _read_pairs_from_grid(self) -> List[dict]:
        pairs = []
        for r in range(self.pairs_grid.rowCount()):
            pair = {}
            for c, col in enumerate(self.PAIR_COLUMNS):
                if col == "pair_no":
                    pair[col] = r
                else:
                    pair[col] = read_item(self.pairs_grid, r, c)
            if pair.get("left_table_key") and pair.get("left_field_name") and pair.get("right_table_key") and pair.get("right_field_name"):
                pair.setdefault("operator", "=")
                pair.setdefault("role", "direct")
                pair.setdefault("pair_join_type", "")
                pairs.append(pair)
        return pairs

    def add_pair(self) -> None:
        selected = self.current_table_key()
        peer = self.current_peer_table_key()
        active = self._current_relation_from_form()
        if not active:
            if not selected or not peer:
                warn(self, "Сначала выберите вторую таблицу и откройте или создайте связь")
                return
            self._select_or_prepare_relation_for_peer(peer)

        keys = [row.get("table_key") or "" for row in self._tables_cache]
        fields_by_table = {
            k: [f.get("field_name") or "" for f in self._fields_cache.get(k, [])]
            for k in keys
        }
        dialog = PairDialog(
            self,
            keys,
            fields_by_table,
            left_table=self.rel_source.currentText(),
            right_table=self.rel_target.currentText(),
        )
        if dialog.exec_() != dialog.Accepted:
            return
        pair = dialog.values()
        if self._pair_already_exists(pair):
            warn(self, "Такая пара полей уже добавлена в текущую связь")
            return
        self._append_pair(pair)

    def add_pair_from_canvas(self, left_table: str, left_field: str, right_table: str, right_field: str) -> None:
        selected = self.current_table_key()
        if not selected:
            return
        pair_tables = {left_table, right_table}
        if selected not in pair_tables or len(pair_tables) != 2:
            warn(self, "Пара должна соединять два поля показанных на карте таблиц")
            return
        peer = right_table if left_table == selected else left_table
        if peer != self.current_peer_table_key():
            self._set_relation_peer_combo(peer, redraw=False)

        active = self._current_relation_from_form()
        if not active or not self._relation_matches(active, selected, peer):
            existing = self._find_relation_between(selected, peer)
            if existing:
                self._select_relation_key(existing.get("relation_key") or "")
            else:
                self._prepare_potential_relation(selected, peer)

        source = self.rel_source.currentText().strip()
        target = self.rel_target.currentText().strip()
        if left_table == source and right_table == target:
            pair = {
                "left_table_key": left_table,
                "left_field_name": left_field,
                "right_table_key": right_table,
                "right_field_name": right_field,
            }
        else:
            pair = {
                "left_table_key": right_table,
                "left_field_name": right_field,
                "right_table_key": left_table,
                "right_field_name": left_field,
            }
        pair.update({"operator": "=", "role": "direct", "pair_join_type": ""})

        if self._pair_already_exists(pair):
            warn(self, "Такая пара полей уже добавлена в текущую связь")
            return
        self._append_pair(pair)
        self._set_relation_dirty(True, redraw=True)
        self._update_relation_map_status()
        self._refresh_relation_map_dialog()

    def _pair_already_exists(self, candidate: dict) -> bool:
        for pair in self._read_pairs_from_grid():
            if all(
                pair.get(key) == candidate.get(key)
                for key in (
                    "left_table_key",
                    "left_field_name",
                    "right_table_key",
                    "right_field_name",
                    "operator",
                )
            ):
                return True
        return False

    def _append_pair(self, pair: dict) -> None:
        old = self._loading
        self._loading = True
        try:
            row = self.pairs_grid.rowCount()
            self.pairs_grid.insertRow(row)
            values = {"pair_no": row, **pair}
            for c, col in enumerate(self.PAIR_COLUMNS):
                self.pairs_grid.setItem(
                    row,
                    c,
                    make_item(values.get(col, ""), editable=(col != "pair_no")),
                )
            self.pairs_grid.resizeColumnsToContents()
            self.pairs_grid.selectRow(row)
        finally:
            self._loading = old
        self._set_relation_dirty(True)
        self.redraw_canvas()
        self._refresh_relation_map_dialog()

    def delete_pair(self) -> None:
        row = selected_row(self.pairs_grid)
        if row < 0:
            warn(self, "Выберите пару полей")
            return
        old = self._loading
        self._loading = True
        try:
            self.pairs_grid.removeRow(row)
            for r in range(self.pairs_grid.rowCount()):
                self.pairs_grid.setItem(r, 0, make_item(r, editable=False))
        finally:
            self._loading = old
        self._set_relation_dirty(True)
        self.redraw_canvas()
        self._refresh_relation_map_dialog()

    def redraw_canvas(self) -> None:
        if not hasattr(self, "canvas"):
            return
        draft_relation = self._current_relation_from_form() if self._relation_dirty else None
        draft_pairs = self._draft_pairs_for_canvas() if self._relation_dirty else []
        self.canvas.redraw(
            self._tables_cache,
            self._fields_cache,
            self._relations_cache,
            self._pairs_cache,
            self.current_table_key(),
            self.current_peer_table_key(),
            draft_relation=draft_relation,
            draft_pairs=draft_pairs,
        )
        self._update_relation_map_status()

    def _mark_relation_dirty(self, redraw: bool = False) -> None:
        if self._loading:
            return
        self._set_relation_dirty(True, redraw=redraw)

    def _set_relation_dirty(self, dirty: bool, redraw: bool = False) -> None:
        self._relation_dirty = bool(dirty)
        if hasattr(self, "save_relation_btn"):
            suffix = " *" if self._relation_dirty else ""
            self.save_relation_btn.setText(f"💾 Сохранить связь и пары{suffix}")
        if redraw and hasattr(self, "canvas"):
            self.redraw_canvas()

    # ------------------------------------------------------------------ relation map v2
    def current_peer_table_key(self) -> str:
        if not hasattr(self, "relation_peer_combo"):
            return ""
        return self.relation_peer_combo.currentData() or ""

    def _populate_relation_peer_combo(self, preferred_key: Optional[str] = None) -> None:
        if not hasattr(self, "relation_peer_combo"):
            return
        selected = self.current_table_key()
        current = self.current_peer_table_key() if preferred_key is None else (preferred_key or "")

        self.relation_peer_combo.blockSignals(True)
        try:
            self.relation_peer_combo.clear()
            self.relation_peer_combo.addItem("— выберите таблицу —", "")
            rows = sorted(
                self._tables_cache,
                key=lambda row: (row.get("table_name") or row.get("table_key") or ""),
            )
            for row in rows:
                key = row.get("table_key") or ""
                if not key or key == selected:
                    continue
                name = row.get("table_name") or key
                fields_count = len(self._fields_cache.get(key, []))
                rel_count = self._relation_count_between(selected, key)
                prefix = "🔗" if rel_count else "○"
                enabled = "" if int(row.get("is_enabled") or 0) else " · выкл."
                self.relation_peer_combo.addItem(
                    f"{prefix} {name}  [{key}] · полей: {fields_count}{enabled}",
                    key,
                )
            self._set_relation_peer_combo(current, redraw=False)
        finally:
            self.relation_peer_combo.blockSignals(False)
        self._update_relation_map_status()

    def _set_relation_peer_combo(self, peer_key: str, redraw: bool = True) -> None:
        if not hasattr(self, "relation_peer_combo"):
            return
        old = self.relation_peer_combo.blockSignals(True)
        try:
            found = False
            for idx in range(self.relation_peer_combo.count()):
                if self.relation_peer_combo.itemData(idx) == peer_key:
                    self.relation_peer_combo.setCurrentIndex(idx)
                    found = True
                    break
            if not found and self.relation_peer_combo.count():
                self.relation_peer_combo.setCurrentIndex(0)
        finally:
            self.relation_peer_combo.blockSignals(old)
        self._update_relation_map_status()
        if redraw:
            self.redraw_canvas()

    def _relation_count_between(self, left: str, right: str) -> int:
        if not left or not right:
            return 0
        return len([rel for rel in self._relations_cache if self._relation_matches(rel, left, right)])

    @staticmethod
    def _relation_matches(relation: dict, left: str, right: str) -> bool:
        return {relation.get("source_table_key") or "", relation.get("target_table_key") or ""} == {left, right}

    def _find_relation_between(self, left: str, right: str) -> Optional[dict]:
        matches = [rel for rel in self._relations_cache if self._relation_matches(rel, left, right)]
        if not matches:
            return None
        matches.sort(key=lambda rel: (0 if int(rel.get("is_enabled") or 0) else 1, rel.get("relation_key") or ""))
        return matches[0]

    @staticmethod
    def _other_table_for_relation(relation: Optional[dict], selected: str) -> str:
        if not relation or not selected:
            return ""
        source = relation.get("source_table_key") or ""
        target = relation.get("target_table_key") or ""
        if source == selected and target != selected:
            return target
        if target == selected and source != selected:
            return source
        return ""

    def _current_relation_from_form(self) -> Optional[dict]:
        if not hasattr(self, "rel_source"):
            return None
        relation_key = self.rel_key.text().strip()
        source = self.rel_source.currentText().strip()
        target = self.rel_target.currentText().strip()
        if not relation_key or not source or not target:
            return None
        return {
            "relation_key": relation_key,
            "relation_name": self.rel_name.text().strip(),
            "source_table_key": source,
            "target_table_key": target,
            "cardinality": self.rel_cardinality.currentText(),
            "join_type": self.rel_join_type.currentText(),
            "missing_policy": self.rel_missing_policy.currentText(),
            "on_many_policy": self.rel_on_many_policy.currentText(),
            "select_prefix": self.rel_select_prefix.text().strip(),
            "is_enabled": 1 if self.rel_enabled.isChecked() else 0,
            "is_generated": 1 if self.rel_generated.isChecked() else 0,
            "notes": self.rel_notes.toPlainText(),
        }

    def _select_relation_key(self, relation_key: str) -> bool:
        if not relation_key:
            return False
        for row in range(self.relations_grid.rowCount()):
            item = self.relations_grid.item(row, self.RELATION_GRID_COLUMNS.index("relation_key"))
            if item and item.text() == relation_key:
                old = self._loading
                self._loading = True
                try:
                    self.relations_grid.selectRow(row)
                finally:
                    self._loading = old
                relation = next((r for r in self._relations_cache if r.get("relation_key") == relation_key), None)
                if relation:
                    self._load_relation_form(relation)
                return True
        return False

    def _select_or_prepare_relation_for_peer(self, peer_key: str) -> None:
        selected = self.current_table_key()
        if not selected or not peer_key:
            return
        relation = self._find_relation_between(selected, peer_key)
        if relation:
            self._select_relation_key(relation.get("relation_key") or "")
        else:
            self._prepare_potential_relation(selected, peer_key)

    def _prepare_potential_relation(self, source: str, target: str) -> None:
        if not source or not target:
            return
        base = build_relation_key(source, target)
        old = self._loading
        self._loading = True
        try:
            self.rel_key.setText(base)
            self.rel_name.setText(base)
            self.rel_source.setCurrentText(source)
            self.rel_target.setCurrentText(target)
            self.rel_cardinality.setCurrentText("many_to_one")
            self.rel_join_type.setCurrentText("LEFT JOIN")
            self.rel_missing_policy.setCurrentText("none")
            self.rel_on_many_policy.setCurrentText("error")
            self.rel_select_prefix.clear()
            self.rel_enabled.setChecked(True)
            self.rel_generated.setChecked(False)
            self.rel_notes.setPlainText("Черновик связи. Будет записан после сохранения связи и пар полей.")
            self.pairs_grid.setRowCount(0)
        finally:
            self._loading = old
        selected = self.current_table_key()
        peer = target if source == selected else source
        self._set_relation_peer_combo(peer, redraw=False)
        self._set_relation_dirty(True)
        self._update_relation_map_status("Подготовлен черновик связи. Линия появится только после соединения конкретных полей.")
        self.redraw_canvas()

    def prepare_relation_for_current_peer(self) -> None:
        selected = self.current_table_key()
        peer = self.current_peer_table_key()
        if not selected:
            warn(self, "Сначала выберите физическую таблицу")
            return
        if not peer:
            warn(self, "Выберите таблицу на панели карты")
            return
        self._select_or_prepare_relation_for_peer(peer)

    def _on_relation_peer_changed(self) -> None:
        if self._loading:
            return
        # Choosing a table changes only the map preview.  It must not create or
        # load a relation until the user presses the explicit action button or
        # connects two fields.
        self._update_relation_map_status()
        self.redraw_canvas()
        self._refresh_relation_map_dialog()

    def _update_relation_map_status(self, custom_text: str = "") -> None:
        if not hasattr(self, "relation_map_status_label"):
            return
        selected = self.current_table_key()
        peer = self.current_peer_table_key()
        self.prepare_relation_btn.setEnabled(bool(selected and peer))

        if custom_text:
            self.relation_map_status_label.setText(custom_text)
            return
        if not selected:
            self.prepare_relation_btn.setText("🎯 Использовать выбранную")
            self.relation_map_status_label.setText("Выберите физическую таблицу слева.")
            return
        if not peer:
            self.prepare_relation_btn.setText("🎯 Использовать выбранную")
            self.relation_map_status_label.setText(
                "Выберите таблицу для карты. Автоматический сосед больше не подставляется."
            )
            return

        active = self._current_relation_from_form()
        if active and self._relation_matches(active, selected, peer):
            pair_count = len(self._draft_pairs_for_canvas())
            if self._relation_dirty:
                self.prepare_relation_btn.setText("✓ Черновик активен")
                self.relation_map_status_label.setText(
                    f"Черновик {active.get('relation_key')} активен; пар полей: {pair_count}. "
                    "Несохранённые пары показаны сплошной янтарной линией."
                )
            else:
                self.prepare_relation_btn.setText("✓ Связь открыта")
                self.relation_map_status_label.setText(
                    f"Открыта сохранённая связь {active.get('relation_key')}. "
                    "Сохранённые пары показаны сплошной зелёной линией."
                )
            return

        matches = [rel for rel in self._relations_cache if self._relation_matches(rel, selected, peer)]
        if matches:
            self.prepare_relation_btn.setText("🔗 Открыть связь")
            names = ", ".join(rel.get("relation_key") or "?" for rel in matches)
            self.relation_map_status_label.setText(
                f"Для выбранной таблицы найдены связи: {names}. "
                "Нажмите «Открыть связь» для редактирования или соедините поля."
            )
        else:
            self.prepare_relation_btn.setText("➕ Создать черновик")
            self.relation_map_status_label.setText(
                "Таблица выбрана как кандидат. Связи ещё нет, поэтому между карточками нет линии."
            )

    def _draft_pairs_for_canvas(self) -> List[dict]:
        try:
            return self._read_pairs_from_grid()
        except Exception:
            return []

    def open_relation_map(self) -> None:
        selected = self.current_table_key()
        if not selected:
            warn(self, "Сначала выберите физическую таблицу")
            return
        dialog = RelationMapDialog(
            self,
            self._tables_cache,
            self._fields_cache,
            self._relations_cache,
            self._pairs_cache,
            selected,
            self.current_peer_table_key(),
            draft_relation=self._current_relation_from_form() if self._relation_dirty else None,
            draft_pairs=self._draft_pairs_for_canvas() if self._relation_dirty else [],
        )
        self._relation_map_dialog = dialog
        dialog.peerChanged.connect(self._on_relation_map_dialog_peer_changed)
        dialog.prepareRelationRequested.connect(self._on_relation_map_dialog_prepare_requested)
        dialog.pairDropped.connect(self.add_pair_from_canvas)
        dialog.showMaximized()
        dialog.exec_()
        self._relation_map_dialog = None

    def _on_relation_map_dialog_peer_changed(self, peer_key: str) -> None:
        self._set_relation_peer_combo(peer_key or "", redraw=True)
        self._refresh_relation_map_dialog()

    def _on_relation_map_dialog_prepare_requested(self, peer_key: str) -> None:
        if not peer_key:
            return
        self._set_relation_peer_combo(peer_key, redraw=False)
        self._select_or_prepare_relation_for_peer(peer_key)
        self._refresh_relation_map_dialog()

    def _refresh_relation_map_dialog(self) -> None:
        dialog = getattr(self, "_relation_map_dialog", None)
        if dialog is None:
            return
        dialog.refresh(
            self._tables_cache,
            self._fields_cache,
            self._relations_cache,
            self._pairs_cache,
            self.current_table_key(),
            self.current_peer_table_key(),
            draft_relation=self._current_relation_from_form() if self._relation_dirty else None,
            draft_pairs=self._draft_pairs_for_canvas() if self._relation_dirty else [],
        )

    # ------------------------------------------------------------------ generator
    def _browse_generator(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выберите context_schema_generator.py", "", "Python (*.py);;Все файлы (*)")
        if path:
            self.generator_path.setText(path)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Выберите папку генерации схем")
        if path:
            self.output_dir.setText(path)

    def run_generator(self, mode: str) -> None:
        if self.generator_process is not None and self.generator_process.state() != QProcess.NotRunning:
            warn(self, "Команда генератора уже выполняется")
            return
        dsn = self.dsn_provider() or ""
        python_exe = sys.executable
        generator = self.generator_path.text().strip()
        out_dir = self.output_dir.text().strip()
        template = self.bootstrap_template.text() if mode == "bootstrap" else self.generate_template.text()
        command = self._render_command(template, python_exe, generator, dsn, out_dir)
        self.generator_log.appendPlainText(f"\n$ {command}\n")

        self.generator_process = QProcess(self)
        self.generator_process.readyReadStandardOutput.connect(self._read_generator_stdout)
        self.generator_process.readyReadStandardError.connect(self._read_generator_stderr)
        self.generator_process.finished.connect(lambda code, status: self._generator_finished(mode, code, status))
        if os.name == "nt":
            self.generator_process.start("cmd", ["/C", command])
        else:
            self.generator_process.start("/bin/sh", ["-lc", command])

    @staticmethod
    def _render_command(template: str, python_exe: str, generator: str, dsn: str, out_dir: str) -> str:
        def q(value: str) -> str:
            return shlex.quote(value or "")

        return template.format(
            python=q(python_exe),
            generator=q(generator),
            dsn=q(dsn),
            out_dir=q(out_dir),
        )

    def _read_generator_stdout(self) -> None:
        if self.generator_process:
            text = bytes(self.generator_process.readAllStandardOutput()).decode("utf-8", errors="replace")
            self.generator_log.appendPlainText(text.rstrip())

    def _read_generator_stderr(self) -> None:
        if self.generator_process:
            text = bytes(self.generator_process.readAllStandardError()).decode("utf-8", errors="replace")
            self.generator_log.appendPlainText(text.rstrip())

    def _generator_finished(self, mode: str, code: int, status) -> None:
        self.generator_log.appendPlainText(f"\n[{mode}] завершено, код выхода = {code}\n")
        if code == 0 and mode == "bootstrap":
            self.reload_all()
