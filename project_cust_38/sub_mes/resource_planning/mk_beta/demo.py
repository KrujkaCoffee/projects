from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PyQt5 import QtWidgets

from adaptive_schedule import (
    CapacityInterval,
    DateTimeAxisBuilder,
    Dependency,
    HeaderStyle,
    InMemoryScheduleRepository,
    ItemHeightMode,
    Lane,
    LaneLayout,
    LayerLayout,
    ScheduleItem,
    ScheduleModel,
    ScheduleServices,
    ScheduleWidget,
    SequentialGroupScheduler,
    SliceMetrics,
    ViewOptions,
    WorkCalendar,
)


def make_demo_model() -> tuple[ScheduleModel, datetime]:
    zone = ZoneInfo("Europe/Berlin")
    start = datetime(2026, 7, 13,  tzinfo=zone)
    calendar = WorkCalendar.standard("production", "Europe/Berlin")
    lanes = (
        Lane("laser", "Лазер", "metal", "Металлообработка", 10, "#60a5fa", "production"),
        Lane("bend", "Гибка", "metal", "Металлообработка", 20, "#38bdf8", "production"),
        Lane("weld", "Сварка", "assembly", "Сборка", 30, "#fb923c", "production"),
        Lane("paint", "Покраска", "finish", "Финиш", 40, "#a78bfa", "production"),
        Lane("profile", "Профиль метрик", "demo", "Демонстрация", 50, "#34d399", "production"),
    )
    items = (
        ScheduleItem(
            "cut-plan",
            "laser",
            "Раскрой корпуса",
            parent_id="order-731",
            effort=timedelta(hours=12),
            planning_group=1,
            progress=0.65,
        ),
        ScheduleItem(
            "bend-plan",
            "bend",
            "Гибка деталей",
            parent_id="order-731",
            effort=timedelta(hours=6),
            planning_group=2,
        ),
        ScheduleItem(
            "weld-plan",
            "weld",
            "Сварка узла",
            parent_id="order-731",
            effort=timedelta(hours=10),
            planning_group=3,
            capacity_usage=0.8,
        ),
        ScheduleItem(
            "paint-plan",
            "paint",
            "Покраска",
            parent_id="order-731",
            effort=timedelta(hours=5),
            planning_group=4,
        ),
        ScheduleItem(
            "cut-fact",
            "laser",
            "Раскрой — факт",
            parent_id="order-731",
            start=start,
            end=start + timedelta(hours=10),
            layer="fact",
            locked=True,
            progress=1.0,
        ),
        ScheduleItem(
            "metrics-profile",
            "profile",
            "Недоработка → план → переработка",
            start=start.replace(hour=0),
            end=start.replace(hour=0) + timedelta(days=3),
        ),
    )
    dependencies = (
        Dependency("cut-plan", "bend-plan", sequence=True),
        Dependency("bend-plan", "weld-plan", sequence=True),
        Dependency("weld-plan", "paint-plan", sequence=True),
    )
    capacities = (
        CapacityInterval("weld", start, start + timedelta(days=30), 1.0),
    )
    model = ScheduleModel(
        lanes=lanes,
        items=items,
        calendars=(calendar,),
        dependencies=dependencies,
        capacities=capacities,
        version=0,
    )
    scheduler = SequentialGroupScheduler(start)
    scheduled = scheduler.schedule(model, {item.id for item in items}).model
    axis_start = start.replace(hour=0)
    axis_cells = DateTimeAxisBuilder(
        working_predicate=lambda index, cell_start, cell_end: index not in (5, 6),
    ).build(axis_start, axis_start + timedelta(days=24))
    slice_metrics = (
        SliceMetrics("metrics-profile", axis_cells[0].id, capacity=8, plan=8, fact=4, quantity_unit="н/ч"),
        SliceMetrics("metrics-profile", axis_cells[1].id, capacity=8, plan=8, fact=8, quantity_unit="н/ч"),
        SliceMetrics("metrics-profile", axis_cells[2].id, capacity=8, plan=6, fact=10, quantity_unit="н/ч"),
    )
    return replace(
        scheduled,
        version=0,
        axis_cells=axis_cells,
        slice_metrics=slice_metrics,
    ), start


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    model, start = make_demo_model()
    services = ScheduleServices(
        scheduler=SequentialGroupScheduler(start),
        repository=InMemoryScheduleRepository(model),
    )
    widget = ScheduleWidget(
        options=ViewOptions(
            start - timedelta(days=2),
            start + timedelta(days=24),
            lane_layout=LaneLayout.FLAT,
            layer_layout=LayerLayout.OVERLAY,
            item_height_mode=ItemHeightMode.FILL,
            header_style=HeaderStyle.STACKED_DATE,
            header_date_format="%y\n%m\n%d\n{weekday}",
            header_bold=True,
            fit_to_width=True,
            show_all_days=True,
            show_sequence_dependencies=False,
        )
    )
    widget.set_data(model)
    widget.set_services(services)
    widget.resize(1280, 640)
    widget.setWindowTitle("Adaptive Schedule — demo")
    widget.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
