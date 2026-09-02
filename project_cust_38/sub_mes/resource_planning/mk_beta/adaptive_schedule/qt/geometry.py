from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..view_options import ViewOptions


SECONDS_PER_DAY = 86_400.0


@dataclass(slots=True)
class TimelineGeometry:
    options: ViewOptions

    @property
    def width(self) -> float:
        return self.date_to_x(self.options.date_to)

    def date_to_x(self, value: datetime) -> float:
        seconds = (value - self.options.date_from).total_seconds()
        return seconds / SECONDS_PER_DAY * self.options.pixels_per_day

    def x_to_date(self, x: float) -> datetime:
        seconds = x / self.options.pixels_per_day * SECONDS_PER_DAY
        return self.options.date_from + timedelta(seconds=seconds)

    def snap_date(self, value: datetime) -> datetime:
        step = self.options.snap.total_seconds()
        seconds = (value - self.options.date_from).total_seconds()
        snapped = round(seconds / step) * step
        return self.options.date_from + timedelta(seconds=snapped)

    def snap_x(self, x: float) -> float:
        return self.date_to_x(self.snap_date(self.x_to_date(x)))

    def row_top(self, row: int) -> float:
        return row * self.options.lane_height

    def row_at(self, y: float, row_count: int) -> int | None:
        row = int(y // self.options.lane_height)
        return row if 0 <= row < row_count else None

