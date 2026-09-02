from __future__ import annotations

from typing import Callable, Iterable, Optional


class LineUpdateLoopError(RuntimeError):
    """Raised when geometry updates keep scheduling themselves."""


class LineUpdateError(RuntimeError):
    """Wrap one or more line refresh failures after the remaining lines ran."""

    def __init__(self, errors: list[tuple[object, Exception]]) -> None:
        self.errors = errors
        super().__init__(f'Не удалось обновить линий: {len(errors)}')


class LineUpdateCoordinator:
    """Coalesce card moves and refresh relation lines outside itemChange().

    The coordinator has no Qt dependency.  Production supplies a zero-timeout
    scheduler; tests can supply a small callback queue.
    """

    def __init__(
        self,
        all_lines: Callable[[], Iterable[object]],
        *,
        incident_lines: Optional[Callable[[str], Iterable[object]]] = None,
        defer: Callable[[Callable[[], None]], None],
        on_error: Optional[Callable[[object, Exception], None]] = None,
        after_flush: Optional[Callable[[], None]] = None,
        max_reentrant_passes: int = 4,
    ) -> None:
        if max_reentrant_passes < 1:
            raise ValueError('max_reentrant_passes должен быть положительным')
        self._all_lines = all_lines
        self._incident_lines = incident_lines
        self._defer = defer
        self._on_error = on_error
        self._after_flush = after_flush
        self._max_reentrant_passes = max_reentrant_passes
        self._pending_cards: set[str] = set()
        self._refresh_all_pending = False
        self._scheduled = False
        self._flushing = False
        self._closed = False

    @property
    def scheduled(self) -> bool:
        return self._scheduled

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def pending_card_keys(self) -> frozenset[str]:
        return frozenset(self._pending_cards)

    def card_moved(self, card_key: str) -> None:
        if self._closed:
            return
        if card_key:
            self._pending_cards.add(str(card_key))
        else:
            self._refresh_all_pending = True
        self._schedule()

    def refresh_all(self) -> None:
        if self._closed:
            return
        self._refresh_all_pending = True
        self._schedule()

    def close(self) -> None:
        self._closed = True
        self._pending_cards.clear()
        self._refresh_all_pending = False
        self._scheduled = False

    def _schedule(self) -> None:
        if self._closed or self._scheduled or self._flushing:
            return
        self._scheduled = True
        self._defer(self.flush)

    @staticmethod
    def _deduplicate(lines: Iterable[object]) -> list[object]:
        result: list[object] = []
        seen: set[int] = set()
        for line in lines:
            marker = id(line)
            if marker in seen:
                continue
            seen.add(marker)
            result.append(line)
        return result

    def _take_pending_lines(self) -> list[object]:
        refresh_all = self._refresh_all_pending
        card_keys = set(self._pending_cards)
        self._refresh_all_pending = False
        self._pending_cards.clear()
        if refresh_all or self._incident_lines is None:
            return self._deduplicate(self._all_lines())
        lines: list[object] = []
        for key in sorted(card_keys):
            lines.extend(self._incident_lines(key))
        return self._deduplicate(lines)

    def flush(self) -> int:
        if self._closed:
            self._scheduled = False
            return 0
        if self._flushing:
            return 0
        self._scheduled = False
        self._flushing = True
        updated = 0
        errors: list[tuple[object, Exception]] = []
        passes = 0
        try:
            while not self._closed and (self._refresh_all_pending or self._pending_cards):
                passes += 1
                if passes > self._max_reentrant_passes:
                    self._refresh_all_pending = False
                    self._pending_cards.clear()
                    raise LineUpdateLoopError(
                        'Обновление линий повторно запланировало само себя '
                        f'более {self._max_reentrant_passes} раз'
                    )
                for line in self._take_pending_lines():
                    try:
                        line.update_path()
                        updated += 1
                    except Exception as exc:  # одна линия не блокирует остальные
                        if self._on_error is not None:
                            self._on_error(line, exc)
                        else:
                            errors.append((line, exc))
            if errors:
                raise LineUpdateError(errors)
            return updated
        finally:
            self._flushing = False
            if not self._closed and self._after_flush is not None:
                self._after_flush()
            if (
                not self._closed
                and (self._refresh_all_pending or self._pending_cards)
                and not self._scheduled
            ):
                self._schedule()
