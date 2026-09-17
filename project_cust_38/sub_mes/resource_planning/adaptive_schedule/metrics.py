from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Iterable
from dataclasses import dataclass

from .resolution import ResolvedBand, ResolvedSlice
from .view_options import NormalizationScope


@dataclass(frozen=True, slots=True)
class MetricSliceProfile:
    """Normalized values used by a renderer; ratios may exceed one in FIXED mode."""

    resolved: ResolvedSlice
    normalization_max: float
    capacity_ratio: float
    plan_ratio: float | None
    fact_ratio: float | None

    @property
    def has_visible_value(self) -> bool:
        return any(
            value is not None and value > 0
            for value in (self.capacity_ratio, self.plan_ratio, self.fact_ratio)
        )


def normalization_maxima(
    bands: Iterable[ResolvedBand],
    scope: NormalizationScope = NormalizationScope.ITEM,
    fixed_max: float | None = None,
) -> dict[Hashable, float]:
    """Return the effective common maximum for every supplied band."""

    values = tuple(bands)
    if scope is NormalizationScope.FIXED:
        if fixed_max is None or fixed_max <= 0:
            raise ValueError("fixed_max must be positive for FIXED normalization")
        return {band.item.id: float(fixed_max) for band in values}
    if scope is NormalizationScope.VIEWPORT:
        maximum = max((band.normalization_max for band in values), default=0.0)
        return {band.item.id: maximum for band in values}
    if scope is NormalizationScope.GROUP:
        groups: dict[Hashable, list[ResolvedBand]] = defaultdict(list)
        for band in values:
            groups[_normalization_group(band)].append(band)
        result: dict[Hashable, float] = {}
        for grouped in groups.values():
            maximum = max((band.normalization_max for band in grouped), default=0.0)
            result.update((band.item.id, maximum) for band in grouped)
        return result
    return {band.item.id: band.normalization_max for band in values}


def metric_profiles(
    band: ResolvedBand,
    normalization_max: float | None = None,
) -> tuple[MetricSliceProfile, ...]:
    maximum = band.normalization_max if normalization_max is None else normalization_max
    if maximum < 0:
        raise ValueError("normalization_max cannot be negative")
    return tuple(_profile(value, maximum) for value in band.slices)


def format_slice_tooltip(
    band: ResolvedBand,
    resolved: ResolvedSlice,
    *,
    lane_title: str = "",
) -> str:
    """Build the exact, locale-neutral metric tooltip required by the UI contract."""

    unit = resolved.quantity_unit
    heading = band.item.title or str(band.item.id)
    if lane_title:
        heading = f"{heading} — {lane_title}"
    lines = [heading, resolved.cell.label]
    lines.extend(
        (
            f"Мощность: {_format_value(resolved.capacity, unit)}",
            f"План: {_format_value(resolved.plan, unit)}",
            f"Факт: {_format_value(resolved.fact, unit)}",
        )
    )
    if resolved.delta is not None:
        sign = "+" if resolved.delta > 0 else ""
        lines.append(f"Отклонение: {sign}{_format_value(resolved.delta, unit)}")
    if resolved.completion_ratio is not None:
        lines.append(f"Выполнение: {resolved.completion_ratio * 100:.1f}%")

    warnings: list[str] = []
    if resolved.plan is not None and resolved.plan > resolved.capacity:
        warnings.append("план выше мощности")
    if resolved.fact is not None and resolved.fact > resolved.capacity:
        warnings.append("факт выше мощности")
    if resolved.over_plan:
        warnings.append("факт выше плана")
    if warnings:
        lines.append("Предупреждение: " + "; ".join(warnings))
    return "\n".join(lines)


def _profile(resolved: ResolvedSlice, maximum: float) -> MetricSliceProfile:
    def ratio(value: float | None) -> float | None:
        if value is None:
            return None
        return 0.0 if maximum == 0 else value / maximum

    return MetricSliceProfile(
        resolved=resolved,
        normalization_max=maximum,
        capacity_ratio=ratio(resolved.capacity) or 0.0,
        plan_ratio=ratio(resolved.plan),
        fact_ratio=ratio(resolved.fact),
    )


def _normalization_group(band: ResolvedBand) -> Hashable:
    explicit = band.item.metadata.get("normalization_group")
    if explicit is not None:
        return explicit
    if band.item.planning_group is not None:
        return band.item.planning_group
    return band.event_id


def _format_value(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    rendered = f"{value:g}"
    return f"{rendered} {unit}" if unit else rendered
