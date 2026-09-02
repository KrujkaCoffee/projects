from .dirty_tracker import DirtyTracker

__all__ = ['DirtyTracker', 'QtEditStateBinder', 'resolve_pending_changes']


def __getattr__(name: str):
    if name == 'QtEditStateBinder':
        from .qt_table_binder import QtEditStateBinder

        return QtEditStateBinder
    if name == 'resolve_pending_changes':
        from .leave_guard import resolve_pending_changes

        return resolve_pending_changes
    raise AttributeError(name)
