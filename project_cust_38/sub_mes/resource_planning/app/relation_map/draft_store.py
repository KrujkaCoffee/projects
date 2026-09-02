from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from app.edit_state import DirtyTracker


def _public_relation(relation: dict) -> dict:
    result = copy.deepcopy(relation or {})
    result.pop('_original_relation_key', None)
    return result


@dataclass
class DraftEntry:
    draft_id: str
    relation: dict
    pairs: List[dict]
    baseline: Optional[dict] = None
    original_relation_key: str = ''
    _tracker: DirtyTracker = field(default_factory=DirtyTracker, init=False, repr=False)

    def __post_init__(self) -> None:
        self.relation = copy.deepcopy(self.relation or {})
        self.pairs = copy.deepcopy(self.pairs or [])
        self.baseline = copy.deepcopy(self.baseline)
        self.original_relation_key = str(
            self.original_relation_key
            or self.relation.pop('_original_relation_key', '')
            or ''
        )
        self._tracker.capture(self.baseline)
        self._tracker.update(self.state())

    def state(self) -> dict:
        return {
            'relation': _public_relation(self.relation),
            'pairs': copy.deepcopy(self.pairs),
        }

    def update(self, relation: dict, pairs: List[dict]) -> None:
        self.relation = copy.deepcopy(relation or {})
        self.pairs = copy.deepcopy(pairs or [])
        self._tracker.update(self.state())

    def touch(self) -> None:
        self._tracker.update(self.state())

    @property
    def dirty(self) -> bool:
        return self._tracker.is_dirty

    @property
    def relation_key(self) -> str:
        return str(self.relation.get('relation_key') or '').strip()

    @property
    def endpoints(self) -> frozenset[str]:
        return frozenset(
            (
                str(self.relation.get('source_table_key') or ''),
                str(self.relation.get('target_table_key') or ''),
            )
        )

    def canvas_state(self) -> dict:
        relation = _public_relation(self.relation)
        if self.original_relation_key:
            relation['_original_relation_key'] = self.original_relation_key
        return {
            'draft_id': self.draft_id,
            'relation': relation,
            'pairs': copy.deepcopy(self.pairs),
        }

    def package(self) -> dict:
        return {
            'draft_id': self.draft_id,
            'relation': _public_relation(self.relation),
            'pairs': copy.deepcopy(self.pairs),
            'baseline': copy.deepcopy(self.baseline),
            'original_relation_key': self.original_relation_key,
        }


class DraftStore:
    """Коллекция локальных черновиков с устойчивым внутренним идентификатором."""

    def __init__(self, packages: Optional[Iterable[dict]] = None) -> None:
        self._entries: List[DraftEntry] = []
        self._next_id = 1
        self.active_id = ''
        if packages:
            self.load(packages)

    def _new_id(self) -> str:
        while True:
            value = f'draft-{self._next_id}'
            self._next_id += 1
            if self.find(value) is None:
                return value

    def load(self, packages: Iterable[dict]) -> None:
        self.clear()
        for package in packages:
            if not package:
                continue
            self.add(
                package.get('relation') or {},
                list(package.get('pairs') or []),
                baseline=package.get('baseline'),
                original_relation_key=str(package.get('original_relation_key') or ''),
                draft_id=str(package.get('draft_id') or ''),
                activate=False,
            )
        if self._entries:
            self.active_id = self._entries[0].draft_id

    def add(
        self,
        relation: dict,
        pairs: List[dict],
        *,
        baseline: Optional[dict] = None,
        original_relation_key: str = '',
        draft_id: str = '',
        activate: bool = True,
    ) -> DraftEntry:
        stable_id = draft_id if draft_id and self.find(draft_id) is None else self._new_id()
        entry = DraftEntry(
            stable_id,
            relation,
            pairs,
            baseline=baseline,
            original_relation_key=original_relation_key,
        )
        self._entries.append(entry)
        if activate or not self.active_id:
            self.active_id = stable_id
        return entry

    def clear(self) -> None:
        self._entries.clear()
        self.active_id = ''
        self._next_id = 1

    def find(self, draft_id: str) -> Optional[DraftEntry]:
        return next((entry for entry in self._entries if entry.draft_id == draft_id), None)

    @property
    def active(self) -> Optional[DraftEntry]:
        return self.find(self.active_id)

    @property
    def entries(self) -> tuple[DraftEntry, ...]:
        return tuple(self._entries)

    @property
    def dirty_entries(self) -> tuple[DraftEntry, ...]:
        return tuple(entry for entry in self._entries if entry.dirty)

    @property
    def is_dirty(self) -> bool:
        return any(entry.dirty for entry in self._entries)

    def set_active(self, draft_id: str) -> bool:
        if self.find(draft_id) is None:
            return False
        self.active_id = draft_id
        return True

    def remove_active(self) -> Optional[DraftEntry]:
        active = self.active
        if active is None:
            return None
        index = self._entries.index(active)
        self._entries.pop(index)
        if self._entries:
            self.active_id = self._entries[min(index, len(self._entries) - 1)].draft_id
        else:
            self.active_id = ''
        return active

    def matching_endpoints(self, left: str, right: str) -> List[DraftEntry]:
        endpoints = frozenset((str(left or ''), str(right or '')))
        return [entry for entry in self._entries if entry.endpoints == endpoints]

    def update_active(self, relation: dict, pairs: List[dict]) -> bool:
        active = self.active
        if active is None:
            return False
        active.update(relation, pairs)
        return True

    def duplicate_relation_keys(self, *, dirty_only: bool = True) -> tuple[str, ...]:
        entries = self.dirty_entries if dirty_only else self.entries
        seen: set[str] = set()
        duplicates: set[str] = set()
        for entry in entries:
            key = entry.relation_key
            if not key:
                continue
            if key in seen:
                duplicates.add(key)
            seen.add(key)
        return tuple(sorted(duplicates))

    def packages(self, *, dirty_only: bool = False) -> List[dict]:
        entries = self.dirty_entries if dirty_only else self.entries
        return [entry.package() for entry in entries]

    def canvas_states(self) -> List[dict]:
        return [entry.canvas_state() for entry in self._entries]
