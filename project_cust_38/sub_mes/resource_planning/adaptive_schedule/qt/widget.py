from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timedelta

from PyQt5 import QtCore, QtGui, QtWidgets

from ..commands import ScheduleCommand
from ..controller import ControllerResult, PreviewResult, ScheduleController
from ..domain import ScheduleModel
from ..services import ScheduleServices, ValidationSeverity
from ..view_options import (
    HeaderStyle,
    ItemHeightMode,
    LaneLayout,
    LayerLayout,
    TimeScale,
    ViewOptions,
)
from .header import TimelineHeader
from .lane_model import LaneTreeView
from .timeline import TimelineScene


class TimelineView(QtWidgets.QGraphicsView):
    selectGroupRequested = QtCore.pyqtSignal()

    def keyPressEvent(self, event) -> None:
        if event.matches(QtGui.QKeySequence.SelectAll):
            self.selectGroupRequested.emit()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_Escape:
            self.scene().clearSelection()
            event.accept()
            return
        super().keyPressEvent(event)


class ScheduleWidget(QtWidgets.QWidget):

    modelChanged = QtCore.pyqtSignal(object)
    previewChanged = QtCore.pyqtSignal(object)
    commandCommitted = QtCore.pyqtSignal(object)
    commandRejected = QtCore.pyqtSignal(object)
    itemActivated = QtCore.pyqtSignal(object)
    selectionChanged = QtCore.pyqtSignal(object)

    def __init__(
        self,
        parent=None,
        *,
        options: ViewOptions | None = None,
        auto_schedule_on_change: bool = False,
    ) -> None:
        super().__init__(parent)
        self._options = options or _default_options()
        self._effective_options = self._options
        self._controller = ScheduleController(
            auto_schedule_on_change=auto_schedule_on_change,
        )
        self._building_toolbar = False

        self._lane_view = LaneTreeView(self)
        self._lane_view.setMinimumWidth(self._options.lane_panel_min_width)
        self._lane_view.setMaximumWidth(self._options.lane_panel_max_width)
        self._lane_view.set_panel_style(self._options.lane_panel_style)
        self._lane_view.set_row_height(round(self._options.lane_height))

        self._scene = TimelineScene(self._controller, self._effective_options, self)
        self._timeline_view = TimelineView(self._scene, self)
        self._timeline_view.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._timeline_view.setRenderHints(
            QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing
        )
        self._timeline_view.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self._timeline_view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self._timeline_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._timeline_view.setViewportUpdateMode(
            QtWidgets.QGraphicsView.BoundingRectViewportUpdate
        )

        self._header = TimelineHeader(self._effective_options, self)
        self._corner = QtWidgets.QLabel(self._options.lane_panel_header, self)
        self._corner.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self._corner.setContentsMargins(10, 0, 0, 0)
        self._corner.setFixedHeight(self._options.header_height)
        self._corner.setStyleSheet(
            "background: #f8fafc; color: #334155; font-weight: 600;"
            "border-bottom: 1px solid #cfd6df;"
        )
        self._status = QtWidgets.QLabel(self)
        self._status.setMinimumHeight(24)
        self._status.setContentsMargins(8, 2, 8, 2)

        self._toolbar = self._make_toolbar()
        body = QtWidgets.QGridLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._corner, 0, 0)
        body.addWidget(self._header, 0, 1)
        body.addWidget(self._lane_view, 1, 0)
        body.addWidget(self._timeline_view, 1, 1)
        body.setColumnStretch(1, 1)
        body.setRowStretch(1, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar)
        layout.addLayout(body, 1)
        layout.addWidget(self._status)

        self._connect_signals()
        self._refresh(reset_lanes=True)

    @property
    def model(self) -> ScheduleModel:
        return self._controller.model

    @property
    def controller(self) -> ScheduleController:
        return self._controller

    @property
    def view_options(self) -> ViewOptions:
        return self._options

    def set_data(self, model: ScheduleModel) -> None:
        self._controller.set_model(model)
        self._refresh(reset_lanes=True)
        self.modelChanged.emit(model)

    def set_services(self, services: ScheduleServices) -> None:
        self._controller.set_services(services)
        self._set_status("Сервисы планирования подключены")
        self._update_actions()

    def set_view_options(self, options: ViewOptions) -> None:
        self._options = options
        self._sync_toolbar()
        self._refresh(reset_lanes=True)

    def set_status_message(
        self,
        text: str,
        severity: ValidationSeverity = ValidationSeverity.ALLOWED,
    ) -> None:
        """Show an integration-specific hint without reaching into private widgets."""
        self._set_status(text, severity)

    def preview_command(self, command: ScheduleCommand) -> PreviewResult:
        return self._controller.preview(command)

    def apply_command(self, command: ScheduleCommand) -> ControllerResult:
        result = self._controller.commit(command)
        self._handle_result(result)
        return result

    def recalculate(self) -> ControllerResult:
        result = self._controller.recalculate()
        self._handle_result(result)
        return result

    def undo(self) -> ControllerResult:
        result = self._controller.undo()
        self._handle_result(result)
        return result

    def redo(self) -> ControllerResult:
        result = self._controller.redo()
        self._handle_result(result)
        return result

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._options.fit_to_width and hasattr(self, "_timeline_view"):
            QtCore.QTimer.singleShot(0, self._refresh_after_resize)

    def _make_toolbar(self) -> QtWidgets.QToolBar:
        toolbar = QtWidgets.QToolBar(self)
        toolbar.setIconSize(QtCore.QSize(16, 16))
        toolbar.setMovable(False)

        self._previous_action = toolbar.addAction("←")
        self._previous_action.setToolTip("Предыдущий период")
        self._today_action = toolbar.addAction("Сегодня")
        self._next_action = toolbar.addAction("→")
        self._next_action.setToolTip("Следующий период")
        toolbar.addSeparator()

        self._scale_combo = QtWidgets.QComboBox(toolbar)
        self._scale_combo.setToolTip("Масштаб времени")
        self._scale_combo.addItem("Месяц", (TimeScale.MONTH, 14.0))
        self._scale_combo.addItem("Неделя", (TimeScale.WEEK, 28.0))
        self._scale_combo.addItem("День", (TimeScale.DAY, 42.0))
        self._scale_combo.addItem("Крупно", (TimeScale.DAY, 70.0))
        toolbar.addWidget(self._scale_combo)

        self._fit_action = toolbar.addAction("Вписать")
        self._fit_action.setCheckable(True)
        self._fit_action.setToolTip("Растянуть видимый период на всю ширину")
        self._all_days_action = toolbar.addAction("Все дни")
        self._all_days_action.setCheckable(True)
        self._all_days_action.setToolTip("Всегда подписывать каждый день периода")
        toolbar.addSeparator()

        self._lane_combo = QtWidgets.QComboBox(toolbar)
        self._lane_combo.setToolTip("Структура рельсов")
        self._lane_combo.addItem("Группы", LaneLayout.NESTED)
        self._lane_combo.addItem("1 строка = 1 рельс", LaneLayout.FLAT)
        toolbar.addWidget(self._lane_combo)

        self._layout_combo = QtWidgets.QComboBox(toolbar)
        self._layout_combo.setToolTip("Отображение plan/fact")
        self._layout_combo.addItem("План / факт", LayerLayout.OVERLAY)
        self._layout_combo.addItem("Слои внутри", LayerLayout.STACKED)
        self._layout_combo.addItem("Слои-рельсы", LayerLayout.SEPARATE_ROWS)
        toolbar.addWidget(self._layout_combo)

        self._fill_action = toolbar.addAction("Вся высота")
        self._fill_action.setCheckable(True)
        toolbar.addSeparator()

        self._header_combo = QtWidgets.QComboBox(toolbar)
        self._header_combo.setToolTip("Вариант шапки")
        self._header_combo.addItem("Шапка: календарь", HeaderStyle.CALENDAR)
        self._header_combo.addItem("Шапка: компактно", HeaderStyle.COMPACT)
        self._header_combo.addItem("Шапка: Y / M / D", HeaderStyle.STACKED_DATE)
        toolbar.addWidget(self._header_combo)

        self._dependencies_action = toolbar.addAction("Связи")
        self._dependencies_action.setCheckable(True)
        self._sequence_action = toolbar.addAction("Порядок")
        self._sequence_action.setCheckable(True)
        self._sequence_action.setToolTip("Линии последовательности подразделений")

        toolbar.addSeparator()
        self._recalculate_action = toolbar.addAction("Пересчитать")
        self._undo_action = toolbar.addAction("Отменить")
        self._redo_action = toolbar.addAction("Повторить")
        self._sync_toolbar()
        return toolbar

    def _connect_signals(self) -> None:
        self._lane_view.rowsChanged.connect(self._refresh_rows)
        self._timeline_view.selectGroupRequested.connect(self._scene.select_group)
        self._timeline_view.horizontalScrollBar().valueChanged.connect(
            self._header.set_offset
        )
        self._timeline_view.verticalScrollBar().valueChanged.connect(
            self._lane_view.verticalScrollBar().setValue
        )
        self._lane_view.verticalScrollBar().valueChanged.connect(
            self._timeline_view.verticalScrollBar().setValue
        )
        self._scene.previewChanged.connect(self._on_preview)
        self._scene.commandCommitted.connect(self._on_scene_commit)
        self._scene.commandRejected.connect(self._on_scene_reject)
        self._scene.itemActivated.connect(self.itemActivated)
        self._scene.selectionChanged.connect(self._emit_selection)

        self._previous_action.triggered.connect(lambda: self._shift_period(-1))
        self._next_action.triggered.connect(lambda: self._shift_period(1))
        self._today_action.triggered.connect(self._show_today)
        self._scale_combo.currentIndexChanged.connect(self._change_scale)
        self._fit_action.toggled.connect(self._toggle_fit)
        self._all_days_action.toggled.connect(self._toggle_all_days)
        self._lane_combo.currentIndexChanged.connect(self._change_lane_layout)
        self._layout_combo.currentIndexChanged.connect(self._change_layer_layout)
        self._fill_action.toggled.connect(self._toggle_fill)
        self._header_combo.currentIndexChanged.connect(self._change_header)
        self._dependencies_action.toggled.connect(self._toggle_dependencies)
        self._sequence_action.toggled.connect(self._toggle_sequence_dependencies)
        self._recalculate_action.triggered.connect(self.recalculate)
        self._undo_action.triggered.connect(self.undo)
        self._redo_action.triggered.connect(self.redo)

    def _refresh(self, *, reset_lanes: bool = False) -> None:
        self._apply_effective_options()
        if reset_lanes or not self._lane_view.visible_rows():
            self._lane_view.set_lanes(
                self.model.lanes,
                grouped=self._options.lane_layout is LaneLayout.NESTED,
                layers_by_lane=self._layers_by_lane(),
                separate_layers=(
                    self._options.layer_layout is LayerLayout.SEPARATE_ROWS
                ),
            )
        else:
            self._refresh_rows()
        self._update_actions()

    def _apply_effective_options(self) -> None:
        effective = self._options
        if self._options.fit_to_width:
            duration_days = (
                self._options.date_to - self._options.date_from
            ).total_seconds() / 86_400
            viewport_width = max(1, self._timeline_view.viewport().width() - 2)
            effective = replace(
                self._options,
                pixels_per_day=max(1.0, viewport_width / duration_days),
            )
            horizontal_policy = QtCore.Qt.ScrollBarAlwaysOff
        else:
            horizontal_policy = QtCore.Qt.ScrollBarAlwaysOn
        self._effective_options = effective
        self._timeline_view.setHorizontalScrollBarPolicy(horizontal_policy)
        self._scene.set_options(effective)
        self._header.set_options(effective)
        self._corner.setFixedHeight(effective.header_height)
        self._corner.setText(effective.lane_panel_header)
        self._lane_view.setMinimumWidth(effective.lane_panel_min_width)
        self._lane_view.setMaximumWidth(effective.lane_panel_max_width)
        self._lane_view.set_panel_style(effective.lane_panel_style)
        self._lane_view.set_row_height(round(effective.lane_height))

    def _layers_by_lane(self) -> dict[object, tuple[str, ...]]:
        result: dict[object, set[str]] = defaultdict(set)
        for item in self.model.items:
            result[item.lane_id].add(item.layer)
        order = {"plan": 0, "fact": 1}
        return {
            lane_id: tuple(sorted(layers, key=lambda layer: (order.get(layer, 2), layer)))
            for lane_id, layers in result.items()
        }

    def _refresh_rows(self) -> None:
        rows = self._lane_view.visible_rows()
        self._scene.rebuild(self.model, rows)
        self._header.set_offset(self._timeline_view.horizontalScrollBar().value())

    def _refresh_after_resize(self) -> None:
        if not self._options.fit_to_width:
            return
        self._apply_effective_options()
        self._refresh_rows()

    def _handle_result(self, result: ControllerResult) -> None:
        if result.success:
            self._refresh(reset_lanes=True)
            self.modelChanged.emit(result.model)
            self.commandCommitted.emit(result)
            message = result.message or "Изменение применено"
            if result.validation.messages:
                message = "; ".join(result.validation.messages)
            self._set_status(message, result.validation.severity)
        else:
            self.commandRejected.emit(result)
            self._set_status(
                result.message or "; ".join(result.validation.messages),
                ValidationSeverity.FORBIDDEN,
            )
        self._update_actions()

    def _on_scene_commit(self, result: ControllerResult) -> None:
        QtCore.QTimer.singleShot(0, lambda: self._handle_result(result))

    def _on_scene_reject(self, result: ControllerResult) -> None:
        QtCore.QTimer.singleShot(0, lambda: self._handle_result(result))

    def _on_preview(self, preview: PreviewResult) -> None:
        self.previewChanged.emit(preview)
        messages = preview.validation.messages
        if messages:
            self._set_status("; ".join(messages), preview.validation.severity)
        else:
            self._set_status("Можно применить")

    def _emit_selection(self) -> None:
        item_ids = tuple(
            item.schedule_item.id
            for item in self._scene.selectedItems()
            if hasattr(item, "schedule_item")
        )
        self.selectionChanged.emit(item_ids)

    def _set_status(
        self,
        text: str,
        severity: ValidationSeverity = ValidationSeverity.ALLOWED,
    ) -> None:
        colors = {
            ValidationSeverity.ALLOWED: ("#ecfdf5", "#166534"),
            ValidationSeverity.WARNING: ("#fffbeb", "#92400e"),
            ValidationSeverity.FORBIDDEN: ("#fef2f2", "#991b1b"),
        }
        background, foreground = colors[severity]
        self._status.setText(text)
        self._status.setStyleSheet(
            f"background: {background}; color: {foreground}; border-top: 1px solid #e5e7eb;"
        )

    def _shift_period(self, direction: int) -> None:
        span = self._options.date_to - self._options.date_from
        self.set_view_options(self._options.shifted(span * direction))

    def _show_today(self) -> None:
        now = datetime.now(self._options.date_from.tzinfo)
        span = self._options.date_to - self._options.date_from
        offset_days = int(span.total_seconds() / 86_400 / 3)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=offset_days
        )
        self.set_view_options(
            replace(self._options, date_from=start, date_to=start + span)
        )

    def _change_scale(self, index: int) -> None:
        if self._building_toolbar or index < 0:
            return
        scale, pixels = self._scale_combo.itemData(index)
        self.set_view_options(
            replace(self._options, scale=scale, pixels_per_day=pixels)
        )

    def _toggle_fit(self, checked: bool) -> None:
        if not self._building_toolbar:
            self.set_view_options(replace(self._options, fit_to_width=checked))

    def _toggle_all_days(self, checked: bool) -> None:
        if not self._building_toolbar:
            self.set_view_options(replace(self._options, show_all_days=checked))

    def _change_lane_layout(self, index: int) -> None:
        if not self._building_toolbar and index >= 0:
            self.set_view_options(
                replace(self._options, lane_layout=self._lane_combo.itemData(index))
            )

    def _change_layer_layout(self, index: int) -> None:
        if not self._building_toolbar and index >= 0:
            self.set_view_options(
                replace(self._options, layer_layout=self._layout_combo.itemData(index))
            )

    def _toggle_fill(self, checked: bool) -> None:
        if not self._building_toolbar:
            mode = ItemHeightMode.FILL if checked else ItemHeightMode.COMPACT
            self.set_view_options(replace(self._options, item_height_mode=mode))

    def _change_header(self, index: int) -> None:
        if self._building_toolbar or index < 0:
            return
        style = self._header_combo.itemData(index)
        self.set_view_options(
            replace(
                self._options,
                header_style=style,
                header_bold=style is HeaderStyle.STACKED_DATE,
            )
        )

    def _toggle_dependencies(self, checked: bool) -> None:
        if not self._building_toolbar:
            self.set_view_options(replace(self._options, show_dependencies=checked))

    def _toggle_sequence_dependencies(self, checked: bool) -> None:
        if not self._building_toolbar:
            self.set_view_options(
                replace(self._options, show_sequence_dependencies=checked)
            )

    def _sync_toolbar(self) -> None:
        if not hasattr(self, "_scale_combo"):
            return
        self._building_toolbar = True
        best_index = min(
            range(self._scale_combo.count()),
            key=lambda index: abs(
                self._scale_combo.itemData(index)[1] - self._options.pixels_per_day
            ),
        )
        self._scale_combo.setCurrentIndex(best_index)
        self._lane_combo.setCurrentIndex(
            max(0, self._lane_combo.findData(self._options.lane_layout))
        )
        self._layout_combo.setCurrentIndex(
            max(0, self._layout_combo.findData(self._options.layer_layout))
        )
        self._header_combo.setCurrentIndex(
            max(0, self._header_combo.findData(self._options.header_style))
        )
        self._fit_action.setChecked(self._options.fit_to_width)
        self._all_days_action.setChecked(self._options.show_all_days)
        self._fill_action.setChecked(
            self._options.item_height_mode is ItemHeightMode.FILL
        )
        self._dependencies_action.setChecked(self._options.show_dependencies)
        self._sequence_action.setChecked(self._options.show_sequence_dependencies)
        self._building_toolbar = False

    def _update_actions(self) -> None:
        if not hasattr(self, "_undo_action"):
            return
        self._undo_action.setEnabled(self._controller.can_undo)
        self._redo_action.setEnabled(self._controller.can_redo)
        self._recalculate_action.setEnabled(self._controller.services.scheduler is not None)
        self._sequence_action.setEnabled(self._options.show_dependencies)


def _default_options() -> ViewOptions:
    now = datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=3)
    return ViewOptions(start, start + timedelta(days=31))
