from __future__ import annotations

from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol

from .commands import ScheduleCommand
from .domain import ScheduleModel


class ValidationSeverity(IntEnum):
    ALLOWED = 0
    WARNING = 1
    FORBIDDEN = 2


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: ValidationSeverity
    message: str
    item_ids: frozenset[Hashable] = frozenset()
    code: str = ""


@dataclass(frozen=True, slots=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...] = ()

    @classmethod
    def allowed(cls) -> "ValidationResult":
        return cls()

    @classmethod
    def warning(
        cls,
        message: str,
        item_ids: frozenset[Hashable] = frozenset(),
        code: str = "",
    ) -> "ValidationResult":
        return cls((ValidationIssue(ValidationSeverity.WARNING, message, item_ids, code),))

    @classmethod
    def forbidden(
        cls,
        message: str,
        item_ids: frozenset[Hashable] = frozenset(),
        code: str = "",
    ) -> "ValidationResult":
        return cls((ValidationIssue(ValidationSeverity.FORBIDDEN, message, item_ids, code),))

    @property
    def severity(self) -> ValidationSeverity:
        return max((issue.severity for issue in self.issues), default=ValidationSeverity.ALLOWED)

    @property
    def can_commit(self) -> bool:
        return self.severity < ValidationSeverity.FORBIDDEN

    @property
    def messages(self) -> tuple[str, ...]:
        return tuple(issue.message for issue in self.issues)

    def merged(self, *others: "ValidationResult") -> "ValidationResult":
        issues = list(self.issues)
        for other in others:
            issues.extend(other.issues)
        return ValidationResult(tuple(issues))


@dataclass(frozen=True, slots=True)
class ScheduleResult:
    model: ScheduleModel
    messages: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CommitResult:
    success: bool
    model: ScheduleModel | None = None
    version: str | int | None = None
    message: str = ""


class ScheduleEngine(Protocol):
    def schedule(
        self,
        snapshot: ScheduleModel,
        changed_ids: set[Hashable],
    ) -> ScheduleResult:
        ...


class CommandValidator(Protocol):
    def validate(
        self,
        command: ScheduleCommand,
        snapshot: ScheduleModel,
        proposed: ScheduleModel,
    ) -> ValidationResult:
        ...


class ScheduleRepository(Protocol):
    def commit(
        self,
        commands: Sequence[ScheduleCommand],
        proposed: ScheduleModel,
        expected_version: str | int | None,
    ) -> CommitResult:
        ...


@dataclass(slots=True)
class ScheduleServices:
    scheduler: ScheduleEngine | None = None
    validator: CommandValidator | None = None
    repository: ScheduleRepository | None = None

