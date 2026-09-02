from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceBounds:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    def expanded(self, horizontal: float, vertical: float) -> 'WorkspaceBounds':
        return WorkspaceBounds(
            self.left - horizontal,
            self.top - vertical,
            self.right + horizontal,
            self.bottom + vertical,
        )

    def united(self, other: 'WorkspaceBounds') -> 'WorkspaceBounds':
        return WorkspaceBounds(
            min(self.left, other.left),
            min(self.top, other.top),
            max(self.right, other.right),
            max(self.bottom, other.bottom),
        )


class MonotonicWorkspace:
    """Grow scene bounds as cards move; never shrink them during a session."""

    def __init__(
        self,
        minimum: WorkspaceBounds = WorkspaceBounds(-1200.0, -900.0, 1200.0, 900.0),
        *,
        horizontal_margin: float = 360.0,
        vertical_margin: float = 280.0,
    ) -> None:
        self._minimum = minimum
        self._bounds = minimum
        self.horizontal_margin = horizontal_margin
        self.vertical_margin = vertical_margin

    @property
    def bounds(self) -> WorkspaceBounds:
        return self._bounds

    def include(self, content: WorkspaceBounds) -> WorkspaceBounds:
        padded = content.expanded(self.horizontal_margin, self.vertical_margin)
        self._bounds = self._bounds.united(self._minimum).united(padded)
        return self._bounds
