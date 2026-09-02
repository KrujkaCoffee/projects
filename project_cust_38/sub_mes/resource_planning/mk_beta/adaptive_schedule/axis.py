from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Generic, Literal, Protocol, TypeVar

from .domain import AxisCell, ScheduleItem, ScheduleModelError, SliceMetrics


CoordinateT = TypeVar("CoordinateT")


class AxisConverter(Protocol[CoordinateT]):
    """Translate domain coordinates to ordered cells and back."""

    def to_cell(self, value: CoordinateT) -> Hashable:
        ...

    def from_cell(
        self,
        cell_id: Hashable,
        edge: Literal["start", "end"],
    ) -> CoordinateT:
        ...

    def shift(self, cell_id: Hashable, delta: int) -> Hashable:
        ...


AxisIdProvider = Callable[[int, datetime, datetime], Hashable]


@dataclass(frozen=True, slots=True)
class DateTimeAxisBuilder:
    """Build a regular datetime axis while keeping its presentation external."""

    step: timedelta = timedelta(days=1)
    labeler: Callable[[int, datetime, datetime], str] | None = None
    cell_id_provider: AxisIdProvider | None = None
    working_predicate: Callable[[int, datetime, datetime], bool] | None = None
    boundary_predicate: Callable[[int, datetime, datetime], bool] | None = None
    section_id_provider: AxisIdProvider | None = None
    section_labeler: Callable[[int, datetime, datetime], str] | None = None

    def __post_init__(self) -> None:
        if self.step <= timedelta(0):
            raise ScheduleModelError("DateTimeAxisBuilder step must be positive")

    def build(self, start: datetime, end: datetime) -> tuple[AxisCell, ...]:
        _check_datetime_range(start, end, "DateTimeAxisBuilder")
        cells: list[AxisCell] = []
        cell_start = start
        index = 0
        while cell_start < end:
            cell_end = min(cell_start + self.step, end)
            cell_id = (
                self.cell_id_provider(index, cell_start, cell_end)
                if self.cell_id_provider is not None
                else cell_start
            )
            label = (
                self.labeler(index, cell_start, cell_end)
                if self.labeler is not None
                else cell_start.strftime("%Y-%m-%d")
            )
            section_id = (
                self.section_id_provider(index, cell_start, cell_end)
                if self.section_id_provider is not None
                else None
            )
            section_label = (
                self.section_labeler(index, cell_start, cell_end)
                if self.section_labeler is not None
                else ""
            )
            cells.append(
                AxisCell(
                    id=cell_id,
                    index=index,
                    label=label,
                    start=cell_start,
                    end=cell_end,
                    section_id=section_id,
                    section_label=section_label,
                    boundary=(
                        self.boundary_predicate(index, cell_start, cell_end)
                        if self.boundary_predicate is not None
                        else index == 0
                    ),
                    is_working=(
                        self.working_predicate(index, cell_start, cell_end)
                        if self.working_predicate is not None
                        else True
                    ),
                )
            )
            cell_start = cell_end
            index += 1
        return tuple(cells)


@dataclass(frozen=True, slots=True)
class DateTimeAxisConverter(AxisConverter[datetime]):
    cells: tuple[AxisCell, ...]

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.cells, key=lambda cell: cell.index))
        if not ordered:
            raise ScheduleModelError("DateTimeAxisConverter requires at least one cell")
        seen_ids: set[Hashable] = set()
        seen_indices: set[int] = set()
        previous: AxisCell | None = None
        for cell in ordered:
            if cell.id in seen_ids:
                raise ScheduleModelError(f"Duplicate axis cell id: {cell.id!r}")
            seen_ids.add(cell.id)
            if cell.index in seen_indices:
                raise ScheduleModelError(f"Duplicate axis cell index: {cell.index!r}")
            seen_indices.add(cell.index)
            if cell.start is None or cell.end is None:
                raise ScheduleModelError(
                    f"AxisCell {cell.id!r} requires datetime boundaries for conversion"
                )
            if previous is not None and previous.end > cell.start:  # type: ignore[operator]
                raise ScheduleModelError("Datetime axis cells cannot overlap")
            previous = cell
        object.__setattr__(self, "cells", ordered)

    def to_cell(self, value: datetime) -> Hashable:
        _check_aware(value, "Axis coordinate")
        for cell in self.cells:
            if cell.start <= value < cell.end:  # type: ignore[operator]
                return cell.id
        raise ScheduleModelError(f"Coordinate {value!r} is outside axis")

    def from_cell(
        self,
        cell_id: Hashable,
        edge: Literal["start", "end"],
    ) -> datetime:
        if edge not in ("start", "end"):
            raise ScheduleModelError(f"Unknown axis cell edge: {edge!r}")
        cell = self._cell(cell_id)
        value = cell.start if edge == "start" else cell.end
        if value is None:  # Protected by __post_init__; keeps the return type precise.
            raise ScheduleModelError(f"AxisCell {cell.id!r} has no datetime boundary")
        return value

    def shift(self, cell_id: Hashable, delta: int) -> Hashable:
        if not isinstance(delta, int) or isinstance(delta, bool):
            raise ScheduleModelError("Axis shift must be an integer")
        for position, cell in enumerate(self.cells):
            if cell.id != cell_id:
                continue
            target = position + delta
            if target < 0 or target >= len(self.cells):
                raise ScheduleModelError(
                    f"Cannot shift axis cell {cell_id!r} by {delta}: outside axis"
                )
            return self.cells[target].id
        raise ScheduleModelError(f"Unknown axis cell: {cell_id!r}")

    def _cell(self, cell_id: Hashable) -> AxisCell:
        for cell in self.cells:
            if cell.id == cell_id:
                return cell
        raise ScheduleModelError(f"Unknown axis cell: {cell_id!r}")


def slice_metrics_from_allocations(
    item: ScheduleItem,
    axis_cells: Sequence[AxisCell],
    *,
    quantity_unit: str = "",
    metric: Literal["plan", "fact"] | None = None,
) -> tuple[SliceMetrics, ...]:
    """Adapt legacy allocations into sparse metrics without changing the item."""

    metric_name = metric or ("fact" if item.layer.casefold() == "fact" else "plan")
    if metric_name not in ("plan", "fact"):
        raise ScheduleModelError(f"Unknown allocation metric: {metric_name!r}")

    result: list[SliceMetrics] = []
    for cell in sorted(axis_cells, key=lambda value: value.index):
        if cell.start is None or cell.end is None:
            continue
        amount = 0.0
        matched = False
        for allocation in item.allocations:
            overlap_start = max(cell.start, allocation.start)
            overlap_end = min(cell.end, allocation.end)
            if overlap_end <= overlap_start:
                continue
            matched = True
            allocation_seconds = (allocation.end - allocation.start).total_seconds()
            overlap_seconds = (overlap_end - overlap_start).total_seconds()
            amount += allocation.amount * overlap_seconds / allocation_seconds
        if not matched:
            continue
        values = {metric_name: amount}
        result.append(
            SliceMetrics(
                item_id=item.id,
                cell_id=cell.id,
                quantity_unit=quantity_unit,
                metadata={"legacy_allocation": True},
                **values,
            )
        )
    return tuple(result)


def _check_datetime_range(start: datetime, end: datetime, label: str) -> None:
    _check_aware(start, f"{label} start")
    _check_aware(end, f"{label} end")
    if end <= start:
        raise ScheduleModelError(f"{label} must end after it starts")


def _check_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ScheduleModelError(f"{label} must be timezone-aware")
