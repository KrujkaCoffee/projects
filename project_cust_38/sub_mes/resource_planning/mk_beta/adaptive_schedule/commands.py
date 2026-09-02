from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Hashable
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from .axis import DateTimeAxisConverter
from .domain import (
    AxisCell,
    Allocation,
    Dependency,
    ScheduleItem,
    ScheduleMode,
    ScheduleModel,
    ScheduleModelError,
)


class ScheduleCommandError(ValueError):
    pass


class ResizeEdge(str, Enum):
    START = "start"
    END = "end"


class ScheduleCommand(ABC):
    @abstractmethod
    def apply(self, model: ScheduleModel) -> ScheduleModel:
        raise NotImplementedError

    @property
    @abstractmethod
    def touched_item_ids(self) -> frozenset[Hashable]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class MoveItem(ScheduleCommand):
    item_id: Hashable
    new_start: datetime
    new_end: datetime
    new_lane_id: Hashable | None = None

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        item = model.item(self.item_id)
        lane_id = item.lane_id if self.new_lane_id is None else self.new_lane_id
        model.lane(lane_id)
        allocations = item.allocations
        if item.start is not None:
            shift = self.new_start - item.start
            allocations = tuple(
                replace(
                    allocation,
                    start=allocation.start + shift,
                    end=allocation.end + shift,
                )
                for allocation in allocations
            )
        try:
            changed = replace(
                item,
                start=self.new_start,
                end=self.new_end,
                lane_id=lane_id,
                allocations=allocations,
            )
        except ScheduleModelError as exc:
            raise ScheduleCommandError(str(exc)) from exc
        return model.replace_item(changed)

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset((self.item_id,))


@dataclass(frozen=True, slots=True)
class ShiftItemCells(ScheduleCommand):
    """Move an item and every one of its sparse metrics by whole axis cells."""

    item_id: Hashable
    delta_cells: int
    new_lane_id: Hashable | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.delta_cells, int) or isinstance(self.delta_cells, bool):
            raise ScheduleCommandError("delta_cells must be an integer")

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        if not model.axis_cells:
            raise ScheduleCommandError("Cell movement requires axis_cells")
        item = model.item(self.item_id)
        if item.start is None and item.end is None:
            raise ScheduleCommandError(
                f"Cannot move item {item.id!r} without a start or end anchor"
            )
        lane_id = item.lane_id if self.new_lane_id is None else self.new_lane_id
        model.lane(lane_id)
        converter = DateTimeAxisConverter(model.axis_cells)
        try:
            new_start = (
                _shift_coordinate(item.start, model.axis_cells, converter, self.delta_cells, "start")
                if item.start is not None
                else None
            )
            new_end = (
                _shift_coordinate(item.end, model.axis_cells, converter, self.delta_cells, "end")
                if item.end is not None
                else None
            )
            anchor_shift = (
                new_start - item.start
                if item.start is not None and new_start is not None
                else new_end - item.end  # type: ignore[operator]
            )
            allocations = tuple(
                replace(
                    allocation,
                    start=allocation.start + anchor_shift,
                    end=allocation.end + anchor_shift,
                )
                for allocation in item.allocations
            )
            changed_item = replace(
                item,
                start=new_start,
                end=new_end,
                lane_id=lane_id,
                allocations=allocations,
            )
            changed_metrics = tuple(
                replace(
                    metrics,
                    cell_id=converter.shift(metrics.cell_id, self.delta_cells),
                )
                if metrics.item_id == item.id
                else metrics
                for metrics in model.slice_metrics
            )
            changed = model.replace_item(changed_item)
            return replace(changed, slice_metrics=changed_metrics)
        except ScheduleModelError as exc:
            raise ScheduleCommandError(str(exc)) from exc

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset((self.item_id,))


@dataclass(frozen=True, slots=True)
class ResizeItem(ScheduleCommand):
    item_id: Hashable
    edge: ResizeEdge
    value: datetime

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        item = model.item(self.item_id)
        if not item.is_scheduled:
            raise ScheduleCommandError(f"Cannot resize unscheduled item {item.id!r}")
        values = {"start": item.start, "end": item.end}
        values[self.edge.value] = self.value
        try:
            changed = replace(item, **values)
        except ScheduleModelError as exc:
            raise ScheduleCommandError(str(exc)) from exc
        return model.replace_item(changed)

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset((self.item_id,))


@dataclass(frozen=True, slots=True)
class ResizeItemCells(ScheduleCommand):
    """Snap one fixed-range edge to an axis-cell boundary and clip sparse slices."""

    item_id: Hashable
    edge: ResizeEdge
    target_cell_id: Hashable

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        if not model.axis_cells:
            raise ScheduleCommandError("Cell resize requires axis_cells")
        item = model.item(self.item_id)
        if item.effective_schedule_mode is not ScheduleMode.FIXED_RANGE:
            raise ScheduleCommandError(
                f"Cannot resize effort-scheduled item {item.id!r} without a scheduling rule"
            )
        if not item.is_scheduled:
            raise ScheduleCommandError(f"Cannot resize unscheduled item {item.id!r}")
        converter = DateTimeAxisConverter(model.axis_cells)
        try:
            value = converter.from_cell(self.target_cell_id, self.edge.value)
            values = {"start": item.start, "end": item.end}
            values[self.edge.value] = value
            changed_item = replace(item, **values)
            new_start = changed_item.start
            new_end = changed_item.end
            changed_item = replace(
                changed_item,
                allocations=_clip_allocations(
                    item,
                    new_start,  # type: ignore[arg-type]
                    new_end,  # type: ignore[arg-type]
                ),
            )
            changed_metrics = tuple(
                metrics
                for metrics in model.slice_metrics
                if metrics.item_id != item.id
                or _cell_intersects(
                    model.axis_cell(metrics.cell_id),
                    new_start,  # type: ignore[arg-type]
                    new_end,  # type: ignore[arg-type]
                )
            )
            changed = model.replace_item(changed_item)
            return replace(changed, slice_metrics=changed_metrics)
        except ScheduleModelError as exc:
            raise ScheduleCommandError(str(exc)) from exc

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset((self.item_id,))


@dataclass(frozen=True, slots=True)
class ChangeLane(ScheduleCommand):
    item_id: Hashable
    new_lane_id: Hashable

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        item = model.item(self.item_id)
        model.lane(self.new_lane_id)
        return model.replace_item(replace(item, lane_id=self.new_lane_id))

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset((self.item_id,))


@dataclass(frozen=True, slots=True)
class CreateItem(ScheduleCommand):
    item: ScheduleItem

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        if self.item.id in model.item_by_id:
            raise ScheduleCommandError(f"Item {self.item.id!r} already exists")
        model.lane(self.item.lane_id)
        return model.with_items(model.items + (self.item,))

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset((self.item.id,))


@dataclass(frozen=True, slots=True)
class DeleteItem(ScheduleCommand):
    item_id: Hashable

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        model.item(self.item_id)
        dependencies = tuple(
            dependency
            for dependency in model.dependencies
            if self.item_id not in (dependency.predecessor_id, dependency.successor_id)
        )
        from dataclasses import replace as dc_replace

        return dc_replace(
            model,
            items=tuple(item for item in model.items if item.id != self.item_id),
            dependencies=dependencies,
            slice_metrics=tuple(
                metrics
                for metrics in model.slice_metrics
                if metrics.item_id != self.item_id
            ),
        )

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset((self.item_id,))


@dataclass(frozen=True, slots=True)
class CreateDependency(ScheduleCommand):
    dependency: Dependency

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        model.item(self.dependency.predecessor_id)
        model.item(self.dependency.successor_id)
        if self.dependency in model.dependencies:
            raise ScheduleCommandError("Dependency already exists")
        from dataclasses import replace as dc_replace

        return dc_replace(model, dependencies=model.dependencies + (self.dependency,))

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset((self.dependency.predecessor_id, self.dependency.successor_id))


@dataclass(frozen=True, slots=True)
class DeleteDependency(ScheduleCommand):
    dependency: Dependency

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        if self.dependency not in model.dependencies:
            raise ScheduleCommandError("Dependency does not exist")
        from dataclasses import replace as dc_replace

        return dc_replace(
            model,
            dependencies=tuple(
                dependency
                for dependency in model.dependencies
                if dependency != self.dependency
            ),
        )

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset((self.dependency.predecessor_id, self.dependency.successor_id))


@dataclass(frozen=True, slots=True)
class BatchCommand(ScheduleCommand):
    commands: tuple[ScheduleCommand, ...]

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        changed = model
        for command in self.commands:
            changed = command.apply(changed)
        return changed

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        result: set[Hashable] = set()
        for command in self.commands:
            result.update(command.touched_item_ids)
        return frozenset(result)


@dataclass(frozen=True, slots=True)
class RestoreSnapshot(ScheduleCommand):
    """Internal command used to pass undo/redo through the same repository boundary."""

    snapshot: ScheduleModel

    def apply(self, model: ScheduleModel) -> ScheduleModel:
        return self.snapshot

    @property
    def touched_item_ids(self) -> frozenset[Hashable]:
        return frozenset(item.id for item in self.snapshot.items)


def _shift_coordinate(
    value: datetime,
    cells: tuple[AxisCell, ...],
    converter: DateTimeAxisConverter,
    delta: int,
    edge: str,
) -> datetime:
    source = _coordinate_cell(cells, value, edge)
    target_id = converter.shift(source.id, delta)
    target = next(cell for cell in cells if cell.id == target_id)
    if source.start is None or source.end is None or target.start is None or target.end is None:
        raise ScheduleModelError("Cell movement requires datetime axis boundaries")
    source_seconds = (source.end - source.start).total_seconds()
    fraction = (value - source.start).total_seconds() / source_seconds
    return target.start + (target.end - target.start) * fraction


def _coordinate_cell(
    cells: tuple[AxisCell, ...],
    value: datetime,
    edge: str,
) -> AxisCell:
    for cell in cells:
        if cell.start is None or cell.end is None:
            continue
        if edge == "end":
            if cell.start < value <= cell.end:
                return cell
        elif cell.start <= value < cell.end:
            return cell
    raise ScheduleModelError(f"Coordinate {value!r} is outside axis")


def _cell_intersects(cell: AxisCell, start: datetime, end: datetime) -> bool:
    if cell.start is None or cell.end is None:
        return False
    return cell.start < end and start < cell.end


def _clip_allocations(
    item: ScheduleItem,
    start: datetime,
    end: datetime,
) -> tuple[Allocation, ...]:
    result: list[Allocation] = []
    for allocation in item.allocations:
        clipped_start = max(start, allocation.start)
        clipped_end = min(end, allocation.end)
        if clipped_end <= clipped_start:
            continue
        source_seconds = (allocation.end - allocation.start).total_seconds()
        clipped_seconds = (clipped_end - clipped_start).total_seconds()
        result.append(
            replace(
                allocation,
                start=clipped_start,
                end=clipped_end,
                amount=allocation.amount * clipped_seconds / source_seconds,
            )
        )
    return tuple(result)
