from __future__ import annotations

import datetime
import importlib
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from PyQt5 import QtCore, QtWidgets

@dataclass(frozen=True)
class RelationGraphPayload:
    tables: tuple[dict[str, Any], ...]
    fields_by_table: Mapping[str, tuple[dict[str, Any], ...]]
    relations: tuple[dict[str, Any], ...]
    pairs_by_relation: Mapping[str, tuple[dict[str, Any], ...]]
    root_table_key: str


@dataclass(frozen=True)
class DraftLane:
    id: Any
    title: str
    group_id: Any = None
    group_title: str = ""
    order: int = 0
    color: str = "#7aa2d6"


@dataclass(frozen=True)
class DraftItem:
    id: Any
    lane_id: Any
    event_id: Any
    title: str
    start: datetime.datetime
    end: datetime.datetime
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class DraftScheduleSnapshot:
    lanes: tuple[DraftLane, ...]
    items: tuple[DraftItem, ...]
    date_from: datetime.datetime
    date_to: datetime.datetime
    skipped_items: int = 0


def relation_graph_payload(catalog: Any, root_table_key: str = "") -> RelationGraphPayload:
    tables_by_key = dict(getattr(catalog, "tables", {}) or {})
    fields = dict(getattr(catalog, "fields", {}) or {})
    relations_by_key = dict(getattr(catalog, "relations", {}) or {})
    if not tables_by_key:
        raise ValueError("В реестре пока нет таблиц для карты связей.")

    table_rows: list[dict[str, Any]] = []
    fields_by_table: dict[str, list[dict[str, Any]]] = {}
    for table_key, table in sorted(tables_by_key.items()):
        table_rows.append(
            {
                "table_key": table_key,
                "db_key": str(getattr(table, "db_key", "") or ""),
                "table_name": str(getattr(table, "table_name", "") or table_key),
                "is_enabled": int(bool(getattr(table, "is_enabled", True))),
                "schema_enabled": int(bool(getattr(table, "schema_enabled", True))),
            }
        )
        fields_by_table[table_key] = []

    for (table_key, field_name), field in sorted(
        fields.items(),
        key=lambda item: (
            item[0][0],
            int(getattr(item[1], "sort_order", 0) or 0),
            item[0][1],
        ),
    ):
        if table_key not in fields_by_table:
            continue
        fields_by_table[table_key].append(
            {
                "table_key": table_key,
                "field_name": field_name,
                "label": str(getattr(field, "label", "") or ""),
                "db_type": str(getattr(field, "db_type", "") or ""),
                "nullable": int(bool(getattr(field, "nullable", True))),
                "is_pk": int(bool(getattr(field, "is_pk", False))),
                "sort_order": int(getattr(field, "sort_order", 0) or 0),
                "include_in_schema": int(
                    bool(getattr(field, "include_in_schema", True))
                ),
            }
        )

    relation_rows: list[dict[str, Any]] = []
    pairs_by_relation: dict[str, list[dict[str, Any]]] = {}
    for relation_key, relation in sorted(relations_by_key.items()):
        relation_rows.append(
            {
                "relation_key": relation_key,
                "relation_name": str(
                    getattr(relation, "relation_name", "") or relation_key
                ),
                "source_table_key": str(
                    getattr(relation, "source_table_key", "") or ""
                ),
                "target_table_key": str(
                    getattr(relation, "target_table_key", "") or ""
                ),
                "cardinality": str(
                    getattr(relation, "cardinality", "many_to_one") or "many_to_one"
                ),
                "join_type": str(
                    getattr(relation, "join_type", "LEFT JOIN") or "LEFT JOIN"
                ),
                "missing_policy": str(
                    getattr(relation, "missing_policy", "none") or "none"
                ),
                "on_many_policy": str(
                    getattr(relation, "on_many_policy", "error") or "error"
                ),
                "is_enabled": int(bool(getattr(relation, "is_enabled", True))),
            }
        )
        pairs_by_relation[relation_key] = [
            {
                "relation_key": relation_key,
                "pair_no": int(getattr(pair, "pair_no", index) or index),
                "left_table_key": str(getattr(pair, "left_table_key", "") or ""),
                "left_field_name": str(getattr(pair, "left_field_name", "") or ""),
                "right_table_key": str(getattr(pair, "right_table_key", "") or ""),
                "right_field_name": str(getattr(pair, "right_field_name", "") or ""),
                "role": str(getattr(pair, "role", "direct") or "direct"),
                "operator": str(getattr(pair, "operator", "=") or "="),
                "pair_join_type": str(
                    getattr(pair, "pair_join_type", "") or ""
                ),
            }
            for index, pair in enumerate(getattr(relation, "field_pairs", ()) or (), 1)
        ]

    enabled_keys = [
        row["table_key"] for row in table_rows if bool(row.get("is_enabled", 1))
    ]
    all_keys = [row["table_key"] for row in table_rows]
    root = root_table_key if root_table_key in tables_by_key else ""
    if not root:
        root = (enabled_keys or all_keys)[0]
    return RelationGraphPayload(
        tables=tuple(table_rows),
        fields_by_table={key: tuple(value) for key, value in fields_by_table.items()},
        relations=tuple(relation_rows),
        pairs_by_relation={key: tuple(value) for key, value in pairs_by_relation.items()},
        root_table_key=root,
    )


def schedule_snapshot(
    resources: Any,
    events: Any,
    crosses: Any,
    *,
    timezone: datetime.tzinfo | None = None,
    now_provider: Callable[[], datetime.datetime] | None = None,
) -> DraftScheduleSnapshot:
    zone = timezone or datetime.datetime.now().astimezone().tzinfo
    if zone is None:
        zone = datetime.timezone.utc
    now = (now_provider or (lambda: datetime.datetime.now(zone)))()
    now = _aware(now, zone)

    resources_by_id = dict(getattr(resources, "dict_elems", {}) or {})
    events_by_id = dict(getattr(events, "dict_elems", {}) or {})
    crosses_by_id = dict(getattr(crosses, "dict_crosses", {}) or {})

    lanes: list[DraftLane] = []
    active_resource_ids: set[Any] = set()
    for order, (resource_id, resource) in enumerate(resources_by_id.items()):
        if bool(_attribute_value(resource, "for_delete", False)):
            continue
        active_resource_ids.add(resource_id)
        template_id = _attribute_value(resource, "shablon", None)
        lanes.append(
            DraftLane(
                id=resource_id,
                title=str(_attribute_value(resource, "name", "") or f"Ресурс {resource_id}"),
                group_id=template_id,
                group_title=(
                    f"Шаблон {template_id}" if template_id is not None else ""
                ),
                order=order,
                color=_color_value(_attribute_value(resource, "color", None)),
            )
        )

    items: list[DraftItem] = []
    skipped = 0
    for cross_id, cross in crosses_by_id.items():
        resource_id = _attribute_value(cross, "res", None)
        event_id = _attribute_value(cross, "eve", None)
        event = events_by_id.get(event_id)
        if resource_id not in active_resource_ids or event is None:
            skipped += 1
            continue
        if bool(_attribute_value(event, "for_delete", False)):
            skipped += 1
            continue
        start = _datetime_value(_attribute_value(cross, "start", None), zone)
        end = _datetime_value(_attribute_value(cross, "end", None), zone)
        if start is None:
            start = _datetime_value(_attribute_value(event, "start", None), zone)
        if end is None:
            end = _datetime_value(_attribute_value(event, "end", None), zone)
        if start is None or end is None or end <= start:
            skipped += 1
            continue
        items.append(
            DraftItem(
                id=cross_id,
                lane_id=resource_id,
                event_id=event_id,
                title=str(_attribute_value(event, "name", "") or f"Событие {event_id}"),
                start=start,
                end=end,
                metadata={
                    "resource_id": resource_id,
                    "event_id": event_id,
                    "cross_id": cross_id,
                    "draft_read_only": True,
                },
            )
        )

    if items:
        date_from = min(item.start for item in items) - datetime.timedelta(days=2)
        date_to = max(item.end for item in items) + datetime.timedelta(days=2)
    else:
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = date_from + datetime.timedelta(days=31)
    if date_to <= date_from:
        date_to = date_from + datetime.timedelta(days=1)
    return DraftScheduleSnapshot(
        lanes=tuple(lanes),
        items=tuple(items),
        date_from=date_from,
        date_to=date_to,
        skipped_items=skipped,
    )


def _attribute_value(obj: Any, name: str, default: Any = None) -> Any:
    value = getattr(obj, name, default)
    return getattr(value, "value", value)


def _datetime_value(value: Any, timezone: datetime.tzinfo) -> datetime.datetime | None:
    value = getattr(value, "dt", value)
    if value is None or value == "":
        return None
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        value = datetime.datetime.combine(value, datetime.time.min)
    if not isinstance(value, datetime.datetime):
        return None
    return _aware(value, timezone)


def _aware(value: datetime.datetime, timezone: datetime.tzinfo) -> datetime.datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def _color_value(value: Any) -> str:
    rgb = getattr(value, "rgb", None)
    if callable(rgb):
        rgb = rgb()
    if isinstance(rgb, (tuple, list)) and len(rgb) >= 3:
        try:
            red, green, blue = (max(0, min(255, int(item))) for item in rgb[:3])
            return f"#{red:02x}{green:02x}{blue:02x}"
        except (TypeError, ValueError):
            pass
    return "#7aa2d6"



RELATIONS_VIEWER_PATH_ENV = "MES_RELATIONS_VIEWER_PATH"
GANT_WIDGET_PATH_ENV = "MES_GANT_WIDGET_PATH"


class DraftIntegrationUnavailable(RuntimeError):
    pass


class FriendlyState(QtWidgets.QFrame):
    retryRequested = QtCore.pyqtSignal()

    def __init__(
        self,
        title: str,
        text: str,
        *,
        icon: str,
        details: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("draftFriendlyState")
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setToolTip(details)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.addStretch(1)
        icon_label = QtWidgets.QLabel(icon, self)
        icon_font = icon_label.font()
        icon_font.setPointSize(30)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(icon_label)
        title_label = QtWidgets.QLabel(title, self)
        title_font = title_label.font()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title_label)
        text_label = QtWidgets.QLabel(text, self)
        text_label.setWordWrap(True)
        text_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(text_label)
        retry_button = QtWidgets.QPushButton("Повторить подключение", self)
        retry_button.clicked.connect(self.retryRequested)
        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(retry_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addStretch(1)


class _DraftPage(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self._body = None
        self.layout_root = QtWidgets.QVBoxLayout(self)
        self.layout_root.setContentsMargins(0, 0, 0, 0)
        self.layout_root.setSpacing(4)
        self.toolbar = QtWidgets.QFrame(self)
        self.toolbar_layout = QtWidgets.QHBoxLayout(self.toolbar)
        self.toolbar_layout.setContentsMargins(8, 4, 8, 4)
        title_label = QtWidgets.QLabel(title, self.toolbar)
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        self.toolbar_layout.addWidget(title_label)
        self.layout_root.addWidget(self.toolbar)

    def _set_body(self, widget: QtWidgets.QWidget) -> None:
        if self._body is not None:
            self.layout_root.removeWidget(self._body)
            self._body.setParent(None)
            self._body.deleteLater()
        self._body = widget
        self.layout_root.addWidget(widget, 1)


class RelationsDraftPage(_DraftPage):
    def __init__(self, catalog_provider: Callable[[], Any], parent=None) -> None:
        super().__init__("Карта связей MES", parent)
        self.catalog_provider = catalog_provider
        self.payload = None
        self.canvas = None
        self._changing_root = False
        self.root_combo = QtWidgets.QComboBox(self.toolbar)
        self.root_combo.setMinimumWidth(260)
        self.root_combo.setToolTip("Таблица в центре карты")
        self.refresh_button = QtWidgets.QPushButton("Обновить", self.toolbar)
        self.status_label = QtWidgets.QLabel(self.toolbar)
        self.status_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.toolbar_layout.addSpacing(12)
        self.toolbar_layout.addWidget(QtWidgets.QLabel("Начать с:", self.toolbar))
        self.toolbar_layout.addWidget(self.root_combo)
        self.toolbar_layout.addWidget(self.refresh_button)
        self.toolbar_layout.addStretch(1)
        self.toolbar_layout.addWidget(self.status_label)
        self.refresh_button.clicked.connect(self.refresh)
        self.root_combo.currentIndexChanged.connect(self._root_changed)

    def refresh(self) -> None:
        try:
            canvas_type = _load_relations_canvas()
            requested_root = str(self.root_combo.currentData() or "")
            self.payload = relation_graph_payload(
                self.catalog_provider(),
                requested_root,
            )
            self._fill_roots(self.payload.root_table_key)
            canvas = canvas_type(self)
            canvas.setObjectName("mesDraftRelationsCanvas")
            canvas.setProperty("draftReadOnly", True)
            canvas.load_graph(
                list(self.payload.tables),
                {
                    key: list(value)
                    for key, value in self.payload.fields_by_table.items()
                },
                list(self.payload.relations),
                {
                    key: list(value)
                    for key, value in self.payload.pairs_by_relation.items()
                },
                self.payload.root_table_key,
            )
            self.canvas = canvas
            self._set_body(canvas)
            self.status_label.setText("Черновой просмотр · без сохранения")
        except Exception as exc:
            self.canvas = None
            self.status_label.setText("Основное окно продолжает работать")
            state = FriendlyState(
                "Карта связей сейчас недоступна",
                "Её можно подключить позже — данные планирования и таблицы не затронуты.",
                icon="🧩",
                details=str(exc),
                parent=self,
            )
            state.retryRequested.connect(self.refresh)
            self._set_body(state)

    def _fill_roots(self, selected: str) -> None:
        if self.payload is None:
            return
        self._changing_root = True
        try:
            self.root_combo.clear()
            for table in self.payload.tables:
                key = str(table.get("table_key") or "")
                name = str(table.get("table_name") or key)
                self.root_combo.addItem(f"{name}  [{key}]", key)
            index = self.root_combo.findData(selected)
            self.root_combo.setCurrentIndex(max(0, index))
        finally:
            self._changing_root = False

    def _root_changed(self) -> None:
        if self._changing_root or self.canvas is None or self.payload is None:
            return
        root = str(self.root_combo.currentData() or "")
        if not root:
            return
        self.canvas.load_graph(
            list(self.payload.tables),
            {key: list(value) for key, value in self.payload.fields_by_table.items()},
            list(self.payload.relations),
            {key: list(value) for key, value in self.payload.pairs_by_relation.items()},
            root,
        )


class GantDraftPage(_DraftPage):
    def __init__(self, schedule_provider: Callable[[], tuple[Any, Any, Any]], parent=None) -> None:
        super().__init__("Черновой Гант", parent)
        self.schedule_provider = schedule_provider
        self.refresh_button = QtWidgets.QPushButton("Обновить", self.toolbar)
        self.status_label = QtWidgets.QLabel(self.toolbar)
        self.status_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.toolbar_layout.addStretch(1)
        self.toolbar_layout.addWidget(self.status_label)
        self.toolbar_layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self.refresh)

    def refresh(self) -> None:
        try:
            adaptive = _load_adaptive_schedule()
            resources, events, crosses = self.schedule_provider()
            snapshot = schedule_snapshot(resources, events, crosses)
            options = adaptive.ViewOptions(
                date_from=snapshot.date_from,
                date_to=snapshot.date_to,
                lane_layout=adaptive.LaneLayout.FLAT,
                layer_layout=adaptive.LayerLayout.OVERLAY,
                fit_to_width=(snapshot.date_to - snapshot.date_from).days <= 40,
                show_all_days=True,
                allow_lane_change=False,
                show_dependencies=False,
            )
            widget = adaptive.ScheduleWidget(parent=self, options=options)
            widget.setObjectName("resourcePlanningDraftGant")
            lanes = tuple(
                adaptive.Lane(
                    id=item.id,
                    title=item.title,
                    group_id=item.group_id,
                    group_title=item.group_title or None,
                    order=item.order,
                    color=item.color,
                )
                for item in snapshot.lanes
            )
            items = tuple(
                adaptive.ScheduleItem(
                    id=item.id,
                    lane_id=item.lane_id,
                    event_id=item.event_id,
                    title=item.title,
                    start=item.start,
                    end=item.end,
                    layer="plan",
                    locked=True,
                    movable=False,
                    resizable=False,
                    manually_scheduled=True,
                    time_owner=adaptive.TimeOwner.RESOURCE,
                    metadata=dict(item.metadata),
                )
                for item in snapshot.items
            )
            widget.set_data(adaptive.ScheduleModel(lanes=lanes, items=items, version=0))
            if items:
                message = (
                    f"Черновой просмотр: {len(items)} участий · изменения не сохраняются"
                )
            else:
                message = "Добавьте корректные даты участий — они появятся здесь автоматически"
            widget.set_status_message(message)
            self.status_label.setText(
                f"Ресурсов: {len(lanes)} · участий: {len(items)}"
                + (f" · без дат: {snapshot.skipped_items}" if snapshot.skipped_items else "")
            )
            self._set_body(widget)
        except Exception as exc:
            self.status_label.setText("Основное окно продолжает работать")
            state = FriendlyState(
                "Гант сейчас недоступен",
                "Черновой экран можно подключить позже — табличный режим остаётся рабочим.",
                icon="📅",
                details=str(exc),
                parent=self,
            )
            state.retryRequested.connect(self.refresh)
            self._set_body(state)


class DraftToolsHost(QtWidgets.QStackedWidget):
    def __init__(
        self,
        *,
        catalog_provider: Callable[[], Any],
        schedule_provider: Callable[[], tuple[Any, Any, Any]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.pages = {
            "mes_relations": RelationsDraftPage(catalog_provider, self),
            "gant": GantDraftPage(schedule_provider, self),
        }
        for page in self.pages.values():
            self.addWidget(page)

    def show_tool(self, name: str) -> None:
        page = self.pages.get(name)
        if page is None:
            raise ValueError(f"Неизвестный черновой инструмент {name!r}.")
        self.setCurrentWidget(page)
        page.refresh()
        self.show()


def _load_relations_canvas():
    _prepare_import_path(RELATIONS_VIEWER_PATH_ENV, "admin_panel", package_subdir="")
    try:
        module = importlib.import_module("app.relation_map.canvas")
        return module.RelationGraphCanvas
    except Exception as exc:
        raise DraftIntegrationUnavailable(
            "Не удалось подключить RelationGraphCanvas из admin_panel."
        ) from exc


def _load_adaptive_schedule():
    _prepare_import_path(GANT_WIDGET_PATH_ENV, "gant_widget", package_subdir="mk_beta")
    try:
        return importlib.import_module("adaptive_schedule")
    except Exception as exc:
        raise DraftIntegrationUnavailable(
            "Не удалось подключить adaptive_schedule из gant_widget."
        ) from exc


def _prepare_import_path(env_name: str, repository_name: str, *, package_subdir: str) -> None:
    candidates: list[pathlib.Path] = []
    configured = str(os.getenv(env_name, "") or "").strip()
    if configured:
        candidates.append(pathlib.Path(configured))
    file_path = pathlib.Path(__file__).resolve()
    for parent in file_path.parents:
        candidates.append(parent / repository_name)
        candidates.append(parent.parent / repository_name)
    for candidate in candidates:
        root = candidate.expanduser()
        if package_subdir and (root / package_subdir).is_dir():
            root = root / package_subdir
        if not root.is_dir():
            continue
        value = str(root)
        if value not in sys.path:
            sys.path.insert(0, value)
        importlib.invalidate_caches()
        return



__all__ = [
    "RELATIONS_VIEWER_PATH_ENV",
    "GANT_WIDGET_PATH_ENV",
    "DraftIntegrationUnavailable",
    "RelationGraphPayload",
    "DraftLane",
    "DraftItem",
    "DraftScheduleSnapshot",
    "relation_graph_payload",
    "schedule_snapshot",
    "FriendlyState",
    "RelationsDraftPage",
    "GantDraftPage",
    "DraftToolsHost",
]
