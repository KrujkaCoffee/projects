from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import Enum
from math import isfinite
from typing import Any, TypeAlias
from zoneinfo import ZoneInfo


class ScheduleModelError(ValueError):
    """Raised when a schedule snapshot contains contradictory data."""


class DependencyType(str, Enum):
    FINISH_TO_START = "finish_to_start"
    START_TO_START = "start_to_start"
    FINISH_TO_FINISH = "finish_to_finish"
    START_TO_FINISH = "start_to_finish"


class TimeOwner(str, Enum):
    EVENT = "event"
    RESOURCE = "resource"


class ScheduleMode(str, Enum):
    FIXED_RANGE = "fixed_range"
    FORWARD_EFFORT = "forward_effort"
    BACKWARD_EFFORT = "backward_effort"


ColorValue: TypeAlias = (
    str
    | tuple[int, int, int]
    | tuple[int, int, int, int]
)


@dataclass(frozen=True, slots=True)
class TimeInterval:
    start: time
    end: time

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ScheduleModelError("TimeInterval start не может быть >= end")

    @property
    def duration(self) -> timedelta:
        anchor = date(2000, 1, 1)
        return datetime.combine(anchor, self.end) - datetime.combine(anchor, self.start)


@dataclass(frozen=True, slots=True)
class CalendarException:
    start: datetime
    end: datetime
    working: bool
    intervals: tuple[TimeInterval, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        _check_interval(self.start, self.end, "CalendarException")

    def covers(self, day: date) -> bool:
        last_day = self.end.date()
        if self.end.time() == time.min:
            last_day -= timedelta(days=1)
        return self.start.date() <= day <= last_day


@dataclass(frozen=True, slots=True)
class WorkCalendar:
    id: Hashable
    timezone: str = "UTC"
    weekly_intervals: Mapping[int, tuple[TimeInterval, ...]] = field(default_factory=dict)
    exceptions: tuple[CalendarException, ...] = ()

    @classmethod
    def standard(
        cls,
        calendar_id: Hashable = "default",
        timezone: str = "UTC",
        day_start: time = time(8),
        day_end: time = time(17),
        working_days: tuple[int, ...] = (0, 1, 2, 3, 4),
    ) -> "WorkCalendar":
        interval = TimeInterval(day_start, day_end)
        return cls(
            id=calendar_id,
            timezone=timezone,
            weekly_intervals={weekday: (interval,) for weekday in working_days},
        )

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def intervals_for_day(self, day: date) -> tuple[TimeInterval, ...]:
        matching = [item for item in self.exceptions if item.covers(day)]
        if matching:
            exception = matching[-1]
            return exception.intervals if exception.working else ()
        return self.weekly_intervals.get(day.weekday(), ())

    def datetime_intervals_for_day(self, day: date) -> tuple[tuple[datetime, datetime], ...]:
        zone = self.zone
        return tuple(
            (
                datetime.combine(day, interval.start, zone),
                datetime.combine(day, interval.end, zone),
            )
            for interval in self.intervals_for_day(day)
        )

    def is_working_day(self, day: date) -> bool:
        return bool(self.intervals_for_day(day))


@dataclass(frozen=True, slots=True)
class CapacityInterval:
    lane_id: Hashable
    start: datetime
    end: datetime
    capacity: float

    def __post_init__(self) -> None:
        _check_interval(self.start, self.end, "CapacityInterval")
        if self.capacity < 0:
            raise ScheduleModelError("Capacity cannot be negative")


@dataclass(frozen=True, slots=True)
class AxisCell:

    id: Hashable
    index: int
    label: str
    start: datetime | None = None
    end: datetime | None = None
    section_id: Hashable | None = None
    section_label: str = ""
    boundary: bool = False
    is_working: bool = True
    color: ColorValue | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.index, int) or isinstance(self.index, bool):
            raise ScheduleModelError("AxisCell index must be an integer")
        if (self.start is None) != (self.end is None):
            raise ScheduleModelError(
                f"AxisCell {self.id!r} must define both start and end or neither"
            )
        if self.start is not None and self.end is not None:
            if not isinstance(self.start, datetime) or not isinstance(self.end, datetime):
                raise ScheduleModelError(
                    f"AxisCell {self.id!r} start and end must be datetimes"
                )
            _check_interval(self.start, self.end, f"AxisCell {self.id!r}")


@dataclass(frozen=True, slots=True)
class SliceMetrics:
    """Capacity, plan and fact for one item inside one axis cell."""

    item_id: Hashable
    cell_id: Hashable
    capacity: float | None = None
    plan: float | None = None
    fact: float | None = None
    quantity_unit: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("capacity", "plan", "fact"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ScheduleModelError(
                    f"SliceMetrics {name} must be a finite number or None"
                )
            if not isfinite(value) or value < 0:
                raise ScheduleModelError(
                    f"SliceMetrics {name} must be finite and non-negative"
                )


@dataclass(frozen=True, slots=True)
class Lane:
    id: Hashable
    title: str
    group_id: Hashable | None = None
    group_title: str | None = None
    order: int = 0
    color: str | None = None
    calendar_id: Hashable | None = None
    allow_overlap: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Allocation:
    start: datetime
    end: datetime
    amount: float
    locked: bool = False
    source: str = "calculated"

    def __post_init__(self) -> None:
        _check_interval(self.start, self.end, "Allocation")
        if self.amount < 0:
            raise ScheduleModelError("Allocation amount cannot be negative")


@dataclass(frozen=True, slots=True)
class ScheduleItem:
    id: Hashable
    lane_id: Hashable
    title: str = ""
    parent_id: Hashable | None = None
    start: datetime | None = None
    end: datetime | None = None
    effort: timedelta | None = None
    layer: str = "plan"
    planning_group: Hashable | None = None
    daily_effort_limit: timedelta | None = None
    priority: int = 0
    progress: float | None = None
    locked: bool = False
    movable: bool = True
    resizable: bool = True
    splittable: bool = False
    manually_scheduled: bool = False
    capacity_usage: float = 1.0
    allocations: tuple[Allocation, ...] = ()
    subtitle: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    event_id: Hashable | None = None
    time_owner: TimeOwner = TimeOwner.EVENT
    schedule_mode: ScheduleMode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.time_owner, TimeOwner):
            raise ScheduleModelError(f"Item {self.id!r} has invalid time_owner")
        if self.schedule_mode is not None and not isinstance(
            self.schedule_mode, ScheduleMode
        ):
            raise ScheduleModelError(f"Item {self.id!r} has invalid schedule_mode")
        if self.start is not None:
            _check_aware_datetime(self.start, f"ScheduleItem {self.id!r} start")
        if self.end is not None:
            _check_aware_datetime(self.end, f"ScheduleItem {self.id!r} end")
        if self.start is not None and self.end is not None:
            _check_interval(self.start, self.end, f"ScheduleItem {self.id!r}")
        if self.effort is not None and self.effort < timedelta(0):
            raise ScheduleModelError(f"Item {self.id!r} effort cannot be negative")
        if self.daily_effort_limit is not None and self.daily_effort_limit <= timedelta(0):
            raise ScheduleModelError(
                f"Item {self.id!r} daily_effort_limit must be positive"
            )
        if self.progress is not None and not 0 <= self.progress <= 1:
            raise ScheduleModelError(f"Item {self.id!r} progress must be in [0, 1]")
        if self.capacity_usage < 0:
            raise ScheduleModelError(f"Item {self.id!r} capacity_usage cannot be negative")

        mode = self.effective_schedule_mode
        if mode is ScheduleMode.FIXED_RANGE:
            if self.start is None or self.end is None:
                raise ScheduleModelError(
                    f"Item {self.id!r} FIXED_RANGE requires start and end"
                )
        elif mode is ScheduleMode.FORWARD_EFFORT:
            if self.start is None or self.effort is None:
                raise ScheduleModelError(
                    f"Item {self.id!r} FORWARD_EFFORT requires start and effort"
                )
        elif mode is ScheduleMode.BACKWARD_EFFORT:
            if self.end is None or self.effort is None:
                raise ScheduleModelError(
                    f"Item {self.id!r} BACKWARD_EFFORT requires end and effort"
                )
        elif (self.start is None) != (self.end is None):
            raise ScheduleModelError(
                f"Item {self.id!r} must define both start and end or provide effort"
            )

    @property
    def is_scheduled(self) -> bool:
        return self.start is not None and self.end is not None

    @property
    def duration(self) -> timedelta | None:
        if not self.is_scheduled:
            return None
        return self.end - self.start  # type: ignore[operator]

    @property
    def effective_schedule_mode(self) -> ScheduleMode | None:
        if self.schedule_mode is not None:
            return self.schedule_mode
        if self.start is not None and self.end is not None:
            return ScheduleMode.FIXED_RANGE
        if self.start is not None and self.effort is not None:
            return ScheduleMode.FORWARD_EFFORT
        if self.end is not None and self.effort is not None:
            return ScheduleMode.BACKWARD_EFFORT
        return None

    @property
    def event_key(self) -> Hashable:
        return self.id if self.event_id is None else self.event_id


@dataclass(frozen=True, slots=True)
class Dependency:
    predecessor_id: Hashable
    successor_id: Hashable
    type: DependencyType = DependencyType.FINISH_TO_START
    lag: timedelta = timedelta(0)
    hard: bool = True
    sequence: bool = False

    def __post_init__(self) -> None:
        if self.predecessor_id == self.successor_id:
            raise ScheduleModelError("An item cannot depend on itself")


@dataclass(frozen=True, slots=True)
class ScheduleModel:
    lanes: tuple[Lane, ...] = ()
    items: tuple[ScheduleItem, ...] = ()
    calendars: tuple[WorkCalendar, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    capacities: tuple[CapacityInterval, ...] = ()
    version: str | int | None = None
    axis_cells: tuple[AxisCell, ...] = ()
    slice_metrics: tuple[SliceMetrics, ...] = ()

    def __post_init__(self) -> None:
        self.validate()

    @property
    def lane_by_id(self) -> dict[Hashable, Lane]:
        return {lane.id: lane for lane in self.lanes}

    @property
    def item_by_id(self) -> dict[Hashable, ScheduleItem]:
        return {item.id: item for item in self.items}

    @property
    def calendar_by_id(self) -> dict[Hashable, WorkCalendar]:
        return {calendar.id: calendar for calendar in self.calendars}

    @property
    def axis_cell_by_id(self) -> dict[Hashable, AxisCell]:
        return {cell.id: cell for cell in self.axis_cells}

    @property
    def slice_metrics_by_item(self) -> dict[Hashable, tuple[SliceMetrics, ...]]:
        result: dict[Hashable, list[SliceMetrics]] = {}
        for metrics in self.slice_metrics:
            result.setdefault(metrics.item_id, []).append(metrics)
        indices = {cell.id: cell.index for cell in self.axis_cells}
        return {
            item_id: tuple(sorted(values, key=lambda value: indices[value.cell_id]))
            for item_id, values in result.items()
        }

    def item(self, item_id: Hashable) -> ScheduleItem:
        try:
            return self.item_by_id[item_id]
        except KeyError as exc:
            raise ScheduleModelError(f"Unknown schedule item: {item_id!r}") from exc

    def lane(self, lane_id: Hashable) -> Lane:
        try:
            return self.lane_by_id[lane_id]
        except KeyError as exc:
            raise ScheduleModelError(f"Unknown lane: {lane_id!r}") from exc

    def axis_cell(self, cell_id: Hashable) -> AxisCell:
        try:
            return self.axis_cell_by_id[cell_id]
        except KeyError as exc:
            raise ScheduleModelError(f"Unknown axis cell: {cell_id!r}") from exc

    def metrics_for_item(self, item_id: Hashable) -> tuple[SliceMetrics, ...]:
        self.item(item_id)
        return self.slice_metrics_by_item.get(item_id, ())

    def calendar_for_lane(self, lane_id: Hashable) -> WorkCalendar | None:
        lane = self.lane(lane_id)
        if lane.calendar_id is None:
            return self.calendars[0] if self.calendars else None
        return self.calendar_by_id.get(lane.calendar_id)

    def replace_item(self, item: ScheduleItem) -> "ScheduleModel":
        if item.id not in self.item_by_id:
            raise ScheduleModelError(f"Cannot replace unknown item: {item.id!r}")
        return replace(
            self,
            items=tuple(item if current.id == item.id else current for current in self.items),
        )

    def with_items(self, items: tuple[ScheduleItem, ...]) -> "ScheduleModel":
        return replace(self, items=items)

    def validate(self) -> None:
        _ensure_unique((lane.id for lane in self.lanes), "lane")
        _ensure_unique((item.id for item in self.items), "item")
        _ensure_unique((calendar.id for calendar in self.calendars), "calendar")
        _ensure_unique((cell.id for cell in self.axis_cells), "axis cell")
        _ensure_unique((cell.index for cell in self.axis_cells), "axis cell index")
        _ensure_unique(
            ((metrics.item_id, metrics.cell_id) for metrics in self.slice_metrics),
            "slice metrics",
        )

        indices = [cell.index for cell in self.axis_cells]
        if indices != sorted(indices):
            raise ScheduleModelError("Axis cells must be ordered by index")

        lane_ids = {lane.id for lane in self.lanes}
        item_ids = {item.id for item in self.items}
        calendar_ids = {calendar.id for calendar in self.calendars}
        cell_ids = {cell.id for cell in self.axis_cells}

        for lane in self.lanes:
            if lane.calendar_id is not None and lane.calendar_id not in calendar_ids:
                raise ScheduleModelError(
                    f"Lane {lane.id!r} references unknown calendar {lane.calendar_id!r}"
                )
        for item in self.items:
            if item.lane_id not in lane_ids:
                raise ScheduleModelError(
                    f"Item {item.id!r} references unknown lane {item.lane_id!r}"
                )
        for dependency in self.dependencies:
            if dependency.predecessor_id not in item_ids:
                raise ScheduleModelError(
                    f"Unknown dependency predecessor {dependency.predecessor_id!r}"
                )
            if dependency.successor_id not in item_ids:
                raise ScheduleModelError(
                    f"Unknown dependency successor {dependency.successor_id!r}"
                )
        for capacity in self.capacities:
            if capacity.lane_id not in lane_ids:
                raise ScheduleModelError(
                    f"Capacity references unknown lane {capacity.lane_id!r}"
                )
        for metrics in self.slice_metrics:
            if metrics.item_id not in item_ids:
                raise ScheduleModelError(
                    f"Slice metrics reference unknown item {metrics.item_id!r}"
                )
            if metrics.cell_id not in cell_ids:
                raise ScheduleModelError(
                    f"Slice metrics reference unknown axis cell {metrics.cell_id!r}"
                )


def _check_interval(start: datetime, end: datetime, label: str) -> None:
    _check_aware_datetime(start, f"{label} start")
    _check_aware_datetime(end, f"{label} end")
    if end <= start:
        raise ScheduleModelError(f"{label} must end after it starts")


def _check_aware_datetime(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ScheduleModelError(f"{label} must be timezone-aware")


def _ensure_unique(values, label: str) -> None:
    seen: set[Hashable] = set()
    for value in values:
        if value in seen:
            raise ScheduleModelError(f"Duplicate {label} id: {value!r}")
        seen.add(value)
