from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from enum import Enum

from .domain import ColorValue


class TimeScale(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class LayerLayout(str, Enum):
    OVERLAY = "overlay"
    STACKED = "stacked"
    SEPARATE_ROWS = "separate_rows"


class LaneLayout(str, Enum):
    NESTED = "nested"
    FLAT = "flat"


class HeaderStyle(str, Enum):
    CALENDAR = "calendar"
    COMPACT = "compact"
    STACKED_DATE = "stacked_date"


class ItemHeightMode(str, Enum):
    COMPACT = "compact"
    FILL = "fill"


class LanePanelStyle(str, Enum):
    PLAIN = "plain"
    COLOR_TINT = "color_tint"


class NormalizationScope(str, Enum):
    ITEM = "item"
    GROUP = "group"
    VIEWPORT = "viewport"
    FIXED = "fixed"


@dataclass(frozen=True, slots=True)
class MetricsStyle:

    capacity_alpha: float = 0.10
    plan_alpha: float = 0.30
    fact_alpha: float = 0.85
    overflow_color: ColorValue | None = None
    fact_width_ratio: float = 0.62

    def __post_init__(self) -> None:
        for name in ("capacity_alpha", "plan_alpha", "fact_alpha"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"MetricsStyle.{name} должен быть в диапазоне [0, 1]")
        if not 0 < self.fact_width_ratio <= 1:
            raise ValueError("MetricsStyle.fact_width_ratio должен быть в диапазоне (0, 1]")


@dataclass(frozen=True, slots=True)
class ViewOptions:
    date_from: datetime
    date_to: datetime
    scale: TimeScale = TimeScale.DAY
    pixels_per_day: float = 42.0
    lane_height: float = 38.0
    header_height: int = 54
    snap: timedelta = timedelta(days=1)
    lane_layout: LaneLayout = LaneLayout.NESTED
    layer_layout: LayerLayout = LayerLayout.OVERLAY
    item_height_mode: ItemHeightMode = ItemHeightMode.COMPACT
    header_style: HeaderStyle = HeaderStyle.CALENDAR
    header_date_format: str = "%y\n%m\n%d\n{weekday}"
    header_locale: str = "ru_RU"
    header_bold: bool = False
    lane_panel_style: LanePanelStyle = LanePanelStyle.PLAIN
    lane_panel_header: str = "Рельсы"
    lane_panel_min_width: int = 180
    lane_panel_max_width: int = 380
    fit_to_width: bool = False
    show_all_days: bool = False
    show_item_labels: bool = True
    show_daily_allocations: bool = False
    daily_allocation_format: str = "{amount:g}"
    show_slice_metrics: bool = True
    normalization_scope: NormalizationScope = NormalizationScope.ITEM
    normalization_fixed_max: float | None = None
    metrics_style: MetricsStyle = field(default_factory=MetricsStyle)
    allow_lane_change: bool = True
    preserve_nonworking_cells: bool = True
    show_dependencies: bool = True
    show_sequence_dependencies: bool = True
    show_weekends: bool = True
    weekend_days: frozenset[int] = frozenset((5, 6))
    holiday_dates: frozenset[date] = frozenset()
    working_date_overrides: frozenset[date] = frozenset()
    weekend_background: str = "#f1f5f9"
    holiday_text_color: str = "#c80b0b"
    show_today: bool = True
    cascade_multi_move: bool = True

    def __post_init__(self) -> None:
        if self.date_from.tzinfo is None or self.date_from.utcoffset() is None:
            raise ValueError("ViewOptions.date_from must be timezone-aware")
        if self.date_to.tzinfo is None or self.date_to.utcoffset() is None:
            raise ValueError("ViewOptions.date_to must be timezone-aware")
        if self.date_to <= self.date_from:
            raise ValueError("ViewOptions.date_to must be after date_from")
        if self.pixels_per_day <= 0 or self.lane_height <= 0:
            raise ValueError("Timeline dimensions must be positive")
        if self.snap <= timedelta(0):
            raise ValueError("ViewOptions.snap must be positive")
        if not self.header_date_format:
            raise ValueError("ViewOptions.header_date_format cannot be empty")
        if self.lane_panel_min_width <= 0:
            raise ValueError("ViewOptions.lane_panel_min_width must be positive")
        if self.lane_panel_max_width < self.lane_panel_min_width:
            raise ValueError(
                "ViewOptions.lane_panel_max_width must be at least lane_panel_min_width"
            )
        if any(day < 0 or day > 6 for day in self.weekend_days):
            raise ValueError("ViewOptions.weekend_days must contain values from 0 to 6")
        if not isinstance(self.normalization_scope, NormalizationScope):
            raise ValueError("ViewOptions.normalization_scope is invalid")
        if self.normalization_fixed_max is not None and self.normalization_fixed_max <= 0:
            raise ValueError("ViewOptions.normalization_fixed_max must be positive")
        if (
            self.normalization_scope is NormalizationScope.FIXED
            and self.normalization_fixed_max is None
        ):
            raise ValueError(
                "ViewOptions.normalization_fixed_max is required for FIXED scope"
            )
        try:
            self.daily_allocation_format.format(amount=1.0)
        except (KeyError, ValueError) as exc:
            raise ValueError(
                "ViewOptions.daily_allocation_format must format an {amount} value"
            ) from exc

    def is_non_working_day(self, value: date | datetime) -> bool:
        day = value.date() if isinstance(value, datetime) else value
        if day in self.working_date_overrides:
            return False
        return day in self.holiday_dates or day.weekday() in self.weekend_days

    def shifted(self, delta: timedelta) -> "ViewOptions":
        return replace(
            self,
            date_from=self.date_from + delta,
            date_to=self.date_to + delta,
        )
