from .contracts import (
    DraftItem,
    DraftLane,
    DraftScheduleSnapshot,
    RelationGraphPayload,
    relation_graph_payload,
    schedule_snapshot,
)

__all__ = [
    "DraftItem",
    "DraftLane",
    "DraftScheduleSnapshot",
    "RelationGraphPayload",
    "relation_graph_payload",
    "schedule_snapshot",
    "DraftToolsHost",
]


def __getattr__(name: str):
    if name == "DraftToolsHost":
        from .panel import DraftToolsHost

        return DraftToolsHost
    raise AttributeError(name)
