from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any, Callable, Iterable, Optional


def _normalize(value: Any, ignored_fields: frozenset[str]) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item, ignored_fields)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in ignored_fields
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item, ignored_fields) for item in value]
    if isinstance(value, bool):
        return 1 if value else 0
    if value is None:
        return ''
    return value


def _diff_paths(before: Any, after: Any, prefix: str = '') -> set[str]:
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        result: set[str] = set()
        for key in sorted(set(before) | set(after), key=str):
            path = f'{prefix}.{key}' if prefix else str(key)
            if key not in before or key not in after:
                result.add(path)
            else:
                result.update(_diff_paths(before[key], after[key], path))
        return result
    if isinstance(before, list) and isinstance(after, list):
        result: set[str] = set()
        for index in range(max(len(before), len(after))):
            path = f'{prefix}[{index}]'
            if index >= len(before) or index >= len(after):
                result.add(path)
            else:
                result.update(_diff_paths(before[index], after[index], path))
        return result
    return {prefix or '<root>'} if before != after else set()


class DirtyTracker:
    """Track a normalized semantic diff instead of a permanent changed flag."""

    def __init__(
        self,
        *,
        ignored_fields: Iterable[str] = ('updated_at',),
        normalizer: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        self._ignored_fields = frozenset(str(field) for field in ignored_fields)
        self._normalizer = normalizer
        self._baseline: Any = None
        self._current: Any = None
        self._captured = False

    def _prepare(self, value: Any) -> Any:
        prepared = self._normalizer(value) if self._normalizer is not None else value
        return _normalize(copy.deepcopy(prepared), self._ignored_fields)

    def capture(self, value: Any) -> None:
        prepared = self._prepare(value)
        self._baseline = prepared
        self._current = copy.deepcopy(prepared)
        self._captured = True

    def update(self, value: Any) -> None:
        prepared = self._prepare(value)
        if not self._captured:
            self.capture(prepared)
            return
        self._current = prepared

    @property
    def is_dirty(self) -> bool:
        return bool(self._captured and self._baseline != self._current)

    @property
    def changed_paths(self) -> frozenset[str]:
        if not self._captured:
            return frozenset()
        return frozenset(_diff_paths(self._baseline, self._current))

    @property
    def baseline(self) -> Any:
        return copy.deepcopy(self._baseline)

    @property
    def current(self) -> Any:
        return copy.deepcopy(self._current)

    def restore(self) -> Any:
        self._current = copy.deepcopy(self._baseline)
        return copy.deepcopy(self._baseline)
