from __future__ import annotations


class SpacePanState:
    """Small Qt-independent state machine for Space + Left Drag panning."""

    def __init__(self) -> None:
        self.space_pressed = False
        self.active = False

    def press_space(self) -> None:
        self.space_pressed = True

    def release_space(self) -> bool:
        was_active = self.active
        self.space_pressed = False
        self.active = False
        return was_active

    def begin_left_drag(self) -> bool:
        if not self.space_pressed or self.active:
            return False
        self.active = True
        return True

    def end_left_drag(self) -> bool:
        if not self.active:
            return False
        self.active = False
        return True

    def reset(self) -> None:
        self.space_pressed = False
        self.active = False
