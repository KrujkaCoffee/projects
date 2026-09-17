from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from typing import Iterable

from .domain import Allocation, ScheduleItem, ScheduleModel, WorkCalendar
from .services import ScheduleResult


@dataclass(slots=True)
class SequentialGroupScheduler:
    """
    A small default engine compatible with the current MES idea:
    items in one planning_group run in parallel, groups run sequentially.

    Applications with resource optimisation can replace this service without
    changing the widget or DTOs.
    """

    start_at: datetime
    default_daily_effort: timedelta = timedelta(hours=8)
    layers: tuple[str, ...] = ("plan",)
    next_group_on_following_day: bool = False

    def __post_init__(self) -> None:
        if self.start_at.tzinfo is None or self.start_at.utcoffset() is None:
            raise ValueError("SequentialGroupScheduler.start_at must be timezone-aware")
        if self.default_daily_effort <= timedelta(0):
            raise ValueError("default_daily_effort must be positive")

    def schedule(
        self,
        snapshot: ScheduleModel,
        changed_ids: set[Hashable],
    ) -> ScheduleResult:
        del changed_ids  # The default engine recalculates complete parent groups.
        by_parent: dict[Hashable | None, list[ScheduleItem]] = defaultdict(list)
        for item in snapshot.items:
            if item.layer in self.layers:
                by_parent[item.parent_id].append(item)

        replacements: dict[Hashable, ScheduleItem] = {}
        messages: list[str] = []
        for parent_id, parent_items in by_parent.items():
            cursor = self.start_at
            grouped: dict[Hashable, list[ScheduleItem]] = defaultdict(list)
            for index, item in enumerate(parent_items):
                key = item.planning_group
                if key is None:
                    key = ("__single__", index)
                grouped[key].append(item)

            for group_key in sorted(grouped, key=_sortable_group_key):
                group_end = cursor
                for item in grouped[group_key]:
                    if item.locked or item.manually_scheduled or item.effort is None:
                        if item.end is not None:
                            group_end = max(group_end, item.end)
                        continue
                    if item.effort == timedelta(0):
                        messages.append(f"Задача {item.id!r} пропущена: нулевая трудоёмкость")
                        continue
                    calendar = snapshot.calendar_for_lane(item.lane_id)
                    if calendar is None:
                        calendar = WorkCalendar.standard(
                            timezone=_timezone_name(cursor)
                        )
                    limit = item.daily_effort_limit or self.default_daily_effort
                    start, end, allocations = _allocate_effort(
                        calendar,
                        cursor,
                        item.effort,
                        limit,
                    )
                    replacements[item.id] = replace(
                        item,
                        start=start,
                        end=end,
                        allocations=allocations,
                    )
                    group_end = max(group_end, end)

                cursor = group_end
                if self.next_group_on_following_day:
                    cursor = datetime.combine(
                        cursor.date() + timedelta(days=1),
                        time.min,
                        cursor.tzinfo,
                    )

        items = tuple(replacements.get(item.id, item) for item in snapshot.items)
        return ScheduleResult(snapshot.with_items(items), tuple(messages))


def _sortable_group_key(value: Hashable) -> tuple[int, int, float, str]:
    if isinstance(value, tuple) and value and value[0] == "__single__":
        return 1, 0, float(value[1]), ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 0, 0, float(value), ""
    return 0, 1, 0.0, str(value)


def _timezone_name(value: datetime) -> str:
    key = getattr(value.tzinfo, "key", None)
    return key or "UTC"


def _allocate_effort(
    calendar: WorkCalendar,
    start_at: datetime,
    effort: timedelta,
    daily_limit: timedelta,
) -> tuple[datetime, datetime, tuple[Allocation, ...]]:
    cursor = start_at.astimezone(calendar.zone)
    remaining = effort.total_seconds()
    limit_seconds = daily_limit.total_seconds()
    allocations: list[Allocation] = []
    day = cursor.date()

    for _ in range(3660):
        day_budget = limit_seconds
        for interval_start, interval_end in calendar.datetime_intervals_for_day(day):
            current = max(cursor, interval_start)
            if current >= interval_end or day_budget <= 0:
                continue
            available = min(
                (interval_end - current).total_seconds(),
                day_budget,
            )
            consumed = min(remaining, available)
            if consumed <= 0:
                continue
            allocation_end = current + timedelta(seconds=consumed)
            allocations.append(
                Allocation(
                    start=current,
                    end=allocation_end,
                    amount=consumed / 3600,
                )
            )
            remaining -= consumed
            day_budget -= consumed
            cursor = allocation_end
            if remaining <= 0:
                return allocations[0].start, allocation_end, tuple(allocations)
        day += timedelta(days=1)
        cursor = datetime.combine(day, time.min, calendar.zone)

    raise RuntimeError("Unable to allocate work inside a ten-year calendar window")
