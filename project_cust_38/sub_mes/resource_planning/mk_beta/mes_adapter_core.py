"""Qt- and database-free conversion of the legacy MES Gant snapshot."""

from __future__ import annotations

import datetime
from collections import defaultdict
from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from typing import Any

from adaptive_schedule import (
    Allocation,
    AxisCell,
    Dependency,
    HeaderStyle,
    ItemHeightMode,
    Lane,
    LaneLayout,
    LanePanelStyle,
    LayerLayout,
    NormalizationScope,
    ScheduleItem,
    ScheduleMode,
    ScheduleModel,
    SliceMetrics,
    TimeOwner,
    ViewOptions,
)


@dataclass(frozen=True, slots=True)
class MesAdapterConfig:
    timezone: datetime.tzinfo
    norm_shift_minutes: float = 480.0
    default_capacity_hours: float = 8.0
    drag_enabled: bool = True
    writeback_enabled: bool = False
    fit_to_width: bool = True
    separate_rows: bool = True
    range_mode: str = "content"
    padding_days: int = 2

    def __post_init__(self) -> None:
        if self.norm_shift_minutes <= 0:
            raise ValueError("norm_shift_minutes must be positive")
        if self.default_capacity_hours < 0:
            raise ValueError("default_capacity_hours cannot be negative")
        if self.padding_days < 0:
            raise ValueError("padding_days cannot be negative")


class MesGantAdapterCore:
    """Convert the already calculated CMS.Gant object using duck-typed fields."""

    def __init__(
        self,
        gant: Any,
        *,
        plan_type: Any,
        fact_type: Any,
        config: MesAdapterConfig,
    ) -> None:
        self.gant = gant
        self.plan_type = plan_type
        self.fact_type = fact_type
        self.config = config
        self._axis_cells: tuple[AxisCell, ...] = ()
        self._cell_by_date: dict[datetime.date, AxisCell] = {}

    def to_model(self, version: int = 0) -> ScheduleModel:
        tables = self._ordered_tables()
        self._axis_cells = self._build_axis(tables)
        self._cell_by_date = {
            cell.start.date(): cell
            for cell in self._axis_cells
            if cell.start is not None
        }

        items: list[ScheduleItem] = []
        metrics: list[SliceMetrics] = []
        plan_items_by_position: dict[Hashable, list[ScheduleItem]] = defaultdict(list)

        for position_id, position in self.gant.dict_pozitions.items():
            for table in tables:
                aggregate = position.dict_agregate_etaps.get(table.name, {})
                for day_type in (self.plan_type, self.fact_type):
                    date_range = aggregate.get(day_type)
                    if date_range is None:
                        continue
                    item = self._item(
                        position_id,
                        position,
                        table,
                        day_type,
                        date_range,
                    )
                    if item is None:
                        continue
                    items.append(item)
                    metrics.extend(self._slice_metrics(item, position, table, day_type))
                    if day_type == self.plan_type:
                        plan_items_by_position[position_id].append(item)

        dependencies: list[Dependency] = []
        for plan_items in plan_items_by_position.values():
            ordered = sorted(
                plan_items,
                key=lambda item: item.metadata.get("mes_order", 0),
            )
            for predecessor, successor in zip(ordered, ordered[1:]):
                dependencies.append(
                    Dependency(
                        predecessor.id,
                        successor.id,
                        hard=False,
                        sequence=True,
                    )
                )

        lanes = tuple(self._lane(table, items) for table in tables)
        return ScheduleModel(
            lanes=lanes,
            items=tuple(items),
            dependencies=tuple(dependencies),
            version=version,
            axis_cells=self._axis_cells,
            slice_metrics=tuple(metrics),
        )

    def view_options(self, model: ScheduleModel) -> ViewOptions:
        start, end = self._view_range(model)
        span_days = max(1, (end - start).days)
        return ViewOptions(
            start,
            end,
            lane_height=48,
            header_height=76,
            snap=datetime.timedelta(days=1),
            lane_layout=LaneLayout.FLAT,
            layer_layout=(
                LayerLayout.SEPARATE_ROWS
                if self.config.separate_rows
                else LayerLayout.OVERLAY
            ),
            item_height_mode=ItemHeightMode.FILL,
            header_style=HeaderStyle.STACKED_DATE,
            header_date_format="%y\n%m\n%d\n{weekday}",
            header_locale="ru_RU",
            header_bold=True,
            lane_panel_style=LanePanelStyle.COLOR_TINT,
            lane_panel_header="Подразделения",
            lane_panel_min_width=245,
            lane_panel_max_width=420,
            fit_to_width=self.config.fit_to_width and span_days <= 40,
            show_all_days=True,
            show_item_labels=False,
            show_daily_allocations=False,
            show_slice_metrics=True,
            normalization_scope=NormalizationScope.ITEM,
            allow_lane_change=False,
            preserve_nonworking_cells=True,
            show_dependencies=True,
            show_sequence_dependencies=False,
            show_weekends=True,
            holiday_dates=self._holiday_dates(),
            working_date_overrides=self._working_date_overrides(),
        )

    def _build_axis(self, tables: Sequence[Any]) -> tuple[AxisCell, ...]:
        del tables
        days: set[datetime.date] = {
            self._aware(day).date() for day in self.gant.dict_template_cld
        }
        for position in self.gant.dict_pozitions.values():
            days.update(self._aware(day).date() for day in position.dict_days)
            for aggregate in position.dict_agregate_etaps.values():
                for start, end in aggregate.values():
                    if start is None or end is None:
                        continue
                    cursor = self._aware(start).date()
                    last = self._aware(end).date()
                    while cursor <= last:
                        days.add(cursor)
                        cursor += datetime.timedelta(days=1)

        if not days:
            start = self._aware(self.gant.min_day).date()
            end = self._aware(self.gant.max_day).date()
        else:
            start, end = min(days), max(days)
        cursor = start
        custom_weekends = self._custom_weekend_dates()
        calendar_by_date = {
            self._aware(day).date(): value
            for day, value in self.gant.dict_template_cld.items()
        }
        result: list[AxisCell] = []
        while cursor <= end:
            day_start = datetime.datetime.combine(
                cursor,
                datetime.time.min,
                self.config.timezone,
            )
            day_end = datetime.datetime.combine(
                cursor + datetime.timedelta(days=1),
                datetime.time.min,
                self.config.timezone,
            )
            calendar_day = calendar_by_date.get(cursor)
            holiday = (
                bool(calendar_day.is_holyday)
                if calendar_day is not None
                else cursor.weekday() >= 5
            )
            custom_weekend = cursor in custom_weekends
            is_working = not holiday and not custom_weekend
            result.append(
                AxisCell(
                    id=day_start,
                    index=len(result),
                    label=day_start.strftime("%d.%m.%Y"),
                    start=day_start,
                    end=day_end,
                    section_id=(cursor.year, cursor.month),
                    section_label=day_start.strftime("%m.%Y"),
                    boundary=cursor.day == 1 or not result,
                    is_working=is_working,
                    metadata={
                        "mes_holiday": holiday,
                        "mes_custom_weekend": custom_weekend,
                    },
                )
            )
            cursor += datetime.timedelta(days=1)
        return tuple(result)

    def _item(
        self,
        position_id: Hashable,
        position: Any,
        table: Any,
        day_type: Any,
        date_range: tuple[datetime.datetime, datetime.datetime],
    ) -> ScheduleItem | None:
        start_legacy, end_legacy = date_range
        if start_legacy is None or end_legacy is None:
            return None
        start = self._day_start(self._aware(start_legacy))
        end = self._day_start(self._aware(end_legacy)) + datetime.timedelta(days=1)
        allocations = self._allocations(position, table, day_type)
        total_hours = sum(value.amount for value in allocations)
        total_minutes = total_hours * 60
        norm_shifts = total_minutes / self.config.norm_shift_minutes
        norm_label = _compact_number(norm_shifts) + " н/см"
        is_fact = day_type == self.fact_type
        has_date_fields = bool(getattr(table, "start_plan_name_field", None)) and bool(
            getattr(table, "end_plan_name_field", None)
        )
        can_drag = self.config.drag_enabled and not is_fact and (
            not self.config.writeback_enabled or has_date_fields
        )
        day_limit = _number(getattr(table, "default_hours_day_gant", None))

        return ScheduleItem(
            id=(position_id, table.name, day_type.name),
            lane_id=table.name,
            title=table.alias or table.name,
            subtitle=norm_label,
            parent_id=position_id,
            start=start,
            end=end,
            effort=datetime.timedelta(minutes=total_minutes),
            layer=day_type.name,
            planning_group=table.group_for_gant,
            daily_effort_limit=(
                datetime.timedelta(hours=day_limit) if day_limit > 0 else None
            ),
            locked=not can_drag,
            movable=can_drag,
            resizable=can_drag,
            manually_scheduled=True,
            allocations=allocations,
            event_id=(position_id, table.name),
            # Plan and fact have independent intervals in MES. Keeping resource
            # ownership makes cell drag preview identical to the committed range;
            # a shared EVENT range would also stretch the movable plan to fact.
            time_owner=TimeOwner.RESOURCE,
            schedule_mode=ScheduleMode.FIXED_RANGE,
            metadata={
                "selection_group": position_id,
                "normalization_group": (position_id, table.name),
                "mes_position_id": position_id,
                "mes_table": table.name,
                "mes_table_alias": table.alias,
                "mes_order": table.order or 0,
                "mes_type": day_type.name,
                "mes_primary_field": table.table_primary_name,
                "mes_start_field": table.start_plan_name_field,
                "mes_end_field": table.end_plan_name_field,
                "norm_minutes": total_minutes,
                "norm_shifts": norm_shifts,
                "norm_shift_minutes": self.config.norm_shift_minutes,
                "mes_writeback": self.config.writeback_enabled and has_date_fields,
            },
        )

    def _slice_metrics(
        self,
        item: ScheduleItem,
        position: Any,
        table: Any,
        day_type: Any,
    ) -> tuple[SliceMetrics, ...]:
        by_date: dict[datetime.date, float] = {}
        for day_dt, day in position.dict_days.items():
            etap = day.dict_etaps.get(table.name)
            if etap is None:
                continue
            cell = etap.get_cell(day_type)
            norm = getattr(cell, "norm", None) if cell is not None else None
            if norm is None:
                continue
            by_date[self._aware(day_dt).date()] = max(0.0, float(norm) / 60)

        day_limit = _number(getattr(table, "default_hours_day_gant", None))
        if day_limit <= 0:
            day_limit = self.config.default_capacity_hours
        is_fact = day_type == self.fact_type
        result: list[SliceMetrics] = []
        for cell in self._axis_cells:
            if cell.start is None or cell.end is None:
                continue
            if cell.end <= item.start or cell.start >= item.end:
                continue
            amount = by_date.get(cell.start.date())
            capacity = day_limit if cell.is_working else 0.0
            result.append(
                SliceMetrics(
                    item_id=item.id,
                    cell_id=cell.id,
                    capacity=capacity,
                    plan=None if is_fact else amount,
                    fact=amount if is_fact else None,
                    quantity_unit="н/ч",
                    metadata={
                        "mes_position_id": item.metadata["mes_position_id"],
                        "mes_table": table.name,
                        "mes_type": day_type.name,
                    },
                )
            )
        return tuple(result)

    def _allocations(
        self,
        position: Any,
        table: Any,
        day_type: Any,
    ) -> tuple[Allocation, ...]:
        result: list[Allocation] = []
        for day_dt, day in sorted(position.dict_days.items()):
            etap = day.dict_etaps.get(table.name)
            if etap is None:
                continue
            cell = etap.get_cell(day_type)
            norm = getattr(cell, "norm", None) if cell is not None else None
            if norm is None or norm <= 0:
                continue
            start = self._day_start(self._aware(day_dt))
            result.append(
                Allocation(
                    start=start,
                    end=start + datetime.timedelta(days=1),
                    amount=float(norm) / 60,
                    locked=day_type == self.fact_type,
                    source="mes_norm_hours",
                )
            )
        return tuple(result)

    def _lane(self, table: Any, items: Sequence[ScheduleItem]) -> Lane:
        layer_subtitles: dict[str, str] = {}
        for layer in (self.plan_type.name, self.fact_type.name):
            total = sum(
                float(item.metadata.get("norm_shifts", 0))
                for item in items
                if item.lane_id == table.name and item.layer == layer
            )
            if total:
                layer_subtitles[layer] = _compact_number(total) + " н/см"
        return Lane(
            id=table.name,
            title=table.alias or table.name,
            group_id=table.group_for_gant,
            group_title=(
                f"Группа {table.group_for_gant}"
                if table.group_for_gant is not None
                else None
            ),
            order=table.order or 0,
            color=_mes_color(table.color),
            allow_overlap=True,
            metadata={
                "mes_table": table.name,
                "norm_shift_minutes": self.config.norm_shift_minutes,
                "layer_subtitles": layer_subtitles,
            },
        )

    def _view_range(
        self,
        model: ScheduleModel,
    ) -> tuple[datetime.datetime, datetime.datetime]:
        axis_start = self._axis_cells[0].start
        axis_end = self._axis_cells[-1].end
        if axis_start is None or axis_end is None:
            raise ValueError("MES datetime axis has no boundaries")
        if self.config.range_mode.casefold() in {"requested", "full"}:
            return axis_start, axis_end
        scheduled = [item for item in model.items if item.is_scheduled]
        if not scheduled:
            return axis_start, axis_end
        start = self._day_start(min(item.start for item in scheduled))
        start -= datetime.timedelta(days=self.config.padding_days)
        end = self._day_start(max(item.end for item in scheduled))
        end += datetime.timedelta(days=self.config.padding_days)
        start = max(start, axis_start)
        end = min(end, axis_end)
        return (start, end) if end > start else (start, start + datetime.timedelta(days=1))

    def _ordered_tables(self) -> list[Any]:
        used_names = {
            name
            for position in self.gant.dict_pozitions.values()
            for name in position.dict_agregate_etaps
        }
        tables = [
            table
            for table in self.gant.fields_db_info.tables_db.tabels_ordered
            if table.name in used_names
        ]
        return sorted(tables, key=lambda table: (table.order or 0, table.name))

    def _holiday_dates(self) -> frozenset[datetime.date]:
        result = {
            self._aware(day).date()
            for day, calendar_day in self.gant.dict_template_cld.items()
            if calendar_day.is_holyday
        }
        result.update(self._custom_weekend_dates())
        return frozenset(result)

    def _custom_weekend_dates(self) -> frozenset[datetime.date]:
        return frozenset(
            self._aware(day).date()
            for position in self.gant.dict_pozitions.values()
            for day, value in position.dict_days.items()
            if value.custom_weekend
        )

    def _working_date_overrides(self) -> frozenset[datetime.date]:
        custom_weekends = self._custom_weekend_dates()
        return frozenset(
            self._aware(day).date()
            for day, calendar_day in self.gant.dict_template_cld.items()
            if calendar_day.is_holyday is False
            and self._aware(day).weekday() >= 5
            and self._aware(day).date() not in custom_weekends
        )

    def _aware(self, value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=self.config.timezone)
        return value.astimezone(self.config.timezone)

    @staticmethod
    def _day_start(value: datetime.datetime) -> datetime.datetime:
        return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _number(value: Any) -> float:
    if value is None or isinstance(value, bool):
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _compact_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _mes_color(color: Any) -> str:
    try:
        red, green, blue = color.rgb
        return f"#{int(red):02x}{int(green):02x}{int(blue):02x}"
    except Exception:
        return "#7aa2d6"
