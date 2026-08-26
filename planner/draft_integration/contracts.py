from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Callable, Mapping


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


__all__ = [
    "RelationGraphPayload",
    "DraftLane",
    "DraftItem",
    "DraftScheduleSnapshot",
    "relation_graph_payload",
    "schedule_snapshot",
]
