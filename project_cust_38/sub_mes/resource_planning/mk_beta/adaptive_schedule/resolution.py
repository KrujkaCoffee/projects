from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

from .axis import AxisConverter, DateTimeAxisConverter, slice_metrics_from_allocations
from .domain import (
    AxisCell,
    ScheduleItem,
    ScheduleMode,
    ScheduleModel,
    ScheduleModelError,
    SliceMetrics,
    TimeOwner,
)


class ScheduleResolutionError(ScheduleModelError):
    """Raised when valid input cannot be resolved inside the supplied axis."""


@dataclass(frozen=True, slots=True)
class ResolutionOptions:
    default_capacity: float = 1.0
    effort_unit: timedelta = timedelta(hours=1)
    use_legacy_allocations: bool = True

    def __post_init__(self) -> None:
        if not isfinite(self.default_capacity) or self.default_capacity < 0:
            raise ScheduleResolutionError(
                "default_capacity must be finite and non-negative"
            )
        if self.effort_unit <= timedelta(0):
            raise ScheduleResolutionError("effort_unit must be positive")


@dataclass(frozen=True, slots=True)
class ResolvedSlice:
    cell: AxisCell
    capacity: float
    plan: float | None = None
    fact: float | None = None
    quantity_unit: str = ""
    source: SliceMetrics | None = None
    derived_plan: bool = False

    @property
    def delta(self) -> float | None:
        if self.plan is None or self.fact is None:
            return None
        return self.fact - self.plan

    @property
    def completion_ratio(self) -> float | None:
        if self.plan is None or self.fact is None or self.plan == 0:
            return None
        return self.fact / self.plan

    @property
    def over_capacity(self) -> bool:
        return any(
            value is not None and value > self.capacity
            for value in (self.plan, self.fact)
        )

    @property
    def over_plan(self) -> bool:
        return self.plan is not None and self.fact is not None and self.fact > self.plan

    def ratio(self, value: float | None, normalization_max: float) -> float | None:
        if value is None:
            return None
        if normalization_max <= 0:
            return 0.0
        return value / normalization_max


@dataclass(frozen=True, slots=True)
class ResolvedBand:
    item: ScheduleItem
    event_id: Hashable
    start: datetime | None
    end: datetime | None
    slices: tuple[ResolvedSlice, ...] = ()
    normalization_max: float = 0.0

    @property
    def first_cell(self) -> AxisCell | None:
        return self.slices[0].cell if self.slices else None

    @property
    def last_cell(self) -> AxisCell | None:
        return self.slices[-1].cell if self.slices else None

    @property
    def has_metrics(self) -> bool:
        return any(value.source is not None or value.derived_plan for value in self.slices)

    @property
    def total_capacity(self) -> float:
        return sum(value.capacity for value in self.slices)

    @property
    def total_plan(self) -> float:
        return sum(value.plan or 0.0 for value in self.slices)

    @property
    def total_fact(self) -> float:
        return sum(value.fact or 0.0 for value in self.slices)


@dataclass(frozen=True, slots=True)
class ResolvedSchedule:
    source: ScheduleModel
    bands: tuple[ResolvedBand, ...]

    @property
    def band_by_item(self) -> dict[Hashable, ResolvedBand]:
        return {band.item.id: band for band in self.bands}

    def band(self, item_id: Hashable) -> ResolvedBand:
        try:
            return self.band_by_item[item_id]
        except KeyError as exc:
            raise ScheduleResolutionError(f"Unknown resolved item: {item_id!r}") from exc


def resolve_schedule(
    model: ScheduleModel,
    *,
    converter: AxisConverter[datetime] | None = None,
    options: ResolutionOptions | None = None,
) -> ResolvedSchedule:
    """Resolve domain items into immutable bands and per-cell visual values."""

    actual_options = options or ResolutionOptions()
    if model.axis_cells and converter is None:
        converter = DateTimeAxisConverter(model.axis_cells)

    metrics_by_item = _metrics_by_item(model, actual_options)
    bands = tuple(
        _resolve_item(
            item,
            model.axis_cells,
            metrics_by_item.get(item.id, {}),
            converter,
            actual_options,
        )
        for item in model.items
    )
    bands = _apply_event_ownership(
        bands,
        model.axis_cells,
        metrics_by_item,
        converter,
        actual_options,
    )
    return ResolvedSchedule(model, bands)


def _metrics_by_item(
    model: ScheduleModel,
    options: ResolutionOptions,
) -> dict[Hashable, dict[Hashable, SliceMetrics]]:
    result: dict[Hashable, dict[Hashable, SliceMetrics]] = defaultdict(dict)
    for metrics in model.slice_metrics:
        result[metrics.item_id][metrics.cell_id] = metrics

    if options.use_legacy_allocations and model.axis_cells:
        for item in model.items:
            if item.id in result or not item.allocations:
                continue
            for metrics in slice_metrics_from_allocations(item, model.axis_cells):
                result[item.id][metrics.cell_id] = metrics
    return dict(result)


def _resolve_item(
    item: ScheduleItem,
    cells: tuple[AxisCell, ...],
    metrics: Mapping[Hashable, SliceMetrics],
    converter: AxisConverter[datetime] | None,
    options: ResolutionOptions,
) -> ResolvedBand:
    mode = item.effective_schedule_mode
    if not cells:
        if mode in (ScheduleMode.FORWARD_EFFORT, ScheduleMode.BACKWARD_EFFORT):
            raise ScheduleResolutionError(
                f"Item {item.id!r} requires axis cells for effort scheduling"
            )
        return ResolvedBand(
            item=item,
            event_id=item.event_key,
            start=item.start,
            end=item.end,
        )
    if converter is None:
        raise ScheduleResolutionError("Axis converter is required for axis cells")

    if mode is ScheduleMode.FIXED_RANGE:
        if item.start is None or item.end is None:
            raise ScheduleResolutionError(
                f"Item {item.id!r} FIXED_RANGE has no complete interval"
            )
        return _frame_band(
            item,
            item.start,
            item.end,
            cells,
            metrics,
            converter,
            options,
        )
    if mode is ScheduleMode.FORWARD_EFFORT:
        return _resolve_forward(item, cells, metrics, converter, options)
    if mode is ScheduleMode.BACKWARD_EFFORT:
        return _resolve_backward(item, cells, metrics, converter, options)

    if metrics:
        ordered = sorted(metrics.values(), key=lambda value: _cell_position(cells, value.cell_id))
        first = ordered[0].cell_id
        last = ordered[-1].cell_id
        return _frame_band(
            item,
            converter.from_cell(first, "start"),
            converter.from_cell(last, "end"),
            cells,
            metrics,
            converter,
            options,
        )
    return ResolvedBand(item, item.event_key, None, None)


def _resolve_forward(
    item: ScheduleItem,
    cells: tuple[AxisCell, ...],
    metrics: Mapping[Hashable, SliceMetrics],
    converter: AxisConverter[datetime],
    options: ResolutionOptions,
) -> ResolvedBand:
    if item.start is None or item.effort is None:
        raise ScheduleResolutionError(
            f"Item {item.id!r} FORWARD_EFFORT requires start and effort"
        )
    remaining = item.effort / options.effort_unit
    if remaining == 0:
        return ResolvedBand(item, item.event_key, item.start, item.start)

    start_position = _cell_position(cells, converter.to_cell(item.start))
    plan_by_cell: dict[Hashable, float] = {}
    resolved_end: datetime | None = None
    for position in range(start_position, len(cells)):
        cell = cells[position]
        cell_start = converter.from_cell(cell.id, "start")
        cell_end = converter.from_cell(cell.id, "end")
        effective_start = max(item.start, cell_start) if position == start_position else cell_start
        full_capacity = _capacity(cell, metrics.get(cell.id), options)
        available = full_capacity * _interval_fraction(effective_start, cell_end, cell_start, cell_end)
        if available <= 0:
            plan_by_cell[cell.id] = 0.0
            continue
        consumed = min(remaining, available)
        plan_by_cell[cell.id] = consumed
        remaining -= consumed
        if remaining <= 1e-12:
            ratio = consumed / available
            resolved_end = effective_start + (cell_end - effective_start) * ratio
            break

    if resolved_end is None:
        raise ScheduleResolutionError(
            f"Not enough capacity on axis to schedule item {item.id!r} forward"
        )
    return _frame_band(
        item,
        item.start,
        resolved_end,
        cells,
        metrics,
        converter,
        options,
        plan_by_cell,
    )


def _resolve_backward(
    item: ScheduleItem,
    cells: tuple[AxisCell, ...],
    metrics: Mapping[Hashable, SliceMetrics],
    converter: AxisConverter[datetime],
    options: ResolutionOptions,
) -> ResolvedBand:
    if item.end is None or item.effort is None:
        raise ScheduleResolutionError(
            f"Item {item.id!r} BACKWARD_EFFORT requires end and effort"
        )
    remaining = item.effort / options.effort_unit
    if remaining == 0:
        return ResolvedBand(item, item.event_key, item.end, item.end)

    end_position = _position_for_end(cells, item.end, converter)
    plan_by_cell: dict[Hashable, float] = {}
    resolved_start: datetime | None = None
    for position in range(end_position, -1, -1):
        cell = cells[position]
        cell_start = converter.from_cell(cell.id, "start")
        cell_end = converter.from_cell(cell.id, "end")
        effective_end = min(item.end, cell_end) if position == end_position else cell_end
        full_capacity = _capacity(cell, metrics.get(cell.id), options)
        available = full_capacity * _interval_fraction(cell_start, effective_end, cell_start, cell_end)
        if available <= 0:
            plan_by_cell[cell.id] = 0.0
            continue
        consumed = min(remaining, available)
        plan_by_cell[cell.id] = consumed
        remaining -= consumed
        if remaining <= 1e-12:
            ratio = consumed / available
            resolved_start = effective_end - (effective_end - cell_start) * ratio
            break

    if resolved_start is None:
        raise ScheduleResolutionError(
            f"Not enough capacity on axis to schedule item {item.id!r} backward"
        )
    return _frame_band(
        item,
        resolved_start,
        item.end,
        cells,
        metrics,
        converter,
        options,
        plan_by_cell,
    )


def _frame_band(
    item: ScheduleItem,
    start: datetime,
    end: datetime,
    cells: tuple[AxisCell, ...],
    metrics: Mapping[Hashable, SliceMetrics],
    converter: AxisConverter[datetime],
    options: ResolutionOptions,
    derived_plan: Mapping[Hashable, float] | None = None,
) -> ResolvedBand:
    if end < start:
        raise ScheduleResolutionError(f"Resolved item {item.id!r} ends before it starts")
    if end == start:
        return ResolvedBand(item, item.event_key, start, end)

    selected: list[AxisCell] = []
    for cell in cells:
        cell_start = converter.from_cell(cell.id, "start")
        cell_end = converter.from_cell(cell.id, "end")
        if cell_start < end and start < cell_end:
            selected.append(cell)
    if not selected:
        raise ScheduleResolutionError(
            f"Resolved interval of item {item.id!r} is outside axis"
        )
    first_start = converter.from_cell(selected[0].id, "start")
    last_end = converter.from_cell(selected[-1].id, "end")
    if first_start > start or last_end < end:
        raise ScheduleResolutionError(
            f"Axis does not fully cover resolved item {item.id!r}"
        )
    covered_until = start
    for cell in selected:
        cell_start = converter.from_cell(cell.id, "start")
        cell_end = converter.from_cell(cell.id, "end")
        if cell_start > covered_until:
            raise ScheduleResolutionError(
                f"Axis has a gap inside resolved item {item.id!r}"
            )
        covered_until = max(covered_until, cell_end)
    if covered_until < end:
        raise ScheduleResolutionError(
            f"Axis does not fully cover resolved item {item.id!r}"
        )

    derived = derived_plan or {}
    slices: list[ResolvedSlice] = []
    for cell in selected:
        source = metrics.get(cell.id)
        has_derived_plan = cell.id in derived
        plan = derived[cell.id] if has_derived_plan else (source.plan if source else None)
        slices.append(
            ResolvedSlice(
                cell=cell,
                capacity=_capacity(cell, source, options),
                plan=plan,
                fact=source.fact if source else None,
                quantity_unit=source.quantity_unit if source else "",
                source=source,
                derived_plan=has_derived_plan,
            )
        )
    normalization_max = max(
        (
            value
            for resolved in slices
            for value in (resolved.capacity, resolved.plan, resolved.fact)
            if value is not None
        ),
        default=0.0,
    )
    return ResolvedBand(
        item=item,
        event_id=item.event_key,
        start=start,
        end=end,
        slices=tuple(slices),
        normalization_max=normalization_max,
    )


def _apply_event_ownership(
    bands: tuple[ResolvedBand, ...],
    cells: tuple[AxisCell, ...],
    metrics_by_item: Mapping[Hashable, Mapping[Hashable, SliceMetrics]],
    converter: AxisConverter[datetime] | None,
    options: ResolutionOptions,
) -> tuple[ResolvedBand, ...]:
    if not cells or converter is None:
        return bands

    groups: dict[Hashable, list[int]] = defaultdict(list)
    for index, band in enumerate(bands):
        if band.item.time_owner is TimeOwner.EVENT:
            groups[band.event_id].append(index)

    replacements: dict[int, ResolvedBand] = {}
    for indices in groups.values():
        if len(indices) < 2:
            continue
        scheduled = [
            bands[index]
            for index in indices
            if bands[index].start is not None
            and bands[index].end is not None
            and bands[index].start < bands[index].end
        ]
        if not scheduled:
            continue
        shared_start = min(value.start for value in scheduled if value.start is not None)
        shared_end = max(value.end for value in scheduled if value.end is not None)
        for index in indices:
            band = bands[index]
            existing_plan = {
                value.cell.id: value.plan
                for value in band.slices
                if value.derived_plan and value.plan is not None
            }
            replacements[index] = _frame_band(
                band.item,
                shared_start,
                shared_end,
                cells,
                metrics_by_item.get(band.item.id, {}),
                converter,
                options,
                existing_plan,
            )

    return tuple(replacements.get(index, band) for index, band in enumerate(bands))


def _capacity(
    cell: AxisCell,
    metrics: SliceMetrics | None,
    options: ResolutionOptions,
) -> float:
    if not cell.is_working:
        return 0.0
    if metrics is not None and metrics.capacity is not None:
        return float(metrics.capacity)
    return float(options.default_capacity)


def _interval_fraction(
    usable_start: datetime,
    usable_end: datetime,
    cell_start: datetime,
    cell_end: datetime,
) -> float:
    full_seconds = (cell_end - cell_start).total_seconds()
    if full_seconds <= 0:
        raise ScheduleResolutionError("Axis cell has non-positive duration")
    usable_seconds = max(0.0, (usable_end - usable_start).total_seconds())
    return min(1.0, usable_seconds / full_seconds)


def _cell_position(cells: tuple[AxisCell, ...], cell_id: Hashable) -> int:
    for position, cell in enumerate(cells):
        if cell.id == cell_id:
            return position
    raise ScheduleResolutionError(f"Unknown axis cell: {cell_id!r}")


def _position_for_end(
    cells: tuple[AxisCell, ...],
    end: datetime,
    converter: AxisConverter[datetime],
) -> int:
    for position, cell in enumerate(cells):
        cell_start = converter.from_cell(cell.id, "start")
        cell_end = converter.from_cell(cell.id, "end")
        if cell_start < end <= cell_end:
            return position
    raise ScheduleResolutionError(f"End coordinate {end!r} is outside axis")
