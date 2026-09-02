from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass, replace

from .commands import RestoreSnapshot, ScheduleCommand, ScheduleCommandError
from .domain import ScheduleModel
from .services import (
    CommitResult,
    ScheduleServices,
    ValidationResult,
)
from .validation import DefaultCommandValidator


@dataclass(frozen=True, slots=True)
class PreviewResult:
    proposed: ScheduleModel | None
    validation: ValidationResult
    error: str = ""


@dataclass(frozen=True, slots=True)
class ControllerResult:
    success: bool
    model: ScheduleModel
    validation: ValidationResult
    message: str = ""


@dataclass(frozen=True, slots=True)
class _HistoryEntry:
    before: ScheduleModel
    after: ScheduleModel


class ScheduleController:
    def __init__(
        self,
        model: ScheduleModel | None = None,
        services: ScheduleServices | None = None,
        *,
        auto_schedule_on_change: bool = False,
    ) -> None:
        self._model = model or ScheduleModel()
        self.services = services or ScheduleServices()
        self.auto_schedule_on_change = auto_schedule_on_change
        self._undo: list[_HistoryEntry] = []
        self._redo: list[_HistoryEntry] = []
        self._default_validator = DefaultCommandValidator()

    @property
    def model(self) -> ScheduleModel:
        return self._model

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def set_model(self, model: ScheduleModel) -> None:
        self._model = model
        self._undo.clear()
        self._redo.clear()

    def set_services(self, services: ScheduleServices) -> None:
        self.services = services

    def preview(self, command: ScheduleCommand) -> PreviewResult:
        try:
            proposed = command.apply(self._model)
            if self.auto_schedule_on_change and self.services.scheduler is not None:
                scheduled = self.services.scheduler.schedule(
                    proposed,
                    set(command.touched_item_ids),
                )
                proposed = scheduled.model
        except (ScheduleCommandError, ValueError) as exc:
            return PreviewResult(
                None,
                ValidationResult.forbidden(str(exc), command.touched_item_ids),
                str(exc),
            )

        validation = self._default_validator.validate(command, self._model, proposed)
        if self.services.validator is not None:
            custom = self.services.validator.validate(command, self._model, proposed)
            validation = validation.merged(custom)
        return PreviewResult(proposed, validation)

    def commit(self, command: ScheduleCommand) -> ControllerResult:
        preview = self.preview(command)
        if preview.proposed is None or not preview.validation.can_commit:
            return ControllerResult(
                False,
                self._model,
                preview.validation,
                preview.error or "Изменение запрещено",
            )

        before = self._model
        result = self._persist((command,), preview.proposed)
        if not result.success or result.model is None:
            return ControllerResult(
                False,
                self._model,
                preview.validation,
                result.message or "Не удалось сохранить расписание",
            )

        self._model = result.model
        self._undo.append(_HistoryEntry(before, self._model))
        self._redo.clear()
        return ControllerResult(True, self._model, preview.validation, result.message)

    def recalculate(
        self,
        changed_ids: set[Hashable] | None = None,
    ) -> ControllerResult:
        if self.services.scheduler is None:
            return ControllerResult(
                False,
                self._model,
                ValidationResult.forbidden("Планировщик не подключён"),
                "Планировщик не подключён",
            )
        scheduled = self.services.scheduler.schedule(
            self._model,
            changed_ids or {item.id for item in self._model.items},
        )
        command = RestoreSnapshot(scheduled.model)
        return self.commit(command)

    def undo(self) -> ControllerResult:
        if not self._undo:
            return ControllerResult(
                False,
                self._model,
                ValidationResult.allowed(),
                "Нет изменений для отмены",
            )
        entry = self._undo.pop()
        result = self._persist((RestoreSnapshot(entry.before),), entry.before)
        if not result.success or result.model is None:
            self._undo.append(entry)
            return ControllerResult(
                False,
                self._model,
                ValidationResult.allowed(),
                result.message,
            )
        current = self._model
        self._model = result.model
        self._redo.append(_HistoryEntry(self._model, current))
        return ControllerResult(True, self._model, ValidationResult.allowed())

    def redo(self) -> ControllerResult:
        if not self._redo:
            return ControllerResult(
                False,
                self._model,
                ValidationResult.allowed(),
                "Нет изменений для повтора",
            )
        entry = self._redo.pop()
        result = self._persist((RestoreSnapshot(entry.after),), entry.after)
        if not result.success or result.model is None:
            self._redo.append(entry)
            return ControllerResult(
                False,
                self._model,
                ValidationResult.allowed(),
                result.message,
            )
        before = self._model
        self._model = result.model
        self._undo.append(_HistoryEntry(before, self._model))
        return ControllerResult(True, self._model, ValidationResult.allowed())

    def _persist(
        self,
        commands: tuple[ScheduleCommand, ...],
        proposed: ScheduleModel,
    ) -> CommitResult:
        if self.services.repository is None:
            return CommitResult(True, proposed, proposed.version)
        result = self.services.repository.commit(
            commands,
            proposed,
            self._model.version,
        )
        if result.success and result.model is not None and result.version is not None:
            if result.model.version != result.version:
                return replace(result, model=replace(result.model, version=result.version))
        return result

