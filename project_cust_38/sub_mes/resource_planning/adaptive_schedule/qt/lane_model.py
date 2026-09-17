from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from PyQt5 import QtCore, QtGui, QtWidgets

from ..domain import Lane
from ..view_options import LanePanelStyle


ROLE_KIND = QtCore.Qt.UserRole + 1
ROLE_KEY = QtCore.Qt.UserRole + 2
ROLE_LANE = QtCore.Qt.UserRole + 3
ROLE_LAYER = QtCore.Qt.UserRole + 4


@dataclass(frozen=True, slots=True)
class VisibleLaneRow:
    kind: Literal["group", "lane"]
    key: object
    title: str
    lane: Lane | None = None
    layer: str | None = None


class LaneTreeView(QtWidgets.QTreeView):
    rowsChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model = QtGui.QStandardItemModel(self)
        self._panel_style = LanePanelStyle.PLAIN
        self.setModel(self._model)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(True)
        self.setIndentation(16)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.expanded.connect(lambda _index: self.rowsChanged.emit())
        self.collapsed.connect(lambda _index: self.rowsChanged.emit())

    def set_panel_style(self, style: LanePanelStyle) -> None:
        self._panel_style = style
        self.setAlternatingRowColors(style is LanePanelStyle.PLAIN)

    def set_row_height(self, height: int) -> None:
        self.setStyleSheet(
            "QTreeView::item {"
            f"height: {height}px;"
            "padding-left: 4px;"
            "border-bottom: 1px solid #e7e9ec;"
            "}"
            "QTreeView::item:selected { background: #dbeafe; color: #172033; }"
        )

    def set_lanes(
        self,
        lanes: tuple[Lane, ...],
        *,
        grouped: bool = True,
        layers_by_lane: dict[object, tuple[str, ...]] | None = None,
        separate_layers: bool = False,
    ) -> None:
        expanded = self._expanded_group_keys()
        self._model.clear()
        layers_by_lane = layers_by_lane or {}
        groups: dict[object, list[Lane]] = defaultdict(list)
        ungrouped: list[Lane] = []
        for lane in sorted(lanes, key=lambda item: (item.order, item.title)):
            if not grouped or lane.group_id is None:
                ungrouped.append(lane)
            else:
                groups[lane.group_id].append(lane)

        for lane in ungrouped:
            for item in self._lane_items(
                lane,
                layers_by_lane.get(lane.id, ()),
                separate_layers,
                self._panel_style,
            ):
                self._model.appendRow(item)

        ordered_groups = sorted(
            groups.items(),
            key=lambda pair: min(item.order for item in pair[1]),
        )
        for group_id, group_lanes in ordered_groups:
            title = next(
                (lane.group_title for lane in group_lanes if lane.group_title),
                str(group_id),
            )
            group_item = QtGui.QStandardItem(title)
            group_item.setEditable(False)
            group_item.setData("group", ROLE_KIND)
            group_item.setData(group_id, ROLE_KEY)
            font = group_item.font()
            font.setBold(True)
            group_item.setFont(font)
            for lane in group_lanes:
                for item in self._lane_items(
                    lane,
                    layers_by_lane.get(lane.id, ()),
                    separate_layers,
                    self._panel_style,
                ):
                    group_item.appendRow(item)
            self._model.appendRow(group_item)
            index = group_item.index()
            if group_id in expanded or not expanded:
                self.expand(index)

        self.rowsChanged.emit()

    def visible_rows(self) -> list[VisibleLaneRow]:
        rows: list[VisibleLaneRow] = []
        root = self._model.invisibleRootItem()
        for row_index in range(root.rowCount()):
            item = root.child(row_index)
            if item.data(ROLE_KIND) == "lane":
                rows.append(self._visible_lane(item))
                continue
            rows.append(
                VisibleLaneRow(
                    "group",
                    item.data(ROLE_KEY),
                    item.text(),
                    None,
                    None,
                )
            )
            if self.isExpanded(item.index()):
                for child_index in range(item.rowCount()):
                    rows.append(self._visible_lane(item.child(child_index)))
        return rows

    def _expanded_group_keys(self) -> set[object]:
        result: set[object] = set()
        root = self._model.invisibleRootItem()
        for index in range(root.rowCount()):
            item = root.child(index)
            if item.data(ROLE_KIND) == "group" and self.isExpanded(item.index()):
                result.add(item.data(ROLE_KEY))
        return result

    @staticmethod
    def _lane_items(
        lane: Lane,
        layers: tuple[str, ...],
        separate_layers: bool,
        panel_style: LanePanelStyle,
    ) -> list[QtGui.QStandardItem]:
        if not separate_layers:
            return [LaneTreeView._lane_item(lane, panel_style=panel_style)]
        effective_layers = layers or ("plan",)
        return [
            LaneTreeView._lane_item(
                lane,
                layer,
                _lane_title(lane, layer, panel_style),
                panel_style,
            )
            for layer in effective_layers
        ]

    @staticmethod
    def _lane_item(
        lane: Lane,
        layer: str | None = None,
        title: str | None = None,
        panel_style: LanePanelStyle = LanePanelStyle.PLAIN,
    ) -> QtGui.QStandardItem:
        item = QtGui.QStandardItem(title or lane.title)
        item.setEditable(False)
        item.setData("lane", ROLE_KIND)
        item.setData((lane.id, layer), ROLE_KEY)
        item.setData(lane, ROLE_LANE)
        item.setData(layer, ROLE_LAYER)
        if lane.color:
            color = QtGui.QColor(lane.color)
            if color.isValid():
                item.setData(_color_icon(color), QtCore.Qt.DecorationRole)
                if panel_style is LanePanelStyle.COLOR_TINT:
                    tint = color.lighter(150 if layer == "fact" else 175)
                    tint.setAlpha(235)
                    item.setData(QtGui.QBrush(tint), QtCore.Qt.BackgroundRole)
        if panel_style is LanePanelStyle.COLOR_TINT and layer == "fact":
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        return item

    @staticmethod
    def _visible_lane(item: QtGui.QStandardItem) -> VisibleLaneRow:
        lane = item.data(ROLE_LANE)
        layer = item.data(ROLE_LAYER)
        return VisibleLaneRow("lane", (lane.id, layer), item.text(), lane, layer)


def _layer_title(layer: str) -> str:
    return {"plan": "План", "fact": "Факт"}.get(layer, layer)


def _lane_title(lane: Lane, layer: str, style: LanePanelStyle) -> str:
    if style is LanePanelStyle.COLOR_TINT:
        prefix = {"plan": "Пл.", "fact": "Ф."}.get(layer, layer)
        subtitle = lane.metadata.get("layer_subtitles", {}).get(layer, "")
        suffix = f"  ·  {subtitle}" if subtitle else ""
        return f"{prefix:<3}  {lane.title}{suffix}"
    return f"{lane.title} · {_layer_title(layer)}"


def _color_icon(color: QtGui.QColor) -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(12, 12)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(QtGui.QPen(color.darker(120), 1))
    painter.setBrush(color)
    painter.drawRoundedRect(QtCore.QRectF(1, 1, 10, 10), 2, 2)
    painter.end()
    return QtGui.QIcon(pixmap)
