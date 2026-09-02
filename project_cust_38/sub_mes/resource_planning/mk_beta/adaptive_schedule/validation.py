from __future__ import annotations

from collections.abc import Hashable

from .commands import (
    BatchCommand,
    MoveItem,
    ResizeItem,
    ResizeItemCells,
    ScheduleCommand,
    ShiftItemCells,
)
from .domain import Dependency, DependencyType, ScheduleItem, ScheduleModel
from .services import ValidationIssue, ValidationResult, ValidationSeverity


class DefaultCommandValidator:
    """Safe defaults that applications can replace or compose with their own rules."""

    def validate(
        self,
        command: ScheduleCommand,
        snapshot: ScheduleModel,
        proposed: ScheduleModel,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        before = snapshot.item_by_id
        after = proposed.item_by_id

        for nested_command in _command_tree(command):
            if not isinstance(
                nested_command,
                (MoveItem, ShiftItemCells, ResizeItem, ResizeItemCells),
            ):
                continue
            item_id = nested_command.item_id
            old = before.get(item_id)
            new = after.get(item_id)
            if old is None or new is None:
                continue
            if old.locked:
                issues.append(self._forbidden(item_id, "Задача заблокирована", "item_locked"))
            if isinstance(nested_command, (MoveItem, ShiftItemCells)) and not old.movable:
                issues.append(self._forbidden(item_id, "Перемещение запрещено", "move_disabled"))
            if isinstance(nested_command, (ResizeItem, ResizeItemCells)) and not old.resizable:
                issues.append(self._forbidden(item_id, "Изменение длительности запрещено", "resize_disabled"))

        issues.extend(self._check_overlaps(proposed, command.touched_item_ids))
        issues.extend(self._check_dependencies(proposed))
        issues.extend(self._check_capacities(proposed, command.touched_item_ids))
        return ValidationResult(tuple(issues))

    def _check_overlaps(
        self,
        model: ScheduleModel,
        touched_ids: frozenset[Hashable],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        lanes = model.lane_by_id
        scheduled = [item for item in model.items if item.is_scheduled]
        for index, left in enumerate(scheduled):
            lane = lanes[left.lane_id]
            if lane.allow_overlap:
                continue
            for right in scheduled[index + 1 :]:
                if left.lane_id != right.lane_id or left.layer != right.layer:
                    continue
                if left.id not in touched_ids and right.id not in touched_ids:
                    continue
                if _overlaps(left, right):
                    ids = frozenset((left.id, right.id))
                    issues.append(
                        ValidationIssue(
                            ValidationSeverity.FORBIDDEN,
                            f"На рельсе «{lane.title}» задачи пересекаются",
                            ids,
                            "lane_overlap",
                        )
                    )
        return issues

    def _check_dependencies(self, model: ScheduleModel) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        items = model.item_by_id
        for dependency in model.dependencies:
            predecessor = items[dependency.predecessor_id]
            successor = items[dependency.successor_id]
            if not predecessor.is_scheduled or not successor.is_scheduled:
                continue
            if _dependency_satisfied(dependency, predecessor, successor):
                continue
            severity = (
                ValidationSeverity.FORBIDDEN
                if dependency.hard
                else ValidationSeverity.WARNING
            )
            issues.append(
                ValidationIssue(
                    severity,
                    f"Нарушена зависимость {predecessor.title!r} → {successor.title!r}",
                    frozenset((predecessor.id, successor.id)),
                    "dependency_violation",
                )
            )
        return issues

    def _check_capacities(
        self,
        model: ScheduleModel,
        touched_ids: frozenset[Hashable],
    ) -> list[ValidationIssue]:
        """Warn about block-level overload; domain validators may provide finer rules."""
        issues: list[ValidationIssue] = []
        lanes = model.lane_by_id
        for capacity in model.capacities:
            candidates = [
                item
                for item in model.items
                if item.is_scheduled
                and item.lane_id == capacity.lane_id
                and item.start < capacity.end
                and capacity.start < item.end
            ]
            for layer in {item.layer for item in candidates}:
                layer_items = [item for item in candidates if item.layer == layer]
                boundaries = sorted(
                    {
                        max(item.start, capacity.start)
                        for item in layer_items
                    }
                    | {
                        min(item.end, capacity.end)
                        for item in layer_items
                    }
                )
                overloaded_ids: set[Hashable] = set()
                for instant in boundaries[:-1]:
                    active = [
                        item
                        for item in layer_items
                        if item.start <= instant < item.end
                    ]
                    if sum(item.capacity_usage for item in active) > capacity.capacity:
                        overloaded_ids.update(item.id for item in active)
                if overloaded_ids and overloaded_ids.intersection(touched_ids):
                    lane_title = lanes[capacity.lane_id].title
                    issues.append(
                        ValidationIssue(
                            ValidationSeverity.WARNING,
                            f"Превышена доступная мощность рельса «{lane_title}»",
                            frozenset(overloaded_ids),
                            "capacity_overload",
                        )
                    )
        return issues

    @staticmethod
    def _forbidden(item_id: Hashable, message: str, code: str) -> ValidationIssue:
        return ValidationIssue(
            ValidationSeverity.FORBIDDEN,
            message,
            frozenset((item_id,)),
            code,
        )


def _overlaps(left: ScheduleItem, right: ScheduleItem) -> bool:
    return left.start < right.end and right.start < left.end  # type: ignore[operator]


def _command_tree(command: ScheduleCommand):
    yield command
    if isinstance(command, BatchCommand):
        for nested in command.commands:
            yield from _command_tree(nested)


def _dependency_satisfied(
    dependency: Dependency,
    predecessor: ScheduleItem,
    successor: ScheduleItem,
) -> bool:
    lag = dependency.lag
    if dependency.type is DependencyType.FINISH_TO_START:
        return successor.start >= predecessor.end + lag  # type: ignore[operator]
    if dependency.type is DependencyType.START_TO_START:
        return successor.start >= predecessor.start + lag  # type: ignore[operator]
    if dependency.type is DependencyType.FINISH_TO_FINISH:
        return successor.end >= predecessor.end + lag  # type: ignore[operator]
    if dependency.type is DependencyType.START_TO_FINISH:
        return successor.end >= predecessor.start + lag  # type: ignore[operator]
    return True
