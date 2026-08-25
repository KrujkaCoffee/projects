from __future__ import annotations

import importlib
import os
import pathlib
import sys
from typing import Any, Callable

from PyQt5 import QtCore, QtWidgets

from .contracts import relation_graph_payload, schedule_snapshot


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
    "FriendlyState",
    "RelationsDraftPage",
    "GantDraftPage",
    "DraftToolsHost",
]
