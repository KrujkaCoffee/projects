from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from app.theme import ThemeDefinition, theme_color


class RoundedRectItem(QGraphicsRectItem):
    """PyQt5-safe rounded rectangle item.

    ``QGraphicsScene.addRoundedRect`` is not available in PyQt5.  Drawing the
    rounded rectangle inside an explicit item gives the same result and works
    with PyQt5 5.15.x.
    """

    def __init__(self, rect: QRectF, radius: float, pen: QPen, brush: QBrush, parent=None) -> None:
        super().__init__(rect, parent)
        self.radius = radius
        self.setPen(pen)
        self.setBrush(brush)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: D401 - Qt override
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawRoundedRect(self.rect(), self.radius, self.radius)


class RelationCanvas(QGraphicsView):
    """Focused two-table map used to edit field pairs.

    The map intentionally shows only the selected physical table and one table
    chosen by the user.  Merely choosing a candidate does *not* draw a fake
    connector.  A line appears only when a real field pair exists:

    * green solid line  — pair saved in the database;
    * amber solid line  — unsaved pair in the active relation draft;
    * grey dashed line  — saved but disabled relation.

    This makes the difference between "table selected" and "relation exists"
    explicit, even in databases with hundreds of tables.
    """

    pairDropped = pyqtSignal(str, str, str, str)

    PORT_DATA_ROLE = 0

    CANVAS_BG = theme_color("canvas_bg")
    CARD_BG = theme_color("card_bg")
    CARD_BG_ACTIVE = theme_color("card_root_bg")
    HEADER_BG = theme_color("canvas_header")
    HEADER_BG_ACTIVE = theme_color("canvas_header_root")
    TEXT = theme_color("canvas_text")
    MUTED = theme_color("muted")
    GRID = theme_color("canvas_grid")
    BORDER = theme_color("canvas_border")
    ACTIVE_BORDER = theme_color("root_border")
    PORT = theme_color("port")
    SAVED = theme_color("saved")
    DRAFT = theme_color("draft")
    DISABLED = theme_color("canvas_disabled")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHints(self.renderHints() | QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(self.CANVAS_BG))
        self.setFrameShape(QGraphicsView.NoFrame)

        self._field_points: Dict[Tuple[str, str, str], QPointF] = {}
        self._table_positions: Dict[str, QRectF] = {}
        self._drag_start: Optional[dict] = None
        self._drag_line: Optional[QGraphicsPathItem] = None
        self._selected_table_key = ""
        self._peer_table_key = ""
        self._last_redraw: dict | None = None

    def apply_application_theme(self, theme: ThemeDefinition) -> None:
        token_map = {
            "CANVAS_BG": "canvas_bg",
            "CARD_BG": "card_bg",
            "CARD_BG_ACTIVE": "card_root_bg",
            "HEADER_BG": "canvas_header",
            "HEADER_BG_ACTIVE": "canvas_header_root",
            "TEXT": "canvas_text",
            "MUTED": "muted",
            "GRID": "canvas_grid",
            "BORDER": "canvas_border",
            "ACTIVE_BORDER": "root_border",
            "PORT": "port",
            "SAVED": "saved",
            "DRAFT": "draft",
            "DISABLED": "canvas_disabled",
        }
        for name, token in token_map.items():
            getattr(self, name).setNamedColor(theme.colors[token])
        self.setBackgroundBrush(QBrush(self.CANVAS_BG))
        if self._last_redraw is not None:
            self.redraw(**self._last_redraw)
        else:
            self.scene.update()

    # ------------------------------------------------------------------ public API
    def redraw(
        self,
        tables: List[dict],
        fields_by_table: Dict[str, List[dict]],
        relations: List[dict],
        pairs_by_relation: Dict[str, List[dict]],
        selected_table_key: str,
        peer_table_key: str = "",
        draft_relation: Optional[dict] = None,
        draft_pairs: Optional[List[dict]] = None,
    ) -> None:
        self._last_redraw = {
            "tables": tables,
            "fields_by_table": fields_by_table,
            "relations": relations,
            "pairs_by_relation": pairs_by_relation,
            "selected_table_key": selected_table_key,
            "peer_table_key": peer_table_key,
            "draft_relation": draft_relation,
            "draft_pairs": draft_pairs,
        }
        self.scene.clear()
        self._field_points.clear()
        self._table_positions.clear()
        self._selected_table_key = selected_table_key or ""
        self._peer_table_key = peer_table_key or ""

        if not selected_table_key:
            self._draw_empty_message("Выберите физическую таблицу слева")
            return

        by_key = {row.get("table_key"): row for row in tables}
        selected_table = by_key.get(selected_table_key)
        if not selected_table:
            self._draw_empty_message(f"Таблица {selected_table_key} не найдена в admin_physical_tables")
            return

        selected_fields = fields_by_table.get(selected_table_key, [])
        selected_height = self._card_height(selected_fields)
        self._draw_card(
            selected_table,
            selected_fields,
            x=30,
            y=78,
            highlighted=True,
            badge="Базовая",
        )

        if not peer_table_key:
            self._draw_peer_placeholder(530, 78, selected_height)
            self._draw_legend(selected_table_key, "", 0, "Кандидат не выбран")
            self._finalize_scene()
            return

        peer_table = by_key.get(peer_table_key)
        if not peer_table:
            self._draw_peer_placeholder(530, 78, selected_height, f"Таблица {peer_table_key} не найдена")
            self._draw_legend(selected_table_key, peer_table_key, 0, "Ошибка выбора")
            self._finalize_scene()
            return

        saved_between = [
            relation
            for relation in relations
            if self._relation_between(relation, selected_table_key, peer_table_key)
        ]
        draft_active = bool(
            draft_relation
            and self._relation_between(draft_relation, selected_table_key, peer_table_key)
            and (draft_relation.get("relation_key") or "").strip()
        )
        saved_keys = {relation.get("relation_key") or "" for relation in saved_between}
        draft_key = (draft_relation or {}).get("relation_key") or ""

        if draft_active and draft_key not in saved_keys:
            peer_badge = "Целевая · черновик"
        elif draft_active:
            peer_badge = "Активная связь"
        elif saved_between:
            peer_badge = "Связанная"
        else:
            peer_badge = "Кандидат"

        peer_fields = fields_by_table.get(peer_table_key, [])
        self._draw_card(
            peer_table,
            peer_fields,
            x=530,
            y=78,
            highlighted=False,
            badge=peer_badge,
        )

        draw_count = self._draw_relation_lines(
            relations,
            pairs_by_relation,
            selected_table_key,
            peer_table_key,
            draft_relation=draft_relation,
            draft_pairs=draft_pairs or [],
        )

        state_text = self._state_text(
            saved_between=saved_between,
            pairs_by_relation=pairs_by_relation,
            draft_relation=draft_relation if draft_active else None,
            draft_pairs=draft_pairs or [],
            line_count=draw_count,
        )
        self._draw_legend(selected_table_key, peer_table_key, draw_count, state_text)
        self._finalize_scene()

    def fit_to_content(self) -> None:
        rect = self.scene.itemsBoundingRect().adjusted(-55, -55, 55, 55)
        if not rect.isNull() and rect.isValid():
            self.fitInView(rect, Qt.KeepAspectRatio)

    def reset_zoom(self) -> None:
        self.resetTransform()

    # ------------------------------------------------------------------ events
    def wheelEvent(self, event):  # noqa: N802 - Qt override
        if event.angleDelta().y() > 0:
            self.scale(1.12, 1.12)
        else:
            self.scale(1 / 1.12, 1 / 1.12)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            port = self._port_at(event.pos())
            if port:
                self._drag_start = port
                scene_pos = self.mapToScene(event.pos())
                preview_pen = QPen(self.PORT, 2.2, Qt.DashLine)
                self._drag_line = self.scene.addPath(QPainterPath(scene_pos), preview_pen)
                self._drag_line.setZValue(20)
                self.setDragMode(QGraphicsView.NoDrag)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        if self._drag_start and self._drag_line:
            start_point = self._best_point(
                self._drag_start["table_key"],
                self._drag_start["field_name"],
                self._drag_start.get("side") or "right",
            )
            if start_point is None:
                start_point = self.mapToScene(event.pos())
            end_point = self.mapToScene(event.pos())
            self._drag_line.setPath(self._make_curve(start_point, end_point))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt override
        if self._drag_start and event.button() == Qt.LeftButton:
            target = self._port_at(event.pos())
            start = self._drag_start
            if self._drag_line:
                self.scene.removeItem(self._drag_line)
            self._drag_line = None
            self._drag_start = None
            self.setDragMode(QGraphicsView.ScrollHandDrag)

            if target and (target["table_key"], target["field_name"]) != (
                start["table_key"],
                start["field_name"],
            ):
                # The focused map must connect the two visible tables, not two
                # fields of the same card by accident.
                if {target["table_key"], start["table_key"]} == {
                    self._selected_table_key,
                    self._peer_table_key,
                }:
                    self.pairDropped.emit(
                        start["table_key"],
                        start["field_name"],
                        target["table_key"],
                        target["field_name"],
                    )
                    event.accept()
                    return
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------ drawing
    def _draw_empty_message(self, text: str) -> None:
        item = self.scene.addText(text)
        item.setDefaultTextColor(self.MUTED)
        item.setPos(24, 24)
        item.setScale(1.05)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-40, -40, 80, 80))

    @staticmethod
    def _card_height(fields: List[dict]) -> int:
        return 64 + max(1, len(fields)) * 28 + 18

    @staticmethod
    def _safe_bool(value, default: int = 0) -> bool:
        try:
            return int(value if value is not None else default) == 1
        except (TypeError, ValueError):
            return bool(value)

    def _add_rounded_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        radius: float,
        pen: QPen,
        brush: QBrush,
    ) -> RoundedRectItem:
        item = RoundedRectItem(QRectF(x, y, width, height), radius, pen, brush)
        self.scene.addItem(item)
        return item

    def _draw_card(
        self,
        table: dict,
        fields: List[dict],
        x: int,
        y: int,
        highlighted: bool = False,
        badge: str = "",
    ) -> None:
        table_key = table.get("table_key") or ""
        title = table.get("table_name") or table_key
        width = 440
        height = self._card_height(fields)
        fill = self.CARD_BG_ACTIVE if highlighted else self.CARD_BG
        border = self.ACTIVE_BORDER if highlighted else self.BORDER
        header_fill = self.HEADER_BG_ACTIVE if highlighted else self.HEADER_BG

        card = self._add_rounded_rect(x, y, width, height, 10, QPen(border, 1.7), QBrush(fill))
        card.setZValue(1)
        self._table_positions[table_key] = QRectF(x, y, width, height)

        header = self.scene.addRect(x, y, width, 40, QPen(border, 1.1), QBrush(header_fill))
        header.setZValue(2)

        title_item = self.scene.addText(f"{title}\n{table_key}")
        title_item.setDefaultTextColor(self.TEXT)
        title_item.setPos(x + 14, y + 3)
        title_item.setScale(0.78)
        title_item.setZValue(3)

        if badge:
            badge_item = self.scene.addText(badge)
            badge_item.setDefaultTextColor(self.ACTIVE_BORDER if "черновик" in badge.lower() else self.MUTED)
            badge_item.setPos(x + width - 164, y + 9)
            badge_item.setScale(0.72)
            badge_item.setZValue(3)

        row_y = y + 56
        if not fields:
            empty = self.scene.addText("нет полей в admin_table_fields")
            empty.setDefaultTextColor(self.MUTED)
            empty.setPos(x + 16, row_y - 8)
            empty.setScale(0.86)
            empty.setZValue(3)
            return

        for field in fields:
            name = field.get("field_name") or ""
            label = field.get("label") or ""
            db_type = field.get("db_type") or ""
            pk = "  PK" if self._safe_bool(field.get("is_pk")) else ""
            inc = "" if self._safe_bool(field.get("include_in_schema"), default=1) else "  выключено"
            nullable = " NULL" if self._safe_bool(field.get("nullable"), default=1) else " NOT NULL"
            text = f"{name}{pk}{inc}"
            if db_type:
                text += f" : {db_type}{nullable}"
            if label:
                text += f" — {label}"

            separator = self.scene.addLine(
                x + 10,
                row_y - 9,
                x + width - 10,
                row_y - 9,
                QPen(self.GRID),
            )
            separator.setZValue(2)

            txt = self.scene.addText(text)
            txt.setPos(x + 20, row_y - 22)
            txt.setScale(0.78)
            txt.setDefaultTextColor(self.TEXT)
            txt.setZValue(3)

            self._add_port(table_key, name, "left", QPointF(x, row_y - 8))
            self._add_port(table_key, name, "right", QPointF(x + width, row_y - 8))
            row_y += 28

    def _draw_peer_placeholder(
        self,
        x: int,
        y: int,
        reference_height: int,
        text: str = "Выберите таблицу для карты",
    ) -> None:
        height = max(170, reference_height)
        item = self._add_rounded_rect(
            x,
            y,
            440,
            height,
            10,
            QPen(self.BORDER, 1.4, Qt.DashLine),
            QBrush(self.CARD_BG),
        )
        item.setZValue(1)
        title = self.scene.addText(
            f"{text}\n\nТаблица появится только после явного выбора.\nАвтоматический сосед больше не подставляется."
        )
        title.setDefaultTextColor(self.MUTED)
        title.setPos(x + 22, y + 26)
        title.setScale(0.95)
        title.setZValue(3)

    def _add_port(self, table_key: str, field_name: str, side: str, center: QPointF) -> None:
        self._field_points[(table_key, field_name, side)] = center
        item = self.scene.addEllipse(
            center.x() - 6,
            center.y() - 6,
            12,
            12,
            QPen(self.PORT, 1.5),
            QBrush(self.CARD_BG),
        )
        item.setZValue(8)
        item.setData(
            self.PORT_DATA_ROLE,
            {"table_key": table_key, "field_name": field_name, "side": side},
        )
        item.setToolTip(f"{table_key}.{field_name}\nПотяните к полю второй таблицы")

    def _draw_relation_lines(
        self,
        relations: List[dict],
        pairs_by_relation: Dict[str, List[dict]],
        selected_table_key: str,
        peer_table_key: str,
        draft_relation: Optional[dict] = None,
        draft_pairs: Optional[List[dict]] = None,
    ) -> int:
        count = 0
        draft_pairs = draft_pairs or []
        draft_key = (draft_relation or {}).get("relation_key") or ""

        for relation in relations:
            if not self._relation_between(relation, selected_table_key, peer_table_key):
                continue
            relation_key = relation.get("relation_key") or ""
            if draft_key and relation_key == draft_key:
                # The dirty form is the current source of truth for this relation.
                continue
            count += self._draw_pairs_for_relation(
                relation,
                pairs_by_relation.get(relation_key, []),
                saved=True,
            )

        if draft_relation and self._relation_between(
            draft_relation,
            selected_table_key,
            peer_table_key,
        ):
            count += self._draw_pairs_for_relation(
                draft_relation,
                draft_pairs,
                saved=False,
            )
        return count

    @staticmethod
    def _relation_between(relation: dict, left: str, right: str) -> bool:
        source = relation.get("source_table_key") or relation.get("left_table_key") or ""
        target = relation.get("target_table_key") or relation.get("right_table_key") or ""
        return {source, target} == {left, right} if left != right else source == left and target == right

    def _draw_pairs_for_relation(self, relation: dict, pairs: List[dict], saved: bool) -> int:
        if not pairs:
            # A relation row without field pairs is described in the status text,
            # not by a phantom connector between table headers.
            return 0

        enabled = self._safe_bool(relation.get("is_enabled"), default=1)
        if not saved:
            pen = QPen(self.DRAFT, 2.6, Qt.SolidLine)
            label_color = self.DRAFT
        elif enabled:
            pen = QPen(self.SAVED, 2.2, Qt.SolidLine)
            label_color = self.SAVED
        else:
            pen = QPen(self.DISABLED, 1.8, Qt.DashLine)
            label_color = self.DISABLED

        cardinality = relation.get("cardinality") or ""
        relation_key = relation.get("relation_key") or ""
        drawn = 0
        for pair in pairs:
            a_table = pair.get("left_table_key") or ""
            a_field = pair.get("left_field_name") or ""
            b_table = pair.get("right_table_key") or ""
            b_field = pair.get("right_field_name") or ""
            left = self._point_towards(a_table, a_field, b_table)
            right = self._point_towards(b_table, b_field, a_table)
            if left is None or right is None:
                continue

            path = self._make_curve(left, right)
            item = self.scene.addPath(path, pen)
            item.setZValue(0)

            mid = path.pointAtPercent(0.5)
            operator = pair.get("operator") or "="
            label_parts = []
            if not saved:
                label_parts.append("черновик")
            if cardinality:
                label_parts.append(cardinality)
            if operator != "=":
                label_parts.append(operator)
            if not label_parts and relation_key:
                label_parts.append(relation_key)

            if label_parts:
                text = self.scene.addText(" · ".join(label_parts))
                text.setDefaultTextColor(label_color)
                text.setPos(mid.x() + 5, mid.y() - 17)
                text.setScale(0.74)
                text.setZValue(6)
            drawn += 1
        return drawn

    def _state_text(
        self,
        saved_between: List[dict],
        pairs_by_relation: Dict[str, List[dict]],
        draft_relation: Optional[dict],
        draft_pairs: List[dict],
        line_count: int,
    ) -> str:
        if draft_relation:
            key = draft_relation.get("relation_key") or "черновик"
            if draft_pairs:
                return f"Несохранённая связь {key}: пар полей {len(draft_pairs)}"
            return f"Черновик {key} подготовлен; соедините поля"

        if saved_between:
            pair_count = sum(
                len(pairs_by_relation.get(relation.get("relation_key") or "", []))
                for relation in saved_between
            )
            if pair_count:
                return f"Сохранённых связей: {len(saved_between)}, пар полей: {pair_count}"
            return f"Связь сохранена, но пары полей ещё не заданы"

        return "Кандидат выбран; связь ещё не создана"

    def _draw_legend(
        self,
        selected_table_key: str,
        peer_table_key: str,
        draw_count: int,
        state_text: str,
    ) -> None:
        title = f"Карта: {selected_table_key}"
        if peer_table_key:
            title += f"  ⇄  {peer_table_key}"
        title += f"   |   отображено пар: {draw_count}"

        item = self.scene.addText(title)
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        item.setFont(font)
        item.setDefaultTextColor(self.TEXT)
        item.setPos(30, 14)
        item.setZValue(10)

        state = self.scene.addText(state_text)
        state.setDefaultTextColor(self.MUTED)
        state.setPos(30, 40)
        state.setScale(0.9)
        state.setZValue(10)

    def _finalize_scene(self) -> None:
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-40, -40, 80, 80))

    # ------------------------------------------------------------------ geometry/helpers
    def _point_towards(
        self,   
        table_key: str,
        field_name: str,
        other_table_key: str,
    ) -> Optional[QPointF]:
        own = self._table_positions.get(table_key)
        other = self._table_positions.get(other_table_key)
        if own is None or other is None:
            return self._best_point(table_key, field_name, "right") or self._best_point(
                table_key,
                field_name,
                "left",
            )
        prefer = "right" if own.center().x() <= other.center().x() else "left"
        return self._best_point(table_key, field_name, prefer)

    def _best_point(self, table_key: str, field_name: str, prefer: str) -> Optional[QPointF]:
        key = (table_key, field_name, prefer)
        if key in self._field_points:
            return self._field_points[key]
        alt = "left" if prefer == "right" else "right"
        return self._field_points.get((table_key, field_name, alt))

    @staticmethod
    def _make_curve(start: QPointF, end: QPointF) -> QPainterPath:
        path = QPainterPath(start)
        dx = max(70, abs(end.x() - start.x()) * 0.48)
        direction = 1 if end.x() >= start.x() else -1
        path.cubicTo(
            QPointF(start.x() + direction * dx, start.y()),
            QPointF(end.x() - direction * dx, end.y()),
            end,
        )
        return path

    def _port_at(self, view_pos) -> Optional[dict]:
        scene_pos = self.mapToScene(view_pos)
        for item in self.scene.items(scene_pos):
            data = item.data(self.PORT_DATA_ROLE)
            if isinstance(data, dict) and data.get("table_key") and data.get("field_name"):
                return data
        return None
