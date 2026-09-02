from .axis import (
    AxisConverter,
    DateTimeAxisBuilder,
    DateTimeAxisConverter,
    slice_metrics_from_allocations,
)
from .commands import (
    BatchCommand,
    ChangeLane,
    CreateDependency,
    CreateItem,
    DeleteDependency,
    DeleteItem,
    MoveItem,
    ResizeEdge,
    ResizeItem,
    ResizeItemCells,
    ScheduleCommand,
    ShiftItemCells,
)
from .controller import ControllerResult, PreviewResult, ScheduleController
from .domain import (
    Allocation,
    AxisCell,
    CalendarException,
    CapacityInterval,
    ColorValue,
    Dependency,
    DependencyType,
    Lane,
    ScheduleItem,
    ScheduleMode,
    ScheduleModel,
    ScheduleModelError,
    SliceMetrics,
    TimeInterval,
    TimeOwner,
    WorkCalendar,
)
from .engine import SequentialGroupScheduler
from .repository import InMemoryScheduleRepository
from .resolution import (
    ResolutionOptions,
    ResolvedBand,
    ResolvedSchedule,
    ResolvedSlice,
    ScheduleResolutionError,
    resolve_schedule,
)
from .metrics import (
    MetricSliceProfile,
    format_slice_tooltip,
    metric_profiles,
    normalization_maxima,
)
from .services import (
    CommitResult,
    ScheduleResult,
    ScheduleServices,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from .view_options import (
    HeaderStyle,
    ItemHeightMode,
    LaneLayout,
    LanePanelStyle,
    LayerLayout,
    MetricsStyle,
    NormalizationScope,
    TimeScale,
    ViewOptions,
)

__all__ = [
    "Allocation",
    "AxisCell",
    "AxisConverter",
    "BatchCommand",
    "CalendarException",
    "CapacityInterval",
    "ChangeLane",
    "CommitResult",
    "ColorValue",
    "ControllerResult",
    "CreateDependency",
    "CreateItem",
    "DeleteDependency",
    "DeleteItem",
    "DateTimeAxisBuilder",
    "DateTimeAxisConverter",
    "Dependency",
    "DependencyType",
    "InMemoryScheduleRepository",
    "HeaderStyle",
    "ItemHeightMode",
    "Lane",
    "LaneLayout",
    "LanePanelStyle",
    "LayerLayout",
    "MetricSliceProfile",
    "MetricsStyle",
    "MoveItem",
    "NormalizationScope",
    "PreviewResult",
    "ResizeEdge",
    "ResizeItem",
    "ResizeItemCells",
    "ResolutionOptions",
    "ResolvedBand",
    "ResolvedSchedule",
    "ResolvedSlice",
    "ScheduleCommand",
    "ScheduleController",
    "ScheduleItem",
    "ScheduleMode",
    "ScheduleModel",
    "ScheduleModelError",
    "ScheduleResolutionError",
    "ScheduleResult",
    "ScheduleServices",
    "SequentialGroupScheduler",
    "SliceMetrics",
    "ShiftItemCells",
    "TimeInterval",
    "TimeOwner",
    "TimeScale",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    "ViewOptions",
    "WorkCalendar",
    "ScheduleWidget",
    "resolve_schedule",
    "format_slice_tooltip",
    "metric_profiles",
    "normalization_maxima",
    "slice_metrics_from_allocations",
]


def __getattr__(name: str):
    # Keeping Qt lazy makes domain-only use and headless tests independent of PyQt5.
    if name == "ScheduleWidget":
        from .qt import ScheduleWidget

        return ScheduleWidget
    raise AttributeError(name)
