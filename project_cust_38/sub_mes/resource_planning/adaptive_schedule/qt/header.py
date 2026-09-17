from __future__ import annotations

import math
from datetime import timedelta

from PyQt5 import QtCore, QtGui, QtWidgets

from ..view_options import HeaderStyle, TimeScale, ViewOptions
from .geometry import TimelineGeometry


class TimelineHeader(QtWidgets.QWidget):
    """Two-level, horizontally scrollable header for the timeline."""

    def __init__(self, options: ViewOptions, parent=None) -> None:
        super().__init__(parent)
        self._options = options
        self._offset = 0
        self.setFixedHeight(options.header_height)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    def set_options(self, options: ViewOptions) -> None:
        self._options = options
        self.setFixedHeight(options.header_height)
        self.update()

    def set_offset(self, value: int) -> None:
        if value != self._offset:
            self._offset = value
            self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("#f8fafc"))
        geometry = TimelineGeometry(self._options)
        pixels = self._options.pixels_per_day
        top_height = max(22, self.height() // 2)

        left_day = max(0, math.floor(self._offset / pixels) - 1)
        right_day = min(
            math.ceil(geometry.width / pixels),
            math.ceil((self._offset + self.width()) / pixels) + 1,
        )
        font = painter.font()
        font.setBold(self._options.header_bold)
        painter.setFont(font)
        if self._options.header_style is HeaderStyle.STACKED_DATE:
            self._paint_formatted_dates(painter, left_day, right_day)
        elif self._options.header_style is HeaderStyle.COMPACT:
            self._paint_compact_dates(painter, left_day, right_day)
        else:
            self._paint_months(painter, left_day, right_day, top_height)
            self._paint_units(painter, left_day, right_day, top_height)

        painter.setPen(QtGui.QColor("#cfd6df"))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

    def _paint_months(
        self,
        painter: QtGui.QPainter,
        first_day: int,
        last_day: int,
        height: int,
    ) -> None:
        day = self._options.date_from + timedelta(days=first_day)
        cursor = day.replace(day=1)
        if cursor < self._options.date_from:
            cursor = self._options.date_from
        locale = QtCore.QLocale()
        while cursor < self._options.date_to:
            if cursor.month == 12:
                next_month = cursor.replace(
                    year=cursor.year + 1,
                    month=1,
                    day=1,
                )
            else:
                next_month = cursor.replace(month=cursor.month + 1, day=1)
            left = (
                (cursor - self._options.date_from).total_seconds() / 86_400
                * self._options.pixels_per_day
                - self._offset
            )
            right = (
                (min(next_month, self._options.date_to) - self._options.date_from).total_seconds()
                / 86_400
                * self._options.pixels_per_day
                - self._offset
            )
            if right >= 0 and left <= self.width():
                rect = QtCore.QRectF(left, 0, right - left, height)
                painter.setPen(QtGui.QColor("#334155"))
                label = f"{locale.monthName(cursor.month)} {cursor.year}"
                painter.drawText(rect.adjusted(7, 0, -4, 0), QtCore.Qt.AlignVCenter, label)
                painter.setPen(QtGui.QColor("#d8dde5"))
                painter.drawLine(QtCore.QPointF(left, 0), QtCore.QPointF(left, height))
            cursor = next_month

    def _paint_units(
        self,
        painter: QtGui.QPainter,
        first_day: int,
        last_day: int,
        top: int,
    ) -> None:
        locale = QtCore.QLocale()
        pixels = self._options.pixels_per_day
        unit_height = self.height() - top
        for day_index in range(first_day, last_day + 1):
            day = self._options.date_from + timedelta(days=day_index)
            left = day_index * pixels - self._offset
            rect = QtCore.QRectF(left, top, pixels, unit_height)
            non_working = self._options.is_non_working_day(day)
            if self._options.show_weekends and non_working:
                painter.fillRect(rect, QtGui.QColor(self._options.weekend_background))
            painter.setPen(QtGui.QColor("#d8dde5"))
            painter.drawLine(rect.topLeft(), rect.bottomLeft())
            painter.setPen(
                QtGui.QColor(self._options.holiday_text_color)
                if self._options.show_weekends and non_working
                else QtGui.QColor("#475569")
            )
            painter.drawText(rect, QtCore.Qt.AlignCenter, self._day_label(day, locale))

    def _day_label(self, day, locale: QtCore.QLocale) -> str:
        if self._options.show_all_days:
            return str(day.day)
        if self._options.scale is TimeScale.MONTH or self._options.pixels_per_day < 20:
            return str(day.day) if day.day == 1 or day.weekday() == 0 else ""
        if self._options.scale is TimeScale.WEEK:
            return f"{day.day}" if day.weekday() == 0 else ""
        weekday = locale.standaloneDayName(day.isoweekday(), QtCore.QLocale.ShortFormat)
        return f"{day.day} {weekday}" if self._options.pixels_per_day >= 38 else str(day.day)

    def _paint_compact_dates(
        self,
        painter: QtGui.QPainter,
        first_day: int,
        last_day: int,
    ) -> None:
        pixels = self._options.pixels_per_day
        locale = QtCore.QLocale()
        for day_index in range(first_day, last_day + 1):
            day = self._options.date_from + timedelta(days=day_index)
            rect = QtCore.QRectF(
                day_index * pixels - self._offset,
                0,
                pixels,
                self.height(),
            )
            non_working = self._options.is_non_working_day(day)
            if self._options.show_weekends and non_working:
                painter.fillRect(rect, QtGui.QColor(self._options.weekend_background))
            painter.setPen(QtGui.QColor("#d8dde5"))
            painter.drawLine(rect.topLeft(), rect.bottomLeft())
            painter.setPen(
                QtGui.QColor(self._options.holiday_text_color)
                if self._options.show_weekends and non_working
                else QtGui.QColor("#334155")
            )
            if self._options.show_all_days or pixels >= 22:
                weekday = locale.standaloneDayName(
                    day.isoweekday(),
                    QtCore.QLocale.NarrowFormat,
                )
                label = f"{day:%d.%m}\n{weekday}" if pixels >= 30 else f"{day.day}"
            else:
                label = str(day.day) if day.weekday() == 0 else ""
            painter.drawText(rect.adjusted(1, 1, -1, -1), QtCore.Qt.AlignCenter, label)

    def _paint_formatted_dates(
        self,
        painter: QtGui.QPainter,
        first_day: int,
        last_day: int,
    ) -> None:
        pixels = self._options.pixels_per_day
        locale = (
            QtCore.QLocale(self._options.header_locale)
            if self._options.header_locale
            else QtCore.QLocale()
        )
        for day_index in range(first_day, last_day + 1):
            day = self._options.date_from + timedelta(days=day_index)
            rect = QtCore.QRectF(
                day_index * pixels - self._offset,
                0,
                pixels,
                self.height(),
            )
            non_working = self._options.is_non_working_day(day)
            if self._options.show_weekends and non_working:
                painter.fillRect(rect, QtGui.QColor(self._options.weekend_background))
            painter.setPen(QtGui.QColor("#d8dde5"))
            painter.drawLine(rect.topLeft(), rect.bottomLeft())
            painter.setPen(
                QtGui.QColor(self._options.holiday_text_color)
                if self._options.show_weekends and non_working
                else QtGui.QColor("#1e293b")
            )
            weekday = locale.standaloneDayName(
                day.isoweekday(),
                QtCore.QLocale.ShortFormat,
            ).rstrip(".")
            weekday = weekday[:1].upper() + weekday[1:]
            label = day.strftime(
                self._options.header_date_format.replace("{weekday}", weekday)
            )
            painter.drawText(rect.adjusted(1, 1, -1, -1), QtCore.Qt.AlignCenter, label)
