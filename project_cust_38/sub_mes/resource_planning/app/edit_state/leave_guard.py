from __future__ import annotations

from typing import Callable

from PyQt5.QtWidgets import QMessageBox


def resolve_pending_changes(
    parent,
    *,
    save: Callable[[], bool],
    discard: Callable[[], None],
    message: str,
) -> bool:
    """Ask Save / Discard / Cancel and return whether navigation may continue."""

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle('Неприменённые изменения связи')
    box.setText(message)
    save_button = box.addButton('Сохранить', QMessageBox.AcceptRole)
    discard_button = box.addButton('Отменить изменения', QMessageBox.DestructiveRole)
    cancel_button = box.addButton('Остаться', QMessageBox.RejectRole)
    box.setDefaultButton(save_button)
    box.exec_()
    clicked = box.clickedButton()
    if clicked is save_button:
        return bool(save())
    if clicked is discard_button:
        discard()
        return True
    if clicked is cancel_button:
        return False
    return False
