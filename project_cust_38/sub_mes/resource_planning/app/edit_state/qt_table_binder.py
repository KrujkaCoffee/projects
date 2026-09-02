from __future__ import annotations

from typing import Mapping, Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush

from app.theme import theme_color


class QtEditStateBinder:
    """Apply semantic dirty markers to relation controls and pair cells."""

    def __init__(self, form_widgets: Mapping[str, object], table, columns: Sequence[str]) -> None:
        self.form_widgets = dict(form_widgets)
        self.table = table
        self.columns = list(columns)

    @staticmethod
    def _set_widget_dirty(widget, dirty: bool) -> None:
        if widget is None or widget.property('editDirty') == dirty:
            return
        widget.setProperty('editDirty', dirty)
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def refresh(self, baseline: dict, current: dict) -> None:
        before_relation = baseline.get('relation') or {}
        after_relation = current.get('relation') or {}
        for field, widget in self.form_widgets.items():
            self._set_widget_dirty(widget, before_relation.get(field) != after_relation.get(field))

        before_pairs = baseline.get('pairs') or []
        after_pairs = current.get('pairs') or []
        old_blocked = self.table.blockSignals(True)
        try:
            for row in range(self.table.rowCount()):
                before = before_pairs[row] if row < len(before_pairs) else {}
                after = after_pairs[row] if row < len(after_pairs) else {}
                for column, field in enumerate(self.columns):
                    item = self.table.item(row, column)
                    if item is None:
                        continue
                    if before.get(field) != after.get(field):
                        item.setData(Qt.BackgroundRole, QBrush(theme_color("dirty_bg")))
                    else:
                        item.setData(Qt.BackgroundRole, None)
        finally:
            self.table.blockSignals(old_blocked)
