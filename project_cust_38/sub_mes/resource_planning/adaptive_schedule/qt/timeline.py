from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Hashable
from datetime import datetime, timedelta

from PyQt5 import QtCore, QtGui, QtWidgets

from ..commands import (
    BatchCommand,
    MoveItem,
    ResizeEdge,
    ResizeItem,
    ResizeItemCells,
    ScheduleCommand,
    ShiftItemCells,
)
from ..controller import PreviewResult, ScheduleController
from ..domain import AxisCell, DependencyType, ScheduleItem, ScheduleMode, ScheduleModel
from ..metrics import format_slice_tooltip, metric_profiles, normalization_maxima
from ..resolution import ResolvedBand, ResolvedSchedule, resolve_schedule
from ..services import ValidationResult, ValidationSeverity
from ..view_options import ItemHeightMode, LayerLayout, ViewOptions
from .geometry import TimelineGeometry
from .lane_model import VisibleLaneRow


class TimelineGridItem(QtWidgets.QGraphicsItem):
    def __init__(
        self,
        geometry: TimelineGeometry,
        rows: list[VisibleLaneRow],
        axis_cells: tuple[AxisCell, ...] = (),
    ) -> None:
        super().__init__()
        self.geometry = geometry
        self.rows = rows
        self.axis_cells = axis_cells
        self.setZValue(-100)

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(
            0,
            0,
            self.geometry.width,
            len(self.rows) * self.geometry.options.lane_height,
        )

    def paint(self, painter, option, widget=None) -> None:
        del widget
        rect = option.exposedRect.intersected(self.boundingRect())
        opts = self.geometry.options
        lane_height = opts.lane_height
        width = self.geometry.width

        painter.fillRect(rect, QtGui.QColor("#ffffff"))
        for row_index, row in enumerate(self.rows):
            top = row_index * lane_height
            if top + lane_height < rect.top() or top > rect.bottom():
                continue
            if row.kind == "group":
                painter.fillRect(
                    QtCore.QRectF(rect.left(), top, rect.width(), lane_height),
                    QtGui.QColor("#eef2f7"),
                )

        if opts.show_weekends and opts.preserve_nonworking_cells:
            overlay = QtGui.QColor(opts.weekend_background)
            overlay.setAlpha(210)
            for cell in self.axis_cells:
                if cell.is_working or cell.start is None or cell.end is None:
                    continue
                left = self.geometry.date_to_x(cell.start)
                right = self.geometry.date_to_x(cell.end)
                cell_rect = QtCore.QRectF(
                    left,
                    rect.top(),
                    right - left,
                    rect.height(),
                )
                if cell_rect.intersects(rect):
                    painter.fillRect(cell_rect.intersected(rect), overlay)

        first_day = max(0, math.floor(rect.left() / opts.pixels_per_day) - 1)
        last_day = min(
            math.ceil(width / opts.pixels_per_day),
            math.ceil(rect.right() / opts.pixels_per_day) + 1,
        )
        today = datetime.now(opts.date_from.tzinfo).date()
        for day_index in range(first_day, last_day + 1):
            day = opts.date_from + timedelta(days=day_index)
            x = day_index * opts.pixels_per_day
            day_rect = QtCore.QRectF(x, rect.top(), opts.pixels_per_day, rect.height())
            if opts.show_weekends and opts.is_non_working_day(day):
                color = QtGui.QColor(opts.weekend_background)
                color.setAlpha(210)
                painter.fillRect(day_rect, color)
            if opts.show_today and day.date() == today:
                painter.fillRect(day_rect, QtGui.QColor(219, 234, 254, 120))
            painter.setPen(QtGui.QPen(QtGui.QColor("#d8dde5"), 1))
            painter.drawLine(QtCore.QPointF(x, rect.top()), QtCore.QPointF(x, rect.bottom()))

        painter.setPen(QtGui.QPen(QtGui.QColor("#e1e5eb"), 1))
        for row_index in range(len(self.rows) + 1):
            y = row_index * lane_height
            if rect.top() - 1 <= y <= rect.bottom() + 1:
                painter.drawLine(QtCore.QPointF(rect.left(), y), QtCore.QPointF(rect.right(), y))


class DependencyGraphicsItem(QtWidgets.QGraphicsPathItem):
    def __init__(self, start: QtCore.QPointF, end: QtCore.QPointF, hard: bool) -> None:
        super().__init__()
        path = QtGui.QPainterPath(start)
        middle = max(start.x() + 18, (start.x() + end.x()) / 2)
        path.lineTo(middle, start.y())
        path.lineTo(middle, end.y())
        path.lineTo(end)
        self.setPath(path)
        color = QtGui.QColor("#667085") if hard else QtGui.QColor("#98a2b3")
        pen = QtGui.QPen(color, 1.4, QtCore.Qt.SolidLine if hard else QtCore.Qt.DashLine)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setZValue(-5)


class ScheduleBlockItem(QtWidgets.QGraphicsRectItem):
    HANDLE_WIDTH = 7.0

    def __init__(
        self,
        item: ScheduleItem,
        rect: QtCore.QRectF,
        scene: "TimelineScene",
        resolved_band: ResolvedBand,
        normalization_max: float,
    ) -> None:
        super().__init__(0, 0, rect.width(), rect.height())
        self.schedule_item = item
        self.timeline_scene = scene
        self.resolved_band = resolved_band
        self.normalization_max = normalization_max
        self._metric_profiles = metric_profiles(resolved_band, normalization_max)
        self.setPos(rect.topLeft())
        self.setZValue(20 if item.layer == "fact" else 10)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setToolTip(self._tooltip())
        self._mode: str | None = None
        self._press_scene_pos = QtCore.QPointF()
        self._original_pos = QtCore.QPointF()
        self._original_rect = QtCore.QRectF()
        self._pending_command: ScheduleCommand | None = None
        self._preview_validation = ValidationResult.allowed()
        self._drag_blocks: list[ScheduleBlockItem] = []
        self._drag_positions: dict[Hashable, QtCore.QPointF] = {}
        self._drag_rects: dict[Hashable, QtCore.QRectF] = {}
        self._pending_cell_delta = 0
        self._pending_target_cell_id: Hashable | None = None

    def _tooltip(self) -> str:
        item = self.schedule_item
        start = (
            self.resolved_band.start.strftime("%d.%m.%Y %H:%M")
            if self.resolved_band.start
            else "—"
        )
        end = (
            self.resolved_band.end.strftime("%d.%m.%Y %H:%M")
            if self.resolved_band.end
            else "—"
        )
        subtitle = f"\n{item.subtitle}" if item.subtitle else ""
        details = ""
        if self._has_metric_profile:
            details = (
                f"\nΣ мощность: {self.resolved_band.total_capacity:g}"
                f"; план: {self.resolved_band.total_plan:g}"
                f"; факт: {self.resolved_band.total_fact:g}"
            )
        return f"{item.title}{subtitle}\n{start} — {end}\nСлой: {item.layer}{details}"

    @property
    def _has_metric_profile(self) -> bool:
        return (
            self.timeline_scene.options.show_slice_metrics
            and self.resolved_band.has_metrics
        )

    @property
    def is_editable(self) -> bool:
        return self.can_move or self.can_resize

    @property
    def uses_cell_axis(self) -> bool:
        return bool(self.timeline_scene.model.axis_cells)

    @property
    def can_move(self) -> bool:
        item = self.schedule_item
        if not item.movable or item.locked:
            return False
        if self.uses_cell_axis:
            return item.start is not None or item.end is not None
        return item.is_scheduled

    @property
    def can_resize(self) -> bool:
        item = self.schedule_item
        if not item.resizable or item.locked or not item.is_scheduled:
            return False
        if not self.uses_cell_axis:
            return True
        return item.effective_schedule_mode is ScheduleMode.FIXED_RANGE

    def hoverMoveEvent(self, event) -> None:
        self._update_slice_tooltip(event.pos().x())
        x = event.pos().x()
        if self.schedule_item.locked or not self.is_editable:
            self.setCursor(QtCore.Qt.ForbiddenCursor)
        elif x <= self.HANDLE_WIDTH and self.can_resize:
            self.setCursor(QtCore.Qt.SizeHorCursor)
        elif x >= self.rect().width() - self.HANDLE_WIDTH and self.can_resize:
            self.setCursor(QtCore.Qt.SizeHorCursor)
        elif self.can_move:
            self.setCursor(QtCore.Qt.OpenHandCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.setToolTip(self._tooltip())
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if (
            event.button() != QtCore.Qt.LeftButton
            or self.schedule_item.locked
            or not self.is_editable
        ):
            super().mousePressEvent(event)
            return
        if event.modifiers() & QtCore.Qt.ControlModifier:
            self.setSelected(not self.isSelected())
            if not self.isSelected():
                event.accept()
                return
        elif not self.isSelected():
            self.timeline_scene.clearSelection()
            self.setSelected(True)
        local_x = event.pos().x()
        if local_x <= self.HANDLE_WIDTH and self.can_resize:
            self._mode = "resize_start"
        elif local_x >= self.rect().width() - self.HANDLE_WIDTH and self.can_resize:
            self._mode = "resize_end"
        elif self.can_move:
            self._mode = "move"
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        else:
            super().mousePressEvent(event)
            return
        self._press_scene_pos = event.scenePos()
        self._original_pos = self.pos()
        self._original_rect = QtCore.QRectF(self.rect())
        self._pending_command = None
        self._pending_cell_delta = 0
        self._pending_target_cell_id = None
        self._drag_blocks = (
            self.timeline_scene.movable_selection(self)
            if self._mode == "move" and self.timeline_scene.options.cascade_multi_move
            else [self]
        )
        self._drag_positions = {
            block.schedule_item.id: QtCore.QPointF(block.pos())
            for block in self._drag_blocks
        }
        self._drag_rects = {
            block.schedule_item.id: QtCore.QRectF(block.rect())
            for block in self._drag_blocks
        }
        for block in self._drag_blocks:
            block.setOpacity(0.78)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._mode is None:
            super().mouseMoveEvent(event)
            return
        delta = event.scenePos() - self._press_scene_pos
        geometry = self.timeline_scene.geometry
        original_left = self._original_pos.x()
        original_right = original_left + self._original_rect.width()
        if self.uses_cell_axis:
            self._move_on_cell_axis(event, delta, original_left, original_right)
        else:
            min_width = max(
                6.0,
                geometry.options.snap.total_seconds()
                / 86_400
                * geometry.options.pixels_per_day,
            )
            if self._mode == "move":
                new_x = geometry.snap_x(original_left + delta.x())
                if len(self._drag_blocks) > 1:
                    snapped_delta = new_x - original_left
                    for block in self._drag_blocks:
                        position = self._drag_positions[block.schedule_item.id]
                        block.setPos(position.x() + snapped_delta, position.y())
                else:
                    lane_id = self._preview_lane_id(event.scenePos().y())
                    new_y = self.timeline_scene.block_y(
                        lane_id,
                        self.schedule_item.layer,
                    )
                    self.setPos(new_x, new_y)
                    self.setRect(
                        0,
                        0,
                        self._original_rect.width(),
                        self._original_rect.height(),
                    )
            elif self._mode == "resize_start":
                new_x = min(
                    geometry.snap_x(original_left + delta.x()),
                    original_right - min_width,
                )
                self.setPos(new_x, self._original_pos.y())
                self.setRect(0, 0, original_right - new_x, self._original_rect.height())
            else:
                new_right = max(
                    geometry.snap_x(original_right + delta.x()),
                    original_left + min_width,
                )
                self.setPos(self._original_pos)
                self.setRect(0, 0, new_right - original_left, self._original_rect.height())

        self._pending_command = self._build_command()
        preview = self.timeline_scene.preview_command(self._pending_command)
        self._preview_validation = preview.validation
        for block in self._drag_blocks:
            block._preview_validation = preview.validation
            block.update()
        event.accept()

    def _move_on_cell_axis(
        self,
        event,
        delta: QtCore.QPointF,
        original_left: float,
        original_right: float,
    ) -> None:
        if self._mode == "move":
            snapped = self.timeline_scene.snap_band_move(
                self.resolved_band,
                original_left + delta.x(),
            )
            if snapped is None:
                return
            _, _, cell_delta = snapped
            self._pending_cell_delta = cell_delta
            lane_id = self._preview_lane_id(event.scenePos().y())
            for block in self._drag_blocks:
                block._pending_cell_delta = cell_delta
                shifted = self.timeline_scene.shifted_band_geometry(
                    block.resolved_band,
                    cell_delta,
                )
                if shifted is None:
                    continue
                left, right = shifted
                position = self._drag_positions[block.schedule_item.id]
                y = (
                    self.timeline_scene.block_y(lane_id, self.schedule_item.layer)
                    if block is self and len(self._drag_blocks) == 1
                    else position.y()
                )
                block.setPos(left, y)
                block.setRect(
                    0,
                    0,
                    max(3.0, right - left),
                    self._drag_rects[block.schedule_item.id].height(),
                )
        else:
            edge = ResizeEdge.START if self._mode == "resize_start" else ResizeEdge.END
            desired = original_left + delta.x() if edge is ResizeEdge.START else original_right + delta.x()
            snapped = self.timeline_scene.snap_resize_edge(
                self.resolved_band,
                edge,
                desired,
            )
            if snapped is None:
                return
            target_cell_id, edge_x = snapped
            self._pending_target_cell_id = target_cell_id
            if edge is ResizeEdge.START:
                self.setPos(edge_x, self._original_pos.y())
                self.setRect(
                    0,
                    0,
                    max(3.0, original_right - edge_x),
                    self._original_rect.height(),
                )
            else:
                self.setPos(self._original_pos)
                self.setRect(
                    0,
                    0,
                    max(3.0, edge_x - original_left),
                    self._original_rect.height(),
                )

    def _preview_lane_id(self, scene_y: float) -> Hashable:
        lane_id = None
        if self.timeline_scene.options.allow_lane_change:
            lane_id = self.timeline_scene.lane_at_y(
                scene_y,
                self.schedule_item.layer,
            )
        return self.schedule_item.lane_id if lane_id is None else lane_id

    def mouseReleaseEvent(self, event) -> None:
        if self._mode is None:
            super().mouseReleaseEvent(event)
            return
        for block in self._drag_blocks:
            block.setOpacity(1.0)
        self.unsetCursor()
        if self._pending_command is not None and self._preview_validation.can_commit:
            self.timeline_scene.commit_command(self._pending_command)
        else:
            for block in self._drag_blocks:
                block.setPos(self._drag_positions[block.schedule_item.id])
                block.setRect(self._drag_rects[block.schedule_item.id])
        self._mode = None
        self._pending_command = None
        for block in self._drag_blocks:
            block._preview_validation = ValidationResult.allowed()
            block._pending_cell_delta = 0
            block._pending_target_cell_id = None
            block.update()
        self._drag_blocks = []
        self._drag_positions = {}
        self._drag_rects = {}
        self._pending_cell_delta = 0
        self._pending_target_cell_id = None
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        self.timeline_scene.itemActivated.emit(self.schedule_item.id)
        super().mouseDoubleClickEvent(event)

    def _build_command(self) -> ScheduleCommand:
        if self.uses_cell_axis:
            return self._build_cell_command()
        geometry = self.timeline_scene.geometry
        if self._mode == "move":
            if len(self._drag_blocks) > 1:
                commands: list[ScheduleCommand] = []
                anchor_start = geometry.snap_date(
                    geometry.x_to_date(self.pos().x())
                )
                shift = anchor_start - self.schedule_item.start  # type: ignore[operator]
                for block in self._drag_blocks:
                    item = block.schedule_item
                    commands.append(
                        MoveItem(
                            item.id,
                            item.start + shift,  # type: ignore[operator]
                            item.end + shift,  # type: ignore[operator]
                            item.lane_id,
                        )
                    )
                return BatchCommand(tuple(commands))
            start = geometry.snap_date(geometry.x_to_date(self.pos().x()))
            duration = self.schedule_item.end - self.schedule_item.start  # type: ignore[operator]
            lane_id = self.timeline_scene.lane_at_y(
                self.pos().y() + self.rect().height() / 2,
                self.schedule_item.layer,
            )
            return MoveItem(
                self.schedule_item.id,
                start,
                start + duration,
                lane_id,
            )
        if self._mode == "resize_start":
            return ResizeItem(
                self.schedule_item.id,
                ResizeEdge.START,
                geometry.snap_date(geometry.x_to_date(self.pos().x())),
            )
        return ResizeItem(
            self.schedule_item.id,
            ResizeEdge.END,
            geometry.snap_date(
                geometry.x_to_date(self.pos().x() + self.rect().width())
            ),
        )

    def _build_cell_command(self) -> ScheduleCommand:
        if self._mode == "move":
            if len(self._drag_blocks) > 1:
                return BatchCommand(
                    tuple(
                        ShiftItemCells(
                            block.schedule_item.id,
                            self._pending_cell_delta,
                            block.schedule_item.lane_id,
                        )
                        for block in self._drag_blocks
                    )
                )
            lane_id = self.timeline_scene.lane_at_y(
                self.pos().y() + self.rect().height() / 2,
                self.schedule_item.layer,
            )
            if not self.timeline_scene.options.allow_lane_change or lane_id is None:
                lane_id = self.schedule_item.lane_id
            return ShiftItemCells(
                self.schedule_item.id,
                self._pending_cell_delta,
                lane_id,
            )

        edge = ResizeEdge.START if self._mode == "resize_start" else ResizeEdge.END
        target = self._pending_target_cell_id
        if target is None:
            cell = (
                self.resolved_band.first_cell
                if edge is ResizeEdge.START
                else self.resolved_band.last_cell
            )
            if cell is None:
                raise ValueError("Resolved band has no axis cell for resize")
            target = cell.id
        return ResizeItemCells(self.schedule_item.id, edge, target)

    def paint(self, painter, option, widget=None) -> None:
        del widget
        rect = self.rect()
        base = _item_color(self.schedule_item, self.timeline_scene.model)
        if option.state & QtWidgets.QStyle.State_Selected:
            base = base.lighter(112)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        border = base.darker(128)
        if self._preview_validation.severity is ValidationSeverity.WARNING:
            border = QtGui.QColor("#d97706")
        elif self._preview_validation.severity is ValidationSeverity.FORBIDDEN:
            border = QtGui.QColor("#dc2626")

        background = base.lighter(172) if self._has_metric_profile else base
        painter.setBrush(QtGui.QBrush(background))
        painter.setPen(QtGui.QPen(border, 1.5))
        painter.drawRoundedRect(rect.adjusted(0.8, 0.8, -0.8, -0.8), 5, 5)

        if self._has_metric_profile:
            self._paint_metric_profile(painter, rect, option.exposedRect, base)

        self._paint_non_working_overlay(painter, rect)

        if self.schedule_item.progress is not None:
            progress_rect = QtCore.QRectF(
                rect.left(),
                rect.bottom() - 4,
                rect.width() * self.schedule_item.progress,
                4,
            )
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor("#0f766e"))
            painter.drawRoundedRect(progress_rect, 2, 2)

        if self.schedule_item.layer == "fact" and not self._has_metric_profile:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 80), 1))
            x = rect.left() - rect.height()
            while x < rect.right():
                painter.drawLine(
                    QtCore.QPointF(x, rect.bottom()),
                    QtCore.QPointF(x + rect.height(), rect.top()),
                )
                x += 8

        if (
            self.timeline_scene.options.show_daily_allocations
            and not self._has_metric_profile
        ):
            self._paint_daily_allocations(painter, rect, base)

        if self.timeline_scene.options.show_item_labels:
            painter.setPen(QtGui.QColor("#102038"))
            font = painter.font()
            font.setPointSizeF(max(7.5, min(10.0, rect.height() * 0.28)))
            painter.setFont(font)
            text_rect = rect.adjusted(7, 1, -7, -1)
            if self.schedule_item.subtitle and rect.height() >= 27:
                title_rect = QtCore.QRectF(
                    text_rect.left(),
                    text_rect.top(),
                    text_rect.width(),
                    text_rect.height() * 0.52,
                )
                subtitle_rect = QtCore.QRectF(
                    text_rect.left(),
                    title_rect.bottom() - 1,
                    text_rect.width(),
                    text_rect.height() * 0.48,
                )
                painter.drawText(title_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                                 self.schedule_item.title)
                subtitle_font = QtGui.QFont(font)
                subtitle_font.setBold(True)
                subtitle_font.setPointSizeF(max(7.0, font.pointSizeF() - 0.5))
                painter.setFont(subtitle_font)
                painter.drawText(subtitle_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                                 self.schedule_item.subtitle)
            else:
                label = self.schedule_item.title
                if self.schedule_item.subtitle:
                    label = f"{label} · {self.schedule_item.subtitle}"
                painter.drawText(
                    text_rect,
                    QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                    label,
                )

        if (
            option.state & QtWidgets.QStyle.State_MouseOver
            and self.can_resize
        ):
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(255, 255, 255, 150))
            painter.drawRoundedRect(QtCore.QRectF(1, 4, 3, rect.height() - 8), 1, 1)
            painter.drawRoundedRect(
                QtCore.QRectF(rect.width() - 4, 4, 3, rect.height() - 8),
                1,
                1,
            )

    def _paint_metric_profile(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRectF,
        exposed: QtCore.QRectF,
        base: QtGui.QColor,
    ) -> None:
        if self.normalization_max <= 0:
            return
        style = self.timeline_scene.options.metrics_style
        fact_width = style.fact_width_ratio
        painter.save()
        painter.setClipRect(rect.adjusted(1, 1, -1, -1))
        painter.setPen(QtCore.Qt.NoPen)

        for profile in self._metric_profiles:
            cell = profile.resolved.cell
            bounds = self.timeline_scene.shifted_cell_bounds(
                cell.id,
                self._pending_cell_delta,
            )
            if bounds is None:
                continue
            scene_left, scene_right = bounds
            left = scene_left - self.pos().x()
            right = scene_right - self.pos().x()
            cell_rect = QtCore.QRectF(left, rect.top(), right - left, rect.height())
            cell_rect = cell_rect.intersected(rect)
            if cell_rect.isEmpty() or not cell_rect.intersects(exposed):
                continue

            self._fill_metric_value(
                painter,
                cell_rect,
                profile.capacity_ratio,
                profile.resolved.capacity,
                _with_alpha(base, style.capacity_alpha),
                1.0,
            )
            self._fill_metric_value(
                painter,
                cell_rect.adjusted(0.7, 0, -0.7, 0),
                profile.plan_ratio,
                profile.resolved.plan,
                _with_alpha(base.darker(112), style.plan_alpha),
                1.0,
            )
            self._fill_metric_value(
                painter,
                cell_rect,
                profile.fact_ratio,
                profile.resolved.fact,
                _with_alpha(base.darker(132), style.fact_alpha),
                fact_width,
            )

            if (
                profile.fact_ratio is not None
                and profile.plan_ratio is not None
                and profile.fact_ratio > profile.plan_ratio
            ):
                overflow = _qcolor(style.overflow_color, base.darker(170))
                overflow = _with_alpha(overflow, min(1.0, style.fact_alpha + 0.12))
                lower = min(1.0, max(0.0, profile.plan_ratio))
                upper = min(1.0, max(0.0, profile.fact_ratio))
                if upper > lower:
                    width = cell_rect.width() * fact_width
                    x = cell_rect.center().x() - width / 2
                    top = cell_rect.bottom() - cell_rect.height() * upper
                    bottom = cell_rect.bottom() - cell_rect.height() * lower
                    painter.fillRect(QtCore.QRectF(x, top, width, bottom - top), overflow)

            if (
                not cell.is_working
                and self.timeline_scene.options.show_weekends
                and self.timeline_scene.options.preserve_nonworking_cells
            ):
                inactive = QtGui.QColor(self.timeline_scene.options.weekend_background)
                inactive.setAlpha(125)
                painter.fillRect(cell_rect, inactive)

            painter.setPen(QtGui.QPen(QtGui.QColor(15, 23, 42, 55), 1))
            painter.drawLine(cell_rect.topLeft(), cell_rect.bottomLeft())
            painter.setPen(QtCore.Qt.NoPen)
        painter.restore()

    @staticmethod
    def _fill_metric_value(
        painter: QtGui.QPainter,
        cell_rect: QtCore.QRectF,
        ratio: float | None,
        provided_value: float | None,
        color: QtGui.QColor,
        width_ratio: float,
    ) -> None:
        if ratio is None:
            return
        width = cell_rect.width() * width_ratio
        x = cell_rect.center().x() - width / 2
        bounded = min(1.0, max(0.0, ratio))
        if bounded == 0:
            if provided_value is not None:
                painter.fillRect(
                    QtCore.QRectF(x, cell_rect.bottom() - 1.4, width, 1.4),
                    color,
                )
            return
        height = cell_rect.height() * bounded
        painter.fillRect(
            QtCore.QRectF(x, cell_rect.bottom() - height, width, height),
            color,
        )

    def _update_slice_tooltip(self, local_x: float) -> None:
        if not self._has_metric_profile:
            return
        scene_x = self.pos().x() + local_x
        lane = self.timeline_scene.model.lane_by_id.get(self.schedule_item.lane_id)
        for profile in self._metric_profiles:
            cell = profile.resolved.cell
            bounds = self.timeline_scene.shifted_cell_bounds(
                cell.id,
                self._pending_cell_delta,
            )
            if bounds is None:
                continue
            left, right = bounds
            if left <= scene_x < right:
                self.setToolTip(
                    format_slice_tooltip(
                        self.resolved_band,
                        profile.resolved,
                        lane_title=lane.title if lane else "",
                    )
                )
                return
        self.setToolTip(self._tooltip())

    def _paint_non_working_overlay(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRectF,
    ) -> None:
        options = self.timeline_scene.options
        start = self.resolved_band.start
        end = self.resolved_band.end
        if not options.show_weekends or start is None or end is None:
            return
        pixels = options.pixels_per_day
        cursor = start.replace(hour=0, minute=0, second=0, microsecond=0)
        overlay = QtGui.QColor(options.weekend_background)
        overlay.setAlpha(155)
        painter.save()
        painter.setClipRect(rect.adjusted(1, 1, -1, -1))
        while cursor < end:
            if options.is_non_working_day(cursor):
                left = (cursor - start).total_seconds() / 86_400 * pixels
                painter.fillRect(
                    QtCore.QRectF(left, rect.top(), pixels, rect.height()),
                    overlay,
                )
            cursor += timedelta(days=1)
        painter.restore()

    def _paint_daily_allocations(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRectF,
        base: QtGui.QColor,
    ) -> None:
        item = self.schedule_item
        if item.start is None or not item.allocations:
            return
        options = self.timeline_scene.options
        pixels = options.pixels_per_day
        painter.save()
        painter.setClipRect(rect.adjusted(1, 1, -1, -1))
        font = painter.font()
        font.setBold(True)
        font.setPointSizeF(max(7.0, min(10.0, rect.height() * 0.31)))
        painter.setFont(font)
        for allocation in item.allocations:
            left = (allocation.start - item.start).total_seconds() / 86_400 * pixels
            right = (allocation.end - item.start).total_seconds() / 86_400 * pixels
            allocation_rect = QtCore.QRectF(
                left,
                rect.top(),
                max(1.0, right - left),
                rect.height(),
            ).intersected(rect)
            if allocation_rect.isEmpty():
                continue
            fill = base.darker(106 if item.layer == "plan" else 112)
            fill.setAlpha(235)
            painter.fillRect(allocation_rect.adjusted(0.8, 0.8, -0.8, -0.8), fill)
            painter.setPen(QtGui.QPen(base.darker(138), 1))
            painter.drawLine(allocation_rect.topLeft(), allocation_rect.bottomLeft())
            if allocation_rect.width() < 13 or allocation_rect.height() < 14:
                continue
            try:
                label = options.daily_allocation_format.format(
                    amount=allocation.amount,
                )
            except (KeyError, ValueError):
                label = f"{allocation.amount:g}"
            painter.setPen(QtGui.QColor("#102038"))
            painter.drawText(
                allocation_rect.adjusted(1, 1, -1, -1),
                QtCore.Qt.AlignCenter,
                label,
            )
        painter.restore()


class TimelineScene(QtWidgets.QGraphicsScene):
    previewChanged = QtCore.pyqtSignal(object)
    commandCommitted = QtCore.pyqtSignal(object)
    commandRejected = QtCore.pyqtSignal(object)
    itemActivated = QtCore.pyqtSignal(object)

    def __init__(
        self,
        controller: ScheduleController,
        options: ViewOptions,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.options = options
        self.geometry = TimelineGeometry(options)
        self.rows: list[VisibleLaneRow] = []
        self.model = controller.model
        self.resolved = ResolvedSchedule(self.model, ())
        self._row_by_key: dict[tuple[Hashable, str | None], int] = {}
        self._layer_slots: dict[Hashable, dict[str, int]] = {}
        self._blocks: dict[Hashable, ScheduleBlockItem] = {}
        self._axis_cells: tuple[AxisCell, ...] = ()
        self._axis_index_by_id: dict[Hashable, int] = {}

    def set_options(self, options: ViewOptions) -> None:
        self.options = options
        self.geometry = TimelineGeometry(options)

    def rebuild(
        self,
        model: ScheduleModel,
        rows: list[VisibleLaneRow],
    ) -> None:
        self.clear()
        self.model = model
        self.resolved = resolve_schedule(model)
        self._axis_cells = model.axis_cells
        self._axis_index_by_id = {
            cell.id: position for position, cell in enumerate(self._axis_cells)
        }
        self.rows = rows
        self._row_by_key = {
            (row.lane.id, row.layer): index
            for index, row in enumerate(rows)
            if row.kind == "lane" and row.lane is not None
        }
        self._build_layer_slots()
        height = max(1.0, len(rows) * self.options.lane_height)
        self.setSceneRect(0, 0, max(1.0, self.geometry.width), height)
        self.addItem(TimelineGridItem(self.geometry, rows, model.axis_cells))
        self._blocks = {}
        visible_bands = tuple(
            band
            for band in self.resolved.bands
            if self._row_index(band.item.lane_id, band.item.layer) is not None
            and band.start is not None
            and band.end is not None
            and band.end > self.options.date_from
            and band.start < self.options.date_to
        )
        maxima = normalization_maxima(
            visible_bands,
            self.options.normalization_scope,
            self.options.normalization_fixed_max,
        )
        for band in visible_bands:
            item = band.item
            rect = self.block_rect(band)
            if rect is None:
                continue
            block = ScheduleBlockItem(
                item,
                rect,
                self,
                band,
                maxima.get(item.id, band.normalization_max),
            )
            self.addItem(block)
            self._blocks[item.id] = block
        if self.options.show_dependencies:
            self._add_dependencies(model)

    def block_rect(self, band: ResolvedBand) -> QtCore.QRectF | None:
        item = band.item
        row = self._row_index(item.lane_id, item.layer)
        if band.start is None or band.end is None or band.start >= band.end or row is None:
            return None
        if band.end <= self.options.date_from or band.start >= self.options.date_to:
            return None
        left = self.geometry.date_to_x(band.start)
        right = self.geometry.date_to_x(band.end)
        y = self.block_y(item.lane_id, item.layer)
        height = self.block_height(item.lane_id, item.layer)
        return QtCore.QRectF(left, y, max(3.0, right - left), height)

    def block_y(self, lane_id: Hashable, layer: str) -> float:
        row = self._row_index(lane_id, layer)
        if row is None:
            raise KeyError((lane_id, layer))
        margin = 4.0
        if self.options.layer_layout is LayerLayout.SEPARATE_ROWS:
            return self.geometry.row_top(row) + self._vertical_margin(lane_id)
        if (
            self.options.item_height_mode is ItemHeightMode.FILL
            and len(self._layer_slots.get(lane_id, {})) <= 1
        ):
            return self.geometry.row_top(row) + self._vertical_margin(lane_id)
        if self.options.layer_layout is LayerLayout.OVERLAY:
            if layer == "fact":
                return self.geometry.row_top(row) + self.options.lane_height * 0.48
            return self.geometry.row_top(row) + margin
        slot = self._layer_slots.get(lane_id, {}).get(layer, 0)
        count = max(1, len(self._layer_slots.get(lane_id, {})))
        slot_height = (self.options.lane_height - margin * 2) / count
        return self.geometry.row_top(row) + margin + slot * slot_height

    def block_height(self, lane_id: Hashable, layer: str) -> float:
        margin = 4.0
        if self.options.layer_layout is LayerLayout.SEPARATE_ROWS:
            vertical_margin = self._vertical_margin(lane_id)
            return max(6.0, self.options.lane_height - vertical_margin * 2)
        if (
            self.options.item_height_mode is ItemHeightMode.FILL
            and len(self._layer_slots.get(lane_id, {})) <= 1
        ):
            vertical_margin = self._vertical_margin(lane_id)
            return max(6.0, self.options.lane_height - vertical_margin * 2)
        if self.options.layer_layout is LayerLayout.OVERLAY:
            return self.options.lane_height * 0.48 - margin
        count = max(1, len(self._layer_slots.get(lane_id, {})))
        return max(6.0, (self.options.lane_height - margin * 2) / count - 2)

    def lane_at_y(self, y: float, layer: str | None = None) -> Hashable | None:
        row_index = self.geometry.row_at(y, len(self.rows))
        if row_index is None:
            return None
        row = self.rows[row_index]
        if row.kind != "lane" or row.lane is None:
            return None
        if row.layer is not None and layer is not None and row.layer != layer:
            return None
        return row.lane.id

    def snap_band_move(
        self,
        band: ResolvedBand,
        desired_left: float,
    ) -> tuple[float, float, int] | None:
        if band.first_cell is None or band.last_cell is None:
            return None
        first = self._axis_index_by_id.get(band.first_cell.id)
        last = self._axis_index_by_id.get(band.last_cell.id)
        if first is None or last is None:
            return None
        candidates: list[tuple[float, float, int]] = []
        for delta in range(-first, len(self._axis_cells) - last):
            shifted = self.shifted_band_geometry(band, delta)
            if shifted is not None:
                candidates.append((shifted[0], shifted[1], delta))
        if not candidates:
            return None
        return min(candidates, key=lambda value: abs(value[0] - desired_left))

    def shifted_band_geometry(
        self,
        band: ResolvedBand,
        delta: int,
    ) -> tuple[float, float] | None:
        if (
            band.start is None
            or band.end is None
            or band.first_cell is None
            or band.last_cell is None
        ):
            return None
        first = self._axis_index_by_id.get(band.first_cell.id)
        last = self._axis_index_by_id.get(band.last_cell.id)
        if first is None or last is None:
            return None
        target_first = first + delta
        target_last = last + delta
        if (
            target_first < 0
            or target_last < 0
            or target_first >= len(self._axis_cells)
            or target_last >= len(self._axis_cells)
        ):
            return None
        start = _map_cell_coordinate(
            band.start,
            band.first_cell,
            self._axis_cells[target_first],
        )
        end = _map_cell_coordinate(
            band.end,
            band.last_cell,
            self._axis_cells[target_last],
        )
        if start is None or end is None:
            return None
        return self.geometry.date_to_x(start), self.geometry.date_to_x(end)

    def snap_resize_edge(
        self,
        band: ResolvedBand,
        edge: ResizeEdge,
        desired_x: float,
    ) -> tuple[Hashable, float] | None:
        start = band.item.start or band.start
        end = band.item.end or band.end
        if start is None or end is None:
            return None
        candidates: list[tuple[Hashable, float]] = []
        for cell in self._axis_cells:
            value = cell.start if edge is ResizeEdge.START else cell.end
            if value is None:
                continue
            if edge is ResizeEdge.START and value >= end:
                continue
            if edge is ResizeEdge.END and value <= start:
                continue
            candidates.append((cell.id, self.geometry.date_to_x(value)))
        if not candidates:
            return None
        return min(candidates, key=lambda value: abs(value[1] - desired_x))

    def shifted_cell_bounds(
        self,
        cell_id: Hashable,
        delta: int = 0,
    ) -> tuple[float, float] | None:
        source = self._axis_index_by_id.get(cell_id)
        if source is None:
            return None
        target = source + delta
        if target < 0 or target >= len(self._axis_cells):
            return None
        cell = self._axis_cells[target]
        if cell.start is None or cell.end is None:
            return None
        return (
            self.geometry.date_to_x(cell.start),
            self.geometry.date_to_x(cell.end),
        )

    def movable_selection(self, anchor: ScheduleBlockItem) -> list[ScheduleBlockItem]:
        selected = [
            item
            for item in self.selectedItems()
            if isinstance(item, ScheduleBlockItem)
            and item.schedule_item.movable
            and not item.schedule_item.locked
            and item.is_editable
        ]
        if anchor not in selected:
            selected.append(anchor)
        return selected

    def select_group(self) -> None:
        selected = [
            item for item in self.selectedItems() if isinstance(item, ScheduleBlockItem)
        ]
        if not selected:
            for block in self._blocks.values():
                block.setSelected(True)
            return
        anchor = selected[-1].schedule_item
        group_key = anchor.metadata.get("selection_group", anchor.parent_id)
        if group_key is None:
            group_key = anchor.planning_group
        for block in self._blocks.values():
            item = block.schedule_item
            candidate = item.metadata.get("selection_group", item.parent_id)
            if candidate is None:
                candidate = item.planning_group
            block.setSelected(candidate == group_key if group_key is not None else True)

    def preview_command(self, command: ScheduleCommand) -> PreviewResult:
        preview = self.controller.preview(command)
        self.previewChanged.emit(preview)
        return preview

    def commit_command(self, command: ScheduleCommand) -> None:
        result = self.controller.commit(command)
        if result.success:
            self.commandCommitted.emit(result)
        else:
            self.commandRejected.emit(result)

    def _build_layer_slots(self) -> None:
        layers: dict[Hashable, set[str]] = defaultdict(set)
        for item in self.model.items:
            if self._row_index(item.lane_id, item.layer) is not None:
                layers[item.lane_id].add(item.layer)
        self._layer_slots = {
            lane_id: {layer: index for index, layer in enumerate(sorted(values))}
            for lane_id, values in layers.items()
        }

    def _add_dependencies(self, model: ScheduleModel) -> None:
        for dependency in model.dependencies:
            if dependency.sequence and not self.options.show_sequence_dependencies:
                continue
            predecessor = self._blocks.get(dependency.predecessor_id)
            successor = self._blocks.get(dependency.successor_id)
            if predecessor is None or successor is None:
                continue
            start = predecessor.sceneBoundingRect().center()
            start.setX(predecessor.sceneBoundingRect().right())
            end = successor.sceneBoundingRect().center()
            end.setX(successor.sceneBoundingRect().left())
            self.addItem(DependencyGraphicsItem(start, end, dependency.hard))

    def _row_index(self, lane_id: Hashable, layer: str) -> int | None:
        if self.options.layer_layout is LayerLayout.SEPARATE_ROWS:
            return self._row_by_key.get((lane_id, layer))
        return self._row_by_key.get((lane_id, None))

    def _vertical_margin(self, lane_id: Hashable) -> float:
        del lane_id
        return 1.5 if self.options.item_height_mode is ItemHeightMode.FILL else 4.0


def _item_color(item: ScheduleItem, model: ScheduleModel) -> QtGui.QColor:
    lane = model.lane_by_id.get(item.lane_id)
    color = QtGui.QColor(lane.color if lane and lane.color else "#7aa2d6")
    if not color.isValid():
        color = QtGui.QColor("#7aa2d6")
    if item.layer == "fact":
        return color.darker(116)
    return color


def _qcolor(value, fallback: QtGui.QColor) -> QtGui.QColor:
    if value is None:
        return QtGui.QColor(fallback)
    if isinstance(value, str):
        color = QtGui.QColor(value)
    else:
        color = QtGui.QColor(*value)
    return color if color.isValid() else QtGui.QColor(fallback)


def _with_alpha(color: QtGui.QColor, alpha: float) -> QtGui.QColor:
    result = QtGui.QColor(color)
    result.setAlphaF(min(1.0, max(0.0, alpha)))
    return result


def _map_cell_coordinate(
    value: datetime,
    source: AxisCell,
    target: AxisCell,
) -> datetime | None:
    if (
        source.start is None
        or source.end is None
        or target.start is None
        or target.end is None
    ):
        return None
    duration = (source.end - source.start).total_seconds()
    if duration <= 0:
        return None
    fraction = (value - source.start).total_seconds() / duration
    return target.start + (target.end - target.start) * fraction
