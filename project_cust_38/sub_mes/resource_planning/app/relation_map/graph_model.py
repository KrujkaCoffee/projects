from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, List, Optional, Set, Tuple

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPainterPath


class GraphModelMixin:
    tables_by_key: Dict[str, dict]
    fields_by_table: Dict[str, List[dict]]
    relations: List[dict]
    pairs_by_relation: Dict[str, List[dict]]
    root_key: str
    visible_keys: Set[str]
    _cards: dict

    @staticmethod
    def relation_endpoints(relation: dict) -> Tuple[str, str]:
        return (
            str(relation.get('source_table_key') or relation.get('left_table_key') or ''),
            str(relation.get('target_table_key') or relation.get('right_table_key') or ''),
        )

    def connected_component(self, root: Optional[str] = None) -> Set[str]:
        root = root or self.root_key
        if not root or root not in self.tables_by_key:
            return set()
        graph: Dict[str, Set[str]] = defaultdict(set)
        for relation in self.relations:
            left, right = self.relation_endpoints(relation)
            if not left or not right:
                continue
            graph[left].add(right)
            graph[right].add(left)
        result, queue = {root}, deque([root])
        while queue:
            current = queue.popleft()
            for neighbour in graph.get(current, set()):
                if neighbour in self.tables_by_key and neighbour not in result:
                    result.add(neighbour)
                    queue.append(neighbour)
        return result

    def layout_positions(self, keys: Optional[Iterable[str]] = None) -> Dict[str, QPointF]:
        keys_set = set(keys or self.visible_keys)
        if not keys_set:
            return {}
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for relation in self.relations:
            left, right = self.relation_endpoints(relation)
            if left in keys_set and right in keys_set:
                adjacency[left].add(right)
                adjacency[right].add(left)

        root = self.root_key if self.root_key in keys_set else sorted(keys_set)[0]
        levels: Dict[str, int] = {root: 0}
        queue = deque([root])
        while queue:
            current = queue.popleft()
            for neighbour in sorted(adjacency[current]):
                if neighbour not in levels:
                    levels[neighbour] = levels[current] + 1
                    queue.append(neighbour)
        detached_level = max(levels.values(), default=0) + 1
        for key in sorted(keys_set):
            levels.setdefault(key, detached_level)

        buckets: Dict[int, List[str]] = defaultdict(list)
        for key, level in levels.items():
            buckets[level].append(key)
        positions: Dict[str, QPointF] = {}
        x_step = 470.0
        for level in sorted(buckets):
            group = sorted(buckets[level])
            total = sum(max(225.0, self._card_height(key) + 45.0) for key in group)
            y = -total / 2.0
            for key in group:
                height = max(225.0, self._card_height(key) + 45.0)
                positions[key] = QPointF(level * x_step, y)
                y += height
        return positions

    def _card_height(self, key: str) -> float:
        card = self._cards.get(key)
        if card is not None:
            return card.height
        return 52.0 + max(1, len(self.fields_by_table.get(key, []))) * 27.0 + 13.0

    def connection_path(self, relation: dict, pair: dict, index: int = 0) -> QPainterPath:
        left_table = str(pair.get('left_table_key') or '')
        right_table = str(pair.get('right_table_key') or '')
        left_field = str(pair.get('left_field_name') or '')
        right_field = str(pair.get('right_field_name') or '')
        left_card, right_card = self._cards.get(left_table), self._cards.get(right_table)
        if left_card is None or right_card is None:
            return QPainterPath()

        if left_table == right_table:
            start = left_card.port_scene_position(left_field, 'right')
            end = right_card.port_scene_position(right_field, 'right')
            if start is None or end is None:
                return QPainterPath()
            path = QPainterPath(start)
            offset = 95.0 + index * 25.0
            path.cubicTo(start.x() + offset, start.y(), end.x() + offset, end.y(), end.x(), end.y())
            return path

        left_on_left = left_card.scenePos().x() <= right_card.scenePos().x()
        start_side, end_side = ('right', 'left') if left_on_left else ('left', 'right')
        start = left_card.port_scene_position(left_field, start_side)
        end = right_card.port_scene_position(right_field, end_side)
        if start is None or end is None:
            return QPainterPath()
        path = QPainterPath(start)
        dx = max(75.0, abs(end.x() - start.x()) * 0.42)
        direction = 1.0 if end.x() >= start.x() else -1.0
        path.cubicTo(start.x() + direction * dx, start.y(), end.x() - direction * dx, end.y(), end.x(), end.y())
        return path
