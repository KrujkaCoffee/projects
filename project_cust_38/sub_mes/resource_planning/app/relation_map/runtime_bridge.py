from __future__ import annotations

import warnings
from typing import Iterable

from PyQt5.QtCore import QRectF, QTimer

from .safe_updates import LineUpdateCoordinator
from .workspace import MonotonicWorkspace, WorkspaceBounds


class RelationMapRuntime:
    """Production bridge between the canvas and independent Stage 2 helpers."""

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.workspace = MonotonicWorkspace()
        self._closed = False
        self._deferred_callback = None
        self._defer_timer = QTimer(canvas)
        self._defer_timer.setSingleShot(True)
        self._defer_timer.timeout.connect(self._run_deferred)
        self.line_updates = LineUpdateCoordinator(
            lambda: list(self.canvas._lines),
            incident_lines=self._incident_lines,
            defer=self._defer,
            on_error=self._line_update_failed,
            after_flush=self.expand_workspace,
        )
        self.canvas._scene.destroyed.connect(self.close)
        self.canvas.destroyed.connect(self.close)
        self.expand_workspace()

    def _defer(self, callback) -> None:
        if self._closed:
            return
        self._deferred_callback = callback
        if not self._defer_timer.isActive():
            self._defer_timer.start(0)

    def _run_deferred(self) -> None:
        callback = self._deferred_callback
        self._deferred_callback = None
        if not self._closed and callback is not None:
            callback()

    def close(self, *_args) -> None:
        if self._closed:
            return
        self._closed = True
        self._deferred_callback = None
        self.line_updates.close()
        try:
            self._defer_timer.stop()
        except RuntimeError:
            # Таймер уже мог быть удалён вместе с canvas.
            pass

    @staticmethod
    def _line_update_failed(line: object, exc: Exception) -> None:
        warnings.warn(
            f'Не удалось обновить геометрию линии {line!r}: {exc}',
            RuntimeWarning,
            stacklevel=2,
        )

    def _incident_lines(self, table_key: str) -> Iterable[object]:
        if self._closed:
            return []
        lines = list(self.canvas._lines)
        if any(not hasattr(line, 'endpoint_table_keys') for line in lines):
            return lines
        return [line for line in lines if table_key in line.endpoint_table_keys]

    def card_moved(self, card) -> None:
        if self._closed:
            return
        self.line_updates.card_moved(str(getattr(card, 'table_key', '') or ''))

    def refresh_all(self) -> None:
        if self._closed:
            return
        self.line_updates.refresh_all()

    def expand_workspace(self) -> None:
        if self._closed:
            return
        rect = self.canvas._scene.itemsBoundingRect()
        if rect.isValid() and not rect.isNull():
            content = WorkspaceBounds(rect.left(), rect.top(), rect.right(), rect.bottom())
            bounds = self.workspace.include(content)
        else:
            bounds = self.workspace.bounds
        self.canvas._scene.setSceneRect(
            QRectF(bounds.left, bounds.top, bounds.width, bounds.height)
        )


def install_relation_map_runtime(canvas) -> RelationMapRuntime:
    return RelationMapRuntime(canvas)
