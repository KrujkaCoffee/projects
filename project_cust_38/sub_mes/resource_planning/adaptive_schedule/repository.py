from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from .commands import ScheduleCommand
from .domain import ScheduleModel
from .services import CommitResult


class InMemoryScheduleRepository:
    """Reference repository used by the demo and simple in-memory calendars."""

    def __init__(self, initial: ScheduleModel | None = None) -> None:
        self._model = initial
        self._revision = _initial_revision(initial)

    @property
    def model(self) -> ScheduleModel | None:
        return self._model

    def commit(
        self,
        commands: Sequence[ScheduleCommand],
        proposed: ScheduleModel,
        expected_version: str | int | None,
    ) -> CommitResult:
        del commands
        if self._model is not None and expected_version != self._model.version:
            return CommitResult(
                False,
                model=self._model,
                version=self._model.version,
                message="Расписание уже изменено в другом месте",
            )
        self._revision += 1
        self._model = replace(proposed, version=self._revision)
        return CommitResult(True, self._model, self._revision)


def _initial_revision(model: ScheduleModel | None) -> int:
    if model is not None and isinstance(model.version, int):
        return model.version
    return 0

